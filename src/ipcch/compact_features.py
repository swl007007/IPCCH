"""compact_climate_weather_oracle_v1: compact origin-aligned climate/context features plus the raw weather oracle.

Contract (task ``10-08-compact-climate-weather-oracle``, ``design.md``):

- Row origin ``O = T - H`` (dense month ordinals); every monthly dynamic recipe is built directly at ``O`` on a keyed
  area x month grid (D16): no carrier-row (``O+12``) masks and no saved-extra-NA copies. Source-native NA stays NA.
- 24 ordinary sources: value, MA3/MA6/MA12 (minimum 2/3/6 valid) and sample SD12 (minimum 6) at ``O``; windows are
  reduced per window (``trailing``), not with pandas' running sums.
- 14 same-month-z sources: monthly ``z[u]`` against strictly earlier years of the same calendar month (>= 2 values,
  non-zero sample SD), then z at ``O`` and MA3/MA6/MA12 of the monthly z. Means/SDs are shift-centred two-pass
  statistics (``trailing``, ``same_month_z``) so constant data give exact zero spread and near-constant data keep
  their relative accuracy.
- Seven stress signals with the inherited rules (D14) and share12 / months_since / longest_run12 / any12 at ``O``.
- Two latest completed growing seasons (``end_exclusive <= first day of O+1``) and a calendar-duration major dummy
  for the latest one; one selection ledger drives both.
- Raw oracle (oracle arm, H3/H6/H12 only): realized ``prcp_anom`` / ``tmean_anom`` at ``O+1 .. O+min(H, 6)``.
- Background (static, coordinates/target calendar, safe IPC history, national IDP) is inherited unchanged from the
  parent ``origin_safe_climate_idp_v1`` inputs.
"""
from __future__ import annotations

import warnings
from typing import Dict, Iterator, List, Mapping, Sequence, Tuple

import numpy as np
import pandas as pd

from ipcch import climate2015_features as cf
from ipcch import origin_safe as osf
from ipcch import retained_feature_recipes as rr
from ipcch import weather_oracle as wo

VERSION = "compact_climate_weather_oracle_v1"
PARENT_VERSION = wo.PARENT_VERSION
PARENT_ARM = wo.PARENT_ARM
LEGACY_NAMESPACES = (wo.PARENT_VERSION, wo.ORACLE_VERSION)
BASELINE_ARM = "compact_baseline"
ORACLE_ARM = "compact_weather_oracle"
ARMS = (BASELINE_ARM, ORACLE_ARM)
ARM_HORIZONS = {BASELINE_ARM: (0, 3, 6, 12), ORACLE_ARM: wo.ORACLE_HORIZONS}
RUN_PLAN = tuple((arm, h) for arm in ARMS for h in ARM_HORIZONS[arm])

COMPOSITES = tuple(f"{g}__composite_mean" for g in rr.COMPOSITES)
INTERIM_SOURCES = ("GPP_mean", "nightlight_mean", "event_count_violence", "sum_fatalities_violence", "WFP_Price",
                   "food_price_index_WB", rr.ENSO, *COMPOSITES)
CLIMATE_BASES = tuple(b for b in cf.CLIMATE_BASES if b != "ndvi_anom")
CLIMATE_SOURCES = tuple(f"{b}_month_ensmean" for b in CLIMATE_BASES)
ORDINARY_SOURCES = INTERIM_SOURCES + CLIMATE_SOURCES
Z_SOURCES = ("GPP_mean", "nightlight_mean", "WFP_Price", "food_price_index_WB", rr.ENSO,
             *(f"{b}_month_ensmean" for b in ("prcp_anom", "rainy_days", "cdd", "tmean_anom", "tmax_anom", "hot_days_p95",
                                              "gdd", "edd", "evi_anom")))
INTERIM_STRESS_SOURCES = ("GPP_mean", "event_count_violence", "WFP_Price", rr.ENSO)
STRESS_STEMS = ("GPP_mean__vegetation_stress", "event_count_violence__nonzero_stress", "WFP_Price__price_shock_stress",
                "nino34_anom__enso_stress", cf.DEFICIT, cf.HOT, cf.VEGETATION)
SEASON_METRICS = tuple(f"{b}_gs_ensmean" for b in CLIMATE_BASES)
MA_WINDOWS = (3, 6, 12)
MIN_PERIODS = {3: 2, 6: 3, 12: 6}
SD_WINDOW, SD_MIN_PERIODS = 12, 6
N_SEASONS = 2
MAJOR = "gs_last1__is_major_at_origin"

# list_sha256 of the frozen fitted order per run (expected_run_index.csv of the approved contract)
FROZEN_FEATURE_SHA256 = {
    (BASELINE_ARM, 0): "e97388f848e7095bf0535f0cfee1a2d798e0c1863dee843462e60cf6a36f9909",
    (BASELINE_ARM, 3): "e97388f848e7095bf0535f0cfee1a2d798e0c1863dee843462e60cf6a36f9909",
    (BASELINE_ARM, 6): "e97388f848e7095bf0535f0cfee1a2d798e0c1863dee843462e60cf6a36f9909",
    (BASELINE_ARM, 12): "e97388f848e7095bf0535f0cfee1a2d798e0c1863dee843462e60cf6a36f9909",
    (ORACLE_ARM, 3): "ce99f6a8af46278f6faf9e60f8a631efae6c5a55e6be025dd0bcfadb1b959e9a",
    (ORACLE_ARM, 6): "3e54c4496d92a76df4f99246a5e9117eccce8ee80a9e3eb8d2d9778c817a2a3e",
    (ORACLE_ARM, 12): "3e54c4496d92a76df4f99246a5e9117eccce8ee80a9e3eb8d2d9778c817a2a3e",
}
EXPECTED_COUNTS = {"static": 29, "ordinary": 120, "same_month_z": 56, "stress": 28, "growing_season": 29,
                   "identifier": 27, "history": 5, "idp": 2}
# frozen numerical runtime, configs and approved contract bytes (design.md; execution-approval.json)
FROZEN_RUNTIME = {"python": "3.12.3", "numpy": "2.4.4", "pandas": "3.0.3", "sklearn": "1.8.0", "xgboost": "3.2.0"}
FROZEN_CONFIG_SHA256 = {"forecasting_hyperparameters.json": "3742300661466f22eba8198e5d4f9c2a277615ba59562fbf27f251ecc932dd76",
                        "forecasting_hyperparameters_p3.json": "cdc0e55aa15bdda932465088568b9ee717d226208ffb32076f438fb274e6317b"}
FROZEN_CONTRACT_SHA256 = {"expected_feature_contract.csv": "a2d1960bf75811a391ec4bd0549b4aaddccb1ce57ca9a08f3a3c28d2fb313bc8",
                          "expected_feature_contract_metadata.json": "8f3964364f89b866fc40f31524d38312aaab3202ca02f3886b5b64ade33e1260",
                          "expected_run_index.csv": "fdd65bc2005016f721995c173a28bcea59ec4580b42c70a43bbf7632b3a4097d"}
# helper modules whose bytes must equal the input build (manifest code_sha256) when a compact run is gated/fitted
HELPER_MODULES = ("src/ipcch/compact_features.py", "src/ipcch/climate2015_features.py", "src/ipcch/retained_feature_recipes.py",
                  "src/ipcch/weather_oracle.py", "src/ipcch/origin_safe.py")
# code whose bytes enter every compact run fingerprint (fit_model and the batch loop live in the runner)
FIT_CODE = (*HELPER_MODULES, "src/ipcch/forecasting_weight_decay.py", "scripts/modeling/run_deep_feature_weight_decay_forecasting.py")


# --------------------------------------------------------------------------- names and schema


def ordinary_names(source: str) -> List[str]:
    return [f"{source}__value_at_origin", *(f"{source}__ma{w}_at_origin" for w in MA_WINDOWS), f"{source}__sd12_at_origin"]


def z_names(source: str) -> List[str]:
    return [f"{source}__hist_same_month_z_at_origin", *(f"{source}__hist_same_month_z_ma{w}_at_origin" for w in MA_WINDOWS)]


def stress_names(stem: str) -> List[str]:
    return [f"{stem}__{s}_at_origin" for s in ("share12", "months_since", "longest_run12", "any12")]


def season_names() -> List[str]:
    out = []
    for k in range(1, N_SEASONS + 1):
        out += [f"gs_last{k}__{m}__at_origin" for m in SEASON_METRICS] + [f"gs_last{k}__months_since_end_at_origin"]
    return out + [MAJOR]


def dynamic_features() -> List[str]:
    """Ordinary (source-major) -> same-month z -> stress (signal-major) -> seasons + major dummy (233 columns)."""
    return ([n for s in ORDINARY_SOURCES for n in ordinary_names(s)] + [n for s in Z_SOURCES for n in z_names(s)]
            + [n for s in STRESS_STEMS for n in stress_names(s)] + season_names())


def background_groups(parent_features: Sequence[str]) -> Dict[str, List[str]]:
    """Static, identifier (coordinates + target calendar), safe history and IDP literals in the parent's relative order."""
    groups = {
        "static": [c for c in parent_features if rr.is_static_name(c)],
        "identifier": [c for c in parent_features if c in ("lat", "lon") or c.startswith(("month_", "year_"))],
        "history": [c for c in parent_features if c in osf.HISTORY_FEATURES],
        "idp": [c for c in parent_features if c in osf.IDP_FEATURES],
    }
    for name, cols in groups.items():
        if len(cols) != EXPECTED_COUNTS[name]:
            raise ValueError(f"parent {name} block has {len(cols)} columns, expected {EXPECTED_COUNTS[name]}")
    if groups["history"] != list(osf.HISTORY_FEATURES) or groups["idp"] != list(osf.IDP_FEATURES):
        raise ValueError("parent history/IDP literals differ from the origin-safe definitions")
    return groups


def oracle_features(horizon: int) -> List[str]:
    return wo.raw_features(horizon)


def run_features(parent_features: Sequence[str], arm: str, horizon: int) -> List[str]:
    """Exact fitted order: static29 -> dynamic233 -> identifier27 -> history5 -> IDP2 (+ raw oracle)."""
    if arm not in ARMS or int(horizon) not in ARM_HORIZONS[arm]:
        raise ValueError(f"{VERSION} has no run {arm} H={horizon}; plan is {RUN_PLAN}")
    g = background_groups(parent_features)
    features = g["static"] + dynamic_features() + g["identifier"] + g["history"] + g["idp"]
    if arm == ORACLE_ARM:
        features += oracle_features(horizon)
    if len(set(features)) != len(features):
        raise ValueError("duplicate feature names in the compact schema")
    if osf.list_sha256(features) != FROZEN_FEATURE_SHA256[(arm, int(horizon))]:
        raise ValueError(f"{arm} H={horizon}: feature order differs from the frozen contract")
    return features


# --------------------------------------------------------------------------- source grids


def composite_frame(panel: pd.DataFrame, members: Mapping[str, Sequence[str]]) -> pd.DataFrame:
    """Arithmetic mean of the non-missing numeric pinned members per area/month (NaN if all missing)."""
    if tuple(members) != rr.COMPOSITES:
        raise ValueError(f"composite groups {list(members)} differ from {rr.COMPOSITES}")
    out = panel.loc[:, list(osf.KEYS)].copy()
    for group, cols in members.items():
        out[f"{group}__composite_mean"] = panel[list(cols)].apply(pd.to_numeric, errors="coerce").mean(axis=1, skipna=True)
    return out


def interim_grid(panel: pd.DataFrame, members: Mapping[str, Sequence[str]]) -> cf.Grid:
    """Keyed grid of the 11 interim sources; months outside an area's contiguous span are NaN (no shifting)."""
    work = pd.concat([panel.loc[:, list(osf.KEYS) + list(INTERIM_SOURCES[:7])].reset_index(drop=True),
                      composite_frame(panel, members).drop(columns=list(osf.KEYS)).reset_index(drop=True)], axis=1)
    return cf.Grid.from_long(work, INTERIM_SOURCES, require_complete=False)


# --------------------------------------------------------------------------- monthly recipes (full grid, at each month)


def trailing(x: np.ndarray, window: int, min_periods: int, reducer: str) -> np.ndarray:
    """Trailing calendar-month window ending at each column, reduced from each window's own values (NaN-skipping).

    Not pandas' running add/remove sums, whose cancellation residue survives after a large value leaves the window
    (e.g. a 12-month constant WFP window got SD 5.6e-6). ``mean``/``std`` are shift-centred two-pass statistics: values
    are first expressed relative to the window minimum (exact for nearby floats), so a constant window has mean equal
    to its value and sample SD (ddof 1) exactly 0, and near-constant windows keep their relative accuracy.
    """
    n_areas, n_months = x.shape
    padded = np.concatenate([np.full((n_areas, window - 1), np.nan), x], axis=1)
    win = np.lib.stride_tricks.sliding_window_view(padded, window, axis=1)
    count = np.sum(~np.isnan(win), axis=2)
    enough = count >= min_periods
    with np.errstate(invalid="ignore", divide="ignore"), warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        if reducer == "max":
            out = np.nanmax(win, axis=2)
        elif reducer in ("mean", "std"):
            ref = np.nanmin(win, axis=2)
            d = win - ref[..., None]
            mean_d = np.nansum(d, axis=2) / count
            if reducer == "mean":
                out = ref + mean_d
            else:
                out = np.sqrt(np.nansum((d - mean_d[..., None]) ** 2, axis=2) / (count - 1))
        else:
            raise ValueError(f"unknown reducer {reducer}")
    return np.where(enough, out, np.nan)


def same_month_z(x: np.ndarray, first_ord: int) -> np.ndarray:
    """z[u] = (x[u] - mean(P[u])) / sd(P[u], ddof=1); P[u] = strictly earlier years of u's calendar month.

    NaN when x[u] is missing, fewer than two prior values, or the prior values are all identical (zero SD, tested
    exactly). Mean, SD and the numerator are computed relative to the series' first observed value of that calendar
    month (shift-centred two-pass): with an uncentred float mean, near-constant histories such as seven 30.0 and one
    29.99999999999999 lose most significant digits (z -2.65 or -2.83 instead of the exact -2.47).
    """
    lead = first_ord % 12
    n_areas, n_months = x.shape
    n_years = -(-(lead + n_months) // 12)
    padded = np.full((n_areas, n_years * 12), np.nan)
    padded[:, lead : lead + n_months] = x
    cube = padded.reshape(n_areas, n_years, 12)
    has = ~np.isnan(cube)
    first = np.argmax(has, axis=1)
    ref = np.take_along_axis(cube, first[:, None, :], axis=1)[:, 0, :]
    d = cube - ref[:, None, :]
    z = np.full_like(cube, np.nan)
    with np.errstate(invalid="ignore", divide="ignore"), warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        for y in range(1, n_years):
            prior = d[:, :y, :]
            count = np.sum(~np.isnan(prior), axis=1)
            mean_d = np.nansum(prior, axis=1) / count
            sd = np.sqrt(np.nansum((prior - mean_d[:, None, :]) ** 2, axis=1) / (count - 1))
            constant = np.nanmax(prior, axis=1) == np.nanmin(prior, axis=1)
            ok = (count >= 2) & ~constant & (sd > 0) & ~np.isnan(d[:, y, :])
            z[:, y, :] = np.where(ok, (d[:, y, :] - mean_d) / sd, np.nan)
    return z.reshape(n_areas, n_years * 12)[:, lead : lead + n_months]


def ordinary_arrays(source: str, x: np.ndarray) -> Iterator[Tuple[str, np.ndarray]]:
    names = ordinary_names(source)
    yield names[0], x
    for name, w in zip(names[1:4], MA_WINDOWS):
        yield name, trailing(x, w, MIN_PERIODS[w], "mean")
    yield names[4], trailing(x, SD_WINDOW, SD_MIN_PERIODS, "std")


def z_arrays(source: str, x: np.ndarray, first_ord: int) -> Iterator[Tuple[str, np.ndarray]]:
    z = same_month_z(x, first_ord)
    names = z_names(source)
    yield names[0], z
    for name, w in zip(names[1:], MA_WINDOWS):
        yield name, trailing(z, w, MIN_PERIODS[w], "mean")


def stress_signal_arrays(interim: cf.Grid, climate: cf.Grid) -> Dict[str, Tuple[cf.Grid, np.ndarray]]:
    """Monthly 0/1/NaN signals with the inherited rules (``rr.stress_signal`` and ``cf.STRESS_RULES``)."""
    out: Dict[str, Tuple[cf.Grid, np.ndarray]] = {}
    for source in INTERIM_STRESS_SOURCES:
        name, s = rr.stress_signal(source, interim.values[source])
        out[name] = (interim, s)
    for name, s in cf.stress_signals(climate).items():
        out[name] = (climate, s)
    if tuple(out) != STRESS_STEMS:
        raise AssertionError(f"stress signal order {list(out)} differs from {STRESS_STEMS}")
    return out


def stress_arrays(stem: str, s: np.ndarray) -> Iterator[Tuple[str, np.ndarray]]:
    names = stress_names(stem)
    yield names[0], trailing(s, 12, cf.STRESS_MIN_PERIODS, "mean")
    yield names[1], cf.months_since(s)
    yield names[2], cf.longest_run(s)
    yield names[3], trailing(s, 12, cf.STRESS_MIN_PERIODS, "max")


def monthly_feature_arrays(interim: cf.Grid, climate: cf.Grid) -> Iterator[Tuple[str, cf.Grid, np.ndarray]]:
    """(name, grid, full-grid array) in contract order; the value at column ``u`` uses source months ``<= u`` only."""
    grids = {s: (interim if s in INTERIM_SOURCES else climate) for s in ORDINARY_SOURCES}
    for s in ORDINARY_SOURCES:
        for name, arr in ordinary_arrays(s, grids[s].values[s]):
            yield name, grids[s], arr
    for s in Z_SOURCES:
        for name, arr in z_arrays(s, grids[s].values[s], grids[s].first_ord):
            yield name, grids[s], arr
    for stem, (grid, s) in stress_signal_arrays(interim, climate).items():
        for name, arr in stress_arrays(stem, s):
            yield name, grid, arr


def monthly_block(interim: cf.Grid, climate: cf.Grid, keys: pd.DataFrame, horizons: Sequence[int]) -> Dict[int, pd.DataFrame]:
    """Ordinary, z and stress columns for each horizon's rows, gathered at the calendar month O = T - H."""
    target = osf.month_ord(keys["year"], keys["month"])
    area = keys["area_id"].to_numpy()
    index = {(id(g), h): g.index_of(area, target - h) for g in (interim, climate) for h in horizons}
    cols: Dict[int, Dict[str, np.ndarray]] = {h: {} for h in horizons}
    for name, grid, arr in monthly_feature_arrays(interim, climate):
        for h in horizons:
            cols[h][name] = cf.gather(arr, index[(id(grid), h)])
    return {h: pd.DataFrame(c) for h, c in cols.items()}


# --------------------------------------------------------------------------- growing seasons


def season_major_flags(seasons: pd.DataFrame) -> pd.Series:
    """Per source row: 1 if uniquely longer than its same-area/same-season_year partner, 0 if shorter, NaN otherwise.

    Duration = end_exclusive - start in calendar days (fixed calendar, not realized weather or support days).
    """
    start = pd.to_datetime(seasons["gs_start_date"], errors="coerce")
    end = pd.to_datetime(seasons["gs_end_date_exclusive"], errors="coerce")
    days = (end - start).dt.days.astype(float)
    days = days.where(days > 0)
    frame = pd.DataFrame({"admin_code": seasons["admin_code"].to_numpy(), "season_year": seasons["season_year"].to_numpy(),
                          "season": seasons["season"].to_numpy(), "days": days.to_numpy()})
    grp = frame.groupby(["admin_code", "season_year"], sort=False)
    pair = (grp["season"].transform("size") == 2) & (grp["season"].transform("nunique") == 2) \
        & frame.assign(ok=frame["season"].isin(["s1", "s2"])).groupby(["admin_code", "season_year"], sort=False)["ok"].transform("all")
    other = grp["days"].transform("sum") - frame["days"]
    comparable = pair & (grp["days"].transform("count") == 2)
    flag = np.where(frame["days"] > other, 1.0, np.where(frame["days"] < other, 0.0, np.nan))
    return pd.Series(np.where(comparable, flag, np.nan), index=seasons.index, name="is_major")


def completed_seasons(seasons: pd.DataFrame, area_ids, origin_ords) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Latest two completed seasons (``end_exclusive <= first day of O+1``) per row: features and selection ledger.

    Same stable selection as ``climate2015_features.last_completed_seasons`` (sorted by end then start, the
    later-starting season wins a tied end, source order for residual ties), but it keeps the selected season
    identity so the major dummy and the metrics come from one lookup.
    """
    s = seasons.copy()
    s["is_major"] = season_major_flags(s).to_numpy()
    s["end"] = pd.to_datetime(s["gs_end_date_exclusive"])
    s["start"] = pd.to_datetime(s["gs_start_date"])
    s["duration_days"] = (s["end"] - s["start"]).dt.days
    s = s.sort_values(["admin_code", "end", "start"], kind="mergesort").reset_index(drop=True)
    s["pos"] = s.groupby("admin_code").cumcount()
    end_month = s["end"] - pd.Timedelta(days=1)
    s["end_ord"] = osf.month_ord(end_month.dt.year, end_month.dt.month)
    origin = np.asarray(origin_ords, dtype=np.int64)
    keys = pd.DataFrame({"row": np.arange(len(origin)), "admin_code": np.asarray(area_ids), "origin": origin})
    cut_ord = keys["origin"] + 1
    keys["cutoff"] = pd.to_datetime({"year": cut_ord // 12, "month": cut_ord % 12 + 1, "day": 1})
    keys = keys.sort_values("cutoff", kind="mergesort")
    right = s[["admin_code", "end", "pos"]].sort_values(["end", "pos"], kind="mergesort")
    hit = pd.merge_asof(keys, right, left_on="cutoff", right_on="end", by="admin_code", direction="backward", allow_exact_matches=True)
    hit = hit.sort_values("row").reset_index(drop=True)
    lookup = s.set_index(["admin_code", "pos"])
    feats: Dict[str, np.ndarray] = {}
    ledger = pd.DataFrame({"origin_ord": origin, "season_cutoff_date": hit["cutoff"].dt.strftime("%Y-%m-%d").to_numpy()})
    for k in range(1, N_SEASONS + 1):
        pos = hit["pos"] - (k - 1)
        ok = (pos.notna() & (pos >= 0)).to_numpy()
        idx = pd.MultiIndex.from_arrays([hit.loc[ok, "admin_code"], pos[ok].astype(int)])
        picked = lookup.reindex(idx)
        for m in SEASON_METRICS:
            col = np.full(len(origin), np.nan)
            col[ok] = picked[m].to_numpy(dtype=float)
            feats[f"gs_last{k}__{m}__at_origin"] = col
        since = np.full(len(origin), np.nan)
        since[ok] = origin[ok] - picked["end_ord"].to_numpy()
        feats[f"gs_last{k}__months_since_end_at_origin"] = since
        for field, src, kind in (("season_year", "season_year", float), ("season", "season", object), ("start", "gs_start_date", object),
                                 ("end_exclusive", "gs_end_date_exclusive", object), ("end_ord", "end_ord", float),
                                 ("duration_days", "duration_days", float), ("is_major", "is_major", float)):
            col = np.full(len(origin), np.nan if kind is float else None, dtype=kind)
            col[ok] = picked[src].to_numpy()
            ledger[f"gs_last{k}_{field}"] = col
    feats[MAJOR] = ledger["gs_last1_is_major"].to_numpy(dtype=float)
    out = pd.DataFrame(feats)
    if list(out.columns) != season_names():
        raise AssertionError("season block order differs from the contract")
    return out, ledger


def assert_season_ledger(frame: pd.DataFrame, ledger: pd.DataFrame, horizon: int) -> Dict[str, int]:
    """CLI gate: season ages/major come from the ledger's selected seasons, all completed by the first day of O+1."""
    origin = osf.month_ord(frame["year"], frame["month"]) - horizon
    if len(ledger) != len(frame) or not np.array_equal(ledger["area_id"].to_numpy(), frame["area_id"].to_numpy()) \
            or not np.array_equal(ledger["origin_ord"].to_numpy(dtype=np.int64), origin):
        raise ValueError("season ledger rows do not align with the dataset rows or the run horizon")
    cutoff = pd.to_datetime(ledger["season_cutoff_date"])
    expected_cut = pd.to_datetime({"year": (origin + 1) // 12, "month": (origin + 1) % 12 + 1, "day": 1})
    if not (cutoff.to_numpy() == expected_cut.to_numpy()).all():
        raise ValueError("season ledger cutoff is not the first day of O+1")
    for k in range(1, N_SEASONS + 1):
        has = ledger[f"gs_last{k}_end_ord"].notna().to_numpy()
        end = pd.to_datetime(ledger.loc[has, f"gs_last{k}_end_exclusive"])
        if (end.to_numpy() > cutoff[has].to_numpy()).any():
            raise ValueError(f"gs_last{k}: selected season ends after the first day of O+1")
        since = frame[f"gs_last{k}__months_since_end_at_origin"].to_numpy(dtype=float)
        if not np.array_equal(np.isfinite(since), has) or not np.array_equal(since[has], origin[has] - ledger.loc[has, f"gs_last{k}_end_ord"].to_numpy(dtype=float)):
            raise ValueError(f"gs_last{k} months_since_end differs from the season ledger")
        for m in SEASON_METRICS:
            if frame.loc[~has, f"gs_last{k}__{m}__at_origin"].notna().any():
                raise ValueError(f"gs_last{k}__{m}: value without a selected season")
    if not np.array_equal(frame[MAJOR].to_numpy(dtype=float), ledger["gs_last1_is_major"].to_numpy(dtype=float), equal_nan=True):
        raise ValueError(f"{MAJOR} differs from the selected latest season's ledger classification")
    return {"rows": len(frame)}


# --------------------------------------------------------------------------- raw oracle


def raw_oracle_block(grid: cf.Grid, keys: pd.DataFrame, horizon: int) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Realized prcp/tmean anomalies at O+1..O+min(H, 6) by calendar month, and the availability ledger."""
    m = wo.window(horizon)
    work = keys.loc[:, list(osf.KEYS)].reset_index(drop=True)
    target = osf.month_ord(work["year"], work["month"])
    origin = target - horizon
    area = work["area_id"].to_numpy()
    cols: Dict[str, np.ndarray] = {}
    for k in range(1, m + 1):
        values = wo.calendar_lookup(grid, area, origin + k)
        for v in wo.ORACLE_VARIABLES:
            cols[wo.raw_name(v, k)] = values[v]
    block = pd.DataFrame(cols)
    if list(block.columns) != oracle_features(horizon):
        raise AssertionError("raw oracle order differs from the contract")
    ledger = work.copy()
    ledger["horizon"] = horizon
    ledger["target_ord"] = target
    ledger["origin_ord"] = origin
    ledger["assumed_forecast_available_ord"] = origin
    ledger["future_obs_first_ord"] = origin + 1
    ledger["future_obs_last_ord"] = origin + m
    ledger["assumed_forecast_available_month"] = [osf.ord_label(o) for o in origin]
    ledger["future_obs_months"] = [f"{osf.ord_label(o + 1)}..{osf.ord_label(o + m)}" for o in origin]
    for v in wo.ORACLE_VARIABLES:
        ledger[f"{v}__future_finite_months"] = np.isfinite(block[[wo.raw_name(v, k) for k in range(1, m + 1)]].to_numpy()).sum(axis=1)
    return block, ledger


def assert_oracle_ledger(frame: pd.DataFrame, ledger: pd.DataFrame, horizon: int) -> Dict[str, int]:
    """CLI gate: oracle columns are exactly the declared window O+1..O+min(H,6) recorded in the ledger."""
    m = wo.window(horizon)
    target = osf.month_ord(frame["year"], frame["month"])
    if len(ledger) != len(frame) or not np.array_equal(ledger["area_id"].to_numpy(), frame["area_id"].to_numpy()) \
            or not np.array_equal(ledger["target_ord"].to_numpy(dtype=np.int64), target):
        raise ValueError("oracle ledger rows do not align with the dataset rows")
    if (ledger["horizon"] != horizon).any():
        raise ValueError("oracle ledger horizon disagrees with the run horizon")
    origin = target - horizon
    expected = {"origin_ord": origin, "assumed_forecast_available_ord": origin, "future_obs_first_ord": origin + 1,
                "future_obs_last_ord": origin + m}
    for column, values in expected.items():
        if not np.array_equal(ledger[column].to_numpy(dtype=np.int64), values):
            raise ValueError(f"oracle ledger {column} is not the declared weather window for H={horizon}")
    for v in wo.ORACLE_VARIABLES:
        finite = np.isfinite(frame[[wo.raw_name(v, k) for k in range(1, m + 1)]].to_numpy(dtype=float)).sum(axis=1)
        if not np.array_equal(finite, ledger[f"{v}__future_finite_months"].to_numpy()):
            raise ValueError(f"{v}: raw oracle columns disagree with the ledger finite-month counts")
    return {"rows": len(frame)}


# --------------------------------------------------------------------------- frozen identities and run fingerprint


def runtime_identity() -> Dict[str, str]:
    import platform
    import sys

    import sklearn
    import xgboost

    return {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__, "sklearn": sklearn.__version__,
            "xgboost": xgboost.__version__, "executable": sys.executable, "python_build": sys.version}


def assert_frozen_environment(manifest: Mapping[str, object], project_root, config_dir) -> Dict[str, object]:
    """Compact gate: frozen runtime/configs, helper bytes equal to the input build, pinned sources/cohort/contract."""
    from pathlib import Path

    runtime = runtime_identity()
    drift = {k: (runtime[k], v) for k, v in FROZEN_RUNTIME.items() if runtime[k] != v}
    if drift:
        raise ValueError(f"numerical runtime differs from the frozen versions: {drift}")
    for name, digest in FROZEN_CONFIG_SHA256.items():
        if osf.file_sha256(Path(config_dir) / name) != digest:
            raise ValueError(f"config {name} differs from the frozen sha256")
    recorded = manifest.get("code_sha256", {})
    for rel in HELPER_MODULES:
        if rel not in recorded or osf.file_sha256(Path(project_root) / rel) != recorded[rel]:
            raise ValueError(f"helper {rel} differs from the code that built the compact inputs")
    for label, item in [*(("source " + k, v) for k, v in manifest["sources"].items()), ("cohort", manifest["cohort"]),
                        *(("contract " + k, v) for k, v in manifest["contract"]["files"].items())]:
        if osf.file_sha256(item["path"]) != item["sha256"]:
            raise ValueError(f"{label} sha256 differs from the compact manifest: {item['path']}")
    if {k: v["sha256"] for k, v in manifest["contract"]["files"].items()} != FROZEN_CONTRACT_SHA256:
        raise ValueError("compact manifest does not bind the approved contract bytes")
    return runtime


def fingerprint_payload(manifest: Mapping[str, object], manifest_sha256: str, arm: str, horizon: int, params: Mapping[str, object],
                        helper_sha256: Mapping[str, str], runtime: Mapping[str, str]) -> Dict[str, object]:
    """Canonical identity of one compact run; the CLI and the verifier build it from the same fields."""
    entry = manifest["horizons"][str(horizon)]
    arm_entry = entry["arms"][arm]
    return {
        "version": VERSION, "arm": arm, "horizon": int(horizon), "manifest_sha256": manifest_sha256,
        "dataset_sha256": arm_entry["dataset"]["sha256"], "feature_sha256": arm_entry["feature_sha256"],
        "frozen_feature_sha256": FROZEN_FEATURE_SHA256[(arm, int(horizon))],
        "ledgers_sha256": {k: entry[k]["sha256"] for k in ("history_ledger", "idp_ledger", "season_ledger")
                           } | ({"oracle_ledger": entry["oracle_ledger"]["sha256"]} if arm == ORACLE_ARM else {}),
        "parent_manifest_sha256": manifest["parent_manifest"]["sha256"],
        "sources_sha256": {k: v["sha256"] for k, v in manifest["sources"].items()}, "cohort_sha256": manifest["cohort"]["sha256"],
        "contract_sha256": {k: v["sha256"] for k, v in manifest["contract"]["files"].items()},
        "build_code_sha256": dict(manifest["code_sha256"]), "helper_sha256": dict(helper_sha256),
        "hyperparameters_sha256": list(FROZEN_CONFIG_SHA256.values()), "xgboost": runtime["xgboost"], "runtime": dict(runtime),
        "params": {k: params[k] for k in ("seed", "half_life_months", "phase_threshold", "n_jobs")},
    }


def fit_code_sha256(project_root) -> Dict[str, str]:
    from pathlib import Path

    return {rel: osf.file_sha256(Path(project_root) / rel) for rel in FIT_CODE}
