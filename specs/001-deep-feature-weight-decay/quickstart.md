# Quickstart: Deep Feature Weighted Decay Forecasting

## Prerequisites

1. Install the project package from the repository root:

   ```bash
   pip install -e .
   ```

2. Add machine-specific external paths to ignored `configs/paths.local.json` or pass paths through CLI flags. Expected external path keys:

   ```json
   {
     "deep_features_forecasting_dataset": "../../../1.Source Data/assembled_IPCCH/forecasting_subset_IPCCH_2026_target_corrected_deep_features_forecasting_ready.csv",
     "ipcch_2026_completed_dataset": "../../../1.Source Data/assembled_IPCCH/IPCCH_2026_completed.csv"
   }
   ```

   Do not commit machine-specific absolute Windows paths.

## Validate without full training

```bash
PYTHONPATH=src python scripts/modeling/run_deep_feature_weight_decay_forecasting.py --dry-run
```

Expected dry-run checks:
- Resolve the configured deep-feature dataset and Somalia lookup paths.
- Confirm required columns exist.
- Create monthly dates from `year` and `month`.
- Derive cumulative phase targets.
- Select eligible non-target numeric feature columns.
- Prepare exactly four splits for 2022, 2023, 2024, and 2025.
- Confirm every training split is strictly before January 1 of the test year.
- Compute sample-weight diagnostics using the default 24-month half-life.
- Derive Somalia area identifiers.
- Print planned output locations without fitting full models.

## Run a lightweight smoke test

Use a small row sample only for automation or local sanity checks:

```bash
PYTHONPATH=src python scripts/modeling/run_deep_feature_weight_decay_forecasting.py \
  --dry-run \
  --sample-rows 500
```

## Run the full workflow

Only run full training when explicitly intended:

```bash
PYTHONPATH=src python scripts/modeling/run_deep_feature_weight_decay_forecasting.py \
  --half-life-months 24
```

Expected outputs:
- Machine-readable artifacts in `results/experiments/deep_feature_weight_decay_forecasting/`.
- Human-readable report in `reports/deep_feature_weight_decay_forecasting/summary.md`.
- Per-year predictions and metrics for 2022, 2023, 2024, and 2025.
- Somalia-only metrics for each year, with no-sample statuses where applicable.

## Validation commands for implementation review

```bash
PYTHONPATH=src python scripts/modeling/run_deep_feature_weight_decay_forecasting.py --help
PYTHONPATH=src python scripts/modeling/run_deep_feature_weight_decay_forecasting.py --dry-run
```

Reviewers should also confirm:
- `notebooks/modeling/Table1_Forecasting_main.ipynb` is unchanged.
- No raw source CSVs were copied into the repository.
- Large generated prediction outputs remain under ignored results paths.
