# Task Evidence Trace: Phase-3 SHAP Six-Category Feature Importance

## Summary

Checked tasks are mostly grounded in the inspected phase-3 SHAP helper, weight-decay output planning, CLI wiring, and tests. The main prior trace question is resolved by user clarification: `--fs` is intentionally one selected feature scope per run, so complete four-scope deliverables are assembled from separate `--fs` invocations or downstream aggregation.

## Evidence Status

- Evidence Status: Ready
- Validation Status: Not Executed
- Acceptance Readiness: Ready with Risks

## Findings

| Task Area | Evidence | Status | Notes |
|---|---|---|---|
| Setup/foundation | `src/ipcch/forecasting_shap.py`, `src/ipcch/forecasting_weight_decay.py`, CLI SHAP flags, and tests exist in current source context | Supported by inspection | Validation not executed. |
| US1 phase-3 SHAP recording | Helper enforces phase-3 target and fitted feature alignment; CLI enables optional SHAP | Supported by inspection | Missing/incompatible SHAP engine behavior not re-tested by this pass. |
| US2 six-category aggregation | Crosswalk validation, aggregation, unmapped diagnostics, and zero-denominator handling are represented in helper surface | Supported by inspection | External crosswalk content not inspected. |
| US3 heatmaps/tables | Matrix and heatmap helpers/paths exist for scope-year outputs | Supported with design clarification | Complete four-scope deliverable is multi-run across `--fs`, not one all-scope invocation. |
| US4 reproducibility/path controls | CLI exposes crosswalk path/key/columns, raw export, allow-unmapped, and overwrite controls | Supported by inspection | Some smoke-test task claims were not re-executed or fully re-inspected. |
| Polish validation | Task list claims unit/smoke checks and production-readiness checks | Not verified by this pass | Validation Status remains Not Executed. |

## Design Alignment Finding

- Observed: The current weight-decay CLI is selected-`--fs` oriented.
- User-confirmed decision: `--fs` is each fs run separately; this was a later design modification.
- Required spec action: Reword all-four-scope requirements and success criteria so a single run produces selected-scope SHAP artifacts, while the full four-scope/96-row deliverable is assembled across separate `--fs fs0`, `--fs fs1`, `--fs fs2`, and `--fs fs3` runs or downstream aggregation.

## Assumptions

- Assumption: The complete long table can be built by concatenating/aggregating selected-scope SHAP outputs across the four runs.
- Assumption: Existing output metadata records enough scope and artifact path information for downstream collection.
- Assumption: Unit/smoke tests remain the authoritative lightweight validation when run separately.

## Open Questions

- None blocking. The former all-scope orchestration question is resolved by user clarification.

## Suggested References

- `specs/006-phase3-shap-importance/evidence.md`
- `specs/006-phase3-shap-importance/contracts/cli-shap-options.md`
- `src/ipcch/forecasting_shap.py`
- `scripts/modeling/run_deep_feature_weight_decay_forecasting.py`
