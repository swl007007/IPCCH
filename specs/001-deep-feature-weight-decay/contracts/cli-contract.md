# Contract: Deep Feature Weighted Decay Forecasting CLI

## Command

`PYTHONPATH=src python scripts/modeling/run_deep_feature_weight_decay_forecasting.py [options]`

The final script name may be adjusted during implementation if the repository chooses a more consistent name, but the command must expose the following behaviours.

## Required behaviours

### Full run
Runs annual holdout evaluations for 2022, 2023, 2024, and 2025 using the configured deep-feature forecasting-ready dataset, default 24-month time-decay half-life unless overridden, and writes results and reports.

### Dry run
Validates path resolution, required columns, date creation, feature selection, split diagnostics, weight monotonicity, Somalia lookup, and output plan without full model training.

## Options

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--dataset` | No | external path key for deep-feature forecasting dataset | Path to corrected forecasting-ready CSV. |
| `--dataset-key` | No | `deep_features_forecasting_dataset` | External path key to resolve when `--dataset` is omitted. |
| `--somalia-lookup` | No | external path key for IPCCH 2026 completed source | Path to source used to derive Somalia `area_id` values. |
| `--somalia-lookup-key` | No | `ipcch_2026_completed_dataset` | External path key to resolve when `--somalia-lookup` is omitted. |
| `--out-dir` | No | `results/experiments/deep_feature_weight_decay_forecasting` | Machine-readable output directory. |
| `--report-dir` | No | `reports/deep_feature_weight_decay_forecasting` | Human-readable report directory. |
| `--half-life-months` | No | `24` | Exponential time-decay half-life in months. |
| `--test-years` | No | `2022 2023 2024 2025` | Holdout years; implementation must reject values that do not produce exactly the required four-year evaluation unless explicitly operating in test mode. |
| `--seed` | No | project default if available, otherwise fixed deterministic seed | Random seed for reproducible fitting. |
| `--dry-run` | No | false | Run validations and diagnostics without fitting full models. |
| `--sample-rows` | No | unset | Optional lightweight validation/sample mode that limits input rows for smoke tests. |
| `--overwrite` | No | false | Allow replacing existing generated outputs. |

## Output contract

Machine-readable outputs under `results/experiments/deep_feature_weight_decay_forecasting/`:

```text
predictions/
  predictions_2022.csv
  predictions_2023.csv
  predictions_2024.csv
  predictions_2025.csv
metrics/
  metrics_2022.json
  metrics_2023.json
  metrics_2024.json
  metrics_2025.json
  metrics_overall.csv
  metrics_somalia.csv
metadata/
  run_metadata.json
  split_diagnostics.csv
```

Human-readable outputs under `reports/deep_feature_weight_decay_forecasting/`:

```text
summary.md
metrics_overall.csv
metrics_somalia.csv
```

## Exit conditions

- Exit successfully when dry-run validations pass or full outputs are written.
- Fail clearly when required columns, valid dates, valid weights, required path inputs, hyperparameter inputs, or eligible train/test rows are missing.
- Report unavailable metric values with explicit reasons in output tables rather than coercing them to zero.
