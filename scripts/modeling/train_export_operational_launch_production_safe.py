#!/usr/bin/env python
"""Train and export production-safe operational launch models.

This exporter is intentionally narrower than the research launch pipeline: it
uses only columns available in the monthly production input table, excludes
target/outcome fields from model features, aligns horizon labels from historical
future outcomes, and writes the pure-inference package consumed by
``IPCCH_monthly_operational``.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from xgboost import XGBRegressor  # noqa: E402

from ipcch import operational_contract as oc  # noqa: E402


SCOPES = (0, 6, 12)
TARGET_PERCENT_COLUMNS = (
    "phase1_percent",
    "phase2_percent",
    "phase3_percent",
    "phase4_percent",
    "phase5_percent",
)
TARGET_COLUMNS = (
    "phase2_worse",
    "phase3_worse",
    "phase4_worse",
    "phase5_worse",
)
TARGET_FORMULAS = {
    "phase2_worse": ("phase2_percent", "phase3_percent", "phase4_percent", "phase5_percent"),
    "phase3_worse": ("phase3_percent", "phase4_percent", "phase5_percent"),
    "phase4_worse": ("phase4_percent", "phase5_percent"),
    "phase5_worse": ("phase5_percent",),
}
TARGET_AND_LABEL_COLUMNS = {
    "overall_phase",
    "overall_phase_pred",
    *TARGET_PERCENT_COLUMNS,
    *TARGET_COLUMNS,
}
IDENTIFIER_COLUMNS = {
    "area_id",
    "admin_code",
    "pcode",
    "iso3",
    "iso",
}
TIME_COLUMNS = {"year", "month", "date", "feature_period", "target_period"}
REPORTING_TEXT_COLUMNS = {
    "ISO3",
    "country",
    "country_code",
    "country_en",
    "state",
    "address",
    "name",
    "region",
}
PRODUCTION_METADATA_COLUMNS = {
    "source_row_count",
    "first_year_month",
    "last_year_month",
}
EXCLUDED_COLUMNS = (
    TARGET_AND_LABEL_COLUMNS
    | IDENTIFIER_COLUMNS
    | TIME_COLUMNS
    | REPORTING_TEXT_COLUMNS
    | PRODUCTION_METADATA_COLUMNS
)


@dataclass(frozen=True)
class ScopeTrainingResult:
    scope_months: int
    train_rows: int
    feature_count: int
    train_min_feature_month: str
    train_max_feature_month: str
    target_min_month: str
    target_max_month: str


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train production-safe 0/6/12m operational launch models."
    )
    parser.add_argument("--raw-csv", required=True, type=Path)
    parser.add_argument("--production-input", required=True, type=Path)
    parser.add_argument("--output-package", required=True, type=Path)
    parser.add_argument("--feature-month", default="2026-04")
    parser.add_argument("--package-id", default="launch_2026_04")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--n-estimators", type=int, default=200)
    parser.add_argument("--max-depth", type=int, default=6)
    parser.add_argument("--learning-rate", type=float, default=0.08)
    parser.add_argument("--subsample", type=float, default=0.9)
    parser.add_argument("--colsample-bytree", type=float, default=0.8)
    parser.add_argument("--n-jobs", type=int, default=4)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        summary_path = train_and_export(args)
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(summary_path)
    return 0


def train_and_export(args: argparse.Namespace) -> Path:
    if not args.raw_csv.exists():
        raise FileNotFoundError(f"raw CSV not found: {args.raw_csv}")
    if not args.production_input.exists():
        raise FileNotFoundError(f"production input not found: {args.production_input}")
    if args.output_package.exists():
        if not args.overwrite:
            raise FileExistsError(
                f"output package already exists; pass --overwrite: {args.output_package}"
            )
        shutil.rmtree(args.output_package)

    feature_month = _normalize_feature_month(args.feature_month)
    target_periods = oc.target_periods_for_feature_month(feature_month, SCOPES)
    production_columns = pd.read_csv(args.production_input, nrows=0).columns.tolist()
    raw_columns = pd.read_csv(args.raw_csv, nrows=0).columns.tolist()
    feature_columns = select_production_safe_feature_columns(
        production_columns=production_columns,
        raw_columns=raw_columns,
        production_input=args.production_input,
    )
    if not feature_columns:
        raise ValueError("no production-safe feature columns selected")

    source = load_source(args.raw_csv, feature_columns)
    source = add_targets(source)
    train_cutoff = pd.Period(feature_month, freq="M")

    args.output_package.mkdir(parents=True)
    scope_summaries = []
    for scope in SCOPES:
        scope_dir = args.output_package / f"scope_{scope}m"
        scope_dir.mkdir()
        training_frame = build_training_frame(source, feature_columns, scope, train_cutoff)
        if training_frame.empty:
            raise ValueError(f"scope_{scope}m training frame is empty")

        usable_features, medians = fit_scope_models(
            training_frame=training_frame,
            feature_columns=feature_columns,
            scope_dir=scope_dir,
            args=args,
        )
        write_feature_contract(scope_dir / "feature_contract.csv", usable_features, scope)
        write_json(scope_dir / "feature_columns.json", usable_features)
        metadata = {
            "package_id": args.package_id,
            "model_package_id": args.package_id,
            "scope_months": scope,
            "feature_month": feature_month,
            "target_month": target_periods[scope],
            "thresholds": {"default": 0.2},
            "monotonicity_policy": "cummax",
            "feature_policy": "production_safe_monthly_input_direct_numeric_with_training_median_impute",
            "imputation_statistics": {
                f"median:{feature}": float(medians[feature])
                for feature in usable_features
            },
            "training_source": str(args.raw_csv),
            "production_input_contract_source": str(args.production_input),
            "excluded_columns": sorted(EXCLUDED_COLUMNS),
        }
        write_json(scope_dir / "model_metadata.json", metadata)
        validation = oc.validate_feature_contract(
            pd.read_csv(scope_dir / "feature_contract.csv"), usable_features
        )
        eligibility = oc.validate_production_safe_feature_contract(
            pd.read_csv(scope_dir / "feature_contract.csv")
        )
        scope_summaries.append(
            scope_training_summary(
                scope,
                training_frame,
                usable_features,
                target_periods[scope],
                validation,
                eligibility,
            )
        )

    manifest = {
        "package_id": args.package_id,
        "created_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "feature_month": feature_month,
        "training_cutoff": train_cutoff.start_time.strftime("%Y-%m-%d"),
        "target_periods": {str(scope): target_periods[scope] for scope in SCOPES},
        "scopes": list(SCOPES),
        "forecasted_weather": {"enabled": False},
        "model_output_semantics": {
            target: "estimated population share in phase >= {0}".format(index)
            for target, index in zip(TARGET_COLUMNS, range(2, 6))
        },
        "feature_selection": {
            "policy": "intersection of raw completed panel and monthly production input, numeric only, target/id/reporting columns excluded",
            "selected_feature_count_by_scope": {
                str(row.scope_months): row.feature_count for row in scope_summaries
            },
        },
    }
    write_json(args.output_package / "model_package_manifest.json", manifest)
    summary = {
        "status": "passed",
        "package": str(args.output_package),
        "manifest": manifest,
        "scope_summaries": [row.__dict__ for row in scope_summaries],
    }
    summary_path = args.output_package / "training_export_summary.json"
    write_json(summary_path, summary)
    return summary_path


def select_production_safe_feature_columns(
    *,
    production_columns: Sequence[str],
    raw_columns: Sequence[str],
    production_input: Path,
) -> list[str]:
    common = [
        column
        for column in production_columns
        if column in set(raw_columns) and column not in EXCLUDED_COLUMNS
    ]
    sample = pd.read_csv(production_input, usecols=common, nrows=500)
    selected = []
    for column in common:
        numeric = pd.to_numeric(sample[column], errors="coerce")
        invalid = sample[column].notna() & numeric.isna()
        if not invalid.any():
            selected.append(column)
    return selected


def load_source(raw_csv: Path, feature_columns: Sequence[str]) -> pd.DataFrame:
    usecols = ["admin_code", "year", "month", *TARGET_PERCENT_COLUMNS, *feature_columns]
    source = pd.read_csv(raw_csv, usecols=usecols, dtype={"admin_code": "string"})
    source = source.replace([np.inf, -np.inf], np.nan)
    source["area_id"] = source["admin_code"].astype("string").str.strip()
    source["year"] = pd.to_numeric(source["year"], errors="raise").astype(int)
    source["month"] = pd.to_numeric(source["month"], errors="raise").astype(int)
    source["period"] = pd.PeriodIndex(
        source["year"].astype(str) + "-" + source["month"].astype(str).str.zfill(2),
        freq="M",
    )
    for column in [*TARGET_PERCENT_COLUMNS, *feature_columns]:
        source[column] = pd.to_numeric(source[column], errors="coerce")
    duplicate_keys = source.duplicated(["area_id", "period"], keep=False)
    if duplicate_keys.any():
        examples = (
            source.loc[duplicate_keys, ["area_id", "period"]]
            .astype(str)
            .drop_duplicates()
            .head(10)
            .to_dict("records")
        )
        raise ValueError(f"raw source has duplicate area_id/month keys, e.g. {examples}")
    return source


def add_targets(source: pd.DataFrame) -> pd.DataFrame:
    result = source.copy()
    for target, columns in TARGET_FORMULAS.items():
        result[target] = result.loc[:, list(columns)].sum(axis=1, min_count=len(columns))
    return result


def build_training_frame(
    source: pd.DataFrame,
    feature_columns: Sequence[str],
    scope: int,
    train_cutoff: pd.Period,
) -> pd.DataFrame:
    labels = source.dropna(subset=list(TARGET_COLUMNS)).loc[
        :, ["area_id", "period", *TARGET_COLUMNS]
    ].copy()
    labels = labels.rename(columns={"period": "target_period"})
    labels["feature_period"] = labels["target_period"].map(
        lambda period: pd.Period(period, freq="M") - int(scope)
    )

    features = source.loc[:, ["area_id", "period", *feature_columns]].copy()
    features = features.rename(columns={"period": "feature_period"})
    train = features.merge(
        labels,
        on=["area_id", "feature_period"],
        how="inner",
        validate="one_to_one",
    )
    train = train[train["feature_period"] < train_cutoff].copy()
    train = train.sort_values(["feature_period", "area_id"]).reset_index(drop=True)
    return train


def fit_scope_models(
    *,
    training_frame: pd.DataFrame,
    feature_columns: Sequence[str],
    scope_dir: Path,
    args: argparse.Namespace,
) -> tuple[list[str], pd.Series]:
    medians = training_frame.loc[:, list(feature_columns)].median(numeric_only=True)
    usable_features = [feature for feature in feature_columns if pd.notna(medians.get(feature))]
    if not usable_features:
        raise ValueError("all selected feature medians are missing")
    X = training_frame.loc[:, usable_features].fillna(medians.loc[usable_features])
    for target in TARGET_COLUMNS:
        ready = training_frame[target].notna()
        if not ready.any():
            raise ValueError(f"no training rows for {target}")
        model = XGBRegressor(
            objective="reg:squarederror",
            n_estimators=args.n_estimators,
            max_depth=args.max_depth,
            learning_rate=args.learning_rate,
            subsample=args.subsample,
            colsample_bytree=args.colsample_bytree,
            random_state=args.seed,
            n_jobs=args.n_jobs,
        )
        model.fit(X.loc[ready], training_frame.loc[ready, target])
        model.save_model(str(scope_dir / f"{target}_model.json"))
    return usable_features, medians.loc[usable_features]


def write_feature_contract(path: Path, feature_columns: Sequence[str], scope: int) -> None:
    rows = []
    for feature in feature_columns:
        rows.append(
            {
                "feature_name": feature,
                "scope_months": str(scope),
                "category": "median_impute",
                "source_column": feature,
                "dtype": "float",
                "required_in_input": True,
                "missing_tolerance": 0.0,
                "fill_method": "median",
                "fill_value_or_stat_key": f"median:{feature}",
                "lookup_asset": "",
                "derive_function": "",
                "as_of_policy": "feature_month_end",
                "notes": "Direct numeric monthly production input feature; missing values filled with training-period median stored in model metadata.",
            }
        )
    pd.DataFrame(rows).to_csv(path, index=False)


def scope_training_summary(
    scope: int,
    training_frame: pd.DataFrame,
    feature_columns: Sequence[str],
    target_month: str,
    validation: dict[str, object],
    eligibility: dict[str, object],
) -> ScopeTrainingResult:
    feature_periods = training_frame["feature_period"].astype(str)
    target_periods = training_frame["target_period"].astype(str)
    return ScopeTrainingResult(
        scope_months=scope,
        train_rows=int(len(training_frame)),
        feature_count=int(len(feature_columns)),
        train_min_feature_month=str(feature_periods.min()),
        train_max_feature_month=str(feature_periods.max()),
        target_min_month=str(target_periods.min()),
        target_max_month=str(target_periods.max()),
    )


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _normalize_feature_month(value: str) -> str:
    text = str(value).strip()
    if len(text) == 6 and text.isdigit():
        text = f"{text[:4]}-{text[4:]}"
    oc.training_cutoff_for_feature_month(text)
    return text


if __name__ == "__main__":
    raise SystemExit(main())
