# CLI Contract: Canonical Forecast Diagnostics

## Command

```bash
python -m ipcch.forecast_diagnostics \
  --predictions <csv> \
  [--metrics <csv>] \
  [--year <yyyy>] \
  [--output-dir results/diagnostics/experiment_0] \
  [--report-dir reports/diagnostics/experiment_0] \
  [--filter-invalid-labels]
```

## Required Arguments

| Argument | Meaning | Validation |
|----------|---------|------------|
| `--predictions <csv>` | Existing held-out prediction CSV to diagnose; Experiment 0 v1 accepts one CSV per run | File must exist and be readable |

## Optional Arguments

| Argument | Meaning | Default/Behavior |
|----------|---------|------------------|
| `--metrics <csv>` | Existing overall metrics CSV for availability/consistency comparison | Optional; absence is recorded, not fatal |
| `--year <yyyy>` | Evaluation year to attach to outputs or filter when input has multiple years | If omitted, infer from `year` column when available; otherwise record as unspecified |
| `--output-dir <path>` | Machine-readable output root | `results/diagnostics/experiment_0` via project path defaults |
| `--report-dir <path>` | Human-readable report root | `reports/diagnostics/experiment_0` via project path defaults |
| `--filter-invalid-labels` | Explicitly exclude invalid true/predicted labels from label-dependent outputs | Off by default; invalid labels are reported, not silently dropped |
| `--overall-phase-col <name>` | True phase column override | `overall_phase` |
| `--overall-phase-pred-col <name>` | Predicted phase column override | `overall_phase_pred` |
| `--phase2-true-col <name>` | True phase2 cumulative target override | `phase2_worse` |
| `--phase3-true-col <name>` | True phase3 cumulative target override | `phase3_worse` |
| `--phase4-true-col <name>` | True phase4 cumulative target override | `phase4_worse` |
| `--phase5-true-col <name>` | True phase5 cumulative target override | `phase5_worse` |
| `--phase2-pred-col <name>` | Predicted cumulative output column override for phase 2 | Alias detection, preferred `phase2_pred` |
| `--phase3-pred-col <name>` | Predicted cumulative output column override for phase 3 | Alias detection, preferred `phase3_pred` |
| `--phase4-pred-col <name>` | Predicted cumulative output column override for phase 4 | Alias detection, preferred `phase4_pred` |
| `--phase5-pred-col <name>` | Predicted cumulative output column override for phase 5 | Alias detection, preferred `phase5_pred` |
| `--thresholds <values>` | Candidate shared thresholds for diagnostic-only sweep | A small default range including 0.2 |
| `--calibration-bins <n>` | Number of bins for cumulative calibration summaries | Sensible small default |

## Behavior Contract

1. The command reads source prediction and optional metrics files without overwriting them.
2. The command writes machine-readable outputs under `<output-dir>/canonical_regressor/`.
3. The command writes human-readable outputs under `<report-dir>/canonical_regressor/`.
4. Invalid labels are reported by default; label-dependent metrics use valid label pairs and preserve invalid-label counts in validation outputs.
5. Missing optional cumulative columns skip only dependent diagnostics and produce validation findings.
6. Threshold-sweep outputs include `diagnostic_only=true` for every row.
7. No output writes tuned thresholds to configs or changes source prediction CSVs.
8. When `--metrics` is supplied, recognized comparable fields are compared to recomputed diagnostics using a documented tolerance; statuses are recorded as `matched`, `mismatch`, `not_available`, or `not_comparable` without altering computed diagnostics.

## Expected Machine-Readable Outputs

| Artifact | Required When |
|----------|---------------|
| `validation_findings.csv` | Always |
| `validation_summary.json` | Always |
| `class_distribution.csv` | Classification columns present |
| `confusion_matrix_counts.csv` | Valid true/predicted labels present |
| `confusion_matrix_row_normalized.csv` | Valid true/predicted labels present |
| `multiclass_metrics.csv` | Valid true/predicted labels present |
| `binary_crisis_metrics.csv` | Valid true/predicted labels present |
| `cumulative_regression_metrics.csv` | At least one cumulative true/predicted pair present |
| `calibration_bins.csv` | At least one cumulative true/predicted pair present |
| `threshold_crossing_rates.csv` | At least one predicted cumulative output present |
| `diagnostic_threshold_sweep.csv` | Predicted cumulative outputs sufficient to reconstruct phases |
| `error_slices.csv` | Valid true/predicted labels present |
| `run_summary.json` | Always |

## Expected Human-Readable Outputs

| Artifact | Required When |
|----------|---------------|
| `summary.md` | Always |
| Review tables or figures | Optional, when useful and lightweight |

## Exit Expectations

- Success when required inputs are readable and at least validation/run-summary artifacts can be produced.
- Non-zero failure for unreadable required prediction CSV, missing required classification columns, unwritable output/report directories, or ambiguous predicted cumulative output columns not resolved by CLI overrides.
- Warnings, not failures, for absent optional metrics files or absent optional cumulative diagnostics columns.
