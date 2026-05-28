# Quickstart: Canonical Forecast Diagnostics

## Purpose

Run Experiment 0 canonical regressor diagnostics on one existing IPCCH prediction CSV per run without retraining models or changing source prediction CSVs. A prediction CSV is the source forecast file for one annual held-out evaluation run, containing true labels, predicted cumulative output columns, and the canonical predicted phase `overall_phase_pred`.

## Install / Import Context

From the repository root, use the editable package install or `PYTHONPATH=src` convention already used by the project:

```bash
pip install -e .
```

or:

```bash
export PYTHONPATH="${PYTHONPATH}:src"
```

## Run Help Check

```bash
python -m ipcch.forecast_diagnostics --help
```

Expected result: command help prints available input, output, column override, invalid-label, calibration, and threshold-sweep options.

## Run on an Existing Annual Prediction CSV

```bash
python -m ipcch.forecast_diagnostics \
  --predictions results/predictions/forecasting/predictions_2025.csv \
  --metrics results/experiments/deep_feature_weight_decay_forecasting/identifier_features_threshold_0_12/metrics/metrics_overall.csv \
  --year 2025 \
  --output-dir results/diagnostics/experiment_0 \
  --report-dir reports/diagnostics/experiment_0
```

Expected machine-readable outputs are written under:

```text
results/diagnostics/experiment_0/canonical_regressor/
```

Expected human-readable outputs are written under:

```text
reports/diagnostics/experiment_0/canonical_regressor/
```

## Run With Explicit Column Overrides

Use overrides when existing prediction CSVs use different predicted cumulative output column names:

```bash
python -m ipcch.forecast_diagnostics \
  --predictions results/predictions/forecasting/predictions_2025.csv \
  --year 2025 \
  --phase2-pred-col phase2_worse_pred \
  --phase3-pred-col phase3_worse_pred \
  --phase4-pred-col phase4_worse_pred \
  --phase5-pred-col phase5_worse_pred
```

## Invalid Labels

By default, invalid labels such as `0`, missing labels, non-numeric labels, or labels outside `1`–`5` are reported in validation artifacts and are not silently dropped.

Use explicit filtering only when needed for a focused valid-label report:

```bash
python -m ipcch.forecast_diagnostics \
  --predictions results/predictions/forecasting/predictions_2025.csv \
  --year 2025 \
  --filter-invalid-labels
```

## Smoke Test Expectation

Implementation validation should use a tiny synthetic CSV with:

- phases 1–4
- at least one invalid true or predicted label
- cumulative true targets for phase2_worse through phase5_worse
- cumulative predicted outputs for phase2 through phase5
- at least one phase 2→3 or phase 3→2 error slice

Smoke-test command pattern:

```bash
python -m ipcch.forecast_diagnostics \
  --predictions /tmp/ipcch_experiment_0_smoke_predictions.csv \
  --year 2025 \
  --output-dir /tmp/ipcch_experiment_0_results \
  --report-dir /tmp/ipcch_experiment_0_reports
```

Expected smoke-test results:

- `validation_findings.csv` reports invalid labels.
- `class_distribution.csv`, confusion matrices, multiclass metrics, binary crisis metrics, threshold sweep, and run summary are produced.
- `diagnostic_threshold_sweep.csv` contains `diagnostic_only=true`.
- Source smoke prediction CSV is unchanged.

## Safety Checks

- Do not run training notebooks for this feature.
- Do not write threshold choices to `configs/`.
- Do not copy large prediction CSVs into tracked feature directories.
- Treat any changes under `src/ipcch/` as review-gated before merge.
