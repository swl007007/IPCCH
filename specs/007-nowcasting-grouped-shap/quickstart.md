# Quickstart: Nowcasting Grouped SHAP Values

## Prerequisites

- Run from the repository root.
- Use an environment with the project package importable, for example `PYTHONPATH=src` or editable install.
- Ensure the SHAP dependency is available before enabling grouped SHAP.
- Configure the six-category crosswalk through the project path mechanism or pass an explicit path override.

## Check CLI Help

```bash
PYTHONPATH=src python scripts/modeling/run_launch_nowcasting_2026_04.py --help
```

Expected:
- Help includes `--compute-grouped-shap`.
- Help includes grouped SHAP crosswalk path/key options if implemented.

## Disabled Behavior Check

Run the existing nowcasting launch without grouped SHAP using the normal project arguments.

Expected:
- No grouped SHAP artifacts are written.
- Existing prediction/model/report behavior remains unchanged.
- Crosswalk path and SHAP dependency are not required solely because the feature exists.

## Supported Grouped SHAP Run

Run a train-and-predict Mode 1 launch with grouped SHAP enabled.

```bash
PYTHONPATH=src python scripts/modeling/run_launch_nowcasting_2026_04.py \
  --compute-grouped-shap \
  --grouped-shap-crosswalk-path "<path-to-forecasting_2026_model_ready_variable_six_category_crosswalk.csv>" \
  --approve-training \
  [other normal launch arguments]
```

Expected:
- The fitted `phase3_worse` model is explained using the phase3 training matrix.
- Console output reports six-category matched count, `weather forecast` count, unmatched count, unmatched attribution share when available, and output paths.
- Results include mapping, grouped SHAP matrix/long output, diagnostics when applicable, and metadata.
- Reports include a grouped SHAP heatmap for available scope data.

## Unsupported Mode Checks

Supplied-model Mode 2 with grouped SHAP:

```bash
PYTHONPATH=src python scripts/modeling/run_launch_nowcasting_2026_04.py \
  --skip-training \
  --compute-grouped-shap \
  [other normal supplied-model arguments]
```

Expected:
- Command rejects the request with a clear message that grouped SHAP currently supports train-and-predict runs only.

Prediction-only Mode 3 with grouped SHAP:

```bash
PYTHONPATH=src python scripts/modeling/run_launch_nowcasting_2026_04.py \
  --skip-prediction \
  --compute-grouped-shap \
  [other normal supplied-prediction arguments]
```

Expected:
- Command rejects the request with a clear message that grouped SHAP requires a fitted `phase3_worse` model and corresponding training feature matrix.

## Suggested Validation Commands

```bash
PYTHONPATH=src pytest -q tests/unit/test_forecasting_shap.py
PYTHONPATH=src pytest -q tests/unit/test_launch_nowcasting.py
PYTHONPATH=src pytest -q tests/smoke/test_weight_decay_shap_cli.py
```

Add or run nowcasting-specific CLI smoke tests once implemented.

Do not run full model training or full SHAP computation unless explicitly approved.
