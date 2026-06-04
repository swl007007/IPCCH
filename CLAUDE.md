# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

IPCCH is a machine learning pipeline for forecasting food security phases (IPC/CH classifications, phases 1-5) across sub-Saharan Africa and other food-insecure regions. It uses XGBoost regression models trained on geospatial and socioeconomic features to predict the proportion of population in each food crisis phase at the area level.

The project is developed primarily through Jupyter notebooks for experimentation, with Python scripts for reusable pipeline stages such as regional model training, error analysis, and label quality analysis.

## Key Commands

```bash
# Install dependencies
pip install -e .
pip install numpy pandas xgboost scikit-learn matplotlib seaborn shap tqdm geopandas contextily cleanlab geemap earthengine-api scipy

# If not installed editable, run scripts from the repo root with PYTHONPATH=src
export PYTHONPATH="${PYTHONPATH}:src"

# Run regional model training
PYTHONPATH=src python scripts/modeling/run_region_models.py \
    --dataset "../1.Source Data/forecasting_subset_IPCCH_v1210.csv" \
    --region-map "data/reference/area_id_country_region_mapping.csv" \
    --out "results/experiments/region_vs_global_model_comparison/output_region_models" \
    --years 2022 2023 2024 --seed 42

# Compare global vs regional models
PYTHONPATH=src python scripts/modeling/compare_global_vs_regional_by_region.py \
    --regional-dir "results/experiments/region_vs_global_model_comparison/output_region_models/predictions" \
    --global-dir "results/predictions/forecasting" \
    --mapping "data/reference/area_id_country_region_mapping.csv" \
    --out-dir "results/experiments/region_vs_global_model_comparison/region_compare"

# Run label quality analysis
PYTHONPATH=src python scripts/preprocessing/cleanlab_label_analysis.py \
    --dataset "../1.Source Data/forecasting_subset_IPCCH_v1210_processed.csv" \
    --output-dir "results/experiments/cleanlab"

# Generate cleanlab visualization report
PYTHONPATH=src python scripts/reporting/cleanlab_report_visualization.py \
    --input-dir "results/experiments/cleanlab" \
    --output-dir "reports/cleanlab"

# Run geographic error analysis
PYTHONPATH=src python scripts/postprocessing/ipc_error_analysis.py \
    --prediction-dir "results/predictions/forecasting" \
    --output-dir "results/maps/error_rate" \
    --figures-dir "reports/figures/error_rate_map"
```

The shared Python utilities live in `src/ipcch/`. Scripts and notebooks should import from `ipcch.food_crisis_functions`, not from a root-level `food_crisis_functions.py`.

## Architecture

### Model Design

The system trains **4 separate XGBoost regressors** per model configuration, one for each cumulative phase target:
- `phase2_worse` = phase2 + phase3 + phase4 + phase5 (% population)
- `phase3_worse` = phase3 + phase4 + phase5
- `phase4_worse` = phase4 + phase5
- `phase5_worse` = phase5

Predicted probabilities are converted to discrete phase classifications (1-5) using a **threshold of 0.2** applied top-down (phase 5 first) via `convert_prob_to_phase()` in `src/ipcch/food_crisis_functions.py`.

Experimental workflows may additionally train a multi-class XGBoost classifier directly on class labels derived from `overall_phase`. This is additive only and must not silently replace the canonical 4-regressor workflow or its reported metrics. Classifier workflows must declare their class mapping before implementation, such as `five_class`, `three_class_123_45`, `four_class_123_45`, or `binary_12_3plus`, and outputs must be labeled with the selected mapping.

When `overall_phase` or any derived phase class is the target, exclude target-related columns from model features, including `phase1_percent`, `phase2_percent`, `phase3_percent`, `phase4_percent`, and `phase5_percent`. Any target-derived or contemporaneous phase columns used only for label construction must be removed from the feature matrix before training.

### Hyperparameters

Four JSON hyperparameter files control XGBoost configuration:
- `configs/forecasting_hyperparameters.json` — Forecasting model, phases 2, 4, 5
- `configs/forecasting_hyperparameters_p3.json` — Forecasting model, phase 3 (separate tuning)
- `configs/contemporaneous_hyperparameters.json` — Nowcasting model, phases 2, 4, 5
- `configs/contemporaneous_hyperparameters_p3.json` — Nowcasting model, phase 3

Machine-specific external data paths can be placed in ignored `configs/paths.local.json`; `configs/paths.example.json` documents the expected keys.

### Temporal Validation

Models use strict temporal splits with no future data leakage. Each feature must declare its split policy before implementation:
- **All-prior-history annual holdout:** train on all eligible records strictly before January 1 of the test year, test on that test year.
- **Fixed-window annual holdout:** train on a declared historical window that ends strictly before January 1 of the test year, test on that test year.
- Test-year records must not influence fitting, tuning, feature scaling, threshold selection, label mapping calibration, sample-weight calibration, model selection, or metrics outside their own test evaluation.

### Metrics

Four canonical regressor metrics computed via `all_metrics()`:
- **Accuracy**: overall classification accuracy across all 5 phases
- **Sensitivity**: recall for phase 3+ (crisis detection rate)
- **Precision**: precision for phase 3+ predictions
- **R² (phase 3+)**: R² score on `phase3_worse` continuous predictions

Experimental classifier workflows must report metrics appropriate to the declared class mapping. At minimum, report overall accuracy, macro-F1, weighted-F1, per-class precision/recall/F1, and a confusion matrix. For mappings with a crisis-positive concept, also report binary crisis metrics for `3+` versus `1-2` when applicable. These metrics must use only the declared temporal split policy.

### Interpretability and SHAP Workflows

Interpretability artifacts intended for comparison or reporting must record the model target, sample source, feature matrix construction, fitted feature order, aggregation metric, and relevant input artifact paths in machine-readable metadata. Comparison helpers should combine artifacts from explicit paths or metadata-recorded paths, not unconstrained recursive directory scans.

Nowcasting grouped SHAP is optional and enabled with `--compute-grouped-shap` in `scripts/modeling/run_launch_nowcasting_2026_04.py`. It currently supports train-and-predict runs only, explains only the fitted `phase3_worse` cumulative regressor, and must use the exact phase-3 training feature matrix with the fitted feature order. It groups features by the six-category crosswalk plus a seventh group named exactly `weather forecast`; runtime weather forecast proxy features take precedence before crosswalk matching. Unmatched features are diagnostics-only and must not be assigned to an `other` fallback group unless a future spec explicitly changes that. Scope comparisons use canonical order `0m`, `3m`, `6m`, `12m`.

### Spec Kit Artifact Alignment

When updating Spec Kit artifacts, use the current implementation plus explicit user design clarifications as the baseline. Record implementation-vs-design drift in `evidence.md` and `task-evidence-trace.md`; do not change `tasks.md` checkboxes as proof of implementation or validation. `Evidence Status: Ready` means the evidence artifact is ready for grounding only; if `Validation Status` is `Not Executed`, do not claim tests, CLI checks, artifact generation, or final acceptance were validated.

Current feature baselines to preserve: Spec002 alert-risk maps are single-scope CLI runs (`--scope global` or an ISO3 such as `SOM`) and global/Somalia deliverables require separate invocations; Spec005 launch scopes are `0`, `3`, `6`, and `12` months, with April 2026 + `12m` targeting April 2027; Spec006 phase-3 SHAP runs one selected `--fs` per invocation, and full four-scope 96-row/four-heatmap deliverables are assembled across `fs0`/`fs1`/`fs2`/`fs3` runs or downstream aggregation.

### Core Package: `src/ipcch/`

Shared utility library imported by notebooks and scripts. Key files:
- `src/ipcch/food_crisis_functions.py` — model utilities, metrics, feature constants, Earth Engine helpers
- `src/ipcch/paths.py` — repository-root paths, config/data/result/report directories, and external data path defaults

Key exports from `food_crisis_functions.py`:

**Model pipeline functions:**
- `convert_prob_to_phase(y_pred_test, th=0.2)` — Probability-to-phase classification (top-down threshold at 0.2)
- `all_metrics(y_test, y_pred, cm, y_pred_test)` — Compute accuracy, sensitivity, precision, and R²
- `calculate_finetune_metric(y_test, y_pred, cm, y_pred_test)` — Combined metric for hyperparameter tuning
- `calculate_fine_metric(accuracy_list, sensitivity_list, precision_list, r2_list)` — Aggregate metrics across folds
- `forecasting_pipeline(train_df, test_df, i)` — Prepare features/targets for phase `i`

**Data utility functions:**
- `drop_cols(df, cols_to_drop, patterns_to_drop)` — Drop columns by name or regex pattern
- `match_nearest(df_left, df_match, dat)` — Spatial nearest-neighbor matching using KDTree
- `plot_missing_value(df)` — Heatmap visualization of missing data
- `extract_from_location(image_collection, location, band, start_time, end_time)` — Extract Earth Engine imagery statistics at point locations
- `upload_to_bucket(bucket_path, collection, gsutil_path)` — Batch upload GeoTIFF files to Google Earth Engine

**Feature set constants:**
- `X_drop_set` — Columns to drop during feature engineering
- `X_stable_set` — Time-invariant features

### Data Flow

```
External source CSV (../1.Source Data/forecasting_subset_IPCCH_v1210.csv)
  → Preprocessing notebooks/scripts
  → Feature engineering and temporal splits
  → XGBoost training (4 models per configuration)
  → Probability predictions → convert_prob_to_phase() → Phase 1-5
  → Metrics computation
  → Machine-readable outputs in results/
  → Human-readable figures/reports in reports/
```

### Regional vs Global Models

`scripts/modeling/run_region_models.py` splits data by geographic region using `data/reference/area_id_country_region_mapping.csv` and trains independent models per region. `scripts/modeling/compare_global_vs_regional_by_region.py` computes delta metrics. Results are stored under `results/experiments/region_vs_global_model_comparison/`. Known challenge: many region-year combinations have sparse data (see `docs/ISSUES_FIXED.md`).

## Directory Structure

```
IPCCH/
├── pyproject.toml                     # Editable package install metadata
├── configs/                           # Hyperparameters and path examples
│   ├── forecasting_hyperparameters.json
│   ├── forecasting_hyperparameters_p3.json
│   ├── contemporaneous_hyperparameters.json
│   ├── contemporaneous_hyperparameters_p3.json
│   └── paths.example.json
├── data/
│   └── reference/
│       └── area_id_country_region_mapping.csv
├── docs/                              # Documentation and architecture diagrams
├── notebooks/
│   ├── modeling/                      # Table1_* and prediction notebooks
│   ├── preprocessing/                 # Data preparation notebooks
│   └── reporting/                     # Figure/country/map notebooks
├── reports/                           # Human-readable generated artifacts
│   ├── cleanlab/
│   └── figures/
├── results/                           # Machine-readable generated outputs
│   ├── experiments/
│   ├── main/
│   ├── maps/
│   └── predictions/
├── scripts/
│   ├── modeling/
│   ├── preprocessing/
│   ├── postprocessing/
│   └── reporting/
├── src/
│   └── ipcch/
│       ├── __init__.py
│       ├── food_crisis_functions.py
│       └── paths.py
└── TODO.txt
```

### Notebook Organization

**Modeling notebooks:** `notebooks/modeling/`
- `Table1_Forecasting_main.ipynb` — Primary baseline forecasting model
- `Table1_Nowcasting_two_layer.ipynb` — Contemporaneous/nowcasting model
- `Table1_Forecasting_main_*.ipynb` — Forecasting variants including ablation, rolling, cleanlab, lag, Nigeria-specific, IPC/CH split, phase 4, 6-month, without MOM, and two-regression experiments
- `Table1_Forecast_phasechange*.ipynb` — Phase transition detection models
- `Table1_new_baseline*.ipynb` — Naive baseline comparisons
- `Forecasting_prediction.ipynb` — Generate full prediction CSVs for 2022-2024

**Preprocessing notebooks:** `notebooks/preprocessing/`
- `area_id_country_table.ipynb` — Build area_id to country mapping
- `combine_IPC_CH.ipynb` — Merge IPC and CH datasets
- `IPCCH_forecasting_prepare.ipynb` — Main forecasting dataset preparation

**Reporting notebooks:** `notebooks/reporting/`
- `Figure11_12_Feature_Importance_Forecasting.ipynb` — SHAP feature importance plots
- `Figure_percentage_a_experiencing_p4.ipynb` — Phase 4+ population analysis
- `country_performance_disaggregate.ipynb` — Country-level performance breakdown
- `geographical_vis.ipynb` — Geographic visualization of results

## Important Conventions

- External source data lives outside this repo under `Analysis/1.Source Data/`; do not copy raw source data into the repository.
- Use `configs/paths.local.json` for machine-specific data paths; it is ignored by git.
- `configs/*.json` model hyperparameters and `data/reference/area_id_country_region_mapping.csv` are trackable project inputs.
- Large generated prediction CSVs live under `results/predictions/` and are ignored.
- Machine-readable generated outputs belong under `results/`; human-readable figures and reports belong under `reports/`.
- Experimental classifier outputs must be separated from canonical regressor outputs and labeled with the selected class mapping.
- The `area_id` column is the primary spatial identifier linking observations to regions, countries, and geographic coordinates.
- `overall_phase` is the ground-truth phase classification; `overall_phase_pred` is the model prediction.
- `CLAUDE.md` itself is listed in `.gitignore` as a local development aid.
- The editable architecture diagram is `docs/IPCCH.drawio`.
- Do not execute heavy model-training notebook cells unless explicitly requested; use import checks, CLI `--help`, and small smoke tests for validation.
- Classifier workflows must expose class mapping via CLI or config, preferably `--phase-class-map`, rather than requiring notebook cell edits.

<!-- SPECKIT START -->
For additional context about the active feature, read the current plan:
`specs/007-nowcasting-grouped-shap/plan.md`
<!-- SPECKIT END -->
