#!/usr/bin/env python3
"""Independent replay of a Somalia v4 calibrated-D run from its saved artifacts.

Reconstructs setting-specific label roles and cohorts, every OOF pool from its spec,
temporal/report isolation, the full 144-recipe selection, final calibration mappings,
saved-model predictions and annual/pooled metrics without the runner's code paths
(pandas merges + scikit-learn metrics/isotonic). Writes only <out-dir>/replay/.

    PYTHONPATH=src python scripts/postprocessing/replay_somalia_v4.py --out-dir results/experiments/somalia_oracle/v4_calibrated_d
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import f1_score, mean_absolute_error, mean_squared_error, precision_score, r2_score, recall_score, roc_auc_score

RT = {"float_precision": "round_trip"}
METHODS = ("none", "shift", "isotonic")
FORMS = ("direct", "residual")
HL_ORDER = {"none": 0, "48": 1, "24": 2, "12": 3}


class Replay:
    def __init__(self, out: Path):
        self.out = out
        self.rows = []

    def check(self, name, ok, detail=""):
        self.rows.append({"check": name, "ok": bool(ok), "detail": str(detail)[:500]})
        return bool(ok)

    def read(self, rel, **kw):
        return pd.read_csv(self.out / rel, **RT, **kw)


def keys_hash(frame):
    k = frame[["area_id", "target_ord"]].to_numpy().astype(np.int64)
    return hashlib.sha256(np.ascontiguousarray(k).tobytes()).hexdigest()[:16]


def sorted_digest(frame):
    k = frame[["area_id", "target_ord"]].astype(np.int64).sort_values(["area_id", "target_ord"], kind="mergesort").to_numpy()
    return hashlib.sha256(np.ascontiguousarray(k).tobytes()).hexdigest()


def fit_map(method, raw, truth, rounds, min_rounds):
    if method == "none":
        return ("ok", lambda x: np.asarray(x, float), None)
    if np.unique(rounds).size < min_rounds:
        return ("unsupported", None, None)
    if method == "shift":
        s = float(np.mean(raw - truth))
        return ("ok", lambda x, s=s: np.asarray(x, float) - s, s)
    if np.unique(raw).size < 2:
        return ("unsupported", None, None)
    iso = IsotonicRegression(y_min=0.0, y_max=1.0, increasing=True, out_of_bounds="clip").fit(raw, truth)
    return ("ok", iso.predict, iso)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--config", type=Path, default=None, help="default: configs/somalia_v4_calibrated_d.json")
    ap.add_argument("--probe-rows", type=int, default=0, help="model probe rows per job (0 = all)")
    args = ap.parse_args(argv)
    R = Replay(args.out_dir)
    cfg_manifest = json.loads((args.out_dir / "manifest.json").read_text())
    from ipcch import paths

    cfg = json.loads((args.config or paths.CONFIG_DIR / "somalia_v4_calibrated_d.json").read_text())
    min_cal = int(cfg["min_calibration_rounds"])
    tol = float(cfg["tie_tolerance"])

    # ---------------- labels, settings and cohorts ----------------
    led = R.read("ledgers/label_ledger.csv.gz")
    prov = {h: R.read(f"ledgers/row_provenance_h{h:02d}.csv.gz") for h in cfg["horizons"]}
    cohort = R.read("ledgers/cohort_ledger.csv.gz")
    slots = R.read("ledgers/cohort_slots.csv")
    copies = led.loc[led["is_copy"]]
    R.check("copies_keep_source_availability", (copies["source_available_ord"] == copies["original_month_ord"]).all() and (copies["original_month_ord"] < copies["target_ord"]).all())
    R.check("copies_never_history", not copies["valid_history"].any())
    R.check("copies_in_pre2022_years", (copies["target_ord"] // 12 < 2022).any(), copies["target_ord"].floordiv(12).value_counts().to_dict())
    R.check("original_cohort_has_no_copies", not cohort.loc[cohort["data_setting"] == "original", "is_copy"].any())
    for (s, y, h), g in cohort.groupby(["data_setting", "outer_year", "horizon"]):
        pool = led.loc[(led["target_ord"] // 12 == y) & ((~led["is_copy"]) if s == "original" else True)]
        pv = prov[h].set_index(["area_id", "target_ord"])["oracle_all_verified"]
        exp = []
        for r in pool.itertuples(index=False):
            if not r.valid_target or not r.valid_score:
                continue
            if h > 0 and not bool(pv.get((r.area_id, r.target_ord), False)):
                continue
            exp.append((r.area_id, r.target_ord))
        prim = g.loc[g["status"] == "primary"]
        ok = set(zip(prim["area_id"], prim["target_ord"])) == set(exp) and len(g) == len(pool)
        R.check(f"cohort_rebuilt_{s}_{y}_h{h}", ok, f"{len(prim)} vs {len(exp)}")
        srow = slots.loc[(slots["data_setting"] == s) & (slots["outer_year"] == y) & (slots["horizon"] == h)]
        R.check(f"cohort_digest_{s}_{y}_h{h}", len(srow) == 1 and srow["cohort_sha256"].iloc[0] == sorted_digest(prim))
    aug_test_copies = cohort.loc[(cohort["data_setting"] == "augmented") & (cohort["status"] == "primary"), "is_copy"].sum()
    R.check("augmented_tests_admit_copies", aug_test_copies > 0, aug_test_copies)

    # ---------------- pools, temporal and report isolation ----------------
    specs = R.read("selection/pool_specs.csv.gz", dtype={"excluded_families": str})
    specs["excluded_families"] = specs["excluded_families"].fillna("")
    fams = {h: p["source_family"].to_numpy(dtype=object) for h, p in prov.items()}
    spec_fams = {}
    bad = []
    for r in specs.itertuples(index=False):
        p = prov[r.horizon]
        m = (p["target_ord"] <= r.label_cutoff_ord) & (p["source_available_ord"] <= r.available_by_ord)
        if r.setting == "original":
            m &= ~p["is_copy"]
        if pd.notna(r.max_year):
            m &= (p["target_ord"] // 12 <= r.max_year) & (p["original_month_ord"] // 12 <= r.max_year)
        ex = [x for x in r.excluded_families.split(";") if x]
        m &= ~p["source_family"].isin(ex)
        sub = p.loc[m]
        spec_fams[r.spec_id] = set(sub["source_family"])
        h = keys_hash(sub) if len(sub) else None
        if (h if h else None) != (r.pool_keys_sha256 if isinstance(r.pool_keys_sha256, str) else None) or len(sub) != r.n_pool:
            bad.append(r.spec_id)
        if r.setting == "original" and sub["is_copy"].any():
            bad.append(f"copy:{r.spec_id}")
    R.check("pools_rebuilt_from_specs", not bad, bad[:5])
    spec_by = specs.set_index("spec_id")
    ctx = R.read("selection/contexts.csv", dtype={"test_families": str})
    ctx["test_families"] = ctx["test_families"].fillna("")
    mem = R.read("selection/scoring_keys.csv.gz")
    cal = R.read("selection/calibration_keys.csv.gz")
    fcal = R.read("selection/final_calibration_keys.csv.gz")
    fam_of = led.set_index(["area_id", "target_ord"])["source_family"]
    fam_by_round = led.drop_duplicates("original_month_ord").set_index("original_month_ord")["source_family"]
    viol = []
    for c in ctx.itertuples(index=False):
        tf = {x for x in c.test_families.split(";") if x}
        h = c.horizon
        m = mem.loc[mem["job_id"] == c.job_id]
        origin = int(pd.Period(c.origin, "M").year * 12 + pd.Period(c.origin, "M").month - 1)
        for r in m.itertuples(index=False):
            sp = spec_by.loc[r.spec_id]
            if sp.label_cutoff_ord != min(r.target_ord - h, r.target_ord - 1) or sp.available_by_ord != r.target_ord - h:
                viol.append(("member_origin", c.job_id, r.target_ord))
            if r.target_ord > origin or fam_of[(r.area_id, r.target_ord)] in spec_fams[r.spec_id] or spec_fams[r.spec_id] & tf:
                viol.append(("member_isolation", c.job_id, r.target_ord))
            if c.data_setting == "original" and r.is_copy:
                viol.append(("member_copy", c.job_id))
        cc = cal.loc[cal["job_id"] == c.job_id]
        for r in cc.itertuples(index=False):
            sp = spec_by.loc[r.spec_id]
            if not (r.target_ord < r.scoring_target_ord and r.target_ord <= r.scoring_target_ord - h and r.round < r.scoring_round):
                viol.append(("calibration_time", c.job_id))
            if fam_by_round[r.scoring_round] in spec_fams[r.spec_id] or fam_of[(r.area_id, r.target_ord)] in spec_fams[r.spec_id] or spec_fams[r.spec_id] & tf:
                viol.append(("calibration_isolation", c.job_id))
            if sp.available_by_ord != r.target_ord - h:
                viol.append(("calibration_origin", c.job_id))
            if c.data_setting == "original" and r.is_copy:
                viol.append(("calibration_copy", c.job_id))
        if c.status == "ok" and isinstance(c.fit_spec_id, str):
            sp = spec_by.loc[c.fit_spec_id]
            if sp.label_cutoff_ord != origin or sp.available_by_ord != origin or spec_fams[c.fit_spec_id] & tf:
                viol.append(("fit_spec", c.job_id))
    R.check("temporal_and_report_isolation", not viol, viol[:5])

    fit = R.read("fits/final_fit_ledger.csv.gz")
    fstat = R.read("fits/final_status.csv") if (args.out_dir / "fits" / "final_status.csv").stat().st_size > 1 else pd.DataFrame()
    wviol = []
    for job_id, g in fit.groupby("job_id"):
        st = fstat.loc[fstat["job_id"] == job_id].iloc[0]
        c = ctx.loc[ctx["job_id"] == job_id].iloc[0]
        origin = int(pd.Period(c.origin, "M").year * 12 + pd.Period(c.origin, "M").month - 1)
        hl = str(st["half_life"])
        age = origin - g["target_ord"]
        exp_w = np.ones(len(g)) if hl == "none" else 0.5 ** (age / float(hl))
        ok = (age >= 0).all() and (g["source_available_ord"] <= origin).all() and (g["target_ord"] // 12 <= c.outer_year - 1).all() and np.allclose(g["weight"], exp_w, rtol=0, atol=1e-15)
        ok &= not (c.data_setting == "original" and g["is_copy"].any())
        tf = {x for x in (c.test_families or "").split(";") if x}
        ok &= not g["source_family"].isin(tf).any()
        if not ok:
            wviol.append(job_id)
    R.check("final_fit_pools_and_decay_weights", not wviol, wviol[:5])

    # ---------------- selection replay ----------------
    units = R.read("selection/oof_units.csv.gz", dtype={"half_life": str})
    oof = R.read("selection/oof_predictions.csv.gz")
    oof_idx = {u: g.set_index(["area_id", "target_ord"])["raw_q3"] for u, g in oof.groupby("unit_id")}
    ukey = {(r.spec_id, r.formulation, r.bundle, r.half_life): (r.unit_id, r.status) for r in units.itertuples(index=False)}
    truth = led.set_index(["area_id", "target_ord"])
    scores = R.read("selection/candidate_scores.csv", dtype={"half_life": str})
    selected = R.read("selection/selected_recipes.csv", dtype={"half_life": str})

    def unit_raw(spec_id, form, bundle, hl, keys):
        uid, st = ukey.get((spec_id, form, bundle, hl), (None, "missing"))
        if st != "ok":
            return None
        s = oof_idx.get(uid)
        return s.reindex(pd.MultiIndex.from_frame(keys[["area_id", "target_ord"]])).to_numpy(dtype=float)

    base_by_h = {h: (np.isfinite(p["hist_q3_obs1"].to_numpy(float)) & (p["history_obs1_source_ord"].to_numpy() >= 0)) for h, p in prov.items()}
    base_idx = {h: pd.Series(base_by_h[h], index=pd.MultiIndex.from_frame(p[["area_id", "target_ord"]])) for h, p in prov.items()}

    def has_base(keys, h):
        return base_idx[h].reindex(pd.MultiIndex.from_frame(keys[["area_id", "target_ord"]])).to_numpy(dtype=bool)

    def cand_raw(frame, form, bundle, hl, h):
        """Residual required exactly on rows with a permitted baseline; others use direct."""
        lab = np.where(has_base(frame, h), "residual", "fallback_direct").astype(object) if form == "residual" else np.full(len(frame), "direct", dtype=object)
        raw = np.full(len(frame), np.nan)
        for sid, g in frame.groupby("spec_id"):
            pos = frame.index.get_indexer(g.index)
            for unit_form, want in (("direct", lab[pos] != "residual"), ("residual", lab[pos] == "residual")):
                if not want.any():
                    continue
                vals = unit_raw(sid, unit_form, bundle, hl, g.loc[want])
                if vals is None:
                    return None, None
                raw[pos[want]] = vals
        return raw, lab

    def maps_for(calrows, form, bundle, hl, method, h):
        cr = calrows.reset_index(drop=True)
        names = ("direct",) if form == "direct" else ("residual", "fallback_direct")
        if method == "none":
            return {n: fit_map("none", None, None, None, min_cal) for n in names}
        y = truth.loc[list(zip(cr["area_id"], cr["target_ord"])), "q3"].to_numpy(dtype=float) if len(cr) else np.array([])
        hb = has_base(cr, h) if len(cr) else np.array([], dtype=bool)
        out = {}
        for name in names:
            unit_form = "residual" if name == "residual" else "direct"
            keep = hb if name == "residual" else np.ones(len(cr), dtype=bool)
            raw = np.full(len(cr), np.nan)
            failed = False
            for sid, g in cr.loc[keep].groupby("spec_id"):
                vals = unit_raw(sid, unit_form, bundle, hl, g)
                if vals is None:
                    failed = True
                    break
                raw[g.index.to_numpy()] = vals
            if failed or not np.isfinite(raw[keep]).all():
                out[name] = ("unsupported", None, None)
                continue
            out[name] = fit_map(method, raw[keep], y[keep], cr["round"].to_numpy()[keep], min_cal)
        return out

    sel_mis, score_mis, n_cand = [], [], 0
    for sig, g in selected.loc[selected["status"] == "ok"].groupby("selection_signature"):
        job = g["job_id"].iloc[0]
        m = mem.loc[mem["job_id"] == job].reset_index(drop=True)
        cc = cal.loc[cal["job_id"] == job]
        sc = scores.loc[scores["selection_signature"] == sig].drop_duplicates(["bundle", "half_life", "formulation", "method"])
        res = []
        for bundle in sorted(sc["bundle"].unique()):
            for hl in ("12", "24", "48", "none"):
                for form in FORMS:
                    raw, lab = cand_raw(m, form, bundle, hl, int(g["horizon"].iloc[0]))
                    for method in METHODS:
                        n_cand += 1
                        if raw is None or not np.isfinite(raw).all():
                            res.append({"bundle": bundle, "half_life": hl, "formulation": form, "method": method, "ok": False})
                            continue
                        fin = np.full(len(m), np.nan)
                        fail = False
                        for (rr, v), gg in m.groupby(["round", "target_ord"]):
                            pos = gg.index.to_numpy()
                            mp = maps_for(cc.loc[(cc["scoring_round"] == rr) & (cc["scoring_target_ord"] == v)], form, bundle, hl, method, int(g["horizon"].iloc[0]))
                            for name in np.unique(lab[pos]):
                                st, fn, _ = mp[name]
                                if st != "ok":
                                    fail = True
                                    break
                                sel = pos[lab[pos] == name]
                                fin[sel] = np.clip(fn(raw[sel]), 0, 1)
                            if fail:
                                break
                        if fail:
                            res.append({"bundle": bundle, "half_life": hl, "formulation": form, "method": method, "ok": False})
                            continue
                        t = truth.loc[list(zip(m["area_id"], m["target_ord"]))]
                        y, cr = t["q3"].to_numpy(float), t["actual_crisis"].to_numpy(float)
                        auc = roc_auc_score(cr == 1, fin) if np.unique(cr).size == 2 else np.nan
                        res.append({"bundle": bundle, "half_life": hl, "formulation": form, "method": method, "ok": True, "rmse": float(np.sqrt(mean_squared_error(y, fin))), "auc": auc})
        rep = pd.DataFrame(res)
        mg = sc.merge(rep, on=["bundle", "half_life", "formulation", "method"], how="outer", validate="one_to_one")
        bad = mg.loc[(mg["status"] == "ok") != mg["ok"]]
        both = mg.loc[(mg["status"] == "ok") & mg["ok"]]
        if len(bad) or len(mg) != 144 or not np.allclose(both["rmse_x"], both["rmse_y"], rtol=1e-12, atol=1e-14):
            score_mis.append(sig)
        okc = rep.loc[rep["ok"]].copy()
        best = okc["rmse"].min()
        tie = okc.loc[okc["rmse"] <= best + tol].copy()
        tie["m"] = tie["method"].map(METHODS.index)
        tie["b"] = tie["bundle"].str[1:].astype(int)
        tie["f"] = tie["formulation"].map(FORMS.index)
        tie["d"] = tie["half_life"].map(HL_ORDER)
        keys, asc = (["auc"], [False]) if (len(tie) > 1 and tie["auc"].notna().all()) else ([], [])
        win = tie.sort_values(keys + ["m", "b", "f", "d"], ascending=asc + [True] * 4, kind="mergesort").iloc[0]
        for r in g.itertuples(index=False):
            if (r.formulation, r.bundle, str(r.half_life), r.method) != (win["formulation"], win["bundle"], win["half_life"], win["method"]):
                sel_mis.append(r.job_id)
    R.check("candidate_scores_replayed", not score_mis, score_mis[:5])
    R.check("selected_recipes_replayed", not sel_mis, sel_mis[:5])

    # ---------------- final mappings and predictions ----------------
    preds = R.read("predictions/final_predictions.csv.gz", dtype={"half_life": str})
    maps_saved = R.read("fits/calibration_mappings.csv")
    fmis = []
    for job_id, g in preds.groupby("job_id"):
        s = selected.loc[selected["job_id"] == job_id].iloc[0]
        mp = maps_for(fcal.loc[fcal["job_id"] == job_id], s["formulation"], s["bundle"], str(s["half_life"]), s["method"], int(s["horizon"]))
        exp = np.full(len(g), np.nan)
        ok_all = True
        for name in g["prediction_branch"].unique():
            st, fn, obj = mp[name]
            sel = (g["prediction_branch"] == name).to_numpy()
            if st != "ok":
                ok_all = False
                continue
            exp[sel] = np.clip(fn(g["q3_raw"].to_numpy(float)[sel]), 0, 1)
            sm = maps_saved.loc[(maps_saved["job_id"] == job_id) & (maps_saved["prediction_branch"] == name)]
            if s["method"] == "shift" and not np.isclose(sm["shift"].iloc[0], obj, rtol=0, atol=1e-15):
                fmis.append((job_id, "shift"))
        if ok_all:
            if not np.allclose(exp, g["q3_final"].to_numpy(float), rtol=0, atol=1e-12):
                fmis.append((job_id, "final"))
        elif g["q3_final"].notna().any():
            fmis.append((job_id, "unavailable_mapping_has_final"))
    R.check("final_mappings_and_bounds_replayed", not fmis, fmis[:5])

    inv = R.read("models/model_inventory.csv")
    import xgboost as xgb

    feats = {}
    schema = json.loads((args.out_dir / "features" / "feature_schema.json").read_text())
    pmis, n_probe = [], 0
    for job_id, g in preds.groupby("job_id"):
        h = int(g["horizon"].iloc[0])
        if h not in feats:
            fm = R.read(f"features/feature_matrix_h{h:02d}.csv.gz")
            feats[h] = fm.set_index(["area_id", "target_ord"])[schema[f"h{h:02d}_D"]]
        gg = g if not args.probe_rows else g.head(args.probe_rows)
        X = feats[h].loc[list(zip(gg["area_id"], gg["target_ord"]))].to_numpy(dtype=np.float32)
        pr = {}
        for r in inv.loc[inv["job_id"] == job_id].itertuples(index=False):
            p = args.out_dir / "models" / r.path
            if hashlib.sha256(p.read_bytes()).hexdigest() != r.sha256:
                pmis.append((job_id, "hash"))
            if r.kind == "xgboost":
                b = xgb.Booster()
                b.load_model(str(p))
                pr[r.target] = b.predict(xgb.DMatrix(X))
            else:
                pr[r.target] = np.full(len(gg), json.loads(p.read_text())["value"])
        base = prov[h].set_index(["area_id", "target_ord"]).loc[list(zip(gg["area_id"], gg["target_ord"])), "hist_q3_obs1"].to_numpy(float)
        q3 = np.where(gg["prediction_branch"] == "residual", base + pr.get("q3_residual_delta", np.full(len(gg), np.nan)), pr["q3_direct"])
        for t, col in (("q2", "q2_raw"), ("q4", "q4_raw"), ("q5", "q5_raw")):
            if not np.allclose(pr[t], gg[col].to_numpy(float), rtol=0, atol=1e-6):
                pmis.append((job_id, t))
        if not np.allclose(q3, gg["q3_raw"].to_numpy(float), rtol=0, atol=1e-6):
            pmis.append((job_id, "q3"))
        n_probe += len(gg)
    R.check("saved_models_reproduce_predictions", not pmis, pmis[:5])

    # ---------------- metrics ----------------
    annual = R.read("metrics/annual_metrics.csv")
    pooled = R.read("metrics/pooled_metrics.csv")

    def metrics(m):
        y, c, f, raw = m["q3"].to_numpy(float), m["actual_crisis"].to_numpy(float) == 1, m["q3_final"].to_numpy(float), m["q3_raw"].to_numpy(float)
        out = {"n": len(m), "final_rmse": np.sqrt(mean_squared_error(y, f)), "final_mae": mean_absolute_error(y, f), "final_bias": float(np.mean(f - y)), "raw_rmse": np.sqrt(mean_squared_error(y, raw))}
        out["final_r2"] = r2_score(y, f) if np.unique(y).size > 1 else np.nan
        out["raw_r2"] = r2_score(y, raw) if np.unique(y).size > 1 else np.nan
        out["final_auc"] = roc_auc_score(c, f) if np.unique(c).size == 2 else np.nan
        out["raw_auc"] = roc_auc_score(c, raw) if np.unique(c).size == 2 else np.nan
        pb = f >= 0.2
        out["bin_f1"] = f1_score(c, pb, zero_division=np.nan)
        out["bin_precision"] = precision_score(c, pb, zero_division=np.nan)
        out["bin_recall"] = recall_score(c, pb, zero_division=np.nan)
        return out

    mmis, parts = [], {}
    tcols = led[["area_id", "target_ord", "q3", "actual_crisis"]]
    for r in annual.itertuples(index=False):
        prim = cohort.loc[(cohort["data_setting"] == r.data_setting) & (cohort["outer_year"] == r.outer_year) & (cohort["horizon"] == r.horizon) & (cohort["status"] == "primary"), ["area_id", "target_ord"]]
        p = preds.loc[(preds["data_setting"] == r.data_setting) & (preds["outer_year"] == r.outer_year) & (preds["horizon"] == r.horizon)]
        if p.duplicated(["area_id", "target_ord"]).any():
            mmis.append((r.data_setting, r.outer_year, r.horizon, "dup"))
        m = prim.merge(tcols, on=["area_id", "target_ord"], how="left").merge(p[["area_id", "target_ord", "q3_raw", "q3_final"]], on=["area_id", "target_ord"], how="left")
        exp_status = "empty_cohort" if prim.empty else ("incomplete" if m["q3_final"].isna().any() else "complete")
        if exp_status != r.status:
            mmis.append((r.data_setting, r.outer_year, r.horizon, "status"))
        if exp_status == "complete":
            parts.setdefault((r.data_setting, r.horizon), []).append(m)
            mm = metrics(m)
            got = r._asdict()
            for k, v in mm.items():
                if not ((np.isnan(v) and pd.isna(got[k])) or np.isclose(v, got[k], rtol=1e-9, atol=1e-12)):
                    mmis.append((r.data_setting, r.outer_year, r.horizon, k))
    for r in pooled.itertuples(index=False):
        a = annual.loc[(annual["data_setting"] == r.data_setting) & (annual["horizon"] == r.horizon)]
        exp_status = "incomplete" if (a["status"] == "incomplete").any() else ("empty_cohort" if not parts.get((r.data_setting, r.horizon)) else "complete")
        if exp_status != r.status:
            mmis.append((r.data_setting, "pooled", r.horizon, "status"))
        if exp_status == "complete":
            m = pd.concat(parts[(r.data_setting, r.horizon)], ignore_index=True)
            got = r._asdict()
            for k, v in metrics(m).items():
                if not ((np.isnan(v) and pd.isna(got[k])) or np.isclose(v, got[k], rtol=1e-9, atol=1e-12)):
                    mmis.append((r.data_setting, "pooled", r.horizon, k))
    R.check("annual_and_pooled_metrics_replayed", not mmis, mmis[:8])
    leak = []
    for s_, g_ in preds.groupby("data_setting"):
        allowed = set(zip(cohort.loc[(cohort["data_setting"] == s_) & (cohort["status"] == "primary"), "area_id"], cohort.loc[(cohort["data_setting"] == s_) & (cohort["status"] == "primary"), "target_ord"]))
        if not set(zip(g_["area_id"], g_["target_ord"])) <= allowed:
            leak.append(s_)
    orig_pred_copies = preds.loc[preds["data_setting"] == "original"].merge(led[["area_id", "target_ord", "is_copy"]], on=["area_id", "target_ord"])["is_copy"].any()
    R.check("predictions_stay_in_own_setting_cohort", not leak and not orig_pred_copies, leak)
    R.check("no_cross_setting_contrast_outputs", not any(c.startswith(("delta", "contrast")) or "bootstrap" in c for c in [*annual.columns, *pooled.columns]) and not (args.out_dir / "metrics" / "contrasts.csv").exists())

    rep = pd.DataFrame(R.rows)
    (args.out_dir / "replay").mkdir(exist_ok=True)
    rep.to_csv(args.out_dir / "replay" / "replay_checks.csv", index=False)
    summary = {"checks": len(rep), "passed": int(rep["ok"].sum()), "failed": rep.loc[~rep["ok"], "check"].tolist(), "candidates_replayed": n_cand, "probe_rows": n_probe, "run_mode": cfg_manifest.get("mode")}
    (args.out_dir / "replay" / "replay_summary.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))
    return 0 if rep["ok"].all() else 1


if __name__ == "__main__":
    sys.exit(main())
