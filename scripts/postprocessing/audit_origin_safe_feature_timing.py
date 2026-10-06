"""Leakage audit of the saved origin_safe_climate_idp_v1 datasets at many cutoffs.

For each cutoff month c, every source observation after c is perturbed — interim monthly sources, the climate
monthly grid, seasons ending after c, IPC labels after c (history source) and DTM IDP reports after c — and all
features are recomputed with the builder's code. A saved feature value of a row whose availability cutoff is
<= c must equal the recomputed value (rows with origin O <= c; history rows with min(O, T-1) <= c).
Comparing against the *saved* dataset ties the published inputs, not only the recipes, to the timing contract.
Every fitted feature must belong to an audited block or to the static/identifier classes listed here.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = next(path for path in Path(__file__).resolve().parents if (path / "src").exists())
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import numpy as np
import pandas as pd

from ipcch import climate2015_features as cf
from ipcch import origin_safe as osf
from ipcch import retained_feature_recipes as rr

spec = importlib.util.spec_from_file_location("builder", PROJECT_ROOT / "scripts/preprocessing/build_origin_safe_climate_idp_inputs.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)

CUTOFFS = ("2018-12", "2020-06", "2021-12", "2022-12", "2023-06", "2023-12", "2024-06", "2024-12", "2025-06")
OUT = PROJECT_ROOT / "results" / "experiments" / builder.VERSION / "timing_audit"


def changed(saved: np.ndarray, new: np.ndarray) -> np.ndarray:
    """A saved value counts as changed if the recomputation differs or loses it (saved NaN is kept missingness)."""
    present = ~np.isnan(saved)
    return present & (np.isnan(new) | (np.abs(new - saved) > 1e-9 * np.maximum(1.0, np.abs(saved))))


def main() -> int:
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(builder.OUT_DIR.joinpath(f"{builder.VERSION}_manifest.json").read_text())
    panel = builder.load_interim(builder.INPUTS["interim"])
    static = panel.groupby("area_id").agg(lat=("lat", "mean"), lon=("lon", "mean"), popdensity=("popdensity", "first"), market_access=("market_access", "first"))
    monthly = pd.read_csv(builder.INPUTS["climate_monthly"], usecols=["admin_code", "year", "month", *cf.MONTHLY_VARIABLES]).rename(columns={"admin_code": "area_id"})
    grid = cf.Grid.from_long(monthly, cf.MONTHLY_VARIABLES)
    del monthly
    seasons = pd.read_csv(builder.INPUTS["climate_seasonal"], usecols=["admin_code", "season_year", "season", "gs_start_date", "gs_end_date_exclusive", *cf.SEASONAL_VARIABLES])
    gco = panel.groupby("area_id")[["lat", "lon"]].mean().reindex(grid.area_ids)
    cvalid = gco["lat"].between(-90, 90).to_numpy() & gco["lon"].between(-180, 180).to_numpy()
    cnb = cf.build_neighbors(gco["lat"].to_numpy(), gco["lon"].to_numpy(), cvalid)
    idp_raw = pd.read_csv(builder.INPUTS["idp_admin0_monthly"])
    lookup = pd.read_csv(builder.INPUTS["country_lookup"]).set_index("area_id")["iso3"]
    rng = np.random.default_rng(11)
    rows, unaudited = [], {}
    for horizon in osf.HORIZONS:
        entry = manifest["horizons"][str(horizon)]
        features = entry["arms"]["climate_safe_history_idp"]["features"]
        data = pd.read_csv(entry["dataset"]["path"], float_precision="round_trip", low_memory=False)
        keys = data[list(osf.KEYS)]
        target = osf.month_ord(keys["year"], keys["month"])
        origin = target - horizon
        label_cut = osf.label_cutoff(target, horizon)
        cls = pd.read_csv(OUT.parent / "input_checks" / f"feature_classification_h{horizon}.csv")
        retained = cls.loc[cls["decision"] == "retained", "feature"].tolist()
        dynamic = [c for c in retained if not rr.is_static_name(c)]
        climate = pd.read_csv(OUT.parent / "input_checks" / f"climate_manifest_h{horizon}.csv")["feature_name"].tolist()
        audited = set(dynamic) | set(climate) | set(osf.HISTORY_FEATURES) | set(osf.IDP_FEATURES)
        other = [f for f in features if f not in audited]
        bad_other = [f for f in other if not (rr.is_static_name(f) or f in ("lat", "lon") or f.startswith(("month_", "year_")))]
        unaudited[horizon] = {"static_or_identifier": other, "unexplained": bad_other}
        if bad_other:
            raise ValueError(f"h{horizon}: features outside audited/static/identifier classes: {bad_other}")
        # identifier year dummies: training rows of the year-Y block never contain year Y
        scope_anchor = None if horizon == 12 else horizon
        context = data[[cf.ENSO_SHARE, "popdensity", "market_access"]]
        saved_dyn = data[dynamic].to_numpy(dtype=float)
        saved_clim = data[climate].to_numpy(dtype=float)
        saved_hist = data[list(osf.HISTORY_FEATURES)].to_numpy(dtype=float)
        saved_idp = data[list(osf.IDP_FEATURES)].to_numpy(dtype=float)
        labels = data[list(osf.KEYS) + ["overall_phase"]]
        for text in CUTOFFS:
            c = builder.ord_of(text)
            # inherited dynamic families
            pert = panel.copy()
            late = osf.month_ord(pert["year"], pert["month"]) > c
            for column in [*rr.ORDINARY_SOURCES, rr.ENSO, *[x for x in pert.columns if x.startswith("bbg_")]]:
                v = pd.to_numeric(pert[column], errors="coerce").to_numpy(dtype=float).copy()
                v[late] = v[late] * rng.uniform(1.5, 3.0, int(late.sum())) + rng.normal(50.0, 10.0, int(late.sum()))
                pert[column] = v
            expected, _ = rr.RetainedRecipes(pert, static).expected(keys, scope_anchor, data)
            new_dyn = np.column_stack([expected[f] for f in dynamic])
            del pert, expected
            # climate block
            values = {}
            late_col = np.arange(grid.n_months) + grid.first_ord > c
            for v, arr in grid.values.items():
                arr = arr.copy()
                arr[:, late_col] = arr[:, late_col] * 2.0 + rng.normal(5.0, 1.0, arr[:, late_col].shape)
                values[v] = arr
            pseasons = seasons.copy()
            first_day_after = pd.Timestamp(year=(c + 1) // 12, month=(c + 1) % 12 + 1, day=1)
            late_s = (pd.to_datetime(pseasons["gs_end_date_exclusive"]) > first_day_after).to_numpy()
            for v in cf.SEASONAL_VARIABLES:
                pseasons.loc[late_s, v] = pseasons.loc[late_s, v] * 2.0 + 5.0
            pclim, _ = cf.build_scope_features(cf.Grid(grid.area_ids, grid.first_ord, grid.n_months, values), pseasons, keys, scope_anchor, cnb, cvalid, context)
            new_clim = pclim[climate].to_numpy(dtype=float)
            del values, pclim
            # IPC history labels after c
            plab = labels.copy()
            lord = osf.month_ord(plab["year"], plab["month"])
            plab.loc[lord > c, "overall_phase"] = rng.integers(1, 6, int((lord > c).sum())).astype(float)
            hist, _ = osf.build_safe_history(osf.valid_phase_observations(plab), keys, horizon)
            new_hist = hist.to_numpy(dtype=float)
            # IDP reports after c
            pidp = idp_raw.copy()
            pidp.loc[(pidp["year"] * 12 + pidp["month"] - 1 > c) & pidp["idp_ind"].notna(), "idp_ind"] *= 7.0
            idp, _ = osf.build_idp_features(osf.idp_observations(pidp), keys, list(np.where(pd.isna(lookup.reindex(keys["area_id"]).to_numpy()), None, lookup.reindex(keys["area_id"]).to_numpy())), horizon)
            new_idp = idp.to_numpy(dtype=float)
            for block, saved, new, eligible in (("retained", saved_dyn, new_dyn, origin <= c), ("climate2015", saved_clim, new_clim, origin <= c),
                                                ("history", saved_hist, new_hist, label_cut <= c), ("idp", saved_idp, new_idp, origin <= c)):
                ch = changed(saved, new)
                rows.append({"horizon": horizon, "cutoff": text, "block": block, "features": saved.shape[1],
                             "rows_eligible": int(eligible.sum()), "changed_cells_eligible": int(ch[eligible].sum()),
                             "changed_cells_after_cutoff": int(ch[~eligible].sum()),
                             "features_with_power": int(ch[~eligible].any(axis=0).sum())})
            print(f"[{time.time() - t0:5.0f}s] h{horizon} {text}: " + ", ".join(f"{r['block']} {r['changed_cells_eligible']}" for r in rows[-4:]), flush=True)
    report = pd.DataFrame(rows)
    report.to_csv(OUT / "timing_audit.csv", index=False)
    summary = {"cutoffs": CUTOFFS, "passed": bool((report["changed_cells_eligible"] == 0).all()),
               "eligible_changed_total": int(report["changed_cells_eligible"].sum()),
               "non_audited_features": unaudited, "elapsed_seconds": round(time.time() - t0, 1)}
    (OUT / "timing_audit_summary.json").write_text(json.dumps(summary, indent=2, default=str))
    print(json.dumps({k: v for k, v in summary.items() if k != "non_audited_features"}, indent=2))
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
