# Phase 0 Research: April 2026 Global Nowcasting Launch (Comprehensive-CSV Fallback)

All NEEDS CLARIFICATION items from Technical Context are resolved below. Findings are grounded in the existing code (file references included).

---

## R1 — Which canonical workflow does this launch reuse?

**Decision**: Reuse the **deep-feature weight-decay forecasting workflow** — module `src/ipcch/forecasting_weight_decay.py` and the orchestration patterns in `scripts/modeling/run_deep_feature_weight_decay_forecasting.py` — operated as a single launch-month run rather than an annual holdout sweep.

**Rationale**:
- The comprehensive fallback source is `forecasting_subset_IPCCH_2026_target_corrected_deep_features.csv` (a deep-feature file); the workflow that consumes deep-feature CSVs is exactly `run_deep_feature_weight_decay_forecasting.py` (its `--dataset` is "corrected deep-feature forecasting-ready CSV").
- The existing alert-risk-map experiment already points at `results/experiments/deep_feature_weight_decay_forecasting` (`alert_risk_maps.default_prediction_root()`), confirming this is the active canonical workflow.
- It already exposes the exact reusable primitives we need: `validate_required_columns`, `add_monthly_date`, `derive_cumulative_targets`, `prepare_forecasting_dataset`, `add_identifier_features`, `select_numeric_feature_columns`, `time_decay_weights`, `prepare_target_matrices`, and the thin `fit_model` / `convert_phase_predictions` helpers (currently in the script).

**Alternatives considered**:
- `food_crisis_functions.forecasting_pipeline()` + `X_drop_set`/`X_stable_set` (one-hot of month + `area_id`): this is the older notebook-era canonical pipeline. Rejected as the primary path because it is tied to the notebook two-cell structure and one-hot `area_id` dummies (up to ~1876 columns), which is not how the deep-feature CSV workflow represents identifiers; using it would break comparability with the intended deep-feature launch. We still honor its `th=0.2` conversion semantics via the shared rule.
- `run_region_models.py`: region/global splitter — out of scope (no regional variants).

---

## R2 — What is the "canonical identifier-feature setting" (FR-011a)?

**Decision**: The canonical identifier-feature setting is the `--add-identifier-features` option of the deep-feature workflow, implemented by `forecasting_weight_decay.add_identifier_features(df, lookup_df)` (forecasting_weight_decay.py:134). The launch defaults this setting **ON** for comparability with the intended identifier-feature launch.

**What it produces** (the identifier-derived model features):
- Merges `lat`/`lon` from an identifier/lookup source on `(area_id≡admin_code, year, month)`.
- Adds one-hot `month_1..12` and per-year `year_*` dummy features.
- Does **not** add raw `area_id` as a model feature; `area_id`/country/region remain reporting identifiers (and are excluded from the model by `select_numeric_feature_columns()` regex blocks for `(^|_)id$`, `country`, `region`, `pcode`, `iso`, `adm[0-9]`).

**Default identifier lookup source**: the canonical lookup is `ipcch.paths.external_path("ipcch_2026_completed_dataset")` (the IPCCH 2026 completed source carrying `admin_code`/`year`/`month`/`lat`/`lon`) — the same default the deep-feature workflow uses (`forecasting_weight_decay.DEFAULT_SOMALIA_LOOKUP_KEY`). The lookup is **used only when the expected identifier-derived columns are absent** from the comprehensive source; if they are already present they are detected and used directly with no lookup. If construction via lookup is required but no lookup path is configured, the launch (and `--validate-only`) fails with a clear message. The feature schema report records, per identifier-derived feature, whether it was **detected directly** in the comprehensive source or **constructed via lookup**.

**Consequences for the launch (FR-011a / FR-002)**:
- Raw country/region/name and `area_id` are preserved for reporting/grouping/joins/visualization but never passed directly to the model.
- Identifier-derived features (`lat`, `lon`, month/year dummies) enter the model only via `add_identifier_features`.
- The feature schema report lists: (a) identifier-derived features included, (b) raw identifier/reporting columns excluded, (c) any expected identifier-derived feature missing from the comprehensive source.
- **Stop/override rule**: if required identifier-derived features cannot be produced (e.g., `lat`/`lon` absent from both the comprehensive source and the supplied identifier/lookup source, or the lookup cannot resolve them consistently), the launch stops with a clear error unless an explicit `--allow-missing-identifier-features` override is passed — because silently dropping them would break comparability with the intended identifier-feature launch.

**Rationale**: The spec mandates forcing the canonical identifier-feature setting for comparability; `add_identifier_features` is the only existing canonical identifier-feature mechanism in the active workflow.

**Alternatives considered**: One-hot `area_id` dummies (old pipeline) — rejected (see R1); not how the deep-feature workflow represents identifiers.

---

## R3 — Which hyperparameters are canonical for this launch?

**Decision**: Use `configs/forecasting_hyperparameters.json` for phases 2/4/5 and `configs/forecasting_hyperparameters_p3.json` for phase 3, loaded exactly as `run_deep_feature_weight_decay_forecasting.load_hyperparameters()` does, with `random_state` injected from `--seed` (default 42).

**Rationale**: These are the hyperparameter files the deep-feature workflow (R1) uses. Although the launch is operationally a *nowcast*, the model architecture, feature schema, and hyperparameters are those of the deep-feature forecasting workflow that consumes this comprehensive source. The launch report states the fallback-nowcasting comparability caveat (spec Overview).

**Alternatives considered**: `contemporaneous_hyperparameters.json` (+ `_p3`) — these belong to the older nowcasting two-layer workflow and a different feature schema; using them would not match the deep-feature source. Documented and rejected. (spec.md Assumptions now names the forecasting set consistently, agreeing with this decision.)

---

## R4 — FR-016: Are 2026-02 and 2026-03 rows included in training?

**Decision**: **Yes.** Under the declared all-prior-history holdout with a 2026-04-01 cutoff, any row with a valid observed target and a date strictly before 2026-04-01 is eligible — this includes 2026-02 and 2026-03 rows if present with valid targets. They are included in training.

**Rationale & validity**:
- The temporal-integrity guarantee (Constitution I) requires only that no test-window/future information leaks. The launch month is 2026-04; 2026-02 and 2026-03 are strictly before the cutoff and are legitimate history for a nowcast that uses contemporaneous features to predict the current month.
- The April-only actual comparison uses **only** 2026-04 actuals, which are never in training; therefore including 2026-02/03 training rows creates no comparison leakage (spec "Comparison isolation").
- If time-decay weighting is enabled (R5), 2026-02/03 rows receive the highest weights (closest to the launch month), which is the intended behavior for a nowcast.

**Reported**: the training data summary records the min/max training date and per-month row counts so the 2026-02/03 inclusion is visible.

---

## R5 — Time-decay sample weighting

**Decision**: Support canonical time-decay weighting via `forecasting_weight_decay.time_decay_weights(dates, anchor_year, half_life_months)` anchored at the **launch month (2026-04)**, exposed as `--half-life-months` (default = canonical `DEFAULT_HALF_LIFE_MONTHS`, 24.0). The launch may also accept `--no-time-decay` to fit unweighted; default mirrors the canonical workflow (weighted).

**Rationale**: The active canonical workflow trains with time-decay weights; matching it preserves comparability. Anchoring at the launch month is consistent with the all-prior-history policy and the project's recorded "time-decay split policy" (use all-prior-history holdouts when decay weights downweight older rows). Weighting uses only training-row dates (no future info).

**Alternatives considered**: Fixed-window training — rejected; the spec declares all-prior-history. Unweighted-only — rejected as default because it diverges from the canonical workflow; offered as an explicit flag.

---

## R6 — Cumulative→phase derivation for prediction-only April rows

**Decision**: Derive `overall_phase_pred` from the four cumulative predictions using `forecast_diagnostics.reconstruct_phase_from_cumulative(df, pred_cols, threshold=0.2)` (forecast_diagnostics.py:449), which performs the canonical top-down `>= 0.2` assignment **without requiring `y_test`**.

**Rationale**:
- `food_crisis_functions.convert_prob_to_phase()` expects long-form rows carrying `y_test` (truth) and drops rows where the phase sums ≤ 0 — unsuitable for prediction-only April rows where actuals are absent and every eligible area must be preserved.
- `reconstruct_phase_from_cumulative` applies the identical canonical threshold semantics on prediction columns alone, preserving all eligible areas (FR-019) and honoring `th=0.2` (FR-018). The deep-feature script's own `convert_phase_predictions` uses the same greedy top-down `>= threshold` logic, confirming equivalence.

**Alternatives considered**: `convert_prob_to_phase` (rejected — needs truth, drops rows); re-implementing the rule (rejected — duplication, Principle II).

---

## R7 — Prediction validation, clipping, non-finite handling (FR-017a)

**Decision**: Between raw `model.predict()` and phase derivation, the launch:
1. Assembles the four cumulative prediction columns per area.
2. **Clips** each to the probability range `[0, 1]` and rounds to 2 decimals (matching canonical conversion's rounding) — this is the documented canonical handling; the count of clipped values is recorded.
3. Flags any **non-finite** (NaN/±inf) cumulative prediction. Non-finite values are recorded in a `prediction_validation_summary` and MUST NOT silently yield a phase label. Default behavior: **fail** with a clear error listing affected `area_id`s; with an explicit `--drop-nonfinite-predictions` flag, the documented canonical fallback excludes those areas and records them as excluded (still reported).
4. Derives `overall_phase_pred` (R6) only from finite, validated cumulative predictions.

**Rationale**: XGBoost predictions on valid numeric features are normally finite; non-finite outputs signal upstream data problems and must be surfaced, never silently converted (FR-017a, SC-002/SC-002a). Clipping to `[0,1]` is consistent with treating cumulative outputs as proportions and with the canonical rounding.

**Alternatives considered**: Silent clamp of non-finite to 0 (rejected — hides data problems); no clipping (rejected — cumulative proportions should be in `[0,1]` for sane phase derivation and reporting).

---

## R8 — Spatial join for the two-panel map (FR-027) — divergence from `alert_risk_maps`

**Decision**: Implement a **launch-specific** join in `launch_visualizations.py` that:
- Reuses `alert_risk_maps.load_spatial_boundaries()` and `normalize_area_id()` for boundary loading and key normalization (which already hard-fail on duplicate boundary `area_id`s).
- **Duplicate join keys → hard failure** (matches FR-027 and the existing module's stance).
- **Unmatched prediction/actual `area_id`s → recorded, not raised**: the map renders the matched subset; unmatched IDs are written to the validation summary and mapped-coverage report.

**Rationale**: `alert_risk_maps.join_predictions_to_spatial()` *raises* `AlertRiskMapError` on any unmatched `area_id` (alert_risk_maps.py:381) — correct for the six-panel/top-risk maps it was built for, but it violates FR-027's requirement to render matched coverage while recording unmatched IDs. A new additive function is the minimal, non-breaking way to satisfy FR-027; it does not change existing behavior used by the 2025 alert maps.

**Alternatives considered**: Reusing the existing join unchanged (rejected — would abort whenever any predicted area lacks a boundary, which is expected at global scale); editing the existing join to stop raising (rejected — would regress the 2025 alert-map feature 002).

---

## R9 — Two-panel figure construction

**Decision**: Add `plot_two_panel_actual_vs_predicted()` in `launch_visualizations.py`, building a **2×1 vertical** figure (top = April actual crisis on covered subset; bottom = April predicted crisis on all mapped predicted areas), reusing `alert_risk_maps` helpers: `NO_ALERT_COLOR`/`ALERT_COLOR`, `_plot_binary_layer`, `_latam_mask`, `_add_latam_inset`, `_set_padded_extent`, `_add_basemap`, `_optional_contextily`, `_require_matplotlib`/`_require_geopandas`, and the `ensure_under` + `ValidationSummary`-style output safety.

**Rationale**: The existing `plot_actual_vs_predicted()` is a fixed 2×3 six-panel figure across 0m/3m/6m horizons (explicitly out of scope). A new 2×1 builder reuses all styling primitives (alert colors, LatAm inset for global scope, no-basemap, padded extent) while producing exactly the required two panels (FR-024). Output safety mirrors `build_output_plan`/`validate_output_conflicts`: figure under `reports/launch/nowcasting_2026_04/visualizations/`, validation summary under `results/launch/nowcasting_2026_04/visualizations/`, refusing overwrite without `--overwrite`.

**Alternatives considered**: Parameterizing the existing six-panel function (rejected — different panel count/semantics, would entangle feature 002).

---

## Cross-cutting confirmations

- **Paths/ignore**: `.gitignore` ignores `results/*` and `reports/*`, so launch outputs (incl. large prediction CSVs) are not committed (FR-037). Comprehensive-source default added as a documented key in `configs/paths.example.json` and resolved via `ipcch.paths.external_path()`; machine-specific value goes in git-ignored `paths.local.json`.
- **Execution modes (FR-036)**: Mode 1 train-and-predict (heavy, approval-gated); Mode 2 `--skip-training --model-artifact-dir`; Mode 3 `--skip-prediction --predictions`. `--validate-only` validates only the inputs needed for the selected mode and never trains. Resolved mode + artifact paths recorded in `run_summary.json`.
- **Model artifacts**: four fitted regressors persisted (e.g., XGBoost JSON booster per target) under `results/launch/nowcasting_2026_04/model_artifacts/` so Mode 2 can reload them; feature column order persisted alongside for schema alignment.
- **Testing without heavy training**: smoke (`--help`, `--validate-only`), unit (pure functions on synthetic frames), integration (tiny synthetic CSV via Mode 3 and a tiny pre-fit model via Mode 2). Mode 1 training is never run by automation.
