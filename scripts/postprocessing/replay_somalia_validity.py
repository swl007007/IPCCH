#!/usr/bin/env python3
"""Independent replay of the validity-augmentation run from saved artifacts.

Checks, without importing augexp/q3opt/q3eval: augmentation rules (blank-only,
inside windows, lineage, no originals changed); report isolation and availability of
every OOF and final fit; rounds plan; candidate scores and strict-RMSE selection; saved
calibration mappings rebuilt from saved OOF predictions; primary metrics with
scikit-learn; identical outer keys across branches; bootstrap intervals; saved models
reproduce saved predictions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import mean_squared_error, r2_score, roc_auc_score

from ipcch import paths

OUT = paths.RESULTS_DIR / "experiments" / "somalia_oracle" / "v3_validity"
FIELDS = ["overall_phase", *[f"phase{i}_percent" for i in range(1, 6)]]


def read(p, **kw):
    return pd.read_csv(p, float_precision="round_trip", **kw)


def ordl(s):
    return int(s[:4]) * 12 + int(s[5:7]) - 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out-dir", type=Path, default=OUT)
    ap.add_argument("--raw-path", type=Path, default=paths.SOURCE_DATA_DIR / "assembled_IPCCH" / "raw" / "IPCCH_2026_completed.csv")
    ap.add_argument("--skip-raw", action="store_true")
    args = ap.parse_args(argv)
    out = args.out_dir
    checks = []
    add = lambda n, ok, d="": checks.append({"check": n, "pass": bool(ok), "detail": d})

    ledger = read(out / "ledgers" / "label_ledger.csv.gz")
    api = read(out / "ledgers" / "api_rounds.csv", dtype={"anl_id": str})
    links = read(out / "ledgers" / "round_links.csv", dtype={"anl_id": str})
    # (1) augmentation
    cp = ledger.loc[ledger["is_copy"]]
    orig = ledger.loc[~ledger["is_copy"]].set_index(["area_id", "target_ord"])
    add("copy_keys_unique", not ledger.duplicated(["area_id", "target_ord"]).any())
    src = orig.reindex(pd.MultiIndex.from_arrays([cp["area_id"], cp["original_month_ord"]]))
    add("copy_values_equal_original", np.allclose(cp[FIELDS].to_numpy(float), src[FIELDS].to_numpy(float), equal_nan=False))
    lk = links.loc[links["link_status"] == "linked"].set_index("original_month_ord")
    win = lk.reindex(cp["original_month_ord"])
    add("copies_inside_linked_window", ((cp["target_ord"].to_numpy() >= win["valid_from_ord"].to_numpy()) & (cp["target_ord"].to_numpy() <= win["valid_to_ord"].to_numpy())).all())
    add("copy_family_is_linked_anl", (cp["source_family"].to_numpy() == ("anl:" + win["anl_id"].astype(str)).to_numpy()).all())
    add("copy_availability_is_original_month", (cp["source_available_ord"] == cp["original_month_ord"]).all())
    add("copies_only_training_years", (cp["target_ord"] // 12 <= 2024).all())
    add("copies_never_history", (~cp["valid_history"].astype(bool)).all())
    for _, r in links.loc[links["link_status"] == "linked"].iterrows():
        ar = api.loc[api["anl_id"] == str(r["anl_id"])]
        add(f"link_unique_start_{r['original_month']}", len(api.loc[api["valid_from_ord"] == r["original_month_ord"]]) == 1 and len(ar) == 1)
    if not args.skip_raw:
        parts = [c[c["ISO3"] == "SOM"] for c in pd.read_csv(args.raw_path, usecols=["admin_code", "ISO3", "year", "month", *FIELDS], chunksize=200000)]
        raw = pd.concat(parts)
        raw["target_ord"] = raw["year"] * 12 + raw["month"] - 1
        raw = raw.rename(columns={"admin_code": "area_id"}).set_index(["area_id", "target_ord"])
        rc = raw.reindex(pd.MultiIndex.from_arrays([cp["area_id"], cp["target_ord"]]))
        add("recipients_blank_in_raw", rc[FIELDS].isna().all(axis=1).all())
        ro = raw.reindex(pd.MultiIndex.from_arrays([ledger.loc[~ledger["is_copy"], "area_id"], ledger.loc[~ledger["is_copy"], "target_ord"]]))
        add("originals_unchanged_vs_raw", np.allclose(ro[FIELDS].to_numpy(float), ledger.loc[~ledger["is_copy"], FIELDS].to_numpy(float), equal_nan=True))

    # (2) isolation/availability for OOF fits via pool membership rules
    prov = {h: read(out / "ledgers" / f"row_provenance_h{h:02d}.csv.gz") for h in (0, 3, 6, 12)}
    oof = read(out / "selection" / "oof_fit_ledger.csv")
    ok = oof.loc[oof["status"] == "ok"]
    add("oof_labels_before_round_origin", ((ok["fit_max_target_ord"] <= ok["fit_label_cutoff"]) & (ok["fit_label_cutoff"] < ok["round"]) & (ok["fit_label_cutoff"] <= ok["round"] - ok["horizon"])).all())
    add("oof_available_by_origin", (ok["available_by"] == ok["round"] - ok["horizon"]).all())
    fits = read(out / "fits" / "final_fit_ledger.csv.gz")
    status = read(out / "fits" / "final_status.csv")
    fm = fits.merge(status[["job_id", "branch", "view", "receiving_origin", "test_year"]].rename(columns={"branch": "label_branch"}), on=["job_id", "label_branch", "view"])
    add("final_fit_labels_before_origin", (fm["target_ord"] <= fm["receiving_origin"].map(ordl)).all())
    add("final_fit_sources_available", (fm["source_available_ord"] <= fm["receiving_origin"].map(ordl)).all())
    add("final_fit_no_test_year", ((fm["target_ord"] // 12 < fm["test_year"]) & (fm["source_available_ord"] // 12 < fm["test_year"])).all())
    add("original_branch_has_no_copies", not fm.loc[fm["label_branch"] == "original", "is_copy"].any())
    add("augmented_branch_uses_copies", fm.loc[fm["label_branch"] == "augmented", "is_copy"].any())
    fam = ledger.set_index(["area_id", "target_ord"])["source_family"]
    for h in (0, 3, 6, 12):
        p = prov[h]
        cpy = p.loc[p["is_copy"]]
        add(f"copy_history_before_own_report_h{h}", (cpy["history_obs1_source_ord"] < cpy["original_month_ord"]).all())
        add(f"history_cutoff_rule_h{h}", (p["history_obs1_source_ord"] <= p["history_cutoff_ord"]).all() and (p["persistence_source_ord"] <= p["history_cutoff_ord"]).all())

    # (3) rounds and selection
    scores = read(out / "selection" / "candidate_scores.csv")
    sel = read(out / "selection" / "selected_recipes.csv")
    sp = read(out / "selection" / "scoring_predictions.csv.gz")
    add("equal_search_budgets", scores.groupby(["branch", "fold"]).size().nunique() == 1)
    truth0 = prov[0].reset_index().rename(columns={"index": "row"})[["row", "q3"]]
    sp = sp.merge(truth0, on="row")
    rep = sp.groupby(["branch", "fold", "view", "bundle", "method"]).apply(lambda g: np.sqrt(mean_squared_error(g["q3"], g["final_q3"]))).rename("rmse_rep").reset_index()
    m = scores.loc[scores["status"] == "ok"].merge(rep, on=["branch", "fold", "view", "bundle", "method"])
    add("candidate_rmse_replay", np.allclose(m["rmse"], m["rmse_rep"], atol=1e-12) and len(m) == (scores["status"] == "ok").sum())
    order = {"none": 0, "shift": 1, "isotonic": 2}
    for (b, f), g in scores.loc[scores["status"] == "ok"].groupby(["branch", "fold"]):
        for view, gg in list(g.groupby("view")) + [("D_selected", g)]:
            best = gg["rmse"].min()
            tie = gg.loc[gg["rmse"] <= best + 1e-12].assign(mo=lambda d: d["method"].map(order), bo=lambda d: d["bundle"].str[1].astype(int), fo=lambda d: (d["formulation"] == "residual").astype(int))
            keys = (["auc"] if len(tie) > 1 and tie["auc"].notna().all() else [])
            w = tie.sort_values(keys + ["mo", "bo", "fo"], ascending=[False] * len(keys) + [True, True, True]).iloc[0]
            s = sel.loc[(sel["branch"] == b) & (sel["test_year"] == f) & (sel["view"] == view)].iloc[0]
            add(f"selection_{b}_{f}_{view}", (s["bundle"], s["method"], s["formulation"]) == (w["bundle"], w["method"], w["formulation"]))
    plan = read(out / "selection" / "rounds_plan.csv")
    for (b, f), g in plan.groupby(["branch", "test_year"]):
        add(f"rounds_distinct_originals_{b}_{f}", g["scoring_round"].is_unique and 2 <= len(g) <= 3)
        for r in g.itertuples(index=False):
            add(f"calibration_before_round_{b}_{f}_{r.scoring_round}", all(ordl(c) < ordl(r.scoring_round) for c in str(r.calibration_rounds).split(";") if c and c != "nan"))
    add("original_rounds_have_no_copies", (plan.loc[plan["branch"] == "original", "n_copy_rows"] == 0).all())

    # (4) mappings rebuilt from saved OOF predictions
    oofp = read(out / "selection" / "oof_predictions.csv.gz", dtype={"bundle": str})
    maps = read(out / "fits" / "calibration_mappings.csv")
    st = status.drop_duplicates(["job_id", "branch", "view"]).set_index(["job_id", "branch", "view"])
    for r in maps.itertuples(index=False):
        if r.method == "none" or r.status != "ok":
            continue
        s = st.loc[(r.job_id, r.branch, r.view)]
        rounds = [ordl(x) for x in str(s["mapping_rounds"]).split(";") if x]
        form = "residual" if r.prediction_branch == "residual" else "direct"
        g = oofp.loc[(oofp["branch"] == r.branch) & (oofp["fold"] == s["test_year"]) & (oofp["horizon"] == s["horizon"]) & (oofp["formulation"] == form) & (oofp["bundle"] == s["bundle"]) & oofp["round"].isin(rounds)]
        rows = set(json.loads(r.fit_rows))
        g = g.loc[g["row"].isin(rows) & np.isfinite(g["raw_q3"])]
        y = prov[int(s["horizon"])]["q3"].to_numpy()[g["row"].to_numpy()]
        add(f"mapping_rows_{r.job_id}_{r.branch}_{r.view}_{r.prediction_branch}", len(g) == len(rows))
        o = s["receiving_origin"]
        add(f"mapping_rows_available_{r.job_id}_{r.branch}_{r.view}_{r.prediction_branch}", (g["target_ord"] <= ordl(o)).all())
        if r.method == "shift":
            add(f"mapping_shift_{r.job_id}_{r.branch}_{r.view}_{r.prediction_branch}", np.isclose(np.mean(g["raw_q3"].to_numpy() - y), r.shift, atol=1e-12))
        else:
            iso = IsotonicRegression(y_min=0, y_max=1, out_of_bounds="clip").fit(g["raw_q3"].to_numpy(), y)
            add(f"mapping_isotonic_{r.job_id}_{r.branch}_{r.view}_{r.prediction_branch}", np.allclose(iso.X_thresholds_, json.loads(r.isotonic_x)) and np.allclose(iso.y_thresholds_, json.loads(r.isotonic_y)))

    # (5) metrics and identical keys
    preds = read(out / "predictions" / "final_predictions.csv.gz")
    metrics = read(out / "metrics" / "metrics.csv")
    cohort = read(out / "ledgers" / "cohort_ledger.csv.gz")
    lk2 = ledger.set_index(["area_id", "target_ord"])
    for (year, h), keys in cohort.loc[cohort["status"] == "primary"].groupby(["test_year", "horizon"]):
        t = keys[["area_id", "target_ord"]].merge(ledger[["area_id", "target_ord", "q3", "actual_crisis"]], on=["area_id", "target_ord"])
        kk = {}
        for b in ("original", "augmented"):
            for v in ("D_direct", "D_residual", "D_selected"):
                p = preds.loc[(preds["test_year"] == year) & (preds["horizon"] == h) & (preds["label_branch"] == b) & (preds["view"] == v)]
                j = t.merge(p, on=["area_id", "target_ord"], how="left", suffixes=("", "_p"))
                add(f"coverage_{year}_h{h}_{b}_{v}", j["q3_raw"].notna().all())
                kk[(b, v)] = set(zip(p["area_id"], p["target_ord"]))
                row = metrics.loc[(metrics["test_year"] == year) & (metrics["horizon"] == h) & (metrics["branch"] == b) & (metrics["view"] == v) & (metrics["cohort"] == "primary")]
                if row.empty or j["q3_raw"].isna().any():
                    continue
                row = row.iloc[0]
                fin = j["q3_final"] if row["status"] == "ok" else j["q3_raw"].clip(0, 1)
                add(f"r2_{year}_h{h}_{b}_{v}", np.isclose(r2_score(j["q3"], fin), row["final_r2"], atol=1e-10))
                add(f"rmse_{year}_h{h}_{b}_{v}", np.isclose(np.sqrt(mean_squared_error(j["q3"], fin)), row["final_rmse"], atol=1e-10))
                if j["actual_crisis"].nunique() == 2:
                    add(f"auc_{year}_h{h}_{b}_{v}", np.isclose(roc_auc_score(j["actual_crisis"] == 1, fin), row["final_auc"], atol=1e-10))
        for v in ("D_direct", "D_residual", "D_selected"):
            add(f"identical_keys_{year}_h{h}_{v}", kk[("original", v)] == kk[("augmented", v)])

    # (6) bootstrap
    con = read(out / "metrics" / "contrasts.csv")
    draws = np.load(out / "metrics" / "bootstrap_draws.npz")
    for r in con.itertuples(index=False):
        key = f"y{r.test_year}_h{r.horizon:02d}_{r.contrast}__{r.metric}"
        if r.interval_status == "ok":
            lo, hi = np.quantile(draws[key], [0.025, 0.975], method="linear")
            add(f"bootstrap_{key}", np.isclose(lo, r.ci_low) and np.isclose(hi, r.ci_high))

    # (7) saved models reproduce saved raw predictions (H0 only; one feature matrix load)
    import xgboost as xgb

    inv = read(out / "models" / "model_inventory.csv")
    schema = json.loads((out / "features" / "feature_schema.json").read_text())
    fm0 = read(out / "features" / "feature_matrix_h00.csv.gz")
    cols = schema["h00_D"]
    for (job, b, v), g in inv.groupby(["job_id", "branch", "view"]):
        if not job.startswith("y") or "_h00_" not in job:
            continue
        p = preds.loc[(preds["job_id"] == job) & (preds["label_branch"] == b) & (preds["view"] == v)]
        X = p[["area_id", "target_ord"]].merge(fm0, on=["area_id", "target_ord"], how="left")[cols].to_numpy(dtype=np.float32)
        outp = {}
        for r in g.itertuples(index=False):
            path = out / "models" / r.path
            add(f"model_hash_{r.path}", hashlib.sha256(path.read_bytes()).hexdigest() == r.sha256)
            if r.kind == "xgboost":
                mm = xgb.XGBRegressor()
                mm.load_model(str(path))
                outp[r.target] = mm.predict(X).astype(float)
            else:
                outp[r.target] = np.full(len(X), json.loads(path.read_text())["value"])
        for t, c in (("q2", "q2_raw"), ("q4", "q4_raw"), ("q5", "q5_raw")):
            add(f"model_{job}_{b}_{v}_{t}", np.allclose(outp[t], p[c].to_numpy(), atol=1e-6))
        rec = outp["q3_direct"] if "q3_residual_delta" not in outp else np.where(p["branch"].to_numpy() == "residual", p["baseline_q3"].to_numpy() + outp["q3_residual_delta"], outp["q3_direct"])
        add(f"model_{job}_{b}_{v}_q3", np.allclose(rec, p["q3_raw"].to_numpy(), atol=1e-6))

    checks = pd.DataFrame(checks)
    checks.to_csv(out / "metrics" / "replay_checks.csv", index=False)
    failed = checks.loc[~checks["pass"]]
    print(f"replay checks: {len(checks) - len(failed)}/{len(checks)} passed")
    if len(failed):
        print(failed.head(30).to_string(index=False))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
