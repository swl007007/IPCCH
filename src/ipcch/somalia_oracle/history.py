"""Rich phase-distribution history, ported from the pinned reference.

Source: Food_Crisis_Cluster@85bc505a5b99 ``IPCCHPopulationHistoryExperiment/prepare_data.py``
(sha256 d582ebad1112778eff1ce5c2d41a0df92bad6707df2455fd6fd5cde1d62814fc),
``build_history_index`` / ``_gather_window`` / ``_window_statistics`` / ``build_history_block``.
Formulas are unchanged. Two task-specific adaptations:

* visibility and reference month are separate: observations with month <= ``cutoff_ord``
  are visible (``cutoff = min(O, T - 1)``), while ages and calendar windows stay
  anchored at the row's origin ``O``. For H >= 1 this is identical to the reference;
  at H = 0 it excludes the target month itself (R5).
* the four reference aliases of original93 columns are materialized here, because
  IPCCH has no semantically identical base feature; ``hist_support_common_all_age``
  equals ``hist_age_obs1`` and is not duplicated.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence

import numpy as np
import pandas as pd

from ipcch import paths


class PreparationError(RuntimeError):
    """A history contract invariant does not hold."""


SERIES_ORDER = ("q2", "q3", "q4", "q5", "severity_index", "entropy", "concentration", "severe_fraction")
COMPLETE_SERIES = SERIES_ORDER[:7]
RATIO_SERIES = "severe_fraction"
WINDOWS = (("m06", 6), ("m12", 12), ("m24", 24), ("m36", 36), ("all", None))
STATISTICS = ("mean", "std", "min", "max", "latest_minus_mean", "slope")
N_SLOTS = 6
CRISIS_THRESHOLD = 0.20
BLOCK_ORDER = (
    "observation_levels",
    "observation_timing",
    "changes",
    "observation_trends",
    "window_statistics",
    "window_support",
    "prior_binary_states",
    "threshold_distance",
    "window_crisis",
    "event_and_run",
)
SCHEMA_PATH = paths.CONFIG_DIR / "somalia_oracle_history_schema.json"


def load_history_schema(path: Path = SCHEMA_PATH) -> Dict[str, object]:
    schema = json.loads(Path(path).read_text(encoding="utf-8"))
    if tuple(schema["series_order"]) != SERIES_ORDER or tuple(schema["windows"]) != tuple(n for n, _ in WINDOWS):
        raise PreparationError("history schema drifted from the implementation")
    if tuple(schema["statistic_order"]) != STATISTICS or tuple(schema["reference_blocks"]) != BLOCK_ORDER:
        raise PreparationError("history schema block/statistic order drifted")
    return schema


def history_feature_names(schema: Dict[str, object] | None = None) -> List[str]:
    """Reference 468 columns in block order, then the materialized aliases."""
    schema = schema or load_history_schema()
    names: List[str] = []
    for block in BLOCK_ORDER:
        names.extend(schema["reference_blocks"][block])
    if len(names) != int(schema["reference_additional_count"]):
        raise PreparationError("reference block inventory does not match its declared count")
    names.extend(schema["materialized_aliases"])
    if len(set(names)) != len(names):
        raise PreparationError("duplicate history feature name")
    return names


def compute_series(p: np.ndarray) -> pd.DataFrame:
    """Eight history series from normalized shares ``p`` (n x 5, p1..p5)."""
    p = np.asarray(p, dtype=np.float64)
    if not np.isfinite(p).all():
        raise PreparationError("non-finite normalized share on a valid history row")
    q2 = p[:, 1:].sum(axis=1)
    q3 = p[:, 2:].sum(axis=1)
    q4 = p[:, 3:].sum(axis=1)
    q5 = p[:, 4]
    weights = np.arange(1, 6, dtype=np.float64)
    severity = p @ weights
    concentration = (p * p).sum(axis=1)
    safe = np.where(p > 0.0, p, 1.0)
    entropy = -(np.where(p > 0.0, p * np.log(safe), 0.0)).sum(axis=1) / np.log(5.0)
    severe_fraction = np.where(q3 > 0.0, q4 / np.where(q3 > 0.0, q3, 1.0), np.nan)
    return pd.DataFrame(
        {
            "q2": q2,
            "q3": q3,
            "q4": q4,
            "q5": q5,
            "severity_index": severity,
            "entropy": entropy,
            "concentration": concentration,
            "severe_fraction": severe_fraction,
        }
    )


_KEY_SCALE = 1_000_000


@dataclass
class HistoryIndex:
    """The full valid ledger, indexed for own-origin history queries."""

    keys: np.ndarray  # packed (admin_code, month), strictly increasing
    admin: np.ndarray
    months: np.ndarray
    months_f: np.ndarray
    states: np.ndarray  # exact ledger binary label
    series: dict  # name -> float64 values, NaN where undefined
    last_crisis: np.ndarray
    last_noncrisis: np.ndarray
    last_entry_newer: np.ndarray
    last_exit_newer: np.ndarray
    run_start: np.ndarray
    max_area_span: int
    n: int


def build_history_index(valid: pd.DataFrame) -> HistoryIndex:
    """Index the full valid history ledger.

    ``valid`` must be the complete set of R1-valid outcomes, not a fitting or
    evaluation subset: the contract reads history from all of it.
    """
    frame = valid.copy()
    frame["month_ord"] = frame["target_ord"].astype(np.int64)
    frame["admin_code"] = frame["area_id"].astype(np.int64)
    if frame.duplicated(["admin_code", "month_ord"]).any():
        raise PreparationError("valid ledger has duplicate (admin_code, month)")
    frame = frame.sort_values(["admin_code", "month_ord"], kind="mergesort").reset_index(
        drop=True
    )

    series = compute_series(frame[[f"h_p{i}" for i in range(1, 6)]].to_numpy(dtype=np.float64))

    admin = frame["admin_code"].to_numpy(dtype=np.int64)
    months = frame["month_ord"].to_numpy(dtype=np.int64)
    if months.min() < 0 or months.max() >= _KEY_SCALE:
        raise PreparationError("month ordinal outside the packing range")
    keys = admin * _KEY_SCALE + months
    if not np.all(np.diff(keys) > 0):
        raise PreparationError("packed observation keys are not strictly increasing")

    states = pd.to_numeric(frame["history_crisis_state"]).to_numpy(dtype=np.int64)
    if not np.isin(states, (0, 1)).all():
        raise PreparationError("valid ledger carries a non-binary label")

    n = len(frame)
    # Most recent record of each kind at or before index i, reset at every area
    # boundary so a neighbouring area can never supply an event.
    last_crisis = np.full(n, -1, dtype=np.int64)
    last_noncrisis = np.full(n, -1, dtype=np.int64)
    last_entry_newer = np.full(n, -1, dtype=np.int64)
    last_exit_newer = np.full(n, -1, dtype=np.int64)
    run_start = np.zeros(n, dtype=np.int64)
    current_crisis = current_noncrisis = current_entry = current_exit = -1
    for i in range(n):
        if i == 0 or admin[i] != admin[i - 1]:
            current_crisis = current_noncrisis = current_entry = current_exit = -1
            run_start[i] = i
        else:
            if states[i] == 1 and states[i - 1] == 0:
                current_entry = i
            elif states[i] == 0 and states[i - 1] == 1:
                current_exit = i
            run_start[i] = run_start[i - 1] if states[i] == states[i - 1] else i
        if states[i] == 0:
            current_noncrisis = i
        else:
            current_crisis = i
        last_crisis[i] = current_crisis
        last_noncrisis[i] = current_noncrisis
        last_entry_newer[i] = current_entry
        last_exit_newer[i] = current_exit

    _, area_sizes = np.unique(admin, return_counts=True)
    max_area_span = int(area_sizes.max()) if n else 0

    return HistoryIndex(
        keys=keys,
        admin=admin,
        months=months,
        months_f=months.astype(np.float64),
        states=states,
        series={name: series[name].to_numpy(dtype=np.float64) for name in SERIES_ORDER},
        last_crisis=last_crisis,
        last_noncrisis=last_noncrisis,
        last_entry_newer=last_entry_newer,
        last_exit_newer=last_exit_newer,
        run_start=run_start,
        max_area_span=max_area_span,
        n=n,
    )


def _gather_window(lo: np.ndarray, hi: np.ndarray, span: int) -> tuple[np.ndarray, np.ndarray]:
    """Padded oldest-to-newest indices for each ``[lo, hi)`` plus an in-range mask."""
    offsets = np.arange(span, dtype=np.int64)
    index = lo[:, None] + offsets[None, :]
    mask = index < hi[:, None]
    return np.where(mask, index, 0), mask


def _window_statistics(
    values: np.ndarray, months_f: np.ndarray, index: np.ndarray, mask: np.ndarray
) -> dict:
    """mean/std/min/max/latest-minus-mean/slope over each gathered window.

    Support rules, applied per statistic rather than per window: mean, extrema
    and latest-minus-mean need one finite value, std needs two, slope needs
    three. Insufficient support is missing, never zero.
    """
    x = np.where(mask, values[index], np.nan)
    finite = np.isfinite(x)
    n = finite.sum(axis=1)
    rows = x.shape[0]

    nan = np.full(rows, np.nan, dtype=np.float64)
    has_one = n >= 1
    total = np.where(finite, x, 0.0).sum(axis=1)
    mean = np.where(has_one, total / np.where(has_one, n, 1), np.nan)

    deviation = np.where(finite, x - mean[:, None], 0.0)
    sq = (deviation * deviation).sum(axis=1)
    std = np.where(n >= 2, np.sqrt(np.maximum(sq / np.where(n >= 2, n, 1), 0.0)), np.nan)

    big = np.where(finite, x, np.inf)
    small = np.where(finite, x, -np.inf)
    minimum = np.where(has_one, big.min(axis=1), np.nan)
    maximum = np.where(has_one, small.max(axis=1), np.nan)

    # Columns run oldest to newest, so the latest finite value is the finite
    # column with the largest position.
    positions = np.where(finite, np.arange(x.shape[1])[None, :], -1)
    latest_column = positions.max(axis=1)
    latest = np.where(
        has_one, x[np.arange(rows), np.maximum(latest_column, 0)], np.nan
    )

    t = np.where(mask, months_f[index], np.nan)
    t_mean = np.where(
        has_one, np.where(finite, t, 0.0).sum(axis=1) / np.where(has_one, n, 1), np.nan
    )
    t_dev = np.where(finite, t - t_mean[:, None], 0.0)
    stt = (t_dev * t_dev).sum(axis=1)
    stx = (t_dev * deviation).sum(axis=1)
    enough = (n >= 3) & (stt > 0.0)
    slope = np.where(enough, stx / np.where(enough, stt, 1.0), np.nan)

    return {
        "n": n,
        "finite": finite,
        "mean": mean,
        "std": std,
        "min": minimum,
        "max": maximum,
        "latest": latest,
        "latest_minus_mean": np.where(has_one, latest - mean, nan),
        "slope": slope,
    }


# --------------------------------------------------------------------------
# The 468 appended columns
# --------------------------------------------------------------------------


def _pick(values: np.ndarray, index: np.ndarray, ok: np.ndarray) -> np.ndarray:
    out = np.full(index.shape, np.nan, dtype=np.float64)
    if ok.any():
        out[ok] = values[index[ok]]
    return out


def build_history_block(
    index: HistoryIndex,
    admin_code: np.ndarray,
    origin_ord: np.ndarray,
    cutoff_ord: np.ndarray,
    feature_names: Sequence[str],
) -> np.ndarray:
    """Compute the appended history columns for each ``(area, origin)`` row.

    ``origin_ord`` is the row's own ``o = T - h``. Observations at months
    strictly after ``o`` are invisible by construction: the range end comes
    from a right-insertion of ``o`` itself into that area's block.
    """
    admin_code = np.asarray(admin_code, dtype=np.int64)
    origin_ord = np.asarray(origin_ord, dtype=np.int64)
    if admin_code.shape != origin_ord.shape:
        raise PreparationError("admin_code and origin_ord lengths differ")
    rows = admin_code.size

    area_start = np.searchsorted(index.keys, admin_code * _KEY_SCALE, side="left")
    cutoff_ord = np.asarray(cutoff_ord, dtype=np.int64)
    if cutoff_ord.shape != origin_ord.shape or np.any(cutoff_ord > origin_ord):
        raise PreparationError("history cutoff must be aligned with and not after the origin")
    hi = np.searchsorted(index.keys, admin_code * _KEY_SCALE + cutoff_ord, side="right")
    if np.any(hi < area_start):
        raise PreparationError("history range end precedes its area block")
    span = index.max_area_span
    if np.any(hi - area_start > span):
        raise PreparationError("an area block is wider than the recorded maximum")

    columns: dict[str, np.ndarray] = {}
    origin_f = origin_ord.astype(np.float64)
    months_f = index.months_f
    states_f = index.states.astype(np.float64)

    # --- observation slots, newest first ----------------------------------
    slot_index = np.empty((N_SLOTS, rows), dtype=np.int64)
    slot_ok = np.empty((N_SLOTS, rows), dtype=bool)
    slot_month = np.empty((N_SLOTS, rows), dtype=np.float64)
    for j in range(N_SLOTS):
        idx = hi - 1 - j
        ok = idx >= area_start
        slot_index[j] = np.where(ok, idx, 0)
        slot_ok[j] = ok
        slot_month[j] = _pick(months_f, slot_index[j], ok)

    slot_value: dict[str, np.ndarray] = {}
    for name in SERIES_ORDER:
        values = index.series[name]
        stacked = np.empty((N_SLOTS, rows), dtype=np.float64)
        for j in range(N_SLOTS):
            stacked[j] = _pick(values, slot_index[j], slot_ok[j])
            columns[f"hist_{name}_obs{j + 1}"] = stacked[j]
        slot_value[name] = stacked

    # observation_timing: ages of slots 2..6 (slot 1's age is an alias of an
    # original93 column) and the five adjacent gaps.
    for j in range(1, N_SLOTS):
        columns[f"hist_age_obs{j + 1}"] = origin_f - slot_month[j]
    for j in range(N_SLOTS - 1):
        columns[f"hist_gap_obs{j + 1}_obs{j + 2}"] = slot_month[j] - slot_month[j + 1]

    # changes: raw difference newer-older and its per-month rate
    for name in SERIES_ORDER:
        stacked = slot_value[name]
        for j in range(N_SLOTS - 1):
            gap = slot_month[j] - slot_month[j + 1]
            difference = stacked[j] - stacked[j + 1]
            usable = np.isfinite(gap) & (gap > 0)
            rate = np.where(usable, difference / np.where(usable, gap, 1.0), np.nan)
            columns[f"hist_{name}_change_obs{j + 1}_obs{j + 2}"] = difference
            columns[f"hist_{name}_rate_obs{j + 1}_obs{j + 2}"] = rate

    # --- trends over the last 3 and last 6 slots --------------------------
    for label, depth in (("last3", 3), ("last6", 6)):
        lo = np.maximum(area_start, hi - depth)
        gathered, mask = _gather_window(lo, hi, depth)
        for name in SERIES_ORDER:
            stats = _window_statistics(index.series[name], months_f, gathered, mask)
            columns[f"hist_{name}_slope_{label}"] = stats["slope"]

    # --- calendar windows --------------------------------------------------
    window_ranges: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
    for label, width in WINDOWS:
        if width is None:
            lo = area_start
        else:
            lo = np.maximum(
                np.searchsorted(
                    index.keys,
                    admin_code * _KEY_SCALE + (origin_ord - width + 1),
                    side="left",
                ),
                area_start,
            )
        gathered, mask = _gather_window(lo, hi, span)
        window_ranges[label] = (lo, gathered, mask)

    for name in SERIES_ORDER:
        for label, _width in WINDOWS:
            _lo, gathered, mask = window_ranges[label]
            stats = _window_statistics(index.series[name], months_f, gathered, mask)
            for statistic in STATISTICS:
                columns[f"hist_{name}_{label}_{statistic}"] = stats[statistic]

    # --- window support ----------------------------------------------------
    # The seven complete series share one mask; severe_fraction carries its own,
    # because a q3 == 0 observation contributes to neither its count nor span.
    for label, _width in WINDOWS:
        lo, gathered, mask = window_ranges[label]
        count = (hi - lo).astype(np.float64)
        has = count >= 1
        newest_month = _pick(months_f, np.where(has, hi - 1, 0), has)
        oldest_month = _pick(months_f, np.where(has, lo, 0), has)
        columns[f"hist_support_common_{label}_count"] = count
        columns[f"hist_support_common_{label}_span"] = newest_month - oldest_month
        if label != "all":  # the all-window age is an alias of an original column
            columns[f"hist_support_common_{label}_age"] = origin_f - newest_month

        ratio_finite = np.isfinite(np.where(mask, index.series[RATIO_SERIES][gathered], np.nan))
        ratio_count = ratio_finite.sum(axis=1)
        ratio_has = ratio_count >= 1
        positions = np.where(ratio_finite, np.arange(mask.shape[1])[None, :], -1)
        newest_column = positions.max(axis=1)
        oldest_column = np.where(
            ratio_finite, np.arange(mask.shape[1])[None, :], mask.shape[1]
        ).min(axis=1)
        row_index = np.arange(rows)
        ratio_newest = np.where(
            ratio_has,
            months_f[gathered[row_index, np.maximum(newest_column, 0)]],
            np.nan,
        )
        ratio_oldest = np.where(
            ratio_has,
            months_f[gathered[row_index, np.minimum(oldest_column, mask.shape[1] - 1)]],
            np.nan,
        )
        columns[f"hist_support_{RATIO_SERIES}_{label}_count"] = ratio_count.astype(np.float64)
        columns[f"hist_support_{RATIO_SERIES}_{label}_span"] = ratio_newest - ratio_oldest
        columns[f"hist_support_{RATIO_SERIES}_{label}_age"] = origin_f - ratio_newest

    # --- prior binary states ----------------------------------------------
    for j in range(1, N_SLOTS):
        columns[f"hist_crisis_obs{j + 1}"] = _pick(states_f, slot_index[j], slot_ok[j])

    # --- distance to the .20 threshold ------------------------------------
    q3_obs1 = slot_value["q3"][0]
    columns["hist_q3_margin_obs1"] = q3_obs1 - CRISIS_THRESHOLD
    columns["hist_q3_abs_margin_obs1"] = np.abs(q3_obs1 - CRISIS_THRESHOLD)
    abs_margin = np.abs(index.series["q3"] - CRISIS_THRESHOLD)
    for label, _width in WINDOWS:
        _lo, gathered, mask = window_ranges[label]
        stats = _window_statistics(abs_margin, months_f, gathered, mask)
        columns[f"hist_q3_{label}_abs_margin_mean"] = stats["mean"]
        columns[f"hist_q3_{label}_abs_margin_min"] = stats["min"]

    # --- observed crisis dynamics per window -------------------------------
    for label, _width in WINDOWS:
        lo, gathered, mask = window_ranges[label]
        count = (hi - lo).astype(np.float64)
        gathered_states = np.where(mask, states_f[gathered], np.nan)
        live = count >= 1
        fraction = np.where(
            live,
            np.where(mask, gathered_states, 0.0).sum(axis=1) / np.where(live, count, 1.0),
            np.nan,
        )
        # A pair exists only where BOTH endpoints are inside the window.
        pair = mask[:, :-1] & mask[:, 1:]
        older = np.where(pair, np.where(mask[:, :-1], gathered_states[:, :-1], 0.0), np.nan)
        newer = np.where(pair, np.where(mask[:, 1:], gathered_states[:, 1:], 0.0), np.nan)
        entries = ((older == 0.0) & (newer == 1.0) & pair).sum(axis=1).astype(np.float64)
        exits = ((older == 1.0) & (newer == 0.0) & pair).sum(axis=1).astype(np.float64)
        enough = count >= 2
        columns[f"hist_crisis_{label}_fraction"] = fraction
        columns[f"hist_crisis_{label}_entries"] = np.where(enough, entries, np.nan)
        columns[f"hist_crisis_{label}_exits"] = np.where(enough, exits, np.nan)
        # Eligible pairs are reported even when the counts are not, so a long
        # gap can never be mistaken for continuous observation.
        columns[f"hist_crisis_{label}_pairs"] = np.maximum(count - 1.0, 0.0)

    # --- events and the current run ---------------------------------------
    newest_index = np.maximum(hi - 1, 0)
    any_history = hi > area_start

    noncrisis_idx = np.where(any_history, index.last_noncrisis[newest_index], -1)
    noncrisis_ok = any_history & (noncrisis_idx >= area_start)
    columns["hist_noncrisis_age"] = origin_f - _pick(
        months_f, np.where(noncrisis_ok, noncrisis_idx, 0), noncrisis_ok
    )
    columns["hist_no_noncrisis"] = (~noncrisis_ok).astype(np.float64)

    for kind, table in (("entry", index.last_entry_newer), ("exit", index.last_exit_newer)):
        idx = np.where(any_history, table[newest_index], -1)
        # The change is dated at its later observed endpoint, which must itself
        # lie inside this row's visible history.
        ok = any_history & (idx >= area_start) & (idx <= hi - 1)
        columns[f"hist_{kind}_age"] = origin_f - _pick(months_f, np.where(ok, idx, 0), ok)
        columns[f"hist_no_{kind}"] = (~ok).astype(np.float64)

    run_begin = np.where(any_history, index.run_start[newest_index], 0)
    columns["hist_current_run_count"] = np.where(
        any_history, (hi - run_begin).astype(np.float64), np.nan
    )
    columns["hist_current_run_span"] = np.where(
        any_history,
        _pick(months_f, newest_index, any_history) - _pick(months_f, run_begin, any_history),
        np.nan,
    )

    # --- materialized aliases (reference check_aliases definitions) ---------
    columns["hist_age_obs1"] = origin_f - _pick(months_f, newest_index, any_history)
    columns["hist_crisis_obs1"] = _pick(states_f, newest_index, any_history)
    crisis_idx = np.where(any_history, index.last_crisis[newest_index], -1)
    crisis_ok = any_history & (crisis_idx >= area_start)
    columns["hist_crisis_age"] = origin_f - _pick(months_f, np.where(crisis_ok, crisis_idx, 0), crisis_ok)
    columns["hist_no_crisis"] = (~crisis_ok).astype(np.float64)

    # --- assemble in the frozen order -------------------------------------
    missing = [name for name in feature_names if name not in columns]
    if missing:
        raise PreparationError(f"history block did not produce: {missing[:10]}")
    extra = sorted(set(columns) - set(feature_names))
    if extra:
        raise PreparationError(f"history block produced unlisted columns: {extra[:10]}")

    block = np.empty((rows, len(feature_names)), dtype=np.float64)
    for position, name in enumerate(feature_names):
        values = columns[name]
        if np.isinf(values).any():
            raise PreparationError(f"engineered column {name} produced an infinity")
        block[:, position] = values
    return block


# --------------------------------------------------------------------------
# Matrices, keys and folds
# --------------------------------------------------------------------------



def history_slot_sources(index: HistoryIndex, admin_code: np.ndarray, cutoff_ord: np.ndarray) -> pd.DataFrame:
    """Source month ordinals of the six newest visible observations (-1 where absent)."""
    admin_code = np.asarray(admin_code, dtype=np.int64)
    cutoff_ord = np.asarray(cutoff_ord, dtype=np.int64)
    area_start = np.searchsorted(index.keys, admin_code * _KEY_SCALE, side="left")
    hi = np.searchsorted(index.keys, admin_code * _KEY_SCALE + cutoff_ord, side="right")
    out = {"history_visible_count": (hi - area_start).astype(np.int64)}
    for j in range(N_SLOTS):
        idx = hi - 1 - j
        ok = idx >= area_start
        out[f"history_obs{j + 1}_source_ord"] = np.where(ok, index.months[np.where(ok, idx, 0)], -1)
    return pd.DataFrame(out)
