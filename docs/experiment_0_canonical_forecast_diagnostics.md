# Experiment 0: Canonical Forecast Diagnostics

Experiment 0 is a diagnostic-only workflow for existing IPCCH canonical cumulative-regression prediction CSVs. It reads one already-generated held-out prediction CSV per run, computes validation and diagnostic artifacts, and never trains models or mutates source predictions.

## Safety constraints

- Do not train or retrain models.
- Do not run heavy notebooks.
- Do not modify source prediction CSVs.
- Do not modify `convert_prob_to_phase()` or the canonical `th=0.2` behavior.
- Do not use threshold sweeps as tuned model performance.
- Treat threshold-sweep rows as post-hoc diagnostics only.

## Run command

```bash
PYTHONPATH=src python -m ipcch.forecast_diagnostics \
  --predictions results/predictions/forecasting/predictions_2025.csv \
  --metrics results/experiments/deep_feature_weight_decay_forecasting/identifier_features_threshold_0_12/metrics/metrics_overall.csv \
  --year 2025 \
  --output-dir results/diagnostics/experiment_0 \
  --report-dir reports/diagnostics/experiment_0
```

Use explicit predicted cumulative output column overrides when needed:

```bash
PYTHONPATH=src python -m ipcch.forecast_diagnostics \
  --predictions results/predictions/forecasting/predictions_2025.csv \
  --year 2025 \
  --phase2-pred-col phase2_worse_pred \
  --phase3-pred-col phase3_worse_pred \
  --phase4-pred-col phase4_worse_pred \
  --phase5-pred-col phase5_worse_pred
```

Invalid true or predicted labels are reported by default. Use `--filter-invalid-labels` only when a focused valid-label output is needed.

## Machine-readable outputs

Outputs are written under `results/diagnostics/experiment_0/canonical_regressor/` by default:

- `validation_findings.csv`
- `validation_summary.json`
- `metrics_comparison.csv`
- `class_distribution.csv`
- `confusion_matrix_counts.csv`
- `confusion_matrix_row_normalized.csv`
- `multiclass_metrics.csv`
- `binary_crisis_metrics.csv`
- `cumulative_regression_metrics.csv`
- `calibration_bins.csv`
- `threshold_crossing_rates.csv`
- `diagnostic_threshold_sweep.csv`
- `error_slices.csv`
- `run_summary.json`

`diagnostic_threshold_sweep.csv` includes `diagnostic_only=true` and does not identify any selected or recommended threshold.

## Human-readable output

The summary report is written under `reports/diagnostics/experiment_0/canonical_regressor/summary.md` by default.

## Lightweight validation

```bash
PYTHONPATH=src python -c "import ipcch.forecast_diagnostics"
PYTHONPATH=src python -m ipcch.forecast_diagnostics --help
PYTHONPATH=src python -m pytest tests/smoke/test_forecast_diagnostics_smoke.py
```
