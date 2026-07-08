# 2025 0m Country Nowcast Panel Export Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and run a post-processing exporter that provides 2025 `0m` nowcast estimates for Lesotho, Nigeria, and Burkina Faso as an admin-month panel CSV plus an accompanying admin-unit shapefile.

**Architecture:** Add one focused export module under `src/ipcch/` and one thin CLI under `scripts/reporting/`. The module reads the existing 2025 `fs0=0m` prediction CSV, joins country metadata, validates a unique `area_id x month` panel, joins one geometry per selected `area_id`, writes the CSV/shapefile/summary package, and never mutates or retrains model outputs.

**Tech Stack:** Python, pandas, geopandas, shapely test geometries, pytest, existing `ipcch.paths` and `ipcch.alert_risk_maps` path/spatial helpers.

## Global Constraints

- Source spec: `docs/superpowers/specs/2026-07-08-2025-0m-country-nowcast-panel-export-design.md`.
- "Nowcast" means the existing 2025 `0m` annual holdout output, not the latest April 2026 launch nowcasting workflow.
- The export is post-processing only: no model training, no rerun of prediction, no threshold tuning, no mutation of existing experiment outputs.
- Default prediction source: `results/experiments/deep_feature_weight_decay_forecasting/0m_global_identifier_features_threshold_0_20/predictions/predictions_2025.csv`.
- Default countries: `LSO`, `NGA`, `BFA`.
- CSV panel grain: one row per `area_id x month`.
- Shapefile grain: one geometry row per selected `area_id`, not one row per admin-month.
- Join key between CSV and shapefile: `area_id`.
- Library code must not hardcode machine-specific absolute paths; use `ipcch.paths`, existing default helpers, or explicit CLI options.
- Generated source spatial data should remain outside the repository except for the generated export package under `results/exports/...`.

---

## File Structure

- Create `src/ipcch/nowcast_panel_export.py`
  - Owns defaults, validation, country filtering, panel assembly, geometry join, output conflict checks, package writing, and summary generation.
  - Public interface for CLI and tests: `run_export(...) -> ExportSummary`.
- Create `scripts/reporting/export_2025_0m_country_nowcast_panel.py`
  - Thin argparse wrapper that bootstraps `src`, calls `run_export`, prints output paths, returns nonzero on validation errors.
- Create `tests/unit/test_nowcast_panel_export.py`
  - Unit tests for panel assembly, ISO3 filtering, duplicate-key failure, geometry join, and output conflict behavior.
- Create `tests/integration/test_export_2025_0m_country_nowcast_panel_cli.py`
  - CLI help and synthetic end-to-end export smoke test with a temporary GeoJSON spatial input.
- Generated during final verification only:
  - `results/exports/nowcast_panel_2025_0m_lso_nga_bfa/nowcast_panel_2025_0m_LSO_NGA_BFA.csv`
  - `results/exports/nowcast_panel_2025_0m_lso_nga_bfa/nowcast_admin_geometries_2025_0m_LSO_NGA_BFA.*`
  - `results/exports/nowcast_panel_2025_0m_lso_nga_bfa/export_validation_summary.json`

---

### Task 1: Core Panel Assembly

**Files:**
- Create: `src/ipcch/nowcast_panel_export.py`
- Test: `tests/unit/test_nowcast_panel_export.py`

**Interfaces:**
- Produces:
  - `class NowcastPanelExportError(Exception)`
  - `PANEL_COLUMNS: tuple[str, ...]`
  - `DEFAULT_COUNTRIES: tuple[str, ...]`
  - `SOURCE_EXPERIMENT: str`
  - `default_prediction_path() -> Path`
  - `default_country_lookup_path() -> Path`
  - `default_output_dir() -> Path`
  - `load_predictions(path: str | Path) -> pd.DataFrame`
  - `load_country_lookup(path: str | Path) -> pd.DataFrame`
  - `build_panel(predictions: pd.DataFrame, country_lookup: pd.DataFrame, countries: Sequence[str]) -> pd.DataFrame`
- Later tasks consume `build_panel()` and `NowcastPanelExportError`.

- [ ] **Step 1: Write failing unit tests for panel assembly**

Add this file:

```python
# tests/unit/test_nowcast_panel_export.py
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from shapely.geometry import box

geopandas = pytest.importorskip("geopandas")

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
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/unit/test_nowcast_panel_export.py -v
```

Expected: FAIL during import with `ModuleNotFoundError: No module named 'ipcch.nowcast_panel_export'`.

- [ ] **Step 3: Implement minimal core module**

Create `src/ipcch/nowcast_panel_export.py`:

```python
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
from ipcch.alert_risk_maps import load_spatial_boundaries, normalize_area_id, resolve_path


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
```

- [ ] **Step 4: Run unit tests for Task 1**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/unit/test_nowcast_panel_export.py -v
```

Expected: the four Task 1 tests pass. Later geometry/export tests are not present yet.

- [ ] **Step 5: Commit Task 1**

Run:

```bash
git add src/ipcch/nowcast_panel_export.py tests/unit/test_nowcast_panel_export.py
git commit -m "feat: assemble 2025 country nowcast panel"
```

---

### Task 2: Geometry Join and Package Writing

**Files:**
- Modify: `src/ipcch/nowcast_panel_export.py`
- Modify: `tests/unit/test_nowcast_panel_export.py`

**Interfaces:**
- Consumes:
  - `build_panel(predictions, country_lookup, countries) -> pd.DataFrame`
  - `NowcastPanelExportError`
- Produces:
  - `@dataclass ExportPaths`
  - `@dataclass ExportSummary`
  - `build_geometry_layer(panel: pd.DataFrame, spatial_path: str | Path) -> geopandas.GeoDataFrame`
  - `build_export_summary(...) -> ExportSummary`
  - `validate_output_conflicts(output_dir: str | Path, overwrite: bool) -> ExportPaths`
  - `write_export_package(panel, geometry, summary, paths) -> None`

- [ ] **Step 1: Add failing geometry and output tests**

Append to `tests/unit/test_nowcast_panel_export.py`:

```python
from ipcch.nowcast_panel_export import (
    GEOMETRY_BASENAME,
    PANEL_FILENAME,
    SUMMARY_FILENAME,
    build_geometry_layer,
    validate_output_conflicts,
    write_export_package,
    ExportSummary,
)


def write_spatial(path: Path, area_ids: list[str]) -> Path:
    gdf = geopandas.GeoDataFrame(
        {
            "area_id": area_ids,
            "geometry": [box(i, i, i + 1, i + 1) for i in range(len(area_ids))],
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
        {"area_id": ["10"], "iso3": ["LSO"], "country": ["Lesotho"], "n_months": [1], "min_date": ["2025-01-01"], "max_date": ["2025-01-01"], "geometry": [box(0, 0, 1, 1)]},
        crs="EPSG:4326",
    )
    paths = validate_output_conflicts(tmp_path / "export", overwrite=False)
    summary = ExportSummary(
        run_timestamp="2026-07-08T00:00:00+00:00",
        prediction_source="pred.csv",
        country_lookup_source="lookup.csv",
        spatial_source="spatial.geojson",
        output_paths={},
        countries=["LSO"],
        source_rows=1,
        panel_rows=1,
        admin_units=1,
        country_row_counts={"LSO": 1},
        country_admin_counts={"LSO": 1},
        month_row_counts={"2025-01": 1},
        geometry_rows=1,
        unmatched_geometry_area_ids=[],
        overwrite=False,
    )

    write_export_package(panel, geometry, summary, paths)

    assert (tmp_path / "export" / PANEL_FILENAME).exists()
    assert (tmp_path / "export" / f"{GEOMETRY_BASENAME}.shp").exists()
    assert (tmp_path / "export" / SUMMARY_FILENAME).exists()
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/unit/test_nowcast_panel_export.py -v
```

Expected: FAIL on missing imports such as `build_geometry_layer` or `ExportSummary`.

- [ ] **Step 3: Implement geometry and package writing**

Append/update `src/ipcch/nowcast_panel_export.py` with:

```python
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
    except Exception as exc:
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
```

- [ ] **Step 4: Run unit tests for Task 2**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/unit/test_nowcast_panel_export.py -v
```

Expected: all Task 1 and Task 2 tests pass.

- [ ] **Step 5: Commit Task 2**

Run:

```bash
git add src/ipcch/nowcast_panel_export.py tests/unit/test_nowcast_panel_export.py
git commit -m "feat: write nowcast panel shapefile package"
```

---

### Task 3: CLI and Synthetic Integration Smoke Test

**Files:**
- Modify: `src/ipcch/nowcast_panel_export.py`
- Create: `scripts/reporting/export_2025_0m_country_nowcast_panel.py`
- Create: `tests/integration/test_export_2025_0m_country_nowcast_panel_cli.py`

**Interfaces:**
- Consumes:
  - `load_predictions`, `load_country_lookup`, `build_panel`, `build_geometry_layer`, `build_export_summary`, `validate_output_conflicts`, `write_export_package`
- Produces:
  - `run_export(predictions_path=None, country_lookup_path=None, spatial_path=None, output_dir=None, countries=DEFAULT_COUNTRIES, overwrite=False) -> ExportSummary`
  - CLI flags: `--predictions`, `--country-lookup`, `--spatial-path`, `--output-dir`, `--countries`, `--overwrite`

- [ ] **Step 1: Add failing integration tests**

Create `tests/integration/test_export_2025_0m_country_nowcast_panel_cli.py`:

```python
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
```

- [ ] **Step 2: Run integration tests to verify they fail**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/integration/test_export_2025_0m_country_nowcast_panel_cli.py -v
```

Expected: FAIL because `scripts/reporting/export_2025_0m_country_nowcast_panel.py` does not exist.

- [ ] **Step 3: Add `run_export()` to the module**

Append to `src/ipcch/nowcast_panel_export.py`:

```python
def run_export(
    *,
    predictions_path: str | Path | None = None,
    country_lookup_path: str | Path | None = None,
    spatial_path: str | Path | None = None,
    output_dir: str | Path | None = None,
    countries: Sequence[str] = DEFAULT_COUNTRIES,
    overwrite: bool = False,
) -> ExportSummary:
    resolved_predictions = resolve_path(predictions_path or default_prediction_path())
    resolved_lookup = resolve_path(country_lookup_path or default_country_lookup_path())
    resolved_spatial = resolve_path(spatial_path or default_spatial_path())
    resolved_output = output_dir or default_output_dir()

    output_paths = validate_output_conflicts(resolved_output, overwrite=overwrite)
    predictions = load_predictions(resolved_predictions)
    lookup = load_country_lookup(resolved_lookup)
    panel = build_panel(predictions, lookup, countries)
    geometry = build_geometry_layer(panel, resolved_spatial)
    summary = build_export_summary(
        predictions=predictions,
        panel=panel,
        geometry=geometry,
        prediction_source=resolved_predictions,
        country_lookup_source=resolved_lookup,
        spatial_source=resolved_spatial,
        output_paths=output_paths,
        countries=countries,
        overwrite=overwrite,
    )
    write_export_package(panel, geometry, summary, output_paths)
    return summary
```

- [ ] **Step 4: Create the CLI wrapper**

Create `scripts/reporting/export_2025_0m_country_nowcast_panel.py`:

```python
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = next(path for path in Path(__file__).resolve().parents if (path / "src").exists())
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from ipcch.nowcast_panel_export import (
    DEFAULT_COUNTRIES,
    NowcastPanelExportError,
    default_country_lookup_path,
    default_output_dir,
    default_prediction_path,
    default_spatial_path,
    run_export,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export 2025 0m IPCCH nowcast panel data and companion admin shapefile.")
    parser.add_argument("--predictions", default=str(default_prediction_path()), help="2025 0m prediction CSV.")
    parser.add_argument("--country-lookup", default=str(default_country_lookup_path()), help="CSV mapping area_id to ISO3/country.")
    parser.add_argument("--spatial-path", default=str(default_spatial_path()), help="Admin geometry file with area_id geometries.")
    parser.add_argument("--output-dir", default=str(default_output_dir()), help="Directory for CSV, shapefile, and validation summary.")
    parser.add_argument("--countries", nargs="+", default=list(DEFAULT_COUNTRIES), help="ISO3 country codes to export.")
    parser.add_argument("--overwrite", action="store_true", help="Replace existing generated export package files.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        summary = run_export(
            predictions_path=args.predictions,
            country_lookup_path=args.country_lookup,
            spatial_path=args.spatial_path,
            output_dir=args.output_dir,
            countries=args.countries,
            overwrite=args.overwrite,
        )
    except NowcastPanelExportError as exc:
        print(f"Validation error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Unexpected error: {exc}", file=sys.stderr)
        return 1

    print("Exported 2025 0m IPCCH nowcast panel package.")
    for label, path in summary.output_paths.items():
        print(f"{label}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Run unit and integration tests**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/unit/test_nowcast_panel_export.py tests/integration/test_export_2025_0m_country_nowcast_panel_cli.py -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit Task 3**

Run:

```bash
git add src/ipcch/nowcast_panel_export.py scripts/reporting/export_2025_0m_country_nowcast_panel.py tests/unit/test_nowcast_panel_export.py tests/integration/test_export_2025_0m_country_nowcast_panel_cli.py
git commit -m "feat: add 2025 country nowcast export CLI"
```

---

### Task 4: Real Export and Acceptance Verification

**Files:**
- Generated, not source-controlled unless explicitly requested:
  - `results/exports/nowcast_panel_2025_0m_lso_nga_bfa/nowcast_panel_2025_0m_LSO_NGA_BFA.csv`
  - `results/exports/nowcast_panel_2025_0m_lso_nga_bfa/nowcast_admin_geometries_2025_0m_LSO_NGA_BFA.*`
  - `results/exports/nowcast_panel_2025_0m_lso_nga_bfa/export_validation_summary.json`

**Interfaces:**
- Consumes:
  - CLI from Task 3.
- Produces:
  - The requested CSV and shapefile package for Lesotho, Nigeria, and Burkina Faso.

- [ ] **Step 1: Run the real export**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/reporting/export_2025_0m_country_nowcast_panel.py --overwrite
```

Expected: exit code 0 and stdout listing `panel_csv`, `geometry_shp`, and `summary_json`.

- [ ] **Step 2: Validate the exported package with a direct check**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY'
import json
from pathlib import Path
import pandas as pd
import geopandas as gpd

root = Path("results/exports/nowcast_panel_2025_0m_lso_nga_bfa")
panel_path = root / "nowcast_panel_2025_0m_LSO_NGA_BFA.csv"
shape_path = root / "nowcast_admin_geometries_2025_0m_LSO_NGA_BFA.shp"
summary_path = root / "export_validation_summary.json"

panel = pd.read_csv(panel_path)
shape = gpd.read_file(shape_path)
summary = json.loads(summary_path.read_text(encoding="utf-8"))

assert set(panel["iso3"]) == {"LSO", "NGA", "BFA"}
assert set(panel["nowcast_scope"]) == {"0m"}
assert set(panel["test_year"]) == {2025}
assert set(panel["year"]) == {2025}
assert not panel.duplicated(["area_id", "year", "month"]).any()
assert set(panel["area_id"].astype(str)) == set(shape["area_id"].astype(str))
assert len(shape) == panel["area_id"].nunique()
assert summary["panel_rows"] == len(panel)
assert summary["geometry_rows"] == len(shape)
assert summary["admin_units"] == panel["area_id"].nunique()
print(f"panel_rows={len(panel)} admin_units={len(shape)} countries={sorted(panel['iso3'].unique())}")
PY
```

Expected: prints the real row/admin counts and exits 0.

- [ ] **Step 3: Run the focused automated test suite one more time**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/unit/test_nowcast_panel_export.py tests/integration/test_export_2025_0m_country_nowcast_panel_cli.py -v
```

Expected: all tests pass.

- [ ] **Step 4: Final status check**

Run:

```bash
git status --short
```

Expected: source changes are committed. Generated export files may be absent from status if ignored by `results/`; if they appear and the user did not request committing generated data, leave them uncommitted and report their paths.

---

## Plan Self-Review

- Spec coverage: Task 1 covers prediction/country loading, ISO3 filtering, panel schema, and duplicate `area_id x month` validation. Task 2 covers one-geometry-per-admin shapefile output, geometry join validation, output conflicts, and summary writing. Task 3 covers the required reporting CLI and synthetic end-to-end test. Task 4 covers the real requested deliverables and acceptance checks.
- Placeholder scan: no `TBD`, `TODO`, "implement later", or unspecified validation steps remain.
- Type consistency: `run_export()` returns `ExportSummary`; CLI prints `summary.output_paths`; `ExportPaths` path names match package writing and tests.
