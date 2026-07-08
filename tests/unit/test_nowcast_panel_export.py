from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from ipcch.nowcast_panel_export import (
    NowcastPanelExportError,
    build_panel,
    load_country_lookup,
    load_predictions,
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
