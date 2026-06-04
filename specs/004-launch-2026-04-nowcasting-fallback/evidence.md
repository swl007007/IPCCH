# Repository Evidence: April 2026 Global Nowcasting Launch

## Summary

Mode 3 post-tasks evidence review applies because `tasks.md` exists and implementation tasks are checked. Current implementation supports the April 2026 production nowcasting launch described by this spec, while later launch extensions for forecast scope, forecast-weather inputs, and grouped SHAP coexist in the same launch module. This pass inspected source/spec/task artifacts but did not run validation commands or production launch jobs.

## Evidence Status

- Evidence Status: Ready
- Validation Status: Not Executed
- Acceptance Readiness: Ready with Risks
- Last updated: 2026-06-03

## Search Coverage

- Inspected `spec.md` and `tasks.md` for fallback comprehensive-source launch scope, execution modes, comparison/map/report outputs, and checked implementation claims.
- Inspected `scripts/modeling/run_launch_nowcasting_2026_04.py` for CLI surface, execution modes, validation-only behavior, scope/weather/grouped-SHAP additions, and training approval gate.
- Inspected `src/ipcch/launch_nowcasting.py` for source loading, training/X-test preparation, feature/schema reporting, prediction validation, output planning, run summary/report writing, scope handling, and optional grouped SHAP wiring.
- Inspected related comparison/visualization implementation context from prior evidence pass findings.

## Findings

### Observed: Core fallback launch design is grounded in source

- The launch workflow uses `src/ipcch/launch_nowcasting.py` and the thin CLI `scripts/modeling/run_launch_nowcasting_2026_04.py`.
- The implementation exposes validation-only/dry-run behavior, execution modes for train-and-predict, supplied models, and supplied predictions, and approval-gated heavy Mode 1 training.
- Source inspection supports the spec’s comprehensive-source fallback framing: build training rows and April 2026 prediction rows from the comprehensive feature source, exclude target-derived columns, align model features, write prediction/schema/summary artifacts, and keep April actuals post-prediction only.

### Observed: Later launch extensions coexist with Spec004

- Current launch code includes later features beyond Spec004, including `--scope` with allowed values including `12`, forecast-weather controls, and optional grouped SHAP.
- These later options are additive to the default April 2026 global fallback launch and should not be read as replacing Spec004’s core Mode 1/2/3 fallback launch behavior.
- Spec004 should remain clear that its baseline is the default/global/0m April 2026 fallback launch, while later feature specs can extend the same CLI/module.

### Observed: Validation evidence was not executed in this pass

- Tasks claim synthetic tests, help checks, validate-only checks, integration checks, and documentation updates.
- This pass did not run pytest, CLI help, validate-only, Mode 2/Mode 3, or production launch commands.
- Heavy Mode 1 training remains approval-gated and should not be treated as executed by this evidence review.

## Task Claim Support

- Supported by source inspection: launch module and CLI existence, comprehensive-source validation surface, training-row/X-test builders, target-derived feature exclusion, schema reports, output guards, execution-mode resolution, prediction validation, phase derivation, comparison/map/report wiring, and training approval gate.
- Supported with design clarification: later scope/weather/grouped-SHAP controls are additive extensions in the same implementation surface, not contradictions of Spec004’s default fallback launch.
- Not verified by this pass: checked unit/smoke/integration commands, real artifact generation, real April 2026 production launch, and generated report/map inspection.

## Risks

- Because validation commands were not executed, task readiness depends on separately running or providing the documented unit/smoke/integration/validate-only checks.
- The same launch module now contains multiple feature generations; future readers may confuse Spec004’s core fallback baseline with later scope/weather/grouped-SHAP extensions unless `spec.md` notes the relationship.
- Real production outputs and large external comprehensive CSV behavior were not inspected in this pass.

## Assumptions

- Assumption: Current source state is the intended implementation baseline for Spec004’s core default/global/0m launch behavior.
- Assumption: Later scope/weather/grouped-SHAP features are governed by their own specs and are additive to, not replacements for, the Spec004 fallback launch.
- Assumption: Existing tests remain the authoritative lightweight validation for the checked implementation tasks.

## Open Questions

- None blocking.

## Suggested References

- `specs/004-launch-2026-04-nowcasting-fallback/evidence.md`
- `src/ipcch/launch_nowcasting.py`
- `scripts/modeling/run_launch_nowcasting_2026_04.py`
