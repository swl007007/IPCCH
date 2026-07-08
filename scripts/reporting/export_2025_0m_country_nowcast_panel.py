from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = next(path for path in Path(__file__).resolve().parents if (path / "src").exists())
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from ipcch.nowcast_panel_export import (  # noqa: E402
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
