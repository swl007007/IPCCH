# Tasks: Nowcasting Grouped SHAP Values

**Input**: Design documents from `specs/007-nowcasting-grouped-shap/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Test tasks are included because the specification defines independent tests, success criteria, CLI help checks, disabled/enabled behavior checks, and backward-compatibility validation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story?] Description [(depends on ...)]`

- **[P]**: Can run in parallel with other ready tasks once any listed dependencies are satisfied
- **[Story?]**: Which user story this task belongs to (e.g., US1, US2, US3). Required for user story phases only
- **(depends on ...)**: Explicit dependency on earlier task IDs
- Every task includes exact file paths

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish test and CLI scaffolding before shared helper implementation.

- [X] T001 Add nowcasting grouped SHAP smoke-test skeleton and help command fixture in tests/smoke/test_launch_nowcasting_grouped_shap_cli.py
- [X] T002 [P] Add grouped SHAP test fixtures for synthetic feature matrices, crosswalk rows, and weather proxy columns in tests/unit/test_forecasting_shap.py
- [X] T003 [P] Add grouped SHAP nowcasting test fixtures for LaunchConfig/output layout/mode handling in tests/unit/test_launch_nowcasting.py
- [X] T004 [P] Inspect and document existing SHAP helper public API preservation points in src/ipcch/forecasting_shap.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core reusable SHAP grouping and nowcasting wiring that all user stories depend on.

**CRITICAL**: No user story work can begin until this phase is complete.

- [X] T005 Add constants for nowcasting grouped SHAP target, scope order, weather forecast group, and expected seven-group handling in src/ipcch/forecasting_shap.py (depends on T004)
- [X] T006 Implement generalized grouped SHAP aggregation helpers that preserve existing six-category forecasting behavior in src/ipcch/forecasting_shap.py (depends on T005)
- [X] T007 Implement scope-by-group matrix and heatmap helpers for `0m`, `3m`, `6m`, `12m` in src/ipcch/forecasting_shap.py (depends on T006)
- [X] T008 Implement attribution coverage summary helpers for unmatched counts and unmatched absolute SHAP contribution/share in src/ipcch/forecasting_shap.py (depends on T006)
- [X] T009 Add grouped SHAP output path fields or helper functions under launch output/report roots in src/ipcch/launch_nowcasting.py (depends on T005)
- [X] T010 Add nowcasting grouped SHAP config fields or dataclass support to src/ipcch/launch_nowcasting.py (depends on T009)
- [X] T011 Add crosswalk path/key resolution support for grouped SHAP without hardcoded local absolute defaults in src/ipcch/launch_nowcasting.py (depends on T010)

**Checkpoint**: Foundation ready - user story implementation can now begin in priority order.

---

## Phase 3: User Story 1 - Enable grouped SHAP for nowcasting (Priority: P1) MVP

**Goal**: User can enable grouped SHAP with `--compute-grouped-shap`; disabled runs remain unchanged.

**Independent Test**: CLI help shows the option; disabled runs do not require SHAP/crosswalk; unsupported modes reject the option clearly.

### Tests for User Story 1

- [X] T012 [P] [US1] Add CLI help test for `--compute-grouped-shap` and grouped SHAP crosswalk options in tests/smoke/test_launch_nowcasting_grouped_shap_cli.py (depends on T001)
- [X] T013 [P] [US1] Add disabled-path test proving grouped SHAP crosswalk resolution is not required when flag is absent in tests/smoke/test_launch_nowcasting_grouped_shap_cli.py (depends on T001)
- [X] T014 [P] [US1] Add Mode 2 rejection test for grouped SHAP with `--skip-training` in tests/smoke/test_launch_nowcasting_grouped_shap_cli.py (depends on T001)
- [X] T015 [P] [US1] Add prediction-only Mode 3 rejection test for grouped SHAP with supplied predictions in tests/smoke/test_launch_nowcasting_grouped_shap_cli.py (depends on T001)

### Implementation for User Story 1

- [X] T016 [US1] Add `--compute-grouped-shap` CLI option to scripts/modeling/run_launch_nowcasting_2026_04.py (depends on T010)
- [X] T017 [US1] Add grouped SHAP crosswalk path/key and optional column override CLI options to scripts/modeling/run_launch_nowcasting_2026_04.py (depends on T011, T016)
- [X] T018 [US1] Propagate grouped SHAP CLI options into nowcasting launch configuration in scripts/modeling/run_launch_nowcasting_2026_04.py (depends on T017)
- [X] T019 [US1] Reject grouped SHAP for supplied-model Mode 2 with a clear actionable error in scripts/modeling/run_launch_nowcasting_2026_04.py (depends on T018)
- [X] T020 [US1] Reject grouped SHAP for supplied-prediction or prediction-only Mode 3 with a clear actionable error in scripts/modeling/run_launch_nowcasting_2026_04.py (depends on T018)
- [X] T021 [US1] Ensure grouped-SHAP-disabled execution does not import SHAP, resolve crosswalk paths, or add grouped SHAP outputs in src/ipcch/launch_nowcasting.py (depends on T018)

**Checkpoint**: User Story 1 is independently functional when CLI tests pass and disabled behavior is unchanged.

---

## Phase 4: User Story 2 - Group nowcasting features consistently (Priority: P1)

**Goal**: Every nowcasting training feature is mapped to a six-category group, `weather forecast`, or explicit unmatched diagnostics.

**Independent Test**: Synthetic nowcasting features produce complete mapping rows with weather precedence, normalized/base matching, ambiguity handling, and unmatched diagnostics.

### Tests for User Story 2

- [X] T022 [P] [US2] Add exact crosswalk match test for nowcasting feature mapping in tests/unit/test_forecasting_shap.py (depends on T002)
- [X] T023 [P] [US2] Add normalized/base-variable match tests for lagged/current/scope suffix variants, original-name preservation, and zero/multiple-match unresolved handling in tests/unit/test_forecasting_shap.py (depends on T002)
- [X] T024 [P] [US2] Add weather forecast precedence test using an explicit `weather_forecast_features` seed set in tests/unit/test_forecasting_shap.py (depends on T002)
- [X] T025 [P] [US2] Add ambiguous normalized match test that leaves the feature unresolved in tests/unit/test_forecasting_shap.py (depends on T002)
- [X] T026 [P] [US2] Add unmatched diagnostics and coverage test for unmapped nowcasting features in tests/unit/test_forecasting_shap.py (depends on T002)

### Implementation for User Story 2

- [X] T027 [US2] Implement weather forecast feature seed handling in src/ipcch/forecasting_shap.py by accepting an explicit `weather_forecast_features` set/list from the caller and applying those seeds before crosswalk matching (depends on T005)
- [X] T028 [US2] Implement exact crosswalk feature matching for nowcasting feature-to-group mapping in src/ipcch/forecasting_shap.py (depends on T027)
- [X] T029 [US2] Implement deterministic normalized/base-variable matching in src/ipcch/forecasting_shap.py, including documented normalization steps, no mutation of original feature names in diagnostics, and unresolved handling for zero or multiple plausible matches (depends on T028)
- [X] T030 [US2] Implement complete feature-to-group mapping output with match method, matched reference variable, weather flag, and unmatched status in src/ipcch/forecasting_shap.py (depends on T029)
- [X] T031 [US2] Generate nowcasting weather forecast proxy feature seeds via existing nowcasting weather proxy helpers in src/ipcch/launch_nowcasting.py and pass them into the grouped SHAP feature-to-group mapping flow (depends on T030)
- [X] T032 [US2] Write feature-to-group mapping CSV for every grouped SHAP run in src/ipcch/launch_nowcasting.py (depends on T031)
- [X] T033 [US2] Write unmatched-feature diagnostics CSV when unresolved features exist in src/ipcch/launch_nowcasting.py (depends on T031)

**Checkpoint**: User Story 2 is independently functional when mapping output includes 100% of training features and weather/unmatched behavior is testable.

---

## Phase 5: User Story 3 - Explain the training feature matrix (Priority: P1)

**Goal**: Grouped SHAP explains the exact fitted `phase3_worse` training matrix in fitted-model feature order.

**Independent Test**: Synthetic nowcasting training data proves SHAP receives `train_featured.dropna(subset=["phase3_worse"]).loc[:, feature_columns]` and rejects feature-order mismatches.

### Tests for User Story 3

- [X] T034 [P] [US3] Add phase3 training-matrix extraction test using target-missing rows in tests/unit/test_launch_nowcasting.py (depends on T003)
- [X] T035 [P] [US3] Add feature-order preservation test for grouped SHAP input matrix in tests/unit/test_launch_nowcasting.py (depends on T003)
- [X] T036 [P] [US3] Add grouped SHAP computation integration test with a fake phase3 model or monkeypatched SHAP helper in tests/unit/test_launch_nowcasting.py (depends on T003)

### Implementation for User Story 3

- [X] T037 [US3] Add helper to build the exact `phase3_worse` SHAP training matrix in src/ipcch/launch_nowcasting.py (depends on T010)
- [X] T038 [US3] Capture or access the fitted `phase3_worse` model after train-and-predict model fitting in src/ipcch/launch_nowcasting.py (depends on T037)
- [X] T039 [US3] Call existing phase3 SHAP computation with the fitted model, exact training matrix, and ordered `feature_columns` in src/ipcch/launch_nowcasting.py (depends on T038)
- [X] T040 [US3] Surface a clear grouped SHAP computation error without writing complete-looking partial outputs in src/ipcch/launch_nowcasting.py (depends on T039)
- [X] T041 [US3] Write grouped SHAP metadata JSON with target, sample source, feature order validation, aggregation metric, crosswalk path, coverage, and artifact paths in src/ipcch/launch_nowcasting.py (depends on T039)

**Checkpoint**: User Story 3 is independently functional when grouped SHAP uses the phase3 training matrix and metadata proves target/sample/order.

---

## Phase 6: User Story 4 - Compare grouped importance across forecasting scopes (Priority: P2)

**Goal**: Produce scope-by-group matrix and heatmap outputs with groups on rows and available scopes in canonical order.

**Independent Test**: Synthetic grouped SHAP outputs for one or more scopes render a matrix/heatmap with seven group rows and canonical scope columns.

### Tests for User Story 4

- [X] T042 [P] [US4] Add seven-group scope matrix test with canonical `0m`, `3m`, `6m`, `12m` ordering in tests/unit/test_forecasting_shap.py (depends on T002)
- [X] T043 [P] [US4] Add available-scope heatmap artifact test for subset scopes in tests/unit/test_forecasting_shap.py (depends on T002)
- [X] T044 [P] [US4] Add zero-row/zero-attribution expected-group test in tests/unit/test_forecasting_shap.py (depends on T002)

### Implementation for User Story 4

- [X] T045 [US4] Implement current-scope grouped SHAP long/matrix output writing with a machine-readable scope label in src/ipcch/launch_nowcasting.py (depends on T039, T031)
- [X] T046 [US4] Implement or wire deterministic scope-by-group matrix generation in src/ipcch/forecasting_shap.py from explicit grouped SHAP artifact paths or metadata-recorded paths, preserving canonical scope order and avoiding unconstrained recursive directory scanning (depends on T007)
- [X] T047 [US4] Implement or wire grouped SHAP heatmap rendering with feature groups on y-axis and forecasting scopes on x-axis in src/ipcch/forecasting_shap.py (depends on T046)
- [X] T048 [US4] Save machine-readable grouped SHAP matrix/long outputs under the launch results root and save grouped SHAP heatmap artifacts under the launch report root in src/ipcch/launch_nowcasting.py (depends on T045, T047)

**Checkpoint**: User Story 4 is independently functional when matrix/heatmap outputs have seven expected rows and canonical scope columns for available scopes.

---

## Phase 7: User Story 5 - Review grouping diagnostics and output locations (Priority: P2)

**Goal**: Console messages, run summary, report metadata, and diagnostics clearly show mapping quality, coverage, and artifact paths.

**Independent Test**: Running grouped SHAP on synthetic or monkeypatched data reports matched/weather/unmatched counts, unmatched attribution coverage, and output paths.

### Tests for User Story 5

- [X] T049 [P] [US5] Add output-path reporting test for grouped SHAP artifacts in tests/unit/test_launch_nowcasting.py (depends on T003)
- [X] T050 [P] [US5] Add run summary metadata test for grouped SHAP counts, coverage, and paths in tests/unit/test_launch_nowcasting.py (depends on T003)
- [X] T051 [P] [US5] Add console output smoke or unit test for grouped SHAP counts and paths in tests/smoke/test_launch_nowcasting_grouped_shap_cli.py (depends on T001)

### Implementation for User Story 5

- [X] T052 [US5] Add grouped SHAP artifact paths and coverage summary to nowcasting run summary in src/ipcch/launch_nowcasting.py (depends on T041, T048)
- [X] T053 [US5] Add grouped SHAP section to launch markdown/report output in src/ipcch/launch_nowcasting.py (depends on T052)
- [X] T054 [US5] Print grouped SHAP matched count, weather forecast count, unmatched count, unmatched attribution coverage, and artifact paths in scripts/modeling/run_launch_nowcasting_2026_04.py (depends on T052)
- [X] T055 [US5] Ensure missing diagnostics path is reported only when unmatched diagnostics exist in src/ipcch/launch_nowcasting.py (depends on T053)

**Checkpoint**: User Story 5 is independently functional when diagnostics and output locations are visible in saved metadata/reporting and console output.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Validate backward compatibility, remove incidental artifacts, and align final behavior with quickstart.

- [X] T056 [P] Run `PYTHONPATH=src pytest -q tests/unit/test_forecasting_shap.py` and record result in implementation notes or PR summary (depends on T047)
- [X] T057 [P] Run `PYTHONPATH=src pytest -q tests/unit/test_launch_nowcasting.py` and record result in implementation notes or PR summary (depends on T055)
- [X] T058 [P] Run nowcasting grouped SHAP CLI help smoke test in tests/smoke/test_launch_nowcasting_grouped_shap_cli.py and record result in implementation notes or PR summary (depends on T054)
- [X] T059 Run `PYTHONPATH=src python scripts/modeling/run_launch_nowcasting_2026_04.py --help` and verify grouped SHAP help text appears (depends on T016)
- [X] T060 Verify grouped-SHAP-disabled nowcasting path remains unchanged by inspecting output guards and disabled tests in src/ipcch/launch_nowcasting.py and tests/smoke/test_launch_nowcasting_grouped_shap_cli.py (depends on T021)
- [X] T061 Review generated artifact paths for results/reports separation in src/ipcch/launch_nowcasting.py (depends on T052)
- [X] T062 Remove accidental temporary Speckit file specs/007-nowcasting-grouped-shap/spec.md.tmp.25158.b8cb2ee216e8 if confirmed unnecessary
- [X] T063 Update quickstart validation notes if final CLI option names differ from specs/007-nowcasting-grouped-shap/quickstart.md

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies; can start immediately.
- **Foundational (Phase 2)**: Depends on Setup; blocks all user stories.
- **US1, US2, US3 (P1)**: Depend on Foundational; implement in priority order for MVP safety, though some tests can be prepared in parallel.
- **US4, US5 (P2)**: Depend on grouped SHAP computation and mapping outputs from P1 stories.
- **Polish**: Depends on desired user stories being complete.

### User Story Dependencies

- **US1 (P1)**: Depends on Phase 2; no dependency on other stories.
- **US2 (P1)**: Depends on Phase 2; can be developed after shared helpers exist.
- **US3 (P1)**: Depends on Phase 2 and integrates with US2 mapping for full grouped output.
- **US4 (P2)**: Depends on US2 and US3 outputs.
- **US5 (P2)**: Depends on US2, US3, and US4 artifact paths/coverage.

### Independent Test Criteria

- **US1**: CLI help shows `--compute-grouped-shap`; disabled path does not require SHAP/crosswalk; Mode 2 and Mode 3 reject grouped SHAP clearly.
- **US2**: Mapping output includes every feature with correct weather precedence, exact/normalized matching, and unmatched diagnostics.
- **US3**: SHAP input matrix equals phase3 training rows and ordered features; grouped SHAP explains only `phase3_worse`.
- **US4**: Grouped SHAP matrix/heatmap has seven group rows and available scope columns ordered `0m`, `3m`, `6m`, `12m`.
- **US5**: Counts, coverage, diagnostics, and output paths appear in console output and saved run metadata/reporting.

---

## Parallel Opportunities

- T002, T003, and T004 can run in parallel after T001 is started.
- T012 through T015 can be written in parallel because they target separate CLI behaviors.
- T022 through T026 can be written in parallel because they cover independent mapping cases.
- T034 through T036 can be written in parallel because they cover independent training-matrix behaviors.
- T042 through T044 can be written in parallel because they cover independent matrix/heatmap cases.
- T049 through T051 can be written in parallel because they cover separate reporting surfaces.
- T056 through T058 can run in parallel once implementation is complete.

### Example Parallel Execution Blocks

```text
# After Phase 2 helpers exist, mapping tests can be authored together:
T022, T023, T024, T025, T026

# After SHAP matrix integration exists, output/report tests can be authored together:
T049, T050, T051

# Final validation can run in parallel:
T056, T057, T058
```

---

## Execution Wave DAG

```text
Wave 1:
  T001, T002, T003, T004

Wave 2:
  T005

Wave 3:
  T006, T009

Wave 4:
  T007, T008, T010

Wave 5:
  T011, T012, T013, T014, T015, T022, T023, T024, T025, T026, T034, T035, T036, T042, T043, T044, T049, T050, T051

Wave 6:
  T016, T027, T037

Wave 7:
  T017, T028, T038

Wave 8:
  T018, T029, T039

Wave 9:
  T019, T020, T021, T030, T040, T041

Wave 10:
  T031, T045, T046

Wave 11:
  T032, T033, T047

Wave 12:
  T048, T052

Wave 13:
  T053, T054, T055

Wave 14:
  T056, T057, T058, T059, T060, T061, T062, T063
```

---

## Implementation Strategy

### MVP First (P1 Stories)

1. Complete Phase 1 and Phase 2 shared helper/config work.
2. Complete US1 so the flag exists, disabled behavior is unchanged, and unsupported modes reject clearly.
3. Complete US2 so feature mapping is complete and auditable.
4. Complete US3 so grouped SHAP uses the exact `phase3_worse` training matrix.
5. Stop and validate P1 independently before adding scope heatmaps and reporting polish.

### Incremental Delivery

1. **MVP**: US1 + US2 + US3 produce grouped SHAP matrix/mapping/diagnostics for a supported train-and-predict run.
2. **Visualization increment**: US4 adds scope-by-group heatmap behavior.
3. **Transparency increment**: US5 adds console/run-summary/reporting polish.
4. **Final validation**: Run unit/smoke/help checks and confirm disabled-path backward compatibility.

### Notes

- Do not run full nowcasting training or full SHAP computation unless the user explicitly approves it.
- Keep existing forecasting SHAP APIs backward-compatible.
- Keep unmatched features diagnostics-only; do not introduce an `other` group.
- Keep grouped SHAP unsupported for supplied-model and prediction-only modes in this feature.
