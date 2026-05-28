# Data Model: Canonical Forecast Diagnostics

## PredictionCSV

Represents one existing held-out canonical forecast prediction CSV.

**Fields**:
- `source_path`: input file path used for provenance
- `year`: evaluation year, from CLI flag or input column when available
- `area_id`: optional spatial identifier
- `month`: optional month identifier
- `date`: optional date identifier
- `country`: optional geographic grouping field
- `region`: optional geographic grouping field
- `overall_phase`: required true IPC/CH phase label
- `overall_phase_pred`: required predicted IPC/CH phase label
- `phase2_worse`, `phase3_worse`, `phase4_worse`, `phase5_worse`: optional true cumulative phase targets
- `phase2_pred`, `phase3_pred`, `phase4_pred`, `phase5_pred`: optional predicted cumulative outputs or resolved aliases

**Validation rules**:
- `overall_phase` and `overall_phase_pred` must be present for classification diagnostics.
- Valid phase labels are numeric values 1, 2, 3, 4, 5.
- Invalid, missing, non-numeric, or out-of-range labels are recorded in validation findings.
- Cumulative columns are numeric diagnostics inputs; missing or unusable columns skip dependent diagnostics and are recorded.
- Source prediction CSVs are read-only and never overwritten.

## OverallMetricsFile

Represents an optional existing canonical summary metrics CSV.

**Fields**:
- `source_path`: metrics file path
- `year`: optional evaluation year
- `metric_name` or existing metric columns: project-specific metrics from canonical outputs
- `metric_value`: value where available

**Validation rules**:
- Missing metrics file does not block diagnostics.
- When present, metrics are used for availability and consistency reporting only, not for recalculating predictions.

## ValidationFinding

Structured finding describing schema, label, or metric-availability status.

**Fields**:
- `year`
- `finding_type`: schema, label, cumulative_column, metrics_file, output, skipped_diagnostic
- `severity`: info, warning, error
- `column`
- `value`
- `row_count`
- `message`

**Validation rules**:
- Invalid labels are reported by value and label source when possible.
- Missing optional diagnostic inputs produce warnings or info findings, not fabricated metrics.

## ClassDistribution

Annual counts and percentages by true/predicted phase label.

**Fields**:
- `year`
- `label_source`: true or predicted
- `phase_label`
- `validation_status`: valid, invalid, missing
- `count`
- `percentage`

**Validation rules**:
- Percentages are computed within each year and label source.
- Invalid and missing labels are included unless explicitly filtered.

## ConfusionMatrix

Annual true-versus-predicted phase crosstab for valid labels.

**Fields**:
- `year`
- `true_label`
- `predicted_label`
- `count`
- `row_percentage`

**Validation rules**:
- Labels 1–5 are represented where present or as zero-support rows/columns when configured.
- Row percentages are undefined or zero-marked when row support is zero, with status recorded.

## MulticlassMetricSummary

Annual multiclass metrics for valid phase labels.

**Fields**:
- `year`
- `phase_label`
- `precision`
- `recall`
- `f1`
- `support`
- `accuracy`
- `macro_f1`
- `weighted_f1`
- `ordinal_mae`

**Validation rules**:
- Metrics use only rows with valid true and predicted labels.
- Zero-support labels are reported with explicit support and safe metric handling.

## CrisisBinaryDiagnostic

Annual binary alert metrics for crisis thresholds 3+ and 4+.

**Fields**:
- `year`
- `crisis_definition`: phase3_plus or phase4_plus
- `positive_label_definition`
- `negative_label_definition`
- `precision`
- `recall`
- `f1`
- `f2`
- `positive_support`
- `negative_support`
- `total_support`

**Validation rules**:
- Metrics use only valid true/predicted phase labels.
- Support counts are always reported.

## CumulativeTargetDiagnostic

Regression-style diagnostics for cumulative phase percentage targets.

**Fields**:
- `year`
- `target`: phase2_worse, phase3_worse, phase4_worse, phase5_worse
- `true_column`
- `predicted_column`
- `n_valid`
- `rmse`
- `mae`
- `bias`
- `correlation`
- `correlation_status`

**Validation rules**:
- Metrics use rows where both true and predicted cumulative values are numeric.
- Constant or insufficient data produces an explicit correlation status.

## CalibrationBin

Calibration summary for cumulative targets.

**Fields**:
- `year`
- `target`
- `bin_lower`
- `bin_upper`
- `bin_label`
- `n_rows`
- `mean_predicted`
- `mean_true`
- `bias`

**Validation rules**:
- Empty bins are reported or skipped with coverage status.
- phase3_worse and phase4_worse receive particular coverage when present.

## ThresholdCrossingRate

Canonical 0.2 crossing summary for predicted cumulative outputs.

**Fields**:
- `year`
- `target`
- `threshold`
- `n_valid`
- `n_crossing`
- `crossing_rate`

**Validation rules**:
- Canonical threshold is 0.2.
- This summary does not modify predictions.

## ThresholdSweepResult

Post-hoc shared-threshold diagnostic sensitivity result.

**Fields**:
- `year`
- `threshold`
- `diagnostic_only`: always true
- `class_distribution_summary`
- `accuracy`
- `macro_f1`
- `phase3_plus_precision`
- `phase3_plus_recall`
- `phase3_plus_f1`
- `phase3_plus_f2`
- `phase4_plus_precision`
- `phase4_plus_recall`
- `phase4_plus_f1`
- `phase4_plus_f2`

**Validation rules**:
- One shared threshold is applied to all cumulative phase outputs for each candidate.
- No threshold is selected or recommended as final performance.
- Results are labeled post-hoc diagnostic only.

## ErrorSlice

Targeted near-boundary phase-confusion summary.

**Fields**:
- `year`
- `slice_name`: true2_pred3, true3_pred2, true4_pred3, true3_pred4
- `group_field`: overall, country, region, area_id, or other available grouping
- `group_value`
- `n_rows`
- `mean_true_phase2_worse` through `mean_true_phase5_worse`
- `mean_pred_phase2` through `mean_pred_phase5`
- `mean_margin_to_0_2_by_target`

**Validation rules**:
- Empty slices are reported explicitly.
- Geographic grouping is only produced when grouping fields are present.

## DiagnosticRunSummary

Run-level provenance and coverage record.

**Fields**:
- `run_timestamp`
- `experiment`: experiment_0
- `workflow`: canonical_regressor_diagnostics
- `input_predictions`
- `input_metrics`
- `years_processed`
- `row_counts`
- `diagnostic_families_generated`
- `diagnostic_families_skipped`
- `validation_warning_count`
- `output_dir`
- `report_dir`

**Validation rules**:
- Must identify all inputs and outputs.
- Must explain skipped diagnostic families.
