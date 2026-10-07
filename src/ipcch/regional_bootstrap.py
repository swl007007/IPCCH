"""Country-stratified whole-area paired bootstrap of saved global predictions (no model fitting).

Contract (task ``10-07-origin-safe-no-weather-oracle-baseline``, design "Region3 saved-prediction comparison"):

- Per period, countries and their observed areas are sorted; one ``PCG64(seed)`` generator per period advances
  through the sorted countries, drawing an ``(n_draws, N_c)`` block of area indices with replacement for each
  country ``c``. An area's multiplicity is the number of times it was drawn; every row of the area carries it.
  The same multiplicities are shared by every arm, horizon, metric and contrast.
- Metrics are the global origin-safe definitions (``ipcch.origin_safe.origin_metrics``) with integer row
  weights, equivalent to explicit row duplication; observation rows keep equal weight.
- Paired-difference intervals are conditional: percentiles over draws where both compared metrics are defined,
  reported only with at least ``MIN_VALID_DRAWS`` such draws; invalid counts/fractions are always reported.
"""
from __future__ import annotations

from typing import Dict, Tuple

import numpy as np
import pandas as pd

from ipcch import origin_safe as osf

N_DRAWS = 2000
SEED = 42
MIN_VALID_DRAWS = 1000
QUANTILES = (0.025, 0.975)
QUANTILE_METHOD = "linear"
INTERVAL_TYPE = "conditional 95% percentile interval over jointly defined paired draws"


def stratified_area_multiplicities(areas: pd.DataFrame, n_draws: int = N_DRAWS, seed: int = SEED) -> Dict[str, object]:
    """``areas``: one row per observed area with ``area_id`` and ``iso3``. Returns sorted ids and (n_draws, n_areas) counts."""
    if areas["area_id"].duplicated().any():
        raise ValueError("areas must be unique")
    if areas["iso3"].isna().any():
        raise ValueError("every area needs a country stratum")
    ordered = areas.sort_values(["iso3", "area_id"], kind="mergesort").reset_index(drop=True)
    rng = np.random.Generator(np.random.PCG64(seed))
    counts = np.zeros((n_draws, len(ordered)), dtype=np.int32)
    sizes = {}
    start = 0
    for country, block in ordered.groupby("iso3", sort=True):
        n_c = len(block)
        picks = rng.integers(0, n_c, size=(n_draws, n_c))
        rows = np.repeat(np.arange(n_draws), n_c)
        np.add.at(counts, (rows, start + picks.ravel()), 1)
        sizes[country] = n_c
        start += n_c
    return {"area_id": ordered["area_id"].to_numpy(), "iso3": ordered["iso3"].to_numpy(), "multiplicity": counts,
            "stratum_sizes": sizes, "seed": seed, "n_draws": n_draws, "generator": "numpy.random.Generator(PCG64(seed))",
            "draw_order": "countries sorted by ISO3; per country one rng.integers(0, N_c, size=(n_draws, N_c)) block; areas sorted by area_id within country"}


def weighted_metrics(frame: pd.DataFrame, weights: np.ndarray) -> Dict[str, Tuple[np.ndarray, np.ndarray]]:
    """Eight global metrics for each weight vector (rows of ``weights``): {metric: (values, defined)}.

    Undefined cases follow ``compute_metrics``: precision with zero predicted 3+ weight, recall with zero observed
    3+ weight, F2 when either is undefined or 4P+R == 0, R² with fewer than two weighted rows or a target that is
    exactly constant over positive-weight rows.
    """
    W = np.atleast_2d(np.asarray(weights, dtype=float))
    y = frame["overall_phase"].to_numpy(dtype=float)
    p = frame["overall_phase_pred"].to_numpy(dtype=float)
    t = frame["phase3_worse"].to_numpy(dtype=float)
    s = frame["phase3_pred"].to_numpy(dtype=float)
    if not (np.isfinite(y).all() and np.isfinite(p).all() and np.isfinite(t).all() and np.isfinite(s).all()):
        raise ValueError("regional metric inputs must be complete")
    if W.shape[1] != len(frame) or (W < 0).any():
        raise ValueError("weights must be non-negative and aligned with rows")
    total = W.sum(axis=1)
    defined_all = total > 0
    obs3, pred3 = y >= 3, p >= 3
    out = {}
    with np.errstate(invalid="ignore", divide="ignore"):
        out["exact_phase_accuracy"] = (W @ (y == p) / total, defined_all)
        out["phase3plus_accuracy"] = (W @ (obs3 == pred3) / total, defined_all)
        tp, pp, op = W @ (obs3 & pred3), W @ pred3, W @ obs3
        precision, recall = tp / pp, tp / op
        p_ok, r_ok = pp > 0, op > 0
        out["precision_phase3plus"] = (np.where(p_ok, precision, np.nan), p_ok)
        out["sensitivity_phase3plus"] = (np.where(r_ok, recall, np.nan), r_ok)
        denominator = 4 * precision + recall
        f_ok = p_ok & r_ok & (denominator != 0)
        out["f2_phase3plus"] = (np.where(f_ok, 5 * precision * recall / denominator, np.nan), f_ok)
        positive = W > 0
        nonconstant = np.where(positive, t, -np.inf).max(axis=1) != np.where(positive, t, np.inf).min(axis=1)
        r_def = (total >= 2) & nonconstant
        mean = (W @ t) / total
        ss_tot = (W * (t[None, :] - mean[:, None]) ** 2).sum(axis=1)
        ss_res = W @ ((t - s) ** 2)
        out["r2_phase3plus"] = (np.where(r_def, 1.0 - ss_res / ss_tot, np.nan), r_def)
        out["mae_phase3plus"] = (W @ np.abs(t - s) / total, defined_all)
        out["ordinal_mae"] = (W @ np.abs(y - p) / total, defined_all)
    return {m: (np.where(d, v, np.nan), d) for m, (v, d) in out.items()}


def duplicated_metrics(frame: pd.DataFrame, weights: np.ndarray) -> Dict[str, object]:
    """Reference path: explicit row duplication through the global evaluator (``osf.origin_metrics``)."""
    repeated = frame.loc[frame.index.repeat(np.asarray(weights, dtype=int))]
    result = osf.origin_metrics(repeated, "overall", "check")
    return {m: result[m]["value"] for m in osf.ORIGIN_METRICS}


def conditional_interval(delta: np.ndarray, valid: np.ndarray, point_defined: bool, has_multi_area_stratum: bool,
                         min_valid: int = MIN_VALID_DRAWS) -> Dict[str, object]:
    delta = np.asarray(delta, dtype=float)
    valid = np.asarray(valid, dtype=bool)
    n_valid = int(valid.sum())
    out = {"interval_type": INTERVAL_TYPE, "draws_total": len(delta), "draws_valid": n_valid, "draws_invalid": len(delta) - n_valid,
           "invalid_fraction": (len(delta) - n_valid) / len(delta) if len(delta) else None, "min_valid_draws": min_valid,
           "ci_lower": None, "ci_upper": None, "ci_status": "unavailable", "ci_reason": None}
    if not point_defined:
        out["ci_reason"] = "observed point metric undefined for at least one compared arm"
    elif not has_multi_area_stratum:
        out["ci_reason"] = "no country stratum with at least two areas"
    elif n_valid < min_valid:
        out["ci_reason"] = f"{n_valid} jointly valid paired draws < {min_valid}"
    else:
        lower, upper = np.quantile(delta[valid], QUANTILES, method=QUANTILE_METHOD)
        out.update(ci_lower=float(lower), ci_upper=float(upper), ci_status="conditional", ci_reason=None)
    return out


TRUTH_COLUMNS = ("overall_phase", *osf.SHARE_COLUMNS, *osf.CUMULATIVE_TARGETS)


def align_paired_predictions(frames: Dict[object, pd.DataFrame]) -> Dict[object, pd.DataFrame]:
    """Sort every run's rows on (area_id, year, month) and require identical keys and truths across runs.

    Saved key hashes are order-sensitive; pairing is defined on this explicit sorted index instead.
    """
    keys = list(osf.KEYS)
    aligned, reference = {}, None
    for name, frame in frames.items():
        if frame.duplicated(keys).any():
            raise ValueError(f"{name}: duplicate prediction keys")
        ordered = frame.sort_values(keys, kind="mergesort").reset_index(drop=True)
        if reference is None:
            reference = ordered
        else:
            if not ordered[keys].equals(reference[keys]):
                raise ValueError(f"{name}: prediction keys differ from the first run")
            for column in TRUTH_COLUMNS:
                if not np.array_equal(ordered[column].to_numpy(dtype=float), reference[column].to_numpy(dtype=float)):
                    raise ValueError(f"{name}: {column} differs across paired runs")
        aligned[name] = ordered
    return aligned
