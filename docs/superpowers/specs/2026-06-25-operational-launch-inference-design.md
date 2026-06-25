# Operational Launch Inference Design

Date: 2026-06-25

## Purpose

Build a production-ready operational inference path for IPCCH launch predictions.
The research IPCCH repository remains responsible for one-time model training
and model-package export. The `IPCCH_monthly_operational` package is responsible
only for monthly inference from one month of production feature input.

The first model package targets April 2026. It trains and exports fixed
launch-mode models for three horizons:

- `0m`: feature month predicts the same month.
- `6m`: feature month predicts feature month plus 6 calendar months.
- `12m`: feature month predicts feature month plus 12 calendar months.

The production package must later accept one monthly input file, such as a July
2026 input table, and emit exactly six primary delivery files: one prediction
sheet and one map for each of `0m`, `6m`, and `12m`.

## Confirmed Decisions

- Use the current launch-mode pipeline, not the annual holdout forecasting
  experiment script.
- Do not use forecasted-weather proxy features in the production-default model
  package or monthly inference path.
- Keep model training out of `IPCCH_monthly_operational`.
- Add a production-side `model_pipeline/` directory for pure inference scripts
  and minimal runtime code.
- Add production-side model artifacts under `model_artifacts/`, with separate
  subdirectories for `scope_0m`, `scope_6m`, and `scope_12m`.
- Write monthly delivery outputs under
  `Outcome/ipcch_unified/predictions/YYYYMM/`.
- Treat Docker and cloud deployment as a later phase. This design reserves a
  clean CLI entrypoint and explicit inputs/outputs so containerization is
  straightforward later.

## Out of Scope

- Dockerfile, cloud scheduler, cloud storage orchestration, and managed runtime
  deployment.
- Automated monthly source-data download or feature-building changes.
- Recurring retraining inside the production package.
- The annual `run_deep_feature_weight_decay_forecasting.py` holdout workflow.
- Forecasted-weather inference dependencies.

## Architecture

### Research Preparation Layer

The research repository performs the one-time preparation run:

1. Read the completed historical panel:
   `IPCCH_monthly_operational/Outcome/ipcch_unified/raw/IPCCH_2026_completed.csv`.
2. Read the operational geometry:
   `IPCCH_monthly_operational/Outcome/ipcch_unified/spatial/ipcch_admin_geometry.shp`.
3. Adapt the operational panel to the launch schema by deriving
   `area_id = admin_code` and preserving `admin_code` as a reporting and join
   alias.
4. Generate a feature contract that defines the production-safe feature set and
   compatibility behavior.
5. Train three launch-mode models with scopes `0`, `6`, and `12`, using April
   2026 as the launch feature month and `training_cutoff = 2026-04-01`.
6. Export model weights and metadata to the production package.
7. Generate the April 2026 baseline delivery outputs from the exported package
   to prove the package can run production-style inference.

### Production Inference Layer

`IPCCH_monthly_operational` runs monthly inference only:

1. Read one monthly feature input CSV, normally from
   `Outcome/ipcch_unified/model_input/ipcch_monthly_base_input_YYYYMM.csv`.
2. Validate that the input represents one feature month.
3. Adapt identifiers by deriving or validating `area_id`, with `admin_code` kept
   as a compatibility alias.
4. Apply the model-package feature contract to build a model-ready feature
   matrix.
5. Load fixed model artifacts for `0m`, `6m`, and `12m`.
6. Generate prediction sheets and predicted crisis maps for all three horizons.
7. Write audit reports for feature compatibility, run configuration, and map
   join validation.

## Production Package Layout

The production package should gain these paths:

```text
IPCCH_monthly_operational/
  model_pipeline/
    run_operational_launch_inference.py
    ipcch_launch_runtime/
      adapters.py
      feature_contract.py
      inference.py
      model_package.py
      visualization.py
  model_artifacts/
    launch_2026_04/
      model_package_manifest.json
      scope_0m/
        phase2_worse_model.json
        phase3_worse_model.json
        phase4_worse_model.json
        phase5_worse_model.json
        feature_columns.json
        feature_contract.csv
        model_metadata.json
      scope_6m/
        phase2_worse_model.json
        phase3_worse_model.json
        phase4_worse_model.json
        phase5_worse_model.json
        feature_columns.json
        feature_contract.csv
        model_metadata.json
      scope_12m/
        phase2_worse_model.json
        phase3_worse_model.json
        phase4_worse_model.json
        phase5_worse_model.json
        feature_columns.json
        feature_contract.csv
        model_metadata.json
  Outcome/ipcch_unified/predictions/YYYYMM/
    ipcch_launch_YYYYMM_scope_0m_predictions.csv
    ipcch_launch_YYYYMM_scope_0m_map.png
    ipcch_launch_YYYYMM_scope_6m_predictions.csv
    ipcch_launch_YYYYMM_scope_6m_map.png
    ipcch_launch_YYYYMM_scope_12m_predictions.csv
    ipcch_launch_YYYYMM_scope_12m_map.png
```

`model_pipeline/` contains the pure inference entrypoint and the minimum runtime
code needed to adapt input data, apply feature compatibility rules, load models,
write predictions, and render maps. It must not contain training entrypoints.

`model_artifacts/launch_2026_04/` is the first fixed model package. The package
manifest records source data paths, source hashes where practical, training
cutoff, launch month, horizon list, threshold, package version, runtime
requirements, and whether forecasted weather was used. For this package,
forecasted weather must be recorded as disabled.

## Feature Compatibility Contract

Future monthly inputs may contain only a subset of the columns available in the
2026 completed panel. The model package must therefore include a
`feature_contract.csv` that tells production inference how each model feature is
handled.

Each model feature must have one compatibility category:

- `required`: must be present in the monthly input; missing values above the
  configured tolerance fail validation.
- `derived`: computed by the inference adapter from available input columns.
- `static_join`: joined from a stable package asset keyed by `area_id`.
- `carry_forward`: filled from an approved latest-known source bundled with or
  referenced by the package.
- `median_impute`: filled from training-period statistics stored in model
  metadata.
- `unsupported` or `excluded`: not allowed to be referenced by exported model
  weights.

The training/export stage must not blindly train on every column in
`IPCCH_2026_completed.csv`. It must train on a production-safe subset:

- Production core features expected to be available monthly.
- Slow-moving or static features that can be joined reliably.
- Features with explicit and documented fallback rules.

Features that are likely unavailable in future monthly inputs and cannot be
reasonably filled must be excluded before training.

Production inference writes both CSV and JSON compatibility reports. These
reports record input columns, model-required columns, filled columns, fill
methods, missing rates, thresholds, and final pass/fail status.

## CLI Contract

The production command should be non-interactive and future container-friendly:

```bash
python model_pipeline/run_operational_launch_inference.py \
  --input Outcome/ipcch_unified/model_input/ipcch_monthly_base_input_YYYYMM.csv \
  --model-package model_artifacts/launch_2026_04 \
  --spatial-path Outcome/ipcch_unified/spatial/ipcch_admin_geometry.shp \
  --output-dir Outcome/ipcch_unified/predictions/YYYYMM \
  --feature-month YYYY-MM
```

Useful flags:

- `--validate-only`: validate input, model package, feature contract, geometry,
  and output conflicts without prediction.
- `--overwrite`: allow replacement of existing outputs.
- `--no-map`: generate prediction sheets and audit outputs only.
- `--actual-source`: optional actual outcomes for same-month comparison when
  available. Production delivery still counts one map per horizon.

The default mode runs all three horizons in the package. A later implementation
may add `--scopes 0 6 12`, but the initial package should treat all three
deliverables as the normal operational contract.

## Monthly Delivery Outputs

For feature month `YYYY-MM`, with compact label `YYYYMM`, the six primary files
are:

```text
Outcome/ipcch_unified/predictions/YYYYMM/
  ipcch_launch_YYYYMM_scope_0m_predictions.csv
  ipcch_launch_YYYYMM_scope_0m_map.png
  ipcch_launch_YYYYMM_scope_6m_predictions.csv
  ipcch_launch_YYYYMM_scope_6m_map.png
  ipcch_launch_YYYYMM_scope_12m_predictions.csv
  ipcch_launch_YYYYMM_scope_12m_map.png
```

Prediction sheets must include at least:

- `area_id`
- `admin_code` when available
- `feature_period`
- `target_period`
- `scope_months`
- `phase2_worse_pred`
- `phase3_worse_pred`
- `phase4_worse_pred`
- `phase5_worse_pred`
- `phase2_pred`
- `phase3_pred`
- `phase4_pred`
- `phase5_pred`
- `overall_phase_pred`
- model package identifier
- source input path or source input hash

Maps default to predicted-only crisis maps. If target-period actuals are
available and supplied, the runtime may render an actual-vs-predicted view for
that horizon, but the primary delivery contract remains one map file per
horizon.

Audit files are expected but are not counted among the six primary delivery
files:

- `run_summary.json`
- `feature_compatibility_report.csv`
- `feature_compatibility_report.json`
- `map_join_validation.csv`
- `map_join_validation.json`

## Error Handling

Production inference must fail fast in these cases:

- The input is missing `admin_code` or `area_id`, `year`, or `month`.
- The input contains multiple feature months unless a future batch mode is
  explicitly added.
- A `required` feature is absent or exceeds the contract missing-rate threshold.
- A model references a feature marked `unsupported` or `excluded`.
- A `median_impute`, `static_join`, or `carry_forward` rule lacks the required
  metadata or lookup asset.
- Filled-feature missingness exceeds the configured threshold.
- The shapefile cannot be loaded or contains no usable `area_id` or
  `admin_code` join key.
- Spatial join coverage falls below the configured threshold.
- A primary delivery file already exists and `--overwrite` is not supplied.

Warnings are acceptable for documented fallback use when thresholds are
satisfied. Warnings must appear in the compatibility report and run summary.

## Testing Strategy

Unit tests:

- `admin_code` to `area_id` adaptation.
- Single-month input validation.
- Feature contract parsing and enforcement.
- `required`, `derived`, `static_join`, `carry_forward`, `median_impute`, and
  `unsupported` behavior.
- Target-period calculation for `0m`, `6m`, and `12m`.
- Output-path naming and overwrite protection.

Smoke tests:

- Use a small synthetic monthly input and dummy model artifacts to run the full
  production CLI and confirm all six primary delivery paths are planned or
  written.
- Validate that `--validate-only` checks package, input, geometry, and conflicts
  without prediction.

Integration validation:

- Use April 2026 operational input and the exported real model package.
- Run production inference for `0m`, `6m`, and `12m`.
- Confirm prediction schema, feature order, feature compatibility reports, map
  join validation, and output naming match the delivery contract.
- Compare April 2026 production-style predictions with the research export
  outputs to detect feature-order or adapter drift.

## Future Docker and Cloud Readiness

This design intentionally keeps the runtime compatible with later Docker and
cloud execution:

- One non-interactive CLI entrypoint.
- Explicit input CSV, model package, geometry, output directory, and feature
  month parameters.
- All model metadata and feature fallback statistics shipped in the model
  package.
- No training step and no forecasted-weather dependency in the production
  inference command.
- Machine-readable run summaries suitable for cloud logging.

The Docker/cloud implementation should be specified separately after the local
production inference package is verified.
