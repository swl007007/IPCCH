"""Synthetic end-to-end smoke run of the q3-first optimization CLI (tiny XGBoost fits)."""
from __future__ import annotations

import json
from importlib import util

import numpy as np
import pandas as pd
import pytest

from ipcch import paths
from ipcch.somalia_oracle import q3opt as qo

_v1_spec = util.spec_from_file_location("v1_smoke", str(paths.PROJECT_ROOT / "tests" / "smoke" / "test_somalia_oracle_pipeline.py"))
_v1_smoke = util.module_from_spec(_v1_spec)
_v1_spec.loader.exec_module(_v1_smoke)
_build_inputs = _v1_smoke._build_inputs


@pytest.fixture
def tiny_config(tmp_path):
    cfg = json.loads(qo.CONFIG_PATH.read_text())
    bundles = json.loads((paths.PROJECT_ROOT / cfg["bundle_config"]).read_text())
    for c in bundles["candidates"]:
        c["common"]["n_estimators"] = 3
    bpath = tmp_path / "bundles.json"
    bpath.write_text(json.dumps(bundles))
    cfg["bundle_config"] = str(bpath)
    cfg["bundle_config_sha256"] = qo.sha256_file(bpath)
    cpath = tmp_path / "q3cfg.json"
    cpath.write_text(json.dumps(cfg))
    return cpath


def test_q3opt_cli_end_to_end_synthetic(tmp_path, tiny_config):
    spec = util.spec_from_file_location("q3runner", str(paths.PROJECT_ROOT / "scripts" / "modeling" / "run_somalia_q3_optimization.py"))
    runner = util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    inputs = _build_inputs(tmp_path)
    out, report = tmp_path / "out", tmp_path / "report"
    argv = ["--out-dir", str(out), "--report-dir", str(report), "--workers", "1", "--skip-input-hash", "--no-v1-check", "--v1-dir", str(tmp_path / "no_v1"), "--config", str(tiny_config)]
    for name, path in inputs.items():
        argv += [f"--{name}-path", str(path)]
    assert runner.main(argv) == 0

    plan = pd.read_csv(out / "selection" / "scoring_plan.csv")
    assert (plan["scoring_month"] != "FINAL_MAPPING").sum() >= 4  # >=2 scoring months per fold
    scores = pd.read_csv(out / "selection" / "candidate_scores.csv")
    assert set(scores["method"]) == {"none", "shift", "isotonic"}
    assert set(scores["view"]) == {"A", "B", "D_direct", "D_residual"}
    oof = pd.read_csv(out / "selection" / "oof_fit_ledger.csv")
    ok = oof.loc[oof["status"] == "ok"]
    assert (ok["fit_max_target_ord"] <= ok["fit_label_cutoff_ord"]).all() and (ok["fit_label_cutoff_ord"] < ok["v"]).all()
    assert (ok["fit_label_cutoff_ord"] <= ok["v"] - ok["horizon"]).all()

    sel = pd.read_csv(out / "selection" / "selected_recipes.csv")
    for year, g in sel.groupby("test_year"):
        s = scores.loc[(scores["test_year"] == year) & (scores["status"] == "ok")]
        for view in ("A", "B", "D_direct", "D_residual"):
            row = g.loc[g["view"] == view].iloc[0]
            assert row["rmse"] == pytest.approx(s.loc[s["view"] == view, "rmse"].min())  # strict minimum RMSE
        dsel = g.loc[g["view"] == "D_selected"].iloc[0]
        assert dsel["rmse"] == pytest.approx(s.loc[s["view"].isin(["D_direct", "D_residual"]), "rmse"].min())

    preds = pd.read_csv(out / "predictions" / "final_predictions.csv.gz")
    assert set(preds["view"]) == {"A", "B", "C", "D_direct", "D_residual", "D_selected"}
    ok_pred = preds.loc[preds["calibration_status"] == "ok"]
    assert ok_pred["q3_final"].between(0, 1).all()
    h0 = preds.loc[preds["horizon"] == 0].pivot_table(index=["job_id", "area_id", "target_ord"], columns="view", values="q3_raw")
    np.testing.assert_array_equal(h0["B"].to_numpy(), h0["C"].to_numpy())
    status = pd.read_csv(out / "fits" / "final_status.csv")
    long = status.loc[status["horizon"] > 0]
    assert (long["recipe_source_view"].isin(["A", "B", "D_direct", "D_residual"])).all()
    assert (long.loc[long["view"] == "C", "recipe_source_view"] == "B").all()
    fits = pd.read_csv(out / "fits" / "final_fit_ledger.csv.gz")
    assert (fits.merge(status[["job_id", "view", "receiving_origin"]], on=["job_id", "view"]).pipe(lambda d: d["target_ord"] <= d["receiving_origin"].map(lambda s: int(s[:4]) * 12 + int(s[5:]) - 1))).all()

    metrics = pd.read_csv(out / "metrics" / "metrics.csv")
    assert {"primary", "share_history_subset"} <= set(metrics["cohort"])
    assert {"share_persistence", "always_crisis", "D_selected"} <= set(metrics["view"])
    contrasts = pd.read_csv(out / "metrics" / "contrasts.csv")
    assert {"D_residual-D_direct", "D_selected-share_persistence"} <= set(contrasts["contrast"])
    assert (report / "summary.md").exists()
