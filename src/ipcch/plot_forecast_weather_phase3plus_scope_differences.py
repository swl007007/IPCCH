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
DEFAULT_REPORT_PATH = paths.REPORTS_DIR / "launch" / "nowcasting_2026_04_forecasted_weather_scopes" / "phase3plus_scope_difference_1x3.png"
DEFAULT_SUMMARY_PATH = paths.RESULTS_DIR / "launch" / "nowcasting_2026_04_forecasted_weather_scopes" / "phase3plus_scope_difference_1x3_summary.json"
PHASE3_PLUS_COLUMN = "phase3_worse_pred"


@dataclass(frozen=True)
class ScopeInput:
    label: str
    prediction_path: Path


@dataclass(frozen=True)
class DifferenceSpec:
    label: str
    later_scope: str
    earlier_scope: str


class Phase3PlusDifferenceMapError(ValueError):
    pass


def default_scope_inputs(forecast_weather_root: Path, forecast_weather_scopes_root: Path) -> list[ScopeInput]:
    return [
        ScopeInput("0m", forecast_weather_root / "predictions_2026_04_all_area_id.csv"),
        ScopeInput("3m", forecast_weather_scopes_root / "scope_3m" / "predictions_2026_04_all_area_id.csv"),
        ScopeInput("6m", forecast_weather_scopes_root / "scope_6m" / "predictions_2026_04_all_area_id.csv"),
        ScopeInput("12m", forecast_weather_scopes_root / "scope_12m" / "predictions_2026_04_all_area_id.csv"),
    ]


def default_difference_specs(*, compare_to_nowcasting: bool = False) -> list[DifferenceSpec]:
    if compare_to_nowcasting:
        return [
            DifferenceSpec("3m - nowcasting", "3m", "0m"),
            DifferenceSpec("6m - nowcasting", "6m", "0m"),
            DifferenceSpec("12m - nowcasting", "12m", "0m"),
        ]
    return [
        DifferenceSpec("3m - 0m", "3m", "0m"),
        DifferenceSpec("6m - 3m", "6m", "3m"),
        DifferenceSpec("12m - 6m", "12m", "6m"),
    ]


def load_scope_predictions(scope_input: ScopeInput) -> pd.DataFrame:
    path = scope_input.prediction_path
    if not path.exists():
        raise Phase3PlusDifferenceMapError(f"Prediction file does not exist for {scope_input.label}: {path}")
    required = ["area_id", PHASE3_PLUS_COLUMN, "target_period"]
    df = pd.read_csv(path)
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise Phase3PlusDifferenceMapError(f"Prediction file for {scope_input.label} missing required columns: {missing}")
    out = df.loc[:, required].copy()
    out["area_id"] = arm.normalize_area_id(out["area_id"])
    out[PHASE3_PLUS_COLUMN] = pd.to_numeric(out[PHASE3_PLUS_COLUMN], errors="coerce")
    if out[PHASE3_PLUS_COLUMN].isna().any():
        raise Phase3PlusDifferenceMapError(f"Prediction file for {scope_input.label} contains missing/non-numeric {PHASE3_PLUS_COLUMN} values")
    if out["area_id"].duplicated().any():
        examples = sorted(out.loc[out["area_id"].duplicated(), "area_id"].unique().tolist())[:10]
        raise Phase3PlusDifferenceMapError(f"Prediction file for {scope_input.label} has duplicate area_id values: {examples}")
    out = out.rename(columns={PHASE3_PLUS_COLUMN: f"phase3plus_share_{scope_input.label}", "target_period": f"target_period_{scope_input.label}"})
    return out


def build_difference_frames(
    forecast_weather_root: Path,
    forecast_weather_scopes_root: Path,
    *,
    compare_to_nowcasting: bool = False,
) -> tuple[list[pd.DataFrame], list[dict]]:
    frames: dict[str, pd.DataFrame] = {}
    for scope_input in default_scope_inputs(forecast_weather_root, forecast_weather_scopes_root):
        frames[scope_input.label] = load_scope_predictions(scope_input)
    base = frames["0m"]
    for label in ["3m", "6m", "12m"]:
        base = base.merge(frames[label], on="area_id", how="inner", validate="one_to_one")
    if len(base) != len(frames["0m"]):
        raise Phase3PlusDifferenceMapError("Scope prediction area_id sets do not match exactly across 0m/3m/6m/12m")
    diff_frames = []
    summaries = []
    for spec in default_difference_specs(compare_to_nowcasting=compare_to_nowcasting):
        later_col = f"phase3plus_share_{spec.later_scope}"
        earlier_col = f"phase3plus_share_{spec.earlier_scope}"
        out = base.loc[:, ["area_id", later_col, earlier_col, f"target_period_{spec.later_scope}", f"target_period_{spec.earlier_scope}"]].copy()
        out["phase3plus_difference_pp"] = (out[later_col] - out[earlier_col]) * 100.0
        out["difference_label"] = spec.label
        out["later_scope"] = spec.later_scope
        out["earlier_scope"] = spec.earlier_scope
        out["later_target_period"] = out[f"target_period_{spec.later_scope}"]
        out["earlier_target_period"] = out[f"target_period_{spec.earlier_scope}"]
        summary = {
            "comparison": spec.label,
            "earlier_scope": spec.earlier_scope,
            "later_scope": spec.later_scope,
            "earlier_target_period": str(out["earlier_target_period"].iloc[0]),
            "later_target_period": str(out["later_target_period"].iloc[0]),
            "area_count": int(len(out)),
            "min_difference_pp": float(out["phase3plus_difference_pp"].min()),
            "p05_difference_pp": float(out["phase3plus_difference_pp"].quantile(0.05)),
            "median_difference_pp": float(out["phase3plus_difference_pp"].median()),
            "mean_difference_pp": float(out["phase3plus_difference_pp"].mean()),
            "p95_difference_pp": float(out["phase3plus_difference_pp"].quantile(0.95)),
            "max_difference_pp": float(out["phase3plus_difference_pp"].max()),
            "increased_area_count": int((out["phase3plus_difference_pp"] > 0).sum()),
            "decreased_area_count": int((out["phase3plus_difference_pp"] < 0).sum()),
            "unchanged_area_count": int((out["phase3plus_difference_pp"] == 0).sum()),
        }
        diff_frames.append(out)
        summaries.append(summary)
    return diff_frames, summaries


def join_difference(boundaries: Any, difference: pd.DataFrame, label: str) -> Any:
    gpd = arm._require_geopandas()
    spatial = boundaries.copy()
    spatial["area_id"] = arm.normalize_area_id(spatial["area_id"])
    merged = spatial.merge(difference, on="area_id", how="right", indicator=True)
    unmatched = sorted(merged.loc[merged["_merge"].ne("both"), "area_id"].astype(str).unique().tolist())
    duplicates = sorted(merged.loc[merged["area_id"].duplicated(), "area_id"].astype(str).unique().tolist())
    if unmatched:
        raise Phase3PlusDifferenceMapError(f"Spatial join failed for {label}; unmatched area_id sample: {unmatched[:10]}")
    if duplicates:
        raise Phase3PlusDifferenceMapError(f"Spatial join duplicated area_id values for {label}: {duplicates[:10]}")
    joined = merged.drop(columns=["_merge"])
    return gpd.GeoDataFrame(joined, geometry="geometry", crs=spatial.crs)


def _add_continuous_latam_inset(ax: Any, latam_gdf: Any, column: str, cmap: str, vlim: float) -> None:
    if latam_gdf.empty:
        return
    inset = ax.inset_axes([0.62, 0.06, 0.34, 0.30])
    latam_gdf.plot(column=column, cmap=cmap, linewidth=0.08, edgecolor="white", ax=inset, vmin=-vlim, vmax=vlim)
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


def _plot_panel(ax: Any, joined: Any, title: str, cmap: str, vlim: float, no_basemap: bool) -> None:
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
    plot_gdf.plot(
        column="phase3plus_difference_pp",
        cmap=cmap,
        linewidth=0.08,
        edgecolor="white",
        ax=ax,
        vmin=-vlim,
        vmax=vlim,
    )
    arm._set_padded_extent(ax, main_extent_gdf if not main_extent_gdf.empty else plot_gdf)
    arm._add_basemap(ax, ctx)
    _add_continuous_latam_inset(ax, latam_inset, "phase3plus_difference_pp", cmap, vlim)
    ax.set_title(title, fontsize=10.5, weight="bold", pad=5)
    ax.set_axis_off()


def plot_difference_grid(
    joined_maps: Sequence[Any],
    summaries: Sequence[dict],
    output_path: Path,
    *,
    cmap: str,
    vlim: float,
    no_basemap: bool,
    compare_to_nowcasting: bool = False,
) -> None:
    plt, _, _ = arm._require_matplotlib()
    import matplotlib as mpl

    fig, axes = plt.subplots(1, 3, figsize=(16, 5.6))
    for ax, joined, summary in zip(axes, joined_maps, summaries):
        title = (
            f"{summary['comparison']}\n"
            f"{summary['earlier_target_period']} → {summary['later_target_period']}"
        )
        _plot_panel(ax, joined, title, cmap, vlim, no_basemap)
    norm = mpl.colors.TwoSlopeNorm(vmin=-vlim, vcenter=0.0, vmax=vlim)
    sm = mpl.cm.ScalarMappable(norm=norm, cmap=cmap)
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=axes, orientation="horizontal", fraction=0.06, pad=0.05, shrink=0.74)
    cbar.set_label("Change in predicted Phase 3+ population share (percentage points)", fontsize=10)
    title = "Forecast-scope changes vs nowcasting in Phase 3+ population share" if compare_to_nowcasting else "Adjacent forecast-scope changes in Phase 3+ population share"
    fig.suptitle(title, fontsize=13, weight="bold")
    fig.subplots_adjust(left=0.02, right=0.99, bottom=0.17, top=0.84, wspace=0.02)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=300)
    plt.close(fig)


def build_difference_map(
    forecast_weather_root: Path,
    forecast_weather_scopes_root: Path,
    spatial_path: Path,
    output_path: Path,
    summary_path: Path,
    *,
    cmap: str = "RdBu_r",
    vlim: float = 15.0,
    no_basemap: bool = False,
    compare_to_nowcasting: bool = False,
) -> dict:
    boundaries = arm.load_spatial_boundaries(spatial_path)
    diff_frames, summaries = build_difference_frames(
        forecast_weather_root,
        forecast_weather_scopes_root,
        compare_to_nowcasting=compare_to_nowcasting,
    )
    joined_maps = [join_difference(boundaries, frame, summary["comparison"]) for frame, summary in zip(diff_frames, summaries)]
    plot_difference_grid(
        joined_maps,
        summaries,
        output_path,
        cmap=cmap,
        vlim=vlim,
        no_basemap=no_basemap,
        compare_to_nowcasting=compare_to_nowcasting,
    )
    payload = {
        "output_path": str(output_path),
        "spatial_path": str(spatial_path),
        "phase3plus_column": PHASE3_PLUS_COLUMN,
        "difference_column": "phase3plus_difference_pp",
        "comparison_mode": "target_scope_vs_nowcasting" if compare_to_nowcasting else "adjacent_scopes",
        "color_scale": {"cmap": cmap, "vmin": -float(vlim), "vcenter": 0.0, "vmax": float(vlim)},
        "comparisons": summaries,
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plot forecast-weather Phase 3+ population-share differences across scopes.")
    parser.add_argument("--forecast-weather-root", type=Path, default=DEFAULT_FORECAST_WEATHER_ROOT)
    parser.add_argument("--forecast-weather-scopes-root", type=Path, default=DEFAULT_FORECAST_WEATHER_SCOPES_ROOT)
    parser.add_argument("--spatial-path", type=Path, default=DEFAULT_SPATIAL_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY_PATH)
    parser.add_argument("--cmap", default="RdBu_r")
    parser.add_argument("--vlim", type=float, default=15.0, help="Symmetric color scale bound in percentage points; values beyond +/-vlim saturate.")
    parser.add_argument("--no-basemap", action="store_true")
    parser.add_argument(
        "--compare-to-nowcasting",
        action="store_true",
        help="Compare each target forecast scope (3m/6m/12m) against nowcasting (0m) instead of adjacent scopes.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    payload = build_difference_map(
        forecast_weather_root=args.forecast_weather_root,
        forecast_weather_scopes_root=args.forecast_weather_scopes_root,
        spatial_path=args.spatial_path,
        output_path=args.output,
        summary_path=args.summary,
        cmap=args.cmap,
        vlim=args.vlim,
        no_basemap=args.no_basemap,
        compare_to_nowcasting=args.compare_to_nowcasting,
    )
    print(f"wrote {payload['output_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
