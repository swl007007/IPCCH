# Data Model: Nowcasting Grouped SHAP Values

## Nowcasting Phase3 Training Feature Matrix

**Purpose**: Input rows and columns used to explain the fitted `phase3_worse` model.

**Fields**:
- `rows`: training observations with non-missing `phase3_worse` target.
- `columns`: exact ordered `feature_columns` list used to fit the model.
- `scope`: forecasting scope label for the run: `0m`, `3m`, `6m`, or `12m`.
- `target`: fixed value `phase3_worse`.

**Validation rules**:
- Rows must be equivalent to `train_featured.dropna(subset=["phase3_worse"])`.
- Columns must exactly match `feature_columns` in fitted-model order.
- Must not use April prediction rows, validation rows, test rows, or prediction-only rows.

## Trained Phase3 Nowcasting Model

**Purpose**: Fitted model object whose feature attributions are summarized.

**Fields**:
- `target`: fixed value `phase3_worse`.
- `feature_columns`: ordered model feature names.
- `model`: fitted estimator compatible with the existing SHAP engine.
- `scope`: forecasting scope for the run.

**Validation rules**:
- Available only in supported Mode 1 train-and-predict grouped SHAP runs.
- Feature order must align with the SHAP input matrix.

## Six-Category Crosswalk

**Purpose**: Reference grouping source for non-weather-forecast model features.

**Fields**:
- `reference_feature`: feature or base variable name from the crosswalk.
- `reference_group`: one of the six reference groups.
- `source_path`: resolved crosswalk file path.
- `feature_column`: selected feature column name.
- `category_column`: selected category column name.

**Validation rules**:
- Crosswalk must contain usable feature and category columns.
- Default resolution must use project path mechanisms or config; local absolute paths are explicit overrides only.

## Feature-to-Group Mapping

**Purpose**: Auditable mapping from every model feature to an assigned group or unmatched status.

**Fields**:
- `feature_name`: model feature name from `feature_columns`.
- `assigned_group`: six-category group, `weather forecast`, or blank for unmatched.
- `match_method`: `weather_forecast`, `exact`, `normalized`, `base_variable`, `ambiguous`, or `unmatched`.
- `matched_reference_feature`: crosswalk feature matched, when applicable.
- `is_weather_forecast`: boolean.
- `is_unmatched`: boolean.
- `notes`: short diagnostic detail when ambiguous or unmatched.

**Validation rules**:
- Contains 100% of `feature_columns`.
- Weather forecast assignment is evaluated before crosswalk matching.
- Ambiguous normalized matches are unresolved, not auto-assigned.
- Unmatched features are diagnostics-only and are not assigned to `other`.

## Grouped SHAP Feature Summary

**Purpose**: Per-feature SHAP attribution summary used for grouping and diagnostics.

**Fields**:
- `feature_name`: model feature name.
- `assigned_group`: mapped group when available.
- `abs_shap_sum`: total absolute SHAP contribution for the feature.
- `mean_abs_shap`: mean absolute SHAP contribution for the feature.
- `relative_importance`: feature importance share using existing forecasting SHAP semantics where applicable.
- `scope`: forecasting scope.

**Validation rules**:
- Computed from training-data SHAP values only.
- Must preserve existing absolute-SHAP aggregation semantics.

## Grouped SHAP Matrix

**Purpose**: Scope-by-group matrix for downstream heatmap rendering.

**Fields**:
- `feature_group`: six reference groups plus `weather forecast`.
- `0m`: grouped importance for 0-month scope when available.
- `3m`: grouped importance for 3-month scope when available.
- `6m`: grouped importance for 6-month scope when available.
- `12m`: grouped importance for 12-month scope when available.

**Validation rules**:
- Rows include expected seven groups with zero values for expected but absent/zero-attribution groups.
- Scope columns appear only when available and are ordered `0m`, `3m`, `6m`, `12m`.

## Attribution Coverage Diagnostics

**Purpose**: Quantify mapping coverage and unmatched attribution impact.

**Fields**:
- `scope`: forecasting scope.
- `reference_matched_feature_count`: count assigned to six reference groups.
- `weather_forecast_feature_count`: count assigned to `weather forecast`.
- `unmatched_feature_count`: count unresolved.
- `unmatched_abs_shap_sum`: total absolute SHAP contribution from unmatched features when SHAP values are available.
- `unmatched_abs_shap_share`: unmatched share when denominator is available.
- `unmatched_features_path`: diagnostics artifact path when present.

**Validation rules**:
- Counts must be reported for every grouped SHAP run.
- Unmatched contribution/share must be reported when SHAP values are available.

## Grouped SHAP Metadata

**Purpose**: Machine-readable record of grouped SHAP execution.

**Fields**:
- `enabled`: boolean.
- `target`: fixed value `phase3_worse`.
- `scope`: forecasting scope.
- `sample_source`: fixed value `phase3_training_matrix`.
- `aggregation_metric`: documented SHAP grouping metric.
- `crosswalk_path`: resolved crosswalk path.
- `artifact_paths`: mapping of grouped SHAP outputs.
- `coverage`: attribution coverage diagnostics.

**Validation rules**:
- Written only when grouped SHAP is enabled and supported.
- Must not claim completion if computation fails.
