from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

import pandas as pd

from ipcch import paths
from ipcch.alert_risk_maps import default_country_lookup_path as _default_country_lookup_path
from ipcch.alert_risk_maps import default_spatial_path as _default_spatial_path
from ipcch.alert_risk_maps import load_spatial_boundaries
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


@dataclass(frozen=True)
class ExportPaths:
    output_dir: Path
    panel_csv: Path
    geometry_shp: Path
    summary_json: Path


@dataclass
class ExportSummary:
    run_timestamp: str
    prediction_source: str
    country_lookup_source: str
    spatial_source: str
    output_paths: Mapping[str, str]
    countries: list[str]
    source_rows: int
    panel_rows: int
    admin_units: int
    country_row_counts: Mapping[str, int]
    country_admin_counts: Mapping[str, int]
    month_row_counts: Mapping[str, int]
    geometry_rows: int
    unmatched_geometry_area_ids: list[str]
    overwrite: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


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


def validate_output_conflicts(output_dir: str | Path, overwrite: bool) -> ExportPaths:
    out_dir = resolve_path(output_dir)
    paths_obj = ExportPaths(
        output_dir=out_dir,
        panel_csv=out_dir / PANEL_FILENAME,
        geometry_shp=out_dir / f"{GEOMETRY_BASENAME}.shp",
        summary_json=out_dir / SUMMARY_FILENAME,
    )
    sidecars = [out_dir / f"{GEOMETRY_BASENAME}{suffix}" for suffix in (".shp", ".shx", ".dbf", ".prj", ".cpg")]
    targets = [paths_obj.panel_csv, paths_obj.summary_json, *sidecars]
    conflicts = [path for path in targets if path.exists()]
    if conflicts and not overwrite:
        joined = ", ".join(str(path) for path in conflicts)
        raise NowcastPanelExportError(f"Existing output file conflict without --overwrite: {joined}")
    return paths_obj


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


def build_geometry_layer(panel: pd.DataFrame, spatial_path: str | Path):
    if panel.empty:
        raise NowcastPanelExportError("Cannot build geometry layer from an empty panel")
    required = ("area_id", "iso3", "country", "date")
    _require_columns(panel, required, "panel")
    panel_meta = panel.loc[:, list(required)].copy()
    panel_meta["area_id"] = normalize_area_id(panel_meta["area_id"])
    panel_meta["date"] = pd.to_datetime(panel_meta["date"], errors="coerce")
    if panel_meta["date"].isna().any():
        raise NowcastPanelExportError("Panel contains invalid date values")

    admin_meta = (
        panel_meta.groupby(["area_id", "iso3", "country"], as_index=False)
        .agg(n_months=("date", "nunique"), min_date=("date", "min"), max_date=("date", "max"))
        .sort_values(["iso3", "area_id"])
    )
    admin_meta["min_date"] = admin_meta["min_date"].dt.date.astype(str)
    admin_meta["max_date"] = admin_meta["max_date"].dt.date.astype(str)

    try:
        boundaries = load_spatial_boundaries(spatial_path)
    except Exception as exc:  # pragma: no cover - exercised through happy path in tests
        raise NowcastPanelExportError(f"Failed to load spatial boundaries: {exc}") from exc

    boundaries = boundaries[["area_id", "geometry"]].copy()
    boundaries["area_id"] = normalize_area_id(boundaries["area_id"])
    joined = admin_meta.merge(boundaries, on="area_id", how="left", validate="one_to_one")
    missing = sorted(joined.loc[joined["geometry"].isna(), "area_id"].astype(str).unique().tolist())
    if missing:
        raise NowcastPanelExportError(f"Selected area_id values missing geometry: {missing[:10]}")

    gpd = __import__("geopandas")
    return gpd.GeoDataFrame(joined, geometry="geometry", crs=boundaries.crs)


def _month_counts(panel: pd.DataFrame) -> dict[str, int]:
    months = pd.to_datetime(panel["date"], errors="coerce").dt.to_period("M").astype(str)
    return {str(key): int(value) for key, value in months.value_counts().sort_index().items()}


def build_export_summary(
    *,
    predictions: pd.DataFrame,
    panel: pd.DataFrame,
    geometry,
    prediction_source: str | Path,
    country_lookup_source: str | Path,
    spatial_source: str | Path,
    output_paths: ExportPaths,
    countries: Sequence[str],
    overwrite: bool,
) -> ExportSummary:
    row_counts = panel.groupby("iso3").size().sort_index()
    admin_counts = panel.groupby("iso3")["area_id"].nunique().sort_index()
    return ExportSummary(
        run_timestamp=datetime.now(timezone.utc).isoformat(),
        prediction_source=str(prediction_source),
        country_lookup_source=str(country_lookup_source),
        spatial_source=str(spatial_source),
        output_paths={
            "panel_csv": str(output_paths.panel_csv),
            "geometry_shp": str(output_paths.geometry_shp),
            "summary_json": str(output_paths.summary_json),
        },
        countries=[code.upper() for code in countries],
        source_rows=int(len(predictions)),
        panel_rows=int(len(panel)),
        admin_units=int(panel["area_id"].nunique()),
        country_row_counts={str(key): int(value) for key, value in row_counts.items()},
        country_admin_counts={str(key): int(value) for key, value in admin_counts.items()},
        month_row_counts=_month_counts(panel),
        geometry_rows=int(len(geometry)),
        unmatched_geometry_area_ids=[],
        overwrite=bool(overwrite),
    )


def write_export_package(panel: pd.DataFrame, geometry, summary: ExportSummary, output_paths: ExportPaths) -> None:
    output_paths.output_dir.mkdir(parents=True, exist_ok=True)
    panel.to_csv(output_paths.panel_csv, index=False)
    geometry.to_file(output_paths.geometry_shp, driver="ESRI Shapefile", encoding="UTF-8")
    summary.output_paths = {
        "panel_csv": str(output_paths.panel_csv),
        "geometry_shp": str(output_paths.geometry_shp),
        "summary_json": str(output_paths.summary_json),
    }
    output_paths.summary_json.write_text(json.dumps(summary.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
