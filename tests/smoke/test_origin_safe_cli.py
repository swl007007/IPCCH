import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from ipcch import origin_safe as osf

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "modeling" / "run_deep_feature_weight_decay_forecasting.py"
KEYS = list(osf.KEYS)


def run_cli(*args):
    env = {**os.environ, "PYTHONPATH": str(REPO_ROOT / "src")}
    return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=REPO_ROOT, text=True, capture_output=True, check=False, env=env)


def write_inputs(tmp_path: Path, horizon: int = 3, extra_feature=None, tamper_ledger: bool = False, full_years: bool = False) -> Path:
    rng = np.random.default_rng(0)
    if full_years:
        keys = pd.DataFrame([(a, y, m) for a in range(1, 4) for y in range(2019, 2026) for m in range(1, 13)], columns=KEYS)
    else:
        keys = pd.DataFrame([(a, y, m) for a in range(1, 13) for y in (2020, 2021, 2022) for m in range(1, 13) if (y, m) <= (2022, 3)], columns=KEYS)
    labels = keys.copy()
    labels["overall_phase"] = rng.integers(1, 6, len(labels)).astype(float)
    shares = rng.dirichlet(np.ones(5), len(labels))
    for k, column in enumerate(osf.SHARE_COLUMNS):
        labels[column] = shares[:, k]
    labels.loc[5, "phase5_percent"] = np.nan  # malformed share block: history-eligible, not fit/eval-eligible
    obs = osf.valid_phase_observations(labels)
    history, hist_ledger = osf.build_safe_history(obs, keys, horizon)
    idp_obs = osf.idp_observations(pd.DataFrame({"admin0Pcode": ["AAA", "AAA"], "year": [2020, 2021], "month": [6, 9], "idp_ind": [10.0, 20.0],
                                                 "observed": [1, 1], "reportingDate": ["2020-06-01", "2021-09-01"]}))
    iso = ["AAA" if a <= 6 else None for a in keys["area_id"]]
    idp, idp_ledger = osf.build_idp_features(idp_obs, keys, iso, horizon)
    if tamper_ledger:
        hist_ledger.loc[hist_ledger["history_1_source_ord"].notna().idxmax(), "history_1_source_ord"] = 2030 * 12
    data = pd.concat([labels, pd.DataFrame({"f1": rng.normal(size=len(keys)), "f2": rng.normal(size=len(keys))}), history, idp], axis=1)
    if extra_feature:
        data[extra_feature] = rng.normal(size=len(keys))
    targets = osf.normalized_cumulative_targets(data)
    cohort = keys.copy()
    cohort["share_valid"] = targets["share_valid"].to_numpy()
    cohort["share_total_raw"] = targets["share_total_raw"].to_numpy()
    cohort["eval_key"] = cohort["share_valid"] & cohort["year"].isin(osf.TARGET_YEARS)
    paths = {name: tmp_path / f"{name}.csv" for name in ("data", "history", "idp", "cohort")}
    data.to_csv(paths["data"], index=False)
    hist_ledger.to_csv(paths["history"], index=False)
    idp_ledger.to_csv(paths["idp"], index=False)
    cohort.to_csv(paths["cohort"], index=False)
    base = ["f1", "f2"] + ([extra_feature] if extra_feature else [])
    arms = {arm: base + list(extra) for arm, extra in osf.ARMS.items()}
    manifest = {
        "status": "COMPLETE",
        "cohort": {"path": str(paths["cohort"]), "sha256": osf.file_sha256(paths["cohort"]), "label_keys_sha256": osf.keys_sha256(keys),
                   "eval_keys_sha256": osf.keys_sha256(cohort.loc[cohort["eval_key"]])},
        "horizons": {str(horizon): {
            "dataset": {"path": str(paths["data"]), "sha256": osf.file_sha256(paths["data"])},
            "history_ledger": {"path": str(paths["history"]), "sha256": osf.file_sha256(paths["history"])},
            "idp_ledger": {"path": str(paths["idp"]), "sha256": osf.file_sha256(paths["idp"])},
            "arms": {arm: {"features": f, "feature_sha256": osf.list_sha256(f)} for arm, f in arms.items()}}},
    }
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest))
    return path


def monthly_args(manifest: Path, out: Path, *extra):
    return ("--protocol", "monthly-origin", "--origin-manifest", str(manifest), "--horizon", "3", "--arm", "climate_safe_history_idp",
            "--out-dir", str(out), "--target-months", "2022-01", "2022-03", "--n-jobs", "2", *extra)


def test_global_annual_protocol_is_rejected_with_migration_message(tmp_path):
    dataset = tmp_path / "d.csv"
    pd.DataFrame({"area_id": [1], "year": [2020], "month": [1], "overall_phase": [1]}).to_csv(dataset, index=False)
    lookup = tmp_path / "lookup.csv"
    pd.DataFrame({"area_id": [1], "iso3": ["SOM"], "country": ["Somalia"]}).to_csv(lookup, index=False)
    result = run_cli("--dataset", str(dataset), "--country-lookup", str(lookup), "--dry-run")
    assert result.returncode == 1
    assert "Global annual holdouts are retired" in result.stderr


def test_monthly_origin_tiny_run_saves_origin_safe_batches_and_resumes(tmp_path):
    manifest = write_inputs(tmp_path)
    out = tmp_path / "run"
    result = run_cli(*monthly_args(manifest, out))
    assert result.returncode == 0, result.stderr
    meta = json.loads((out / "run_metadata.json").read_text())
    assert meta["status"] == "PARTIAL"
    for record in meta["batches"]:
        batch = out / "batches" / record["target_month"]
        target = pd.Period(record["target_month"], freq="M")
        assert record["label_cutoff_month"] == str(target - 3) and record["fit_max_label_month"] <= record["label_cutoff_month"]
        assert record["fit_min_age_months"] == 0
        fit_keys = pd.read_csv(batch / "fit_keys.csv.gz")
        assert (fit_keys["year"] * 12 + fit_keys["month"] - 1).max() == target.year * 12 + target.month - 4
        assert not ((fit_keys["area_id"] == 1) & (fit_keys["year"] == 2020) & (fit_keys["month"] == 6)).any()  # malformed shares
        preds = pd.read_csv(batch / "predictions.csv", float_precision="round_trip")
        assert len(preds) == 12 and preds["overall_phase_pred"].between(1, 5).all()
        assert sorted(p.name for p in batch.glob("model_*.ubj")) == [f"model_{t}.ubj" for t in sorted(osf.CUMULATIVE_TARGETS)]
    again = run_cli(*monthly_args(manifest, out))
    assert again.returncode == 0 and again.stdout.count("verified existing batch") == 2


def test_reintroduced_lag1_is_rejected_before_fitting(tmp_path):
    manifest = write_inputs(tmp_path, extra_feature="overall_phase_lag1")
    out = tmp_path / "run"
    result = run_cli(*monthly_args(manifest, out))
    assert result.returncode == 1 and "unsafe features" in result.stderr and "overall_phase_lag1" in result.stderr
    assert not (out / "batches").exists()


def test_history_after_origin_in_ledger_is_rejected_before_fitting(tmp_path):
    manifest = write_inputs(tmp_path, tamper_ledger=True)
    out = tmp_path / "run"
    result = run_cli(*monthly_args(manifest, out))
    assert result.returncode == 1 and "after min(O, T-1)" in result.stderr
    assert not (out / "batches").exists()


def test_changed_dataset_hash_is_rejected(tmp_path):
    manifest = write_inputs(tmp_path)
    data_path = Path(json.loads(manifest.read_text())["horizons"]["3"]["dataset"]["path"])
    df = pd.read_csv(data_path)
    df.loc[0, "f1"] = 99.0
    df.to_csv(data_path, index=False)
    result = run_cli(*monthly_args(manifest, tmp_path / "run"))
    assert result.returncode == 1 and "sha256 differs" in result.stderr


def test_full_plan_assembles_yearly_and_pooled_metrics(tmp_path):
    manifest = write_inputs(tmp_path, full_years=True)
    out = tmp_path / "run"
    args = [a for a in monthly_args(manifest, out)]
    cut = args.index("--target-months")
    args = args[:cut] + args[cut + 3:]  # full 48-month plan
    result = run_cli(*args)
    assert result.returncode == 0, result.stderr
    meta = json.loads((out / "run_metadata.json").read_text())
    assert meta["status"] == "COMPLETE" and len(meta["batches"]) == 48 and meta["prediction_rows"] == 3 * 48
    metrics = pd.read_csv(out / "metrics" / "metrics_overall.csv")
    assert metrics["test_year"].astype(str).tolist() == ["2022", "2023", "2024", "2025", "pooled"]
    assert metrics.loc[4, "n_samples"] == 144 and metrics["ordinal_mae"].notna().all()
    yearly = pd.concat([pd.read_csv(out / "predictions" / f"predictions_{y}.csv") for y in osf.TARGET_YEARS])
    assert len(yearly) == 144 and not yearly.duplicated(KEYS).any()
