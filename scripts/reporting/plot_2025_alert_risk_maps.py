from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = next(path for path in Path(__file__).resolve().parents if (path / "src").exists())
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from ipcch.alert_risk_maps import AlertRiskMapError, default_prediction_root, default_report_dir, default_results_dir, default_spatial_path, run_alert_risk_maps


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate 2025 IPCCH alert and top-risk maps from existing prediction outputs.")
    parser.add_argument("--prediction-root", default=str(default_prediction_root()), help="Root directory containing prediction outputs.")
    parser.add_argument("--spatial-path", default=str(default_spatial_path()), help="Spatial boundary file with area_id geometries.")
    parser.add_argument("--out-report-dir", default=str(default_report_dir()), help="Directory under reports/ for final figures.")
    parser.add_argument("--out-results-dir", default=str(default_results_dir()), help="Directory under results/ for validation summaries.")
    parser.add_argument("--horizon-0m-file", help="Explicit global 0m prediction CSV.")
    parser.add_argument("--horizon-3m-file", help="Explicit global 3m prediction CSV.")
    parser.add_argument("--horizon-6m-file", help="Explicit global 6m prediction CSV.")
    parser.add_argument("--somalia-horizon-0m-file", help="Explicit Somalia global-grouping 0m prediction CSV.")
    parser.add_argument("--somalia-horizon-3m-file", help="Explicit Somalia global-grouping 3m prediction CSV.")
    parser.add_argument("--somalia-horizon-6m-file", help="Explicit Somalia global-grouping 6m prediction CSV.")
    parser.add_argument("--overwrite", action="store_true", help="Replace existing final figures and validation summary.")
    parser.add_argument("--write-validation-summary", dest="write_validation_summary", action="store_true", default=True, help="Write validation summary JSON under results/.")
    parser.add_argument("--no-write-validation-summary", dest="write_validation_summary", action="store_false", help="Do not write validation summary JSON.")
    parser.add_argument("--no-basemap", action="store_true", help="Disable contextual basemap tiles.")
    parser.add_argument("--figure-format", default="png", help="Final figure format, default png.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    horizon_files = {
        "0m": args.horizon_0m_file,
        "3m": args.horizon_3m_file,
        "6m": args.horizon_6m_file,
    }
    somalia_horizon_files = {
        "0m": args.somalia_horizon_0m_file,
        "3m": args.somalia_horizon_3m_file,
        "6m": args.somalia_horizon_6m_file,
    }
    try:
        summary = run_alert_risk_maps(
            prediction_root=args.prediction_root,
            spatial_path=args.spatial_path,
            out_report_dir=args.out_report_dir,
            out_results_dir=args.out_results_dir,
            horizon_files=horizon_files,
            somalia_horizon_files=somalia_horizon_files,
            overwrite=args.overwrite,
            write_summary=args.write_validation_summary,
            no_basemap=args.no_basemap,
            figure_format=args.figure_format,
        )
    except AlertRiskMapError as exc:
        print(f"Validation error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Unexpected error: {exc}", file=sys.stderr)
        return 1
    print("Generated 2025 IPCCH alert risk maps.")
    for key, output in summary.output_paths.items():
        print(f"{key}: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
