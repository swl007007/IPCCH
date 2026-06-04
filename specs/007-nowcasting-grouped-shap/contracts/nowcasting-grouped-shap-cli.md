# Contract: Nowcasting Grouped SHAP CLI

## Interface

User-facing command: `scripts/modeling/run_launch_nowcasting_2026_04.py`

## New CLI Options

### `--compute-grouped-shap`

Enables grouped SHAP computation for the supported train-and-predict nowcasting run.

**Behavior**:
- When absent, no grouped SHAP dependency resolution, computation, or grouped SHAP outputs occur.
- When present in Mode 1, the workflow computes grouped SHAP for the fitted `phase3_worse` model using the exact phase3 training matrix.
- When present with supplied-model Mode 2, the command rejects the request with a clear actionable error.
- When present with supplied-prediction / prediction-only Mode 3, the command rejects the request with a clear actionable error.

### `--grouped-shap-crosswalk-path PATH`

Explicit path override for the six-category crosswalk CSV.

**Behavior**:
- Takes precedence over configured path-key defaults.
- May point to the user-provided external crosswalk file.
- Must not be required when grouped SHAP is disabled.

### `--grouped-shap-crosswalk-key KEY`

Configured external path key for the six-category crosswalk CSV.

**Behavior**:
- Used when grouped SHAP is enabled and no explicit path override is provided.
- Default should align with existing project path mechanisms where available.
- Must not hardcode a local Windows absolute path as the only default.

### Optional crosswalk column overrides

If implemented for parity with forecasting SHAP:
- `--grouped-shap-crosswalk-feature-column COLUMN`
- `--grouped-shap-crosswalk-category-column COLUMN`

**Behavior**:
- Override automatic crosswalk column detection.
- Must not be required for the standard `variable` / `six_category` crosswalk schema.

## Required Outputs When Enabled and Supported

Machine-readable outputs under the launch results root:
- Feature-to-group mapping CSV.
- Grouped SHAP long or matrix CSV for the current scope.
- Unmatched-feature diagnostics CSV when unmatched features exist.
- Grouped SHAP metadata JSON including target, sample source, aggregation metric, crosswalk path, coverage, and artifact paths.

Human-readable outputs under the launch reports root:
- Grouped SHAP heatmap PNG for available scope data.
- Optional scope-by-group matrix CSV for report consumption.

## Console Output Contract

When grouped SHAP completes, the command reports:
- Number of features matched to six-category reference groups.
- Number of features assigned to `weather forecast`.
- Number of unmatched features.
- Unmatched absolute SHAP contribution or share when available.
- Paths to mapping, grouped matrix, diagnostics when applicable, metadata, and heatmap.

## Error Contract

The command fails clearly when:
- Grouped SHAP is requested with supplied-model Mode 2.
- Grouped SHAP is requested with supplied-prediction / prediction-only Mode 3.
- Crosswalk path resolution fails while grouped SHAP is enabled.
- Crosswalk schema lacks usable feature/category columns.
- SHAP computation fails for the fitted `phase3_worse` model.
- The SHAP input matrix columns do not exactly match fitted-model feature order.

The grouped-SHAP-disabled path must remain unaffected by these errors.
