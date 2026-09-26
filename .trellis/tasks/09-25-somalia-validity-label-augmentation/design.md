# Specification — Somalia validity-period label augmentation

Version0.2 — 2026-09-25. G1-G3 incorporated; final technical review accepted 2026-09-25 (prd.md Final acceptance; G3 in grill.md, R16). PRD R1-R15 record accepted intent; remaining technical details below are concrete proposals for acceptance. No augmented labels, feature regeneration or new model runs have been executed.

## 1. Question and comparison

Test whether filling previously unlabeled months within verified source-report validity improves overall monthly performance of D. The treatment intentionally adds training rows and gives longer-validity reports greater summed fitting influence. Original label values and raw covariates are preserved.

Two branches, each with D-direct, D-residual and D-selected:

| Branch | Model, selection and calibration label pool | Outer evaluation |
|---|---|---|
| original | Original eligible raw-label observations only | Full eligible expanded cohort |
| augmented | Originals plus permitted blank-month copies | Same full eligible expanded cohort |

Use the inherited Somalia windows: supervised2022-24/test2025, supervised2023-25/test2026. Retain pre2022 original history where previously authorized. Restrict augmentation targets to2022-26 and actual monthly covariate support. Optimize H0; H3/H6/H12 refit each branch's H0 recipe without horizon-specific search. The previously accepted later-recipe-label exception for ancillary horizons remains disclosed; it does not waive new source-report isolation or fit/calibration availability rules.

Headline results are the expanded-cohort comparison. Original-label rows form the secondary restricted-cohort table; added-only rows may be shown as a diagnostic. All comparisons within a year/horizon use identical frozen truth/keys, except explicitly named baseline-support subsets. No headline restricted-only comparison and no cross-horizon ranking. Do not compare a new expanded score directly to an old narrower score as proof of improvement.

## 2. Inputs, authority and the mapping gate

Preserve the raw panel `assembled_IPCCH/raw/IPCCH_2026_completed.csv` and v1/v2 artifacts. The latest verified local validity snapshot is `Step0_Initialization_and_construct_Scaffold/curl_new_data/outputs/areas_combined_2026-05-15.geojson`; use its embedded metadata/hash and SO/A/C records, not an older pull or projected periods. Keep analyses metadata for diagnostics; its created/modified fields are not verified publication dates.

Treat raw phase1_percent..phase5_percent and overall_phase as authoritative values, and the API only as potential matched validity metadata. Retain the established finite/nonnegative/positive-sum normalization for model targets; never use newer API values to correct original values in this experiment. Do not take target columns from the corrected deep-feature artifact as raw truth. Reconcile any raw-versus-v2 label differences before presenting a fresh original branch; preserve both sources and identify the chosen raw row.

Before expansion, produce an area/report correspondence ledger with raw area/original month, API snapshot/id/anl_id/period/from/to, mapping evidence, spatial multiplicity and match status. Acceptance requires documented original-source lineage or a separately verified authoritative crosswalk/reconstruction tying this original record to that area/report/period. A nearest centroid, point-in-polygon, equal phase vector, similar name or matching month alone does not prove source identity. Such candidates may be diagnostics, never silently upgraded to verified matches. Handle GeometryCollection explicitly if spatial checking is used; do not inherit its silent exclusion from the old correction notebook.

No complete crosswalk has yet been established. Mapping preflight must quantify verified matches and potential added labels by year; unmatched/conflicting records remain originals and are not extended. If no rows can be safely added, stop after the coverage/diagnostic output with `augmentation_unavailable`, not a model experiment claiming augmentation. If implementing the mapping would require a weaker evidence rule, source replacement or recovery of missing external artifacts, surface that concrete requirement separately; this spec does not authorize guessing.

## 3. Label extension, missingness and overlap

Proposed monthly contract: include both from and to months. For each verified original source record, enumerate its valid months and intersect with2022-26 and existing raw `(area_id,month)` rows. Do not create May/June2026 covariates merely because an API record is valid through June; current raw support ends April2026.

An augmentable source has a valid reported phase and complete supervised P1-P5 under existing QC. G2 confirms a recipient is blank only when overall_phase and all five shares are missing under the existing CSV missing-value parser. Copy the full six-field label from one source. Preserve partially populated, sentinel-coded or invalid existing label rows unchanged and record them; do not reinterpret zero as missing, mix phases/shares from multiple reports or silently fill partial outcomes. Unrelated raw values, including recipient covariates, remain unchanged. The supervised source distribution is normalized consistently after preserving raw components. A full raw scan found zero partial six-field blocks for Somalia2022-26; this does not make all blank rows valid augmentation recipients.

Existing raw labels always win. Where multiple verified reports can fill a blank month, select maximum original observation month, not the report giving the most favorable model score. Equal-date conflicting values leave the recipient unfilled. Equal-date/equal-value candidates may only collapse when verified to be the same source assessment; otherwise retain ambiguity and leave unfilled. Keep all contenders, decision and reasons. API-only records lacking an original source label do not enter either branch.

Original observations remain present even when their timestamp is not inside a matched validity interval; that mismatch itself must be resolved before that record can authorize expansion. Do not move the original record's date or invent a new validity interval to make it fit.

## 4. Identity, availability and history

Keep these separate: recipient target month, original observation month, source available-at, validity interval, raw source-record key, and verified assessment identity. Source availability stays original observation month-end for all copies under the inherited ideal assumption. This is not historical release-date reconstruction. A backfilled truth can describe an earlier month but was not then available to fitting or predictors.

Each original `(area_id,original_month,source_snapshot)` is an immutable local label-source key; all descendants inherit it. Where verified API lineage connects several originals/local areas to one assessment, retain the shared analysis/period group and use it for exclusion so an assessment cannot escape via another linked local ID. Unmatched originals receive explicitly local-only identities, not invented API IDs. They are not expanded. Disclose unresolved broader publication grouping and do not claim that a local-only key proves complete publication independence. Freeze this group map before any split or score.

The historical observation ledger contains original reports only, with verified duplicates collapsed and original timing retained. Added monthly target rows do not become extra historical observations. Both branches use the same original information ledger for a given fit/scoring context. Rebuild rich-history slots/windows, categorical phase history, residual baseline and persistence from this ledger, enforcing source availability, the existing origin cutoff, strict target self-exclusion and exclusion of the target source family. No-history remains missing and triggers the approved same-bundle direct fallback for residual prediction.

Applying this rule changes some original-row historical inputs relative to v2; regenerate both comparison branches consistently. Keeping v2 models fixed would not be a fair control. A raw historical row that fails distribution QC may still be eligible for phase persistence under the existing separate valid-phase rule; preserve the distinction.

## 5. Per-context fitting and report isolation

For a scoring context, identify its target source families before constructing fitting/calibration pools. Remove all their copies from those label pools and from history inputs that would expose the held-out assessment. Each training feature row additionally excludes its own target assessment. Fit-context exclusions must follow OOF/calibration dependencies: an OOF prediction used to fit the scoring context's mapping cannot have been trained with that context's held-out source labels. A cached feature/OOF matrix is reusable only if its exclusion set, branch, cutoff, schema and source identities match.

For a fit origin O, both recipient training target month and original source available-at must obey O; for inner target v also enforce target<v. Both the source-original year and the recipient target year must lie in that fold's candidate training years. This prevents a report first observed in an outer test year from entering training by backfilling an earlier target year. Earlier test-year original reports may update allowed feature histories for later origins, as before, but are never added to that fold's fitting/selection/calibration labels. Own-target/report exclusions still apply.

Keep evaluation keys fixed when report isolation reduces fitting support. Mark unsupported contexts and reasons; do not discard difficult evaluation rows or leak their source reports back into fitting. Shared per-month fits may exclude the union of that month's scoring families; apply the same grouping to both branches and disclose the resulting support. Report isolation is metadata-based, not outcome-value-based.

## 6. Row weights and inherited model contract

Every eligible original or copied month is a training row. Retain the v2 model decay weight `0.5**((fit_origin-target_month)/24)` per row, with nonnegative age; original availability is a separate eligibility condition. Do not divide by descendants or source-report count. Calibration fitting and validation/evaluation use equal row weights, as in v2. A longer covered interval therefore intentionally has greater summed influence when its copies are eligible. Save counts and summed model/calibration weights by original source to verify this treatment.

Reuse the q3 optimization's six frozen XGBoost bundles, squared-error loss and runtime, direct/residual alternatives for D, branch-specific calibration from none/shift/isotonic, final [0,1] share bounds, raw prediction retention, and strict final-q3 RMSE selection with AUC for numerical ties. Equal candidate budgets mean equal alternatives, not artificially equal training-row counts. Each original/augmented branch selects independently on its own allowed training-period label pool; neither uses outer-test outcomes.

D-selected is a validation-selected view, never the best-performing outer-test view. q2/q4/q5 remain direct regressors for legacy diagnostics. Residual target is q3 minus the latest permitted distinct-report q3; no-history uses the same-bundle direct model and its own calibration mapping under the inherited protocol. Report direct, residual and selected for both branches even when outcomes are unfavorable.

## 7. Calibration/selection rounds — approved in grill G1

Counting the latest three *copied months* can select three copies of the same assessment. G1 approves using the latest three eligible distinct original-report observation months as chronological scoring rounds, minimum two supported rounds, then scoring each branch's eligible target rows belonging to those reports (original-only for original, original+copies for augmented). Limit all targets/source availability to the allowed training window and outer cutoff. Existing strict row/date/report exclusions still apply inside each round. Keep round dates and member source families explicit; copies never establish another round. Freeze round support before candidate scores, not separately for favorable model outcomes; a candidate lacking support on frozen scoring keys is unsupported rather than scored on fewer rows.

For a scoring target v with origin O_v, calibration uses OOF predictions from up to three earlier eligible original-report rounds, minimum two, satisfying c<v, recipient c<=O_v and source availability<=O_v. Purge the scoring families from mapping labels and every base fit that produced those calibration predictions. A copied month does not satisfy the minimum independent-round count. Fit shift/isotonic on all remaining branch-specific monthly rows without report balancing. Require adequate mapping support on every frozen scoring key; otherwise the candidate is unavailable, not scored on a smaller subset. None needs no fitted mapping.

Pool squared errors over the scoring rows; do not average report R2 or equalize report weights. The grouping prevents copied-month leakage and false support counts; it does not undo the user's intentional monthly weighting. Exact deterministic handling of concurrent analyses is tied to the frozen source-group ledger. Final refits use the selected recipe and a mapping refitted on eligible earlier OOF rounds under the outer scoring exclusions.

H3/H6/H12 inherit each branch's H0 recipe and only refit. Because expanded target months add jobs, create the H0 recipe/job references for the expanded evaluation calendar in both branches, reusing only identical contexts. No long-horizon search or relaxation of model/calibration report exclusions. Disclose later recipe-selection labels as previously approved.

## 8. Monthly X recovery

Use the same full monthly deep-feature artifact, fixed static schema and neighbor definitions for both branches. Recover H0/H3/H6 scope features through the upstream multi-scope logic with the full monthly baseline, not its filtered fs3 input. Keep full monthly continuity for row-shift/rolling calculations and requisite pre2022 history. Slice to Somalia/model dates only after ensuring source continuity and fixed spatial features. Do not rebuild a different neighbor graph for each label branch.

Verify existing non-label feature values/order on old keys against the v2 inputs, allowing only explicitly identified necessary history reconstruction. D's V2 season join and permitted original-weather oracle offsets retain their existing rules; missing verified weather still limits primary long-horizon support. Do not confuse target-corrected columns inside deep features with the raw label authority.

Current reusable boundaries: `pipeline.prepare` label/history join, `data.build_label_ledger`, `history.build_history_block`, `q3opt` OOF/calibration/selection, and `q3eval` metrics/paired comparisons. Upstream full deep file and `build_multiscope_ipcch_features.py` are described in `research.md`. Prefer a task-local adapter using these definitions; do not overwrite external raw or upstream shared artifacts or introduce a new framework. Implementation layout follows after spec agreement.

## 9. Evaluation, baselines and evidence

Primary table: per test year/horizon, common expanded truth and all six original/augmented D views, final/raw q3 R2, RMSE, bias, continuous-score crisis AUC, binary F1/recall at final q3>=.2, row count, area count and original-report count. Labels are monthly values inherited within validity, not independently measured monthly outcomes. Show original versus added coverage and headline augmented-minus-original contrasts for matching D views.

Secondary table repeats on original observed-label keys; optional added-only diagnostics explain the main result. Recompute share persistence from permitted distinct original reports excluding the target assessment; use identical baseline predictions across branches on the same contexts, with explicit missing support. Report phase persistence for its classification interpretation separately if retained by q3eval. All-crisis predicts positive for binary metrics only; R2/RMSE is not applicable. Do not compare a full-cohort model with a subset-only persistence score without rescoring the model on that subset.

Retain existing area-cluster paired bootstrap machinery for within-year/horizon q3 R2/RMSE and crisis-AUC contrasts:2000 PCG64(42) draws, ascending canonical numeric area IDs, resample N areas with replacement and retain all their months with shared multiplicities for the paired methods. Use95% percentile intervals with linear interpolation. No refits. Retain draws, undefined counts and reasons; an undefined point metric, fewer than two areas or any undefined paired draw makes that metric's interval unavailable, without suppressing other computable metrics. Shared report/month dependence, including one source mapped to multiple areas, is not fully accounted for by area resampling and must be disclosed. Do not label expanded row counts as independent sample counts. Report empty/unsupported cells and source gaps, including raw covariate cutoff, without turning unavailable into a pass or promising improvement.

Save source/config/runtime hashes; correspondence and conflict ledger; original/augmented labels with raw/normalized values, source families, availability and provenance; X schema/parity evidence; per-context purges/history sources and fitting weights; OOF and calibration dependency ledgers; selections; raw/final predictions; common scoring keys, baselines and replayed metrics. Reuse current CSV.gz/JSON/model conventions with a separate output root and no overwrite of v1/v2.

## 10. Execution gates and later checks

1. Mapping gate: independently defensible validity links and nonzero eligible additions, with no unresolved conflict promoted to a match. Missing old geometry/crosswalk evidence remains a real current limitation.
2. Data gate: original labels/covariates unchanged; unique recipient keys; approved bounds/overlap; complete source family and availability lineage for every added row; no unrequested partial filling.
3. Feature gate: full monthly source continuity and non-label parity on old keys; categorical/rich histories rebuilt with report exclusions.
4. Split gate: original/augmented label pools correct; no scoring source family in fitting/calibration dependency paths; no availability leak; report rounds and row weights match the chosen contract.
5. Model/report gate: equal search inventories, no outer-score selection, main expanded and secondary restricted matched-key results, requested baselines and independent replay. No performance threshold is promised.

All gates above describe later implementation checks; none has passed merely because this spec exists. G1-G2 are resolved; stay planning until consolidated final technical acceptance, then prepare an implementation plan/context manifests and follow the enrolled Claude audit-start lifecycle. Do not mutate or close the previous q3 task as part of this new planning work.
