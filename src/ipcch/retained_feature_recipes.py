"""Recompute inherited non-climate dynamic predictors from interim source months at declared anchors.

The saved scope files were produced by ``assemble_latest_IPCCH/build_deep_ipcch_features.py`` (asof12
families, anchor t-12) and ``build_multiscope_ipcch_features.py`` (``_sH`` families: asof12 rows shifted by
``-(12-H)`` on each area's contiguous monthly rows, i.e. anchor t-H). This module re-implements those recipes
on an explicit area x month grid with the ``climate2015_features`` primitives, so every retained column gets a
declared anchor and a row-level comparison against values computed only from source months ``<= t - anchor``.
Columns that cannot be reproduced are reported, never assigned a provenance.
"""
from __future__ import annotations

import re
from typing import Dict, Iterator, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from ipcch import climate2015_features as cf

ORDINARY_SOURCES = (
    "GPP_mean", "nightlight_mean", "event_count_violence", "sum_fatalities_violence",
    "FAO_price", "WFP_Price", "food_price_index_WB", "food_inflation_wb",
)
ENSO = "nino34_anom"
CONFLICT = ("event_count_violence", "sum_fatalities_violence")
# upstream STRESS_SOURCE_COLUMNS / HISTORICAL_RELATIVE_COLUMNS restricted to retained sources
STRESS_SOURCES = ("GPP_mean", "event_count_violence", "FAO_price", "WFP_Price", "food_inflation_wb", ENSO)
HISTORICAL_SOURCES = ("GPP_mean", "nightlight_mean", "FAO_price", "WFP_Price", "food_price_index_WB", ENSO)
COMPOSITES = ("bbg_staple_food", "bbg_oilgas", "bbg_soybean_oil", "bbg_global_food")
COMPOUND_MODIFIERS = ("popdensity", "market_access")
SCOPE_INTERACTIONS = (("event_count_violence", "elevation"), ("FAO_price", "coastline_dist"))
NEIGHBOR_SOURCE = "event_count_violence__nonzero_stress__share12_asof12"
STATIC_COLUMNS_PATTERN = r"^(AEZ_\d+|crop|elevation|market_access|popdensity|range|ruggedness|slope|coastline_dist)$"


def commodity_members(columns: Sequence[str]) -> Dict[str, List[str]]:
    """Upstream ``commodity_groups``: bbg_* members by group name."""
    groups: Dict[str, List[str]] = {name: [] for name in COMPOSITES}
    for column in columns:
        lower = column.lower()
        if not lower.startswith("bbg_"):
            continue
        if "staple_food" in lower:
            groups["bbg_staple_food"].append(column)
        elif "oilgas" in lower or "ngushhub" in lower:
            groups["bbg_oilgas"].append(column)
        elif "soybean_oil" in lower:
            groups["bbg_soybean_oil"].append(column)
        else:
            groups["bbg_global_food"].append(column)
    return {k: v for k, v in groups.items() if len(v) >= 2}


def stress_signal(source: str, x: np.ndarray) -> Tuple[str, np.ndarray]:
    """Upstream ``create_stress_signals`` rule for one retained source (NaN where the source month is NaN)."""
    prev = cf.shift(x, 12)
    with np.errstate(invalid="ignore", divide="ignore"):
        if source in CONFLICT:
            name, hit = "nonzero_stress", np.nan_to_num(x, nan=0.0) > 0
        elif source == "GPP_mean":
            name, hit = "vegetation_stress", x < prev * 0.9
        elif source == ENSO:
            name, hit = "enso_stress", np.abs(x) > 0.5
        else:
            name, hit = "price_shock_stress", cf.safe_divide(x - prev, prev) > 0.10
    return f"{source}__{name}", np.where(np.isnan(x), np.nan, hit.astype(float))


def asof12_families(source: str, x: np.ndarray, first_ord: int) -> Iterator[Tuple[str, np.ndarray]]:
    """Upstream asof12 block for one source; every value uses months ``<= t-12``."""
    is_composite = source.endswith("__composite_mean")
    for lag in (12, 15, 18, 24):
        yield f"{source}__l{lag}", cf.shift(x, lag)
    base = cf.shift(x, 12)
    for w in (3, 6, 12):
        yield f"{source}__roll{w}_mean_asof12", cf.rolling(base, w, cf.MIN_PERIODS_BY_WINDOW[w], "mean")
        if source in CONFLICT:
            yield f"{source}__roll{w}_sum_asof12", cf.rolling(base, w, cf.MIN_PERIODS_BY_WINDOW[w], "sum")
    l12, l24 = cf.shift(x, 12), cf.shift(x, 24)
    yield f"{source}__l12_minus_l24", l12 - l24
    yield f"{source}__l12_ratio_l24", cf.safe_divide(l12, l24)
    for w in (6, 12, 24):
        yield f"{source}__slope{w}_asof12", (l12 - cf.shift(x, 12 + w - 1)) / max(w - 1, 1)
    yield f"{source}__accel6_vs_prev6_asof12", (cf.shift(x, 12) - cf.shift(x, 17)) / 5 - (cf.shift(x, 18) - cf.shift(x, 23)) / 5
    if not is_composite and source in STRESS_SOURCES:
        for r in ("std", "min", "max"):
            yield f"{source}__roll12_{r}_asof12", cf.rolling(base, 12, 6, r)
        yield f"{source}__roll12_iqr_asof12", cf.rolling(base, 12, 6, "q75") - cf.rolling(base, 12, 6, "q25")
        signal, s = stress_signal(source, x)
        for fname, val in cf.stress_families(signal, s, 12, lambda n: n):
            yield fname, val
    if not is_composite and source in HISTORICAL_SOURCES:
        mean, std, rank = cf.same_month_history(x, first_ord)
        for suffix, src in (("anom", x - mean), ("pctnormal", cf.safe_divide(x, mean)), ("z", cf.safe_divide(x - mean, std)), ("pctile", rank)):
            yield f"{source}__hist_same_month_{suffix}_l12", cf.shift(src, 12)


def scope_source_columns(source: str) -> List[str]:
    """Upstream ``available_dynamic_source_columns`` subset that is realigned into the ``_sH`` block."""
    out = [f"{source}__l12"]
    for w in (3, 6, 12):
        out.append(f"{source}__roll{w}_mean_asof12")
        if source in CONFLICT:
            out.append(f"{source}__roll{w}_sum_asof12")
    out += [f"{source}__slope6_asof12", f"{source}__slope12_asof12"]
    if source in STRESS_SOURCES:
        out += [f"{source}__roll12_std_asof12", f"{source}__roll12_iqr_asof12"]
        signal, _ = stress_signal(source, np.zeros((1, 1)))
        out += [f"{signal}__{s}_asof12" for s in ("share12", "months_since", "longest_run12", "any12")]
    return out


def scope_name(asof12_name: str, h: int) -> str:
    """Upstream ``feature_name_from_asof12``."""
    if asof12_name.endswith("__l12"):
        return f"{asof12_name[:-len('__l12')]}__l{h}_s{h}"
    return f"{asof12_name[:-len('_asof12')]}_asof{h}_s{h}"


class RetainedRecipes:
    """Full-grid recomputation of retained dynamic families; :meth:`expected` gathers them for model rows."""

    def __init__(self, panel: pd.DataFrame, static: pd.DataFrame):
        members = commodity_members(panel.columns)
        work = panel.copy()
        for group, cols in members.items():
            work[f"{group}__composite_mean"] = work[cols].apply(pd.to_numeric, errors="coerce").mean(axis=1, skipna=True)
        self.sources = [*ORDINARY_SOURCES, ENSO, *[f"{g}__composite_mean" for g in members]]
        self.grid = cf.Grid.from_long(work, self.sources, require_complete=False)
        self.members = members
        self.static = static.reindex(self.grid.area_ids)
        coords = static.reindex(self.grid.area_ids)
        self.coord_valid = coords["lat"].between(-90, 90).to_numpy() & coords["lon"].between(-180, 180).to_numpy()
        self.neighbors = cf.build_neighbors(coords["lat"].to_numpy(), coords["lon"].to_numpy(), self.coord_valid)
        # Upstream families live on panel rows only: months outside an area's row span have no carrier row,
        # so they are NaN here too (this matters for neighbour means and for the -(12-H) row realignment).
        ai, mi, ok = self.grid.index_of(work["area_id"].to_numpy(), cf.month_ord(work["year"], work["month"]))
        self.row_exists = np.zeros((len(self.grid.area_ids), self.grid.n_months), dtype=bool)
        self.row_exists[ai[ok], mi[ok]] = True
        self.asof12: Dict[str, np.ndarray] = {}
        for source in self.sources:
            for name, val in asof12_families(source, self.grid.values[source], self.grid.first_ord):
                self.asof12[name] = np.where(self.row_exists, val, np.nan)
        self.asof12[f"neighbor3_mean__{NEIGHBOR_SOURCE}"] = np.where(self.row_exists, cf.neighbor_mean(self.asof12[NEIGHBOR_SOURCE], self.neighbors, self.coord_valid), np.nan)
        for modifier in COMPOUND_MODIFIERS:
            self.asof12[f"{NEIGHBOR_SOURCE}__x__{modifier}"] = self.asof12[NEIGHBOR_SOURCE] * self.static[modifier].to_numpy(dtype=float)[:, None]

    def gather(self, values: np.ndarray, keys: pd.DataFrame, offset: int = 0) -> np.ndarray:
        """Grid value at month ``t + offset`` (``offset = 12 - H`` mimics the upstream row shift)."""
        return cf.gather(values, self.grid.index_of(keys["area_id"].to_numpy(), cf.month_ord(keys["year"], keys["month"]) + offset))

    def expected(self, keys: pd.DataFrame, horizon: Optional[int], scope_static: pd.DataFrame) -> Tuple[Dict[str, np.ndarray], Dict[str, int]]:
        """Recomputed columns for a scope file's rows plus their declared anchor (latest source month t-anchor)."""
        out: Dict[str, np.ndarray] = {}
        anchor: Dict[str, int] = {}
        for name, val in self.asof12.items():
            out[name] = self.gather(val, keys)
            anchor[name] = 12
        if horizon is None:
            return out, anchor
        h = horizon
        for source in ORDINARY_SOURCES:
            for src in scope_source_columns(source):
                out[scope_name(src, h)] = self.gather(self.asof12[src], keys, 12 - h)
                anchor[scope_name(src, h)] = h
        nb = f"neighbor3_mean__{NEIGHBOR_SOURCE}"
        out[scope_name(nb, h)] = self.gather(self.asof12[nb], keys, 12 - h)
        anchor[scope_name(nb, h)] = h
        out[f"{ENSO}__forecast_sequence_s{h}"] = self.gather(self.asof12[f"{ENSO}__l12"], keys, 12 - h)
        anchor[f"{ENSO}__forecast_sequence_s{h}"] = h
        out[f"{ENSO}__l12_delayed_control_s{h}"] = self.gather(self.asof12[f"{ENSO}__l12"], keys)
        anchor[f"{ENSO}__l12_delayed_control_s{h}"] = 12
        for source, modifier in SCOPE_INTERACTIONS:
            left = f"{source}__l{h}_s{h}"
            out[f"{left}__x__{modifier}_s{h}"] = out[left] * scope_static[modifier].to_numpy(dtype=float)
            anchor[f"{left}__x__{modifier}_s{h}"] = h
        return out, anchor


def compare_columns(saved: pd.DataFrame, expected: Dict[str, np.ndarray], rtol: float = 1e-6, atol: float = 1e-9) -> pd.DataFrame:
    """Row-level comparison. ``saved_value_unsupported`` counts saved values the recipe cannot reproduce."""
    rows = []
    for column in saved.columns:
        s = pd.to_numeric(saved[column], errors="coerce").to_numpy(dtype=float)
        if column not in expected:
            rows.append({"feature": column, "status": "no_recipe", "n_rows": len(s)})
            continue
        e = expected[column]
        both = ~np.isnan(s) & ~np.isnan(e)
        close = np.zeros(len(s), dtype=bool)
        close[both] = np.isclose(s[both], e[both], rtol=rtol, atol=atol)
        value_mismatch = int((both & ~close).sum())
        saved_only = int((~np.isnan(s) & np.isnan(e)).sum())
        expected_only = int((np.isnan(s) & ~np.isnan(e)).sum())
        if value_mismatch == 0 and saved_only == 0:
            status = "verified" if expected_only == 0 else "verified_saved_missing_retained"
        else:
            status = "disagreement"
        rows.append({
            "feature": column, "status": status, "n_rows": len(s), "n_both": int(both.sum()),
            "value_mismatch": value_mismatch, "saved_value_unsupported": saved_only,
            "saved_missing_recipe_present": expected_only,
            "max_abs_diff": float(np.max(np.abs(s[both] - e[both]))) if both.any() else 0.0,
        })
    return pd.DataFrame(rows)


def is_static_name(column: str) -> bool:
    return re.match(STATIC_COLUMNS_PATTERN, column) is not None
