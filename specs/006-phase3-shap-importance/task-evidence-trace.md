# Task Evidence Trace: Phase-3 SHAP Six-Category Feature Importance

## Summary

Mode 3 post-tasks evidence trace was run because `specs/006-phase3-shap-importance/tasks.md` exists. Repository evidence now exists at `specs/006-phase3-shap-importance/evidence.md`. Most task groups are grounded in the spec, plan, contract, and inspected source files, but several completed smoke-test tasks are only partially supported by the inspected test file, and the all-four-scope deliverable needs clarification against the selected-`--fs` CLI behavior.

## Findings

| Task | Expected Trace | Evidence / Plan Source | Issue | Severity | Recommended Action |
|---|---|---|---|---|---|
| T021 | US1 / FR-027a: SHAP-enabled CLI path fails clearly when SHAP engine unavailable or incompatible | `spec.md` FR-027a; `src/ipcch/forecasting_shap.py` `import_shap_engine()`; `tests/smoke/test_weight_decay_shap_cli.py` | Observed: helper has fail-fast import behavior, but inspected smoke tests do not simulate missing/incompatible `shap`; current SHAP-enabled smoke path fails on missing crosswalk/dataset instead. | Medium | Add a smoke/unit test that isolates SHAP engine unavailability, or change T021 completion evidence to point to a helper-level test. |
| T055 | US4 / FR-012, FR-028: explicit crosswalk path selection | `contracts/cli-shap-options.md`; `scripts/modeling/run_deep_feature_weight_decay_forecasting.py`; `tests/smoke/test_weight_decay_shap_cli.py` | Observed: smoke test verifies an explicit missing crosswalk path appears in stderr and overrides a bad key, but it does not use a temporary valid crosswalk as the task states. | Low | Either add a temp valid-crosswalk smoke path or revise task wording to “explicit missing path/override resolution.” |
| T057 | US4 / FR-080 and overwrite behavior: SHAP overwrite conflicts fail when `--overwrite` omitted | `src/ipcch/forecasting_weight_decay.py` `check_existing_outputs()` includes SHAP artifacts when `include_shap=True`; `tests/smoke/test_weight_decay_shap_cli.py` | Observed: implementation support exists, but no inspected smoke/unit test asserts SHAP output conflict behavior. | Medium | Add a smoke or unit test that creates planned SHAP artifact(s) and verifies non-overwrite failure. |
| T058 | US4 / FR-011a: raw row-level SHAP export size guard | `src/ipcch/forecasting_shap.py` `enforce_raw_export_size()`; `tests/unit/test_forecasting_shap.py`; `tests/smoke/test_weight_decay_shap_cli.py` | Observed: helper unit test covers size guard; smoke test only verifies raw flags are visible in help. The task specifically requests smoke coverage of raw export behavior. | Low | Keep helper test and either add CLI-level raw guard smoke or split the task into helper and CLI coverage. |
| T065/T066 | Polish validation: run unit and smoke tests | `tasks.md`; `quickstart.md` | Observed: both remain unchecked in `tasks.md`; this evidence pass did not execute pytest. | Medium | Run `PYTHONPATH=src pytest tests/unit/test_forecasting_shap.py` and `PYTHONPATH=src pytest tests/smoke/test_weight_decay_shap_cli.py` before claiming validation complete. |
| T062 / US3-US4 artifact paths | FR-003, FR-019, FR-021: all four scopes and four heatmaps | `spec.md` SC-001/SC-003; `scripts/modeling/run_deep_feature_weight_decay_forecasting.py`; `src/ipcch/forecasting_weight_decay.py` | Observed: output plan has matrix/heatmap paths for all scopes, but current CLI run writes metadata and heatmap/matrix for selected `args.fs` only. Assumption: complete deliverable may require four separate `--fs` runs. | Medium | Clarify spec/quickstart or add orchestration for all scopes in one run. |

## Assumptions

- Assumption: Source/test files inspected are intended implementation state; `git status` showed no source/test diffs, but this trace did not inspect commits.
- Assumption: The external crosswalk file exists and contains exactly six display groups; this was not verified because external data was not read.
- Assumption: Full production SHAP outputs are generated manually or by repeated selected-scope runs; current evidence does not show one command producing four scope heatmaps.

## Open Questions

| Question | Why It Matters | Blocking? |
|---|---|---|
| Should `run_deep_feature_weight_decay_forecasting.py` support an all-scope mode for SHAP, or is four separate `--fs` invocations acceptable? | Spec success criteria require four scope heatmaps and a 96-row complete table. | Potentially |
| Should completed task checkboxes be treated as implementation status or validation status? | Several `[X]` tests are not fully evidenced by inspected test files. | No, but affects readiness reporting |
| Is the configured crosswalk available in the user’s local `paths.local.json` and schema-compatible with model features? | Production aggregation depends on it. | Yes for production run |

## Suggested References

- `specs/006-phase3-shap-importance/evidence.md`
- `specs/006-phase3-shap-importance/contracts/cli-shap-options.md`
- `.specify/memory/constitution.md`
