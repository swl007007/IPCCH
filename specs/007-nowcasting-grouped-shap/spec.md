# Feature Specification: Nowcasting Grouped SHAP Values

**Feature Branch**: `[007-nowcasting-grouped-shap]`  
**Created**: 2026-06-03  
**Status**: Draft  
**Input**: User description: "Add a grouped SHAP value CLI option to the IPCCH nowcasting workflow, using the existing forecasting SHAP implementation as reference, adapting six-category variable grouping to nowcasting features, adding a seventh weather forecast category, and updating grouped SHAP heatmap output to forecasting-scope-by-group."

## Clarifications

### Session 2026-06-03

- Q: Should supplied-model Mode 2 support grouped SHAP in this feature? → A: Mode 2 rejected for now; only Mode 1 is supported.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Enable grouped SHAP for nowcasting (Priority: P1)

As a researcher running the IPCCH nowcasting workflow, I want to activate grouped SHAP value computation with an explicit command option so that I can generate group-level feature attribution outputs without changing the default nowcasting run.

**Why this priority**: This is the minimum useful capability. The interpretability workflow must be optional so routine nowcasting runs remain unchanged.

**Independent Test**: Run the nowcasting workflow with and without grouped SHAP enabled and verify that grouped SHAP outputs are produced only for the enabled run.

**Acceptance Scenarios**:

1. **Given** the current nowcasting workflow, **When** the user runs it without grouped SHAP enabled, **Then** the workflow completes with its existing outputs and no grouped SHAP outputs.
2. **Given** the current nowcasting workflow, **When** the user runs it with grouped SHAP enabled, **Then** the workflow computes grouped SHAP values from the fitted `phase3_worse` model's training feature matrix and writes grouped SHAP outputs.
3. **Given** the workflow help text, **When** the user checks available options, **Then** the grouped SHAP option is visible and described clearly.

---

### User Story 2 - Group nowcasting features consistently (Priority: P1)

As a researcher interpreting nowcasting models, I want every nowcasting training feature to be mapped into transparent feature groups so that grouped SHAP results can be compared with the existing six-category forecasting interpretation while separately identifying runtime weather forecast features.

**Why this priority**: Grouped SHAP values are only useful if feature grouping is complete, auditable, and semantically consistent.

**Independent Test**: Apply the mapping workflow to the nowcasting training features and inspect the saved mapping and diagnostics.

**Acceptance Scenarios**:

1. **Given** the nowcasting training feature list, **When** grouped SHAP is enabled, **Then** every training feature appears in the feature-to-group mapping output.
2. **Given** a feature that directly matches the six-category reference crosswalk, **When** mapping is performed, **Then** the feature is assigned to the matching reference category.
3. **Given** a lagged, current-period, or otherwise renamed nowcasting feature that does not directly match the reference crosswalk, **When** mapping is performed, **Then** normalized or base-variable matching is attempted and the match method is recorded.
4. **Given** target-month or lagged-target-month rainfall or temperature forecast features generated for nowcasting, **When** mapping is performed, **Then** those features are assigned to the `weather forecast` group before crosswalk matching is attempted.
5. **Given** a feature that cannot be confidently matched, **When** mapping is performed, **Then** the feature is explicitly reported in the mapping diagnostics and its attribution coverage is reported when SHAP values are available.

---

### User Story 3 - Explain the training feature matrix (Priority: P1)

As a model developer, I want grouped SHAP values to be computed on the exact training feature matrix used by the fitted `phase3_worse` nowcasting model so that the attribution results explain the model as trained rather than prediction-only or evaluation-only data.

**Why this priority**: The requested interpretation is invalid if computed on the wrong target model, wrong rows, or a different feature order.

**Independent Test**: Compare the grouped SHAP input matrix metadata with the fitted `phase3_worse` model feature list and the training rows used for that target.

**Acceptance Scenarios**:

1. **Given** a fitted nowcasting model, **When** grouped SHAP is computed, **Then** the SHAP input rows come from the corresponding `phase3_worse` model training data.
2. **Given** the fitted model’s feature order, **When** SHAP values are computed, **Then** the SHAP input feature order matches the training feature order exactly.
3. **Given** grouped SHAP outputs, **When** the grouped matrix is inspected, **Then** the grouped values aggregate from training-data feature attributions for `phase3_worse` only.

---

### User Story 4 - Compare grouped importance across forecasting scopes (Priority: P2)

As a researcher comparing nowcasting interpretability across horizons, I want a heatmap with feature groups on the y-axis and forecasting scopes on the x-axis so that I can compare group-level importance across `0m`, `3m`, `6m`, and `12m`.

**Why this priority**: The visualization is the primary human-readable interpretability deliverable, but it depends on correct SHAP computation and grouping.

**Independent Test**: Generate grouped SHAP outputs for available scopes and verify that the saved heatmap uses feature groups as rows and forecasting scopes as columns.

**Acceptance Scenarios**:

1. **Given** grouped SHAP results, **When** the heatmap is generated, **Then** its y-axis includes the six reference categories plus `weather forecast` when those groups are present or expected for the run.
2. **Given** grouped SHAP results for one or more forecasting scopes, **When** the heatmap is generated, **Then** its x-axis includes the available scopes among `0m`, `3m`, `6m`, and `12m` in that order.
3. **Given** all four scope results are available, **When** the workflow or companion helper generates the combined heatmap, **Then** the heatmap includes columns for `0m`, `3m`, `6m`, and `12m`.

---

### User Story 5 - Review grouping diagnostics and output locations (Priority: P2)

As a developer or researcher reviewing the grouped SHAP workflow, I want saved diagnostics and clear run messages so that I can verify matching quality, unmatched features, attribution coverage, and generated artifact locations.

**Why this priority**: Nowcasting feature names may differ from the reference crosswalk; transparent diagnostics prevent silent attribution errors.

**Independent Test**: Run the workflow with grouped SHAP enabled and review console messages plus saved diagnostic outputs.

**Acceptance Scenarios**:

1. **Given** grouped SHAP is enabled, **When** feature mapping completes, **Then** the run reports how many features matched the six-category reference groups.
2. **Given** grouped SHAP is enabled, **When** weather forecast features are identified, **Then** the run reports how many features were assigned to `weather forecast`.
3. **Given** unmatched features exist, **When** mapping completes, **Then** the run reports the unmatched count and writes explicit unmatched-feature diagnostics.
4. **Given** SHAP values are available for unmatched features, **When** diagnostics are written, **Then** the run reports their total absolute SHAP contribution or share.
5. **Given** grouped SHAP outputs are written, **When** the workflow finishes, **Then** the run reports the paths for the grouped SHAP matrix, feature-to-group mapping, unmatched diagnostics when present, metadata, and heatmap.

### Edge Cases

- No target-month or lagged-target-month rainfall or temperature forecast features are present; the mapping remains valid and reports zero `weather forecast` features.
- A nowcasting feature has multiple plausible normalized matches in the reference crosswalk; the feature is treated as unresolved and reported rather than assigned ambiguously.
- A feature name contains rainfall or temperature terms but is not clearly a runtime weather forecast feature; the feature is not assigned to `weather forecast` unless it matches the conservative runtime forecast-feature definition.
- The reference crosswalk is missing, malformed, or lacks usable feature/category columns; grouped SHAP fails with a clear actionable error while the default non-grouped workflow remains unaffected.
- Training features are not present in the reference crosswalk and are not identifiable as weather forecast features; they appear in diagnostics and are not silently dropped from grouping evidence.
- Only some forecasting scopes among `0m`, `3m`, `6m`, and `12m` are available; the heatmap is generated for available scopes in the expected order.
- Grouped SHAP is requested for a supplied-model run; the run rejects the request with a clear actionable error because supplied-model compatibility is out of scope for this feature.
- Grouped SHAP is requested for a prediction-only run; the run rejects the request with a clear actionable error because it lacks model and training-matrix context.
- Grouped SHAP computation fails for the fitted model; the run surfaces a clear error and does not produce partial outputs that appear complete.
- A group has zero assigned features or zero grouped attribution; the matrix and heatmap still include the group with zero values when the group is part of the expected seven-group set.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide an explicit user-facing command option named `--compute-grouped-shap` that enables grouped SHAP computation for the nowcasting workflow.
- **FR-002**: System MUST expose `--compute-grouped-shap` through `scripts/modeling/run_launch_nowcasting_2026_04.py` and propagate the parsed option into grouped SHAP support code in `src/ipcch/launch_nowcasting.py`.
- **FR-003**: System MUST preserve existing nowcasting behavior and output set when grouped SHAP is not enabled.
- **FR-004**: System MUST align grouped SHAP calculations, aggregation semantics, output naming, and visualization style with the existing forecasting grouped SHAP workflow where applicable.
- **FR-005**: System SHOULD reuse or adapt existing grouped SHAP behavior rather than creating a separate inconsistent interpretation workflow.
- **FR-006**: System MUST explain the fitted `phase3_worse` nowcasting model only; grouped SHAP MUST NOT be broadened to all cumulative targets unless a future requirement explicitly asks for that.
- **FR-007**: System MUST compute grouped SHAP values using the exact `phase3_worse` training feature matrix, not April prediction rows, validation rows, test rows, or prediction-only rows.
- **FR-008**: System MUST use training rows equivalent to `train_featured.dropna(subset=["phase3_worse"]).loc[:, feature_columns]` for grouped SHAP input.
- **FR-009**: System MUST preserve the fitted model’s training feature ordering exactly by requiring grouped SHAP matrix columns to match `feature_columns` in fitted-model order.
- **FR-010**: System MUST use the project’s six-category variable crosswalk as the reference grouping system for non-weather-forecast features.
- **FR-011**: System MUST support an explicit user-provided crosswalk path override for the relevant six-category crosswalk file, including the user-provided file at `C:\Users\swl00\IFPRI Dropbox\Weilun Shi\Google fund\Analysis\1.Source Data\assembled_IPCCH\metadata\forecasting_2026_model_ready_variable_six_category_crosswalk.csv`.
- **FR-012**: System MUST prefer existing project path mechanisms such as configured external path keys for default crosswalk resolution and MUST NOT hardcode a local Windows absolute path as the only production default.
- **FR-013**: System MUST treat the six-category crosswalk as a reference mapping and not require exact one-to-one feature-name matches for all nowcasting features.
- **FR-014**: System MUST attempt exact feature matching first, then transparent normalized or base-variable matching for lagged, current-period, or otherwise renamed nowcasting features.
- **FR-014A**: System MUST make normalized/base-variable matching deterministic by applying a documented normalization sequence. The sequence MUST preserve the original feature name in diagnostics and SHOULD include: lowercasing; stripping known lag/current/scope tokens only when they are structural suffixes or prefixes; stripping nowcasting runtime suffixes such as forecast-proxy suffixes only after weather-forecast seed matching has already been applied; comparing against normalized crosswalk `variable` values; and leaving features unresolved when normalization produces zero matches or multiple plausible matches.
- **FR-015**: System MUST include a seventh grouped SHAP category named exactly `weather forecast`.
- **FR-016**: System MUST identify runtime weather forecast features before six-category crosswalk matching and make `weather forecast` assignment take precedence over crosswalk assignment.
- **FR-017**: System MUST assign target-month and lagged-target-month rainfall and temperature forecast proxy features generated for nowcasting to exactly `weather forecast`.
- **FR-018**: System MUST use existing nowcasting weather proxy feature definitions as authoritative seeds for weather-forecast grouping where available.
- **FR-019**: System MUST NOT automatically assign ambiguous rainfall or temperature features to `weather forecast` unless they match the conservative runtime forecast-feature definition.
- **FR-020**: System MUST prevent runtime weather forecast features from being assigned to the original six reference categories.
- **FR-021**: System MUST explicitly handle unmatched features by writing them to diagnostics rather than silently dropping them from grouping evidence.
- **FR-022**: System MUST keep unmatched features diagnostics-only and MUST NOT assign them to an `other` fallback group unless a future requirement explicitly changes this.
- **FR-023**: System MUST report attribution coverage, including unmatched feature count and, when SHAP values are available, unmatched features' total absolute SHAP contribution or share.
- **FR-024**: System MUST save grouped SHAP matrix outputs based on training-data attributions for the available forecasting scope or scopes.
- **FR-025**: System MUST save the feature-to-group mapping used for the run, including each training feature, assigned group if any, match method, matched reference variable when available, and unmatched status.
- **FR-026**: System MUST save unmatched-feature diagnostics when one or more training features cannot be confidently assigned.
- **FR-027**: System MUST document the grouped SHAP aggregation metric in metadata and use the same absolute-SHAP group importance convention as the existing forecasting grouped SHAP workflow where applicable.
- **FR-028**: System MUST generate a grouped SHAP heatmap with feature groups on the y-axis and forecasting scopes on the x-axis.
- **FR-029**: System MUST include the six reference categories plus `weather forecast` in grouped SHAP outputs, using zero values where an expected group has no assigned features or no attribution.
- **FR-030**: System MUST show forecasting scopes among `0m`, `3m`, `6m`, and `12m` in that order when those scope results are available.
- **FR-031**: System MUST allow each single-scope nowcasting run to write grouped SHAP outputs for that scope while using an output schema that can be combined into a scope-by-group matrix ordered `0m`, `3m`, `6m`, `12m`.
- **FR-031A**: System MUST make scope combination deterministic by combining grouped SHAP scope outputs from explicit artifact paths or paths recorded in grouped SHAP run metadata. The workflow MUST NOT rely on unconstrained recursive directory scanning to discover scope outputs.
- **FR-031B**: Each grouped SHAP scope output MUST include a machine-readable scope label so a companion helper can combine available outputs into a scope-by-group matrix ordered `0m`, `3m`, `6m`, `12m`.
- **FR-032**: System SHOULD render a four-column grouped SHAP heatmap when all four scope outputs are available and SHOULD render an available-scope heatmap in canonical scope order when only some scope outputs are available.
- **FR-033**: System MUST NOT require one single command invocation to train and explain all four scopes unless that is already supported cleanly by the workflow.
- **FR-034**: System MUST report the number of features matched to the six-category reference groups.
- **FR-035**: System MUST report the number of features assigned to `weather forecast`.
- **FR-036**: System MUST report the number of unmatched features.
- **FR-037**: System MUST report output paths for the grouped SHAP matrix, feature-to-group mapping, unmatched-feature diagnostics when applicable, grouped SHAP metadata, and grouped SHAP heatmap.
- **FR-038**: System MUST keep model training and prediction behavior unchanged except for retaining or accessing the training feature matrix needed for grouped SHAP.
- **FR-039**: System MUST keep grouped SHAP computation optional and controlled entirely by the grouped SHAP command option.
- **FR-040**: System MUST support grouped SHAP for train-and-predict runs that have access to the fitted `phase3_worse` model and corresponding training feature matrix.
- **FR-041**: System MUST reject supplied-model runs with a clear actionable error when grouped SHAP is requested because supplied-model compatibility is out of scope for this feature.
- **FR-042**: System MUST reject supplied-prediction or prediction-only runs with a clear actionable error when grouped SHAP is requested because they lack the fitted model and training-matrix context required for grouped SHAP.

### Key Entities *(include if feature involves data)*

- **Nowcasting Phase3 Training Feature Matrix**: The set of training rows equivalent to `train_featured.dropna(subset=["phase3_worse"]).loc[:, feature_columns]`, with columns in fitted-model order, used to explain the `phase3_worse` model.
- **Trained Phase3 Nowcasting Model**: The fitted `phase3_worse` model whose feature attributions are being summarized.
- **Feature-to-Group Mapping**: A saved table containing every training feature, assigned group when available, match method, matched reference variable when available, and unmatched status.
- **Six-Category Crosswalk**: The reference grouping table that maps base variables to the original six feature groups.
- **Weather Forecast Group**: The seventh group, `weather forecast`, containing target-month and lagged-target-month runtime rainfall and temperature forecast proxy features used by nowcasting.
- **Grouped SHAP Matrix**: A saved table aggregating training-data feature attributions into feature-group values by forecasting scope.
- **Attribution Coverage Diagnostics**: Saved and reported unmatched-feature counts and unmatched absolute SHAP contribution or share when SHAP values are available.
- **Forecasting Scope**: The horizon label used for comparison, expected to be one of `0m`, `3m`, `6m`, or `12m`.
- **Grouped SHAP Heatmap**: A human-readable visualization summarizing grouped SHAP values by feature group and forecasting scope.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In a run without grouped SHAP enabled, zero grouped SHAP artifacts are produced and the standard nowcasting output set remains unchanged.
- **SC-002**: In a supported run with grouped SHAP enabled and a fitted `phase3_worse` model available, grouped SHAP matrix outputs are saved using training-data attributions for the available forecasting scope or scopes.
- **SC-003**: The grouped SHAP workflow explains only the fitted `phase3_worse` nowcasting model unless future requirements explicitly broaden the target scope.
- **SC-004**: The SHAP input matrix uses 100% of the `phase3_worse` training rows and columns equivalent to `train_featured.dropna(subset=["phase3_worse"]).loc[:, feature_columns]`, with column order exactly matching the fitted model feature order.
- **SC-005**: The feature-to-group mapping output contains 100% of training feature names from the explained model.
- **SC-006**: When runtime rainfall or temperature forecast proxy features are present, the mapping output includes at least one entry assigned to `weather forecast` and none of those runtime forecast features are assigned to the original six groups.
- **SC-007**: Each grouped SHAP run reports four coverage counts or metrics: reference-group matched features, `weather forecast` features, unmatched features, and unmatched absolute SHAP contribution or share when available.
- **SC-008**: When all six reference groups plus `weather forecast` are expected, the grouped SHAP matrix and heatmap contain seven feature-group rows.
- **SC-009**: When all four forecasting scopes are available, the grouped SHAP matrix and heatmap contain four scope columns ordered `0m`, `3m`, `6m`, `12m`.
- **SC-010**: 100% of unmatched training features, if any, are listed in the saved diagnostics.
- **SC-011**: The workflow help text includes `--compute-grouped-shap` and describes that it produces grouped SHAP outputs.
- **SC-012**: A supplied-model run that requests grouped SHAP is rejected with a clear actionable error explaining that grouped SHAP currently supports train-and-predict runs only.
- **SC-013**: A prediction-only run that requests grouped SHAP is rejected with a clear actionable error explaining that grouped SHAP requires a fitted `phase3_worse` model and corresponding training feature matrix.
- **SC-014**: Existing forecasting SHAP behavior remains backward-compatible, including existing grouped SHAP tests and six-category forecasting outputs.
- **SC-015**: Existing nowcasting checks pass after the feature is added, and predictions from grouped-SHAP-disabled runs remain unchanged relative to the same inputs before this feature.

## Assumptions

- The grouped SHAP interpretation explains the fitted `phase3_worse` nowcasting model only; the feature does not explain all cumulative targets unless a future requirement explicitly broadens scope.
- Grouped SHAP inherits the existing nowcasting train-and-predict split policy and introduces no new train/test/evaluation split, no new target definition, and no new predictive metrics. It computes interpretability artifacts from the fitted `phase3_worse` model’s existing training feature matrix only.
- The grouped SHAP input matrix is the exact `phase3_worse` training matrix equivalent to `train_featured.dropna(subset=["phase3_worse"]).loc[:, feature_columns]`.
- The user-provided six-category crosswalk file remains the authoritative reference for non-weather-forecast feature grouping, but production code should resolve it through an explicit override or existing path configuration rather than hardcoding a local absolute path.
- Runtime weather forecast features are identified before crosswalk matching, and `weather forecast` assignment takes precedence over any original six-category assignment.
- Runtime weather forecast features are identified conservatively using existing nowcasting weather proxy definitions where possible; ambiguous rainfall or temperature features remain eligible for crosswalk matching or unmatched diagnostics rather than automatic `weather forecast` assignment.
- Unmatched features are handled through diagnostics rather than assigned to a fallback group, because this is more consistent with the existing forecasting grouped SHAP behavior.
- Each nowcasting scope may be run separately; grouped SHAP outputs should still be shaped so available scopes can be combined into a canonical `0m`, `3m`, `6m`, `12m` heatmap.
- Train-and-predict runs support grouped SHAP when enabled. Supplied-model runs are rejected for grouped SHAP in this feature because compatibility validation is out of scope. Supplied-prediction or prediction-only runs cannot produce grouped SHAP.

## References

- specs/007-nowcasting-grouped-shap/evidence.md
- .specify/memory/constitution.md
- src/ipcch/forecasting_shap.py
- scripts/modeling/run_deep_feature_weight_decay_forecasting.py
- src/ipcch/launch_nowcasting.py
- scripts/modeling/run_launch_nowcasting_2026_04.py
- tests/unit/test_forecasting_shap.py
- tests/smoke/test_weight_decay_shap_cli.py
- tests/unit/test_launch_nowcasting.py
