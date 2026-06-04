# Feature Specification: 2025 Alert Risk Maps

**Feature Branch**: `002-2025-alert-risk-maps`  
**Created**: 2026-05-27  
**Status**: Draft  
**Input**: User description: "Create a reproducible IPCCH plotting workflow that generates 2025 actual-vs-predicted alert maps and top-risk comparison maps from existing prediction outputs. Somalia-only outputs in this spec must use Somalia-only or global-Somalia prediction outputs under the global experiment grouping, not Somalia-local model outputs."

## Clarifications

### Session 2026-05-27

- Q: What should “alert” mean in the actual-vs-predicted panels? → A: Binary alert: actual `overall_phase >= 3` vs predicted `overall_phase_pred >= 3`.
- Q: What spatial join coverage should be required before final figures are saved? → A: Fail unless 100% of filtered prediction `area_id` records join to spatial boundaries.
- Q: How should the workflow handle ambiguous horizon file discovery? → A: Fail unless the user provides explicit files for 0m, 3m, and 6m.
- Q: How should the workflow handle existing output files? → A: Fail if output files already exist unless overwrite is explicitly enabled.
- Q: How should binary map colors and Latin America areas be displayed? → A: Use green for no-alert/non-top-risk and red for alert/top-risk, and show Latin America areas in a small per-panel thumbnail/inset when present.
- Q: How should top-30% risk comparison figures be structured? → A: Use the same actual-over-predicted subplot structure as alert maps: actual top-30% on the upper panel and predicted top-30% on the lower panel, with the same green/red encoding.

### Session 2026-06-03

- Q: Should one CLI run generate global and Somalia figures together? → A: No. The current single-scope CLI is the intended design: each invocation selects one `--scope` (`global` or a country ISO3 such as `SOM`) and writes that selected scope's actual-vs-predicted and top-risk outputs. Generating global and Somalia deliverables requires separate runs.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Generate global 2025 actual-vs-predicted alert map (Priority: P1)

As an IPCCH analyst, I want one global 2025 figure comparing observed and predicted alert outcomes across 0-month, 3-month, and 6-month horizons so that I can assess how forecast lead time changes the spatial pattern of model alerts.

**Why this priority**: This is the primary cross-horizon visualization requested for the full prediction coverage area and is the broadest decision-support output.

**Independent Test**: Can be tested by providing the 2025 prediction outputs and spatial boundaries, running the plotting workflow for global actual-vs-predicted maps, and confirming that one global 2x3 figure is produced with correct horizons, rows, labels, and saved location.

**Acceptance Scenarios**:

1. **Given** available global 0m, 3m, and 6m prediction files containing 2025 records and matching spatial boundaries, **When** the user generates the global actual-vs-predicted map for 2025, **Then** the workflow saves one human-readable global figure under `reports/` with three horizon columns and two rows for actual and predicted outcomes.
2. **Given** a global prediction file has multiple 2025 rows for the same `area_id`, **When** the workflow prepares the horizon panel, **Then** only the latest 2025 row for that `area_id` contributes to the map and the panel has at most one prediction observation per `area_id`.
3. **Given** a required 0m, 3m, or 6m global prediction file is missing or ambiguous, **When** the user requests the global figure without providing explicit files for the ambiguous horizons, **Then** the workflow fails before producing a partial figure and explains which horizon could not be selected.

---

### User Story 2 - Generate Somalia-only 2025 actual-vs-predicted alert map (Priority: P2)

As an IPCCH analyst focused on Somalia, I want one Somalia-only 2025 figure comparing observed and predicted alert outcomes across 0-month, 3-month, and 6-month horizons so that I can inspect model behavior in the Somalia subregion without global map clutter.

**Why this priority**: Somalia is a key focus area and requires the same cross-horizon comparison as the global view at a country-specific extent.

**Independent Test**: Can be tested by providing the 2025 prediction outputs and spatial boundaries, running the plotting workflow for Somalia actual-vs-predicted maps, and confirming that one Somalia-only 2x3 figure is produced with only Somalia areas shown or highlighted.

**Acceptance Scenarios**:

1. **Given** available 0m, 3m, and 6m global-grouping prediction files containing Somalia 2025 records and matching spatial boundaries, **When** the user generates the Somalia actual-vs-predicted map for 2025, **Then** the workflow saves one human-readable Somalia figure under `reports/` with three horizon columns and two rows for actual and predicted outcomes.
2. **Given** Somalia scope is requested, **When** the workflow selects prediction inputs, **Then** it uses Somalia-only or global-Somalia outputs from the global experiment grouping and does not use Somalia-local model outputs.
3. **Given** global prediction inputs are used for Somalia scope, **When** the workflow prepares the Somalia figure, **Then** the mapped records and boundaries are filtered to Somalia before plotting.
4. **Given** no Somalia records remain after filtering and spatial joining, **When** the user requests the Somalia figure, **Then** the workflow fails clearly instead of saving an empty or misleading figure.

---

### User Story 3 - Generate global nowcasting top-risk comparison map (Priority: P3)

As an IPCCH analyst, I want a global 2025 nowcasting map comparing areas in the actual top 30% phase-3-or-worse risk set with areas in the predicted top 30% risk set so that I can assess whether the model identifies the highest-risk areas.

**Why this priority**: This provides a different evaluation view for the nowcasting horizon by focusing on ranking and overlap among the highest-risk areas.

**Independent Test**: Can be tested by providing the 0m 2025 prediction output and spatial boundaries, running the top-risk map workflow for global scope, and confirming that the saved map distinguishes actual-only, predicted-only, both, and background areas.

**Acceptance Scenarios**:

1. **Given** a 0m prediction file with 2025 `phase3_worse` and `phase3_pred` values, **When** the user generates the global top-risk comparison map, **Then** the workflow saves one global 2025 top-risk comparison figure under `reports/`.
2. **Given** duplicate 2025 rows for one or more `area_id` values, **When** the workflow computes top 30% risk sets, **Then** the duplicate filtering is completed first and the top-risk threshold is computed from one latest 2025 row per `area_id`.
3. **Given** a mapped area is in both the actual and predicted top 30% sets, **When** the figure is produced, **Then** that area is visually distinct from actual-only, predicted-only, and background areas.

---

### User Story 4 - Generate Somalia-only nowcasting top-risk comparison map (Priority: P4)

As an IPCCH analyst focused on Somalia, I want a Somalia-only 2025 nowcasting top-risk comparison map so that I can evaluate whether the model identifies the highest-risk Somalia areas.

**Why this priority**: This is the country-focused counterpart to the global top-risk view and supports local interpretation of nowcasting performance.

**Independent Test**: Can be tested by providing the 0m 2025 prediction output and spatial boundaries, running the top-risk map workflow for Somalia scope, and confirming that the saved map uses only Somalia records and distinguishes the required top-risk categories.

**Acceptance Scenarios**:

1. **Given** a 0m global-grouping prediction file with Somalia 2025 records and matching spatial boundaries, **When** the user generates the Somalia top-risk comparison map, **Then** the workflow saves one Somalia-only 2025 top-risk comparison figure under `reports/`.
2. **Given** Somalia scope is requested for the top-risk map, **When** the workflow selects the 0m input, **Then** it uses a Somalia-only or global-Somalia output from the global experiment grouping and does not use a Somalia-local model output.
3. **Given** Somalia has duplicate 2025 records for an `area_id`, **When** the workflow computes Somalia top-risk sets, **Then** only the latest record for that `area_id` is used before calculating the Somalia top 30% threshold.
4. **Given** Somalia filtering leaves too few or no mapped records to compute a meaningful top 30% comparison, **When** the user requests the Somalia top-risk map, **Then** the workflow fails with a clear explanation of the insufficient data condition.

---

### User Story 5 - Validate inputs, joins, and duplicate filtering (Priority: P1)

As an IPCCH analyst, I want the workflow to validate files, columns, spatial joins, scopes, and duplicate filtering before producing figures so that missing or ambiguous inputs are caught early and maps are not silently wrong.

**Why this priority**: Every requested figure depends on correct input selection, year filtering, latest-record selection, and spatial joining; validation protects all downstream outputs.

**Independent Test**: Can be tested with small representative prediction and spatial inputs that intentionally include missing columns, ambiguous horizon files, duplicate `area_id` values, unmatched spatial IDs, and valid records, then confirming that valid cases pass and invalid cases fail with actionable messages.

**Acceptance Scenarios**:

1. **Given** all required prediction files, columns, year values, and spatial IDs are present, **When** validation runs, **Then** the workflow proceeds to figure generation and reports the number of records used per horizon and scope.
2. **Given** any required column for filtering, joining, actual alert values, predicted alert values, or top-risk scoring is missing, **When** validation runs, **Then** the workflow stops and names the missing column and affected input.
3. **Given** any filtered prediction `area_id` record cannot be joined to spatial boundaries, **When** validation runs, **Then** the workflow stops, reports the unmatched IDs clearly, and saves no final figure.

### Edge Cases

- A horizon has no records for year 2025 after filtering.
- A prediction file has multiple candidate date columns or no usable temporal column for selecting the latest 2025 row.
- A prediction file has duplicate `area_id` rows with identical latest timestamps.
- A horizon has multiple plausible prediction files and the user has not explicitly selected which one to use.
- A Somalia-only request could match both global-grouping Somalia outputs and Somalia-local model outputs; the workflow must reject Somalia-local model outputs for this feature.
- Required actual or predicted alert columns are absent, misspelled, or entirely null.
- `phase3_worse` or `phase3_pred` contains non-numeric values that prevent top-risk ranking.
- Spatial boundaries are missing `area_id` or contain duplicate `area_id` geometries that would duplicate mapped predictions.
- Prediction `area_id` values do not match spatial `area_id` values because of type, whitespace, casing, or identifier-format differences.
- Somalia-only filtering cannot identify Somalia consistently from the available prediction or spatial attributes.
- The output destination already contains figures with the intended filenames and overwrite has not been explicitly enabled.
- Basemap or contextual map tiles are unavailable; the required data overlays must remain interpretable without external tile access.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Each workflow invocation MUST generate outputs for exactly one selected 2025 map scope. For the selected `--scope` (`global` or a country ISO3 such as `SOM`), the run MUST write one actual-vs-predicted alert map for the 0m/3m/6m horizons and one nowcasting top-risk comparison map for the 0m horizon. Producing both global and Somalia deliverables requires separate invocations.
- **FR-002**: The workflow MUST treat this feature as visualization and post-processing only; it MUST NOT retrain models, tune hyperparameters, tune thresholds, recalibrate labels, or modify existing prediction outputs.
- **FR-003**: The workflow MUST allow users to provide path-bearing inputs without embedding machine-specific absolute paths in reusable project artifacts.
- **FR-004**: The workflow MUST use existing prediction outputs under the selected prediction root and existing external spatial boundary data without copying raw spatial source data into the repository.
- **FR-005**: The workflow MUST support selecting or discovering prediction inputs for the 0m, 3m, and 6m horizons, and it MUST fail clearly if discovery produces missing candidates for a requested figure.
- **FR-006**: If horizon discovery produces multiple plausible candidates, the workflow MUST fail unless the user provides explicit files for the ambiguous 0m, 3m, or 6m horizons.
- **FR-007**: For the default IPCCH experiment root, the workflow MUST recognize horizon-specific prediction outputs corresponding to `0m`, `3m`, and `6m`, including 2025 prediction files where available.
- **FR-008**: For each horizon, the workflow MUST filter prediction records to year 2025 before duplicate handling, mapping, ranking, or plotting.
- **FR-009**: For each horizon, the workflow MUST retain only the temporally latest 2025 prediction record for each `area_id` before any figure values or top-risk thresholds are computed.
- **FR-010**: After filtering, the workflow MUST verify that each `area_id` contributes at most one prediction observation per horizon and fail if this cannot be guaranteed.
- **FR-011**: The workflow MUST join filtered prediction records to spatial boundaries using `area_id` and report the number of matched and unmatched records for each horizon and scope.
- **FR-012**: The workflow MUST require 100% of filtered prediction `area_id` records to join to spatial boundaries before saving any final figure.
- **FR-013**: The workflow MUST fail clearly when any filtered prediction record cannot be joined to spatial boundaries or when the join result would produce duplicate mapped records for an `area_id`.
- **FR-014**: The workflow MUST support selecting one map scope per run: `global` or a country ISO3 scope such as `SOM`. Somalia-only outputs are produced by running the same CLI with the Somalia scope.
- **FR-015**: The Somalia-only scope MUST include only Somalia areas in both the prediction records and mapped spatial boundaries.
- **FR-016**: Somalia-only figures MUST use Somalia-only or global-Somalia prediction outputs from the global experiment grouping; they MUST NOT use Somalia-local model outputs.
- **FR-017**: If both global-grouping Somalia outputs and Somalia-local outputs exist for a requested horizon, the workflow MUST select the global-grouping Somalia output or require an explicit user selection that still excludes Somalia-local outputs.
- **FR-018**: Each actual-vs-predicted figure MUST use a 2x3 layout with columns ordered 0m, 3m, and 6m; the first row MUST show actual or observed 2025 alert outcomes, and the second row MUST show predicted 2025 alert outcomes.
- **FR-019**: Actual-vs-predicted maps MUST define alert status as binary crisis status: actual alert is `overall_phase >= 3`, and predicted alert is `overall_phase_pred >= 3`.
- **FR-020**: Actual-vs-predicted maps MUST use consistent alert category definitions and visual encodings across all horizons and scopes in the same figure, with no-alert areas shown in green and alert areas shown in red.
- **FR-021**: Global maps MUST preserve Latin America coverage when present by showing Latin America areas in a small thumbnail/inset rather than letting the main panel extent be distorted.
- **FR-022**: The workflow MUST generate top-risk comparison maps only for the nowcasting or 0m horizon.
- **FR-023**: Top-risk comparison maps MUST identify the top 30% of areas by actual `phase3_worse` after filtering to year 2025 and retaining the latest row per `area_id`.
- **FR-024**: Top-risk comparison maps MUST identify the top 30% of areas by predicted `phase3_pred` from the same filtered one-row-per-`area_id` dataset.
- **FR-025**: Top-risk comparison maps MUST use two vertically stacked mapped panels: actual top-30% membership above predicted top-30% membership, using the same green background/no-risk and red top-risk encoding as the alert maps.
- **FR-026**: Final human-readable figures MUST be saved under `reports/` with filenames that include the year, scope, horizon group, and map type.
- **FR-027**: The workflow MUST fail before writing final figures or validation summaries if any target output file already exists, unless overwrite is explicitly enabled by the user.
- **FR-028**: Machine-readable intermediate outputs, if produced, MUST be saved under `results/` and MUST NOT overwrite or alter source prediction outputs.
- **FR-029**: The workflow MUST provide clear validation feedback for missing files, missing required columns, invalid year filtering, ambiguous horizon selection, failed Somalia filtering, failed spatial joins, duplicate `area_id` handling, existing output conflicts, and accidental Somalia-local model selection.
- **FR-030**: The workflow MUST be runnable from the repository root after normal project setup.
- **FR-031**: The workflow MUST support lightweight automation validation through import checks, help/usage checks, static checks, and small smoke tests without requiring heavy model training or notebook execution.
- **FR-032**: The prior 2024 plotting workflow MUST be treated as prior art for visual layout, green/red map presentation, and Latin America thumbnail patterns, but the 2025 workflow MUST not inherit hardcoded machine-specific input paths from that script.

### Key Entities *(include if feature involves data)*

- **Prediction Root**: The user-selected directory containing existing experiment outputs and horizon-specific prediction files or subfolders. Key attributes include root path, horizon candidates, scope candidates, model grouping, and selected prediction file for each horizon.
- **Prediction Record**: One prediction row for an `area_id` and temporal observation. Key attributes include `area_id`, date or temporal ordering field, year, `overall_phase`, `overall_phase_pred`, binary actual alert status, binary predicted alert status, `phase3_worse`, and `phase3_pred`.
- **Horizon Dataset**: The filtered prediction records for one horizon after year selection and latest-record-per-`area_id` filtering. It must contain at most one row per `area_id`.
- **Spatial Boundary**: A polygon or multipolygon geometry representing an IPCCH area. Key attributes include `area_id`, country or scope-identifying attributes, and geometry.
- **Map Scope**: The single geographic coverage selected for one CLI invocation. Supported scopes include `global` and country ISO3 values such as `SOM`. Somalia-only is a geographic filter on global-grouping or global-Somalia outputs, not a request to use Somalia-local model outputs.
- **Actual-vs-Predicted Figure**: A 2x3 final map artifact for the selected scope and year, with horizon columns and actual/predicted rows.
- **Top-Risk Comparison Figure**: A final map artifact for the selected scope and year that compares actual and predicted 0m top-30% `phase3_worse` risk membership.
- **Validation Result**: A summary of file selection, filtering, duplicate handling, spatial join coverage, and output destinations for each requested map.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can generate the selected scope's two required 2025 figures in one workflow run from valid existing prediction and spatial inputs without manually editing notebook cells or source files; global and Somalia deliverables are generated by separate `--scope` runs.
- **SC-002**: Each actual-vs-predicted output contains exactly six mapped panels arranged as two rows by three columns, with horizon labels for 0m, 3m, and 6m and row labels for actual and predicted outcomes.
- **SC-003**: For every generated figure, 100% of mapped prediction data used in each horizon has been filtered to year 2025 and reduced to at most one row per `area_id` before plotting.
- **SC-004**: Top-risk comparison outputs compute both actual and predicted top-30% groups only after duplicate filtering and display them as actual-over-predicted subplots using the same green/red encoding as the alert maps.
- **SC-005**: For valid inputs with no output conflicts or with overwrite explicitly enabled, the workflow saves the selected scope's two final human-readable figures under `reports/` with filenames that visibly identify `2025`, scope, horizon group, and map type.
- **SC-006**: For invalid inputs in the validation scenarios, the workflow stops before saving final figures and reports the specific missing, ambiguous, duplicate, or unmatched condition that must be corrected.
- **SC-007**: Validation reports record counts for each horizon and scope, including raw 2025 rows, retained latest rows, duplicate rows removed, spatial matches, and spatial non-matches.
- **SC-008**: The complete workflow can be validated with lightweight checks and small representative samples without running model training, hyperparameter tuning, threshold tuning, or notebook-heavy execution.

## Assumptions

- The primary user is an IPCCH analyst or researcher who already has access to the existing prediction outputs and external spatial boundary data.
- The requested year is fixed at 2025 for this feature.
- The default horizon labels are `0m`, `3m`, and `6m`; `0m` is treated as nowcasting.
- Existing prediction outputs include enough temporal information to identify 2025 records and choose the latest record per `area_id`.
- Existing prediction outputs include or can be mapped to actual alert, predicted alert, `phase3_worse`, and `phase3_pred` values needed for the requested maps.
- The default prediction root is the existing deep feature weight decay forecasting experiment output directory, but users may override path-bearing inputs when running the workflow.
- The default spatial data source is the external assembled IPCCH spatial directory, but the workflow accepts a user-provided spatial path or project path configuration rather than embedding that absolute path.
- Somalia-only scope can be identified from country-related attributes in prediction records or spatial boundaries.
- Somalia-only outputs for this feature come from Somalia-only or global-Somalia prediction outputs under the global experiment grouping; Somalia-local model outputs are intentionally out of scope.
- If multiple valid visual encodings are possible, consistency and interpretability across panels take priority over matching the 2024 prior-art script exactly.
- Existing output figures or validation summaries may be overwritten only when the user explicitly enables overwrite.
