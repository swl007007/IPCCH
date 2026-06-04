from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import pandas as pd

from ipcch import alert_risk_maps as arm
from ipcch import paths


DEFAULT_FORECAST_WEATHER_ROOT = paths.RESULTS_DIR / "launch" / "nowcasting_2026_04_forecasted_weather"
DEFAULT_FORECAST_WEATHER_SCOPES_ROOT = paths.RESULTS_DIR / "launch" / "nowcasting_2026_04_forecasted_weather_scopes"
DEFAULT_SPATIAL_PATH = paths.SOURCE_DATA_DIR / "assembled_IPCCH" / "spatial" / "ipcch_admin_geometry.shp"
DEFAULT_REPORT_PATH = paths.REPORTS_DIR / "launch" / "nowcasting_2026_04_forecasted_weather_scopes" / "phase3plus_population_share_1x4.png"
DEFAULT_SUMMARY_PATH = paths.RESULTS_DIR / "launch" / "nowcasting_2026_04_forecasted_weather_scopes" / "phase3plus_population_share_1x4_summary.json"
PHASE3_PLUS_COLUMN = "phase3_worse_pred"


@dataclass(frozen=True)
class ScopeInput:
    label: str
    scope_months: int
    prediction_path: Path


class Phase3PlusMapError(ValueError):
    pass


def default_scope_inputs(forecast_weather_root: Path, forecast_weather_scopes_root: Path) -> list[ScopeInput]:
    return [
        ScopeInput("0m", 0, forecast_weather_root / "predictions_2026_04_all_area_id.csv"),
        ScopeInput("3m", 3, forecast_weather_scopes_root / "scope_3m" / "predictions_2026_04_all_area_id.csv"),
        ScopeInput("6m", 6, forecast_weather_scopes_root / "scope_6m" / "predictions_2026_04_all_area_id.csv"),
        ScopeInput("12m", 12, forecast_weather_scopes_root / "scope_12m" / "predictions_2026_04_all_area_id.csv"),
    ]


def load_scope_predictions(scope_input: ScopeInput) -> pd.DataFrame:
    path = scope_input.prediction_path
    if not path.exists():
        raise Phase3PlusMapError(f"Prediction file does not exist for {scope_input.label}: {path}")
    required = ["area_id", PHASE3_PLUS_COLUMN, "target_period"]
    df = pd.read_csv(path)
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise Phase3PlusMapError(f"Prediction file for {scope_input.label} missing required columns: {missing}")
    out = df.loc[:, [c for c in ["area_id", PHASE3_PLUS_COLUMN, "target_period", "threshold"] if c in df.columns]].copy()
    out["area_id"] = arm.normalize_area_id(out["area_id"])
    out["phase3plus_population_share"] = pd.to_numeric(out[PHASE3_PLUS_COLUMN], errors="coerce")
    if out["phase3plus_population_share"].isna().any():
        raise Phase3PlusMapError(f"Prediction file for {scope_input.label} contains missing/non-numeric {PHASE3_PLUS_COLUMN} values")
    out["phase3plus_population_percent"] = (out["phase3plus_population_share"].clip(lower=0, upper=1) * 100).astype(float)
    out["scope_label"] = scope_input.label
    out["scope_months"] = scope_input.scope_months
    out["prediction_source"] = str(path)
    if out["area_id"].duplicated().any():
        examples = sorted(out.loc[out["area_id"].duplicated(), "area_id"].unique().tolist())[:10]
        raise Phase3PlusMapError(f"Prediction file for {scope_input.label} has duplicate area_id values: {examples}")
    return out


def join_predictions(boundaries: Any, predictions: pd.DataFrame, scope_label: str) -> tuple[Any, dict]:
    gpd = arm._require_geopandas()
    spatial = boundaries.copy()
    spatial["area_id"] = arm.normalize_area_id(spatial["area_id"])
    merged = spatial.merge(predictions, on="area_id", how="right", indicator=True)
    unmatched = sorted(merged.loc[merged["_merge"].ne("both"), "area_id"].astype(str).unique().tolist())
    duplicates = sorted(merged.loc[merged["area_id"].duplicated(), "area_id"].astype(str).unique().tolist())
    if unmatched:
        raise Phase3PlusMapError(f"Spatial join failed for {scope_label}; unmatched area_id sample: {unmatched[:10]}")
    if duplicates:
        raise Phase3PlusMapError(f"Spatial join duplicated area_id values for {scope_label}: {duplicates[:10]}")
    joined = merged.drop(columns=["_merge"])
    joined = gpd.GeoDataFrame(joined, geometry="geometry", crs=spatial.crs)
    summary = {
        "scope": scope_label,
        "prediction_rows": int(len(predictions)),
        "mapped_rows": int(len(joined)),
        "min_percent": float(joined["phase3plus_population_percent"].min()),
        "max_percent": float(joined["phase3plus_population_percent"].max()),
        "mean_percent": float(joined["phase3plus_population_percent"].mean()),
        "target_period": str(predictions["target_period"].iloc[0]) if "target_period" in predictions.columns and len(predictions) else None,
        "prediction_source": str(predictions["prediction_source"].iloc[0]) if len(predictions) else None,
        "unmatched_area_ids": unmatched,
    }
    return joined, summary


def _add_continuous_latam_inset(ax: Any, latam_gdf: Any, column: str, cmap: str, vmin: float, vmax: float) -> None:
    if latam_gdf.empty:
        return
    inset = ax.inset_axes([0.62, 0.06, 0.34, 0.30])
    latam_gdf.plot(column=column, cmap=cmap, linewidth=0.08, edgecolor="white", ax=inset, vmin=vmin, vmax=vmax)
    minx, miny, maxx, maxy = latam_gdf.total_bounds
    pad_x = (maxx - minx) * 0.05 if maxx > minx else 1
    pad_y = (maxy - miny) * 0.12 if maxy > miny else 1
    inset.set_xlim(minx - pad_x, maxx + pad_x)
    inset.set_ylim(miny - pad_y, maxy + pad_y)
    inset.set_xticks([])
    inset.set_yticks([])
    for spine in inset.spines.values():
        spine.set_edgecolor("0.35")
        spine.set_linewidth(0.7)
    inset.set_title("Latin America", fontsize=6.5, pad=1.5)
    inset.patch.set_facecolor("white")
    inset.patch.set_alpha(0.92)


def _plot_panel(ax: Any, joined: Any, title: str, cmap: str, vmin: float, vmax: float, no_basemap: bool) -> Any:
    plot_gdf = joined.copy()
    latam_gdf = plot_gdf.iloc[0:0]
    latam = arm._latam_mask(plot_gdf)
    latam_gdf = plot_gdf[latam].copy()
    plot_gdf = plot_gdf[~latam].copy()
    latam_inset = latam_gdf.to_crs(epsg=4326) if not latam_gdf.empty and getattr(latam_gdf, "crs", None) is not None else latam_gdf
    ctx = None if no_basemap else arm._optional_contextily()
    if ctx is not None and getattr(plot_gdf, "crs", None) is not None:
        plot_gdf = plot_gdf.to_crs(epsg=3857)
        main_extent_gdf = plot_gdf[plot_gdf.geometry.centroid.x.ge(arm.AFRICA_MIN_X_M)].copy()
    else:
        extent_source = plot_gdf.to_crs(epsg=4326) if getattr(plot_gdf, "crs", None) is not None else plot_gdf
        main_extent_gdf = plot_gdf[extent_source.geometry.bounds["minx"].ge(arm.AFRICA_MIN_LON)].copy()
    plotted = plot_gdf.plot(
        column="phase3plus_population_percent",
        cmap=cmap,
        linewidth=0.08,
        edgecolor="white",
        ax=ax,
        vmin=vmin,
        vmax=vmax,
    )
    arm._set_padded_extent(ax, main_extent_gdf if not main_extent_gdf.empty else plot_gdf)
    arm._add_basemap(ax, ctx)
    _add_continuous_latam_inset(ax, latam_inset, "phase3plus_population_percent", cmap, vmin, vmax)
    ax.set_title(title, fontsize=10.5, weight="bold", pad=5)
    ax.set_axis_off()
    return plotted


def plot_phase3plus_grid(
    joined_maps: Sequence[Any],
    summaries: Sequence[dict],
    output_path: Path,
    *,
    cmap: str,
    no_basemap: bool,
    vmin: float,
    vmax: float,
) -> None:
    plt, _, _ = arm._require_matplotlib()
    import matplotlib as mpl

    fig, axes = plt.subplots(1, 4, figsize=(20, 5.6))
    for ax, joined, summary in zip(axes, joined_maps, summaries):
        title = f"{summary['scope']} target {summary['target_period']}\nPhase 3+ population share"
        _plot_panel(ax, joined, title, cmap, vmin, vmax, no_basemap)
    norm = mpl.colors.Normalize(vmin=vmin, vmax=vmax)
    sm = mpl.cm.ScalarMappable(norm=norm, cmap=cmap)
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=axes, orientation="horizontal", fraction=0.045, pad=0.04, shrink=0.72)
    cbar.set_label("Predicted percentage of population in IPC/CH Phase 3+", fontsize=10)
    fig.suptitle("Forecast-weather launch predictions: Phase 3+ population percentage by area", fontsize=13, weight="bold")
    fig.subplots_adjust(left=0.02, right=0.99, bottom=0.16, top=0.86, wspace=0.02)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=300)
    plt.close(fig)


def build_phase3plus_map(
    forecast_weather_root: Path,
    forecast_weather_scopes_root: Path,
    spatial_path: Path,
    output_path: Path,
    summary_path: Path,
    *,
    cmap: str = "YlOrRd",
    no_basemap: bool = False,
    vmin: float = 5.0,
    vmax: float = 70.0,
) -> dict:
    boundaries = arm.load_spatial_boundaries(spatial_path)
    joined_maps = []
    summaries = []
    for scope_input in default_scope_inputs(forecast_weather_root, forecast_weather_scopes_root):
        predictions = load_scope_predictions(scope_input)
        joined, summary = join_predictions(boundaries, predictions, scope_input.label)
        joined_maps.append(joined)
        summaries.append(summary)
    plot_phase3plus_grid(joined_maps, summaries, output_path, cmap=cmap, no_basemap=no_basemap, vmin=vmin, vmax=vmax)
    payload = {
        "output_path": str(output_path),
        "spatial_path": str(spatial_path),
        "phase3plus_column": PHASE3_PLUS_COLUMN,
        "value_column": "phase3plus_population_percent",
        "color_scale": {"cmap": cmap, "vmin": float(vmin), "vmax": float(vmax)},
        "scopes": summaries,
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plot a 1x4 forecast-weather Phase 3+ population-percentage map for 0m/3m/6m/12m launch outputs.")
    parser.add_argument("--forecast-weather-root", type=Path, default=DEFAULT_FORECAST_WEATHER_ROOT)
    parser.add_argument("--forecast-weather-scopes-root", type=Path, default=DEFAULT_FORECAST_WEATHER_SCOPES_ROOT)
    parser.add_argument("--spatial-path", type=Path, default=DEFAULT_SPATIAL_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY_PATH)
    parser.add_argument("--cmap", default="YlOrRd")
    parser.add_argument("--vmin", type=float, default=5.0, help="Lower color scale bound in percent; default enhances contrast around the common 20% range.")
    parser.add_argument("--vmax", type=float, default=70.0, help="Upper color scale bound in percent; values above this saturate at the darkest color.")
    parser.add_argument("--no-basemap", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    payload = build_phase3plus_map(
        forecast_weather_root=args.forecast_weather_root,
        forecast_weather_scopes_root=args.forecast_weather_scopes_root,
        spatial_path=args.spatial_path,
        output_path=args.output,
        summary_path=args.summary,
        cmap=args.cmap,
        no_basemap=args.no_basemap,
        vmin=args.vmin,
        vmax=args.vmax,
    )
    print(f"wrote {payload['output_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
