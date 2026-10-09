"""Build compact_climate_weather_oracle_v1 inputs: compact baseline (H0/H3/H6/H12) and baseline + raw oracle (H3/H6/H12).

Rows, labels, cohort, static context, coordinates/target calendar, safe IPC history and national IDP come unchanged
from the frozen parent ``origin_safe_climate_idp_v1`` inputs. The monthly dynamic and growing-season block is rebuilt
directly at each row's origin ``O = T - H`` from the pinned source grids (``ipcch.compact_features``; no carrier-row or
saved-extra-NA masks). Writes one dataset per arm and horizon, season/oracle ledgers, source-support perturbation
checks, old-vs-new comparability and coverage diagnostics and a manifest binding parent/source/contract/code hashes.
Parent and legacy files are never modified. Design: ``.trellis/tasks/10-08-compact-climate-weather-oracle/design.md``.
"""
from __future__ import annotations

import argparse
import json
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = next(path for path in Path(__file__).resolve().parents if (path / "src").exists())
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import numpy as np
import pandas as pd

from ipcch import climate2015_features as cf
from ipcch import compact_features as cpf
from ipcch import origin_safe as osf
from ipcch import paths
from ipcch import retained_feature_recipes as rr
from ipcch import weather_oracle as wo

VERSION = cpf.VERSION
MODEL_READY = paths.SOURCE_DATA_DIR / "assembled_IPCCH" / "model_ready"
PARENT_MANIFEST = MODEL_READY / cpf.PARENT_VERSION / f"{cpf.PARENT_VERSION}_manifest.json"
PARENT_MANIFEST_SHA256 = "3b479c80498e9f2d6d20b88936fce468f297d2e0ccd6f0cb32c61a7470a209bf"
ORACLE_V1_MANIFEST = MODEL_READY / wo.ORACLE_VERSION / f"{wo.ORACLE_VERSION}_manifest.json"
OUT_DIR = MODEL_READY / VERSION
CHECK_DIR = paths.RESULTS_DIR / "experiments" / VERSION / "input_checks"
TASK_DIR = PROJECT_ROOT / ".trellis" / "tasks" / "10-08-compact-climate-weather-oracle"
KEYS = list(osf.KEYS)
LABEL_COLUMNS = ["overall_phase", *osf.SHARE_COLUMNS]
SUPPORT_CUTOFFS = ("2022-06", "2024-03")
EXPECTED_EVAL = {2022: 5599, 2023: 6064, 2024: 5127, 2025: 11415}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--horizons", type=int, nargs="+", default=list(osf.HORIZONS), choices=osf.HORIZONS)
    parser.add_argument("--out-dir", default=str(OUT_DIR))
    parser.add_argument("--check-dir", default=str(CHECK_DIR))
    parser.add_argument("--contract-dir", default=str(TASK_DIR), help="Directory holding the approved expected-feature contract.")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def log(t0: float, message: str) -> None:
    print(f"[{time.time() - t0:6.0f}s] {message}", flush=True)


def ord_of(text: str) -> int:
    year, month = (int(x) for x in text.split("-"))
    return year * 12 + month - 1


def check_pinned(item: dict, label: str) -> None:
    if osf.file_sha256(item["path"]) != item["sha256"]:
        raise SystemExit(f"{label} differs from the parent manifest: {item['path']}")


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


def unchanged(a: pd.DataFrame, b: pd.DataFrame) -> pd.DataFrame:
    x, y = a.to_numpy(dtype=float), b.to_numpy(dtype=float)
    return pd.DataFrame((x == y) | (np.isnan(x) & np.isnan(y)), columns=a.columns)


def old_candidates(name: str, horizon: int) -> list:
    """Parent-dataset columns computing the same quantity at the same origin (recipes that existed before)."""
    sfx = f"_asof{horizon}_s{horizon}" if horizon != 12 else "_asof12"
    lag = f"__l{horizon}_s{horizon}" if horizon != 12 else "__l12"
    for stat in ("share12", "months_since", "longest_run12", "any12"):
        if name.endswith(f"__{stat}_at_origin"):
            return [name.replace(f"__{stat}_at_origin", f"__{stat}{sfx}")]
    if name.startswith("gs_last"):
        if name == cpf.MAJOR:
            return []
        base = name.replace("__at_origin", "").replace("_at_origin", "")
        return [base + sfx]
    if "__hist_same_month_z_at_origin" in name and horizon == 12:
        return [name.replace("__hist_same_month_z_at_origin", "__hist_same_month_z_l12")]
    if "__hist_same_month_z" in name:
        return []
    for w in cpf.MA_WINDOWS:
        if name.endswith(f"__ma{w}_at_origin"):
            return [name.replace(f"__ma{w}_at_origin", f"__roll{w}_mean{sfx}")]
    if name.endswith("__sd12_at_origin"):
        return [name.replace("__sd12_at_origin", f"__roll12_std{sfx}")]
    if name.endswith("__value_at_origin"):
        return [name.replace("__value_at_origin", lag)]
    return []


def comparability(new: pd.DataFrame, parent: pd.DataFrame, horizon: int, eval_rows: np.ndarray) -> pd.DataFrame:
    """Old vs new on matched keys for features whose old recipe existed at the same origin (diagnostic only)."""
    rows = []
    for name in new.columns:
        old_names = [c for c in old_candidates(name, horizon) if c in parent.columns]
        if not old_names:
            rows.append({"horizon": horizon, "feature": name, "old_feature": None, "status": "no_comparable_old_recipe"})
            continue
        n = new[name].to_numpy(dtype=float)
        o = parent[old_names[0]].to_numpy(dtype=float)
        both = ~np.isnan(n) & ~np.isnan(o)
        close = np.zeros(len(n), dtype=bool)
        close[both] = np.isclose(n[both], o[both], rtol=1e-9, atol=1e-12)
        restored = np.isnan(o) & ~np.isnan(n)
        lost = ~np.isnan(o) & np.isnan(n)
        rows.append({"horizon": horizon, "feature": name, "old_feature": old_names[0], "n_rows": len(n), "both_present": int(both.sum()),
                     "value_mismatch": int((both & ~close).sum()),
                     "max_abs_diff": float(np.max(np.abs(n[both] - o[both]))) if both.any() else 0.0,
                     "old_na_restored": int(restored.sum()), "old_na_restored_eval": int((restored & eval_rows).sum()),
                     "old_present_now_na": int(lost.sum()), "both_na": int((np.isnan(o) & np.isnan(n)).sum()),
                     "status": "equal_where_both_present" if not (both & ~close).any() else "value_mismatch"})
    return pd.DataFrame(rows)


def coverage(frame: pd.DataFrame, features: list, ords: np.ndarray, share_valid: np.ndarray, eval_key: np.ndarray, horizon: int) -> pd.DataFrame:
    """Non-missing counts per feature for each annual fitting batch and each evaluation year."""
    rows = []
    values = frame[features].notna().to_numpy()
    years = frame["year"].to_numpy()
    for year in osf.TARGET_YEARS:
        fit = share_valid & (ords <= year * 12 - max(horizon, 1))
        ev = eval_key & (years == year)
        for role, mask in (("fit_batch", fit), ("evaluation", ev)):
            n = values[mask].sum(axis=0)
            for name, k in zip(features, n):
                rows.append({"horizon": horizon, "year": year, "rows_role": role, "feature": name, "rows": int(mask.sum()),
                             "nonmissing": int(k), "nonmissing_rate": float(k / mask.sum()) if mask.any() else None})
    return pd.DataFrame(rows)


def main() -> int:
    args = parse_args()
    t0 = time.time()
    out_dir, check_dir = Path(args.out_dir), Path(args.check_dir)
    if any(ns in out_dir.resolve().parts for ns in cpf.LEGACY_NAMESPACES) or any(ns in check_dir.resolve().parts for ns in cpf.LEGACY_NAMESPACES):
        raise SystemExit("refusing to write into a legacy feature-version namespace")
    manifest_path = out_dir / f"{VERSION}_manifest.json"
    if manifest_path.exists() and not args.overwrite:
        raise SystemExit(f"{manifest_path} exists (use --overwrite)")
    if osf.file_sha256(PARENT_MANIFEST) != PARENT_MANIFEST_SHA256:
        raise SystemExit("parent manifest sha256 differs from the frozen reference")
    parent = json.loads(PARENT_MANIFEST.read_text(encoding="utf-8"))
    if parent.get("version") != cpf.PARENT_VERSION or parent.get("status") != "COMPLETE":
        raise SystemExit("parent manifest is not the COMPLETE origin_safe_climate_idp_v1 build")
    contract_dir = Path(args.contract_dir)
    contract_hashes = {name: osf.file_sha256(contract_dir / name) for name in cpf.FROZEN_CONTRACT_SHA256}
    if contract_hashes != cpf.FROZEN_CONTRACT_SHA256:
        raise SystemExit(f"approved contract files differ from the frozen hashes: {contract_hashes}")
    contract = json.loads((contract_dir / "expected_feature_contract_metadata.json").read_text(encoding="utf-8-sig"))
    for name in ("interim", "climate_monthly", "climate_seasonal"):
        check_pinned(parent["inputs"][name], f"source {name}")
    check_pinned(parent["cohort"], "parent cohort")
    out_dir.mkdir(parents=True, exist_ok=True)
    check_dir.mkdir(parents=True, exist_ok=True)
    # byte copy of the approved contract inside the versioned input namespace: archiving the task cannot break this version
    contract_copy = out_dir / "contract"
    contract_copy.mkdir(exist_ok=True)
    contract_files = {}
    for name, digest in cpf.FROZEN_CONTRACT_SHA256.items():
        shutil.copyfile(contract_dir / name, contract_copy / name)
        if osf.file_sha256(contract_copy / name) != digest:
            raise SystemExit(f"contract copy {name} differs from the approved bytes")
        contract_files[name] = {"path": str(contract_copy / name), "sha256": digest}
    approval = contract_dir / "execution-approval.json"
    code = (Path(__file__), *(PROJECT_ROOT / rel for rel in cpf.HELPER_MODULES))
    members = parent["commodity_members"]
    manifest = {
        "version": VERSION, "status": "BUILDING", "created_utc": pd.Timestamp.now(tz="UTC").isoformat(),
        "git_head": subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=PROJECT_ROOT).stdout.strip(),
        "git_status_porcelain": subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, cwd=PROJECT_ROOT).stdout,
        "runtime": {"python": sys.version, "platform": platform.platform(), "numpy": np.__version__, "pandas": pd.__version__,
                    "executable": sys.executable},
        "code_sha256": {str(p.relative_to(PROJECT_ROOT)): osf.file_sha256(p) for p in code},
        "parent_manifest": {"path": str(PARENT_MANIFEST), "sha256": PARENT_MANIFEST_SHA256, "version": cpf.PARENT_VERSION, "arm": cpf.PARENT_ARM},
        "contract": {"files": contract_files, "spec_sha256": contract["spec_sha256"],
                     "features_by_run_sha256": {run: osf.list_sha256(f) for run, f in contract["features_by_run"].items()},
                     "approved_source": {"task_dir": str(contract_dir), "sha256": contract_hashes,
                                         "execution_approval": {"path": str(approval), "sha256": osf.file_sha256(approval)} if approval.exists() else None,
                                         "planning_commit": "928d08081376311b298358cbad5eb8b21ad7fc35"}},
        "sources": {name: parent["inputs"][name] for name in ("interim", "climate_monthly", "climate_seasonal")},
        "commodity_members": members,
        "cohort": parent["cohort"],
        "arms": {cpf.BASELINE_ARM: {"horizons": list(cpf.ARM_HORIZONS[cpf.BASELINE_ARM]),
                                    "definition": "static29 -> ordinary120 -> same-month z56 -> stress28 -> seasons29 -> coordinates/calendar27 -> history5 -> IDP2"},
                 cpf.ORACLE_ARM: {"horizons": list(cpf.ARM_HORIZONS[cpf.ORACLE_ARM]),
                                  "definition": "compact baseline followed by raw prcp_anom/tmean_anom at O+1..O+min(H,6); H0 uses the baseline"}},
        "recipes": {
            "origin": "O = T - H in dense month ordinals; every monthly recipe is evaluated at the calendar month O on a keyed grid",
            "ordinary": "value x[O]; MA3/MA6/MA12 mean of non-missing x[O-w+1..O] with >= 2/3/6 values; SD12 sample SD (ddof 1) over O-11..O with >= 6 values",
            "same_month_z": "z[u] = (x[u] - mean(P[u])) / sd(P[u], ddof 1), P[u] = non-missing values of the same calendar month in strictly earlier "
                            "years; NaN if x[u] missing, < 2 prior values or zero prior spread (exact all-equal test); then z[O] and MA3/6/12 of monthly z",
            "stress": "inherited rules: GPP x < 0.9 x[u-12] (missing year-ago -> 0); conflict x > 0; WFP (x - x[u-12]) / x[u-12] > 0.10 "
                      "(missing/zero denominator -> 0); |ENSO| > 0.5; SPI03 <= -1; tmean anomaly >= 1; EVI anomaly <= -0.015; current NA -> NA; "
                      "share12/any12 over O-11..O with >= 6 valid; months_since over all history; longest_run12 (NA breaks runs, >= 6 valid)",
            "seasons": "two latest records with end_exclusive <= first day of O+1 (end, then start; later start wins tied end); 13 metrics and "
                       "months since end per rank; gs_last1 major = longer calendar duration (end_exclusive - start) of its same-year s1/s2 pair, "
                       "ties/unpaired/no season NA",
            "masks": "D16: no carrier-row (O+12) and no saved-extra-NA masks; no interpolation or forward fill; source-native NA retained",
            "raw_oracle": "realized prcp_anom/tmean_anom at O+1..O+min(H,6) by calendar month, assumed available at O (only declared exception)",
        },
        "timing_contract": {**parent["timing_contract"],
                            "weather_oracle_exception": "oracle arm only: prcp_anom_month_ensmean and tmean_anom_month_ensmean at O+1..O+min(H,6)"},
        "limits": [
            "Observation/report month is the availability proxy; historical release vintages and supplier climatology-fitting samples are unverified.",
            "Static geospatial/context snapshots are fixed retrospective context, not historical vintages.",
            "National DTM IDP stock is country-level context; old reports are stale.",
            "BBG composites keep mixed member quote scales; stress rules keep their original missing-comparator behaviour (D14).",
            "Major season means longer calendar duration of the s1/s2 pair, not certified agronomic importance.",
            "D16 changes missingness as well as the feature set; differences from older runs are not attributable to deleting features alone.",
            "Histories that are near-constant but not identical (source float noise) keep finite, possibly very large z values; no clipping.",
            "The weather oracle is a counterfactual perfect forecast, not historical forecast-vintage evidence.",
            "Rolling, z and stress windows are gathered at O inside each source grid (interim 2010-01..2026-04, climate "
            "2015-01..2026-08); an origin after a grid's last month would be NA even where earlier months could support a "
            "window. The frozen cohort has no such origin (checked per horizon); future cohorts are out of scope.",
        ],
        "horizons": {},
    }

    # ---------------------------------------------------------------- sources
    interim_path = parent["inputs"]["interim"]["path"]
    header = pd.read_csv(interim_path, nrows=0).columns
    if rr.commodity_members(header) != members:
        raise SystemExit("bbg member columns in the interim header differ from the pinned parent members")
    member_cols = [c for cols in members.values() for c in cols]
    panel = pd.read_csv(interim_path, usecols=["admin_code", "year", "month", *cpf.INTERIM_SOURCES[:7], *member_cols]).rename(columns={"admin_code": "area_id"})
    if panel.duplicated(KEYS).any():
        raise SystemExit("interim panel has duplicate keys")
    interim = cpf.interim_grid(panel, members)
    del panel
    monthly = pd.read_csv(parent["inputs"]["climate_monthly"]["path"], usecols=["admin_code", "year", "month", *cpf.CLIMATE_SOURCES]).rename(columns={"admin_code": "area_id"})
    climate = cf.Grid.from_long(monthly, cpf.CLIMATE_SOURCES)
    del monthly
    for grid in (interim, climate):
        for v, arr in grid.values.items():
            if np.isinf(arr).any():
                raise SystemExit(f"{v}: infinite source values")
    seasons = pd.read_csv(parent["inputs"]["climate_seasonal"]["path"],
                          usecols=["admin_code", "season_year", "season", "gs_start_date", "gs_end_date_exclusive", *cpf.SEASON_METRICS])
    z_guard = {}
    for s in cpf.Z_SOURCES:
        grid = interim if s in cpf.INTERIM_SOURCES else climate
        mean, std, _ = cf.same_month_history(grid.values[s], grid.first_ord)
        with np.errstate(invalid="ignore", divide="ignore"):
            legacy_z = cf.safe_divide(grid.values[s] - mean, std)
        z_guard[s] = int((np.isfinite(legacy_z) & np.isnan(cpf.same_month_z(grid.values[s], grid.first_ord))).sum())
    manifest["source_grids"] = {
        "interim": {"first_month": osf.ord_label(interim.first_ord), "last_month": osf.ord_label(interim.first_ord + interim.n_months - 1),
                    "areas": len(interim.area_ids), "missing_cells": {v: int(np.isnan(a).sum()) for v, a in interim.values.items()}},
        "climate_monthly": {"first_month": osf.ord_label(climate.first_ord), "last_month": osf.ord_label(climate.first_ord + climate.n_months - 1),
                            "areas": len(climate.area_ids), "missing_cells": {v: int(np.isnan(a).sum()) for v, a in climate.values.items()}},
        "seasons": {"rows": len(seasons), "areas": int(seasons["admin_code"].nunique())},
        "same_month_z_exact_constant_history_cells_set_na": z_guard,
    }
    log(t0, f"grids: interim {manifest['source_grids']['interim']['first_month']}..{manifest['source_grids']['interim']['last_month']}, "
            f"climate {manifest['source_grids']['climate_monthly']['first_month']}..{manifest['source_grids']['climate_monthly']['last_month']}; z guard {z_guard}")

    cohort = pd.read_csv(parent["cohort"]["path"])
    keys = cohort[KEYS]
    eval_key = cohort["eval_key"].to_numpy(dtype=bool)
    share_valid = cohort["share_valid"].to_numpy(dtype=bool)
    if osf.keys_sha256(cohort.loc[eval_key]) != parent["cohort"]["eval_keys_sha256"] \
            or {int(k): int(v) for k, v in cohort.loc[eval_key, "year"].value_counts().items()} != EXPECTED_EVAL:
        raise SystemExit("frozen evaluation cohort differs")
    ords = osf.month_ord(keys["year"], keys["month"])
    horizons = list(args.horizons)
    span = {}
    for h in horizons:
        origin = ords - h
        span[str(h)] = {name: {"origin_after_last_month": int((origin > g.first_ord + g.n_months - 1).sum()),
                               "origin_before_first_month": int((origin < g.first_ord).sum())}
                        for name, g in (("interim", interim), ("climate_monthly", climate))}
        if any(v["origin_after_last_month"] for v in span[str(h)].values()):
            raise SystemExit(f"h{h}: cohort origins after a source grid's last month (out of scope): {span[str(h)]}")
    manifest["origin_within_source_span"] = span
    blocks = cpf.monthly_block(interim, climate, keys, horizons)
    log(t0, f"monthly blocks built for H={horizons}: {blocks[horizons[0]].shape[1]} columns")

    # ---------------------------------------------------------------- source-support perturbation (non-oracle and oracle)
    rng = np.random.default_rng(20261008)
    support_rows = []
    oracle_support_rows = []
    for cutoff_text in SUPPORT_CUTOFFS:
        cutoff = ord_of(cutoff_text)
        late_interim, late_climate = perturbed(interim, True, cutoff, rng), perturbed(climate, True, cutoff, rng)
        late_blocks = cpf.monthly_block(late_interim, late_climate, keys, horizons)
        pseasons = seasons.copy()
        first_day_after = pd.Timestamp(year=(cutoff + 1) // 12, month=(cutoff + 1) % 12 + 1, day=1)
        late_season = (pd.to_datetime(pseasons["gs_end_date_exclusive"]) > first_day_after).to_numpy()
        for m in cpf.SEASON_METRICS:
            pseasons.loc[late_season, m] = pseasons.loc[late_season, m] + 100.0
        early_climate = perturbed(climate, False, cutoff, rng)
        for h in horizons:
            origin = ords - h
            early, later = origin <= cutoff, origin > cutoff
            base_s, _ = cpf.completed_seasons(seasons, keys["area_id"].to_numpy(), origin)
            pert_s, _ = cpf.completed_seasons(pseasons, keys["area_id"].to_numpy(), origin)
            same = pd.concat([unchanged(blocks[h], late_blocks[h]), unchanged(base_s, pert_s)], axis=1)
            for name in same.columns:
                ok = same[name].to_numpy()
                support_rows.append({"horizon": h, "cutoff": cutoff_text, "feature": name, "rows_origin_le_cutoff": int(early.sum()),
                                     "changed_rows_origin_le_cutoff": int((~ok & early).sum()),
                                     "power_changed_rows_origin_gt_cutoff": int((~ok & later).sum())})
            if h in wo.ORACLE_HORIZONS:
                m = wo.window(h)
                base_o, _ = cpf.raw_oracle_block(climate, keys, h)
                late_o, _ = cpf.raw_oracle_block(late_climate, keys, h)
                early_o, _ = cpf.raw_oracle_block(early_climate, keys, h)
                closed = origin + m <= cutoff
                beyond = closed & (origin + h > cutoff)
                future_only = origin >= cutoff
                same_late, same_early = unchanged(base_o, late_o), unchanged(base_o, early_o)
                for name in base_o.columns:
                    oracle_support_rows.append({"horizon": h, "cutoff": cutoff_text, "feature": name,
                                                "rows_window_closed": int(closed.sum()), "changed_window_closed": int((~same_late[name] & closed).sum()),
                                                "rows_beyond_window_perturbed": int(beyond.sum()),
                                                "changed_beyond_window_perturbed": int((~same_late[name] & beyond).sum()),
                                                "rows_origin_ge_cutoff": int(future_only.sum()),
                                                "changed_origin_ge_cutoff_by_past_perturbation": int((~same_early[name] & future_only).sum()),
                                                "power_changed_window_open": int((~same_late[name] & ~closed).sum())})
        del late_interim, late_climate, late_blocks, early_climate
    support = pd.DataFrame(support_rows)
    support.to_csv(check_dir / "source_support.csv", index=False)
    oracle_support = pd.DataFrame(oracle_support_rows)
    oracle_support.to_csv(check_dir / "oracle_source_support.csv", index=False)
    bad = support[support["changed_rows_origin_le_cutoff"] > 0]
    if len(bad):
        raise SystemExit(f"post-origin source perturbation changed {len(bad)} feature/cutoff cells:\n{bad.head(20)}")
    if len(oracle_support) and ((oracle_support["changed_window_closed"] > 0) | (oracle_support["changed_origin_ge_cutoff_by_past_perturbation"] > 0)).any():
        raise SystemExit("raw oracle columns depend on undeclared months")
    log(t0, f"source-support perturbation passed ({len(support)} + {len(oracle_support)} feature/cutoff cells)")

    # ---------------------------------------------------------------- per-horizon datasets
    oracle_v1 = json.loads(ORACLE_V1_MANIFEST.read_text(encoding="utf-8")) if ORACLE_V1_MANIFEST.exists() else None
    comparisons, coverages = [], []
    for h in horizons:
        entry = parent["horizons"][str(h)]
        for label in ("dataset", "history_ledger", "idp_ledger"):
            check_pinned(entry[label], f"h{h} parent {label}")
        data = pd.read_csv(entry["dataset"]["path"], float_precision="round_trip", low_memory=False)
        if not data[KEYS].equals(keys) or osf.keys_sha256(data) != parent["cohort"]["label_keys_sha256"]:
            raise SystemExit(f"h{h}: parent dataset keys differ from the frozen cohort")
        osf.assert_history_ledger(data, pd.read_csv(entry["history_ledger"]["path"], float_precision="round_trip"), h)
        osf.assert_idp_ledger(data, pd.read_csv(entry["idp_ledger"]["path"], float_precision="round_trip"), h)
        targets = osf.normalized_cumulative_targets(data)
        if not np.array_equal(targets["share_valid"].to_numpy(), share_valid):
            raise SystemExit(f"h{h}: share validity differs from the frozen cohort")
        parent_features = entry["arms"][cpf.PARENT_ARM]["features"]
        groups = cpf.background_groups(parent_features)
        for m in range(1, 13):
            if not np.array_equal(data[f"month_{m}"].to_numpy(dtype=float), (data["month"] == m).to_numpy(dtype=float)):
                raise SystemExit(f"h{h}: month_{m} is not the target-calendar dummy")
        for y in range(2014, 2027):
            if not np.array_equal(data[f"year_{y}"].to_numpy(dtype=float), (data["year"] == y).to_numpy(dtype=float)):
                raise SystemExit(f"h{h}: year_{y} is not the target-calendar dummy")
        season_block, season_ledger = cpf.completed_seasons(seasons, keys["area_id"].to_numpy(), ords - h)
        legacy_seasons = cf.last_completed_seasons(seasons.assign(ndvi_anom_gs_ensmean=np.nan), keys["area_id"].to_numpy(), ords - h)
        for k in (1, 2):
            for m in cpf.SEASON_METRICS + ("months_since_end",):
                new = season_block[f"gs_last{k}__{m}__at_origin" if m != "months_since_end" else f"gs_last{k}__months_since_end_at_origin"]
                if not np.array_equal(new.to_numpy(dtype=float), legacy_seasons[f"gs_last{k}__{m}"].to_numpy(dtype=float), equal_nan=True):
                    raise SystemExit(f"h{h}: gs_last{k} {m} differs from the existing completed-season selection")
        season_ledger.insert(0, "area_id", keys["area_id"].to_numpy())
        season_ledger.insert(1, "year", keys["year"].to_numpy())
        season_ledger.insert(2, "month", keys["month"].to_numpy())
        season_ledger.insert(3, "horizon", h)
        dynamic = pd.concat([blocks[h], season_block], axis=1)
        if list(dynamic.columns) != cpf.dynamic_features():
            raise SystemExit(f"h{h}: dynamic block order differs from the contract")
        baseline_features = cpf.run_features(parent_features, cpf.BASELINE_ARM, h)
        if baseline_features != contract["features_by_run"][f"{cpf.BASELINE_ARM}/{h}m"]:
            raise SystemExit(f"h{h}: baseline schema differs from the approved contract")
        baseline = pd.concat([data[KEYS + LABEL_COLUMNS + groups["static"]], dynamic,
                              data[groups["identifier"] + groups["history"] + groups["idp"]]], axis=1)
        if list(baseline.columns) != KEYS + LABEL_COLUMNS + baseline_features:
            raise SystemExit(f"h{h}: baseline column order")
        feature_values = baseline[baseline_features]
        if not all(pd.api.types.is_numeric_dtype(feature_values[c]) for c in baseline_features) or np.isinf(feature_values.to_numpy(dtype=float)).any():
            raise SystemExit(f"h{h}: non-numeric or infinite baseline features")
        if osf.forbidden_features(baseline_features):
            raise SystemExit(f"h{h}: forbidden features {osf.forbidden_features(baseline_features)}")
        base_path = out_dir / f"{VERSION}_{cpf.BASELINE_ARM}_h{h}.csv"
        season_path = out_dir / f"{VERSION}_season_ledger_h{h}.csv"
        baseline.to_csv(base_path, index=False)
        season_ledger.to_csv(season_path, index=False)
        base_check = pd.read_csv(base_path, float_precision="round_trip", low_memory=False)
        if not base_check.equals(baseline):
            raise SystemExit(f"h{h}: baseline CSV round trip changed cells")
        cpf.assert_season_ledger(base_check, pd.read_csv(season_path, float_precision="round_trip"), h)
        arms = {cpf.BASELINE_ARM: {"features": baseline_features, "feature_count": len(baseline_features),
                                   "feature_sha256": osf.list_sha256(baseline_features),
                                   "dataset": {"path": str(base_path), "sha256": osf.file_sha256(base_path), "rows": len(baseline), "columns": baseline.shape[1]}}}
        horizon_entry = {"parent_dataset": entry["dataset"], "history_ledger": entry["history_ledger"], "idp_ledger": entry["idp_ledger"],
                         "season_ledger": {"path": str(season_path), "sha256": osf.file_sha256(season_path)}}
        if h in wo.ORACLE_HORIZONS:
            raw, oracle_ledger = cpf.raw_oracle_block(climate, keys, h)
            oracle_features = cpf.run_features(parent_features, cpf.ORACLE_ARM, h)
            if oracle_features != contract["features_by_run"][f"{cpf.ORACLE_ARM}/{h}m"]:
                raise SystemExit(f"h{h}: oracle schema differs from the approved contract")
            if oracle_v1 is not None:
                old = pd.read_csv(oracle_v1["horizons"][str(h)]["dataset"]["path"], usecols=KEYS + list(raw.columns), float_precision="round_trip")
                if not old[KEYS].equals(keys) or not old[list(raw.columns)].equals(raw):
                    raise SystemExit(f"h{h}: raw oracle differs from the {wo.ORACLE_VERSION} raw oracle on the same source")
                horizon_entry["raw_oracle_equals_oracle_v1"] = True
            appended = pd.concat([baseline, raw], axis=1)
            oracle_path = out_dir / f"{VERSION}_{cpf.ORACLE_ARM}_h{h}.csv"
            oracle_ledger_path = out_dir / f"{VERSION}_oracle_ledger_h{h}.csv"
            appended.to_csv(oracle_path, index=False)
            oracle_ledger.to_csv(oracle_ledger_path, index=False)
            check = pd.read_csv(oracle_path, float_precision="round_trip", low_memory=False)
            if list(check.columns) != list(base_check.columns) + list(raw.columns) or not check[list(base_check.columns)].equals(base_check):
                raise SystemExit(f"h{h}: oracle input's baseline projection differs from the compact baseline (cells/NA/order/keys/labels)")
            if not check[list(raw.columns)].equals(raw):
                raise SystemExit(f"h{h}: raw oracle changed in the CSV round trip")
            cpf.assert_oracle_ledger(check, pd.read_csv(oracle_ledger_path, float_precision="round_trip"), h)
            arms[cpf.ORACLE_ARM] = {"features": oracle_features, "feature_count": len(oracle_features), "feature_sha256": osf.list_sha256(oracle_features),
                                    "appended": list(raw.columns),
                                    "dataset": {"path": str(oracle_path), "sha256": osf.file_sha256(oracle_path), "rows": len(appended), "columns": appended.shape[1]}}
            horizon_entry["oracle_ledger"] = {"path": str(oracle_ledger_path), "sha256": osf.file_sha256(oracle_ledger_path)}
            horizon_entry["baseline_parity"] = "oracle input re-read with round_trip parsing; every baseline column equals the compact baseline input"
            coverages.append(coverage(appended, list(raw.columns), ords, share_valid, eval_key, h).assign(arm=cpf.ORACLE_ARM))
            del appended, check, raw
        comp = comparability(dynamic, data, h, eval_key)
        comparisons.append(comp)
        coverages.append(coverage(baseline, baseline_features, ords, share_valid, eval_key, h).assign(arm=cpf.BASELINE_ARM))
        horizon_entry["arms"] = arms
        horizon_entry["comparability_summary"] = {
            "features_compared": int((comp["status"] != "no_comparable_old_recipe").sum()),
            "features_with_value_mismatch": comp.loc[comp["status"] == "value_mismatch", "feature"].tolist(),
            "old_na_restored_cells": int(comp["old_na_restored"].fillna(0).sum()),
            "old_na_restored_eval_cells": int(comp["old_na_restored_eval"].fillna(0).sum()),
            "old_present_now_na_cells": int(comp["old_present_now_na"].fillna(0).sum()),
        }
        horizon_entry["season_major_eval"] = season_ledger.loc[eval_key, "gs_last1_is_major"].value_counts(dropna=False).rename(str).to_dict()
        horizon_entry["dynamic_nan_share_eval"] = float(dynamic.loc[eval_key].isna().to_numpy().mean())
        manifest["horizons"][str(h)] = horizon_entry
        log(t0, f"h{h}: wrote {[a for a in arms]} ({', '.join(str(a['feature_count']) for a in arms.values())} features); "
                f"comparability {horizon_entry['comparability_summary']['features_compared']} compared, "
                f"mismatch {len(horizon_entry['comparability_summary']['features_with_value_mismatch'])}, "
                f"restored {horizon_entry['comparability_summary']['old_na_restored_cells']}")
        del data, baseline, base_check, dynamic
    pd.concat(comparisons, ignore_index=True).to_csv(check_dir / "old_new_comparability.csv", index=False)
    pd.concat(coverages, ignore_index=True).to_csv(check_dir / "feature_coverage.csv", index=False)
    manifest["checks"] = {
        "support_cutoffs": list(SUPPORT_CUTOFFS),
        "support_cells": len(support), "support_power_changed_cells_origin_gt_cutoff": int(support["power_changed_rows_origin_gt_cutoff"].sum()),
        "oracle_support_cells": len(oracle_support),
        "files": {"source_support": str(check_dir / "source_support.csv"), "oracle_source_support": str(check_dir / "oracle_source_support.csv"),
                  "old_new_comparability": str(check_dir / "old_new_comparability.csv"), "feature_coverage": str(check_dir / "feature_coverage.csv")},
    }
    manifest["status"] = "COMPLETE"
    manifest["elapsed_seconds"] = round(time.time() - t0, 1)
    osf.dump_json(manifest_path, manifest)
    osf.dump_json(check_dir / f"{VERSION}_manifest_copy.json", manifest)
    log(t0, f"manifest {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
