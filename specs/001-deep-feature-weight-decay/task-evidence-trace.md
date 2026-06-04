# Task Evidence Trace: Deep Feature Weighted Decay Forecasting

## Summary

Checked tasks in `tasks.md` are broadly supported by the inspected implementation in `scripts/modeling/run_deep_feature_weight_decay_forecasting.py` and `src/ipcch/forecasting_weight_decay.py`. This pass did not run validation commands, so validation tasks remain accepted as claims rather than independently verified results.

## Evidence Status

- Evidence Status: Ready
- Validation Status: Not Executed
- Acceptance Readiness: Ready with Risks

## Findings

| Task Area | Evidence | Status | Notes |
|---|---|---|---|
| T001-T006 setup | CLI and package helper files exist; path resolution and import through `ipcch` are present | Supported | Current CLI includes later additive options beyond original setup. |
| T007-T018 foundational helpers | `forecasting_weight_decay.py` contains date, target, split, feature, weight, metric, and output helper logic | Supported | Validation not executed in this pass. |
| T019-T024 US1 dry-run/splits | CLI includes `--dry-run`, `--sample-rows`, `--test-years`; helper split logic supports 2022-2025 all-prior-history | Supported by inspection | T024 command result not re-run. |
| T025-T032 US2 time decay/model fitting | Half-life validation, time-decay weights, weight diagnostics, hyperparameter loading, and weighted fit flow are visible | Supported by inspection | T032 command result not re-run. |
| T033-T038 US3 metrics/F2 | Metric helpers include accuracy, phase3+ precision/sensitivity, R2, and F2 with unavailable reasons | Supported by inspection | T038 helper validation not re-run. |
| T039-T045 US4 Somalia metrics | Somalia lookup and metrics flow are present in source | Supported by inspection | T045 validation not re-run. |
| T046-T057 US5/polish | Output/report planning, metadata paths, CLI help/dry-run claims, and review tasks are plausible | Partially supported | Checked validation commands were not executed by this pass. |
| T003 generated prediction ignore rule | `.gitignore` broadly ignores `results/*`; task-specific path wording names a non-nested predictions path | Supported with drift | Current default output plan may write under `<experiment_name>/predictions/`; broad ignore still protects generated outputs. |

## Assumptions

- Assumption: Current source state is the intended baseline; this trace did not inspect historical commits.
- Assumption: Later `--fs`, `--region-scope`, identifier-feature, threshold, and SHAP controls are additive to spec001 rather than replacing its core behavior.

## Open Questions

- Should the spec mention that current default outputs are experiment-name scoped? This is not blocking because broad `results/*` ignore protects generated outputs.

## Suggested References

- `specs/001-deep-feature-weight-decay/evidence.md`
- `src/ipcch/forecasting_weight_decay.py`
- `scripts/modeling/run_deep_feature_weight_decay_forecasting.py`
