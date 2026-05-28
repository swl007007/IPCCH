from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_recall_fscore_support, r2_score

from ipcch import paths

PHASE_LABELS = [1, 2, 3, 4, 5]
CANONICAL_THRESHOLD = 0.2
DEFAULT_THRESHOLDS = [0.1, 0.15, 0.2, 0.25, 0.3]
CUMULATIVE_TARGETS = {
    2: "phase2_worse",
    3: "phase3_worse",
    4: "phase4_worse",
    5: "phase5_worse",
}
PREDICTED_COLUMN_ALIASES = {
    2: ["phase2_pred", "phase2_worse_pred", "pred_phase2_worse", "phase2_worse_prediction"],
    3: ["phase3_pred", "phase3_worse_pred", "pred_phase3_worse", "phase3_worse_prediction"],
    4: ["phase4_pred", "phase4_worse_pred", "pred_phase4_worse", "phase4_worse_prediction"],
    5: ["phase5_pred", "phase5_worse_pred", "pred_phase5_worse", "phase5_worse_prediction"],
}
ERROR_SLICE_DEFINITIONS = {
    "true2_pred3": (2, 3),
    "true3_pred2": (3, 2),
    "true4_pred3": (4, 3),
    "true3_pred4": (3, 4),
}
GROUPING_COLUMNS = ["country", "region", "area_id"]
METRIC_TOLERANCE = 1e-6


@dataclass(frozen=True)
class DiagnosticConfig:
    predictions: Path | None = None
    metrics: Path | None = None
    year: int | None = None
    output_dir: Path = paths.RESULTS_DIR / "diagnostics" / "experiment_0"
    report_dir: Path = paths.REPORTS_DIR / "diagnostics" / "experiment_0"
    overall_phase_col: str = "overall_phase"
    overall_phase_pred_col: str = "overall_phase_pred"
    true_cols: dict[int, str] | None = None
    pred_cols: dict[int, str | None] | None = None
    thresholds: tuple[float, ...] = tuple(DEFAULT_THRESHOLDS)
    calibration_bins: int = 5
    filter_invalid_labels: bool = False


def default_output_dir() -> Path:
    return paths.RESULTS_DIR / "diagnostics" / "experiment_0"


def default_report_dir() -> Path:
    return paths.REPORTS_DIR / "diagnostics" / "experiment_0"


def _true_cols(config: DiagnosticConfig) -> dict[int, str]:
    return config.true_cols or CUMULATIVE_TARGETS.copy()


def _pred_cols(config: DiagnosticConfig) -> dict[int, str | None]:
    return config.pred_cols or {phase: None for phase in CUMULATIVE_TARGETS}


def safe_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def phase_label_status(series: pd.Series) -> pd.Series:
    numeric = safe_numeric(series)
    status = pd.Series("invalid", index=series.index, dtype="object")
    status[series.isna()] = "missing"
    status[numeric.isin(PHASE_LABELS)] = "valid"
    return status


def valid_phase_mask(true_values: pd.Series, pred_values: pd.Series) -> pd.Series:
    return (phase_label_status(true_values) == "valid") & (phase_label_status(pred_values) == "valid")


def resolve_predicted_columns(df: pd.DataFrame, overrides: dict[int, str | None] | None = None) -> tuple[dict[int, str], list[dict]]:
    overrides = overrides or {}
    resolved: dict[int, str] = {}
    findings: list[dict] = []
    for phase, aliases in PREDICTED_COLUMN_ALIASES.items():
        override = overrides.get(phase)
        if override:
            if override in df.columns:
                resolved[phase] = override
            else:
                findings.append(
                    {
                        "finding_type": "schema",
                        "severity": "warning",
                        "column": override,
                        "value": "missing_override",
                        "row_count": 0,
                        "message": f"Override for phase {phase} predicted cumulative output column is missing.",
                    }
                )
            continue
        matches = [column for column in aliases if column in df.columns]
        if len(matches) == 1:
            resolved[phase] = matches[0]
        elif len(matches) > 1:
            findings.append(
                {
                    "finding_type": "schema",
                    "severity": "error",
                    "column": ",".join(matches),
                    "value": "ambiguous_predicted_cumulative_output_columns",
                    "row_count": 0,
                    "message": f"Multiple aliases match phase {phase}; use --phase{phase}-pred-col.",
                }
            )
        else:
            findings.append(
                {
                    "finding_type": "schema",
                    "severity": "info",
                    "column": f"phase{phase}_pred",
                    "value": "missing_optional",
                    "row_count": 0,
                    "message": f"No predicted cumulative output column found for phase {phase}.",
                }
            )
    return resolved, findings


def validate_prediction_schema(
    df: pd.DataFrame,
    config: DiagnosticConfig | None = None,
    metrics_path: Path | None = None,
) -> tuple[pd.DataFrame, dict, dict[int, str]]:
    config = config or DiagnosticConfig()
    findings: list[dict] = []
    required = [config.overall_phase_col, config.overall_phase_pred_col]
    for column in required:
        if column not in df.columns:
            findings.append(
                {
                    "finding_type": "schema",
                    "severity": "error",
                    "column": column,
                    "value": "missing_required",
                    "row_count": len(df),
                    "message": f"Required classification column {column} is missing.",
                }
            )
    true_cols = _true_cols(config)
    for phase, column in true_cols.items():
        if column not in df.columns:
            findings.append(
                {
                    "finding_type": "cumulative_column",
                    "severity": "info",
                    "column": column,
                    "value": "missing_optional",
                    "row_count": 0,
                    "message": f"Optional true cumulative target for phase {phase} is missing.",
                }
            )
    resolved_pred_cols, pred_findings = resolve_predicted_columns(df, _pred_cols(config))
    findings.extend(pred_findings)
    for column, label_source in [(config.overall_phase_col, "true"), (config.overall_phase_pred_col, "predicted")]:
        if column not in df.columns:
            continue
        status = phase_label_status(df[column])
        for invalid_status in ["missing", "invalid"]:
            mask = status == invalid_status
            if mask.any():
                values = df.loc[mask, column].astype("string").fillna("<missing>").value_counts(dropna=False)
                for value, count in values.items():
                    findings.append(
                        {
                            "finding_type": "label",
                            "severity": "warning",
                            "column": column,
                            "value": str(value),
                            "row_count": int(count),
                            "message": f"{label_source} phase label is {invalid_status}.",
                        }
                    )
    if metrics_path is not None and not metrics_path.exists():
        findings.append(
            {
                "finding_type": "metrics_file",
                "severity": "warning",
                "column": "",
                "value": "not_available",
                "row_count": 0,
                "message": f"Optional metrics file does not exist: {metrics_path}",
            }
        )
    years = sorted(safe_numeric(df["year"]).dropna().astype(int).unique().tolist()) if "year" in df.columns else []
    validation_summary = {
        "row_count": int(len(df)),
        "columns": list(df.columns),
        "years": years,
        "has_required_columns": all(column in df.columns for column in required),
        "invalid_label_findings": int(sum(1 for finding in findings if finding["finding_type"] == "label")),
        "error_count": int(sum(1 for finding in findings if finding["severity"] == "error")),
        "metrics_file_status": "not_available" if metrics_path is not None and not metrics_path.exists() else ("supplied" if metrics_path is not None else "not_supplied"),
    }
    return pd.DataFrame(findings), validation_summary, resolved_pred_cols


def _year_value(df: pd.DataFrame, explicit_year: int | None = None) -> int | str:
    if explicit_year is not None:
        return int(explicit_year)
    if "year" in df.columns:
        years = safe_numeric(df["year"]).dropna().astype(int).unique()
        if len(years) == 1:
            return int(years[0])
    return "unspecified"


def _valid_label_frame(df: pd.DataFrame, config: DiagnosticConfig) -> pd.DataFrame:
    if config.overall_phase_col not in df.columns or config.overall_phase_pred_col not in df.columns:
        return df.iloc[0:0].copy()
    mask = valid_phase_mask(df[config.overall_phase_col], df[config.overall_phase_pred_col])
    out = df.loc[mask].copy()
    out[config.overall_phase_col] = safe_numeric(out[config.overall_phase_col]).astype(int)
    out[config.overall_phase_pred_col] = safe_numeric(out[config.overall_phase_pred_col]).astype(int)
    return out


def compute_class_distribution(df: pd.DataFrame, year: int | str, config: DiagnosticConfig | None = None) -> pd.DataFrame:
    config = config or DiagnosticConfig()
    rows: list[dict] = []
    for column, label_source in [(config.overall_phase_col, "true"), (config.overall_phase_pred_col, "predicted")]:
        if column not in df.columns:
            continue
        status = phase_label_status(df[column])
        labels = safe_numeric(df[column])
        display_values = labels.where(labels.notna(), df[column])
        total = len(df)
        grouped = pd.DataFrame({"phase_label": display_values, "validation_status": status}).value_counts(dropna=False)
        for (phase_label, validation_status), count in grouped.items():
            rows.append(
                {
                    "year": year,
                    "label_source": label_source,
                    "phase_label": "missing" if pd.isna(phase_label) else phase_label,
                    "validation_status": validation_status,
                    "count": int(count),
                    "percentage": float(count / total) if total else np.nan,
                }
            )
    return pd.DataFrame(rows)


def compute_confusion_matrices(df: pd.DataFrame, year: int | str, config: DiagnosticConfig | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    config = config or DiagnosticConfig()
    valid_df = _valid_label_frame(df, config)
    if valid_df.empty:
        columns = ["year", "true_label", "predicted_label", "count"]
        return pd.DataFrame(columns=columns), pd.DataFrame(columns=["year", "true_label", "predicted_label", "row_percentage"])
    y_true = valid_df[config.overall_phase_col]
    y_pred = valid_df[config.overall_phase_pred_col]
    matrix = confusion_matrix(y_true, y_pred, labels=PHASE_LABELS)
    count_rows: list[dict] = []
    pct_rows: list[dict] = []
    row_sums = matrix.sum(axis=1)
    for i, true_label in enumerate(PHASE_LABELS):
        for j, pred_label in enumerate(PHASE_LABELS):
            count = int(matrix[i, j])
            row_pct = float(count / row_sums[i]) if row_sums[i] else np.nan
            count_rows.append({"year": year, "true_label": true_label, "predicted_label": pred_label, "count": count})
            pct_rows.append({"year": year, "true_label": true_label, "predicted_label": pred_label, "row_percentage": row_pct})
    return pd.DataFrame(count_rows), pd.DataFrame(pct_rows)


def compute_multiclass_metrics(df: pd.DataFrame, year: int | str, config: DiagnosticConfig | None = None) -> pd.DataFrame:
    config = config or DiagnosticConfig()
    valid_df = _valid_label_frame(df, config)
    if valid_df.empty:
        return pd.DataFrame(columns=["year", "phase_label", "precision", "recall", "f1", "support", "accuracy", "macro_f1", "weighted_f1", "ordinal_mae"])
    y_true = valid_df[config.overall_phase_col]
    y_pred = valid_df[config.overall_phase_pred_col]
    precision, recall, f1, support = precision_recall_fscore_support(y_true, y_pred, labels=PHASE_LABELS, zero_division=0)
    accuracy = float(accuracy_score(y_true, y_pred))
    macro_f1 = float(f1_score(y_true, y_pred, labels=PHASE_LABELS, average="macro", zero_division=0))
    weighted_f1 = float(f1_score(y_true, y_pred, labels=PHASE_LABELS, average="weighted", zero_division=0))
    ordinal_mae = float(np.mean(np.abs(y_true.to_numpy() - y_pred.to_numpy())))
    rows = []
    for idx, phase_label in enumerate(PHASE_LABELS):
        rows.append(
            {
                "year": year,
                "phase_label": phase_label,
                "precision": float(precision[idx]),
                "recall": float(recall[idx]),
                "f1": float(f1[idx]),
                "support": int(support[idx]),
                "accuracy": accuracy,
                "macro_f1": macro_f1,
                "weighted_f1": weighted_f1,
                "ordinal_mae": ordinal_mae,
            }
        )
    return pd.DataFrame(rows)


def _binary_metrics(y_true: pd.Series, y_pred: pd.Series, threshold: int) -> dict:
    true_pos = y_true >= threshold
    pred_pos = y_pred >= threshold
    tp = int((true_pos & pred_pos).sum())
    fp = int((~true_pos & pred_pos).sum())
    fn = int((true_pos & ~pred_pos).sum())
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    beta2 = 4.0
    f2 = (1 + beta2) * precision * recall / (beta2 * precision + recall) if beta2 * precision + recall else 0.0
    return {
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "f2": float(f2),
        "positive_support": int(true_pos.sum()),
        "negative_support": int((~true_pos).sum()),
        "total_support": int(len(y_true)),
    }


def compute_binary_crisis_metrics(df: pd.DataFrame, year: int | str, config: DiagnosticConfig | None = None) -> pd.DataFrame:
    config = config or DiagnosticConfig()
    valid_df = _valid_label_frame(df, config)
    rows = []
    if valid_df.empty:
        return pd.DataFrame(columns=["year", "crisis_definition", "positive_label_definition", "negative_label_definition", "precision", "recall", "f1", "f2", "positive_support", "negative_support", "total_support"])
    y_true = valid_df[config.overall_phase_col]
    y_pred = valid_df[config.overall_phase_pred_col]
    for threshold, name, negative in [(3, "phase3_plus", "phase1_to_phase2"), (4, "phase4_plus", "phase1_to_phase3")]:
        row = {
            "year": year,
            "crisis_definition": name,
            "positive_label_definition": f"phase{threshold}_plus",
            "negative_label_definition": negative,
        }
        row.update(_binary_metrics(y_true, y_pred, threshold))
        rows.append(row)
    return pd.DataFrame(rows)


def _cumulative_pairs(df: pd.DataFrame, config: DiagnosticConfig, resolved_pred_cols: dict[int, str]) -> list[tuple[int, str, str]]:
    pairs = []
    for phase, true_col in _true_cols(config).items():
        pred_col = resolved_pred_cols.get(phase)
        if true_col in df.columns and pred_col in df.columns:
            pairs.append((phase, true_col, pred_col))
    return pairs


def compute_cumulative_regression_metrics(df: pd.DataFrame, year: int | str, resolved_pred_cols: dict[int, str], config: DiagnosticConfig | None = None) -> pd.DataFrame:
    config = config or DiagnosticConfig()
    rows = []
    for phase, true_col, pred_col in _cumulative_pairs(df, config, resolved_pred_cols):
        values = pd.DataFrame({"true": safe_numeric(df[true_col]), "pred": safe_numeric(df[pred_col])}).dropna()
        if values.empty:
            rows.append({"year": year, "target": true_col, "true_column": true_col, "predicted_column": pred_col, "n_valid": 0, "rmse": np.nan, "mae": np.nan, "bias": np.nan, "correlation": np.nan, "correlation_status": "insufficient_data"})
            continue
        error = values["pred"] - values["true"]
        if len(values) < 2:
            corr = np.nan
            corr_status = "insufficient_data"
        elif values["true"].nunique() < 2 or values["pred"].nunique() < 2:
            corr = np.nan
            corr_status = "constant_input"
        else:
            corr = float(values["true"].corr(values["pred"]))
            corr_status = "computed"
        rows.append(
            {
                "year": year,
                "target": true_col,
                "true_column": true_col,
                "predicted_column": pred_col,
                "n_valid": int(len(values)),
                "rmse": float(np.sqrt(np.mean(error**2))),
                "mae": float(np.mean(np.abs(error))),
                "bias": float(error.mean()),
                "correlation": corr,
                "correlation_status": corr_status,
            }
        )
    return pd.DataFrame(rows)


def compute_calibration_bins(df: pd.DataFrame, year: int | str, resolved_pred_cols: dict[int, str], config: DiagnosticConfig | None = None) -> pd.DataFrame:
    config = config or DiagnosticConfig()
    rows = []
    edges = np.linspace(0.0, 1.0, config.calibration_bins + 1)
    for phase, true_col, pred_col in _cumulative_pairs(df, config, resolved_pred_cols):
        values = pd.DataFrame({"true": safe_numeric(df[true_col]), "pred": safe_numeric(df[pred_col])}).dropna()
        for idx in range(len(edges) - 1):
            lower = float(edges[idx])
            upper = float(edges[idx + 1])
            if idx == len(edges) - 2:
                mask = (values["pred"] >= lower) & (values["pred"] <= upper)
            else:
                mask = (values["pred"] >= lower) & (values["pred"] < upper)
            subset = values.loc[mask]
            rows.append(
                {
                    "year": year,
                    "target": true_col,
                    "bin_lower": lower,
                    "bin_upper": upper,
                    "bin_label": f"[{lower:.2f},{upper:.2f}{']' if idx == len(edges) - 2 else ')'}",
                    "n_rows": int(len(subset)),
                    "mean_predicted": float(subset["pred"].mean()) if not subset.empty else np.nan,
                    "mean_true": float(subset["true"].mean()) if not subset.empty else np.nan,
                    "bias": float((subset["pred"] - subset["true"]).mean()) if not subset.empty else np.nan,
                }
            )
    return pd.DataFrame(rows)


def compute_threshold_crossing_rates(df: pd.DataFrame, year: int | str, resolved_pred_cols: dict[int, str], threshold: float = CANONICAL_THRESHOLD) -> pd.DataFrame:
    rows = []
    for phase, pred_col in resolved_pred_cols.items():
        if pred_col not in df.columns:
            continue
        pred = safe_numeric(df[pred_col]).dropna()
        rows.append(
            {
                "year": year,
                "target": CUMULATIVE_TARGETS[phase],
                "predicted_column": pred_col,
                "threshold": float(threshold),
                "n_valid": int(len(pred)),
                "n_crossing": int((pred >= threshold).sum()),
                "crossing_rate": float((pred >= threshold).mean()) if len(pred) else np.nan,
            }
        )
    return pd.DataFrame(rows)


def reconstruct_phase_from_cumulative(df: pd.DataFrame, resolved_pred_cols: dict[int, str], threshold: float) -> pd.Series:
    required = [resolved_pred_cols.get(phase) for phase in [2, 3, 4, 5]]
    if any(column is None or column not in df.columns for column in required):
        return pd.Series(dtype="float64")
    phases = pd.Series(1, index=df.index, dtype="int64")
    for phase in [2, 3, 4, 5]:
        phases[safe_numeric(df[resolved_pred_cols[phase]]) >= threshold] = phase
    return phases


def run_diagnostic_threshold_sweep(df: pd.DataFrame, year: int | str, resolved_pred_cols: dict[int, str], thresholds: Sequence[float] | None = None, config: DiagnosticConfig | None = None) -> pd.DataFrame:
    config = config or DiagnosticConfig()
    thresholds = thresholds or config.thresholds
    valid_true = config.overall_phase_col in df.columns
    rows = []
    for threshold in thresholds:
        reconstructed = reconstruct_phase_from_cumulative(df, resolved_pred_cols, float(threshold))
        if reconstructed.empty:
            continue
        counts = reconstructed.value_counts().to_dict()
        valid_mask = phase_label_status(df[config.overall_phase_col]) == "valid" if valid_true else pd.Series(False, index=df.index)
        y_true = safe_numeric(df.loc[valid_mask, config.overall_phase_col]).astype(int) if valid_true else pd.Series(dtype="int64")
        y_pred = reconstructed.loc[valid_mask].astype(int) if valid_true else pd.Series(dtype="int64")
        row = {"year": year, "threshold": float(threshold), "diagnostic_only": True, "class_distribution_summary": json.dumps({str(k): int(v) for k, v in counts.items()}, sort_keys=True)}
        if len(y_true):
            row["accuracy"] = float(accuracy_score(y_true, y_pred))
            row["macro_f1"] = float(f1_score(y_true, y_pred, labels=PHASE_LABELS, average="macro", zero_division=0))
            for crisis_threshold, prefix in [(3, "phase3_plus"), (4, "phase4_plus")]:
                metrics = _binary_metrics(y_true, y_pred, crisis_threshold)
                row[f"{prefix}_precision"] = metrics["precision"]
                row[f"{prefix}_recall"] = metrics["recall"]
                row[f"{prefix}_f1"] = metrics["f1"]
                row[f"{prefix}_f2"] = metrics["f2"]
        else:
            row.update({"accuracy": np.nan, "macro_f1": np.nan, "phase3_plus_precision": np.nan, "phase3_plus_recall": np.nan, "phase3_plus_f1": np.nan, "phase3_plus_f2": np.nan, "phase4_plus_precision": np.nan, "phase4_plus_recall": np.nan, "phase4_plus_f1": np.nan, "phase4_plus_f2": np.nan})
        rows.append(row)
    return pd.DataFrame(rows)


def summarize_error_slices(df: pd.DataFrame, year: int | str, resolved_pred_cols: dict[int, str], config: DiagnosticConfig | None = None) -> pd.DataFrame:
    config = config or DiagnosticConfig()
    valid_df = _valid_label_frame(df, config)
    rows = []
    group_fields: list[str | None] = [None] + [column for column in GROUPING_COLUMNS if column in valid_df.columns]
    unavailable_groups = [column for column in GROUPING_COLUMNS if column not in df.columns]
    true_cols = _true_cols(config)
    for slice_name, (true_label, pred_label) in ERROR_SLICE_DEFINITIONS.items():
        base_slice = valid_df[(valid_df[config.overall_phase_col] == true_label) & (valid_df[config.overall_phase_pred_col] == pred_label)]
        for group_field in group_fields:
            if group_field is None:
                groups = [("overall", "overall", base_slice)]
            else:
                groups = [(group_field, group_value, group_df) for group_value, group_df in base_slice.groupby(group_field, dropna=False)]
                if not groups:
                    groups = [(group_field, "<empty>", base_slice)]
            for emitted_group_field, group_value, subset in groups:
                row = {"year": year, "slice_name": slice_name, "group_field": emitted_group_field, "group_value": group_value, "n_rows": int(len(subset)), "unavailable_group_fields": ",".join(unavailable_groups)}
                for phase, true_col in true_cols.items():
                    pred_col = resolved_pred_cols.get(phase)
                    row[f"mean_true_phase{phase}_worse"] = float(safe_numeric(subset[true_col]).mean()) if true_col in subset.columns and not subset.empty else np.nan
                    row[f"mean_pred_phase{phase}"] = float(safe_numeric(subset[pred_col]).mean()) if pred_col in subset.columns and not subset.empty else np.nan
                    row[f"mean_margin_to_0_2_phase{phase}"] = float((safe_numeric(subset[pred_col]) - CANONICAL_THRESHOLD).mean()) if pred_col in subset.columns and not subset.empty else np.nan
                rows.append(row)
    return pd.DataFrame(rows)


def compare_metrics_file(metrics_df: pd.DataFrame | None, computed: dict[str, float], year: int | str | None = None, tolerance: float = METRIC_TOLERANCE) -> pd.DataFrame:
    rows = []
    if metrics_df is None:
        for metric_name, recomputed_value in computed.items():
            rows.append({"year": year, "metric_name": metric_name, "status": "not_available", "supplied_value": np.nan, "recomputed_value": recomputed_value, "absolute_difference": np.nan})
        return pd.DataFrame(rows)
    lower_columns = {column.lower(): column for column in metrics_df.columns}
    comparable_df = metrics_df.copy()
    if year is not None:
        for year_col in ["test_year", "year"]:
            if year_col in lower_columns:
                source_col = lower_columns[year_col]
                year_mask = safe_numeric(comparable_df[source_col]) == int(year)
                if year_mask.any():
                    comparable_df = comparable_df.loc[year_mask]
                break
    for metric_name, recomputed_value in computed.items():
        supplied_value = np.nan
        status = "not_available"
        if metric_name in lower_columns:
            values = safe_numeric(comparable_df[lower_columns[metric_name]]).dropna()
            if not values.empty:
                supplied_value = float(values.iloc[-1])
                if pd.isna(recomputed_value):
                    status = "not_comparable"
                else:
                    diff = abs(supplied_value - float(recomputed_value))
                    status = "matched" if diff <= tolerance else "mismatch"
        elif {"metric_name", "metric_value"}.issubset(lower_columns):
            name_col = lower_columns["metric_name"]
            value_col = lower_columns["metric_value"]
            match = comparable_df[comparable_df[name_col].astype(str).str.lower() == metric_name]
            if not match.empty:
                values = safe_numeric(match[value_col]).dropna()
                if not values.empty:
                    supplied_value = float(values.iloc[-1])
                    if pd.isna(recomputed_value):
                        status = "not_comparable"
                    else:
                        diff = abs(supplied_value - float(recomputed_value))
                        status = "matched" if diff <= tolerance else "mismatch"
        diff_value = abs(supplied_value - float(recomputed_value)) if pd.notna(supplied_value) and pd.notna(recomputed_value) else np.nan
        rows.append({"year": year, "metric_name": metric_name, "status": status, "supplied_value": supplied_value, "recomputed_value": recomputed_value, "absolute_difference": diff_value})
    return pd.DataFrame(rows)


def _write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def _write_json(payload: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def _markdown_table(df: pd.DataFrame, columns: list[str], max_rows: int | None = None) -> list[str]:
    if df.empty:
        return ["No rows."]
    display = df.loc[:, columns].copy()
    if max_rows is not None:
        display = display.head(max_rows)
    rows = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for _, row in display.iterrows():
        values = []
        for column in columns:
            value = row[column]
            if isinstance(value, float):
                values.append("" if pd.isna(value) else f"{value:.6f}")
            else:
                values.append(str(value))
        rows.append("| " + " | ".join(values) + " |")
    return rows


def _write_summary(
    report_path: Path,
    run_summary: dict,
    validation_findings: pd.DataFrame,
    metrics_comparison: pd.DataFrame | None,
    class_distribution: pd.DataFrame,
    multiclass_metrics: pd.DataFrame,
    binary_crisis_metrics: pd.DataFrame,
    cumulative_regression_metrics: pd.DataFrame,
) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    warnings = int((validation_findings.get("severity") == "warning").sum()) if not validation_findings.empty else 0
    lines = [
        "# Experiment 0 Canonical Regressor Diagnostics",
        "",
        "This report summarizes post-hoc diagnostics for existing canonical cumulative-regression prediction CSVs. It does not train models, tune thresholds, select label mappings, or modify source prediction CSVs.",
        "",
        "## Run Summary",
        "",
        f"- Prediction CSV: `{run_summary.get('input_predictions')}`",
        f"- Metrics CSV: `{run_summary.get('input_metrics')}`",
        f"- Years processed: {run_summary.get('years_processed')}",
        f"- Input rows: {run_summary.get('row_counts', {}).get('input')}",
        f"- Valid label metric rows: {run_summary.get('row_counts', {}).get('label_metric_rows')}",
        f"- Validation warnings: {warnings}",
        "",
    ]
    if not multiclass_metrics.empty:
        first = multiclass_metrics.iloc[0]
        lines.extend(
            [
                "## Classification Metrics",
                "",
                f"- Accuracy: {first['accuracy']:.6f}",
                f"- Macro-F1: {first['macro_f1']:.6f}",
                f"- Weighted-F1: {first['weighted_f1']:.6f}",
                f"- Ordinal MAE: {first['ordinal_mae']:.6f}",
                "",
                "### Per-Class Metrics",
                "",
                *_markdown_table(multiclass_metrics, ["phase_label", "precision", "recall", "f1", "support"]),
                "",
            ]
        )
    if not binary_crisis_metrics.empty:
        lines.extend(["## Crisis Binary Metrics", "", *_markdown_table(binary_crisis_metrics, ["crisis_definition", "precision", "recall", "f1", "f2", "positive_support", "negative_support", "total_support"]), ""])
    if not class_distribution.empty:
        lines.extend(["## Class Distribution", "", *_markdown_table(class_distribution, ["label_source", "phase_label", "validation_status", "count", "percentage"]), ""])
    if not cumulative_regression_metrics.empty:
        lines.extend(["## Cumulative Regression Metrics", "", *_markdown_table(cumulative_regression_metrics, ["target", "rmse", "mae", "bias", "correlation", "correlation_status", "n_valid"]), ""])
    lines.extend(["## Generated Diagnostic Families", ""])
    for family in run_summary.get("diagnostic_families_generated", []):
        lines.append(f"- {family}")
    if run_summary.get("diagnostic_families_skipped"):
        lines.extend(["", "## Skipped Diagnostic Families", ""])
        for family, reason in run_summary["diagnostic_families_skipped"].items():
            lines.append(f"- {family}: {reason}")
    lines.extend(["", "## Threshold Sweep", "", "Threshold-sweep rows are post-hoc diagnostic-only. No threshold is selected or recommended as final performance."])
    if metrics_comparison is not None and not metrics_comparison.empty:
        status_counts = metrics_comparison["status"].value_counts().to_dict()
        lines.extend(["", "## Metrics Comparison", "", f"Comparison status counts: {status_counts}", "", *_markdown_table(metrics_comparison, ["metric_name", "status", "supplied_value", "recomputed_value", "absolute_difference"]), ""])
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _computed_summary_metrics(
    multiclass_metrics: pd.DataFrame,
    binary_crisis_metrics: pd.DataFrame,
    df: pd.DataFrame,
    resolved_pred_cols: dict[int, str],
    config: DiagnosticConfig,
) -> dict[str, float]:
    computed: dict[str, float] = {}
    if not multiclass_metrics.empty:
        first = multiclass_metrics.iloc[0]
        computed["accuracy"] = float(first["accuracy"])
        computed["macro_f1"] = float(first["macro_f1"])
        computed["weighted_f1"] = float(first["weighted_f1"])
        computed["ordinal_mae"] = float(first["ordinal_mae"])
    for crisis_name, source_prefix in [("phase3_plus", "phase3plus"), ("phase4_plus", "phase4plus")]:
        if binary_crisis_metrics.empty:
            continue
        row = binary_crisis_metrics[binary_crisis_metrics["crisis_definition"] == crisis_name]
        if row.empty:
            continue
        computed[f"precision_{source_prefix}"] = float(row["precision"].iloc[0])
        computed[f"sensitivity_{source_prefix}"] = float(row["recall"].iloc[0])
        computed[f"f2_{source_prefix}"] = float(row["f2"].iloc[0])
    true_cols = _true_cols(config)
    for phase in [3, 4]:
        true_col = true_cols.get(phase)
        pred_col = resolved_pred_cols.get(phase)
        if true_col in df.columns and pred_col in df.columns:
            values = pd.DataFrame({"true": safe_numeric(df[true_col]), "pred": safe_numeric(df[pred_col])}).dropna()
            if len(values) >= 2 and values["true"].nunique() > 1:
                computed[f"r2_phase{phase}plus"] = float(r2_score(values["true"], values["pred"]))
    return computed


def run_diagnostics(df: pd.DataFrame, config: DiagnosticConfig, metrics_df: pd.DataFrame | None = None) -> dict[str, pd.DataFrame | dict]:
    source_df = df.copy(deep=True)
    year = _year_value(source_df, config.year)
    if config.year is not None and "year" in source_df.columns:
        year_values = safe_numeric(source_df["year"])
        source_df = source_df.loc[year_values == config.year].copy()
    validation_findings, validation_summary, resolved_pred_cols = validate_prediction_schema(source_df, config, config.metrics)
    if validation_summary["error_count"]:
        raise ValueError("Prediction CSV is missing required columns or has ambiguous predicted cumulative output columns.")
    working_df = _valid_label_frame(source_df, config) if config.filter_invalid_labels else source_df.copy()
    class_distribution = compute_class_distribution(working_df, year, config)
    confusion_counts, confusion_row_normalized = compute_confusion_matrices(working_df, year, config)
    multiclass_metrics = compute_multiclass_metrics(working_df, year, config)
    binary_crisis_metrics = compute_binary_crisis_metrics(working_df, year, config)
    cumulative_regression_metrics = compute_cumulative_regression_metrics(working_df, year, resolved_pred_cols, config)
    calibration_bins = compute_calibration_bins(working_df, year, resolved_pred_cols, config)
    threshold_crossing_rates = compute_threshold_crossing_rates(working_df, year, resolved_pred_cols)
    diagnostic_threshold_sweep = run_diagnostic_threshold_sweep(working_df, year, resolved_pred_cols, config.thresholds, config)
    error_slices = summarize_error_slices(working_df, year, resolved_pred_cols, config)
    summary_metrics = _computed_summary_metrics(multiclass_metrics, binary_crisis_metrics, working_df, resolved_pred_cols, config)
    metrics_comparison = compare_metrics_file(metrics_df, summary_metrics, year) if config.metrics is not None else pd.DataFrame()
    if config.metrics is not None:
        comparison_findings = metrics_comparison.assign(finding_type="metrics_file", severity=lambda x: np.where(x["status"] == "mismatch", "warning", "info"), column="", value=lambda x: x["status"], row_count=0, message=lambda x: "Metrics-file comparison status for " + x["metric_name"].astype(str))
        validation_findings = pd.concat([validation_findings, comparison_findings[["finding_type", "severity", "column", "value", "row_count", "message"]]], ignore_index=True)
    families = {
        "class_distribution": class_distribution,
        "confusion_matrices": confusion_counts,
        "multiclass_metrics": multiclass_metrics,
        "binary_crisis_metrics": binary_crisis_metrics,
        "cumulative_regression_metrics": cumulative_regression_metrics,
        "calibration_bins": calibration_bins,
        "threshold_crossing_rates": threshold_crossing_rates,
        "diagnostic_threshold_sweep": diagnostic_threshold_sweep,
        "error_slices": error_slices,
    }
    generated = [name for name, frame in families.items() if not frame.empty]
    skipped = {name: "No usable input columns or valid rows" for name, frame in families.items() if frame.empty}
    run_summary = {
        "run_timestamp": datetime.now(timezone.utc).isoformat(),
        "experiment": "experiment_0",
        "workflow": "canonical_regressor_diagnostics",
        "input_predictions": str(config.predictions) if config.predictions else None,
        "input_metrics": str(config.metrics) if config.metrics else None,
        "years_processed": [year],
        "row_counts": {"input": int(len(source_df)), "label_metric_rows": int(len(_valid_label_frame(source_df, config)))},
        "diagnostic_families_generated": generated,
        "diagnostic_families_skipped": skipped,
        "validation_warning_count": int((validation_findings.get("severity") == "warning").sum()) if not validation_findings.empty else 0,
        "metrics_file_comparison_status": metrics_comparison["status"].value_counts().to_dict() if not metrics_comparison.empty else {},
        "output_dir": str(config.output_dir / "canonical_regressor"),
        "report_dir": str(config.report_dir / "canonical_regressor"),
        "canonical_threshold": CANONICAL_THRESHOLD,
        "threshold_sweep_policy": "post_hoc_diagnostic_only_no_selected_threshold",
    }
    return {
        "validation_findings": validation_findings,
        "validation_summary": validation_summary,
        "metrics_comparison": metrics_comparison,
        "class_distribution": class_distribution,
        "confusion_matrix_counts": confusion_counts,
        "confusion_matrix_row_normalized": confusion_row_normalized,
        "multiclass_metrics": multiclass_metrics,
        "binary_crisis_metrics": binary_crisis_metrics,
        "cumulative_regression_metrics": cumulative_regression_metrics,
        "calibration_bins": calibration_bins,
        "threshold_crossing_rates": threshold_crossing_rates,
        "diagnostic_threshold_sweep": diagnostic_threshold_sweep,
        "error_slices": error_slices,
        "run_summary": run_summary,
    }


def write_outputs(results: dict[str, pd.DataFrame | dict], config: DiagnosticConfig) -> None:
    output_dir = config.output_dir / "canonical_regressor"
    report_dir = config.report_dir / "canonical_regressor"
    csv_names = [
        "validation_findings",
        "metrics_comparison",
        "class_distribution",
        "confusion_matrix_counts",
        "confusion_matrix_row_normalized",
        "multiclass_metrics",
        "binary_crisis_metrics",
        "cumulative_regression_metrics",
        "calibration_bins",
        "threshold_crossing_rates",
        "diagnostic_threshold_sweep",
        "error_slices",
    ]
    for name in csv_names:
        frame = results.get(name)
        if isinstance(frame, pd.DataFrame):
            _write_csv(frame, output_dir / f"{name}.csv")
    _write_json(results["validation_summary"], output_dir / "validation_summary.json")
    _write_json(results["run_summary"], output_dir / "run_summary.json")
    _write_summary(
        report_dir / "summary.md",
        results["run_summary"],
        results["validation_findings"],
        results.get("metrics_comparison"),
        results["class_distribution"],
        results["multiclass_metrics"],
        results["binary_crisis_metrics"],
        results["cumulative_regression_metrics"],
    )


def run_from_paths(config: DiagnosticConfig) -> dict[str, pd.DataFrame | dict]:
    if config.predictions is None:
        raise ValueError("--predictions is required")
    df = pd.read_csv(config.predictions)
    metrics_df = pd.read_csv(config.metrics) if config.metrics is not None and config.metrics.exists() else None
    results = run_diagnostics(df, config, metrics_df)
    write_outputs(results, config)
    return results


def _parse_thresholds(value: str) -> tuple[float, ...]:
    return tuple(float(part.strip()) for part in value.split(",") if part.strip())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Experiment 0 canonical forecast diagnostics on one existing prediction CSV.")
    parser.add_argument("--predictions", required=True, type=Path, help="Existing held-out prediction CSV to diagnose.")
    parser.add_argument("--metrics", type=Path, help="Optional metrics CSV for comparison.")
    parser.add_argument("--year", type=int, help="Evaluation year to attach to outputs or filter from a year column.")
    parser.add_argument("--output-dir", type=Path, default=default_output_dir(), help="Machine-readable output root.")
    parser.add_argument("--report-dir", type=Path, default=default_report_dir(), help="Human-readable report root.")
    parser.add_argument("--filter-invalid-labels", action="store_true", help="Explicitly exclude invalid true/predicted labels from label-dependent outputs.")
    parser.add_argument("--overall-phase-col", default="overall_phase", help="True phase column name.")
    parser.add_argument("--overall-phase-pred-col", default="overall_phase_pred", help="Canonical predicted phase column name.")
    for phase in [2, 3, 4, 5]:
        parser.add_argument(f"--phase{phase}-true-col", default=f"phase{phase}_worse", help=f"True phase {phase}+ cumulative target column.")
        parser.add_argument(f"--phase{phase}-pred-col", default=None, help=f"Predicted cumulative output column for phase {phase}.")
    parser.add_argument("--thresholds", default=",".join(str(value) for value in DEFAULT_THRESHOLDS), help="Comma-separated shared thresholds for diagnostic-only sweep.")
    parser.add_argument("--calibration-bins", type=int, default=5, help="Number of bins for cumulative calibration summaries.")
    return parser


def config_from_args(args: argparse.Namespace) -> DiagnosticConfig:
    return DiagnosticConfig(
        predictions=args.predictions,
        metrics=args.metrics,
        year=args.year,
        output_dir=args.output_dir,
        report_dir=args.report_dir,
        overall_phase_col=args.overall_phase_col,
        overall_phase_pred_col=args.overall_phase_pred_col,
        true_cols={phase: getattr(args, f"phase{phase}_true_col") for phase in [2, 3, 4, 5]},
        pred_cols={phase: getattr(args, f"phase{phase}_pred_col") for phase in [2, 3, 4, 5]},
        thresholds=_parse_thresholds(args.thresholds),
        calibration_bins=args.calibration_bins,
        filter_invalid_labels=args.filter_invalid_labels,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    config = config_from_args(args)
    run_from_paths(config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
