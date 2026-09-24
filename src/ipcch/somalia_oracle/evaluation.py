"""Pooled metrics, reference baselines and the paired area-cluster bootstrap."""
from __future__ import annotations

import hashlib
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from ipcch.somalia_oracle import BOOTSTRAP_DRAWS, BOOTSTRAP_SEED


def _ratio(numerator: float, denominator: float, reason: str) -> Tuple[Optional[float], Optional[str]]:
    if denominator <= 0:
        return None, reason
    return float(numerator / denominator), None


def binary_metrics(truth: np.ndarray, predicted: np.ndarray, weights: Optional[np.ndarray] = None) -> Dict[str, object]:
    """Pooled confusion-count Phase 3+ metrics with explicit undefined reasons."""
    truth = np.asarray(truth, dtype=bool)
    predicted = np.asarray(predicted, dtype=bool)
    w = np.ones(truth.shape[0]) if weights is None else np.asarray(weights, dtype=np.float64)
    tp = float(w[truth & predicted].sum())
    fp = float(w[~truth & predicted].sum())
    fn = float(w[truth & ~predicted].sum())
    tn = float(w[~truth & ~predicted].sum())
    out: Dict[str, object] = {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "n": tp + fp + fn + tn}
    out["precision"], out["precision_reason"] = _ratio(tp, tp + fp, "no predicted positives")
    out["recall"], out["recall_reason"] = _ratio(tp, tp + fn, "no actual positives")
    out["f1"], out["f1_reason"] = _ratio(2 * tp, 2 * tp + fp + fn, "no actual or predicted positives")
    out["f2"], out["f2_reason"] = _ratio(5 * tp, 5 * tp + 4 * fn + fp, "no actual or predicted positives")
    out["prevalence"], _ = _ratio(tp + fn, out["n"], "empty cohort")
    return out


def f2_weighted(truth: np.ndarray, predicted: np.ndarray, weights: np.ndarray) -> np.ndarray:
    """F2 for each weight row (draws x rows); NaN where the denominator is zero."""
    tp = weights @ (truth & predicted).astype(np.float64)
    fp = weights @ (~truth & predicted).astype(np.float64)
    fn = weights @ (truth & ~predicted).astype(np.float64)
    denominator = 5 * tp + 4 * fn + fp
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(denominator > 0, 5 * tp / np.where(denominator > 0, denominator, 1.0), np.nan)


def r2_score_raw(truth: np.ndarray, pred: np.ndarray) -> Tuple[Optional[float], Optional[str]]:
    truth = np.asarray(truth, dtype=np.float64)
    pred = np.asarray(pred, dtype=np.float64)
    if truth.shape[0] < 2:
        return None, "fewer than two rows"
    total = ((truth - truth.mean()) ** 2).sum()
    if total == 0:
        return None, "constant truth"
    return float(1.0 - ((truth - pred) ** 2).sum() / total), None


def model_metrics(frame: pd.DataFrame) -> Dict[str, object]:
    """Metrics for one arm on one cohort frame (actual_crisis, overall_phase, phase_pred, q3, q3_pred)."""
    truth = frame["actual_crisis"].to_numpy() == 1
    predicted = frame["phase_pred"].to_numpy() >= 3
    out = binary_metrics(truth, predicted)
    out["accuracy"], out["accuracy_reason"] = _ratio(
        float((frame["overall_phase"].to_numpy() == frame["phase_pred"].to_numpy()).sum()), float(len(frame)), "empty cohort"
    )
    out["r2_q3"], out["r2_q3_reason"] = r2_score_raw(frame["q3"].to_numpy(), frame["q3_pred"].to_numpy())
    out["predicted_prevalence"], _ = _ratio(float(predicted.sum()), float(len(frame)), "empty cohort")
    for phase in range(1, 6):
        out[f"n_actual_phase{phase}"] = int((frame["overall_phase"].to_numpy() == phase).sum())
        out[f"n_pred_phase{phase}"] = int((frame["phase_pred"].to_numpy() == phase).sum())
    out["mean_q3_pred"] = float(frame["q3_pred"].mean()) if len(frame) else None
    return out


def persistence_metrics(frame: pd.DataFrame) -> Dict[str, object]:
    truth = frame["actual_crisis"].to_numpy() == 1
    predicted = frame["persistence_phase"].to_numpy() >= 3
    out = binary_metrics(truth, predicted)
    out["accuracy"], out["accuracy_reason"] = _ratio(
        float((frame["overall_phase"].to_numpy() == frame["persistence_phase"].to_numpy()).sum()), float(len(frame)), "empty cohort"
    )
    out["r2_q3"], out["r2_q3_reason"] = None, "not applicable: phase-only baseline"
    return out


def always_crisis_metrics(frame: pd.DataFrame) -> Dict[str, object]:
    truth = frame["actual_crisis"].to_numpy() == 1
    out = binary_metrics(truth, np.ones(truth.shape[0], dtype=bool))
    out["accuracy"], out["accuracy_reason"] = None, "not applicable: binary-only reference"
    out["r2_q3"], out["r2_q3_reason"] = None, "not applicable: binary-only reference"
    return out


def cohort_hash(keys: pd.DataFrame) -> str:
    text = keys.sort_values(["area_id", "target_ord"]).to_csv(index=False, lineterminator="\n")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def bootstrap_multiplicities(n_areas: int, draws: int = BOOTSTRAP_DRAWS, seed: int = BOOTSTRAP_SEED) -> np.ndarray:
    rng = np.random.Generator(np.random.PCG64(seed))
    counts = np.empty((draws, n_areas), dtype=np.int32)
    for d in range(draws):
        counts[d] = np.bincount(rng.integers(0, n_areas, size=n_areas), minlength=n_areas)
    return counts


def paired_bootstrap(
    cohort: pd.DataFrame,
    truth: np.ndarray,
    vectors: Mapping[str, np.ndarray],
    contrasts: Sequence[Tuple[str, str]],
    draws: int = BOOTSTRAP_DRAWS,
    seed: int = BOOTSTRAP_SEED,
) -> Tuple[List[Dict[str, object]], Dict[str, object]]:
    """Whole-area resampling with shared multiplicities for every compared vector.

    ``vectors`` maps a name to the Phase 3+ predicted-positive vector over the
    cohort rows (same order as ``cohort``). Returns contrast rows plus the replay
    bundle (ordered areas, multiplicities, deltas).
    """
    areas = np.array(sorted(cohort["area_id"].unique()))
    area_pos = np.searchsorted(areas, cohort["area_id"].to_numpy())
    truth = np.asarray(truth, dtype=bool)
    bundle: Dict[str, object] = {"areas": areas, "seed": seed, "draws": draws, "rng": "numpy.random.Generator(PCG64)"}
    rows: List[Dict[str, object]] = []
    if len(areas) < 2:
        for a, b in contrasts:
            point = _point_delta(truth, vectors[a], vectors[b])
            rows.append({"contrast": f"{a}-{b}", "point_delta_f2": point, "ci_low": None, "ci_high": None, "interval_status": "unavailable", "interval_reason": "fewer than two areas", "valid_draws": 0, "undefined_draws": None})
        return rows, bundle
    multiplicities = bootstrap_multiplicities(len(areas), draws, seed)
    weights = multiplicities[:, area_pos].astype(np.float64)
    bundle["multiplicities"] = multiplicities
    scores = {name: f2_weighted(truth, np.asarray(vec, dtype=bool), weights) for name, vec in vectors.items()}
    for a, b in contrasts:
        delta = scores[a] - scores[b]
        undefined = int(np.isnan(delta).sum())
        point = _point_delta(truth, vectors[a], vectors[b])
        row = {"contrast": f"{a}-{b}", "point_delta_f2": point, "valid_draws": int(draws - undefined), "undefined_draws": undefined}
        if point is None:
            row.update(ci_low=None, ci_high=None, interval_status="unavailable", interval_reason="point F2 undefined")
        elif undefined:
            row.update(ci_low=None, ci_high=None, interval_status="unavailable", interval_reason=f"{undefined} undefined paired draws")
        else:
            low, high = np.quantile(delta, [0.025, 0.975], method="linear")
            row.update(ci_low=float(low), ci_high=float(high), interval_status="ok", interval_reason=None)
        bundle[f"delta::{a}-{b}"] = delta
        rows.append(row)
    return rows, bundle


def _point_delta(truth: np.ndarray, a: np.ndarray, b: np.ndarray) -> Optional[float]:
    fa = binary_metrics(truth, a)["f2"]
    fb = binary_metrics(truth, b)["f2"]
    if fa is None or fb is None:
        return None
    return float(fa - fb)
