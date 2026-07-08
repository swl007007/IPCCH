from __future__ import annotations

from pathlib import Path

import geopandas
import pandas as pd
import pytest
from shapely.geometry import Polygon, box

from ipcch.nowcast_panel_export import (
    GEOMETRY_BASENAME,
    PANEL_FILENAME,
    SUMMARY_FILENAME,
    NowcastPanelExportError,
    build_panel,
    build_export_summary,
    build_geometry_layer,
    load_country_lookup,
    load_predictions,
    validate_output_conflicts,
    write_export_package,
)


def prediction_row(area_id: str, month: int = 1, **overrides) -> dict:
    row = {
        "test_year": 2025,
        "area_id": area_id,
        "year": 2025,
        "month": month,
        "date": f"2025-{month:02d}-01",
        "overall_phase": 2,
        "overall_phase_pred": 3,
        "phase2_worse": 0.4,
        "phase3_worse": 0.2,
        "phase4_worse": 0.0,
        "phase5_worse": 0.0,
        "phase2_pred": 0.5,
        "phase3_pred": 0.25,
        "phase4_pred": 0.1,
        "phase5_pred": 0.0,
    }
    row.update(overrides)
    return row


def write_csv(path: Path, rows: list[dict]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def test_build_panel_filters_requested_iso3_and_adds_export_metadata():
    predictions = pd.DataFrame(
        [
            prediction_row("10", month=1),
            prediction_row("10", month=2),
            prediction_row("100033", month=1),
            prediction_row("SO1", month=1),
        ]
    )
    lookup = pd.DataFrame(
        [
            {"area_id": "10", "iso3": "LSO", "country": "Lesotho"},
            {"area_id": "100033", "iso3": "NGA", "country": "Nigeria"},
            {"area_id": "SO1", "iso3": "SOM", "country": "Somalia"},
        ]
    )

    panel = build_panel(predictions, lookup, ["LSO", "NGA"])

    assert panel["iso3"].tolist() == ["LSO", "LSO", "NGA"]
    assert panel["nowcast_scope"].unique().tolist() == ["0m"]
    assert panel["source_experiment"].unique().tolist() == ["0m_global_identifier_features_threshold_0_20"]
    assert set(panel["area_id"]) == {"10", "100033"}
    assert panel[["area_id", "year", "month"]].duplicated().sum() == 0


def test_build_panel_fails_on_duplicate_area_month_rows():
    predictions = pd.DataFrame([prediction_row("10", month=1), prediction_row("10", month=1)])
    lookup = pd.DataFrame([{"area_id": "10", "iso3": "LSO", "country": "Lesotho"}])

    with pytest.raises(NowcastPanelExportError, match="Duplicate selected prediction rows"):
        build_panel(predictions, lookup, ["LSO"])


def test_build_panel_fails_when_required_prediction_columns_missing():
    predictions = pd.DataFrame([prediction_row("10")]).drop(columns=["phase3_pred"])
    lookup = pd.DataFrame([{"area_id": "10", "iso3": "LSO", "country": "Lesotho"}])

    with pytest.raises(NowcastPanelExportError, match="Missing required prediction columns"):
        build_panel(predictions, lookup, ["LSO"])


def test_load_country_lookup_requires_iso3_and_country_columns(tmp_path):
    path = write_csv(tmp_path / "lookup.csv", [{"area_id": "10", "country": "Lesotho"}])

    with pytest.raises(NowcastPanelExportError, match="Missing required country lookup columns"):
        load_country_lookup(path)


def write_spatial(path: Path, area_ids: list[str], geometries: list | None = None) -> Path:
    if geometries is None:
        geometries = [box(i, i, i + 1, i + 1) for i in range(len(area_ids))]
    gdf = geopandas.GeoDataFrame(
        {
            "area_id": area_ids,
            "geometry": geometries,
        },
        crs="EPSG:4326",
    )
    gdf.to_file(path, driver="GeoJSON")
    return path


def test_build_geometry_layer_has_one_row_per_area_id(tmp_path):
    panel = pd.DataFrame(
        [
            {"area_id": "10", "iso3": "LSO", "country": "Lesotho", "date": "2025-01-01"},
            {"area_id": "10", "iso3": "LSO", "country": "Lesotho", "date": "2025-02-01"},
            {"area_id": "100033", "iso3": "NGA", "country": "Nigeria", "date": "2025-01-01"},
        ]
    )
    spatial = write_spatial(tmp_path / "spatial.geojson", ["10", "100033"])

    geometry = build_geometry_layer(panel, spatial)

    assert geometry["area_id"].tolist() == ["10", "100033"]
    assert geometry.set_index("area_id").loc["10", "n_months"] == 2
    assert geometry.crs.to_string() == "EPSG:4326"


def test_build_export_summary_tracks_geometry_repairs_and_country_month_counts(tmp_path):
    panel = pd.DataFrame(
        [
            {"area_id": "10", "iso3": "LSO", "country": "Lesotho", "date": "2025-01-01"},
            {"area_id": "10", "iso3": "LSO", "country": "Lesotho", "date": "2025-02-01"},
            {"area_id": "100033", "iso3": "NGA", "country": "Nigeria", "date": "2025-01-01"},
        ]
    )
    invalid_polygon = Polygon([(0, 0), (1, 1), (1, 0), (0, 1), (0, 0)])
    spatial = write_spatial(tmp_path / "invalid_spatial.geojson", ["10", "100033"], [invalid_polygon, box(2, 2, 3, 3)])
    geometry = build_geometry_layer(panel, spatial)
    summary = build_export_summary(
        predictions=pd.DataFrame([{"area_id": "10"}]),
        panel=panel,
        geometry=geometry,
        prediction_source="predictions.csv",
        country_lookup_source="lookup.csv",
        spatial_source=spatial,
        output_paths=validate_output_conflicts(tmp_path / "export", overwrite=True),
        countries=["LSO", "NGA"],
        overwrite=True,
    )

    assert summary.geometry_repaired_count > 0
    assert summary.month_row_counts == {"LSO": {"2025-01": 1, "2025-02": 1}, "NGA": {"2025-01": 1}}


def test_build_geometry_layer_fails_on_missing_area_id(tmp_path):
    panel = pd.DataFrame([{"area_id": "10", "iso3": "LSO", "country": "Lesotho", "date": "2025-01-01"}])
    spatial = write_spatial(tmp_path / "spatial.geojson", ["11"])

    with pytest.raises(NowcastPanelExportError, match="Selected area_id values missing geometry"):
        build_geometry_layer(panel, spatial)


def test_validate_output_conflicts_blocks_existing_package_without_overwrite(tmp_path):
    out_dir = tmp_path / "export"
    out_dir.mkdir()
    (out_dir / PANEL_FILENAME).write_text("existing")

    with pytest.raises(NowcastPanelExportError, match="Existing output file conflict"):
        validate_output_conflicts(out_dir, overwrite=False)


def test_write_export_package_writes_csv_shapefile_and_summary(tmp_path):
    panel = pd.DataFrame(
        [
            {
                "iso3": "LSO",
                "country": "Lesotho",
                "area_id": "10",
                "test_year": 2025,
                "year": 2025,
                "month": 1,
                "date": "2025-01-01",
                "overall_phase": 2,
                "overall_phase_pred": 3,
                "phase2_worse": 0.4,
                "phase3_worse": 0.2,
                "phase4_worse": 0.0,
                "phase5_worse": 0.0,
                "phase2_pred": 0.5,
                "phase3_pred": 0.25,
                "phase4_pred": 0.1,
                "phase5_pred": 0.0,
                "nowcast_scope": "0m",
                "source_experiment": "0m_global_identifier_features_threshold_0_20",
            }
        ]
    )
    geometry = geopandas.GeoDataFrame(
        {
            "area_id": ["10"],
            "iso3": ["LSO"],
            "country": ["Lesotho"],
            "n_months": [1],
            "min_date": ["2025-01-01"],
            "max_date": ["2025-01-01"],
            "geometry": [box(0, 0, 1, 1)],
        },
        crs="EPSG:4326",
    )
    paths = validate_output_conflicts(tmp_path / "export", overwrite=False)
    summary = build_export_summary(
        predictions=pd.DataFrame([{"area_id": "10"}]),
        panel=panel,
        geometry=geometry,
        prediction_source="pred.csv",
        country_lookup_source="lookup.csv",
        spatial_source="spatial.geojson",
        output_paths=paths,
        countries=["LSO"],
        overwrite=False,
    )

    write_export_package(panel, geometry, summary, paths)

    assert (tmp_path / "export" / PANEL_FILENAME).exists()
    assert (tmp_path / "export" / f"{GEOMETRY_BASENAME}.shp").exists()
    assert (tmp_path / "export" / SUMMARY_FILENAME).exists()
    assert summary.month_row_counts == {"LSO": {"2025-01": 1}}
