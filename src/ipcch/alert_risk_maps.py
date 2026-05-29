from __future__ import annotations

import json
import math
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional, Sequence, Union

import pandas as pd

from ipcch import paths

YEAR = 2025
HORIZONS = ("0m", "3m", "6m")
SCOPES = ("global", "somalia")
ACTUAL_COLUMNS = ("area_id", "overall_phase", "overall_phase_pred")
TOP_RISK_COLUMNS = ("area_id", "phase3_worse", "phase3_pred")
TEMPORAL_COLUMNS = ("date", "year", "month")
COUNTRY_COLUMNS = ("country", "country_name", "country_en", "admin0", "ADMIN0", "adm0_name", "ADM0_NAME", "iso3", "ISO3", "country_code")
AREA_ID_ALIASES = ("area_id", "admin_code", "pcode", "PCODE", "admin_id", "ADM_ID")
NO_ALERT_COLOR = "#2ca02c"
ALERT_COLOR = "#d62728"
LATAM_COUNTRIES = {"guatemala", "haiti"}
AFRICA_MIN_X_M = -2_226_000.0
AFRICA_MIN_LON = -20.0


def _require_geopandas():
    try:
        import geopandas as gpd
    except ImportError as exc:
        raise AlertRiskMapError("geopandas is required for spatial boundary loading and map plotting") from exc
    return gpd


def _require_matplotlib():
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.colors import ListedColormap
        from matplotlib.patches import Patch
    except ImportError as exc:
        raise AlertRiskMapError("matplotlib is required for map plotting") from exc
    return plt, ListedColormap, Patch


def _optional_contextily():
    try:
        import contextily as ctx
    except ImportError:
        return None
    return ctx


class AlertRiskMapError(ValueError):
    pass


@dataclass(frozen=True)
class PredictionSelection:
    horizon: str
    scope: str
    path: Path
    explicit: bool
    rejected_somalia_local_candidates: tuple[str, ...] = ()


@dataclass
class HorizonDataset:
    horizon: str
    scope: str
    source_file: Path
    raw_2025_count: int
    retained_count: int
    duplicates_removed: int
    records: pd.DataFrame


@dataclass
class JoinValidation:
    horizon: str
    scope: str
    matched_count: int
    unmatched_area_ids: list[str]
    duplicate_join_area_ids: list[str]


@dataclass
class JoinedMapDataset:
    horizon: str
    scope: str
    source_file: Path
    joined_records: Any
    validation: JoinValidation


@dataclass(frozen=True)
class OutputPlan:
    report_dir: Path
    results_dir: Path
    figure_format: str
    figures: Mapping[str, Path]
    validation_summary: Path


@dataclass
class ValidationSummary:
    selected_files: dict[str, str] = field(default_factory=dict)
    record_counts: dict[str, dict[str, int]] = field(default_factory=dict)
    join_counts: dict[str, dict[str, Any]] = field(default_factory=dict)
    somalia_local_rejections: list[str] = field(default_factory=list)
    output_paths: dict[str, str] = field(default_factory=dict)
    status: str = "planned"
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def default_prediction_root() -> Path:
    return paths.RESULTS_DIR / "experiments" / "deep_feature_weight_decay_forecasting"


def default_report_dir() -> Path:
    return paths.REPORTS_DIR / "deep_feature_weight_decay_forecasting" / "alert_risk_maps"


def default_results_dir() -> Path:
    return paths.RESULTS_DIR / "experiments" / "deep_feature_weight_decay_forecasting" / "alert_risk_maps"


def default_spatial_path() -> Optional[Path]:
    try:
        return paths.external_path("ipcch_admin_geometry")
    except KeyError:
        candidate = paths.SOURCE_DATA_DIR / "assembled_IPCCH" / "spatial" / "ipcch_admin_geometry.shp"
        return candidate


def default_country_lookup_path() -> Path:
    return paths.SOURCE_DATA_DIR / "assembled_IPCCH" / "country_area_id_lookup.csv"


def resolve_path(path: Union[str, Path]) -> Path:
    return Path(path).expanduser().resolve()


def ensure_under(path: Path, root: Path, label: str) -> None:
    resolved = path.resolve()
    root_resolved = root.resolve()
    try:
        resolved.relative_to(root_resolved)
    except ValueError as exc:
        raise AlertRiskMapError(f"{label} path must resolve under {root_resolved}: {resolved}") from exc


def build_output_plan(out_report_dir: Optional[Union[str, Path]], out_results_dir: Optional[Union[str, Path]], figure_format: str, scope: str, filename_suffix: str = "") -> OutputPlan:
    report_dir = resolve_path(out_report_dir or default_report_dir())
    results_dir = resolve_path(out_results_dir or default_results_dir())
    ensure_under(report_dir, paths.REPORTS_DIR, "Report output")
    ensure_under(results_dir, paths.RESULTS_DIR, "Results output")
    fmt = figure_format.lower().lstrip(".")
    suffix = filename_suffix
    scope_label = scope.lower()
    figures = {
        "actual_vs_predicted": report_dir / f"ipcch_2025_{scope_label}_0m-3m-6m_actual_vs_predicted_alert_map{suffix}.{fmt}",
        "top_risk": report_dir / f"ipcch_2025_{scope_label}_0m_top30_phase3_risk_comparison_map{suffix}.{fmt}",
    }
    validation_summary = results_dir / f"ipcch_2025_{scope_label}_alert_risk_maps_validation_summary.json"
    return OutputPlan(report_dir, results_dir, fmt, figures, validation_summary)


def validate_output_conflicts(plan: OutputPlan, overwrite: bool, write_validation_summary: bool = True) -> None:
    targets = list(plan.figures.values())
    if write_validation_summary:
        targets.append(plan.validation_summary)
    conflicts = [path for path in targets if path.exists()]
    if conflicts and not overwrite:
        joined = ", ".join(str(path) for path in conflicts)
        raise AlertRiskMapError(f"Existing output file conflict without --overwrite: {joined}")


def _prediction_files(root: Path) -> list[Path]:
    if not root.exists():
        raise AlertRiskMapError(f"Prediction root does not exist: {root}")
    return sorted(path for path in root.rglob("*.csv") if "prediction" in path.name.lower() or "prediction" in str(path.parent).lower())


def _is_somalia_local(path: Path) -> bool:
    text = str(path).lower().replace("\\", "/")
    return "somalia-local" in text or "somalia_local" in text or "/somalia/" in text or "local_somalia" in text


def _is_somalia_global_grouping(path: Path) -> bool:
    text = str(path).lower().replace("\\", "/")
    return "somalia" in text and not _is_somalia_local(path)


def _matches_horizon(path: Path, horizon: str) -> bool:
    text = str(path).lower().replace("\\", "/")
    token = re.escape(horizon.lower())
    return bool(re.search(rf"(^|[/_\-]){token}($|[/_\-])", text))


def discover_prediction_file(root: Union[str, Path], horizon: str, scope: str, explicit_file: Optional[Union[str, Path]] = None) -> PredictionSelection:
    if horizon not in HORIZONS:
        raise AlertRiskMapError(f"Unsupported horizon {horizon}; expected one of {HORIZONS}")
    if explicit_file:
        path = resolve_path(explicit_file)
        if not path.exists():
            raise AlertRiskMapError(f"Explicit {scope} {horizon} prediction file does not exist: {path}")
        return PredictionSelection(horizon, scope, path, True, ())

    prediction_root = resolve_path(root)
    candidates = [path for path in _prediction_files(prediction_root) if _matches_horizon(path, horizon)]
    candidates = [path for path in candidates if "somalia" not in str(path).lower()]
    if not candidates:
        raise AlertRiskMapError(f"No global prediction candidates found for horizon {horizon} under {prediction_root}")
    if len(candidates) > 1:
        sample = ", ".join(str(path) for path in candidates[:5])
        raise AlertRiskMapError(f"Ambiguous global prediction candidates for horizon {horizon}; provide an explicit file. Candidates: {sample}")
    return PredictionSelection(horizon, scope, candidates[0], False, ())


def validate_required_columns(df: pd.DataFrame, required: Iterable[str], source_file: Path, horizon: str, scope: str) -> None:
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise AlertRiskMapError(f"Missing required prediction columns for {scope} {horizon} in {source_file}: {missing}")
    all_null = [column for column in required if df[column].isna().all()]
    if all_null:
        raise AlertRiskMapError(f"All-null required prediction columns for {scope} {horizon} in {source_file}: {all_null}")


def add_temporal_date(df: pd.DataFrame, source_file: Path, horizon: str, scope: str) -> pd.DataFrame:
    df = df.copy()
    if "date" in df.columns:
        df["_record_date"] = pd.to_datetime(df["date"], errors="coerce")
    elif {"year", "month"}.issubset(df.columns):
        df["_record_date"] = pd.to_datetime(
            {"year": pd.to_numeric(df["year"], errors="coerce"), "month": pd.to_numeric(df["month"], errors="coerce"), "day": 1},
            errors="coerce",
        )
    else:
        raise AlertRiskMapError(f"Missing temporal field for {scope} {horizon} in {source_file}; expected date or year plus month")
    if df["_record_date"].isna().all():
        raise AlertRiskMapError(f"No usable temporal values for {scope} {horizon} in {source_file}")
    df["_record_year"] = df["_record_date"].dt.year
    return df


def normalize_area_id(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip()


def filter_latest_2025(df: pd.DataFrame, source_file: Path, horizon: str, scope: str, min_record_date: Optional[pd.Timestamp] = None) -> tuple[pd.DataFrame, int, int]:
    df = add_temporal_date(df, source_file, horizon, scope)
    df = df[df["_record_year"].eq(YEAR)].copy()
    raw_count = len(df)
    if df.empty:
        raise AlertRiskMapError(f"No 2025 records for {scope} {horizon} in {source_file}")
    df["area_id"] = normalize_area_id(df["area_id"])
    retained_parts: list[pd.DataFrame] = []
    duplicate_removed = 0
    for area_id, group in df.groupby("area_id", sort=False, dropna=False):
        latest = group[group["_record_date"].eq(group["_record_date"].max())].copy()
        comparable = latest.drop(columns=[col for col in ["_record_date", "_record_year"] if col in latest.columns])
        exact = comparable.drop_duplicates()
        if len(exact) > 1:
            raise AlertRiskMapError(f"Conflicting duplicate latest records for {scope} {horizon} area_id {area_id} in {source_file}")
        retained_parts.append(latest.iloc[[0]])
        duplicate_removed += len(group) - 1
    retained = pd.concat(retained_parts, ignore_index=True)
    if min_record_date is not None:
        retained = retained[retained["_record_date"].ge(min_record_date)].copy()
        if retained.empty:
            raise AlertRiskMapError(f"No 2025 records on or after {min_record_date.date()} for {scope} {horizon} in {source_file}")
    return retained, raw_count, duplicate_removed


def load_prediction_dataset(
    source_file: Union[str, Path],
    horizon: str,
    scope: str,
    mode: str,
    min_record_date: Optional[Union[str, pd.Timestamp]] = None,
    predicted_alert_threshold: Optional[float] = None,
    actual_alert_threshold: Optional[float] = None,
) -> HorizonDataset:
    path = resolve_path(source_file)
    if not path.exists():
        raise AlertRiskMapError(f"Prediction file does not exist for {scope} {horizon}: {path}")
    df = pd.read_csv(path)
    required = ACTUAL_COLUMNS if mode == "actual" else TOP_RISK_COLUMNS
    if mode == "actual" and predicted_alert_threshold is not None:
        required = tuple(dict.fromkeys(required + ("phase3_pred",)))
    if mode == "actual" and actual_alert_threshold is not None:
        required = tuple(dict.fromkeys(required + ("phase3_worse",)))
    validate_required_columns(df, required, path, horizon, scope)
    min_date = pd.Timestamp(min_record_date) if min_record_date is not None else None
    filtered, raw_count, duplicates_removed = filter_latest_2025(df, path, horizon, scope, min_date)
    if mode == "actual":
        for column in ["overall_phase", "overall_phase_pred"]:
            filtered[column] = pd.to_numeric(filtered[column], errors="coerce")
            if filtered[column].isna().any():
                raise AlertRiskMapError(f"Non-numeric or missing column {column} for {scope} {horizon} in {path}")
        if actual_alert_threshold is None:
            filtered["actual_alert"] = filtered["overall_phase"].ge(3)
        else:
            filtered["phase3_worse"] = pd.to_numeric(filtered["phase3_worse"], errors="coerce")
            if filtered["phase3_worse"].isna().any():
                raise AlertRiskMapError(f"Non-numeric or missing column phase3_worse for {scope} {horizon} in {path}")
            filtered["actual_alert"] = filtered["phase3_worse"].ge(actual_alert_threshold)
        if predicted_alert_threshold is None:
            filtered["predicted_alert"] = filtered["overall_phase_pred"].ge(3)
        else:
            filtered["phase3_pred"] = pd.to_numeric(filtered["phase3_pred"], errors="coerce")
            if filtered["phase3_pred"].isna().any():
                raise AlertRiskMapError(f"Non-numeric or missing column phase3_pred for {scope} {horizon} in {path}")
            filtered["predicted_alert"] = filtered["phase3_pred"].ge(predicted_alert_threshold)
    elif mode == "top_risk":
        for column in ["phase3_worse", "phase3_pred"]:
            filtered[column] = pd.to_numeric(filtered[column], errors="coerce")
            if filtered[column].isna().any():
                raise AlertRiskMapError(f"Non-numeric or missing column {column} for {scope} {horizon} in {path}")
    else:
        raise AlertRiskMapError(f"Unsupported mode {mode}")
    retained_count = len(filtered)
    if retained_count != filtered["area_id"].nunique():
        raise AlertRiskMapError(f"Duplicate retained area_id records for {scope} {horizon} in {path}")
    return HorizonDataset(horizon, scope, path, raw_count, retained_count, duplicates_removed, filtered)


def load_spatial_boundaries(spatial_path: Union[str, Path]) -> Any:
    path = resolve_path(spatial_path)
    if not path.exists():
        raise AlertRiskMapError(f"Spatial boundary file does not exist: {path}")
    gpd = _require_geopandas()
    gdf = gpd.read_file(path)
    area_column = next((column for column in AREA_ID_ALIASES if column in gdf.columns), None)
    if area_column is None:
        raise AlertRiskMapError(f"Spatial boundary file missing area_id or documented equivalent column: {path}")
    if area_column != "area_id":
        gdf = gdf.rename(columns={area_column: "area_id"})
    if "geometry" not in gdf.columns:
        raise AlertRiskMapError(f"Spatial boundary file missing geometry column: {path}")
    gdf = gdf.dropna(subset=["area_id", "geometry"]).copy()
    gdf["area_id"] = normalize_area_id(gdf["area_id"])
    if not gdf.geometry.is_valid.all():
        repaired = gdf.copy()
        repaired["geometry"] = repaired.geometry.buffer(0)
        if not repaired.geometry.is_valid.all():
            raise AlertRiskMapError(f"Spatial boundary file contains invalid geometries that could not be repaired: {path}")
        gdf = repaired
    duplicates = sorted(gdf.loc[gdf["area_id"].duplicated(), "area_id"].unique().tolist())
    if duplicates:
        raise AlertRiskMapError(f"Spatial boundary file has duplicate area_id values: {duplicates[:10]}")
    return gdf


def load_country_area_lookup(country_lookup_path: Union[str, Path]) -> pd.DataFrame:
    path = resolve_path(country_lookup_path)
    if not path.exists():
        raise AlertRiskMapError(f"Country area lookup file does not exist: {path}")
    lookup = pd.read_csv(path, usecols=["area_id", "iso3"])
    validate_required_columns(lookup, ("area_id", "iso3"), path, "lookup", "country")
    lookup = lookup.dropna(subset=["area_id", "iso3"]).copy()
    lookup["area_id"] = normalize_area_id(lookup["area_id"])
    lookup["iso3"] = lookup["iso3"].astype(str).str.strip().str.upper()
    return lookup.drop_duplicates(["area_id", "iso3"])


def country_area_ids(country_lookup: pd.DataFrame, iso3: str) -> set[str]:
    code = iso3.upper()
    area_ids = set(country_lookup.loc[country_lookup["iso3"].eq(code), "area_id"])
    if not area_ids:
        raise AlertRiskMapError(f"No area_id records found for ISO3 scope {code} in country lookup")
    return area_ids


def filter_to_area_ids(df: Any, area_ids: set[str], label: str, scope: str) -> Any:
    filtered = df[df["area_id"].astype(str).isin(area_ids)].copy()
    if filtered.empty:
        raise AlertRiskMapError(f"No {label} rows remain for ISO3 scope {scope}")
    return filtered


def join_predictions_to_spatial(dataset: HorizonDataset, boundaries: Any, area_ids: Optional[set[str]] = None) -> JoinedMapDataset:
    prediction = dataset.records.copy()
    prediction["area_id"] = normalize_area_id(prediction["area_id"])
    spatial = boundaries
    if area_ids is not None:
        prediction = filter_to_area_ids(prediction, area_ids, "prediction", dataset.scope)
        spatial = filter_to_area_ids(spatial, area_ids, "spatial boundary", dataset.scope)
    joined = spatial.merge(prediction, on="area_id", how="right", indicator=True)
    unmatched = sorted(joined.loc[joined["_merge"].ne("both"), "area_id"].astype(str).unique().tolist())
    duplicates = sorted(joined.loc[joined["area_id"].duplicated(), "area_id"].astype(str).unique().tolist())
    validation = JoinValidation(dataset.horizon, dataset.scope, int(joined["_merge"].eq("both").sum()), unmatched, duplicates)
    if unmatched:
        raise AlertRiskMapError(f"Spatial join failed for {dataset.scope} {dataset.horizon}; unmatched area_id sample: {unmatched[:10]}")
    if duplicates:
        raise AlertRiskMapError(f"Spatial join duplicated area_id values for {dataset.scope} {dataset.horizon}: {duplicates[:10]}")
    joined = joined.drop(columns=["_merge"])
    gpd = _require_geopandas()
    joined = gpd.GeoDataFrame(joined, geometry="geometry", crs=spatial.crs)
    return JoinedMapDataset(dataset.horizon, dataset.scope, dataset.source_file, joined, validation)


def compute_top_risk_categories(df: pd.DataFrame, top_fraction: float = 0.30) -> pd.DataFrame:
    if df.empty:
        raise AlertRiskMapError("Cannot compute top-risk categories for an empty dataset")
    output = df.copy()
    n_top = max(1, math.ceil(len(output) * top_fraction))
    actual_top = set(output.nlargest(n_top, "phase3_worse")["area_id"].astype(str))
    predicted_top = set(output.nlargest(n_top, "phase3_pred")["area_id"].astype(str))

    def category(area_id: Any) -> str:
        key = str(area_id)
        actual = key in actual_top
        predicted = key in predicted_top
        if actual and predicted:
            return "both"
        if actual:
            return "actual_only"
        if predicted:
            return "predicted_only"
        return "background"

    output["actual_top_risk"] = output["area_id"].astype(str).isin(actual_top)
    output["predicted_top_risk"] = output["area_id"].astype(str).isin(predicted_top)
    output["risk_category"] = output["area_id"].map(category)
    return output


def _latam_mask(gdf: Any) -> pd.Series:
    mask = pd.Series(False, index=gdf.index)
    for column in COUNTRY_COLUMNS:
        if column in gdf.columns:
            mask |= gdf[column].astype(str).str.strip().str.lower().isin(LATAM_COUNTRIES)
    if not mask.any():
        source = gdf.to_crs(epsg=4326) if getattr(gdf, "crs", None) is not None and str(gdf.crs).upper() != "EPSG:4326" else gdf
        mask = source.geometry.bounds["maxx"].lt(AFRICA_MIN_LON)
    return mask


def _add_latam_inset(parent_ax: Any, latam_gdf: Any, column: str, listed_cmap: Any) -> None:
    if latam_gdf.empty:
        return
    inset = parent_ax.inset_axes([0.67, 0.09, 0.30, 0.28])
    _plot_binary_layer(latam_gdf, column, inset, listed_cmap)
    minx, miny, maxx, maxy = latam_gdf.total_bounds
    pad_x = (maxx - minx) * 0.05 if maxx > minx else 1
    pad_y = (maxy - miny) * 0.12 if maxy > miny else 1
    inset.set_xlim(minx - pad_x, maxx + pad_x)
    inset.set_ylim(miny - pad_y, maxy + pad_y)
    inset.set_xticks([])
    inset.set_yticks([])
    for spine in inset.spines.values():
        spine.set_edgecolor("0.35")
        spine.set_linewidth(0.9)
    inset.set_title("Latin America", fontsize=7, pad=1.5)
    inset.patch.set_facecolor("white")
    inset.patch.set_alpha(0.92)


def _plot_binary_layer(gdf: Any, column: str, ax: Any, listed_cmap: Any) -> None:
    if gdf.empty:
        return
    plot_gdf = gdf.copy()
    plot_gdf["_binary_code"] = plot_gdf[column].astype(bool).astype(int)
    cmap = listed_cmap([NO_ALERT_COLOR, ALERT_COLOR])
    plot_gdf.plot(column="_binary_code", cmap=cmap, linewidth=0.15, edgecolor="white", ax=ax, vmin=0, vmax=1)


def _set_padded_extent(ax: Any, gdf: Any, x_pad_fraction: float = 0.03, y_pad_fraction: float = 0.03) -> None:
    if gdf.empty:
        return
    minx, miny, maxx, maxy = gdf.total_bounds
    pad_x = (maxx - minx) * x_pad_fraction if maxx > minx else 1
    pad_y = (maxy - miny) * y_pad_fraction if maxy > miny else 1
    ax.set_xlim(minx - pad_x, maxx + pad_x)
    ax.set_ylim(miny - pad_y, maxy + pad_y)


def _add_basemap(ax: Any, ctx: Any) -> None:
    if ctx is None:
        return
    try:
        ctx.add_basemap(ax, source=ctx.providers.CartoDB.Positron, attribution=False, alpha=0.4)
    except Exception:
        return


def _add_binary_stats(ax: Any, gdf: Any, column: str) -> None:
    if gdf.empty:
        text = "No data available"
    else:
        values = gdf[column].astype(bool)
        n_positive = int(values.sum())
        n_total = int(values.notna().sum())
        pct_positive = n_positive / n_total * 100 if n_total else 0.0
        text = f"Alert: {n_positive:,}/{n_total:,} ({pct_positive:.1f}%)"
    ax.text(
        0.98,
        0.02,
        text,
        transform=ax.transAxes,
        fontsize=8.5,
        verticalalignment="bottom",
        horizontalalignment="right",
        bbox={"boxstyle": "round", "facecolor": "white", "alpha": 0.85, "edgecolor": "0.6"},
    )


def _plot_boolean_map(gdf: Any, column: str, ax: Any, title: str, listed_cmap: Any, use_latam_thumbnail: bool, no_basemap: bool) -> None:
    plot_gdf = gdf.copy()
    latam_gdf = plot_gdf.iloc[0:0]
    if use_latam_thumbnail:
        latam = _latam_mask(plot_gdf)
        latam_gdf = plot_gdf[latam].copy()
        plot_gdf = plot_gdf[~latam].copy()
    latam_inset_gdf = latam_gdf.to_crs(epsg=4326) if not latam_gdf.empty and getattr(latam_gdf, "crs", None) is not None else latam_gdf
    ctx = None if no_basemap else _optional_contextily()
    if ctx is not None and getattr(plot_gdf, "crs", None) is not None:
        plot_gdf = plot_gdf.to_crs(epsg=3857)
        main_extent_gdf = plot_gdf[plot_gdf.geometry.centroid.x.ge(AFRICA_MIN_X_M)].copy()
    elif use_latam_thumbnail:
        extent_source = plot_gdf.to_crs(epsg=4326) if getattr(plot_gdf, "crs", None) is not None else plot_gdf
        main_extent_gdf = plot_gdf[extent_source.geometry.bounds["minx"].ge(AFRICA_MIN_LON)].copy()
    else:
        main_extent_gdf = plot_gdf
    _plot_binary_layer(plot_gdf, column, ax, listed_cmap)
    _set_padded_extent(ax, main_extent_gdf if not main_extent_gdf.empty else plot_gdf)
    _add_basemap(ax, ctx)
    _add_binary_stats(ax, plot_gdf, column)
    _add_latam_inset(ax, latam_inset_gdf, column, listed_cmap)
    ax.set_title(title, fontsize=12, weight="bold", pad=6)
    ax.set_axis_off()


def plot_actual_vs_predicted(datasets: Sequence[JoinedMapDataset], output_path: Union[str, Path], scope: str, no_basemap: bool = False) -> None:
    by_horizon = {dataset.horizon: dataset.joined_records for dataset in datasets}
    plt, listed_cmap, patch = _require_matplotlib()
    use_latam_thumbnail = scope == "global"
    if len(datasets) == 1:
        horizon = datasets[0].horizon
        fig, axes = plt.subplots(1, 2, figsize=(10, 5))
        _plot_boolean_map(by_horizon[horizon], "actual_alert", axes[0], f"{horizon} actual: phase >= 3", listed_cmap, use_latam_thumbnail, no_basemap)
        _plot_boolean_map(by_horizon[horizon], "predicted_alert", axes[1], f"{horizon} predicted: phase >= 3", listed_cmap, use_latam_thumbnail, no_basemap)
        fig.subplots_adjust(left=0.03, right=0.99, bottom=0.12, top=0.84, wspace=0.08)
    else:
        missing = [horizon for horizon in HORIZONS if horizon not in by_horizon]
        if missing:
            raise AlertRiskMapError(f"Missing horizons for {scope} actual-vs-predicted figure: {missing}")
        fig, axes = plt.subplots(2, 3, figsize=(15, 9))
        for col, horizon in enumerate(HORIZONS):
            _plot_boolean_map(by_horizon[horizon], "actual_alert", axes[0, col], f"{horizon} actual: phase >= 3", listed_cmap, use_latam_thumbnail, no_basemap)
            _plot_boolean_map(by_horizon[horizon], "predicted_alert", axes[1, col], f"{horizon} predicted: phase >= 3", listed_cmap, use_latam_thumbnail, no_basemap)
        fig.subplots_adjust(left=0.03, right=0.99, bottom=0.08, top=0.90, wspace=0.08, hspace=0.22)
    handles = [patch(color=NO_ALERT_COLOR, label="No alert"), patch(color=ALERT_COLOR, label="Alert")]
    fig.legend(handles=handles, loc="lower center", ncol=2)
    fig.suptitle(f"IPCCH 2025 {scope.title()} Actual vs Predicted Alert Map")
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=300)
    plt.close(fig)


def plot_top_risk(gdf: Any, output_path: Union[str, Path], scope: str, no_basemap: bool = False) -> None:
    plt, listed_cmap, patch = _require_matplotlib()
    fig, axes = plt.subplots(2, 1, figsize=(10, 12))
    use_latam_thumbnail = scope == "global"
    _plot_boolean_map(gdf, "actual_top_risk", axes[0], "Actual top 30% by phase3_worse", listed_cmap, use_latam_thumbnail, no_basemap)
    _plot_boolean_map(gdf, "predicted_top_risk", axes[1], "Predicted top 30% by phase3_pred", listed_cmap, use_latam_thumbnail, no_basemap)
    handles = [patch(color=NO_ALERT_COLOR, label="Not top 30%"), patch(color=ALERT_COLOR, label="Top 30%")]
    fig.legend(handles=handles, loc="lower center", ncol=2)
    fig.suptitle(f"IPCCH 2025 {scope.title()} Top 30% Phase 3+ Risk Comparison")
    fig.subplots_adjust(left=0.08, right=0.96, bottom=0.08, top=0.92, hspace=0.28)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=300)
    plt.close(fig)


def write_validation_summary(summary: ValidationSummary, path: Union[str, Path], overwrite: bool) -> None:
    output = Path(path)
    if output.exists() and not overwrite:
        raise AlertRiskMapError(f"Existing validation summary conflict without --overwrite: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary.to_dict(), indent=2, sort_keys=True), encoding="utf-8")


def run_alert_risk_maps(
    prediction_root: Optional[Union[str, Path]] = None,
    spatial_path: Optional[Union[str, Path]] = None,
    out_report_dir: Optional[Union[str, Path]] = None,
    out_results_dir: Optional[Union[str, Path]] = None,
    horizon_files: Optional[Mapping[str, Optional[Union[str, Path]]]] = None,
    somalia_horizon_files: Optional[Mapping[str, Optional[Union[str, Path]]]] = None,
    country_lookup_path: Optional[Union[str, Path]] = None,
    overwrite: bool = False,
    write_summary: bool = True,
    no_basemap: bool = False,
    figure_format: str = "png",
    scope: str = "global",
    scopes: Optional[Sequence[str]] = None,
    min_record_date: Optional[Union[str, pd.Timestamp]] = None,
    predicted_alert_threshold: Optional[float] = None,
    actual_alert_threshold: Optional[float] = None,
    filename_suffix: str = "",
) -> ValidationSummary:
    root = resolve_path(prediction_root or default_prediction_root())
    spatial = resolve_path(spatial_path or default_spatial_path())
    selected_scope = (tuple(scopes)[0] if scopes else scope).strip().upper()
    if selected_scope == "GLOBAL":
        selected_scope = "global"
    plan = build_output_plan(out_report_dir, out_results_dir, figure_format, selected_scope, filename_suffix)
    summary = ValidationSummary(output_paths={key: str(value) for key, value in plan.figures.items()} | {"validation_summary": str(plan.validation_summary)})
    try:
        validate_output_conflicts(plan, overwrite, write_summary)
        boundaries = load_spatial_boundaries(spatial)
        summary.selected_files["spatial"] = str(spatial)
        horizon_files = horizon_files or {}
        country_area_filter = None
        if selected_scope != "global":
            country_lookup_file = resolve_path(country_lookup_path or default_country_lookup_path())
            country_lookup = load_country_area_lookup(country_lookup_file)
            country_area_filter = country_area_ids(country_lookup, selected_scope)
            summary.selected_files["country_lookup"] = str(country_lookup_file)
        actual_joined: list[JoinedMapDataset] = []
        top_joined: Optional[JoinedMapDataset] = None
        for horizon in HORIZONS:
            selection = discover_prediction_file(root, horizon, selected_scope, horizon_files.get(horizon))
            key = f"{selected_scope}_{horizon}"
            summary.selected_files[key] = str(selection.path)
            dataset = load_prediction_dataset(selection.path, horizon, selected_scope, "actual", min_record_date, predicted_alert_threshold, actual_alert_threshold)
            joined = join_predictions_to_spatial(dataset, boundaries, country_area_filter)
            actual_joined.append(joined)
            summary.record_counts[key] = {
                "raw_2025_count": dataset.raw_2025_count,
                "retained_count": dataset.retained_count,
                "duplicates_removed": dataset.duplicates_removed,
            }
            summary.join_counts[key] = {
                "matched_count": joined.validation.matched_count,
                "unmatched_area_ids": joined.validation.unmatched_area_ids,
                "duplicate_join_area_ids": joined.validation.duplicate_join_area_ids,
            }
            if horizon == "0m":
                top_dataset = load_prediction_dataset(selection.path, horizon, selected_scope, "top_risk", min_record_date)
                top_dataset.records = compute_top_risk_categories(top_dataset.records)
                top_joined = join_predictions_to_spatial(top_dataset, boundaries, country_area_filter)
        if top_joined is None:
            raise AlertRiskMapError("Missing 0m top-risk dataset")
        plot_actual_vs_predicted(actual_joined, plan.figures["actual_vs_predicted"], selected_scope, no_basemap)
        plot_top_risk(top_joined.joined_records, plan.figures["top_risk"], selected_scope, no_basemap)
        summary.status = "success"
        if write_summary:
            write_validation_summary(summary, plan.validation_summary, overwrite)
        return summary
    except Exception as exc:
        summary.status = "failure"
        summary.errors.append(str(exc))
        raise
