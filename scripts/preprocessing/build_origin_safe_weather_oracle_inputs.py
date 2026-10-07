"""Build origin_safe_weather_oracle_v1 inputs: the parent origin_safe_climate_idp_v1 datasets plus oracle/B6 columns.

Append-only: for H = 3/6/12 every parent column (keys, labels, inherited features, safe history, IDP) is kept as
saved, in order, and the declared raw oracle + B6 columns (``ipcch.weather_oracle``) are appended. H0 is the shared
reference and gets no dataset. Writes the appended datasets, per-row oracle availability ledgers, source-support
perturbation checks and a manifest binding parent/source/code hashes. Parent files are never modified.
Design: ``.trellis/tasks/10-07-origin-safe-no-weather-oracle-baseline/design.md``.
"""
from __future__ import annotations

import argparse
import platform
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = next(path for path in Path(__file__).resolve().parents if (path / "src").exists())
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import json

import numpy as np
import pandas as pd

from ipcch import climate2015_features as cf
from ipcch import origin_safe as osf
from ipcch import paths
from ipcch import weather_oracle as wo

VERSION = wo.ORACLE_VERSION
MODEL_READY = paths.SOURCE_DATA_DIR / "assembled_IPCCH" / "model_ready"
PARENT_MANIFEST = MODEL_READY / wo.PARENT_VERSION / f"{wo.PARENT_VERSION}_manifest.json"
PARENT_MANIFEST_SHA256 = "3b479c80498e9f2d6d20b88936fce468f297d2e0ccd6f0cb32c61a7470a209bf"
OUT_DIR = MODEL_READY / VERSION
CHECK_DIR = paths.RESULTS_DIR / "experiments" / VERSION / "input_checks"
KEYS = list(osf.KEYS)
SUPPORT_CUTOFFS = ("2022-06", "2024-03")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--horizons", type=int, nargs="+", default=list(wo.ORACLE_HORIZONS), choices=wo.ORACLE_HORIZONS)
    parser.add_argument("--out-dir", default=str(OUT_DIR))
    parser.add_argument("--check-dir", default=str(CHECK_DIR))
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def log(t0: float, message: str) -> None:
    print(f"[{time.time() - t0:6.0f}s] {message}", flush=True)


def ord_of(text: str) -> int:
    year, month = (int(x) for x in text.split("-"))
    return year * 12 + month - 1


def perturbed(grid: cf.Grid, late: bool, cutoff: int, rng) -> cf.Grid:
    """Shift every source month after (``late``) or at/before ``cutoff`` by a large random amount."""
    months = np.arange(grid.n_months) + grid.first_ord
    cols = months > cutoff if late else months <= cutoff
    values = {}
    for v, arr in grid.values.items():
        arr = arr.copy()
        arr[:, cols] = arr[:, cols] + rng.normal(100.0, 10.0, arr[:, cols].shape)
        values[v] = arr
    return cf.Grid(grid.area_ids, grid.first_ord, grid.n_months, values)


def support_checks(grid, keys, horizon, rolling, history1, history1_src, block, cutoffs, rng) -> pd.DataFrame:
    """Post-window months must not move any new column; months <= O must not move raw/F/Q (B may move)."""
    m = wo.window(horizon)
    origin = osf.month_ord(keys["year"], keys["month"]) - horizon
    rows = []
    for cutoff in cutoffs:
        late_block, _ = wo.build_oracle_block(perturbed(grid, True, cutoff, rng), keys, horizon, rolling, history1, history1_src)
        early_block, _ = wo.build_oracle_block(perturbed(grid, False, cutoff, rng), keys, horizon, rolling, history1, history1_src)
        window_closed = origin + m <= cutoff
        beyond_window = window_closed & (origin + horizon > cutoff)  # H12: O+7..O+12 perturbed, window O+1..O+6 not
        future_only = origin >= cutoff
        for name in block.columns:
            base = block[name].to_numpy(dtype=float)
            same_late = np.isclose(base, late_block[name].to_numpy(dtype=float), rtol=0, atol=0, equal_nan=True)
            same_early = np.isclose(base, early_block[name].to_numpy(dtype=float), rtol=0, atol=0, equal_nan=True)
            protected_early = "__halfmean_" not in name
            rows.append({"horizon": horizon, "cutoff": osf.ord_label(cutoff), "feature": name,
                         "rows_window_closed": int(window_closed.sum()), "rows_beyond_window_perturbed": int(beyond_window.sum()),
                         "changed_window_closed": int((~same_late & window_closed).sum()),
                         "changed_beyond_window_perturbed": int((~same_late & beyond_window).sum()),
                         "power_changed_window_open": int((~same_late & ~window_closed).sum()),
                         "rows_origin_ge_cutoff": int(future_only.sum()),
                         "changed_origin_ge_cutoff_by_past_perturbation": int((~same_early & future_only).sum()),
                         "past_perturbation_allowed": not protected_early})
    out = pd.DataFrame(rows)
    bad = out[(out["changed_window_closed"] > 0) | (~out["past_perturbation_allowed"] & (out["changed_origin_ge_cutoff_by_past_perturbation"] > 0))]
    if len(bad):
        raise ValueError(f"h{horizon}: oracle columns depend on undeclared months:\n{bad.head(20)}")
    return out


def main() -> int:
    args = parse_args()
    t0 = time.time()
    out_dir, check_dir = Path(args.out_dir), Path(args.check_dir)
    if out_dir.resolve() == PARENT_MANIFEST.parent.resolve():
        raise SystemExit("refusing to write into the parent model-ready directory")
    manifest_path = out_dir / f"{VERSION}_manifest.json"
    if manifest_path.exists() and not args.overwrite:
        raise SystemExit(f"{manifest_path} exists (use --overwrite)")
    if osf.file_sha256(PARENT_MANIFEST) != PARENT_MANIFEST_SHA256:
        raise SystemExit("parent manifest sha256 differs from the frozen reference")
    parent = json.loads(PARENT_MANIFEST.read_text(encoding="utf-8"))
    if parent.get("version") != wo.PARENT_VERSION or parent.get("status") != "COMPLETE":
        raise SystemExit("parent manifest is not the COMPLETE origin_safe_climate_idp_v1 build")
    out_dir.mkdir(parents=True, exist_ok=True)
    check_dir.mkdir(parents=True, exist_ok=True)
    source = parent["inputs"]["climate_monthly"]
    if osf.file_sha256(source["path"]) != source["sha256"]:
        raise SystemExit("shared monthly climate source differs from the parent manifest")
    cohort_entry = parent["cohort"]
    if osf.file_sha256(cohort_entry["path"]) != cohort_entry["sha256"]:
        raise SystemExit("parent cohort file differs from the parent manifest")
    code = (Path(__file__), PROJECT_ROOT / "src/ipcch/weather_oracle.py", PROJECT_ROOT / "src/ipcch/origin_safe.py",
            PROJECT_ROOT / "src/ipcch/climate2015_features.py")
    manifest = {
        "version": VERSION, "status": "BUILDING", "created_utc": pd.Timestamp.now(tz="UTC").isoformat(),
        "git_head": subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=PROJECT_ROOT).stdout.strip(),
        "git_status_porcelain": subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, cwd=PROJECT_ROOT).stdout,
        "runtime": {"python": sys.version, "platform": platform.platform(), "numpy": np.__version__, "pandas": pd.__version__,
                    "executable": sys.executable},
        "code_sha256": {str(p.relative_to(PROJECT_ROOT)): osf.file_sha256(p) for p in code},
        "parent_manifest": {"path": str(PARENT_MANIFEST), "sha256": PARENT_MANIFEST_SHA256, "version": wo.PARENT_VERSION, "arm": wo.PARENT_ARM},
        "oracle_source": {"path": source["path"], "sha256": source["sha256"], "variables": list(wo.ORACLE_VARIABLES),
                          "parser": "pandas default float parser and admin_code -> area_id, as the parent builder; unmasked, no filling"},
        "cohort": cohort_entry,
        "reference_only_horizons": [0],
        "arms": {wo.RAW_ARM: "parent reference + raw oracle months", wo.B6_ARM: "parent reference + raw oracle + B6 (F, B, Q per variable)"},
        "timing_contract": {**parent["timing_contract"],
                            "weather_oracle_exception": "only prcp_anom_month_ensmean and tmean_anom_month_ensmean at O+1..O+min(H,6) "
                                                        "(and F/B/Q derived from them) are treated as perfect forecasts assumed available "
                                                        "at O; actual observation months are recorded separately in the oracle ledger. "
                                                        "IPC history, IDP, growing season and fitting labels keep the parent cutoffs."},
        "b6_formulas": {"F": "mean x_v(O+1..O+m); all m future months finite",
                        "B": "(R_v + F_v) / 2; F, saved parent R_v and all m past months O-m+1..O finite",
                        "Q": "F_v * 1[overall_phase_history_1 >= 3]; F and safe history_1 finite (missing F stays NaN under a zero gate)"},
        "limits": parent["limits"] + [
            "The weather oracle is a counterfactual perfect forecast (realized values assumed available at origin), not "
            "historical forecast-vintage evidence and not a theoretical upper bound on the value of weather information.",
            "Safe history_1 used by the Q gate may be stale; B is not a crop-season exposure measure.",
        ],
        "horizons": {},
    }
    monthly = pd.read_csv(source["path"], usecols=["admin_code", "year", "month", *wo.ORACLE_VARIABLES]).rename(columns={"admin_code": "area_id"})
    grid = cf.Grid.from_long(monthly, wo.ORACLE_VARIABLES)
    wo.assert_finite_or_missing(grid)
    manifest["oracle_source"].update(first_month=osf.ord_label(grid.first_ord), last_month=osf.ord_label(grid.first_ord + grid.n_months - 1),
                                     areas=len(grid.area_ids), missing_cells={v: int(np.isnan(grid.values[v]).sum()) for v in wo.ORACLE_VARIABLES})
    del monthly
    cohort = pd.read_csv(cohort_entry["path"])
    eval_rows = cohort["eval_key"].to_numpy(dtype=bool)
    rng = np.random.default_rng(20261007)
    cutoffs = [ord_of(c) for c in SUPPORT_CUTOFFS]
    log(t0, f"source grid {manifest['oracle_source']['first_month']}..{manifest['oracle_source']['last_month']}, {len(grid.area_ids)} areas")

    for horizon in args.horizons:
        entry = parent["horizons"][str(horizon)]
        for label in ("dataset", "history_ledger", "idp_ledger"):
            if osf.file_sha256(entry[label]["path"]) != entry[label]["sha256"]:
                raise SystemExit(f"h{horizon}: parent {label} differs from the parent manifest")
        data = pd.read_csv(entry["dataset"]["path"], float_precision="round_trip", low_memory=False)
        history_ledger = pd.read_csv(entry["history_ledger"]["path"], float_precision="round_trip")
        osf.assert_history_ledger(data, history_ledger, horizon)
        if osf.keys_sha256(data) != cohort_entry["label_keys_sha256"] or not cohort[KEYS].equals(data[KEYS]):
            raise SystemExit(f"h{horizon}: parent dataset keys differ from the frozen cohort")
        keys = data[KEYS]
        rolling = {v: data[wo.parent_rolling_column(v, horizon)].to_numpy(dtype=float) for v in wo.ORACLE_VARIABLES}
        history1 = data[wo.HISTORY_GATE].to_numpy(dtype=float)
        history1_src = history_ledger["history_1_source_ord"].to_numpy(dtype=float)
        block, ledger = wo.build_oracle_block(grid, keys, horizon, rolling, history1, history1_src)
        # Saved R must be the trailing mean of the same past months whenever that window is complete.
        m = wo.window(horizon)
        r_checks = {}
        for v in wo.ORACLE_VARIABLES:
            past = np.column_stack([wo.calendar_lookup(grid, keys["area_id"].to_numpy(), ledger["origin_ord"].to_numpy() - j)[v] for j in range(m)])
            full = np.isfinite(past).all(axis=1) & np.isfinite(rolling[v])
            gap = np.abs(rolling[v][full] - past[full].mean(axis=1))
            r_checks[v] = {"rows_full_past_and_R": int(full.sum()), "max_abs_diff": float(gap.max()) if full.any() else None,
                           "rows_R_finite_past_incomplete": int((np.isfinite(rolling[v]) & ~np.isfinite(past).all(axis=1)).sum()),
                           "rows_past_complete_R_missing": int((np.isfinite(past).all(axis=1) & ~np.isfinite(rolling[v])).sum())}
            if full.any() and gap.max() > 1e-9:
                raise SystemExit(f"h{horizon}: saved {wo.parent_rolling_column(v, horizon)} is not the O-{m - 1}..O mean (max diff {gap.max()})")
        support = support_checks(grid, keys, horizon, rolling, history1, history1_src, block, cutoffs, rng)
        support.to_csv(check_dir / f"oracle_source_support_h{horizon}.csv", index=False)
        log(t0, f"h{horizon}: oracle block {block.shape[1]} columns; support checks passed")

        appended = pd.concat([data, block], axis=1)
        if appended.columns.duplicated().any():
            raise SystemExit(f"h{horizon}: duplicate output columns")
        parent_features = entry["arms"][wo.PARENT_ARM]["features"]
        arms = {arm: wo.arm_features(parent_features, arm, horizon) for arm in wo.ORACLE_ARMS}
        for arm, features in arms.items():
            if len(features) != wo.EXPECTED_FEATURE_COUNTS[(horizon, arm)]:
                raise SystemExit(f"h{horizon} {arm}: {len(features)} features, expected {wo.EXPECTED_FEATURE_COUNTS[(horizon, arm)]}")
            if osf.forbidden_features(features):
                raise SystemExit(f"h{horizon} {arm}: forbidden features {osf.forbidden_features(features)}")
        data_path = out_dir / f"{VERSION}_h{horizon}.csv"
        ledger_path = out_dir / f"{VERSION}_oracle_ledger_h{horizon}.csv"
        appended.to_csv(data_path, index=False)
        ledger.to_csv(ledger_path, index=False)
        check = pd.read_csv(data_path, float_precision="round_trip", low_memory=False)
        if list(check.columns) != list(data.columns) + list(block.columns) or not check[list(data.columns)].equals(data):
            raise SystemExit(f"h{horizon}: written dataset does not reproduce every parent cell, mask, key and label")
        if not check[list(block.columns)].equals(block):
            raise SystemExit(f"h{horizon}: oracle columns changed in the CSV round trip")
        wo.assert_oracle_inputs(check, pd.read_csv(ledger_path, float_precision="round_trip"), horizon, wo.B6_ARM)
        coverage = {name: {"eval_nonmissing": int(block.loc[eval_rows, name].notna().sum()),
                           "eval_rate": float(block.loc[eval_rows, name].notna().mean())} for name in block.columns}
        manifest["horizons"][str(horizon)] = {
            "window_months": m,
            "parent_dataset": entry["dataset"],
            "dataset": {"path": str(data_path), "sha256": osf.file_sha256(data_path), "rows": len(appended), "columns": appended.shape[1]},
            "history_ledger": entry["history_ledger"], "idp_ledger": entry["idp_ledger"],
            "oracle_ledger": {"path": str(ledger_path), "sha256": osf.file_sha256(ledger_path)},
            "parent_feature_count": len(parent_features), "parent_feature_sha256": osf.list_sha256(parent_features),
            "parent_rolling_columns": {v: wo.parent_rolling_column(v, horizon) for v in wo.ORACLE_VARIABLES},
            "parent_rolling_check": r_checks,
            "arms": {arm: {"feature_count": len(f), "feature_sha256": osf.list_sha256(f), "features": f,
                           "appended": wo.appended_features(arm, horizon)} for arm, f in arms.items()},
            "parent_parity": "every parent column re-read with round_trip parsing equals the saved parent dataset (values, NaN masks, order, keys, labels)",
            "support_cutoffs": list(SUPPORT_CUTOFFS),
            "support_power_changed_cells_window_open": int(support["power_changed_window_open"].sum()),
            "support_rows_beyond_window_perturbed": int(support["rows_beyond_window_perturbed"].max()),
            "eval_coverage": coverage,
            "history_1_staleness_months_eval": ledger.loc[eval_rows, "history_1_staleness_months"].describe().to_dict(),
        }
        log(t0, f"h{horizon}: wrote {data_path.name} ({appended.shape[1]} columns) and {ledger_path.name}")
        del data, appended, check, block, ledger

    manifest["status"] = "COMPLETE"
    manifest["elapsed_seconds"] = round(time.time() - t0, 1)
    osf.dump_json(manifest_path, manifest)
    osf.dump_json(check_dir / f"{VERSION}_manifest_copy.json", manifest)
    log(t0, f"manifest {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
