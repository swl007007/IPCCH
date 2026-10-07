"""Perfect-weather oracle features appended to the origin-safe reference (``origin_safe_weather_oracle_v1``).

Contract (task ``10-07-origin-safe-no-weather-oracle-baseline``):

- Row origin ``O = T - H``; window ``m = min(H, 6)``; only H = 3/6/12 receive oracle columns (H0 none).
- Raw oracle: shared monthly ``prcp_anom_month_ensmean`` and ``tmean_anom_month_ensmean`` observed at
  ``O+1 .. O+m``, looked up by calendar month (never by row offset). Realized values are treated as
  100%-accurate forecasts assumed available at ``O``; the actual observation month is recorded separately.
  This is the only exception to the origin-safe timing rules; IPC history, IDP, growing season and fitting
  labels keep their existing cutoffs.
- B6 per variable: ``F`` = mean of the ``m`` future months (all finite); ``B = (R + F) / 2`` with ``R`` the
  saved parent trailing mean over ``O-m+1 .. O`` (requires F, R and all ``m`` past months finite);
  ``Q = F * 1[overall_phase_history_1 >= 3]`` (requires F and safe history1). Missing stays NaN; a missing F
  is never turned into zero by a zero gate. The gate is internal, not a predictor.
"""
from __future__ import annotations

from typing import Dict, List, Mapping, Sequence, Tuple

import numpy as np
import pandas as pd

from ipcch import origin_safe as osf

ORACLE_VERSION = "origin_safe_weather_oracle_v1"
PARENT_VERSION = "origin_safe_climate_idp_v1"
PARENT_ARM = "climate_safe_history_idp"
ORACLE_VARIABLES = ("prcp_anom_month_ensmean", "tmean_anom_month_ensmean")
ORACLE_HORIZONS = (3, 6, 12)
MAX_FUTURE_MONTHS = 6
RAW_ARM = "climate_safe_history_idp_oracle"
B6_ARM = "climate_safe_history_idp_oracle_b6"
ORACLE_ARMS = (RAW_ARM, B6_ARM)
HISTORY_GATE = osf.HISTORY_VALUES[0]
CRISIS_PHASE = 3
EXPECTED_FEATURE_COUNTS = {(3, RAW_ARM): 876, (3, B6_ARM): 882, (6, RAW_ARM): 882, (6, B6_ARM): 888,
                           (12, RAW_ARM): 666, (12, B6_ARM): 672}


def window(horizon: int) -> int:
    if int(horizon) not in ORACLE_HORIZONS:
        raise ValueError(f"oracle horizons are {ORACLE_HORIZONS}; H={horizon} uses the shared reference only")
    return min(int(horizon), MAX_FUTURE_MONTHS)


def raw_name(variable: str, offset: int) -> str:
    return f"oracle_{variable}_o{offset}"


def future_mean_name(variable: str, m: int) -> str:
    return f"oracle_{variable}__wmean_o1_o{m}"


def halfmean_name(variable: str, m: int) -> str:
    return f"oracle_{variable}__halfmean_roll{m}_o1_o{m}"


def gated_name(variable: str, m: int) -> str:
    return f"oracle_{variable}__wmean_o1_o{m}__x__crisis_history_1_ge3"


def raw_features(horizon: int) -> List[str]:
    """Increasing future offset; precipitation then temperature at each offset."""
    m = window(horizon)
    return [raw_name(v, k) for k in range(1, m + 1) for v in ORACLE_VARIABLES]


def b6_features(horizon: int) -> List[str]:
    """F, B, Q for precipitation, then F, B, Q for temperature."""
    m = window(horizon)
    return [name(v, m) for v in ORACLE_VARIABLES for name in (future_mean_name, halfmean_name, gated_name)]


def parent_rolling_column(variable: str, horizon: int) -> str:
    """Existing trailing mean over O-m+1 .. O in the parent dataset."""
    m = window(horizon)
    return f"{variable}__roll6_mean_asof12" if horizon == 12 else f"{variable}__roll{m}_mean_asof{horizon}_s{horizon}"


def appended_features(arm: str, horizon: int) -> List[str]:
    if arm == RAW_ARM:
        return raw_features(horizon)
    if arm == B6_ARM:
        return raw_features(horizon) + b6_features(horizon)
    raise ValueError(f"unknown oracle arm {arm!r}; allowed {ORACLE_ARMS}")


def arm_features(parent_features: Sequence[str], arm: str, horizon: int) -> List[str]:
    """Exact fitted order: the parent reference features unchanged, then the declared oracle columns."""
    added = appended_features(arm, horizon)
    clash = sorted(set(parent_features) & set(added))
    if clash:
        raise ValueError(f"oracle names collide with parent features {clash}")
    return list(parent_features) + added


# --------------------------------------------------------------------------- construction


def calendar_lookup(grid, area_ids, ords) -> np.ndarray:
    """Value of the grid at (area, calendar month); NaN outside the grid. ``grid`` is a climate2015 ``Grid``."""
    ai, mi, ok = grid.index_of(np.asarray(area_ids), np.asarray(ords, dtype=np.int64))
    out = {}
    for v in ORACLE_VARIABLES:
        values = grid.values[v][ai, mi]
        out[v] = np.where(ok, values, np.nan)
    return out


def assert_finite_or_missing(grid) -> None:
    for v in ORACLE_VARIABLES:
        if np.isinf(grid.values[v]).any():
            raise ValueError(f"{v}: non-finite source values other than missing")


def oracle_terms(future: Mapping[str, np.ndarray], past_complete: Mapping[str, np.ndarray], rolling: Mapping[str, np.ndarray],
                 history1: np.ndarray) -> Dict[str, Dict[str, np.ndarray]]:
    """F/B/Q per variable from future months (n, m), a full-past flag, the saved parent R and safe history1."""
    gate_known = np.isfinite(history1)
    with np.errstate(invalid="ignore"):
        crisis = history1 >= CRISIS_PHASE
    out = {}
    for v in ORACLE_VARIABLES:
        x = future[v]
        complete = np.isfinite(x).all(axis=1)
        f = np.full(len(x), np.nan)
        f[complete] = x[complete].mean(axis=1)
        r = np.asarray(rolling[v], dtype=float)
        b_ok = complete & np.asarray(past_complete[v], dtype=bool) & np.isfinite(r)
        b = np.full(len(x), np.nan)
        b[b_ok] = (r[b_ok] + f[b_ok]) / 2.0
        q_ok = complete & gate_known
        q = np.full(len(x), np.nan)
        q[q_ok] = np.where(crisis[q_ok], f[q_ok], 0.0)
        out[v] = {"F": f, "B": b, "Q": q}
    return out


def build_oracle_block(grid, keys: pd.DataFrame, horizon: int, rolling: Mapping[str, np.ndarray], history1: np.ndarray,
                       history1_source_ord: np.ndarray) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Raw + B6 oracle columns (declared order) and the per-row availability/source ledger."""
    m = window(horizon)
    work = keys.loc[:, list(osf.KEYS)].reset_index(drop=True)
    target = osf.month_ord(work["year"], work["month"])
    origin = target - horizon
    area = work["area_id"].to_numpy()
    future = {v: np.empty((len(work), m)) for v in ORACLE_VARIABLES}
    past = {v: np.empty((len(work), m)) for v in ORACLE_VARIABLES}
    for k in range(1, m + 1):
        values = calendar_lookup(grid, area, origin + k)
        for v in ORACLE_VARIABLES:
            future[v][:, k - 1] = values[v]
    for j in range(m):  # past window O-m+1 .. O
        values = calendar_lookup(grid, area, origin - j)
        for v in ORACLE_VARIABLES:
            past[v][:, j] = values[v]
    past_complete = {v: np.isfinite(past[v]).all(axis=1) for v in ORACLE_VARIABLES}
    terms = oracle_terms(future, past_complete, rolling, np.asarray(history1, dtype=float))
    cols: Dict[str, np.ndarray] = {}
    for k in range(1, m + 1):
        for v in ORACLE_VARIABLES:
            cols[raw_name(v, k)] = future[v][:, k - 1]
    for v in ORACLE_VARIABLES:
        cols[future_mean_name(v, m)] = terms[v]["F"]
        cols[halfmean_name(v, m)] = terms[v]["B"]
        cols[gated_name(v, m)] = terms[v]["Q"]
    block = pd.DataFrame(cols)
    if list(block.columns) != raw_features(horizon) + b6_features(horizon):
        raise AssertionError("oracle block order differs from the declared schema")
    label = np.vectorize(osf.ord_label, otypes=[object])
    ledger = work.copy()
    ledger["horizon"] = horizon
    ledger["target_ord"] = target
    ledger["origin_ord"] = origin
    ledger["assumed_forecast_available_ord"] = origin
    ledger["future_obs_first_ord"] = origin + 1
    ledger["future_obs_last_ord"] = origin + m
    ledger["past_window_first_ord"] = origin - m + 1
    ledger["past_window_last_ord"] = origin
    ledger["assumed_forecast_available_month"] = label(origin)
    ledger["future_obs_months"] = [f"{osf.ord_label(o + 1)}..{osf.ord_label(o + m)}" for o in origin]
    for v in ORACLE_VARIABLES:
        ledger[f"{v}__future_finite_months"] = np.isfinite(future[v]).sum(axis=1)
        ledger[f"{v}__past_finite_months"] = np.isfinite(past[v]).sum(axis=1)
    src = np.asarray(history1_source_ord, dtype=float)
    ledger["history_1_source_ord"] = src
    ledger["history_1_staleness_months"] = origin - src
    ledger["history_1_value"] = np.asarray(history1, dtype=float)
    return block, ledger


# --------------------------------------------------------------------------- prefit gate


def assert_oracle_inputs(frame: pd.DataFrame, ledger: pd.DataFrame, horizon: int, arm: str) -> Dict[str, int]:
    """CLI gate: ledger timing and exact F/B/Q replay from the dataset's raw oracle columns, saved R and history1.

    Raw values versus the shared source are checked by the builder and the independent verifier.
    """
    m = window(horizon)
    if len(ledger) != len(frame) or not np.array_equal(ledger["area_id"].to_numpy(), frame["area_id"].to_numpy()) \
            or not np.array_equal(ledger["target_ord"].to_numpy(dtype=np.int64), osf.month_ord(frame["year"], frame["month"])):
        raise ValueError("oracle ledger rows do not align with the dataset rows")
    if (ledger["horizon"] != horizon).any():
        raise ValueError("oracle ledger horizon disagrees with the run horizon")
    origin = ledger["target_ord"].to_numpy(dtype=np.int64) - horizon
    expected = {"origin_ord": origin, "assumed_forecast_available_ord": origin, "future_obs_first_ord": origin + 1,
                "future_obs_last_ord": origin + m, "past_window_first_ord": origin - m + 1, "past_window_last_ord": origin}
    for column, values in expected.items():
        if not np.array_equal(ledger[column].to_numpy(dtype=np.int64), values):
            raise ValueError(f"oracle ledger {column} is not the declared weather window for H={horizon}")
    history1 = frame[HISTORY_GATE].to_numpy(dtype=float)
    if not np.array_equal(ledger["history_1_value"].to_numpy(dtype=float), history1, equal_nan=True):
        raise ValueError("oracle ledger history_1 differs from the dataset's safe history")
    src = ledger["history_1_source_ord"].to_numpy(dtype=float)
    has = np.isfinite(src)
    if (np.isfinite(history1) != has).any() or (src[has] > osf.label_cutoff(ledger["target_ord"].to_numpy(dtype=np.int64)[has], horizon)).any():
        raise ValueError("Q gate history_1 is missing its source or is after min(O, T-1)")
    future = {v: frame[[raw_name(v, k) for k in range(1, m + 1)]].to_numpy(dtype=float) for v in ORACLE_VARIABLES}
    for v in ORACLE_VARIABLES:
        if not np.array_equal(np.isfinite(future[v]).sum(axis=1), ledger[f"{v}__future_finite_months"].to_numpy()):
            raise ValueError(f"{v}: raw oracle columns disagree with the ledger finite-month counts")
    if arm == B6_ARM:
        past_complete = {v: ledger[f"{v}__past_finite_months"].to_numpy() == m for v in ORACLE_VARIABLES}
        rolling = {v: frame[parent_rolling_column(v, horizon)].to_numpy(dtype=float) for v in ORACLE_VARIABLES}
        terms = oracle_terms(future, past_complete, rolling, history1)
        for v in ORACLE_VARIABLES:
            for key, name in (("F", future_mean_name(v, m)), ("B", halfmean_name(v, m)), ("Q", gated_name(v, m))):
                if not np.array_equal(frame[name].to_numpy(dtype=float), terms[v][key], equal_nan=True):
                    raise ValueError(f"{name} is not the declared function of its dependencies")
    return {"rows": len(frame)}
