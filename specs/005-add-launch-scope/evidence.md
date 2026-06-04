# Repository Evidence: Launch Forecast Scope

## Summary

Mode 3 post-tasks evidence review applies because `tasks.md` exists and implementation tasks are checked. Current implementation supports selected launch forecast scopes `0`, `3`, `6`, and `12` months. The original spec/task text focused on `0`, `3`, and `6`; user clarification confirms `12m` is now part of the intended scope feature and should be reflected in `spec.md`.

## Evidence Status

- Evidence Status: Ready
- Validation Status: Not Executed
- Acceptance Readiness: Ready with Risks
- Last updated: 2026-06-03

## Search Coverage

- Inspected `spec.md` and `tasks.md` for scope semantics, leakage prevention, target-period metadata, and checked task claims.
- Inspected `scripts/modeling/run_launch_nowcasting_2026_04.py` for `--scope` CLI behavior and forecast-weather controls.
- Inspected `src/ipcch/launch_nowcasting.py` for allowed scope validation, scope-aware feature/target period behavior, output/report metadata, and forecast-only behavior.
- Compared current implementation baseline to older spec/task wording that allowed only `0`, `3`, and `6`.

## Findings

### Observed: Current implementation includes 12-month scope

- `ALLOWED_SCOPE_MONTHS` in the launch implementation includes `0`, `3`, `6`, and `12`.
- The CLI `--scope` uses the implementation allowed values and defaults to `0`.
- User clarification confirms `12m` is part of the intended launch-scope feature, not an unrelated later accident.

### Observed: Original spec/task wording is stale for allowed values

- `spec.md` FR-001, edge cases, user-story examples, key entities, success criteria, and assumptions describe only `0`, `3`, and `6`.
- `tasks.md` includes checked setup/polish wording for `--scope {0,3,6}` and notes that scope values remain restricted to `0`, `3`, and `6`.
- Task checkbox states should not be changed by this evidence pass, but the trace should preserve the drift and the spec should be updated to include `12`.

### Observed: Core scope semantics remain aligned

- The feature/target-period distinction remains the central behavior: for scope `s`, launch prediction uses feature-period rows and labels the target period as feature period plus `s` months.
- For April 2026 launch examples, the target periods are April 2026 (`0m`), July 2026 (`3m`), October 2026 (`6m`), and April 2027 (`12m`).
- Forecast-only visualization/reporting remains appropriate when target-period actuals are unavailable.

## Task Claim Support

- Supported by source inspection: selected-scope CLI/config behavior, scope-aware period helpers, output metadata, scoped training/evaluation alignment, static/time-varying validation surfaces, forecast-only visualization/reporting behavior, and scope output coexistence.
- Supported with drift: checked tasks that mention only `0`, `3`, and `6` are stale relative to the current implementation baseline and user-confirmed `12m` inclusion.
- Not verified by this pass: checked help output, targeted tests, integration tests, quickstart/contract updates, and real scoped artifact generation.

## Risks

- If `spec.md` remains restricted to `0`, `3`, and `6`, future readers may incorrectly treat implemented `12m` support as out of scope.
- Some checked tasks still contain old allowed-value wording; this evidence pass does not change task checkbox states.
- Validation commands were not executed, so runtime confidence depends on separately running or providing the documented test/help checks.

## Assumptions

- Assumption: Current source state and the user clarification are the authoritative design baseline for launch scope.
- Assumption: `12m` follows the same period-aware alignment and forecast-only actual-availability rules as `3m` and `6m`.
- Assumption: Existing synthetic tests cover the shared scope machinery sufficiently once updated/verified for `12m`.

## Open Questions

- None blocking.

## Suggested References

- `specs/005-add-launch-scope/evidence.md`
- `src/ipcch/launch_nowcasting.py`
- `scripts/modeling/run_launch_nowcasting_2026_04.py`
