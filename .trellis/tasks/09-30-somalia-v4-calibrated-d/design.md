# Specification — Somalia v4

Version: 1.3 approved, 2026-09-30. Status: G1-G9 resolved; user approved the final consolidated summary ("确认"). Validation status: Not Executed (planning-file consistency checks only). `prd.md` owns requirements; `grill.md` records decisions; `candidate-configs.json` records the candidate inventory and numerical policies. Original and augmented are separate scenarios throughout all label roles. Planning commit and audit lifecycle setup are authorized; model execution is not.

## 1. Changes from v3

| Contract | V3 | V4 |
|---|---|---|
| Seasonal source | `climate_2022_2026_FINAL_MODEL_READY_V2.csv` | `climate_2015_2026_MODELING_READY.csv` |
| Outer target years | 2025, 2026 | 2022, 2023, 2024, 2025, 2026 |
| Candidate fitting years | three preceding years | all eligible earlier years through Y-1, expanding by outer year (G1 approved) |
| Model views | direct, residual, selected per setting | one selected final D per setting; direct/residual and none/shift/isotonic remain internal candidates (G2 approved) |
| Data settings | original and augmented fitting pools | original-only versus validity-expanded labels throughout fitting, selection, calibration and testing (G8) |
| Augmentation years | 2022-2026 | all verifiable historical source years; fold cutoffs still apply (G3 approved) |
| Outer truth | shared expanded policy, but final mapping added no 2025/2026 tests | original: observed labels only; augmented: originals plus permitted validity copies; additions depend on source/covariate support |
| Reporting | year/horizon results | independent annual plus pooled 2022-2026 results per setting/horizon; no cross-setting deltas or ranking |
| Horizon selection | H0 selection transferred to H3/H6/H12, with disclosed later-recipe labels | independent origin-valid selection at H0/H3/H6/H12 (G4 approved) |

Detailed reuse references: v3 `design.md` sections 2-8, final G3 in `prd.md:69-76`, and q3-first v2 `design.md` sections 2-5. The user clarified that the priority is the best attainable performance under the current setting; training choices may change and a v3 score comparison is unnecessary. Reuse those scientific definitions where appropriate, without treating historical comparability as a constraint. Freeze the accepted procedure/search budget before outer scoring and interpret attained performance within that budget, not as a proven global maximum.

## 2. Inputs and seasonal join

Climate path: `/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/IPCCH_shared_folder/climate_2015_2026_MODELING_READY.csv`.

SHA-256 at planning: `f024a66c8979fb4a8c66fba1f04e7e69355fa75b499793d29001a146d8c2958e`.

Use exactly `prcp_anom_gs_ensmean`, `prcp_z_gs_ensmean`, `rainy_days_gs_ensmean`, `cdd_gs_ensmean`, `tmean_anom_gs_ensmean`, `tmax_anom_gs_ensmean`, `hot_days_p95_gs_ensmean`, `gdd_gs_ensmean`, `edd_gs_ensmean`, `sm_z_gs_ensmean`, `ndvi_anom_gs_ensmean`, `evi_anom_gs_ensmean`, `spi03_gs_ensmean`, and `spei03_gs_ensmean`.

For area and origin O, choose the latest season by actual exclusive end E with E <= first day after origin month. Verify calendar validity and exported available duration against recalculated planned duration. An ended but incomplete selected season gives an unavailable/NaN seasonal block, not silent substitution from an earlier season. Missing metrics/history do not remove an otherwise eligible evaluation row. Cross-year season dates, not `season_year` alone, determine eligibility. Equal-ended ambiguous seasons fail preparation.

Pin raw panel, full monthly deep-feature source, fixed spatial/schema definitions, lookup and validity snapshot through explicit paths. Preserve raw outcome values and normalize finite nonnegative complete phase shares by their positive sum as in v3. D retains the original temporal predictors, seasonal means, permitted realized-weather offsets, and report-aware rich history. At H0 there are no added future-weather offsets.

Source roots are exact, not recursive-discovery hints:

- Raw: `/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/Google fund/Analysis/1.Source Data/assembled_IPCCH/raw/IPCCH_2026_completed.csv`.
- Monthly X: `/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/Google fund/Analysis/1.Source Data/assembled_IPCCH/features/forecasting_subset_IPCCH_2026_target_corrected_deep_features.csv`.
- Somalia lookup: `/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/Google fund/Analysis/1.Source Data/assembled_IPCCH/country_area_id_lookup.csv` (`iso3=SOM`).
- Validity: `/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/Google fund/Analysis/2.source_code/Step0_Initialization_and_construct_Scaffold/curl_new_data/outputs/areas_combined_2026-05-15.geojson`; recorded expected SHA `f5418154a0aafd8d353fb0ce1f379ba5f95cad212725d4961bc90d5d52016214`, reverify at preflight.

Retain the v3 explicit fs0/fs1/fs2/fs3 paths and hashes as non-label parity references, never as the expanded label/X cohort. Read monthly X in Somalia-filtered chunks with full required temporal continuity and fixed neighbor features; recover H0/H3/H6 through the existing upstream scope functions and H12 through the existing full deep schema. Target-corrected outcome columns do not establish truth. Block `overall_phase_lag1` and target-side `estimated_population`; rebuild allowed categorical/rich history with source-report exclusions. Seasonal changes are intentional; parity on previously supported keys applies to the remaining non-label predictors, with every permitted exception named.

Supervised targets require complete finite nonnegative P1-P5 with finite positive sum; normalize row-locally, preserve original components and reported phase, and derive q2/q3/q4/q5. Preserve v3's separate history QC (including its flagged missing-P5-to-zero history-only rule), source timing and missing-history semantics. D's rich history retains the referenced eight-series recipe, six actual report slots, elapsed times/differences/slopes and 6/12/24/36-month/all-history summaries. Do not turn copied target months into observations or regenerate branch-specific spatial graphs.

The source audit reports removed QA fields and source-composition changes, not proof of upstream correctness. Keep source counts and window/QA metadata diagnostic; no new predictor family or upstream repair is implied. Coverage and hash checks are performed; season-join, source-value parity and upstream provenance validation remain future gates.

## 3. Annual folds — G1 approved

Use all eligible original-source history through the year before each outer target year. The candidate label pool expands as Y increases; the augmented setting adds permitted copies of those eligible sources. With the currently inspected ledger, the anticipated windows are:

| Outer target year | Candidate supervised years |
|---|---|
| 2022 | 2017-2021 |
| 2023 | 2017-2022 |
| 2024 | 2017-2023 |
| 2025 | 2017-2024 |
| 2026 | 2017-2025 |

The rule is earliest eligible raw labels through Y-1, not an arbitrary fixed 2017 lower bound. Verify the raw source and supervised QC at preflight; report actual support and update the inventory if earlier eligible labels are found. Climate coverage starts in 2015 but supplies no missing outcome labels. Admitting all earlier rows does not imply equal fitting weights; G5 approves selecting time decay within training-period validation.

For each target T and horizon H, O=T-H. A fitting label must satisfy both recipient target <=O and source-original availability <=O, with inner fit target < scoring target. Both original year and recipient target year must lie in that fold's accepted supervised window. Outer-year labels do not enter that year's fitting/selection/calibration pool, even when a later source could backfill an earlier target month. Earlier outer-year reports may update permitted feature histories for later origins subject to report exclusions; they do not become fitting labels in that fold.

Canonical prediction key: `(data_setting, outer_year, horizon, area_id, target_month)`. This identifies each scenario's predictions; no paired cross-setting key is defined. Keep immutable source-record key `(area_id, original_month, raw_snapshot_sha)` and source-family identity separate. Verified current analyses use their shared `anl_id`; unmatched originals retain v3's explicit local-month group identity and cannot authorize copies. Such local grouping does not prove full publication independence. Pin the group map before folds/scores. Month arithmetic is `year*12 + month-1`.

Freeze scoring keys separately per setting from its label policy and source/feature eligibility before scores. Keep unavailable cells if a fold lacks training/calibration support. Preserve per-fold source-family purges and OOF dependency provenance rather than reducing the evaluation cohort to improve support. G9 approves the full-cohort incomplete-result policy below; it does not permit copies in original or a change to leakage rules.

## 4. Two distinct label scenarios — G3 and G8 approved

| Setting | Base fitting, inner selection, calibration labels | Outer truth and interpretation |
|---|---|---|
| original | eligible original raw labels only | eligible original raw labels only; performance at observed assessment months |
| augmented (validity) | eligible originals plus permitted validity copies | eligible originals plus permitted validity copies; performance over the supported validity-expanded monthly population |

Run both settings afresh with equal accepted candidate inventories and independent training-only selection. The settings use their own validation and test populations; different row counts, months and report-duration influence are part of the scenarios. They are not paired arms for estimating augmentation's effect. Keep setting identity on all cohorts, scores and manifests; do not force key equality, trim to an intersection or rank settings by headline scores. Both use the same original-report information ledger and non-label feature sources. No copied report enters history as a new observation or resets observation age.

G8 correction supersedes the earlier shared-test design and rejects the shared-selection proposal. Canonical setting IDs remain `original` and `augmented`; validity is an alias for the latter, not an extra experiment. A common provenance-aware source ledger may be reused, but every original fitting, selection, calibration and test view filters to `is_copy=false`. Augmented views admit eligible copies under the rules below. Common source facts do not establish a common scoring cohort.

Inherited replication: preserve raw values; use verified SO/A/C validity metadata; include endpoint months; intersect with supported raw area-month covariates; fill only fully missing six-field label blocks; originals win overlaps; latest original observation month wins competing verified reports; unresolved equal-date conflicts stay unfilled. Copies inherit the source family and original observation-month-end availability. Exclude the target family from its own history/residual baseline/persistence and every fitting/calibration dependency serving its scoring context.

G3 approved: apply this replication policy to all eligible historical source years in the augmented training pool, removing v3's 2022 lower bound. Existing `v3_validity/ledgers/api_rounds.csv:7-11` records multi-month current periods in 2019-2021 (2019 July-September; 2020 January-March and July-September; 2021 January-March and July-September). Its 2017-2018 periods are single-month. Early periods are candidate evidence, not completed v4 links or proven added rows; the same unique-round-start correspondence, raw-value authority and recipient-covariate/blank-block checks still apply. Test replication applies only to augmented in requested target years 2022-2026; original tests never include copies. Fold eligibility is applied after constructing the provenance-aware ledger, so expanding validity scope never overrides supervised-year, origin or source-family exclusions. Each eligible copy retains its ordinary per-row fitting weight rather than being normalized by report length.

Current coverage limitation: v3 accepted unique round-start matches for linked 2022-2024 analyses and excluded 2025 projection/spillover records and the 2026 beyond-covariate window. Existing v3 copies do not demonstrate expanded 2025/2026 testing. Apply the same verified linkage policy to the new historical scope and retain unmatched/unsupported diagnostics. Do not invent windows, extend every original merely because replication is requested, or upgrade API values to raw truth. Actual 2026 raw monthly support ends April; later seasonal coverage does not extend that panel.

Expansion is the augmented scenario's truth policy, not a promise that each year gains rows. Report original/copy/unmatched counts and distinct report counts per setting/year, with zero copies required for original. If required linked support cannot be established, record the affected augmented cell/source gap explicitly and apply the agreed stop/unavailable behavior.

Mark the augmented scenario `augmentation_unavailable` and stop its fitting if there are no permissible added labels across the requested scope; an independently valid original scenario may proceed. A particular year with zero additions is valid and disclosed; it does not justify invented windows or a comparative claim. Existing raw labels keep precedence, including excluded-for-linkage months: linkage exclusion is not authorization to overwrite/delete raw outcomes. Partially populated/sentinel/invalid original blocks stay unchanged and diagnostic. For equally dated candidates, differing values or distinct unresolved source identities leave the recipient unfilled. Preserve every candidate, winner/rejection reason, original/copy flag and raw/normalized label representation.

## 5. Calibrated D — G2 and G5 approved

G2 approved: one validation-selected D procedure per setting, with direct/residual and none/shift/isotonic available internally; report only its selected final output. Identity/none is an eligible choice when learned calibration performs worse in training-period temporal validation. Keep the selected formulation, mapping and raw/final predictions explicit; the name calibrated D describes this selection procedure and does not imply a learned mapping always wins. G5 freezes X1-X6 as the bounded tree-parameter inventory crossed with the four time-decay choices below. This is not evidence of a globally optimal parameter search.

The inherited technical baseline is q3 = normalized phase3+phase4+phase5, squared-error regression, seed42 and CPU histogram. Final q3 is bounded to [0,1]; raw q3 remains saved. Residual candidates reconstruct q3 from the latest permitted distinct-report q3 and use the same-bundle direct fallback with its own mapping when history is missing. Do not manufacture a residual baseline.

Reuse the exact X1-X6 dictionaries from `configs/somalia_oracle_candidates.json`, SHA `9d572793a3815baa42aa8c85a3304b0cc5aef8b52f191b1f7d3b7924aca9ef0f`; only its tree/runtime dictionaries are reused, not its old F2 selector or fixed 24-month policy. Q3 depths are 3/5/5/7/7/9; trees 200/200/500/200/500/200; learning rates .05/.05/.05/.05/.05/.10; min-child weights 5/5/5/5/5/0. Common/q3 column subsample remains .5/.7, row subsample 1/.5 and gamma 0/.1. No new search, early stopping or loss is introduced. Preserve q2/q4/q5 as uncalibrated final-fit auxiliary outputs using the selected bundle/decay, as in v3; they do not drive selection or add model-comparison/ordinal headline tables.

G5 approved: select model time-decay half-life from 12, 24, 48 months and no decay, crossed with X1-X6, direct/residual and none/shift/isotonic. For finite half-life L, `w=0.5**((fit_origin-target_month)/L)`; for no decay, `w=1`. Ages must be nonnegative. Original and copied rows use the same per-row rule, with original source availability separately controlling eligibility; do not normalize by report duration or candidate total weight. Calibration and selection/evaluation remain equally weighted. This gives 144 declared recipes per selection context before unsupported candidates are marked; calibration choices reuse base OOF predictions, so they do not each require separate XGBoost fits. Model/OOF cache identity must include weighting and all existing pool/exclusion/schema/source identities. A residual candidate's same-bundle direct fallback also uses the same selected decay.

Selection uses the latest three eligible distinct original-report rounds, minimum two supported rounds. Copies do not count as new rounds. Mapping fits use earlier eligible OOF rounds only, purge the served scoring families from all dependencies, and never score a mapping on its own fitting rows. Fit/calibration/scoring labels are branch-specific. Model rows retain full decay weights; calibration/validation/scoring rows are equally weighted, with no report-length normalization.

For each scoring target v, use its own origin `O_v=v-H`; the fit cutoff is `min(O_v,v-1)`. Selection round membership groups original observation months, but never substitutes the original-report month for a copied row's target/origin. Freeze supported scoring rounds and their full branch-specific keys before candidate scores. Require at least two supported scoring rounds. Keep all eligible monthly members of each selected source round after window/origin/source-availability checks. A candidate missing support on any required frozen key is unavailable on the comparison, not rescored on a smaller sample.

For a learned mapping serving v, use up to the latest three earlier eligible original-report rounds, minimum two, with calibration target c<v, c<=O_v and original source availability<=O_v. Each OOF prediction must itself be made with its own origin-valid fit and histories. Purge v's held-out families from calibration labels and every upstream base fit/history input producing those OOF predictions, as well as that OOF row's own target family. Carry outer scoring-family exclusions through the entire inner dependency chain. Final mapping refits use eligible earlier OOF rows within the outer training window and origin; the same exclusions apply. The selected recipe and mapping must satisfy every origin-specific context even if identical contexts permit cache reuse.

The context identity includes setting, outer fold, horizon, scoring/receiving origin, all inherited held-out source families, candidate bundle/formulation/decay, exact fit/calibration/scoring keys and source/schema/runtime identities. Reuse only identical dependency contexts. Existing v3 RoundStore keys alone do not prove this identity. Persist context IDs and model/OOF/mapping parent IDs for independent traversal.

Mapping definitions: none is identity followed by final bounding; shift subtracts the unweighted mean raw-minus-truth error; isotonic is increasing least squares with [0,1] outputs and clipped extrapolation, requiring at least two distinct calibration scores. Constant truth may produce a valid constant mapping. Residual and same-bundle direct fallback fit separate mappings using their respective OOF predictions; no-history fallback is based on missing permitted history, not on failure of a supported residual model. Reconstruct q3 before calibration/bounding; never clip residual delta. An unsupported chosen mapping remains unavailable.

Inherited candidate selection minimizes pooled held-out final-q3 RMSE, then within a fixed 1e-12 global-minimum tie set uses pooled crisis AUC, mapping order none/shift/isotonic, bundle order, and direct-before-residual. The final deterministic weighting tie order is no decay, 48, 24, 12 months. Preserve unsupported-candidate behavior on fixed keys; do not silently change the chosen calibration method if final support fails. Keep actual search support, failure reasons and declared inventory in evidence; any budget change after freezing requires a new pre-score decision rather than inspecting outer scores to expand the search.

No frozen XGBoost configuration is selected using annual or pooled outer evaluation outcomes. Save selection dates, recipe identities and mapping support.

G7 approved: the selector optimizes population-share error, not every reported endpoint. On identical validation rows/weights, lower final-q3 RMSE corresponds to higher R2 where R2 is defined, but reported-phase crisis AUC and fixed-threshold F1/recall may decline. AUC only breaks a numerical RMSE tie; classification deterioration is reported and does not veto the RMSE winner. Do not switch objectives after observing outer results.

## 6. Horizons — G4 approved

Baseline fact: v3 uses H=0,3,6,12, optimizes H0 only and refits its selected recipe at H3/H6/H12, including an explicitly disclosed exception allowing later H0 recipe-selection labels. That was a historical computational/scientific choice, not a requirement to preserve under the clarified v4 objective.

G4 approved: retain H=0,3,6,12 and independently select the calibrated D recipe for each horizon, data setting, outer-year fold and applicable outer origin. Use that horizon's own temporally valid inner predictions and available training-period labels to select direct/residual, the hyperparameter/weighting candidate and none/shift/isotonic. Model fitting, preprocessing, calibration and selection all obey the receiving origin cutoff and scoring-report exclusions. Do not transfer a later H0 winner as an undeclared fallback. Independent tuning adds computation and can expose insufficient early-fold support, which remains explicitly unavailable.

This supersedes v3's ancillary recipe-transfer exception. Retain the deliberate perfect-weather allowance and ideal label-availability assumption: realized-weather offsets remain 1..min(H,6), with verified weather and explicit source gaps. Report each horizon separately, with no horizon pooling/ranking.

## 7. Annual and pooled evaluation — G6 approved

Annual tables score each setting's own frozen truth/keys within each year/horizon: observed-only for original, observed plus permitted copies for augmented. Report raw/final q3 R2, RMSE, MAE, signed mean error, continuous-score crisis AUC against raw-authority reported phase>=3, and fixed-threshold binary F1/precision/recall using final q3>=0.2. Counts include rows, areas, months, original reports, original/copy status, unsupported predictions and exclusions. Undefined R2/AUC stays null with a reason.

Report scope: 40 annual slots (five years × four horizons × two settings) and eight pooled slots. Retain all slots with status/reason, even when a setting's source-defined cohort is empty. Each setting has one primary cohort under its own label policy; remove the earlier common observed-only secondary comparison. Only selected D appears in model tables. Keep means of truth/prediction, clipping and fallback counts, confusion counts, and actual year/month coverage as diagnostics. Separate direct/residual candidate results remain selection evidence, not extra outer-score comparisons. Persistence/all-crisis and ordinal headline tables are omitted under the requested model simplification.

G6 approved pooled estimand, scoped by G8: concatenate saved annual out-of-sample predictions for 2022-2026 separately within each setting/horizon, using one equally weighted eligible canonical area-target row. Original pools observed labels only; augmented pools observed and permitted copied labels, each contributing weight one. Recompute each metric from this concatenation; do not average annual metrics and do not refit. Years with more eligible area-months have more pooled weight; retain annual scores and year/row composition so this weighting is visible. Later folds may legally train on earlier years' observations; each prediction is out of sample relative to its own fold, not generated by one five-year holdout model. This scoring weight is separate from the model's validation-selected training decay.

Keep `(area_id,target_month,horizon,setting)` unique and retain `outer_year`, prediction/model identity and a separate cohort hash per setting/year/horizon. No removal of failed predictions after fitting and no mixing settings/horizons in pooled results. Augmented pooled labels represent repeated monthly validity truth, not independent monthly assessments; original results concern observed assessment months. Actual 2026 partial coverage remains disclosed in each scenario.

Join truth and predictions by explicit canonical keys with one-to-one validation within each setting; verify that setting's saved cohort digest. Never align by row position or convert keys to sets before duplicate checks. G9 approved: a missing/nonfinite required prediction or failed chosen mapping makes the affected setting/year/horizon's full-cohort final result incomplete. Keep any available raw predictions as clearly separate diagnostics; do not replace final predictions by clipped raw or drop failed rows. That setting/horizon's requested pooled final result is incomplete if any required row in its union of source-eligible annual keys lacks its required final prediction. Complete annual results and the other setting's complete result remain reportable. A structurally empty source-defined annual cohort adds no rows and is disclosed; it is not a failed prediction to be hidden. Undefined AUC/constant-truth R2 is a metric-specific status and does not suppress computable errors. Preflight exposes structural support gaps before expensive fits; implementation defects still require repair.

G8 reporting consequence: remove augmented-minus-original differences, paired area bootstrap, common-cohort secondary comparisons and cross-setting significance/ranking claims. Do not silently replace them with a new per-setting CI procedure. Tables may present separately labeled scenarios, but a score difference cannot be interpreted as augmentation helping or hurting because the evaluation populations differ. Preserve original/copy composition as diagnostics, without forcing a matched cohort even where particular years happen to have identical keys.

## 8. Evidence and lifecycle boundary

Future evidence includes explicit input/config/runtime hashes; source/label/cohort/fold ledgers; selected season and complete-window diagnostics; schema/parity checks; report exclusions and fitting weights; OOF/calibration dependencies and selections; keyed raw/final predictions; annual and pooled metrics replay. Keep separate v4 results/reports roots and all earlier artifacts immutable.

V4 output roots: `results/experiments/somalia_oracle/v4_calibrated_d/` and `reports/somalia_oracle/v4_calibrated_d/`. Use existing CSV.gz/JSON/model formats. Predictions name `data_setting` and `prediction_branch` separately. Persist stable explicit keys as authority; frame-local row positions are diagnostics only. Parse stored prediction floats with round-trip precision so isotonic ties and .2 decisions survive replay. Independently reconstruct each setting's label eligibility, annual/pooled keys and metrics from saved predictions and source ledgers, not solely saved aggregate scores. Verify original has zero copies in every label role and augmented admits permitted copies; no cross-setting digest equality or paired-delta replay is required.

Verified planning runtime: `/home/swl007007/.venvs/ipcch-geo/bin/python`, Python 3.12.3, NumPy 2.4.4, pandas 3.0.3, scikit-learn 1.8.0, XGBoost 3.2.0. Record/check the actual environment again before execution; no silent interpreter/package substitution. One model thread; at most 12 workers, bounded by the measured pilot and memory. Do not run full pytest concurrently with heavy model jobs. Training cost is unmeasured; the execution plan requires a source/support preflight and bounded pilot before a full run.

`implement.md`, `implement.jsonl` and `check.jsonl` carry the concrete execution/check plan and context. After final user review, commit only approved task artifacts, verify the other running Claude executor, bind it through `trellis-audit register`, and have that executor run `trellis-audit --repo '<exact existing path>' start somalia-v4-calibrated-d`. Boot and verify the controller, active run, executor session/terminal, base SHA and Trellis status. Initial inspection found a stopped controller and no active runs; recheck live state at setup. Registration/start is setup only; this session does not authorize implementation, experiments or task close. Preserve that boundary explicitly in the executor handoff.
