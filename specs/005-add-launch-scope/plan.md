# Implementation Plan: Launch Forecast Scope

**Branch**: `005-add-launch-scope` | **Date**: 2026-05-30 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/005-add-launch-scope/spec.md`

## Summary

Add a `--scope {0,3,6}` launch option to the April 2026 launch workflow. Scope 0 preserves legacy same-period behavior; scope 3 and scope 6 train/evaluate with period-aware feature-target alignment and generate launch predictions where the target period is the feature period plus the selected scope. The implementation will extend the existing launch CLI and `ipcch.launch_nowcasting` utilities, keep canonical cumulative-regressor modeling unchanged, write scope-aware metadata/artifacts without overwriting legacy scope 0 outputs, and make launch visualizations/reporting predicted-only when target-period actuals are unavailable.

## Technical Context

**Language/Version**: Python 3.x, matching current project environment  
**Primary Dependencies**: pandas, numpy, xgboost, scikit-learn, matplotlib, geopandas/contextily for maps, existing `ipcch` package utilities  
**Storage**: File-based CSV/JSON/PNG outputs under `results/` and `reports/`; tracked config/reference inputs under `configs/` and `data/reference/`  
**Testing**: pytest unit/smoke tests with `PYTHONPATH=src`; validate via CLI `--help`, the confirmed lightweight validation entry point discovered or added during implementation, and tiny synthetic frames rather than heavy training  
**Target Platform**: Local/WSL command-line workflow run from repository root  
**Project Type**: Python package plus CLI launch script  
**Performance Goals**: Avoid extra full-data copies beyond the existing launch workflow where possible; scoped alignment should be vectorized and complete within the current launch data-processing budget  
**Constraints**: No hardcoded absolute paths; no heavy model-training notebook execution; preserve canonical 4-regressor workflow and threshold; preserve scope 0 legacy predictions and downstream-compatible outputs  
**Scale/Scope**: Existing April 2026 launch scale, including ~1.2M model-ready rows and April launch predictions across all available areas

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

1. **Temporal validation**: PASS. Split policy is all-prior-history with optional time-decay weighting: training/evaluation records must pair `y(area_id, t)` with time-varying predictors from `t - scope`, and launch prediction must use only feature-period predictors. No target-period or future predictors influence fitting, prediction, reporting, or metrics.
2. **Reusable code**: PASS. Reusable scoped-alignment, static-feature validation, output metadata, and visualization behavior will live in `src/ipcch/`; the script in `scripts/modeling/` remains a thin CLI wrapper.
3. **Path handling**: PASS. Existing `LaunchConfig`, CLI flags, and `ipcch.paths` defaults are retained; no new absolute paths are introduced.
4. **Artifact separation**: PASS. Machine-readable prediction/config/summary outputs remain under `results/launch/...`; human-readable reports/maps remain under `reports/launch/...`; tracked inputs/config remain separate.
5. **Execution discipline**: PASS. Plan validation uses unit tests, smoke tests, `--help`, the confirmed lightweight validation entry point, and synthetic data paths; no notebooks or heavy model training are run by automation.
6. **Review-gated inputs**: PASS. The feature touches `src/ipcch/` and the launch CLI, so changes require review before merge.
7. **Classifier workflows, if present**: N/A. This feature preserves the canonical cumulative-regressor workflow and does not add a classifier.

## Project Structure

### Documentation (this feature)

```text
specs/005-add-launch-scope/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── launch-scope-cli.md
└── tasks.md
```

### Source Code (repository root)

```text
scripts/
└── modeling/
    └── run_launch_nowcasting_2026_04.py

src/
└── ipcch/
    ├── launch_nowcasting.py
    ├── launch_visualizations.py
    └── launch_comparison.py

tests/
├── smoke/
│   └── test_launch_cli.py
├── unit/
│   ├── test_launch_nowcasting.py
│   ├── test_launch_scope_alignment.py
│   ├── test_launch_static_features.py
│   ├── test_launch_scope_outputs.py
│   ├── test_launch_visualizations.py
│   └── test_launch_comparison.py
└── integration/
    └── test_launch_end_to_end.py
```

**Structure Decision**: Keep the existing package/CLI structure. Add reusable scope and alignment logic to `src/ipcch/launch_nowcasting.py`, keep `scripts/modeling/run_launch_nowcasting_2026_04.py` as argument parsing and orchestration, adapt map behavior in `src/ipcch/launch_visualizations.py`, and extend unit/smoke tests. The task list intentionally introduces `tests/unit/test_launch_scope_alignment.py`, `tests/unit/test_launch_static_features.py`, and `tests/unit/test_launch_scope_outputs.py` to separate alignment, static-feature, and output concerns while reducing merge conflicts.

## Complexity Tracking

No constitution violations or justified complexity exceptions.

## Phase 0: Research & Decisions

See [research.md](research.md). Key decisions:

- Use period-aware area/month alignment for training/evaluation rather than dataframe row shifting.
- Treat launch prediction rows separately from training/evaluation rows; prediction requires feature-period predictors but not target-period targets or actuals.
- Keep the workflow config as the source of truth for static feature lists, with basic helper interfaces based on area-level invariance scanning; deeper regeneration, unresolved-inconsistency handling, clear `LaunchError`s, and audit/reporting details are completed in US3.
- Preserve scope 0 legacy outputs and optionally add scope-qualified copies/metadata.
- Make visualization layout depend on target-period actual availability.

## Phase 1: Design & Contracts

See [data-model.md](data-model.md), [contracts/launch-scope-cli.md](contracts/launch-scope-cli.md), and [quickstart.md](quickstart.md).

### Implementation Approach

1. Extend `LaunchConfig` and CLI parsing with `scope_months`/`--scope` restricted to `0`, `3`, or `6`, defaulting to `0`.
2. Introduce a monthly-period helper that derives feature and target periods consistently from `year`/`month` or existing date fields.
3. Add scoped training/evaluation preparation that joins target rows at period `t` to time-varying predictors from period `t - scope` within the same `area_id`, preserving config-recognized static predictors for the same `area_id`.
4. Separate launch prediction preparation from training alignment: launch prediction uses the launch feature-period rows, computes target period as `feature_period + scope`, and does not look for target-period actual/target rows.
5. Add basic static/time-varying helper interfaces based on config and area-level invariance scanning so scope-aware validation and output preparation can call a common API; deeper regeneration/validation behavior, unresolved-inconsistency handling, clear `LaunchError`s, and audit/reporting details are completed in US3.
6. Existing project conventions for static/time-varying classification are derived from the current launch config/schema generation and feature-selection behavior discovered during Phase 1. If no existing regeneration convention exists, define a minimal validation convention consistent with the spec: static features are config-recognized predictors whose observed non-missing values do not vary within any `area_id` across `year`/`month`, and unresolved inconsistencies fail clearly before the requested long-running workflow step begins.
7. Extend prediction output assembly and summary/config JSON with `scope_months`, `feature_period`, `target_period`, and record-type semantics.
8. Adjust output layout so scope 3 and scope 6 never overwrite scope 0; preserve legacy scope 0 outputs and optionally write scope-qualified copies/metadata.
9. Update visualization/reporting so predicted-only maps are produced when target-period actuals are unavailable, while scope 0 actual-vs-predicted behavior remains available when actuals exist.
10. Use the confirmed lightweight validation entry point discovered or added during implementation; do not assume `run_validation_only()` exists unless Phase 1 inspection confirms it.
11. Treat US2 as independently implementable at the launch prediction record, metadata, validation, and output-layout level after foundational work, but do not treat scope 3/6 results as analytically valid until US3 leakage-prevention alignment and static-feature validation are complete.
12. Extend tests for CLI parsing, alignment direction, static-feature validation, prediction without future rows, leakage examples, scope 0 compatibility, and visualization/reporting behavior.

### Post-Design Constitution Check

1. **Temporal validation**: PASS. Design explicitly prevents future time-varying predictors and keeps target-period actuals out of launch prediction.
2. **Reusable code**: PASS. Shared behavior remains in `src/ipcch/`, with the CLI wrapper delegating to package utilities.
3. **Path handling**: PASS. Existing path configuration patterns are retained.
4. **Artifact separation**: PASS. Results/reports/config separation is preserved.
5. **Execution discipline**: PASS. Planned validation uses tests and smoke commands only.
6. **Review-gated inputs**: PASS. Changes to `src/ipcch/` are identified for review.
7. **Classifier workflows**: N/A.

## Phase 2 Preview: Task Generation Guidance

Use `/speckit-tasks` to break implementation into tasks in this order:

1. CLI/config plumbing and scope metadata.
2. Period helper and scoped alignment utilities with unit tests.
3. Basic static/time-varying helper interfaces and tests, followed by US3 static feature regeneration/validation completion.
4. Launch prediction preparation and output schema updates with unit tests; US2 record/metadata/output-layout behavior can land before US3 analytical-validity completion.
5. Output layout and scope 0 compatibility tests.
6. Visualization/reporting behavior updates with unit tests.
7. CLI smoke and integration validation through the confirmed lightweight validation entry point.
