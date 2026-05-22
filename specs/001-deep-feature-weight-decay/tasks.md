# Tasks: Deep Feature Weighted Decay Forecasting

**Input**: Design documents from `/specs/001-deep-feature-weight-decay/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: No standalone test suite was explicitly requested. Validation tasks use the required CLI `--help`, dry-run, and small/synthetic smoke checks from quickstart.md and the feature spec.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4, US5)
- Each task includes exact file paths

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish feature files, path keys, and command skeleton without changing the original notebook.

- [X] T001 Add external path keys `deep_features_forecasting_dataset` and `ipcch_2026_completed_dataset` to `configs/paths.example.json`
- [X] T002 Add default external path entries for the corrected forecasting dataset and Somalia lookup in `src/ipcch/paths.py`
- [X] T003 Add generated prediction ignore rule for `results/experiments/deep_feature_weight_decay_forecasting/predictions/` in `.gitignore`
- [X] T004 Create reusable helper module skeleton with constants for test years, target columns, metric names, and default half-life in `src/ipcch/forecasting_weight_decay.py`
- [X] T005 Create CLI entry point skeleton with argparse options from the CLI contract in `scripts/modeling/run_deep_feature_weight_decay_forecasting.py`
- [X] T006 Add imports through `ipcch` package paths in `scripts/modeling/run_deep_feature_weight_decay_forecasting.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Implement shared data, split, feature, weight, output, and metric primitives required before any user story can be completed.

**CRITICAL**: No user story work can be complete until this phase is complete.

- [X] T007 Implement dataset path resolution using explicit path arguments or `ipcch.paths.external_path()` keys in `src/ipcch/forecasting_weight_decay.py`
- [X] T008 Implement required-column validation for ForecastingReadyDataset fields in `src/ipcch/forecasting_weight_decay.py`
- [X] T009 Implement monthly `date` creation from `year` and `month` with invalid-date errors in `src/ipcch/forecasting_weight_decay.py`
- [X] T010 Implement cumulative target derivation for `phase2_worse`, `phase3_worse`, `phase4_worse`, and `phase5_worse` in `src/ipcch/forecasting_weight_decay.py`
- [X] T011 Implement numeric feature selection excluding identifiers, dates, target fields, observed labels, prediction fields, and leakage fields in `src/ipcch/forecasting_weight_decay.py`
- [X] T012 Validate the script only selects existing numeric feature columns and does not create upstream/deep-feature predictors beyond date and cumulative target derivation in `src/ipcch/forecasting_weight_decay.py`
- [X] T013 Implement all-prior-history annual split generation for 2022, 2023, 2024, and 2025 in `src/ipcch/forecasting_weight_decay.py`
- [X] T014 Implement split diagnostics including train/test row counts and max training date checks in `src/ipcch/forecasting_weight_decay.py`
- [X] T015 Implement exponential half-life sample-weight calculation and validation in `src/ipcch/forecasting_weight_decay.py`
- [X] T016 Implement unavailable-aware metric result helpers for accuracy, phase3+ precision, phase3+ sensitivity, phase3+ R2, and phase3+ F2 in `src/ipcch/forecasting_weight_decay.py`
- [X] T017 Implement output directory planning and overwrite checks for results and reports paths in `src/ipcch/forecasting_weight_decay.py`
- [X] T018 Wire shared helper calls into the CLI control flow without fitting models in `scripts/modeling/run_deep_feature_weight_decay_forecasting.py`

**Checkpoint**: Foundation ready - user story implementation can now begin.

---

## Phase 3: User Story 1 - Evaluate the corrected deep-feature dataset (Priority: P1) MVP

**Goal**: Provide a dry-run-capable workflow that loads the corrected dataset, derives dates/targets/features, and prepares exactly four leakage-safe annual holdout splits without modifying the original notebook.

**Independent Test**: Run the CLI in dry-run mode and verify it resolves the configured dataset, reports required columns/features, prepares 2022-2025 splits, confirms all training rows are before each test year, and leaves `notebooks/modeling/Table1_Forecasting_main.ipynb` unchanged.

### Implementation for User Story 1

- [X] T019 [US1] Implement dataset loading and optional `--sample-rows` handling in `scripts/modeling/run_deep_feature_weight_decay_forecasting.py`
- [X] T020 [US1] Implement dry-run split diagnostics output for exactly 2022, 2023, 2024, and 2025 in `scripts/modeling/run_deep_feature_weight_decay_forecasting.py`
- [X] T021 [US1] Reject non-required `--test-years` values outside the four-year feature contract during normal runs in `scripts/modeling/run_deep_feature_weight_decay_forecasting.py`
- [X] T022 [US1] Write planned split diagnostics to `results/experiments/deep_feature_weight_decay_forecasting/metadata/split_diagnostics.csv` in dry-run and full-run modes from `scripts/modeling/run_deep_feature_weight_decay_forecasting.py`
- [X] T023 [US1] Add dry-run console summary covering dataset source, feature count, target columns, split row counts, and output plan in `scripts/modeling/run_deep_feature_weight_decay_forecasting.py`
- [X] T024 [US1] Validate US1 with the dry-run command documented in `specs/001-deep-feature-weight-decay/quickstart.md`

**Checkpoint**: User Story 1 is independently testable as the MVP.

---

## Phase 4: User Story 2 - Weight training records by temporal recency (Priority: P2)

**Goal**: Compute and apply valid exponential time-decay sample weights with a default 24-month half-life for every annual cumulative-phase model fit.

**Independent Test**: Use dry-run diagnostics or a small sampled run to verify newer training rows receive larger weights, invalid half-life values fail clearly, and every cumulative-phase model fit receives aligned sample weights.

### Implementation for User Story 2

- [X] T025 [US2] Add half-life diagnostics including min, max, and monotonicity checks per holdout year in `scripts/modeling/run_deep_feature_weight_decay_forecasting.py`
- [X] T026 [US2] Implement hyperparameter loading for forecasting and phase-3-specific configurations in `scripts/modeling/run_deep_feature_weight_decay_forecasting.py`
- [X] T027 [US2] Implement target-specific train/test matrix preparation with weight alignment after target-missing-row drops in `src/ipcch/forecasting_weight_decay.py`
- [X] T028 [US2] Implement weighted XGBoost fitting for phases 2, 3, 4, and 5 with `sample_weight` in `scripts/modeling/run_deep_feature_weight_decay_forecasting.py`
- [X] T029 [US2] Implement annual prediction assembly with continuous phase prediction columns in `scripts/modeling/run_deep_feature_weight_decay_forecasting.py`
- [X] T030 [US2] Apply existing discrete phase conversion convention to annual prediction outputs in `scripts/modeling/run_deep_feature_weight_decay_forecasting.py`
- [X] T031 [US2] Record decay formulation and half-life used for each holdout in `results/experiments/deep_feature_weight_decay_forecasting/metadata/run_metadata.json` from `scripts/modeling/run_deep_feature_weight_decay_forecasting.py`
- [X] T032 [US2] Validate US2 with a sampled smoke invocation using `--dry-run --sample-rows` as documented in `specs/001-deep-feature-weight-decay/quickstart.md`

**Checkpoint**: All four cumulative-phase models can be fit with aligned time-decay weights when full training is requested.

---

## Phase 5: User Story 3 - Compare annual model quality with F2 included (Priority: P3)

**Goal**: Save per-year predictions and annual metric outputs including F2 plus existing metric set, with unavailable metric reasons instead of misleading zeros.

**Independent Test**: Run metric helpers on known observed/predicted phase values and verify F2 uses beta 2 for phase 3+, undefined denominators are unavailable with reasons, and completed holdout outputs contain every required metric field.

### Implementation for User Story 3

- [X] T033 [US3] Implement F2 computation for discrete phase 3+ observed and predicted labels in `src/ipcch/forecasting_weight_decay.py`
- [X] T034 [US3] Implement unavailable reason handling for zero-denominator precision, sensitivity, F2, and invalid R2 cases in `src/ipcch/forecasting_weight_decay.py`
- [X] T035 [US3] Implement per-year metrics JSON writing for `metrics_2022.json`, `metrics_2023.json`, `metrics_2024.json`, and `metrics_2025.json` in `scripts/modeling/run_deep_feature_weight_decay_forecasting.py`
- [X] T036 [US3] Implement consolidated overall metrics CSV writing to `results/experiments/deep_feature_weight_decay_forecasting/metrics/metrics_overall.csv` in `scripts/modeling/run_deep_feature_weight_decay_forecasting.py`
- [X] T037 [US3] Implement annual prediction CSV writing to `results/experiments/deep_feature_weight_decay_forecasting/predictions/` with the output contract columns in `scripts/modeling/run_deep_feature_weight_decay_forecasting.py`
- [X] T038 [US3] Validate US3 metric behavior with a small known in-memory metric example through helper functions in `src/ipcch/forecasting_weight_decay.py`

**Checkpoint**: Overall annual prediction and metric outputs match the CLI and output schema contracts.

---

## Phase 6: User Story 4 - Produce Somalia-only performance metrics (Priority: P4)

**Goal**: Derive Somalia area IDs from the configured completed IPCCH source and produce Somalia-only metrics for each annual holdout after prediction generation.

**Independent Test**: Load the Somalia lookup source, derive Somalia area IDs using ISO3-first matching, filter prediction outputs by those IDs, and verify each year has the same metric fields or an explicit no-eligible-samples status.

### Implementation for User Story 4

- [X] T039 [US4] Implement Somalia lookup source path resolution from `--somalia-lookup` or `--somalia-lookup-key` in `src/ipcch/forecasting_weight_decay.py`
- [X] T040 [US4] Implement ISO3-first Somalia `area_id` extraction with normalized country-name fallback in `src/ipcch/forecasting_weight_decay.py`
- [X] T041 [US4] Implement Somalia filtering of annual prediction dataframes after all holdout predictions are produced in `scripts/modeling/run_deep_feature_weight_decay_forecasting.py`
- [X] T042 [US4] Implement no-eligible-Somalia-samples status rows for missing year-specific Somalia test rows in `src/ipcch/forecasting_weight_decay.py`
- [X] T043 [US4] Write Somalia metrics to `results/experiments/deep_feature_weight_decay_forecasting/metrics/metrics_somalia.csv` in `scripts/modeling/run_deep_feature_weight_decay_forecasting.py`
- [X] T044 [US4] Record Somalia lookup source identity and Somalia area-id count in `results/experiments/deep_feature_weight_decay_forecasting/metadata/run_metadata.json` from `scripts/modeling/run_deep_feature_weight_decay_forecasting.py`
- [X] T045 [US4] Validate US4 with dry-run Somalia lookup diagnostics documented in `specs/001-deep-feature-weight-decay/quickstart.md`

**Checkpoint**: Somalia-only metrics are produced after annual holdout predictions, with clear no-sample statuses.

---

## Phase 7: User Story 5 - Preserve project discipline and auditability (Priority: P5)

**Goal**: Finalize reports, metadata, validation commands, and repository discipline checks so the workflow is reproducible and reviewable.

**Independent Test**: Inspect changed files and generated locations to confirm the original notebook is unchanged, no raw source CSVs are copied, path inputs are configurable, machine-readable artifacts go under results, and human-readable summaries go under reports.

### Implementation for User Story 5

- [X] T046 [US5] Implement human-readable summary report generation in `reports/deep_feature_weight_decay_forecasting/summary.md` from `scripts/modeling/run_deep_feature_weight_decay_forecasting.py`
- [X] T047 [US5] Copy consolidated overall and Somalia metric tables to `reports/deep_feature_weight_decay_forecasting/` from `scripts/modeling/run_deep_feature_weight_decay_forecasting.py`
- [X] T048 [US5] Ensure run metadata includes dataset source, Somalia lookup source, split rule, test years, target columns, feature count, feature column sample or hash, output locations, dry-run flag, and `notebook_modified: false` in `scripts/modeling/run_deep_feature_weight_decay_forecasting.py`
- [X] T049 [US5] Add clear CLI failure messages for missing paths, missing required columns, invalid dates, invalid weights, existing outputs without `--overwrite`, and missing hyperparameter configs in `scripts/modeling/run_deep_feature_weight_decay_forecasting.py`
- [X] T050 [US5] Run CLI help validation command from `specs/001-deep-feature-weight-decay/quickstart.md`
- [X] T051 [US5] Run dry-run validation command from `specs/001-deep-feature-weight-decay/quickstart.md`
- [X] T052 [US5] Inspect `git status --short` to confirm `notebooks/modeling/Table1_Forecasting_main.ipynb` remains unchanged, no raw external CSVs are added to the repository, and generated prediction CSVs under `results/experiments/deep_feature_weight_decay_forecasting/predictions/` are not staged or tracked

**Checkpoint**: Feature is audit-ready and validation outputs follow repository conventions.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Final cleanup that spans user stories without changing feature scope.

- [X] T053 [P] Update `specs/001-deep-feature-weight-decay/quickstart.md` if implementation command names or output paths changed during implementation
- [X] T054 [P] Review `specs/001-deep-feature-weight-decay/contracts/cli-contract.md` against final CLI options in `scripts/modeling/run_deep_feature_weight_decay_forecasting.py`
- [X] T055 [P] Review `specs/001-deep-feature-weight-decay/contracts/output-schemas.md` against final outputs under `results/experiments/deep_feature_weight_decay_forecasting/`
- [X] T056 Refactor duplicated orchestration logic from `scripts/modeling/run_deep_feature_weight_decay_forecasting.py` into `src/ipcch/forecasting_weight_decay.py` only where reuse or testability requires it
- [X] T057 Run final validation commands from `specs/001-deep-feature-weight-decay/quickstart.md` without full model training

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies; starts immediately.
- **Foundational (Phase 2)**: Depends on Setup completion; blocks all user stories.
- **User Story 1 (Phase 3)**: Depends on Foundational; delivers MVP dry-run split workflow.
- **User Story 2 (Phase 4)**: Depends on Foundational; can start after helpers exist, but full validation benefits from US1 dry-run plumbing.
- **User Story 3 (Phase 5)**: Depends on US2 prediction generation for full integration; metric helpers can be developed independently after Foundational.
- **User Story 4 (Phase 6)**: Depends on US3 annual prediction outputs for full integration; Somalia lookup helpers can be developed independently after Foundational.
- **User Story 5 (Phase 7)**: Depends on desired preceding stories; final audit checks should run after US1-US4.
- **Polish (Phase 8)**: Depends on all desired user stories being complete.

### User Story Dependencies

- **US1 (P1)**: No dependencies on other user stories after Foundational; MVP.
- **US2 (P2)**: Needs Foundational weight and split helpers; model fitting integrates with US1 CLI flow.
- **US3 (P3)**: Metrics helpers are independent, but full per-year outputs depend on US2 predictions.
- **US4 (P4)**: Lookup helpers are independent, but Somalia metrics depend on US3 prediction and metric outputs.
- **US5 (P5)**: Cross-cutting audit and reporting depends on whichever user stories are included in the delivery increment.

### Within Each User Story

- Build reusable helpers before CLI wiring when both are needed.
- Preserve dry-run validation before adding full heavy training paths.
- Write outputs only after validating path and overwrite rules.
- Validate each story at its checkpoint before moving to the next priority.

---

## Parallel Opportunities

- T001 and T002 can be reviewed independently from T004 and T005 if path keys are known.
- T008 through T011 can be implemented in parallel with T017 because they touch distinct helper concerns.
- T016 metric helper work can proceed in parallel with T013 split helper work after constants exist.
- US3 metric helpers T033-T034 can be implemented while US2 model-fitting integration T026-T030 is underway.
- US4 lookup helpers T039-T040 can be implemented while US3 output writing T035-T037 is underway.
- Polish review tasks T053-T055 can run in parallel after implementation stabilizes.

## Parallel Example: User Story 1

```text
Task: "Implement dry-run split diagnostics output for exactly 2022, 2023, 2024, and 2025 in scripts/modeling/run_deep_feature_weight_decay_forecasting.py"
Task: "Reject non-required --test-years values outside the four-year feature contract during normal runs in scripts/modeling/run_deep_feature_weight_decay_forecasting.py"
```

## Parallel Example: User Story 3

```text
Task: "Implement F2 computation for discrete phase 3+ observed and predicted labels in src/ipcch/forecasting_weight_decay.py"
Task: "Implement unavailable reason handling for zero-denominator precision, sensitivity, F2, and invalid R2 cases in src/ipcch/forecasting_weight_decay.py"
```

## Parallel Example: User Story 4

```text
Task: "Implement Somalia lookup source path resolution from --somalia-lookup or --somalia-lookup-key in src/ipcch/forecasting_weight_decay.py"
Task: "Implement ISO3-first Somalia area_id extraction with normalized country-name fallback in src/ipcch/forecasting_weight_decay.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 setup tasks T001-T006.
2. Complete Phase 2 foundational tasks T007-T018.
3. Complete Phase 3 US1 tasks T019-T024.
4. Stop and validate dry-run behavior before adding full model fitting.

### Incremental Delivery

1. Setup + Foundational: path resolution, dataset validation, dates, targets, splits, weights, metrics primitives.
2. US1: corrected data source and four annual split dry-run MVP.
3. US2: weighted training and prediction generation.
4. US3: overall metrics including F2 and unavailable statuses.
5. US4: Somalia-only metrics after annual predictions.
6. US5: reports, metadata, failure messages, and repository discipline checks.

### Validation Discipline

- Do not run heavy notebook cells.
- Do not run full 2022-2025 training unless explicitly requested.
- Prefer `--help`, `--dry-run`, sampled dry-run, and helper-level smoke checks during automation.
- Confirm original notebook preservation and no raw source data additions before declaring implementation complete.
