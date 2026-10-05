"""Phase 3+ alert map for the latest Somalia round (2026-04) from the closed v4 calibrated-D run.

Reads existing v4 predictions only (no refit). Alert = q3_raw >= 0.2 (uncalibrated; a post-hoc
deviation from the pre-registered q3_final, which applies the selected shift calibration).
Actual = reported phase >= 3 from the v4 label ledger. The 904 cohort areas overlap heavily
(polygons from several analysis vintages), so the map uses the non-overlapping district layer:
cohort areas first labelled in 2017, checked to tile without overlap.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

PROJECT_ROOT = next(path for path in Path(__file__).resolve().parents if (path / "src").exists())
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import pandas as pd

from ipcch import paths

V4_DIR = paths.RESULTS_DIR / "experiments" / "somalia_oracle" / "v4_calibrated_d"
SPATIAL_PATH = paths.SOURCE_DATA_DIR / "assembled_IPCCH" / "spatial" / "ipcch_admin_geometry.shp"
TARGET_YEAR, TARGET_MONTH = 2026, 4
THRESHOLD = 0.2
DISTRICT_FIRST_YEAR = 2017
MAX_OVERLAP_SHARE = 0.01

ALERT = "#c2410c"
NO_ALERT = "#1baf7a"
OUTCOME_COLORS = {"Hit (TP)": "#c2410c", "Missed (FN)": "#2a78d6", "False alarm (FP)": "#e69a2e", "Correct no-alert (TN)": NO_ALERT}
TEXT_PRIMARY, TEXT_SECONDARY = "#0b0b0b", "#52514e"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--v4-dir", default=str(V4_DIR))
    parser.add_argument("--spatial-path", default=str(SPATIAL_PATH))
    parser.add_argument("--data-setting", default="augmented", choices=["augmented", "original"])
    parser.add_argument("--out-report-dir", default=str(paths.REPORTS_DIR / "somalia_oracle" / "v4_calibrated_d" / "alert_map_2026_04"))
    parser.add_argument("--out-results-dir", default=str(V4_DIR / "alert_map_2026_04"))
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def load_area_table(v4_dir: Path, data_setting: str) -> pd.DataFrame:
    target_ord = TARGET_YEAR * 12 + TARGET_MONTH - 1
    pred = pd.read_csv(v4_dir / "predictions" / "final_predictions.csv.gz", low_memory=False)
    pred = pred[(pred["outer_year"] == TARGET_YEAR) & (pred["horizon"] == 0) & (pred["data_setting"] == data_setting) & (pred["target_ord"] == target_ord)]
    if pred.empty or pred["area_id"].duplicated().any() or pred["hx"].notna().any():
        raise ValueError("expected one history-free H0 prediction per area for the target month")
    labels = pd.read_csv(v4_dir / "ledgers" / "label_ledger.csv.gz", low_memory=False)
    originals = labels[~labels["is_copy"].astype(bool)]
    first_year = originals.groupby("area_id")["year"].min().rename("first_label_year")
    truth = originals[originals["target_ord"] == target_ord][["area_id", "overall_phase", "q3", "actual_crisis"]]
    if truth["area_id"].duplicated().any():
        raise ValueError("duplicate original labels for the target month")
    if not (truth["actual_crisis"].astype(bool) == (truth["overall_phase"] >= 3)).all():
        raise ValueError("actual_crisis does not equal reported phase >= 3")
    table = pred[["area_id", "q3_raw", "q3_final", "formulation", "bundle", "half_life", "method"]].merge(truth, on="area_id", how="left", validate="one_to_one")
    if table["actual_crisis"].isna().any():
        raise ValueError("predicted areas without a target-month label")
    table = table.join(first_year, on="area_id")
    table["actual_alert"] = table["actual_crisis"].astype(bool)
    table["pred_alert"] = table["q3_raw"] >= THRESHOLD
    table["outcome"] = [
        ("Hit (TP)" if p else "Missed (FN)") if a else ("False alarm (FP)" if p else "Correct no-alert (TN)")
        for a, p in zip(table["actual_alert"], table["pred_alert"])
    ]
    return table


def binary_metrics(actual: pd.Series, alert: pd.Series) -> dict:
    tp, fp = int((alert & actual).sum()), int((alert & ~actual).sum())
    fn, tn = int((~alert & actual).sum()), int((~alert & ~actual).sum())
    return {
        "n": len(actual), "actual_3plus": int(actual.sum()), "alerts": int(alert.sum()),
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "recall": tp / (tp + fn) if tp + fn else None,
        "precision": tp / (tp + fp) if tp + fp else None,
        "f1": 2 * tp / (2 * tp + fp + fn) if tp + fp + fn else None,
        "accuracy": (tp + tn) / len(actual),
    }


def district_layer(table: pd.DataFrame, spatial_path: Path):
    import geopandas as gpd

    shapes = gpd.read_file(spatial_path)
    shapes["area_id"] = pd.to_numeric(shapes["admin_code"])
    ids = table.loc[table["first_label_year"] == DISTRICT_FIRST_YEAR, "area_id"]
    gdf = shapes[shapes["area_id"].isin(ids)].merge(table, on="area_id", validate="one_to_one")
    if len(gdf) != len(ids):
        raise ValueError("district areas missing geometry")
    metric = gdf.to_crs(32638)
    metric["geometry"] = metric.buffer(0)
    overlap_share = 1 - metric.union_all().area / metric.area.sum()
    if overlap_share > MAX_OVERLAP_SHARE:
        raise ValueError(f"district layer overlaps ({overlap_share:.3%} of summed area)")
    return gdf, overlap_share


def plot(gdf, metrics: dict, all_metrics: dict, recipe: str, data_setting: str, out_path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    fig, axes = plt.subplots(1, 3, figsize=(16, 7.6))
    edge = {"edgecolor": "white", "linewidth": 0.5}
    n_actual, n_pred = int(gdf["actual_alert"].sum()), int(gdf["pred_alert"].sum())
    panels = [
        ("Reported phase 3+", gdf["actual_alert"], [Patch(color=ALERT, label=f"Phase 3+ ({n_actual})"), Patch(color=NO_ALERT, label=f"Phase 1-2 ({len(gdf) - n_actual})")]),
        (f"Predicted phase 3+ (q3 ≥ {THRESHOLD})", gdf["pred_alert"], [Patch(color=ALERT, label=f"Alert ({n_pred})"), Patch(color=NO_ALERT, label=f"No alert ({len(gdf) - n_pred})")]),
    ]
    for ax, (title, flag, handles) in zip(axes[:2], panels):
        gdf.plot(color=flag.map({True: ALERT, False: NO_ALERT}), ax=ax, **edge)
        ax.set_title(title, fontsize=12, color=TEXT_PRIMARY, loc="left")
        ax.legend(handles=handles, loc="lower right", frameon=False, fontsize=9, labelcolor=TEXT_PRIMARY)
    counts = gdf["outcome"].value_counts()
    gdf.plot(color=gdf["outcome"].map(OUTCOME_COLORS), ax=axes[2], **edge)
    axes[2].set_title("Prediction vs reported", fontsize=12, color=TEXT_PRIMARY, loc="left")
    axes[2].legend(handles=[Patch(color=c, label=f"{k} ({int(counts.get(k, 0))})") for k, c in OUTCOME_COLORS.items()], loc="lower right", frameon=False, fontsize=9, labelcolor=TEXT_PRIMARY)
    for ax in axes:
        ax.set_axis_off()
        ax.set_aspect("equal")

    def fmt(m: dict) -> str:
        return f"recall {m['recall']:.2f} · precision {m['precision']:.2f} · F1 {m['f1']:.2f} · accuracy {m['accuracy']:.2f}"

    fig.suptitle("Somalia phase 3+ alert map — April 2026 (nowcast, H=0)", x=0.01, ha="left", fontsize=15, color=TEXT_PRIMARY)
    fig.text(0.01, 0.925, f"{len(gdf)} districts: {fmt(metrics)}   |   all {all_metrics['n']} cohort areas: {fmt(all_metrics)}", fontsize=9.5, color=TEXT_SECONDARY)
    fig.text(
        0.01, 0.02,
        f"Model: Somalia oracle v4, {data_setting} data, selected recipe {recipe} (its calibration step not applied); trained only on labels before 2026. "
        f"Prediction = uncalibrated q3_raw (post-hoc; the pre-registered q3_final applies a shift calibration).\n"
        f"Actual = reported IPC phase ≥ 3 in the v4 label ledger. Map shows the {len(gdf)} non-overlapping district polygons; "
        f"the other cohort areas overlap them (multiple analysis vintages) and are scored but not drawn.",
        fontsize=8.5, color=TEXT_SECONDARY,
    )
    fig.subplots_adjust(left=0.01, right=0.99, top=0.86, bottom=0.08, wspace=0.02)
    fig.savefig(out_path, dpi=200, facecolor="#fcfcfb")
    plt.close(fig)


def main() -> int:
    args = parse_args()
    v4_dir, spatial_path = Path(args.v4_dir), Path(args.spatial_path)
    report_dir, results_dir = Path(args.out_report_dir), Path(args.out_results_dir)
    stem = f"somalia_alert_2026_04_h0_{args.data_setting}_q3raw"
    outputs = [report_dir / f"{stem}.png", results_dir / f"{stem}_areas.csv", results_dir / f"{stem}_summary.json"]
    existing = [str(p) for p in outputs if p.exists()]
    if existing and not args.overwrite:
        raise SystemExit("outputs exist (use --overwrite): " + "; ".join(existing))
    report_dir.mkdir(parents=True, exist_ok=True)
    results_dir.mkdir(parents=True, exist_ok=True)

    table = load_area_table(v4_dir, args.data_setting)
    gdf, overlap_share = district_layer(table, spatial_path)
    table["in_district_map"] = table["area_id"].isin(gdf["area_id"])
    recipe_cols = ["formulation", "bundle", "half_life", "method"]
    if table[recipe_cols].drop_duplicates().shape[0] != 1:
        raise ValueError("more than one selected recipe in the target context")
    recipe = "/".join(f"{c}={table[c].iloc[0]}" for c in recipe_cols)
    plot_recipe = f"{table['formulation'].iloc[0]}/{table['bundle'].iloc[0]}/half-life {table['half_life'].iloc[0]}"
    all_metrics = binary_metrics(table["actual_alert"], table["pred_alert"])
    district_metrics = binary_metrics(gdf["actual_alert"], gdf["pred_alert"])

    plot(gdf, district_metrics, all_metrics, plot_recipe, args.data_setting, outputs[0])
    table.sort_values("area_id").to_csv(outputs[1], index=False)
    inputs = [v4_dir / "predictions" / "final_predictions.csv.gz", v4_dir / "ledgers" / "label_ledger.csv.gz", spatial_path]
    summary = {
        "target_month": f"{TARGET_YEAR}-{TARGET_MONTH:02d}", "horizon": 0, "data_setting": args.data_setting,
        "selected_recipe": recipe, "prediction_column": "q3_raw", "calibration_note": "post-hoc: uncalibrated q3_raw instead of pre-registered q3_final",
        "alert_rule": f"q3_raw >= {THRESHOLD}", "actual_rule": "reported overall_phase >= 3",
        "map_layer": {"rule": f"cohort areas whose first original label year is {DISTRICT_FIRST_YEAR}", "n_areas": len(gdf), "overlap_share_of_summed_area": overlap_share},
        "metrics_district_layer": district_metrics, "metrics_all_cohort_areas": all_metrics,
        "metrics_all_cohort_areas_q3_final_reference": binary_metrics(table["actual_alert"], table["q3_final"] >= THRESHOLD),
        "inputs": {str(p): sha256(p) for p in inputs},
        "outputs": [str(p) for p in outputs],
    }
    outputs[2].write_text(json.dumps(summary, indent=2))
    print(json.dumps({k: summary[k] for k in ("selected_recipe", "map_layer", "metrics_district_layer", "metrics_all_cohort_areas")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
