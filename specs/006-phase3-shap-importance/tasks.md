# Tasks: Phase-3 SHAP Six-Category Feature Importance

**Input**: Design documents from `/specs/006-phase3-shap-importance/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/cli-shap-options.md, quickstart.md

**Tests**: Tests are included because the specification requires lightweight validation hooks, synthetic aggregation checks, visualization-shape checks, path-configuration checks, default-disabled checks, and smoke tests without heavy full training.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- All tasks include exact file paths

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare path configuration, actual entrypoint alignment, module skeleton, and test files shared by all stories.

- [X] T001 Verify the actual weight-decay forecasting CLI entrypoint and main pipeline function in `scripts/modeling/run_deep_feature_weight_decay_forecasting.py` and `src/ipcch/forecasting_weight_decay.py`; if the script does not exist, update downstream tasks to the real entrypoint or add a thin CLI wrapper around `src/ipcch/forecasting_weight_decay.py`
- [X] T002 Add `six_category_feature_crosswalk` example key to `configs/paths.example.json`
- [X] T003 Create reusable SHAP helper module skeleton in `src/ipcch/forecasting_shap.py`
- [X] T004 Create unit test file skeleton for SHAP helpers in `tests/unit/test_forecasting_shap.py`
- [X] T005 Create smoke test file skeleton for CLI SHAP options in `tests/smoke/test_weight_decay_shap_cli.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core data structures, dependency strategy, CLI controls, validation hooks, and output planning that all user stories depend on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T006 Define constants for target `phase3_worse`, allowed sample types, expected feature-group count, and default crosswalk key in `src/ipcch/forecasting_shap.py`
- [X] T007 Implement dataclasses or typed records for SHAP run config, per-feature summary, six-category summary, and diagnostics in `src/ipcch/forecasting_shap.py`
- [X] T008 Extend output planning with phase-3 SHAP result/report directories and deterministic artifact filenames in `src/ipcch/forecasting_weight_decay.py`
- [X] T009 Extend `ensure_output_dirs()` to create planned phase-3 SHAP result/report subdirectories in `src/ipcch/forecasting_weight_decay.py`
- [X] T010 Add SHAP CLI argument definitions from `contracts/cli-shap-options.md` to `scripts/modeling/run_deep_feature_weight_decay_forecasting.py`
- [X] T011 Implement crosswalk path resolution from explicit path or external-path key in `scripts/modeling/run_deep_feature_weight_decay_forecasting.py`
- [X] T012 [P] Add CLI help smoke assertions for `--enable-shap`, crosswalk, sample, raw export, unmapped, and size guard options in `tests/smoke/test_weight_decay_shap_cli.py`
- [X] T013 [P] Add unit tests for deterministic phase-3 SHAP artifact filename generation in `tests/unit/test_forecasting_shap.py`
- [X] T014 [P] Add or document the SHAP dependency strategy as a required dependency, optional extra, or documented prerequisite in `pyproject.toml`
- [X] T015 Verify existing support for `--dry-run` and `--sample-rows` in `scripts/modeling/run_deep_feature_weight_decay_forecasting.py`; if absent, implement them or replace the quickstart lightweight validation command with an existing equivalent path
- [X] T016 Verify `PYTHONPATH=src python scripts/modeling/run_deep_feature_weight_decay_forecasting.py --help` shows SHAP options without local absolute paths

**Checkpoint**: Foundation ready - user story implementation can now begin.

---

## Phase 3: User Story 1 - Record phase-3 SHAP explanations during forecasting runs (Priority: P1) 🎯 MVP

**Goal**: When explicitly enabled, record SHAP values for only the fitted phase-3-or-higher model without changing ordinary prediction and metric behavior.

**Independent Test**: Run a tiny smoke path or mocked phase-3 model path with SHAP enabled for one scope-year and verify phase-3 SHAP artifacts are produced while normal prediction/metric artifacts remain present; run SHAP-disabled help/default tests to verify unchanged behavior.

### Tests for User Story 1

- [X] T017 [US1] Add unit test for phase-3-only target enforcement rejecting phase-2, phase-4, phase-5, and final-label SHAP explanations in `tests/unit/test_forecasting_shap.py`
- [X] T018 [US1] Add unit test for exact feature-column order and feature-matrix alignment validation in `tests/unit/test_forecasting_shap.py`
- [X] T019 [US1] Add smoke test that SHAP-disabled CLI path remains backward-compatible and does not require the SHAP package in `tests/smoke/test_weight_decay_shap_cli.py`
- [X] T020 [US1] Add smoke test that SHAP-disabled runs do not require a crosswalk path and do not validate crosswalk files in `tests/smoke/test_weight_decay_shap_cli.py`
- [X] T021 [US1] Add smoke test that SHAP-enabled CLI path fails clearly when the SHAP package/engine is unavailable or incompatible in `tests/smoke/test_weight_decay_shap_cli.py`
- [X] T022 [US1] Add unit tests for SHAP output shape normalization and shape-mismatch errors in `tests/unit/test_forecasting_shap.py`

### Implementation for User Story 1

- [X] T023 [US1] Implement optional SHAP package/engine import and version detection that runs only when SHAP is enabled in `src/ipcch/forecasting_shap.py`
- [X] T024 [US1] Implement feature-matrix alignment validation against fitted phase-3 feature columns in `src/ipcch/forecasting_shap.py`
- [X] T025 [US1] Normalize SHAP outputs from supported SHAP APIs into a two-dimensional rows-by-features array and validate shape against the SHAP matrix in `src/ipcch/forecasting_shap.py`
- [X] T026 [US1] Implement phase-3-only SHAP computation for a fitted model and aligned SHAP matrix in `src/ipcch/forecasting_shap.py`
- [X] T027 [US1] Modify the actual holdout-training function, likely in `src/ipcch/forecasting_weight_decay.py`, or add an equivalent phase-3 callback hook so the CLI entrypoint in `scripts/modeling/run_deep_feature_weight_decay_forecasting.py` can capture the fitted `phase3_worse` model, existing training matrix, existing test matrix, existing sample weights if needed, and feature order without changing train/test split membership, date cutoffs, preprocessing state, predictions, or metrics
- [X] T028 [US1] Wire `--enable-shap` and `--shap-sample train|test` into the holdout loop and default to training rows in `scripts/modeling/run_deep_feature_weight_decay_forecasting.py`
- [X] T029 [US1] Write phase-3 SHAP run metadata including target `phase3_worse`, forecasting scopes `fs0`, `fs1`, `fs2`, `fs3`, test years 2022, 2023, 2024, 2025, per-record scope and test year where applicable, temporal split rule, SHAP explanation sample type, feature count, SHAP explanation row count, SHAP package/engine name and version, and generated artifact path placeholders in `scripts/modeling/run_deep_feature_weight_decay_forecasting.py`
- [X] T030 [US1] Record unavailable split/model diagnostics for empty phase-3 training rows or empty SHAP explanation rows in `src/ipcch/forecasting_shap.py`
- [X] T031 [US1] Ensure SHAP-disabled runs bypass all explanation imports, crosswalk validation, and SHAP output creation in `scripts/modeling/run_deep_feature_weight_decay_forecasting.py`

**Checkpoint**: User Story 1 is fully functional and testable independently.

---

## Phase 4: User Story 2 - Aggregate explanations into six feature categories (Priority: P1)

**Goal**: Convert feature-level phase-3 SHAP values into six-category absolute and relative importance tables using the external crosswalk.

**Independent Test**: Use synthetic SHAP and crosswalk tables to verify six rows per scope-year, relative importance sums to 1.0 when nonzero, zero denominators produce six zeros and diagnostics, duplicate mappings fail, and explicit unmapped mode excludes unmapped importance with diagnostics.

### Tests for User Story 2

- [X] T032 [US2] Add unit test for crosswalk column auto-detection and explicit column selection in `tests/unit/test_forecasting_shap.py`
- [X] T033 [US2] Add unit test that crosswalk validation requires exactly six distinct display labels in `tests/unit/test_forecasting_shap.py`
- [X] T034 [US2] Add unit test that duplicate feature-to-multiple-group mappings fail before aggregation in `tests/unit/test_forecasting_shap.py`
- [X] T035 [US2] Add unit test that missing mappings fail by default in `tests/unit/test_forecasting_shap.py`
- [X] T036 [US2] Add unit test that allowed unmapped features are excluded from the denominator and diagnostics include mapped sum, unmapped sum, and unmapped share in `tests/unit/test_forecasting_shap.py`
- [X] T037 [US2] Add unit test that nonzero six-category relative importance sums to 1.0 within tolerance in `tests/unit/test_forecasting_shap.py`
- [X] T038 [US2] Add unit test that zero mapped denominator writes six `0` relative values and a diagnostic in `tests/unit/test_forecasting_shap.py`
- [X] T039 [US2] Add unit test that a complete long six-category table has exactly 96 rows for four scopes, four test years, and six feature groups in `tests/unit/test_forecasting_shap.py`

### Implementation for User Story 2

- [X] T040 [US2] Implement crosswalk loading with feature and category column detection/overrides in `src/ipcch/forecasting_shap.py`
- [X] T041 [US2] Implement crosswalk validation for exactly six labels, invalid categories, duplicate mappings, missing mappings, and documented alias or normalization metadata in `src/ipcch/forecasting_shap.py`
- [X] T042 [US2] Implement per-feature absolute SHAP summary with fields required by FR-010 and sample type from metadata in `src/ipcch/forecasting_shap.py`
- [X] T043 [US2] Implement six-category aggregation and relative-importance calculation with zero-denominator handling in `src/ipcch/forecasting_shap.py`
- [X] T044 [US2] Implement unmapped-feature diagnostics with mapped absolute sum, unmapped absolute sum, and unmapped absolute share per scope-year in `src/ipcch/forecasting_shap.py`
- [X] T045 [US2] Write per-feature summary, long six-category table, diagnostics, and metadata CSV/JSON outputs under phase-3 SHAP results directories, and update metadata artifact paths for the per-feature summary, long six-category table, diagnostics, and metadata JSON in `scripts/modeling/run_deep_feature_weight_decay_forecasting.py`
- [X] T046 [US2] Respect `--allow-unmapped-shap-features`, `--crosswalk-feature-column`, and `--crosswalk-category-column` in aggregation wiring in `scripts/modeling/run_deep_feature_weight_decay_forecasting.py`

**Checkpoint**: User Story 2 is fully functional and testable independently.

---

## Phase 5: User Story 3 - Generate phase-3 six-category heatmaps by forecasting scope (Priority: P2)

**Goal**: Produce one human-readable 6 x 4 heatmap and matrix table per forecasting scope using six-category relative importance.

**Independent Test**: Use a synthetic six-category relative-importance table for one or more scopes and verify each scope matrix has six rows, four test-year columns, preserved crosswalk labels, sample type in captions/tables, and no phase-4 or phase-5 visualizations.

### Tests for User Story 3

- [X] T047 [US3] Add unit test that a complete scope matrix has 6 x 4 shape and preserves crosswalk labels in `tests/unit/test_forecasting_shap.py`
- [X] T048 [US3] Add unit test that heatmap captions and matrix outputs include the SHAP explanation sample type in `tests/unit/test_forecasting_shap.py`
- [X] T049 [US3] Add unit test that no phase-4, phase-5, or combined phase-3/phase-4 artifact names are generated in `tests/unit/test_forecasting_shap.py`

### Implementation for User Story 3

- [X] T050 [US3] Implement scope matrix creation with six feature-group rows and exactly four annual test-year columns: 2022, 2023, 2024, and 2025 in `src/ipcch/forecasting_shap.py`
- [X] T051 [US3] Implement phase-3 heatmap rendering with relative-importance color intensity and unavailable/zero-denominator cell handling in `src/ipcch/forecasting_shap.py`
- [X] T052 [US3] Write one matrix table per scope with columns 2022, 2023, 2024, and 2025 under phase-3 SHAP report directories in `scripts/modeling/run_deep_feature_weight_decay_forecasting.py`
- [X] T053 [US3] Write one heatmap per scope with columns 2022, 2023, 2024, and 2025 under phase-3 SHAP report directories with deterministic phase-3 filenames in `scripts/modeling/run_deep_feature_weight_decay_forecasting.py`
- [X] T054 [US3] Add report summary text listing target `phase3_worse`, sample type, crosswalk source, and four scope heatmap paths in `scripts/modeling/run_deep_feature_weight_decay_forecasting.py`

**Checkpoint**: User Story 3 is fully functional and testable independently.

---

## Phase 6: User Story 4 - Keep the workflow reproducible and path-agnostic (Priority: P3)

**Goal**: Ensure collaborators can run the feature without editing source paths and that outputs respect overwrite and artifact-separation rules.

**Independent Test**: Invoke CLI help and dry-run/default-disabled paths from the repository root; verify user-facing controls exist, explicit crosswalk paths and configured keys work, no local absolute defaults are embedded, and overwrite conflicts fail clearly.

### Tests for User Story 4

- [X] T055 [US4] Add smoke test for explicit `--variable-crosswalk-path` path selection using a temporary crosswalk in `tests/smoke/test_weight_decay_shap_cli.py`
- [X] T056 [US4] Add smoke test for documented crosswalk external-path key visibility and absence of hardcoded local absolute paths in CLI help in `tests/smoke/test_weight_decay_shap_cli.py`
- [X] T057 [US4] Add unit or smoke test that SHAP output overwrite conflicts fail when `--overwrite` is omitted in `tests/smoke/test_weight_decay_shap_cli.py`
- [X] T058 [US4] Add smoke test for raw row-level SHAP export size guard in `tests/smoke/test_weight_decay_shap_cli.py`: raw export is disabled by default, oversized raw export is refused without `--allow-large-raw-shap` or an explicit maximum-row limit, and export succeeds only with documented `--raw-shap-max-rows` or `--allow-large-raw-shap` behavior

### Implementation for User Story 4

- [X] T059 [US4] Verify `configs/paths.example.json` documents the `six_category_feature_crosswalk` key with a non-local placeholder path and matching instructions in `specs/006-phase3-shap-importance/quickstart.md`
- [X] T060 [US4] Ensure explicit crosswalk path overrides external-path key resolution in `scripts/modeling/run_deep_feature_weight_decay_forecasting.py`
- [X] T061 [US4] Extend overwrite checks to include planned SHAP result and report artifacts in `src/ipcch/forecasting_weight_decay.py`
- [X] T062 [US4] Ensure metadata records crosswalk source as an explicit path or external path key, unmapped-feature count, mapped absolute SHAP sum, unmapped absolute SHAP sum, unmapped absolute SHAP share where applicable, and final artifact paths for per-feature summary, long six-category table, matrix tables, heatmaps, diagnostics, raw SHAP outputs when enabled, and metadata JSON without hardcoded local defaults in `scripts/modeling/run_deep_feature_weight_decay_forecasting.py`
- [X] T063 [US4] Implement raw row-level SHAP export opt-in, maximum-row guard, and large-output override behavior in `src/ipcch/forecasting_shap.py`
- [X] T064 [US4] Wire `--save-raw-shap`, `--raw-shap-max-rows`, and `--allow-large-raw-shap` to raw export behavior in `scripts/modeling/run_deep_feature_weight_decay_forecasting.py`

**Checkpoint**: User Story 4 is fully functional and testable independently.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Validate the full feature and clean up integration points.

- [ ] T065 [P] Run `PYTHONPATH=src pytest tests/unit/test_forecasting_shap.py` and fix failures in `src/ipcch/forecasting_shap.py`
- [ ] T066 [P] Run `PYTHONPATH=src pytest tests/smoke/test_weight_decay_shap_cli.py` and fix failures in `scripts/modeling/run_deep_feature_weight_decay_forecasting.py`
- [X] T067 Run `PYTHONPATH=src python scripts/modeling/run_deep_feature_weight_decay_forecasting.py --help` and confirm all SHAP controls are visible without local absolute paths
- [X] T068 Run a dry-run default-disabled validation with `PYTHONPATH=src python scripts/modeling/run_deep_feature_weight_decay_forecasting.py --fs fs3 --sample-rows 50 --dry-run` and confirm existing behavior remains unchanged
- [X] T069 Review generated code for no classifier workflow, no phase-4/phase-5 SHAP visualization, no threshold/metric changes, no hardcoded absolute paths, SHAP capture uses the existing annual holdout split objects, no future/test-window data enters training, preprocessing, weighting, or metric generation, and enabling SHAP does not alter predictions or metrics in `src/ipcch/forecasting_shap.py` and `scripts/modeling/run_deep_feature_weight_decay_forecasting.py`
- [X] T070 Update `specs/006-phase3-shap-importance/quickstart.md` if final CLI option names or artifact filenames differ from the contract

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately.
- **Foundational (Phase 2)**: Depends on Setup completion - blocks all user stories.
- **User Story 1 (Phase 3)**: Depends on Foundational; MVP for phase-3 SHAP recording.
- **User Story 2 (Phase 4)**: Depends on Foundational and the SHAP value summary shape from US1.
- **User Story 3 (Phase 5)**: Depends on six-category relative-importance outputs from US2.
- **User Story 4 (Phase 6)**: Depends on Foundational; can proceed partly in parallel with US1-US3, but final overwrite/raw-output integration depends on SHAP artifact planning.
- **Polish (Phase 7)**: Depends on desired user stories being complete.

### User Story Dependencies

- **US1 (P1)**: No dependency on other stories after Foundational.
- **US2 (P1)**: Requires SHAP per-feature value inputs; synthetic tests can start after Foundational, production wiring follows US1.
- **US3 (P2)**: Requires US2 relative-importance tables.
- **US4 (P3)**: Mostly independent after Foundational; final validation depends on all output paths being known.

### Within Each User Story

- Tests first, then helper implementation, then CLI wiring, then story checkpoint validation.
- Shared helper changes in `src/ipcch/forecasting_shap.py` precede CLI orchestration in `scripts/modeling/run_deep_feature_weight_decay_forecasting.py`.
- Output planning in `src/ipcch/forecasting_weight_decay.py` precedes overwrite and artifact writing integration.

## Parallel Opportunities

- T012, T013, and T014 can run in parallel after T004, T005, and T010 because they touch separate files: smoke tests, unit tests, and `pyproject.toml`.
- US1 unit tests in `tests/unit/test_forecasting_shap.py` should be done sequentially with each other, and US1 smoke tests in `tests/smoke/test_weight_decay_shap_cli.py` should be done sequentially with each other.
- US2 tests T032-T039 should be done sequentially because they all edit `tests/unit/test_forecasting_shap.py`.
- US3 tests T047-T049 should be done sequentially because they all edit `tests/unit/test_forecasting_shap.py`.
- US4 tests T055-T058 should be done sequentially because they all edit `tests/smoke/test_weight_decay_shap_cli.py`.
- Polish validation T065 and T066 can run in parallel after implementation because they execute separate validation paths/test files.

## Parallel Example: User Story 1

```bash
# These two workstreams can proceed in parallel because they edit different files:
Task: "T017-T018 and T022 add US1 unit tests sequentially in tests/unit/test_forecasting_shap.py"
Task: "T019-T021 add US1 smoke tests sequentially in tests/smoke/test_weight_decay_shap_cli.py"
```

## Parallel Example: User Story 2

```bash
# US2 test tasks all edit the same unit test file and should be performed sequentially:
Task: "T032-T039 add crosswalk and aggregation unit tests sequentially in tests/unit/test_forecasting_shap.py"
```

## Parallel Example: User Story 3

```bash
# US3 test tasks all edit the same unit test file and should be performed sequentially:
Task: "T047-T049 add matrix, caption, and artifact-name tests sequentially in tests/unit/test_forecasting_shap.py"
```

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 setup.
2. Complete Phase 2 foundation.
3. Complete Phase 3 User Story 1.
4. Stop and validate phase-3-only SHAP recording independently.
5. Confirm SHAP-disabled behavior remains unchanged.

### Incremental Delivery

1. Setup + Foundational → CLI and helper skeleton ready.
2. US1 → phase-3 SHAP values can be recorded.
3. US2 → SHAP values become six-category relative-importance tables.
4. US3 → tables become scope heatmaps and report artifacts.
5. US4 → reproducibility, path handling, overwrite, and raw-output guards complete.

### Validation Discipline

- Do not run heavy full training during automated validation.
- Prefer unit tests with synthetic SHAP/crosswalk tables.
- Use CLI `--help`, dry-run, and tiny smoke tests for integration validation.
- Keep final implementation phase-3-only and cumulative-regressor-only.
