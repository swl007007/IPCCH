"""April-only, coverage-aware comparison of launch predictions vs actuals.

Post-prediction ONLY: actual labels are loaded after predictions exist and are
never used for training, feature selection, X_test coverage, threshold selection,
calibration, or model selection (Constitution I; spec FR-020..FR-023).

Comparison uses April 2026 actual labels only (no Feb/Mar pooling, no
latest-across-months selection). All reported metrics are DESCRIPTIVE
covered-subset comparison metrics — not validation/model-selection/tuning evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import pandas as pd

from sklearn.metrics import accuracy_score, confusion_matrix, f1_score

DESCRIPTIVE_NOTE = (
    "Descriptive covered-subset comparison only; not held-out validation, "
    "model-selection, or threshold-tuning evidence."
)
CRISIS_PHASE = 3


def load_april_actuals(
    actuals: pd.DataFrame, launch_month: str = "2026-04", crisis_flag_col: Optional[str] = None
) -> pd.DataFrame:
    """Build the April actual crisis layer (April only; no pooling). FR-020/021."""
    df = actuals.copy()
    if "year" in df.columns and "month" in df.columns:
        ly, lm = (int(x) for x in launch_month.split("-"))
        df = df[(pd.to_numeric(df["year"], errors="coerce") == ly) & (pd.to_numeric(df["month"], errors="coerce") == lm)].copy()
    df["area_id"] = df["area_id"].astype(str)
    if df["area_id"].duplicated().any():
        # Single month expected; if duplicates exist, that is a data problem — surface it.
        dups = sorted(df.loc[df["area_id"].duplicated(), "area_id"].unique().tolist())
        raise ValueError(f"Duplicate area_id in April actuals (single-month layer expects unique ids): {dups[:10]}")
    out = pd.DataFrame({"area_id": df["area_id"].values})
    out["actual_month"] = launch_month
    if "overall_phase" in df.columns:
        out["actual_overall_phase"] = pd.to_numeric(df["overall_phase"].values, errors="coerce")
    else:
        out["actual_overall_phase"] = np.nan
    if crisis_flag_col and crisis_flag_col in df.columns:
        out["actual_crisis"] = df[crisis_flag_col].astype(bool).values
    else:
        out["actual_crisis"] = out["actual_overall_phase"] >= CRISIS_PHASE
    return out


@dataclass
class ComparisonResult:
    per_area: pd.DataFrame
    coverage: dict
    metrics: dict
    class_distribution: pd.DataFrame
    confusion: pd.DataFrame
    binary_metrics: pd.DataFrame
    unmatched_actual: pd.DataFrame
    unmatched_prediction: pd.DataFrame


def _binary_metrics(y_true: pd.Series, y_pred: pd.Series, crisis_threshold: int) -> dict:
    t = (y_true >= crisis_threshold).astype(int)
    p = (y_pred >= crisis_threshold).astype(int)
    tp = int(((t == 1) & (p == 1)).sum())
    fp = int(((t == 0) & (p == 1)).sum())
    fn = int(((t == 1) & (p == 0)).sum())
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    f2 = (5 * precision * recall / (4 * precision + recall)) if (4 * precision + recall) else 0.0
    return {"precision": precision, "recall": recall, "f1": f1, "f2": f2, "support_positive": int(t.sum())}


def compare_predictions_to_actuals(
    predictions: pd.DataFrame, april_actuals: pd.DataFrame, crisis_phase: int = CRISIS_PHASE
) -> ComparisonResult:
    """Coverage-aware April-only comparison (FR-022/023). Predictions are never modified."""
    pred = predictions.copy()
    pred["area_id"] = pred["area_id"].astype(str)
    act = april_actuals.copy()
    act["area_id"] = act["area_id"].astype(str)

    pred_ids = set(pred["area_id"])
    act_ids = set(act["area_id"])
    covered = sorted(pred_ids & act_ids)

    pred["predicted_crisis"] = pd.to_numeric(pred["overall_phase_pred"], errors="coerce") >= crisis_phase
    merged = pred.merge(act, on="area_id", how="left", suffixes=("", "_actual"))
    merged["comparison_eligible"] = merged["area_id"].isin(covered) & merged["actual_overall_phase"].notna()
    merged["coverage_status"] = np.where(merged["area_id"].isin(act_ids), "covered", "prediction_only")
    merged["reason_not_compared"] = np.where(merged["comparison_eligible"], "", "no_april_actual_label")

    per_area = merged[[
        c for c in ["area_id", "actual_month", "actual_overall_phase", "actual_crisis",
                    "overall_phase_pred", "predicted_crisis",
                    "phase2_worse_pred", "phase3_worse_pred", "phase4_worse_pred", "phase5_worse_pred",
                    "coverage_status", "comparison_eligible", "reason_not_compared"] if c in merged.columns
    ]].copy()
    per_area = per_area.rename(columns={"overall_phase_pred": "predicted_overall_phase"})

    coverage = {
        "predicted_area_count": int(len(pred_ids)),
        "april_actual_labeled_area_count": int(len(act_ids)),
        "covered_intersection_count": int(len(covered)),
        "coverage_share_of_predicted": (len(covered) / len(pred_ids) if pred_ids else 0.0),
        "actual_coverage_partial": len(covered) < len(pred_ids),
        "note": DESCRIPTIVE_NOTE,
    }

    sub = merged[merged["comparison_eligible"]].copy()
    metrics: dict = {"covered_area_count": int(len(sub)), "descriptive_only": True, "note": DESCRIPTIVE_NOTE}
    class_rows, conf_df, binary_rows = [], pd.DataFrame(), []
    if len(sub):
        y_true = pd.to_numeric(sub["actual_overall_phase"], errors="coerce").astype(int)
        y_pred = pd.to_numeric(sub["overall_phase_pred"], errors="coerce").astype(int)
        labels = [1, 2, 3, 4, 5]
        metrics["accuracy"] = float(accuracy_score(y_true, y_pred))
        metrics["macro_f1"] = float(f1_score(y_true, y_pred, labels=labels, average="macro", zero_division=0))
        metrics["weighted_f1"] = float(f1_score(y_true, y_pred, labels=labels, average="weighted", zero_division=0))
        for ct, prefix in [(3, "phase3_plus"), (4, "phase4_plus")]:
            bm = _binary_metrics(y_true, y_pred, ct)
            for k, v in bm.items():
                metrics[f"{prefix}_{k}"] = v
            binary_rows.append({"crisis_threshold": ct, **bm})
        # confusion-driven rates
        metrics["true_phase4_predicted_as_3_rate"] = _rate(y_true, y_pred, 4, 3)
        metrics["true_phase2_predicted_as_3_rate"] = _rate(y_true, y_pred, 2, 3)
        cm = confusion_matrix(y_true, y_pred, labels=labels)
        conf_df = pd.DataFrame(cm, index=[f"true_{l}" for l in labels], columns=[f"pred_{l}" for l in labels])
        # class distributions on covered subset
        for name, series in [("actual", y_true), ("predicted", y_pred)]:
            vc = series.value_counts().to_dict()
            for lab in labels:
                class_rows.append({"layer": name, "phase": lab, "count": int(vc.get(lab, 0))})

    unmatched_actual = pd.DataFrame({"area_id": sorted(act_ids - pred_ids)})
    unmatched_prediction = pd.DataFrame({"area_id": sorted(pred_ids - act_ids)})
    return ComparisonResult(
        per_area=per_area, coverage=coverage, metrics=metrics,
        class_distribution=pd.DataFrame(class_rows), confusion=conf_df,
        binary_metrics=pd.DataFrame(binary_rows), unmatched_actual=unmatched_actual,
        unmatched_prediction=unmatched_prediction,
    )


def _rate(y_true: pd.Series, y_pred: pd.Series, true_phase: int, pred_phase: int) -> Optional[float]:
    denom = int((y_true == true_phase).sum())
    if not denom:
        return None
    return float(((y_true == true_phase) & (y_pred == pred_phase)).sum()) / denom


def unavailable_actuals_comparison_summary(predictions: pd.DataFrame, target_period: str) -> dict:
    pred_ids = predictions["area_id"].astype(str).nunique() if "area_id" in predictions.columns else len(predictions)
    reason = f"target-period actuals are unavailable for {target_period}"
    return {
        "coverage": {
            "predicted_area_count": int(pred_ids),
            "target_period": target_period,
            "actuals_available": False,
            "covered_intersection_count": 0,
            "note": reason,
        },
        "metrics": {
            "status": "unavailable",
            "reason": reason,
            "descriptive_only": True,
        },
    }


def write_comparison_outputs(result: ComparisonResult, comparison_dir: Path, launch_month: str = "2026-04") -> None:
    comparison_dir.mkdir(parents=True, exist_ok=True)
    result.per_area.to_csv(comparison_dir / f"actual_crisis_{launch_month.replace('-', '_')}_by_area.csv", index=False)
    pd.DataFrame([result.coverage]).to_csv(comparison_dir / f"actual_coverage_summary_{launch_month.replace('-', '_')}.csv", index=False)
    pd.DataFrame([result.metrics]).to_csv(comparison_dir / f"comparison_metrics_actual_{launch_month.replace('-', '_')}_vs_prediction_{launch_month.replace('-', '_')}.csv", index=False)
    if not result.class_distribution.empty:
        result.class_distribution.to_csv(comparison_dir / f"class_distribution_actual_{launch_month.replace('-', '_')}_vs_prediction_{launch_month.replace('-', '_')}.csv", index=False)
    if not result.confusion.empty:
        result.confusion.to_csv(comparison_dir / f"confusion_matrix_actual_{launch_month.replace('-', '_')}_vs_prediction_{launch_month.replace('-', '_')}.csv")
    if not result.binary_metrics.empty:
        result.binary_metrics.to_csv(comparison_dir / f"binary_crisis_metrics_actual_{launch_month.replace('-', '_')}_vs_prediction_{launch_month.replace('-', '_')}.csv", index=False)
    result.unmatched_actual.to_csv(comparison_dir / "unmatched_actual_area_id.csv", index=False)
    result.unmatched_prediction.to_csv(comparison_dir / "unmatched_prediction_area_id.csv", index=False)
