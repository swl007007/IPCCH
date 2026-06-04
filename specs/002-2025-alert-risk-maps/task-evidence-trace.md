# Task Evidence Trace: 2025 Alert Risk Maps

## Summary

Checked tasks are mostly supported by current source inspection. The main trace finding is design drift: tasks and implementation now support a single selected-scope CLI run, while older spec text still says all four final figures are generated in one workflow run.

## Evidence Status

- Evidence Status: Ready
- Validation Status: Not Executed
- Acceptance Readiness: Ready with Risks

## Findings

| Task Area | Evidence | Status | Notes |
|---|---|---|---|
| T001-T004 setup | `src/ipcch/alert_risk_maps.py`, `scripts/reporting/plot_2025_alert_risk_maps.py`, and tests referenced by tasks exist in current repo search/read context | Supported by inspection | Tests not executed. |
| T005-T020 foundational validation | Source includes typed records, output planning, conflict checks, horizon discovery, 2025 filtering, spatial joins, selected files, and validation summaries | Supported by inspection | No command validation run. |
| T021-T027 US1 global actual-vs-predicted | Source supports selected `global` scope and 2x3 0m/3m/6m actual-vs-predicted figure | Supported with design clarification | It is one selected-scope run, not all scopes at once. |
| T028-T034 validation story | Validation errors and summary fields are represented in implementation | Supported by inspection | Integration tests not executed. |
| T035-T041 Somalia actual-vs-predicted | Implementation uses selected non-global scope and country lookup filtering | Supported with design clarification | User confirmed selected scope is intended design. |
| T042-T048 global top-risk | Source computes/plans 0m top-risk figure for selected `global` scope | Supported by inspection | Tests not executed. |
| T049-T054 Somalia top-risk | Source can use selected country scope for 0m top-risk figure | Supported with design clarification | Generate via separate `--scope SOM` run. |
| T055-T066 polish/real validation | Task list claims help/import/unit/integration and real overwrite run | Not verified by this pass | Validation Status remains Not Executed. |

## Design Alignment Finding

- Observed: The implementation has one `--scope` argument and creates one scope’s `actual_vs_predicted` and `top_risk` outputs per run.
- User-confirmed decision: Spec002’s single-scope CLI is the new design, and each run generates one scope.
- Required spec action: Reword FR-001, SC-001, SC-005, user-story acceptance scenarios, and key entities so global/Somalia are supported selected scopes rather than four required outputs from one invocation.

## Assumptions

- Assumption: `global` and `SOM` are the main intended scopes, but the current CLI can accept other ISO3 scopes when country lookup supports them.

## Open Questions

- None blocking.

## Suggested References

- `specs/002-2025-alert-risk-maps/evidence.md`
- `src/ipcch/alert_risk_maps.py`
- `scripts/reporting/plot_2025_alert_risk_maps.py`
