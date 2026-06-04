# Repository Evidence: Phase-3 SHAP Six-Category Feature Importance

## Summary

Mode 3 post-tasks evidence review applies because `tasks.md` exists and implementation tasks are checked. Current implementation supports optional phase-3-only SHAP for the forecasting weight-decay workflow, selected by one `--fs` value per CLI invocation. User clarification resolves the earlier all-scope orchestration question: complete four-scope deliverables are assembled from separate `--fs fs0`, `--fs fs1`, `--fs fs2`, and `--fs fs3` runs or downstream aggregation, not from one required all-scope CLI invocation.

## Evidence Status

- Evidence Status: Ready
- Validation Status: Not Executed
- Acceptance Readiness: Ready with Risks
- Last updated: 2026-06-03

## Search Coverage

- Inspected `spec.md`, `tasks.md`, contracts, and prior evidence/trace artifacts for phase-3 SHAP scope, crosswalk, outputs, validation claims, and all-scope wording.
- Inspected `scripts/modeling/run_deep_feature_weight_decay_forecasting.py` for `--fs`, `--enable-shap`, crosswalk, raw export, overwrite, and selected-scope orchestration.
- Inspected `src/ipcch/forecasting_shap.py` and `src/ipcch/forecasting_weight_decay.py` for phase-3 target enforcement, fitted feature-order checks, crosswalk validation, six-category aggregation, metadata/diagnostics, matrix/heatmap path planning, and raw export guard.
- Inspected unit/smoke test surfaces in prior evidence context; this pass did not run validation commands.

## Findings

### Observed: SHAP implementation is phase-3-only and post-hoc

- `src/ipcch/forecasting_shap.py` targets `phase3_worse` and validates feature alignment against the fitted feature order.
- SHAP is optional and imported only when enabled; disabled default behavior should preserve ordinary forecasting outputs.
- The inspected helper surface supports crosswalk validation, unmapped-feature diagnostics, six-category aggregation, matrix/heatmap construction, metadata, and raw export size guarding.

### Observed: Current CLI runs one selected `--fs` per invocation

- `scripts/modeling/run_deep_feature_weight_decay_forecasting.py` exposes a selected `--fs` dataset/scope option.
- Current metadata and report writing are selected-scope oriented: a run records and writes the matrix/heatmap for the selected `args.fs`.
- User clarification confirms this per-`--fs` design is intended. Older evidence language that treated all-scope orchestration as unresolved is now stale.

### Observed: Complete four-scope outputs remain a multi-run deliverable

- A complete 96-row long table still means four scopes × four annual test years × six groups.
- Under the current implementation baseline, that complete table is assembled by running the selected-scope CLI separately for `fs0`, `fs1`, `fs2`, and `fs3`, or by downstream aggregation of those selected-scope artifacts.
- `spec.md` should state per-run expectations separately from complete-deliverable expectations.

## Task Claim Support

- Supported by source inspection: optional SHAP flag, phase-3-only target, fitted feature-order validation, crosswalk path/key controls, six-category aggregation, metadata/diagnostics, matrix/heatmap outputs, raw export guard, and selected-`--fs` orchestration.
- Supported with design clarification: tasks/spec requirements that discuss all four scopes should be read as complete deliverable requirements across separate `--fs` runs, not one CLI invocation.
- Partially supported by inspected tests: missing/incompatible SHAP engine behavior, overwrite conflicts, and raw export guard have helper support but were not fully re-validated by this pass.
- Not verified by this pass: pytest, CLI help, smoke commands, external crosswalk content, real SHAP engine compatibility, and generated production SHAP artifacts.

## Risks

- If `spec.md` keeps implying one invocation produces all four heatmaps, it will conflict with the user-confirmed selected-`--fs` implementation design.
- External crosswalk availability/content remains unverified; production SHAP runs depend on a compatible six-category crosswalk.
- Validation commands were not executed, so acceptance remains subject to separate unit/smoke/SHAP-enabled validation.

## Assumptions

- Assumption: Current selected-`--fs` CLI behavior and user clarification are the authoritative implementation baseline.
- Assumption: Downstream aggregation or manual collection of per-`--fs` artifacts is acceptable for complete four-scope reporting.
- Assumption: Existing tests remain the authoritative lightweight validation once executed.

## Open Questions

- None blocking. The previous all-scope-vs-selected-`--fs` question is resolved: each `--fs` is run separately.

## Suggested References

- `specs/006-phase3-shap-importance/evidence.md`
- `specs/006-phase3-shap-importance/contracts/cli-shap-options.md`
- `src/ipcch/forecasting_shap.py`
- `scripts/modeling/run_deep_feature_weight_decay_forecasting.py`
