#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from ipcch import paths
from ipcch.forecasting_weight_decay import (
    DECAY_FORMULATION,
    DEFAULT_DATASET_KEY,
    DEFAULT_FS,
    DEFAULT_HALF_LIFE_MONTHS,
    DEFAULT_PHASE_THRESHOLD,
    DEFAULT_SOMALIA_LOOKUP_KEY,
    FS_DATASET_KEYS,
    FS_LABELS,
    DEFAULT_TEST_YEARS,
    METRIC_NAMES,
    SPLIT_RULE,
    TARGET_COLUMNS,
    add_identifier_features,
    annual_splits,
    check_existing_outputs,
    compute_metrics,
    ensure_output_dirs,
    extract_somalia_area_ids,
    feature_hash_or_sample,
    flatten_metric_result,
    plan_outputs,
    prepare_forecasting_dataset,
    prepare_target_matrices,
    resolve_input_path,
    select_numeric_feature_columns,
    split_diagnostics,
    time_decay_weights,
    unavailable_metrics,
    validate_half_life,
    validate_phase_threshold,
    validate_test_years,
    weight_diagnostics,
    write_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run IPCCH deep-feature annual forecasting with exponential time-decay sample weights."
    )
    parser.add_argument("--dataset", help="Path to corrected deep-feature forecasting-ready CSV. Overrides --fs and --dataset-key.")
    parser.add_argument("--dataset-key", help="ipcch.paths external key for the dataset. Overrides --fs when --dataset is omitted.")
    parser.add_argument("--fs", choices=sorted(FS_DATASET_KEYS), default=DEFAULT_FS, help="Feature-scope dataset selector: fs0=0m, fs1=3m, fs2=6m, fs3=default forecasting-ready.")
    parser.add_argument("--region-scope", type=int, choices=(0, 1), default=0, help="0=global IPC+CH rows; 1=Somalia-only rows selected by area_id before modeling.")
    parser.add_argument("--somalia-lookup", help="Path to IPCCH completed source used to derive Somalia area_id values.")
    parser.add_argument("--somalia-lookup-key", default=DEFAULT_SOMALIA_LOOKUP_KEY, help="ipcch.paths external key for Somalia lookup source.")
    parser.add_argument("--out-dir", help="Machine-readable output directory.")
    parser.add_argument("--report-dir", help="Human-readable report directory.")
    parser.add_argument("--half-life-months", type=float, default=DEFAULT_HALF_LIFE_MONTHS, help="Exponential decay half-life in months.")
    parser.add_argument("--phase-threshold", type=float, default=DEFAULT_PHASE_THRESHOLD, help="Cumulative phase prediction threshold for phase conversion.")
    parser.add_argument("--add-identifier-features", action="store_true", help="Merge lat/lon from the identifier source and add year/month dummy features.")
    parser.add_argument("--identifier-source", help="Path to IPCCH completed source with admin_code, year, month, lat, and lon.")
    parser.add_argument("--identifier-source-key", default=DEFAULT_SOMALIA_LOOKUP_KEY, help="ipcch.paths external key for the identifier source.")
    parser.add_argument("--test-years", type=int, nargs="+", default=list(DEFAULT_TEST_YEARS), help="Required annual holdout years.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for XGBoost fitting.")
    parser.add_argument("--dry-run", action="store_true", help="Validate inputs and split plan without fitting models.")
    parser.add_argument("--sample-rows", type=int, help="Limit loaded rows for lightweight validation.")
    parser.add_argument("--overwrite", action="store_true", help="Allow replacing existing outputs.")
    return parser.parse_args()


def load_dataset(path: Path, sample_rows: Optional[int], area_ids: Optional[Sequence[object]] = None) -> pd.DataFrame:
    if sample_rows is not None and sample_rows <= 0:
        raise ValueError("--sample-rows must be positive when provided")
    if not area_ids:
        if sample_rows:
            return pd.read_csv(path, nrows=sample_rows)
        return pd.read_csv(path)

    area_id_strings = {str(area_id) for area_id in area_ids}
    chunks = []
    rows_remaining = sample_rows
    for chunk in pd.read_csv(path, chunksize=100_000):
        if "area_id" not in chunk.columns:
            raise ValueError("Dataset is missing area_id; cannot apply --region-scope 1")
        matched = chunk[chunk["area_id"].astype(str).isin(area_id_strings)]
        if rows_remaining is not None:
            matched = matched.head(rows_remaining)
            rows_remaining -= len(matched)
        if not matched.empty:
            chunks.append(matched)
        if rows_remaining == 0:
            break
    if not chunks:
        raise ValueError("Region scope filter produced zero rows")
    return pd.concat(chunks, ignore_index=True)


def resolve_dataset_selection(args: argparse.Namespace) -> Tuple[Path, str]:
    if args.dataset:
        key = args.dataset_key or FS_DATASET_KEYS[args.fs]
        return resolve_input_path(args.dataset, key), key
    if args.dataset_key:
        return resolve_input_path(None, args.dataset_key), args.dataset_key
    key = FS_DATASET_KEYS[args.fs]
    return resolve_input_path(None, key), key


def default_experiment_name(fs: str, region_scope: int, phase_threshold: float, add_identifier_features: bool) -> str:
    scope = "somalia" if region_scope == 1 else "global"
    parts = [FS_LABELS[fs], scope]
    if add_identifier_features:
        parts.append("identifier_features")
    parts.append(f"threshold_{phase_threshold:.2f}".replace(".", "_"))
    return "_".join(parts)


def resolve_output_plan(args: argparse.Namespace, test_years: Sequence[int]):
    out_dir = args.out_dir
    report_dir = args.report_dir
    if out_dir is None or report_dir is None:
        experiment_name = default_experiment_name(args.fs, args.region_scope, args.phase_threshold, args.add_identifier_features)
        if out_dir is None:
            out_dir = str(paths.RESULTS_DIR / "experiments" / "deep_feature_weight_decay_forecasting" / experiment_name)
        if report_dir is None:
            report_dir = str(paths.REPORTS_DIR / "deep_feature_weight_decay_forecasting" / experiment_name)
    return plan_outputs(out_dir, report_dir, test_years)


def load_hyperparameters() -> Tuple[Dict[str, object], Dict[str, object]]:
    hyper_path = paths.CONFIG_DIR / "forecasting_hyperparameters.json"
    hyper_p3_path = paths.CONFIG_DIR / "forecasting_hyperparameters_p3.json"
    missing = [str(path) for path in (hyper_path, hyper_p3_path) if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing hyperparameter config files: " + "; ".join(missing))
    return (
        json.loads(hyper_path.read_text(encoding="utf-8")),
        json.loads(hyper_p3_path.read_text(encoding="utf-8")),
    )


def fit_model(X_train: pd.DataFrame, y_train: pd.Series, sample_weight: pd.Series, target_column: str, hyperparams: Mapping[str, object], hyperparams_p3: Mapping[str, object], seed: int):
    import xgboost as xgb

    params = dict(hyperparams_p3 if target_column == "phase3_worse" else hyperparams)
    params["random_state"] = seed
    model = xgb.XGBRegressor(**params)
    model.fit(X_train, y_train, sample_weight=sample_weight)
    return model


def convert_phase_predictions(phase_predictions: Mapping[str, pd.Series], phase_truth: Mapping[str, pd.Series], phase_threshold: float) -> pd.DataFrame:
    converted = pd.DataFrame(index=phase_truth["phase2_worse"].index)
    target_to_phase = {
        "phase2_worse": 2,
        "phase3_worse": 3,
        "phase4_worse": 4,
        "phase5_worse": 5,
    }
    for target_column, phase in target_to_phase.items():
        converted[f"phase{phase}_pred"] = phase_predictions[target_column].reindex(converted.index).round(2)
        converted[f"phase{phase}_test"] = phase_truth[target_column].reindex(converted.index)
    converted = converted.fillna(0)
    converted = converted[(converted[["phase2_pred", "phase3_pred", "phase4_pred", "phase5_pred"]].sum(axis=1) > 0)]
    converted = converted[(converted[["phase2_test", "phase3_test", "phase4_test", "phase5_test"]].sum(axis=1) > 0)]
    converted["overall_phase"] = 1
    converted["overall_phase_pred"] = 1
    for phase in (5, 4, 3, 2):
        test_mask = (converted["overall_phase"] == 1) & (converted[f"phase{phase}_test"] >= phase_threshold)
        pred_mask = (converted["overall_phase_pred"] == 1) & (converted[f"phase{phase}_pred"] >= phase_threshold)
        converted.loc[test_mask, "overall_phase"] = phase
        converted.loc[pred_mask, "overall_phase_pred"] = phase
    converted["test_index"] = converted.index
    return converted


def run_holdout(
    test_year: int,
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    feature_columns: Sequence[str],
    weights: pd.Series,
    hyperparams: Mapping[str, object],
    hyperparams_p3: Mapping[str, object],
    seed: int,
    phase_threshold: float,
) -> pd.DataFrame:
    if train_df.empty:
        raise ValueError(f"No eligible training rows for {test_year}")
    if test_df.empty:
        raise ValueError(f"No eligible test rows for {test_year}")

    eligible_test = test_df.dropna(subset=list(TARGET_COLUMNS)).copy()
    if eligible_test.empty:
        raise ValueError(f"No test rows with complete cumulative targets for {test_year}")

    phase_predictions: Dict[str, pd.Series] = {}
    phase_truth: Dict[str, pd.Series] = {}
    for target_column in TARGET_COLUMNS:
        X_train, y_train, X_test, y_test, aligned_weights = prepare_target_matrices(
            train_df, eligible_test, feature_columns, target_column, weights
        )
        if X_train.empty:
            raise ValueError(f"No training rows with target {target_column} for {test_year}")
        if X_test.empty:
            raise ValueError(f"No test rows with target {target_column} for {test_year}")
        model = fit_model(X_train, y_train, aligned_weights, target_column, hyperparams, hyperparams_p3, seed)
        phase_predictions[target_column] = pd.Series(model.predict(X_test), index=X_test.index)
        phase_truth[target_column] = y_test

    converted = convert_phase_predictions(phase_predictions, phase_truth, phase_threshold)
    if "test_index" in converted.columns:
        converted = converted.set_index("test_index", drop=True)
        converted.index = converted.index.astype(int)
    else:
        converted.index = eligible_test.index[: len(converted)]

    predictions = eligible_test.loc[converted.index, ["area_id", "year", "month", "date", "overall_phase", *TARGET_COLUMNS]].copy()
    predictions.insert(0, "test_year", test_year)
    predictions["overall_phase_pred"] = converted["overall_phase_pred"].astype(int).to_numpy()
    for target_column in TARGET_COLUMNS:
        phase = target_column.replace("_worse", "")
        predictions[f"{phase}_pred"] = converted[f"{phase}_pred"].to_numpy()
    predictions["date"] = pd.to_datetime(predictions["date"]).dt.date.astype(str)
    ordered_columns = [
        "test_year",
        "area_id",
        "year",
        "month",
        "date",
        "overall_phase",
        "overall_phase_pred",
        *TARGET_COLUMNS,
        "phase2_pred",
        "phase3_pred",
        "phase4_pred",
        "phase5_pred",
    ]
    return predictions[ordered_columns]


def write_split_diagnostics(diagnostics: pd.DataFrame, output_plan) -> None:
    output_plan.metadata_dir.mkdir(parents=True, exist_ok=True)
    diagnostics.to_csv(output_plan.split_diagnostics_csv, index=False)


def write_metrics_outputs(metrics_by_year: Mapping[int, Mapping[str, object]], output_plan) -> pd.DataFrame:
    rows = []
    for year, result in metrics_by_year.items():
        write_json(output_plan.metrics_json_paths[year], result)
        rows.append(flatten_metric_result(result))
    metrics_df = pd.DataFrame(rows).sort_values("test_year")
    metrics_df.to_csv(output_plan.metrics_overall_csv, index=False)
    return metrics_df


def write_somalia_metrics(predictions_by_year: Mapping[int, pd.DataFrame], somalia_area_ids: Sequence[object], output_plan) -> pd.DataFrame:
    rows = []
    somalia_ids = set(somalia_area_ids)
    for year, predictions in predictions_by_year.items():
        somalia_predictions = predictions[predictions["area_id"].isin(somalia_ids)].copy()
        if somalia_predictions.empty:
            result = unavailable_metrics(year, "somalia", "no eligible Somalia samples")
        else:
            result = compute_metrics(somalia_predictions, year, "somalia")
        rows.append(flatten_metric_result(result))
    metrics_df = pd.DataFrame(rows).sort_values("test_year")
    metrics_df.to_csv(output_plan.metrics_somalia_csv, index=False)
    return metrics_df


def write_report(metrics_overall: Optional[pd.DataFrame], metrics_somalia: Optional[pd.DataFrame], metadata: Mapping[str, object], output_plan) -> None:
    output_plan.report_dir.mkdir(parents=True, exist_ok=True)
    if metrics_overall is not None:
        metrics_overall.to_csv(output_plan.report_metrics_overall_csv, index=False)
    if metrics_somalia is not None:
        metrics_somalia.to_csv(output_plan.report_metrics_somalia_csv, index=False)

    lines = [
        "# Deep Feature Weighted Decay Forecasting Summary",
        "",
        f"Run timestamp: `{metadata['run_timestamp']}`",
        "",
        "## Data source replacement",
        "",
        f"Dataset source: `{metadata['dataset_source']}`",
        f"Somalia lookup source: `{metadata['somalia_lookup_source']}`",
        "",
        "## Time-decay weighting",
        "",
        f"Formula: `{metadata['decay_formulation']}`",
        f"Half-life months: `{metadata['half_life_months']}`",
        "",
        "## Phase conversion",
        "",
        f"Cumulative phase threshold: `{metadata['phase_threshold']}`",
        "",
        "## Identifier feature option",
        "",
        f"Identifier source: `{metadata['identifier_feature_source']}`",
        f"Identifier feature columns: `{metadata['identifier_feature_columns']}`",
        "",
        "## Split rule",
        "",
        f"{metadata['split_rule']}",
        "",
        "## Overall metrics",
        "",
    ]
    lines.extend(_markdown_table(metrics_overall))
    lines.extend(["", "## Somalia-only metrics", ""])
    lines.extend(_markdown_table(metrics_somalia))
    lines.extend(["", "## Notebook discipline", "", "Original notebook modified: `false`", ""])
    output_plan.summary_report.write_text("\n".join(lines), encoding="utf-8")


def _markdown_table(df: Optional[pd.DataFrame]) -> List[str]:
    if df is None or df.empty:
        return ["No metrics were produced."]
    display_columns = ["test_year", "n_samples", "accuracy", "precision_phase3plus", "sensitivity_phase3plus", "r2_phase3plus", "f2_phase3plus"]
    available_columns = [column for column in display_columns if column in df.columns]
    table = df[available_columns].copy()
    rows = ["| " + " | ".join(available_columns) + " |", "| " + " | ".join(["---"] * len(available_columns)) + " |"]
    for _, row in table.iterrows():
        rows.append("| " + " | ".join(_format_report_value(row[column]) for column in available_columns) + " |")
    return rows


def _format_report_value(value: object) -> str:
    if pd.isna(value):
        return ""
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def build_metadata(
    dataset_path: Path,
    dataset_key: str,
    fs: str,
    region_scope: int,
    loaded_rows: int,
    somalia_filtered: bool,
    somalia_lookup_path: Path,
    somalia_lookup_key: str,
    test_years: Sequence[int],
    feature_columns: Sequence[str],
    output_plan,
    half_life_months: float,
    phase_threshold: float,
    add_identifier_feature_columns: Sequence[str],
    identifier_source: Optional[Path],
    identifier_source_key: str,
    dry_run: bool,
    somalia_area_id_count: int,
    weight_diagnostics_rows: Sequence[Mapping[str, object]],
) -> Dict[str, object]:
    return {
        "run_timestamp": datetime.now(timezone.utc).isoformat(),
        "dataset_source": {"key": dataset_key, "path": str(dataset_path), "fs": fs},
        "region_scope": int(region_scope),
        "region_scope_name": "somalia" if region_scope == 1 else "global",
        "loaded_rows": int(loaded_rows),
        "somalia_filtered_before_modeling": bool(somalia_filtered),
        "somalia_lookup_source": {"key": somalia_lookup_key, "path": str(somalia_lookup_path)},
        "somalia_area_id_count": int(somalia_area_id_count),
        "split_rule": SPLIT_RULE,
        "test_years": list(test_years),
        "target_columns": list(TARGET_COLUMNS),
        "feature_count": len(feature_columns),
        "feature_columns_hash_or_sample": feature_hash_or_sample(feature_columns),
        "decay_formulation": DECAY_FORMULATION,
        "half_life_months": float(half_life_months),
        "phase_threshold": float(phase_threshold),
        "identifier_feature_source": {"key": identifier_source_key, "path": str(identifier_source)} if identifier_source else None,
        "identifier_feature_columns": list(add_identifier_feature_columns),
        "weight_diagnostics": list(weight_diagnostics_rows),
        "output_locations": {
            "base_dir": str(output_plan.base_dir),
            "predictions": str(output_plan.prediction_dir),
            "metrics": str(output_plan.metrics_dir),
            "metadata": str(output_plan.metadata_dir),
            "report_dir": str(output_plan.report_dir),
        },
        "dry_run": bool(dry_run),
        "notebook_modified": False,
    }


def print_dry_run_summary(
    dataset_path: Path,
    somalia_lookup_path: Path,
    df: pd.DataFrame,
    feature_columns: Sequence[str],
    diagnostics: pd.DataFrame,
    weight_rows: Sequence[Mapping[str, object]],
    somalia_area_ids: Sequence[object],
    output_plan,
) -> None:
    print("Deep-feature weighted-decay forecasting dry run")
    print(f"Dataset source: {dataset_path}")
    print(f"Rows loaded: {len(df):,}")
    print(f"Feature count: {len(feature_columns):,}")
    print(f"Target columns: {', '.join(TARGET_COLUMNS)}")
    print(f"Somalia lookup source: {somalia_lookup_path}")
    print(f"Somalia area_id count: {len(somalia_area_ids):,}")
    print("\nSplit diagnostics:")
    print(diagnostics.to_string(index=False))
    print("\nWeight diagnostics:")
    print(pd.DataFrame(weight_rows).to_string(index=False))
    print("\nOutput plan:")
    print(f"  results: {output_plan.base_dir}")
    print(f"  reports: {output_plan.report_dir}")
    print(f"  split diagnostics: {output_plan.split_diagnostics_csv}")
    print("Dry run completed without fitting models.")


def run(args: argparse.Namespace) -> int:
    validate_half_life(args.half_life_months)
    validate_phase_threshold(args.phase_threshold)
    test_years = validate_test_years(args.test_years)
    dataset_path, dataset_key = resolve_dataset_selection(args)
    somalia_lookup_path = resolve_input_path(args.somalia_lookup, args.somalia_lookup_key)
    identifier_source_path = resolve_input_path(args.identifier_source, args.identifier_source_key) if args.add_identifier_features else None
    output_plan = resolve_output_plan(args, test_years)
    check_existing_outputs(output_plan, args.overwrite, args.dry_run)
    ensure_output_dirs(output_plan)

    somalia_lookup_df = pd.read_csv(somalia_lookup_path)
    somalia_area_ids = extract_somalia_area_ids(somalia_lookup_df)
    region_area_ids = somalia_area_ids if args.region_scope == 1 else None
    raw_df = load_dataset(dataset_path, args.sample_rows, region_area_ids)
    df = prepare_forecasting_dataset(raw_df)
    identifier_feature_columns: List[str] = []
    if args.add_identifier_features:
        identifier_lookup_df = pd.read_csv(identifier_source_path)
        df = add_identifier_features(df, identifier_lookup_df)
        identifier_feature_columns = [column for column in df.columns if column in {"lat", "lon"} or column.startswith("month_") or column.startswith("year_")]
    feature_columns = select_numeric_feature_columns(df)
    splits = annual_splits(df, test_years)
    diagnostics = split_diagnostics(splits)
    if (diagnostics["train_rows"] == 0).any() or (diagnostics["test_rows"] == 0).any():
        raise ValueError("At least one holdout has no eligible train or test rows; see split diagnostics")
    if not diagnostics["max_training_before_test"].all():
        raise ValueError("At least one holdout has training rows on or after the test start date")

    weights_by_year = {}
    weight_rows = []
    for year, (train_df, _) in splits.items():
        weights = time_decay_weights(train_df["date"], year, args.half_life_months)
        weights_by_year[year] = weights
        weight_rows.append(weight_diagnostics(train_df, year, weights))
    if not all(row["newer_rows_have_larger_weights"] for row in weight_rows):
        raise ValueError("Sample-weight monotonicity check failed")

    write_split_diagnostics(diagnostics, output_plan)

    metrics_overall = None
    metrics_somalia = None
    predictions_by_year: Dict[int, pd.DataFrame] = {}

    if args.dry_run:
        print_dry_run_summary(dataset_path, somalia_lookup_path, df, feature_columns, diagnostics, weight_rows, somalia_area_ids, output_plan)
    else:
        hyperparams, hyperparams_p3 = load_hyperparameters()
        metrics_by_year: Dict[int, Mapping[str, object]] = {}
        for year, (train_df, test_df) in splits.items():
            print(f"Running holdout {year}: {len(train_df):,} train rows, {len(test_df):,} test rows")
            predictions = run_holdout(
                year,
                train_df,
                test_df,
                feature_columns,
                weights_by_year[year],
                hyperparams,
                hyperparams_p3,
                args.seed,
                args.phase_threshold,
            )
            predictions.to_csv(output_plan.prediction_paths[year], index=False)
            predictions_by_year[year] = predictions
            metrics_by_year[year] = compute_metrics(predictions, year, "overall")
        metrics_overall = write_metrics_outputs(metrics_by_year, output_plan)
        metrics_somalia = write_somalia_metrics(predictions_by_year, somalia_area_ids, output_plan)

    metadata = build_metadata(
        dataset_path,
        dataset_key,
        args.fs,
        args.region_scope,
        len(df),
        args.region_scope == 1,
        somalia_lookup_path,
        args.somalia_lookup_key,
        test_years,
        feature_columns,
        output_plan,
        args.half_life_months,
        args.phase_threshold,
        identifier_feature_columns,
        identifier_source_path,
        args.identifier_source_key,
        args.dry_run,
        len(somalia_area_ids),
        weight_rows,
    )
    write_json(output_plan.run_metadata_json, metadata)
    write_report(metrics_overall, metrics_somalia, metadata, output_plan)
    return 0


def main() -> int:
    args = parse_args()
    try:
        return run(args)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
