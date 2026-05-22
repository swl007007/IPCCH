# Implementation Plan: Deep Feature Weighted Decay Forecasting

**Branch**: `001-deep-feature-weight-decay` | **Date**: 2026-05-21 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-deep-feature-weight-decay/spec.md`

**Note**: This plan ends after Phase 2 planning artifacts. Implementation tasks are generated separately by `/speckit-tasks`.

## Summary

Create a new IPCCH modelling command for the corrected deep-feature forecasting-ready dataset. The workflow will prepare four annual holdouts for 2022-2025 using all eligible records before each test year, compute exponential time-decay sample weights with a default 24-month half-life, fit the existing four cumulative-phase XGBoost design, report F2 plus existing metrics, and generate Somalia-only metrics after all annual prediction outputs are available. Reusable helpers should live in `src/ipcch/`, path defaults should be resolved through `ipcch.paths`, and full validation should rely on dry-run/smoke checks rather than automated heavy notebook execution.

## Technical Context

**Language/Version**: Python >=3.9, matching `pyproject.toml`  
**Primary Dependencies**: pandas, numpy, xgboost, scikit-learn, existing `ipcch.food_crisis_functions`, existing `ipcch.paths`  
**Storage**: External CSV inputs; generated CSV, JSON, and Markdown files under `results/` and `reports/`  
**Testing**: CLI `--help`, import checks, dry-run validation, small/synthetic smoke tests; no automated heavy notebook training  
**Target Platform**: Repository-root execution on Linux/WSL with configurable Windows/Dropbox external paths  
**Project Type**: Python package utilities plus modelling CLI script  
**Performance Goals**: Dry-run validation should inspect paths, columns, splits, feature selection, weights, and output plan without full fitting; full training performance is bounded by existing XGBoost workflow cost  
**Constraints**: Do not modify `notebooks/modeling/Table1_Forecasting_main.ipynb`; do not copy raw external source data; do not hardcode absolute Windows paths; do not execute heavy notebook cells through automation; generated machine-readable artifacts under `results/`; reports under `reports/`  
**Scale/Scope**: One corrected forecasting-ready CSV, four annual holdout years, four cumulative target models per year, overall and Somalia-only metrics

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

1. **Temporal validation uses no test-window or future information**: PASS. The feature declares an all-prior-history annual holdout policy and uses only records strictly before January 1 of each test year for training.
2. **Reusable code lives in `src/ipcch/` and is imported through `ipcch`**: PASS. Plan uses a new script under `scripts/modeling/` and package helpers under `src/ipcch/` only when logic is reusable.
3. **Paths resolved through `ipcch.paths` or documented CLI flags**: PASS. Plan adds path keys and CLI overrides; no committed absolute external paths.
4. **Inputs, generated outputs, and reports remain separated**: PASS. External data remains outside repo; outputs go to `results/`; human-readable summaries go to `reports/`.
5. **Automation avoids heavy notebook training**: PASS. Plan validates via help, imports, dry-run, and small smoke tests. The original notebook is not modified or executed.
6. **Changes to shared inputs/utilities are review-gated**: PASS. Any changes under `src/ipcch/` or `configs/*.json` are visible for review; no `data/reference/` changes are planned.

## Project Structure

### Documentation (this feature)

```text
specs/001-deep-feature-weight-decay/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── cli-contract.md
│   └── output-schemas.md
└── tasks.md
```

### Source Code (repository root)

```text
configs/
└── paths.example.json                       # add documented external path keys

scripts/
└── modeling/
    └── run_deep_feature_weight_decay_forecasting.py

src/
└── ipcch/
    ├── food_crisis_functions.py             # reuse convert_prob_to_phase/all_metrics conventions; add only small metric helper if appropriate
    ├── paths.py                             # add external path defaults for the new dataset and Somalia lookup
    └── forecasting_weight_decay.py          # reusable split, weight, metric, lookup, and output helpers if task design confirms need

results/
└── experiments/
    └── deep_feature_weight_decay_forecasting/
        ├── predictions/
        ├── metrics/
        └── metadata/

reports/
└── deep_feature_weight_decay_forecasting/
    └── summary.md
```

**Structure Decision**: Use the existing Python package plus modelling script layout. Keep orchestration in `scripts/modeling/`; put reusable logic in `src/ipcch/`; document external path keys in `configs/paths.example.json`; write generated artifacts under `results/` and `reports/`.

## Complexity Tracking

No constitution violations remain after the constitution was amended to allow feature-declared all-prior-history annual holdouts when they preserve strict no-future-leakage boundaries.

## Phase 0: Research Summary

Research decisions are captured in [research.md](research.md):

- New modelling CLI plus reusable `ipcch` helpers.
- All-prior-history annual holdout split.
- Constitution-aligned all-prior-history annual holdout split.
- Exponential 24-month half-life default.
- Existing cumulative-phase model and phase-conversion conventions preserved.
- F2 on discrete phase 3+ labels; undefined metrics unavailable with reasons.
- Somalia lookup derived from configured source with ISO3-first matching.
- New external path keys for the corrected dataset and Somalia lookup.
- Dry-run and small/synthetic validation instead of heavy automated training.

## Phase 1: Design Summary

Design artifacts are captured in:

- [data-model.md](data-model.md)
- [contracts/cli-contract.md](contracts/cli-contract.md)
- [contracts/output-schemas.md](contracts/output-schemas.md)
- [quickstart.md](quickstart.md)

Implementation should preserve these key interfaces:

1. Dry-run mode validates inputs, splits, feature selection, weight monotonicity, Somalia lookup, and output planning without fitting full models.
2. Full mode runs exactly four holdouts unless explicitly in implementation test mode.
3. Prediction and metrics outputs use the documented file locations and unavailable-metric schema.
4. Metadata records source identity, split rule, test years, feature count, decay half-life, and output locations.

## Post-Design Constitution Check

1. **Temporal validation uses no test-window or future information**: PASS. Data model and contracts require all-prior-history train rows strictly before the holdout year and test rows within the holdout year only.
2. **Reusable code lives in `src/ipcch/` and is imported through `ipcch`**: PASS. Design separates orchestration script from reusable helper module.
3. **Paths resolved through `ipcch.paths` or documented CLI flags**: PASS. CLI contract defines dataset and lookup path flags plus external path keys.
4. **Inputs, generated outputs, and reports remain separated**: PASS. Output schema and quickstart keep generated artifacts in `results/` and `reports/`.
5. **Automation avoids heavy notebook training**: PASS. Quickstart recommends `--help`, `--dry-run`, and sampled smoke checks.
6. **Changes to shared inputs/utilities are review-gated**: PASS. Planned changes to `src/ipcch/` and `configs/paths.example.json` are explicit and reviewable.
