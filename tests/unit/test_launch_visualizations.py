from __future__ import annotations

import pandas as pd
import pytest

gpd = pytest.importorskip("geopandas")
shapely = pytest.importorskip("shapely")
from shapely.geometry import box  # noqa: E402

from ipcch import launch_visualizations as lv  # noqa: E402


def _boundaries(area_ids, duplicate=False):
    rows = []
    for i, aid in enumerate(area_ids):
        rows.append({"area_id": aid, "geometry": box(i, 0, i + 1, 1)})
    if duplicate:
        rows.append({"area_id": area_ids[0], "geometry": box(99, 0, 100, 1)})
    return gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:4326")


def _predictions(area_ids):
    return pd.DataFrame({"area_id": area_ids, "overall_phase_pred": [3] * len(area_ids)})


def test_recording_join_records_unmatched_not_raise():
    boundaries = _boundaries(["A", "B"])  # only A,B have geometry
    preds = _predictions(["A", "B", "C"])  # C unmatched
    actuals = pd.DataFrame({"area_id": ["A", "Z"], "actual_overall_phase": [4, 3], "actual_crisis": [True, True]})
    join = lv.join_for_two_panel(preds, actuals, boundaries)
    assert join.unmatched_prediction == ["C"]
    assert join.unmatched_actual == ["Z"]
    assert join.duplicate_spatial_keys == []  # zero on success
    assert join.mapped_predicted_count == 2
    assert join.mapped_actual_count == 1


def test_duplicate_spatial_keys_hard_fail():
    boundaries = _boundaries(["A", "B"], duplicate=True)
    preds = _predictions(["A", "B"])
    with pytest.raises(lv.LaunchMapError, match="Duplicate spatial join keys"):
        lv.join_for_two_panel(preds, preds.iloc[0:0], boundaries)


def test_build_map_predicted_only_when_actuals_unavailable(tmp_path):
    pytest.importorskip("matplotlib")
    import json
    from ipcch import paths

    boundaries_path = tmp_path / "boundaries.geojson"
    _boundaries(["A", "B", "C"]).to_file(boundaries_path, driver="GeoJSON")
    preds = _predictions(["A", "B", "C"])
    import shutil
    import uuid
    token = uuid.uuid4().hex[:8]
    rep_dir = paths.REPORTS_DIR / "launch" / f"_pytest_{token}" / "visualizations"
    res_dir = paths.RESULTS_DIR / "launch" / f"_pytest_{token}" / "visualizations"
    try:
        summary = lv.build_map(
            predictions=preds, april_actuals=None, spatial_path=boundaries_path,
            figure_path=rep_dir / "map.png", summary_path=res_dir / "summary.json",
            join_validation_csv=res_dir / "join.csv", actual_source="none",
            prediction_source="preds.csv", scope="global", no_basemap=True, overwrite=True,
            target_period="2027-04", prediction_period="2027-04",
        )
        assert (rep_dir / "map.png").exists()
        written = json.loads((res_dir / "summary.json").read_text())
        assert written["status"] == "rendered_predicted_only"
        assert written["actual_month"] == "2027-04"
        assert written["prediction_month"] == "2027-04"
        assert written["mapped_actual_count"] == 0
        assert summary.mapped_predicted_count == 3
    finally:
        shutil.rmtree(rep_dir.parent, ignore_errors=True)
        shutil.rmtree(res_dir.parent, ignore_errors=True)


def test_build_map_renders_and_writes_validation_summary(tmp_path):
    pytest.importorskip("matplotlib")
    import json
    from ipcch import paths

    boundaries_path = tmp_path / "boundaries.geojson"
    _boundaries(["A", "B", "C"]).to_file(boundaries_path, driver="GeoJSON")
    preds = _predictions(["A", "B", "C", "D"])  # D unmatched
    actuals = pd.DataFrame({"area_id": ["A", "B"], "actual_overall_phase": [4, 2], "actual_crisis": [True, False]})

    # Use repo-relative dirs so ensure_under passes; clean up after.
    import shutil
    import uuid
    token = uuid.uuid4().hex[:8]
    rep_dir = paths.REPORTS_DIR / "launch" / f"_pytest_{token}" / "visualizations"
    res_dir = paths.RESULTS_DIR / "launch" / f"_pytest_{token}" / "visualizations"
    try:
        summary = lv.build_map(
            predictions=preds, april_actuals=actuals, spatial_path=boundaries_path,
            figure_path=rep_dir / "map.png", summary_path=res_dir / "summary.json",
            join_validation_csv=res_dir / "join.csv", actual_source="actuals.csv",
            prediction_source="preds.csv", scope="global", no_basemap=True, overwrite=True,
        )
        assert (rep_dir / "map.png").exists()
        written = json.loads((res_dir / "summary.json").read_text())
        assert written["predicted_area_count"] == 4
        assert written["mapped_predicted_count"] == 3
        assert written["unmatched_prediction_area_ids"] == ["D"]
        assert written["duplicate_spatial_keys"] == []
    finally:
        shutil.rmtree(rep_dir.parent, ignore_errors=True)
        shutil.rmtree(res_dir.parent, ignore_errors=True)
