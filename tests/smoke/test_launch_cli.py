from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CLI = REPO_ROOT / "scripts" / "modeling" / "run_launch_nowcasting_2026_04.py"


def _run(args, env=None):
    return subprocess.run([sys.executable, str(CLI), *args], capture_output=True, text=True, cwd=str(REPO_ROOT), env=env)


def test_help_runs_without_computation():
    res = _run(["--help"])
    assert res.returncode == 0
    assert "comprehensive-source" in res.stdout


def test_missing_key_clear_message(monkeypatch):
    # No --comprehensive-source and key not configured -> clear actionable error (not KeyError)
    res = _run(["--validate-only"])
    assert res.returncode == 2
    assert "deep_features_2026_target_corrected_dataset" in res.stderr
    assert "configs/paths.local.json" in res.stderr
    assert "KeyError" not in res.stderr


@pytest.fixture
def repo_temp_dirs():
    import shutil
    import uuid
    token = uuid.uuid4().hex[:8]
    out = REPO_ROOT / "results" / "launch" / f"_pytest_{token}"
    rep = REPO_ROOT / "reports" / "launch" / f"_pytest_{token}"
    yield out, rep
    for d in (out, rep):
        shutil.rmtree(d, ignore_errors=True)


def test_validate_only_with_explicit_source(comprehensive_csv, repo_temp_dirs):
    out, rep = repo_temp_dirs
    res = _run([
        "--comprehensive-source", str(comprehensive_csv),
        "--out-root", str(out), "--report-root", str(rep),
        "--validate-only",
    ])
    assert res.returncode == 0, res.stderr
    assert (out / "input_validation_summary.json").exists()
    assert (out / "feature_schema_report.csv").exists()
    # validate-only must NOT write production outputs
    assert not (out / "predictions_2026_04_all_area_id.csv").exists()


def test_validate_only_does_not_overwrite_existing_production_outputs(comprehensive_csv, repo_temp_dirs):
    out, rep = repo_temp_dirs
    out.mkdir(parents=True, exist_ok=True)
    prod = out / "predictions_2026_04_all_area_id.csv"
    prod.write_text("sentinel", encoding="utf-8")
    res = _run([
        "--comprehensive-source", str(comprehensive_csv),
        "--out-root", str(out), "--report-root", str(rep),
        "--validate-only",
    ])
    assert res.returncode == 0, res.stderr
    assert prod.read_text(encoding="utf-8") == "sentinel"  # untouched


def test_skip_training_without_artifact_dir_fails(comprehensive_csv):
    res = _run(["--comprehensive-source", str(comprehensive_csv), "--skip-training"])
    assert res.returncode == 2
    assert "model-artifact-dir" in res.stderr


def test_skip_prediction_without_predictions_fails():
    res = _run(["--skip-prediction"])
    assert res.returncode == 2
    assert "--predictions" in res.stderr


def test_threshold_locked():
    res = _run(["--comprehensive-source", "x.csv", "--threshold", "0.3"])
    assert res.returncode == 2
    assert "th=0.2" in res.stderr
