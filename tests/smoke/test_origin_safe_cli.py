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


def origin_args(manifest: Path, out: Path, *extra):
    return ("--protocol", "origin-safe", "--origin-manifest", str(manifest), "--horizon", "3", "--arm", "climate_safe_history_idp",
            "--out-dir", str(out), "--block-years", "2022", "--n-jobs", "2", *extra)


def test_global_annual_protocol_is_rejected_with_migration_message(tmp_path):
    dataset = tmp_path / "d.csv"
    pd.DataFrame({"area_id": [1], "year": [2020], "month": [1], "overall_phase": [1]}).to_csv(dataset, index=False)
    lookup = tmp_path / "lookup.csv"
    pd.DataFrame({"area_id": [1], "iso3": ["SOM"], "country": ["Somalia"]}).to_csv(lookup, index=False)
    result = run_cli("--dataset", str(dataset), "--country-lookup", str(lookup), "--dry-run")
    assert result.returncode == 1
    assert "Global annual holdouts are retired" in result.stderr


def test_origin_safe_tiny_run_saves_origin_safe_batches_and_resumes(tmp_path):
    manifest = write_inputs(tmp_path)
    out = tmp_path / "run"
    result = run_cli(*origin_args(manifest, out))
    assert result.returncode == 0, result.stderr
    meta = json.loads((out / "run_metadata.json").read_text())
    assert meta["status"] == "PARTIAL"
    (record,) = meta["batches"]
    batch = out / "batches" / "2022"
    # strictest cutoff of the year: Jan 2022 - 3 = Oct 2021, used for every scored month of 2022
    assert record["fit_origin_month"] == "2021-10" and record["fit_label_cutoff_month"] == "2021-10"
    assert record["fit_max_label_month"] == "2021-10" and record["fit_min_age_months"] == 0
    fit_keys = pd.read_csv(batch / "fit_keys.csv.gz")
    assert (fit_keys["year"] * 12 + fit_keys["month"] - 1).max() == 2021 * 12 + 9
    assert not ((fit_keys["area_id"] == 1) & (fit_keys["year"] == 2020) & (fit_keys["month"] == 6)).any()  # malformed shares
    preds = pd.read_csv(batch / "predictions.csv", float_precision="round_trip")
    assert len(preds) == 36 and preds["overall_phase_pred"].between(1, 5).all()
    assert (preds["fit_label_cutoff_month"] == "2021-10").all()
    assert preds["row_origin_month"].tolist() == [str(pd.Period(f"{y}-{m:02d}", freq="M") - 3) for y, m in zip(preds["year"], preds["month"])]
    assert sorted(p.name for p in batch.glob("model_*.ubj")) == [f"model_{t}.ubj" for t in sorted(osf.CUMULATIVE_TARGETS)]
    again = run_cli(*origin_args(manifest, out))
    assert again.returncode == 0 and again.stdout.count("verified existing batch") == 1


def test_reintroduced_lag1_is_rejected_before_fitting(tmp_path):
    manifest = write_inputs(tmp_path, extra_feature="overall_phase_lag1")
    out = tmp_path / "run"
    result = run_cli(*origin_args(manifest, out))
    assert result.returncode == 1 and "unsafe features" in result.stderr and "overall_phase_lag1" in result.stderr
    assert not (out / "batches").exists()


def test_history_after_origin_in_ledger_is_rejected_before_fitting(tmp_path):
    manifest = write_inputs(tmp_path, tamper_ledger=True)
    out = tmp_path / "run"
    result = run_cli(*origin_args(manifest, out))
    assert result.returncode == 1 and "after min(O, T-1)" in result.stderr
    assert not (out / "batches").exists()


def test_changed_dataset_hash_is_rejected(tmp_path):
    manifest = write_inputs(tmp_path)
    data_path = Path(json.loads(manifest.read_text())["horizons"]["3"]["dataset"]["path"])
    df = pd.read_csv(data_path)
    df.loc[0, "f1"] = 99.0
    df.to_csv(data_path, index=False)
    result = run_cli(*origin_args(manifest, tmp_path / "run"))
    assert result.returncode == 1 and "sha256 differs" in result.stderr


def test_full_plan_assembles_yearly_and_pooled_metrics(tmp_path):
    manifest = write_inputs(tmp_path, full_years=True)
    out = tmp_path / "run"
    args = [a for a in origin_args(manifest, out)]
    cut = args.index("--block-years")
    args = args[:cut] + args[cut + 2:]  # full plan: every test year
    result = run_cli(*args)
    assert result.returncode == 0, result.stderr
    meta = json.loads((out / "run_metadata.json").read_text())
    assert meta["status"] == "COMPLETE" and len(meta["batches"]) == 4 and meta["prediction_rows"] == 3 * 48
    assert [b["fit_label_cutoff_month"] for b in meta["batches"]] == ["2021-10", "2022-10", "2023-10", "2024-10"]
    metrics = pd.read_csv(out / "metrics" / "metrics_overall.csv")
    assert metrics["test_year"].astype(str).tolist() == ["2022", "2023", "2024", "2025", "pooled"]
    assert metrics.loc[4, "n_samples"] == 144 and metrics["ordinal_mae"].notna().all()
    yearly = pd.concat([pd.read_csv(out / "predictions" / f"predictions_{y}.csv") for y in osf.TARGET_YEARS])
    assert len(yearly) == 144 and not yearly.duplicated(KEYS).any()


def test_dry_run_validates_without_fitting_or_writing(tmp_path):
    manifest = write_inputs(tmp_path)
    out = tmp_path / "run"
    result = run_cli(*origin_args(manifest, out, "--dry-run"))
    assert result.returncode == 0, result.stderr
    assert "no fitting, nothing written" in result.stdout and "2021-10" in result.stdout
    assert not out.exists()


def test_resume_rejects_batch_record_missing_a_required_artifact(tmp_path):
    manifest = write_inputs(tmp_path)
    out = tmp_path / "run"
    assert run_cli(*origin_args(manifest, out)).returncode == 0
    record_path = out / "batches" / "2022" / "batch_record.json"
    record = json.loads(record_path.read_text())
    del record["artifacts"]["model_phase2_worse.ubj"]
    (out / "batches" / "2022" / "model_phase2_worse.ubj").unlink()
    record_path.write_text(json.dumps(record))
    again = run_cli(*origin_args(manifest, out))
    assert again.returncode == 1 and "lacks required artifacts" in again.stderr and "model_phase2_worse.ubj" in again.stderr


# --------------------------------------------------------------------------- origin_safe_weather_oracle_v1 contract


def write_oracle_inputs(tmp_path: Path, tamper_b6: bool = False) -> Path:
    from ipcch import climate2015_features as cf
    from ipcch import weather_oracle as wo

    parent_path = write_inputs(tmp_path)
    parent = json.loads(parent_path.read_text())
    entry = parent["horizons"]["3"]
    data = pd.read_csv(entry["dataset"]["path"], float_precision="round_trip")
    history_ledger = pd.read_csv(entry["history_ledger"]["path"], float_precision="round_trip")
    rng = np.random.default_rng(1)
    grid = cf.Grid(np.arange(1, 13), 2019 * 12, 60, {v: rng.normal(size=(12, 60)) for v in wo.ORACLE_VARIABLES})
    origin = osf.month_ord(data["year"], data["month"]) - 3
    for v in wo.ORACLE_VARIABLES:  # parent R column: trailing mean of O-2..O
        data[wo.parent_rolling_column(v, 3)] = np.mean([wo.calendar_lookup(grid, data["area_id"], origin - j)[v] for j in range(3)], axis=0)
    block, ledger = wo.build_oracle_block(grid, data[KEYS], 3, {v: data[wo.parent_rolling_column(v, 3)].to_numpy() for v in wo.ORACLE_VARIABLES},
                                          data[wo.HISTORY_GATE].to_numpy(), history_ledger["history_1_source_ord"].to_numpy())
    appended = pd.concat([data, block], axis=1)
    if tamper_b6:
        appended.loc[0, wo.halfmean_name(wo.ORACLE_VARIABLES[0], 3)] += 1.0
    data_path, ledger_path = tmp_path / "oracle_data.csv", tmp_path / "oracle_ledger.csv"
    appended.to_csv(data_path, index=False)
    ledger.to_csv(ledger_path, index=False)
    parent_features = entry["arms"][wo.PARENT_ARM]["features"]
    arms = {arm: wo.arm_features(parent_features, arm, 3) for arm in wo.ORACLE_ARMS}
    manifest = {
        "version": wo.ORACLE_VERSION, "status": "COMPLETE", "cohort": parent["cohort"],
        "parent_manifest": {"path": str(parent_path), "sha256": osf.file_sha256(parent_path)},
        "horizons": {"3": {
            "dataset": {"path": str(data_path), "sha256": osf.file_sha256(data_path)},
            "history_ledger": entry["history_ledger"], "idp_ledger": entry["idp_ledger"],
            "oracle_ledger": {"path": str(ledger_path), "sha256": osf.file_sha256(ledger_path)},
            "parent_feature_sha256": osf.list_sha256(parent_features),
            "arms": {arm: {"features": f, "feature_sha256": osf.list_sha256(f)} for arm, f in arms.items()}}},
    }
    path = tmp_path / "oracle_manifest.json"
    path.write_text(json.dumps(manifest))
    return path


def oracle_args(manifest: Path, out: Path, arm: str = "climate_safe_history_idp_oracle_b6", horizon: str = "3", *extra):
    return ("--protocol", "origin-safe", "--origin-manifest", str(manifest), "--horizon", horizon, "--arm", arm,
            "--out-dir", str(out), "--block-years", "2022", "--n-jobs", "2", *extra)


def test_oracle_dry_run_validates_exact_schema_and_ledger(tmp_path):
    manifest = write_oracle_inputs(tmp_path)
    result = run_cli(*oracle_args(manifest, tmp_path / "run", "climate_safe_history_idp_oracle_b6", "3", "--dry-run"))
    assert result.returncode == 0, result.stderr
    assert "no fitting, nothing written" in result.stdout and "21 features" in result.stdout  # 9 parent (2 + 5 history + 2 IDP), 6 raw, 6 B6
    assert not (tmp_path / "run").exists()


def test_oracle_version_and_arm_must_match(tmp_path):
    oracle = write_oracle_inputs(tmp_path)
    legacy_arm = run_cli(*oracle_args(oracle, tmp_path / "a", "climate_safe_history_idp"))
    assert legacy_arm.returncode == 1 and "not allowed with manifest version" in legacy_arm.stderr
    legacy_manifest = tmp_path / "manifest.json"  # the parent written by write_inputs
    oracle_arm = run_cli(*oracle_args(legacy_manifest, tmp_path / "b", "climate_safe_history_idp_oracle"))
    assert oracle_arm.returncode == 1 and "not allowed with manifest version" in oracle_arm.stderr
    h0 = run_cli(*oracle_args(oracle, tmp_path / "c", "climate_safe_history_idp_oracle", "0"))
    assert h0.returncode == 1 and "shared reference" in h0.stderr
    old_namespace = run_cli(*oracle_args(oracle, tmp_path / "origin_safe_climate_idp_v1" / "runs" / "x"))
    assert old_namespace.returncode == 1 and "must not write into" in old_namespace.stderr


def test_oracle_b6_column_not_matching_its_dependencies_is_rejected(tmp_path):
    manifest = write_oracle_inputs(tmp_path, tamper_b6=True)
    result = run_cli(*oracle_args(manifest, tmp_path / "run"))
    assert result.returncode == 1 and "declared function of its dependencies" in result.stderr
    assert not (tmp_path / "run").exists()


def test_oracle_tiny_fit_records_oracle_fingerprint_and_exact_feature_order(tmp_path):
    from ipcch import weather_oracle as wo

    manifest = write_oracle_inputs(tmp_path)
    out = tmp_path / "run"
    result = run_cli(*oracle_args(manifest, out, "climate_safe_history_idp_oracle"))
    assert result.returncode == 0, result.stderr
    meta = json.loads((out / "run_metadata.json").read_text())
    assert meta["fingerprint_payload"]["oracle"]["version"] == wo.ORACLE_VERSION
    assert meta["features"][-6:] == wo.raw_features(3) and len(meta["features"]) == 15
    import xgboost as xgb

    booster = xgb.Booster()
    booster.load_model(str(out / "batches" / "2022" / "model_phase3_worse.ubj"))
    assert list(booster.feature_names) == meta["features"]
