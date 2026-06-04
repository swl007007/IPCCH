# Repository Evidence: Canonical Forecast Diagnostics

## Summary

Mode 3 post-tasks evidence review applies because `tasks.md` exists and implementation tasks are checked. Current implementation in `src/ipcch/forecast_diagnostics.py` aligns with the spec’s diagnostic-only, one-annual-prediction-CSV-per-run design. This pass inspected source/spec/task artifacts but did not run validation commands.

## Evidence Status

- Evidence Status: Ready
- Validation Status: Not Executed
- Acceptance Readiness: Ready with Risks
- Last updated: 2026-06-03

## Search Coverage

- Inspected `spec.md` and `tasks.md` for diagnostic scope, post-hoc threshold policy, and checked claims.
- Inspected `src/ipcch/forecast_diagnostics.py` for schema validation, label validation, cumulative-column aliases, metrics, threshold sweep, error slices, output/report defaults, and CLI configuration.
- Searched current implementation references for forecast diagnostics and canonical threshold behavior.

## Findings

### Observed: Implementation is diagnostic-only and path-agnostic

- `DiagnosticConfig` defaults outputs under `results/diagnostics/experiment_0` and reports under `reports/diagnostics/experiment_0`.
- The module consumes existing prediction/metrics paths and does not train or modify model outputs.
- Canonical threshold constants and threshold-sweep defaults are local to diagnostics, with sweep behavior intended as post-hoc diagnostic output.

### Observed: Core diagnostic families are grounded in source

- Source contains valid phase-label helpers, predicted cumulative alias resolution, schema validation, and optional metrics-file comparison structures.
- The task list claims outputs for validation findings, class distributions, confusion matrices, multiclass metrics, binary crisis metrics, cumulative regression metrics, calibration bins, threshold crossing rates, threshold sweeps, and error slices.
- The inspected module surface supports these families, though this pass did not read every function body or execute smoke tests.

### Observed: Spec003 has minimal implementation-vs-design drift

- Spec text says one annual prediction CSV per run; tasks and implementation align with that boundary.
- The main unknown is validation execution status, not design mismatch.

## Task Claim Support

- Supported by inspection: module location under `src/ipcch`, diagnostic config/path defaults, phase-label validation, alias resolution, canonical threshold constants, and task-level implementation organization.
- Not verified by this pass: smoke test output, CLI help output, import check, and generated artifact inspection tasks T047-T053.

## Risks

- Because validation commands were not executed in this pass, readiness depends on separately running or providing the documented smoke/help/import checks.
- This evidence pass did not inspect large prediction CSVs or real annual outputs; it is source/test-artifact grounding only.

## Assumptions

- Assumption: Checked tasks correspond to implemented functions in the module body beyond the excerpt inspected.
- Assumption: Existing smoke tests remain the authoritative lightweight validation for full artifact generation.

## Open Questions

- None blocking for spec alignment.

## Suggested References

- `specs/003-canonical-forecast-diagnostics/evidence.md`
- `src/ipcch/forecast_diagnostics.py`
- `.specify/memory/constitution.md`
