"""C0 planning builder (read-only over sources; writes only into this task's c0/ directory).

Inputs: the source hash CSV from hash_sources.py, the 12 allowlisted roots, saved
model inventories / batch records / metric files. Outputs (c0/):
  source_inventory.csv  every file under the 12 roots + role + proposed decision
  model_members.csv     every logical model-version member (fitted file or explicit alias)
  metric_map.csv        every metric column of every selected metric file -> readable leaf
  expected_counts.json  frozen object counts per level
Not integration code: it is planning evidence for supervisor checkpoint C0.
"""
import csv, json, re, sys
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd
from pandas.api.types import is_numeric_dtype

REPO = Path(sys.argv[1]); HASHES = Path(sys.argv[2]); OUT = Path(sys.argv[3])
SRC = {r["source_key"]: r for r in csv.DictReader(open(OUT.parent / "sources.csv"))}
SOM = "results/experiments/somalia_oracle"
LEADS = ("0", "3", "6", "12")

# ------------------------------------------------------------ vocabulary (proposal; naming.md authority)
FAMILY = {  # (source_key, setting) -> (slug, short title, scope, stage, label_setting)
    ("somalia_oracle_v1", None): ("somalia_oracle_information", "Somalia oracle information historical", "somalia_local", "historical", None),
    ("somalia_oracle_v2_q3", None): ("somalia_q3_optimization", "Somalia q3 optimization historical", "somalia_local", "historical", None),
    ("somalia_oracle_v3_validity", "original"): ("somalia_validity_observed", "Somalia validity observed-label historical", "somalia_local", "historical", "observed"),
    ("somalia_oracle_v3_validity", "augmented"): ("somalia_validity_augmented", "Somalia validity augmented-training historical", "somalia_local", "historical", "training_augmented"),
    ("somalia_oracle_v4_calibrated_d", "original"): ("somalia_calibrated_observed", "Somalia calibrated observed-label historical", "somalia_local", "historical", "observed"),
    ("somalia_oracle_v4_calibrated_d", "augmented"): ("somalia_calibrated_augmented", "Somalia calibrated augmented-label historical", "somalia_local", "historical", "role_augmented"),
    ("origin_safe_climate_idp_v1", None): ("origin_safe_climate_global", "Origin-safe climate global historical", "global", "historical", None),
    ("origin_safe_weather_oracle_v1", None): ("origin_safe_weather_global", "Origin-safe weather global historical", "global", "historical", None),
    ("compact_global_original", None): ("compact_climate_global", "Compact climate global historical", "global", "historical", None),
    ("compact_global_2026_extension", None): ("compact_climate_global", "Compact climate global historical", "global", "historical", None),
    ("compact_somalia_original", None): ("compact_climate_somalia", "Compact climate Somalia-local historical", "somalia_local", "historical", None),
    ("compact_somalia_2026_extension", None): ("compact_climate_somalia", "Compact climate Somalia-local historical", "somalia_local", "historical", None),
    ("compact_global_launch", None): ("compact_launch_global", "Compact climate global launch", "global", "launch", None),
    ("compact_somalia_launch", None): ("compact_launch_somalia", "Compact climate Somalia-local launch", "somalia_local", "launch", None),
}
ARM = {
    "A": "existing_predictors", "B": "seasonal_climate", "C": "weather_oracle", "D": "weather_oracle_with_share_history",
    "D_direct": "share_history_direct", "D_residual": "share_history_residual", "D_selected": "share_history_selected",
    "D_calibrated": "calibrated_share_history",
    "climate_no_history": "no_ipc_history", "climate_safe_history": "safe_ipc_history", "climate_safe_history_idp": "safe_ipc_history_idp",
    "climate_safe_history_idp_oracle": "weather_oracle", "climate_safe_history_idp_oracle_b6": "weather_oracle_with_summaries",
    "compact_baseline": "baseline", "compact_weather_oracle": "weather_oracle", "compact_cds_weather": "cds_weather",
}
METRIC_ONLY = {  # metric-only views; never registered
    "persistence": "phase_persistence", "phase_persistence": "phase_persistence", "share_persistence": "share_persistence",
    "always_crisis": "always_crisis", "v1_D_raw": "reference_weather_oracle_with_share_history_raw",
    "v1_D_isotonic": "reference_weather_oracle_with_share_history_isotonic",
    "reference:climate_safe_history_idp": "reference_safe_ipc_history_idp",
}
ROLE = {"existing_predictors": "baseline", "seasonal_climate": "candidate", "weather_oracle": "candidate",
        "weather_oracle_with_share_history": "candidate", "share_history_direct": "candidate", "share_history_residual": "candidate",
        "share_history_selected": "candidate", "calibrated_share_history": "candidate", "no_ipc_history": "baseline",
        "safe_ipc_history": "candidate", "safe_ipc_history_idp": "candidate", "weather_oracle_with_summaries": "candidate",
        "baseline": "baseline", "cds_weather": "candidate"}


def lead_label(h): return f"{int(h)}-month"
def lead_tag(h): return f"{int(h):02d}"


# ------------------------------------------------------------ 1. source inventory with roles/decisions
hashes = pd.read_csv(HASHES)
def role(p):
    n = p.split("/")[-1]
    if n.endswith(".ubj"): return "booster", "bundle:models.tar"
    if "/superseded_build1/" in p: return "superseded_build", "exclude:superseded pre-fit input build (no fitted model); recorded in excluded manifest"
    if n.endswith((".pid",)): return "process_pid", "exclude:process id file, no content value"
    if "/logs/" in p: return "log", "archive:logs"
    if "/inputs/approved_spec/" in p or "/parent_contract/" in p: return "approved_spec_copy", "archive:inputs"
    if "/metrics/" in p or "/report/" in p or n in ("verification.json", "report_outputs.json") or "/region3/" in p: return "metric_or_report", "archive:metrics (values extracted by explicit field selection)"
    if "/population/" in p: return "launch_prediction_summary", "archive:population"
    if "/predictions" in p or n.startswith("predictions") or "final_predictions" in n: return "predictions", "archive:predictions"
    if "batch_record.json" in n or "artifact_record.json" in n or n == "run_metadata.json" or "model_inventory" in n or "feature_schema" in n or n in ("fit_keys.csv.gz", "fit_targets.csv.gz", "fit_weights.csv.gz"):
        return "model_recipe_member", "bundle:models.tar"
    if "/features/" in p or "inference_features" in n or "/inference/" in p: return "feature_matrix", "archive:features"
    if "/fits/" in p or "/selection/" in p: return "fit_selection_calibration", "bundle:models.tar (calibration/selection members)"
    if "/ledgers/" in p or "/input_checks/" in p or "/preflight/" in p or "/input_verification/" in p or "/verification/" in p or "/replay/" in p or "/scope/" in p or "/diagnostics/" in p or "/visualizations/" in p or "/training/" in p or "/inputs/" in p or n.endswith("manifest.json"):
        return "ledger_or_check", "archive:ledgers"
    return "other", "UNRESOLVED"
hashes[["role", "decision"]] = [role(p) for p in hashes.path]
# mixed-content scan: excluded families named inside allowlisted files (text only, small files)
EXCL = re.compile(r"climate2015|nigeria_weather_land|nigeria_identifier|nigeria.{0,20}sep(?:tember)?.?18", re.I)
flags = []
for p, b in zip(hashes.path, hashes.bytes):
    hit = ""
    if b < 20_000_000 and not p.endswith((".ubj", ".gz", ".npz", ".xlsx", ".png")):
        try:
            txt = (REPO / p).read_text(errors="ignore")
            m = EXCL.findall(txt)
            hit = ";".join(sorted(set(x.lower() for x in m)))
        except OSError:
            hit = "unreadable"
    flags.append(hit)
hashes["excluded_family_mentions"] = flags
hashes.to_csv(OUT / "source_inventory.csv", index=False)

# ------------------------------------------------------------ 2. model members
mem = []
def add(source, setting, arm_raw, h, member_kind, path, sha, year=None, origin=None, target=None, alias_of=None, note=""):
    fam = FAMILY[(source, setting)]
    mem.append({"source_key": source, "family": fam[0], "family_title": fam[1], "arm_raw": arm_raw, "arm": ARM[arm_raw],
                "lead_months": lead_tag(h), "year": year, "origin": origin, "target": target, "member_kind": member_kind,
                "path": path, "sha256": sha, "alias_of_path": alias_of, "note": note})
hmap = dict(zip(hashes.path, hashes.sha256))

def jparse(j):
    m = re.match(r"(?:(original|augmented)_)?y(\d{4})_h(\d\d)_o(\d{4}-\d\d)", j)
    return m.group(1), m.group(2), str(int(m.group(3))), m.group(4)

d = pd.read_csv(REPO / SOM / "v1/models/model_inventory.csv")
seen = set()
for r in d.itertuples():
    _, y, h, o = jparse(r.job_id); p = f"{SOM}/v1/models/{r.path}"
    if (r.job_id, r.arm, r.target) in seen:  # inventory repeats the B rows for H0 C (pipeline.py:354-363 clone)
        add("somalia_oracle_v1", None, "C", h, "alias_h0_clone_of_B", p, r.sha256, y, o, r.target, p, "H0 C clones B; inventory lists the B file twice")
    else:
        seen.add((r.job_id, r.arm, r.target))
        add("somalia_oracle_v1", None, r.arm, h, "fitted", p, r.sha256, y, o, r.target)
d = pd.read_csv(REPO / SOM / "v2_q3/models/model_inventory.csv")
for r in d.itertuples():
    _, y, h, o = jparse(r.job_id); p = f"{SOM}/v2_q3/models/{r.path}"
    add("somalia_oracle_v2_q3", None, r.view, h, "fitted", p, r.sha256, y, o, r.target, note=f"bundle {r.bundle}")
    if r.view == "D_residual":  # selected_recipes.csv: D_selected = D_residual recipe in 2025 and 2026 (reuse_source)
        add("somalia_oracle_v2_q3", None, "D_selected", h, "alias_selected_recipe", p, r.sha256, y, o, r.target, p, "D_selected reuses D_residual fits (run_somalia_q3_optimization.py:86-94)")
for r in d[(d.view == "B") & d.job_id.str.contains("_h00_")].itertuples():
    _, y, h, o = jparse(r.job_id); p = f"{SOM}/v2_q3/models/{r.path}"
    add("somalia_oracle_v2_q3", None, "C", h, "alias_h0_clone_of_B", p, r.sha256, y, o, r.target, p, "H0 C reused from B")
d = pd.read_csv(REPO / SOM / "v3_validity/models/model_inventory.csv")
for r in d.itertuples():
    _, y, h, o = jparse(r.job_id)
    add("somalia_oracle_v3_validity", r.branch, r.view, h, "fitted", f"{SOM}/v3_validity/models/{r.path}", r.sha256, y, o, r.target)
d = pd.read_csv(REPO / SOM / "v4_calibrated_d/models/model_inventory.csv")
for r in d.itertuples():
    s, y, h, o = jparse(r.job_id)
    add("somalia_oracle_v4_calibrated_d", s, "D_calibrated", h, "fitted", f"{SOM}/v4_calibrated_d/models/{r.path}", r.sha256, y, o, r.target)

def batches(source, root):
    out = []
    for p in sorted(hashes.loc[hashes.source_key == source, "path"]):
        m = re.search(r"/runs/([^/]+)/(\d+)m/(?:batches/(\d{4})/)?model_(phase\d_worse)\.ubj$", p)
        if m: out.append((m.group(1), m.group(2), m.group(3), m.group(4), p))
    return out
for src in ("origin_safe_climate_idp_v1", "origin_safe_weather_oracle_v1", "compact_global_original", "compact_somalia_original",
            "compact_global_2026_extension", "compact_somalia_2026_extension", "compact_global_launch", "compact_somalia_launch"):
    for arm_raw, h, y, tgt, p in batches(src, None):
        add(src, None, arm_raw, h, "fitted", p, hmap[p], y, None, tgt)
# extensions: version = original 2022-2025 members (reused, not refit) + own 2026 fits
for ext, orig in (("compact_global_2026_extension", "compact_global_original"), ("compact_somalia_2026_extension", "compact_somalia_original")):
    for m in [x for x in mem if x["source_key"] == orig and x["member_kind"] == "fitted"]:
        add(ext, None, m["arm_raw"], m["lead_months"].lstrip("0") or "0", "reused_from_original_snapshot", m["path"], m["sha256"], m["year"], None, m["target"], m["path"],
            "2022-2025 weights reused; run_compact_eval_2026_extension.py:817-826")
# H0 oracle/CDS views share the baseline H0 fit (no registered model; alias view only)
for src, oracle in (("compact_global_original", "compact_weather_oracle"), ("compact_somalia_original", "compact_weather_oracle"),
                    ("compact_global_2026_extension", "compact_weather_oracle"), ("compact_somalia_2026_extension", "compact_weather_oracle"),
                    ("compact_global_launch", "compact_cds_weather"), ("compact_somalia_launch", "compact_cds_weather")):
    for m in [x for x in mem if x["source_key"] == src and x["arm_raw"] == "compact_baseline" and x["lead_months"] == "00"]:
        add(src, None, oracle, "0", "alias_shared_h0_baseline", m["path"], m["sha256"], m["year"], None, m["target"], m["path"], "H0 shared baseline fit")
M = pd.DataFrame(mem)
M.to_csv(OUT / "model_members.csv", index=False)

# ------------------------------------------------------------ 3. metric map (explicit file x column)
NON_METRIC = re.compile(r"(_status|_reason|^status$|^reason$|cohort_sha256|target_months|^within_month_auc_months$|^within_month_auc_undefined_months$|rows_by_year|^years$|bootstrap_bundle|^contrast$|^metric$|interval_status|interval_type|ci_status|point_status|^specification$|^view$|^branch$|^cohort$|^arm$|^benchmark$|^method$|^scope$|^region(_name)?$|^period$|^run_id$|^test_year$|^outer_year$|^horizon$|^data_setting$|^first_calibration$|^second_calibration$|^diagnostic_only$|^comparison_complete$|^version$|^display_arm$|^source_run_id$|^shared_h0_fit$|^origin_month$|^target_month$|^country$|^model_scope$|^delta_status$)")
LEAF = {  # source column -> readable leaf (Somalia + modern)
    "exact_phase_accuracy": "five_class.accuracy", "phase3plus_accuracy": "binary.accuracy", "precision_phase3plus": "binary.precision",
    "sensitivity_phase3plus": "binary.recall", "f2_phase3plus": "binary.f2", "r2_phase3plus": "share_phase3plus_r2",
    "mae_phase3plus": "share_phase3plus_mae", "ordinal_mae": "five_class.ordinal_mae", "n_samples": "n_rows", "n": "n_rows", "n_rows": "n_rows",
    "n_areas": "n_areas", "n_countries": "n_countries",
    # Somalia v1 (binary crisis on phase from shares; r2 on q3)
    "tp": "binary.count.tp", "fp": "binary.count.fp", "fn": "binary.count.fn", "tn": "binary.count.tn", "precision": "binary.precision",
    "recall": "binary.recall", "f1": "binary.f1", "f2": "binary.f2", "accuracy": "five_class.accuracy",  # somalia_oracle/evaluation.py:63-65 exact overall_phase == phase_pred
    "prevalence": "binary.observed_prevalence", "predicted_prevalence": "binary.predicted_prevalence", "r2_q3": "share_phase3plus_r2",
    "mean_q3_pred": "share_phase3plus_mean_pred", "macro_f1": "five_class.macro_f1", "p4plus_recall": "binary_phase4plus.recall",
    "pred_p3_share": "binary.predicted_prevalence", "r2_n": "share_phase3plus_r2_n_rows", "auc_crisis": "binary.auc_pooled",
    "within_month_auc": "binary.auc_within_month",
    # Somalia v2-v4 raw/final share and AUC families stay distinct
    **{f"{s}_{m}": f"share_phase3plus_{s}.{m}" for s in ("raw", "final") for m in ("r2", "rmse", "mae", "bias", "mean_truth", "mean_pred")},
    "raw_auc": "binary.auc_pooled_raw", "final_auc": "binary.auc_pooled_final", "final_within_month_auc": "binary.auc_within_month_final",
    "raw_within_month_auc": "binary.auc_within_month_raw",
    **{f"bin_{m}": f"binary.{m}" for m in ("f1", "recall", "precision", "f2")}, **{f"bin_{c}": f"binary.count.{c}" for c in ("tp", "fp", "fn", "tn")},
    "legacy_phase_accuracy": "five_class.accuracy", "legacy_multiclass_macro_f1": "five_class.macro_f1",
    **{f"legacy_{m}": f"legacy_phase_binary.{m}" for m in ("f1", "recall", "precision", "f2")}, **{f"legacy_{c}": f"legacy_phase_binary.count.{c}" for c in ("tp", "fp", "fn", "tn")},
    "q3_binary_vs_legacy_disagreements": "binary.disagreements_vs_legacy_phase", "n_clipped": "share_phase3plus_n_clipped",
    "n_fallback_direct": "n_rows_fallback_direct", "n_residual_branch": "n_rows_residual_branch", "n_primary": "n_rows_primary_cohort",
    "n_wider_only": "n_rows_wider_only", "n_excluded": "n_rows_excluded", "n_cohort": "n_rows_cohort", "n_months": "n_target_months",
    "n_original_reports": "n_original_reports", "n_originals": "n_rows_original", "n_copies": "n_rows_copies",
    "n_actual_phase1": "five_class.count.observed_phase1", **{f"n_actual_phase{k}": f"five_class.count.observed_phase{k}" for k in range(1, 6)},
    **{f"n_pred_phase{k}": f"five_class.count.predicted_phase{k}" for k in range(1, 6)},
    # contrasts / intervals (saved only)
    "point_delta_f2": "delta.binary.f2", "point_delta": "delta.<metric>", "delta": "delta.<metric>", "ci_low": "delta.<metric>.ci_low",
    "ci_high": "delta.<metric>.ci_high", "ci_lower": "delta.<metric>.ci_low", "ci_upper": "delta.<metric>.ci_high",
    "valid_draws": "delta.<metric>.draws_valid", "undefined_draws": "delta.<metric>.draws_undefined", "draws_total": "delta.<metric>.draws_total",
    "draws_valid": "delta.<metric>.draws_valid", "draws_invalid": "delta.<metric>.draws_invalid", "invalid_fraction": "delta.<metric>.invalid_fraction",
    "min_valid_draws": "delta.<metric>.min_valid_draws", "oracle_value": "SKIP:duplicate of arm metric (cross-checked equal)",
    "baseline_value": "SKIP:duplicate of arm metric (cross-checked equal)", "value": "<metric>",
    "observed_3plus": "binary.count.observed_positive", "observed_1_2": "binary.count.observed_negative", "predicted_3plus": "binary.count.predicted_positive",
    "true_positive_3plus": "binary.count.tp", "distinct_phase3_worse": "share_phase3plus_n_distinct_truth",
    "oracle_predicted_3plus": "SKIP:in arm row", "baseline_predicted_3plus": "SKIP:in arm row",
}
LAUNCH = re.compile(r"^(delta_)?(count|share)_(raw|effective)_(phase\d|p3plus|p4plus)$|^population_(raw|effective)$|^n_(zero_population_areas|capped_areas)$")
METRIC_FILES = {
    "somalia_oracle_v1": [f"{SOM}/v1/metrics/metrics.csv", f"{SOM}/v1/metrics/contrasts.csv", f"{SOM}/v1/diagnostics/discrimination_auc.csv",
                          f"{SOM}/v1/diagnostics/calibrated_d_vs_benchmarks.csv", f"{SOM}/v1/diagnostics/calibrated_d_vs_benchmarks_contrasts.csv",
                          f"{SOM}/v1/diagnostics/calibration_threshold_metrics.csv"],
    "somalia_oracle_v2_q3": [f"{SOM}/v2_q3/metrics/metrics.csv", f"{SOM}/v2_q3/metrics/contrasts.csv"],
    "somalia_oracle_v3_validity": [f"{SOM}/v3_validity/metrics/metrics.csv", f"{SOM}/v3_validity/metrics/contrasts.csv"],
    "somalia_oracle_v4_calibrated_d": [f"{SOM}/v4_calibrated_d/metrics/annual_metrics.csv", f"{SOM}/v4_calibrated_d/metrics/pooled_metrics.csv"],
    "origin_safe_climate_idp_v1": sorted(p for p in hashes.path if p.startswith("results/experiments/origin_safe_climate_idp_v1/") and p.endswith("/metrics/metrics_overall.csv")),
    "origin_safe_weather_oracle_v1": sorted(p for p in hashes.path if p.startswith("results/experiments/origin_safe_weather_oracle_v1/runs/") and p.endswith("/metrics/metrics_overall.csv"))
        + ["results/experiments/origin_safe_weather_oracle_v1/verification/global_comparison_baseline_first.csv",
           "results/experiments/origin_safe_weather_oracle_v1/region3/region3_metrics.csv",
           "results/experiments/origin_safe_weather_oracle_v1/region3/region3_paired_intervals.csv"],
    "compact_global_original": sorted(p for p in hashes.path if p.startswith("results/experiments/compact_climate_weather_oracle_v1/runs/") and p.endswith("/metrics/metrics_overall.csv")),
    "compact_somalia_original": ["results/experiments/compact_climate_weather_oracle_v1_somalia_local/report/som_metrics_long.csv",
                                 "results/experiments/compact_climate_weather_oracle_v1_somalia_local/report/som_oracle_minus_baseline_deltas.csv"],
    "compact_global_2026_extension": ["results/experiments/compact_climate_weather_oracle_eval_2026_jan_apr_v1/report/all_metrics_long.csv",
                                      "results/experiments/compact_climate_weather_oracle_eval_2026_jan_apr_v1/report/global_deltas.csv",
                                      "results/experiments/compact_climate_weather_oracle_eval_2026_jan_apr_v1/report/regional_deltas.csv"],
    "compact_somalia_2026_extension": ["results/experiments/compact_climate_weather_oracle_eval_2026_jan_apr_v1_somalia_local/report/som_metrics_long.csv",
                                       "results/experiments/compact_climate_weather_oracle_eval_2026_jan_apr_v1_somalia_local/report/som_oracle_minus_baseline_deltas.csv"],
    "compact_global_launch": [f"results/launch/nowcasting_2026_04_compact_cds_v1/population/{f}.csv" for f in (
        "global_population_summary", "global_population_paired_differences", "regional_population_summary", "region_population_paired_differences",
        "country_population_summary", "country_population_paired_differences")],
    "compact_somalia_launch": [f"results/launch/nowcasting_2026_04_compact_cds_v1_somalia_local/population/{f}.csv" for f in (
        "som_population_summary", "som_population_paired_differences")],
}
mrows = []
for src, files in METRIC_FILES.items():
    for f in files:
        df = pd.read_csv(REPO / f)
        long = "metric" in df.columns and ("value" in df.columns or "point_delta" in df.columns or "delta" in df.columns)
        for c in df.columns:
            if NON_METRIC.search(c) or not is_numeric_dtype(df[c]):
                continue
            leaf = LEAF.get(c)
            if leaf is None and LAUNCH.match(c):
                leaf = "prediction_summary." + c.replace("delta_", "paired_difference.") if c.startswith("delta_") else "prediction_summary." + c
            leaf = leaf or "UNRESOLVED:no naming rule"
            sub = [(None, df)] if not long else list(df.groupby("metric"))
            for mname, part in sub:
                col = part[c]
                lf = leaf.replace("<metric>", LEAF.get(mname, mname)) if mname else leaf
                if mname and c == "value":
                    lf = LEAF.get(mname, "UNRESOLVED:" + str(mname))
                mrows.append({"source_key": src, "file": f, "column": c, "long_metric": mname, "readable_leaf": lf,
                              "diagnostic_only": bool(re.search("LEAKY", " ".join(map(str, part.get("method", pd.Series([], dtype=str)).unique())))),
                              "rows": len(part), "finite": int(pd.to_numeric(col, errors="coerce").notna().sum()),
                              "na": int(pd.to_numeric(col, errors="coerce").isna().sum())})
MM = pd.DataFrame(mrows)
MM.to_csv(OUT / "metric_map.csv", index=False)

# ------------------------------------------------------------ 4. counts
counts = {"source_roots": len(SRC), "source_files_hashed": int(len(hashes)), "source_bytes": int(hashes.bytes.sum()),
          "booster_files": int((hashes.role == "booster").sum()),
          "booster_distinct_sha256": int(hashes.loc[hashes.role == "booster", "sha256"].nunique()),
          "booster_files_by_source": {k: int(v) for k, v in hashes[hashes.role == "booster"].groupby("source_key").size().items()},
          "booster_distinct_sha_by_source": {k: int(v) for k, v in hashes[hashes.role == "booster"].groupby("source_key").sha256.nunique().items()},
          "unresolved_file_roles": hashes.loc[hashes.decision == "UNRESOLVED", "path"].tolist(),
          "files_mentioning_excluded_families": hashes.loc[hashes.excluded_family_mentions != "", ["path", "excluded_family_mentions"]].values.tolist()}
fitted = M[M.member_kind == "fitted"]
counts["actual_fits_saved"] = int(len(fitted))  # one save_model per fitted booster; deterministic equal bytes are separate fits
counts["member_rows_by_kind"] = {k: int(v) for k, v in M.member_kind.value_counts().items()}
reg = M[~M.member_kind.isin(["alias_h0_clone_of_B", "alias_shared_h0_baseline"])].groupby(["family", "arm", "lead_months"])
versions = M[~M.member_kind.isin(["alias_h0_clone_of_B", "alias_shared_h0_baseline"])].groupby(["family", "arm", "lead_months", "source_key"])
counts["registered_models"] = int(reg.ngroups)
counts["model_versions"] = int(versions.ngroups)
counts["registered_models_by_family"] = {k: int(v) for k, v in M[~M.member_kind.isin(["alias_h0_clone_of_B", "alias_shared_h0_baseline"])].drop_duplicates(["family", "arm", "lead_months"]).groupby("family").size().items()}
vt = versions.agg(members=("path", "size"), fitted=("member_kind", lambda s: int((s == "fitted").sum())),
                  reused=("member_kind", lambda s: int((s == "reused_from_original_snapshot").sum())),
                  alias=("member_kind", lambda s: int(s.str.startswith("alias").sum())), distinct_sha=("sha256", "nunique")).reset_index()
vt.to_csv(OUT / "model_versions_expected.csv", index=False)
counts["version_member_refs_total"] = int(vt.members.sum())
(OUT / "expected_counts.json").write_text(json.dumps(counts, indent=1, default=str))
print(json.dumps({k: v for k, v in counts.items() if k not in ("files_mentioning_excluded_families",)}, indent=1, default=str))
print("excluded-family mentions:", len(counts["files_mentioning_excluded_families"]))
print("metric map rows", len(MM), "unresolved", int(MM.readable_leaf.str.startswith("UNRESOLVED").sum()))
print(MM[MM.readable_leaf.str.startswith("UNRESOLVED")][["source_key", "file", "column", "long_metric", "readable_leaf"]].drop_duplicates(["column", "long_metric"]).to_string())
