# Repository Evidence: Phase-3 SHAP Six-Category Feature Importance

## Feature Request

Add optional post-hoc SHAP explainability artifacts to the existing IPCCH forecasting weight-decay pipeline, focused only on the `phase3_worse` cumulative regressor, aggregated through a six-category feature crosswalk, and visualized as one 6 x 4 heatmap per forecasting scope.

## Evidence Status

- Status: Ready
- Final Speckit feature directory: `specs/006-phase3-shap-importance/`
- Feature directory: `specs/006-phase3-shap-importance/`
- Evidence artifact path: `specs/006-phase3-shap-importance/evidence.md`
- Last updated: 2026-06-01
- Scope inspected: governance docs, feature spec/plan/tasks/design artifacts, existing weight-decay CLI/module, SHAP helper module, unit/smoke tests, path config, package metadata, repository grep coverage.
- Major unknowns: external crosswalk file existence/content was not verified; pytest and CLI commands were not executed by this evidence pass; real full-scope production SHAP outputs were not inspected.

## Search Coverage

| Search Term / Method | Purpose | Result | Notes |
|---|---|---|---|
| `find specs/006-phase3-shap-importance` | Determine Speckit artifact mode | Found `spec.md`, `plan.md`, `tasks.md`, design docs, contract; no pre-existing `evidence.md` | Because `tasks.md` exists, latest review mode is Mode 3. |
| Governance/doc scan (`constitution.md`, `CLAUDE.md`, docs) | Identify project constraints | Constitution requires temporal integrity, reusable `src/ipcch` utilities, path-agnostic config, artifact separation, safe validation | See `.specify/memory/constitution.md` lines 54-155 and 236-280. |
| `phase3|phase 3|SHAP|shap|feature importance|importance|XGBoost|convert_prob_to_phase|all_metrics` | Locate feature-domain implementation and nearby conventions | Found weight-decay SHAP implementation, canonical regressor docs, phase-3 metrics, tests | Search excluded generated outputs, reports, `.git`, `.claude`, and notebooks for token control. |
| `six_category_feature_crosswalk|enable-shap|variable-crosswalk|phase3_worse_feature_summary|phase3_worse_heatmap|raw-shap` | Locate SHAP-specific CLI, paths, tests, artifacts | Found config key, helper constants, CLI options, tests, and Spec Kit artifacts | Confirms implementation names match contract terms. |
| `git status --short && git diff --stat` | Determine whether source evidence is provisional | Only `.claude/settings.local.json` modified and `speckit-evidence-pack/` untracked were reported | Source/test files inspected are current working-tree state with no git diff shown. |

## Negative Evidence / Not Found

| Searched For | Search Method / Terms | Result | Implication |
|---|---|---|---|
| Existing `evidence.md` for feature 006 | Feature directory listing | Not found | This artifact is the first evidence pack for the feature. |
| Smoke test for overwrite conflict behavior | Read `tests/smoke/test_weight_decay_shap_cli.py` | No test asserting existing SHAP outputs fail without `--overwrite` | Task trace should flag T057 as unsupported by inspected test file. |
| Smoke test for unavailable SHAP package/engine | Read `tests/smoke/test_weight_decay_shap_cli.py` | No monkeypatch/environment test for missing `shap`; only missing crosswalk/dataset errors observed | Task trace should flag T021 as not evidenced by current smoke tests. |
| Smoke test exercising raw export size guard through CLI | Read `tests/smoke/test_weight_decay_shap_cli.py` | Help flags are checked; raw size guard behavior is unit-tested in helper tests, not CLI smoke-tested | Task trace should flag T058 as partially evidenced only. |
| Verified external crosswalk content | File reads/searches only | External source data not read | Crosswalk schema/content remains an operational unknown until local external path is available. |
| Executed test results for T065/T066 | Evidence pass was read/search-oriented | Tests were not run; tasks remain unchecked in `tasks.md` | Completion status depends on separate validation. |

## Files Inspected

| Path | Type | Why Inspected | Relevant Finding | Implication | Confidence |
|---|---|---|---|---|---|
| `.specify/memory/constitution.md` | Governance | Determine mandatory project constraints | Temporal validation is non-negotiable; reusable code must live in `src/ipcch`; paths must use `ipcch.paths`/config; validation avoids heavy training | SHAP must remain post-hoc, path-agnostic, lightweight-testable, and in package utilities | High |
| `CLAUDE.md` | Project instructions | Confirm canonical model conventions | Canonical workflow is four cumulative XGBoost regressors with phase-3-specific hyperparameters and `convert_prob_to_phase()` threshold behavior | Feature must not replace canonical regressor workflow or add classifier behavior | High |
| `specs/006-phase3-shap-importance/spec.md` | Feature spec | Identify requirements and acceptance criteria | FR-001–FR-036 define optional phase-3-only SHAP, six groups, 96-row complete table, four 6 x 4 heatmaps, metadata/diagnostics, path controls | Evidence/task trace should map tasks back to these requirements | High |
| `specs/006-phase3-shap-importance/plan.md` | Plan | Ground planned implementation | Plan targets `src/ipcch/forecasting_shap.py`, weight-decay CLI, config path key, tests, and no heavy validation | Planned file targets align with current repo conventions | High |
| `specs/006-phase3-shap-importance/tasks.md` | Tasks | Mode 3 trace input | Tasks are mostly marked complete; T065/T066 remain unchecked; tasks describe tests and implementation by story | Requires trace check for completed-task evidence and remaining validation | High |
| `specs/006-phase3-shap-importance/contracts/cli-shap-options.md` | Contract | Verify user-facing CLI and artifact expectations | Contract defines `--enable-shap`, crosswalk path/key/columns, sample, unmapped, raw export, overwrite, filenames | CLI evidence should be compared against this list | High |
| `specs/006-phase3-shap-importance/quickstart.md` | Quickstart | Verify lightweight validation and run examples | Quickstart uses `--help`, dry-run, unit/smoke tests, and path-key SHAP examples; completion checks require 96 rows and four heatmaps | Supports validation discipline, but actual tests were not run here | High |
| `src/ipcch/forecasting_shap.py` | Source | Inspect reusable SHAP helper implementation | Defines target/sample constants, optional SHAP import, alignment validation, crosswalk validation, aggregation, heatmap, raw export guard | Reusable helper exists in package and supports most feature requirements | High |
| `src/ipcch/forecasting_weight_decay.py` | Source | Inspect existing weight-decay pipeline and output planning | Defines annual splits, target columns, feature exclusion, phase threshold, SHAP output paths, overwrite checks | Existing split/feature/output conventions are available for SHAP wiring | High |
| `scripts/modeling/run_deep_feature_weight_decay_forecasting.py` | Source | Inspect actual CLI entrypoint and SHAP wiring | CLI exposes SHAP flags; `run_holdout()` callback captures phase-3 model matrices; metadata/report writing includes SHAP fields | CLI supports optional SHAP; current run appears scoped to one selected `--fs` per invocation | High |
| `tests/unit/test_forecasting_shap.py` | Tests | Inspect helper validation coverage | Tests target phase-3 enforcement, alignment, crosswalk, aggregation, matrix shape, heatmap name, raw size guard | Synthetic helper coverage exists; not executed in this pass | High |
| `tests/smoke/test_weight_decay_shap_cli.py` | Tests | Inspect CLI smoke coverage | Tests help options, absence of local Dropbox defaults, disabled crosswalk behavior, explicit crosswalk override error | Some task-claimed smoke cases are not fully evidenced | High |
| `configs/paths.example.json` | Config | Verify documented external path key | Contains `six_category_feature_crosswalk` key with relative external source path | Supports path-agnostic crosswalk resolution pattern | High |
| `pyproject.toml` | Package metadata | Verify dependency strategy | Defines optional dependency group `shap = ["shap"]` | SHAP is optional and should be imported only when enabled | High |

## Existing Similar Behavior

| Behavior / Pattern | Source | How It Works | Relevance | Implication |
|---|---|---|---|---|
| All-prior-history annual holdout | `.specify/memory/constitution.md`; `src/ipcch/forecasting_weight_decay.py` | Constitution requires train before Jan 1 of test year; `annual_splits()` uses `date < start` for train and calendar-year test | SHAP must reuse existing split matrices and not alter fitting/metrics | Explain after phase-3 model fit, never for split/tuning decisions |
| Canonical cumulative regressor targets | `.specify/memory/constitution.md`; `src/ipcch/forecasting_weight_decay.py` | Targets are `phase2_worse`, `phase3_worse`, `phase4_worse`, `phase5_worse`; phase 3 has separate hyperparameters | Feature target is only `phase3_worse` | Avoid classifier/final-label explanations |
| Target and prediction feature exclusion | `src/ipcch/forecasting_weight_decay.py` | `select_numeric_feature_columns()` excludes IDs, dates, phase percentages, cumulative targets, predictions, labels | Prevents target leakage into model and SHAP explanation matrix | SHAP feature columns should come from the fitted model feature list |
| Path-agnostic external inputs | `.specify/memory/constitution.md`; `src/ipcch/forecasting_weight_decay.py`; `configs/paths.example.json` | `resolve_input_path()` uses explicit path or `paths.external_path()`; config documents external keys | Crosswalk should be explicit path or config key | No hardcoded local absolute crosswalk path |
| Output separation | `.specify/memory/constitution.md`; `src/ipcch/forecasting_weight_decay.py` | Output plan separates `results/.../shap/phase3` and `reports/.../shap/phase3` | Matches spec artifact separation | Generated SHAP outputs should remain under results/reports |
| Lightweight validation | `.specify/memory/constitution.md`; `quickstart.md`; tests | Automation uses help, dry-run, unit/smoke tests, synthetic inputs | Avoids heavy model training | Remaining validation should run T065/T066 separately, not notebooks |

## Related Tests

| Test Path | Behavior Covered | Test Pattern | Missing Coverage | Implication |
|---|---|---|---|---|
| `tests/unit/test_forecasting_shap.py` | Phase-3 target enforcement, feature alignment, SHAP shape normalization, diagnostics, crosswalk validation, aggregation, matrix shape, heatmap rendering, raw size guard | Synthetic DataFrames/arrays and temp artifact output | Does not validate real SHAP engine with fitted XGBoost; not executed in this pass | Good unit grounding for helpers, but runtime SHAP compatibility needs separate validation |
| `tests/smoke/test_weight_decay_shap_cli.py` | CLI help options, no local Dropbox defaults, disabled crosswalk behavior, explicit crosswalk path override error, raw flags visible | Subprocess calls to CLI with `--help` and deliberately missing paths | Missing/partial evidence for overwrite conflict, missing SHAP package failure, raw export guard via CLI, valid temp crosswalk selection | Some tasks marked complete should be revisited or reworded |

## Existing APIs / Contracts / Schemas

| Item | Source | Current Behavior | Compatibility Concern | Implication |
|---|---|---|---|---|
| CLI entrypoint | `scripts/modeling/run_deep_feature_weight_decay_forecasting.py` | Existing command exposes dataset/scope/output/dry-run flags and new SHAP flags | Default-disabled behavior must not require crosswalk or SHAP package | Keep `--enable-shap` as the only activation path |
| SHAP CLI contract | `specs/006-phase3-shap-importance/contracts/cli-shap-options.md` | Defines exact user-facing controls and artifact contract | Smoke tests do not cover every contract behavior | Keep contract in `spec.md ## References` or evidence references for later stages |
| Artifact filenames | `src/ipcch/forecasting_weight_decay.py`; `src/ipcch/forecasting_shap.py` | Filenames include `phase3_worse` and scope for matrix/heatmap | Per-run script metadata only lists selected `args.fs` matrix/heatmap | Clarify whether four scopes are produced in one run or by repeated runs |
| Optional SHAP dependency | `pyproject.toml`; `src/ipcch/forecasting_shap.py` | `shap` is optional extra; import attempted in `import_shap_engine()` only when SHAP computation is requested | Runtime environment may lack SHAP | SHAP-enabled runs should fail clearly; disabled runs should not import `shap` |

## Data Models / Persistence

| Model / Storage Area | Source | Current Pattern | Migration / Compatibility Concern | Implication |
|---|---|---|---|---|
| Crosswalk | `data-model.md`; `configs/paths.example.json`; `src/ipcch/forecasting_shap.py` | External CSV maps feature names to exactly six display groups; path key is `six_category_feature_crosswalk` | External file content not verified | Keep validation strict and diagnostics explicit |
| Per-feature SHAP summary | `data-model.md`; `src/ipcch/forecasting_shap.py` | Rows include scope, label, year, target, sample type, feature, group, absolute sum, mean absolute SHAP, row count | Current helper omits unmapped features from summary | Diagnostics must preserve unmapped contribution when allowed |
| Six-category long table | `data-model.md`; `src/ipcch/forecasting_shap.py` | Six rows per scope-year; relative importance divides by mapped total; zero denominator writes zeros | Complete 96 rows require all four scopes and years | Clarify multi-scope orchestration expectations |
| Matrix/heatmap reports | `data-model.md`; `src/ipcch/forecasting_shap.py`; `src/ipcch/forecasting_weight_decay.py` | Matrix columns are 2022-2025; heatmap filenames are phase-3-only | Script writes selected-scope matrix/heatmap in current implementation | If spec expects one invocation to produce four heatmaps, add orchestration task |
| Metadata/diagnostics | `data-model.md`; `scripts/modeling/run_deep_feature_weight_decay_forecasting.py` | Metadata includes split rule, target, sample type, crosswalk source, diagnostics, artifact paths | Some metadata fields are populated only after non-dry-run SHAP contexts | Dry-run/default-disabled metadata expectations should stay explicit |

## Auth / Validation / Error Handling / Observability Patterns

| Concern | Source | Existing Pattern | Required Follow-up |
|---|---|---|---|
| Temporal validation | `annual_splits()` and split diagnostics in `src/ipcch/forecasting_weight_decay.py` | Build train/test per year and fail if training rows are on/after test start | SHAP callback should continue using existing `X_train`/`X_test` context only |
| Crosswalk validation | `src/ipcch/forecasting_shap.py` | Detect columns, require six groups, reject duplicate multi-group mappings, fail missing mappings unless allowed | Verify external crosswalk names/categories when file is available |
| Feature alignment | `src/ipcch/forecasting_shap.py` | Requires SHAP matrix column order match fitted phase-3 feature columns | Keep target/prediction exclusions upstream |
| Overwrite conflicts | `src/ipcch/forecasting_weight_decay.py` | `check_existing_outputs()` includes SHAP artifacts when `include_shap=True` | Add/confirm smoke coverage for SHAP overwrite conflict |
| Raw export guard | `src/ipcch/forecasting_shap.py` | Refuses raw SHAP frame exceeding max rows unless override is set | Add/confirm CLI smoke coverage if required by tasks |
| User-facing errors | `scripts/modeling/run_deep_feature_weight_decay_forecasting.py` | `main()` prints `ERROR: ...` and returns nonzero | Missing/incompatible SHAP engine behavior needs explicit smoke evidence |

## Architecture Constraints

| Constraint | Source | Implication | Risk |
|---|---|---|---|
| No future/test leakage | `.specify/memory/constitution.md` lines 54-85 | SHAP must not influence model fitting, weights, thresholds, metrics, or selection | Any pre-fit explanation/sample selection based on test outcomes would violate governance |
| Reusable code in `src/ipcch` | `.specify/memory/constitution.md` lines 87-104 | SHAP helpers belong in package module, not notebooks/root scripts | Duplicated notebook logic would fail constitution check |
| Path-agnostic external paths | `.specify/memory/constitution.md` lines 106-123 | Crosswalk path must be CLI/config-driven | Hardcoded Dropbox path would break collaborators |
| Separate results/reports | `.specify/memory/constitution.md` lines 125-148 | Machine-readable SHAP CSV/JSON in `results`; heatmaps/reports in `reports` | Mixed output locations would confuse reproducibility/deliverables |
| No heavy automated training | `.specify/memory/constitution.md` lines 150-155 | Evidence/validation should use static reads, help, dry-run, synthetic tests | Full production SHAP verification remains manual/explicit |
| No classifier scope | `spec.md`; constitution data/model standards | Feature remains canonical regressor-only | Classifier controls/artifacts would be out of scope |

## Risks

| Risk | Evidence | Severity | Mitigation / Follow-up |
|---|---|---|---|
| Tasks marked complete without matching smoke evidence | `tasks.md`; `tests/smoke/test_weight_decay_shap_cli.py` | Medium | Add/adjust smoke tests for T021, T055, T057, T058 or update task descriptions to match actual coverage |
| Four-scope deliverable may require repeated single-scope runs | `spec.md` requires four heatmaps; current CLI writes selected `args.fs` matrix/heatmap | Medium | Clarify whether one invocation must generate all scopes or quickstart should document running `--fs fs0..fs3` |
| External crosswalk schema/content unknown | External source file not read | Medium | Validate with configured `six_category_feature_crosswalk` before production use |
| SHAP package/runtime compatibility not proven | Optional dependency exists; tests read but not run; no real fitted-model SHAP smoke observed | Medium | Run lightweight SHAP-enabled test with tiny fitted model or mocked engine if required |
| Unit/smoke validation incomplete | T065/T066 unchecked in `tasks.md` | Medium | Run the two pytest commands after evidence pack review |

## Open Questions

| Question | Why It Matters | Who / What Can Resolve It | Blocking? |
|---|---|---|---|
| Should one CLI invocation produce all four scope heatmaps, or is a complete deliverable assembled by running the CLI once per `--fs`? | Spec success criteria say four heatmaps; current CLI is selected-scope-oriented | User/spec owner or implementation decision | Potentially blocking for final acceptance |
| Is the external crosswalk file available at the configured key and does it map every selected model feature? | Aggregation fails by default on missing model-feature mappings | Local config/external source data validation | Blocking for production SHAP run |
| Should smoke tests simulate missing `shap` package explicitly? | Tasks claim this behavior, but current smoke tests do not evidence it | Test owner | Not blocking for evidence, blocking for task completion confidence |
| Should overwrite conflict be tested at helper level or CLI level? | T057 requests smoke/unit coverage; helper supports check, but inspected smoke file lacks assertion | Test owner | Not blocking for evidence, blocking for task trace closure |

## Assumptions

| Assumption | Basis | Confidence | How To Validate |
|---|---|---|---|
| The source/test files inspected represent committed current implementation | `git status --short` showed no source/test diffs | Medium | Confirm `git status` before merge and review recent commit containing SHAP feature |
| The crosswalk category labels are exactly the six requested groups | Spec and configured path imply this, but external file not read | Low | Read configured crosswalk and run `validate_crosswalk()` with model feature columns |
| A complete 96-row output may be assembled across four single-scope runs | CLI is `--fs` scoped while spec requires four scopes | Low | Ask user/spec owner or add all-scope orchestration |
| Unit/smoke tests will pass when run with `PYTHONPATH=src` | Test files exist and quickstart documents commands; not executed here | Medium | Run T065/T066 commands |

## Implications for Spec

- Observed: `spec.md` should reference this evidence artifact so future Speckit stages can load repository grounding without re-scanning all source files.
- Inference: `spec.md` or quickstart may need to clarify whether “all four forecasting scopes” means one run across all scopes or one selected-scope run repeated for `fs0`-`fs3`.
- Assumption: External crosswalk labels remain the source of truth for display names, as stated in `spec.md` and `data-model.md`.

## Implications for Plan

- Observed: The plan’s main file targets are grounded in current files: `src/ipcch/forecasting_shap.py`, `src/ipcch/forecasting_weight_decay.py`, `scripts/modeling/run_deep_feature_weight_decay_forecasting.py`, `configs/paths.example.json`, and tests.
- Observed: The constitution supports optional SHAP as post-hoc explainability if it does not affect temporal splits, fitting, thresholds, or metrics.
- Inference: The plan should carry forward the risk that complete four-scope outputs may require explicit orchestration or documentation.

## Implications for Tasks

- Observed: T065 and T066 remain unchecked and should be run or intentionally deferred before claiming full validation.
- Observed: Some tasks marked `[X]` are only partially evidenced by inspected tests: T021, T055, T057, and T058.
- Inference: Add or adjust tests before final task closure, especially for overwrite conflicts, missing SHAP engine, and raw export guard through the CLI.

## Suggested References

| Path | Why Include | Reference Type | Needed For |
|---|---|---|---|
| `specs/006-phase3-shap-importance/evidence.md` | Main feature evidence artifact and scan coverage | Evidence | plan/tasks/implement/review |
| `specs/006-phase3-shap-importance/contracts/cli-shap-options.md` | High-signal CLI and artifact contract | Contract | CLI wiring and smoke tests |
| `.specify/memory/constitution.md` | Governing temporal/path/artifact/testing constraints | Governance | plan/tasks/review |

## Copy into spec.md

```markdown
## References

- specs/006-phase3-shap-importance/evidence.md
- specs/006-phase3-shap-importance/contracts/cli-shap-options.md
- .specify/memory/constitution.md
```
