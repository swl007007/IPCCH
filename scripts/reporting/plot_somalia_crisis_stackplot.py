import argparse
import sys
from pathlib import Path

PROJECT_ROOT = next(path for path in Path(__file__).resolve().parents if (path / "src").exists())
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import matplotlib

matplotlib.use("Agg")

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

from ipcch import paths

DEFAULT_DATASET = paths.external_path("deep_features_forecasting_dataset")
DEFAULT_LOOKUP_SOURCE = paths.external_path("ipcch_2026_completed_dataset")
DEFAULT_ASSEMBLED_DIR = DEFAULT_LOOKUP_SOURCE.parents[1]
DEFAULT_LOOKUP_OUTPUT = DEFAULT_ASSEMBLED_DIR / "country_area_id_lookup.csv"
DEFAULT_OUTPUT_DIR = paths.REPORTS_DIR / "figures" / "somalia_crisis_stackplot"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plot Somalia crisis vs non-crisis stack plot by date.")
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET), help="Model-ready forecasting dataset CSV.")
    parser.add_argument("--lookup-source", default=str(DEFAULT_LOOKUP_SOURCE), help="Raw IPCCH completed CSV with country and area ID columns.")
    parser.add_argument("--lookup-output", default=str(DEFAULT_LOOKUP_OUTPUT), help="Country-area lookup CSV to create or refresh.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Directory for plot and aggregated data outputs.")
    parser.add_argument("--country-iso3", default="SOM", help="ISO3 country code to plot.")
    parser.add_argument("--country-name", default="Somalia", help="Country name used as a fallback filter and plot title.")
    parser.add_argument("--min-total", type=int, default=10, help="Drop quarters with fewer than this many area-month observations.")
    return parser.parse_args()


def first_valid(values: pd.Series):
    values = values.dropna()
    if values.empty:
        return None
    return values.iloc[0]


def build_country_area_lookup(source_path: Path, output_path: Path) -> pd.DataFrame:
    source_df = pd.read_csv(
        source_path,
        usecols=lambda column: column in {"area_id", "admin_code", "ISO3", "country", "country_code", "country_en"},
    )
    if "area_id" not in source_df.columns:
        if "admin_code" not in source_df.columns:
            raise ValueError("Lookup source must contain area_id or admin_code.")
        source_df = source_df.rename(columns={"admin_code": "area_id"})

    for column in ["ISO3", "country", "country_code", "country_en"]:
        if column not in source_df.columns:
            source_df[column] = None

    lookup = (
        source_df.dropna(subset=["area_id"])
        .groupby("area_id", as_index=False)
        .agg({"ISO3": first_valid, "country": first_valid, "country_code": first_valid, "country_en": first_valid})
        .rename(columns={"ISO3": "iso3"})
    )
    lookup = lookup[["area_id", "iso3", "country", "country_code", "country_en"]].sort_values("area_id")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lookup.to_csv(output_path, index=False)
    return lookup


def load_somalia_area_ids(lookup: pd.DataFrame, country_iso3: str, country_name: str) -> set[str]:
    iso3 = country_iso3.strip().upper()
    normalized_name = country_name.strip().lower()
    matches = pd.Series(False, index=lookup.index)
    if "iso3" in lookup.columns:
        matches |= lookup["iso3"].astype(str).str.strip().str.upper().eq(iso3)
    for column in ["country", "country_en", "country_code"]:
        if column in lookup.columns:
            matches |= lookup[column].astype(str).str.strip().str.lower().eq(normalized_name)
    area_ids = set(lookup.loc[matches, "area_id"].dropna().astype(str))
    if not area_ids:
        raise ValueError(f"No area IDs found for {country_name} ({country_iso3}).")
    return area_ids


def load_country_model_rows(dataset_path: Path, area_ids: set[str]) -> pd.DataFrame:
    required_columns = ["area_id", "year", "month", "overall_phase"]
    df = pd.read_csv(dataset_path, usecols=required_columns)
    df = df[df["area_id"].astype(str).isin(area_ids)].copy()
    if df.empty:
        raise ValueError("No model-ready rows match the selected country area IDs.")
    df = df.dropna(subset=["year", "month", "overall_phase"])
    df["date"] = pd.to_datetime(
        {"year": df["year"].astype(int), "month": df["month"].astype(int), "day": 1},
        errors="coerce",
    )
    df = df.dropna(subset=["date"])
    return df


def aggregate_crisis_counts(df: pd.DataFrame, min_total: int) -> pd.DataFrame:
    df = df.copy()
    df["quarter"] = df["date"].dt.to_period("Q")
    df["quarter_start"] = df["quarter"].dt.start_time
    df["crisis_status"] = df["overall_phase"].astype(float).ge(3).map({True: "crisis", False: "non_crisis"})
    aggregated = (
        df.groupby(["quarter", "quarter_start", "crisis_status"])
        .size()
        .unstack(fill_value=0)
        .rename_axis(columns=None)
        .reset_index()
        .sort_values("quarter_start")
    )
    for column in ["crisis", "non_crisis"]:
        if column not in aggregated.columns:
            aggregated[column] = 0
    aggregated = aggregated.rename(columns={"quarter_start": "date"})
    aggregated["quarter"] = aggregated["quarter"].astype(str)
    aggregated = aggregated[["quarter", "date", "crisis", "non_crisis"]]
    aggregated["total"] = aggregated["crisis"] + aggregated["non_crisis"]
    if min_total > 0:
        aggregated = aggregated[aggregated["total"] >= min_total].copy()
    if aggregated.empty:
        raise ValueError(f"No quarters remain after applying --min-total {min_total}.")
    aggregated["crisis_share"] = aggregated["crisis"] / aggregated["total"]
    aggregated["non_crisis_share"] = aggregated["non_crisis"] / aggregated["total"]
    return aggregated


def plot_stack(aggregated: pd.DataFrame, output_path: Path, country_name: str) -> None:
    fig, ax = plt.subplots(figsize=(13, 7))
    dates = pd.to_datetime(aggregated["date"])
    ax.stackplot(
        dates,
        aggregated["crisis"],
        aggregated["non_crisis"],
        labels=["Crisis: overall_phase >= 3", "Non-crisis: overall_phase < 3"],
        colors=["#c44e52", "#4c72b0"],
        alpha=0.85,
    )
    ax.set_title(f"{country_name}: Quarterly Crisis and Non-crisis Observations")
    ax.set_xlabel("Quarter")
    ax.set_ylabel("Number of area-month observations per quarter")
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.legend(loc="upper left")
    ax.grid(axis="y", alpha=0.3)
    fig.autofmt_xdate()
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=300)
    plt.close(fig)


def main() -> None:
    args = parse_args()
    dataset_path = Path(args.dataset).expanduser()
    lookup_source = Path(args.lookup_source).expanduser()
    lookup_output = Path(args.lookup_output).expanduser()
    output_dir = Path(args.output_dir).expanduser()

    lookup = build_country_area_lookup(lookup_source, lookup_output)
    area_ids = load_somalia_area_ids(lookup, args.country_iso3, args.country_name)
    country_df = load_country_model_rows(dataset_path, area_ids)
    aggregated = aggregate_crisis_counts(country_df, args.min_total)

    output_dir.mkdir(parents=True, exist_ok=True)
    data_output = output_dir / "somalia_quarterly_crisis_stackplot_data.csv"
    plot_output = output_dir / "somalia_quarterly_crisis_stackplot.png"
    aggregated.to_csv(data_output, index=False)
    plot_stack(aggregated, plot_output, args.country_name)

    print(f"Saved lookup: {lookup_output}")
    print(f"Saved aggregated data: {data_output}")
    print(f"Saved stack plot: {plot_output}")
    print(f"Somalia area IDs: {len(area_ids):,}")
    print(f"Somalia model-ready rows: {len(country_df):,}")
    print(f"Minimum quarter total: {args.min_total:,}")
    print(f"Quarters plotted: {len(aggregated):,}")


if __name__ == "__main__":
    main()
