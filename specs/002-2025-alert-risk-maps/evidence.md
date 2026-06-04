# Repository Evidence: 2025 Alert Risk Maps

## Summary

Mode 3 post-tasks evidence review applies because `tasks.md` exists and implementation tasks are checked. Current implementation is a single selected-scope CLI workflow: one run selects one `--scope` (`global` or country ISO3 such as `SOM`) and writes that scope’s actual-vs-predicted and top-risk figures plus one validation summary. This differs from older spec wording that required all four final figures in one run.

## Evidence Status

- Evidence Status: Ready
- Validation Status: Not Executed
- Acceptance Readiness: Ready with Risks
- Last updated: 2026-06-03

## Search Coverage

- Inspected `spec.md` and `tasks.md` for original all-figure/all-scope requirements and checked implementation claims.
- Inspected `scripts/reporting/plot_2025_alert_risk_maps.py` for CLI flags and orchestration call.
- Inspected `src/ipcch/alert_risk_maps.py` for output planning, horizon discovery, selected-scope behavior, filtering, spatial joins, and plotting.
- Searched implementation references for `--scope`, alert risk maps, horizon files, and top-risk outputs.

## Findings

### Observed: Implementation supports one selected map scope per run

- The CLI exposes `--scope`, defaulting to `global` and accepting values such as `SOM` or other country ISO3 codes.
- `run_alert_risk_maps()` resolves one `selected_scope` from either `scope` or the first value in `scopes`, then builds output paths for that selected scope only.
- For the selected scope, the workflow processes all three horizons for the actual-vs-predicted 2x3 figure and the 0m horizon for the top-risk figure.

### Observed: Current outputs are two figure types per selected scope, not four figures in one invocation

- `build_output_plan()` creates two figure paths for the selected scope: `actual_vs_predicted` and `top_risk`.
- The CLI prints output paths from the returned summary for that selected scope.
- User clarification confirms this single-scope CLI is the intended current design: each run generates one scope.

### Observed: Core data validation remains aligned with the feature intent

- Implementation resolves explicit 0m/3m/6m horizon files or discovers candidates; ambiguous/missing candidates raise clear errors.
- The code filters to 2025, retains latest records per `area_id`, validates required columns, rejects failed spatial joins/duplicate join keys, and writes a validation summary under `results/`.
- Somalia-local exclusion/global-grouping handling exists in helper predicates and country-area filtering logic.

## Design Drift to Resolve in Spec

- Older `spec.md` FR-001 and SC-001 require all four final figures in one workflow run. Current design is one geographic scope per run; generating global and Somalia outputs requires separate invocations.
- Older user stories describe global and Somalia as separate required outputs from one workflow. They should be reframed as supported selected scopes.
- The spec should keep 0m/3m/6m horizon behavior for actual-vs-predicted figures and 0m-only behavior for top-risk figures.

## Task Claim Support

- Supported by source inspection: module/CLI creation, horizon file flags, selected scope, validation, latest-record filtering, join validation, 2x3 actual-vs-predicted plotting, top-risk plotting, output conflict checks, and validation summaries.
- Not verified by this pass: checked help/import/unit/integration commands and real-data regeneration task T066.

## Risks

- Validation commands were not run by this pass.
- Existing spec text can mislead future implementers into expecting one command to produce all global and Somalia figures; it should be updated to the current single-scope design.

## Assumptions

- Assumption: The user-confirmed single-scope CLI is the authoritative design baseline.
- Assumption: Generating both global and Somalia deliverables is done by invoking the same CLI separately for `--scope global` and `--scope SOM`.

## Open Questions

- None blocking. User clarification resolves the main implementation-vs-design difference.

## Suggested References

- `specs/002-2025-alert-risk-maps/evidence.md`
- `src/ipcch/alert_risk_maps.py`
- `scripts/reporting/plot_2025_alert_risk_maps.py`
