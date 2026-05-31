# Implementation Plan: Phase-3 SHAP Six-Category Feature Importance

**Branch**: `006-phase3-shap-importance` | **Date**: 2026-05-31 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/006-phase3-shap-importance/spec.md`

## Summary

Add optional post-hoc SHAP explainability to the existing deep-feature weight-decay forecasting workflow. The implementation will explain only the fitted `phase3_worse` cumulative regressor, aggregate absolute SHAP values through a six-category crosswalk, and emit phase-3-only machine-readable tables plus one 6 x 4 heatmap per forecasting scope. Default runs remain unchanged when SHAP is disabled.

## Technical Context

**Language/Version**: Python >=3.9  
**Primary Dependencies**: pandas, numpy, xgboost, scikit-learn, matplotlib/seaborn for reports, optional `shap` imported only when SHAP is enabled  
**Storage**: Filesystem artifacts under `results/`, `reports/`, and machine-specific external paths via `configs/paths.local.json`  
**Testing**: pytest unit/smoke tests, CLI `--help`, import checks, and tiny synthetic aggregation/visualization tests  
**Target Platform**: Local Windows/WSL/Linux repository checkout run from repo root with editable install or `PYTHONPATH=src`  
**Project Type**: Python package plus CLI workflow script  
**Performance Goals**: Default non-SHAP forecasting path has no material extra work; SHAP path supports deterministic sample limiting and refuses oversized raw row-level exports without explicit override  
**Constraints**: No hardcoded absolute paths; no heavy production training in automated validation; no change to temporal split, weight-decay fitting, phase threshold, metrics, or classifier workflows  
**Scale/Scope**: Four forecasting scopes (`fs0`-`fs3`), annual holdouts 2022-2025, six feature groups, complete long table of 96 rows when all scope-years are available

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

1. **Temporal validation**: PASS. SHAP is post-hoc and computed only after fitted model/prediction generation. The declared split remains all-prior-history annual holdout: training rows strictly before January 1 of each test year, test rows in that calendar year. SHAP must not affect fitting, tuning, feature scaling, sample weights, thresholds, model selection, or metrics.
2. **Reusable code**: PASS. Reusable SHAP recording, crosswalk validation, aggregation, and heatmap helpers will live in `src/ipcch/`, imported by the existing CLI script.
3. **Path handling**: PASS. Crosswalk path will be exposed through CLI and/or a documented `ipcch.paths.external_path()` key; no local absolute paths.
4. **Artifact separation**: PASS. Machine-readable SHAP artifacts go under `results/experiments/deep_feature_weight_decay_forecasting/...`; report tables/figures go under `reports/deep_feature_weight_decay_forecasting/...`.
5. **Execution discipline**: PASS. Validation will use imports, CLI help, unit tests with synthetic tables, and tiny smoke tests only; no heavy notebook or production training.
6. **Review-gated inputs**: PASS. Expected implementation touches `src/ipcch/`, `scripts/modeling/run_deep_feature_weight_decay_forecasting.py`, `configs/paths.example.json`, and tests; these require review before merge.
7. **Classifier workflows, if present**: PASS. No classifier workflow is added. The canonical cumulative-regressor workflow is preserved and only `phase3_worse` is explained.

## Project Structure

### Documentation (this feature)

```text
specs/006-phase3-shap-importance/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── cli-shap-options.md
└── tasks.md              # Created later by /speckit-tasks
```

### Source Code (repository root)

```text
configs/
└── paths.example.json                 # Document crosswalk external path key

scripts/modeling/
└── run_deep_feature_weight_decay_forecasting.py

src/ipcch/
├── forecasting_weight_decay.py         # Existing split/model/output helpers; update phase-3 hook points if needed
└── forecasting_shap.py                 # New reusable SHAP/crosswalk/aggregation/heatmap helpers

tests/
├── unit/
│   └── test_forecasting_shap.py
└── smoke/
    └── test_weight_decay_shap_cli.py
```

**Structure Decision**: Keep model explainability logic reusable inside `src/ipcch/` and keep the existing CLI script as the orchestration layer. Do not create notebooks or root-level helper modules.

## Complexity Tracking

No constitution violations require justification.

## Phase 0: Research Summary

See [research.md](research.md). Key decisions:

- Use optional SHAP execution that fails clearly when requested but unavailable.
- Explain only the `phase3_worse` model after fitting and ordinary prediction generation.
- Default explanation sample is the phase-3 training feature matrix, with any alternative sample type recorded in outputs.
- Validate crosswalk one-to-one mappings to exactly six groups; fail by default on missing mappings and support explicit unmapped exclusion diagnostics.
- Preserve six-row output shape for zero denominators and allowed-unmapped cases.

## Phase 1: Design Summary

See [data-model.md](data-model.md), [contracts/cli-shap-options.md](contracts/cli-shap-options.md), and [quickstart.md](quickstart.md).

### Post-Design Constitution Check

1. **Temporal validation**: PASS. Design stores SHAP sample type and uses already-split train/test matrices; no future/test information is introduced into fitting or metrics.
2. **Reusable code**: PASS. `forecasting_shap.py` owns reusable validation, aggregation, diagnostics, and plotting helpers.
3. **Path handling**: PASS. CLI path overrides and external-path keys are documented; `configs/paths.example.json` will document the crosswalk key.
4. **Artifact separation**: PASS. Result and report directories are specified separately, with SHAP under phase-3-specific subdirectories.
5. **Execution discipline**: PASS. Tests are synthetic/lightweight; quickstart uses `--help`, dry-run/default-disabled checks, and optional tiny smoke data.
6. **Review-gated inputs**: PASS. Planned changes to `src/ipcch/` and `configs/paths.example.json` are explicit.
7. **Classifier workflows**: PASS. Design explicitly excludes classifiers and non-phase-3 model explanations.
