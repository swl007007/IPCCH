# Quality Guidelines

> Code quality standards for IPCCH modeling code (`src/ipcch/`, `scripts/`).

---

## Overview

IPCCH is a research pipeline; the dominant failure mode is silent temporal leakage or
silent sample changes, not crashes. Checks favour explicit contracts over convenience.

---

## Forbidden Patterns

- **Trusting a feature file's scope label as proof of as-of timing.** Verify lineage per
  feature family. Known facts about `assembled_IPCCH/model_ready` scope files (from the
  upstream builder `assemble_latest_IPCCH/build_multiscope_ipcch_features.py`):
  - `_sH` families are the `asof12` columns shifted to latest source month exactly `T-H`;
    `_s0` therefore uses the target month itself (a nowcast).
  - `overall_phase_prev_observed_asof_sH` is the exact calendar month `T-max(1,H)`.
  - `overall_phase_lag1` is the previous *observed* row with any gap — it post-dates the
    origin for most H>=3 rows. Block it for any forecast with H>0.
  - `estimated_population` is corrected together with the targets for month T — target-side.
  - `ipcch.forecasting_weight_decay.select_numeric_feature_columns` admits both of the last two.
- **Rounding predictions before the 0.2 phase threshold** (old runner behaviour). Compare
  unrounded cumulative predictions with `>=`; round only for display.
- **Dropping rows by predicted or true cumulative sums** (`convert_phase_predictions`
  style). All-zero valid truth is phase 1; cohorts must be frozen before predictions exist.
- **Forward-filled weather treated as observations.** In `IPCCH_2026_completed.csv`,
  772 Somalia areas repeat their 2025-01 rain/temperature through 2026-03 and all areas
  repeat March in 2026-04. Detect exact repeats of the previous month and treat them as
  unverified.
- Recursive "latest file" discovery for inputs; resolve explicit paths via `ipcch.paths`.

---

## Required Patterns

- Month arithmetic with dense ordinals `year*12 + (month-1)`; origin `O = T - H`.
- History visible months `U <= min(O, T-1)` (H=0 must exclude the target month).
- Inner validation cutoffs per fold: fit labels `<= min(v-H, v-1)`; decay weights anchored
  at each fit's own origin.
- Machine-readable outputs under `results/`, human-readable under `reports/`; write a
  manifest with input sha256, git HEAD and runtime versions.
- Provide an independent replay (different code path, e.g. scikit-learn) for reported metrics.

---

## Testing Requirements

- `PYTHONPATH=src ~/.venvs/ipcch-geo/bin/python -m pytest tests/unit/... -q` for focused
  contract tests on tiny synthetic frames; boundary cases (.196/.2/.204, exclusive season
  ends, H=0 self-exclusion) must be explicit.
- Heavy training only when requested; synthetic smoke tests use tiny `n_estimators`.
- The existing suite has 12 pre-existing failures (alert-risk maps / launch CLI) on main;
  compare against that baseline rather than assuming a clean suite.

---

## Code Review Checklist

- Does any predictor's latest source month exceed the row's origin?
- Are fitting, tuning and threshold choices free of test-year labels?
- Are sample exclusions decided before predictions, identically across compared arms?
- Are undefined metrics reported as undefined (not zero, not dropped)?

## Lessons from the q3-first optimization (2026-09-25)

- Reading saved float predictions with `pd.read_csv` default parsing can change the last bit and split isotonic-calibration ties; replays of saved scores must use `float_precision="round_trip"`.
- Don't run the full pytest suite and a 12–14 worker XGBoost run concurrently on the 15 GB machine; the worker pool dies (`BrokenProcessPool`).
- Training-period validation choices (e.g. residual vs direct q3) can fail to transfer to the outer year; always report non-selected formulations alongside the selected view.
