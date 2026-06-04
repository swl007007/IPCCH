# Repository Evidence

## Feature Request

Add an optional grouped SHAP workflow to the April 2026 launch nowcasting workflow. The grouped SHAP computation should explain the phase-3 cumulative regressor using the training feature matrix, map features to the six-category forecasting crosswalk plus a seventh `weather forecast` group, write grouped SHAP outputs and diagnostics, and render a forecasting-scope-by-group heatmap for scopes `0m`, `3m`, `6m`, and `12m`.

## Evidence Status

- Status: Ready
- Draft slug: grouped-shap-nowcasting
- Final Speckit feature directory: Assumption: not created yet
- Feature directory: `specs/_evidence/`
- Evidence artifact path: `specs/_evidence/grouped-shap-nowcasting.evidence.md`
- Last updated: 2026-06-03
- Scope inspected: current SHAP helpers, forecasting SHAP CLI integration, nowcasting launch module and wrapper CLI, nowcasting weather-feature tests, crosswalk header/sample rows, constitution/governance docs
- Major unknowns: whether the final implementation should aggregate across four independent nowcasting scope runs or orchestrate all scopes in one command; whether grouped SHAP should be supported in Mode 2 supplied-model runs and hard-fail in Mode 3 supplied-prediction runs

## Validation Status

- Status: Not Applicable
- Tests executed by this pass: none
- Commands executed: repository searches and file/artifact inspection only
- Commands not executed: no tests, no CLI smoke checks, no model training, no SHAP computation
- Artifact outputs inspected: crosswalk header/sample rows only
- Artifact outputs not inspected: existing generated SHAP outputs under `results/`/`reports/`, if any
- Validation evidence source: source/test/static artifact inspection
- Remaining validation unknowns: runtime SHAP cost and memory footprint on the launch training matrix; whether the `shap` package is available in every intended launch environment

## Acceptance Readiness

- Status: Not Applicable
- Reason: This is a pre-spec evidence pass; implementation and validation are outside this skill's scope.
- Blocking issues: none for evidence grounding
- Non-blocking risks: existing grouped SHAP helpers assume exact crosswalk matching and a year-by-year heatmap; nowcasting requirements need robust normalized matching and a scope-by-group matrix.
- Required follow-up before final acceptance: implement code, add tests, run CLI help, run without flag, run with flag on a bounded dataset or approved full launch, inspect matrix/mapping/heatmap outputs.

## Search Coverage

| Search Term / Method | Purpose | Result | Notes |
|---|---|---|---|
| `find . -maxdepth 3 ... spec.md plan.md tasks.md evidence.md` | Locate existing Speckit feature artifacts and choose evidence-pack mode | No grouped-nowcasting SHAP feature directory found; existing specs `001`-`006` found | Mode 1 pre-spec evidence pass selected. |
| `Read .specify/memory/constitution.md` | Governance and quality constraints | Observed package, path, artifact separation, safe execution, and canonical model rules | Most relevant lines: `.specify/memory/constitution.md:54-80`, `87-123`, `125-148`, `150-179`, `236-280`. |
| `smart_outline src/ipcch/forecasting_shap.py` | Identify reusable SHAP helper surface | Found SHAP config/path dataclasses, crosswalk validation, per-feature summary, aggregation, matrix, heatmap, raw export helpers | Detailed inspection followed. |
| `grep -R "group\|shap\|six_category\|crosswalk\|forecasting_shap" ...` | Locate similar grouped SHAP integrations | Found `scripts/modeling/run_deep_feature_weight_decay_forecasting.py`, `tests/unit/test_forecasting_shap.py`, `tests/smoke/test_weight_decay_shap_cli.py` | No existing nowcasting grouped SHAP integration found. |
| `Read src/ipcch/forecasting_shap.py` | Reference implementation details | Observed exact feature-order validation, SHAP computation, six-category validation, aggregation, diagnostics, heatmap naming | Current helpers are reusable but exact-match/six-category/year-oriented. |
| `Read scripts/modeling/run_deep_feature_weight_decay_forecasting.py` | Workflow integration pattern | Observed CLI flags, callback on phase3 model training, training/test SHAP sample selection, output writes and metadata | Useful integration model but nowcasting should force training matrix per requirement. |
| `Read src/ipcch/launch_nowcasting.py` | Target workflow integration points | Observed training feature matrix construction, feature selection, model training, prediction, output layout, run summary/reporting | New SHAP hook should attach after model training/loading and before/near run summary output. |
| `Read scripts/modeling/run_launch_nowcasting_2026_04.py` | Actual nowcasting CLI parser | Observed current CLI flags live in wrapper script, not in `launch_nowcasting.py` | Important for requirement wording: CLI exposure likely requires wrapper changes plus launch module support. |
| `Read tests/unit/test_forecasting_shap.py` | Existing unit test expectations | Observed tests for feature order, crosswalk validation, unmapped diagnostics, 6x4 year matrix, heatmap artifact naming | New tests should adapt/extend, not silently break existing 6-category behavior. |
| `Read tests/smoke/test_weight_decay_shap_cli.py` | Existing SHAP CLI smoke patterns | Observed help visibility and disabled-SHAP no-crosswalk behavior tests | Nowcasting CLI should get analogous smoke tests. |
| `Read crosswalk CSV sample` | Crosswalk schema and labels | Observed columns `variable,six_category,...`, with category values such as `agriculture` | Crosswalk auto-detection supports `variable` and `six_category`. |
| `git status --short` | Check whether inspected source is provisional | Observed uncommitted changes in nowcasting files and two new plotting scripts | Treat current `launch_nowcasting.py`/tests evidence as provisional until committed or accepted. |

## Negative Evidence / Not Found

| Searched For | Search Method / Terms | Result | Implication |
|---|---|---|---|
| Existing nowcasting SHAP CLI flag | Grep for `shap`, read `scripts/modeling/run_launch_nowcasting_2026_04.py` | No nowcasting SHAP flag observed in lines `27-72` | Feature needs new CLI exposure. |
| Existing grouped SHAP code in `launch_nowcasting.py` | Smart outline and grep | No SHAP symbols observed in module outline | Feature needs new integration in the nowcasting workflow. |
| Robust normalized crosswalk matching | `forecasting_shap.py` inspection | Existing `validate_crosswalk()` checks exact feature names only (`feature_set - mapped_set`) | Requirement needs new or adapted matching helper. |
| Scope-by-group nowcasting heatmap helper | `forecasting_shap.py` inspection | Existing `scope_matrix()` pivots one forecasting scope across test years and `render_heatmap()` x-axis is years | Requirement needs new matrix/plot function or parameters. |
| Unmatched fallback group support | `forecasting_shap.py` inspection | Existing allowed unmapped features are diagnosed and excluded from six-category denominator, not assigned to `other` | Nowcasting requirement should explicitly choose diagnostics vs fallback group. |

## Files Inspected

| Path | Symbols / Sections | Type | Why Inspected | Relevant Finding | Implication | Confidence |
|---|---|---|---|---|---|---|
| `.specify/memory/constitution.md` | Core principles, quality gates | Governance | Establish constraints for implementation planning | Shared code must live under `src/ipcch/`; paths should use `ipcch.paths`; generated machine outputs under `results/`, reports under `reports/`; heavy training not run by automation unless requested | SHAP helpers belong in package code; output layout should preserve results/reports split; validation should use help/smoke tests unless full run approved | High |
| `src/ipcch/forecasting_shap.py` | `compute_phase3_shap_values()` lines `138-147` | Source | Reference SHAP computation | Validates exact matrix feature order, calls `shap.TreeExplainer`, normalizes values | Nowcasting should reuse this for phase3 model with `train_featured.loc[:, feature_columns]` in exact order | High |
| `src/ipcch/forecasting_shap.py` | `validate_feature_alignment()` lines `112-116` | Source | Preserve fitted model feature order | Raises if matrix columns differ from `feature_columns` | Training SHAP matrix must be column-ordered exactly as fitted model expects | High |
| `src/ipcch/forecasting_shap.py` | `load_crosswalk()`, `detect_crosswalk_columns()`, `_select_column()` lines `191-216` | Source | Crosswalk handling | Auto-detects feature/category columns including `variable` and `six_category` | Can reuse for the provided crosswalk schema | High |
| `src/ipcch/forecasting_shap.py` | `validate_crosswalk()` lines `219-249` | Source | Existing mapping policy | Requires exactly six groups and exact feature name mappings unless `allow_unmapped=True` | This is too strict for nowcasting suffix/lag/current matching; adapt rather than use unchanged | High |
| `src/ipcch/forecasting_shap.py` | `per_feature_shap_summary()` lines `252-284` | Source | Per-feature output shape | Computes absolute SHAP sums and mean abs SHAP per mapped feature; silently skips unmapped features | Reusable if the nowcasting mapping table is normalized to `feature_name, feature_group`; but unmatched policy needs care | High |
| `src/ipcch/forecasting_shap.py` | `aggregate_six_category_importance()` lines `287-318` | Source | Group aggregation | Aggregates `abs_shap_sum` by group and computes `relative_importance` over mapped denominator | Can be generalized to seven groups plus optional unmatched/other; current name is six-category-specific | High |
| `src/ipcch/forecasting_shap.py` | `unmapped_feature_diagnostics()` lines `321-348` | Source | Unmatched handling | Records unmapped features and their absolute SHAP share; unmapped features are excluded from denominator | Requirement says do not silently drop; diagnostic-file approach is consistent with existing implementation | High |
| `src/ipcch/forecasting_shap.py` | `scope_matrix()` lines `351-367`, `render_heatmap()` lines `377-400` | Source | Existing heatmap pattern | Current matrix rows=groups, columns=test years for one scope; heatmap x-label is `test year` | Nowcasting needs rows=groups, columns=`0m/3m/6m/12m`; likely new helper needed | High |
| `scripts/modeling/run_deep_feature_weight_decay_forecasting.py` | CLI options lines `73-105` | Source | Existing SHAP CLI conventions | Uses `--enable-shap`, `--variable-crosswalk-path/key`, `--crosswalk-feature-column`, `--crosswalk-category-column`, `--allow-unmapped-shap-features`, raw export controls | Nowcasting can mirror high-signal flags but should avoid unsupported `--shap-sample` if training-only is required | High |
| `scripts/modeling/run_deep_feature_weight_decay_forecasting.py` | `build_phase3_shap_callback()` lines `477-538` | Source | Integration pattern | Callback computes SHAP after fitting phase3 model; uses `X_train` or `X_test`; appends per-feature/group/raw frames and summaries | Nowcasting can implement direct post-training phase3 SHAP instead of callback because it trains all four models in one function | High |
| `scripts/modeling/run_deep_feature_weight_decay_forecasting.py` | `run()` lines `597-687`, metadata lines `710-732` | Source | Output/metadata pattern | Loads/validates crosswalk only when SHAP enabled; writes feature summary, long group table, matrix, heatmap, diagnostics, metadata | Nowcasting should keep no-flag behavior unchanged and record artifact paths in run summary/metadata | High |
| `src/ipcch/forecasting_weight_decay.py` | `OutputPlan` lines `60-84`, `plan_outputs()` lines `431-465` | Source | SHAP output naming/layout | SHAP machine outputs under `base/shap/phase3`; SHAP report heatmaps under `report/shap/phase3`; filenames start with `phase3_worse` | Nowcasting output layout can mirror this under launch output/report roots | High |
| `src/ipcch/launch_nowcasting.py` | `LaunchConfig` lines `76-105` | Source | Configuration pattern | Dataclass contains workflow flags and paths, including forecasted-weather fields; validates `scope_months` | Add SHAP config fields here or pass a separate SHAP config into helper functions | Medium |
| `src/ipcch/launch_nowcasting.py` | Forecast-weather helpers lines `325-669` | Source | Weather forecast feature naming | Forecast proxy features include `Rainf_f_tavg_mean_forecast_proxy`, `Tair_f_tavg_mean_forecast_proxy`, and `_minus_N_forecast_proxy` variants; active only scopes 3/6/12 | Seventh `weather forecast` group can conservatively identify these via `forecasted_weather_proxy_columns(scope)` / suffix and base names | High |
| `src/ipcch/launch_nowcasting.py` | `select_model_features()` lines `985-997` | Source | Model feature selection | Selects numeric feature columns after excluding target/metadata families | SHAP feature mapping must use this final `feature_columns` list, not raw frame columns | High |
| `src/ipcch/launch_nowcasting.py` | `train_cumulative_regressors()` lines `1178-1198` | Source | Training matrix availability | For each target, uses `ready = train_featured.dropna(subset=[target])`, `X = ready.loc[:, feature_columns]`, and fits model; phase3 model uses rows where `phase3_worse` is non-null | SHAP requirement says training data; best matrix is phase3-ready `train_featured.dropna(subset=['phase3_worse']).loc[:, feature_columns]` | High |
| `src/ipcch/launch_nowcasting.py` | `predict_april()` lines `1228-1240` | Source | Inference matrix pattern | Reindexes April features to `feature_columns` for prediction | Do not use this prediction-only matrix for grouped SHAP per requirement | High |
| `src/ipcch/launch_nowcasting.py` | `OutputLayout`, `resolve_output_layout()` lines `1064-1120` | Source | Nowcasting output layout | Results/report roots gain `scope_{m}m` suffix for nonzero scopes; output paths are guarded under `RESULTS_DIR`/`REPORTS_DIR` | Add grouped SHAP output paths here or derive from layout under `out_root/shap/phase3` and `report_root/shap/phase3` | High |
| `src/ipcch/launch_nowcasting.py` | `build_run_summary()` lines `1304-1343`, `write_launch_reports()` lines `1395-1475` | Source | Summary/report extension points | Run summary includes output paths and forecasted weather metadata; report renders config, forecasted weather, distributions, comparisons, maps, warnings | Add grouped SHAP artifact paths and counts to run summary/report when enabled | High |
| `scripts/modeling/run_launch_nowcasting_2026_04.py` | `parse_args()` lines `27-72`, `run()` lines `117-209` | Source | Actual nowcasting CLI | CLI parser lives in wrapper; Mode 1 trains, Mode 2 loads models, Mode 3 reports from supplied predictions; full training requires `--approve-training` | New CLI flag likely must be added to wrapper and propagated to `LaunchConfig` or a new nowcasting SHAP config; Mode 3 cannot satisfy training-data SHAP | High |
| `tests/unit/test_forecasting_shap.py` | All tests lines `27-192` | Test | Existing SHAP test expectations | Tests cover phase3-only naming, exact feature order, six-group validation, unmapped diagnostics, 6x4 year matrix, heatmap write | New nowcasting tests should preserve these and add separate seven-group/scope-matrix tests | High |
| `tests/smoke/test_weight_decay_shap_cli.py` | Help and disabled behavior tests lines `21-92` | Test | Existing CLI smoke pattern | Verifies SHAP options appear in help, no local absolute defaults, disabled SHAP does not require crosswalk | Nowcasting should add analogous help/disabled tests | High |
| `tests/unit/test_launch_nowcasting.py` | Forecast-weather tests lines `209-228`, `231-258` and related | Test | Existing weather forecast feature coverage | Tests verify scope-specific forecast proxy column names/counts, disabled/noop behavior, active scope behavior | Add tests for `weather forecast` grouping of these proxy columns | High |
| External crosswalk CSV | Header/sample rows lines `1-20` | Data artifact | Confirm crosswalk schema | Columns include `variable` and `six_category`; sample category `agriculture` | Existing `detect_crosswalk_columns()` can auto-detect this file | High |

## Existing Similar Behavior

| Behavior / Pattern | Source | How It Works | Relevance | Implication |
|---|---|---|---|---|
| Phase-3-only SHAP computation | `src/ipcch/forecasting_shap.py:138-147` | Validates matrix feature order, uses `shap.TreeExplainer`, normalizes to 2D finite array | Directly reusable for nowcasting phase3 model | Use `models['phase3_worse']` and the phase3 training matrix in `feature_columns` order. |
| Crosswalk loading and column detection | `src/ipcch/forecasting_shap.py:191-216` | Reads CSV and detects feature/category columns among known candidates | Provided crosswalk has `variable` and `six_category` | Reuse unchanged for reading; extend matching after loading. |
| Exact six-category validation | `src/ipcch/forecasting_shap.py:219-249` | Requires exactly six groups and exact feature names unless allowed unmapped | Reference behavior but too strict for nowcasting suffixes | Implement a nowcasting-specific resolver that starts from six groups then adds `weather forecast`. |
| Unmapped diagnostics | `src/ipcch/forecasting_shap.py:321-348` | Writes diagnostics for unmapped features and unmapped SHAP share | Requirement asks not to silently drop unmatched features | Prefer diagnostic output over silently skipping; optionally add `other` only if explicitly chosen. |
| Forecasting SHAP CLI gating | `scripts/modeling/run_deep_feature_weight_decay_forecasting.py:94-103`, `597-608`, `672-687` | SHAP outputs only resolved/written when `--enable-shap` is active | Backward compatibility model | Nowcasting no-flag path should not load crosswalk or import SHAP. |
| Forecasting SHAP output split | `src/ipcch/forecasting_weight_decay.py:437-464` | Machine-readable SHAP CSV/JSON under results; heatmaps under reports | Matches constitution artifact separation | Nowcasting grouped SHAP should mirror layout under launch `out_root`/`report_root`. |
| Nowcasting forecast-weather generated features | `src/ipcch/launch_nowcasting.py:367-375` | Returns runtime proxy column names for each scope | Required seventh group | Use these columns as authoritative weather-forecast group seeds. |
| Nowcasting training matrix construction | `src/ipcch/launch_nowcasting.py:1178-1198` | Each target model trains on `ready.loc[:, feature_columns]` after dropping target-missing rows | Requirement says training data and same ordering | SHAP should use the phase3 model's exact `ready` feature matrix, not all training rows if some target values are missing. |

## Related Tests

| Test Path | Behavior Covered | Test Pattern | Missing Coverage | Implication |
|---|---|---|---|---|
| `tests/unit/test_forecasting_shap.py` | SHAP helper validation, crosswalk validation, aggregation, matrix, heatmap | Pure unit tests with small synthetic arrays/dataframes | No robust normalized feature matching, no seven-group matrix, no scope-by-group heatmap | Add new helper tests rather than changing existing six-category expectations. |
| `tests/smoke/test_weight_decay_shap_cli.py` | Forecasting SHAP CLI help and disabled/enabled crosswalk resolution behavior | Subprocess `--help` and missing-path checks | No nowcasting CLI SHAP tests | Add analogous smoke tests for `scripts/modeling/run_launch_nowcasting_2026_04.py`. |
| `tests/unit/test_launch_nowcasting.py` | Nowcasting config, source validation, feature selection, forecast-weather scope columns | Synthetic dataframe tests; no heavy training required | No grouped SHAP tests | Add unit tests for mapping weather proxy columns, unmatched diagnostics, and output path/report metadata helpers. |

## Existing APIs / Contracts / Schemas

| Item | Source | Current Behavior | Compatibility Concern | Implication |
|---|---|---|---|---|
| Nowcasting CLI parser | `scripts/modeling/run_launch_nowcasting_2026_04.py:27-72` | Exposes launch/source/model/weather/map/safety flags; no SHAP flag | User request says add CLI flag in `launch_nowcasting.py`, but parser is in wrapper script | Implement CLI exposure in wrapper and supporting config/helpers in `src/ipcch/launch_nowcasting.py`, or explicitly move parser only if desired. |
| Launch execution modes | `scripts/modeling/run_launch_nowcasting_2026_04.py:75-80`, `117-209` | Mode 1 trains/predicts, Mode 2 loads supplied models, Mode 3 uses supplied predictions | Training-data SHAP impossible in Mode 3 because no model/training matrix is available | If SHAP enabled with `--skip-prediction`, hard-fail with actionable message; Mode 2 may work if training matrix is built and model features match. |
| Forecasting SHAP crosswalk CLI | `scripts/modeling/run_deep_feature_weight_decay_forecasting.py:94-103` | Supports explicit path/key and explicit column names | Nowcasting can reuse naming for consistency | Add `--enable-grouped-shap` or mirror `--enable-shap`; use explicit crosswalk path/key flags. |
| Crosswalk schema | External CSV line `1` | `variable,six_category,...` | Nowcasting feature names may not exactly match `variable` values | Need normalized/base-variable matching and diagnostics. |
| Forecasting SHAP matrix schema | `src/ipcch/forecasting_shap.py:351-367` | `feature_group` plus year columns `2022`-`2025` | Nowcasting requirement expects `feature_group,0m,3m,6m,12m` | New matrix helper should not break existing `scope_matrix()`. |
| Output path guardrails | `src/ipcch/launch_nowcasting.py:1090-1120` | Ensures output/report roots are under `RESULTS_DIR`/`REPORTS_DIR` | SHAP output paths should stay under these roots | Add SHAP paths via `OutputLayout` or deterministic helper using layout roots. |

## Data Models / Persistence

| Model / Storage Area | Source | Current Pattern | Migration / Compatibility Concern | Implication |
|---|---|---|---|---|
| Forecasting SHAP machine outputs | `src/ipcch/forecasting_weight_decay.py:437-464` | `results/.../shap/phase3/phase3_worse_feature_summary.csv`, `phase3_worse_six_category_long.csv`, diagnostics, metadata, raw values | Nowcasting needs grouped matrix and mapping file; exact filenames not yet defined | Use clear filenames under `layout.out_root / 'shap' / 'phase3'`. |
| Forecasting SHAP report outputs | `src/ipcch/forecasting_weight_decay.py:437-464` | `reports/.../shap/phase3/phase3_worse_{scope}_matrix.csv` and heatmap PNGs | Nowcasting needs one scope-by-group heatmap, potentially built from multiple runs | Store human-readable heatmap under `layout.report_root / 'shap' / 'phase3'`; decide single-scope vs combined-root output. |
| Nowcasting run summary | `src/ipcch/launch_nowcasting.py:1304-1343` | JSON records core run metadata and output paths | SHAP metadata absent | Add `grouped_shap` metadata only when enabled or with `enabled: false` summary. |
| Feature-to-group mapping | Requirement | No current nowcasting mapping artifact | Needed for transparent robust matching | Write CSV with at least model feature, assigned group, match method, crosswalk feature matched, and notes/unmatched status. |

## Auth / Validation / Error Handling / Observability Patterns

| Concern | Source | Existing Pattern | Required Follow-up |
|---|---|---|---|
| Missing optional dependency | `src/ipcch/forecasting_shap.py:103-109` | Raises `ShapDependencyError` only when SHAP engine imported | Import SHAP only when grouped SHAP flag is enabled. |
| Feature order mismatch | `src/ipcch/forecasting_shap.py:112-116` | Raises validation error if SHAP matrix columns differ from fitted order | Build SHAP matrix with `ready.loc[:, list(feature_columns)]` and preserve order. |
| Unmapped features | `src/ipcch/forecasting_shap.py:245-249`, `321-348` | Can warn/diagnose missing mappings; existing aggregation excludes them | Nowcasting must explicitly write unmatched diagnostics or assign fallback group; do not silently skip. |
| Output conflicts | `src/ipcch/launch_nowcasting.py:1123-1127`, `src/ipcch/forecasting_weight_decay.py:481-509` | Production output conflict checks unless overwrite/dry-run | Add grouped SHAP outputs to conflict guard when flag is enabled. |
| Console logging | `scripts/modeling/run_launch_nowcasting_2026_04.py:175-177`, `262-263` | Prints weather feature status and final output location | Add grouped SHAP counts and artifact paths when enabled. |

## Architecture Constraints

| Constraint | Source | Implication | Risk |
|---|---|---|---|
| Temporal/training integrity | `.specify/memory/constitution.md:54-80` and user requirement | SHAP must explain model using training matrix only; no validation/test/prediction rows | Using April prediction rows would violate explicit requirement. |
| Shared utilities under `ipcch` | `.specify/memory/constitution.md:87-105` | Put reusable matching/matrix helpers in `src/ipcch/`, likely `forecasting_shap.py` or a new nowcasting SHAP helper | Duplicating logic in CLI wrapper would violate convention. |
| Path-agnostic code | `.specify/memory/constitution.md:106-123` | Crosswalk defaults should use `paths.external_path()` key or CLI path, not hardcoded Windows path | User-provided absolute paths should not become defaults in code. |
| Results/reports separation | `.specify/memory/constitution.md:125-148` | CSV/JSON matrix/mapping/diagnostics under `results`; heatmap under `reports` | Writing all outputs to one side would violate artifact separation. |
| Safe execution | `.specify/memory/constitution.md:150-179` | Evidence/validation should avoid heavy training unless explicitly approved | Full grouped SHAP launch may be expensive; unit/smoke tests preferred first. |
| Current working tree provisional | `git status --short` | Nowcasting files are modified/uncommitted | Treat current weather-feature code as provisional baseline until accepted. |

## Risks

| Risk | Evidence | Severity | Mitigation / Follow-up |
|---|---|---|---|
| Exact crosswalk validation fails for nowcasting-generated/lagged features | `validate_crosswalk()` exact missing check at `src/ipcch/forecasting_shap.py:241-246`; user requirement says nowcasting names may differ | High | Add transparent normalized/base-variable matching before validation/aggregation; write mapping artifact and unmatched diagnostics. |
| Weather forecast features could be misclassified into existing `weather` instead of new `weather forecast` | Crosswalk includes weather category; proxy features are runtime-generated in `launch_nowcasting.py:367-375` | High | Check forecast proxy columns first and assign group exactly `weather forecast` before crosswalk matching. |
| Heatmap cannot naturally have four scope columns from a single nowcasting run | `resolve_output_layout()` runs one `scope_months` at a time; nonzero scopes write under `scope_{m}m` | Medium | Either build per-run grouped SHAP long outputs and add a separate combine command/helper, or implement an orchestrator that reads outputs for `0m/3m/6m/12m`. Document choice in spec. |
| Mode 3 cannot satisfy training-data SHAP | `scripts/modeling/run_launch_nowcasting_2026_04.py:128-138` reads supplied predictions only | High | If grouped SHAP flag is enabled with `--skip-prediction`, raise `LaunchError` explaining unsupported mode. |
| SHAP runtime/memory cost on training matrix | `train_cumulative_regressors()` training rows may be large; SHAP explains rows x features | Medium | Consider optional row sampling only if user accepts; otherwise document full training-matrix cost and test on sample rows. Requirement currently says training data, not necessarily all rows. |
| Existing helper name `aggregate_six_category_importance` is semantically narrow | `src/ipcch/forecasting_shap.py:287-318` | Low | Add generalized aggregation helper and keep old function as wrapper for backward compatibility. |

## Open Questions

| Question | Why It Matters | Who / What Can Resolve It | Blocking? |
|---|---|---|---|
| Should nowcasting grouped SHAP be computed for all four scopes in one CLI invocation, or should each scope run write its own grouped output and a separate combine step render the 4-column heatmap? | Requirement wants heatmap columns `0m`, `3m`, `6m`, `12m`, but current launch CLI runs one scope at a time | User/spec decision | Yes for final UX/output design |
| What should the default crosswalk source be? | Forecasting SHAP uses external key `six_category_feature_crosswalk`; user gave an absolute reference path | Existing `configs/paths.local.json` or user | Non-blocking if both `--variable-crosswalk-path` and key default are supported |
| Should unmatched non-weather features be assigned to `other` or only written to diagnostics while excluded from denominator? | Requirement allows either; existing forecasting behavior diagnoses and excludes | User/spec decision | Non-blocking; evidence favors diagnostics for consistency |
| Should Mode 2 supplied-model runs support grouped SHAP using the built training feature frame and supplied phase3 model? | Mode 2 has model artifacts and builds training data, but model provenance may differ | User/spec decision | Non-blocking if initially limited to Mode 1 |
| Should grouped SHAP explain all four cumulative targets or phase3 only? | Existing reference is phase3-only and requirement focuses Phase 3+ context, but says grouped SHAP generally | User/spec decision | Likely non-blocking; evidence supports phase3-only consistency |

## Assumptions

| Assumption | Basis | Confidence | How To Validate |
|---|---|---|---|
| The implementation should remain phase3-only, explaining `phase3_worse`. | Reference module constant `TARGET = "phase3_worse"` and helper names are phase3-specific | Medium | Confirm in spec or user clarification. |
| `weather forecast` group should include only columns returned by `forecasted_weather_proxy_columns(scope)` plus obvious rain/temp forecast-proxy variants. | User requirement and `launch_nowcasting.py:367-375` | High | Add tests for 3m/6m/12m proxy names and no accidental assignment to six original groups. |
| Existing forecasting SHAP helpers should remain backward-compatible for feature 006. | Tests assert six groups and year matrix | High | Run existing `tests/unit/test_forecasting_shap.py` after implementation. |
| The final Speckit feature directory will differ from `specs/_evidence/`. | No grouped nowcasting feature dir exists yet | High | Move/copy this artifact after `/speckit.specify` creates the directory. |

## Implications for Spec

- Specify whether grouped SHAP is phase3-only or multi-target; repository evidence strongly supports phase3-only reuse.
- Specify whether the scope-by-group heatmap is produced by a single multi-scope command or by aggregating artifacts from four separate scope runs.
- Require training-matrix SHAP explicitly: phase3-ready rows from `train_featured.dropna(subset=['phase3_worse'])`, columns exactly `feature_columns`.
- Require the feature-to-group mapping artifact to include match method and unmatched status for transparency.
- Require `weather forecast` assignment to take precedence over six-category crosswalk matching.
- Require Mode 3 behavior to be explicit because supplied predictions cannot support training-data SHAP.

## Implications for Plan

- Add reusable matching helpers under `src/ipcch/` rather than only in the wrapper CLI.
- Prefer extending `forecasting_shap.py` with generalized group aggregation/matrix/heatmap helpers while preserving existing six-category APIs and tests.
- Add SHAP output paths to nowcasting layout or a dedicated helper preserving `results/` vs `reports/` separation.
- Add CLI flags in `scripts/modeling/run_launch_nowcasting_2026_04.py` because that is the observed parser.
- Add a guarded post-training hook after `feature_columns` and `models` exist and before run summary is written.
- Add console output for matched six-category count, `weather forecast` count, unmatched count, and artifact paths.

## Implications for Tasks

- Add unit tests for normalized crosswalk matching using lag/current/suffix variants.
- Add unit tests that forecast proxy columns map to `weather forecast` before crosswalk matching.
- Add unit tests for a seven-row, four-scope matrix helper.
- Add smoke test that nowcasting CLI help shows the grouped SHAP flag and crosswalk options.
- Add disabled-path smoke/unit test showing the nowcasting workflow does not require crosswalk/SHAP when flag is absent.
- Add Mode 3 unsupported test if grouped SHAP is enabled with `--skip-prediction`.
- Run existing `tests/unit/test_forecasting_shap.py` to prove backward compatibility.

## Suggested References

| Path | Why Include | Reference Type | Needed For |
|---|---|---|---|
| `specs/_evidence/grouped-shap-nowcasting.evidence.md` | Main feature evidence artifact | Evidence | plan/tasks/implement |
| `.specify/memory/constitution.md` | Governs temporal integrity, shared utilities, path handling, artifact split, safe execution | Governance | plan/tasks/implement |
| `src/ipcch/forecasting_shap.py` | Reference grouped SHAP helper implementation | Source reference | plan/tasks/implement |
| `scripts/modeling/run_deep_feature_weight_decay_forecasting.py` | Reference CLI workflow integration for SHAP | Source reference | plan/tasks/implement |
| `src/ipcch/launch_nowcasting.py` | Target nowcasting workflow and training matrix construction | Target source | plan/tasks/implement |
| `scripts/modeling/run_launch_nowcasting_2026_04.py` | Actual nowcasting CLI parser and execution modes | Target CLI | plan/tasks/implement |
| `tests/unit/test_forecasting_shap.py` | Existing helper compatibility contract | Test reference | tasks/validation |
| `tests/smoke/test_weight_decay_shap_cli.py` | Existing CLI smoke-test pattern for SHAP flags | Test reference | tasks/validation |
| `tests/unit/test_launch_nowcasting.py` | Nowcasting feature/weather test patterns | Test reference | tasks/validation |

## Copy into spec.md

```markdown
## References

- specs/_evidence/grouped-shap-nowcasting.evidence.md
- .specify/memory/constitution.md
- src/ipcch/forecasting_shap.py
- scripts/modeling/run_deep_feature_weight_decay_forecasting.py
- src/ipcch/launch_nowcasting.py
- scripts/modeling/run_launch_nowcasting_2026_04.py
- tests/unit/test_forecasting_shap.py
- tests/smoke/test_weight_decay_shap_cli.py
- tests/unit/test_launch_nowcasting.py
```

Expected final path after `/speckit.specify`, when applicable: `specs/<feature>/evidence.md`.
