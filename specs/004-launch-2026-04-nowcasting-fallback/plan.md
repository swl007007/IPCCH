# Implementation Plan: April 2026 Global Nowcasting Launch (Comprehensive-CSV Fallback)

**Branch**: `004-launch-2026-04-nowcasting-fallback` | **Date**: 2026-05-28 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/004-launch-2026-04-nowcasting-fallback/spec.md`

## Summary

Build a production CLI launch (`scripts/modeling/run_launch_nowcasting_2026_04.py`) plus reusable `src/ipcch/` modules that: (1) read one comprehensive deep-feature CSV; (2) train the existing canonical four-regressor cumulative-phase XGBoost workflow on valid-target rows strictly before 2026-04-01; (3) predict `phase2_worse`…`phase5_worse` for **every eligible April 2026 `area_id`** and derive `overall_phase_pred` via the canonical `th=0.2` rule; (4) optionally compare to **April 2026 actual** labels on a coverage-aware covered subset; and (5) optionally render one two-panel actual-vs-predicted global crisis map. The work maximally reuses the active canonical deep-feature workflow (`ipcch.forecasting_weight_decay`), the cumulative→phase derivation in `ipcch.forecast_diagnostics`, and the visualization guardrails in `ipcch.alert_risk_maps`.

**Key technical decision**: the "existing canonical cumulative-regression workflow" and "canonical identifier-feature setting" referenced throughout the spec resolve to the **deep-feature weight-decay forecasting workflow** (`forecasting_weight_decay.py` + `run_deep_feature_weight_decay_forecasting.py`) at its 0m/nowcast usage, with the `--add-identifier-features` setting (`add_identifier_features()`) and `configs/forecasting_hyperparameters.json` (+ `_p3.json`). This is the workflow the comprehensive deep-feature source feeds and that the existing alert-risk-map experiment directory already targets. See research.md R1–R3.

## Technical Context

**Language/Version**: Python 3.12 (WSL Ubuntu; also runs on Windows/Dropbox)
**Primary Dependencies**: pandas, numpy, xgboost, scikit-learn (modeling/metrics); geopandas + matplotlib + optional contextily (visualization, optional/guarded)
**Storage**: Flat files only — comprehensive CSV input; CSV/JSON/Parquet outputs under `results/` and PNG under `reports/`. No database.
**Testing**: pytest, mirroring existing `tests/{unit,smoke,integration}`. Smoke = `--help` / `--validate-only`; unit = filters/feature-schema/comparison/join logic on tiny synthetic frames; integration = end-to-end on a tiny synthetic comprehensive CSV using Mode 3 (and Mode 2 with a tiny fitted model) so no heavy training runs.
**Target Platform**: Local CLI run from repository root (`pip install -e .` or `PYTHONPATH=src`).
**Project Type**: Single project — reusable library code in `src/ipcch/`, thin CLI in `scripts/modeling/`.
**Performance Goals**: Single launch run; not latency-sensitive. Training one global model set (~thousands–tens-of-thousands of rows, ≤~1800 area_id units × history) must complete in a normal interactive session.
**Constraints**: No hardcoded absolute paths (resolve via `ipcch.paths`); heavy training (Mode 1) gated behind explicit user approval; `th=0.2` fixed; no calibration/router/hurdle/threshold-tuning; April-only descriptive comparison (actuals never touch training/selection).
**Scale/Scope**: Global IPCCH coverage — all eligible April 2026 `area_id` rows in the comprehensive source; training across all prior-history valid-target rows.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

1. **Temporal validation** — **PASS (declared)**. Split policy: *all-prior-history holdout adapted for a single launch month*. Train on valid-target rows strictly before 2026-04-01; predict the 2026-04 launch month. No 2026-04 (or any future) data influences fitting, feature selection, scaling, weighting, threshold (`th=0.2` is fixed, not tuned), or model selection. April actual labels are loaded **only after** predictions and used only for descriptive comparison. **FR-016 decision (research R4)**: 2026-02 and 2026-03 valid-target rows precede the cutoff and are included in training under the all-prior-history rule; this is documented and is independent of the April-only comparison (no leakage — April actuals are never used in training).
2. **Reusable code** — **PASS**. New logic in `src/ipcch/launch_nowcasting.py`, `launch_comparison.py`, `launch_visualizations.py`; thin CLI in `scripts/modeling/`. Reuses `ipcch.forecasting_weight_decay`, `ipcch.forecast_diagnostics`, `ipcch.alert_risk_maps`, `ipcch.paths`. No pipeline primitives redefined in the script.
3. **Path handling** — **PASS**. All paths via `ipcch.paths` (`external_path`, `RESULTS_DIR`, `REPORTS_DIR`, `ensure_under`) or explicit CLI flags; no hardcoded absolute paths. The comprehensive source is **workspace-local**: it is resolved from an explicit `--comprehensive-source` flag or the `external_path("deep_features_2026_target_corrected_dataset")` key supplied in the git-ignored `configs/paths.local.json`. This feature deliberately does **not** add that workspace-specific path to `src/ipcch/paths.py` `DEFAULT_EXTERNAL_PATHS` (only an example entry in `configs/paths.example.json`, which `external_path()` does not read at runtime); an unresolved key with no explicit flag fails with a clear, actionable message (not a raw `KeyError`).
4. **Artifact separation** — **PASS**. Machine-readable outputs under `results/launch/nowcasting_2026_04/`; human-readable report + figure under `reports/launch/nowcasting_2026_04/`. No tracked inputs modified except a new `configs/paths.example.json` key (review-gated, item 6). Both `results/*` and `reports/*` are git-ignored, so large prediction CSVs are not committed (FR-037).
5. **Execution discipline** — **PASS**. Mode 1 heavy training requires explicit user approval and is never auto-run; `--validate-only`/`--dry-run` and `--help` do no training; tests use tiny synthetic data and Modes 2/3.
6. **Review-gated inputs** — **FLAGGED (no violation)**. Touches `src/ipcch/` (new modules + optionally promoting the canonical `fit_model`/`convert_phase_predictions` helpers from the script into `forecasting_weight_decay.py`) and adds one `configs/paths.example.json` key. These are review-gated per policy; no `data/reference/` change.
7. **Classifier workflows** — **N/A**. This is the canonical cumulative-regressor workflow, not a phase classifier. No class mapping. Target-derived feature exclusion is still enforced (FR-011b) via the canonical `select_numeric_feature_columns()` plus the documented exclusion patterns.

**Result**: PASS. No Complexity Tracking entries required. One intentional, documented divergence from an existing module is recorded in research R6 (a launch-specific spatial join that *records* unmatched IDs and renders the matched subset, instead of raising as `alert_risk_maps.join_predictions_to_spatial()` does) — this is additive (a new function), does not alter existing behavior, and is required by FR-027.

## Project Structure

### Documentation (this feature)

```text
specs/004-launch-2026-04-nowcasting-fallback/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 output (decisions R1–R9)
├── data-model.md        # Phase 1 output (entities, schemas, artifacts)
├── quickstart.md        # Phase 1 output (how to run the three modes)
├── contracts/
│   └── cli.md           # CLI contract: flags, modes, exit behavior, outputs
├── checklists/
│   └── requirements.md  # Spec quality checklist (from /speckit-specify)
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created here)
```

### Source Code (repository root)

```text
src/ipcch/
├── launch_nowcasting.py        # NEW: source validation, train/predict orchestration,
│                               #      feature-schema report, prediction validation, run summary
├── launch_comparison.py        # NEW: April-only coverage-aware comparison + metrics
├── launch_visualizations.py    # NEW: two-panel map + launch-specific recording spatial join
├── forecasting_weight_decay.py # REUSE (+ optional promotion of fit_model/convert helpers)
├── forecast_diagnostics.py     # REUSE: reconstruct_phase_from_cumulative, metric helpers
├── alert_risk_maps.py          # REUSE: color constants, latam inset, binary layer, ensure_under,
│                               #        ValidationSummary pattern, geopandas/matplotlib guards
└── paths.py                    # REUSE: external_path, RESULTS_DIR, REPORTS_DIR

scripts/modeling/
└── run_launch_nowcasting_2026_04.py   # NEW: thin CLI wiring the launch modules

configs/
└── paths.example.json          # ADD one documented key for the comprehensive fallback source

tests/
├── unit/        # filters, feature-schema diff, target-derived exclusion, comparison math, join recording
├── smoke/       # --help, --validate-only (no training)
└── integration/ # tiny synthetic end-to-end via Mode 3 and Mode 2
```

**Structure Decision**: Single-project layout. Reusable logic lives in three new `src/ipcch/launch_*.py` modules imported through `ipcch`; a single thin CLI script under `scripts/modeling/` wires them and exposes flags. This honors Principle II (shared utilities in the package) and keeps the script free of pipeline primitives. Existing modules are reused rather than duplicated; the only optional edit to an existing module is promoting the two tiny canonical helpers (`fit_model`, `convert_phase_predictions`) from the deep-feature script into `forecasting_weight_decay.py` so both the launch and the original script share one definition (prevents drift). If that promotion is declined in review, the launch module mirrors the canonical fit semantics locally with a documented comment.

## Complexity Tracking

> No constitution violations require justification. Table intentionally empty.
