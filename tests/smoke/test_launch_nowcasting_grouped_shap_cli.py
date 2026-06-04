from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace


REPO_ROOT = Path(__file__).resolve().parents[2]
CLI = REPO_ROOT / "scripts" / "modeling" / "run_launch_nowcasting_2026_04.py"
if str(REPO_ROOT / "scripts" / "modeling") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "scripts" / "modeling"))
import run_launch_nowcasting_2026_04 as launch_cli  # noqa: E402


def run_cli(*args):
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def test_help_runs_for_nowcasting_grouped_shap_cli():
    result = run_cli("--help")
    assert result.returncode == 0
    assert "April 2026 global nowcasting launch" in result.stdout


def test_help_includes_grouped_shap_options():
    result = run_cli("--help")
    assert result.returncode == 0
    for option in (
        "--compute-grouped-shap",
        "--grouped-shap-crosswalk-path",
        "--grouped-shap-crosswalk-key",
        "--grouped-shap-crosswalk-feature-column",
        "--grouped-shap-crosswalk-category-column",
    ):
        assert option in result.stdout
    assert "C:\\Users" not in result.stdout
    assert "IFPRI Dropbox" not in result.stdout


def test_grouped_shap_disabled_does_not_require_crosswalk_resolution():
    result = run_cli("--validate-only")
    assert result.returncode != 0
    assert "deep_features_2026_target_corrected_dataset" in result.stderr
    assert "six_category_feature_crosswalk" not in result.stderr
    assert "Grouped SHAP crosswalk" not in result.stderr


def test_grouped_shap_rejects_mode2_supplied_models_before_crosswalk_resolution(tmp_path):
    missing_models = tmp_path / "models"
    result = run_cli(
        "--compute-grouped-shap",
        "--skip-training",
        "--model-artifact-dir",
        str(missing_models),
        "--grouped-shap-crosswalk-key",
        "not_a_real_key",
    )
    assert result.returncode == 2
    assert "grouped SHAP currently supports train-and-predict" in result.stderr
    assert "not_a_real_key" not in result.stderr


def test_grouped_shap_rejects_mode3_supplied_predictions_before_crosswalk_resolution(tmp_path):
    predictions = tmp_path / "predictions.csv"
    predictions.write_text("area_id,phase2_worse_pred,phase3_worse_pred,phase4_worse_pred,phase5_worse_pred\nA,0,0,0,0\n", encoding="utf-8")
    result = run_cli(
        "--compute-grouped-shap",
        "--skip-prediction",
        "--predictions",
        str(predictions),
        "--grouped-shap-crosswalk-key",
        "not_a_real_key",
    )
    assert result.returncode == 2
    assert "grouped SHAP requires a fitted phase3_worse model" in result.stderr
    assert "not_a_real_key" not in result.stderr


def test_grouped_shap_console_output_reports_counts_and_paths(monkeypatch, capsys, tmp_path):
    config = launch_cli.ln.LaunchConfig(comprehensive_source=Path("dummy.csv"), out_root=launch_cli.ln.paths.RESULTS_DIR / "launch" / "_pytest_console", report_root=launch_cli.ln.paths.REPORTS_DIR / "launch" / "_pytest_console")
    layout = launch_cli.ln.resolve_output_layout(config)
    args = SimpleNamespace(actual_source=None, actual_crisis_flag=None, make_map=False, spatial_path=None, no_basemap=True, overwrite=True)
    grouped = {
        "matched_feature_count": 2,
        "weather_forecast_feature_count": 1,
        "unmatched_feature_count": 1,
        "coverage": {"unmatched_abs_shap_share": 0.25},
        "metadata_path": str(layout.grouped_shap_metadata_json),
    }
    monkeypatch.setattr(launch_cli.lc, "unavailable_actuals_comparison_summary", lambda pred, target: {})
    monkeypatch.setattr(launch_cli.ln, "write_json", lambda *a, **k: None)
    monkeypatch.setattr(launch_cli.ln, "write_launch_reports", lambda *a, **k: None)
    monkeypatch.setattr(launch_cli.ln, "prediction_distribution_summary", lambda pred: None)
    monkeypatch.setattr(launch_cli.ln, "predicted_phase_distribution", lambda pred: None)
    launch_cli._post_prediction(
        config,
        layout,
        args,
        launch_cli.pd.DataFrame({"area_id": ["A"], "overall_phase_pred": [1]}),
        {"training_rows": 1},
        {"launch_month_area_count": 1},
        ["a"],
        {},
        [],
        {},
        grouped,
    )
    captured = capsys.readouterr().out
    assert "[grouped-shap]" in captured
    assert "matched=2" in captured
    assert "weather_forecast=1" in captured
    assert "unmatched=1" in captured
    assert str(layout.grouped_shap_metadata_json) in captured
