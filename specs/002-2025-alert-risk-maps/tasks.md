# Tasks: 2025 Alert Risk Maps

**Input**: Design documents from `/specs/002-2025-alert-risk-maps/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/plot-alert-risk-maps-cli.md, quickstart.md

**Tests**: Tests are included because the plan and quickstart require lightweight import checks, CLI `--help`, and tiny smoke tests for validation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4, US5)
- Every task includes an exact file path

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the module, CLI, and test skeletons for the plotting workflow.

- [X] T001 Create reusable plotting module skeleton in `src/ipcch/alert_risk_maps.py`
- [X] T002 Create reporting CLI skeleton with argument parser in `scripts/reporting/plot_2025_alert_risk_maps.py`
- [X] T003 [P] Create unit test file skeleton in `tests/unit/test_alert_risk_maps.py`
- [X] T004 [P] Create integration test file skeleton in `tests/integration/test_plot_2025_alert_risk_maps_cli.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Implement shared data structures, path handling, discovery, filtering, validation, and plotting primitives required by all user stories.

**Critical**: No user story work can begin until this phase is complete.

- [X] T005 Define dataclasses or typed records for `PredictionSelection`, `HorizonDataset`, `JoinedMapDataset`, `JoinValidation`, `OutputPlan`, and `ValidationSummary` in `src/ipcch/alert_risk_maps.py`
- [X] T006 Implement repository-relative default output path builders for reports and validation summaries in `src/ipcch/alert_risk_maps.py`
- [X] T007 Implement CLI arguments for prediction root, spatial path, explicit horizon files, output directories, figure format, basemap toggle, validation summary, and overwrite in `scripts/reporting/plot_2025_alert_risk_maps.py`; keep year fixed at 2025 for this feature
- [X] T008 Implement output conflict validation that fails when target figure or summary files exist without overwrite in `src/ipcch/alert_risk_maps.py`
- [X] T009 Implement prediction CSV loading and required-column validation for alert and top-risk modes in `src/ipcch/alert_risk_maps.py`
- [X] T010 Implement 2025 filtering and latest-record-per-`area_id` selection in `src/ipcch/alert_risk_maps.py`, including failure for missing temporal fields, no 2025 rows, and conflicting duplicate latest timestamps while permitting exact duplicate latest rows only when values are unchanged
- [X] T011 Implement horizon prediction file discovery with missing-candidate failure and ambiguous-candidate failure unless explicit files are supplied in `src/ipcch/alert_risk_maps.py`
- [X] T012 Implement Somalia-local output rejection and global-grouping/global-Somalia selection validation in `src/ipcch/alert_risk_maps.py`
- [X] T013 Implement spatial boundary loading, `area_id` normalization, geometry validity handling, and duplicate-boundary detection in `src/ipcch/alert_risk_maps.py`
- [X] T014 Implement 100% spatial join validation with actionable unmatched and duplicate `area_id` errors in `src/ipcch/alert_risk_maps.py`
- [X] T015 Implement validation summary assembly and optional JSON writing under `results/` in `src/ipcch/alert_risk_maps.py`
- [X] T016 Implement orchestration function that connects selection, loading, filtering, joins, output planning, and figure generation in `src/ipcch/alert_risk_maps.py`
- [X] T017 Wire `scripts/reporting/plot_2025_alert_risk_maps.py` to call the orchestration function and return non-zero on validation failures
- [X] T018 [P] Add unit tests for latest-record filtering, exact duplicate latest-row handling, conflicting duplicate latest-row failure, missing temporal fields, no 2025 rows, and binary alert derivation in `tests/unit/test_alert_risk_maps.py`
- [X] T019 [P] Add unit tests for output conflict validation and ambiguous horizon discovery failures in `tests/unit/test_alert_risk_maps.py`
- [X] T020 [P] Add unit tests for Somalia-local rejection and 100% spatial join validation in `tests/unit/test_alert_risk_maps.py`

**Checkpoint**: Shared workflow foundation is ready; each user story can now build on the same validated data pipeline.

---

## Phase 3: User Story 1 - Generate global 2025 actual-vs-predicted alert map (Priority: P1) MVP

**Goal**: Produce one global 2x3 2025 actual-vs-predicted binary alert map across 0m, 3m, and 6m horizons.

**Independent Test**: Run the workflow with three valid global prediction inputs and a matching synthetic or real spatial file, then verify a single global 2x3 alert figure is saved under `reports/` and all panels use `overall_phase >= 3` vs `overall_phase_pred >= 3`.

### Tests for User Story 1

- [X] T021 [P] [US1] Add unit test for global actual-vs-predicted panel dataset construction in `tests/unit/test_alert_risk_maps.py`
- [X] T022 [P] [US1] Add integration smoke test for global actual-vs-predicted CLI output using tiny synthetic inputs in `tests/integration/test_plot_2025_alert_risk_maps_cli.py`

### Implementation for User Story 1

- [X] T023 [US1] Implement binary actual/predicted alert field derivation for `overall_phase >= 3` and `overall_phase_pred >= 3` in `src/ipcch/alert_risk_maps.py`
- [X] T024 [US1] Implement global actual-vs-predicted 2x3 figure plotting with columns ordered 0m, 3m, 6m in `src/ipcch/alert_risk_maps.py`
- [X] T063 [US1] Update actual-vs-predicted binary map encoding to use green for no-alert and red for alert, with matching legend labels, in `src/ipcch/alert_risk_maps.py`
- [X] T026 [US1] Add global actual-vs-predicted output filename generation for `ipcch_2025_global_0m-3m-6m_actual_vs_predicted_alert_map.<format>` in `src/ipcch/alert_risk_maps.py`
- [X] T027 [US1] Expose global actual-vs-predicted generation through `scripts/reporting/plot_2025_alert_risk_maps.py`

**Checkpoint**: User Story 1 is independently functional and is the MVP.

---

## Phase 4: User Story 5 - Validate paths, files, columns, joins, and duplicate filtering (Priority: P1)

**Goal**: Provide clear validation behavior for missing files, missing columns, ambiguous discovery, duplicate filtering, Somalia-local rejection, 100% joins, and output conflicts.

**Independent Test**: Run unit and CLI smoke tests with invalid synthetic inputs and confirm the workflow fails before final figure creation with actionable messages.

### Tests for User Story 5

- [X] T028 [P] [US5] Add integration test for missing required prediction columns, all-null required values, missing temporal fields, no 2025 rows, and no-output behavior in `tests/integration/test_plot_2025_alert_risk_maps_cli.py`
- [X] T029 [P] [US5] Add integration test for unmatched spatial `area_id` failure and no-output behavior in `tests/integration/test_plot_2025_alert_risk_maps_cli.py`
- [X] T030 [P] [US5] Add integration test for existing output conflict failure without overwrite in `tests/integration/test_plot_2025_alert_risk_maps_cli.py`

### Implementation for User Story 5

- [X] T031 [US5] Ensure all validation failures include horizon, scope, file path, column name, output path, or sample `area_id` details in `src/ipcch/alert_risk_maps.py`
- [X] T032 [US5] Ensure validation failures prevent final figure writes and validation summary overwrites in `src/ipcch/alert_risk_maps.py`
- [X] T033 [US5] Add CLI error reporting that prints actionable validation errors and exits non-zero in `scripts/reporting/plot_2025_alert_risk_maps.py`
- [X] T034 [US5] Ensure validation summary records selected files, raw 2025 counts, retained counts, duplicate rows removed, spatial matches, spatial non-matches, rejected Somalia-local candidates, outputs, and status for every requested horizon and scope in `src/ipcch/alert_risk_maps.py`

**Checkpoint**: Validation behavior is independently testable and protects all map outputs.

---

## Phase 5: User Story 2 - Generate Somalia-only 2025 actual-vs-predicted alert map (Priority: P2)

**Goal**: Produce one Somalia-only 2x3 2025 actual-vs-predicted binary alert map across 0m, 3m, and 6m horizons using global-grouping/global-Somalia outputs only.

**Independent Test**: Run the workflow with valid Somalia global-grouping/global-Somalia prediction inputs and matching spatial boundaries, then verify a single Somalia-only 2x3 alert figure is saved under `reports/` and Somalia-local model outputs are not accepted.

### Tests for User Story 2

- [X] T035 [P] [US2] Add unit test for Somalia scope filtering from prediction or spatial country attributes in `tests/unit/test_alert_risk_maps.py`
- [X] T036 [P] [US2] Add integration smoke test for Somalia actual-vs-predicted CLI output using tiny synthetic inputs in `tests/integration/test_plot_2025_alert_risk_maps_cli.py`

### Implementation for User Story 2

- [X] T037 [US2] Implement Somalia-only scope filtering for prediction records and spatial boundaries in `src/ipcch/alert_risk_maps.py`
- [X] T038 [US2] Integrate Somalia global-grouping/global-Somalia horizon file selection into actual-vs-predicted dataset preparation in `src/ipcch/alert_risk_maps.py`
- [X] T039 [US2] Reuse actual-vs-predicted 2x3 plotting for Somalia extent and Somalia-only data in `src/ipcch/alert_risk_maps.py`
- [X] T040 [US2] Add Somalia actual-vs-predicted output filename generation for `ipcch_2025_somalia_0m-3m-6m_actual_vs_predicted_alert_map.<format>` in `src/ipcch/alert_risk_maps.py`
- [X] T041 [US2] Expose Somalia actual-vs-predicted generation through `scripts/reporting/plot_2025_alert_risk_maps.py`

**Checkpoint**: User Story 2 is independently functional without relying on Somalia-local model outputs.

---

## Phase 6: User Story 3 - Generate global nowcasting top-30% phase3-risk comparison map (Priority: P3)

**Goal**: Produce one global 2025 nowcasting map comparing actual top 30% by `phase3_worse` and predicted top 30% by `phase3_pred` after latest-record filtering.

**Independent Test**: Run the workflow with a valid global 0m prediction input and matching spatial boundaries, then verify the saved map distinguishes actual-only, predicted-only, both, and background categories.

### Tests for User Story 3

- [X] T042 [P] [US3] Add unit test for top-30% actual and predicted risk set computation after latest-record filtering in `tests/unit/test_alert_risk_maps.py`
- [X] T043 [P] [US3] Add integration smoke test for global top-risk CLI output using tiny synthetic inputs in `tests/integration/test_plot_2025_alert_risk_maps_cli.py`

### Implementation for User Story 3

- [X] T044 [US3] Implement top-30% risk set computation for `phase3_worse` and `phase3_pred` in `src/ipcch/alert_risk_maps.py`
- [X] T045 [US3] Implement mutually exclusive risk category assignment for `actual_only`, `predicted_only`, `both`, and `background` in `src/ipcch/alert_risk_maps.py`
- [X] T064 [US3] Rework top-risk comparison plotting to use two vertical subplots for actual top 30% and predicted top 30% with green/red encoding in `src/ipcch/alert_risk_maps.py`
- [X] T047 [US3] Add global top-risk output filename generation for `ipcch_2025_global_0m_top30_phase3_risk_comparison_map.<format>` in `src/ipcch/alert_risk_maps.py`
- [X] T048 [US3] Expose global top-risk generation through `scripts/reporting/plot_2025_alert_risk_maps.py`

**Checkpoint**: User Story 3 is independently functional for nowcasting/global scope.

---

## Phase 7: User Story 4 - Generate Somalia-only nowcasting top-30% phase3-risk comparison map (Priority: P4)

**Goal**: Produce one Somalia-only 2025 nowcasting top-risk comparison map using global-grouping/global-Somalia 0m outputs only.

**Independent Test**: Run the workflow with a valid Somalia global-grouping/global-Somalia 0m prediction input and matching spatial boundaries, then verify the saved map distinguishes the required risk categories and excludes Somalia-local model outputs.

### Tests for User Story 4

- [X] T049 [P] [US4] Add unit test for Somalia top-30% threshold computation after Somalia latest-record filtering in `tests/unit/test_alert_risk_maps.py`
- [X] T050 [P] [US4] Add integration smoke test for Somalia top-risk CLI output using tiny synthetic inputs in `tests/integration/test_plot_2025_alert_risk_maps_cli.py`

### Implementation for User Story 4

- [X] T051 [US4] Reuse Somalia scope filtering with 0m top-risk dataset preparation in `src/ipcch/alert_risk_maps.py`
- [X] T065 [US2/US3/US4] Add Latin America thumbnail/inset handling for global actual-vs-predicted and global top-risk panels when Latin America boundaries are present in `src/ipcch/alert_risk_maps.py`
- [X] T053 [US4] Add Somalia top-risk output filename generation for `ipcch_2025_somalia_0m_top30_phase3_risk_comparison_map.<format>` in `src/ipcch/alert_risk_maps.py`
- [X] T054 [US4] Expose Somalia top-risk generation through `scripts/reporting/plot_2025_alert_risk_maps.py`

**Checkpoint**: User Story 4 is independently functional for nowcasting/Somalia scope.

---

## Final Phase: Polish & Cross-Cutting Concerns

**Purpose**: Final verification, documentation alignment, and cleanup across all stories.

- [X] T055 [P] Update `specs/002-2025-alert-risk-maps/quickstart.md` if final CLI flags or output filenames differ from the contract
- [X] T056 [P] Add lightweight import validation command notes to `specs/002-2025-alert-risk-maps/quickstart.md` if implementation changes validation commands
- [X] T057 Run `PYTHONPATH=src python scripts/reporting/plot_2025_alert_risk_maps.py --help` from the repository root
- [X] T058 Run `PYTHONPATH=src python -c "import ipcch.alert_risk_maps"` from the repository root
- [X] T059 Run lightweight unit tests for `tests/unit/test_alert_risk_maps.py`
- [X] T060 Run lightweight integration smoke tests for `tests/integration/test_plot_2025_alert_risk_maps_cli.py`, including validation-summary content assertions for every requested horizon and scope
- [X] T061 Review generated code to confirm no hardcoded machine-specific absolute paths or raw spatial data copies in `src/ipcch/alert_risk_maps.py` and `scripts/reporting/plot_2025_alert_risk_maps.py`
- [X] T066 Run `PYTHONPATH=src ~/.venvs/ipcch-geo/bin/python scripts/reporting/plot_2025_alert_risk_maps.py --overwrite ...` to regenerate and overwrite the four final figures under `reports/deep_feature_weight_decay_forecasting/alert_risk_maps`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies; can start immediately.
- **Foundational (Phase 2)**: Depends on Setup; blocks all user stories.
- **US1 (Phase 3, P1 MVP)**: Depends on Foundational.
- **US5 (Phase 4, P1 validation)**: Depends on Foundational; can run in parallel with US1 after shared validation primitives exist, but should complete before real-output runs.
- **US2 (Phase 5, P2)**: Depends on Foundational and reuses US1 plotting primitives.
- **US3 (Phase 6, P3)**: Depends on Foundational; independent of US2.
- **US4 (Phase 7, P4)**: Depends on Foundational, Somalia filtering from US2, and top-risk primitives from US3.
- **Polish**: Depends on selected user stories being complete.

### User Story Dependencies

- **US1**: Can start after Foundational; MVP scope.
- **US5**: Can start after Foundational; validates all stories and should be completed before using real outputs.
- **US2**: Can start after US1 plotting primitives and Foundational are complete.
- **US3**: Can start after Foundational; no dependency on US1/US2 beyond shared join/filter primitives.
- **US4**: Best after US2 and US3 because it combines Somalia scope with top-risk comparison.

### Within Each User Story

- Tests are written before or alongside implementation for the same story.
- Data preparation before plotting.
- Plotting before CLI exposure for that story.
- CLI exposure before independent smoke validation.

---

## Parallel Execution Examples

### User Story 1

```bash
# Parallel tests before implementation
Task: "T021 [US1] Add unit test for global actual-vs-predicted panel dataset construction in tests/unit/test_alert_risk_maps.py"
Task: "T022 [US1] Add integration smoke test for global actual-vs-predicted CLI output using tests/integration/test_plot_2025_alert_risk_maps_cli.py"
```

### User Story 5

```bash
# Parallel validation smoke tests
Task: "T028 [US5] Add integration test for missing required prediction columns in tests/integration/test_plot_2025_alert_risk_maps_cli.py"
Task: "T029 [US5] Add integration test for unmatched spatial area_id failure in tests/integration/test_plot_2025_alert_risk_maps_cli.py"
Task: "T030 [US5] Add integration test for existing output conflict failure in tests/integration/test_plot_2025_alert_risk_maps_cli.py"
```

### User Story 2

```bash
# Parallel Somalia tests
Task: "T035 [US2] Add unit test for Somalia scope filtering in tests/unit/test_alert_risk_maps.py"
Task: "T036 [US2] Add integration smoke test for Somalia actual-vs-predicted CLI output in tests/integration/test_plot_2025_alert_risk_maps_cli.py"
```

### User Story 3

```bash
# Parallel top-risk tests
Task: "T042 [US3] Add unit test for top-30% risk set computation in tests/unit/test_alert_risk_maps.py"
Task: "T043 [US3] Add integration smoke test for global top-risk CLI output in tests/integration/test_plot_2025_alert_risk_maps_cli.py"
```

### User Story 4

```bash
# Parallel Somalia top-risk tests
Task: "T049 [US4] Add unit test for Somalia top-30% threshold computation in tests/unit/test_alert_risk_maps.py"
Task: "T050 [US4] Add integration smoke test for Somalia top-risk CLI output in tests/integration/test_plot_2025_alert_risk_maps_cli.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 setup.
2. Complete Phase 2 foundational data loading, filtering, discovery, join, validation, and orchestration primitives.
3. Complete Phase 3 User Story 1.
4. Stop and validate the global actual-vs-predicted 2x3 map independently.
5. Add User Story 5 validation hardening before running against real full outputs.

### Incremental Delivery

1. Shared foundation enables all map types.
2. US1 delivers the global cross-horizon alert map MVP.
3. US5 ensures invalid inputs fail safely and clearly.
4. US2 adds Somalia-only cross-horizon alert maps without Somalia-local outputs.
5. US3 adds global nowcasting top-risk comparison.
6. US4 adds Somalia-only nowcasting top-risk comparison.
7. Polish validates CLI, imports, tests, and artifact separation.

### Parallel Team Strategy

- One implementer can build foundational logic while another writes synthetic test fixtures and smoke tests.
- After Foundational, US2 and US3 can proceed mostly independently once US1 plotting primitives are available.
- US4 should be scheduled after both Somalia filtering and top-risk category logic are stable.

## Notes

- [P] tasks touch different files or independent test cases and can run in parallel.
- User story labels map to the spec’s five user stories.
- All real-data validation must remain lightweight and must not execute training notebooks or model fitting.
- Do not copy external shapefiles or raw source data into the repository.
- Do not overwrite existing report figures or validation summaries unless `--overwrite` behavior is explicitly used.
