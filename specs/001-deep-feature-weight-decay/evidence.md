# Repository Evidence: Deep Feature Weighted Decay Forecasting

## Summary

Mode 3 post-tasks evidence review applies because `tasks.md` exists and implementation tasks are checked. The current implementation is grounded in `scripts/modeling/run_deep_feature_weight_decay_forecasting.py` and `src/ipcch/forecasting_weight_decay.py`. This pass inspected source/spec/task artifacts but did not execute validation commands.

## Evidence Status

- Evidence Status: Ready
- Validation Status: Not Executed
- Acceptance Readiness: Ready with Risks
- Last updated: 2026-06-03

## Search Coverage

- Inspected `spec.md` and `tasks.md` for feature intent, completed-task claims, and output expectations.
- Inspected `scripts/modeling/run_deep_feature_weight_decay_forecasting.py` for CLI surface, dataset selection, `--fs`, `--region-scope`, dry-run, time-decay, output planning, and later SHAP controls.
- Inspected `src/ipcch/forecasting_weight_decay.py` for split logic, time-decay weights, metrics, output layout, and overwrite checks.
- Inspected related implementation references through repository search for `deep_feature_weight_decay_forecasting`, `--fs`, `half-life`, and SHAP.

## Findings

### Observed: Core spec001 behavior is implemented in the weight-decay workflow

- `scripts/modeling/run_deep_feature_weight_decay_forecasting.py` exposes the separate modeling entry point, dry-run/sample controls, half-life configuration, annual test-year selection, Somalia lookup, output/report roots, and overwrite behavior.
- `src/ipcch/forecasting_weight_decay.py` implements all-prior-history annual splits, target derivation, time-decay weights, metric helpers including F2 and unavailable status handling, Somalia lookup helpers, and separated `results/` and `reports/` output planning.

### Observed: Current implementation has expanded beyond the original spec001 baseline

- The CLI now includes `--fs`, `--region-scope`, identifier feature controls, threshold controls, and phase-3 SHAP controls. These later additions are current implementation state, but they are not all part of the original spec001 feature request.
- The current default output plan nests generated artifacts under an experiment name when default `out-dir`/`report-dir` are omitted, e.g. `results/experiments/deep_feature_weight_decay_forecasting/<experiment_name>/...`.

### Observed: Potential generated-output ignore mismatch

- `tasks.md` T003 references `.gitignore` coverage for `results/experiments/deep_feature_weight_decay_forecasting/predictions/`.
- Current default output resolution can place prediction outputs under `results/experiments/deep_feature_weight_decay_forecasting/<experiment_name>/predictions/`.
- Project-level `.gitignore` broadly ignores `results/*`, so accidental tracking is still protected in the current repository, but the task-specific path wording is stale relative to the nested default output layout.

## Task Claim Support

- Supported by source inspection: dataset path resolution, monthly date creation, cumulative targets, all-prior-history splits, time-decay weights, model fitting hooks, F2/unavailable metrics, Somalia metrics, metadata/report outputs, and path-agnostic CLI flags.
- Not verified by this pass: the checked validation commands in tasks T024, T032, T038, T045, T050-T052, and T057. They may have been run earlier, but this evidence pass did not execute them.

## Risks

- Validation evidence is not refreshed by this pass. Acceptance remains “Ready with Risks” until the documented lightweight commands are re-run or their output is provided.
- Spec001 should not be read as excluding later current CLI options; the implementation now also supports later feature scopes and SHAP extensions.

## Assumptions

- Assumption: Checked task states represent intended implementation claims, not proof of validation execution.
- Assumption: Later CLI extensions are compatible with spec001 as additive behavior unless they change the baseline weighted-decay semantics.

## Open Questions

- None blocking for artifact grounding. The only notable drift is documentation clarity around later additive CLI options and nested default output paths.

## Suggested References

- `specs/001-deep-feature-weight-decay/evidence.md`
- `.specify/memory/constitution.md`
- `src/ipcch/forecasting_weight_decay.py`
- `scripts/modeling/run_deep_feature_weight_decay_forecasting.py`
