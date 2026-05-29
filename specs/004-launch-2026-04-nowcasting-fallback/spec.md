# Feature Specification: April 2026 Global Nowcasting Launch (Comprehensive-CSV Fallback)

**Feature Branch**: `004-launch-2026-04-nowcasting-fallback`
**Created**: 2026-05-28
**Status**: Draft
**Input**: User description: "Launch April 2026 global nowcasting predictions for all IPCCH area_id units using the comprehensive feature CSV fallback plan."

## Overview

This is a **production global nowcasting launch** for the launch month **2026-04 (April 2026)**, not a held-out validation experiment. The launch trains the existing canonical four-regressor cumulative-phase workflow on eligible historical labeled rows from one comprehensive feature CSV, then predicts `phase2_worse` through `phase5_worse` and a discrete `overall_phase_pred` (via the canonical top-down threshold `th=0.2`) for **every eligible global April 2026 `area_id`**, regardless of whether April 2026 actual labels exist.

The launch is a **fallback** because the usual "0m model-ready" / April-specific X_test path may be problematic. Both training rows and April 2026 X_test rows are drawn directly from the same comprehensive feature CSV (`forecasting_subset_IPCCH_2026_target_corrected_deep_features.csv` under `assembled_IPCCH/features`), using its columns directly as features. No 0m model-ready subset, April-only interim X_test file, or multiscope 0m feature builder is used or depended upon.

**Fallback-nowcasting terminology**: This fallback launch is operationally a nowcasting launch because the prediction target is April 2026 contemporaneous crisis status. However, the fallback feature schema is drawn directly from the comprehensive feature CSV rather than the canonical `scope_0m_model_ready` feature schema. The launch report must state that results may not be directly comparable to prior canonical 0m model-ready experiments if the feature schema differs.

After predictions are produced, the launch performs an optional, **coverage-aware** comparison against **April 2026 actual** food-crisis labels only (no pooling across months), and produces a single two-panel actual-vs-predicted global crisis map following the existing visualization module's style and safety guardrails. April 2026 covered-subset metrics are post-launch descriptive comparison metrics only — not held-out validation performance, not model-selection evidence, and not threshold-tuning evidence.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Generate April 2026 global predictions for all eligible areas (Priority: P1)

As the launch analyst, I run one command from the repository root that trains the canonical cumulative-regression workflow on eligible historical labeled rows (strictly before 2026-04-01) from the comprehensive feature CSV, constructs April 2026 X_test from all April 2026 rows in the same CSV, predicts the four cumulative targets, derives `overall_phase_pred` with `th=0.2`, and writes a standardized per-area prediction CSV plus run metadata — covering every eligible global April 2026 `area_id` even where actual labels are absent.

**Why this priority**: This is the core deliverable. Without it there is no launch. It delivers shareable April 2026 phase predictions on its own.

**Independent Test**: Run the launch with training approved on the comprehensive source; confirm a predictions CSV is produced containing one row per eligible April 2026 `area_id`, with the four cumulative prediction columns, `overall_phase_pred`, and all required provenance columns, and a `run_summary.json` recording scale, source, cutoff, launch month, threshold, row/feature counts, and output paths.

**Acceptance Scenarios**:

1. **Given** the comprehensive feature CSV with valid labeled rows before 2026-04-01 and April 2026 rows, **When** the launch runs with training approved, **Then** four cumulative regressors are trained on pre-cutoff valid-target rows only and produce `phase2_worse_pred`…`phase5_worse_pred` for every eligible April 2026 `area_id`.
2. **Given** raw cumulative predictions for April 2026, **When** the canonical conversion rule with `th=0.2` is applied, **Then** each area receives an `overall_phase_pred` in 1–5 and no experimental calibration/router/hurdle/threshold-tuning is applied.
3. **Given** April 2026 rows where `overall_phase` and phase-percentage labels are missing, **When** X_test is constructed, **Then** those areas are still predicted (coverage is not restricted to actual-labeled areas).
4. **Given** existing prediction artifacts already present at the output paths, **When** the launch runs without explicit overwrite approval, **Then** the launch refuses to overwrite them and reports the conflict.

---

### User Story 2 - Preflight validation without heavy training (Priority: P1)

As the launch analyst, before committing to a heavy training run I execute a `--validate-only` / `--dry-run` mode that checks source existence/readability, required identifier columns, date constructability, presence of valid pre-cutoff training rows, presence of April 2026 X_test rows, target derivability, feature-schema alignment between training and X_test, comparison-coverage feasibility, visualization inputs, and output-path safety — and produces a feature schema report and input-validation summary, all without fitting any model.

**Why this priority**: Heavy training must be gated and de-risked. The analyst needs to confirm the fallback source is usable and the schema is sound before approving training next week.

**Independent Test**: Run `--validate-only`; confirm it exits without training, writes an input validation summary and a feature schema report, and reports clear pass/fail on each required check (including a hard stop if no April 2026 rows exist).

**Acceptance Scenarios**:

1. **Given** a comprehensive source missing `area_id`, `year`, or `month`, **When** validate-only runs, **Then** it reports the missing identifier columns and stops without training.
2. **Given** a comprehensive source with no `year=2026, month=4` rows, **When** validate-only runs, **Then** it stops and reports that a valid comprehensive source with April 2026 rows is required.
3. **Given** a valid source, **When** validate-only runs, **Then** it writes a feature schema report listing included and excluded columns and confirms the training feature schema and April 2026 X_test feature schema match (or documents any handled differences).
4. **Given** `--help` or `--validate-only`, **When** invoked, **Then** no model is trained and no heavy computation occurs.
5. **Given** a skip mode requested without its required artifacts (`--skip-training` without `--model-artifact-dir`, or `--skip-prediction` without `--predictions`), **When** the CLI runs, **Then** it fails with a clear message; **and** `--validate-only` validates the inputs required for the selected execution mode without training.

---

### User Story 3 - Coverage-aware comparison to April 2026 actuals (Priority: P2)

As the launch analyst, after predictions exist I compare them to **April 2026 actual** food-crisis labels only, using actuals strictly for post-prediction comparison. The comparison joins April 2026 predictions to April 2026 actual labels where available, reports denominators and covered-area counts, and clearly states that metrics apply only to the April actual-covered subset when coverage is partial. These are descriptive covered-subset metrics only — not held-out validation, model-selection, or threshold-tuning evidence.

**Why this priority**: It gives a sanity check on launch quality but must never gate or contaminate the production predictions; predictions stand on their own (US1).

**Independent Test**: Provide partial April 2026 actual labels; confirm the comparison joins by `area_id` to April actuals only (no pooling), reports prediction/actual/intersection counts and coverage share, and emits class distributions, a confusion matrix, and crisis metrics on the April actual-covered subset only, with explicit partial/unavailable-coverage warnings.

**Acceptance Scenarios**:

1. **Given** April 2026 actual labels covering a subset of areas, **When** the comparison runs, **Then** April predictions are joined to April actuals by `area_id` (no Feb/Mar pooling and no latest-across-months selection) and only the covered subset is scored.
2. **Given** partial or unavailable April actual coverage, **When** metrics are computed, **Then** the report states the denominator and that metrics apply only to covered areas (or reports actual coverage as unavailable), and does not claim full validation; predictions are still produced regardless.
3. **Given** April actual labels, **When** the launch runs, **Then** those labels are loaded only after predictions are generated and are never used for training, feature construction, threshold selection, calibration, model selection, or X_test coverage.
4. **Given** comparable covered data, **When** metrics are computed, **Then** accuracy, macro-F1, weighted-F1, 3+ and 4+ crisis precision/recall/F1/F2, and confusion-driven rates (true-4-as-3, true-2-as-3) are reported where computable.

---

### User Story 4 - Two-panel actual-vs-predicted global crisis map (Priority: P2)

As the launch analyst, I produce one vertical two-subplot figure — top panel: April 2026 actual crisis for `area_id` units with April actual labels (`overall_phase >= 3`); bottom panel: April 2026 predicted crisis for all eligible predicted `area_id` units (`overall_phase_pred >= 3`) — following the existing visualization module's alert/no-alert colors, spatial-join validation, output-path safety, overwrite protection, optional no-basemap mode, and Latin America inset/thumbnail convention. The figure and report make explicit that actual and predicted coverage may differ. The figure must not implement top-risk comparison maps or the six-panel actual-vs-predicted alert map.

**Why this priority**: It is the headline visual for collaborators but depends on predictions (US1) and benefits from comparison (US3).

**Independent Test**: With predictions and partial April actuals plus a spatial boundary file, generate the two-panel map; confirm a validation summary records both panels' counts (predicted, April-actual-covered, mapped-predicted, mapped-actual, unmatched prediction/actual `area_id` values, duplicate spatial keys) and that the figure title/caption states coverage may differ, with no silent dropping of unmatched joins, a hard failure on duplicate spatial keys, and no overwrite without `--overwrite`.

**Acceptance Scenarios**:

1. **Given** predictions and April 2026 actuals, **When** the map is generated, **Then** the figure has exactly two vertical subplots (April actual on top, April predicted below) and uses the module's alert/no-alert colors and Latin America inset where practical.
2. **Given** unmatched prediction or actual `area_id` values, **When** the map is generated, **Then** they are recorded in the validation summary and mapped-coverage report and are not silently dropped; the map may render the matched subset only, but the report must state mapped coverage.
3. **Given** duplicate spatial join keys, **When** the map is generated, **Then** the workflow hard-fails rather than rendering an ambiguous join.
4. **Given** an existing figure at the target path, **When** the map runs without `--overwrite`, **Then** it refuses to overwrite.
5. **Given** missing basemap dependencies, **When** `--no-basemap` is set, **Then** the map still renders.
6. **Given** partial April actual coverage, **When** the figure is produced, **Then** its title/subtitle/caption (or adjacent report text) states actual coverage is partial and does not imply actual coverage equals full prediction coverage.

---

### User Story 5 - Human-readable launch report for collaborators (Priority: P3)

As the launch analyst, I get a concise human-readable launch report (and supporting markdown summaries) stating launch month and global scale, the fallback comprehensive source path, training cutoff, training row count and date coverage, number of predicted April 2026 areas, X_test coverage, feature schema status, predicted phase distribution, phase2–5 worse distribution summaries, comparison coverage and covered-subset metrics, map coverage/interpretation, partial-coverage warnings, and explicit statements that this is a production launch (not a held-out validation) and a fallback comprehensive-source launch that may not be directly comparable to prior 0m model-ready experiments if the feature schema differs.

**Why this priority**: It packages the launch for sharing; it depends on the artifacts produced by US1–US4.

**Independent Test**: After a run, open the launch report and confirm every listed section is present, including the production-launch and fallback-comparability statements and partial-coverage warnings.

**Acceptance Scenarios**:

1. **Given** a completed run, **When** the report is generated, **Then** it includes the production-launch statement and the fallback comprehensive-source comparability caveat.
2. **Given** partial actual coverage, **When** the report is generated, **Then** it states metrics apply to covered areas only.

---

### Edge Cases

- **No April 2026 rows in source** → hard stop with a clear message that a valid comprehensive source with April 2026 rows is required.
- **Duplicate `area_id` rows for April 2026** → stop, or apply a documented deterministic duplicate rule and report it; never silently keep an arbitrary row.
- **Non-numeric model feature columns after canonical preprocessing** → reported in the feature schema report; the workflow must require numeric features.
- **Training-target derivability**: rows lacking sufficient phase-percentage targets to derive `phase2_worse`…`phase5_worse` (and lacking precomputed `*_worse`) are excluded from training and the exclusion is reported.
- **`overall_phase == 0` or missing** in a candidate training row → excluded from training.
- **Actual labels absent entirely** → predictions still produced; comparison and actual map panel report zero covered areas with warnings rather than failing.
- **Feature schema mismatch** between training and April 2026 X_test → reported clearly; missing/extra columns handled and documented rather than silently passed.
- **Output path already exists** → refuse to overwrite predictions, summaries, or figures without explicit overwrite approval.
- **2026-02 / 2026-03 rows** present before the cutoff → their inclusion in training is decided by the declared launch policy and documented (see Temporal Validation / Launch Policy and the open policy item for `/speckit-plan`).

## Requirements *(mandatory)*

### Functional Requirements

#### Scope & framing

- **FR-001**: The feature MUST identify itself as a production April 2026 global fallback launch, not a held-out validation experiment, in its outputs and report.
- **FR-002**: The feature MUST operate at global scale only and MUST NOT implement Somalia-local, country-specific, region-specific, or area-specific model variants, calibration, or post-processing. Country/region/name fields, when present, MUST be preserved for reporting, grouping, joins, and visualization. They may enter the model only as identifier-derived model features when required by the existing canonical identifier-feature workflow, as specified in FR-011a; raw reporting identifiers MUST NOT be passed directly to the model unless that is exactly how the canonical identifier-feature workflow represents them.
- **FR-003**: The launch MUST use the existing canonical four-regressor cumulative-phase workflow (`phase2_worse`, `phase3_worse`, `phase4_worse`, `phase5_worse`) and MUST NOT introduce calibration, correction routing, new thresholds, new features, or a new model architecture.

#### Source & data selection

- **FR-004**: Both training rows and April 2026 X_test rows MUST be read from the same comprehensive feature CSV (default: `…/assembled_IPCCH/features/forecasting_subset_IPCCH_2026_target_corrected_deep_features.csv`).
- **FR-005**: The launch MUST NOT use the 0m model-ready subset, the April-only interim X_test file, or any multiscope 0m feature builder, and MUST NOT reconstruct 0m lag features or regenerate a full all-month model-ready dataset.
- **FR-006**: The launch MUST validate the comprehensive source: it exists and is readable; required identifier columns `area_id`, `year`, `month` are present; a date can be constructed (from `year`/`month` if needed); valid labeled training rows exist before 2026-04-01; April 2026 X_test rows exist; the four cumulative targets are derivable for training; and April 2026 X_test can be constructed without actual labels.
- **FR-007**: Training rows MUST be filtered to records strictly before 2026-04-01 with `overall_phase` present and not equal to 0, and with sufficient phase-percentage targets to derive `phase2_worse`…`phase5_worse` (or those `*_worse` columns already present). April 2026 rows and any actual-comparison labels MUST be excluded from training.
- **FR-008**: April 2026 X_test MUST be filtered to `year=2026, month=4` and MUST preserve all eligible April 2026 `area_id` rows regardless of missing `overall_phase` or phase-percentage labels. Target availability MUST NOT define prediction coverage, and X_test MUST NOT be inner-joined to actual labels.
- **FR-009**: If duplicate `area_id` rows exist for April 2026, the launch MUST by default **hard-stop**. An optional override `--dedup-rule latest-date` MAY be supplied, permitted only when a date/timestamp column exists and the selected row is deterministic; when used, the launch MUST write a duplicate-resolution report listing all duplicated `area_id` values, candidate row counts, the selected date, and the dropped rows. The launch MUST NEVER silently retain an arbitrary duplicate.
- **FR-010**: If the comprehensive source contains no April 2026 prediction rows, the launch MUST stop and report that a valid comprehensive source with April 2026 rows is required.

#### Features

- **FR-011**: The launch MUST use comprehensive-source columns directly as the model feature source, applying the identifier-feature policy (FR-011a) and the target-derived exclusion rule (FR-011b) below.
- **FR-011a** *(Identifier-feature policy — mandatory)*: The launch MUST use the existing canonical identifier-feature setting. Identifier-derived model features MUST be included when they are present in, or constructible from, the comprehensive fallback source consistently with the existing canonical identifier-feature workflow. Raw identifiers and reporting fields (e.g., `area_id`, country/region/name fields) MUST be preserved for output/reporting/joins but MUST NOT be passed directly to the model unless that is exactly how the canonical identifier-feature workflow already represents them. The feature schema report MUST list: (a) identifier-derived model features included, (b) raw identifier/reporting columns excluded from modeling, and (c) any expected identifier-derived features missing from the comprehensive fallback source. If required identifier-derived model features are unavailable and cannot be constructed consistently with the canonical identifier-feature workflow, the launch MUST stop or require an explicit override, because comparability with the intended identifier-feature launch would be broken.
- **FR-011b** *(Target-derived exclusion rule — documented)*: The launch MUST exclude from model features all target/label columns — `overall_phase`, `phase1_percent`…`phase5_percent`, `phase2_worse`…`phase5_worse`, and `overall_phase_pred` if present — and MUST exclude target-derived/diagnostic columns following the existing feature-engineering guardrails, including columns matching patterns such as `overall_phase_lag`, `target_relative`, `diagnostic`, `phase_target`, and `target`. All excluded columns and their exclusion reasons MUST be written to the feature schema report. The launch MUST NOT silently include any target-derived column as a model feature.
- **FR-012**: The same selected feature columns MUST be used for both training and April 2026 X_test, and all model feature columns MUST be numeric after canonical preprocessing.
- **FR-013**: The launch MUST produce a feature schema report documenting included and excluded columns (with exclusion reasons and the identifier-feature listing of FR-011a) and comparing the training feature schema to the April 2026 X_test feature schema, explaining any handled differences.

#### Training

- **FR-014**: The launch MUST train four canonical cumulative regressors using all eligible valid-target training rows strictly before 2026-04-01, using the old/canonical hyperparameters and model settings where applicable.
- **FR-015**: April 2026 actual labels and any April 2026 comparison labels MUST NOT influence fitting, feature selection, threshold selection, calibration, or model selection.
- **FR-016**: The launch policy MUST document whether 2026-02 and 2026-03 rows are included in training and why that is valid for an April 2026 nowcasting launch.

#### Prediction

- **FR-017**: The launch MUST output predicted cumulative values for every eligible April 2026 `area_id` as `phase2_worse_pred`…`phase5_worse_pred` (supporting the canonical `phase2_pred`…`phase5_pred` aliases if the existing workflow uses them), with clipping/handling consistent with the canonical workflow.
- **FR-017a** *(Prediction validation & non-finite handling)*: Predicted cumulative values MUST be validated and clipped/handled according to the canonical workflow **before** phase conversion. NaN, infinite, or otherwise non-finite cumulative predictions MUST be reported in prediction validation outputs and MUST NOT silently produce an `overall_phase_pred`. For any non-finite cumulative prediction, the launch MUST either fail with a clear error or apply a documented canonical fallback. The prediction distribution summary (or a dedicated prediction validation summary) MUST report counts of clipped values, non-finite predictions, and rows excluded or failed due to invalid predictions.
- **FR-018**: The launch MUST convert the validated, finite cumulative predictions to `overall_phase_pred` using the existing canonical conversion rule with `th=0.2`, and MUST NOT apply Experiment 1 calibration, the correction router, a threshold sweep, a phase4 hurdle model, or any other experimental post-processing.
- **FR-019**: Predictions MUST cover all eligible April 2026 `area_id` units (not only actual-labeled areas), and the prediction output MUST preserve all eligible areas unless exclusions are explicitly reported (including any rows excluded under FR-017a).

#### Comparison (post-prediction only)

- **FR-020**: The launch MUST compare April 2026 predictions against **April 2026 actual** food-crisis labels only, joining by `area_id` to the April actual labels where available. It MUST NOT pool February/March/April actuals and MUST NOT keep a latest observation across months. April covered-subset metrics are descriptive comparison metrics only — not held-out validation performance, not model-selection evidence, and not threshold-tuning evidence.
- **FR-021**: Actual crisis MUST default to actual `overall_phase >= 3` (unless a documented actual-crisis flag is supplied); predicted crisis MUST default to `overall_phase_pred >= 3`.
- **FR-022**: The comparison MUST be coverage-aware and report: number of predicted April 2026 areas; number of April actual-labeled areas; intersection (April actual-covered) count; coverage share vs all predicted areas; class distribution of April actuals; class distribution of April predictions on the covered subset; confusion matrix on the covered subset; accuracy, macro-F1, weighted-F1; 3+ and 4+ crisis precision/recall/F1/F2; true-phase-4-predicted-as-3 rate; and true-phase-2-predicted-as-3 rate — each where computable.
- **FR-023**: If April actual labels are unavailable, incomplete, partial, non-comparable, or use a different label definition, the launch MUST still produce predictions and MUST record warnings (including reporting actual coverage as unavailable where applicable) rather than forcing full-validation claims; metrics MUST report their denominator and covered-area count.

#### Visualization

- **FR-024**: The launch MUST produce exactly one two-panel (vertical) actual-vs-predicted global crisis map: top panel April 2026 actual crisis for `area_id` units with April actual labels (`overall_phase >= 3`), bottom panel April 2026 predicted crisis for all eligible predicted `area_id` units (`overall_phase_pred >= 3`). It MUST NOT implement the six-panel actual-vs-predicted alert map or any top-risk comparison maps.
- **FR-025**: The map MUST follow the existing visualization module's guardrails and style: alert/no-alert color conventions (or a canonical style constant if exposed), spatial boundary loading and `area_id` alias handling, spatial-join validation, output-path safety, overwrite protection, validation-summary writing, optional no-basemap behavior, and the Latin America inset/thumbnail convention where practical.
- **FR-026**: The map MUST make coverage explicit: the actual panel shows only areas with April actuals and a successful spatial join; the predicted panel may show all eligible predicted areas with a successful join; and the figure/report text MUST state that actual coverage is partial when it is and MUST NOT imply actual coverage equals full prediction coverage.
- **FR-027** *(Spatial join failure policy)*: Duplicate spatial join keys MUST be a hard failure: the map step MUST hard-fail **before rendering**, surfacing the duplicate-key details in the error message and, when possible, writing them to an error validation summary. Consequently, **on a successful map run the duplicate spatial key count MUST be 0 and the duplicate spatial key list MUST be empty.** Unmatched prediction or actual `area_id` values are NOT hard failures: they MUST be recorded in the validation outputs and the mapped-coverage report; the map MAY render the matched subset only when unmatched counts are nonzero, but the report MUST state mapped coverage and MUST NOT silently drop unmatched IDs. The visualization validation summary MUST distinguish and include: actual source path, prediction source path, spatial boundary source path, actual month (2026-04), prediction month (2026-04), predicted area count, April actual-covered area count, mapped-predicted count, mapped-actual count, the unmatched prediction `area_id` values, the unmatched actual `area_id` values, the duplicate spatial key count/list (0/empty on success), and output path.
- **FR-028**: The map MUST NOT overwrite existing figure outputs unless `--overwrite` is explicitly set, and MUST support a no-basemap mode that does not fail when optional basemap dependencies are unavailable.

#### Outputs & provenance

- **FR-029**: Machine-readable outputs MUST be written under `results/launch/nowcasting_2026_04/` and human-readable reports/figures under `reports/launch/nowcasting_2026_04/`; visualization validation summaries under `results/launch/nowcasting_2026_04/visualizations/` and figures under `reports/launch/nowcasting_2026_04/visualizations/`. Output filenames MUST reflect April-only actual comparison (no pooled-window naming), specifically: `actual_crisis_2026_04_by_area.csv`, `actual_coverage_summary_2026_04.csv`, `comparison_metrics_actual_2026_04_vs_prediction_2026_04.csv`, `class_distribution_actual_2026_04_vs_prediction_2026_04.csv`, `confusion_matrix_actual_2026_04_vs_prediction_2026_04.csv`, `binary_crisis_metrics_actual_2026_04_vs_prediction_2026_04.csv`, and the figure `ipcch_2026_04_global_actual_vs_predicted_crisis_map.png`.
- **FR-030**: The April 2026 prediction CSV MUST include: `area_id`, `year`, `month`, `date` or `launch_month`, country/region fields if available, the four cumulative prediction columns (`phase{2..5}_worse_pred` or `phase{2..5}_pred`), `overall_phase_pred`, `model_workflow`, `scale`, `threshold`, `training_cutoff`, `comprehensive_source`, and `run_id`.
- **FR-031**: A `run_summary.json` MUST record scale, comprehensive source, training cutoff, launch month, threshold, model workflow, execution mode (FR-036) with any supplied model/prediction artifact paths, row counts, feature counts, output paths, and visualization paths when generated; the launch MUST also emit a resolved-config record, input validation summary, training data summary, feature schema report, X_test coverage report, April 2026 eligibility list, model-aligned X_test artifact, prediction distribution summary, prediction validation summary (clipped/non-finite/excluded counts per FR-017a), and predicted phase distribution.
- **FR-032**: Actual-comparison outputs MUST preserve, per area: `area_id`, `actual_month`, `actual_overall_phase` (if available), `actual_crisis` flag, April `predicted_overall_phase`, April `predicted_crisis` flag, predicted cumulative values where available, coverage status, comparison-eligibility flag, spatial-join-eligibility flag, and `reason_not_compared` where applicable.
- **FR-033**: The visualization input record MUST include: `area_id`, `actual_month` (always 2026-04), `actual_overall_phase`, `actual_crisis`, `predicted_overall_phase`, `predicted_crisis`, `comparison_eligible`, `actual_coverage_status`, `prediction_coverage_status`, and `spatial_join_status`.
- **FR-034**: The launch MUST NOT overwrite existing prediction, summary, or figure artifacts unless the user explicitly approves; existing-output conflicts without approval MUST stop the run with a clear message.

#### CLI, execution safety & code placement

- **FR-035**: The launch MUST provide a CLI runnable from the repository root with no hardcoded absolute paths, resolving paths through `ipcch.paths` or explicit CLI flags. It MUST expose: launch month (default 2026-04), scale (default global), training cutoff (default 2026-04-01), comprehensive source path (default the fallback CSV), output root, optional actual-comparison files/paths, optional spatial boundary path, and `--no-basemap` / `--overwrite` visualization flags. It MUST also expose the execution-mode flags of FR-036 (`--skip-training --model-artifact-dir <dir>`, `--skip-prediction --predictions <csv>`). The `--threshold` flag is fixed/informational: it defaults to `0.2`, the only accepted value is `0.2`, passing any other value MUST fail with a clear message that the launch is constitutionally fixed to canonical `th=0.2` (no tuning), and `run_summary.json` MUST record `threshold=0.2`. This requirement lists the core CLI flags; `contracts/cli.md` is the complete and authoritative flag list, including optional flags such as `--dedup-rule`, `--identifier-source`, `--allow-missing-identifier-features`, `--half-life-months`, `--no-time-decay`, `--approve-training`, `--drop-nonfinite-predictions`, and the hyperparameter override flags (`--hyperparameter-set`, `--hyperparameters`, `--hyperparameters-p3`).
- **FR-036** *(Execution modes — unambiguous)*: The CLI MUST support three clearly distinct execution modes selected by explicit flags, and MUST record the resolved mode plus any supplied model/prediction artifact paths in `run_summary.json`:
  - **Mode 1 — train-and-predict (default)**: fit the four regressors from the comprehensive source, generate April 2026 predictions, then optionally compare/report/map.
  - **Mode 2 — predict-with-supplied-models** (`--skip-training --model-artifact-dir <dir>`): skip training, load supplied fitted model artifacts, build April 2026 X_test from the comprehensive source, generate predictions, then optionally compare/report/map.
  - **Mode 3 — report-from-supplied-predictions** (`--skip-prediction --predictions <csv>`): skip both training and prediction, load a supplied April 2026 prediction CSV, then run comparison/reporting/visualization only.
  If a skip mode is requested without its required supplied artifacts (model-artifact directory for Mode 2, prediction CSV for Mode 3), the CLI MUST fail with a clear message. The CLI MUST also support `--help` and a `--validate-only`/`--dry-run` mode that validates the inputs required for the selected mode — inputs, source coverage, feature schema, comparison-coverage feasibility, visualization inputs, and output paths — without running heavy training. Heavy model training (Mode 1) MUST be gated behind explicit user approval and MUST NOT be executed by automation without it.
- **FR-037**: New reusable code MUST live under `src/ipcch/` (e.g., `launch_nowcasting.py`, `launch_comparison.py`, `launch_visualizations.py`, or extensions to `forecast_diagnostics.py`), reusing existing canonical model utilities and the existing visualization module's guardrails; it MUST NOT duplicate upstream multiscope feature-engineering logic. Generated large prediction CSVs MUST remain under `results/` and MUST NOT be committed if ignored by project rules.

### Temporal Validation / Launch Policy *(mandatory — Constitution Principle I)*

- **Split policy declared**: **All-prior-history holdout adapted for a single launch month.** Training uses all eligible valid-target observations strictly before 2026-04-01; the launch month 2026-04 is the prediction target. No 2026-04 actual labels are used for fitting or preprocessing.
- **Feb/Mar 2026 inclusion**: Whether 2026-02 and 2026-03 rows are included in training is governed by this policy and MUST be documented in the plan with justification for an April 2026 nowcasting launch (these months precede the 2026-04-01 cutoff and carry observed targets, so they are eligible under the all-prior-history rule unless the plan declares otherwise).
- **Comparison isolation**: April 2026 actual labels are used only for post-prediction comparison, loaded only after predictions are generated, and never used for training, feature construction, threshold selection, calibration, model selection, or X_test coverage. Because the actual comparison is April-only and April 2026 actuals are never used in training, there is no Feb/Mar actual-comparison leakage concern; the Feb/Mar training-inclusion documentation requirement above is independent of actual comparison.
- **Sample-weighting policy**: The launch uses the canonical time-decay sample weighting setting from the existing deep-feature workflow, anchored at the April 2026 launch month and computed only from training-row dates strictly before 2026-04-01. Sample weights must not use April 2026 actual labels or any post-launch information. The resolved weighting mode, half-life, anchor month, and whether weighting is enabled or disabled must be recorded in `run_summary.json` and the launch report. (Default: enabled, matching the canonical workflow; `--no-time-decay` fits unweighted.)

### Key Entities *(include if feature involves data)*

- **Comprehensive feature CSV (fallback source)**: The single authoritative input for both training rows and April 2026 X_test; keyed by `area_id` with `year`/`month`; contains feature columns plus target/label columns to be excluded from features.
- **Training dataset**: Valid-target rows strictly before 2026-04-01 (selected numeric features; targets `phase2_worse`…`phase5_worse`).
- **Launch X_test (April 2026)**: All eligible `year=2026, month=4` rows, aligned to the trained feature schema; coverage independent of actual-label availability.
- **April 2026 predictions**: Per-`area_id` cumulative predictions, `overall_phase_pred`, and provenance fields.
- **April actual crisis layer**: April 2026 actual observations by `area_id` (actual month: 2026-04), with `actual_crisis` derived from `overall_phase >= 3`. No cross-month pooling and no latest-across-months selection.
- **Comparison table**: Coverage-aware join of April predictions and April actuals with eligibility/coverage flags (April actual-covered subset).
- **Two-panel crisis map + validation summary**: Vertical April-actual(top)/April-predicted(bottom) figure plus a join-validation record.
- **Run metadata**: Resolved config, run summary, schema/coverage/distribution reports.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A single command run from the repository root produces an April 2026 prediction record for 100% of eligible global April 2026 `area_id` units present in the comprehensive source (after the documented duplicate rule), with zero eligible areas dropped for lack of actual labels.
- **SC-002**: 100% of emitted `overall_phase_pred` values are in 1–5 and are derived solely from finite, validated cumulative predictions via `th=0.2`, with no experimental post-processing applied; no non-finite cumulative prediction silently yields a phase label.
- **SC-002a**: Every clipping and non-finite-prediction event is visible in the prediction validation outputs (counts of clipped values, non-finite predictions, and rows excluded/failed), and a non-finite cumulative prediction either fails with a clear error or is handled by the documented canonical fallback.
- **SC-003**: The prediction CSV contains every required column (including `run_id` and `comprehensive_source`), and the run summary records scale, source, cutoff, launch month, threshold, model workflow, execution mode (with any supplied model/prediction artifact paths), row counts, feature counts, and all output/visualization paths — verifiable by inspecting the two files.
- **SC-004**: `--help` and `--validate-only`/`--dry-run` complete without training any model and produce an input-validation summary and a feature schema report; a source lacking April 2026 rows causes a hard stop with the prescribed message; and each of the three execution modes either runs with its required artifacts or fails with a clear message when they are missing.
- **SC-005**: The feature schema report shows the training and April 2026 X_test feature sets are identical (or documents 100% of differences and how they were handled), and 100% of model feature columns are numeric.
- **SC-006**: The actual comparison reports exact denominators (predicted-area count, April actual-covered-area count, intersection count, coverage share) and computes all requested covered-subset metrics where comparable; when coverage is partial or unavailable, every metric output and the report explicitly scope to the covered subset (or report actual coverage as unavailable). Reported metrics are labeled descriptive comparison metrics, not validation/model-selection/threshold-tuning evidence.
- **SC-007**: The two-panel map is produced with exactly two vertical subplots, accompanied by a validation summary that accounts for every predicted and every April actual-covered `area_id` (mapped and unmatched counts reconcile; unmatched IDs are listed), duplicate spatial keys cause a hard failure, and zero unmatched joins are silently dropped.
- **SC-008**: No existing prediction, summary, or figure artifact is overwritten in any run that did not pass explicit overwrite approval (`--overwrite` for figures / approved overwrite for artifacts).
- **SC-009**: All machine-readable outputs reside under `results/launch/nowcasting_2026_04/` and all human-readable reports/figures under `reports/launch/nowcasting_2026_04/`; no output is written elsewhere.
- **SC-010**: The launch report is self-contained for a collaborator: it states production-launch (not held-out validation), the fallback comprehensive-source caveat about comparability with prior 0m experiments, partial-coverage warnings, training cutoff and counts, predicted phase distribution, and map interpretation — all present in one document.

## Assumptions

- The canonical cumulative-regression utilities (4-regressor training, `convert_prob_to_phase(th=0.2)`, metrics) already exist in `ipcch.food_crisis_functions` / `ipcch.forecast_diagnostics` and are reused rather than reimplemented.
- The existing visualization module (`ipcch.alert_risk_maps`) provides the reusable guardrails to follow/adapt: alert/no-alert color constants, spatial boundary loading with `area_id` alias handling, spatial-join validation, output-path safety (`ensure_under`), overwrite protection, validation-summary structure, optional no-basemap behavior, and the Latin America inset.
- The comprehensive feature CSV path is workspace-local: reached via `ipcch.paths.external_path("deep_features_2026_target_corrected_dataset")` resolved from the git-ignored `configs/paths.local.json` (or via an explicit `--comprehensive-source` flag). The key is documented as an example in `configs/paths.example.json` but is intentionally NOT added to `paths.py` `DEFAULT_EXTERNAL_PATHS`; an unresolved key with no explicit flag fails with a clear, actionable message (see `contracts/cli.md`).
- "Canonical hyperparameters" for this launch are the existing `configs/forecasting_hyperparameters.json` (+ `forecasting_hyperparameters_p3.json`) files — the same set used by the deep-feature workflow that consumes this comprehensive deep-feature source (see plan.md R3). These are used consistently for the launch; the CLI may expose a hyperparameter selector, but the forecasting set is the default and the documented canonical choice.
- The April 2026 actual-comparison label source is supplied via optional CLI inputs; if none is supplied, the comparison and the actual map panel report actual coverage as unavailable (zero covered areas) with warnings rather than failing, and predictions are still produced.
- The spatial boundary file for the map is supplied via an optional CLI input defaulting to the project's existing boundary default; the map runs in no-basemap mode when basemap dependencies are unavailable.
- Supplied artifacts for Mode 2 (fitted model directory) and Mode 3 (April 2026 prediction CSV) are expected to come from a prior Mode 1 run of this same launch workflow against a compatible comprehensive source / feature schema; the launch validates their compatibility (e.g., feature schema for Mode 2, required columns for Mode 3) rather than assuming it.
- A `run_id` is generated per run for provenance; its exact form is an implementation detail.
- Country/region fields, where present in the source, are carried through for reporting/grouping/joins/visualization only and never used to alter the global model.

## Out of Scope

- The 0m model-ready subset, the April-only interim X_test file, and any multiscope 0m feature engineering or full model-ready dataset regeneration.
- Experiment 1 calibration, historical annual-holdout calibration, ordinal correction router, phase4 hurdle model, wavelet/reservoir features, threshold tuning, or any change to `th=0.2`.
- Any Somalia-local, country-specific, region-specific, or area-specific launch variant or calibration/post-processing.
- The six-panel actual-vs-predicted alert map, top-risk comparison maps, and separate global/Somalia six-figure map suites.
- Pooling February/March/April 2026 actuals or keeping a latest observation across those months for comparison (comparison is April-only).
- Using April 2026 actual labels for training, calibration, threshold selection, model selection, or feature engineering; restricting predictions to actual-labeled areas; or treating full prediction coverage as actual comparison coverage.
- Amending the constitution; executing heavy training during planning/implementation without explicit user approval.
