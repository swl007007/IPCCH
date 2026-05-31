# Quickstart: Phase-3 SHAP Six-Category Feature Importance

## Purpose

Validate and run the optional phase-3 SHAP workflow for the deep-feature weight-decay forecasting pipeline without changing the default forecasting behavior.

## Prerequisites

- Run from the repository root.
- Install package editable or set `PYTHONPATH=src`.
- Ensure the six-category crosswalk is available either by explicit path or through the documented external-path key in `configs/paths.local.json`.
- Ensure the explanation dependency is installed before enabling SHAP.

## Validation Without Heavy Training

### 1. Confirm CLI visibility

```bash
PYTHONPATH=src python scripts/modeling/run_deep_feature_weight_decay_forecasting.py --help
```

Expected:

- SHAP enablement option is visible.
- Crosswalk path/key options are visible.
- Crosswalk column options are visible.
- Sample type, raw output, unmapped feature, size guard, and overwrite controls are visible.
- No local absolute Dropbox path appears as a source-code default.

### 2. Confirm default-disabled behavior

```bash
PYTHONPATH=src python scripts/modeling/run_deep_feature_weight_decay_forecasting.py \
  --fs fs3 \
  --sample-rows 50 \
  --dry-run
```

Expected:

- Dry-run completes without fitting models.
- No SHAP-specific output is required when SHAP is disabled.
- Existing split and output-plan diagnostics remain available.

### 3. Run unit tests for synthetic SHAP aggregation

```bash
PYTHONPATH=src pytest tests/unit/test_forecasting_shap.py
```

Expected:

- Six-category aggregation produces six rows per scope-year.
- Nonzero relative importance sums to 1.0 within tolerance.
- Zero-denominator scope-years produce six zeros and diagnostics.
- Duplicate and missing crosswalk mappings are caught.
- Allowed unmapped mode records mapped sum, unmapped sum, and unmapped share.

### 4. Run smoke tests for CLI wiring

```bash
PYTHONPATH=src pytest tests/smoke/test_weight_decay_shap_cli.py
```

Expected:

- CLI help includes SHAP options.
- SHAP-disabled run path remains backward-compatible.
- Missing explanation dependency fails only when SHAP is enabled.

## Example SHAP-Enabled Run Pattern

Use explicit paths or configured external-path keys; do not edit source code paths.

```bash
PYTHONPATH=src python scripts/modeling/run_deep_feature_weight_decay_forecasting.py \
  --fs fs0 \
  --enable-shap \
  --variable-crosswalk-key six_category_feature_crosswalk \
  --shap-sample train \
  --overwrite
```

Expected outputs:

- Machine-readable SHAP artifacts under the run's `results/.../shap/phase3/` area.
- Human-readable heatmap and summary artifacts under the run's `reports/.../shap/phase3/` area.
- Metadata states target `phase3_worse`, forecasting scope, annual test years, split rule, sample type, crosswalk source, feature counts, and explanation package/version.

## Example Raw SHAP Export Pattern

Raw row-level exports are optional and protected by a size guard.

```bash
PYTHONPATH=src python scripts/modeling/run_deep_feature_weight_decay_forecasting.py \
  --fs fs0 \
  --enable-shap \
  --variable-crosswalk-key six_category_feature_crosswalk \
  --save-raw-shap \
  --raw-shap-max-rows 1000 \
  --overwrite
```

Expected:

- Raw export is written only if it is within the explicit size guard or if an explicit large-output override is provided.
- Summary and heatmap artifacts remain phase-3-only.

## Completion Checks

A complete all-scope SHAP deliverable has:

- 96 rows in the long six-category relative-importance table.
- Four scope matrices, each 6 x 4.
- Four phase-3 heatmaps, one per `fs0`, `fs1`, `fs2`, and `fs3`.
- No phase-4, phase-5, classifier, or final-label explanation visualizations.
