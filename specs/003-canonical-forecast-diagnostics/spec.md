# Feature Specification: Canonical Forecast Diagnostics

**Feature Branch**: `003-canonical-forecast-diagnostics`  
**Created**: 2026-05-27  
**Status**: Draft  
**Input**: User description: "Create a Spec Kit feature for Experiment 0: canonical forecast diagnostic baseline. Build a reproducible diagnostic/evaluation workflow for existing IPCCH canonical cumulative-regression predictions, without retraining models or changing model outputs."

## Clarifications

### Session 2026-05-27

- Q: How should candidate thresholds be applied in the diagnostic-only threshold sweep? → A: Use one shared threshold value applied to all cumulative phase outputs at each candidate setting.

## Terminology

- **Prediction CSV**: The source forecast file for one annual held-out evaluation run, containing true labels, predicted cumulative output columns, and the canonical predicted phase.
- **Predicted cumulative output columns**: The cumulative-regression prediction columns for phase 2 through phase 5, preferably `phase2_pred`, `phase3_pred`, `phase4_pred`, and `phase5_pred`, or user-configured aliases.
- **Canonical predicted phase**: The `overall_phase_pred` field already produced by the canonical forecasting workflow.
- **Canonical regressor diagnostics**: Diagnostics for the existing cumulative-regression workflow, separate from classifier or correction-model outputs.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Validate canonical annual prediction outputs (Priority: P1)

As a food-security modeling researcher, I want to run a diagnostic baseline on an already-generated annual prediction CSV so that I can confirm the canonical forecast outputs are complete, valid, and interpretable before comparing them with future experiments.

**Why this priority**: This is the minimum viable diagnostic baseline. Without validation and core annual diagnostics, downstream analysis could silently rely on invalid labels, missing outputs, or misinterpreted canonical forecasts.

**Independent Test**: Can be fully tested by providing one existing annual prediction CSV with true and predicted phase fields, then confirming that validation artifacts, class distributions, confusion matrices, and per-class metrics are produced without changing the input predictions.

**Acceptance Scenarios**:

1. **Given** an annual prediction CSV containing true phase labels, the canonical predicted phase, and held-out prediction rows, **When** the researcher runs the diagnostic workflow, **Then** the workflow produces validation results, true/canonical-predicted class distributions, a confusion matrix, and per-class metric summaries for that year.
2. **Given** an annual prediction CSV containing invalid phase labels such as 0 or missing labels, **When** the researcher runs the diagnostic workflow, **Then** the workflow reports the invalid labels in validation outputs instead of silently dropping them.
3. **Given** an annual prediction CSV with valid labels from 1 through 5, **When** the researcher reviews the confusion matrix, **Then** the output includes raw counts and row-normalized percentages for the phase labels present in the file.

---

### User Story 2 - Diagnose crisis-detection and cumulative-regression behavior (Priority: P2)

As a modeling researcher, I want crisis-binary and cumulative-regression diagnostics for the same held-out prediction rows so that I can understand whether canonical cumulative predictions are producing useful 3+ and 4+ food-security alerts.

**Why this priority**: Crisis detection is the key substantive use case for IPC/CH forecasts, and cumulative-regression diagnostics explain whether classification behavior is driven by calibrated cumulative outputs or threshold-margin issues.

**Independent Test**: Can be tested by providing an annual prediction CSV with cumulative true percentages and predicted cumulative outputs, then confirming that crisis metrics, cumulative-target diagnostics, calibration summaries, and canonical threshold crossing summaries are produced.

**Acceptance Scenarios**:

1. **Given** a prediction CSV with overall true and predicted phases, **When** diagnostics are generated, **Then** the workflow reports 3+ versus 1–2 and 4+ versus 1–3 precision, recall, F1, F2, and support.
2. **Given** a prediction CSV with true and predicted cumulative phase percentages for phase2_worse, phase3_worse, phase4_worse, and phase5_worse, **When** diagnostics are generated, **Then** the workflow reports RMSE, MAE, bias, correlation, calibration-bin summaries, and canonical 0.2 threshold crossing rates for each available cumulative target.
3. **Given** cumulative target columns are missing or entirely unusable, **When** diagnostics are generated, **Then** the workflow records the missing diagnostic coverage clearly rather than fabricating metrics.

---

### User Story 3 - Compare post-hoc threshold behavior without changing canonical performance (Priority: P3)

As a modeling researcher, I want a diagnostic-only threshold sweep and targeted error-slice summaries so that I can understand sensitivity around the canonical 0.2 threshold without treating the sweep as model tuning or changing the canonical conversion behavior.

**Why this priority**: Threshold sensitivity and boundary errors are useful for diagnosis, but they must be clearly separated from canonical performance to preserve temporal validation integrity and avoid post-hoc model selection.

**Independent Test**: Can be tested by running the workflow on a prediction CSV with cumulative outputs and verifying that threshold-sweep artifacts are labeled post-hoc diagnostic only, no final tuned threshold is selected, and error slices summarize boundary behavior for specified phase confusions.

**Acceptance Scenarios**:

1. **Given** predicted cumulative phase outputs, **When** the workflow performs threshold sweeps, **Then** it reports class distributions, accuracy, macro-F1, 3+ metrics, and 4+ metrics for candidate thresholds while labeling all sweep outputs as post-hoc diagnostic only.
2. **Given** threshold-sweep results, **When** the researcher reviews the summary, **Then** no threshold is selected or recommended as final model performance and the canonical 0.2 behavior remains the reference baseline.
3. **Given** prediction rows with phase 2↔3 or phase 3↔4 confusions, **When** error-slice diagnostics are generated, **Then** the workflow summarizes mean true/predicted cumulative percentages and margins around 0.2 for each requested slice, with optional geographic grouping when those fields are available.

---

### Edge Cases

- Prediction files contain invalid true or predicted phase labels, including 0, blank, non-numeric, or values outside 1–5.
- Prediction files contain missing required columns for one or more diagnostic families.
- Cumulative true or predicted percentage columns contain missing, non-numeric, or out-of-range values.
- A year has no rows after optional explicit invalid-label filtering.
- Some phase labels are absent from a year, making per-class support zero for those labels.
- Confusion-matrix rows have zero support, making row-normalized percentages undefined.
- Correlation is undefined because a true or predicted cumulative target is constant or has insufficient valid observations.
- Calibration bins are sparse or empty for one or more cumulative targets.
- Optional country, region, or area identifiers are absent, so geographic error-slice grouping cannot be produced.
- Existing metrics files are absent, incomplete, or inconsistent with the supplied prediction CSV.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The workflow MUST accept one annual prediction CSV per run and use only its existing held-out prediction rows for diagnostics; batch or multi-file annual aggregation is out of scope for Experiment 0 v1.
- **FR-002**: Experiment 0 evaluation policy: This diagnostic workflow consumes prediction CSVs that were already produced from the canonical annual holdout forecasting workflow. Each annual prediction CSV is treated as a held-out test-year artifact. Experiment 0 performs post-holdout diagnostics only; it does not fit models, refit preprocessing, tune thresholds, calibrate labels, select models, change class mappings, alter the canonical temporal split, or use test-window data to influence fitted parameters or reported canonical metrics. Any threshold sweep is post-hoc diagnostic output only and cannot be reported as tuned model performance.
- **FR-003**: The workflow MUST preserve the canonical cumulative-to-phase interpretation using the 0.2 threshold as the reference baseline.
- **FR-004**: The workflow MUST validate true and predicted phase labels and report invalid labels such as 0, missing labels, non-numeric labels, and labels outside 1–5.
- **FR-005**: The workflow MUST provide an explicit option to filter invalid labels; without that explicit option, invalid-label rows MUST be reported rather than silently dropped.
- **FR-006**: The workflow MUST produce an annual class distribution table for true phases and predicted phases, including count, percentage, phase label, label source, year, and validation status.
- **FR-007**: The workflow MUST produce annual confusion matrices with raw counts and row-normalized percentages for labels 1, 2, 3, 4, and 5 where present.
- **FR-008**: The workflow MUST produce annual per-class metrics including precision, recall, F1, support, macro-F1, weighted-F1, accuracy, and ordinal MAE when valid ordinal labels are available.
- **FR-009**: The workflow MUST produce crisis-binary diagnostics for 3+ versus 1–2 and 4+ versus 1–3, including precision, recall, F1, F2, positive support, negative support, and total support.
- **FR-010**: The workflow MUST produce cumulative-regression diagnostics for available phase2_worse, phase3_worse, phase4_worse, and phase5_worse targets, including RMSE, MAE, bias, and correlation.
- **FR-011**: The workflow MUST produce calibration-bin summaries for each available cumulative target, with particular coverage for phase3_worse and phase4_worse when those targets are present.
- **FR-012**: The workflow MUST summarize canonical 0.2 threshold crossing rates for each available predicted cumulative output.
- **FR-013**: The workflow MUST produce a diagnostic-only threshold sweep where each candidate threshold is applied as one shared threshold value across phase2, phase3, phase4, and phase5 cumulative outputs.
- **FR-014**: Threshold-sweep outputs MUST report resulting class distribution, accuracy, macro-F1, 3+ metrics, and 4+ metrics for each shared-threshold candidate setting.
- **FR-015**: Threshold-sweep outputs MUST be clearly labeled as post-hoc diagnostic only and MUST NOT select, recommend, or promote a tuned threshold as final model performance.
- **FR-016**: The workflow MUST produce error-slice diagnostics for phase 2 predicted as 3, phase 3 predicted as 2, phase 4 predicted as 3, and phase 3 predicted as 4.
- **FR-017**: Error-slice diagnostics MUST summarize mean true cumulative percentages, mean predicted cumulative percentages, and margins around the canonical 0.2 threshold for each requested slice.
- **FR-018**: Error-slice diagnostics MUST include country, region, or area grouping summaries when those fields are present, and MUST record when those optional grouping fields are unavailable.
- **FR-019**: When an optional metrics file such as `metrics_overall.csv` is supplied, the workflow MUST load it, identify recognized comparable fields, compare those supplied values to recomputed annual diagnostics using a documented tolerance, and write comparison results to validation findings and the run summary without altering computed diagnostics.
- **FR-020**: Metrics-file comparison results MUST use status values such as `matched`, `mismatch`, `not_available`, or `not_comparable`; mismatches MUST include supplied value, recomputed value, and absolute difference, while unavailable or non-comparable fields MUST be recorded without failing the diagnostic run.
- **FR-021**: The workflow MUST write machine-readable diagnostic artifacts and human-readable diagnostic summaries in separate experiment-specific output locations.
- **FR-022**: The workflow MUST include a run summary that lists inputs, row counts, years covered, diagnostic families produced, validation warnings, metrics-file comparison status, and any skipped diagnostic families with reasons.
- **FR-023**: The workflow MUST remain separate from future experimental classifier or correction outputs so that canonical regressor diagnostics are not mixed with non-canonical experiment results.
- **FR-024**: The workflow MUST be runnable with path-agnostic defaults and allow users to override input and output locations.
- **FR-025**: The workflow MUST be verifiable through a command help check, an importability check, and a small synthetic or sampled-data smoke test that does not require heavy notebook execution.

### Key Entities *(include if feature involves data)*

- **Prediction CSV**: An existing held-out forecast CSV for one year, containing true phase labels, the canonical predicted phase, and any available cumulative true and predicted phase percentage fields.
- **Overall Metrics File**: An existing summary of canonical annual performance metrics used as a comparison or provenance input, not as a source for recalculating predictions.
- **Validation Finding**: A structured record of schema coverage, invalid labels, missing values, unusable values, skipped diagnostics, and consistency checks.
- **Class Distribution**: Annual counts and percentages of true and predicted labels, including valid and invalid label statuses.
- **Confusion Matrix**: Annual cross-tabulation of true versus predicted phase labels, represented as raw counts and row-normalized percentages.
- **Per-Class Metric Summary**: Annual multiclass classification metrics for each phase label and aggregate metrics across labels.
- **Crisis Binary Diagnostic**: Annual binary alert-performance metrics for crisis thresholds 3+ and 4+.
- **Cumulative Target Diagnostic**: Annual error, bias, correlation, calibration, and threshold-crossing summaries for cumulative phase percentage targets.
- **Threshold Sweep Result**: A post-hoc diagnostic record for candidate cumulative-output thresholds that describes sensitivity but does not define canonical performance.
- **Error Slice**: A targeted subset of rows representing specified near-boundary phase confusions, optionally summarized by available geography fields.
- **Diagnostic Report**: Human-readable annual summaries and figures describing validation results, classification behavior, cumulative behavior, threshold sensitivity, and error slices.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For a valid annual prediction CSV containing all required phase and cumulative columns, users can generate the complete diagnostic artifact set in one CLI run without retraining or changing predictions.
- **SC-002**: 100% of invalid true or predicted phase labels in the input are counted and reported in validation outputs unless the user explicitly chooses invalid-label filtering.
- **SC-003**: For every processed year with valid phase labels, the workflow produces true/predicted class distributions, raw and row-normalized confusion matrices, per-class metrics, 3+ diagnostics, and 4+ diagnostics.
- **SC-004**: For every available cumulative target among phase2_worse, phase3_worse, phase4_worse, and phase5_worse, the workflow reports RMSE, MAE, bias, correlation status, calibration-bin coverage, and canonical threshold crossing rates.
- **SC-005**: 100% of threshold-sweep artifacts and summaries include an explicit post-hoc diagnostic-only label and no output identifies a tuned threshold as final or recommended performance.
- **SC-006**: Error-slice outputs are produced for all four requested phase-confusion slices when matching rows exist, and empty slices are reported explicitly rather than omitted without explanation.
- **SC-007**: A small smoke-test input with representative valid labels, invalid labels, cumulative columns, and at least one requested error slice produces validation, metrics, threshold-sweep, and report-summary artifacts successfully.
- **SC-008**: Users can identify, from the run summary alone, which inputs were used, which years were processed, which diagnostic families were generated, and which diagnostics were skipped or warned.

## Assumptions

- Users are IPCCH modeling researchers or analysts evaluating canonical cumulative-regression forecasts before comparing later experiments.
- Prediction CSVs supplied to the workflow already represent held-out annual forecast rows produced by the canonical forecasting process.
- Experiment 0 v1 covers one annual prediction CSV per run; batch or multi-file annual aggregation is out of scope and may be added later.
- Existing metrics files are optional comparison inputs; absence of those files does not prevent diagnostics from being generated from prediction CSVs.
- The canonical 0.2 threshold remains the official baseline for cumulative-to-phase conversion; threshold sweeps are sensitivity diagnostics only.
- Optional geographic grouping is limited to fields already present in the prediction input and does not require joining new geography data.
- Human-readable summaries may include tables and figures, while machine-readable outputs remain suitable for downstream analysis and audit.
- Large prediction inputs are referenced and read in place; the feature does not require storing copies of large prediction CSVs in the repository.

## Out of Scope

- Batch or multi-file annual aggregation across several prediction CSVs in one run.
- Training, retraining, preprocessing refits, threshold tuning for final performance, label calibration, class-mapping changes, or canonical model-output changes.
- Recursive scanning of large ignored prediction directories or copying source prediction CSVs into this repository.
