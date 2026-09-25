#!/usr/bin/env python3
"""Independent replay of the q3-first Somalia run from saved artifacts.

Recomputes, without importing q3opt/q3eval: (1) every candidate's validation RMSE
and AUC from saved scoring predictions and the label ledger; (2) the strict-RMSE
selection with the declared tie order; (3) primary-cohort final/raw q3 R2, RMSE,
bias and AUC with scikit-learn; (4) paired bootstrap intervals from saved
multiplicities; and chronology invariants in the OOF/final fit ledgers.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import mean_squared_error, r2_score, roc_auc_score

from ipcch import paths

OUT = paths.RESULTS_DIR / "experiments" / "somalia_oracle" / "v2_q3"
TOL = 1e-12


def read(path, **kw):
    # Exact float round-trip: pandas' default parser can perturb the last bit and split isotonic ties.
    return pd.read_csv(path, float_precision="round_trip", **kw)


def ordl(label: str) -> int:
    return int(label[:4]) * 12 + int(label[5:7]) - 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out-dir", type=Path, default=OUT)
    parser.add_argument("--v1-dir", type=Path, default=paths.RESULTS_DIR / "experiments" / "somalia_oracle" / "v1")
    args = parser.parse_args(argv)
    out = args.out_dir
    checks = []
    add = lambda name, ok, detail="": checks.append({"check": name, "pass": bool(ok), "detail": detail})

    ledger = read(args.v1_dir / "ledgers" / "label_ledger.csv.gz")[["area_id", "target_ord", "q3", "actual_crisis"]]
    prov = read(args.v1_dir / "ledgers" / "row_provenance_h00.csv.gz")[["area_id", "target_ord"]]
    sp = read(out / "selection" / "scoring_predictions.csv.gz")
    scores = read(out / "selection" / "candidate_scores.csv")
    sel = read(out / "selection" / "selected_recipes.csv")
    plan = read(out / "selection" / "scoring_plan.csv")

    # (1) candidate scores
    frame0 = prov.reset_index().rename(columns={"index": "row"})
    sp = sp.merge(frame0, on="row", suffixes=("", "_p")).merge(ledger, on=["area_id", "target_ord"])
    add("scoring_rows_match_provenance", (sp["target_ord"] == sp["target_ord_p"]).all() if "target_ord_p" in sp else True)
    rep = []
    for key, g in sp.groupby(["test_year", "view", "bundle", "method"]):
        rmse = float(np.sqrt(mean_squared_error(g["q3"], g["final_q3"])))
        auc = roc_auc_score(g["actual_crisis"] == 1, g["final_q3"]) if g["actual_crisis"].nunique() == 2 else np.nan
        rep.append(dict(zip(["test_year", "view", "bundle", "method"], key), rmse_rep=rmse, auc_rep=auc, n_rep=len(g), months=";".join(map(str, sorted(g["target_ord"].unique())))))
    rep = pd.DataFrame(rep)
    m = scores.loc[scores["status"] == "ok"].merge(rep, on=["test_year", "view", "bundle", "method"], how="left")
    add("all_ok_candidates_replayed", m["rmse_rep"].notna().all(), f"{int(m['rmse_rep'].isna().sum())} missing")
    add("candidate_rmse_replay", np.allclose(m["rmse"], m["rmse_rep"], atol=1e-12))
    add("candidate_auc_replay", np.allclose(m["auc"].fillna(-9), m["auc_rep"].fillna(-9), atol=1e-12))
    for year, g in plan.loc[plan["scoring_month"] != "FINAL_MAPPING"].groupby("test_year"):
        months = ";".join(str(ordl(x)) for x in sorted(g["scoring_month"]))
        add(f"scoring_months_fixed_{year}", (m.loc[m["test_year"] == year, "months"] == months).all())
        for cal, sc in zip(g["calibration_months"], g["scoring_month"]):
            add(f"calibration_before_scoring_{year}_{sc}", all(ordl(c) < ordl(sc) for c in str(cal).split(";") if c and c != "nan"))
    add("scoring_keys_identical_across_candidates", m.groupby("test_year")["n_rep"].nunique().max() == 1)

    # (2) selection
    order = {"none": 0, "shift": 1, "isotonic": 2}
    for (year, view), g in m.groupby(["test_year", "view"]):
        best = g["rmse"].min()
        tie = g.loc[g["rmse"] <= best + TOL].copy()
        tie["mo"], tie["bo"] = tie["method"].map(order), tie["bundle"].str[1].astype(int)
        keys, asc = (["auc"], [False]) if len(tie) > 1 and tie["auc"].notna().all() else ([], [])
        win = tie.sort_values(keys + ["mo", "bo"], ascending=asc + [True, True]).iloc[0]
        s = sel.loc[(sel["test_year"] == year) & (sel["view"] == view)].iloc[0]
        add(f"selection_{year}_{view}", (s["bundle"], s["method"]) == (win["bundle"], win["method"]))
    for year, g in m.loc[m["view"].isin(["D_direct", "D_residual"])].groupby("test_year"):
        s = sel.loc[(sel["test_year"] == year) & (sel["view"] == "D_selected")].iloc[0]
        add(f"selection_{year}_D_selected_min", abs(s["rmse"] - g["rmse"].min()) <= TOL)

    # (3) primary metrics
    preds = read(out / "predictions" / "final_predictions.csv.gz")
    cohort = read(out / "ledgers" / "cohort_ledger.csv.gz")
    metrics = read(out / "metrics" / "metrics.csv")
    prim = cohort.loc[cohort["status"] == "primary"]
    for (year, h), keys in prim.groupby(["test_year", "horizon"]):
        t = keys[["area_id", "target_ord"]].merge(ledger, on=["area_id", "target_ord"])
        for view in ("A", "B", "C", "D_direct", "D_residual", "D_selected"):
            p = preds.loc[(preds["test_year"] == year) & (preds["horizon"] == h) & (preds["view"] == view)]
            j = t.merge(p, on=["area_id", "target_ord"], how="left", suffixes=("", "_p"))
            add(f"coverage_{year}_h{h}_{view}", j["q3_raw"].notna().all(), f"{int(j['q3_raw'].isna().sum())} missing")
            row = metrics.loc[(metrics["test_year"] == year) & (metrics["horizon"] == h) & (metrics["view"] == view) & (metrics["cohort"] == "primary")]
            if row.empty or j["q3_raw"].isna().any():
                continue
            row = row.iloc[0]
            final = j["q3_final"] if row["status"] == "ok" else j["q3_raw"].clip(0, 1)
            add(f"final_r2_{year}_h{h}_{view}", np.isclose(r2_score(j["q3"], final), row["final_r2"], atol=1e-10))
            add(f"final_rmse_{year}_h{h}_{view}", np.isclose(np.sqrt(mean_squared_error(j["q3"], final)), row["final_rmse"], atol=1e-10))
            add(f"final_bias_{year}_h{h}_{view}", np.isclose((final - j["q3"]).mean(), row["final_bias"], atol=1e-10))
            add(f"raw_r2_{year}_h{h}_{view}", np.isclose(r2_score(j["q3"], j["q3_raw"]), row["raw_r2"], atol=1e-10))
            if j["actual_crisis"].nunique() == 2:
                add(f"final_auc_{year}_h{h}_{view}", np.isclose(roc_auc_score(j["actual_crisis"] == 1, final), row["final_auc"], atol=1e-10))
                add(f"binary_recall_{year}_h{h}_{view}", np.isclose(((final >= 0.2) & (j["actual_crisis"] == 1)).sum() / (j["actual_crisis"] == 1).sum(), row["bin_recall"], atol=1e-12))
            ok_final = j.loc[j["calibration_status"] == "ok", "q3_final"]
            add(f"final_bound_{year}_h{h}_{view}", ok_final.between(0, 1).all())

    # (4) chronology invariants
    oof = read(out / "selection" / "oof_fit_ledger.csv")
    ok = oof.loc[oof["status"] == "ok"]
    add("oof_fit_labels_before_cutoff", (ok["fit_max_target_ord"] <= ok["fit_label_cutoff_ord"]).all())
    add("oof_cutoff_h_and_self_exclusion", ((ok["fit_label_cutoff_ord"] <= ok["v"] - ok["horizon"]) & (ok["fit_label_cutoff_ord"] < ok["v"])).all())
    add("oof_labels_in_fold_window", (ok["fit_max_target_ord"] // 12 < ok["scope"]).all())
    status = read(out / "fits" / "final_status.csv")
    fits = read(out / "fits" / "final_fit_ledger.csv.gz").merge(status[["job_id", "view", "receiving_origin", "test_year"]].drop_duplicates(["job_id", "view"]), on=["job_id", "view"])
    add("final_fit_labels_before_origin", (fits["target_ord"] <= fits["receiving_origin"].map(ordl)).all())
    add("final_fit_labels_before_test_year", (fits["target_ord"] // 12 < fits["test_year"]).all())
    st = status.dropna(subset=["mapping_months"])
    add("mapping_months_before_origin", all(all(ordl(x) <= ordl(o) for x in str(mm).split(";") if x) for mm, o in zip(st["mapping_months"], st["receiving_origin"])))
    longh = status.loc[status["horizon"] > 0]
    add("long_horizon_flags_disclosed", (longh["selection_uses_later_labels"] == (longh["recipe_selection_max_label"].map(ordl) > longh["receiving_origin"].map(ordl))).all())

    # (5) bootstrap intervals
    contrasts = read(out / "metrics" / "contrasts.csv")
    draws = np.load(out / "metrics" / "bootstrap_draws.npz")
    for r in contrasts.itertuples(index=False):
        key = f"y{r.test_year}_h{r.horizon:02d}_{r.contrast}__{r.metric}"
        if r.interval_status == "ok":
            low, high = np.quantile(draws[key], [0.025, 0.975], method="linear")
            add(f"bootstrap_{key}", np.isclose(low, r.ci_low) and np.isclose(high, r.ci_high))
        mk = f"y{r.test_year}_h{r.horizon:02d}_{r.contrast}__multiplicities"
        if mk in draws.files:
            add(f"bootstrap_whole_area_{key}", (draws[mk].sum(axis=1) == r.n_areas).all())

    checks = pd.DataFrame(checks)
    (out / "metrics").mkdir(exist_ok=True)
    checks.to_csv(out / "metrics" / "replay_checks.csv", index=False)
    failed = checks.loc[~checks["pass"]]
    print(f"replay checks: {len(checks) - len(failed)}/{len(checks)} passed")
    if len(failed):
        print(failed.to_string(index=False))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
