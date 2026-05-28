from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from shapely.geometry import box

from ipcch.alert_risk_maps import (
    AlertRiskMapError,
    _latam_mask,
    build_output_plan,
    compute_top_risk_categories,
    discover_prediction_file,
    join_predictions_to_spatial,
    load_prediction_dataset,
    load_spatial_boundaries,
    plot_actual_vs_predicted,
    validate_output_conflicts,
)

geopandas = pytest.importorskip("geopandas")


def write_prediction(path: Path, rows: list[dict]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def prediction_row(area_id: str, year: int = 2025, month: int = 1, **overrides):
    row = {
        "area_id": area_id,
        "year": year,
        "month": month,
        "overall_phase": 2,
        "overall_phase_pred": 4,
        "phase3_worse": 0.1,
        "phase3_pred": 0.2,
    }
    row.update(overrides)
    return row


def test_latest_record_filtering_and_alert_derivation(tmp_path):
    csv_path = write_prediction(
        tmp_path / "0m_global" / "predictions" / "predictions_2025.csv",
        [
            prediction_row("A", month=1, overall_phase=2, overall_phase_pred=2),
            prediction_row("A", month=12, overall_phase=3, overall_phase_pred=4),
            prediction_row("B", month=6, overall_phase=1, overall_phase_pred=3),
        ],
    )

    dataset = load_prediction_dataset(csv_path, "0m", "global", "actual")

    assert dataset.raw_2025_count == 3
    assert dataset.retained_count == 2
    assert dataset.duplicates_removed == 1
    latest_a = dataset.records.set_index("area_id").loc["A"]
    assert bool(latest_a["actual_alert"]) is True
    assert bool(latest_a["predicted_alert"]) is True


def test_exact_duplicate_latest_rows_are_allowed(tmp_path):
    row = prediction_row("A", month=12, overall_phase=3, overall_phase_pred=4)
    csv_path = write_prediction(tmp_path / "predictions_2025.csv", [row, row.copy()])

    dataset = load_prediction_dataset(csv_path, "0m", "global", "actual")

    assert dataset.retained_count == 1
    assert dataset.duplicates_removed == 1


def test_conflicting_duplicate_latest_rows_fail(tmp_path):
    csv_path = write_prediction(
        tmp_path / "predictions_2025.csv",
        [
            prediction_row("A", month=12, overall_phase=3),
            prediction_row("A", month=12, overall_phase=4),
        ],
    )

    with pytest.raises(AlertRiskMapError, match="Conflicting duplicate latest records"):
        load_prediction_dataset(csv_path, "0m", "global", "actual")


def test_missing_temporal_fields_fail(tmp_path):
    csv_path = write_prediction(tmp_path / "predictions_2025.csv", [prediction_row("A")])
    df = pd.read_csv(csv_path).drop(columns=["year", "month"])
    df.to_csv(csv_path, index=False)

    with pytest.raises(AlertRiskMapError, match="Missing temporal field"):
        load_prediction_dataset(csv_path, "0m", "global", "actual")


def test_no_2025_rows_fail(tmp_path):
    csv_path = write_prediction(tmp_path / "predictions_2024.csv", [prediction_row("A", year=2024)])

    with pytest.raises(AlertRiskMapError, match="No 2025 records"):
        load_prediction_dataset(csv_path, "0m", "global", "actual")


def test_output_conflict_validation(tmp_path):
    report_dir = tmp_path / "reports" / "maps"
    results_dir = tmp_path / "results" / "maps"
    from ipcch import paths

    old_reports = paths.REPORTS_DIR
    old_results = paths.RESULTS_DIR
    paths.REPORTS_DIR = tmp_path / "reports"
    paths.RESULTS_DIR = tmp_path / "results"
    try:
        plan = build_output_plan(report_dir, results_dir, "png")
        conflict = plan.figures["global_actual_vs_predicted"]
        conflict.parent.mkdir(parents=True)
        conflict.write_text("existing")
        with pytest.raises(AlertRiskMapError, match="Existing output file conflict"):
            validate_output_conflicts(plan, overwrite=False)
    finally:
        paths.REPORTS_DIR = old_reports
        paths.RESULTS_DIR = old_results


def test_ambiguous_horizon_discovery_fails(tmp_path):
    root = tmp_path / "root"
    write_prediction(root / "0m_global_a" / "predictions" / "predictions_2025.csv", [prediction_row("A")])
    write_prediction(root / "0m_global_b" / "predictions" / "predictions_2025.csv", [prediction_row("A")])

    with pytest.raises(AlertRiskMapError, match="Ambiguous global prediction candidates"):
        discover_prediction_file(root, "0m", "global")


def test_somalia_local_rejection(tmp_path):
    csv_path = write_prediction(tmp_path / "0m_somalia_local" / "predictions_2025.csv", [prediction_row("A")])

    with pytest.raises(AlertRiskMapError, match="Somalia-local"):
        discover_prediction_file(tmp_path, "0m", "somalia", csv_path)


def test_spatial_join_requires_full_coverage(tmp_path):
    csv_path = write_prediction(tmp_path / "predictions_2025.csv", [prediction_row("A"), prediction_row("B")])
    dataset = load_prediction_dataset(csv_path, "0m", "global", "actual")
    boundaries = geopandas.GeoDataFrame({"area_id": ["A"], "geometry": [box(0, 0, 1, 1)]}, crs="EPSG:4326")

    with pytest.raises(AlertRiskMapError, match="unmatched area_id"):
        join_predictions_to_spatial(dataset, boundaries)


def test_top_risk_category_assignment():
    df = pd.DataFrame(
        {
            "area_id": ["A", "B", "C", "D"],
            "phase3_worse": [0.9, 0.8, 0.1, 0.0],
            "phase3_pred": [0.1, 0.7, 0.95, 0.0],
        }
    )

    result = compute_top_risk_categories(df, top_fraction=0.5).set_index("area_id")

    assert result.loc["A", "risk_category"] == "actual_only"
    assert result.loc["B", "risk_category"] == "both"
    assert result.loc["C", "risk_category"] == "predicted_only"
    assert result.loc["D", "risk_category"] == "background"


def test_somalia_scope_filtering_from_spatial_country(tmp_path):
    csv_path = write_prediction(tmp_path / "predictions_2025.csv", [prediction_row("SO1")])
    dataset = load_prediction_dataset(csv_path, "0m", "somalia", "actual")
    boundaries = geopandas.GeoDataFrame(
        {"area_id": ["SO1", "KE1"], "iso3": ["SOM", "KEN"], "geometry": [box(0, 0, 1, 1), box(2, 2, 3, 3)]},
        crs="EPSG:4326",
    )

    joined = join_predictions_to_spatial(dataset, boundaries)

    assert joined.validation.matched_count == 1
    assert joined.joined_records["area_id"].tolist() == ["SO1"]


def test_latam_mask_uses_country_columns():
    gdf = geopandas.GeoDataFrame(
        {
            "area_id": ["GT1", "HT1", "KE1"],
            "country": ["Guatemala", "Haiti", "Kenya"],
            "geometry": [box(-91, 14, -90, 15), box(-73, 18, -72, 19), box(36, 0, 37, 1)],
        },
        crs="EPSG:4326",
    )

    mask = _latam_mask(gdf)

    assert mask.tolist() == [True, True, False]


def test_plot_actual_vs_predicted_global_renders_latam_thumbnail(tmp_path):
    joined = []
    for horizon in ["0m", "3m", "6m"]:
        gdf = geopandas.GeoDataFrame(
            {
                "area_id": ["GT1", "HT1", "KE1", "SO1"],
                "country": ["Guatemala", "Haiti", "Kenya", "Somalia"],
                "actual_alert": [True, False, False, True],
                "predicted_alert": [False, True, True, False],
                "geometry": [box(-91, 14, -90, 15), box(-73, 18, -72, 19), box(36, 0, 37, 1), box(45, 2, 46, 3)],
            },
            crs="EPSG:4326",
        )
        validation = type("Validation", (), {"matched_count": len(gdf), "unmatched_area_ids": [], "duplicate_join_area_ids": []})()
        joined.append(type("Joined", (), {"horizon": horizon, "joined_records": gdf, "source_file": tmp_path / f"{horizon}.csv", "validation": validation})())

    output = tmp_path / "global.png"
    plot_actual_vs_predicted(joined, output, "global", no_basemap=True)

    assert output.exists()
    assert output.stat().st_size > 0
