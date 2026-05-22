# Feature Specification: Deep Feature Weighted Decay Forecasting

**Feature Branch**: `001-deep-feature-weight-decay`  
**Created**: 2026-05-21  
**Status**: Draft  
**Input**: User description: "Create a new IPCCH modelling entry point using the deep-feature forecasting-ready dataset, exponential time-decay sample weights, F2 reporting, annual holdouts for 2022-2025, and Somalia-only metrics, without modifying the original notebook or upstream data assembly pipeline."

## Clarifications

### Session 2026-05-21

- Q: What default time-decay parameter should full model runs use? → A: Default half-life is 24 months.
- Q: What training window should annual holdouts use if the reference notebook differs? → A: Always use all records before the test year.
- Q: How should undefined metrics be reported? → A: Report unavailable with reason.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Evaluate the corrected deep-feature dataset (Priority: P1)

As an IPCCH researcher, I want a separate modelling workflow that consumes the new deep-feature forecasting-ready dataset and evaluates annual holdout years 2022, 2023, 2024, and 2025, so that I can compare results from the corrected feature source without changing the original forecasting notebook or upstream data assembly work.

**Why this priority**: This is the minimum useful workflow: it validates the new modelling data source and produces the four required annual evaluations while preserving the existing notebook as a reference artifact.

**Independent Test**: Run the workflow in a lightweight validation mode and verify that it resolves the configured external input source, creates monthly dates from year and month, identifies eligible features and targets, and prepares exactly four annual holdout splits without fitting full models.

**Acceptance Scenarios**:

1. **Given** the configured deep-feature forecasting-ready dataset is available, **When** the modelling workflow is launched, **Then** it loads that dataset instead of the legacy forecasting source.
2. **Given** annual split diagnostics are produced, **When** they are inspected, **Then** the only test years listed are 2022, 2023, 2024, and 2025.
3. **Given** any annual holdout year, **When** its split is inspected, **Then** every training record is strictly earlier than January 1 of that test year and every test record belongs to that test year.
4. **Given** the original forecasting notebook exists, **When** the feature changes are reviewed, **Then** that notebook remains unchanged.

---

### User Story 2 - Weight training records by temporal recency (Priority: P2)

As an IPCCH researcher, I want training records closer to each annual test window to receive larger fitting weights than older records, so that model fitting can emphasize more recent observations while preserving strict temporal validation.

**Why this priority**: The time-decay weighting is a core modelling change and directly affects fitted parameters, so it must be explicit, configurable, recorded, and testable.

**Independent Test**: Use validation diagnostics or a small sample to confirm that month distances are computed relative to the first month of each holdout year, newer training rows receive larger weights than older rows, and each fitted cumulative-phase model receives the corresponding weight vector.

**Acceptance Scenarios**:

1. **Given** a 2024 holdout, **When** weights are computed, **Then** a 2023 training record receives a higher weight than an otherwise comparable 2021 training record.
2. **Given** any annual holdout model run, **When** fitted model inputs are audited, **Then** all four cumulative phase targets are trained with valid sample weights.
3. **Given** a decay parameter is provided or configured, **When** outputs are saved, **Then** metadata records the decay formula, parameter value, test year, and split rule.
4. **Given** the decay half-life parameter is omitted, **When** full model fitting is requested, **Then** the workflow uses the default 24-month half-life and records that default in metadata.
5. **Given** the decay parameter is invalid, **When** full model fitting is requested, **Then** the workflow stops with a clear validation error rather than fitting unweighted or ambiguous models.

---

### User Story 3 - Compare annual model quality with F2 included (Priority: P3)

As an IPCCH researcher, I want each annual holdout report to include F2 in addition to accuracy, precision, sensitivity/recall, and phase-3+ R2, so that recall-weighted crisis detection performance is visible alongside the existing metrics.

**Why this priority**: F2 is required for interpreting phase 3+ crisis detection where recall is especially important, but it depends on predictions produced by the annual holdout workflow.

**Independent Test**: Evaluate a known small set of observed and predicted phases and verify that F2 is reported for the phase 3+ positive class using beta = 2 and that zero-denominator cases are reported as unavailable with a reason.

**Acceptance Scenarios**:

1. **Given** a completed annual holdout prediction output, **When** metrics are calculated, **Then** F2 appears alongside accuracy, precision, sensitivity/recall, and R2.
2. **Given** observed and predicted phases, **When** F2 is calculated, **Then** phases 3, 4, and 5 are treated as the positive crisis class and beta = 2 gives recall more weight than precision.
3. **Given** the consolidated final report is opened, **When** the annual metrics table is inspected, **Then** each test year from 2022 through 2025 has a metric value or an explicit unavailable reason for every required metric.

---

### User Story 4 - Produce Somalia-only performance metrics (Priority: P4)

As an IPCCH researcher, I want Somalia-only test-sample metrics after all annual holdout predictions are produced, so that I can compare overall model performance with country-specific performance for Somalia.

**Why this priority**: Somalia-specific results are required for interpretation, but they depend on the prediction outputs from the annual holdout runs and a reliable Somalia area lookup.

**Independent Test**: Load the configured IPCCH completed source, derive Somalia area identifiers, filter one holdout prediction output to those identifiers, and verify that the same metric set is produced for Somalia-only rows.

**Acceptance Scenarios**:

1. **Given** the Somalia lookup source contains country identifiers, **When** the workflow builds the Somalia area list, **Then** it extracts area identifiers using ISO3 value `SOM` when available, otherwise normalized Somalia country-name matching.
2. **Given** annual holdout predictions exist, **When** Somalia filtering is applied, **Then** each test year is evaluated separately using only Somalia test samples.
3. **Given** Somalia has no eligible test rows for a year, **When** Somalia metrics are reported, **Then** that year is marked as having no eligible Somalia samples instead of silently reporting misleading zero metrics.

---

### User Story 5 - Preserve project discipline and auditability (Priority: P5)

As a maintainer, I want the new workflow, outputs, and metadata to follow the modelling repository’s conventions, so that the feature is reproducible, reviewable, and does not contaminate source data or generated output tracking.

**Why this priority**: The feature must be maintainable and auditable after the core modelling behavior works.

**Independent Test**: Review the changed files and generated outputs to confirm that source code changes are isolated to a new modelling entry point and any reusable package utilities, external raw data is not copied into the repository, machine-readable outputs are under results, and human-readable summaries are under reports.

**Acceptance Scenarios**:

1. **Given** the feature is implemented, **When** the repository diff is inspected, **Then** the original forecasting notebook is unchanged and the new workflow is separate.
2. **Given** path-bearing inputs are needed, **When** configuration and invocation options are inspected, **Then** machine-specific external paths are configurable and not committed as hardcoded source-code paths.
3. **Given** full or partial runs complete, **When** output locations are inspected, **Then** machine-readable outputs are stored under results and human-readable summaries are stored under reports.
4. **Given** raw external IPCCH source data is needed, **When** the repository contents are inspected, **Then** those raw source files have not been copied into the repository.

---

### Edge Cases

- The configured forecasting-ready dataset path is missing, unreadable, or points to the legacy source instead of the corrected deep-feature source.
- The input dataset lacks required identifiers, date components, phase percentage targets, or the observed overall phase.
- The input dataset contains non-numeric candidate features that could be selected accidentally.
- The year and month columns cannot be converted into valid monthly dates.
- Target values are missing for some records in a holdout training or test split.
- A holdout year has no eligible test records.
- A holdout year has no eligible training records strictly before its January start date.
- The configured decay half-life is non-positive, non-finite, or produces non-finite weights.
- Sample weights contain null, infinite, zero where disallowed, or negative values.
- Required model configuration inputs are missing or unreadable.
- Metric denominators are zero for precision, sensitivity/recall, or F2, requiring an unavailable status with a reason.
- R2 is undefined because too few valid rows exist or the observed phase-3+ target is constant, requiring an unavailable status with a reason.
- Prediction or metrics outputs already exist at the target location.
- Somalia lookup data has multiple country identifier columns, missing ISO3 values, inconsistent country names, or duplicate area identifiers.
- Somalia has no eligible test rows in one or more holdout years.
- Full model fitting is too expensive for routine validation.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a separate modelling workflow for the deep-feature weighted-decay forecasting evaluation.
- **FR-002**: The system MUST use the corrected deep-feature forecasting-ready dataset as the modelling input, resolved through configurable external data settings or invocation options rather than committed machine-specific source paths.
- **FR-003**: The system MUST preserve the original main forecasting notebook unchanged.
- **FR-004**: The system MUST create a monthly date field from year and month before preparing annual splits.
- **FR-005**: The system MUST use `area_id` as the canonical spatial identifier and reject inputs that cannot provide a compatible area identifier.
- **FR-006**: The system MUST preserve the cumulative target structure for phase2_worse, phase3_worse, phase4_worse, and phase5_worse.
- **FR-007**: The system MUST evaluate exactly four annual holdout years: 2022, 2023, 2024, and 2025.
- **FR-008**: For each holdout year, the system MUST train only on records strictly before January 1 of that year and test only on records in that calendar year.
- **FR-009**: The system MUST prevent test-year or future records from influencing fitted parameters, hyperparameter selection, scaling, threshold selection, sample-weight calibration, or any metric outside that year’s test evaluation.
- **FR-010**: The system MUST compute training sample weights from whole-month distance between each training row date and January 1 of the relevant holdout year.
- **FR-011**: The system MUST assign larger sample weights to training rows closer to the relevant holdout test window under an exponential decay rule.
- **FR-012**: The system MUST use a configurable exponential decay half-life with a default of 24 months for full training and MUST record the parameter used for each run.
- **FR-013**: The system MUST apply the computed sample weights to every fitted cumulative-phase model for every annual holdout run.
- **FR-014**: The system MUST preserve the existing four-model cumulative phase design and existing phase conversion convention unless planning identifies a project-approved replacement.
- **FR-015**: The system MUST preserve phase-3-specific model configuration behavior where the existing modelling workflow uses a distinct phase-3 configuration.
- **FR-016**: The system MUST select modelling features from eligible non-target numeric columns while excluding identifiers, dates, target fields, observed labels, prediction fields, and target-derived leakage fields.
- **FR-017**: The system MUST NOT recompute upstream deep features or perform feature engineering that uses future or test-window information.
- **FR-018**: For each annual holdout year, the system MUST report accuracy, precision for phase 3+, sensitivity/recall for phase 3+, R2 for phase3_worse, and F2 for phase 3+.
- **FR-019**: The system MUST define F2 as the F-beta score with beta = 2 for the discrete phase 3+ crisis class and report unavailable metrics with an explicit reason when denominators or validity conditions make them undefined.
- **FR-020**: The system MUST load Somalia area identifiers from the configured IPCCH completed source or equivalent configured lookup source.
- **FR-021**: The system MUST identify Somalia by ISO3 `SOM` when available, otherwise by normalized Somalia country-name matching in available country fields.
- **FR-022**: The system MUST compute Somalia-only metrics for each holdout year using the same metric set as the overall annual reports.
- **FR-023**: The system MUST explicitly report years with no eligible Somalia test samples rather than producing misleading numeric Somalia metrics.
- **FR-024**: The system MUST save per-year prediction outputs, per-year overall metrics, consolidated overall metrics, Somalia-only metrics, and run metadata under results.
- **FR-025**: The system MUST save a human-readable report under reports containing overall annual metrics, Somalia-only annual metrics, the data-source replacement note, the time-decay formula and configured parameter, and confirmation that the original notebook was not modified.
- **FR-026**: The system MUST provide a lightweight validation mode that checks path resolution, required columns, feature selection, split diagnostics, weight monotonicity, and output planning without executing full heavy training.
- **FR-027**: The system MUST avoid copying raw external source data into the repository.
- **FR-028**: The system MUST avoid requiring large generated prediction outputs to be tracked in version control.
- **FR-029**: The system MUST record run metadata including input source identity, Somalia lookup source identity, split rule, test years, target columns, feature count, decay formulation and parameter, output locations, and run timestamp.

### Key Entities *(include if feature involves data)*

- **ForecastingReadyDataset**: The corrected deep-feature IPCCH modelling dataset containing area identifiers, year, month, observed phase labels, phase percentage targets, and numeric forecasting-ready features.
- **AnnualHoldoutRun**: One yearly evaluation consisting of a holdout year, strict train/test split, four cumulative-phase fitted models, predictions, metrics, and metadata.
- **TimeDecayWeights**: Per-training-row weights derived from whole-month distance to the first month of the holdout year, with nearer rows receiving larger weights.
- **CumulativePhaseTarget**: One of the four cumulative crisis targets used by the forecasting workflow: phase2_worse, phase3_worse, phase4_worse, or phase5_worse.
- **MetricsReport**: A machine-readable or human-readable summary containing accuracy, precision, sensitivity/recall, R2, and F2 for one or more annual holdout years.
- **SomaliaAreaLookup**: The configured source and derived set of area identifiers corresponding to Somalia.
- **SomaliaMetricsReport**: The Somalia-only metrics table by holdout year, including explicit no-sample statuses where applicable.
- **RunMetadata**: Audit information describing the input sources, split rule, test years, decay settings, feature count, outputs, and execution timestamp.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A maintainer can verify from the repository diff that the original forecasting notebook has zero changes and the new workflow is separate.
- **SC-002**: Lightweight validation completes without full model training and reports exactly four planned holdout years: 2022, 2023, 2024, and 2025.
- **SC-003**: For 100% of planned holdout years, split diagnostics show the maximum training date is earlier than January 1 of the test year.
- **SC-004**: For 100% of completed model fits, all four cumulative-phase targets receive valid time-decay sample weights.
- **SC-005**: Weight diagnostics demonstrate that, for each holdout year, newer training records have monotonically larger weights than older records under the configured decay formula.
- **SC-006**: For every completed annual holdout year, the overall metrics table includes accuracy, precision, sensitivity/recall, R2, and F2 or an explicit unavailable reason.
- **SC-007**: For every completed annual holdout year, the Somalia metrics table includes the same required metric fields or an explicit no-eligible-samples status.
- **SC-008**: The consolidated human-readable report includes two annual comparison tables: overall performance and Somalia-only performance.
- **SC-009**: Run metadata records the data source identity, Somalia lookup source identity, split rule, four test years, decay parameter, feature count, and output locations for every run.
- **SC-010**: No raw external source data files are added to the repository as part of this feature.
- **SC-011**: All machine-readable generated artifacts are written under results, and all human-readable generated summaries are written under reports.
- **SC-012**: A reviewer can reproduce path-bearing inputs using documented configuration or invocation options without finding committed machine-specific absolute paths in source code.

## Assumptions

- The new forecasting-ready dataset has already been created outside this modelling repository and should be treated as an external input, not regenerated here.
- Annual holdouts use all eligible prior history before the test year, regardless of whether the reference notebook uses a shorter fixed-window convention.
- The default time-decay parameter is a 24-month half-life; users may override it with an explicit configured value for sensitivity analysis.
- F2 is calculated on discrete phase predictions using phase 3 or above as the positive crisis class.
- Somalia area identifiers are derived by preferring ISO3 `SOM` when present, then falling back to normalized country-name matching for Somalia.
- The suggested entry-point name is acceptable unless maintainers choose another repository-consistent name during planning.
- Existing forecasting hyperparameter files and phase conversion conventions remain authoritative unless planning discovers a newer project-approved convention.
- Full model training may be expensive; routine automated validation should use lightweight diagnostics, import checks, help output, dry-run behavior, or small samples unless the user explicitly requests full training.
