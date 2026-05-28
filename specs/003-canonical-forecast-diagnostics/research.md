# Research: Canonical Forecast Diagnostics

## Decision: Implement as an `ipcch` package module with module CLI

**Rationale**: Shared diagnostic logic belongs in `src/ipcch/` under the project constitution. A module CLI (`python -m ipcch.forecast_diagnostics`) keeps reusable functions importable while allowing a reproducible command-line workflow from the repository root.

**Alternatives considered**:
- Standalone script under `scripts/`: rejected because shared metric logic would be less discoverable and easier to duplicate.
- Notebook-only workflow: rejected because reusable metric logic must not be notebook-local and automation must not run heavy notebooks.

## Decision: Use existing lightweight tabular dependencies

**Rationale**: `pandas`, `numpy`, and `scikit-learn` are already part of the project workflow and are sufficient for validation, distributions, confusion matrices, per-class metrics, F-beta scores, regression errors, and calibration summaries.

**Alternatives considered**:
- Add new metric/reporting dependencies: rejected because the workflow should stay lightweight.
- Reuse `all_metrics()` only: rejected because Experiment 0 requires additional multiclass, binary, cumulative-regression, calibration, and threshold-sweep diagnostics beyond canonical summary metrics.

## Decision: Resolve predicted cumulative output columns with aliases plus CLI overrides

**Rationale**: Existing prediction CSVs may use names such as `phase2_pred` through `phase5_pred` or equivalent cumulative-output names. Alias detection provides sensible defaults, while explicit CLI column flags prevent silent misinterpretation when names vary.

**Alternatives considered**:
- Require one strict predicted-column naming convention: rejected because existing artifacts may not be uniform.
- Auto-detect by loose substring matching only: rejected because ambiguous names could map incorrectly without user override.

**Header inspection note**: The documented example path `results/predictions/forecasting/predictions_2025.csv` was not present in this checkout during implementation validation, so no large prediction directory scan was performed. The implementation relies on preferred `phase2_pred` through `phase5_pred` names plus explicit CLI overrides and bounded alias detection.

## Decision: Treat invalid labels as validation findings by default

**Rationale**: The acceptance criteria require invalid labels such as 0 and missing labels to be reported instead of silently dropped. Classification metrics should be computed on rows with valid true/predicted labels, while invalid rows remain represented in validation findings and class-distribution validation status.

**Alternatives considered**:
- Fail immediately on any invalid label: rejected because users need a diagnostic report of invalid label prevalence.
- Drop invalid labels silently: rejected by the specification.

## Decision: Threshold sweep uses one shared candidate threshold

**Rationale**: Clarification on 2026-05-27 selected a shared threshold applied to all cumulative outputs at each candidate setting. This avoids a combinatorial grid, keeps diagnostics interpretable, and prevents the sweep from looking like model tuning.

**Alternatives considered**:
- Independent one-phase-at-a-time threshold sweeps: rejected by clarification in favor of simpler shared-threshold diagnostics.
- Full four-threshold grid: rejected because it increases complexity and tuning risk.

## Decision: Write machine-readable and human-readable artifacts separately

**Rationale**: The constitution requires generated machine-readable outputs under `results/` and human-readable summaries/figures under `reports/`. Adding a `canonical_regressor` subdirectory and metadata label prevents confusion with future classifier or correction outputs.

**Alternatives considered**:
- Single mixed output directory: rejected because it violates artifact separation.
- Write summaries next to source predictions: rejected because source prediction locations should not be mutated.

## Decision: Validation uses import, help, and tiny smoke tests only

**Rationale**: The feature is diagnostic-only and must not run heavy notebook training. A tiny synthetic dataset with phases 1–4, invalid labels, cumulative targets, and representative error slices is sufficient to validate core logic paths.

**Alternatives considered**:
- Run existing notebooks end-to-end: rejected by safe execution rules.
- Run full annual prediction CSVs as validation: optional for user execution, but not required for implementation validation because large files may be ignored or unavailable.
