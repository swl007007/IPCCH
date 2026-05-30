"""Two-panel April 2026 actual-vs-predicted global crisis map.

Reuses the ``ipcch.alert_risk_maps`` guardrails (alert/no-alert colors, Latin
America inset, binary layer, no-basemap, ensure_under) but provides a
launch-specific spatial join that RECORDS unmatched area_id values and renders
the matched subset, while hard-failing on duplicate spatial keys (spec FR-024..
FR-028, R8/R9). This does not alter the existing six-panel/top-risk behavior.

Top panel: April 2026 actual crisis (overall_phase >= 3) on the actual-covered
subset. Bottom panel: April 2026 predicted crisis (overall_phase_pred >= 3) on
all eligible predicted areas. Coverage may differ; the figure states this.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, List, Optional

import pandas as pd

from ipcch import paths
from ipcch import alert_risk_maps as arm


class LaunchMapError(ValueError):
    pass


@dataclass
class TwoPanelJoin:
    boundaries: Any  # GeoDataFrame
    actual_joined: Any  # GeoDataFrame (matched actual-covered subset)
    predicted_joined: Any  # GeoDataFrame (matched predicted subset)
    unmatched_actual: List[str]
    unmatched_prediction: List[str]
    duplicate_spatial_keys: List[str]
    mapped_actual_count: int
    mapped_predicted_count: int


@dataclass
class MapValidationSummary:
    actual_source: str
    prediction_source: str
    spatial_boundary_source: str
    actual_month: str = "2026-04"
    prediction_month: str = "2026-04"
    predicted_area_count: int = 0
    april_actual_covered_area_count: int = 0
    mapped_predicted_count: int = 0
    mapped_actual_count: int = 0
    unmatched_prediction_area_ids: List[str] = field(default_factory=list)
    unmatched_actual_area_ids: List[str] = field(default_factory=list)
    duplicate_spatial_keys: List[str] = field(default_factory=list)
    output_path: str = ""
    status: str = "planned"

    def to_dict(self) -> dict:
        return asdict(self)


def join_for_two_panel(
    predictions: pd.DataFrame, april_actuals: pd.DataFrame, boundaries: Any
) -> TwoPanelJoin:
    """Recording spatial join (FR-027, R8): record unmatched, hard-fail on duplicate keys."""
    gpd = arm._require_geopandas()
    spatial = boundaries.copy()
    spatial["area_id"] = arm.normalize_area_id(spatial["area_id"])
    # Duplicate spatial keys are a hard failure BEFORE rendering.
    dup_keys = sorted(spatial.loc[spatial["area_id"].duplicated(), "area_id"].astype(str).unique().tolist())
    if dup_keys:
        raise LaunchMapError(f"Duplicate spatial join keys in boundaries (hard failure): {dup_keys[:10]}")

    pred = predictions.copy()
    pred["area_id"] = arm.normalize_area_id(pred["area_id"])
    pred_ids = set(pred["area_id"])
    boundary_ids = set(spatial["area_id"])

    pred_join = spatial.merge(pred, on="area_id", how="inner")
    pred_join = gpd.GeoDataFrame(pred_join, geometry="geometry", crs=spatial.crs)
    unmatched_prediction = sorted(pred_ids - boundary_ids)

    actual_joined = spatial.iloc[0:0]
    unmatched_actual: List[str] = []
    mapped_actual_count = 0
    if april_actuals is not None and len(april_actuals):
        act = april_actuals.copy()
        act["area_id"] = arm.normalize_area_id(act["area_id"])
        act_ids = set(act["area_id"])
        act_join = spatial.merge(act, on="area_id", how="inner")
        actual_joined = gpd.GeoDataFrame(act_join, geometry="geometry", crs=spatial.crs)
        unmatched_actual = sorted(act_ids - boundary_ids)
        mapped_actual_count = int(actual_joined["area_id"].nunique())

    return TwoPanelJoin(
        boundaries=spatial,
        actual_joined=actual_joined,
        predicted_joined=pred_join,
        unmatched_actual=unmatched_actual,
        unmatched_prediction=unmatched_prediction,
        duplicate_spatial_keys=[],  # always empty on success (duplicates hard-fail above)
        mapped_actual_count=mapped_actual_count,
        mapped_predicted_count=int(pred_join["area_id"].nunique()),
    )


def _ensure_crisis_columns(join: TwoPanelJoin) -> None:
    if len(join.predicted_joined):
        join.predicted_joined["predicted_crisis"] = (
            pd.to_numeric(join.predicted_joined["overall_phase_pred"], errors="coerce") >= 3
        )
    if len(join.actual_joined):
        if "actual_crisis" in join.actual_joined.columns:
            join.actual_joined["actual_crisis"] = join.actual_joined["actual_crisis"].astype(bool)
        elif "overall_phase" in join.actual_joined.columns:
            join.actual_joined["actual_crisis"] = pd.to_numeric(join.actual_joined["overall_phase"], errors="coerce") >= 3
        elif "actual_overall_phase" in join.actual_joined.columns:
            join.actual_joined["actual_crisis"] = pd.to_numeric(join.actual_joined["actual_overall_phase"], errors="coerce") >= 3


def plot_predicted_only(
    join: TwoPanelJoin, output_path: Path, scope: str = "global", no_basemap: bool = False,
) -> None:
    plt, listed_cmap, patch = arm._require_matplotlib()
    _ensure_crisis_columns(join)
    fig, ax = plt.subplots(1, 1, figsize=(10, 7))
    use_latam = scope == "global"
    _panel(
        ax,
        join.predicted_joined,
        "predicted_crisis",
        f"Predicted crisis (phase >= 3) — all eligible predicted areas (n={join.mapped_predicted_count})",
        listed_cmap,
        use_latam,
        no_basemap,
    )
    handles = [patch(color=arm.NO_ALERT_COLOR, label="No crisis (phase 1-2)"), patch(color=arm.ALERT_COLOR, label="Crisis (phase 3+)")]
    fig.legend(handles=handles, loc="lower center", ncol=2)
    fig.suptitle("IPCCH Forecast Crisis Map\nTarget-period actuals unavailable; predicted-only view.", fontsize=12)
    fig.subplots_adjust(left=0.04, right=0.97, bottom=0.10, top=0.88)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=300)
    plt.close(fig)


def plot_two_panel_actual_vs_predicted(
    join: TwoPanelJoin, output_path: Path, scope: str = "global", no_basemap: bool = False, partial_coverage: bool = True,
) -> None:
    """Build a 2x1 vertical figure (April actual top, April predicted bottom). FR-024/025/026."""
    plt, listed_cmap, patch = arm._require_matplotlib()
    _ensure_crisis_columns(join)
    fig, axes = plt.subplots(2, 1, figsize=(10, 12))
    use_latam = scope == "global"

    _panel(axes[0], join.actual_joined, "actual_crisis",
           f"April 2026 actual crisis (phase >= 3) — actual-covered subset (n={join.mapped_actual_count})",
           listed_cmap, use_latam, no_basemap)
    _panel(axes[1], join.predicted_joined, "predicted_crisis",
           f"April 2026 predicted crisis (phase >= 3) — all eligible predicted areas (n={join.mapped_predicted_count})",
           listed_cmap, use_latam, no_basemap)

    handles = [patch(color=arm.NO_ALERT_COLOR, label="No crisis (phase 1-2)"), patch(color=arm.ALERT_COLOR, label="Crisis (phase 3+)")]
    fig.legend(handles=handles, loc="lower center", ncol=2)
    title = "IPCCH April 2026 Global Actual vs Predicted Crisis"
    subtitle = "Actual coverage is partial; actual and predicted panels may cover different area_id sets." if partial_coverage else "Actual vs predicted crisis."
    fig.suptitle(f"{title}\n{subtitle}", fontsize=12)
    fig.subplots_adjust(left=0.04, right=0.97, bottom=0.08, top=0.90, hspace=0.18)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=300)
    plt.close(fig)


def _panel(ax: Any, gdf: Any, column: str, title: str, listed_cmap: Any, use_latam: bool, no_basemap: bool) -> None:
    ax.set_title(title, fontsize=11, weight="bold", pad=6)
    ax.set_axis_off()
    if gdf is None or len(gdf) == 0:
        ax.text(0.5, 0.5, "No mapped areas", ha="center", va="center", transform=ax.transAxes)
        return
    plot_gdf = gdf.copy()
    latam_gdf = plot_gdf.iloc[0:0]
    if use_latam:
        latam = arm._latam_mask(plot_gdf)
        latam_gdf = plot_gdf[latam].copy()
        plot_gdf = plot_gdf[~latam].copy()
    ctx = None if no_basemap else arm._optional_contextily()
    # Reproject to Web Mercator (EPSG:3857) before plotting so contextily basemap
    # tiles align (mirrors arm._plot_boolean_map); plotting in EPSG:4326 makes
    # contextily misread the extent and pick an invalid zoom -> no tiles render.
    if ctx is not None and getattr(plot_gdf, "crs", None) is not None:
        plot_gdf = plot_gdf.to_crs(epsg=3857)
        main_extent_gdf = plot_gdf[plot_gdf.geometry.centroid.x.ge(arm.AFRICA_MIN_X_M)].copy()
    elif use_latam:
        extent_source = plot_gdf.to_crs(epsg=4326) if getattr(plot_gdf, "crs", None) is not None else plot_gdf
        main_extent_gdf = plot_gdf[extent_source.geometry.bounds["minx"].ge(arm.AFRICA_MIN_LON)].copy()
    else:
        main_extent_gdf = plot_gdf
    arm._plot_binary_layer(plot_gdf, column, ax, listed_cmap)
    arm._set_padded_extent(ax, main_extent_gdf if not main_extent_gdf.empty else plot_gdf)
    arm._add_basemap(ax, ctx)
    if use_latam and len(latam_gdf):
        latam_inset = latam_gdf.to_crs(epsg=4326) if getattr(latam_gdf, "crs", None) is not None else latam_gdf
        arm._add_latam_inset(ax, latam_inset, column, listed_cmap)


def build_map(
    predictions: pd.DataFrame,
    april_actuals: Optional[pd.DataFrame],
    spatial_path: Path,
    figure_path: Path,
    summary_path: Path,
    join_validation_csv: Path,
    actual_source: str,
    prediction_source: str,
    scope: str = "global",
    no_basemap: bool = False,
    overwrite: bool = False,
) -> MapValidationSummary:
    """Orchestrate the two-panel map with output safety + validation summary."""
    arm.ensure_under(figure_path.parent, paths.REPORTS_DIR, "Map figure output")
    arm.ensure_under(summary_path.parent, paths.RESULTS_DIR, "Map validation output")
    targets = [figure_path, summary_path, join_validation_csv]
    conflicts = [str(p) for p in targets if p.exists()]
    if conflicts and not overwrite:
        raise LaunchMapError("Existing map output conflict without --overwrite: " + ", ".join(conflicts))

    boundaries = arm.load_spatial_boundaries(spatial_path)
    actuals_available = april_actuals is not None and len(april_actuals) > 0
    join = join_for_two_panel(predictions, april_actuals if actuals_available else predictions.iloc[0:0], boundaries)
    partial = (not actuals_available) or (join.mapped_actual_count < join.mapped_predicted_count)
    if actuals_available:
        plot_two_panel_actual_vs_predicted(join, figure_path, scope=scope, no_basemap=no_basemap, partial_coverage=partial)
        status = "rendered"
    else:
        plot_predicted_only(join, figure_path, scope=scope, no_basemap=no_basemap)
        status = "rendered_predicted_only"

    summary = MapValidationSummary(
        actual_source=actual_source,
        prediction_source=prediction_source,
        spatial_boundary_source=str(spatial_path),
        predicted_area_count=int(predictions["area_id"].astype(str).nunique()),
        april_actual_covered_area_count=int(april_actuals["area_id"].astype(str).nunique()) if april_actuals is not None and len(april_actuals) else 0,
        mapped_predicted_count=join.mapped_predicted_count,
        mapped_actual_count=join.mapped_actual_count,
        unmatched_prediction_area_ids=join.unmatched_prediction,
        unmatched_actual_area_ids=join.unmatched_actual,
        duplicate_spatial_keys=join.duplicate_spatial_keys,
        output_path=str(figure_path),
        status=status,
    )
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    import json
    summary_path.write_text(json.dumps(summary.to_dict(), indent=2), encoding="utf-8")
    join_rows = (
        [{"area_id": a, "layer": "prediction", "join_status": "unmatched"} for a in join.unmatched_prediction]
        + [{"area_id": a, "layer": "actual", "join_status": "unmatched"} for a in join.unmatched_actual]
    )
    pd.DataFrame(join_rows or [{"area_id": None, "layer": None, "join_status": "all_matched"}]).to_csv(join_validation_csv, index=False)
    return summary
