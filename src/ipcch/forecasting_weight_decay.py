from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, r2_score

from ipcch import paths

DEFAULT_TEST_YEARS = (2022, 2023, 2024, 2025)
DEFAULT_HALF_LIFE_MONTHS = 24.0
DEFAULT_PHASE_THRESHOLD = 0.2
PERCENT_TARGET_COLUMNS = (
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
REQUIRED_COLUMNS = ("area_id", "year", "month", "overall_phase", *PERCENT_TARGET_COLUMNS)
METRIC_NAMES = (
    "accuracy",
    "precision_phase3plus",
    "sensitivity_phase3plus",
    "r2_phase3plus",
    "f2_phase3plus",
)
DEFAULT_DATASET_KEY = "deep_features_forecasting_dataset"
DEFAULT_SOMALIA_LOOKUP_KEY = "ipcch_2026_completed_dataset"
SPLIT_RULE = "all-prior-history annual holdout: train date < January 1 of test year; test rows in test calendar year"
DECAY_FORMULATION = "weight = 0.5 ** (distance_months / half_life_months)"


@dataclass(frozen=True)
class OutputPlan:
    base_dir: Path
    prediction_dir: Path
    metrics_dir: Path
    metadata_dir: Path
    report_dir: Path
    prediction_paths: Mapping[int, Path]
    metrics_json_paths: Mapping[int, Path]
    metrics_overall_csv: Path
    metrics_somalia_csv: Path
    split_diagnostics_csv: Path
    run_metadata_json: Path
    summary_report: Path
    report_metrics_overall_csv: Path
    report_metrics_somalia_csv: Path


def resolve_input_path(explicit_path: Optional[str], key: str) -> Path:
    if explicit_path:
        resolved = Path(explicit_path).expanduser()
    else:
        try:
            resolved = paths.external_path(key)
        except KeyError as exc:
            raise ValueError(f"Missing external path key '{key}' in ipcch.paths or configs/paths.local.json") from exc
    if not resolved.exists():
        raise FileNotFoundError(f"Input path does not exist: {resolved}")
    return resolved


def validate_required_columns(df: pd.DataFrame, required_columns: Sequence[str] = REQUIRED_COLUMNS) -> None:
    missing = [column for column in required_columns if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")


def add_monthly_date(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    try:
        year = pd.to_numeric(result["year"], errors="raise").astype("Int64")
        month = pd.to_numeric(result["month"], errors="raise").astype("Int64")
        result["date"] = pd.to_datetime(
            {"year": year.astype(int), "month": month.astype(int), "day": 1},
            errors="raise",
        )
    except Exception as exc:
        raise ValueError("Invalid year/month values; cannot create monthly date") from exc
    if result["date"].isna().any():
        raise ValueError("Invalid year/month values produced missing dates")
    return result


def derive_cumulative_targets(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    for column in PERCENT_TARGET_COLUMNS:
        result[column] = pd.to_numeric(result[column], errors="coerce")
    result["phase2_worse"] = result["phase2_percent"] + result["phase3_percent"] + result["phase4_percent"] + result["phase5_percent"]
    result["phase3_worse"] = result["phase3_percent"] + result["phase4_percent"] + result["phase5_percent"]
    result["phase4_worse"] = result["phase4_percent"] + result["phase5_percent"]
    result["phase5_worse"] = result["phase5_percent"]
    return result


def prepare_forecasting_dataset(df: pd.DataFrame) -> pd.DataFrame:
    validate_required_columns(df)
    result = df.replace([np.inf, -np.inf], np.nan).copy()
    result = add_monthly_date(result)
    result = derive_cumulative_targets(result)
    result["overall_phase"] = pd.to_numeric(result["overall_phase"], errors="coerce")
    result = result.sort_values(["area_id", "date"]).reset_index(drop=True)
    return result


def add_identifier_features(df: pd.DataFrame, lookup_df: pd.DataFrame) -> pd.DataFrame:
    required_lookup = {"admin_code", "year", "month", "lat", "lon"}
    missing = sorted(required_lookup - set(lookup_df.columns))
    if missing:
        raise ValueError("Identifier source is missing required columns: " + ", ".join(missing))

    result = df.copy()
    result["_merge_area_id"] = result["area_id"].astype(str)
    result["_merge_year"] = pd.to_numeric(result["year"], errors="raise").astype(int)
    result["_merge_month"] = pd.to_numeric(result["month"], errors="raise").astype(int)

    lookup = lookup_df[["admin_code", "year", "month", "lat", "lon"]].copy()
    lookup["_merge_area_id"] = lookup["admin_code"].astype(str)
    lookup["_merge_year"] = pd.to_numeric(lookup["year"], errors="raise").astype(int)
    lookup["_merge_month"] = pd.to_numeric(lookup["month"], errors="raise").astype(int)
    lookup["lat"] = pd.to_numeric(lookup["lat"], errors="coerce")
    lookup["lon"] = pd.to_numeric(lookup["lon"], errors="coerce")
    lookup = lookup.dropna(subset=["lat", "lon"])
    lookup = lookup.drop_duplicates(["_merge_area_id", "_merge_year", "_merge_month"])

    result = result.merge(
        lookup[["_merge_area_id", "_merge_year", "_merge_month", "lat", "lon"]],
        on=["_merge_area_id", "_merge_year", "_merge_month"],
        how="left",
        validate="many_to_one",
    )
    if result[["lat", "lon"]].isna().any().any():
        missing_count = int(result[["lat", "lon"]].isna().any(axis=1).sum())
        raise ValueError(f"Identifier merge produced missing lat/lon for {missing_count} rows")

    month_dummies = pd.get_dummies(result["_merge_month"], prefix="month", dtype=bool)
    year_dummies = pd.get_dummies(result["_merge_year"], prefix="year", dtype=bool)
    result = pd.concat([result, month_dummies, year_dummies], axis=1)
    return result.drop(columns=["_merge_area_id", "_merge_year", "_merge_month"])


def validate_phase_threshold(phase_threshold: float) -> None:
    if not math.isfinite(float(phase_threshold)) or not 0 < float(phase_threshold) < 1:
        raise ValueError("phase threshold must be finite and between 0 and 1")


def select_numeric_feature_columns(df: pd.DataFrame) -> List[str]:
    numeric_columns = list(df.select_dtypes(include=[np.number, "bool"]).columns)
    exact_exclusions = {
        "area_id",
        "year",
        "month",
        "date",
        "overall_phase",
        "test_year",
        "scope",
        "status",
        "unavailable_reason",
        *PERCENT_TARGET_COLUMNS,
        *TARGET_COLUMNS,
    }
    blocked_patterns = (
        r"(^|_)id$",
        r"(^|_)code$",
        r"^adm[0-9]?(_|$)",
        r"country",
        r"region",
        r"iso",
        r"pcode",
        r"^overall_phase($|_pred$|_test$)",
        r"(^|_)target($|_)",
        r"(^|_)label($|_)",
        r"(^|_)pred($|_)",
        r"prediction",
        r"phase[1-5]_percent",
        r"phase[1-5]_worse",
        r"phase[1-5]_test",
        r"phase[1-5]_pred",
    )
    features = []
    for column in numeric_columns:
        lower = column.lower()
        if lower in exact_exclusions:
            continue
        if any(re.search(pattern, lower) for pattern in blocked_patterns):
            continue
        features.append(column)
    if not features:
        raise ValueError("No eligible numeric feature columns found after excluding identifiers, dates, targets, and prediction fields")
    return features


def validate_test_years(test_years: Sequence[int]) -> Tuple[int, ...]:
    years = tuple(int(year) for year in test_years)
    if years != DEFAULT_TEST_YEARS:
        expected = ", ".join(str(year) for year in DEFAULT_TEST_YEARS)
        received = ", ".join(str(year) for year in years)
        raise ValueError(f"This feature requires exactly test years {expected}; received {received}")
    return years


def annual_splits(df: pd.DataFrame, test_years: Sequence[int] = DEFAULT_TEST_YEARS) -> Dict[int, Tuple[pd.DataFrame, pd.DataFrame]]:
    splits = {}
    for year in validate_test_years(test_years):
        start = pd.Timestamp(year=year, month=1, day=1)
        end = pd.Timestamp(year=year + 1, month=1, day=1)
        train_df = df[df["date"] < start].copy()
        test_df = df[(df["date"] >= start) & (df["date"] < end)].copy()
        splits[year] = (train_df, test_df)
    return splits


def split_diagnostics(splits: Mapping[int, Tuple[pd.DataFrame, pd.DataFrame]]) -> pd.DataFrame:
    rows = []
    for year, (train_df, test_df) in splits.items():
        test_start = pd.Timestamp(year=year, month=1, day=1)
        max_train_date = train_df["date"].max() if len(train_df) else pd.NaT
        rows.append(
            {
                "test_year": year,
                "train_rows": len(train_df),
                "test_rows": len(test_df),
                "train_min_date": _format_date(train_df["date"].min() if len(train_df) else pd.NaT),
                "train_max_date": _format_date(max_train_date),
                "test_min_date": _format_date(test_df["date"].min() if len(test_df) else pd.NaT),
                "test_max_date": _format_date(test_df["date"].max() if len(test_df) else pd.NaT),
                "test_start_date": test_start.date().isoformat(),
                "max_training_before_test": bool(pd.notna(max_train_date) and max_train_date < test_start),
            }
        )
    return pd.DataFrame(rows)


def _format_date(value: pd.Timestamp) -> Optional[str]:
    if pd.isna(value):
        return None
    return pd.Timestamp(value).date().isoformat()


def month_distances(dates: pd.Series, test_year: int) -> pd.Series:
    test_start = pd.Timestamp(year=test_year, month=1, day=1)
    normalized = pd.to_datetime(dates).dt.to_period("M").dt.to_timestamp()
    distances = (test_start.year - normalized.dt.year) * 12 + (test_start.month - normalized.dt.month)
    return distances.astype(int)


def time_decay_weights(dates: pd.Series, test_year: int, half_life_months: float = DEFAULT_HALF_LIFE_MONTHS) -> pd.Series:
    validate_half_life(half_life_months)
    distances = month_distances(dates, test_year)
    if (distances <= 0).any():
        raise ValueError(f"Invalid training dates for {test_year}; all month distances must be positive")
    weights = np.power(0.5, distances.astype(float) / float(half_life_months))
    weights = pd.Series(weights, index=dates.index, name="sample_weight")
    validate_weights(weights)
    return weights


def validate_half_life(half_life_months: float) -> None:
    if not math.isfinite(float(half_life_months)) or float(half_life_months) <= 0:
        raise ValueError("half-life months must be positive and finite")


def validate_weights(weights: pd.Series) -> None:
    values = weights.to_numpy(dtype=float)
    if not np.isfinite(values).all() or (values <= 0).any():
        raise ValueError("sample_weight contains NaN, infinite, zero, or negative values")


def weight_diagnostics(train_df: pd.DataFrame, test_year: int, weights: pd.Series) -> Dict[str, object]:
    distances = month_distances(train_df.loc[weights.index, "date"], test_year)
    diagnostic = pd.DataFrame({"distance_months": distances, "weight": weights})
    grouped = diagnostic.groupby("distance_months", as_index=False)["weight"].mean().sort_values("distance_months")
    monotonic = bool(grouped["weight"].is_monotonic_decreasing)
    return {
        "test_year": test_year,
        "weight_min": float(weights.min()) if len(weights) else None,
        "weight_max": float(weights.max()) if len(weights) else None,
        "min_distance_months": int(distances.min()) if len(distances) else None,
        "max_distance_months": int(distances.max()) if len(distances) else None,
        "newer_rows_have_larger_weights": monotonic,
    }


def prepare_target_matrices(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    feature_columns: Sequence[str],
    target_column: str,
    weights: pd.Series,
) -> Tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series, pd.Series]:
    if target_column not in TARGET_COLUMNS:
        raise ValueError(f"Unsupported target column: {target_column}")
    train_ready = train_df.dropna(subset=[target_column])
    test_ready = test_df.dropna(subset=[target_column])
    aligned_weights = weights.reindex(train_ready.index)
    if aligned_weights.isna().any():
        raise ValueError(f"sample_weight alignment failed for {target_column}")
    validate_weights(aligned_weights)
    return (
        train_ready.loc[:, feature_columns],
        train_ready[target_column],
        test_ready.loc[:, feature_columns],
        test_ready[target_column],
        aligned_weights,
    )


def metric_value(value: Optional[float], status: str = "ok", reason: Optional[str] = None) -> Dict[str, object]:
    if status == "ok":
        return {"value": float(value), "status": "ok", "reason": None}
    return {"value": None, "status": status, "reason": reason or "unavailable"}


def unavailable_metrics(test_year: int, scope: str, reason: str) -> Dict[str, object]:
    result = {"test_year": int(test_year), "scope": scope, "n_samples": 0, "status": "no eligible samples"}
    for metric in METRIC_NAMES:
        result[metric] = metric_value(None, "unavailable", reason)
    return result


def compute_metrics(predictions: pd.DataFrame, test_year: int, scope: str) -> Dict[str, object]:
    if len(predictions) == 0:
        return unavailable_metrics(test_year, scope, "no eligible samples")
    result: Dict[str, object] = {"test_year": int(test_year), "scope": scope, "n_samples": int(len(predictions)), "status": "completed"}

    class_df = predictions.dropna(subset=["overall_phase", "overall_phase_pred"])
    if len(class_df) == 0:
        result["accuracy"] = metric_value(None, "unavailable", "no valid observed and predicted phase labels")
    else:
        result["accuracy"] = metric_value(accuracy_score(class_df["overall_phase"], class_df["overall_phase_pred"]))

    if len(class_df) == 0:
        observed_positive = pd.Series(dtype=bool)
        predicted_positive = pd.Series(dtype=bool)
    else:
        observed_positive = class_df["overall_phase"].astype(float) >= 3
        predicted_positive = class_df["overall_phase_pred"].astype(float) >= 3

    true_positive = int((observed_positive & predicted_positive).sum()) if len(class_df) else 0
    predicted_denominator = int(predicted_positive.sum()) if len(class_df) else 0
    observed_denominator = int(observed_positive.sum()) if len(class_df) else 0

    if predicted_denominator == 0:
        result["precision_phase3plus"] = metric_value(None, "unavailable", "zero predicted phase3plus denominator")
    else:
        result["precision_phase3plus"] = metric_value(true_positive / predicted_denominator)

    if observed_denominator == 0:
        result["sensitivity_phase3plus"] = metric_value(None, "unavailable", "zero observed phase3plus denominator")
    else:
        result["sensitivity_phase3plus"] = metric_value(true_positive / observed_denominator)

    precision = result["precision_phase3plus"]["value"]
    recall = result["sensitivity_phase3plus"]["value"]
    if precision is None or recall is None:
        result["f2_phase3plus"] = metric_value(None, "unavailable", "precision or recall unavailable")
    elif (4 * precision + recall) == 0:
        result["f2_phase3plus"] = metric_value(None, "unavailable", "zero f2 denominator")
    else:
        result["f2_phase3plus"] = metric_value((5 * precision * recall) / (4 * precision + recall))

    r2_df = predictions.dropna(subset=["phase3_worse", "phase3_pred"])
    if len(r2_df) < 2:
        result["r2_phase3plus"] = metric_value(None, "unavailable", "fewer than two valid samples")
    elif r2_df["phase3_worse"].nunique(dropna=True) < 2:
        result["r2_phase3plus"] = metric_value(None, "unavailable", "constant target")
    else:
        result["r2_phase3plus"] = metric_value(r2_score(r2_df["phase3_worse"], r2_df["phase3_pred"]))

    return result


def flatten_metric_result(result: Mapping[str, object]) -> Dict[str, object]:
    row = {
        "scope": result["scope"],
        "test_year": result["test_year"],
        "n_samples": result["n_samples"],
    }
    csv_prefixes = {
        "accuracy": "accuracy",
        "precision_phase3plus": "precision",
        "sensitivity_phase3plus": "sensitivity",
        "r2_phase3plus": "r2",
        "f2_phase3plus": "f2",
    }
    for metric, prefix in csv_prefixes.items():
        value = result[metric]
        row[metric] = value["value"]
        row[f"{prefix}_status"] = value["status"]
        row[f"{prefix}_reason"] = value["reason"]
    return row


def plan_outputs(base_dir: Optional[str] = None, report_dir: Optional[str] = None, test_years: Sequence[int] = DEFAULT_TEST_YEARS) -> OutputPlan:
    base = Path(base_dir).expanduser() if base_dir else paths.RESULTS_DIR / "experiments" / "deep_feature_weight_decay_forecasting"
    report = Path(report_dir).expanduser() if report_dir else paths.REPORTS_DIR / "deep_feature_weight_decay_forecasting"
    prediction_dir = base / "predictions"
    metrics_dir = base / "metrics"
    metadata_dir = base / "metadata"
    years = validate_test_years(test_years)
    return OutputPlan(
        base_dir=base,
        prediction_dir=prediction_dir,
        metrics_dir=metrics_dir,
        metadata_dir=metadata_dir,
        report_dir=report,
        prediction_paths={year: prediction_dir / f"predictions_{year}.csv" for year in years},
        metrics_json_paths={year: metrics_dir / f"metrics_{year}.json" for year in years},
        metrics_overall_csv=metrics_dir / "metrics_overall.csv",
        metrics_somalia_csv=metrics_dir / "metrics_somalia.csv",
        split_diagnostics_csv=metadata_dir / "split_diagnostics.csv",
        run_metadata_json=metadata_dir / "run_metadata.json",
        summary_report=report / "summary.md",
        report_metrics_overall_csv=report / "metrics_overall.csv",
        report_metrics_somalia_csv=report / "metrics_somalia.csv",
    )


def ensure_output_dirs(output_plan: OutputPlan) -> None:
    for directory in (output_plan.prediction_dir, output_plan.metrics_dir, output_plan.metadata_dir, output_plan.report_dir):
        directory.mkdir(parents=True, exist_ok=True)


def check_existing_outputs(output_plan: OutputPlan, overwrite: bool, dry_run: bool) -> None:
    if overwrite or dry_run:
        return
    paths_to_check = [
        *output_plan.prediction_paths.values(),
        *output_plan.metrics_json_paths.values(),
        output_plan.metrics_overall_csv,
        output_plan.metrics_somalia_csv,
        output_plan.run_metadata_json,
        output_plan.split_diagnostics_csv,
        output_plan.summary_report,
        output_plan.report_metrics_overall_csv,
        output_plan.report_metrics_somalia_csv,
    ]
    existing = [str(path) for path in paths_to_check if path.exists()]
    if existing:
        raise FileExistsError("Output paths already exist; rerun with --overwrite to replace: " + "; ".join(existing))


def extract_somalia_area_ids(lookup_df: pd.DataFrame) -> List[object]:
    area_column = _lookup_area_id_column(lookup_df)
    iso_columns = [column for column in lookup_df.columns if column.lower() in {"iso3", "country_iso3", "iso3_code", "adm0_iso3"}]
    matches = pd.Series(False, index=lookup_df.index)
    for column in iso_columns:
        matches = matches | (lookup_df[column].astype(str).str.strip().str.upper() == "SOM")
    if not matches.any():
        country_columns = [column for column in lookup_df.columns if "country" in column.lower() or column.lower() in {"adm0_name", "admin0", "country_en"}]
        for column in country_columns:
            normalized = lookup_df[column].map(_normalize_country_name)
            matches = matches | (normalized == "somalia")
    ids = lookup_df.loc[matches, area_column].dropna().drop_duplicates().tolist()
    if not ids:
        raise ValueError("No Somalia area_id values found in lookup source")
    return ids


def _lookup_area_id_column(lookup_df: pd.DataFrame) -> str:
    for column in ("area_id", "admin_code"):
        if column in lookup_df.columns:
            return column
    raise ValueError("Somalia lookup is missing area_id or equivalent admin_code column")


def _normalize_country_name(value: object) -> str:
    return re.sub(r"\s+", " ", str(value).strip().lower())


def feature_hash_or_sample(feature_columns: Sequence[str], sample_size: int = 20) -> Dict[str, object]:
    joined = "\n".join(feature_columns)
    return {
        "sha256": hashlib.sha256(joined.encode("utf-8")).hexdigest(),
        "sample": list(feature_columns[:sample_size]),
    }


def write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2, default=_json_default), encoding="utf-8")


def _json_default(value: object) -> object:
    if isinstance(value, (np.integer, np.floating)):
        return value.item()
    if isinstance(value, (pd.Timestamp, Path)):
        return str(value)
    if pd.isna(value):
        return None
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")
