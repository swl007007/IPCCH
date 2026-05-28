# Quickstart: 2025 Alert Risk Maps

## Purpose

Generate four reproducible 2025 IPCCH visualization outputs from existing prediction CSVs and external spatial boundaries:

1. Global actual-vs-predicted alert map, 2x3 layout for 0m/3m/6m.
2. Somalia-only actual-vs-predicted alert map, 2x3 layout for 0m/3m/6m.
3. Global nowcasting top-30% phase3-risk comparison map.
4. Somalia-only nowcasting top-30% phase3-risk comparison map.

The workflow is post-processing only. It does not retrain models, tune thresholds, recalibrate labels, run notebooks, or modify prediction outputs.

## Prerequisites

From the repository root:

```bash
pip install -e .
pip install pandas geopandas matplotlib contextily
```

If the editable install is not available:

```bash
export PYTHONPATH="${PYTHONPATH}:src"
```

External spatial data remains outside the repository, for example:

```text
/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/Google fund/Analysis/1.Source Data/assembled_IPCCH/spatial/ipcch_admin_geometry.shp
```

## Expected default prediction root

```text
results/experiments/deep_feature_weight_decay_forecasting
```

The default root is expected to contain horizon-specific 2025 prediction files for `0m`, `3m`, and `6m`. Somalia-only outputs must come from global-grouping/global-Somalia prediction outputs, not Somalia-local model outputs.

## Lightweight validation

```bash
PYTHONPATH=src python scripts/reporting/plot_2025_alert_risk_maps.py --help
PYTHONPATH=src python -c "import ipcch.alert_risk_maps"
```

These checks should not run training or notebooks.

## Example full run

```bash
PYTHONPATH=src python scripts/reporting/plot_2025_alert_risk_maps.py \
  --prediction-root "results/experiments/deep_feature_weight_decay_forecasting" \
  --spatial-path "/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/Google fund/Analysis/1.Source Data/assembled_IPCCH/spatial/ipcch_admin_geometry.shp" \
  --out-report-dir "reports/deep_feature_weight_decay_forecasting/alert_risk_maps" \
  --out-results-dir "results/experiments/deep_feature_weight_decay_forecasting/alert_risk_maps"
```

If horizon discovery is ambiguous, provide explicit files:

```bash
PYTHONPATH=src python scripts/reporting/plot_2025_alert_risk_maps.py \
  --horizon-0m-file "results/experiments/deep_feature_weight_decay_forecasting/0m_global_identifier_features_threshold_0_20/predictions/predictions_2025.csv" \
  --horizon-3m-file "results/experiments/deep_feature_weight_decay_forecasting/3m_global_identifier_features_threshold_0_20/predictions/predictions_2025.csv" \
  --horizon-6m-file "results/experiments/deep_feature_weight_decay_forecasting/6m_global_identifier_features_threshold_0_20/predictions/predictions_2025.csv" \
  --somalia-horizon-0m-file "results/experiments/deep_feature_weight_decay_forecasting/0m_somalia_identifier_features_threshold_0_20/predictions/predictions_2025.csv" \
  --somalia-horizon-3m-file "results/experiments/deep_feature_weight_decay_forecasting/3m_somalia_identifier_features_threshold_0_20/predictions/predictions_2025.csv" \
  --somalia-horizon-6m-file "results/experiments/deep_feature_weight_decay_forecasting/6m_somalia_identifier_features_threshold_0_20/predictions/predictions_2025.csv" \
  --spatial-path "/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/Google fund/Analysis/1.Source Data/assembled_IPCCH/spatial/ipcch_admin_geometry.shp"
```

## Overwriting outputs

By default, the workflow fails if target figures or validation summaries already exist. To intentionally replace outputs:

```bash
PYTHONPATH=src python scripts/reporting/plot_2025_alert_risk_maps.py --overwrite [other options]
```

## Expected outputs

Under `reports/`:

```text
ipcch_2025_global_0m-3m-6m_actual_vs_predicted_alert_map.png
ipcch_2025_somalia_0m-3m-6m_actual_vs_predicted_alert_map.png
ipcch_2025_global_0m_top30_phase3_risk_comparison_map.png
ipcch_2025_somalia_0m_top30_phase3_risk_comparison_map.png
```

Optional validation summary under `results/`:

```text
ipcch_2025_alert_risk_maps_validation_summary.json
```

## Acceptance checks

- Actual-vs-predicted maps have exactly six panels: actual row, predicted row, and 0m/3m/6m columns.
- Alert status is binary: actual `overall_phase >= 3`, predicted `overall_phase_pred >= 3`.
- Top-risk maps use only the latest 2025 row per `area_id` before computing top 30% groups.
- Spatial join coverage is 100%; any unmatched filtered `area_id` fails the run.
- Somalia-only maps do not use Somalia-local model outputs.
