from __future__ import annotations

import numpy as np
import pandas as pd

from ipcch import launch_comparison as lc


def _predictions():
    # 5 predicted areas A..E
    return pd.DataFrame({
        "area_id": ["A", "B", "C", "D", "E"],
        "overall_phase_pred": [1, 3, 3, 4, 2],
        "phase2_worse_pred": [0.1, 0.6, 0.5, 0.8, 0.4],
        "phase3_worse_pred": [0.0, 0.3, 0.25, 0.5, 0.1],
        "phase4_worse_pred": [0.0, 0.05, 0.0, 0.25, 0.0],
        "phase5_worse_pred": [0.0, 0.0, 0.0, 0.05, 0.0],
    })


def _april_actuals():
    # Actuals cover only A, B, C (partial); D, E have no April actual labels
    return pd.DataFrame({
        "area_id": ["A", "B", "C"],
        "year": [2026, 2026, 2026],
        "month": [4, 4, 4],
        "overall_phase": [1, 2, 4],
    })


def test_april_only_no_pooling_and_partial_coverage():
    actuals = pd.concat([
        _april_actuals(),
        pd.DataFrame({"area_id": ["A"], "year": [2026], "month": [3], "overall_phase": [5]}),  # March row must be ignored
    ], ignore_index=True)
    april = lc.load_april_actuals(actuals, "2026-04")
    assert set(april["area_id"]) == {"A", "B", "C"}  # March dropped (no pooling)
    assert (april["actual_month"] == "2026-04").all()
    assert int(april.loc[april.area_id == "A", "actual_overall_phase"].iloc[0]) == 1  # not the March 5


def test_coverage_aware_metrics_on_covered_subset_only():
    april = lc.load_april_actuals(_april_actuals(), "2026-04")
    result = lc.compare_predictions_to_actuals(_predictions(), april)
    cov = result.coverage
    assert cov["predicted_area_count"] == 5
    assert cov["april_actual_labeled_area_count"] == 3
    assert cov["covered_intersection_count"] == 3
    assert cov["actual_coverage_partial"] is True
    assert result.metrics["covered_area_count"] == 3
    assert result.metrics["descriptive_only"] is True
    # 3+ crisis metrics computed on covered subset
    assert "phase3_plus_f2" in result.metrics
    # unmatched predictions D,E recorded
    assert set(result.unmatched_prediction["area_id"]) == {"D", "E"}


def test_true_phase_confusion_rates():
    # actual C=4 predicted 3 -> true-4-as-3 rate = 1.0; actual B=2 predicted 3 -> true-2-as-3 = 1.0
    april = lc.load_april_actuals(_april_actuals(), "2026-04")
    result = lc.compare_predictions_to_actuals(_predictions(), april)
    assert result.metrics["true_phase4_predicted_as_3_rate"] == 1.0
    assert result.metrics["true_phase2_predicted_as_3_rate"] == 1.0


def test_unavailable_actuals_does_not_break_predictions():
    empty = pd.DataFrame({"area_id": [], "year": [], "month": [], "overall_phase": []})
    april = lc.load_april_actuals(empty, "2026-04")
    result = lc.compare_predictions_to_actuals(_predictions(), april)
    assert result.coverage["covered_intersection_count"] == 0
    assert result.metrics["covered_area_count"] == 0
