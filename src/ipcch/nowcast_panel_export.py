from __future__ import annotations

from pathlib import Path
from typing import Sequence

import pandas as pd

from ipcch import paths
from ipcch.alert_risk_maps import default_country_lookup_path as _default_country_lookup_path
from ipcch.alert_risk_maps import default_spatial_path as _default_spatial_path
from ipcch.alert_risk_maps import normalize_area_id, resolve_path


class NowcastPanelExportError(Exception):
    """Raised when the 2025 nowcast panel export cannot be produced safely."""


SOURCE_EXPERIMENT = "0m_global_identifier_features_threshold_0_20"
DEFAULT_COUNTRIES = ("LSO", "NGA", "BFA")
PREDICTION_FILENAME = "predictions_2025.csv"
PANEL_FILENAME = "nowcast_panel_2025_0m_LSO_NGA_BFA.csv"
GEOMETRY_BASENAME = "nowcast_admin_geometries_2025_0m_LSO_NGA_BFA"
SUMMARY_FILENAME = "export_validation_summary.json"

PREDICTION_COLUMNS = (
    "test_year",
    "area_id",
    "year",
    "month",
    "date",
    "overall_phase",
    "overall_phase_pred",
    "phase2_worse",
    "phase3_worse",
    "phase4_worse",
    "phase5_worse",
    "phase2_pred",
    "phase3_pred",
    "phase4_pred",
    "phase5_pred",
)
PANEL_COLUMNS = (
    "iso3",
    "country",
    "area_id",
    "test_year",
    "year",
    "month",
    "date",
    "overall_phase",
    "overall_phase_pred",
    "phase2_worse",
    "phase3_worse",
    "phase4_worse",
    "phase5_worse",
    "phase2_pred",
    "phase3_pred",
    "phase4_pred",
    "phase5_pred",
    "nowcast_scope",
    "source_experiment",
)
LOOKUP_COLUMNS = ("area_id", "iso3", "country")


def default_prediction_path() -> Path:
    return (
        paths.RESULTS_DIR
        / "experiments"
        / "deep_feature_weight_decay_forecasting"
        / SOURCE_EXPERIMENT
        / "predictions"
        / PREDICTION_FILENAME
    )


def default_country_lookup_path() -> Path:
    return _default_country_lookup_path()


def default_spatial_path() -> Path:
    spatial = _default_spatial_path()
    if spatial is None:
        return paths.SOURCE_DATA_DIR / "assembled_IPCCH" / "spatial" / "ipcch_admin_geometry.shp"
    return Path(spatial)


def default_output_dir() -> Path:
    return paths.RESULTS_DIR / "exports" / "nowcast_panel_2025_0m_lso_nga_bfa"


def _require_columns(df: pd.DataFrame, required: Sequence[str], label: str) -> None:
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise NowcastPanelExportError(f"Missing required {label} columns: {missing}")


def load_predictions(path: str | Path) -> pd.DataFrame:
    resolved = resolve_path(path)
    if not resolved.exists():
        raise NowcastPanelExportError(f"Prediction CSV does not exist: {resolved}")
    predictions = pd.read_csv(resolved)
    _require_columns(predictions, PREDICTION_COLUMNS, "prediction")
    return predictions


def load_country_lookup(path: str | Path) -> pd.DataFrame:
    resolved = resolve_path(path)
    if not resolved.exists():
        raise NowcastPanelExportError(f"Country lookup CSV does not exist: {resolved}")
    lookup = pd.read_csv(resolved)
    _require_columns(lookup, LOOKUP_COLUMNS, "country lookup")
    lookup = lookup.loc[:, list(LOOKUP_COLUMNS)].dropna(subset=["area_id", "iso3"]).copy()
    lookup["area_id"] = normalize_area_id(lookup["area_id"])
    lookup["iso3"] = lookup["iso3"].astype(str).str.strip().str.upper()
    lookup["country"] = lookup["country"].astype(str).str.strip()
    duplicates = sorted(lookup.loc[lookup["area_id"].duplicated(), "area_id"].astype(str).unique().tolist())
    if duplicates:
        raise NowcastPanelExportError(f"Country lookup has duplicate area_id values: {duplicates[:10]}")
    return lookup


def build_panel(predictions: pd.DataFrame, country_lookup: pd.DataFrame, countries: Sequence[str]) -> pd.DataFrame:
    _require_columns(predictions, PREDICTION_COLUMNS, "prediction")
    _require_columns(country_lookup, LOOKUP_COLUMNS, "country lookup")
    requested = tuple(code.upper() for code in countries)
    if not requested:
        raise NowcastPanelExportError("At least one country ISO3 code is required")

    pred = predictions.loc[:, list(PREDICTION_COLUMNS)].copy()
    pred["area_id"] = normalize_area_id(pred["area_id"])
    pred["test_year"] = pd.to_numeric(pred["test_year"], errors="coerce").astype("Int64")
    pred["year"] = pd.to_numeric(pred["year"], errors="coerce").astype("Int64")
    pred["month"] = pd.to_numeric(pred["month"], errors="coerce").astype("Int64")
    pred = pred[pred["test_year"].eq(2025) & pred["year"].eq(2025)].copy()
    if pred.empty:
        raise NowcastPanelExportError("No 2025 prediction rows found after filtering test_year=2025 and year=2025")

    lookup = country_lookup.loc[:, list(LOOKUP_COLUMNS)].copy()
    lookup["area_id"] = normalize_area_id(lookup["area_id"])
    lookup["iso3"] = lookup["iso3"].astype(str).str.strip().str.upper()
    lookup["country"] = lookup["country"].astype(str).str.strip()
    lookup = lookup[lookup["iso3"].isin(requested)].copy()
    if lookup.empty:
        raise NowcastPanelExportError(f"No country lookup rows found for requested ISO3 codes: {list(requested)}")

    merged = pred.merge(lookup, on="area_id", how="inner", validate="many_to_one")
    if merged.empty:
        raise NowcastPanelExportError(f"No prediction rows matched requested ISO3 codes: {list(requested)}")

    duplicate_mask = merged.duplicated(["area_id", "year", "month"], keep=False)
    if duplicate_mask.any():
        sample = merged.loc[duplicate_mask, ["area_id", "year", "month"]].head(10).to_dict("records")
        raise NowcastPanelExportError(f"Duplicate selected prediction rows for area_id/year/month: {sample}")

    merged["nowcast_scope"] = "0m"
    merged["source_experiment"] = SOURCE_EXPERIMENT
    merged = merged.loc[:, list(PANEL_COLUMNS)].sort_values(["iso3", "area_id", "year", "month"]).reset_index(drop=True)
    return merged
