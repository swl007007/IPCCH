# Data Model: Phase-3 SHAP Six-Category Feature Importance

## Forecasting Scope

**Represents**: A model-ready feature scope selected for the weight-decay forecasting workflow.

**Fields**:
- `forecasting_scope`: one of `fs0`, `fs1`, `fs2`, `fs3`
- `scope_label`: display label for reports and metadata
- `dataset_key`: configured external-path key or explicit dataset source used for the run

**Validation rules**:
- Scope must be one of the four supported values.
- SHAP outputs must preserve scope in all scope-specific tables, diagnostics, metadata, and filenames.

## Annual Split

**Represents**: One temporal holdout for a scope.

**Fields**:
- `test_year`: one of 2022, 2023, 2024, 2025
- `split_rule`: all-prior-history annual holdout
- `train_rows`: count of eligible training rows before January 1 of the test year
- `test_rows`: count of eligible rows in the test calendar year
- `status`: `available`, `skipped`, or `failed`
- `diagnostic_reason`: nullable reason for skipped or failed states

**Validation rules**:
- Training rows must be strictly before January 1 of `test_year`.
- SHAP must not change split membership, weights, predictions, or metrics.
- Empty phase-3 training or explanation rows produce diagnostics.

## Phase-3 Model Explanation Context

**Represents**: The fitted phase-3-or-higher model and feature matrix used for explanation.

**Fields**:
- `forecasting_scope`
- `test_year`
- `target`: fixed to `phase3_worse`
- `sample_type`: e.g. `train` by default, or another supported user-selected sample
- `feature_columns`: ordered list used by the fitted phase-3 model
- `feature_count`
- `n_explanation_rows`
- `model_feature_alignment_status`: `matched` or diagnostic failure

**Validation rules**:
- Target must be `phase3_worse` only.
- The feature matrix must use exactly the columns, order, and preprocessing state used by the fitted phase-3 model.
- Final phase labels and phase-2/phase-4/phase-5 models are not valid explanation targets.

## Feature Crosswalk

**Represents**: External mapping from model feature names to six feature-group display labels.

**Fields**:
- `feature_name`
- `feature_group`
- `crosswalk_path_or_key`
- optional `alias_or_normalization_rule` metadata if category normalization is used

**Validation rules**:
- The crosswalk must define exactly six distinct feature-group labels.
- Each mapped feature must map to exactly one group.
- Duplicate feature-to-multiple-group mappings fail validation.
- Category labels from the crosswalk are preserved in outputs.
- If unmapped features are not explicitly allowed, any missing model feature fails aggregation.

## Per-Feature SHAP Summary

**Represents**: Aggregated absolute explanation importance for one feature within one scope-year.

**Fields**:
- `forecasting_scope`
- `scope_label`
- `test_year`
- `target`: `phase3_worse`
- `sample_type`
- `feature_name`
- `feature_group`
- `abs_shap_sum`
- `mean_abs_shap`
- `n_explanation_rows`

**Validation rules**:
- `abs_shap_sum` and `mean_abs_shap` must be non-negative.
- Every row must have a feature group unless it is recorded only in unmapped diagnostics.
- Feature order used for SHAP must match model feature order.

## Six-Category Relative Importance

**Represents**: One feature-group relative importance value for one scope-year.

**Fields**:
- `forecasting_scope`
- `scope_label`
- `test_year`
- `target`: `phase3_worse`
- `sample_type`
- `feature_group`
- `feature_group_abs_shap_sum`
- `total_mapped_abs_shap_sum`
- `relative_importance`
- `zero_denominator`: boolean

**Validation rules**:
- Complete data contains exactly six rows per `(forecasting_scope, test_year)`.
- For nonzero mapped denominators, the six `relative_importance` values sum to 1.0 within 0.000001.
- For zero mapped denominators, all six `relative_importance` values are `0` and diagnostics record the condition.
- Complete all-scope output contains 96 rows.

## Scope Matrix Table

**Represents**: One scope-specific matrix for heatmap generation.

**Fields**:
- `forecasting_scope`
- `feature_group` as row key
- columns for `2022`, `2023`, `2024`, `2025`
- `sample_type` included in table metadata or adjacent long-form metadata

**Validation rules**:
- Matrix shape is 6 x 4 for a complete scope.
- Row labels preserve crosswalk group labels.
- Column labels are the four annual test years.

## Diagnostic Record

**Represents**: Machine-readable explanation validation or execution issue.

**Fields**:
- `forecasting_scope`
- `test_year`
- `target`: usually `phase3_worse`
- `diagnostic_type`: missing mapping, duplicate mapping, invalid category labels, zero denominator, unavailable split, skipped SHAP, explanation-engine error, overwrite conflict, feature alignment mismatch, raw export size guard
- `severity`: info, warning, or error
- `message`
- `feature_name`: optional
- `mapped_abs_shap_sum`: optional
- `unmapped_abs_shap_sum`: optional
- `unmapped_abs_shap_share`: optional

**Validation rules**:
- Allow-unmapped diagnostics include mapped sum, unmapped sum, and unmapped share per scope-year.
- Error diagnostics that block outputs must be emitted before final aggregate artifacts are written.

## Run Metadata

**Represents**: Reproducibility record for the SHAP-enabled run.

**Fields**:
- `target`: `phase3_worse`
- `forecasting_scopes`
- `test_years`
- `split_rule`
- `sample_type`
- `crosswalk_source`
- `feature_count`
- `unmapped_feature_count`
- `explanation_package_version`
- `raw_export_enabled`
- `raw_export_size_guard`
- `artifact_paths`
- `alias_or_normalization_rules`

**Validation rules**:
- Metadata must state sample type and crosswalk source.
- Metadata must not contain hardcoded local absolute paths as defaults.
