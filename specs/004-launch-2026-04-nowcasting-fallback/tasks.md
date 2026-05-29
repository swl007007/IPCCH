---
description: "Task list for April 2026 Global Nowcasting Launch (Comprehensive-CSV Fallback)"
---

# Tasks: April 2026 Global Nowcasting Launch (Comprehensive-CSV Fallback)

**Input**: Design documents from `specs/004-launch-2026-04-nowcasting-fallback/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/cli.md ✓

**Tests**: Included. The project has `tests/{unit,smoke,integration}` and the spec's success criteria (SC-001…SC-010) are verification-oriented (`--validate-only`, coverage denominators, join reconciliation). Heavy Mode-1 training is NEVER run by tests — tests use tiny synthetic data, Mode 3, and a tiny pre-fit model for Mode 2.

**Organization**: Tasks grouped by user story. MVP = User Story 1 (+ shared Foundational + the Setup phase).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1–US5 maps to spec.md user stories
- Exact file paths included

## Path Conventions

Single project: reusable code in `src/ipcch/`, thin CLI in `scripts/modeling/`, tests in `tests/{unit,smoke,integration}/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create file skeletons and config wiring.

- [X] T001 Create empty module skeletons with module docstrings and `from __future__ import annotations`: `src/ipcch/launch_nowcasting.py`, `src/ipcch/launch_comparison.py`, `src/ipcch/launch_visualizations.py`
- [X] T002 Create the thin CLI entry point skeleton `scripts/modeling/run_launch_nowcasting_2026_04.py` with a self-locating `PROJECT_ROOT` / `PYTHONPATH=src` bootstrap and an `argparse` placeholder that imports from `ipcch.launch_nowcasting`
- [X] T003 [P] Document the comprehensive-source key `deep_features_2026_target_corrected_dataset` (pointing at `assembled_IPCCH/features/forecasting_subset_IPCCH_2026_target_corrected_deep_features.csv`) as an **example/documentation** entry in `configs/paths.example.json`. **NOTE: `paths.example.json` is NOT read by `ipcch.paths.external_path()` at runtime** — the key must be supplied in the git-ignored `configs/paths.local.json` (or passed via `--comprehensive-source`) for the CLI default to resolve. Do NOT add this workspace-specific path to `src/ipcch/paths.py` `DEFAULT_EXTERNAL_PATHS`. Confirm `quickstart.md` shows the exact `paths.local.json` entry to add (already drafted — verify parity)
- [X] T004 [P] Create test module placeholders: `tests/unit/test_launch_nowcasting.py`, `tests/unit/test_launch_comparison.py`, `tests/unit/test_launch_visualizations.py`, `tests/smoke/test_launch_cli.py`, `tests/integration/test_launch_end_to_end.py`, plus a tiny synthetic comprehensive-CSV fixture builder in `tests/conftest.py` (or a `tests/_fixtures/` helper) producing pre-2026-04 valid-target rows + April-2026 rows with `area_id`/`year`/`month`/phase columns/lat/lon/a few numeric features

**Checkpoint**: Skeletons exist; imports resolve.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Source validation, the feature pipeline, the feature schema report, output/path safety, and CLI/mode resolution — all shared by US1 and US2 and required before any story is testable.

**⚠️ CRITICAL**: No user story work begins until this phase is complete.

- [X] T005 [US-shared] Implement source loading + validation in `src/ipcch/launch_nowcasting.py` (`load_comprehensive_source`, `validate_source`): resolve the source from `--comprehensive-source` or `external_path("deep_features_2026_target_corrected_dataset")` — when the key is unresolved (not in `paths.local.json`) and no explicit flag is passed, **fail with a clear, actionable message** (missing key name; pass `--comprehensive-source <path>` or add the key to `configs/paths.local.json`; expected target file) rather than a raw `KeyError`, and surface this cleanly under `--validate-only`. Then: existence/readability; required `area_id`/`year`/`month`; date construction via `ipcch.forecasting_weight_decay.add_monthly_date`; presence of pre-cutoff valid-target rows and April-2026 rows; cumulative-target derivability via `derive_cumulative_targets`; hard-stop if no April rows (FR-006, FR-010) → emits `input_validation_summary.json` payload (dict)
- [X] T006 [US-shared] Implement the training-row filter (`build_training_frame`) in `src/ipcch/launch_nowcasting.py`: strictly before `--training-cutoff` (2026-04-01), `overall_phase` present and ≠ 0, four cumulative targets derivable/present; exclude April rows and any actual labels; record min/max date + per-month counts for the training data summary (FR-007, R4)
- [X] T007 [US-shared] Implement the April X_test builder (`build_xtest_april`) in `src/ipcch/launch_nowcasting.py`: filter `year=2026, month=4`; preserve all eligible `area_id` rows regardless of label availability; never inner-join to actuals; on duplicate `area_id` → **default hard-stop**; only with `--dedup-rule latest-date` (and only when a date/timestamp column exists) resolve deterministically and write a duplicate-resolution report (duplicated `area_id`s, candidate counts, selected date, dropped rows); never silently keep an arbitrary duplicate (FR-008, FR-009)
- [X] T008 [US-shared] Implement the feature pipeline (`apply_identifier_features`, `select_model_features`) in `src/ipcch/launch_nowcasting.py`. The identifier-feature implementation MUST match the existing canonical identifier-feature representation — do NOT introduce a new ad hoc identifier encoding:
  - If the canonical identifier-derived columns (e.g., `lat`/`lon`, `month_*`, `year_*`) already exist in the comprehensive fallback source, detect and include them as-is.
  - Otherwise apply the canonical helper `forecasting_weight_decay.add_identifier_features` (default ON) to construct them from raw identifiers using the default lookup `external_path("ipcch_2026_completed_dataset")` (overridable via `--identifier-source`); record the transformation details (source columns, lookup used, derived columns produced) for the feature schema report (T009). The schema report MUST record, per identifier-derived feature, whether it was **detected directly** in the comprehensive source or **constructed via lookup**. If construction via lookup is required but no lookup is configured, fail clearly (including in `--validate-only`).
  - Raw `area_id`/country/region/name fields remain reporting/join columns and MUST NOT be passed to the model unless the canonical identifier-feature workflow itself represents them as features.
  Then select features via `select_numeric_feature_columns`; enforce the FR-011b target-derived exclusion (`overall_phase`, `phase{1..5}_percent`, `phase{2..5}_worse`, `overall_phase_pred`, patterns `overall_phase_lag|target_relative|diagnostic|phase_target|target`); stop (unless `--allow-missing-identifier-features`) when required identifier-derived features cannot be produced or constructed consistently with the canonical workflow (FR-011a, FR-011b)
- [X] T009 [US-shared] Implement the feature schema report (`build_feature_schema_report`) in `src/ipcch/launch_nowcasting.py`. Because the FR-011b exclusion patterns include broad terms (e.g., `target`), every excluded column MUST be auditable. `feature_schema_report.csv` MUST include per column: `column`, `included_in_model`, `exclusion_reason`, `matched_pattern` (the exact pattern/rule that triggered exclusion, if any), `exclusion_family` (one of `target_label`, `target_derived`, `identifier_reporting`, `non_numeric`, `unused_extra`), `role`, `present_in_training`, `present_in_xtest`, `expected_identifier_feature_missing`, plus the T008 identifier-derived transformation details. Compare training vs April X_test feature sets; flag non-numeric survivors. **Emit a WARNING** (and record it in the input/feature-schema validation summary) if target-derived exclusion removes an unexpectedly large share of columns or removes any column outside the known target-derived families — do not silently drop large feature families without audit visibility (FR-013, SC-005, data-model §4)
- [X] T010 [US-shared] Implement output/path safety + run metadata scaffolding (`resolve_output_layout`, `guard_output_conflicts`, `write_run_summary`) in `src/ipcch/launch_nowcasting.py`, reusing `ipcch.alert_risk_maps.ensure_under` semantics and `ipcch.paths` (RESULTS_DIR/REPORTS_DIR): default roots `results/launch/nowcasting_2026_04/` and `reports/launch/nowcasting_2026_04/`; refuse overwrite of **production** outputs without approval. `guard_output_conflicts` MUST separate (a) the small set of **validate-only artifacts** (`input_validation_summary.json`, `feature_schema_report.csv`) from (b) **production outputs** (predictions, model artifacts, comparison, figures): in validate-only mode it MAY write/refresh (a) but MUST NOT write or overwrite (b); it should *report* intended production-output conflicts without blocking the preflight source/schema checks (unless the validate-only artifact paths themselves would be overwritten without `--overwrite`). `run_summary.json` records scale/source/cutoff/launch-month/threshold/model-workflow/execution-mode/artifact-paths/row+feature counts/output paths (FR-029, FR-031, FR-034, SC-009)
- [X] T011 [US-shared] Implement CLI argument parsing + execution-mode resolution in `scripts/modeling/run_launch_nowcasting_2026_04.py` per `contracts/cli.md`: all flags; resolve Mode 1/2/3 from `--skip-training`/`--skip-prediction`; treat `--threshold` as fixed/informational (default 0.2, only 0.2 accepted, any other value fails with a clear "constitutionally fixed to canonical th=0.2" message, recorded as `threshold=0.2` in `run_summary.json`); fail clearly when a skip mode lacks its required artifact (`--model-artifact-dir` / `--predictions`); parse/validate the hyperparameter override flags (`--hyperparameter-set {canonical,custom}`, `--hyperparameters`, `--hyperparameters-p3`) per `contracts/cli.md` — `custom` requires both override paths, supplying only one fails clearly. CLI parsing MUST follow the complete `contracts/cli.md` flag list, not only the abbreviated spec FR-035 list (FR-035, FR-036)
- [X] T012 [P] [US-shared] Unit tests in `tests/unit/test_launch_nowcasting.py` for T005–T009: source validation (missing id cols; no April rows hard-stop), training filter (cutoff/phase≠0/Feb-Mar inclusion), X_test preservation; duplicate April `area_id` → **fails by default**, and with `--dedup-rule latest-date` resolves deterministically + writes the duplicate-resolution report; feature exclusion (targets/patterns excluded; identifier-derived included), schema-report training-vs-xtest parity, exclusion-audit fields populated (`matched_pattern`, `exclusion_family`), and the over-exclusion warning fires when an out-of-family or oversized exclusion occurs
- [X] T012a [P] [US-shared] Path-resolution tests in `tests/smoke/test_launch_cli.py` (or `tests/unit/test_launch_nowcasting.py`): with the `deep_features_2026_target_corrected_dataset` key unresolved (no `paths.local.json` entry) and no `--comprehensive-source`, the CLI / `--validate-only` fails with the clear actionable message (not a raw `KeyError`); and passing `--comprehensive-source <fixture.csv>` explicitly bypasses the missing key and proceeds (FR-006, I1)

**Checkpoint**: Validation, filtering, feature schema, output safety, and CLI mode resolution all work and are unit-tested on synthetic data.

---

## Phase 3: User Story 1 - Generate April 2026 global predictions for all eligible areas (Priority: P1) 🎯 MVP

**Goal**: Train the four canonical cumulative regressors on pre-cutoff valid-target rows and predict every eligible April 2026 `area_id`, deriving `overall_phase_pred` via `th=0.2`, with full prediction validation and provenance.

**Independent Test**: With training approved on a (synthetic) comprehensive source, produce `predictions_2026_04_all_area_id.csv` with one row per eligible April `area_id`, all four cumulative preds, `overall_phase_pred ∈ {1..5}`, all required provenance columns, plus `run_summary.json`.

### Tests for User Story 1 ⚠️

- [X] T013 [P] [US1] Integration test (Mode 2, no heavy training) in `tests/integration/test_launch_end_to_end.py`: build a tiny pre-fit 4-model artifact dir, run `--skip-training --model-artifact-dir …`, assert predictions cover 100% of synthetic April areas and schema/columns match `contracts/cli.md` + data-model §5 (SC-001, SC-003)
- [X] T014 [P] [US1] Unit tests in `tests/unit/test_launch_nowcasting.py` for prediction validation (T016): clipping counts, non-finite → fail by default and excluded+reported under `--drop-nonfinite-predictions`; phase derivation yields 1–5 from finite cumulatives only (SC-002, SC-002a)

### Implementation for User Story 1

- [X] T015 [US1] Implement training (`train_cumulative_regressors`) in `src/ipcch/launch_nowcasting.py`: load the **canonical** hyperparameters `configs/forecasting_hyperparameters.json` (phases 2/4/5) + `configs/forecasting_hyperparameters_p3.json` (phase 3) — the consistent set per spec Assumptions and plan.md **R3** (the deep-feature workflow consuming this source uses them). The CLI exposes the documented override flags `--hyperparameter-set {canonical,custom}` / `--hyperparameters` / `--hyperparameters-p3` (see `contracts/cli.md`), but the forecasting set is the default; the resolved hyperparameter file paths + selected set MUST be recorded in `run_summary.json` and the launch report. Then: optional canonical time-decay weights anchored at launch month via `time_decay_weights` (`--half-life-months`, `--no-time-decay`, R5); per-target `prepare_target_matrices` + a canonical-mirroring `fit_model` (XGBRegressor; p3 hyperparams for phase3; `random_state=--seed`); persist 4 boosters + feature-column order to `model_artifacts/` (FR-014, FR-015)
- [X] T016 [US1] Implement prediction + validation (`predict_april`, `validate_and_clip_predictions`) in `src/ipcch/launch_nowcasting.py`: predict the four cumulative targets for all April rows; clip to [0,1] + round 2dp (canonical handling); detect non-finite → fail (listing area_ids) or exclude+report with `--drop-nonfinite-predictions`; emit prediction distribution + `prediction_validation_summary.json` (FR-017, FR-017a, SC-002a)
- [X] T017 [US1] Implement phase derivation (`derive_overall_phase`) in `src/ipcch/launch_nowcasting.py` using the **exact canonical phase-conversion helper** of the existing model workflow — `ipcch.forecast_diagnostics.reconstruct_phase_from_cumulative(th=0.2)` — on finite validated cumulatives; preserve all eligible areas. MUST NOT reimplement the top-down rule (FR-018, FR-019, R6)
- [X] T017a [P] [US1] Equivalence unit test in `tests/unit/test_launch_nowcasting.py`: prove `reconstruct_phase_from_cumulative(th=0.2)` produces the same `overall_phase` as the canonical `food_crisis_functions.convert_prob_to_phase(th=0.2)` / canonical top-down conversion on representative cumulative cases (clear phase 1–5, threshold boundary at exactly 0.2, non-monotone cumulatives, ties), so the prediction-only path is provably equivalent to the canonical conversion (FR-018, R6)
- [X] T018 [US1] Implement Mode 2 model loading (`load_model_artifacts`) in `src/ipcch/launch_nowcasting.py`: reload 4 boosters + feature order, align April X_test to that schema, then reuse T016/T017 (FR-036 Mode 2)
- [X] T019 [US1] Assemble + write the prediction CSV and distribution/eligibility/coverage artifacts in `src/ipcch/launch_nowcasting.py` (`write_prediction_outputs`): `predictions_2026_04_all_area_id.csv` with all required columns incl. `run_id`/`comprehensive_source`/`model_workflow`/`scale`/`threshold`/`training_cutoff`; `prediction_distribution_summary.csv`, `predicted_phase_distribution.csv`, `x_test_area_coverage.csv`, `april_2026_area_id_eligibility.csv`, model-aligned X_test artifact (FR-030, data-model §5/§6/§11)
- [X] T020 [US1] Wire Mode 1 (train→predict, approval-gated by `--approve-training`) and Mode 2 (predict-with-supplied-models) through the CLI `run()` in `scripts/modeling/run_launch_nowcasting_2026_04.py`; refuse Mode-1 training without `--approve-training`; record resolved mode + artifact paths in `run_summary.json` (FR-031, FR-036, Constitution V)

**Checkpoint**: US1 fully functional — April predictions for all eligible areas with provenance, runnable via Mode 1 (approved) and Mode 2.

---

## Phase 4: User Story 2 - Preflight validation without heavy training (Priority: P1)

**Goal**: `--validate-only`/`--dry-run` checks all inputs for the selected mode and emits the input-validation + feature-schema reports without fitting any model; `--help` does nothing heavy.

**Independent Test**: `--validate-only` exits without training, writes `input_validation_summary.json` + `feature_schema_report.csv`, hard-stops on missing id columns / no-April-rows, and validates mode-specific required artifacts.

### Tests for User Story 2 ⚠️

- [X] T021 [P] [US2] Smoke tests in `tests/smoke/test_launch_cli.py`: `--help` exits 0 with no computation; `--validate-only` on the synthetic fixture exits 0 and writes the two summaries; `--validate-only` with a source lacking April rows exits non-zero with the prescribed message; skip-mode without its artifact exits non-zero; and `--validate-only` run when prior production outputs already exist still completes source/schema validation and does NOT overwrite those production outputs (SC-004)

### Implementation for User Story 2

- [X] T022 [US2] Implement the validate-only/dry-run flow (`run_validation_only`) in `src/ipcch/launch_nowcasting.py`: run T005 + T008/T009 (no training/prediction); for the selected execution mode, validate only the required inputs (Mode 2 → model-artifact dir + feature order; Mode 3 → predictions CSV columns); validate comparison-coverage feasibility + visualization inputs + output-path safety. It MUST complete source/schema/mode validation **even when prior production outputs already exist** — production-output conflicts are *reported* (not raised) so preflight is not blocked — and it MUST NOT overwrite production outputs; only the validate-only artifacts (`input_validation_summary.json`, `feature_schema_report.csv`) are written, and those are guarded by `--overwrite` only if they themselves would be replaced (FR-006, FR-036, SC-004)
- [X] T023 [US2] Wire `--validate-only`/`--dry-run`, `--help`, and the heavy-training approval gate into the CLI in `scripts/modeling/run_launch_nowcasting_2026_04.py`; ensure no model fitting occurs in validation paths and that validate-only never overwrites production outputs while still reporting intended production conflicts (FR-036, Constitution V)

**Checkpoint**: Preflight validation works for all three modes without training; safe for automation.

---

## Phase 5: User Story 3 - Coverage-aware comparison to April 2026 actuals (Priority: P2)

**Goal**: After predictions, compare to April-2026 actuals only (no pooling), coverage-aware, descriptive-only metrics on the covered subset.

**Independent Test**: With partial synthetic April actuals, produce the comparison table + coverage summary + metrics, scoped to the covered subset, with warnings when partial/unavailable.

### Tests for User Story 3 ⚠️

- [X] T024 [P] [US3] Unit tests in `tests/unit/test_launch_comparison.py`: April-only join by `area_id` (no Feb/Mar pooling); coverage denominators (predicted/actual/intersection/share); covered-subset accuracy/macro-F1/weighted-F1, 3+/4+ P/R/F1/F2, true-4-as-3 & true-2-as-3; partial/unavailable coverage → warnings + denominator scoping; actuals never alter predictions (SC-006, FR-020–FR-023)

### Implementation for User Story 3

> **Actual-source isolation (applies to all US3 tasks)**: Actual-source loading MUST occur only **after** predictions exist (Modes 1/2) or **after** supplied predictions are validated (Mode 3). No actual-source dataframe may be passed into training, feature selection, X_test coverage, or prediction functions. The comparison module receives only the finished predictions plus the separately-loaded April actuals.

- [X] T025 [US3] Implement April actual loading + crisis layer (`load_april_actuals`) in `src/ipcch/launch_comparison.py`: filter to 2026-04 only; `actual_crisis = overall_phase>=3` (or documented `--actual-crisis-flag`); loaded only post-prediction (per the isolation note above) → `actual_crisis_2026_04_by_area.csv` (FR-020, FR-021, Constitution I)
- [X] T026 [US3] Implement the coverage-aware comparison (`compare_predictions_to_actuals`) in `src/ipcch/launch_comparison.py`: join April predictions↔actuals by `area_id`; per-area record with coverage/eligibility/reason flags; coverage summary; reuse `ipcch.forecast_diagnostics` metric helpers (multiclass + binary crisis) on the covered subset; F2 and confusion-rate additions where not already provided (FR-022, data-model §7/§8)
- [X] T027 [US3] Write comparison outputs + descriptive-only labeling in `src/ipcch/launch_comparison.py` (`write_comparison_outputs`): `actual_coverage_summary_2026_04.csv`, `comparison_metrics_actual_2026_04_vs_prediction_2026_04.csv`, `class_distribution_…csv`, `confusion_matrix_…csv`, `binary_crisis_metrics_…csv`, `unmatched_actual_area_id.csv`, `unmatched_prediction_area_id.csv`; every metric output labeled descriptive (not validation/selection/tuning) with denominators (FR-023, SC-006)
- [X] T028 [US3] Wire `--actual-source`/`--actual-crisis-flag` and the post-prediction comparison step into the CLI `run()` in `scripts/modeling/run_launch_nowcasting_2026_04.py` so the comparison step executes strictly **after** predictions are produced/validated (Modes 1/2) or supplied predictions are validated (Mode 3); the actual-source must never reach training/feature-selection/X_test/prediction code paths (runs in Modes 1/2/3 when actuals supplied)

**Checkpoint**: Comparison runs coverage-aware against April actuals without contaminating predictions.

---

## Phase 6: User Story 4 - Two-panel actual-vs-predicted global crisis map (Priority: P2)

**Goal**: One 2×1 vertical figure (April actual top, April predicted bottom) reusing visualization guardrails, with a validation summary that records unmatched IDs and hard-fails on duplicate spatial keys.

**Independent Test**: With predictions + partial actuals + a (synthetic) boundary file, produce the PNG + validation summary reconciling mapped/unmatched counts; duplicate keys hard-fail; `--no-basemap` works without contextily; no overwrite without `--overwrite`.

### Tests for User Story 4 ⚠️

- [X] T029 [P] [US4] Unit tests in `tests/unit/test_launch_visualizations.py` for the recording spatial join (T030): matched subset returned; unmatched prediction/actual `area_id`s recorded (not raised); duplicate spatial keys raise a hard failure before rendering; on a successful run the duplicate-key count is 0 and the list is empty; validation-summary fields present and counts reconcile (FR-027, SC-007)

### Implementation for User Story 4

- [X] T030 [US4] Implement the launch-specific recording spatial join (`join_for_two_panel`) in `src/ipcch/launch_visualizations.py`: reuse `alert_risk_maps.load_spatial_boundaries` + `normalize_area_id`; render matched subset, record unmatched prediction/actual IDs (not hard failures); **hard-fail on duplicate join keys before rendering**, surfacing duplicate-key details in the error + an error validation summary (so successful runs always report duplicate-key count=0 / empty list); build the visualization input record (data-model §9) (FR-027, R8)
- [X] T031 [US4] Implement the two-panel figure (`plot_two_panel_actual_vs_predicted`) in `src/ipcch/launch_visualizations.py`: 2×1 vertical (April actual `overall_phase>=3` top; April predicted `overall_phase_pred>=3` bottom) reusing `alert_risk_maps` `NO_ALERT_COLOR`/`ALERT_COLOR`, `_plot_binary_layer`, `_latam_mask`/`_add_latam_inset` (global), `_set_padded_extent`, `_add_basemap`/`_optional_contextily`, `_require_matplotlib`; coverage-explicit title/caption; `--no-basemap` safe (FR-024, FR-025, FR-026, FR-028, R9)
- [X] T032 [US4] Implement map output safety + validation summary writing (`write_map_outputs`) in `src/ipcch/launch_visualizations.py`: figure → `reports/launch/nowcasting_2026_04/visualizations/ipcch_2026_04_global_actual_vs_predicted_crisis_map.png`; `april_2026_crisis_map_validation_summary.json` + `april_2026_crisis_map_join_validation.csv` → `results/launch/.../visualizations/`; include all FR-027 metadata fields; refuse overwrite without `--overwrite` (FR-027, FR-028, FR-029, SC-007, SC-008)
- [X] T033 [US4] Wire `--spatial-path`/`--make-map`/`--no-map`/`--no-basemap`/`--overwrite` and the map step into the CLI `run()` in `scripts/modeling/run_launch_nowcasting_2026_04.py`

**Checkpoint**: Two-panel map produced with explicit coverage and full join validation.

---

## Phase 7: User Story 5 - Human-readable launch report (Priority: P3)

**Goal**: Concise collaborator-facing markdown summarizing the launch.

**Independent Test**: After a run, the report includes every required section incl. production-launch statement, fallback comparability caveat, and partial-coverage warnings.

### Tests for User Story 5 ⚠️

- [X] T034 [P] [US5] Integration assertion in `tests/integration/test_launch_end_to_end.py`: after a Mode-3 run, `launch_summary.md` contains the production-launch statement, the fallback comprehensive-source comparability caveat, training cutoff/counts, predicted phase distribution, and partial-coverage warning when actuals partial (SC-010)

### Implementation for User Story 5

- [X] T035 [US5] Implement the report writer (`write_launch_reports`) in `src/ipcch/launch_nowcasting.py` (or a small `launch_reporting` section): generate `launch_summary.md`, `prediction_distribution_summary.md`, `actual_comparison_summary.md`, `data_coverage_and_warnings.md` under `reports/launch/nowcasting_2026_04/` — launch month + global scale, fallback source path + nowcasting/0m comparability caveat, training cutoff/rows/date coverage, predicted-area count, X_test coverage, feature schema status, predicted phase distribution, phase2–5 worse distributions, April covered-subset comparison + descriptive-only statement, two-panel map interpretation, partial-coverage warnings, production-launch statement (SC-010, FR-001, data-model "Human-readable reports")
- [X] T036 [US5] Wire report generation into the CLI `run()` for all modes in `scripts/modeling/run_launch_nowcasting_2026_04.py`

**Checkpoint**: All five stories independently functional.

---

## Phase 8: Polish & Cross-Cutting Concerns

- [X] T037 [P] Run `quickstart.md` validation end-to-end on the synthetic fixture (Mode 3 + Mode 2 + `--validate-only`); fix any drift between `contracts/cli.md` and the implemented flags
- [X] T038 [P] Add `pip install -e .` import check + `--help` invocation to `tests/smoke/test_launch_cli.py`; ensure no absolute paths and all outputs land under `results/launch/...` and `reports/launch/...` (SC-009, Constitution III/IV)
- [X] T038a [P] Forbidden-source negative-constraint test in `tests/unit/test_launch_nowcasting.py` (or `tests/smoke/`): assert the launch reads **only** the comprehensive source path for both training and X_test; assert it does NOT open the 0m model-ready subset path, the April-only interim X_test path, nor invoke/import the multiscope feature builder in the launch execution path (implement via monkeypatching the file-open/path-resolver or by inspecting resolved config + imported launch modules). Ordinary imports of shared `ipcch` utilities are allowed; the test MUST fail if the launch workflow depends on the forbidden sources/builders (FR-005, FR-037)
- [X] T039 Review-gated canonical-helper reuse: identify the exact canonical **training** and **phase-conversion** helpers used by the current production workflow. If they live in `scripts/modeling/run_deep_feature_weight_decay_forecasting.py`, promote only the **generic, reusable** helpers (e.g., a plain `fit_model`, the top-down phase conversion) into `src/ipcch/forecasting_weight_decay.py` **without importing experiment-specific weight-decay assumptions** (time-decay weighting, fixed `DEFAULT_TEST_YEARS`, annual-holdout sweeps) unless explicitly selected by plan.md. Otherwise keep the launch's mirroring `fit_model` with a comment referencing the canonical source. Document the choice; do not entangle the launch with weight-decay experiment defaults (plan "Structure Decision", R1)
- [X] T040 [P] Update `docs/` (and confirm `CLAUDE.md` SPECKIT pointer) with a short note describing the launch CLI and the three execution modes

---

## Dependencies & Execution Order

### Phase Dependencies
- **Setup (P1: T001–T004)** → no deps.
- **Foundational (P2: T005–T012)** → depends on Setup; **BLOCKS all stories**.
- **US1 (P3)** → depends on Foundational. MVP.
- **US2 (P4)** → depends on Foundational; thin (reuses validation/schema). Independent of US1's training.
- **US3 (P5)** → depends on Foundational + a prediction artifact (from US1 Mode 1/2 or a supplied CSV via Mode 3). Independently testable with a synthetic predictions CSV.
- **US4 (P6)** → depends on Foundational + predictions (+ optional actuals from US3). Independently testable with synthetic predictions + boundaries.
- **US5 (P7)** → depends on the artifacts produced by US1–US4 (degrades gracefully when comparison/map absent).
- **Polish (P8)** → after desired stories complete.

### User Story Dependencies
- US1, US2 are both P1 and independent of each other (share Foundational). US1 is the MVP increment.
- US3 and US4 (P2) consume US1 outputs but are independently testable via supplied/synthetic predictions (Mode 3).
- US5 (P3) assembles whatever artifacts exist.

### Within Each Story
- Tests (marked ⚠️) written to fail first, then implementation.
- In US1: training (T015) → predict/validate (T016) → phase derivation (T017) → Mode-2 load (T018) → write outputs (T019) → CLI wiring (T020).

### Parallel Opportunities
- Setup: T003, T004 in parallel.
- Foundational: T012 (tests) in parallel with doc work once T005–T011 land.
- Cross-story (after Foundational): US1, US2, and the test scaffolds for US3/US4 can proceed in parallel by different developers.
- All `[P]` test tasks (T012, T013, T014, T021, T024, T029, T034) touch distinct test files and can run in parallel.

---

## Parallel Example: User Story 1

```bash
# Tests first (distinct files, parallel):
Task: "Integration test (Mode 2) in tests/integration/test_launch_end_to_end.py"   # T013
Task: "Unit tests for prediction validation in tests/unit/test_launch_nowcasting.py" # T014
# Then implement sequentially within launch_nowcasting.py (same file): T015 → T016 → T017 → T018 → T019, then CLI wiring T020.
```

---

## Implementation Strategy

### MVP First (User Story 1 + US2 preflight)
1. Phase 1 Setup → Phase 2 Foundational.
2. Phase 4 US2 preflight (`--validate-only`) — confirm the comprehensive source is usable **before** approving training.
3. Phase 3 US1 — train (with `--approve-training`) and predict all eligible April areas.
4. **STOP & VALIDATE**: predictions cover 100% of eligible areas; provenance + run summary complete.

### Incremental Delivery
1. Foundational + US2 + US1 → shareable April 2026 predictions (MVP).
2. + US3 → coverage-aware April comparison.
3. + US4 → two-panel crisis map.
4. + US5 → collaborator report.

---

## Notes
- `[P]` = different files, no incomplete-task dependency.
- Heavy Mode-1 training is approval-gated and NEVER executed by tests or automation; tests use synthetic data + Modes 2/3.
- Most launch logic lands in `src/ipcch/launch_nowcasting.py` (sequential within-file); comparison and visualization are separate files (parallelizable across stories).
- Commit after each task or logical group. Stop at any checkpoint to validate a story independently.
