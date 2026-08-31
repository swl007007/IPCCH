# Feature Specification: Nigeria Weather-Land XGBoost Rerun

**Feature Branch**: `[008-nigeria-weather-land-xgb-rerun]`  
**Created**: 2026-08-25  
**Status**: Executed and validated  
**Input**: Rerun the previous Nigeria ensemble XGBoost architecture in new experiment folders using the prepared weather-land feature release.

## Scope Boundary

This specification covers only freezing and executing a comparable three-scope Nigeria experiment. It does not redesign the model, tune thresholds or hyperparameters, alter upstream variable assembly, or overwrite the 2026-08-22 Nigeria baseline.

In this specification, “ensemble XGBoost” means the authoritative 2026-08-22 weighted-decay CLI architecture: four independently fitted cumulative-target XGBoost regressors (`phase2_worse` through `phase5_worse`) combined by the existing severity-first threshold cascade. It does not mean averaging or voting, and it does not reproduce accidental parameter mutation from the older notebook.

## Frozen Experiment Contract

- Scopes: `fs0`/0m, `fs1`/3m, and `fs2`/6m as three separate runs.
- Inputs: the matching `nga_scope_{0m,3m,6m}_model_ready_v1.csv` files from release `nga-weather-land-20260825-v1`.
- Population: Nigeria only (`NGA`), expected 545 areas and 6,538 rows per scope before target-specific filtering.
- Evaluation: annual holdouts 2022, 2023, 2024, and 2025; training uses all strictly earlier records.
- Architecture: four cumulative-target regressors and the existing severity-first phase conversion.
- Weighting: exponential time decay with 24-month half-life.
- Identifier augmentation: unchanged latitude/longitude plus existing year/month dummy construction.
- Hyperparameters: existing standard config for P2+/P4+/P5+ and existing phase-3 config for P3+.
- Threshold and seed: explicitly fixed at `0.20` and `42`.
- Missing values: preserve land-system gating and failed-source nulls; use XGBoost native missing-value handling; do not impute or add new missingness indicators in this rerun.
- Outputs: explicit, new, release-specific result and report directories; never pass `--overwrite`.
- Comparison baseline: matching 2026-08-22 Nigeria CLI artifacts, described as path-recorded rather than byte-exact reproducible because their metadata did not hash every dependency.

## User Scenario and Acceptance

As a researcher, I want to rerun the frozen Nigeria weighted-decay XGBoost architecture with only the prepared weather-land release changed, so that paired performance differences can be interpreted as an augmented-feature experiment rather than a model redesign.

Acceptance requires:

1. Each dataset is paired with its matching scope: 0m→`fs0`, 3m→`fs1`, 6m→`fs2`.
2. New and historical prediction keys match exactly within each scope and holdout year before metric differences are interpreted.
3. The new selected feature set differs from the historical run by exactly the intended 16 released predictors; the release's all-null legacy predictors remain admitted unchanged and are recorded separately from the 16 additions.
4. Threshold, seed, half-life, identifiers, split years, cumulative targets, phase cascade, and hyperparameter files remain unchanged.
5. No historical result or report artifact is modified.
6. A failed scope cannot make the three-scope experiment appear complete; completion is declared only after all three scopes pass validation and training.
7. Reports include the existing metrics and a derived overall-phase MAE by holdout year for paired comparison; MAE is labeled as a new comparison diagnostic, not a historically published metric.

## Functional Requirements

- **FR-001**: The rerun MUST use explicit `--dataset`, matching `--fs`, `--country-iso3 NGA`, `--add-identifier-features`, `--half-life-months 24`, `--phase-threshold 0.20`, and `--seed 42` arguments.
- **FR-002**: The rerun MUST use explicit unique `--out-dir` and `--report-dir` paths containing the weather-land release identity.
- **FR-003**: The rerun MUST NOT use `--overwrite` and MUST fail before training if any planned output path already exists.
- **FR-004**: The rerun MUST record the release manifest hash and the SHA-256 hashes of each model-ready CSV, runner, feature selector utility, country lookup, identifier source, and both hyperparameter files.
- **FR-005**: Provenance MUST record Git HEAD, dirty status, and hashes of dirty modeling files so the run remains attributable without altering the user's existing changes.
- **FR-006**: Preflight MUST verify 6,538 rows, 545 areas, expected date coverage, four holdout years, Nigeria-only IDs, and exact old/new evaluation-key equality for each scope.
- **FR-007**: Preflight MUST verify that the 16 added predictors are selected and MUST report their missingness, land-system gating, SPI invalid counts, and SPI coverage-failure counts by scope.
- **FR-008**: Failed-source SPI values and non-applicable land-system variables MUST remain null; zero-fill and mean/median imputation are prohibited.
- **FR-009**: No threshold search, hyperparameter search, feature selection based on holdout results, or post-run rule changes are permitted.
- **FR-010**: Full training MUST begin only after all three scope preflights pass, and each scope MUST write only to its own new result/report directory.
- **FR-011**: Post-run validation MUST check output completeness, prediction schema, expected years, Nigeria-only IDs, deterministic feature order, and absence of changes to historical artifacts.
- **FR-012**: Comparison MUST pair predictions on scope, test year, area, year, and month keys and report existing metrics plus derived overall-phase MAE.
- **FR-013**: If one scope fails, successful scope artifacts remain labeled partial and the combined experiment remains incomplete until the failed scope is rerun successfully.

## Reverse Stress-Test Register

| Attack | Resolution | Status |
|---|---|---|
| “Ensemble” could imply averaging/voting | Define it as the four cumulative regressors plus severity-first cascade | Resolved |
| Old notebook differs from current runner | Use the 2026-08-22 Nigeria CLI as the baseline architecture | Resolved |
| Default names collide with old experiments | Require explicit release-specific output and report directories | Resolved |
| Dirty runner obscures provenance | Hash HEAD, dirty state, runner, selector, configs, and lookups | Resolved |
| Dataset and `--fs` can be mismatched | Freeze a one-to-one file/scope mapping and verify it preflight | Resolved |
| Land gating creates high structural missingness | Preserve nulls and use native XGBoost missing branches; no imputation | Resolved |
| SPI source failures look like ordinary nulls | Record invalid and coverage-failure diagnostics; prohibit filling | Resolved |
| Old baseline lacks dependency hashes | Make only a path-recorded comparison claim, not byte-exact reproducibility | Resolved |
| Threshold tuning could contaminate feature attribution | Freeze 0.20 before execution and prohibit tuning | Resolved |
| Partial scope success could be mistaken for completion | Require all three scopes for complete status | Resolved |
| 0m/6m contain one all-null legacy predictor | Retain unchanged; record in schema/provenance; use native XGBoost missing handling | Resolved |

## Confirmed Decision

The 0m release contains an all-null `overall_phase_prev_observed_asof_s0` column and the 6m release contains an all-null `overall_phase_prev_observed_asof_s6` column. The rerun retains them so that the released inputs and current selector are consumed unchanged. They receive no imputation, remain visible in the fitted feature schema and provenance, and are not counted among the 16 newly engineered predictors.

## Success Criteria

- All preflight invariants pass for all three scopes before model fitting.
- Each completed scope produces four annual prediction/metric sets and country metrics without overwriting prior artifacts.
- Every run has machine-readable provenance sufficient to identify exact code and input bytes.
- New-versus-old comparisons use identical evaluation keys and clearly separate existing published metrics from newly derived MAE.
- The stress-test register contains no open Blocker or Major decision before execution authorization.

## Planned Directories

```text
results/experiments/deep_feature_weight_decay_forecasting/
  0m_nigeria_weather_land_v1_threshold_0_20_seed_42/
  3m_nigeria_weather_land_v1_threshold_0_20_seed_42/
  6m_nigeria_weather_land_v1_threshold_0_20_seed_42/

reports/deep_feature_weight_decay_forecasting/
  0m_nigeria_weather_land_v1_threshold_0_20_seed_42/
  3m_nigeria_weather_land_v1_threshold_0_20_seed_42/
  6m_nigeria_weather_land_v1_threshold_0_20_seed_42/
```

## Execution Evidence

See [evidence.md](evidence.md). All three scope preflights, full runs, paired-key checks, artifact checks, and derived MAE comparisons completed on 2026-08-25.
