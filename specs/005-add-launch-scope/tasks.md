# Tasks: Launch Forecast Scope

**Input**: Design documents from `/specs/005-add-launch-scope/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/launch-scope-cli.md, quickstart.md

**Tests**: Tests are included because the specification requires testable leakage prevention, CLI behavior, output compatibility, and visualization/reporting behavior. Write or update tests before implementation where practical, and use synthetic data rather than heavy model training.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing. Parallel labels are limited to tasks that target different files or low-conflict areas; scope-specific alignment, static-feature, and output tests use separate test files to reduce merge conflicts.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Every task includes exact file paths

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm current launch surface, validation entry points, and shared scope vocabulary before feature work.

- [X] T001 Inspect current CLI parser, confirm whether `--validate-only` already exists, and if not either add it as part of this feature or replace validate-only smoke tests with the project’s existing lightweight validation entry point in `scripts/modeling/run_launch_nowcasting_2026_04.py`
- [X] T002 Inspect current launch config fields, feature schema selection, and existing validation paths in `src/ipcch/launch_nowcasting.py`
- [X] T003 [P] Inspect existing launch visualization and comparison control flow in `src/ipcch/launch_visualizations.py`, `src/ipcch/launch_comparison.py`, and `scripts/modeling/run_launch_nowcasting_2026_04.py`
- [X] T004 [P] Inspect existing launch tests to identify extension points in `tests/unit/test_launch_nowcasting.py`, `tests/smoke/test_launch_cli.py`, `tests/unit/test_launch_visualizations.py`, and `tests/unit/test_launch_comparison.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Add shared scope, period, validation, and static/time-varying feature primitives that all user stories depend on.

**CRITICAL**: No user story work can begin until this phase is complete.

- [X] T005 Add `scope_months` to `LaunchConfig` with default `0` and validation for allowed values `0`, `3`, and `6` in `src/ipcch/launch_nowcasting.py`
- [X] T006 Add `--scope {0,3,6}` CLI parsing and pass it through `build_config()` in `scripts/modeling/run_launch_nowcasting_2026_04.py`
- [X] T007 Add unit tests for `LaunchConfig` scope defaults, explicit scope values, and invalid scope rejection in `tests/unit/test_launch_nowcasting.py`
- [X] T008 Add smoke tests that `--help` lists `--scope` and invalid `--scope` values fail fast via the CLI parser or confirmed lightweight validation entry point before starting the requested long-running workflow step, such as model training, prediction generation, reporting, or visualization, in `tests/smoke/test_launch_cli.py`
- [X] T009 Implement monthly period helper functions for deriving feature period, target period, and ±3/±6 calendar month offsets from `year`/`month` or date fields in `src/ipcch/launch_nowcasting.py`
- [X] T010 [P] Add unit tests for monthly period helper behavior covering adding 3 months, adding 6 months, subtracting 3 months, subtracting 6 months, year-boundary behavior, and April 2026 scope 0/3/6 target-period examples in `tests/unit/test_launch_scope_alignment.py`
- [X] T011 Add shared validation required by both training/evaluation and launch prediction for `area_id`, `year`/`month` or equivalent monthly period fields, and predictor columns from config with clear fail-fast errors before starting the requested long-running workflow step, such as model training, prediction generation, reporting, or visualization, in `src/ipcch/launch_nowcasting.py`
- [X] T012 Add training/evaluation-only validation for target columns, target rows, and aligned earlier feature rows with clear fail-fast errors before starting the requested long-running workflow step, such as model training, prediction generation, reporting, or visualization, in `src/ipcch/launch_nowcasting.py`
- [X] T013 Add launch-prediction validation requiring valid feature-period predictor rows and failing clearly when no usable launch feature-period prediction records exist, while explicitly not requiring target-period target or actual rows for scope 3/6, in `src/ipcch/launch_nowcasting.py`
- [X] T014 Add basic static-feature tests that config-recognized static features have no observed non-missing variation within each `area_id` across `year`/`month` in `tests/unit/test_launch_static_features.py`
- [X] T015 Add basic static-feature tests that non-invariant predictors are treated as time-varying rather than static in `tests/unit/test_launch_static_features.py`
- [X] T016 Implement or expose basic static/time-varying classification helper interfaces based on workflow config and area-level invariance scanning; defer regeneration, unresolved-inconsistency handling, and audit details to US3 in `src/ipcch/launch_nowcasting.py`
- [X] T017 Update `run_validation_only()` if it exists, or implement/use the confirmed lightweight validation entry point, so foundational validation can run without starting heavy training in `src/ipcch/launch_nowcasting.py`

**Checkpoint**: Foundation ready; CLI can accept scope, shared/training/prediction validation boundaries are explicit, period helpers exist, and static/time-varying helper interfaces exist. Deeper leakage-prevention and static-feature regeneration/consistency behavior is completed in US3.

---

## Phase 3: User Story 1 - Run default April 2026 launch workflow unchanged (Priority: P1) MVP

**Goal**: Scope 0 remains default and preserves legacy prediction values, paths, visualization compatibility, and downstream behavior while allowing optional scope-aware metadata/copies.

**Independent Test**: Run CLI help and scope 0 validation paths; confirm scope 0 behaves like the existing April 2026 same-period workflow, legacy outputs remain available, and scope metadata is additive.

### Tests for User Story 1

- [X] T018 [US1] Add tests that omitting `--scope` and passing `--scope 0` produce equivalent `LaunchConfig` semantics in `tests/unit/test_launch_nowcasting.py`
- [X] T019 [US1] Add smoke tests that the confirmed lightweight validation entry point accepts default scope 0 and explicit `--scope 0` without changing existing required arguments in `tests/smoke/test_launch_cli.py`
- [X] T020 [US1] Add output schema tests that prediction outputs and run summary include `scope_months`, `feature_period`, and `target_period` for scope 0 without replacing existing metadata in `tests/unit/test_launch_scope_outputs.py`
- [X] T021 [US1] Add output-layout tests that scope 0 legacy output names/paths remain available and optional scope-qualified metadata or copies do not replace them in `tests/unit/test_launch_scope_outputs.py`

### Implementation for User Story 1

- [X] T022 [US1] Preserve default scope 0 behavior in `build_training_frame()`, `build_xtest_april()`, and `predict_april()` call paths while treating scope 0 as same-period feature-to-target prediction in `src/ipcch/launch_nowcasting.py`
- [X] T023 [US1] Add scope 0 metadata fields such as `scope_months`, `feature_period`, and `target_period` without removing existing metadata in `assemble_prediction_output()` and `build_run_summary()` in `src/ipcch/launch_nowcasting.py`
- [X] T024 [US1] Update `resolve_output_layout()` and `write_prediction_outputs()` so scope 0 legacy output targets remain available unless intentionally migrated in `src/ipcch/launch_nowcasting.py`
- [X] T025 [US1] Ensure `_post_prediction()` receives and preserves scope 0 metadata without changing existing comparison/map behavior in `scripts/modeling/run_launch_nowcasting_2026_04.py`

**Checkpoint**: User Story 1 is independently functional; running without `--scope` remains MVP-compatible and scope 0 metadata is additive.

---

## Phase 4: User Story 2 - Generate forward-scope predictions from April 2026 features (Priority: P1)

**Goal**: Scope 3 and scope 6 generate launch predictions from feature-period rows, compute target period as feature period plus scope, and do not require target-period target or actual rows.

**Independent Test**: Use synthetic launch input with April 2026 feature rows and no July/October 2026 target/actual rows; confirm predictions can be assembled for July/October target periods and outputs are scope-qualified.

### Tests for User Story 2

- [X] T026 [US2] Add tests that scope 3 and scope 6 launch prediction compute July 2026 and October 2026 target metadata from April 2026 feature rows without requiring target-period target or actual rows in `tests/unit/test_launch_scope_outputs.py`
- [X] T027 [US2] Add tests that missing future target or actual rows are not counted as missing prediction records for scope 3/6 in `tests/unit/test_launch_scope_outputs.py`
- [X] T028 [US2] Add tests that prediction output schema and run summary include `scope_months`, `feature_period`, and `target_period` for scope 3 and scope 6 in `tests/unit/test_launch_scope_outputs.py`
- [X] T029 [US2] Add output-layout coexistence tests verifying the legacy scope 0 path remains available, an optional scope0-qualified path does not replace the legacy path, scope 3 and scope 6 paths do not overwrite scope 0 artifacts, and scope 3 and scope 6 paths are distinct from each other in `tests/unit/test_launch_scope_outputs.py`
- [X] T030 [US2] Add tests that scope-qualified output path generation rejects or avoids collisions across scope 0, scope 3, and scope 6 artifacts in `tests/unit/test_launch_scope_outputs.py`
- [X] T031 [US2] Add smoke tests for `--scope 3` and `--scope 6` using the confirmed lightweight validation entry point and synthetic CSV fixtures in `tests/smoke/test_launch_cli.py`

### Implementation for User Story 2

- [X] T032 [US2] Add launch prediction record preparation that uses feature-period predictor rows and computes `target_period = feature_period + scope_months` in `src/ipcch/launch_nowcasting.py`
- [X] T033 [US2] Update `build_xtest_april()` or introduce a scope-aware launch prediction builder; preserve existing function names only if needed for backward compatibility, but internally treat the logic as feature-period launch prediction rather than hardcoded April target prediction in `src/ipcch/launch_nowcasting.py`
- [X] T034 [US2] Update `predict_april()` or introduce a scope-aware prediction wrapper; preserve existing function names only if needed for backward compatibility, but emit predictions for the computed target period rather than assuming April is always the target in `src/ipcch/launch_nowcasting.py`
- [X] T035 [US2] Update `assemble_prediction_output()` to emit scope-aware feature and target period metadata for scope 3/6 in `src/ipcch/launch_nowcasting.py`
- [X] T036 [US2] Update `run_validation_only()` if it exists, or implement/use the confirmed lightweight validation entry point, so scope 3/6 validation requires valid feature-period predictor rows but does not require target-period target or actual rows in `src/ipcch/launch_nowcasting.py`
- [X] T037 [US2] Update orchestration so prediction generation distinguishes launch prediction records from training/evaluation records in `scripts/modeling/run_launch_nowcasting_2026_04.py`
- [X] T038 [US2] Update `resolve_output_layout()` so scope 3/6 outputs are path- or filename-qualified and do not overwrite scope 0 artifacts in `src/ipcch/launch_nowcasting.py`

**Checkpoint**: User Story 2 is independently functional at the record, metadata, validation, and output-layout level; scope 3/6 outputs should not be treated as analytically valid until US3 leakage-prevention alignment is complete.

---

## Phase 5: User Story 3 - Prevent time leakage in scoped training data (Priority: P1)

**Goal**: Scoped training/evaluation uses period-aware, area-aware alignment and validated static feature classification so no future time-varying predictors leak into training, evaluation, or launch prediction.

**Independent Test**: Use synthetic multi-month, multi-area data to confirm `y(area_id, t)` aligns with `X(area_id, t - scope)`, static attributes are not shifted, non-static predictors are shifted, and future-period predictors are never used.

### Tests for User Story 3

- [X] T039 [US3] Add tests for scope 3 alignment where target `area_id=A, 2025-07` uses time-varying predictors from `area_id=A, 2025-04` in `tests/unit/test_launch_scope_alignment.py`
- [X] T040 [US3] Add tests for scope 6 alignment using same-area calendar-month joins and no row-order shifting in `tests/unit/test_launch_scope_alignment.py`
- [X] T041 [US3] Add tests that scoped alignment never borrows feature values across `area_id` values in `tests/unit/test_launch_scope_alignment.py`
- [X] T042 [US3] Add tests that scope 3 launch prediction with April 2026 features does not use May, June, or July 2026 time-varying predictors in `tests/unit/test_launch_scope_alignment.py`
- [X] T043 [US3] Add tests that scope 6 launch prediction with April 2026 features does not use May through October 2026 time-varying predictors in `tests/unit/test_launch_scope_alignment.py`
- [X] T044 [US3] Add deeper static classification tests where observed non-missing variation within an `area_id` prevents static classification in `tests/unit/test_launch_static_features.py`
- [X] T045 [US3] Add static classification tests that one-period-only areas do not alone prove a feature is globally static in `tests/unit/test_launch_static_features.py`
- [X] T046 [US3] Add tests that missing static/time-varying classification triggers existing regeneration or validation behavior in `tests/unit/test_launch_static_features.py`
- [X] T047 [US3] Add tests that unresolved static classification inconsistency raises a clear `LaunchError` before starting the requested long-running workflow step, such as model training, prediction generation, reporting, or visualization, in `tests/unit/test_launch_static_features.py`

### Implementation for User Story 3

- [X] T048 [US3] Implement scoped training/evaluation alignment that joins target rows to time-varying feature rows by `area_id` and calendar feature reference period in `src/ipcch/launch_nowcasting.py`
- [X] T049 [US3] Update `build_training_frame()` to use scoped alignment for scope 3/6 while preserving all-prior-history cutoff semantics in `src/ipcch/launch_nowcasting.py`
- [X] T050 [US3] Complete static feature classification regeneration/validation behavior, including unresolved-inconsistency handling and clear errors, based on config and area-level invariance scanning in `src/ipcch/launch_nowcasting.py`
- [X] T051 [US3] Update `select_model_features()` or adjacent schema-selection logic so identifiers, targets, predictions, and config-recognized static attributes are excluded from time-varying shifting in `src/ipcch/launch_nowcasting.py`
- [X] T052 [US3] Add clear `LaunchError` messages for missing required keys, missing predictor columns, no usable scoped training/evaluation records, no usable launch feature-period prediction records, and unresolved static classification inconsistency before starting the requested long-running workflow step, such as model training, prediction generation, reporting, or visualization, in `src/ipcch/launch_nowcasting.py`
- [X] T053 [US3] Extend `build_feature_schema_report()` to record scope role information for static versus time-varying predictors where useful for auditability in `src/ipcch/launch_nowcasting.py`

**Checkpoint**: User Story 3 is independently functional; leakage-prevention semantics are testable with synthetic data and scope 3/6 results can be considered analytically valid after this checkpoint.

---

## Phase 6: User Story 4 - Produce forecast-only visualizations and clear reporting when actuals are unavailable (Priority: P2)

**Goal**: Visualization and reporting choose predicted-only or actual-vs-predicted layouts based on target-period actual availability, preserving scope 0 comparison behavior and making scope 3/6 future forecasts usable without actuals.

**Independent Test**: Use prediction fixtures with and without target-period actuals; confirm scope 3/6 predicted-only maps and unavailable actual-dependent reports, and scope 0 actual-vs-predicted maps when actuals exist.

### Tests for User Story 4

- [X] T054 [US4] Add visualization tests for predicted-only map output when target-period actuals are unavailable in `tests/unit/test_launch_visualizations.py`
- [X] T055 [US4] Add visualization tests that scope 0 actual-vs-predicted behavior remains available when actuals exist in `tests/unit/test_launch_visualizations.py`
- [X] T056 [P] [US4] Add comparison/reporting tests that actual-dependent metrics are skipped, marked unavailable, or omitted clearly when actuals are missing in `tests/unit/test_launch_comparison.py`
- [X] T057 [US4] Add lightweight CLI/post-prediction tests that scope 3/6 with missing future actuals still writes predictions and forecast-only map artifacts using synthetic fixtures and mocked or minimal model outputs in `tests/smoke/test_launch_cli.py`

### Implementation for User Story 4

- [X] T058 [US4] Add predicted-only visualization support to `build_map()` and supporting plot helpers in `src/ipcch/launch_visualizations.py`
- [X] T059 [US4] Preserve actual-vs-predicted visualization behavior for scope 0 with available actuals in `src/ipcch/launch_visualizations.py`
- [X] T060 [US4] Update `_post_prediction()` to choose predicted-only visualization when target-period actuals are unavailable and comparison mode cannot run in `scripts/modeling/run_launch_nowcasting_2026_04.py`
- [X] T061 [US4] Update `src/ipcch/launch_comparison.py` or post-prediction summary handling so actual-dependent metrics/reports are skipped, marked unavailable, or omitted clearly when actuals are missing
- [X] T062 [US4] Update `write_launch_reports()` and `build_run_summary()` to include scope-aware actual availability status for reports and summaries in `src/ipcch/launch_nowcasting.py`

**Checkpoint**: User Story 4 is independently functional; maps and reports behave correctly with and without actuals.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Validate end-to-end behavior and clean up documentation after all desired user stories are implemented.

- [ ] T063 [P] Update `specs/005-add-launch-scope/quickstart.md` if final CLI examples, validation entry point, or output names differ from planned contract
- [ ] T064 [P] Update `specs/005-add-launch-scope/contracts/launch-scope-cli.md` if implemented output fields, validation behavior, or unavailable-actual behavior differ from planned contract
- [X] T065 Run `PYTHONPATH=src python scripts/modeling/run_launch_nowcasting_2026_04.py --help` and confirm `--scope {0,3,6}` appears in `scripts/modeling/run_launch_nowcasting_2026_04.py`
- [ ] T066 Run targeted tests with `PYTHONPATH=src pytest tests/unit/test_launch_nowcasting.py tests/unit/test_launch_scope_alignment.py tests/unit/test_launch_static_features.py tests/unit/test_launch_scope_outputs.py tests/unit/test_launch_visualizations.py tests/unit/test_launch_comparison.py tests/smoke/test_launch_cli.py`
- [ ] T067 Run any existing launch integration tests that are lightweight enough for automation in `tests/integration/test_launch_end_to_end.py`
- [X] T068 Review generated scope metadata and output-path behavior against `specs/005-add-launch-scope/contracts/launch-scope-cli.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies; can start immediately.
- **Foundational (Phase 2)**: Depends on Setup completion; blocks all user stories.
- **User Stories (Phase 3+)**: Depend on Foundational completion.
- **Polish (Phase 7)**: Depends on all desired user stories being complete.

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational; no dependencies on other stories; recommended MVP for preserving legacy scope 0 behavior.
- **User Story 2 (P1)**: Can start after Foundational and can be implemented independently at the launch prediction record, metadata, validation, and output-layout level.
- **User Story 3 (P1)**: Can start after Foundational; required before scope 3/6 results are considered analytically valid because it completes leakage-prevention alignment and static-feature validation.
- **User Story 4 (P2)**: Can start after Foundational but benefits from scope metadata from US1/US2 and actual-availability status from reporting changes.

### Within Each User Story

- Tests should be added before implementation where practical and should fail before corresponding code changes.
- Shared helpers should be implemented before orchestration wiring.
- Output schema updates should happen before reporting/visualization consumers depend on those fields.
- Validation failures should fail fast with a clear message before starting the requested long-running workflow step, such as model training, prediction generation, reporting, or visualization.
- Story checkpoint must pass before treating that story as complete.

### Parallel Opportunities

- T003 and T004 can run in parallel after T001 begins because they inspect different files.
- T010 can run in parallel with T014/T015 after T009 interfaces are decided because they target separate scope/static test files.
- US1 tests T018 through T021 should be coordinated because they share launch configuration and output schema assumptions; T020 and T021 can run alongside implementation work after output layout interfaces are decided.
- US2 output tests T026 through T030 share fixtures in `tests/unit/test_launch_scope_outputs.py` and should be coordinated rather than treated as independent `[P]` tasks; T031 can run independently in `tests/smoke/test_launch_cli.py`.
- US3 alignment tests T039 through T043 share fixtures in `tests/unit/test_launch_scope_alignment.py`, and static-feature tests T044 through T047 share fixtures in `tests/unit/test_launch_static_features.py`; coordinate same-file edits rather than treating them as independent `[P]` tasks.
- US4 visualization tests T054/T055 share `tests/unit/test_launch_visualizations.py` and should be coordinated; comparison test T056 can run in parallel because it targets `tests/unit/test_launch_comparison.py`.
- Polish documentation tasks T063 and T064 can run in parallel.

---

## Parallel Example: User Story 2

```bash
Task: "Add tests that scope 3 and scope 6 launch prediction compute July 2026 and October 2026 target metadata from April 2026 feature rows without requiring target-period target or actual rows in tests/unit/test_launch_scope_outputs.py"
Task: "Add output-layout coexistence tests verifying legacy scope 0 path availability and distinct non-overwriting scope 3/scope 6 paths in tests/unit/test_launch_scope_outputs.py"
Task: "Add smoke tests for --scope 3 and --scope 6 using the confirmed lightweight validation entry point and synthetic CSV fixtures in tests/smoke/test_launch_cli.py"
```

## Parallel Example: User Story 3

```bash
Task: "Add tests for scope 3 alignment where target area_id=A, 2025-07 uses time-varying predictors from area_id=A, 2025-04 in tests/unit/test_launch_scope_alignment.py"
Task: "Add deeper static classification tests where observed non-missing variation within an area_id prevents static classification in tests/unit/test_launch_static_features.py"
Task: "Add tests that unresolved static classification inconsistency raises a clear LaunchError before starting the requested long-running workflow step in tests/unit/test_launch_static_features.py"
```

## Parallel Example: User Story 4

```bash
Task: "Add visualization tests for predicted-only map output when target-period actuals are unavailable in tests/unit/test_launch_visualizations.py"
Task: "Add visualization tests that scope 0 actual-vs-predicted behavior remains available when actuals exist in tests/unit/test_launch_visualizations.py"
Task: "Add comparison/reporting tests that actual-dependent metrics are skipped, marked unavailable, or omitted clearly when actuals are missing in tests/unit/test_launch_comparison.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 setup, including confirming the lightweight validation entry point.
2. Complete Phase 2 foundational scope, period, validation, and static/time-varying primitives.
3. Complete Phase 3 User Story 1.
4. Stop and validate default scope 0 behavior independently.

### Incremental Delivery

1. Setup + Foundational: CLI accepts scope, validation boundaries are explicit, period helpers exist, and static/time-varying helper interfaces exist; deeper regeneration and consistency behavior remains in US3.
2. US1: Default and explicit scope 0 remain legacy-compatible with additive scope metadata.
3. US2: Scope 3/6 launch prediction records, metadata, validation, and output coexistence work without future target/actual rows.
4. US3: Scoped training/evaluation alignment and static-feature validation prevent leakage; scope 3/6 results become analytically valid.
5. US4: Visualization/reporting degrade cleanly when actuals are unavailable and preserve scope 0 actual-vs-predicted behavior when actuals exist.
6. Polish: Run targeted test suite and update documentation/contracts if implementation details differ.

### Parallel Team Strategy

After Phase 2, separate contributors can work on US1 output compatibility, US2 launch prediction records, US3 alignment/static validation, and US4 visualization/reporting. Coordinate edits to `src/ipcch/launch_nowcasting.py`; test work is split across `tests/unit/test_launch_scope_alignment.py`, `tests/unit/test_launch_static_features.py`, and `tests/unit/test_launch_scope_outputs.py` to reduce file-level conflicts.

## Notes

- [P] tasks indicate independent or low-conflict work; tasks sharing the same file still require coordination.
- All story-phase tasks include `[US#]` labels for traceability.
- Avoid heavy model training and notebook execution; rely on unit/smoke tests and synthetic data.
- Keep canonical cumulative-regressor workflow and threshold unchanged.
- Scope values remain restricted to `0`, `3`, and `6`.
- Scope 0 backward compatibility remains part of the MVP.
- Scope 3/6 launch prediction can be scaffolded before US3, but scope 3/6 outputs should not be interpreted analytically until US3 leakage-prevention alignment and static-feature validation are complete.
