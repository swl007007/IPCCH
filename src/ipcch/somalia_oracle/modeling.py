"""Temporal candidate selection and final cumulative-regressor fits."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from ipcch import paths
from ipcch.somalia_oracle import (
    CUMULATIVE_COLUMNS,
    HALF_LIFE_MONTHS,
    INNER_VALIDATION_MONTHS,
    MIN_SUPPORTED_INNER_MONTHS,
    PHASE_THRESHOLD,
    PREDICTION_COLUMNS,
)

CANDIDATE_CONFIG_PATH = paths.CONFIG_DIR / "somalia_oracle_candidates.json"


class ModelingError(RuntimeError):
    """A fitting or selection invariant does not hold."""


def load_candidates(path: Path = CANDIDATE_CONFIG_PATH) -> Dict[str, object]:
    config = json.loads(Path(path).read_text(encoding="utf-8"))
    if config["selection_metric"] != "phase3plus_f2" or config["tie_break"] != "candidate_order":
        raise ModelingError("candidate config selection contract changed")
    if float(config["phase_threshold"]) != PHASE_THRESHOLD or float(config["half_life_months"]) != HALF_LIFE_MONTHS:
        raise ModelingError("candidate config threshold/half-life drifted from the frozen constants")
    if len(config["candidates"]) != 6:
        raise ModelingError("exactly six candidate bundles are required")
    return config


def candidate_params(config: Mapping[str, object], candidate: Mapping[str, object], target: str) -> Dict[str, object]:
    params = dict(candidate["common"])
    if target == "q3":
        params.update(candidate["phase3_overrides"])
    params.update(config["common_runtime"])
    return params


def decay_weights(target_ord: np.ndarray, fit_origin_ord: int, half_life: float = HALF_LIFE_MONTHS) -> np.ndarray:
    distance = int(fit_origin_ord) - np.asarray(target_ord, dtype=np.int64)
    if (distance < 0).any():
        raise ModelingError("a fitting label is after its fit origin")
    return np.power(0.5, distance.astype(np.float64) / float(half_life))


def phase_from_predictions(pred: np.ndarray, threshold: float = PHASE_THRESHOLD) -> np.ndarray:
    """Unrounded descending phase5->phase2 conversion; ``>=`` threshold; default 1 (G3)."""
    pred = np.asarray(pred, dtype=np.float64)
    if not np.isfinite(pred).all():
        raise ModelingError("non-finite cumulative prediction on an eligible row")
    phase = np.ones(pred.shape[0], dtype=np.int64)
    assigned = np.zeros(pred.shape[0], dtype=bool)
    for position, value in ((3, 5), (2, 4), (1, 3), (0, 2)):
        hit = ~assigned & (pred[:, position] >= threshold)
        phase[hit] = value
        assigned |= hit
    return phase


def f2_from_counts(tp: float, fp: float, fn: float) -> Optional[float]:
    denominator = 5 * tp + 4 * fn + fp
    if denominator <= 0:
        return None
    return float(5 * tp / denominator)


@dataclass
class FittedRegressor:
    target: str
    kind: str  # "xgboost" | "constant"
    model: object = None
    constant: Optional[float] = None
    n_rows: int = 0

    def predict(self, X: np.ndarray) -> np.ndarray:
        if self.kind == "constant":
            return np.full(X.shape[0], float(self.constant), dtype=np.float64)
        return np.asarray(self.model.predict(X), dtype=np.float64)


def fit_regressor(X: np.ndarray, y: np.ndarray, weights: np.ndarray, params: Mapping[str, object], target: str) -> FittedRegressor:
    if X.shape[0] == 0:
        raise ModelingError(f"no fitting rows for {target}")
    if np.nanmax(y) == np.nanmin(y):
        return FittedRegressor(target=target, kind="constant", constant=float(y[0]), n_rows=int(X.shape[0]))
    import xgboost as xgb

    model = xgb.XGBRegressor(**params)
    model.fit(X, y, sample_weight=weights)
    return FittedRegressor(target=target, kind="xgboost", model=model, n_rows=int(X.shape[0]))


def fit_ensemble(X: np.ndarray, Y: np.ndarray, weights: np.ndarray, config, candidate) -> List[FittedRegressor]:
    return [
        fit_regressor(X, Y[:, i], weights, candidate_params(config, candidate, target), target)
        for i, target in enumerate(CUMULATIVE_COLUMNS)
    ]


def predict_ensemble(models: Sequence[FittedRegressor], X: np.ndarray) -> np.ndarray:
    return np.column_stack([m.predict(X) for m in models])


@dataclass
class ArmJobResult:
    job_id: str
    arm: str
    status: str
    reason: Optional[str]
    selected_candidate: Optional[str]
    inner_folds: List[Dict[str, object]] = field(default_factory=list)
    candidate_scores: List[Dict[str, object]] = field(default_factory=list)
    validation_predictions: Optional[pd.DataFrame] = None
    predictions: Optional[pd.DataFrame] = None
    fit_ledger: Optional[pd.DataFrame] = None
    final_models: List[FittedRegressor] = field(default_factory=list)


def plan_inner_folds(pool: pd.DataFrame, horizon: int, candidate_years: Sequence[int]) -> List[Dict[str, object]]:
    """Latest three distinct eligible target months; each with its own origin cutoff."""
    months = sorted(pool["target_ord"].unique())[-INNER_VALIDATION_MONTHS:]
    folds = []
    for v in months:
        ov = int(v) - int(horizon)
        cutoff = min(ov, int(v) - 1)
        fit_rows = pool.index[(pool["target_ord"] <= cutoff) & pool["target_year"].isin(candidate_years)]
        val_rows = pool.index[(pool["target_ord"] == v) & pool["valid_score"]]
        reason = None
        if len(fit_rows) == 0:
            reason = "empty_inner_fitting_pool"
        elif len(val_rows) == 0:
            reason = "no_scorable_validation_rows"
        folds.append(
            {
                "validation_ord": int(v),
                "inner_origin_ord": ov,
                "fit_label_cutoff_ord": cutoff,
                "fit_rows": fit_rows,
                "val_rows": val_rows,
                "supported": reason is None,
                "reason": reason,
            }
        )
    return folds


def run_arm_job(
    job: Mapping[str, object],
    arm: str,
    frame: pd.DataFrame,
    feature_columns: Sequence[str],
    config: Mapping[str, object],
    eval_index: pd.Index,
    fit_pool_index: pd.Index,
    keep_models: bool = False,
) -> ArmJobResult:
    """Inner temporal F2 selection, then refit on the clipped outer pool and predict."""
    X_all = frame.loc[:, list(feature_columns)].to_numpy(dtype=np.float32)
    position = pd.Series(np.arange(len(frame)), index=frame.index)
    targets = frame.loc[:, list(CUMULATIVE_COLUMNS)].to_numpy(dtype=np.float64)
    pool = frame.loc[fit_pool_index]
    horizon = int(job["horizon"])
    candidate_years = tuple(job["candidate_years"])
    folds = plan_inner_folds(pool, horizon, candidate_years)
    result = ArmJobResult(job_id=job["job_id"], arm=arm, status="pending", reason=None, selected_candidate=None)
    for fold in folds:
        result.inner_folds.append(
            {
                "job_id": job["job_id"],
                "arm": arm,
                "validation_ord": fold["validation_ord"],
                "inner_origin_ord": fold["inner_origin_ord"],
                "fit_label_cutoff_ord": fold["fit_label_cutoff_ord"],
                "n_fit": int(len(fold["fit_rows"])),
                "n_validation": int(len(fold["val_rows"])),
                "fit_max_target_ord": int(frame.loc[fold["fit_rows"], "target_ord"].max()) if len(fold["fit_rows"]) else None,
                "supported": fold["supported"],
                "reason": fold["reason"],
            }
        )
    supported = [f for f in folds if f["supported"]]
    if len(supported) < MIN_SUPPORTED_INNER_MONTHS:
        result.status, result.reason = "unsupported", f"only {len(supported)} supported inner validation months"
        return result
    val_truth = np.concatenate([frame.loc[f["val_rows"], "actual_crisis"].to_numpy(dtype=np.float64) for f in supported])
    if val_truth.min() == val_truth.max():
        result.status, result.reason = "unsupported", "pooled validation truth lacks a crisis or noncrisis class"
        return result

    val_frames = []
    best = None
    for order, candidate in enumerate(config["candidates"]):
        tp = fp = fn = 0
        for fold in supported:
            fit_pos = position[fold["fit_rows"]].to_numpy()
            val_pos = position[fold["val_rows"]].to_numpy()
            weights = decay_weights(frame["target_ord"].to_numpy()[fit_pos], fold["inner_origin_ord"])
            models = fit_ensemble(X_all[fit_pos], targets[fit_pos], weights, config, candidate)
            pred = predict_ensemble(models, X_all[val_pos])
            phase = phase_from_predictions(pred)
            truth = frame["actual_crisis"].to_numpy()[val_pos] == 1
            predicted = phase >= 3
            tp += int((truth & predicted).sum())
            fp += int((~truth & predicted).sum())
            fn += int((truth & ~predicted).sum())
            vf = frame.loc[fold["val_rows"], ["area_id", "target_ord"]].copy()
            vf["job_id"], vf["arm"], vf["candidate"], vf["validation_ord"] = job["job_id"], arm, candidate["id"], fold["validation_ord"]
            for i, column in enumerate(PREDICTION_COLUMNS):
                vf[column] = pred[:, i]
            vf["phase_pred"] = phase
            vf["actual_crisis"] = frame["actual_crisis"].to_numpy()[val_pos]
            val_frames.append(vf)
        score = f2_from_counts(tp, fp, fn)
        result.candidate_scores.append(
            {"job_id": job["job_id"], "arm": arm, "candidate": candidate["id"], "order": order, "tp": tp, "fp": fp, "fn": fn, "f2": score}
        )
        if score is not None and (best is None or score > best[0]):
            best = (score, candidate)
    result.validation_predictions = pd.concat(val_frames, ignore_index=True)
    if best is None:
        result.status, result.reason = "unsupported", "validation F2 undefined for every candidate"
        return result
    selected = best[1]
    result.selected_candidate = selected["id"]

    fit_pos = position[fit_pool_index].to_numpy()
    weights = decay_weights(frame["target_ord"].to_numpy()[fit_pos], int(job["origin_ord"]))
    models = fit_ensemble(X_all[fit_pos], targets[fit_pos], weights, config, selected)
    eval_pos = position[eval_index].to_numpy()
    pred = predict_ensemble(models, X_all[eval_pos])
    phase = phase_from_predictions(pred)
    predictions = frame.loc[eval_index, ["area_id", "target_ord", "origin_ord"]].copy()
    predictions["job_id"], predictions["arm"], predictions["selected_candidate"] = job["job_id"], arm, selected["id"]
    for i, column in enumerate(PREDICTION_COLUMNS):
        predictions[column] = pred[:, i]
    predictions["phase_pred"] = phase
    result.predictions = predictions
    ledger = frame.loc[fit_pool_index, ["area_id", "target_ord"]].copy()
    ledger["job_id"], ledger["arm"], ledger["weight"] = job["job_id"], arm, weights
    result.fit_ledger = ledger
    result.final_models = models if keep_models else []
    result.status = "completed"
    return result
