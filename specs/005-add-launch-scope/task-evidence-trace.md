# Task Evidence Trace: Launch Forecast Scope

## Summary

Checked tasks are mostly supported by current source inspection, but task text and the original spec are stale where they restrict allowed scope values to `0`, `3`, and `6`. Current implementation and user clarification establish `12m` as part of the intended scope feature.

## Evidence Status

- Evidence Status: Ready
- Validation Status: Not Executed
- Acceptance Readiness: Ready with Risks

## Findings

| Task Area | Evidence | Status | Notes |
|---|---|---|---|
| T001-T004 setup | Launch CLI, launch config, visualization/comparison modules, and launch tests exist in current repo context | Supported by inspection | Validation entry point not executed. |
| T005-T017 foundational scope helpers | Current implementation includes `scope_months`, CLI `--scope`, period helpers, required-key validation, and static/time-varying helper surfaces | Supported with drift | T005/T006 mention only `{0,3,6}`; current implementation supports `{0,3,6,12}`. |
| T018-T025 US1 scope 0 compatibility | Source behavior supports default scope 0 and additive scope metadata/output behavior | Supported by inspection | Tests not run. |
| T026-T038 US2 forward-scope launch predictions | Source/task claims align for forward target-period metadata and no target-period actual requirement | Supported with drift | Task examples focus on 3m/6m; spec should add 12m examples. |
| T039-T053 US3 leakage prevention | Task claims align with period-aware, area-aware scoped alignment and static/time-varying validation surfaces | Supported by inspection | No command validation run. |
| T054-T062 US4 visualization/reporting | Task claims align with predicted-only visualization and actual-dependent output unavailability handling | Supported by inspection | Real figure/report outputs not inspected. |
| T063-T068 polish validation | Some polish tasks remain unchecked; T065 wording checks `--scope {0,3,6}` and is stale for current baseline | Partially supported | Validation Status remains Not Executed. |

## Design Alignment Finding

- Observed: Current implementation supports `ALLOWED_SCOPE_MONTHS = (0, 3, 6, 12)`.
- User-confirmed decision: Spec005’s `12m` support belongs in the launch-scope feature.
- Required spec action: Update allowed scope values, examples, edge cases, requirements, key entities, success criteria, and assumptions from `0/3/6` to `0/3/6/12`; add the April 2026 → April 2027 target-period example for scope 12.

## Assumptions

- Assumption: Scope 12 uses the same period-aware training/evaluation alignment as scope 3 and 6.
- Assumption: Future actuals for April 2027 are unavailable at launch time, so scope 12 follows the same forecast-only visualization/reporting behavior as other forward scopes.

## Open Questions

- None blocking.

## Suggested References

- `specs/005-add-launch-scope/evidence.md`
- `src/ipcch/launch_nowcasting.py`
- `scripts/modeling/run_launch_nowcasting_2026_04.py`
