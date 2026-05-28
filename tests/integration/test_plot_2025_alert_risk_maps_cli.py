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
CLI = REPO_ROOT / "scripts" / "reporting" / "plot_2025_alert_risk_maps.py"
REPORT_TEST_ROOT = REPO_ROOT / "reports" / "pytest_alert_risk_maps"
RESULT_TEST_ROOT = REPO_ROOT / "results" / "pytest_alert_risk_maps"


@pytest.fixture
def output_dirs(tmp_path):
    report_dir = REPORT_TEST_ROOT / tmp_path.name
    results_dir = RESULT_TEST_ROOT / tmp_path.name
    shutil.rmtree(report_dir, ignore_errors=True)
    shutil.rmtree(results_dir, ignore_errors=True)
    yield report_dir, results_dir
    shutil.rmtree(report_dir, ignore_errors=True)
    shutil.rmtree(results_dir, ignore_errors=True)


def prediction_row(area_id: str, month: int = 1, **overrides):
    row = {
        "area_id": area_id,
        "year": 2025,
        "month": month,
        "overall_phase": 2,
        "overall_phase_pred": 3,
        "phase3_worse": 0.1,
        "phase3_pred": 0.2,
    }
    row.update(overrides)
    return row


def write_prediction(path: Path, rows: list[dict]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def write_spatial(path: Path, area_ids: list[str]) -> Path:
    gdf = geopandas.GeoDataFrame(
        {
            "area_id": area_ids,
            "iso3": ["SOM" if area_id.startswith("SO") else "KEN" for area_id in area_ids],
            "geometry": [box(i, i, i + 0.5, i + 0.5) for i in range(len(area_ids))],
        },
        crs="EPSG:4326",
    )
    gdf.to_file(path, driver="GeoJSON")
    return path


def base_command(tmp_path: Path, spatial: Path, files: dict[str, Path], report_dir: Path, results_dir: Path) -> list[str]:
    return [
        sys.executable,
        str(CLI),
        "--prediction-root",
        str(tmp_path / "predictions"),
        "--spatial-path",
        str(spatial),
        "--out-report-dir",
        str(report_dir),
        "--out-results-dir",
        str(results_dir),
        "--horizon-0m-file",
        str(files["global_0m"]),
        "--horizon-3m-file",
        str(files["global_3m"]),
        "--horizon-6m-file",
        str(files["global_6m"]),
        "--somalia-horizon-0m-file",
        str(files["somalia_0m"]),
        "--somalia-horizon-3m-file",
        str(files["somalia_3m"]),
        "--somalia-horizon-6m-file",
        str(files["somalia_6m"]),
        "--no-basemap",
    ]


def create_inputs(tmp_path: Path) -> tuple[Path, dict[str, Path]]:
    spatial = write_spatial(tmp_path / "spatial.geojson", ["G1", "G2", "SO1", "SO2"])
    files = {}
    for horizon in ["0m", "3m", "6m"]:
        files[f"global_{horizon}"] = write_prediction(
            tmp_path / "predictions" / f"{horizon}_global" / "predictions" / "predictions_2025.csv",
            [
                prediction_row("G1", phase3_worse=0.9, phase3_pred=0.1),
                prediction_row("G2", phase3_worse=0.1, phase3_pred=0.9),
            ],
        )
        files[f"somalia_{horizon}"] = write_prediction(
            tmp_path / "predictions" / f"{horizon}_global_somalia" / "predictions" / "predictions_2025.csv",
            [
                prediction_row("SO1", phase3_worse=0.9, phase3_pred=0.1),
                prediction_row("SO2", phase3_worse=0.1, phase3_pred=0.9),
            ],
        )
    return spatial, files


def run_cli(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=REPO_ROOT, text=True, capture_output=True, check=False)


def test_cli_help():
    result = run_cli([sys.executable, str(CLI), "--help"])

    assert result.returncode == 0
    assert "--horizon-0m-file" in result.stdout


def test_cli_smoke_generates_all_outputs_and_summary(tmp_path, output_dirs):
    spatial, files = create_inputs(tmp_path)
    result = run_cli(base_command(tmp_path, spatial, files, *output_dirs))

    assert result.returncode == 0, result.stderr
    report_dir = output_dirs[0]
    expected = [
        "ipcch_2025_global_0m-3m-6m_actual_vs_predicted_alert_map.png",
        "ipcch_2025_somalia_0m-3m-6m_actual_vs_predicted_alert_map.png",
        "ipcch_2025_global_0m_top30_phase3_risk_comparison_map.png",
        "ipcch_2025_somalia_0m_top30_phase3_risk_comparison_map.png",
    ]
    for filename in expected:
        assert (report_dir / filename).exists()
    summary_path = output_dirs[1] / "ipcch_2025_alert_risk_maps_validation_summary.json"
    summary = json.loads(summary_path.read_text())
    assert summary["status"] == "success"
    for scope in ["global", "somalia"]:
        for horizon in ["0m", "3m", "6m"]:
            key = f"{scope}_{horizon}"
            assert key in summary["selected_files"]
            assert summary["record_counts"][key]["raw_2025_count"] == 2
            assert summary["join_counts"][key]["matched_count"] == 2


def test_missing_required_prediction_columns_fail_without_outputs(tmp_path, output_dirs):
    spatial, files = create_inputs(tmp_path)
    broken = pd.read_csv(files["global_0m"]).drop(columns=["overall_phase_pred"])
    broken.to_csv(files["global_0m"], index=False)

    result = run_cli(base_command(tmp_path, spatial, files, *output_dirs))

    assert result.returncode != 0
    assert "overall_phase_pred" in result.stderr
    assert not (output_dirs[0]).exists()


def test_all_null_required_values_fail_without_outputs(tmp_path, output_dirs):
    spatial, files = create_inputs(tmp_path)
    broken = pd.read_csv(files["global_0m"])
    broken["overall_phase_pred"] = None
    broken.to_csv(files["global_0m"], index=False)

    result = run_cli(base_command(tmp_path, spatial, files, *output_dirs))

    assert result.returncode != 0
    assert "All-null" in result.stderr
    assert not (output_dirs[0]).exists()


def test_no_2025_rows_fail_without_outputs(tmp_path, output_dirs):
    spatial, files = create_inputs(tmp_path)
    broken = pd.read_csv(files["global_0m"])
    broken["year"] = 2024
    broken.to_csv(files["global_0m"], index=False)

    result = run_cli(base_command(tmp_path, spatial, files, *output_dirs))

    assert result.returncode != 0
    assert "No 2025 records" in result.stderr
    assert not (output_dirs[0]).exists()


def test_missing_temporal_fields_fail_without_outputs(tmp_path, output_dirs):
    spatial, files = create_inputs(tmp_path)
    broken = pd.read_csv(files["global_0m"]).drop(columns=["year", "month"])
    broken.to_csv(files["global_0m"], index=False)

    result = run_cli(base_command(tmp_path, spatial, files, *output_dirs))

    assert result.returncode != 0
    assert "Missing temporal field" in result.stderr
    assert not (output_dirs[0]).exists()


def test_unmatched_spatial_area_id_failure_without_outputs(tmp_path, output_dirs):
    spatial, files = create_inputs(tmp_path)
    write_spatial(spatial, ["G1", "SO1", "SO2"])

    result = run_cli(base_command(tmp_path, spatial, files, *output_dirs))

    assert result.returncode != 0
    assert "unmatched area_id" in result.stderr
    assert not (output_dirs[0]).exists()


def test_existing_output_conflict_without_overwrite(tmp_path, output_dirs):
    spatial, files = create_inputs(tmp_path)
    report_dir = output_dirs[0]
    report_dir.mkdir(parents=True)
    (report_dir / "ipcch_2025_global_0m-3m-6m_actual_vs_predicted_alert_map.png").write_text("existing")

    result = run_cli(base_command(tmp_path, spatial, files, *output_dirs))

    assert result.returncode != 0
    assert "Existing output file conflict" in result.stderr
