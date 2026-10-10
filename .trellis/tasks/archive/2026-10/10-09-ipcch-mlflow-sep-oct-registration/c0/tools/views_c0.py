"""C0: enumerate evaluation views (detailed children) and candidate evaluation datasets from saved metric files."""
import json, sys
from pathlib import Path
import pandas as pd
REPO = Path(sys.argv[1]); OUT = Path(sys.argv[2]); SOM = REPO / "results/experiments/somalia_oracle"
A = {"A": "existing_predictors", "B": "seasonal_climate", "C": "weather_oracle", "D": "weather_oracle_with_share_history",
     "D_direct": "share_history_direct", "D_residual": "share_history_residual", "D_selected": "share_history_selected",
     "persistence": "phase_persistence", "phase_persistence": "phase_persistence", "share_persistence": "share_persistence",
     "always_crisis": "always_crisis", "v1_D_raw": "reference_weather_oracle_with_share_history_raw",
     "v1_D_isotonic": "reference_weather_oracle_with_share_history_isotonic",
     "climate_no_history": "no_ipc_history", "climate_safe_history": "safe_ipc_history", "climate_safe_history_idp": "safe_ipc_history_idp",
     "climate_safe_history_idp_oracle": "weather_oracle", "climate_safe_history_idp_oracle_b6": "weather_oracle_with_summaries",
     "compact_baseline": "baseline", "compact_weather_oracle": "weather_oracle", "compact_cds_weather": "cds_weather"}
FIT = {"existing_predictors", "seasonal_climate", "weather_oracle", "weather_oracle_with_share_history", "share_history_direct",
       "share_history_residual", "share_history_selected", "calibrated_share_history", "no_ipc_history", "safe_ipc_history",
       "safe_ipc_history_idp", "weather_oracle_with_summaries", "baseline", "cds_weather"}
V, DS = [], []
def view(src, fam, arm, h, kind, periods, cohorts):
    V.append({"source_key": src, "family": fam, "arm": arm, "lead_months": f"{int(h):02d}", "view_kind": kind,
              "period_roles": ";".join(periods), "cohorts": ";".join(cohorts)})
def kind(arm, h, fam):
    if arm not in FIT: return "metric_only"
    if int(h) == 0 and ((arm == "weather_oracle" and fam.startswith(("somalia_oracle", "somalia_q3", "compact"))) or arm == "cds_weather"):
        return "alias_h0_shared"
    return "fitted"
# Somalia v1
m = pd.read_csv(SOM / "v1/metrics/metrics.csv"); m = m[m.specification != "all"]
for (s, h), g in m.groupby(["specification", "horizon"]):
    arm = A[s]; view("somalia_oracle_v1", "somalia_oracle_information", arm, h, kind(arm, h, "somalia_oracle"),
                     sorted({f"year_{y}" for y in g.test_year}), sorted(set(g.cohort)))
for (y, h, c), g in m.groupby(["test_year", "horizon", "cohort"]):
    DS.append({"source_key": "somalia_oracle_v1", "truth_group": "somalia_v1_observed", "lead": h, "period": f"year_{y}", "cohort": c, "n": g.n_rows.dropna().unique().tolist()})
# v2
m = pd.read_csv(SOM / "v2_q3/metrics/metrics.csv"); m = m[m.view != "all"]
for (s, h), g in m.groupby(["view", "horizon"]):
    arm = A[s]; view("somalia_oracle_v2_q3", "somalia_q3_optimization", arm, h, kind(arm, h, "somalia_q3"), sorted({f"year_{y}" for y in g.test_year}), sorted(set(g.cohort)))
for (y, h, c), g in m.groupby(["test_year", "horizon", "cohort"]):
    DS.append({"source_key": "somalia_oracle_v2_q3", "truth_group": "somalia_v2_target_corrected", "lead": h, "period": f"year_{y}", "cohort": c, "n": g.n.dropna().unique().tolist()})
# v3
m = pd.read_csv(SOM / "v3_validity/metrics/metrics.csv"); m = m[m.view != "all"]
for (b, s, h), g in m.groupby(["branch", "view", "horizon"]):
    arm = A[s]
    fams = {"original": ["somalia_validity_observed"], "augmented": ["somalia_validity_augmented"]}.get(b, ["somalia_validity_observed", "somalia_validity_augmented"])
    for fam in fams:
        view("somalia_oracle_v3_validity", fam, arm, h, kind(arm, h, fam), sorted({f"year_{y}" for y in g.test_year}), sorted(set(g.cohort)))
for (y, h, c), g in m.groupby(["test_year", "horizon", "cohort"]):
    DS.append({"source_key": "somalia_oracle_v3_validity", "truth_group": "somalia_v3_raw_original_eval", "lead": h, "period": f"year_{y}", "cohort": c, "n": g.n.dropna().unique().tolist()})
# v4
a = pd.read_csv(SOM / "v4_calibrated_d/metrics/annual_metrics.csv"); p = pd.read_csv(SOM / "v4_calibrated_d/metrics/pooled_metrics.csv")
for (s, h), g in a.groupby(["data_setting", "horizon"]):
    fam = {"original": "somalia_calibrated_observed", "augmented": "somalia_calibrated_augmented"}[s]
    st = ";".join(f"{y}:{t}" for y, t in zip(g.outer_year, g.status))
    view("somalia_oracle_v4_calibrated_d", fam, "calibrated_share_history", h, "fitted", ["pooled_2022_2026"] + [f"year_{y}" for y in sorted(g.outer_year)], ["primary"])
    V[-1]["slot_status"] = st + "; pooled:" + ";".join(p[(p.data_setting == s) & (p.horizon == h)].status)
for (s, y, h), g in a.groupby(["data_setting", "outer_year", "horizon"]):
    DS.append({"source_key": "somalia_oracle_v4_calibrated_d", "truth_group": f"somalia_v4_{s}_eval", "lead": h, "period": f"year_{y}", "cohort": "primary", "n": g.n.dropna().unique().tolist(), "status": g.status.iloc[0]})
for (s, h), g in p.groupby(["data_setting", "horizon"]):
    DS.append({"source_key": "somalia_oracle_v4_calibrated_d", "truth_group": f"somalia_v4_{s}_eval", "lead": h, "period": "pooled_2022_2026", "cohort": "primary", "n": g.n.dropna().unique().tolist(), "status": g.status.iloc[0]})
# modern historical (global)
for src, root, fam in (("origin_safe_climate_idp_v1", "results/experiments/origin_safe_climate_idp_v1", "origin_safe_climate_global"),
                       ("origin_safe_weather_oracle_v1", "results/experiments/origin_safe_weather_oracle_v1", "origin_safe_weather_global"),
                       ("compact_global_original", "results/experiments/compact_climate_weather_oracle_v1", "compact_climate_global")):
    for f in sorted((REPO / root / "runs").glob("*/*m/metrics/metrics_overall.csv")):
        arm, h = A[f.parts[-4]], f.parts[-3][:-1]
        d = pd.read_csv(f)
        view(src, fam, arm, h, kind(arm, h, fam), ["pooled_2022_2025"] + [f"year_{y}" for y in d.test_year if y != "pooled"], ["all_scored"])
        for y, n in zip(d.test_year, d.n_samples):
            DS.append({"source_key": src, "truth_group": "global_origin_safe_eval", "lead": h, "period": "pooled_2022_2025" if y == "pooled" else f"year_{y}", "cohort": "all_scored", "n": [n]})
    if src == "origin_safe_weather_oracle_v1":
        for h in ("0", "3", "6", "12"):
            view(src, fam, "reference_safe_ipc_history_idp", h, "metric_only_reference_to_other_source", ["pooled_2022_2025", "year_2022..2025"], ["all_scored", "region_southern_africa_global_model(region3)"])
    if src == "compact_global_original":
        view(src, fam, "weather_oracle", "0", "alias_h0_shared", ["pooled_2022_2025", "year_2022..2025"], ["all_scored"])
# compact extensions and SOM local historical
for src, f, fam in (("compact_somalia_original", "results/experiments/compact_climate_weather_oracle_v1_somalia_local/report/som_metrics_long.csv", "compact_climate_somalia"),
                    ("compact_global_2026_extension", "results/experiments/compact_climate_weather_oracle_eval_2026_jan_apr_v1/report/all_metrics_long.csv", "compact_climate_global"),
                    ("compact_somalia_2026_extension", "results/experiments/compact_climate_weather_oracle_eval_2026_jan_apr_v1_somalia_local/report/som_metrics_long.csv", "compact_climate_somalia")):
    d = pd.read_csv(REPO / f)
    d["cohort"] = d.apply(lambda r: "all_scored" if r.scope in ("global", "SOM") else f"region_{str(r.region_name).lower().replace(' ', '_')}_global_model", axis=1)
    for (arm, h), g in d.groupby(["arm", "horizon"]):
        view(src, fam, A[arm], h, kind(A[arm], h, fam), sorted({str(x) if str(x).startswith("pooled") else f"year_{x}" for x in g.period}), sorted(set(g.cohort)))
    if not (d.arm.eq("compact_weather_oracle") & d.horizon.eq(0)).any():
        view(src, fam, "weather_oracle", "0", "alias_h0_shared", ["(same as baseline 0-month)"], ["(same as baseline 0-month)"])
    for (per, h, c), g in d.groupby(["period", "horizon", "cohort"]):
        pr = str(per) if str(per).startswith("pooled") else f"year_{per}"
        if pr == "pooled": pr = "pooled_2022_2025"
        DS.append({"source_key": src, "truth_group": "som_local_eval" if "somalia" in src else "global_origin_safe_eval", "lead": str(h), "period": pr, "cohort": c, "n": sorted(g.n_rows.dropna().astype(int).unique().tolist())})
# launches
for src, fam in (("compact_global_launch", "compact_launch_global"), ("compact_somalia_launch", "compact_launch_somalia")):
    for arm, h in (("baseline", 0), ("baseline", 6), ("baseline", 12), ("cds_weather", 6), ("cds_weather", 12), ("cds_weather", 0)):
        view(src, fam, arm, h, "alias_h0_shared" if (arm == "cds_weather" and h == 0) else "fitted", ["prediction_summary"], ["launch_population"])
VV = pd.DataFrame(V); VV.to_csv(OUT / "views_expected.csv", index=False)
D = pd.DataFrame(DS); D["n"] = D["n"].astype(str)
D.to_csv(OUT / "eval_dataset_candidates.csv", index=False)
latest = VV[~VV.source_key.isin(["compact_global_original", "compact_somalia_original"])]
summary = {"detailed_parents": int(VV.source_key.nunique()), "detailed_children": len(VV),
           "children_by_kind": VV.view_kind.value_counts().to_dict(), "children_by_source": VV.groupby("source_key").size().to_dict(),
           "dashboard_rows_latest": len(latest), "dashboard_rows_by_family": latest.groupby("family").size().to_dict(),
           "eval_dataset_candidate_rows": len(D),
           "eval_dataset_unique_keys(truth_group,lead,period,cohort)": int(D.drop_duplicates(["truth_group", "lead", "period", "cohort"]).shape[0]),
           "same_key_different_n": D.groupby(["truth_group", "lead", "period", "cohort"]).n.nunique().gt(1).sum().item(),
           "launch_inference_descriptors": 10, "training_pool_descriptors_proposed": "one per family x lead (see report)"}
(OUT / "views_counts.json").write_text(json.dumps(summary, indent=1, default=str)); print(json.dumps(summary, indent=1, default=str))
