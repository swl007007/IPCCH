# Technical specification — q3-first Somalia optimization

Version 0.2 — 2026-09-25. Status: G1-G5 incorporated; final technical acceptance recorded 2026-09-25. Validation: no new model fits or implementation checks executed. User-approved requirements are R1-R15 in `prd.md`; the remaining numerical defaults and mechanics below are concrete proposals for final review.

## 1. Experiment and interpretation

Keep Somalia only and the prior normalized share targets, ideal availability assumptions and temporal feature rules. Candidate supervised target years remain 2022-2024 for test2025 and 2023-2025 for test2026, additionally clipped to each fit origin. Earlier test-year records may update permitted histories but never enter that fold's fitting, tuning or calibration labels. Missing seasons/history stay missing. Actual 2026 coverage remains partial.

Optimize H0 only. H3/H6/H12 retrain and report, using the corresponding H0-selected recipe even when recipe-selection labels postdate their origins, as explicitly allowed in G1. Never use long-horizon validation or test scores to choose a recipe. Label those results ancillary retrospective transfers with possible selection leakage, not fully origin-valid forecasts. Preserve v1 artifacts and data-gap disclosures. The previously inspected test years provide retrospective iterative evidence, not a newly untouched test. Existing source-lineage waivers do not establish verified oracle months or repair the H3/H6 2026 empty primary cohorts. G2 confirms H0 training-only temporal selection: a fold's own evaluation outcomes cannot select its configuration or calibration. This does not remove 2025 labels from the approved 2026-fold training window.

Use the same primary comparison keys as v1 when sources are unchanged, retaining wider-cohort/exclusion counts. A changed source/cohort requires a separately identified run and matched-key comparison, not silent replacement. Compare specifications only within year/horizon; no horizon-ranking or cross-horizon superiority score.

## 2. Models and comparisons

| Procedure | Information set | q3 target |
|---|---|---|
| A-direct | Existing temporally valid predictors | q3 |
| B-direct | A plus V2 means | q3 |
| C-direct | B plus permitted realized future weather | q3 |
| D-direct | C plus existing rich history | q3 |
| D-residual | Same D information set | q3 minus latest eligible historical q3 |

D is the main specification. A-C are baselines; they do not receive historical q3 through reconstruction. At H0 B=C, so reuse their identical fits and predictions. Retain four cumulative-regression outputs q2/q3/q4/q5; only q3 gets a residual alternative. q2/q4/q5 remain direct-share regressions with the selected bundle's common settings, used for legacy ordinal diagnostics rather than primary selection.

For a D-residual row, b is `hist_q3_obs1` from its own latest valid distribution at U<=O,U<T; source identity is `history_obs1_source_ord`. Train delta=q3-b only on baseline-supported fitting rows; predict raw q3=b+delta_hat. A residual-training set with no supported rows is unsupported, not a constant-zero residual. A truly constant finite residual target may use the existing recorded constant predictor.

For no-history prediction rows, use a D-direct q3 model fitted with the same bundle on the full eligible fitting pool. Reuse those fits/OOF predictions from the D-direct candidate evaluation. A residual candidate declares one calibration method shared by its two branches, with separately fitted mapping parameters. Baseline-supported rows use the residual branch's mapping fitted on supported reconstructed-q3 OOF predictions; no-history rows use the direct model and its mapping fitted on direct OOF predictions. This fallback is not necessarily the separately selected D-direct winner. Missing history receives neither a fabricated b nor a residual mapping. Record branch, baseline source, and model/calibration identities for every row. Evaluate the same branch rule during selection and outer prediction.

Report D-direct and D-residual separately. Also produce D-selected by taking the best eligible formulation/bundle/calibration combination using H0 validation only; this is a selected view, not another fit. The main feature-ablation comparison remains A/B/C/D-direct under identical direct-target budgets. D-selected versus baselines includes formulation selection and must be described that way. D-residual versus D-direct uses identical D information but different residual fitting support; disclose support counts rather than claiming a pure algebraic reparameterization with identical training rows.

## 3. Bounded search and loss

Reuse the six X1-X6 scientific bundles in `configs/somalia_oracle_candidates.json`, including their common/q3 overrides. Do not edit that v1 file in place. Pin the existing values/hash in the implementation artifact manifest. This round retains `reg:squarederror`, 24-month origin-referenced training decay, seed42, CPU hist and one model thread. No new custom loss, ranking objective, random search, early stopping or post-test search expansion.

| Bundle | Depth common/q3 | Trees | Learning rate | Min child weight |
|---|---|---:|---:|---:|
| X1 | 3/3 | 200 | .05 | 5 |
| X2 | 5/5 | 200 | .05 | 5 |
| X3 | 5/5 | 500 | .05 | 5 |
| X4 | 7/7 | 200 | .05 | 5 |
| X5 | 7/7 | 500 | .05 | 5 |
| X6 | 11/9 | 200 | .10 | 0 |

Common/q3 subsample=1/.5, column subsample=.5/.7, gamma=0/.1. Direct A-D each get six bundles and three q3 calibration options. D additionally gets the same six bundles/options for residual q3. There are no extra A-C target formulations. Calibration candidates reuse the same underlying raw predictions; they do not trigger duplicate XGBoost fits. Existing six bundles are a bounded starting inventory, not proof that they are optimal for q3.

Squared error applies to the original share scale. For fixed b, residual squared error equals reconstructed-share squared error. Training weights remain the existing decay weights, whereas validation/scoring rows are unweighted, matching the reported row-level target. Report that difference; do not call the training objective numerically identical to unweighted test R2.

## 4. H0 temporal calibration and selection

For outer candidate window W and recipe cutoff C, generate chronological H0 OOF predictions at eligible target months v<=C in W. Each OOF model uses only training targets u in W with u<v; row features obey their own origins. Fit preprocessing, if any, uses that fitting pool only. A prediction and its label at v never enter the model that produced that prediction.

Freeze the latest three target months with scorable truth and nonempty base fitting pools as scoring months, before candidate scores are seen. Require at least two supported scoring months. The q3 scoring cohort is fixed across candidates; do not drop a row because a candidate fails or has an extreme prediction. A method/formulation lacking required fit or mapping support on any of those scoring keys is unsupported on the whole comparison, not scored on a favorable smaller subset. The identity method needs no calibration support, but must score the same keys. Missing crisis classes do not block q3 error evaluation. Constant-truth months contribute squared error normally; their individual R2/AUC may be undefined.

For each scoring month v, fit its calibration mapping on the same candidate's earlier eligible OOF predictions with target c<v. Use the latest three eligible calibration target months, with at least two required for a fitted mapping. Calibration labels must be available at the scoring origin as well; at H0 this is satisfied by c<v. Apply the fitted mapping only to held-out scoring predictions. For residual calibration, require this support on its baseline-supported branch; the direct fallback has its own supported direct calibration fit. Do not fit a mapping and evaluate its selection score on the same calibration rows.

G3-approved q3 calibration inventory (detailed support mechanics remain for final technical review):

1. None: identity on raw reconstructed/direct q3, followed by the common final range bound below. No learned mapping.
2. Shift: subtract the mean raw prediction-minus-truth error on eligible calibration rows, then bound to [0,1].
3. Isotonic: reuse sklearn's increasing least-squares mapping with output bounds [0,1] and clipped extrapolation. Require at least two distinct calibration input scores; otherwise mark this candidate unsupported rather than silently switching methods. Constant calibration truth may legitimately yield a constant mapping.

All calibration fitting uses equal row weights in q3 units. A final [0,1] bound is a fixed physical-range constraint, not an estimated correction: preserve the unbounded raw q3 and counts affected by bounding. The none option means no learned mapping, not a promise of an unbounded final share. Do not clip residual delta itself; reconstruct q3 first. Keep raw and final score columns distinct. q2/q4/q5 remain uncalibrated diagnostics this round; do not silently add cross-target monotonic projection.

G5 fixes strict priority: pool held-out scoring-row squared errors and minimize final-q3 RMSE. Do not average monthly R2 or give a four-row month the same total weight as a 904-row month. With identical rows/weights this selects the highest pooled R2. Find the global minimum eligible RMSE first, then restrict tie-breaking to candidates within 1e-12 of that minimum in share units. Among that fixed tie set, prefer higher pooled final-score crisis ROC AUC when defined on the full fixed classification subset; then no calibration, shift, isotonic; then earlier bundle; then direct over residual for a remaining formulation tie. If pooled truth has one class, skip the AUC tie-break for all candidates. This deterministic rule cannot accumulate pairwise tolerance drift or trade a substantive RMSE loss for AUC.

After selection, fit the chosen base procedure on the full outer eligible pool. Refit the selected q3 mapping using its latest three eligible OOF calibration target months (at least two), all available by the outer cutoff and excluding the outer test year. Earlier scoring months may now be calibration training data; their earlier held-out scores must not be replaced by in-sample fitted values. The selected OOF score is a development selection estimate, not a fresh unbiased performance result.

## 5. H3/H6/H12 ancillary recipe transfer — grill G1 decision

The user rejected extra origin-matched H0 selections. Prioritize nowcasting performance on 2025/2026; receiving H3/H6/H12 jobs may use the corresponding H0 recipe despite later selection labels. Proposed deterministic mapping: same test fold, target month, arm/formulation, using that H0 job's selected recipe. No additional H0 selections at earlier long-horizon origins. If the matching H0 recipe is unavailable, report the dependent cell unavailable rather than select using long-horizon scores.

For each arm/formulation, freeze the bundle and calibration method from that H0 recipe, then fit the receiving horizon's models on its own origin-eligible rows/features. C inherits the H0 B/C recipe even though future-weather columns are present at H>0. D-selected inherits the formulation selected at H0, not whichever long-horizon formulation scores best. Still report D-direct and D-residual, each with its H0-selected recipe. Record recipe-selection maximum label date, receiving origin and whether selection used later labels; do not conceal the permitted leakage.

Generate OOF predictions for the fixed receiving-horizon procedure solely to refit its fixed calibration mapping. At OOF target v, model labels must obey u<=v-H and u<v. For the final mapping, calibration labels must be <=outer O and remain in the fold's training years. Use the same latest-three/minimum-two calibration-month rule. No H>0 calibration-method search, threshold search or model selection. If the fixed method cannot be fitted with adequate support, mark the final calibrated cell unavailable and retain raw predictions as explicitly labeled diagnostics; do not silently replace the chosen method.

H12 lacks enough early months for a nested calibration *search*, but no such search is required here. Its fixed final mapping may use the eligible OOF labels available at outer O. Do not mistakenly demand a separate H12 method-selection score. Empty verified-oracle cohorts remain unavailable, including current 2026 H3/H6 primary cells.

The G1 exception concerns recipe transfer only. It does not expand receiving-horizon base-model/calibration-fitting labels or authorize tuning against long-horizon performance. G2 confirms that H0 recipes themselves are selected within the respective training window, without that fold's evaluation outcomes.

## 6. Reporting and secondary metrics

Headline: D-selected nowcasting q3 R2, RMSE, MAE and signed mean error; show D-direct, D-residual, calibrated-v1 D and share persistence alongside it on matched keys. Record raw versus final metrics, support, source months, fallback counts and clipping counts. Show means of truth/prediction so a positive R2 cannot hide systematic level bias. H3/H6/H12 use secondary report panels without performance ranking across horizons.

Primary crisis discrimination is pooled ROC AUC against reported phase>=3, calculated separately for raw and final q3. Also report within-month AUC with its established equal-month convention, excluding undefined single-class months with explicit counts. Do not label it as pooled AUC or select which version to emphasize after seeing outcomes. One-class pooled truth makes AUC unavailable without invalidating regression error.

G4-approved secondary decision metrics: binary crisis F1/recall/precision from final q3>=0.2, with full precision, against reported overall_phase>=3. Keep the existing descending q5-to-q2 phase reconstruction as a separate legacy ordinal diagnostic. The q3-only crisis threshold can disagree with phase>=3 from nonmonotone cumulative outputs; report disagreement counts and do not interchange these decisions. No threshold optimization this round. Multiclass macro-F1 and phase accuracy remain diagnostics, distinct from binary crisis F1. Report any F1/recall decline even if q3 error improves; the threshold does not assert that reported phase is defined solely by this population share.

Share persistence carries the latest eligible valid-history q3. Phase persistence carries the latest eligible reported phase. They may have different source rows/support; evaluate each on its own matched subset and recompute the model metrics there. Include always-crisis for binary F1/recall context. Never assign it an artificial population-share prediction or meaningful discrimination claim.

Proposed uncertainty: reuse area-cluster paired bootstrap, 2,000 PCG64(42) draws, exact cohort keys and shared area multiplicities, for within-year/horizon delta q3 R2/RMSE and final-score AUC. Prioritize D-direct versus v1-D, D-residual versus D-direct, and D-selected versus share persistence. AUC uses share-persistence scores on the valid-history subset, not the binary phase baseline mislabeled as a continuous score. Sort canonical numeric area IDs; sample N areas with replacement, retaining all their cohort months with sampled multiplicities. Compute metrics from pooled weighted rows per draw. Report 2.5th/97.5th percentiles with linear interpolation and retain draws for replay. If there are fewer than two areas, an undefined point metric, or any undefined paired draw, mark that metric's interval unavailable with the reason and counts; do not suppress other computable metrics, redraw, or silently discard replicates. These intervals condition on saved predictions, exclude refitting/selection uncertainty and do not establish future-year gains or correct all spatial dependence. This extension from v1 F2 intervals to q3/AUC remains part of final technical review.

## 7. Minimal reuse, evidence and checks

Reuse `src/ipcch/somalia_oracle/{data,history,pipeline,modeling,evaluation}.py`, current runner/result conventions and calibration arithmetic. Keep v1 configs/reports untouched. No new training framework, classifier, experiment database, or sibling-repo edits. Retain XGBoost environment recorded in `research.md`; pin actual source/config/input/runtime identities before execution.

Evidence must retain existing ledgers/models/predictions plus: candidate formulation and fallback identity; baseline source/value; base OOF fit cutoff; calibration fit keys/dates/method; held-out scoring keys and final predictions; selected recipe and its information cutoff; receiving horizon; raw/final q3; raw/final crisis AUC; reporting cohorts and bootstrap draws. CSV.gz, JSON and existing model formats suffice.

Later implementation checks must cover: residual reconstruction and missing-history fallback; H0 target exclusion; OOF/calibration chronology; correct H0 recipe transfer with explicit later-label selection flags and origin-valid receiving model/calibration fits; constant targets/truth and undefined AUC; equal scoring keys and RMSE selection; raw/final bounds and threshold boundaries; no silent calibration fallback; B=C identity at H0; immutable v1 artifacts; replayable paired comparisons. Feasibility evidence in `research.md` is not a test pass or a promise of improved metrics.

## 8. Lifecycle

All five grill questions are resolved; stay planning until consolidated final technical acceptance. `implement.md` and execution manifests follow that spec agreement. No training, source changes, task start or audit close is authorized here. Before later implementation, follow enrolled repository rules: verify the actual Claude executor/controller, commit approved planning artifacts, and use the audit wrapper with the exact registered path. A historical setup or prior task audit is not an audit verdict for this task.
