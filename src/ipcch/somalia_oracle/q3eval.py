"""q3-first reporting: share error, raw/final discrimination, fixed q3>=.2 decisions, baselines, bootstrap."""
from __future__ import annotations

from typing import Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import roc_auc_score

from ipcch.somalia_oracle import evaluation as ev
from ipcch.somalia_oracle import modeling as md

BINARY_THRESHOLD = 0.2


def _nan(x) -> float:
    return float("nan") if x is None else float(x)


def share_metrics(truth: np.ndarray, pred: np.ndarray, weights: Optional[np.ndarray] = None) -> Dict[str, float]:
    truth = np.asarray(truth, dtype=np.float64)
    pred = np.asarray(pred, dtype=np.float64)
    w = np.ones(truth.size) if weights is None else np.asarray(weights, dtype=np.float64)
    total = w.sum()
    if total <= 0:
        return {"r2": np.nan, "rmse": np.nan, "mae": np.nan, "bias": np.nan, "mean_truth": np.nan, "mean_pred": np.nan}
    err = pred - truth
    mean_t = (w * truth).sum() / total
    ss_tot = (w * (truth - mean_t) ** 2).sum()
    return {
        "r2": float(1 - (w * err ** 2).sum() / ss_tot) if ss_tot > 0 else np.nan,
        "rmse": float(np.sqrt((w * err ** 2).sum() / total)),
        "mae": float((w * np.abs(err)).sum() / total),
        "bias": float((w * err).sum() / total),
        "mean_truth": float(mean_t),
        "mean_pred": float((w * pred).sum() / total),
    }


def pooled_auc(crisis: np.ndarray, score: np.ndarray, weights: Optional[np.ndarray] = None) -> float:
    crisis = np.asarray(crisis) == 1
    if weights is not None:
        keep = np.asarray(weights) > 0
        if np.unique(crisis[keep]).size < 2:
            return np.nan
        return float(roc_auc_score(crisis[keep], np.asarray(score)[keep], sample_weight=np.asarray(weights)[keep]))
    if np.unique(crisis).size < 2:
        return np.nan
    return float(roc_auc_score(crisis, score))


def within_month_auc(frame: pd.DataFrame, score_col: str) -> Tuple[float, int, int]:
    values, undefined = [], 0
    for _, g in frame.groupby("target_ord"):
        crisis = g["actual_crisis"].to_numpy() == 1
        if np.unique(crisis).size < 2:
            undefined += 1
            continue
        values.append(roc_auc_score(crisis, g[score_col]))
    return (float(np.mean(values)) if values else np.nan), len(values), undefined


def binary_metrics(crisis: np.ndarray, predicted: np.ndarray) -> Dict[str, float]:
    m = ev.binary_metrics(np.asarray(crisis) == 1, np.asarray(predicted, dtype=bool))
    return {"f1": _nan(m["f1"]), "recall": _nan(m["recall"]), "precision": _nan(m["precision"]), "f2": _nan(m["f2"]), "tp": m["tp"], "fp": m["fp"], "fn": m["fn"], "tn": m["tn"]}


def model_view_metrics(frame: pd.DataFrame) -> Dict[str, object]:
    """Frame: q3 truth, actual_crisis, overall_phase, q3_raw, q3_final, q2_raw, q4_raw, q5_raw, clipped, branch."""
    out: Dict[str, object] = {"n": int(len(frame)), "n_areas": int(frame["area_id"].nunique())}
    raw = share_metrics(frame["q3"], frame["q3_raw"])
    final = share_metrics(frame["q3"], frame["q3_final"])
    out.update({f"raw_{k}": v for k, v in raw.items()})
    out.update({f"final_{k}": v for k, v in final.items()})
    out["raw_auc"] = pooled_auc(frame["actual_crisis"], frame["q3_raw"])
    out["final_auc"] = pooled_auc(frame["actual_crisis"], frame["q3_final"])
    out["final_within_month_auc"], out["within_month_auc_months"], out["within_month_auc_undefined_months"] = within_month_auc(frame, "q3_final")
    out["raw_within_month_auc"], _, _ = within_month_auc(frame, "q3_raw")
    binary = frame["q3_final"].to_numpy() >= BINARY_THRESHOLD
    out.update({f"bin_{k}": v for k, v in binary_metrics(frame["actual_crisis"], binary).items()})
    legacy = md.phase_from_predictions(frame[["q2_raw", "q3_raw", "q4_raw", "q5_raw"]].to_numpy())
    out["legacy_phase_accuracy"] = float((legacy == frame["overall_phase"].to_numpy()).mean())
    out.update({f"legacy_{k}": v for k, v in binary_metrics(frame["actual_crisis"], legacy >= 3).items()})
    out["q3_binary_vs_legacy_disagreements"] = int((binary != (legacy >= 3)).sum())
    out["n_clipped"] = int(frame["clipped"].sum())
    out["n_fallback_direct"] = int((frame["branch"] == "fallback_direct").sum())
    out["n_residual_branch"] = int((frame["branch"] == "residual").sum())
    return out


def v1_calibrated_d(v1_dir, cohort_keys: pd.DataFrame, ledger: pd.DataFrame) -> pd.DataFrame:
    """v1 arm-D raw q3 and its isotonic calibration (inner-validation, selected candidate)."""
    preds = pd.read_csv(v1_dir / "predictions" / "predictions.csv.gz")
    preds = preds.loc[preds["arm"] == "D"]
    val = pd.read_csv(v1_dir / "fits" / "validation_predictions.csv.gz")
    status = pd.read_csv(v1_dir / "fits" / "arm_job_status.csv")
    val = val.merge(status[["job_id", "arm", "selected_candidate"]], on=["job_id", "arm"])
    val = val.loc[(val["arm"] == "D") & (val["candidate"] == val["selected_candidate"])].merge(ledger[["area_id", "target_ord", "q3"]], on=["area_id", "target_ord"])
    parts = []
    for job, g in preds.groupby("job_id"):
        v = val.loc[val["job_id"] == job]
        iso = IsotonicRegression(y_min=0, y_max=1, out_of_bounds="clip").fit(v["q3_pred"], v["q3"])
        parts.append(g.assign(v1_q3_raw=g["q3_pred"], v1_q3_cal=iso.predict(g["q3_pred"])))
    out = pd.concat(parts, ignore_index=True)[["test_year", "horizon", "area_id", "target_ord", "v1_q3_raw", "v1_q3_cal"]]
    return out.merge(cohort_keys, on=["test_year", "horizon", "area_id", "target_ord"])


def paired_share_bootstrap(frame: pd.DataFrame, truth_col: str, crisis_col: str, a_col: str, b_col: str, draws: int, seed: int) -> Dict[str, object]:
    """Paired whole-area bootstrap of delta R2 / RMSE / AUC (a minus b) on identical rows."""
    frame = frame.sort_values(["area_id", "target_ord"]).reset_index(drop=True)
    areas = np.array(sorted(frame["area_id"].unique()))
    y, c = frame[truth_col].to_numpy(dtype=float), frame[crisis_col].to_numpy()
    a, b = frame[a_col].to_numpy(dtype=float), frame[b_col].to_numpy(dtype=float)
    point = {}
    for metric in ("r2", "rmse"):
        point[metric] = share_metrics(y, a)[metric] - share_metrics(y, b)[metric]
    point["auc"] = pooled_auc(c, a) - pooled_auc(c, b)
    result = {"n": len(frame), "n_areas": len(areas), "areas": areas}
    if len(areas) < 2:
        for metric in point:
            result[metric] = {"point": point[metric], "ci_low": np.nan, "ci_high": np.nan, "status": "unavailable", "reason": "fewer than two areas", "undefined_draws": None}
        return result
    mult = ev.bootstrap_multiplicities(len(areas), draws, seed)
    w = mult[:, np.searchsorted(areas, frame["area_id"].to_numpy())].astype(float)
    result["multiplicities"] = mult
    deltas = {m: np.empty(draws) for m in point}
    for d in range(draws):
        wd = w[d]
        sa, sb = share_metrics(y, a, wd), share_metrics(y, b, wd)
        deltas["r2"][d] = sa["r2"] - sb["r2"]
        deltas["rmse"][d] = sa["rmse"] - sb["rmse"]
        deltas["auc"][d] = pooled_auc(c, a, wd) - pooled_auc(c, b, wd)
    for metric, values in deltas.items():
        undefined = int(np.isnan(values).sum())
        entry = {"point": point[metric], "undefined_draws": undefined, "draws": values}
        if np.isnan(point[metric]):
            entry.update(ci_low=np.nan, ci_high=np.nan, status="unavailable", reason="point metric undefined")
        elif undefined:
            entry.update(ci_low=np.nan, ci_high=np.nan, status="unavailable", reason=f"{undefined} undefined paired draws")
        else:
            low, high = np.quantile(values, [0.025, 0.975], method="linear")
            entry.update(ci_low=float(low), ci_high=float(high), status="ok", reason=None)
        result[metric] = entry
    return result
