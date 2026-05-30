# Data Model: Launch Forecast Scope

## Forecast Scope

Represents the number of calendar months between the feature period and target period.

**Fields**

- `scope_months`: integer, one of `0`, `3`, `6`
- `feature_period`: monthly period used for launch predictor values
- `target_period`: monthly period computed as `feature_period + scope_months`

**Validation Rules**

- `scope_months` must be exactly one of `0`, `3`, or `6`.
- Period fields must support adding and subtracting 3 or 6 calendar months.
- Scope 0 with April 2026 features targets April 2026.
- Scope 3 with April 2026 features targets July 2026.
- Scope 6 with April 2026 features targets October 2026.

## Scoped Training or Evaluation Row

Represents a labeled row used for model fitting or evaluation under a forecast scope.

**Fields**

- `area_id`: spatial identifier
- `target_period`: monthly period for the target outcome
- `feature_reference_period`: `target_period - scope_months`
- `target_columns`: canonical cumulative target outcomes and phase labels as required by the existing workflow
- `time_varying_predictors`: model predictors aligned from `feature_reference_period`
- `static_predictors`: config-recognized static predictors for the same `area_id`

**Relationships**

- Belongs to one `area_id`.
- Uses one `Forecast Scope`.
- Joins to source feature rows by `area_id` and monthly feature reference period.

**Validation Rules**

- Requires target outcome at `y(area_id, t)`.
- Requires time-varying predictors from `X(area_id, t - scope_months)`.
- Must not use time-varying predictors from after the required feature reference period.
- Must not borrow predictors across different `area_id` values.
- If no usable training/evaluation records remain after scoped alignment, the workflow fails clearly.

**Example**

For `area_id = A`, `year = 2025`, `month = 7`, and `scope_months = 3`, the target outcome is July 2025 and the time-varying predictors come from April 2025 for the same `area_id`.

## Launch Prediction Record

Represents an unlabeled prediction row generated from launch feature-period predictor values.

**Fields**

- `area_id`: spatial identifier
- `feature_period`: launch feature monthly period
- `target_period`: `feature_period + scope_months`
- `scope_months`: selected forecast scope
- `predictor_columns`: model feature columns from config and schema selection
- `prediction_columns`: canonical cumulative predictions plus derived `overall_phase_pred`

**Relationships**

- Belongs to one `area_id`.
- Uses one `Forecast Scope`.
- Produces one scoped prediction artifact row.

**Validation Rules**

- Requires valid feature-period predictor rows.
- Does not require target-period target rows.
- Does not require target-period actual rows.
- Missing July/October 2026 target or actual rows must not be treated as missing prediction records.
- If no usable feature-period prediction records exist, the workflow fails clearly.

**Example**

For `area_id = A`, feature row April 2026, and `scope_months = 3`, the workflow emits a prediction for July 2026.

## Static Attribute

Represents a predictor that is not shifted during scoped alignment.

**Fields**

- `feature_name`: predictor column name from workflow config
- `classification_source`: workflow config
- `validation_basis`: area-level invariance across `year` and `month`

**Relationships**

- Applies to feature rows for one or more `area_id` values.
- Is excluded from time-varying period alignment.

**Validation Rules**

- Config remains the source of truth for static designation.
- Static list is generated or validated by scanning existing feature data.
- A feature must not be classified as static if observed non-missing values vary within any `area_id` across `year`/`month`.
- Areas with only one observed period do not alone prove global static status.
- Missing classification must be regenerated or validated before training.
- Unresolved inconsistency fails before model training.

## Time-Varying Feature

Represents a model predictor that must be period-aligned under scope 3 or scope 6.

**Fields**

- `feature_name`: predictor column name
- `feature_period`: monthly period for the predictor value
- `area_id`: spatial identifier

**Relationships**

- Belongs to one feature row identified by `area_id` and monthly period.
- Is paired with a target row at `feature_period + scope_months` for training/evaluation.

**Validation Rules**

- Any model predictor that is not an identifier, target, prediction, or config-recognized static attribute is time-varying.
- Scope 3 with April 2026 launch features must not use May, June, or July 2026 time-varying predictors.
- Scope 6 with April 2026 launch features must not use May through October 2026 time-varying predictors.

## Scoped Prediction Artifact

Represents a generated output associated with a forecast scope.

**Fields**

- `scope_months`
- `feature_period`
- `target_period`
- `area_id`
- canonical prediction columns
- workflow metadata such as threshold, training cutoff, scale, run id, and source path

**Validation Rules**

- Must record feature period and target period.
- Scope 3/6 artifacts must not overwrite scope 0 artifacts.
- Scope 0 legacy artifacts remain downstream-compatible.
- Actual-dependent metrics/reports are skipped, marked unavailable, or omitted when target-period actuals are unavailable.
