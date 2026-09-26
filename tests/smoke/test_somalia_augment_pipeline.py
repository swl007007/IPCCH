"""Synthetic end-to-end smoke run of the validity-augmentation CLI (tiny XGBoost fits)."""
from __future__ import annotations

import json
from importlib import util

import numpy as np
import pandas as pd
import pytest

from ipcch import paths
from ipcch.somalia_oracle import PERCENT_COLUMNS
from ipcch.somalia_oracle import q3opt as qo

_v1_spec = util.spec_from_file_location("v1_smoke", str(paths.PROJECT_ROOT / "tests" / "smoke" / "test_somalia_oracle_pipeline.py"))
_v1 = util.module_from_spec(_v1_spec)
_v1_spec.loader.exec_module(_v1)


@pytest.fixture
def configs(tmp_path):
    q = json.loads(qo.CONFIG_PATH.read_text())
    bundles = json.loads((paths.PROJECT_ROOT / q["bundle_config"]).read_text())
    for c in bundles["candidates"]:
        c["common"]["n_estimators"] = 3
    bpath = tmp_path / "bundles.json"
    bpath.write_text(json.dumps(bundles))
    q["bundle_config"], q["bundle_config_sha256"] = str(bpath), qo.sha256_file(bpath)
    qpath = tmp_path / "q3.json"
    qpath.write_text(json.dumps(q))
    # validity snapshot: Jul-Sep 2022, Jan-Mar 2023, Jan-Mar 2024 windows starting at labelled months
    feats = [{"type": "Feature", "geometry": None, "properties": {"country": "SO", "condition": "A", "ipc_period": "C", "anl_id": a, "from": f, "to": t}}
             for a, f, t in [("11", "Jul 2022", "Sep 2022"), ("12", "Oct 2022", "Oct 2022"), ("13", "Jan 2023", "Mar 2023"), ("14", "Jan 2024", "Mar 2024"), ("15", "Jul 2024", "Aug 2024")]]
    snap = tmp_path / "areas.geojson"
    snap.write_text(json.dumps({"type": "FeatureCollection", "features": feats}))
    a = json.loads((paths.CONFIG_DIR / "somalia_validity_augmentation.json").read_text())
    a.update(validity_snapshot=str(snap), validity_snapshot_sha256=qo.sha256_file(snap), q3_config=str(qpath), q3_config_sha256=qo.sha256_file(qpath), excluded_raw_months={})
    apath = tmp_path / "aug.json"
    apath.write_text(json.dumps(a))
    return apath, qpath


def _deep(inputs, tmp_path):
    raw = pd.read_csv(inputs["raw"])
    raw = raw.rename(columns={"admin_code": "area_id"})
    fs3 = pd.read_csv(inputs["fs3"])
    feat = [c for c in fs3.columns if c not in ("area_id", "year", "month", "overall_phase", *PERCENT_COLUMNS, "estimated_population", "overall_phase_lag1")]
    deep = raw[["area_id", "year", "month", "overall_phase", *PERCENT_COLUMNS]].merge(fs3[["area_id", "year", "month", *feat]], on=["area_id", "year", "month"], how="left")
    rng = np.random.default_rng(5)
    for c in feat:
        miss = deep[c].isna()
        deep.loc[miss, c] = rng.normal(size=int(miss.sum()))
    deep = deep.loc[deep["area_id"] != 9]
    path = tmp_path / "deep.csv"
    deep.to_csv(path, index=False)
    return path


def test_augmentation_cli_end_to_end_synthetic(tmp_path, configs, monkeypatch):
    apath, qpath = configs
    inputs = _v1._build_inputs(tmp_path)
    raw = pd.read_csv(inputs["raw"])
    raw["estimated_population"] = 1000.0
    raw.to_csv(inputs["raw"], index=False)
    deep_path = _deep(inputs, tmp_path)
    from ipcch.somalia_oracle import monthly_features as mf

    for name in ("fs0", "fs1", "fs2"):  # synthetic scope files mirror the H12 columns used below
        f = pd.read_csv(inputs[name])
        f3 = pd.read_csv(inputs["fs3"])
        f.merge(f3[["area_id", "year", "month", "feat__l12"]], on=["area_id", "year", "month"], how="left").to_csv(inputs[name], index=False)
    orig_scope = mf.scope_frame
    monkeypatch.setattr(mf, "scope_frame", lambda deep, h: orig_scope(deep, 12))  # synthetic panel has no upstream scope columns
    monkeypatch.setattr(mf, "parity_check", lambda rec, ref, skip: pd.DataFrame({"column": ["x"], "status": ["ok"], "n_mismatch": [0]}))
    spec = util.spec_from_file_location("augrunner", str(paths.PROJECT_ROOT / "scripts" / "modeling" / "run_somalia_validity_augmentation.py"))
    runner = util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    out, report = tmp_path / "out", tmp_path / "report"
    argv = ["--out-dir", str(out), "--report-dir", str(report), "--workers", "1", "--skip-input-hash", "--config", str(apath), "--q3-config", str(qpath), "--deep-path", str(deep_path)]
    for n, p in inputs.items():
        argv += [f"--{n}-path", str(p)]
    assert runner.main(argv) == 0
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["mode"] == "full" and manifest["notes"]["n_copies"] > 0

    ledger = pd.read_csv(out / "ledgers" / "label_ledger.csv.gz")
    cp = ledger.loc[ledger["is_copy"]]
    assert (cp["target_ord"] // 12 < 2025).all() and (cp["source_available_ord"] == cp["original_month_ord"]).all()
    plan = pd.read_csv(out / "selection" / "rounds_plan.csv")
    assert set(plan["branch"]) == {"original", "augmented"} and (plan.loc[plan["branch"] == "original", "n_copy_rows"] == 0).all()
    oof = pd.read_csv(out / "selection" / "oof_fit_ledger.csv")
    ok = oof.loc[oof["status"] == "ok"]
    assert (ok["fit_max_target_ord"] <= ok["fit_label_cutoff"]).all() and (ok["fit_label_cutoff"] < ok["round"]).all()
    scores = pd.read_csv(out / "selection" / "candidate_scores.csv")
    assert scores.groupby("branch").size().nunique() == 1  # equal search budgets
    fits = pd.read_csv(out / "fits" / "final_fit_ledger.csv.gz")
    assert not fits.loc[fits["label_branch"] == "original", "is_copy"].any()
    preds = pd.read_csv(out / "predictions" / "final_predictions.csv.gz")
    assert set(preds["branch"]) <= {"direct", "residual", "fallback_direct"}  # per-row prediction branch is preserved
    k = preds.groupby(["job_id", "view", "label_branch"])["target_ord"].count().unstack("label_branch")
    assert (k["original"] == k["augmented"]).all()  # identical outer keys
    metrics = pd.read_csv(out / "metrics" / "metrics.csv")
    assert {"share_persistence", "phase_persistence", "always_crisis"} <= set(metrics["view"])
    contrasts = pd.read_csv(out / "metrics" / "contrasts.csv")
    assert contrasts["contrast"].str.startswith("augmented_D_").any()
    assert (report / "summary.md").exists()
