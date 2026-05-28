# Implementation Plan: Canonical Forecast Diagnostics

**Branch**: `003-canonical-forecast-diagnostics` | **Date**: 2026-05-27 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/003-canonical-forecast-diagnostics/spec.md`

## Summary

Experiment 0 provides a lightweight diagnostic/evaluation workflow for already-generated IPCCH canonical cumulative-regression predictions. The workflow will read one held-out prediction CSV per run and an optional metrics CSV, validate schema and label quality, compute annual diagnostic outputs, optionally compare recognized metrics-file values to recomputed diagnostics, and write machine-readable canonical-regressor artifacts under `results/diagnostics/experiment_0/` plus human-readable summaries under `reports/diagnostics/experiment_0/` without retraining, tuning, calibration, threshold selection, or prediction mutation.

## Technical Context

**Language/Version**: Python >=3.9, consistent with `pyproject.toml`; current WSL runtime may use Python 3.12  
**Primary Dependencies**: Existing project stack: `pandas`, `numpy`, `scikit-learn`; optional plotting through existing report stack if needed (`matplotlib`/`seaborn`)  
**Storage**: Filesystem CSV/JSON/Markdown/figure artifacts only; no database  
**Testing**: Import checks, CLI `--help`, and tiny synthetic-data smoke tests; no heavy notebooks or model training  
**Target Platform**: Repository-root CLI/module execution on Linux/WSL with editable install or `PYTHONPATH=src`  
**Project Type**: Python package module with CLI entry point via `python -m ipcch.forecast_diagnostics`  
**Performance Goals**: Complete diagnostics for typical annual prediction CSVs in a single local run without retraining; smoke tests complete quickly on tiny data  
**Constraints**: Must not overwrite source prediction CSVs, write tuned thresholds to configs, execute heavy notebook cells, or hardcode absolute paths  
**Scale/Scope**: One annual prediction CSV per run for Experiment 0 v1; batch or multi-file annual aggregation is out of scope; generated diagnostic artifacts are separated from future classifier/correction outputs and labeled as canonical regressor diagnostics

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Phase 0 Gate

1. **Temporal validation**: PASS. Experiment 0 evaluation policy: this feature consumes prediction CSVs already produced from the canonical annual holdout forecasting workflow. Each annual prediction CSV is treated as a held-out test-year artifact. Experiment 0 performs post-holdout diagnostics only; it does not fit models, refit preprocessing, tune thresholds, calibrate labels, select models, change class mappings, alter the canonical temporal split, or use test-window data to influence fitted parameters or reported canonical metrics. Threshold sweeps are post-hoc diagnostics only and are not reported as tuned canonical performance.
2. **Reusable code**: PASS. Shared metric, validation, schema, threshold-sweep, and reporting logic will live in `src/ipcch/forecast_diagnostics.py` or an equivalent `ipcch` module. Notebook-local metric redefinitions are out of scope.
3. **Path handling**: PASS. Defaults use `ipcch.paths`; all path-bearing inputs and outputs are exposed through CLI flags. No hardcoded absolute paths.
4. **Artifact separation**: PASS. Machine-readable artifacts go under `results/diagnostics/experiment_0/`; human-readable summaries/figures go under `reports/diagnostics/experiment_0/`; large source prediction CSVs are read in place and not copied into git.
5. **Execution discipline**: PASS. Validation is limited to import checks, `python -m ipcch.forecast_diagnostics --help`, and tiny synthetic/sampled smoke tests. No heavy notebook training.
6. **Review-gated inputs**: PASS with review note. Implementation changes under `src/ipcch/` are review-gated by project policy; no `configs/*.json` or `data/reference/` changes are planned.
7. **Classifier workflows**: PASS. Not applicable because Experiment 0 is canonical cumulative-regressor diagnostics only. Artifact names and metadata will explicitly use canonical-regressor/experiment-0 labels so outputs are not confused with classifier artifacts.

No constitution violations require complexity tracking.

## Project Structure

### Documentation (this feature)

```text
specs/003-canonical-forecast-diagnostics/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── cli-contract.md
└── tasks.md
```

### Source Code (repository root)

```text
src/ipcch/
├── forecast_diagnostics.py          # reusable diagnostics module and module CLI
├── paths.py                         # existing path defaults used by CLI
└── __init__.py

results/diagnostics/experiment_0/
└── canonical_regressor/             # machine-readable generated diagnostics

reports/diagnostics/experiment_0/
└── canonical_regressor/             # human-readable summaries and figures
```

**Structure Decision**: Implement this as a package module under `src/ipcch/` with a module CLI (`python -m ipcch.forecast_diagnostics`). This follows the existing package convention, avoids notebook-local logic, and keeps generated diagnostic outputs in the existing `results/` and `reports/` trees.

## Technical Design

### Terminology and Input Schema Strategy

- **Prediction CSV**: The source forecast file for one annual held-out evaluation run, containing true labels, predicted cumulative output columns, and the canonical predicted phase.
- **Predicted cumulative output columns**: The cumulative-regression prediction columns for phase 2 through phase 5, preferably `phase2_pred`, `phase3_pred`, `phase4_pred`, and `phase5_pred`, or user-configured aliases.
- **Canonical predicted phase**: The `overall_phase_pred` field already produced by the canonical forecasting workflow.
- **Canonical regressor diagnostics**: Diagnostics for the existing cumulative-regression workflow, separate from classifier or correction-model outputs.

Each prediction CSV is expected to contain:

- Required classification columns: `overall_phase`, `overall_phase_pred`
- Optional identifiers/time fields: `area_id`, `year`, `month`, `date`, `country`, `region`
- Optional true cumulative targets: `phase2_worse`, `phase3_worse`, `phase4_worse`, `phase5_worse`
- Optional predicted cumulative output columns: preferred `phase2_pred`, `phase3_pred`, `phase4_pred`, `phase5_pred`, with robust aliases and explicit CLI overrides when existing prediction CSVs use different names

The workflow will validate the available schema and produce coverage findings. Missing optional fields skip only dependent diagnostics and are recorded in the run summary.

### Reusable Functions

Implement reusable functions in `src/ipcch/forecast_diagnostics.py`:

- `validate_prediction_schema()`
- `compute_class_distribution()`
- `compute_confusion_matrices()`
- `compute_multiclass_metrics()`
- `compute_binary_crisis_metrics()`
- `compute_cumulative_regression_metrics()`
- `compute_calibration_bins()`
- `compute_threshold_crossing_rates()`
- `run_diagnostic_threshold_sweep()`
- `summarize_error_slices()`

Supporting internal helpers may handle label validation, column alias resolution, F-beta computation, safe numeric coercion, optional metrics-file comparison with documented tolerance, output writing, and report-summary generation.

### CLI Contract

Primary command:

```bash
python -m ipcch.forecast_diagnostics \
  --predictions <csv> \
  --metrics <csv optional> \
  --year 2025 \
  --output-dir results/diagnostics/experiment_0 \
  --report-dir reports/diagnostics/experiment_0
```

The CLI accepts one prediction CSV per run. It should also expose column override flags for phase labels and predicted cumulative output columns when file naming varies. Defaults should resolve through `ipcch.paths` for output/report locations and use the provided input file path without rewriting it.

### Artifact Plan

Machine-readable artifacts under `results/diagnostics/experiment_0/canonical_regressor/`:

- `validation_findings.csv` and/or `validation_summary.json`, including optional metrics-file comparison findings
- `metrics_comparison.csv` when a metrics file is supplied and comparable fields are recognized
- `class_distribution.csv`
- `confusion_matrix_counts.csv`
- `confusion_matrix_row_normalized.csv`
- `multiclass_metrics.csv`
- `binary_crisis_metrics.csv`
- `cumulative_regression_metrics.csv`
- `calibration_bins.csv`
- `threshold_crossing_rates.csv`
- `diagnostic_threshold_sweep.csv` with `diagnostic_only=true`
- `error_slices.csv`
- `run_summary.json`

Human-readable artifacts under `reports/diagnostics/experiment_0/canonical_regressor/`:

- `summary.md` with validation, metric, threshold-sweep, and error-slice summaries
- optional compact CSV tables and figures suitable for review, keeping narrative outputs separate from machine-readable outputs

### Risk Controls

- Invalid and missing phase labels are counted and reported by default.
- Invalid-label filtering requires an explicit CLI flag.
- Optional metrics-file comparison records `matched`, `mismatch`, `not_available`, or `not_comparable` status and never changes recomputed diagnostics.
- Source prediction CSVs are never overwritten.
- Threshold-sweep results are marked `diagnostic_only=true` and are not written to configs.
- No generated tuned threshold is selected or recommended as final model performance.
- Classifier/correction outputs are excluded from this artifact namespace.

## Phase 0: Research Outcomes

See [research.md](research.md). Decisions resolved: package module CLI, pandas/scikit-learn metrics, alias-based schema detection plus CLI overrides, shared-threshold post-hoc threshold sweep, file-based artifacts, and smoke-test validation only.

## Phase 1: Design Outcomes

See [data-model.md](data-model.md), [contracts/cli-contract.md](contracts/cli-contract.md), and [quickstart.md](quickstart.md). These artifacts define the diagnostic data entities, CLI interface, artifact expectations, validation behavior, and smoke-test workflow.

## Post-Design Constitution Check

1. **Temporal validation**: PASS. Design only consumes one prediction CSV per run containing already-held-out prediction rows and an optional existing metrics file for comparison. Threshold sweeps remain shared-threshold, post-hoc, `diagnostic_only=true`, and non-selective; optional metrics-file comparisons never alter recomputed diagnostics or reported canonical metrics.
2. **Reusable code**: PASS. All reusable diagnostic logic is planned for `src/ipcch/forecast_diagnostics.py`; no notebook-local logic.
3. **Path handling**: PASS. CLI exposes inputs/outputs and uses `ipcch.paths` defaults; no absolute paths.
4. **Artifact separation**: PASS. Outputs split between `results/diagnostics/experiment_0/canonical_regressor/` and `reports/diagnostics/experiment_0/canonical_regressor/`.
5. **Execution discipline**: PASS. Validation plan uses import, help, and tiny smoke tests only.
6. **Review-gated inputs**: PASS with review note. Planned `src/ipcch/` changes require review before merge; no config/reference changes planned.
7. **Classifier workflows**: PASS. Not applicable; artifact labels explicitly say canonical regressor diagnostics.

No constitution violations remain.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |
