from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest
from shapely.geometry import box

geopandas = pytest.importorskip("geopandas")

REPO_ROOT = Path(__file__).resolve().parents[2]
CLI = REPO_ROOT / "scripts" / "reporting" / "export_2025_0m_country_nowcast_panel.py"
RESULT_TEST_ROOT = REPO_ROOT / "results" / "pytest_nowcast_panel_export"


@pytest.fixture
def output_dir(tmp_path):
    out = RESULT_TEST_ROOT / tmp_path.name
    shutil.rmtree(out, ignore_errors=True)
    yield out
    shutil.rmtree(out, ignore_errors=True)


def prediction_row(area_id: str, month: int) -> dict:
    return {
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


def run_cli(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=REPO_ROOT, text=True, capture_output=True, check=False)


def test_cli_help():
    result = run_cli([sys.executable, str(CLI), "--help"])

    assert result.returncode == 0
    assert "--countries" in result.stdout
    assert "--spatial-path" in result.stdout


def test_cli_exports_panel_shapefile_and_summary(tmp_path, output_dir):
    predictions = tmp_path / "predictions_2025.csv"
    pd.DataFrame(
        [
            prediction_row("10", 1),
            prediction_row("10", 2),
            prediction_row("100033", 1),
            prediction_row("BFA1", 1),
            prediction_row("SO1", 1),
        ]
    ).to_csv(predictions, index=False)

    lookup = tmp_path / "country_lookup.csv"
    pd.DataFrame(
        [
            {"area_id": "10", "iso3": "LSO", "country": "Lesotho"},
            {"area_id": "100033", "iso3": "NGA", "country": "Nigeria"},
            {"area_id": "BFA1", "iso3": "BFA", "country": "Burkina Faso"},
            {"area_id": "SO1", "iso3": "SOM", "country": "Somalia"},
        ]
    ).to_csv(lookup, index=False)

    spatial = tmp_path / "spatial.geojson"
    geopandas.GeoDataFrame(
        {
            "area_id": ["10", "100033", "BFA1"],
            "geometry": [box(0, 0, 1, 1), box(1, 1, 2, 2), box(2, 2, 3, 3)],
        },
        crs="EPSG:4326",
    ).to_file(spatial, driver="GeoJSON")

    result = run_cli(
        [
            sys.executable,
            str(CLI),
            "--predictions",
            str(predictions),
            "--country-lookup",
            str(lookup),
            "--spatial-path",
            str(spatial),
            "--output-dir",
            str(output_dir),
            "--overwrite",
        ]
    )

    assert result.returncode == 0, result.stderr
    panel = pd.read_csv(output_dir / "nowcast_panel_2025_0m_LSO_NGA_BFA.csv")
    assert set(panel["iso3"]) == {"LSO", "NGA", "BFA"}
    assert set(panel["nowcast_scope"]) == {"0m"}
    exported_geometry = geopandas.read_file(output_dir / "nowcast_admin_geometries_2025_0m_LSO_NGA_BFA.shp")
    assert set(exported_geometry["area_id"].astype(str)) == {"10", "100033", "BFA1"}
    summary = json.loads((output_dir / "export_validation_summary.json").read_text(encoding="utf-8"))
    assert summary["panel_rows"] == 4
    assert summary["admin_units"] == 3
    assert summary["geometry_repaired_count"] == 0
    assert summary["month_row_counts"] == {"BFA": {"2025-01": 1}, "LSO": {"2025-01": 1, "2025-02": 1}, "NGA": {"2025-01": 1}}
