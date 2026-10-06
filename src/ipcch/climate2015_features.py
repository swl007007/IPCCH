"""climate2015_v1: fork of the upstream deep-feature climate recipe for the 2015-2026 climate release.

Upstream recipe: ``assemble_latest_IPCCH/build_deep_ipcch_features.py`` (asof12 families) and
``build_multiscope_ipcch_features.py`` (scope ``_sH`` families). Families are computed here on a
complete area x month grid with an explicit anchor ``a`` (latest source month ``t-a``) instead of
upstream's row shift of the asof12 columns; for a complete grid the two are equivalent.
Design: ``.trellis/tasks/10-05-global-climate-2015-features/design.md``.
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass
from typing import Callable, Dict, Iterator, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

CLIMATE_BASES = (
    "prcp_anom", "prcp_z", "rainy_days", "cdd", "tmean_anom", "tmax_anom", "hot_days_p95",
    "gdd", "edd", "sm_z", "spi03", "spei03", "ndvi_anom", "evi_anom",
)
MONTHLY_VARIABLES = tuple(f"{b}_month_ensmean" for b in CLIMATE_BASES)
SEASONAL_VARIABLES = tuple(f"{b}_gs_ensmean" for b in CLIMATE_BASES)
OLD_CLIMATE_TOKENS = ("Rainf_f_tavg_mean", "Tair_f_tavg_mean", "SoilMoi00_10cm_tavg_mean", "EVI_mean")

ANCHOR_LAGS_OFFSETS = (0, 3, 6, 12)  # upstream ANCHOR_LAGS [12, 15, 18, 24] relative to anchor 12
ROLLING_WINDOWS = (3, 6, 12)
TREND_WINDOWS = (6, 12, 24)
SCOPE_TREND_WINDOWS = (6, 12)
MIN_PERIODS_BY_WINDOW = {3: 2, 6: 3, 12: 6, 24: 12}
STRESS_MIN_PERIODS = 6

DEFICIT = "spi03_month_ensmean__deficit_stress"
HOT = "tmean_anom_month_ensmean__hot_stress"
VEGETATION = "evi_anom_month_ensmean__vegetation_stress"
# (signal name, source variable, rule) -- fixed standard thresholds (grill 2026-10-05)
STRESS_RULES: Tuple[Tuple[str, str, Callable[[np.ndarray], np.ndarray]], ...] = (
    (DEFICIT, "spi03_month_ensmean", lambda x: x <= -1.0),
    (HOT, "tmean_anom_month_ensmean", lambda x: x >= 1.0),
    (VEGETATION, "evi_anom_month_ensmean", lambda x: x <= -0.015),
)
SCOPE_INTERACTIONS = (("prcp_z_month_ensmean", "market_access"), ("tmean_anom_month_ensmean", "popdensity"))
COMPOUND_STATIC_MODIFIERS = ("popdensity", "market_access")
ENSO_SHARE = "nino34_anom__enso_stress__share12_asof12"
N_LAST_SEASONS = 2
N_NEIGHBORS = 3


def month_ord(year, month):
    return np.asarray(year, dtype=np.int64) * 12 + np.asarray(month, dtype=np.int64) - 1


def is_old_climate_column(column: str) -> bool:
    return any(token in column for token in OLD_CLIMATE_TOKENS)


# --------------------------------------------------------------------------- grid primitives


@dataclass
class Grid:
    """Complete area x month panel; ``values[v]`` is an (n_areas, n_months) float array."""

    area_ids: np.ndarray
    first_ord: int
    n_months: int
    values: Dict[str, np.ndarray]

    @classmethod
    def from_long(cls, df: pd.DataFrame, variables: Sequence[str], area_col: str = "area_id", require_complete: bool = True) -> "Grid":
        """``require_complete=False`` accepts ragged spans if every area's months are contiguous
        (missing cells become NaN; values of observed months are unaffected)."""
        ords = month_ord(df["year"], df["month"])
        area_ids = np.sort(df[area_col].unique())
        first, last = int(ords.min()), int(ords.max())
        n_months = last - first + 1
        if df.duplicated([area_col, "year", "month"]).any():
            raise ValueError("panel has duplicate area-month keys")
        if require_complete and len(df) != len(area_ids) * n_months:
            raise ValueError("climate panel is not a complete area x month grid")
        if not require_complete:
            span = pd.Series(ords).groupby(df[area_col].to_numpy()).agg(["min", "max", "count"])
            if ((span["max"] - span["min"] + 1) != span["count"]).any():
                raise ValueError("panel has internal month gaps; row shifts would not equal month shifts")
        ai = np.searchsorted(area_ids, df[area_col].to_numpy())
        mi = ords - first
        values = {}
        for v in variables:
            arr = np.full((len(area_ids), n_months), np.nan)
            arr[ai, mi] = pd.to_numeric(df[v], errors="coerce").to_numpy(dtype=float)
            values[v] = arr
        return cls(area_ids, first, n_months, values)

    def index_of(self, area_ids, ords) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Row/column indices for keys plus a mask of keys inside the grid."""
        area_ids = np.asarray(area_ids)
        ai = np.searchsorted(self.area_ids, area_ids)
        ai_clip = np.clip(ai, 0, len(self.area_ids) - 1)
        mi = np.asarray(ords, dtype=np.int64) - self.first_ord
        ok = (self.area_ids[ai_clip] == area_ids) & (mi >= 0) & (mi < self.n_months)
        return ai_clip, np.clip(mi, 0, self.n_months - 1), ok


def shift(x: np.ndarray, k: int) -> np.ndarray:
    """Value at month t-k (k >= 0), NaN where history is unavailable."""
    if k == 0:
        return x.copy()
    out = np.full_like(x, np.nan)
    out[:, k:] = x[:, :-k]
    return out


def rolling(x: np.ndarray, window: int, min_periods: int, reducer: str) -> np.ndarray:
    """Trailing window over months ending at each column (pandas semantics, NaN-skipping)."""
    roller = pd.DataFrame(x.T).rolling(window, min_periods=min_periods)
    if reducer == "q25":
        out = roller.quantile(0.25)
    elif reducer == "q75":
        out = roller.quantile(0.75)
    else:
        out = getattr(roller, reducer)()
    return out.to_numpy().T


def safe_divide(num: np.ndarray, den: np.ndarray) -> np.ndarray:
    den = np.where(den == 0, np.nan, den)
    with np.errstate(divide="ignore", invalid="ignore"):
        return num / den


def months_since(signal_at_anchor: np.ndarray) -> np.ndarray:
    """Upstream ``months_since_stress`` on an already anchor-shifted signal."""
    out = np.full_like(signal_at_anchor, np.nan)
    last = np.full(signal_at_anchor.shape[0], np.nan)
    for j in range(signal_at_anchor.shape[1]):
        value = signal_at_anchor[:, j]
        hit = value == 1
        last = np.where(hit, 0.0, last + 1.0)  # NaN + 1 stays NaN until the first stress month
        out[:, j] = last
    return out


def longest_run(signal_at_anchor: np.ndarray, window: int = 12, min_periods: int = STRESS_MIN_PERIODS) -> np.ndarray:
    """Upstream ``longest_run``: longest run of 1s in the trailing window; NaN breaks a run."""
    n_areas, n_months = signal_at_anchor.shape
    out = np.full_like(signal_at_anchor, np.nan)
    for j in range(n_months):
        lo = max(0, j - window + 1)
        win = signal_at_anchor[:, lo : j + 1]
        enough = np.sum(~np.isnan(win), axis=1) >= min_periods
        best = np.zeros(n_areas)
        current = np.zeros(n_areas)
        for k in range(win.shape[1]):
            current = np.where(win[:, k] == 1, current + 1, 0)
            best = np.maximum(best, current)
        out[:, j] = np.where(enough, best, np.nan)
    return out


def same_month_history(x: np.ndarray, first_ord: int) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Prior (strictly earlier years) mean, std (ddof=1) and <=-rank by area and calendar month."""
    lead = first_ord % 12
    n_areas, n_months = x.shape
    total = lead + n_months
    n_years = -(-total // 12)
    padded = np.full((n_areas, n_years * 12), np.nan)
    padded[:, lead : lead + n_months] = x
    cube = padded.reshape(n_areas, n_years, 12)
    mean = np.full_like(cube, np.nan)
    std = np.full_like(cube, np.nan)
    rank = np.full_like(cube, np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        for y in range(1, n_years):
            prior = cube[:, :y, :]
            count = np.sum(~np.isnan(prior), axis=1)
            psum = np.nansum(prior, axis=1)
            mean[:, y, :] = np.where(count >= 1, psum / np.maximum(count, 1), np.nan)
            centred = prior - mean[:, y : y + 1, :]
            ss = np.nansum(centred**2, axis=1)
            std[:, y, :] = np.where(count >= 2, np.sqrt(ss / np.maximum(count - 1, 1)), np.nan)
            current = cube[:, y, :]
            le = np.sum(prior <= current[:, None, :], axis=1)
            rank[:, y, :] = np.where((count >= 1) & ~np.isnan(current), le / np.maximum(count, 1), np.nan)

    def unpad(c: np.ndarray) -> np.ndarray:
        return c.reshape(n_areas, n_years * 12)[:, lead : lead + n_months]

    return unpad(mean), unpad(std), unpad(rank)


# --------------------------------------------------------------------------- feature families


def variable_families(v: str, x: np.ndarray, anchor: int, name: Callable[[str], str], full: bool, first_ord: int) -> Iterator[Tuple[str, np.ndarray]]:
    """Generic per-variable families at ``anchor``.

    ``full=True`` is the upstream asof12 block (lags 12/15/18/24, gap, 3 slopes, accel, dispersion,
    same-month history); ``full=False`` is the upstream scope block (lag, rolling, slope6/12, std/iqr).
    """
    base = shift(x, anchor)
    if full:
        for off in ANCHOR_LAGS_OFFSETS:
            yield f"{v}__l{anchor + off}", shift(x, anchor + off)
    else:
        yield name(f"{v}__l{anchor}"), base
    for w in ROLLING_WINDOWS:
        yield name(f"{v}__roll{w}_mean_asof{anchor}"), rolling(base, w, MIN_PERIODS_BY_WINDOW[w], "mean")
    if full:
        l12, l24 = shift(x, anchor), shift(x, anchor + 12)
        yield f"{v}__l{anchor}_minus_l{anchor + 12}", l12 - l24
        yield f"{v}__l{anchor}_ratio_l{anchor + 12}", safe_divide(l12, l24)
    for w in TREND_WINDOWS if full else SCOPE_TREND_WINDOWS:
        yield name(f"{v}__slope{w}_asof{anchor}"), (base - shift(x, anchor + w - 1)) / max(w - 1, 1)
    if full:
        recent = shift(x, anchor) - shift(x, anchor + 5)
        older = shift(x, anchor + 6) - shift(x, anchor + 11)
        yield f"{v}__accel6_vs_prev6_asof{anchor}", recent / 5 - older / 5
    reducers = ("std", "min", "max", "iqr") if full else ("std", "iqr")
    for r in reducers:
        if r == "iqr":
            val = rolling(base, 12, 6, "q75") - rolling(base, 12, 6, "q25")
        else:
            val = rolling(base, 12, 6, r)
        yield name(f"{v}__roll12_{r}_asof{anchor}"), val
    if full:
        mean, std, rank = same_month_history(x, first_ord)
        sources = {
            "anom": x - mean,
            "pctnormal": safe_divide(x, mean),
            "z": safe_divide(x - mean, std),
            "pctile": rank,
        }
        for suffix, src in sources.items():
            yield f"{v}__hist_same_month_{suffix}_l{anchor}", shift(src, anchor)


def stress_signals(grid: Grid, rules=STRESS_RULES) -> Dict[str, np.ndarray]:
    out = {}
    for signal, source, rule in rules:
        x = grid.values[source]
        with np.errstate(invalid="ignore"):
            out[signal] = np.where(np.isnan(x), np.nan, rule(x).astype(float))
    return out


def stress_families(signal: str, s: np.ndarray, anchor: int, name: Callable[[str], str]) -> Iterator[Tuple[str, np.ndarray]]:
    base = shift(s, anchor)
    yield name(f"{signal}__share12_asof{anchor}"), rolling(base, 12, STRESS_MIN_PERIODS, "mean")
    yield name(f"{signal}__months_since_asof{anchor}"), months_since(base)
    yield name(f"{signal}__longest_run12_asof{anchor}"), longest_run(base)
    yield name(f"{signal}__any12_asof{anchor}"), rolling(base, 12, STRESS_MIN_PERIODS, "max")


def build_neighbors(lat: np.ndarray, lon: np.ndarray, valid: np.ndarray, k: int = N_NEIGHBORS) -> np.ndarray:
    """k nearest valid-coordinate areas by haversine distance (upstream ``build_neighbors``).

    Returns grid-row indices of shape (n_areas, k); rows of invalid areas are 0 and must be masked.
    """
    valid_idx = np.flatnonzero(valid)
    rad = np.radians(np.column_stack([lat[valid_idx], lon[valid_idx]]).astype(float))
    sub = np.empty((len(valid_idx), k), dtype=np.int64)
    for start in range(0, len(valid_idx), 512):
        stop = min(start + 512, len(valid_idx))
        lat1, lon1 = rad[start:stop, 0][:, None], rad[start:stop, 1][:, None]
        a = np.sin((rad[:, 0][None, :] - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(rad[:, 0][None, :]) * np.sin((rad[:, 1][None, :] - lon1) / 2) ** 2
        dist = 2 * 6371.0088 * np.arcsin(np.sqrt(a))
        for local, row in enumerate(dist):
            row[start + local] = np.inf
            nearest = np.argpartition(row, kth=min(k, len(row) - 1))[:k]
            sub[start + local] = nearest[np.argsort(row[nearest])]
    out = np.zeros((len(lat), k), dtype=np.int64)
    out[valid_idx] = valid_idx[sub]
    return out


def neighbor_mean(values: np.ndarray, neighbors: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """Mean of neighbours' values at the same month; areas without valid coordinates get NaN."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        out = np.nanmean(values[neighbors], axis=1)
    out[~valid] = np.nan
    return out


# --------------------------------------------------------------------------- seasonal block


def last_completed_seasons(seasons: pd.DataFrame, area_ids, origin_ords, n_last: int = N_LAST_SEASONS) -> pd.DataFrame:
    """Values of the ``n_last`` latest seasons with ``gs_end_date_exclusive <= first day of origin month + 1``."""
    s = seasons.copy()
    s["end"] = pd.to_datetime(s["gs_end_date_exclusive"])
    s["start"] = pd.to_datetime(s["gs_start_date"])
    s = s.sort_values(["admin_code", "end", "start"], kind="mergesort").reset_index(drop=True)
    s["pos"] = s.groupby("admin_code").cumcount()
    end_month = s["end"] - pd.Timedelta(days=1)
    s["end_ord"] = month_ord(end_month.dt.year, end_month.dt.month)

    keys = pd.DataFrame({"row": np.arange(len(origin_ords)), "admin_code": np.asarray(area_ids), "origin": np.asarray(origin_ords, dtype=np.int64)})
    cut_ord = keys["origin"] + 1
    keys["cutoff"] = pd.to_datetime({"year": cut_ord // 12, "month": cut_ord % 12 + 1, "day": 1})
    keys = keys.sort_values("cutoff", kind="mergesort")
    # stable (end, pos) order: with tied end dates merge_asof must land on the later-starting season
    right = s[["admin_code", "end", "pos"]].sort_values(["end", "pos"], kind="mergesort")
    hit = pd.merge_asof(keys, right, left_on="cutoff", right_on="end", by="admin_code", direction="backward", allow_exact_matches=True)
    hit = hit.sort_values("row").reset_index(drop=True)
    lookup = s.set_index(["admin_code", "pos"])
    out = pd.DataFrame(index=np.arange(len(origin_ords)))
    for k in range(1, n_last + 1):
        pos = hit["pos"] - (k - 1)
        ok = pos.notna() & (pos >= 0)
        idx = pd.MultiIndex.from_arrays([hit.loc[ok, "admin_code"], pos[ok].astype(int)])
        picked = lookup.reindex(idx)
        for v in SEASONAL_VARIABLES:
            col = np.full(len(out), np.nan)
            col[ok.to_numpy()] = picked[v].to_numpy(dtype=float)
            out[f"gs_last{k}__{v}"] = col
        since = np.full(len(out), np.nan)
        since[ok.to_numpy()] = hit.loc[ok, "origin"].to_numpy() - picked["end_ord"].to_numpy()
        out[f"gs_last{k}__months_since_end"] = since
    return out


# --------------------------------------------------------------------------- scope assembly


def scope_suffix(anchor: int, scope_block: bool) -> Callable[[str], str]:
    return (lambda n: f"{n}_s{anchor}") if scope_block else (lambda n: n)


def monthly_feature_stream(grid: Grid, anchor: int, scope_block: bool, neighbors: Optional[np.ndarray], coord_valid: Optional[np.ndarray]) -> Iterator[Tuple[str, np.ndarray]]:
    """All monthly-derived grid features for one block (asof12 if ``scope_block`` is False)."""
    name = scope_suffix(anchor, scope_block)
    for v in MONTHLY_VARIABLES:
        yield from variable_families(v, grid.values[v], anchor, name, not scope_block, grid.first_ord)
    signals = stress_signals(grid)
    for signal, s in signals.items():
        for fname, val in stress_families(signal, s, anchor, name):
            yield fname, val
            if signal == DEFICIT and "__share12_" in fname and neighbors is not None:
                yield f"neighbor3_mean__{fname}", neighbor_mean(val, neighbors, coord_valid)


def gather(values: np.ndarray, index: Tuple[np.ndarray, np.ndarray, np.ndarray]) -> np.ndarray:
    ai, mi, ok = index
    out = values[ai, mi]
    return np.where(ok, out, np.nan)


def build_scope_features(
    grid: Grid,
    seasons: pd.DataFrame,
    keys: pd.DataFrame,
    scope_anchor: Optional[int],
    neighbors: Optional[np.ndarray],
    coord_valid: Optional[np.ndarray],
    context: pd.DataFrame,
) -> Tuple[pd.DataFrame, List[dict]]:
    """New climate features for model rows ``keys`` (area_id, year, month).

    ``scope_anchor`` is 0/3/6 for fs0/fs1/fs2 (adds the scope block) and None for fs3 (asof12 only).
    ``context`` holds the row-aligned scope-file columns used by interactions.
    """
    target_ord = month_ord(keys["year"], keys["month"])
    index = grid.index_of(keys["area_id"].to_numpy(), target_ord)
    cols: Dict[str, np.ndarray] = {}
    manifest: List[dict] = []

    def add(name, values, family, anchor, block):
        if name in cols:
            raise ValueError(f"duplicate feature {name}")
        cols[name] = values
        manifest.append({"feature_name": name, "family": family, "block": block, "latest_source_month": f"t-{anchor}" if anchor else "t"})

    blocks = [(12, False)] + ([(scope_anchor, True)] if scope_anchor is not None else [])
    for anchor, is_scope in blocks:
        block = f"scope_s{anchor}" if is_scope else "asof12"
        for fname, val in monthly_feature_stream(grid, anchor, is_scope, neighbors, coord_valid):
            family = "neighbor" if fname.startswith("neighbor3_mean__") else ("stress" if "_stress__" in fname else "monthly")
            add(fname, gather(val, index), family, anchor, block)

    deficit, veg = f"{DEFICIT}__share12_asof12", f"{VEGETATION}__share12_asof12"
    add(f"{deficit}__x__{veg}", cols[deficit] * cols[veg], "interaction", 12, "asof12")
    add(f"{ENSO_SHARE}__x__{deficit}", context[ENSO_SHARE].to_numpy(dtype=float) * cols[deficit], "interaction", 12, "asof12")
    for modifier in COMPOUND_STATIC_MODIFIERS:
        add(f"{deficit}__x__{modifier}", cols[deficit] * context[modifier].to_numpy(dtype=float), "interaction", 12, "asof12")
    if scope_anchor is not None:
        s = scope_anchor
        for v, modifier in SCOPE_INTERACTIONS:
            left = f"{v}__l{s}_s{s}"
            add(f"{left}__x__{modifier}_s{s}", cols[left] * context[modifier].to_numpy(dtype=float), "interaction", s, f"scope_s{s}")

    season_anchor = scope_anchor if scope_anchor is not None else 12
    seasonal = last_completed_seasons(seasons, keys["area_id"].to_numpy(), target_ord - season_anchor)
    suffix = f"_asof{season_anchor}" + (f"_s{season_anchor}" if scope_anchor is not None else "")
    for c in seasonal.columns:
        add(f"{c}{suffix}", seasonal[c].to_numpy(), "seasonal", season_anchor, "seasonal")
    return pd.DataFrame(cols, index=keys.index), manifest
