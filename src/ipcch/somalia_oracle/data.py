"""Input ledgers and as-of feature blocks for the Somalia oracle experiment.

Every block here is keyed by ``(area_id, target_ord)`` plus the row's own origin
``o = T - H``. Months are dense ordinals ``year * 12 + (month - 1)`` so that a
difference of ordinals is a number of calendar months.
"""
from __future__ import annotations

import hashlib
from decimal import Decimal
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

import numpy as np
import pandas as pd

from ipcch.forecasting_weight_decay import extract_country_area_ids, select_numeric_feature_columns
from ipcch.somalia_oracle import (
    BLOCKED_BASE_FEATURES,
    CUMULATIVE_COLUMNS,
    NORMALIZED_COLUMNS,
    ORACLE_WEATHER_VARIABLES,
    PERCENT_COLUMNS,
    PROVENANCE_CHECK_FROM_YEAR,
    V2_FEATURES,
    oracle_offsets,
)

KEY = ["area_id", "target_ord"]


class DataContractError(RuntimeError):
    """An input or as-of invariant does not hold."""


def month_ord(year, month):
    return np.asarray(year, dtype=np.int64) * 12 + (np.asarray(month, dtype=np.int64) - 1)


def ord_label(ordinal) -> str:
    ordinal = int(ordinal)
    return f"{ordinal // 12:04d}-{ordinal % 12 + 1:02d}"


def ord_labels(ordinals: Iterable[int]) -> List[str]:
    return [ord_label(o) for o in ordinals]


def ord_first_day(ordinal) -> pd.Timestamp:
    ordinal = int(ordinal)
    return pd.Timestamp(year=ordinal // 12, month=ordinal % 12 + 1, day=1)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 22), b""):
            digest.update(block)
    return digest.hexdigest()


def frame_digest(frame: pd.DataFrame, columns: Sequence[str]) -> str:
    text = frame.loc[:, list(columns)].to_csv(index=False, lineterminator="\n")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def somalia_area_ids(lookup: pd.DataFrame) -> Set[int]:
    ids = extract_country_area_ids(lookup, "SOM", "Somalia")
    normalized = {int(v) for v in ids}
    if len(normalized) != len(ids):
        raise DataContractError("Somalia area ids are not unique after integer normalization")
    return normalized


def read_area_rows(path: Path, area_ids: Set[int], id_column: str, usecols: Optional[Sequence[str]] = None) -> pd.DataFrame:
    """Chunked read keeping only rows whose ``id_column`` is a Somalia area."""
    parts = []
    for chunk in pd.read_csv(path, usecols=usecols, chunksize=100_000, low_memory=False):
        if id_column not in chunk.columns:
            raise DataContractError(f"{path} is missing {id_column}")
        ids = pd.to_numeric(chunk[id_column], errors="coerce")
        keep = ids.isin(area_ids)
        if keep.any():
            parts.append(chunk.loc[keep])
    if not parts:
        raise DataContractError(f"No Somalia rows found in {path}")
    frame = pd.concat(parts, ignore_index=True)
    frame[id_column] = pd.to_numeric(frame[id_column]).astype(np.int64)
    return frame


# --------------------------------------------------------------------------
# Label ledger (grill G4 normalization)
# --------------------------------------------------------------------------


def _exact_crisis_state(p3: float, p4: float, p5: float, total: float) -> int:
    """Reference history convention ``5 * (P3 + P4 + P5) > S`` without float rounding."""
    exact = [Decimal(repr(float(v))) for v in (p3, p4, p5)]
    return int(Decimal(5) * sum(exact) > Decimal(repr(float(total))))


def build_label_ledger(model_ready: Mapping[str, pd.DataFrame], raw_labeled_keys: Set[Tuple[int, int]]) -> pd.DataFrame:
    """Union of the labeled model-ready Somalia rows with explicit validity flags.

    Raw components, their sum, normalized shares and cumulative targets are kept
    side by side. Reported ``overall_phase`` is never rewritten.
    """
    value_columns = ["overall_phase", *PERCENT_COLUMNS, "estimated_population"]
    frames = []
    for name, frame in model_ready.items():
        part = frame.loc[frame["overall_phase"].notna(), ["area_id", "year", "month", *value_columns]].copy()
        part["source_file"] = name
        frames.append(part)
    stacked = pd.concat(frames, ignore_index=True)
    stacked["target_ord"] = month_ord(stacked["year"], stacked["month"])
    conflicts = (
        stacked.groupby(KEY)[value_columns]
        .nunique(dropna=False)
        .max(axis=1)
    )
    if (conflicts > 1).any():
        examples = conflicts[conflicts > 1].index[:5].tolist()
        raise DataContractError(f"Model-ready files disagree on label values for keys {examples}")
    sources = stacked.groupby(KEY)["source_file"].agg(lambda s: "|".join(sorted(set(s))))
    ledger = stacked.drop_duplicates(KEY).drop(columns="source_file").set_index(KEY)
    ledger["source_files"] = sources
    ledger = ledger.reset_index().sort_values(KEY, kind="mergesort").reset_index(drop=True)

    raw = ledger.loc[:, list(PERCENT_COLUMNS)].apply(pd.to_numeric, errors="coerce")
    values = raw.to_numpy(dtype=np.float64)
    total = values.sum(axis=1)
    ledger["raw_sum"] = total

    reason = np.full(len(ledger), "", dtype=object)
    missing = np.isnan(values).any(axis=1)
    nonfinite = ~missing & ~np.isfinite(values).all(axis=1)
    negative = ~missing & ~nonfinite & (values < 0).any(axis=1)
    nonpositive = ~missing & ~nonfinite & ~negative & ~(np.isfinite(total) & (total > 0))
    reason[missing] = "missing_component"
    reason[nonfinite] = "nonfinite_component"
    reason[negative] = "negative_component"
    reason[nonpositive] = "nonpositive_sum"

    keys = list(zip(ledger["area_id"].astype(int), ledger["target_ord"].astype(int)))
    unreconciled = np.array(
        [year >= PROVENANCE_CHECK_FROM_YEAR and key not in raw_labeled_keys for year, key in zip(ledger["year"], keys)]
    )
    ledger["provenance_ok"] = ~unreconciled
    target_reason = np.where(unreconciled & (reason == ""), "provenance_unreconciled", reason)
    ledger["target_invalid_reason"] = target_reason
    ledger["valid_target"] = target_reason == ""

    with np.errstate(invalid="ignore", divide="ignore"):
        normalized = values / total[:, None]
    normalized[~ledger["valid_target"].to_numpy()] = np.nan
    for index, column in enumerate(NORMALIZED_COLUMNS):
        ledger[column] = normalized[:, index]
    ledger["q2"] = normalized[:, 1:].sum(axis=1)
    ledger["q3"] = normalized[:, 2:].sum(axis=1)
    ledger["q4"] = normalized[:, 3:].sum(axis=1)
    ledger["q5"] = normalized[:, 4]
    for column in CUMULATIVE_COLUMNS:
        ledger.loc[~ledger["valid_target"], column] = np.nan
    ledger["normalization_changed"] = ledger["valid_target"] & (np.abs(total - 1.0) > 1e-12)

    phase = pd.to_numeric(ledger["overall_phase"], errors="coerce")
    ledger["valid_phase"] = phase.isin([1, 2, 3, 4, 5]).to_numpy() & ~unreconciled
    ledger["valid_score"] = ledger["valid_target"] & ledger["valid_phase"]
    ledger["actual_crisis"] = np.where(ledger["valid_phase"], (phase >= 3).astype(float), np.nan)
    derived = share_phase(ledger[list(CUMULATIVE_COLUMNS)].to_numpy(dtype=np.float64))
    ledger["share_derived_phase"] = np.where(ledger["valid_target"], derived, np.nan)

    # Reference history QC: P1..P4 observed, missing P5 -> 0 (flagged), shares in
    # [0, 1], positive population, positive sum. The reference's [.90, 1.10] sum gate
    # is superseded by grill G4 proportional normalization.
    p1_4_missing = np.isnan(values[:, :4]).any(axis=1)
    p5_filled = ~p1_4_missing & np.isnan(values[:, 4])
    filled = values.copy()
    filled[p5_filled, 4] = 0.0
    filled_total = filled.sum(axis=1)
    population = pd.to_numeric(ledger["estimated_population"], errors="coerce").to_numpy(dtype=np.float64)
    history_reason = np.full(len(ledger), "", dtype=object)
    history_reason[unreconciled] = "provenance_unreconciled"
    history_reason[(history_reason == "") & p1_4_missing] = "missing_phase_1_to_4"
    bounds = np.isfinite(filled).all(axis=1) & (filled >= 0).all(axis=1) & (filled <= 1).all(axis=1)
    history_reason[(history_reason == "") & ~bounds] = "phase_share_out_of_bounds"
    history_reason[(history_reason == "") & ~(np.isfinite(population) & (population > 0))] = "population_not_positive"
    history_reason[(history_reason == "") & ~(filled_total > 0)] = "nonpositive_sum"
    ledger["history_invalid_reason"] = history_reason
    ledger["valid_history"] = history_reason == ""
    ledger["history_p5_filled"] = p5_filled & ledger["valid_history"].to_numpy()
    with np.errstate(invalid="ignore", divide="ignore"):
        history_normalized = filled / filled_total[:, None]
    for index in range(5):
        ledger[f"h_p{index + 1}"] = np.where(ledger["valid_history"], history_normalized[:, index], np.nan)
    states = np.full(len(ledger), np.nan)
    for row in np.flatnonzero(ledger["valid_history"].to_numpy()):
        states[row] = _exact_crisis_state(filled[row, 2], filled[row, 3], filled[row, 4], filled_total[row])
    ledger["history_crisis_state"] = states
    return ledger


def share_phase(cumulative: np.ndarray, threshold: float = 0.2) -> np.ndarray:
    """Descending phase5->phase2 first crossing (>= threshold); default phase 1."""
    cumulative = np.asarray(cumulative, dtype=np.float64)
    phase = np.ones(cumulative.shape[0], dtype=np.int64)
    assigned = np.zeros(cumulative.shape[0], dtype=bool)
    for position, value in ((3, 5), (2, 4), (1, 3), (0, 2)):
        hit = ~assigned & (cumulative[:, position] >= threshold)
        phase[hit] = value
        assigned |= hit
    return phase


# --------------------------------------------------------------------------
# Realized weather ledger and oracle block (R4)
# --------------------------------------------------------------------------


def build_weather_ledger(raw_rows: pd.DataFrame) -> pd.DataFrame:
    """Monthly realized rain/temperature with a verification status per area-month.

    A month is verified only when both variables are finite and do not both repeat
    the previous month exactly (the forward-fill signature observed from 2025-02).
    """
    weather = raw_rows.loc[:, ["admin_code", "year", "month", *ORACLE_WEATHER_VARIABLES]].copy()
    weather = weather.rename(columns={"admin_code": "area_id"})
    weather["month_ord"] = month_ord(weather["year"], weather["month"])
    if weather.duplicated(["area_id", "month_ord"]).any():
        raise DataContractError("Raw weather has duplicate area/month keys")
    weather = weather.sort_values(["area_id", "month_ord"], kind="mergesort").reset_index(drop=True)
    previous = weather.groupby("area_id")[["month_ord", *ORACLE_WEATHER_VARIABLES]].shift(1)
    finite = np.isfinite(weather[list(ORACLE_WEATHER_VARIABLES)].to_numpy(dtype=np.float64)).all(axis=1)
    adjacent = (previous["month_ord"] == weather["month_ord"] - 1).to_numpy()
    repeats = adjacent.copy()
    for column in ORACLE_WEATHER_VARIABLES:
        repeats &= (weather[column] == previous[column]).to_numpy()
    status = np.where(~finite, "nonfinite", np.where(repeats, "repeats_previous_month", "verified"))
    weather["weather_status"] = status
    weather["weather_verified"] = status == "verified"
    return weather.drop(columns=["year", "month"])


def oracle_block(weather: pd.DataFrame, area_id: np.ndarray, origin_ord: np.ndarray, horizon: int) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Realized weather at o+1..o+min(H,6); unverified months are NaN.

    Returns (features, per-row-month ledger). Never forward-fills or substitutes.
    """
    offsets = oracle_offsets(horizon)
    features = pd.DataFrame(index=pd.RangeIndex(len(area_id)))
    indexed = weather.set_index(["area_id", "month_ord"])
    ledger_parts = []
    all_verified = np.ones(len(area_id), dtype=bool)
    for k in offsets:
        months = np.asarray(origin_ord, dtype=np.int64) + k
        lookup = pd.MultiIndex.from_arrays([np.asarray(area_id, dtype=np.int64), months])
        found = indexed.reindex(lookup)
        verified = found["weather_verified"].fillna(False).to_numpy(dtype=bool)
        status = found["weather_status"].fillna("missing").to_numpy(dtype=object)
        for variable in ORACLE_WEATHER_VARIABLES:
            features[f"oracle_{variable}_o{k}"] = np.where(verified, found[variable].to_numpy(dtype=np.float64), np.nan)
        all_verified &= verified
        ledger_parts.append(
            pd.DataFrame({"row": np.arange(len(area_id)), "offset": k, "weather_month_ord": months, "weather_status": status})
        )
    ledger = pd.concat(ledger_parts, ignore_index=True) if ledger_parts else pd.DataFrame(columns=["row", "offset", "weather_month_ord", "weather_status"])
    features["oracle_all_verified"] = all_verified
    return features, ledger


# --------------------------------------------------------------------------
# V2 latest-ended-season join (R3)
# --------------------------------------------------------------------------


def prepare_v2_seasons(v2_rows: pd.DataFrame) -> pd.DataFrame:
    seasons = v2_rows.rename(columns={"admin_code": "area_id"}).copy()
    seasons["season_end_exclusive"] = pd.to_datetime(seasons["gs_end_date_exclusive"], errors="raise")
    seasons["season_start"] = pd.to_datetime(seasons["gs_start_date"], errors="raise")
    if seasons.duplicated(["area_id", "season_year", "season"]).any():
        raise DataContractError("V2 has duplicate area/season_year/season keys")
    if seasons.duplicated(["area_id", "season_end_exclusive"]).any():
        raise DataContractError("V2 has equal-ended seasons within an area; selection would be ambiguous")
    complete = (
        (pd.to_numeric(seasons["gs_calendar_valid"], errors="coerce") == 1)
        & (pd.to_numeric(seasons["gs_available_window_days"], errors="coerce") >= pd.to_numeric(seasons["gs_duration_recalculated_days"], errors="coerce"))
    )
    seasons["season_complete"] = complete.to_numpy()
    keep = ["area_id", "season_year", "season", "season_start", "season_end_exclusive", "gs_available_window_days", "gs_duration_recalculated_days", "gs_calendar_quality", "season_complete", *V2_FEATURES]
    return seasons.loc[:, keep].sort_values(["season_end_exclusive"], kind="mergesort").reset_index(drop=True)


def v2_block(seasons: pd.DataFrame, area_id: np.ndarray, origin_ord: np.ndarray) -> pd.DataFrame:
    """Latest season with exclusive end <= first day of the month after the origin."""
    rows = pd.DataFrame(
        {
            "row": np.arange(len(area_id)),
            "area_id": np.asarray(area_id, dtype=np.int64),
            "boundary": [ord_first_day(o + 1) for o in np.asarray(origin_ord, dtype=np.int64)],
        }
    ).sort_values("boundary", kind="mergesort")
    joined = pd.merge_asof(
        rows,
        seasons,
        left_on="boundary",
        right_on="season_end_exclusive",
        by="area_id",
        direction="backward",
        allow_exact_matches=True,
    ).sort_values("row").reset_index(drop=True)
    status = np.where(joined["season_end_exclusive"].isna(), "no_prior_season", np.where(joined["season_complete"].fillna(False).astype(bool), "selected", "incomplete_export"))
    out = pd.DataFrame({"v2_status": status})
    usable = status == "selected"
    for column in V2_FEATURES:
        out[column] = np.where(usable, pd.to_numeric(joined[column], errors="coerce").to_numpy(dtype=np.float64), np.nan)
    out["v2_season_year"] = joined["season_year"].to_numpy()
    out["v2_season"] = joined["season"].to_numpy()
    out["v2_season_start"] = joined["season_start"].dt.date.astype(str).where(joined["season_start"].notna(), None).to_numpy()
    out["v2_season_end_exclusive"] = joined["season_end_exclusive"].dt.date.astype(str).where(joined["season_end_exclusive"].notna(), None).to_numpy()
    return out


# --------------------------------------------------------------------------
# Base features and persistence
# --------------------------------------------------------------------------


def base_feature_columns(frame: pd.DataFrame) -> List[str]:
    columns = [c for c in select_numeric_feature_columns(frame) if c not in BLOCKED_BASE_FEATURES]
    leaked = [c for c in columns if c in BLOCKED_BASE_FEATURES]
    if leaked:
        raise DataContractError(f"Blocked predictors survived selection: {leaked}")
    return columns


def persistence_lookup(ledger: pd.DataFrame, area_id: np.ndarray, origin_ord: np.ndarray, target_ord: np.ndarray) -> pd.DataFrame:
    """Latest valid reported phase with U <= O and U < T for each row."""
    source = ledger.loc[ledger["valid_phase"], ["area_id", "target_ord", "overall_phase"]].sort_values(["area_id", "target_ord"], kind="mergesort")
    keys = source["area_id"].to_numpy(dtype=np.int64) * 1_000_000 + source["target_ord"].to_numpy(dtype=np.int64)
    area_id = np.asarray(area_id, dtype=np.int64)
    cutoff = np.minimum(np.asarray(origin_ord, dtype=np.int64), np.asarray(target_ord, dtype=np.int64) - 1)
    start = np.searchsorted(keys, area_id * 1_000_000, side="left")
    end = np.searchsorted(keys, area_id * 1_000_000 + cutoff, side="right")
    has = end > start
    index = np.where(has, end - 1, 0)
    months = source["target_ord"].to_numpy(dtype=np.int64)
    phases = source["overall_phase"].to_numpy(dtype=np.float64)
    out = pd.DataFrame(
        {
            "persistence_available": has,
            "persistence_phase": np.where(has, phases[index], np.nan),
            "persistence_source_ord": np.where(has, months[index], -1),
        }
    )
    out["persistence_age_months"] = np.where(has, np.asarray(origin_ord) - out["persistence_source_ord"], np.nan)
    out["persistence_status"] = np.where(has, "available", "no_history")
    return out
