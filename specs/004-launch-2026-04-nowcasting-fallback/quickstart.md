# Quickstart: April 2026 Global Nowcasting Launch (Comprehensive-CSV Fallback)

> Production launch, **not** a held-out validation experiment. Global scale only. Uses the comprehensive deep-feature CSV directly (fallback) — results may not be directly comparable to prior canonical 0m model-ready experiments if the feature schema differs.

## 0. Setup

```bash
cd <repo-root>
pip install -e .          # or: export PYTHONPATH="$PYTHONPATH:src"
# Point the comprehensive-source key at your machine's path (git-ignored):
#   configs/paths.local.json
#   { "deep_features_2026_target_corrected_dataset":
#     ".../assembled_IPCCH/features/forecasting_subset_IPCCH_2026_target_corrected_deep_features.csv" }
```

## 1. Preflight — validate without training (always do this first)

```bash
python scripts/modeling/run_launch_nowcasting_2026_04.py --validate-only
```
Checks source readability, `area_id`/`year`/`month`, date construction, pre-cutoff valid-target training rows, April 2026 rows, target derivability, identifier-feature availability, feature-schema alignment, and output-path safety. Writes `input_validation_summary.json` + `feature_schema_report.csv`. **No model is trained.** A source lacking April 2026 rows hard-stops here.

## 2. Mode 1 — train and predict (heavy; requires explicit approval)

```bash
python scripts/modeling/run_launch_nowcasting_2026_04.py --approve-training
```
Trains four cumulative regressors on valid-target rows before 2026-04-01 (incl. 2026-02/03 if present), predicts every eligible April 2026 `area_id`, derives `overall_phase_pred` via `th=0.2`, and writes predictions + run metadata + model artifacts under `results/launch/nowcasting_2026_04/`. Add `--actual-source <csv>` and/or `--spatial-path <file>` to also compare and map.

## 3. Mode 2 — predict with supplied models (no training)

```bash
python scripts/modeling/run_launch_nowcasting_2026_04.py \
  --skip-training --model-artifact-dir results/launch/nowcasting_2026_04/model_artifacts
```

## 4. Mode 3 — report/map from supplied predictions (no training, no prediction)

```bash
python scripts/modeling/run_launch_nowcasting_2026_04.py \
  --skip-prediction --predictions results/launch/nowcasting_2026_04/predictions_2026_04_all_area_id.csv \
  --actual-source <april_actuals.csv> --spatial-path <boundaries> --make-map
```

## 5. Outputs

Machine-readable → `results/launch/nowcasting_2026_04/`:
`run_summary.json`, `launch_config_resolved.json`, `input_validation_summary.json`, `training_data_summary.csv`, `feature_schema_report.csv`, `x_test_area_coverage.csv`, `april_2026_area_id_eligibility.csv`, `x_test_2026_04_all_area_id_model_aligned.{csv,parquet}`, `predictions_2026_04_all_area_id.csv`, `prediction_distribution_summary.csv`, `prediction_validation_summary.json`, `predicted_phase_distribution.csv`, `model_artifacts/phase{2..5}_worse_model.*`, `actual_comparison/…`, `visualizations/april_2026_crisis_map_validation_summary.json` + `…join_validation.csv`.

Human-readable → `reports/launch/nowcasting_2026_04/`:
`launch_summary.md`, `prediction_distribution_summary.md`, `actual_comparison_summary.md`, `data_coverage_and_warnings.md`, `visualizations/ipcch_2026_04_global_actual_vs_predicted_crisis_map.png`.

## 6. Acceptance smoke checks

- `--help` and `--validate-only` run with no training (SC-004).
- Predictions cover 100% of eligible April 2026 areas; every row has 4 cumulative preds + `overall_phase_pred ∈ {1..5}` from finite validated values (SC-001/002/002a).
- Comparison (if actuals given) reports denominators and scopes metrics to the April covered subset, labeled descriptive-only (SC-006).
- Two-panel map: 2 vertical subplots; validation summary lists unmatched IDs and reconciles counts; duplicate spatial keys hard-fail; no overwrite without `--overwrite` (SC-007/008).
- All outputs under `results/launch/...` and `reports/launch/...` (SC-009).
