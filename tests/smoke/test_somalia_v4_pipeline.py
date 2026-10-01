"""Synthetic end-to-end smoke run of the Somalia v4 CLI and its independent replay (tiny XGBoost fits)."""
from __future__ import annotations

import json
from importlib import util

import numpy as np
import pandas as pd

from ipcch import paths
from ipcch.somalia_oracle import PERCENT_COLUMNS, V2_FEATURES
from ipcch.somalia_oracle import data as sd

# semiannual originals 2018-2021, denser from 2022; validity windows create copies in 2020 and 2023
LABEL_MONTHS = [(y, m) for y in (2018, 2019, 2020, 2021) for m in (1, 7)] + [(2022, 1), (2022, 7), (2022, 10), (2023, 1), (2023, 8), (2024, 1), (2024, 7), (2025, 4), (2025, 10), (2026, 4)]
WINDOWS = [("21", "Jul 2020", "Sep 2020"), ("22", "Jan 2023", "Mar 2023"), ("23", "Jul 2024", "Aug 2024")]


def _module(rel, name):
    spec = util.spec_from_file_location(name, str(paths.PROJECT_ROOT / rel))
    mod = util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _inputs(tmp_path):
    rng = np.random.default_rng(11)
    areas = list(range(1600, 1608))
    lookup = pd.DataFrame({"area_id": areas + [9], "iso3": ["SOM"] * len(areas) + ["KEN"], "country": ["Somalia"] * len(areas) + ["Kenya"], "country_code": "SO", "country_en": ["Somalia"] * len(areas) + ["Kenya"]})
    raw_rows, fs_rows = [], []
    for area in areas + [9]:
        for year in range(2016, 2027):
            for month in range(1, 13):
                if (year, month) > (2026, 4):
                    continue
                # March 2023 reports cover only part of the areas, inside the Jan-Mar 2023 validity window:
                # the other areas receive copies, and the March originals see the January report in history
                lab = (year, month) in LABEL_MONTHS or ((year, month) == (2023, 3) and area < 1604)
                p = rng.dirichlet([2, 2, 1.5, 0.7, 0.2]) if lab else None
                phase = (3.0 if p[2:].sum() >= 0.2 else 2.0) if lab else np.nan
                raw_rows.append({"admin_code": area, "ISO3": "SOM" if area != 9 else "KEN", "year": year, "month": month, "overall_phase": phase, **{c: (p[i] if lab else np.nan) for i, c in enumerate(PERCENT_COLUMNS)},
                                 "Rainf_f_tavg_mean": float(rng.random()), "Tair_f_tavg_mean": float(295 + rng.random()), "estimated_population": 1000.0})
                if lab:
                    fs_rows.append({"area_id": area, "year": year, "month": month, "overall_phase": phase, **{c: p[i] for i, c in enumerate(PERCENT_COLUMNS)}, "estimated_population": 1000.0, "overall_phase_lag1": 2.0})
    raw = pd.DataFrame(raw_rows)
    out = {"raw": tmp_path / "raw.csv", "lookup": tmp_path / "lookup.csv", "v2": tmp_path / "v2.csv", "deep": tmp_path / "deep.csv"}
    raw.to_csv(out["raw"], index=False)
    lookup.to_csv(out["lookup"], index=False)
    fs = pd.DataFrame(fs_rows)
    for name in ("fs0", "fs1", "fs2", "fs3"):
        out[name] = tmp_path / f"{name}.csv"
        fs.assign(feat__l12=0.0, static_x=fs["area_id"] % 3).to_csv(out[name], index=False)
    deep = raw.rename(columns={"admin_code": "area_id"})[["area_id", "year", "month", "overall_phase", *PERCENT_COLUMNS]].copy()
    deep["feat__l12"] = rng.normal(size=len(deep)) + deep["phase3_percent"].fillna(0) * 3
    deep["static_x"] = deep["area_id"] % 3
    deep.loc[deep["area_id"] != 9].to_csv(out["deep"], index=False)
    v2 = []
    for area in areas:
        for year in range(2016, 2027):
            for season, start, end in (("s1", f"{year}-04-10", f"{year}-08-10"), ("s2", f"{year - 1}-09-20", f"{year}-02-20")):
                v2.append({"admin_code": area, "season_year": year, "season": season, "gs_start_date": start, "gs_end_date_exclusive": end, "gs_calendar_valid": 1, "gs_calendar_quality": "high",
                           "gs_available_window_days": 120, "gs_duration_recalculated_days": 120, **{c: float(rng.normal()) for c in V2_FEATURES}})
    pd.DataFrame(v2).to_csv(out["v2"], index=False)
    feats = [{"type": "Feature", "geometry": None, "properties": {"country": "SO", "condition": "A", "ipc_period": "C", "anl_id": a, "from": f, "to": t}} for a, f, t in WINDOWS]
    out["snapshot"] = tmp_path / "areas.geojson"
    out["snapshot"].write_text(json.dumps({"type": "FeatureCollection", "features": feats}))
    return out


def _config(tmp_path, inp):
    cfg = json.loads((paths.CONFIG_DIR / "somalia_v4_calibrated_d.json").read_text())
    bundles = json.loads((paths.PROJECT_ROOT / cfg["bundle_config"]).read_text())
    for c in bundles["candidates"]:
        c["common"]["n_estimators"] = 3
    bpath = tmp_path / "bundles.json"
    bpath.write_text(json.dumps(bundles))
    cfg.update(inputs={k: str(inp[k]) for k in ("raw", "deep", "lookup", "v2")}, bundle_config=str(bpath), bundle_config_sha256=sd.sha256_file(bpath),
               validity_snapshot=str(inp["snapshot"]), validity_snapshot_sha256=sd.sha256_file(inp["snapshot"]), excluded_raw_months={})
    path = tmp_path / "v4.json"
    path.write_text(json.dumps(cfg))
    return path


def test_v4_cli_and_replay_end_to_end_synthetic(tmp_path, monkeypatch):
    inp = _inputs(tmp_path)
    cpath = _config(tmp_path, inp)
    from ipcch.somalia_oracle import monthly_features as mf

    orig_scope = mf.scope_frame
    monkeypatch.setattr(mf, "scope_frame", lambda deep, h: orig_scope(deep, 12))  # synthetic panel has no upstream scope columns
    monkeypatch.setattr(mf, "parity_check", lambda rec, ref, skip: pd.DataFrame({"column": ["x"], "status": ["ok"], "n_mismatch": [0]}))
    runner = _module("scripts/modeling/run_somalia_v4_calibrated_d.py", "v4runner")
    replay = _module("scripts/postprocessing/replay_somalia_v4.py", "v4replay")
    out = tmp_path / "out"
    argv = ["--config", str(cpath), "--out-dir", str(out), "--workers", "1", "--skip-input-hash"] + sum([[f"--{n}-path", str(inp[n])] for n in ("fs0", "fs1", "fs2", "fs3")], [])
    assert runner.main(argv) == 0
    man = json.loads((out / "manifest.json").read_text())
    assert man["mode"] == "full" and man["n_copies"] > 0 and "2020" in {str(k) for k in man["copies_by_year"]}
    cohort = pd.read_csv(out / "ledgers" / "cohort_ledger.csv.gz")
    assert not cohort.loc[cohort["data_setting"] == "original", "is_copy"].any()
    assert cohort.loc[(cohort["data_setting"] == "augmented") & (cohort["status"] == "primary"), "is_copy"].any()  # copied test truth in 2023
    scores = pd.read_csv(out / "selection" / "candidate_scores.csv")
    assert (scores.groupby("selection_signature").size() == 144).all()
    sel = pd.read_csv(out / "selection" / "selected_recipes.csv")
    assert not sel["selection_labels_after_origin"].any()
    ctx = pd.read_csv(out / "selection" / "contexts.csv")
    assert set(ctx["horizon"]) == {0, 3, 6, 12} and ctx.groupby("horizon")["selection_signature"].nunique().min() >= 1  # independent horizons
    fits = pd.read_csv(out / "fits" / "final_fit_ledger.csv.gz")
    orig_jobs = fits["job_id"].str.startswith("original_")
    assert not fits.loc[orig_jobs, "is_copy"].any() and fits.loc[~orig_jobs, "is_copy"].any()
    preds = pd.read_csv(out / "predictions" / "final_predictions.csv.gz", float_precision="round_trip")
    assert not preds.duplicated(["data_setting", "outer_year", "horizon", "area_id", "target_ord"]).any()
    annual = pd.read_csv(out / "metrics" / "annual_metrics.csv")
    pooled = pd.read_csv(out / "metrics" / "pooled_metrics.csv")
    assert len(annual) == 40 and len(pooled) == 8
    assert set(annual["status"]) <= {"complete", "incomplete", "empty_cohort"}
    assert not any(c.startswith("delta") or "bootstrap" in c for c in [*annual.columns, *pooled.columns])
    assert (out / "report" / "summary.md").exists()
    ovr = pd.read_csv(out / "selection" / "history_overrides.csv.gz")
    test_ovr = ovr.loc[ovr["role"] == "test_prediction"]
    assert len(test_ovr) and (test_ovr["context_obs1_source_ord"] != sd.month_ord(2023, 1)).all()  # held-out January report removed
    exposed = preds.loc[preds["hx"].fillna("") != ""]
    assert len(exposed) and set(exposed["job_id"]) == {"augmented_y2023_h00_o2023-03"}
    # independent replay of the smoke run must pass every check
    assert replay.main(["--out-dir", str(out), "--config", str(cpath)]) == 0
    checks = pd.read_csv(out / "replay" / "replay_checks.csv")
    assert checks["ok"].all() and len(checks) > 40
