# Feature Specification: Phase-3 SHAP Six-Category Feature Importance

**Feature Branch**: `006-phase3-shap-importance`  
**Created**: 2026-05-31  
**Status**: Draft  
**Input**: User description: "Add post-hoc SHAP explainability artifacts to the existing IPCCH forecasting weight-decay pipeline, focused only on phase-3-or-higher cumulative regressor outputs, aggregated into six crosswalk-driven feature categories and visualized as one 6 x 4 heatmap per forecasting scope."

## Clarifications

### Session 2026-05-31

- Q: If a user explicitly enables the “allow unmapped features” option, how should the pipeline treat model features that are missing from the six-category crosswalk when computing phase-3 relative feature-group importance? → A: Exclude unmapped features from the six-category aggregation denominator, write their names and total absolute importance to diagnostics, and compute relative importance only over mapped features.
- Q: When phase-3 explanation recording is requested but the required explanation engine/package is unavailable or incompatible with the fitted model, should the forecasting pipeline fail the run or continue predictions while marking SHAP artifacts as unavailable? → A: Fail the run with a clear diagnostic when explanation recording is enabled but the explanation engine is unavailable or incompatible.
- Q: When phase-3 explanation recording is enabled and the user does not explicitly choose an explanation sample, which rows should be explained by default for each forecasting scope and annual split? → A: Explain the phase-3 training feature matrix for each scope-year split by default.
- Q: If the user enables raw row-level SHAP export and the resulting output would be very large, what should the workflow do by default to prevent accidental oversized artifacts? → A: Refuse oversized raw exports by default unless the user sets an explicit size override or maximum-row limit.
- Q: If all mapped phase-3 absolute SHAP values are zero for a forecasting scope and test year, so the six-category relative-importance denominator is zero, what should the output table and heatmap show for that scope-year? → A: Write `0` for all six relative-importance values and record a zero-denominator diagnostic.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Record phase-3 SHAP explanations during forecasting runs (Priority: P1)

As a researcher running the forecasting weight-decay pipeline, I want to optionally record explanation values for the trained phase-3-or-higher model so that I can inspect which model features drive phase-3-or-higher risk forecasts without changing the forecasting workflow itself.

**Why this priority**: This is the core capability. Without reliable phase-3 explanation extraction from the existing cumulative-regressor workflow, downstream six-category summaries and heatmaps cannot be produced.

**Independent Test**: Run the forecasting workflow on a tiny smoke-test dataset or equivalent lightweight validation path with explanation recording enabled for one forecasting scope and one annual split. Verify that phase-3 explanation artifacts are produced and that the ordinary prediction, metric, and diagnostic outputs remain present.

**Acceptance Scenarios**:

1. **Given** explanation recording is enabled, **When** the forecasting workflow completes the phase-3-or-higher model for a supported scope and test year, **Then** it records phase-3 explanation values for the selected explanation rows, using the phase-3 training feature matrix by default.
2. **Given** explanation recording is disabled, **When** the forecasting workflow runs normally, **Then** existing prediction, metric, metadata, and report behavior remains unchanged.
3. **Given** a scope-year split has no eligible phase-3 training or explanation rows, **When** explanation recording is enabled, **Then** the system records a diagnostic status for that split rather than silently omitting it.

---

### User Story 2 - Aggregate explanations into six feature categories (Priority: P1)

As a researcher comparing thematic feature families, I want feature-level phase-3 explanation values aggregated into six feature categories so that importance can be interpreted at the food prices, geography, econ, conflict, agriculture, and weather levels rather than as hundreds of individual variables.

**Why this priority**: The requested analytical deliverable is six-category relative importance. The aggregation step makes raw explanation values interpretable and reusable for tables and figures.

**Independent Test**: Use a small synthetic explanation table and a small synthetic crosswalk containing the six expected categories. Verify that the grouped output contains six rows per forecasting scope and test year, and that relative importance sums to 1.0 within each complete scope-year group.

**Acceptance Scenarios**:

1. **Given** every model feature has exactly one crosswalk category, **When** aggregation runs, **Then** the system sums absolute explanation values by category and normalizes the six category totals within each forecasting scope and test year.
2. **Given** a model feature is missing from the crosswalk, **When** aggregation runs, **Then** the system writes an unmapped-feature diagnostic and fails by default unless the user explicitly allows unmapped features; if unmapped features are explicitly allowed, their importance is excluded from the six-category denominator and reported in diagnostics.
3. **Given** a crosswalk feature maps to multiple categories, **When** validation runs, **Then** the system raises a clear duplicate-mapping error before producing final relative-importance outputs.

---

### User Story 3 - Generate phase-3 six-category heatmaps by forecasting scope (Priority: P2)

As a researcher preparing manuscript or project outputs, I want one heatmap per forecasting scope showing six feature groups across the four annual test years so that I can visually compare how group importance changes across time.

**Why this priority**: The heatmap is the main human-readable deliverable, but it depends on reliable phase-3 explanation recording and six-category aggregation.

**Independent Test**: Use a six-category relative-importance table with four test years for one forecasting scope. Verify that the generated heatmap has six category rows, four annual test-year columns, and marks unavailable scope-year cells consistently when data are missing.

**Acceptance Scenarios**:

1. **Given** valid six-category relative-importance data for `fs0`, `fs1`, `fs2`, and `fs3`, **When** visualization runs, **Then** four separate phase-3 heatmap artifacts are created.
2. **Given** a scope-year has unavailable explanation values, **When** visualization runs, **Then** the corresponding heatmap cell is marked consistently and a diagnostic is recorded.
3. **Given** phase-4 or phase-5 explanation data exist in reference material or prior outputs, **When** this feature runs, **Then** no phase-4, phase-5, or combined phase-3/phase-4 visualization is generated.

---

### User Story 4 - Keep the workflow reproducible and path-agnostic (Priority: P3)

As a collaborator using a different machine, I want the feature to run without editing source code paths so that the explanation workflow remains reproducible across Windows, WSL, and shared repository setups.

**Why this priority**: The workflow must not depend on a single local Dropbox path or machine-specific source code edit, especially because the crosswalk and source data live outside the repository.

**Independent Test**: Invoke the forecasting workflow's help or dry-run capability from the repository root. Verify that explanation and crosswalk options are discoverable, that a user-provided crosswalk can be selected, and that no local absolute path appears as a source-code default.

**Acceptance Scenarios**:

1. **Given** a user provides a crosswalk path, **When** six-category aggregation runs, **Then** the system uses that crosswalk for feature grouping.
2. **Given** no explicit crosswalk path is provided but a documented external-path key is configured, **When** six-category aggregation runs, **Then** the system resolves the crosswalk through the configured project path mechanism.
3. **Given** output artifacts already exist and overwrite is not permitted, **When** the feature attempts to write outputs, **Then** it fails with a clear message instead of silently replacing artifacts.

---

### Edge Cases

- The crosswalk path is missing, cannot be resolved, or points to an unreadable file.
- The crosswalk exists but lacks a detectable feature-name column or category column.
- A model feature used for phase-3 explanation is absent from the crosswalk.
- A crosswalk feature maps to more than one of the six feature categories.
- The crosswalk contains category labels outside the expected six groups.
- A forecasting scope and annual split has no eligible phase-3 training rows or explanation rows.
- All mapped explanation values are zero for a complete scope-year, producing a zero normalization denominator; the output records `0` for all six relative-importance values and writes a diagnostic.
- The explanation engine is unavailable or incompatible with the fitted phase-3 model; if explanation recording is enabled, the run fails with a clear diagnostic.
- Raw row-level explanation output would be large enough to require an explicit opt-in and an explicit size override or maximum-row limit before oversized artifacts are written.
- Output files already exist and overwrite is not permitted.
- Feature names in the trained model and explanation matrix do not match.
- Target-related, prediction, or diagnostic columns accidentally appear among explanation input features; these must remain excluded.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide an optional phase-3 explanation recording mode for the existing forecasting weight-decay workflow.
- **FR-002**: The system MUST preserve default forecasting behavior when explanation recording is disabled, including existing training, prediction, metrics, target derivation, sample weighting, split rules, and reports.
- **FR-003**: The system MUST support explanation recording and aggregation for all four forecasting scopes: `fs0`, `fs1`, `fs2`, and `fs3`.
- **FR-004**: The system MUST focus all explanation outputs on the phase-3-or-higher cumulative target only.
- **FR-005**: The system MUST preserve the annual holdout rule: training observations are strictly before the test year and test observations are in the test calendar year.
- **FR-006**: The system MUST preserve the requested annual test years: 2022, 2023, 2024, and 2025.
- **FR-007**: The system MUST compute explanation values only after the phase-3 model has been fitted and its ordinary predictions and metrics can be produced.
- **FR-007a**: When explanation recording is enabled and the user does not select an explanation sample, the system MUST explain the phase-3 training feature matrix for each forecasting scope and annual split by default.
- **FR-008**: The system MUST NOT use explanation values to influence model fitting, feature selection, thresholding, weighting, tuning, model selection, or reported predictive metrics.
- **FR-009**: The system MUST write machine-readable phase-3 explanation artifacts in a separated results location for the forecasting weight-decay workflow.
- **FR-010**: The system MUST write a per-feature explanation summary table with at least: forecasting scope, scope label, test year, target, feature name, absolute explanation sum, mean absolute explanation value, number of explanation rows, and feature group.
- **FR-011**: The system SHOULD support raw row-level explanation export only behind an explicit user opt-in.
- **FR-011a**: When raw row-level explanation export is requested and the output would exceed the default size guard, the system MUST refuse the oversized export unless the user provides an explicit size override or maximum-row limit.
- **FR-012**: The system MUST load the six-category feature crosswalk from a user-provided path or documented project path configuration, not from a hardcoded local absolute path.
- **FR-013**: The system MUST validate the crosswalk before producing final aggregate outputs.
- **FR-014**: Crosswalk validation MUST confirm that every model feature used in phase-3 explanation aggregation maps to exactly one of the six feature categories unless the user explicitly allows unmapped features.
- **FR-014a**: When unmapped features are explicitly allowed, the system MUST exclude their absolute explanation values from the six-category relative-importance denominator and MUST report their names and total absolute importance in diagnostics.
- **FR-015**: The system MUST allow the feature-name and category columns in the crosswalk to be detected from clear column names or selected by the user.
- **FR-016**: The system MUST aggregate feature-level importance by summing absolute explanation values across explanation rows and features within each feature group.
- **FR-017**: The system MUST compute relative importance within each forecasting scope and test year as each feature group's absolute importance divided by the total absolute importance across the six groups.
- **FR-017a**: When the mapped absolute-importance denominator is zero for a forecasting scope and test year, the system MUST write `0` for all six relative-importance values and MUST record a zero-denominator diagnostic.
- **FR-018**: The system MUST write a long six-category relative-importance table with one row per forecasting scope, test year, and feature group when all data are available.
- **FR-019**: The complete long six-category table MUST contain 96 rows when all four scopes, four test years, and six feature groups are available.
- **FR-020**: The system MUST write one matrix table per forecasting scope with six feature-group rows and four annual test-year columns.
- **FR-021**: The system MUST generate one phase-3 heatmap for each forecasting scope: `fs0`, `fs1`, `fs2`, and `fs3`.
- **FR-022**: Each heatmap MUST be a 6 x 4 grid with six feature-group rows and four annual test-year columns.
- **FR-023**: Heatmap cell color intensity MUST represent relative feature-group importance.
- **FR-024**: The system MUST save human-readable phase-3 heatmaps and summary tables in a separated reports location for the forecasting weight-decay workflow.
- **FR-025**: The system MUST NOT generate phase-4, phase-5, or combined phase-3/phase-4 explanation visualizations as part of this feature.
- **FR-026**: The system MUST write run metadata documenting target, scopes, test years, split rule, explanation sample type, crosswalk source, feature count, unmapped-feature count, and explanation package/version when available.
- **FR-027**: The system MUST write diagnostics for missing mappings, duplicate mappings, invalid category labels, zero normalization denominators, unavailable scope-year splits, skipped explanation calculations, explanation-engine unavailability or incompatibility, and overwrite conflicts.
- **FR-027a**: When explanation recording is enabled and the explanation engine is unavailable or incompatible with the fitted phase-3 model, the system MUST fail the run with a clear diagnostic rather than silently skipping requested explanation outputs.
- **FR-028**: The system MUST expose discoverable user-facing controls for enabling phase-3 explanations, selecting the crosswalk, selecting crosswalk columns, selecting explanation sample type if supported, opting into raw outputs, allowing unmapped features, and overwrite behavior.
- **FR-029**: The system MUST keep generated machine-readable outputs under project results areas and human-readable figures and tables under project reports areas.
- **FR-030**: The system MUST support lightweight validation without heavy full model training, including synthetic aggregation checks, visualization-shape checks, path-configuration checks, and default-disabled behavior checks.
- **FR-031**: The system MUST compute explanation values for the fitted phase-3-or-higher regressor only; it MUST NOT explain final predicted phase labels, phase-2, phase-4, or phase-5 models as part of this feature.
- **FR-032**: The explanation feature matrix MUST use exactly the feature columns, order, and preprocessing state used by the fitted phase-3 model for that forecasting scope and annual split.
- **FR-033**: Heatmap captions, matrix tables, and metadata MUST state the explanation sample type, especially whether values are computed on training rows or test rows.
- **FR-034**: The crosswalk MUST define exactly six distinct feature-group labels. Outputs MUST preserve crosswalk labels for display; if canonical category validation uses aliases or normalization rules, those rules MUST be documented.
- **FR-035**: When unmapped features are explicitly allowed, diagnostics MUST report mapped absolute explanation sum, unmapped absolute explanation sum, and unmapped absolute explanation share for each forecasting scope and test year.
- **FR-036**: Phase-3 explanation output filenames SHOULD be deterministic and include target, forecasting scope where applicable, and artifact type.

### Key Entities *(include if feature involves data)*

- **Forecasting Scope**: One of `fs0`, `fs1`, `fs2`, or `fs3`; identifies the forecasting horizon or feature-scope variant being explained.
- **Annual Split**: One test year among 2022, 2023, 2024, and 2025, with training observations limited to prior years and test observations limited to the calendar year.
- **Phase-3 Model**: The fitted cumulative forecasting model whose target represents phase-3-or-higher risk.
- **Explanation Value Record**: A value associated with one feature, one explanation row, one forecasting scope, one test year, and the phase-3 target.
- **Feature Crosswalk**: A table mapping each model feature name to exactly one of six categories: food prices, geography, econ, conflict, agriculture, or weather.
- **Feature Group Importance**: The aggregate absolute explanation value for one feature group within one forecasting scope and test year.
- **Relative Feature Group Importance**: A feature group's importance divided by the total importance of all six groups within the same forecasting scope and test year.
- **Heatmap Artifact**: A human-readable figure for one forecasting scope with six feature groups as rows and four annual test years as columns.
- **Diagnostic Record**: A machine-readable record describing validation failures, skipped scope-years, missing mappings, zero denominators, or unavailable explanation calculations.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: With explanations enabled and valid data for all scopes and years, researchers receive a six-category relative-importance table containing exactly 96 rows: four scopes times four test years times six feature groups.
- **SC-002**: For every complete forecasting scope and test year with nonzero mapped absolute importance, the six relative-importance values sum to 1.0 within a tolerance of 0.000001; zero-denominator scope-years contain six `0` values and a diagnostic.
- **SC-003**: Researchers receive four phase-3 heatmap artifacts, one each for `fs0`, `fs1`, `fs2`, and `fs3`.
- **SC-004**: Each heatmap contains exactly six category rows and four annual test-year columns.
- **SC-005**: The feature produces zero phase-4, phase-5, or combined phase-3/phase-4 heatmap artifacts.
- **SC-006**: When explanation recording is disabled, existing forecasting prediction and metric outputs are unchanged relative to a run with the same inputs and settings.
- **SC-007**: A collaborator can discover the explanation and crosswalk controls from the workflow help or equivalent user-facing documentation without editing source code.
- **SC-008**: Crosswalk validation catches missing model-feature mappings and duplicate feature-category mappings before final relative-importance outputs are produced.
- **SC-009**: Automated validation can complete using lightweight checks only and does not require a full production forecasting run.

## Assumptions

- This feature extends the canonical cumulative-regressor forecasting workflow and does not introduce any classifier workflow.
- The only target explained by this feature is the phase-3-or-higher cumulative target.
- The six feature groups are food prices, geography, econ, conflict, agriculture, and weather, with category labels supplied by the crosswalk as the source of truth.
- The single-scope heatmaps always use annual test years 2022, 2023, 2024, and 2025 as the four columns.
- Absolute explanation values are used for feature importance to avoid signed cancellation.
- If explanation downsampling is supported, it is deterministic and recorded in run metadata.
- The default explanation sample is the phase-3 training feature matrix for each forecasting scope and annual split unless the user selects another supported sample type.
- Raw row-level explanation values may be large and therefore require explicit user opt-in plus an explicit size override or maximum-row limit when the default size guard would be exceeded.
- Existing target-related, prediction, and diagnostic columns remain excluded from model feature inputs and explanation inputs.
- The crosswalk file is an external project input and must be selected through user-facing configuration rather than embedded as a local absolute path.
