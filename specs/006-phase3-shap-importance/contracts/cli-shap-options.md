# Contract: Weight-Decay Forecasting SHAP CLI Options

## Interface

The existing deep-feature weight-decay forecasting command remains the user-facing entry point. SHAP behavior is disabled by default and becomes active only when the user selects the SHAP recording mode.

## New or Updated User-Facing Controls

### Enable phase-3 SHAP

`--enable-shap`

- Enables phase-3-only SHAP recording and six-category aggregation.
- When omitted, existing prediction, metric, metadata, and report behavior remains unchanged.
- When enabled, explanation-engine unavailability or incompatibility is an error.

### Crosswalk source

`--variable-crosswalk-path PATH`

- Uses an explicit crosswalk CSV path.
- Overrides the crosswalk external-path key.

`--variable-crosswalk-key KEY`

- Resolves the crosswalk through the project external-path configuration.
- Default key should be documented in `configs/paths.example.json`.

### Crosswalk columns

`--crosswalk-feature-column NAME`

- Selects the crosswalk column containing model feature names.
- If omitted, the system may auto-detect from clear names such as `feature_name` or `variable`.

`--crosswalk-category-column NAME`

- Selects the crosswalk column containing six feature-group labels.
- If omitted, the system may auto-detect from clear names such as `feature_group` or `six_category`.

### Explanation sample

`--shap-sample train|test`

- Defaults to `train`.
- The selected value must appear in metadata, matrix tables, and heatmap captions.

### Unmapped feature behavior

`--allow-unmapped-shap-features`

- When omitted, missing crosswalk mappings fail validation.
- When provided, unmapped features are excluded from the six-category denominator.
- Diagnostics must report unmapped feature names, mapped absolute SHAP sum, unmapped absolute SHAP sum, and unmapped absolute SHAP share per forecasting scope and test year.

### Raw row-level output

`--save-raw-shap`

- Writes raw row-level phase-3 SHAP values only when explicitly requested.
- Summary tables and heatmaps do not require this option.

`--raw-shap-max-rows N`

- Maximum raw explanation rows allowed without an override.
- If raw output would exceed the guard, the run refuses oversized raw export unless a size override or row limit is explicitly provided.

`--allow-large-raw-shap`

- Explicitly permits raw row-level SHAP output beyond the default size guard.

### Output overwrite

`--overwrite`

- Existing workflow option remains authoritative for replacing generated outputs.
- SHAP outputs must respect the same overwrite behavior.

## Expected Artifact Contract

When SHAP is enabled and all four scopes and years are available, the run produces:

- Per-feature phase-3 summary table with at least:
  - `forecasting_scope`
  - `scope_label`
  - `test_year`
  - `target`
  - `sample_type`
  - `feature_name`
  - `feature_group`
  - `abs_shap_sum`
  - `mean_abs_shap`
  - `n_explanation_rows`
- Long six-category relative-importance table with 96 rows when complete.
- One 6 x 4 matrix table per forecasting scope.
- One phase-3 heatmap per forecasting scope.
- Run metadata documenting target, scopes, years, split rule, sample type, crosswalk source, feature counts, unmapped counts, explanation version, and artifact paths.
- Diagnostics for missing/duplicate mappings, invalid groups, zero denominators, skipped splits, explanation-engine failures, feature alignment mismatch, raw export size guard, and overwrite conflicts.

## Filename Contract

Phase-3 SHAP filenames should be deterministic and include:

- target: `phase3_worse`
- forecasting scope when scope-specific
- artifact type, such as `feature_summary`, `six_category_long`, `matrix`, `heatmap`, `diagnostics`, or `metadata`

## Non-Goals

The interface must not add classifier controls, phase-4 visualizations, phase-5 visualizations, or explanation outputs for final predicted phase labels.
