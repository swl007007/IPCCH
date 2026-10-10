"""Readable vocabulary for the IPCCH Forecasting MLflow catalog.

The only place for user-facing names, tags and description text. Convention follows the
Food_Crisis_Cluster readable-naming delivery (FCC 38adbda, IPCCHMLflow/naming.py and
local-mlflow-import.md): English names, ``0-month`` lead display, zero-padded ``lead_months``
tags, provenance under ``zz_prov.*`` written after the readable tags. Unknown identifiers
raise ``SourceConflict``; nothing is passed through as raw shorthand.
"""

from __future__ import annotations

import re

PROV = "zz_prov."
DETAILED_EXPERIMENT = "IPCCH Forecasting - detailed runs"
DASHBOARD_EXPERIMENT = "IPCCH Forecasting - dashboard"
MODEL_PREFIX = "IPCCH Forecasting"
NOTE = "mlflow.note.content"


class SourceConflict(RuntimeError):
    """Source, plan or store state that must stop the import before (further) writes."""


# ------------------------------------------------------------------ leads

def lead_label(h) -> str:
    return f"{int(h)}-month"


def lead_tag(h) -> str:
    return f"{int(h):02d}"


# ------------------------------------------------------------------ families

MODEL_RECIPE = ("Four XGBoost regressors predict the cumulative population shares q2..q5 (phase 2 or worse .. phase 5) "
                "of each area; the IPC phase is the highest phase whose unrounded cumulative score is >= 0.20.")
SOMALIA_RECIPE = ("Somalia-local XGBoost regressors of the cumulative shares q2..q5 (q3 = phase 3 or worse); the "
                  "phase follows the 0.20 rule. Fitted only on Somalia areas.")
REALIZED_WEATHER = ("Realized future weather is a counterfactual perfect forecast assumed available at the origin; it "
                    "is not an operational forecast.")

FAMILIES = {
    "somalia_oracle_information": dict(
        short="Somalia oracle information historical", scope="somalia_local", stage="historical", label_setting=None,
        long="Somalia oracle information historical (local Somalia fits, cumulative information sets, 2025-2026)",
        what=(f"{SOMALIA_RECIPE} Cumulative information sets: existing predictors; plus seasonal climate means; plus "
              "realized rainfall/temperature after the origin (weather oracle); plus rich population-share history."),
        question="How much does each added information set, including perfect future weather, change Somalia crisis prediction?",
        truth="Truth: reported overall phase (five classes), crisis truth = reported overall phase >= 3 (somalia_oracle/data.py:172-175), never a threshold on the actual q3 share, and the actual population share in phase 3 or worse (q3) of the frozen Somalia cohort."),
    "somalia_q3_optimization": dict(
        short="Somalia q3 optimization historical", scope="somalia_local", stage="historical", label_setting=None,
        long="Somalia q3 optimization historical (direct vs residual phase-3+ share, calibrated, 2025-2026)",
        what=(f"{SOMALIA_RECIPE} Recipes (tree bundle, direct or residual-on-history q3, calibration none/shift/isotonic) "
              "are selected on 0-month training-period validation; 3/6/12-month refits reuse the 0-month recipe."),
        question="Can the phase-3+ share prediction error be reduced by recipe selection and calibration?",
        truth="Truth: actual q3 share and reported overall phase from the v2 label ledger; crisis truth = reported overall phase >= 3 (somalia_oracle/data.py:172-175), never a threshold on the actual q3 share. Binary predictions use the predicted q3_final >= 0.20 rule (q3eval.py:82-83); that is a prediction rule, not the truth."),
    "somalia_validity_observed": dict(
        short="Somalia validity observed-label historical", scope="somalia_local", stage="historical", label_setting="observed",
        long="Somalia validity historical (observed labels vs validity-augmented training, 2025-2026)",
        what=f"{SOMALIA_RECIPE} Share-history (D) recipes fitted on observed labels only.",
        question="Do validity-period label copies used only in training improve the Somalia share-history model?",
        truth="Truth: raw reported q3 share and overall phase of the original outer Somalia cohort (identical keys in both label settings); crisis truth = reported overall phase >= 3 (somalia_oracle/data.py:172-175), never a threshold on the actual q3 share."),
    "somalia_validity_augmented": dict(
        short="Somalia validity augmented-training historical", scope="somalia_local", stage="historical",
        label_setting="training_augmented",
        long="Somalia validity historical (observed labels vs validity-augmented training, 2025-2026)",
        what=(f"{SOMALIA_RECIPE} Share-history (D) recipes fitted with validity-period label copies added to training "
              "only; the outer evaluation keys are the same original keys as the observed-label setting."),
        question="Do validity-period label copies used only in training improve the Somalia share-history model?",
        truth="Truth: raw reported q3 share and overall phase of the original outer Somalia cohort (identical keys in both label settings); crisis truth = reported overall phase >= 3 (somalia_oracle/data.py:172-175), never a threshold on the actual q3 share."),
    "somalia_calibrated_observed": dict(
        short="Somalia calibrated observed-label historical", scope="somalia_local", stage="historical", label_setting="observed",
        long="Somalia calibrated share-history historical (per-origin selected and calibrated D, 2022-2026)",
        what=(f"{SOMALIA_RECIPE} For every forecast origin the share-history recipe and calibration are selected out of "
              "fold and refit; observed labels in every role."),
        question="What is the best attainable calibrated share-history performance under each label setting?",
        truth="Truth: reported q3 share and overall phase of the setting's own frozen required cohort; crisis truth = reported overall phase >= 3 (somalia_oracle/data.py:172-175), never a threshold on the actual q3 share."),
    "somalia_calibrated_augmented": dict(
        short="Somalia calibrated augmented-label historical", scope="somalia_local", stage="historical",
        label_setting="role_augmented",
        long="Somalia calibrated share-history historical (per-origin selected and calibrated D, 2022-2026)",
        what=(f"{SOMALIA_RECIPE} For every forecast origin the share-history recipe and calibration are selected out of "
              "fold and refit; validity-augmented label copies take part in fitting, selection, calibration and "
              "outer evaluation."),
        question="What is the best attainable calibrated share-history performance under each label setting?",
        truth="Truth: reported q3 share and overall phase of the setting's own frozen required cohort, including label copies "
              "(copy truth identified by its source family and original month); crisis truth = reported overall phase >= 3 (somalia_oracle/data.py:172-175), never a threshold on the actual q3 share."),
    "origin_safe_climate_global": dict(
        short="Origin-safe climate global historical", scope="global", stage="historical", label_setting=None,
        long="Origin-safe climate global historical (annual refit, safe IPC history and IDP, 2022-2025)",
        what=(f"{MODEL_RECIPE} One fit per evaluation year on all areas with labels up to the strictest origin of that "
              "year and 24-month decay weights; every feature respects its row's own forecast origin."),
        question="How do origin-safe IPC history and national IDP inputs change global crisis prediction?",
        truth="Reported overall phase and normalized phase-3-or-worse share of the frozen global origin-safe cohort."),
    "origin_safe_weather_global": dict(
        short="Origin-safe weather global historical", scope="global", stage="historical", label_setting=None,
        long="Origin-safe weather global historical (realized future weather oracle on the origin-safe reference, 2022-2025)",
        what=(f"{MODEL_RECIPE} The origin-safe reference inputs plus realized rainfall/temperature anomalies after the "
              f"origin (and, for weather_oracle_with_summaries, fixed future/past summary terms). {REALIZED_WEATHER}"),
        question="How much would perfect future weather improve global origin-safe forecasts at 3/6/12 months?",
        truth="Reported overall phase and normalized phase-3-or-worse share of the frozen global origin-safe cohort."),
    "compact_climate_global": dict(
        short="Compact climate global historical", scope="global", stage="historical", label_setting=None,
        long="Compact climate global historical (compact inputs; original 2022-2025 and extended 2022-2026 Jan-Apr snapshots)",
        what=(f"{MODEL_RECIPE} Compact baseline inputs (296) at every lead; the weather oracle appends realized monthly "
              f"rainfall and temperature anomalies after the origin. {REALIZED_WEATHER}"),
        question="Does a compact feature set with realized future weather improve global crisis prediction?",
        truth="Reported overall phase and normalized phase-3-or-worse share of the frozen global origin-safe cohort."),
    "compact_climate_somalia": dict(
        short="Compact climate Somalia-local historical", scope="somalia_local", stage="historical", label_setting=None,
        long="Compact climate Somalia-local historical (compact inputs refit on Somalia areas only; 2022-2025 / 2022-2026 Jan-Apr)",
        what=(f"{MODEL_RECIPE} Same compact recipes as the global family but fitted only on Somalia (iso3 SOM) areas. "
              f"{REALIZED_WEATHER}"),
        question="Does the compact weather-oracle result hold when the models are fitted on Somalia only?",
        truth="Reported overall phase and normalized phase-3-or-worse share of the frozen Somalia-local cohort."),
    "compact_launch_global": dict(
        short="Compact climate global launch", scope="global", stage="launch", label_setting=None,
        long="Compact climate global launch (origin 2026-04; targets 2026-04, 2026-10, 2027-04; CDS forecasts at inference)",
        what=(f"{MODEL_RECIPE} Fitted on all labels before April 2026 and applied to the April 2026 inference population. "
              "The CDS weather arm is trained on realized weather anomalies and applied with ECMWF April-2026 "
              "seasonal forecast anomalies."),
        question="What do the compact baseline and CDS-weather models predict for April 2026, October 2026 and April 2027?",
        truth=("These saved prediction-summary records have no attached scoring truth; this catalog computes no scores "
               "(actual April 2026 reports may exist for some areas but are not part of these records)."),),
    "compact_launch_somalia": dict(
        short="Compact climate Somalia-local launch", scope="somalia_local", stage="launch", label_setting=None,
        long="Compact climate Somalia-local launch (origin 2026-04; Somalia areas; CDS forecasts at inference)",
        what=(f"{MODEL_RECIPE} Fitted on Somalia labels before April 2026 and applied to the Somalia April 2026 inference "
              "areas. The CDS weather arm is trained on realized weather and applied with ECMWF April-2026 forecasts."),
        question="What do Somalia-local compact models predict for April 2026, October 2026 and April 2027?",
        truth=("These saved prediction-summary records have no attached scoring truth; this catalog computes no scores "
               "(actual April 2026 reports may exist for some areas but are not part of these records)."),),
}

# raw arm -> (readable arm, arm_role)
ARMS = {
    "A": ("existing_predictors", "baseline"), "B": ("seasonal_climate", "candidate"), "C": ("weather_oracle", "candidate"),
    "D": ("weather_oracle_with_share_history", "candidate"),
    "D_direct": ("share_history_direct", "candidate"), "D_residual": ("share_history_residual", "candidate"),
    "D_selected": ("share_history_selected", "candidate"), "D_calibrated": ("calibrated_share_history", "candidate"),
    "climate_no_history": ("no_ipc_history", "baseline"), "climate_safe_history": ("safe_ipc_history", "candidate"),
    "climate_safe_history_idp": ("safe_ipc_history_idp", "candidate"),
    "climate_safe_history_idp_oracle": ("weather_oracle", "candidate"),
    "climate_safe_history_idp_oracle_b6": ("weather_oracle_with_summaries", "candidate"),
    "compact_baseline": ("baseline", "baseline"), "compact_weather_oracle": ("weather_oracle", "candidate"),
    "compact_cds_weather": ("cds_weather", "candidate"),
    # metric-only views (no fitted model)
    "persistence": ("phase_persistence", "baseline"), "phase_persistence": ("phase_persistence", "baseline"),
    "share_persistence": ("share_persistence", "baseline"), "always_crisis": ("always_crisis", "baseline"),
    "v1_D_raw": ("reference_weather_oracle_with_share_history_raw", "diagnostic"),
    "v1_D_isotonic": ("reference_weather_oracle_with_share_history_isotonic", "diagnostic"),
    "reference:climate_safe_history_idp": ("reference_safe_ipc_history_idp", "baseline"),
}
ARM_MEANING = {
    "existing_predictors": "Information set A: the existing Somalia predictors.",
    "seasonal_climate": "Information set B: A plus fourteen seasonal climate means.",
    "weather_oracle": "Adds realized rainfall and temperature after the forecast origin (weather oracle).",
    "weather_oracle_with_share_history": "Information set D: C plus rich population-share history.",
    "share_history_direct": "Share-history model predicting q3 directly.",
    "share_history_residual": "Share-history model predicting the q3 change from the latest observed share (direct fallback where no history).",
    "share_history_selected": "The share-history recipe selected on 0-month training-period validation (direct or residual).",
    "calibrated_share_history": "The per-origin selected and calibrated share-history recipe.",
    "no_ipc_history": "Origin-safe inputs without IPC history.",
    "safe_ipc_history": "Origin-safe inputs plus the latest three reported phases visible at the origin.",
    "safe_ipc_history_idp": "Safe IPC history plus national IDP reports.",
    "weather_oracle_with_summaries": "Weather oracle plus fixed future-mean, past/future-mean and crisis-gated summary terms.",
    "baseline": "Compact baseline inputs (296).",
    "cds_weather": "Compact inputs plus monthly weather anomalies: realized in training, ECMWF April-2026 forecasts at inference.",
    "phase_persistence": "Last reported phase carried forward (no model).",
    "share_persistence": "Latest observed phase-3+ share carried forward (no model).",
    "always_crisis": "Every area predicted in crisis (no model).",
    "reference_weather_oracle_with_share_history_raw": "Somalia oracle information D predictions reused as a raw reference.",
    "reference_weather_oracle_with_share_history_isotonic": "Somalia oracle information D predictions with isotonic calibration, reused as a reference.",
    "reference_safe_ipc_history_idp": "The origin-safe climate safe_ipc_history_idp fit reused unchanged as the reference.",
}
ROLE_MEANING = {"baseline": "comparison reference", "candidate": "fitted model under evaluation",
                "diagnostic": "diagnostic reference, not a primary comparison"}

LABEL_SETTING_TEXT = {"observed": "observed labels", "training_augmented": "validity-augmented training labels",
                      "role_augmented": "validity-augmented labels in every role"}


def family(slug: str) -> dict:
    if slug not in FAMILIES:
        raise SourceConflict(f"no family vocabulary for {slug!r}")
    return FAMILIES[slug]


def arm(raw: str) -> tuple:
    if raw not in ARMS:
        raise SourceConflict(f"no arm vocabulary for {raw!r}")
    return ARMS[raw]


# ------------------------------------------------------------------ cohorts and periods

COHORTS = {
    "primary": ("primary", "Frozen primary evaluation cohort of the source (decided before predictions)."),
    "all_scored": ("all_scored", "Every frozen evaluation key of the period."),
    "wider_labeled": ("wider_labeled", "Primary keys plus labeled keys whose oracle weather is unverified."),
    "persistence_subset": ("phase_persistence_subset", "Primary keys with a reported phase visible at the origin."),
    "phase_persistence_subset": ("phase_persistence_subset", "Primary keys with a reported phase visible at the origin."),
    "share_history_subset": ("share_history_subset", "Primary keys with an observed phase-3+ share visible at the origin."),
}
REGIONS = {0: "Asia", 1: "East Africa", 2: "West Africa", 3: "Southern Africa", 4: "Central Africa",
           5: "Latin America", 6: "Mali", 7: "Somalia", 8: "Palestine"}


def region_cohort(region: int) -> str:
    if int(region) not in REGIONS:
        raise SourceConflict(f"no region name for region {region!r}")
    return "region_" + REGIONS[int(region)].lower().replace(" ", "_") + "_global_model"


REGION_COHORTS = {region_cohort(r): r for r in REGIONS}


def cohort(raw: str) -> str:
    if raw in REGION_COHORTS:
        return raw
    if raw not in COHORTS:
        raise SourceConflict(f"no cohort vocabulary for {raw!r}")
    return COHORTS[raw][0]


def cohort_definition(c: str) -> str:
    for k, (name, text) in COHORTS.items():
        if name == c:
            return text
    if c in REGION_COHORTS:
        return (f"Areas of region {REGION_COHORTS[c]} ({REGIONS[REGION_COHORTS[c]]}; area_id join with "
                "data/reference/area_id_country_region_mapping.csv), scored with the globally fitted model; not a local fit.")
    raise SourceConflict(f"no cohort definition for {c!r}")


def launch_cohort(unit: str, region: int | None = None, region_name: str | None = None, country: str | None = None) -> str:
    """Launch prediction-summary units; region names must match the declared vocabulary."""
    if unit == "all":
        return "all_inference_areas"
    if unit == "region":
        if int(region) not in REGIONS or REGIONS[int(region)] != region_name:
            raise SourceConflict(f"launch region {region!r}/{region_name!r} does not match the region vocabulary")
        return "region_" + REGIONS[int(region)].lower().replace(" ", "_") + "_areas"
    if unit == "country":
        slug = re.sub(r"[^a-z0-9]+", "_", (country or "").lower()).strip("_")
        if not slug:
            raise SourceConflict("empty launch country name")
        return "country_" + slug
    raise SourceConflict(f"no launch unit {unit!r}")


PERIOD_ROLE = re.compile(r"^(primary|original|pooled|year_20\d\d|prediction_summary)$")


def period_role(raw: str) -> str:
    if not PERIOD_ROLE.match(raw):
        raise SourceConflict(f"no period role vocabulary for {raw!r}")
    return raw


# ------------------------------------------------------------------ metric leaves

LEAF = {
    # modern 8-metric schema
    "exact_phase_accuracy": "five_class.accuracy", "phase3plus_accuracy": "binary.accuracy",
    "precision_phase3plus": "binary.precision", "sensitivity_phase3plus": "binary.recall", "f2_phase3plus": "binary.f2",
    "r2_phase3plus": "share_phase3plus_r2", "mae_phase3plus": "share_phase3plus_mae", "ordinal_mae": "five_class.ordinal_mae",
    "n_samples": "n_rows", "n_rows": "n_rows", "n": "n_rows", "n_areas": "n_areas", "n_countries": "n_countries",
    "observed_3plus": "binary.count.observed_positive", "observed_1_2": "binary.count.observed_negative",
    "predicted_3plus": "binary.count.predicted_positive", "true_positive_3plus": "binary.count.tp",
    "distinct_phase3_worse": "share_phase3plus_n_distinct_truth",
    # Somalia v1 (accuracy = exact five-class, somalia_oracle/evaluation.py:63-65)
    "tp": "binary.count.tp", "fp": "binary.count.fp", "fn": "binary.count.fn", "tn": "binary.count.tn",
    "precision": "binary.precision", "recall": "binary.recall", "f1": "binary.f1", "f2": "binary.f2",
    "accuracy": "five_class.accuracy", "prevalence": "binary.observed_prevalence",
    "predicted_prevalence": "binary.predicted_prevalence", "r2_q3": "share_phase3plus_r2",
    "mean_q3_pred": "share_phase3plus_mean_pred", "macro_f1": "five_class.macro_f1",
    "p4plus_recall": "binary_phase4plus.recall", "pred_p3_share": "binary.predicted_prevalence",
    "r2_n": "share_phase3plus_r2_n_rows", "auc_crisis": "binary.auc_pooled", "within_month_auc": "binary.auc_within_month",
    **{f"n_actual_phase{k}": f"five_class.count.observed_phase{k}" for k in range(1, 6)},
    **{f"n_pred_phase{k}": f"five_class.count.predicted_phase{k}" for k in range(1, 6)},
    # Somalia v2-v4: raw vs final (calibrated) share and AUC families stay distinct
    **{f"{s}_{m}": f"share_phase3plus_{s}.{m}" for s in ("raw", "final") for m in ("r2", "rmse", "mae", "bias", "mean_truth", "mean_pred")},
    "raw_auc": "binary.auc_pooled_raw", "final_auc": "binary.auc_pooled_final",
    "final_within_month_auc": "binary.auc_within_month_final", "raw_within_month_auc": "binary.auc_within_month_raw",
    "within_month_auc_months": "binary.auc_within_month_final.n_months",
    "within_month_auc_undefined_months": "binary.auc_within_month_final.n_undefined_months",
    **{f"bin_{m}": f"binary.{m}" for m in ("f1", "recall", "precision", "f2")},
    **{f"bin_{c}": f"binary.count.{c}" for c in ("tp", "fp", "fn", "tn")},
    "legacy_phase_accuracy": "five_class.accuracy", "legacy_multiclass_macro_f1": "five_class.macro_f1",
    **{f"legacy_{m}": f"legacy_phase_binary.{m}" for m in ("f1", "recall", "precision", "f2")},
    **{f"legacy_{c}": f"legacy_phase_binary.count.{c}" for c in ("tp", "fp", "fn", "tn")},
    "q3_binary_vs_legacy_disagreements": "binary.disagreements_vs_legacy_phase",
    "n_clipped": "share_phase3plus_n_clipped", "n_fallback_direct": "n_rows_fallback_direct",
    "n_residual_branch": "n_rows_residual_branch", "n_primary": "n_rows_primary_cohort", "n_wider_only": "n_rows_wider_only",
    "n_excluded": "n_rows_excluded", "n_cohort": "n_rows_cohort", "n_months": "n_target_months",
    "n_original_reports": "n_original_reports", "n_originals": "n_rows_original", "n_copies": "n_rows_copies",
}
# contrast/interval columns -> suffix after delta.<A>_minus_<B>.<metric>
DELTA_COLUMNS = {"point_delta_f2": "", "point_delta": "", "delta": "", "ci_low": ".ci_low", "ci_high": ".ci_high",
                 "ci_lower": ".ci_low", "ci_upper": ".ci_high", "valid_draws": ".draws_valid", "undefined_draws": ".draws_undefined",
                 "draws_total": ".draws_total", "draws_valid": ".draws_valid", "draws_invalid": ".draws_invalid",
                 "invalid_fraction": ".invalid_fraction", "min_valid_draws": ".min_valid_draws"}
DELTA_METRIC = {"auc": "binary.auc_pooled_final", "r2": "share_phase3plus_final.r2", "rmse": "share_phase3plus_final.rmse",
                **{k: LEAF[k] for k in ("exact_phase_accuracy", "phase3plus_accuracy", "precision_phase3plus", "sensitivity_phase3plus",
                                        "f2_phase3plus", "r2_phase3plus", "mae_phase3plus", "ordinal_mae")}}
LAUNCH_COLUMN = re.compile(r"^(?:(delta)_)?(count|share)_(raw|effective)_(phase[1-5]|p3plus|p4plus)$")
LAUNCH_EXTRA = {"population_raw": "population_raw", "population_effective": "population_effective",
                "n_areas": "n_areas", "n_zero_population_areas": "n_zero_population_areas", "n_capped_areas": "n_capped_areas"}


def leaf(raw: str) -> str:
    if raw not in LEAF:
        raise SourceConflict(f"no metric vocabulary for source name {raw!r}")
    return LEAF[raw]


def delta_metric(raw: str) -> str:
    if raw not in DELTA_METRIC:
        raise SourceConflict(f"no delta metric vocabulary for {raw!r}")
    return DELTA_METRIC[raw]


def launch_leaf(col: str) -> str:
    if col in LAUNCH_EXTRA:
        return "prediction_summary." + LAUNCH_EXTRA[col]
    m = LAUNCH_COLUMN.match(col)
    if not m:
        raise SourceConflict(f"no launch summary vocabulary for {col!r}")
    d, kind, basis, cls = m.groups()
    body = f"{'population_count' if kind == 'count' else 'population_share'}_{basis}.{cls}"
    return ("paired_difference.cds_weather_minus_baseline." if d else "prediction_summary.") + body


METRIC_KEY = re.compile(r"^[A-Za-z0-9_\-./ ]{1,250}$")


def metric_key(role: str, coh: str, leaf_name: str) -> str:
    k = f"{period_role(role)}.{coh}.{leaf_name}"
    if not METRIC_KEY.match(k):
        raise SourceConflict(f"metric key not allowed by MLflow: {k!r}")
    return k


# ------------------------------------------------------------------ object names

NAME_FORBIDDEN = re.compile(r"[./:%\"']")


def run_name(fam: str, arm_name: str, h) -> str:
    return " | ".join([family(fam)["short"], arm_name, lead_label(h)])


def registered_model_name(fam: str, arm_name: str, h) -> str:
    return f"{MODEL_PREFIX} {run_name(fam, arm_name, h)}"


def logged_model_name(fam: str, arm_name: str, h, snapshot_label: str) -> str:
    n = f"{run_name(fam, arm_name, h)} | {snapshot_label}"
    if NAME_FORBIDDEN.search(n):
        raise SourceConflict(f"logged model name has a forbidden character: {n!r}")
    return n


def eval_dataset_name(h, span: str, coh: str, group_label: str) -> str:
    return f"{MODEL_PREFIX} eval | {lead_label(h)} | {span} | {coh} ({group_label})"


def training_dataset_name(fam: str, snapshot_qualifier: str, n_inputs: int, h) -> str:
    title = family(fam)["short"] + (f" ({snapshot_qualifier})" if snapshot_qualifier else "")
    return f"{MODEL_PREFIX} training pool | {title} | {n_inputs} inputs | {lead_label(h)}"


def inference_dataset_name(scope_label: str, inputs_label: str, origin: str, target: str) -> str:
    return f"{MODEL_PREFIX} inference | {scope_label} | {inputs_label} | origin {origin} | target {target}"


# ------------------------------------------------------------------ descriptions

EXTERNAL_NOTE = ("External catalog descriptor of saved XGBoost boosters: the weights are downloadable from the detailed "
                 "parent run (members.json lists every member and its bundle); there is no MLflow prediction wrapper and "
                 "nothing was retrained.")
TIMES_NOTE = "MLflow times are registration times, not fit times."


def view_description(v: dict, src: dict) -> str:
    f = family(v["family"])
    role = v["arm_role"]
    lead = lead_label(v["lead"])
    kind = v["view_kind"]
    what = f"{ARM_MEANING[v['arm']]} Family: {f['long']}. {lead} lead (forecast origin = target month minus {int(v['lead'])})."
    if f["label_setting"]:
        what += f" Label setting: {LABEL_SETTING_TEXT[f['label_setting']]}."
    if v.get("n_inputs"):
        what += f" Fitted inputs: {v['n_inputs']}."
    if kind == "alias":
        what += f" This view reuses the fit of {v['alias_text']}; it has no fit or registered model of its own."
    elif kind == "metric_only":
        what += " Metric-only comparison view; no fitted model."
    elif kind == "reference":
        what += f" Reference view reusing {v['alias_text']}; no second fit."
    elif kind == "evaluation_revision":
        what += f" Evaluation-only revision: the saved results changed, the model is {v['alias_text']} (no refit)."
    if v.get("fit_note"):
        what += " " + v["fit_note"]
    compare = v.get("compare_with") or ("the family's baseline arm at the same lead on the same evaluation dataset "
                                        "(same keys, truth and definition); compare values only within one dataset.")
    status = f"Source status: {src['status_text']} Slot status: {v['slot_status_text']}"
    caveats = [v.get("caveats", ""), f["truth"],
               "Undefined source values are not logged; view/na.json lists them with the source reason.",
               "Metric keys read <period_role>.<cohort>.<metric>; view/evaluation_view.json maps every key to the source file, row and column.",
               EXTERNAL_NOTE if kind in ("fitted",) else "", f"Source snapshot: {src['source_key']}.", TIMES_NOTE]
    return "\n\n".join([
        f"**{run_name(v['family'], v['arm'], v['lead'])}**",
        f"**What:** {what} Role: {role} ({ROLE_MEANING[role]}).",
        f"**Compare with:** {compare}",
        f"**Status:** {status}",
        "**Caveats + original:** " + " ".join(c for c in caveats if c),
    ])


def parent_description(fam_slugs: list, src: dict) -> str:
    f = family(fam_slugs[0])
    titles = "; ".join(family(s)["short"] for s in fam_slugs)
    conclusion = src.get("conclusion") or "No accepted scientific conclusion is recorded in the source; this catalog adds none."
    return "\n\n".join([
        f"**{f['long']}**",
        f"**What:** {f['what']} Child families: {titles}.",
        f"**Question:** {f['question']}",
        f"**Accepted conclusion:** {conclusion}",
        f"**Status:** {src['status_text']} Fitting dates: {src['fit_date_evidence']}",
        ("**Reading guide:** child runs hold one family x arm x lead each (metrics, view/evaluation_view.json, view/na.json, "
         "members.json). This run archives the source files: models.tar (weights and recipe members), source.tar (metrics, "
         "ledgers, predictions, logs, cited reports) and manifests/ (inventory, exclusions, plan summary). "
         f"Source snapshot {src['source_key']} ({src['snapshot_role']}). {TIMES_NOTE}"),
    ])


def registered_model_description(fam: str, arm_name: str, h) -> str:
    f = family(fam)
    return (f"{ARM_MEANING[arm_name]} {f['long']}, {lead_label(h)} lead, {f['scope'].replace('_', '-')} fit. Versions are "
            f"immutable source snapshots (see version tags). {EXTERNAL_NOTE}")


def dashboard_description() -> str:
    return "\n\n".join([
        "**IPCCH Forecasting - dashboard**: one row per family x arm x lead for the latest source snapshot. Start here; "
        "each row links to its detailed run, evaluation datasets and model version.",
        ("**Vocabulary:** `family`, `arm`, `arm_role` (baseline / candidate / diagnostic), `lead_months` (00, 03, 06, 12), "
         "`model_scope` (global / somalia_local), `stage` (historical / launch), `label_setting`, `source_status`. "
         "Metric keys read `<period_role>.<cohort>.<metric>`: `primary`, `original` (compact pooled 2022-2025), "
         "`pooled`, `year_YYYY`; cohorts such as `all_scored`, `primary`, `share_history_subset`, "
         "`region_<name>_global_model` (scores of a global model on a region's areas, not local fits). Metrics: "
         "`five_class.*` (exact five IPC phases), `binary.*` (phase 3+ vs 1-2), `share_phase3plus_*`, `n_rows`; saved "
         "contrasts `*.delta.<A>_minus_<B>.*`. Launch rows hold `prediction_summary.*` and `paired_difference.*` values "
         "(predictions, not accuracy)."),
        ("**Comparability:** compare values only on the same evaluation dataset (run Inputs; one name = one digest). "
         "2026 compact support is January-April only. Weather oracles use realized future weather. No global best-model "
         "ranking is implied."),
        ("**Filters:** `tags.lead_months = '06'`; `tags.family = 'compact_climate_global'`; `tags.stage = 'launch'`; "
         "`tags.model_scope = 'somalia_local'`; `tags.arm_role = 'candidate'`."),
    ])
