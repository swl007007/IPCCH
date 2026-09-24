# Technical specification — Somalia oracle-information experiment

Version: 1.1 — 2026-09-24
Status: G1–G6 resolved; accepted 2026-09-24 with preflight resolutions in implement.md; implementation authorized.
Authority: `prd.md` records user-approved requirements. Candidate values, inner-validation support rules and bootstrap reproducibility details below were accepted 2026-09-24 (see `implement.md`). Validation status: see task evidence/.

## 1. Minimal architecture and reuse

Use the existing IPCCH cumulative XGBoost pipeline, configurable external inputs and results/reports conventions. Adapt or extract small reusable helpers rather than create a new framework. The implementation plan, after grill, will name the minimal runner and affected helpers.

| Responsibility | Reuse source | Required adaptation |
|---|---|---|
| Somalia filtering and model runner | `scripts/modeling/run_deep_feature_weight_decay_forecasting.py:172-203,264-345,697-704` | Two candidate-year windows and fitting by origin |
| Cumulative targets and matrices | `src/ipcch/forecasting_weight_decay.py:132-150,331-352` | Explicit input/schema validity; preserve feature NaNs |
| Weighting and metrics | Same module `287-302,368-415` | Origin-based weights; F1; fixed common scoring support |
| Weather alignment | `src/ipcch/launch_nowcasting.py:336-359,421-458,580-673` | Oracle-only source, offsets 1..min(H,6), no forecast fallback |
| Rich history | Sibling `IPCCHPopulationHistoryExperiment/prepare_data.py:291-340,384-399,540-745` | Current schema aliases and H=0 strict target exclusion |

Do not import a runner with execution side effects just to reuse helpers. Do not change the sibling repository or migrate its full experiment. Pin the exact reference code/schema revision used. `fs3` must be validated as H=12 by its construction, not inferred from its label `forecasting`.

## 2. Keys, source contracts and feature availability

Canonical row key: `(area_id, target_month, horizon_months)`; arm is an extra key on predictions. Store `origin_month`, month-end cutoff, test year and source row identity separately. Normalize IDs losslessly and verify country lookup uniqueness. Duplicate source area/month or V2 area/year/season keys fail preparation.

Inputs are explicit paths resolved through project configuration or CLI; no recursive search for whichever artifact looks newest. Hash inputs and record their semantic role. Store raw label shares, cumulative targets and reported `overall_phase` separately.

Original covariates require per-family source-window evidence. A horizon-specific input filename or an asof suffix is not proof. Known risk: `overall_phase_lag1` may encode a target-adjacent value after O. Reconstruct a verified as-of equivalent consistently across arms or block affected features/runs for review; do not silently retain it. Preserve source feature units and transformations. No full-panel fitted scaler, imputer or outcome-derived feature selection is permitted.

The ideal publication assumption removes operational release delays, not future source observations, retrospective outcome corrections or test-fitted preprocessing. For anomaly/z/SPI/SPEI features, record reference-period and fitting provenance; require an externally fixed climatology or permissible training-only fitting. Unknown provenance stays a preflight gap, not a no-leakage pass.

### Outcome and common scoring support

Grill G4 explicitly authorizes normalization before cumulative-target and percentage-history construction. After parsing source components on their documented scale, require complete finite nonnegative P1–P5 and finite positive S=sum(P1..P5) for supervised targets. Set p_k=P_k/S, then q2=p2+p3+p4+p5, q3=p3+p4+p5, q4=p4+p5 and q5=p5. Do not reject merely because raw S differs from one, including raw cumulative totals above one. Do not apply an upper sum tolerance or clip the components instead of proportional normalization. Invalid negative/nonfinite inputs, missing supervised components and zero/nonfinite sums remain invalid.

Store raw components, raw S, normalized components and whether/how normalization changed the row. Apply the same row-local operation to training, validation, evaluation and eligible historical distributions; it estimates no parameter across rows or years. Source truth normalization is not a predictor: test outcomes remain isolated from fitting and current-row history. Retain reported `overall_phase` unchanged. Example area1981/2026-04: raw (.15,.25,.60,.25,0) becomes (.12,.20,.48,.20,0); q2=.88, q3=.68, q4=.20, q5=0. This is the agreed data treatment, not proof that each corrected component matches an independently verified source value. Final support must be recomputed after this policy; the earlier q2>1 exclusion screen is superseded.

For comparable fitting support, use rows with valid complete cumulative targets for all four regressors, shared across arms. For primary classification scoring require a valid reported `overall_phase` and complete cumulative truth; actual crisis is reported phase>=3, matching the existing runner's final prediction-table truth source. Record disagreements with a share-derived phase for diagnosis. Do not silently replace reported phase by a reconstructed target.

Before fitting, freeze evaluation keys per test year/horizon for which required original feature rows and verified oracle months exist. V2/history NaNs do not remove a row. Apply those keys to A–D. Do not intersect predictions after the fact to hide failures. Also record the wider labeled cohort and all exclusion reasons. If an arm fails on an eligible key, the comparison is incomplete.

## 3. V2 as-of join

Input key `(admin_code, season_year, season)` maps to canonical area ID using the verified lookup. For each area/O: retain seasons with exclusive end E <= first day after origin month; select maximum E. Reject ambiguous equal-ended nonidentical seasons instead of arbitrary row-order selection.

A selected season must have valid calendar boundaries and a complete exported observation window; compare available and planned duration and inspect relevant QA. An ended-but-incompletely-exported season is a data gap: leave its V2 block unavailable/NaN and disclose it, rather than backfill a different season as if it were the selected latest season. Do not invent values for individual missing metrics. Preserve season dates, window duration, selection key, metric missingness and QA in diagnostics.

Only the 14 named ensemble means enter X. The same season/values must be used for all rows with the same area/O regardless of target/horizon, subject to the same source snapshot.

## 4. Oracle weather

Use `Rainf_f_tavg_mean` and `Tair_f_tavg_mean`, the pair required by the existing forecast-weather module, from verified historical realized observations. Materialize two columns per permitted k with stable offset suffixes. Thus the added weather width is 0/6/12/12 for H=0/3/6/12.

For a row with origin o, month k is o+k, with 1<=k<=min(H,6). Never use weather after the target or after o+6. Training rows use their own origins, not the current test origin. Since training T<=fit O and k<=H, their oracle weather event months cannot exceed their training target month; verify this in the ledger.

Missing/unverified oracle observations invalidate that row for the common oracle comparison until resolved. No forecast-file substitution, temporal forward fill or shortened oracle window. Current raw April 2026 Somalia rain/temperature exactly match March for 904 areas; source tracing is required. Exact equality is a warning to investigate, not proof of the mechanism. Report per-horizon eligibility because H=12 may not require those April values.

## 5. Rich-history construction

Use valid Somalia distributions from the full authorized ledger, including pre-2022 and earlier test-year records, but only U<=o and U<t for each feature row. A historical ledger row can be a valid predictor source without being an eligible supervised training row.

History QC retains P1–P4 required, the reference's explicitly recorded missing-P5-to-zero history rule and positive estimated population. Grill G4 supersedes the reference's [.90,1.10] sum gate: for finite nonnegative components with positive finite S, normalize by S using the same arithmetic as supervised targets. Do not reject solely because the raw distribution sums to more or less than one. A missing-P5 history fallback must be flagged and does not authorize filling missing supervised targets. Log remaining QC exclusions. A source lacking the required history-QC fields is a preparation gap.

The eight series are q2,q3,q4,q5; sum(k*Pk); normalized entropy −sum(Pk*ln(Pk))/ln(5); concentration sum(Pk²); and q4/q3 (NaN when q3=0). Preserve the reference's exact threshold convention for binary history descriptors, without substituting it for reported-phase evaluation truth.

Port the ordered history recipe (468 additions in the reference) and explicitly resolve five reused baseline aliases. If no semantically identical IPCCH base feature exists, materialize the required history quantity once; freeze the resulting ordered schema and width before fitting. Do not import original93 features or force width561.

Last six slots are the last six valid observations, not fixed monthly lags. Keep actual gaps, original slots for ratios with undefined values, and NaNs. Reference windows m06/m12/m24/m36 are inclusive calendar windows ending at o; all means all eligible history. Use population standard deviation with at least two values and OLS slopes with at least three; averages/extrema need one. Preserve observed-transition semantics rather than implying continuous state between sparse reports.

Retain six selected source keys per feature row and the full eligible source ledger needed to reconstruct windows. No history means NaN summaries and explicit support counts/absence flags. No explicit history-weather products.

## 6. Temporal selection and final fitting

Define an outer fitting job for each `(test_year, horizon, origin)` with eligible test rows. The candidate supervised window is fixed by test year; clip its maximum label month at outer O. Predictions at the same origin share one selected ensemble per arm. Reuse only when source, feature schema, fitting keys, validation keys and configuration identity match.

### Inner validation proposal

Within the clipped outer pool, use the latest three distinct eligible target months as the chronological validation tail. Do not use random row splits. At least two such validation months must yield supported inner folds; otherwise the outer job is unsupported. This minimum is a technical proposal, not an empirically established sample-size guarantee.

For each inner validation target v, origin ov=v−H. Fit only candidate-window rows with target u<=ov AND u<v. No label at v enters that inner fit (critical at H=0). Features on every inner fitting row obey its own origin. Earlier observed validation months may update a later validation row's history; chronological refitting may use them only when already known by that inner origin. Every validation target must be <=outer O, so no later labels enter selection.

An inner fold needs nonempty eligible fitting and validation pools. Record unsupported folds and reasons before candidate scoring, identically across candidates/arms. Do not replace skipped recent months with cherry-picked older favorable months. If the supported pooled validation truth lacks either crisis/noncrisis class, declare selection unsupported rather than optimize a degenerate classification sample.

Fit each of six configuration bundles on each supported inner origin. Pool TP/FP/FN over the shared validation keys and maximize F2=5TP/(5TP+4FN+FP); no equal average of monthly F2s. Tie: first bundle in the predeclared order. Do not use outer test outcomes for ties, budgets, thresholds or candidate expansion.

Refit the selected bundle on the full clipped outer training pool. Constant targets use a recorded constant predictor instead of injecting fake rows. Nonconstant fit errors make the cell incomplete; do not switch models silently.

### Six candidate bundles

Each bundle specifies common settings for q2/q4/q5 and a q3 override; counts below are regressors' tree counts, not ensemble member counts. Full executable inventory: `candidate-configs.json`.

| ID | max_depth common/q3 | n_estimators | learning_rate | min_child_weight |
|---|---|---:|---:|---:|
| X1 | 3/3 | 200 | .05 | 5 |
| X2 | 5/5 | 200 | .05 | 5 |
| X3 | 5/5 | 500 | .05 | 5 |
| X4 | 7/7 | 200 | .05 | 5 |
| X5 | 7/7 | 500 | .05 | 5 |
| X6 | 11/9 | 200 | .10 | 0 |

Preserve existing common/q3 subsample 1/.5, colsample_bytree .5/.7 and gamma 0/.1. Use squared-error regressors, seed42, CPU histogram fitting, one model thread, no early stopping or extra calibration. X6 reflects the current JSON values for those scientific hyperparameters; it is not a previously validated no-leakage model or an asserted exact runtime reproduction. Freeze the actual environment before execution.

Fit weights w=0.5**((fit_origin−training_target_month)/24), with month distance>=0, for outer and inner fits. Do not anchor long-horizon inner fits to test-year January.

Maximum tuning fits per supported outer arm job: six bundles x three validation months x four regressors =72, plus four final fits. Empty/constant paths reduce actual fits. At most 2 years x 12 target months x 4 horizons x 4 arms =384 outer jobs before H=0 B/C deduplication; do not launch this bound blindly. Preflight computes the actual job/fit inventory; a bounded pilot measures runtime after implementation is authorized.

## 7. Phase conversion and metrics

Preserve fixed threshold .2 and the existing descending phase5→phase2 first-crossing convention; default predicted phase is1. Grill G3 explicitly supersedes the old runner's rounding: compare full-precision predicted cumulative shares directly with >=.2 in both inner selection and outer scoring. Save raw cumulative outputs and compute share R-squared from raw q3 predictions. Rounding is presentation-only and never feeds decisions or scores. Do not introduce clipping/isotonic correction/calibration silently. A boundary check must distinguish .196 (below), .2 (at) and .204 (above) without premature rounding.

Unlike `convert_phase_predictions` at `scripts/modeling/run_deep_feature_weight_decay_forecasting.py:285-287`, do not fill missing predictions with zero or delete rows based on summed predictions/truth. All-zero valid cumulative truth is a valid phase-1 distribution. Nonfinite prediction on an eligible row is a failure, not permission to remove it.

Report pooled confusion-count F2/F1/precision/recall, reported-phase accuracy and raw-q3 R-squared per year/horizon/arm. Formula-zero F scores with actual positive truth and no predicted positives are valid zero; undefined denominators or constant-truth R-squared get null plus a reason. Include support, all phase counts, months, exclusions and validation support. Report paired sequential deltas on the fixed common keys. No significance or stable-superiority claim is authorized solely from these two years' point estimates.

Grill G5: the pooling above is over eligible rows within one `(test_year,horizon)`, never across horizons. Compare specifications A–D and reference baselines within that stratum on the corresponding matched keys. Display horizon-specific panels if useful, but no cross-horizon ranking, cross-horizon key intersection or aggregate horizon-averaged superiority claim. The task is specification comparison conditional on horizon.

### Persistence reference — approved in grill G1

For each evaluation area/target/horizon, retrieve the latest valid reported `overall_phase` with U<=O and U<T. Carry that phase forward unchanged; its binary crisis prediction is phase>=3. Use the same ideal month-end availability assumption as the model histories. Permitted source records include pre-2022 and earlier test-year observations. No fitting, parameter selection, age cap, cross-area borrowing or no-history phase imputation.

Save the chosen source area/month, phase, age, and a no-history status. Evaluate classification metrics and phase accuracy on `primary_common_keys intersect persistence_available_keys`. Recompute every A–D model's metrics on that same subset before paired persistence contrasts. Preserve the original A–D primary-cohort scores separately; never compare full-cohort model F2 with subset persistence F2. Report supports and no-history counts per year/horizon. This phase-only baseline has no population-share prediction: its share R-squared is not applicable, not zero. Verify latest-observation selection, H=0 self-exclusion and no-history behavior in a focused check.

### Always-crisis diagnostic — approved in grill G2

Predict binary Phase3+ for every row, without fitting, tuning, threshold selection or assigning a specific ordinal phase. For a nonempty cohort, TP equals actual positives, FP actual negatives, FN=TN=0. Compute F2/F1/precision/recall with the same denominator rules as learned predictions. With positive prevalence p, F2=5p/(1+4p). Also report prevalence and the confusion counts so high F2 from frequent crisis is visible.

Evaluate on both the primary A–D cohort and the persistence-supported subset, using their exact keys. Ordinal phase accuracy and share R-squared are not applicable. Do not count this as a fifth fitted arm or allow its scores to change the frozen candidate search. A hand-calculable confusion-count case suffices to verify the reference computation.

### Paired area-cluster bootstrap — approved in grill G6

Report point delta F2 and a 95% percentile interval for B−A, C−B and D−C on primary common keys within each `(test_year,horizon)`. Also report each A–D arm minus persistence on the persistence-supported subset, and each arm minus always-crisis on both declared cohorts. Identify the cohort explicitly; do not treat the two cohort versions as interchangeable. H=0 C−B is exactly zero wherever F2 is defined because the predictions are reused.

Proposed reproducibility contract: within each stratum/cohort, sort unique canonical integer area IDs in ascending numeric order (implementation decision recorded 2026-09-24; the saved ordered area list is authoritative for replay) and initialize NumPy `Generator(PCG64(42))`. For each of exactly 2,000 draws, sample N area indices uniformly with replacement from the N areas. Include every eligible month of each selected area with its sampled multiplicity. Reuse that draw's multiplicities across every prediction vector compared on the cohort. Compute weighted TP/FP/FN and F2 from pooled rows, not the mean of area or month F2s. Save the ordered area list, cohort-key hash, RNG/seed, draw-indexed multiplicities and contrast deltas so comparisons can be replayed without refitting or drawing again.

Use the 2.5th and 97.5th percentiles of paired delta draws with linear quantile interpolation. Each replicate follows the same metric denominator rules as point scoring. Do not substitute zero for undefined F2, redraw until successful or silently discard undefined replicates. Record valid/undefined counts and reasons per contrast; if a point score is undefined, fewer than two areas are supported, or any of the 2,000 paired deltas is undefined, report the interval as unavailable (retain finite draws as diagnostics only). Identical predictions may legitimately produce a zero-width interval when otherwise supported.

These are conditional intervals over the observed areas and saved predictions. They do not include model-refitting/selection uncertainty, establish future-year guarantees, correct all spatial dependence, or authorize multiplicity-adjusted significance claims. No intervals comparing different years or horizons and no pooled superiority headline.

## 8. Evidence, checks and current source gaps

Persist explicit source/code/runtime hashes, ordered X schema, area/season/weather/history lookup provenance, candidate inventory, fitting and inner-validation keys/dates, validation predictions/F2, selections, models or constant specifications, raw predictions and replayable metrics. Presentation values may be rounded but are never an authoritative scoring artifact. Use existing CSV.gz/JSON/model formats and project results/report roots. Keep raw external sources unchanged; avoid an unnecessary storage framework.

Minimum runnable checks in the later implementation plan:

1. Month-end GS join including cross-year/exclusive-end boundary and no prior season.
2. Weather offsets for all four H, verified observation identity and no forecast fallback.
3. Inner/outer label cutoffs, H=0 target self-exclusion, and authorized earlier-test-year history use without fitting leakage.
4. Rich-history parity on irregular observations, missing q3 ratio, absent slots and schema aliases.
5. Common scoring support, valid phase1/all-zero targets, candidate tie, constant fit and unsupported validation paths.
6. Independent metrics replay from saved keys/predictions and a bounded model smoke run.
7. Paired bootstrap replay: whole-area month retention, shared multiplicities, deterministic draws/quantiles, identical-prediction zero deltas and explicit undefined/insufficient-area handling.

Current gaps retained from `research.md`: April2026 weather provenance; isolated model-ready Somalia January2026 label; fs3/asof12 and legacy category-history lineage; V2 source window/calibration provenance; existing hyperparameter-selection provenance. Input corrections require explicit evidence and approved scope, not silent source overwrites. Missing evidence can block a particular cell or a no-leakage claim without being called a scientific model failure.

## 9. Review and audit lifecycle

The requested sequence brainstorm → written spec → grill is complete through G6; consolidated final technical acceptance remains pending. This does not close the task or authorize fitting. After final spec acceptance, prepare a separate implementation plan and acceptance evidence mapping. Approved planning artifacts must be committed before the verified bound Claude executor runs `trellis-audit --repo '<exact registered IPCCH path>' start somalia-flood-food-crisis`.

Reverify executor/session and controller before that transition. Do not invent a historical base SHA or transfer an active run. Implementation checks and committed evidence precede close; controller acceptance governs audit status. The current registration and boot evidence are historical setup facts, not proof that an audit run exists now.
