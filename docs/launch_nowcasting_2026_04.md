# April 2026 Global Nowcasting Launch (Comprehensive-CSV Fallback)

Production launch (NOT a held-out validation experiment) that predicts April 2026
food-crisis phases for every eligible global `area_id` using one comprehensive
deep-feature CSV for both training and X_test. Canonical four-regressor
cumulative-phase workflow; phases via `th=0.2`. See
`specs/004-launch-2026-04-nowcasting-fallback/` for the full spec/plan/tasks.

## Code

- `src/ipcch/launch_nowcasting.py` — source validation, training-row / April X_test
  construction, identifier-feature application, feature-schema report, training,
  prediction validation (clip/non-finite), phase derivation (`th=0.2`), outputs, reports.
- `src/ipcch/launch_comparison.py` — April-only, coverage-aware, descriptive comparison.
- `src/ipcch/launch_visualizations.py` — two-panel actual-vs-predicted crisis map
  (recording spatial join; duplicate keys hard-fail; unmatched recorded).
- `scripts/modeling/run_launch_nowcasting_2026_04.py` — CLI.

## CLI (complete flag list in `specs/.../contracts/cli.md`)

```bash
# 1. Preflight (no training):
python scripts/modeling/run_launch_nowcasting_2026_04.py --validate-only

# 2. Mode 1 — train & predict (heavy; approval-gated):
python scripts/modeling/run_launch_nowcasting_2026_04.py --approve-training \
  [--actual-source <april_actuals.csv>] [--spatial-path <boundaries>]

# 3. Mode 2 — predict with supplied models:
python scripts/modeling/run_launch_nowcasting_2026_04.py \
  --skip-training --model-artifact-dir results/launch/nowcasting_2026_04/model_artifacts

# 4. Mode 3 — report/map from supplied predictions:
python scripts/modeling/run_launch_nowcasting_2026_04.py \
  --skip-prediction --predictions results/launch/nowcasting_2026_04/predictions_2026_04_all_area_id.csv \
  --actual-source <april_actuals.csv> --spatial-path <boundaries>
```

The comprehensive source is workspace-local: add the key
`deep_features_2026_target_corrected_dataset` to `configs/paths.local.json`
(see `configs/paths.example.json`) or pass `--comprehensive-source <path>`.
Hyperparameters default to `configs/forecasting_hyperparameters.json` (+`_p3`).
`th` is fixed at 0.2. Heavy Mode-1 training never runs without `--approve-training`.

Outputs: machine-readable under `results/launch/nowcasting_2026_04/`,
human-readable under `reports/launch/nowcasting_2026_04/`.
