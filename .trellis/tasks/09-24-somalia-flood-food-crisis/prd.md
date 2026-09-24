# Somalia flooding–food crisis: oracle-information model comparison

Version: 1.1 — 2026-09-24
Status: G1–G6 recorded; final spec accepted 2026-09-24 via the user session goal (see implement.md).
Execution: authorized by the 2026-09-24 session goal; follows implement.md.

## Goal and interpretation

Estimate the empirical performance ceiling of the existing Somalia-local cumulative ensemble XGBoost pipeline under the agreed best-information scenario. Future realized weather is explicitly permitted; all other information follows the specified origin-time rules. These experiments provide evidence for a subsequent Somalia government flooding–food crisis report.

“Ceiling” means performance attained by this model family, information set and bounded search, not a mathematical upper bound. Results do not establish flood causality or historical operational forecast performance. Ideal immediate publication and oracle weather are explicit experimental assumptions.

## R1. Population, model and experiment arms

Fit and evaluate Somalia only, using the project's country lookup. Preserve the four cumulative XGBoost regressors for phase2_worse through phase5_worse and phase-3-specific configuration behavior. Do not substitute the sibling project's binary classifiers, RF or correction models.

Grill G4 authorizes proportional normalization of source phase distributions: for finite nonnegative P1–P5 with positive sum S, use p_k=P_k/S. Derive cumulative supervised targets and percentage-history features from these normalized shares. A total different from 100% alone is not an exclusion; this supersedes the earlier rejection proposal and the reference history's [.90,1.10] sum gate. Preserve raw components, S, normalized components and correction status without overwriting the external source. Normalization does not authorize filling missing components for supervised targets, repairing negative/nonfinite values or dividing by zero. Reported `overall_phase` remains unchanged.

| Arm | Predictors |
|---|---|
| A | Existing predictors, subject to origin-time validity checks |
| B | A plus the 14 V2 seasonal ensemble means |
| C | B plus original-variable realized future weather |
| D | C plus the referenced rich phase-percentage history recipe |

Use identical fitting eligibility, temporal validation rules, candidate inventory and comparison keys across arms within each horizon/fold. A may already contain categorical phase history; it must not be described as a no-history model. Existing predictors are retained only when their temporal lineage satisfies this specification. Repairing their alignment is not permission for a new feature search.

At H=0, B and C are identical: reuse their fit/predictions. Report every arm, including negative or mixed results. Pairwise differences B−A, C−B and D−C reflect sequential additions with parameter adaptation; they are not causal effects or a complete factorial interaction analysis.

Grill G5 fixes the comparison unit: compare model specifications and references within the same test year and horizon. Horizons are separate experimental conditions, not a performance ranking. Do not construct a common-sample intersection across horizons, pool horizons for a headline superiority score, or interpret cross-horizon metric differences as performance gains. Matching samples remains mandatory for the specifications/baselines being compared within each year/horizon.

Also report an unfitted persistence baseline, as approved during grill G1: predict the latest valid reported phase for the same area with source month U<=O and U<T. Keep A–D as the four tuned arms. Persistence does not train or tune; missing history yields unavailable rather than an invented phase. Report its source keys, history ages and coverage. Compare each model with persistence only on identical keys supported by both, without shrinking or replacing A–D's primary common cohort.

Also report the always-predict-Phase-3+ diagnostic reference, approved in grill G2. It requires no fitting or tuning and does not change the primary F2 selection criterion. Compute its binary metrics on the same primary and persistence-comparison cohorts; it supplies no ordinal phase or population-share prediction. This exposes high F2 obtainable from crisis prevalence alone.

## R2. Time and supervised fitting eligibility

- Horizons H are exactly 0, 3, 6 and 12 months.
- Target month T determines train/test year membership; O=T−H is the end of the origin month.
- Fold 2025: candidate supervised training target years 2022–2024; evaluation targets in 2025.
- Fold 2026: candidate supervised training target years 2023–2025; evaluation targets in the verified portion of 2026.
- For each test O, further restrict supervised training targets to those available by O. Thus a longer-horizon prediction may use less than three years of effective training data.
- A label is assumed available at the end of its target month. A seasonal feature is assumed available at season completion. Publication delay reconstruction is outside this ideal-information experiment; the assumptions must be disclosed.
- Fitting, fitted preprocessing, parameter selection and validation respect the same allowed label information. No outer-test-year labels enter those fitting/selection operations. Inner temporal validation applies its own origin cutoff.
- The oracle allowance applies only to the specified future weather predictors. It never allows future IPC labels, current target self-use or unrelated future covariates.

## R3. Additional V2 seasonal features

Input: `C:\Users\swl00\IFPRI Dropbox\Weilun Shi\IPCCH_shared_folder\climate_2022_2026_FINAL_MODEL_READY_V2.csv` (external source, not copied or modified).

Add exactly these 14 inputs:

`prcp_anom_gs_ensmean`, `prcp_z_gs_ensmean`, `rainy_days_gs_ensmean`, `cdd_gs_ensmean`, `tmean_anom_gs_ensmean`, `tmax_anom_gs_ensmean`, `hot_days_p95_gs_ensmean`, `gdd_gs_ensmean`, `edd_gs_ensmean`, `sm_z_gs_ensmean`, `ndvi_anom_gs_ensmean`, `evi_anom_gs_ensmean`, `spi03_gs_ensmean`, `spei03_gs_ensmean`.

For each area/O, select the season with the latest end among seasons completed by O. With exclusive end date E, eligibility is E <= first day of the month after O. Select by dates across years/seasons, never by the prediction target's season. Missing prior seasons leave all added V2 values missing; retain the sample. Missing individual metrics remain missing.

Individual sources, QA fields, source counts/spreads, crop fraction, identifiers and season metadata are lookup/diagnostic fields rather than additional model predictors. Preserve selected-season identity and dates. A nominally ended season does not by itself prove the export covers its complete observation window; incomplete exports require an explicit data-gap status.

## R4. Perfect-weather inputs

Reuse the existing monthly weather alignment/merge logic. Source the original weather variables' realized observations, not the V2 seasonal aggregates or forecast-product values. Additional offsets k are 1 through min(H,6): none for H=0; 1–3 for H=3; 1–6 for H=6/12. The design fixes the existing module's rain and temperature variable pair.

Do not duplicate O as an additional future month. Apply the same construction to fitting, validation and test rows at their respective origins. Unverified, substituted or missing future-weather observations do not qualify as perfect-weather evidence.

## R5. Rich history

Reuse the recipe in `Food_Crisis_Cluster/IPCCHPopulationHistoryExperiment`: eight phase-distribution series; last six actual valid observations; elapsed times; differences/rates; slopes; 6/12/24/36-month and all-prior-history summaries; distribution and crisis/run descriptors. Preserve reference formulas and applicable history QA with explicit schema/alias mapping, subject to the G4 normalization override in R1; do not import its original93 predictor block or assume a final width of 561.

Let XGBoost learn interactions. No explicit history-times-weather product columns are required.

For every history source month U, require U<=O and U<T. Apply to both fitting and prediction rows, including existing categorical history. H=0 must exclude the current target month despite assumed month-end publication.

Pre-2022 Somalia records may construct features without becoming supervised training rows. Earlier test-year observations may update later prediction histories once available by that row's O; they remain excluded from that fold's fitting/tuning. No interpolation, future-season/label filling, cross-area borrowing or deletion merely because history is absent. Retain missing-value semantics and source observation keys.

## R6. Tuning and scoring

Use six predeclared XGBoost configuration bundles with equal search budgets across A–D. Each arm selects independently using temporal validation inside the allowed training pool. Retain phase conversion threshold 0.2 and a 24-month exponential weight half-life, referenced to each model's fitting origin. Exact candidate values and deterministic selection rules are in `design.md` and `candidate-configs.json`; these technical details await consolidated final review.

Primary selection metric: Phase 3+ F2. Also report Phase 3+ precision, recall, F1, overall phase accuracy and Phase 3+ population-share R-squared. Do not choose the primary metric after inspecting outer-test scores.

As approved in grill G3, use unrounded prediction values for phase conversion and all metric calculations. Compare directly with >=0.2, preserving the descending phase5-to-phase2 convention. Apply this identically in inner validation and outer evaluation for every arm. Rounding is presentation-only; the old runner's round-before-threshold behavior is explicitly superseded.

Insufficient temporal validation support or an undefined required selection score yields an explicit unsupported/incomplete cell. Do not borrow later labels or substitute an undeclared fallback. No performance target guarantees D improves on C or any enhanced arm improves on A.

Grill G6 approves paired area-cluster bootstrap 95% intervals for within-year/within-horizon delta F2. Resample areas with all their eligible months, using identical area multiplicities for both sides of each contrast; reuse saved predictions without refitting. Sequential specification contrasts use the primary common cohort; persistence contrasts use its explicitly supported matched subset. Always-crisis contrasts use the declared matching cohort. Record reproducible draws, undefined-score counts and interval status. These intervals describe conditional comparison uncertainty, not future-year guarantees or a full correction for spatial dependence; no cross-horizon pooling or ranking.

## R7. Coverage and reproducibility

Determine evaluation eligibility from source validity and predictor availability before examining predictions, identically across arms. Feature NaNs in seasonal/history blocks are permitted; absence of verified oracle evidence is separately recorded. Never remove a row because its predicted cumulative shares sum to zero or because it is phase 1.

Report 2026 actual target months and counts, not full-year performance unless supported. Preserve all planned cells, including unavailable ones; report missing/unverified source gaps explicitly. Publish keyed predictions, comparison keys, fitting/validation provenance, selected configs, ordered feature schema, input/code/runtime identities and a reproducible metrics report. No training or source repair is part of this planning turn.

## Out of scope

A full government-facing report, flood causal-effect estimation, new flood exposure acquisition, new model families, explicit history/weather products, cross-horizon common-cohort comparisons or performance rankings, actual weather forecast deployment, full-year 2026 claims without evidence, and expanding the experiment based on favorable test results.

## Acceptance criteria

| ID | Observable requirement | Evidence |
|---|---|---|
| AC1 | Four arms, two target-year folds and four horizons match R1/R2 | Run/fold inventory; H=0 B/C identity |
| AC1b | Valid finite nonnegative phase vectors are proportionally normalized to unit sum before target/history construction; source records and reported phase remain intact | Raw/sum/normalized ledger, transformation checks and correction counts |
| AC2 | Supervised fit/selection labels stay in candidate years and obey origin cutoffs | Per-fit and inner-validation key/date ledgers |
| AC3 | Only the 14 approved V2 fields join from the latest ended season | Feature schema, season keys and independent join checks |
| AC4 | Oracle offsets and realized-weather identity satisfy R4 | Per-row month/source ledger; missing/gap report |
| AC5 | History matches the reference recipe and U<=O,U<T, with authorized source years | Alias map, selected observation keys, reference-parity checks |
| AC6 | Six equal-budget candidates, temporal F2 selection, fixed threshold/decay | Candidate inventory, validation predictions/scores and selections |
| AC7 | Common comparison keys and phase-1 preservation; no prediction-dependent exclusions | Cohort ledger, independent metrics replay |
| AC7b | Persistence uses the latest eligible reported phase; model comparisons share exact supported keys and disclose no-history coverage | Persistence source-key/age ledger and paired reference metrics |
| AC7c | Always-crisis reference and model binary metrics use identical declared cohorts | Confusion counts, prevalence and replayed reference metrics |
| AC7d | Within-year/horizon delta F2 has paired area-cluster bootstrap 95% intervals or an explicit unavailable reason | Cohort keys/hash, seed/RNG/draw inventory, paired deltas, undefined counts and independent interval replay |
| AC8 | Coverage, conditional-ceiling interpretation and assumptions are accurately reported | Metrics/support tables, data-gap report, narrative |
| AC9 | Inputs, features, models and predictions are reproducible and audit-accessible | Hash-bound artifact manifest and validation evidence |
| AC10 | Spec/grill and later implementation approval precede execution | Planning approvals and bound audit start/close records |

## Artifact and lifecycle status

`prd.md` is the requirements specification; `design.md` is the technical specification; `research.md` preserves observed evidence and reuse pointers. `candidate-configs.json` freezes proposed technical candidates for review. All acceptance criteria are unexecuted.

The requested order remains brainstorm → written spec → grill. Do not create an implementation plan or begin implementation merely because this spec is written. After grill converges, prepare/review `implement.md`, commit approved planning artifacts, and start via the bound Claude executor's audit wrapper. Repository registration/controller setup is recorded in `research.md`; it is not an audit verdict or execution authorization.
