from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = next(path for path in Path(__file__).resolve().parents if (path / "src").exists())
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from ipcch.alert_risk_maps import (
    AlertRiskMapError,
    compute_top_risk_categories,
    default_country_lookup_path,
    default_prediction_root,
    default_report_dir,
    default_results_dir,
    default_spatial_path,
    join_predictions_to_spatial,
    load_country_area_lookup,
    load_prediction_dataset,
    load_spatial_boundaries,
    plot_top_risk,
    plot_actual_vs_predicted,
    country_area_ids,
    resolve_path,
    validate_output_conflicts,
    OutputPlan,
)


def default_somalia_local_file() -> Path:
    return default_prediction_root() / "somalia_only_identifier_features_threshold_0_20" / "predictions" / "predictions_2025.csv"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Somalia local-model 2025 IPCCH alert and top-risk maps from one local prediction output.")
    parser.add_argument("--prediction-file", default=str(default_somalia_local_file()), help="Somalia local-model prediction CSV.")
    parser.add_argument("--scope", default="SOM", help="Country ISO3 to keep from the local-model file, default SOM.")
    parser.add_argument("--country-lookup-path", default=str(default_country_lookup_path()), help="CSV mapping area_id to ISO3 country codes.")
    parser.add_argument("--spatial-path", default=str(default_spatial_path()), help="Spatial boundary file with area_id geometries.")
    parser.add_argument("--out-report-dir", default=str(default_report_dir()), help="Directory under reports/ for final figures.")
    parser.add_argument("--out-results-dir", default=str(default_results_dir()), help="Directory under results/ for validation summaries.")
    parser.add_argument("--min-record-date", help="Drop retained latest records before this date, e.g. 2025-03-01.")
    parser.add_argument("--predicted-alert-threshold", type=float, help="Recompute predicted alert as phase3_pred greater than or equal to this threshold.")
    parser.add_argument("--actual-alert-threshold", type=float, help="Recompute actual alert as phase3_worse greater than or equal to this threshold.")
    parser.add_argument("--filename-suffix", default="_local_model", help="Suffix to append before the figure extension.")
    parser.add_argument("--overwrite", action="store_true", help="Replace existing local-model figures.")
    parser.add_argument("--no-basemap", action="store_true", help="Disable contextual basemap tiles.")
    parser.add_argument("--figure-format", default="png", help="Final figure format, default png.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    scope = args.scope.strip().upper()
    report_dir = resolve_path(args.out_report_dir)
    results_dir = resolve_path(args.out_results_dir)
    fmt = args.figure_format.lower().lstrip(".")
    suffix = args.filename_suffix
    figures = {
        "actual_vs_predicted": report_dir / f"ipcch_2025_{scope.lower()}_local_model_actual_vs_predicted_alert_map{suffix}.{fmt}",
        "top_risk": report_dir / f"ipcch_2025_{scope.lower()}_local_model_top30_phase3_risk_comparison_map{suffix}.{fmt}",
    }
    plan = OutputPlan(report_dir, results_dir, fmt, figures, results_dir / f"ipcch_2025_{scope.lower()}_local_model_alert_risk_maps_validation_summary.json")
    try:
        validate_output_conflicts(plan, args.overwrite, write_validation_summary=False)
        boundaries = load_spatial_boundaries(args.spatial_path)
        lookup = load_country_area_lookup(args.country_lookup_path)
        area_ids = country_area_ids(lookup, scope)
        actual_dataset = load_prediction_dataset(
            args.prediction_file,
            "local",
            scope,
            "actual",
            args.min_record_date,
            args.predicted_alert_threshold,
            args.actual_alert_threshold,
        )
        actual_joined = join_predictions_to_spatial(actual_dataset, boundaries, area_ids)
        top_dataset = load_prediction_dataset(args.prediction_file, "local", scope, "top_risk", args.min_record_date)
        top_dataset.records = compute_top_risk_categories(top_dataset.records)
        top_joined = join_predictions_to_spatial(top_dataset, boundaries, area_ids)
        plot_actual_vs_predicted([actual_joined], figures["actual_vs_predicted"], f"{scope} Local Model", args.no_basemap)
        plot_top_risk(top_joined.joined_records, figures["top_risk"], f"{scope} Local Model", args.no_basemap)
    except AlertRiskMapError as exc:
        print(f"Validation error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Unexpected error: {exc}", file=sys.stderr)
        return 1
    print("Generated 2025 IPCCH local-model alert risk maps.")
    for key, output in figures.items():
        print(f"{key}: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
