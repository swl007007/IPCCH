# Somalia v4 decision log

Status: spec v1.3 approved; G1-G9 resolved, including the G8 correction and G9 acceptance. Original and augmented are distinct scenarios throughout all label roles. The user confirmed the final consolidated summary ("确认") on 2026-09-30. No individual design question remains. Planning commit and the requested other-Claude audit registration/start/controller setup are authorized; implementation, experiments and close are not.

## G1 — Candidate supervised years for five outer folds

Fact: v3 uses three preceding supervised years, not an expanding pool (`v3/design.md:16`). The new 2015-2026 climate file extends seasonal inputs but does not choose the label fitting window; the existing raw-derived ledger has no 2015/2016 labels.

Question: retain rolling three-year supervised windows for test2022-2026, or use all eligible earlier years as an expanding training pool?

Initial recommendation (not adopted): retain rolling three years for v3 comparability.

Decision: user selected B, expanding prior-year history: "B。不必拘泥于改变训练设定，也不用跟v3比较，最重要的是探究当前设定下模型可能达到的最好结果。" Use all eligible earlier raw labels through Y-1, additionally clipped by per-origin/source-availability cutoffs and report isolation. Current inspected label support implies 2017-2021→2022 through 2017-2025→2026; verify actual earliest eligible raw labels at preflight.

Objective clarification: explore best attainable performance under the current setting. V3 comparisons and preservation of its training settings for comparability are not required. Outer-test selection remains excluded; the final procedure/search budget must be explicit. All-history eligibility is separate from time-decay weights.

## G2 — Meaning of the single calibrated D procedure

Fact: v3 selects among direct/residual formulations and none/shift/isotonic calibration using training-only temporal validation; D-selected is the selected view, not a separate model fit or outer-test winner.

Recommendation: keep those alternatives inside one D selection procedure and report only the selected final D for each original/augmented setting. This avoids excluding a potentially better eligible candidate solely to simplify displayed model views. Identity/none remains available if learned calibration hurts validation performance; model/search details will be frozen before outer scoring.

Question: accept this validation-selected D definition, including identity/none as an eligible calibration choice?

Decision: approved ("接受"). Retain direct/residual and none/shift/isotonic internally, choose only with training-period temporal validation, and report the selected final D per original/augmented setting. Identity/none is explicitly eligible. Hyperparameter/weighting budget remains a separate decision.

## G3 — Replication years under expanding training

Fact: v3 config restricts augmentation targets to 2022-2026. The existing API-round ledger already includes current-period windows for 2017-2021; its 2019-2021 multi-month windows were outside that configured scope. V4's approved expanding fitting pool now includes those earlier raw observations. Source evidence: `configs/somalia_validity_augmentation.json:7` and `results/experiments/somalia_oracle/v3_validity/ledgers/api_rounds.csv:2-11`.

Recommendation at G3: extend augmentation eligibility to all available historical source years in the expanding pool, using the same verified round/validity and blank-month rules. This may add earlier monthly training rows and intentionally increases the total influence of eligible longer-validity reports. No change to raw-value authority, report isolation, availability or per-fold cutoffs. The then-assumed shared replicated test truth was later superseded by G8: only augmented includes copied test labels. Lack of valid links/covariates may leave some augmented years with no additions.

Question: extend the augmented setting's replication scope to all verifiable historical years, including the eligible 2019-2021 report windows?

Decision: approved ("接受"). Extend augmentation to all verifiable historical source years, including eligible 2019-2021 windows. Retain raw-authority, blank-recipient, availability, report-isolation and per-fold rules; copies retain ordinary per-row influence. Approval does not assert completed links or added counts, which require preflight evidence.

## G4 — Horizon-specific selection for the performance objective

Fact: v3's H3/H6/H12 inherit H0-selected recipes and permit later recipe-selection labels, while receiving base/calibration fits remain origin-clipped (`09-25-somalia-auc-r2-optimization/design.md:68-78`). The user has removed v3 comparability as a constraint and prioritizes attainable performance.

Recommendation: keep H=0,3,6,12 and let each horizon select its own calibrated D procedure using its own origin-valid training-period temporal validation. Apply the same accepted candidate inventory to both settings; do not transfer a later H0 recipe. This better targets each horizon's procedure at higher computational cost; unsupported early long-horizon selection/calibration contexts stay explicit.

Question: retain the four horizons and independently tune calibrated D for each using its own eligible training information?

Decision: approved ("采用"). H0/H3/H6/H12 each independently select their D configuration and calibration using only that origin's permitted training information. The later-H0-recipe transfer exception is superseded; declared perfect-weather and ideal label-availability assumptions remain.

## G5 — Time decay as a searched training choice

Fact: `configs/somalia_oracle_candidates.json:7-8` fixes the v3 model half-life at 24 months, referenced to each fitting origin. The same file contains the six X1-X6 tree bundles; `configs/somalia_q3_optimization.json:6-10` defines RMSE selection and formulation/calibration choices. With expanding history, a fixed decay predetermines how much the newly admitted older labels matter.

Recommendation: retain the six existing tree bundles and compare half-lives 12, 24, 48 months and no decay in training-period temporal validation. Cross these with the accepted direct/residual and none/shift/isotonic alternatives: 144 declared recipes per selection context. Calibration alternatives reuse base predictions. This expands weighting choices at higher fitting cost while keeping one final D per setting/horizon and a finite, reproducible inventory. No report-balanced weighting; original/copy rows retain their normal candidate-specific weights.

Question: include 12/24/48-month and no-decay weighting in the tuning search instead of fixing the half-life at 24 months?

Decision: approved ("采用"). Freeze the proposed search inventory: X1-X6 × half-lives {12,24,48,no decay} × {direct,residual} × {none,shift,isotonic}, 144 declared recipes per selection context. Every horizon and setting selects from that inventory using its permitted training-period temporal validation; candidate evidence and unsupported cases remain recorded.

## G6 — Weighting the pooled 2022-2026 evaluation

Fact: eligible monthly row counts differ across years, and 2026 is partial. Annual metrics, especially R2 and AUC, cannot be arithmetically averaged to obtain a pooled metric. The chosen training decay does not define evaluation weights.

Recommendation: concatenate the five annual out-of-sample prediction sets separately per horizon and setting, then give each canonical area-month row weight one (original and permitted copy alike). Recompute all pooled metrics directly. Years with more eligible rows contribute more weight; the separate annual tables and pooled year composition expose that fact. This preserves the existing per-area-month estimand and the intentional duration influence of validity copies. Equal-year scoring would answer a different question by reweighting rows within each year.

Question: use equal area-month weights for the pooled evaluation, accepting that years with more eligible rows contribute more weight?

Decision: approved ("采用"). Concatenate annual out-of-sample predictions within each horizon/setting and give each eligible canonical area-month row weight one. Under G8's corrected cohort policy, original includes observed labels only; augmented includes observed labels and permitted copies. Recompute pooled metrics directly; retain separate annual results and year composition. This does not impose the model's time-decay weights on evaluation.

## G7 — What wins when share accuracy and crisis identification disagree?

Fact: `configs/somalia_q3_optimization.json:6-8` selects minimum final-q3 RMSE, with AUC only inside a 1e-12 RMSE tie set. On the same validation rows/weights, lower RMSE gives higher R2 when defined. It does not guarantee better AUC or F1 against reported overall_phase>=3; q3 is a population share and is not identical to the reported-phase binary outcome. This priority was inherited into the draft, not separately grilled in G1-G6.

Recommendation: keep q3 RMSE/R2 as the primary objective of this q3-calibrated D experiment, with crisis AUC/F1/recall reported as secondary outcomes even if they deteriorate. This yields one predeclared winner and preserves the agreed continuous-share model target. Choosing crisis discrimination or decision quality as the main aim would require a deliberately different selector; do not switch after seeing outer results or introduce an undeclared blended score.

Question: if a candidate improves q3 RMSE/R2 but worsens crisis AUC/F1 in training-period temporal validation, should it still win under the RMSE-first rule?

Decision: approved ("确认"). Minimum held-out final-q3 RMSE remains decisive even when crisis AUC/F1 deteriorate. Retain AUC only within the declared numerical RMSE tie set; report classification deterioration transparently rather than vetoing the RMSE winner or changing objectives after outer scoring.

## G8 — Two separate scenarios, including separate test populations

Superseded premise: v1.1 treated outer truth as shared and asked whether both settings should also use shared expanded internal validation. The user rejected that premise and requested a systematic rewrite.

Authoritative correction: "错误的。我的意思是original的最终test set应该不包含validity复制月份，只有augmented/validaty的setting才包含复制月份。这两组setting不可比，但体现了两个不同的情形。这部分需要系统性重写。"

Decision: original uses original observed labels only for fitting, internal selection, calibration and final testing. Augmented/validity uses eligible originals plus verified validity copies in those roles. Validity names the augmented scenario, not a third setting. Keep selection/calibration populations setting-specific; the shared-selection proposal is rejected. This explicit correction supersedes earlier shared-test wording, including the original request and intervening draft assumptions.

Consequences: freeze cohorts independently; report annual and pooled metrics separately under each setting's label policy. Original measures performance at observed assessment months; augmented measures performance over supported validity-expanded monthly truth. Remove cross-setting matched-key/digest requirements, score deltas, paired bootstrap, ranking/significance/augmentation-effect claims and the common observed-only secondary comparison. Do not invent a replacement CI procedure. Retain each setting's own keyed alignment, full-cohort integrity and replay. Common source provenance, candidate inventory and non-label features remain reusable without making the evaluation populations comparable.

Preserved decisions: G1-G7 still govern each setting. G3 expands only augmented replication; G6 equal-area-month pooling applies within each setting's eligible rows. Original/copy composition is diagnostic, and an augmented year with no copies is disclosed without restoring a comparative estimand.

Status: corrected across PRD, design, implementation plan, candidate config, context manifests, task description and research implications; accepted in the subsequent consolidated final review.

## G9 — Incomplete support and requested pooled results

Fact: independent horizon-specific temporal selection needs at least two eligible original-report scoring rounds; learned mappings additionally need at least two earlier eligible OOF rounds under full source-family purges (`design.md` sections 5-6). Early or long-horizon support has not yet been measured. `research.md` records the old runner's clipped-raw replacement for unavailable final mappings, which the v4 draft prohibits. Identity/none is already eligible through normal selection, not an automatic repair after a chosen mapping fails.

Recommendation: retain strict availability semantics. If source/origin-eligible training support cannot produce a required selected-D final prediction, mark that setting/year/horizon incomplete and its full 2022-2026 pooled result incomplete. Keep coverage/reasons and complete annual results; do not drop failed rows, relax temporal/report isolation, transfer a later H0 recipe or silently replace a failed chosen mapping. An independently complete other setting remains reportable. Preflight should expose structural support gaps before expensive fits; implementation defects still need repair.

Trade-off: the requested output slots remain present but some may lack full-cohort final scores. Guaranteeing filled slots would require a separately specified fallback procedure or a changed evaluation population, altering the estimand/procedure rather than merely improving reporting.

Question: accept incomplete affected annual/pooled results when permitted support is insufficient, instead of forcing a score through fallback or dropping rows?

Decision: approved ("接受"). Insufficient permitted support leaves the affected setting/year/horizon's full-cohort final result and its complete 2022-2026 pooled result incomplete. Preserve coverage/reasons, complete annual results and independently complete other-setting results. Do not fill a score by row removal, temporal/report leakage or undeclared fallback. Identity/none remains a normal selection candidate. Implementation defects remain repair obligations.

## Convergence and final acceptance

The additional requested grill resolved objective priority (G7), corrected the two scenario definitions (G8), and accepted incomplete annual/pooled results where eligible support is insufficient (G9). G1-G9 are resolved, with no remaining individual design question. The consolidated final-review package now includes the corrected estimands and accepted failure behavior; do not treat approval of one question as approval of the entire latest package.

The approved final package covers selected D only, one primary cohort per setting under its own label policy, inherited raw/final share and crisis metrics, and original/copy coverage. No cross-setting comparison, common-subset secondary table, bootstrap/CI, persistence/all-crisis or ordinal headline comparison tables are included. Auxiliary q2/q4/q5 final outputs remain for pipeline compatibility and do not drive selection.

`implement.md` and curated context manifests are present. Existing code limitations are captured in `research.md`; new source/support, feature, nested dependency, fit and replay gates remain unexecuted. After the final v1.3 summary, the user replied "确认", approving the consolidated package and lifecycle setup. Perform only the authorized planning commit and verified other-Claude audit registration/start/controller setup; model implementation and experiments remain outside this session's authorization.
