"""Origin-safe global protocol: safe IPC history, national IDP context, frozen cohorts and annual origin-safe fits.

Contract (task ``10-06-global-origin-safe-climate-idp``; observation month is the availability proxy):

- Target month ``T``, horizon ``H`` in (0, 3, 6, 12), month-end origin ``O = T - H`` (dense ordinals
  ``year * 12 + month - 1``).
- Historical IPC labels, in features and in fitting, must satisfy ``U <= min(O, T - 1)``; H=0 excludes the
  target month for every area.
- Monthly dynamic observations (here: national IDP reports) must satisfy ``U <= O``.
- Sample weights ``0.5 ** ((O - U) / half_life)``; age 0 is allowed for H > 0.
- Cumulative targets come from shares normalized to sum to one; classification truth is the reported phase.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

HORIZONS = (0, 3, 6, 12)
TARGET_YEARS = (2022, 2023, 2024, 2025)
VALID_PHASES = (1, 2, 3, 4, 5)
KEYS = ("area_id", "year", "month")
SHARE_COLUMNS = tuple(f"phase{k}_percent" for k in VALID_PHASES)
CUMULATIVE_TARGETS = ("phase2_worse", "phase3_worse", "phase4_worse", "phase5_worse")
PRED_COLUMNS = ("phase2_pred", "phase3_pred", "phase4_pred", "phase5_pred")
HISTORY_VALUES = tuple(f"overall_phase_history_{k}" for k in (1, 2, 3))
HISTORY_CHANGES = ("overall_phase_history_change_1_2", "overall_phase_history_change_1_3")
HISTORY_FEATURES = HISTORY_VALUES + HISTORY_CHANGES
IDP_FEATURES = ("idp_admin0_latest_stock", "idp_admin0_latest_age_months")
ARMS: Dict[str, Tuple[str, ...]] = {
    "climate_no_history": (),
    "climate_safe_history": HISTORY_FEATURES,
    "climate_safe_history_idp": HISTORY_FEATURES + IDP_FEATURES,
}
# Columns that must never reach an origin-safe fit: legacy IPC history (unverified source rows / post-origin
# lag1), target-side population, labels, shares and cumulative targets.
FORBIDDEN_FEATURE_PATTERNS = (
    r"^overall_phase($|_lag|_prev_observed|_target_relative|_test|_pred)",
    r"^estimated_population$",
    r"^phase[1-5]_(percent|worse|pred|test)$",
    r"^(area_id|year|month|date|test_year|origin_ord|target_ord)$",
    r"(^|_)source_(ord|month|area)",
)
REQUIRED_BATCH_ARTIFACTS = frozenset({"predictions.csv", "fit_keys.csv.gz", *(f"model_{t}.ubj" for t in CUMULATIVE_TARGETS)})
DEFAULT_HALF_LIFE_MONTHS = 24.0
DEFAULT_PHASE_THRESHOLD = 0.2


def month_ord(year, month) -> np.ndarray:
    return np.asarray(year, dtype=np.int64) * 12 + np.asarray(month, dtype=np.int64) - 1


def ord_label(value: float) -> Optional[str]:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    value = int(value)
    return f"{value // 12:04d}-{value % 12 + 1:02d}"


def validate_horizon(horizon: int) -> int:
    if int(horizon) not in HORIZONS:
        raise ValueError(f"horizon must be one of {HORIZONS}; received {horizon}")
    return int(horizon)


def label_cutoff(target_ord, horizon: int):
    """Latest label month usable for a target month: ``min(T - H, T - 1)``."""
    horizon = validate_horizon(horizon)
    return np.asarray(target_ord, dtype=np.int64) - max(horizon, 1)


def keys_sha256(frame: pd.DataFrame, columns: Sequence[str] = KEYS) -> str:
    """Order-sensitive hash of key tuples (sort first for a set hash)."""
    text = "\n".join("|".join(str(v) for v in row) for row in frame.loc[:, list(columns)].itertuples(index=False, name=None))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def list_sha256(values: Iterable[str]) -> str:
    return hashlib.sha256("\n".join(values).encode("utf-8")).hexdigest()


def file_sha256(path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 22), b""):
            digest.update(chunk)
    return digest.hexdigest()


# --------------------------------------------------------------------------- labels and targets


def valid_phase_observations(labels: pd.DataFrame) -> pd.DataFrame:
    """Reported phase 1-5 observations (area_id, ord, overall_phase); duplicates fail."""
    for column in ("area_id", "year", "month", "overall_phase"):
        if column not in labels.columns:
            raise ValueError(f"labels missing {column}")
    if labels.duplicated(["area_id", "year", "month"]).any():
        raise ValueError("labels have duplicate area_id/year/month keys")
    phase = pd.to_numeric(labels["overall_phase"], errors="coerce")
    keep = phase.isin(VALID_PHASES)
    out = pd.DataFrame({
        "area_id": labels.loc[keep, "area_id"].to_numpy(),
        "ord": month_ord(labels.loc[keep, "year"], labels.loc[keep, "month"]),
        "overall_phase": phase[keep].astype(float).to_numpy(),
    })
    return out.sort_values(["area_id", "ord"], kind="mergesort").reset_index(drop=True)


def share_validity(frame: pd.DataFrame) -> np.ndarray:
    """Reported phase 1-5 with five finite non-negative shares and a positive total."""
    phase = pd.to_numeric(frame["overall_phase"], errors="coerce")
    shares = frame.loc[:, list(SHARE_COLUMNS)].apply(pd.to_numeric, errors="coerce").to_numpy(dtype=float)
    finite = np.isfinite(shares).all(axis=1)
    with np.errstate(invalid="ignore"):
        nonneg = (shares >= 0).all(axis=1)
        total = np.where(finite, shares.sum(axis=1), np.nan)
    return (phase.isin(VALID_PHASES).to_numpy() & finite & nonneg & (total > 0))


def normalized_cumulative_targets(frame: pd.DataFrame) -> pd.DataFrame:
    """phaseK_worse from shares divided by their total; NaN on rows without valid shares. Raw shares untouched."""
    valid = share_validity(frame)
    shares = frame.loc[:, list(SHARE_COLUMNS)].apply(pd.to_numeric, errors="coerce").to_numpy(dtype=float)
    norm = np.full_like(shares, np.nan)
    norm[valid] = shares[valid] / shares[valid].sum(axis=1, keepdims=True)
    out = pd.DataFrame(index=frame.index)
    for k, column in zip((2, 3, 4, 5), CUMULATIVE_TARGETS):
        out[column] = norm[:, k - 1 :].sum(axis=1)
        out.loc[~valid, column] = np.nan
    out["share_total_raw"] = np.where(np.isfinite(shares).all(axis=1), shares.sum(axis=1), np.nan)
    out["share_valid"] = valid
    return out


# --------------------------------------------------------------------------- safe IPC history


def build_safe_history(observations: pd.DataFrame, rows: pd.DataFrame, horizon: int) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Latest three reported phases of the same area with month ``<= min(O, T-1)``.

    Extracted from ``assemble_latest_IPCCH/experiments/nga_aligned_ipc_history_20260918_v1/build_and_run.py``
    ``build_history`` (per-area searchsorted over observation months), generalized to H=12 and to a label
    table that is separate from the feature rows. ``observations``: area_id, ord, overall_phase (from
    :func:`valid_phase_observations`). ``rows``: area_id, year, month. Returns the five history predictors
    (missing history stays NaN) and a ledger of the actual source keys.
    """
    horizon = validate_horizon(horizon)
    if observations.duplicated(["area_id", "ord"]).any():
        raise ValueError("history observations have duplicate area/month keys")
    if not observations["overall_phase"].isin(VALID_PHASES).all():
        raise ValueError("history observations must be reported phases 1-5")
    work = rows.loc[:, ["area_id", "year", "month"]].reset_index(drop=True)
    target = month_ord(work["year"], work["month"])
    cutoff = label_cutoff(target, horizon)
    values = np.full((len(work), 3), np.nan)
    sources = np.full((len(work), 3), np.nan)
    obs_groups = {area: idx for area, idx in observations.groupby("area_id", sort=False).indices.items()}
    obs_ord = observations["ord"].to_numpy(dtype=np.int64)
    obs_phase = observations["overall_phase"].to_numpy(dtype=float)
    for area, indices in work.groupby("area_id", sort=False).indices.items():
        if area not in obs_groups:
            continue
        available = obs_groups[area]
        available = available[np.argsort(obs_ord[available], kind="mergesort")]
        times = obs_ord[available]
        positions = np.searchsorted(times, cutoff[indices], side="right")
        for k in range(3):
            previous = positions - 1 - k
            ok = previous >= 0
            source = available[previous[ok]]
            values[indices[ok], k] = obs_phase[source]
            sources[indices[ok], k] = obs_ord[source]
    block = pd.DataFrame(values, columns=list(HISTORY_VALUES))
    block[HISTORY_CHANGES[0]] = block[HISTORY_VALUES[0]] - block[HISTORY_VALUES[1]]
    block[HISTORY_CHANGES[1]] = block[HISTORY_VALUES[0]] - block[HISTORY_VALUES[2]]
    ledger = work.copy()
    ledger["horizon"] = horizon
    ledger["target_ord"] = target
    ledger["origin_ord"] = target - horizon
    ledger["label_cutoff_ord"] = cutoff
    for k in range(3):
        ledger[f"history_{k + 1}_source_area_id"] = np.where(np.isnan(sources[:, k]), None, work["area_id"].to_numpy())
        ledger[f"history_{k + 1}_source_ord"] = sources[:, k]
        ledger[f"history_{k + 1}_value"] = values[:, k]
    return block, ledger


def reference_history_check(observations: pd.DataFrame, ledger: pd.DataFrame, block: pd.DataFrame) -> Dict[str, int]:
    """Independent pure-Python latest-three replay over every ledger row; raises on any disagreement."""
    records: Dict[object, List[Tuple[int, float]]] = {}
    for area, ord_, phase in observations.loc[:, ["area_id", "ord", "overall_phase"]].itertuples(index=False, name=None):
        records.setdefault(area, []).append((int(ord_), float(phase)))
    for area in records:
        records[area].sort()
    checked = 0
    present = 0
    for i, row in enumerate(ledger.itertuples(index=False)):
        cutoff = int(row.label_cutoff_ord)
        if cutoff != int(row.target_ord) - max(int(row.horizon), 1):
            raise AssertionError(f"row {i}: cutoff is not min(O, T-1)")
        allowed = [r for r in records.get(row.area_id, []) if r[0] <= cutoff]
        expected = list(reversed(allowed[-3:]))
        for k in range(3):
            src = getattr(row, f"history_{k + 1}_source_ord")
            val = block.iat[i, k]
            if k < len(expected):
                if src != expected[k][0] or val != expected[k][1]:
                    raise AssertionError(f"row {i} history_{k + 1}: got ({src}, {val}), expected {expected[k]}")
                if getattr(row, f"history_{k + 1}_source_area_id") != row.area_id:
                    raise AssertionError(f"row {i} history_{k + 1}: source area differs from row area")
                if not src <= cutoff < row.target_ord:
                    raise AssertionError(f"row {i} history_{k + 1}: source month after cutoff")
                present += 1
            elif not (np.isnan(src) and np.isnan(val)):
                raise AssertionError(f"row {i} history_{k + 1}: expected missing history")
        h1, h2, h3 = block.iat[i, 0], block.iat[i, 1], block.iat[i, 2]
        for got, want in ((block.iat[i, 3], h1 - h2), (block.iat[i, 4], h1 - h3)):
            if not ((np.isnan(got) and np.isnan(want)) or got == want):
                raise AssertionError(f"row {i}: history change mismatch")
        checked += 1
    return {"rows_checked": checked, "history_values_present": present}


# --------------------------------------------------------------------------- national IDP context


def idp_observations(idp_monthly: pd.DataFrame) -> pd.DataFrame:
    """Observed non-null DTM admin0 stocks (iso3, report_ord, stock); validates one report per country-month."""
    required = {"admin0Pcode", "year", "month", "idp_ind", "observed", "reportingDate"}
    missing = sorted(required - set(idp_monthly.columns))
    if missing:
        raise ValueError(f"IDP admin0 table missing {missing}")
    if idp_monthly.duplicated(["admin0Pcode", "year", "month"]).any():
        raise ValueError("IDP admin0 table has duplicate country-month rows")
    obs = idp_monthly[idp_monthly["idp_ind"].notna()].copy()
    if (obs["observed"] != 1).any():
        raise ValueError("non-null IDP stock on a row not flagged observed")
    report = pd.to_datetime(obs["reportingDate"], errors="raise")
    if ((report.dt.year != obs["year"]) | (report.dt.month != obs["month"])).any():
        raise ValueError("IDP reportingDate month disagrees with the row month")
    if (obs["idp_ind"] < 0).any():
        raise ValueError("negative IDP stock")
    out = pd.DataFrame({
        "iso3": obs["admin0Pcode"].astype(str).str.strip().str.upper().to_numpy(),
        "report_ord": month_ord(obs["year"], obs["month"]),
        "stock": obs["idp_ind"].astype(float).to_numpy(),
    })
    return out.sort_values(["iso3", "report_ord"], kind="mergesort").reset_index(drop=True)


def build_idp_features(observations: pd.DataFrame, rows: pd.DataFrame, iso3: Sequence[Optional[str]], horizon: int) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Latest observed national stock with report month ``<= O`` and its age ``O - report``; missing stays NaN."""
    horizon = validate_horizon(horizon)
    work = rows.loc[:, ["area_id", "year", "month"]].reset_index(drop=True)
    origin = month_ord(work["year"], work["month"]) - horizon
    codes = pd.Series(list(iso3), dtype="object").where(pd.notna(pd.Series(list(iso3), dtype="object")), None)
    stock = np.full(len(work), np.nan)
    report = np.full(len(work), np.nan)
    groups = observations.groupby("iso3", sort=False).indices
    obs_ord = observations["report_ord"].to_numpy(dtype=np.int64)
    obs_stock = observations["stock"].to_numpy(dtype=float)
    for code, indices in pd.Series(np.arange(len(work))).groupby(codes.to_numpy(), dropna=True).indices.items():
        if code not in groups:
            continue
        available = groups[code]
        times = obs_ord[available]
        positions = np.searchsorted(times, origin[indices], side="right") - 1
        ok = positions >= 0
        stock[indices[ok]] = obs_stock[available[positions[ok]]]
        report[indices[ok]] = times[positions[ok]]
    block = pd.DataFrame({IDP_FEATURES[0]: stock, IDP_FEATURES[1]: origin - report})
    ledger = work.copy()
    ledger["iso3"] = codes.to_numpy()
    ledger["horizon"] = horizon
    ledger["origin_ord"] = origin
    ledger["idp_report_ord"] = report
    ledger["idp_stock"] = stock
    return block, ledger


def reference_idp_check(observations: pd.DataFrame, ledger: pd.DataFrame, block: pd.DataFrame) -> Dict[str, int]:
    """Independent replay of the national IDP lookup on unique (iso3, origin) pairs."""
    by_code: Dict[str, List[Tuple[int, float]]] = {}
    for code, ord_, value in observations.loc[:, ["iso3", "report_ord", "stock"]].itertuples(index=False, name=None):
        by_code.setdefault(code, []).append((int(ord_), float(value)))
    cache: Dict[Tuple[object, int], Tuple[float, float]] = {}
    present = 0
    for i, row in enumerate(ledger.itertuples(index=False)):
        key = (row.iso3, int(row.origin_ord))
        if key not in cache:
            allowed = [r for r in by_code.get(row.iso3, []) if r[0] <= key[1]] if row.iso3 is not None else []
            cache[key] = (float(allowed[-1][0]), allowed[-1][1]) if allowed else (np.nan, np.nan)
        want_report, want_stock = cache[key]
        got_stock, got_age = block.iat[i, 0], block.iat[i, 1]
        if np.isnan(want_report):
            if not (np.isnan(got_stock) and np.isnan(got_age) and np.isnan(row.idp_report_ord)):
                raise AssertionError(f"row {i}: IDP should be missing")
            continue
        if row.idp_report_ord != want_report or got_stock != want_stock or got_age != key[1] - want_report or got_age < 0:
            raise AssertionError(f"row {i}: IDP mismatch")
        present += 1
    return {"rows_checked": len(ledger), "idp_present": present}


# --------------------------------------------------------------------------- fitting protocol


def fit_mask(target_ords, share_valid, outer_target_ord: int, horizon: int) -> np.ndarray:
    """Training rows for one outer target month: valid shares and label month ``<= min(O, T-1)``."""
    cutoff = int(label_cutoff(np.asarray([outer_target_ord]), horizon)[0])
    return np.asarray(share_valid, dtype=bool) & (np.asarray(target_ords, dtype=np.int64) <= cutoff)


def origin_weights(target_ords, origin_ord: int, half_life_months: float = DEFAULT_HALF_LIFE_MONTHS) -> np.ndarray:
    age = int(origin_ord) - np.asarray(target_ords, dtype=np.int64)
    if (age < 0).any():
        raise ValueError("training label after the fit origin")
    if not np.isfinite(half_life_months) or half_life_months <= 0:
        raise ValueError("half-life must be positive and finite")
    return np.power(0.5, age.astype(float) / float(half_life_months))


def classify_cumulative(predictions: pd.DataFrame, threshold: float = DEFAULT_PHASE_THRESHOLD) -> np.ndarray:
    """Highest phase whose unrounded cumulative score is ``>= threshold``; phase 1 otherwise. No row is dropped."""
    out = np.ones(len(predictions), dtype=int)
    assigned = np.zeros(len(predictions), dtype=bool)
    for phase in (5, 4, 3, 2):
        hit = ~assigned & (predictions[f"phase{phase}_pred"].to_numpy(dtype=float) >= threshold)
        out[hit] = phase
        assigned |= hit
    return out


def forbidden_features(columns: Iterable[str]) -> List[str]:
    return [c for c in columns if any(re.search(p, c) for p in FORBIDDEN_FEATURE_PATTERNS)]


def assert_history_ledger(frame: pd.DataFrame, ledger: pd.DataFrame, horizon: int) -> None:
    """Prefit gate: history predictors must come from a ledger of real source months within the cutoff."""
    if len(ledger) != len(frame) or not np.array_equal(ledger["area_id"].to_numpy(), frame["area_id"].to_numpy()) \
            or not np.array_equal(month_ord(ledger["year"], ledger["month"]), month_ord(frame["year"], frame["month"])):
        raise ValueError("history ledger rows do not align with the dataset rows")
    if (ledger["horizon"] != horizon).any():
        raise ValueError("history ledger horizon disagrees with the run horizon")
    cutoff = label_cutoff(month_ord(frame["year"], frame["month"]), horizon)
    if not np.array_equal(ledger["label_cutoff_ord"].to_numpy(dtype=np.int64), cutoff):
        raise ValueError("history ledger cutoff is not min(O, T-1)")
    for k in range(3):
        src = ledger[f"history_{k + 1}_source_ord"].to_numpy(dtype=float)
        value = frame[HISTORY_VALUES[k]].to_numpy(dtype=float)
        if (np.isnan(src) != np.isnan(value)).any():
            raise ValueError(f"history_{k + 1}: value without source month (or source without value)")
        if (src[~np.isnan(src)] > cutoff[~np.isnan(src)]).any():
            raise ValueError(f"history_{k + 1}: source month after min(O, T-1)")
        if not np.array_equal(ledger[f"history_{k + 1}_value"].to_numpy(dtype=float), value, equal_nan=True):
            raise ValueError(f"history_{k + 1}: dataset value differs from ledger")
    h1, h2, h3 = (frame[c].to_numpy(dtype=float) for c in HISTORY_VALUES)
    for column, expected in zip(HISTORY_CHANGES, (h1 - h2, h1 - h3)):
        if not np.array_equal(frame[column].to_numpy(dtype=float), expected, equal_nan=True):
            raise ValueError(f"{column} is not the difference of the ledger-validated history values")


def assert_idp_ledger(frame: pd.DataFrame, ledger: pd.DataFrame, horizon: int) -> None:
    if len(ledger) != len(frame) or not np.array_equal(ledger["area_id"].to_numpy(), frame["area_id"].to_numpy()):
        raise ValueError("IDP ledger rows do not align with the dataset rows")
    origin = month_ord(frame["year"], frame["month"]) - horizon
    report = ledger["idp_report_ord"].to_numpy(dtype=float)
    stock = frame[IDP_FEATURES[0]].to_numpy(dtype=float)
    age = frame[IDP_FEATURES[1]].to_numpy(dtype=float)
    if (np.isnan(report) != np.isnan(stock)).any() or (np.isnan(report) != np.isnan(age)).any():
        raise ValueError("IDP value without report month")
    has = ~np.isnan(report)
    if (report[has] > origin[has]).any() or not np.array_equal(age[has], origin[has] - report[has]):
        raise ValueError("IDP report after origin or inconsistent age")
    if not np.array_equal(ledger["idp_stock"].to_numpy(dtype=float), stock, equal_nan=True):
        raise ValueError("IDP stock differs from ledger")


# --------------------------------------------------------------------------- metrics


def origin_metrics(predictions: pd.DataFrame, scope: str = "overall", test_year=None) -> Dict[str, object]:
    """Exact-phase and phase-3+ accuracy, phase-3+ precision/recall/F2, phase-3+ R2/MAE and ordinal MAE.

    ``exact_phase_accuracy`` is the project's canonical five-class accuracy; ``phase3plus_accuracy`` compares
    phase >= 3 against phase <= 2. Undefined values stay None.
    """
    from ipcch.forecasting_weight_decay import compute_metrics, metric_value

    result = compute_metrics(predictions, test_year if test_year is not None else -1, scope)
    result["exact_phase_accuracy"] = result.pop("accuracy")
    if len(predictions) == 0:
        for metric in ("phase3plus_accuracy", "mae_phase3plus", "ordinal_mae"):
            result[metric] = metric_value(None, "unavailable", "no eligible samples")
        return result
    observed3 = predictions["overall_phase"].to_numpy(dtype=float) >= 3
    predicted3 = predictions["overall_phase_pred"].to_numpy(dtype=float) >= 3
    result["phase3plus_accuracy"] = metric_value(float(np.mean(observed3 == predicted3)))
    truth = predictions["phase3_worse"].to_numpy(dtype=float)
    pred = predictions["phase3_pred"].to_numpy(dtype=float)
    result["mae_phase3plus"] = metric_value(float(np.mean(np.abs(truth - pred))))
    observed = predictions["overall_phase"].to_numpy(dtype=float)
    predicted = predictions["overall_phase_pred"].to_numpy(dtype=float)
    result["ordinal_mae"] = metric_value(float(np.mean(np.abs(observed - predicted))))
    return result


ORIGIN_METRICS = ("exact_phase_accuracy", "phase3plus_accuracy", "precision_phase3plus", "sensitivity_phase3plus",
                  "f2_phase3plus", "r2_phase3plus", "mae_phase3plus", "ordinal_mae")


def flatten_origin_metrics(result: Mapping[str, object]) -> Dict[str, object]:
    row = {"scope": result["scope"], "test_year": result["test_year"], "n_samples": result["n_samples"]}
    for metric in ORIGIN_METRICS:
        value = result[metric]
        row[metric] = value["value"]
        row[f"{metric}_status"] = value["status"]
        row[f"{metric}_reason"] = value["reason"]
    return row


def dump_json(path, payload: Mapping[str, object]) -> None:
    def default(value):
        if isinstance(value, (np.integer, np.floating)):
            return value.item()
        if isinstance(value, np.ndarray):
            return value.tolist()
        return str(value)

    text = json.dumps(payload, indent=2, default=default)
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        handle.write(text + "\n")
    import os

    os.replace(tmp, path)
