"""Fidelity gate for the climate2015 fork: recompute old FLDAS families with the forked helpers and
compare them with the values saved in the current fs0 (scope 0m) model-ready file.

Upstream stress rules are plugged in here (ratio to the prior-year same month), so a match shows the
forked family code reproduces the upstream recipe; the climate2015 build only swaps inputs/thresholds.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = next(path for path in Path(__file__).resolve().parents if (path / "src").exists())
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import numpy as np
import pandas as pd

from ipcch import climate2015_features as cf
from ipcch import paths

OLD_VARIABLES = ("Rainf_f_tavg_mean", "Tair_f_tavg_mean", "EVI_mean")
INTERIM = paths.SOURCE_DATA_DIR / "assembled_IPCCH" / "interim" / "IPCCH_2026_target_corrected_nino34_wbfood.csv"


def upstream_signals(grid: cf.Grid) -> dict:
    out = {}
    rules = {
        "Rainf_f_tavg_mean": ("deficit_stress", lambda x, p: x < p * 0.8),
        "Tair_f_tavg_mean": ("hot_stress", lambda x, p: x > p),
        "EVI_mean": ("vegetation_stress", lambda x, p: x < p * 0.9),
    }
    for v, (suffix, rule) in rules.items():
        x = grid.values[v]
        with np.errstate(invalid="ignore"):
            out[f"{v}__{suffix}"] = np.where(np.isnan(x), np.nan, rule(x, cf.shift(x, 12)).astype(float))
    return out


def recompute(grid: cf.Grid, lat: np.ndarray, lon: np.ndarray, valid: np.ndarray):
    neighbors = cf.build_neighbors(lat, lon, valid)
    signals = upstream_signals(grid)
    for anchor, is_scope in ((12, False), (0, True)):
        name = cf.scope_suffix(anchor, is_scope)
        for v in OLD_VARIABLES:
            yield from cf.variable_families(v, grid.values[v], anchor, name, not is_scope, grid.first_ord)
        for signal, s in signals.items():
            for fname, val in cf.stress_families(signal, s, anchor, name):
                yield fname, val
                if signal.startswith("Rainf") and "__share12_" in fname:
                    yield f"neighbor3_mean__{fname}", cf.neighbor_mean(val, neighbors, valid)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--interim", default=str(INTERIM))
    parser.add_argument("--fs0", default=str(paths.external_path("deep_features_scope_0m_model_ready_dataset")))
    parser.add_argument("--sample-areas", type=int, default=400)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--rtol", type=float, default=1e-6)
    parser.add_argument("--out", required=True, help="CSV path for the per-feature fidelity report")
    args = parser.parse_args()

    raw = pd.read_csv(args.interim, usecols=["admin_code", "year", "month", "lat", "lon", *OLD_VARIABLES])
    raw = raw.rename(columns={"admin_code": "area_id"})
    grid = cf.Grid.from_long(raw, OLD_VARIABLES, require_complete=False)
    coord = raw.groupby("area_id")[["lat", "lon"]].mean().reindex(grid.area_ids)
    valid = coord["lat"].between(-90, 90).to_numpy() & coord["lon"].between(-180, 180).to_numpy()

    header = pd.read_csv(args.fs0, nrows=0).columns
    fs0 = pd.read_csv(args.fs0, usecols=lambda c: c in {"area_id", "year", "month"} or any(v in c for v in OLD_VARIABLES) or c in {"popdensity", "market_access", cf.ENSO_SHARE})
    rng = np.random.default_rng(args.seed)
    areas = rng.choice(fs0["area_id"].unique(), size=min(args.sample_areas, fs0["area_id"].nunique()), replace=False)
    fs0 = fs0[fs0["area_id"].isin(areas)].reset_index(drop=True)
    index = grid.index_of(fs0["area_id"].to_numpy(), cf.month_ord(fs0["year"], fs0["month"]))

    rows, computed = [], {}
    for fname, val in recompute(grid, coord["lat"].to_numpy(), coord["lon"].to_numpy(), valid):
        computed[fname] = cf.gather(val, index)
    deficit, veg = "Rainf_f_tavg_mean__deficit_stress__share12_asof12", "EVI_mean__vegetation_stress__share12_asof12"
    computed[f"{deficit}__x__{veg}"] = computed[deficit] * computed[veg]
    computed[f"{cf.ENSO_SHARE}__x__{deficit}"] = fs0[cf.ENSO_SHARE].to_numpy(dtype=float) * computed[deficit]
    for m in ("popdensity", "market_access"):
        computed[f"{deficit}__x__{m}"] = computed[deficit] * fs0[m].to_numpy(dtype=float)
    computed["Rainf_f_tavg_mean__l0_s0__x__market_access_s0"] = computed["Rainf_f_tavg_mean__l0_s0"] * fs0["market_access"].to_numpy(dtype=float)
    computed["Tair_f_tavg_mean__l0_s0__x__popdensity_s0"] = computed["Tair_f_tavg_mean__l0_s0"] * fs0["popdensity"].to_numpy(dtype=float)

    targets = [c for c in header if any(v in c for v in OLD_VARIABLES)]
    for col in targets:
        saved = pd.to_numeric(fs0[col], errors="coerce").to_numpy(dtype=float)
        if col not in computed:
            rows.append({"feature": col, "status": "not_recomputed"})
            continue
        new = computed[col]
        both_nan = np.isnan(saved) & np.isnan(new)
        close = np.isclose(new, saved, rtol=args.rtol, atol=1e-9) | both_nan
        rows.append({
            "feature": col, "status": "match" if close.all() else "mismatch", "n": len(saved),
            "n_mismatch": int((~close).sum()), "n_nan_saved": int(np.isnan(saved).sum()), "n_nan_new": int(np.isnan(new).sum()),
            "max_abs_diff": float(np.nanmax(np.abs(new - saved))) if (~np.isnan(new - saved)).any() else 0.0,
        })
    report = pd.DataFrame(rows)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    report.to_csv(args.out, index=False)
    print(report["status"].value_counts().to_string())
    bad = report[report["status"] != "match"]
    if len(bad):
        print(bad.to_string(index=False))
    return 0 if bad.empty else 1


if __name__ == "__main__":
    raise SystemExit(main())
