from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from ipcch.forecast_diagnostics import (
    DiagnosticConfig,
    compute_class_distribution,
    compute_confusion_matrices,
    compute_multiclass_metrics,
    main,
    run_diagnostics,
    validate_prediction_schema,
)


def tiny_prediction_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"area_id": "A", "country": "Somalia", "region": "East Africa", "year": 2025, "month": 1, "overall_phase": 1, "overall_phase_pred": 1, "phase2_worse": 0.10, "phase3_worse": 0.00, "phase4_worse": 0.00, "phase5_worse": 0.00, "phase2_pred": 0.18, "phase3_pred": 0.05, "phase4_pred": 0.01, "phase5_pred": 0.00},
            {"area_id": "B", "country": "Somalia", "region": "East Africa", "year": 2025, "month": 1, "overall_phase": 2, "overall_phase_pred": 3, "phase2_worse": 0.35, "phase3_worse": 0.18, "phase4_worse": 0.04, "phase5_worse": 0.00, "phase2_pred": 0.30, "phase3_pred": 0.22, "phase4_pred": 0.03, "phase5_pred": 0.00},
            {"area_id": "C", "country": "Somalia", "region": "East Africa", "year": 2025, "month": 1, "overall_phase": 3, "overall_phase_pred": 2, "phase2_worse": 0.55, "phase3_worse": 0.25, "phase4_worse": 0.08, "phase5_worse": 0.00, "phase2_pred": 0.40, "phase3_pred": 0.18, "phase4_pred": 0.04, "phase5_pred": 0.00},
            {"area_id": "D", "country": "Somalia", "region": "East Africa", "year": 2025, "month": 1, "overall_phase": 4, "overall_phase_pred": 3, "phase2_worse": 0.80, "phase3_worse": 0.60, "phase4_worse": 0.24, "phase5_worse": 0.05, "phase2_pred": 0.70, "phase3_pred": 0.50, "phase4_pred": 0.18, "phase5_pred": 0.02},
            {"area_id": "E", "country": "Somalia", "region": "East Africa", "year": 2025, "month": 1, "overall_phase": 3, "overall_phase_pred": 4, "phase2_worse": 0.65, "phase3_worse": 0.30, "phase4_worse": 0.15, "phase5_worse": 0.02, "phase2_pred": 0.60, "phase3_pred": 0.25, "phase4_pred": 0.21, "phase5_pred": 0.00},
            {"area_id": "F", "country": "Somalia", "region": "East Africa", "year": 2025, "month": 1, "overall_phase": 0, "overall_phase_pred": 3, "phase2_worse": 0.20, "phase3_worse": 0.10, "phase4_worse": 0.00, "phase5_worse": 0.00, "phase2_pred": 0.25, "phase3_pred": 0.20, "phase4_pred": 0.05, "phase5_pred": 0.00},
            {"area_id": "G", "country": "Somalia", "region": "East Africa", "year": 2025, "month": 1, "overall_phase": 2, "overall_phase_pred": None, "phase2_worse": 0.30, "phase3_worse": 0.05, "phase4_worse": 0.00, "phase5_worse": 0.00, "phase2_pred": 0.25, "phase3_pred": 0.10, "phase4_pred": 0.00, "phase5_pred": 0.00},
        ]
    )


def test_schema_validation_reports_invalid_labels_and_preserves_source_frame():
    df = tiny_prediction_frame()
    before = df.copy(deep=True)
    findings, summary, resolved = validate_prediction_schema(df, DiagnosticConfig(year=2025))

    assert summary["row_count"] == 7
    assert resolved == {2: "phase2_pred", 3: "phase3_pred", 4: "phase4_pred", 5: "phase5_pred"}
    assert set(findings["finding_type"]) >= {"label"}
    assert any(findings["value"].astype(str).str.contains("0"))
    pd.testing.assert_frame_equal(df, before)


def test_us1_classification_outputs_are_computed():
    df = tiny_prediction_frame()
    config = DiagnosticConfig(year=2025)

    distribution = compute_class_distribution(df, 2025, config)
    counts, row_normalized = compute_confusion_matrices(df, 2025, config)
    metrics = compute_multiclass_metrics(df, 2025, config)

    assert {"true", "predicted"}.issubset(set(distribution["label_source"]))
    assert int(counts.loc[(counts["true_label"] == 2) & (counts["predicted_label"] == 3), "count"].iloc[0]) == 1
    assert row_normalized["row_percentage"].notna().any()
    assert metrics["ordinal_mae"].iloc[0] > 0


def test_all_diagnostic_families_and_diagnostic_only_sweep_are_produced():
    df = tiny_prediction_frame()
    config = DiagnosticConfig(year=2025)
    results = run_diagnostics(df, config)

    assert not results["binary_crisis_metrics"].empty
    assert not results["cumulative_regression_metrics"].empty
    assert set(results["cumulative_regression_metrics"]["correlation_status"]) <= {"computed", "constant_input", "insufficient_data"}
    assert not results["calibration_bins"].empty
    assert (results["threshold_crossing_rates"]["threshold"] == 0.2).all()
    assert not results["diagnostic_threshold_sweep"].empty
    assert results["diagnostic_threshold_sweep"]["diagnostic_only"].all()
    assert "recommended" not in " ".join(results["diagnostic_threshold_sweep"].columns)
    assert set(results["error_slices"]["slice_name"]) == {"true2_pred3", "true3_pred2", "true4_pred3", "true3_pred4"}


def test_cli_writes_expected_artifacts_and_metrics_comparison(tmp_path: Path):
    predictions = tmp_path / "predictions_2025.csv"
    metrics = tmp_path / "metrics_overall.csv"
    output_dir = tmp_path / "results" / "diagnostics" / "experiment_0"
    report_dir = tmp_path / "reports" / "diagnostics" / "experiment_0"
    tiny_prediction_frame().to_csv(predictions, index=False)
    pd.DataFrame(
        [
            {"metric_name": "accuracy", "metric_value": 0.2},
            {"metric_name": "macro_f1", "metric_value": 0.99},
        ]
    ).to_csv(metrics, index=False)

    rc = main(["--predictions", str(predictions), "--metrics", str(metrics), "--year", "2025", "--output-dir", str(output_dir), "--report-dir", str(report_dir)])

    assert rc == 0
    result_root = output_dir / "canonical_regressor"
    report_root = report_dir / "canonical_regressor"
    expected = {
        "validation_findings.csv",
        "validation_summary.json",
        "metrics_comparison.csv",
        "class_distribution.csv",
        "confusion_matrix_counts.csv",
        "confusion_matrix_row_normalized.csv",
        "multiclass_metrics.csv",
        "binary_crisis_metrics.csv",
        "cumulative_regression_metrics.csv",
        "calibration_bins.csv",
        "threshold_crossing_rates.csv",
        "diagnostic_threshold_sweep.csv",
        "error_slices.csv",
        "run_summary.json",
    }
    assert expected.issubset({path.name for path in result_root.iterdir()})
    assert (report_root / "summary.md").exists()
    sweep = pd.read_csv(result_root / "diagnostic_threshold_sweep.csv")
    assert sweep["diagnostic_only"].all()
    comparison = pd.read_csv(result_root / "metrics_comparison.csv")
    assert set(comparison["status"]) >= {"matched", "mismatch", "not_available"}
    summary = json.loads((result_root / "run_summary.json").read_text())
    assert summary["threshold_sweep_policy"] == "post_hoc_diagnostic_only_no_selected_threshold"


def test_unavailable_metrics_file_records_not_available(tmp_path: Path):
    predictions = tmp_path / "predictions_2025.csv"
    output_dir = tmp_path / "results"
    report_dir = tmp_path / "reports"
    missing_metrics = tmp_path / "missing_metrics.csv"
    tiny_prediction_frame().to_csv(predictions, index=False)

    main(["--predictions", str(predictions), "--metrics", str(missing_metrics), "--year", "2025", "--output-dir", str(output_dir), "--report-dir", str(report_dir)])

    comparison = pd.read_csv(output_dir / "canonical_regressor" / "metrics_comparison.csv")
    assert (comparison["status"] == "not_available").all()
    findings = pd.read_csv(output_dir / "canonical_regressor" / "validation_findings.csv")
    assert "not_available" in set(findings["value"].astype(str))
