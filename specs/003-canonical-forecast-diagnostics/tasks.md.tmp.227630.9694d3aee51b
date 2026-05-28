# Tasks: Canonical Forecast Diagnostics

**Input**: Design documents from `specs/003-canonical-forecast-diagnostics/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/cli-contract.md, quickstart.md

**Tests**: Smoke tests are explicitly requested. Validation is limited to import checks, CLI `--help`, and tiny synthetic-data smoke tests. Do not run heavy notebooks or model training.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel after dependencies are satisfied because it touches different files or independent sections
- **[Story]**: Maps to a user story from `spec.md`
- Every task includes an exact file path

## Terminology

- **Prediction CSV**: The source forecast file for one annual held-out evaluation run, containing true labels, predicted cumulative output columns, and the canonical predicted phase.
- **Predicted cumulative output columns**: The cumulative-regression prediction columns for phase 2 through phase 5, preferably `phase2_pred`, `phase3_pred`, `phase4_pred`, and `phase5_pred`, or user-configured aliases.
- **Canonical predicted phase**: The `overall_phase_pred` field already produced by the canonical forecasting workflow.
- **Canonical regressor diagnostics**: Diagnostics for the existing cumulative-regression workflow, separate from classifier or correction-model outputs.

## Constitution Guardrails

- Experiment 0 v1 accepts one annual prediction CSV per run; batch or multi-file aggregation is out of scope.
- Do not fit, refit, tune, calibrate, select thresholds, alter label mappings, alter the canonical temporal split, or use test-window data to influence fitted parameters or reported canonical metrics.
- Do not modify canonical `convert_prob_to_phase(th=0.2)` behavior or source prediction CSVs.
- Keep reusable code in `src/ipcch/`.
- Use `ipcch.paths` and CLI path flags; do not hardcode absolute paths.
- Write machine-readable outputs under `results/diagnostics/experiment_0/canonical_regressor/`.
- Write human-readable outputs under `reports/diagnostics/experiment_0/canonical_regressor/`.
- Do not execute heavy notebook cells or model training.
- Treat changes under `src/ipcch/` as review-gated before merge.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish the module, bounded schema inspection notes, smoke-test location, and documentation entry point.

- [X] T001 Inspect headers only from user-specified prediction CSV paths, provided sample files, or small available fixture files using header-only loading such as `pandas.read_csv(..., nrows=0)`, record discovered true labels, canonical predicted phase, and predicted cumulative output column aliases in `specs/003-canonical-forecast-diagnostics/research.md`, and do not recursively scan `results/predictions/` or copy large prediction CSVs into the repository
- [X] T002 Create `src/ipcch/forecast_diagnostics.py` with module docstring, canonical constants, public function stubs, and `main()` placeholder
- [X] T003 [P] Create `tests/smoke/test_forecast_diagnostics_smoke.py` with a tiny synthetic dataframe fixture covering phases 1–4, invalid labels, cumulative targets, optional metrics-file rows, and phase 2→3 / phase 3→2 slices
- [X] T004 [P] Create `docs/experiment_0_canonical_forecast_diagnostics.md` with the Experiment 0 purpose, safety constraints, terminology, one-CSV-per-run scope, and planned CLI command

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Implement shared schema, validation, optional metrics-file comparison, and output plumbing required by all diagnostic stories.

**Critical**: No user story work should begin until this phase is complete.

- [X] T005 Implement column alias configuration and CLI override data structures for true labels, canonical predicted phase, and predicted cumulative output columns in `src/ipcch/forecast_diagnostics.py`
- [X] T006 Implement path resolution helpers using `ipcch.paths` for default output and report directories in `src/ipcch/forecast_diagnostics.py`
- [X] T007 Implement safe numeric coercion and valid phase-label helper functions for labels 1–5 in `src/ipcch/forecast_diagnostics.py`
- [X] T008 Implement `validate_prediction_schema()` with required label-column checks, optional cumulative-column coverage, invalid/missing label findings, and metrics-file availability findings in `src/ipcch/forecast_diagnostics.py`
- [X] T009 Implement optional metrics-file comparison helpers with recognized comparable fields, documented tolerance, `matched`/`mismatch`/`not_available`/`not_comparable` statuses, supplied value, recomputed value, and absolute-difference fields in `src/ipcch/forecast_diagnostics.py`
- [X] T010 Implement output writer helpers for CSV, JSON, and Markdown summary artifacts under `canonical_regressor/` subdirectories in `src/ipcch/forecast_diagnostics.py`
- [X] T011 Add smoke assertions for schema validation, invalid-label reporting, optional metrics-file unavailable status, and no mutation of the source dataframe in `tests/smoke/test_forecast_diagnostics_smoke.py`

**Checkpoint**: Schema validation, optional metrics-file comparison helpers, and artifact writing are available for user-story diagnostics.

---

## Phase 3: User Story 1 - Validate canonical annual prediction outputs (Priority: P1) MVP

**Goal**: Run a diagnostic baseline on an already-generated annual prediction CSV and produce validation, class distribution, confusion matrix, and per-class metric summaries without changing inputs.

**Independent Test**: Run the smoke test on a tiny synthetic prediction dataframe and confirm validation artifacts, class distributions, confusion matrices, and per-class metrics are produced while invalid labels are reported.

### Implementation for User Story 1

- [X] T012 [US1] Implement `compute_class_distribution()` with true/predicted label counts, percentages, validation status, and year fields in `src/ipcch/forecast_diagnostics.py`
- [X] T013 [US1] Implement `compute_confusion_matrices()` producing raw counts and row-normalized percentages for valid labels 1–5 in `src/ipcch/forecast_diagnostics.py`
- [X] T014 [US1] Implement `compute_multiclass_metrics()` with per-class precision, recall, F1, support, accuracy, macro-F1, weighted-F1, and ordinal MAE in `src/ipcch/forecast_diagnostics.py`
- [X] T015 [US1] Implement optional invalid-label filtering behavior that requires an explicit CLI/config flag in `src/ipcch/forecast_diagnostics.py`
- [X] T016 [US1] Wire validation, class distribution, confusion matrices, and multiclass metrics into the core diagnostic run orchestration in `src/ipcch/forecast_diagnostics.py`
- [X] T017 [US1] Write US1 machine-readable outputs `validation_findings.csv`, `validation_summary.json`, `class_distribution.csv`, `confusion_matrix_counts.csv`, `confusion_matrix_row_normalized.csv`, and `multiclass_metrics.csv` from `src/ipcch/forecast_diagnostics.py`
- [X] T018 [US1] Write US1 smoke tests for class distributions, invalid-label inclusion, confusion matrix counts, row-normalized percentages, and ordinal MAE in `tests/smoke/test_forecast_diagnostics_smoke.py`
- [X] T019 [US1] Update `docs/experiment_0_canonical_forecast_diagnostics.md` with US1 output artifact descriptions and invalid-label behavior

**Checkpoint**: User Story 1 is independently functional and delivers the interim MVP diagnostic baseline.

---

## Phase 4: User Story 2 - Diagnose crisis-detection and cumulative-regression behavior (Priority: P2)

**Goal**: Add crisis-binary metrics and cumulative-regression diagnostics for available held-out prediction rows.

**Independent Test**: Run the smoke test with cumulative true/predicted columns and confirm 3+ / 4+ crisis metrics, cumulative RMSE/MAE/bias/correlation, calibration bins, and canonical 0.2 crossing rates are produced or skipped with explicit findings.

### Implementation for User Story 2

- [X] T020 [US2] Implement `compute_binary_crisis_metrics()` for 3+ versus 1–2 and 4+ versus 1–3 precision, recall, F1, F2, positive support, negative support, and total support in `src/ipcch/forecast_diagnostics.py`
- [X] T021 [US2] Implement cumulative true/predicted column pair resolution for phase2_worse through phase5_worse and predicted cumulative output columns with aliases and explicit overrides in `src/ipcch/forecast_diagnostics.py`
- [X] T022 [US2] Implement `compute_cumulative_regression_metrics()` with RMSE, MAE, bias, correlation, valid row counts, and correlation status in `src/ipcch/forecast_diagnostics.py`
- [X] T023 [US2] Implement `compute_calibration_bins()` for each available cumulative target with bin bounds, row counts, mean predicted, mean true, and bias in `src/ipcch/forecast_diagnostics.py`
- [X] T024 [US2] Implement `compute_threshold_crossing_rates()` at canonical threshold 0.2 without changing the source prediction CSV or canonical predicted phase in `src/ipcch/forecast_diagnostics.py`
- [X] T025 [US2] Wire binary crisis, cumulative-regression, calibration-bin, and threshold-crossing diagnostics into the core diagnostic run orchestration in `src/ipcch/forecast_diagnostics.py`
- [X] T026 [US2] Write US2 machine-readable outputs `binary_crisis_metrics.csv`, `cumulative_regression_metrics.csv`, `calibration_bins.csv`, and `threshold_crossing_rates.csv` from `src/ipcch/forecast_diagnostics.py`
- [X] T027 [US2] Add smoke assertions for 3+ and 4+ crisis metrics, cumulative metric values, sparse/constant correlation status, calibration-bin coverage, and canonical 0.2 threshold crossing rates in `tests/smoke/test_forecast_diagnostics_smoke.py`
- [X] T028 [US2] Update `docs/experiment_0_canonical_forecast_diagnostics.md` with US2 crisis and cumulative diagnostic artifact descriptions

**Checkpoint**: User Stories 1 and 2 both work independently on the smoke dataframe.

---

## Phase 5: User Story 3 - Compare post-hoc threshold behavior without changing canonical performance (Priority: P3)

**Goal**: Add shared-threshold diagnostic sweeps and targeted error-slice summaries while preserving canonical 0.2 performance as the reference baseline.

**Independent Test**: Run the smoke test with cumulative predictions and boundary errors, then confirm threshold-sweep rows contain `diagnostic_only=true`, no recommended threshold is emitted, and requested error slices are summarized or explicitly empty.

### Implementation for User Story 3

- [X] T029 [US3] Implement a local diagnostic phase reconstruction helper for shared-threshold sweep results without modifying `convert_prob_to_phase()` in `src/ipcch/forecast_diagnostics.py`
- [X] T030 [US3] Implement `run_diagnostic_threshold_sweep()` using one shared threshold across phase2, phase3, phase4, and phase5 predicted cumulative output columns with `diagnostic_only=true` in `src/ipcch/forecast_diagnostics.py`
- [X] T031 [US3] Add threshold-sweep metrics for resulting class distribution, accuracy, macro-F1, phase3+ precision/recall/F1/F2, and phase4+ precision/recall/F1/F2 in `src/ipcch/forecast_diagnostics.py`
- [X] T032 [US3] Implement `summarize_error_slices()` for true2_pred3, true3_pred2, true4_pred3, and true3_pred4 with cumulative means and margins to 0.2 in `src/ipcch/forecast_diagnostics.py`
- [X] T033 [US3] Add optional error-slice grouping by available `country`, `region`, and `area_id` fields while recording unavailable grouping fields in `src/ipcch/forecast_diagnostics.py`
- [X] T034 [US3] Wire threshold sweep and error-slice diagnostics into the core diagnostic run orchestration in `src/ipcch/forecast_diagnostics.py`
- [X] T035 [US3] Write US3 machine-readable outputs `diagnostic_threshold_sweep.csv` and `error_slices.csv` from `src/ipcch/forecast_diagnostics.py`
- [X] T036 [US3] Add smoke assertions that threshold-sweep outputs contain `diagnostic_only=true`, do not include a recommended threshold, and error-slice outputs include all requested slice names in `tests/smoke/test_forecast_diagnostics_smoke.py`
- [X] T037 [US3] Update `docs/experiment_0_canonical_forecast_diagnostics.md` with post-hoc threshold-sweep warnings and error-slice output descriptions

**Checkpoint**: All diagnostic families from the spec are implemented and independently smoke-testable.

---

## Phase 6: CLI, Reports, and Integration

**Purpose**: Expose the workflow through the contract CLI and generate the final separated report/run-summary artifacts.

- [X] T038 Implement argparse CLI options from `specs/003-canonical-forecast-diagnostics/contracts/cli-contract.md` in `src/ipcch/forecast_diagnostics.py`
- [X] T039 Implement single prediction CSV loading, optional metrics CSV loading, year filtering/inference, and read-only source provenance handling in `src/ipcch/forecast_diagnostics.py`
- [X] T040 Integrate optional metrics-file comparison after recomputed annual diagnostics are available and write comparison rows to `validation_findings.csv`, `metrics_comparison.csv`, and `run_summary.json` without altering computed diagnostics in `src/ipcch/forecast_diagnostics.py`
- [X] T041 Implement `run_summary.json` with inputs, row counts, years processed, generated/skipped diagnostic families, validation warnings, metrics-file comparison status, output directory, and report directory in `src/ipcch/forecast_diagnostics.py`
- [X] T042 Implement human-readable `summary.md` generation under `reports/diagnostics/experiment_0/canonical_regressor/` in `src/ipcch/forecast_diagnostics.py`
- [X] T043 Ensure default machine-readable outputs are written under `results/diagnostics/experiment_0/canonical_regressor/` and report outputs under `reports/diagnostics/experiment_0/canonical_regressor/` in `src/ipcch/forecast_diagnostics.py`
- [X] T044 Add a smoke test that writes a tiny synthetic prediction CSV and optional comparable metrics CSV to a temporary directory, runs `main()`, and verifies all expected artifact filenames plus metrics comparison statuses in `tests/smoke/test_forecast_diagnostics_smoke.py`
- [X] T045 Add a smoke test for the unavailable optional metrics-file case that verifies `not_available` status without failing the run in `tests/smoke/test_forecast_diagnostics_smoke.py`
- [X] T046 Update `specs/003-canonical-forecast-diagnostics/quickstart.md` if CLI flags or artifact filenames differ from the planned contract

---

## Phase 7: Polish & Cross-Cutting Validation

**Purpose**: Validate only lightweight checks, document usage, and preserve safety constraints.

- [X] T047 Run import check `PYTHONPATH=src python -c "import ipcch.forecast_diagnostics"` from repository root
- [X] T048 Run CLI help check `PYTHONPATH=src python -m ipcch.forecast_diagnostics --help` from repository root
- [X] T049 Run the tiny smoke test file `PYTHONPATH=src python -m pytest tests/smoke/test_forecast_diagnostics_smoke.py` from repository root
- [X] T050 Verify `diagnostic_threshold_sweep.csv` rows include `diagnostic_only=true` and no generated artifact recommends a tuned threshold in `tests/smoke/test_forecast_diagnostics_smoke.py`
- [X] T051 Verify no task or code path executes notebooks, trains models, writes configs, overwrites prediction CSVs, changes class mappings, alters the canonical temporal split, or changes canonical threshold behavior in `src/ipcch/forecast_diagnostics.py`
- [X] T052 Finalize `docs/experiment_0_canonical_forecast_diagnostics.md` with the completed CLI command, artifact list, safety constraints, one-CSV-per-run scope, metrics-file comparison statuses, and smoke-test validation steps
- [X] T053 Review generated git diff for large prediction CSVs or misplaced artifacts under `results/predictions/` before requesting review

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 Setup**: No dependencies; can start immediately.
- **Phase 2 Foundational**: Depends on Phase 1; blocks all user-story work.
- **Phase 3 US1**: Depends on Phase 2; interim MVP scope.
- **Phase 4 US2**: Depends on Phase 2; can start after foundation, but should integrate cleanly with US1 orchestration.
- **Phase 5 US3**: Depends on Phase 2 and cumulative column resolution from US2 task T021 for threshold/error diagnostics.
- **Phase 6 CLI/Reports**: Depends on all required diagnostic families from US1, US2, and US3, not only a subset of desired families.
- **Phase 7 Polish/Validation**: Depends on CLI/report integration and the complete diagnostic artifact set.

### User Story Dependencies

- **US1 (P1)**: Starts after foundation and has no dependency on US2 or US3.
- **US2 (P2)**: Starts after foundation; uses the same validated label rows as US1 but remains independently testable.
- **US3 (P3)**: Starts after foundation and cumulative prediction column resolution; depends on US2 T021 for shared column mapping.

### MVP Scope and Completion Boundary

Complete Phases 1–3 to deliver the interim MVP: validation, invalid-label reporting, annual class distribution, confusion matrices, and per-class metrics. US1 may be delivered first as an interim MVP, but Experiment 0 is not complete until all required diagnostic families and artifacts are produced in a single CLI run for a valid annual prediction CSV.

---

## Parallel Opportunities

- T003 and T004 can run in parallel after T001–T002 are understood.
- Documentation tasks T019, T028, T037, and T052 can be done in parallel with code review after each story stabilizes.
- After Phase 2, US1 classification metrics (T012–T014) can be implemented before orchestration T016.
- After T021, US2 cumulative metrics (T022), calibration bins (T023), and threshold crossing rates (T024) can be implemented in parallel.
- US3 threshold sweep tasks T029–T031 and error-slice tasks T032–T033 can proceed in parallel after T021.

## Parallel Example: User Story 2

```text
Task: "Implement compute_cumulative_regression_metrics() with RMSE, MAE, bias, correlation, valid row counts, and correlation status in src/ipcch/forecast_diagnostics.py"
Task: "Implement compute_calibration_bins() for each available cumulative target with bin bounds, row counts, mean predicted, mean true, and bias in src/ipcch/forecast_diagnostics.py"
Task: "Implement compute_threshold_crossing_rates() at canonical threshold 0.2 without changing the source prediction CSV or canonical predicted phase in src/ipcch/forecast_diagnostics.py"
```

## Parallel Example: User Story 3

```text
Task: "Implement run_diagnostic_threshold_sweep() using one shared threshold across phase2, phase3, phase4, and phase5 predicted cumulative output columns with diagnostic_only=true in src/ipcch/forecast_diagnostics.py"
Task: "Implement summarize_error_slices() for true2_pred3, true3_pred2, true4_pred3, and true3_pred4 with cumulative means and margins to 0.2 in src/ipcch/forecast_diagnostics.py"
```

---

## Implementation Strategy

### MVP First

1. Complete Phase 1 setup.
2. Complete Phase 2 foundational schema/output helpers.
3. Complete Phase 3 User Story 1.
4. Stop and validate the interim MVP with the tiny smoke test only.

### Incremental Delivery

1. Add US1 validation/classification diagnostics and smoke-test them.
2. Add US2 crisis/cumulative diagnostics and smoke-test them.
3. Add US3 threshold/error-slice diagnostics and smoke-test them.
4. Add CLI/report integration, including metrics-file comparison.
5. Run import, help, and tiny smoke validation only.
6. Final validation requires the complete diagnostic artifact set in one CLI run for a valid annual prediction CSV.

### Review Guidance

- Review `src/ipcch/forecast_diagnostics.py` before merge because `src/ipcch/` changes are review-gated.
- Do not include large prediction CSVs or generated `results/predictions/` artifacts in commits.
- Treat threshold sweep outputs as diagnostic evidence only, not canonical performance changes.
