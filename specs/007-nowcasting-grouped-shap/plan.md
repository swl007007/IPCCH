# Implementation Plan: Nowcasting Grouped SHAP Values

**Branch**: `[007-nowcasting-grouped-shap]` | **Date**: 2026-06-03 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/007-nowcasting-grouped-shap/spec.md`

## Summary

Add an optional `--compute-grouped-shap` workflow to the April 2026 nowcasting launch command. The implementation will explain only the fitted `phase3_worse` model using its exact training feature matrix, map model features to the six-category crosswalk plus `weather forecast`, write grouped SHAP matrix/mapping/diagnostic metadata artifacts, and render grouped SHAP heatmaps by forecasting scope without changing default nowcasting behavior.

## Technical Context

**Language/Version**: Python 3.x, using the existing IPCCH package layout  
**Primary Dependencies**: pandas, numpy, xgboost model objects, shap, matplotlib/seaborn-style plotting through existing SHAP helpers, existing `ipcch.paths` and nowcasting modules  
**Storage**: File artifacts only: CSV/JSON under `results/`, PNG/CSV report artifacts under `reports/`; no database  
**Testing**: pytest unit tests and smoke tests; CLI `--help`; static/import checks; no heavy training unless explicitly approved  
**Target Platform**: Local/WSL repository CLI workflow with `PYTHONPATH=src` or editable install  
**Project Type**: Python package plus CLI wrapper script  
**Performance Goals**: Preserve grouped-SHAP-disabled runtime and predictions; grouped SHAP may add explainability cost only when explicitly enabled  
**Constraints**: No hardcoded local absolute paths in production defaults; no prediction-only or supplied-model grouped SHAP in this feature; exact `phase3_worse` training feature rows and feature order required; generated outputs must remain under `results/` and `reports/`  
**Split Policy**: Grouped SHAP inherits the existing nowcasting train-and-predict split policy and introduces no new train/test/evaluation split, no new target definition, and no new predictive metrics. It computes interpretability artifacts from the fitted `phase3_worse` model’s existing training feature matrix only.  
**Scale/Scope**: One nowcasting scope per launch invocation, with output schema supporting combined `0m`, `3m`, `6m`, `12m` heatmaps when scope outputs are available

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

1. **Temporal validation**: PASS. Grouped SHAP inherits the existing nowcasting train-and-predict split policy and introduces no new train/test/evaluation split, no new target definition, and no new predictive metrics. SHAP explains the already fitted `phase3_worse` model using only the corresponding training matrix.
2. **Reusable code**: PASS. Reusable mapping, aggregation, matrix, and plotting helpers will live under `src/ipcch/`, reusing/extending `forecasting_shap.py` and integrating through `launch_nowcasting.py`.
3. **Path handling**: PASS. Crosswalk resolution will use an explicit CLI path override and existing `ipcch.paths`/configured external-key mechanisms; the user-provided Windows path is accepted as an override, not hardcoded as the production default.
4. **Artifact separation**: PASS. Machine-readable grouped SHAP CSV/JSON artifacts will go under launch `results/`; human-readable heatmaps/report artifacts will go under launch `reports/`.
5. **Execution discipline**: PASS. Planning and validation use static inspection, `--help`, unit tests, and smoke tests; full nowcasting/SHAP runs require explicit user approval.
6. **Review-gated inputs**: PASS. Planned changes touch `src/ipcch/` and CLI/tests, so they require normal review. No tracked source data changes are planned.
7. **Classifier workflows, if present**: PASS. Not applicable; the feature explains the canonical cumulative regressor target `phase3_worse` and does not add a classifier.

## Project Structure

### Documentation (this feature)

```text
specs/007-nowcasting-grouped-shap/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── nowcasting-grouped-shap-cli.md
└── tasks.md
```

### Source Code (repository root)

```text
src/ipcch/
├── forecasting_shap.py          # Extend/generalize grouped SHAP mapping, aggregation, diagnostics, matrix, heatmap helpers while preserving existing APIs
└── launch_nowcasting.py         # Add nowcasting grouped SHAP config, output paths, training-matrix hook, summary/report metadata

scripts/modeling/
└── run_launch_nowcasting_2026_04.py  # Expose CLI flags and reject unsupported modes

tests/
├── unit/
│   ├── test_forecasting_shap.py      # Preserve existing forecasting behavior; add helper coverage if appropriate
│   └── test_launch_nowcasting.py     # Add nowcasting grouped SHAP mapping/output/mode tests
└── smoke/
    └── test_launch_nowcasting_grouped_shap_cli.py
```

**Structure Decision**: Keep shared SHAP behavior in `src/ipcch/` and expose user-facing flags in the existing April 2026 nowcasting CLI wrapper. Smoke coverage for this feature will live in `tests/smoke/test_launch_nowcasting_grouped_shap_cli.py`. Existing `tests/smoke/test_weight_decay_shap_cli.py` remains a reference pattern only and should not be modified for this feature unless backward-compatibility maintenance requires it. Do not introduce a new service, dependency layer, or notebook workflow.

## Phase 0: Research Summary

See [research.md](research.md). All planning decisions are resolved without `NEEDS CLARIFICATION` markers.

## Phase 1: Design Summary

See [data-model.md](data-model.md), [contracts/nowcasting-grouped-shap-cli.md](contracts/nowcasting-grouped-shap-cli.md), and [quickstart.md](quickstart.md).

## Implementation Approach

1. Extend grouped SHAP helper surface while preserving forecasting behavior:
   - Reuse `compute_phase3_shap_values`, `load_crosswalk`, feature-order validation, and existing per-feature/diagnostic conventions.
   - The nowcasting launch workflow derives the `weather_forecast_features` seed set from existing nowcasting weather proxy helpers and passes that explicit set into generic grouped-SHAP mapping helpers. The generic helpers in `src/ipcch/forecasting_shap.py` apply those seeds before crosswalk matching but do not import or depend on `src/ipcch/launch_nowcasting.py`.
   - Add generalized seven-group aggregation and scope-by-group matrix/heatmap helpers without breaking existing six-category/year-matrix tests.

2. Integrate grouped SHAP into nowcasting train-and-predict flow:
   - Add configuration fields/helpers in `src/ipcch/launch_nowcasting.py`.
   - Build the SHAP input matrix as `train_featured.dropna(subset=["phase3_worse"]).loc[:, feature_columns]` after the fitted `phase3_worse` model is available.
   - Save mapping, grouped matrix/long outputs, unmatched diagnostics, metadata, and heatmap paths under existing launch output/report roots.

3. Expose CLI behavior:
   - Add `--compute-grouped-shap` and crosswalk path/key options to `scripts/modeling/run_launch_nowcasting_2026_04.py`.
   - Keep disabled behavior unchanged and avoid resolving/importing SHAP-only dependencies when the flag is absent.
   - Reject `--skip-training` and prediction-only/supplied-prediction mode when grouped SHAP is requested.

4. Add validation coverage:
   - Unit tests for weather forecast precedence, normalized matching, ambiguous matches, unmatched diagnostics, seven-row grouped outputs, and mode rejection.
   - Smoke test for CLI help and disabled-path behavior.
   - Existing forecasting SHAP tests must continue to pass.

## Constitution Check (Post-Design)

1. **Temporal validation**: PASS. Design inherits the existing nowcasting train-and-predict split policy, only reads the phase3 training matrix for explanation, and does not introduce new splits, targets, evaluation metrics, or training/evaluation behavior.
2. **Reusable code**: PASS. Shared helpers remain in `src/ipcch/`; CLI wrapper only parses/propagates options.
3. **Path handling**: PASS. Crosswalk paths are CLI/config resolved; no production hardcoded local absolute path.
4. **Artifact separation**: PASS. CSV/JSON outputs under `results/`; heatmaps/reports under `reports/`.
5. **Execution discipline**: PASS. Planned validation is help/unit/smoke unless user approves full launch.
6. **Review-gated inputs**: PASS. `src/ipcch/` changes are explicit and review-gated.
7. **Classifier workflows**: PASS. Not applicable.

## Complexity Tracking

No constitution violations require justification.
