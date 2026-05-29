from __future__ import annotations

import json
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

import pandas as pd
import pytest

pytest.importorskip("xgboost")

REPO_ROOT = Path(__file__).resolve().parents[2]
CLI = REPO_ROOT / "scripts" / "modeling" / "run_launch_nowcasting_2026_04.py"


def _run(args):
    return subprocess.run([sys.executable, str(CLI), *args], capture_output=True, text=True, cwd=str(REPO_ROOT))


@pytest.fixture
def repo_dirs():
    token = uuid.uuid4().hex[:8]
    out = REPO_ROOT / "results" / "launch" / f"_pytest_{token}"
    rep = REPO_ROOT / "reports" / "launch" / f"_pytest_{token}"
    yield out, rep
    for d in (out, rep):
        shutil.rmtree(d, ignore_errors=True)


def test_mode1_then_mode2_then_mode3(comprehensive_csv, repo_dirs, tmp_path):
    out, rep = repo_dirs

    # --- Mode 1: train-and-predict (tiny synthetic data; explicitly approved) ---
    res1 = _run([
        "--comprehensive-source", str(comprehensive_csv),
        "--out-root", str(out), "--report-root", str(rep),
        "--approve-training",
    ])
    assert res1.returncode == 0, res1.stderr
    preds_csv = out / "predictions_2026_04_all_area_id.csv"
    preds = pd.read_csv(preds_csv)
    # All eligible April areas predicted (SC-001)
    assert set(preds["area_id"]) == {"A", "B", "C", "D", "E"}
    # Required columns incl. provenance (FR-030, SC-003)
    for col in ["overall_phase_pred", "phase2_worse_pred", "phase5_worse_pred", "model_workflow",
                "scale", "threshold", "training_cutoff", "comprehensive_source", "run_id", "launch_month"]:
        assert col in preds.columns
    # overall_phase_pred in 1..5, finite-derived (SC-002)
    assert preds["overall_phase_pred"].dropna().astype(int).between(1, 5).all()

    run_summary = json.loads((out / "run_summary.json").read_text())
    assert run_summary["scale"] == "global"
    assert run_summary["threshold"] == 0.2
    assert run_summary["execution_mode"] == "train_and_predict"
    assert run_summary["predicted_area_count"] == 5
    assert "forecasting_hyperparameters" in run_summary["hyperparameters"]["hyperparameters"]
    assert (out / "model_artifacts" / "phase2_worse_model.json").exists()
    assert (out / "feature_schema_report.csv").exists()

    # launch report content (SC-010)
    report = (rep / "launch_summary.md").read_text()
    assert "production launch" in report.lower()
    assert "may not be" in report.lower() and "0m model-ready" in report.lower()

    # --- Mode 2: predict-with-supplied-models (no training) ---
    out2 = out.parent / (out.name + "_m2")
    rep2 = rep.parent / (rep.name + "_m2")
    try:
        res2 = _run([
            "--comprehensive-source", str(comprehensive_csv),
            "--out-root", str(out2), "--report-root", str(rep2),
            "--skip-training", "--model-artifact-dir", str(out / "model_artifacts"),
        ])
        assert res2.returncode == 0, res2.stderr
        preds2 = pd.read_csv(out2 / "predictions_2026_04_all_area_id.csv")
        assert set(preds2["area_id"]) == {"A", "B", "C", "D", "E"}
        assert json.loads((out2 / "run_summary.json").read_text())["execution_mode"] == "predict_with_supplied_models"
    finally:
        shutil.rmtree(out2, ignore_errors=True)
        shutil.rmtree(rep2, ignore_errors=True)

    # --- Mode 3: report-from-supplied-predictions + partial actuals ---
    out3 = out.parent / (out.name + "_m3")
    rep3 = rep.parent / (rep.name + "_m3")
    actuals = tmp_path / "april_actuals.csv"
    pd.DataFrame({"area_id": ["A", "B", "C"], "year": [2026] * 3, "month": [4] * 3,
                  "overall_phase": [1, 2, 4]}).to_csv(actuals, index=False)
    try:
        res3 = _run([
            "--out-root", str(out3), "--report-root", str(rep3),
            "--skip-prediction", "--predictions", str(preds_csv),
            "--actual-source", str(actuals), "--no-map",
        ])
        assert res3.returncode == 0, res3.stderr
        cov = pd.read_csv(out3 / "actual_comparison" / "actual_coverage_summary_2026_04.csv")
        assert int(cov["covered_intersection_count"].iloc[0]) == 3
        assert bool(cov["actual_coverage_partial"].iloc[0]) is True
    finally:
        shutil.rmtree(out3, ignore_errors=True)
        shutil.rmtree(rep3, ignore_errors=True)
