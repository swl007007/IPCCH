"""Independent verification and global comparison for origin_safe_weather_oracle_v1.

``--stage reference`` (preflight, before any new fit): frozen runtime/config/manifest hashes, an inventory of
every reused reference artifact, and for the oracle-free reference ``climate_safe_history_idp`` at H0/H3/H6/H12:
fitting keys/ages/weights, normalized targets, cohort/truth, class rule, all-four-year model replay and metric
replay. ``--stage all`` adds parent-matrix parity of the appended inputs, an independent pandas replay of every
oracle column from the shared monthly source, the same checks for the six new runs, F/B/Q coverage, the
baseline-first three-arm comparison and its three paired deltas. Reference runs are only read, never refit.
Legacy helpers (scikit-learn metric replay, class rule, hashing) come from verify_origin_safe_climate_idp.py.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import platform
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = next(path for path in Path(__file__).resolve().parents if (path / "src").exists())
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import numpy as np
import pandas as pd

from ipcch import origin_safe as osf
from ipcch import paths
from ipcch import weather_oracle as wo

_spec = importlib.util.spec_from_file_location("legacy_verify", PROJECT_ROOT / "scripts" / "postprocessing" / "verify_origin_safe_climate_idp.py")
legacy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(legacy)

VERSION = wo.ORACLE_VERSION
MODEL_READY = paths.SOURCE_DATA_DIR / "assembled_IPCCH" / "model_ready"
PARENT_MANIFEST = MODEL_READY / wo.PARENT_VERSION / f"{wo.PARENT_VERSION}_manifest.json"
MANIFEST = MODEL_READY / VERSION / f"{VERSION}_manifest.json"
REFERENCE_RUNS = paths.RESULTS_DIR / "experiments" / wo.PARENT_VERSION / "runs" / wo.PARENT_ARM
RESULTS = paths.RESULTS_DIR / "experiments" / VERSION
REPORTS = paths.REPORTS_DIR / VERSION
FROZEN = {
    "parent_manifest_sha256": "3b479c80498e9f2d6d20b88936fce468f297d2e0ccd6f0cb32c61a7470a209bf",
    "eval_keys_sha256": "f0193c1402d0609556755844b476227b7188f9671323d21317336d7ef58d2e0f",
    "eval_by_year": {2022: 5599, 2023: 6064, 2024: 5127, 2025: 11415},
    "config_sha256": {"configs/forecasting_hyperparameters.json": "3742300661466f22eba8198e5d4f9c2a277615ba59562fbf27f251ecc932dd76",
                      "configs/forecasting_hyperparameters_p3.json": "cdc0e55aa15bdda932465088568b9ee717d226208ffb32076f438fb274e6317b"},
    "runtime": {"python": "3.12.3", "numpy": "2.4.4", "pandas": "3.0.3", "sklearn": "1.8.0", "xgboost": "3.2.0"},
    "protocol": {"seed": 42, "half_life_months": 24.0, "phase_threshold": 0.2, "n_jobs": 16},
}
YEARS = osf.TARGET_YEARS
KEYS = list(osf.KEYS)
TARGETS = osf.CUMULATIVE_TARGETS
PREDS = osf.PRED_COLUMNS
METRICS = osf.ORIGIN_METRICS
ARM_ORDER = (wo.PARENT_ARM, wo.RAW_ARM, wo.B6_ARM)
CONTRASTS = (("raw_oracle - reference", wo.RAW_ARM, wo.PARENT_ARM),
             ("raw_oracle_b6 - reference", wo.B6_ARM, wo.PARENT_ARM),
             ("raw_oracle_b6 - raw_oracle (whole B6 package increment)", wo.B6_ARM, wo.RAW_ARM))
METRIC_UNITS = {"exact_phase_accuracy": "share of rows, higher better", "phase3plus_accuracy": "share of rows, higher better",
                "precision_phase3plus": "share, higher better", "sensitivity_phase3plus": "share, higher better",
                "f2_phase3plus": "dimensionless, higher better", "r2_phase3plus": "dimensionless, higher better",
                "mae_phase3plus": "normalized population share, lower better", "ordinal_mae": "phase steps, lower better"}


def new_run_dir(arm: str, horizon: int) -> Path:
    return RESULTS / "runs" / arm / f"{horizon}m"


def runtime_identity() -> dict:
    import sklearn
    import xgboost

    code = ("scripts/postprocessing/verify_origin_safe_weather_oracle.py", "scripts/postprocessing/verify_origin_safe_climate_idp.py",
            "scripts/modeling/run_deep_feature_weight_decay_forecasting.py", "scripts/preprocessing/build_origin_safe_weather_oracle_inputs.py",
            "src/ipcch/origin_safe.py", "src/ipcch/weather_oracle.py", "src/ipcch/forecasting_weight_decay.py")
    return {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__, "sklearn": sklearn.__version__,
            "xgboost": xgboost.__version__, "executable": sys.executable,
            "git_head": subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=PROJECT_ROOT).stdout.strip(),
            "code_sha256": {p: legacy.sha(PROJECT_ROOT / p) for p in code if (PROJECT_ROOT / p).exists()}}


def frozen_checks(problems: list) -> dict:
    identity = runtime_identity()
    for key, want in FROZEN["runtime"].items():
        if identity[key] != want:
            problems.append(f"runtime {key} {identity[key]} != frozen {want}")
    for rel, want in FROZEN["config_sha256"].items():
        if legacy.sha(PROJECT_ROOT / rel) != want:
            problems.append(f"{rel} sha256 changed")
    if legacy.sha(PARENT_MANIFEST) != FROZEN["parent_manifest_sha256"]:
        problems.append("parent manifest sha256 changed")
    return identity


def load_labels(data: pd.DataFrame, cohort: pd.DataFrame) -> pd.DataFrame:
    """Independent normalized targets from the raw shares (not osf.normalized_cumulative_targets)."""
    labels = data[KEYS + ["overall_phase", *osf.SHARE_COLUMNS]].copy()
    if not cohort[KEYS].equals(labels[KEYS]):
        raise ValueError("cohort rows differ from dataset rows")
    shares = labels[list(osf.SHARE_COLUMNS)].to_numpy(dtype=float)
    with np.errstate(invalid="ignore", divide="ignore"):  # invalid share blocks are outside the cohort's share_valid rows
        norm = shares / shares.sum(axis=1)[:, None]
    for k, column in zip((2, 3, 4, 5), TARGETS):
        labels[column] = norm[:, k - 1:].sum(axis=1)
    labels["ord"] = labels["year"] * 12 + labels["month"] - 1
    valid = cohort["share_valid"].to_numpy(dtype=bool)
    runner = osf.normalized_cumulative_targets(data)
    if not np.array_equal(runner["share_valid"].to_numpy(), valid):
        raise ValueError("share validity differs from the frozen cohort")
    if not np.allclose(runner.loc[valid, list(TARGETS)].to_numpy(), labels.loc[valid, list(TARGETS)].to_numpy(), rtol=0, atol=1e-12):
        raise ValueError("runner normalized targets differ from the independent normalization")
    return labels


def verify_run(run: Path, label: str, features: list, horizon: int, data: pd.DataFrame, labels: pd.DataFrame, valid: np.ndarray,
               eval_keys: pd.DataFrame, problems: list, checks: dict, inventory: list, fit_digests: dict):
    """All-year verification of one saved run; returns its concatenated predictions (or None)."""
    import xgboost as xgb

    meta_path = run / "run_metadata.json"
    if not meta_path.exists():
        problems.append(f"{label}: missing run_metadata.json")
        return None, None
    meta = json.loads(meta_path.read_text())
    inventory.append({"run": label, "year": None, "artifact": "run_metadata.json", "path": str(meta_path), "recorded_sha256": None,
                      "current_sha256": legacy.sha(meta_path)})
    if meta.get("status") != "COMPLETE" or meta.get("protocol") != "origin-safe":
        problems.append(f"{label}: status/protocol {meta.get('status')}/{meta.get('protocol')}")
    if meta["features"] != features or meta["feature_count"] != len(features):
        problems.append(f"{label}: fitted feature order differs from the manifest")
    for key, want in FROZEN["protocol"].items():
        if meta.get(key) != want:
            problems.append(f"{label}: {key}={meta.get(key)} != {want}")
    payload = meta["fingerprint_payload"]
    if payload["hyperparameters_sha256"] != list(FROZEN["config_sha256"].values()) or payload["xgboost"] != FROZEN["runtime"]["xgboost"] \
            or payload["horizon"] != horizon or payload["feature_sha256"] != osf.list_sha256(features):
        problems.append(f"{label}: fingerprint payload differs from the frozen configs/runtime/features")
    if sorted(b["block_year"] for b in meta["batches"]) != list(YEARS):
        problems.append(f"{label}: annual blocks incomplete")
    position = pd.MultiIndex.from_frame(data[KEYS])
    frames = []
    for record in meta["batches"]:
        year = record["block_year"]
        bdir = run / "batches" / str(year)
        disk = json.loads((bdir / "batch_record.json").read_text())
        if disk != json.loads(json.dumps(record)) or disk["fingerprint"] != meta["fingerprint"]:
            problems.append(f"{label} {year}: batch record differs from run metadata")
        if set(disk["artifacts"]) != legacy.REQUIRED_ARTIFACTS:
            problems.append(f"{bdir}: artifact inventory is not the required set")
        for name, digest in disk["artifacts"].items():
            current = legacy.sha(bdir / name)
            inventory.append({"run": label, "year": year, "artifact": name, "path": str(bdir / name), "recorded_sha256": digest, "current_sha256": current})
            checks["artifacts_rehashed"] += 1
            if current != digest:
                problems.append(f"{bdir / name}: sha256 mismatch")
        inventory.append({"run": label, "year": year, "artifact": "batch_record.json", "path": str(bdir / "batch_record.json"),
                          "recorded_sha256": None, "current_sha256": legacy.sha(bdir / "batch_record.json")})
        origin, cutoff = year * 12 - horizon, year * 12 - max(horizon, 1)
        if legacy.ym_ord(record["fit_origin_month"]) != origin or legacy.ym_ord(record["fit_label_cutoff_month"]) != cutoff:
            problems.append(f"{bdir}: fit origin/cutoff inconsistent with horizon and block year")
        if record["feature_sha256"] != osf.list_sha256(features) or record["feature_count"] != len(features):
            problems.append(f"{bdir}: batch feature hash differs")
        fk = pd.read_csv(bdir / "fit_keys.csv.gz", float_precision="round_trip")
        ford = fk["year"].to_numpy() * 12 + fk["month"].to_numpy() - 1
        expected_fit = labels.loc[valid & (labels["ord"] <= cutoff).to_numpy(), KEYS].reset_index(drop=True)
        if not fk[KEYS].equals(expected_fit) or osf.keys_sha256(fk) != record["fit_keys_sha256"] or len(fk) != record["fit_rows"]:
            problems.append(f"{bdir}: fit keys differ from all valid labels <= min(O, T-1) or from the record")
        if ford.max() > cutoff or (fk["age_months"].to_numpy() != origin - ford).any() or \
                not np.allclose(fk["sample_weight"].to_numpy(), 0.5 ** ((origin - ford) / 24.0), rtol=0, atol=1e-15):
            problems.append(f"{bdir}: fit cutoff/age/weight check failed")
        fit_rows = position.get_indexer(pd.MultiIndex.from_frame(fk[KEYS]))
        if (fit_rows < 0).any() or not np.isfinite(labels.iloc[fit_rows][list(TARGETS)].to_numpy()).all():
            problems.append(f"{bdir}: a fitting row lacks a finite normalized target")
        checks["fit_rows_checked"] += len(fk)
        fit_digests.setdefault((horizon, year), {})[label] = osf.keys_sha256(fk)
        pred = pd.read_csv(bdir / "predictions.csv", float_precision="round_trip")
        expected_eval = eval_keys[eval_keys["year"] == year].reset_index(drop=True)
        if not pred[KEYS].equals(expected_eval) or osf.keys_sha256(pred) != record["eval_keys_sha256"]:
            problems.append(f"{bdir}: evaluation keys differ from the frozen cohort")
        pord = pred["year"].to_numpy() * 12 + pred["month"].to_numpy() - 1
        if (pord - max(horizon, 1) < cutoff).any() or [legacy.ym_ord(x) for x in pred["row_origin_month"]] != list(pord - horizon):
            problems.append(f"{bdir}: scored month cutoff earlier than the fit cutoff, or wrong row origins")
        rows = position.get_indexer(pd.MultiIndex.from_frame(pred[KEYS]))
        if (rows < 0).any():
            problems.append(f"{bdir}: prediction keys absent from the dataset")
            continue
        lab = labels.iloc[rows]
        if not np.array_equal(lab["overall_phase"].to_numpy(dtype=float), pred["overall_phase"].to_numpy(dtype=float)):
            problems.append(f"{bdir}: truth differs from reported phase")
        if not np.allclose(lab[list(TARGETS)].to_numpy(), pred[list(TARGETS)].to_numpy(), rtol=0, atol=1e-12):
            problems.append(f"{bdir}: normalized targets differ")
        if not np.array_equal(legacy.classes(pred, meta["phase_threshold"]), pred["overall_phase_pred"].to_numpy()):
            problems.append(f"{bdir}: class assignment differs from unrounded >= threshold rule")
        X = data.iloc[rows][features]
        for target, column in zip(TARGETS, PREDS):
            booster = xgb.Booster()
            booster.load_model(str(bdir / f"model_{target}.ubj"))
            if list(booster.feature_names) != features:
                problems.append(f"{bdir}: model feature names differ")
            again = booster.predict(xgb.DMatrix(X, feature_names=features))
            diff = float(np.max(np.abs(again - pred[column].to_numpy())))
            checks["max_model_replay_abs_diff"] = max(checks["max_model_replay_abs_diff"], diff)
            if not np.allclose(again, pred[column].to_numpy(), rtol=0, atol=1e-6):
                problems.append(f"{bdir}: reloaded {target} model does not reproduce saved predictions (max diff {diff})")
            checks["models_reloaded"] += 1
        saved_year = pd.read_csv(run / "predictions" / f"predictions_{year}.csv", float_precision="round_trip")
        if not saved_year.equals(pred):
            problems.append(f"{label} {year}: run-level predictions differ from the batch predictions")
        frames.append(pred)
        checks["batches"] += 1
    if len(frames) != len(YEARS):
        return None, meta
    allpred = pd.concat(frames, ignore_index=True)
    if len(allpred) != len(eval_keys) or allpred.duplicated(KEYS).any():
        problems.append(f"{label}: predictions do not cover the frozen keys exactly once")
    return allpred, meta


def metric_rows(label_arm: str, horizon: int, pred: pd.DataFrame, run: Path, problems: list) -> list:
    """scikit-learn replay of the eight metrics, checked against the runner's saved metrics (atol 1e-12, same undefined mask)."""
    saved = pd.read_csv(run / "metrics" / "metrics_overall.csv")
    saved["test_year"] = saved["test_year"].astype(str)
    rows = []
    for year in (*YEARS, "pooled"):
        part = pred if year == "pooled" else pred[pred["year"] == year]
        row = {"arm": label_arm, "horizon": horizon, "test_year": str(year), **legacy.replay(part)}
        runner = osf.flatten_origin_metrics(osf.origin_metrics(part, "overall", year))
        ref = saved[saved["test_year"] == str(year)].iloc[0]
        for metric in METRICS:
            a, b, c = row[metric], ref[metric], runner[metric]
            a = np.nan if a is None else float(a)
            b = np.nan if pd.isna(b) else float(b)
            c = np.nan if c is None else float(c)
            if np.isnan(a) != np.isnan(b) or np.isnan(a) != np.isnan(c) or (not np.isnan(a) and (abs(a - b) > 1e-12 or abs(a - c) > 1e-12)):
                problems.append(f"{label_arm} h{horizon} {year} {metric}: replay {a} / saved {b} / runner {c} disagree")
            row[f"{metric}_status"] = runner[f"{metric}_status"]
            row[f"{metric}_reason"] = runner[f"{metric}_reason"]
        rows.append(row)
    return rows


# --------------------------------------------------------------------------- appended-input checks


def independent_oracle(data: pd.DataFrame, source: pd.DataFrame, horizon: int) -> dict:
    """Raw/F/B/Q by pandas merges on calendar months (separate path from the builder's grid lookup)."""
    m = wo.window(horizon)
    base = pd.DataFrame({"row": np.arange(len(data)), "area_id": data["area_id"].to_numpy(),
                         "origin": data["year"].to_numpy() * 12 + data["month"].to_numpy() - 1 - horizon})
    src = source.assign(ord=source["year"] * 12 + source["month"] - 1).set_index(["area_id", "ord"])
    out = {}

    def at(offset):
        idx = pd.MultiIndex.from_arrays([base["area_id"].to_numpy(), (base["origin"] + offset).to_numpy()])
        return src.reindex(idx)

    future = {v: [] for v in wo.ORACLE_VARIABLES}
    past = {v: [] for v in wo.ORACLE_VARIABLES}
    for k in range(1, m + 1):
        got = at(k)
        for v in wo.ORACLE_VARIABLES:
            out[wo.raw_name(v, k)] = got[v].to_numpy(dtype=float)
            future[v].append(out[wo.raw_name(v, k)])
    for j in range(m):
        got = at(-j)
        for v in wo.ORACLE_VARIABLES:
            past[v].append(got[v].to_numpy(dtype=float))
    gate = data[wo.HISTORY_GATE].to_numpy(dtype=float)
    for v in wo.ORACLE_VARIABLES:
        f = pd.DataFrame(np.column_stack(future[v])).mean(axis=1, skipna=False).to_numpy()
        past_ok = pd.DataFrame(np.column_stack(past[v])).notna().all(axis=1).to_numpy()
        r = data[wo.parent_rolling_column(v, horizon)].to_numpy(dtype=float)
        b = np.where(past_ok & ~np.isnan(r) & ~np.isnan(f), (r + f) / 2.0, np.nan)
        q = np.where(np.isnan(f) | np.isnan(gate), np.nan, np.where(gate >= 3, f, 0.0))
        out[wo.future_mean_name(v, m)], out[wo.halfmean_name(v, m)], out[wo.gated_name(v, m)] = f, b, q
    return out


def check_appended_inputs(manifest: dict, parent: dict, horizon: int, parent_data: pd.DataFrame, source: pd.DataFrame, problems: list, checks: dict):
    entry = manifest["horizons"][str(horizon)]
    if legacy.sha(Path(entry["dataset"]["path"])) != entry["dataset"]["sha256"]:
        problems.append(f"h{horizon}: oracle dataset sha256 differs from its manifest")
    data = pd.read_csv(entry["dataset"]["path"], float_precision="round_trip", low_memory=False)
    parent_cols = list(parent_data.columns)
    declared = wo.raw_features(horizon) + wo.b6_features(horizon)
    if list(data.columns) != parent_cols + declared:
        problems.append(f"h{horizon}: appended dataset columns are not parent columns + declared oracle columns in order")
    if not data[parent_cols].equals(parent_data):
        bad = [c for c in parent_cols if not data[c].equals(parent_data[c])]
        problems.append(f"h{horizon}: inherited cells/labels/keys changed in {len(bad)} columns, e.g. {bad[:5]}")
    checks["parent_cells_compared"] += int(parent_data.shape[0] * parent_data.shape[1])
    parent_features = parent["horizons"][str(horizon)]["arms"][wo.PARENT_ARM]["features"]
    for arm in wo.ORACLE_ARMS:
        if entry["arms"][arm]["features"] != wo.arm_features(parent_features, arm, horizon) \
                or len(entry["arms"][arm]["features"]) != wo.EXPECTED_FEATURE_COUNTS[(horizon, arm)]:
            problems.append(f"h{horizon} {arm}: manifest schema differs from the declared exact order/count")
    expected = independent_oracle(data, source, horizon)
    for name in declared:
        a, b = data[name].to_numpy(dtype=float), expected[name]
        exact = name.startswith("oracle_") and "__" not in name
        same_nan = np.array_equal(np.isnan(a), np.isnan(b))
        close = np.allclose(a[~np.isnan(a)], b[~np.isnan(b)], rtol=0, atol=0 if exact else 1e-12) if same_nan else False
        if not (same_nan and close):
            problems.append(f"h{horizon}: {name} differs from the independent source replay")
        checks["oracle_columns_replayed"] += 1
    return data


def coverage_rows(data: pd.DataFrame, horizon: int, cohort: pd.DataFrame, fit_keys_by_year: dict) -> list:
    """Nonmissing counts/rates of every appended column: fitting rows per annual batch and evaluation rows per year."""
    declared = wo.raw_features(horizon) + wo.b6_features(horizon)
    position = pd.MultiIndex.from_frame(data[KEYS])
    rows = []
    for year in YEARS:
        fit = position.get_indexer(pd.MultiIndex.from_frame(fit_keys_by_year[year][KEYS]))
        ev = (cohort["eval_key"].to_numpy(dtype=bool)) & (data["year"].to_numpy() == year)
        for role, block in (("fit_batch", data.iloc[fit]), ("evaluation", data.loc[ev])):
            for name in declared:
                n = int(block[name].notna().sum())
                rows.append({"horizon": horizon, "block_or_test_year": year, "rows_role": role, "feature": name,
                             "kind": "raw" if "__" not in name else ("F" if name.endswith(f"wmean_o1_o{wo.window(horizon)}") else
                                                                     ("B" if "__halfmean_" in name else "Q")),
                             "rows": len(block), "nonmissing": n, "nonmissing_rate": n / len(block) if len(block) else None})
    return rows


# --------------------------------------------------------------------------- comparison and report


def deltas_table(replayed: pd.DataFrame) -> pd.DataFrame:
    out = []
    for label, a, b in CONTRASTS:
        for horizon in wo.ORACLE_HORIZONS:
            for year in [str(y) for y in YEARS] + ["pooled"]:
                ra = replayed[(replayed.arm == a) & (replayed.horizon == horizon) & (replayed.test_year == year)]
                rb = replayed[(replayed.arm == b) & (replayed.horizon == horizon) & (replayed.test_year == year)]
                if ra.empty or rb.empty:
                    continue
                row = {"contrast": label, "horizon": horizon, "test_year": year, "n_samples": int(ra["n_samples"].iloc[0])}
                for metric in METRICS:
                    x, y = ra[metric].iloc[0], rb[metric].iloc[0]
                    undefined = x is None or y is None or pd.isna(x) or pd.isna(y)
                    row[metric] = None if undefined else float(x) - float(y)
                    row[f"{metric}_status"] = "undefined" if undefined else "ok"
                out.append(row)
    return pd.DataFrame(out)


def fmt(value, digits: int = 4) -> str:
    return "undefined" if value is None or pd.isna(value) else f"{value:.{digits}f}"


def write_report(replayed: pd.DataFrame, deltas: pd.DataFrame, coverage: pd.DataFrame, summary: dict, manifest: dict) -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    head = "| arm | year | n | exact-phase acc | phase 3+ acc | precision 3+ | recall 3+ | F2 3+ | R² 3+ | MAE 3+ | ordinal MAE |"
    sep = "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    lines = [f"# {VERSION}: perfect-weather oracle comparison on the origin-safe climate/IDP reference (global)", "",
             f"Machine-readable sources: `results/experiments/{VERSION}/verification/`. Metrics are replayed with scikit-learn from saved "
             "unrounded predictions on the frozen 28,205 evaluation keys and match the runner's metrics (atol 1e-12, same undefined mask).", "",
             f"Verification passed: `{summary['passed']}`; runs {summary['runs_verified']}/10; batches {summary['batches']}; "
             f"models reloaded {summary['models_reloaded']} (all four years of every run); artifacts re-hashed {summary['artifacts_rehashed']}.", "",
             "## Configurations", "",
             f"1. **Reference (oracle-free)** `{wo.PARENT_ARM}` from `{wo.PARENT_VERSION}`: shared monthly climate, completed growing-season "
             "climate, safe IPC history and national IDP. Saved models/predictions were verified and reused, not refit. "
             "This is the original reference configuration, not a claim that it was run first.",
             f"2. **+ raw oracle** `{wo.RAW_ARM}`: realized `prcp_anom_month_ensmean` and `tmean_anom_month_ensmean` at O+1..O+min(H,6) "
             "(6/12/12 columns at H3/H6/H12), treated as perfect forecasts assumed available at origin O.",
             f"3. **+ raw oracle + B6** `{wo.B6_ARM}`: adds per variable the future mean F, the equal-weight past/future mean B=(R+F)/2 "
             "and the safe-history IPC3+-gated future mean Q.", "",
             "Metric units/directions: " + "; ".join(f"`{k}` {v}" for k, v in METRIC_UNITS.items()) + ". Differences are in the same units "
             "(accuracy/MAE differences are raw shares, not percentage points). Evaluation uses observation-row weighting.", ""]
    lines += ["## H = 0 (reference only; no oracle columns or new fits)", "", head, sep]
    for _, r in replayed[replayed.horizon == 0].iterrows():
        lines.append(f"| reference | {r.test_year} | {r.n_samples} | " + " | ".join(fmt(r[m]) for m in METRICS) + " |")
    lines.append("")
    names = {wo.PARENT_ARM: "reference", wo.RAW_ARM: "+raw oracle", wo.B6_ARM: "+raw oracle+B6"}
    for horizon in wo.ORACLE_HORIZONS:
        lines += [f"## H = {horizon} months", "", head, sep]
        for arm in ARM_ORDER:
            for _, r in replayed[(replayed.horizon == horizon) & (replayed.arm == arm)].iterrows():
                lines.append(f"| {names[arm]} | {r.test_year} | {r.n_samples} | " + " | ".join(fmt(r[m]) for m in METRICS) + " |")
        lines.append("")
    lines += ["## Paired differences (identical keys, truths and per-year fitting keys; single seed 42 point estimates)", "",
              "| contrast | H | year | exact-phase acc | phase 3+ acc | precision 3+ | recall 3+ | F2 3+ | R² 3+ | MAE 3+ | ordinal MAE |",
              "|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for _, r in deltas.iterrows():
        lines.append(f"| {r.contrast} | {r.horizon} | {r.test_year} | " + " | ".join(fmt(r[m]) for m in METRICS) + " |")
    pooled = coverage.groupby(["horizon", "rows_role", "kind"]).agg(rows=("rows", "sum"), nonmissing=("nonmissing", "sum")).reset_index()
    pooled["nonmissing_rate"] = pooled["nonmissing"] / pooled["rows"]
    lines += ["", "## Oracle/B6 coverage (diagnostic only)", "",
              "Summed over the declared columns of each kind and over the four years; fitting rows are counted once per annual batch "
              "(the same row recurs in later batches), so fitting totals are not unique observations. Per-feature, per-year rows are in "
              "`verification/oracle_coverage.csv`; the per-row availability ledger records observation months, assumed availability, "
              "finite-month counts and history_1 source month/staleness.", "",
              "| H | rows | kind | row-feature cells | nonmissing | rate |", "|---:|---|---|---:|---:|---:|"]
    for _, r in pooled.iterrows():
        lines.append(f"| {r.horizon} | {r.rows_role} | {r.kind} | {r.rows} | {r.nonmissing} | {fmt(r.nonmissing_rate)} |")
    lines += ["", "## Interpretation limits", "",
              "- The oracle is a counterfactual: realized weather is assumed to be a 100%-accurate forecast available at O. It is not "
              "historical forecast-vintage evidence and not a theoretical upper bound on the value of weather information "
              "(two variables, first six post-origin months, fixed model configuration).",
              "- `raw_oracle_b6 - raw_oracle` is the increment of the whole fixed six-feature package (F, B, Q), not an isolated IPC "
              "interaction or causal effect. B is not a crop-season exposure; safe history_1 may be stale.",
              "- Single seed (42) and one fit per annual block: global differences are point estimates without intervals. Gains can be "
              "zero or negative; the frozen comparison is reported as is.",
              *[f"- {x}" for x in manifest.get("limits", [])], ""]
    (REPORTS / "global_report.md").write_text("\n".join(lines))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--stage", choices=("reference", "all"), required=True)
    parser.add_argument("--manifest", default=str(MANIFEST))
    args = parser.parse_args()
    problems: list = []
    checks = {"batches": 0, "artifacts_rehashed": 0, "models_reloaded": 0, "fit_rows_checked": 0, "max_model_replay_abs_diff": 0.0,
              "parent_cells_compared": 0, "oracle_columns_replayed": 0}
    identity = frozen_checks(problems)
    parent = json.loads(PARENT_MANIFEST.read_text())
    cohort = pd.read_csv(parent["cohort"]["path"])
    if legacy.sha(Path(parent["cohort"]["path"])) != parent["cohort"]["sha256"]:
        problems.append("parent cohort sha256 differs")
    eval_keys = cohort.loc[cohort["eval_key"], KEYS].reset_index(drop=True)
    if osf.keys_sha256(eval_keys) != FROZEN["eval_keys_sha256"] or \
            {int(k): int(v) for k, v in eval_keys["year"].value_counts().items()} != FROZEN["eval_by_year"]:
        problems.append("frozen evaluation keys differ")
    manifest = None
    source = None
    if args.stage == "all":
        manifest_path = Path(args.manifest)
        manifest = json.loads(manifest_path.read_text())
        if manifest.get("version") != VERSION or manifest.get("status") != "COMPLETE" \
                or manifest["parent_manifest"]["sha256"] != FROZEN["parent_manifest_sha256"]:
            problems.append("oracle manifest version/status/parent hash")
        src = parent["inputs"]["climate_monthly"]
        if legacy.sha(Path(src["path"])) != src["sha256"] or manifest["oracle_source"]["sha256"] != src["sha256"]:
            problems.append("shared monthly source sha256 differs")
        source = pd.read_csv(src["path"], usecols=["admin_code", "year", "month", *wo.ORACLE_VARIABLES]).rename(columns={"admin_code": "area_id"})
    out_dir = RESULTS / ("reference_preflight" if args.stage == "reference" else "verification")
    out_dir.mkdir(parents=True, exist_ok=True)
    inventory, replay_rows, fit_digests, coverage, predictions, reference_identity = [], [], {}, [], {}, {}
    for horizon in osf.HORIZONS:
        entry = parent["horizons"][str(horizon)]
        if legacy.sha(Path(entry["dataset"]["path"])) != entry["dataset"]["sha256"]:
            problems.append(f"h{horizon}: parent dataset sha256 differs")
        data = pd.read_csv(entry["dataset"]["path"], float_precision="round_trip", low_memory=False)
        labels = load_labels(data, cohort)
        valid = cohort["share_valid"].to_numpy(dtype=bool)
        ref_features = entry["arms"][wo.PARENT_ARM]["features"]
        run = REFERENCE_RUNS / f"{horizon}m"
        pred, meta = verify_run(run, f"reference h{horizon}", ref_features, horizon, data, labels, valid, eval_keys, problems, checks, inventory, fit_digests)
        if meta is not None:
            reference_identity[horizon] = {"run_dir": str(run), "original_fingerprint": meta["fingerprint"],
                                           "original_fingerprint_payload": meta["fingerprint_payload"], "run_timestamp": meta["run_timestamp"]}
        if pred is not None:
            predictions[(wo.PARENT_ARM, horizon)] = pred
            replay_rows += metric_rows(wo.PARENT_ARM, horizon, pred, run, problems)
        print(f"reference h{horizon}: verified ({len(problems)} problems so far)", flush=True)
        if args.stage == "all" and horizon in wo.ORACLE_HORIZONS:
            appended = check_appended_inputs(manifest, parent, horizon, data, source, problems, checks)
            del data
            appended_labels = load_labels(appended, cohort)
            for arm in wo.ORACLE_ARMS:
                features = manifest["horizons"][str(horizon)]["arms"][arm]["features"]
                run = new_run_dir(arm, horizon)
                pred, meta = verify_run(run, f"{arm} h{horizon}", features, horizon, appended, appended_labels, valid, eval_keys, problems,
                                        checks, inventory, fit_digests)
                if meta is not None and (meta["fingerprint_payload"].get("oracle") is None
                                         or meta["manifest"] != str(Path(args.manifest))):
                    problems.append(f"{arm} h{horizon}: run is not bound to the oracle manifest")
                if pred is not None:
                    predictions[(arm, horizon)] = pred
                    replay_rows += metric_rows(arm, horizon, pred, run, problems)
                if arm == wo.B6_ARM and meta is not None:
                    fit_keys = {y: pd.read_csv(run / "batches" / str(y) / "fit_keys.csv.gz") for y in YEARS}
                    coverage += coverage_rows(appended, horizon, cohort, fit_keys)
                print(f"{arm} h{horizon}: verified ({len(problems)} problems so far)", flush=True)
            del appended
    for (horizon, year), digests in fit_digests.items():
        if len(set(digests.values())) != 1:
            problems.append(f"h{horizon} {year}: fitting keys differ across arms")
    truth_ref = None
    for key, pred in predictions.items():
        t = pred.sort_values(KEYS)[KEYS + ["overall_phase", *TARGETS]].reset_index(drop=True)
        if truth_ref is None:
            truth_ref = t
        elif not t.equals(truth_ref):
            problems.append(f"{key}: keys/truth differ across arms/horizons")
    replayed = pd.DataFrame(replay_rows)
    replayed.to_csv(out_dir / "metrics_replay.csv", index=False)
    pd.DataFrame(inventory).to_csv(out_dir / "artifact_inventory.csv", index=False)
    expected_runs = 4 if args.stage == "reference" else 10
    summary = {"stage": args.stage, "passed": not problems and len(predictions) == expected_runs, "problems": problems,
               "runs_verified": len(predictions), "expected_runs": expected_runs, **checks,
               "eval_keys": len(eval_keys), "eval_keys_sha256": osf.keys_sha256(eval_keys),
               "reference_original_training_identity": reference_identity, "current_verification_identity": identity,
               "frozen": FROZEN, "parent_manifest": str(PARENT_MANIFEST),
               "tolerances": {"model_replay": "atol 1e-6, rtol 0", "metric_replay": "atol 1e-12, identical undefined mask",
                              "csv_parsing": "float_precision=round_trip"}}
    if args.stage == "all":
        deltas = deltas_table(replayed)
        deltas.to_csv(out_dir / "paired_deltas.csv", index=False)
        coverage = pd.DataFrame(coverage)
        coverage.to_csv(out_dir / "oracle_coverage.csv", index=False)
        comparison = replayed[replayed.horizon == 0].assign(order=0)
        comparison = pd.concat([comparison] + [replayed[(replayed.horizon == h) & (replayed.arm == a)].assign(order=i + 1)
                                               for h in wo.ORACLE_HORIZONS for i, a in enumerate(ARM_ORDER)], ignore_index=True)
        comparison.drop(columns="order").to_csv(out_dir / "global_comparison_baseline_first.csv", index=False)
        summary["manifest"] = str(args.manifest)
        summary["manifest_sha256"] = legacy.sha(Path(args.manifest))
        summary["run_paths"] = {f"{a} h{h}": str(REFERENCE_RUNS / f"{h}m" if a == wo.PARENT_ARM else new_run_dir(a, h)) for a, h in predictions}
        write_report(replayed, deltas, coverage, summary, manifest)
    osf.dump_json(out_dir / "verification_summary.json", summary)
    print(json.dumps({k: v for k, v in summary.items() if k not in ("problems", "reference_original_training_identity", "frozen")}, indent=2, default=str))
    for p in problems[:50]:
        print("PROBLEM:", p)
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
