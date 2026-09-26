# Written-spec grill — q3-first optimization

Status: G1-G5 resolved; final technical review accepted 2026-09-25; implementation authorized per implement.md. User-approved requirements are in PRD R1-R15; remaining technical defaults are presented in design.md.

## G1 — A recipe chosen later can leak into a longer-horizon forecast

Fact: the earliest test2025 H12 origin is April2024. A recipe chosen using all 2022-2024 labels would include information after that origin even if the receiving model itself were refitted only on earlier labels. Hyperparameter/formulation/calibration selection is part of the information cutoff.

Question: use origin-matched H0 development selections, each restricted to the receiving origin's available training labels, then freeze the resulting recipe for H3/H6/H12 refitting without using their scores for selection?

Recommendation: adopt design section5. This retains H0-only optimization and avoids borrowing later choices. Cost: additional H0 selections at early origins; reuse identical cutoffs. A single earliest-origin recipe is cheaper but constrains later H0 optimization to older selection evidence.

Decision: rejected. User prioritizes 2025/2026 nowcasting performance and explicitly permits later-selected H0 recipes for ancillary long horizons, but forbids tuning against long-horizon performance. Remove extra origin-matched H0 selection. Disclose long-horizon recipe-selection leakage. Keep receiving model and calibration fit cutoffs unchanged; broader leakage has not been inferred. Proposed recipe mapping is corresponding fold/target/arm H0, as written in design section5.

## G2 — Does permission include selecting on nowcasting evaluation labels?

Ambiguity: later labels can mean labels inside the permitted H0 training window but after the long-horizon origin, or the 2025/2026 evaluation labels themselves. G1 resolves the former. It does not unambiguously authorize the latter.

Recommendation: keep H0 candidate selection/calibration inside temporal training validation; permit later-than-long-origin recipe selection for ancillary horizons. If the user instead wants to select recipes by their 2025/2026 scores, explicitly redefine those years as development/selection cohorts and avoid independent-test or out-of-sample-performance claims. No such choice licenses direct target self-use in predictors.

Question: may the 2025/2026 nowcasting evaluation scores themselves determine which model/calibration recipe is selected, or do those labels remain evaluation-only?

Decision: user adopted the recommendation ("采用"): keep H0 training-period temporal selection; do not select models/calibration using that fold's 2025/2026 evaluation scores. G1 remains the explicit ancillary-horizon exception. The approved 2026 training window still contains 2025 labels. Prior inspection of the evaluation years remains disclosed.

## G3 — Bound calibration complexity and permit no learned correction

Question: restrict this round to no learned calibration, mean-bias shift, and isotonic, selected by held-out chronological q3 RMSE?

Recommendation: adopt these three existing methods. Shift directly addresses the observed upward mean bias; isotonic permits nonlinear correction but can overfit sparse historical distributions; no calibration protects against nontransferable corrections. Retain raw scores and require held-out evaluation for method choice. Do not add calibration families or enlarge the search after seeing outer outcomes. The proposed common [0,1] final bound is a separate fixed physical constraint, not a learned mapping; no-calibration means no learned correction.

Decision: approved ("采用"). Exactly three calibration candidates; final share bound [0,1]; preserve raw predictions and metrics. Recorded in PRD R13 and design section4. No additional calibration family or post-test search expansion is implied.

## G4 — Secondary crisis decisions should refer to the optimized q3 output

Fact: four independently predicted cumulative shares can be nonmonotone. The existing descending q5-to-q2 ordinal rule can label crisis even when the q3 score is below .2. Optimizing q3 alone does not necessarily improve that separate ordinal decision.

Question: define secondary crisis F1/recall from final q3>=.2 against reported phase>=3, keep the legacy ordinal metrics separately, and do not tune a new decision threshold this round?

Recommendation: adopt this fixed q3 rule to align secondary decision metrics with the main output. It is a modeling threshold, not an assertion that area-level reported phase is determined solely by population share. Preserve the legacy phase metrics for comparability, clearly distinguished. Trade-off: binary F1/recall are monitored but not maximized by threshold search and may decline while share RMSE improves. AUC remains a continuous-score metric.

Decision: approved ("采用"). Final q3>=.2 defines secondary binary predictions, reported phase>=3 remains truth, legacy phase metrics are separate, and no new threshold tuning is allowed. Recorded in PRD R14 and design section6.

## G5 — Strict q3 priority versus an AUC trade-off

Question: retain strict minimum held-out q3 RMSE selection even when a competing model has higher crisis AUC, using AUC only to break numerical RMSE ties?

Recommendation: retain strict priority, consistent with q3 as the main outcome. The design's proposed tolerance 1e-12 in share units is numerical equality, not a practical allowance for worse RMSE. AUC remains a reported secondary outcome and a tie-break; no minimum AUC constraint or weighted composite is implied. Example: validation RMSE 10.0 percentage points/AUC .70 beats RMSE 10.2 points/AUC .78. An alternative would require a user-approved RMSE sacrifice or AUC floor before looking at outer scores.

Decision: approved ("采用"). Strict minimum held-out final-q3 RMSE; AUC only breaks numerical ties. Recorded in PRD R15 and design section4. No practical RMSE-sacrifice tolerance, AUC floor or weighted metric composite.

## Grill closure and final technical review

All five questions have decisions. The consolidated design records pooled error aggregation, chronological calibration, missing-history branches, raw/final score separation, fixed binary threshold, inspected-test interpretation and sparse/empty long-horizon coverage. No additional scientific question is being opened here.

Final review covers the bounded six-bundle search/squared-error loss, latest-three scoring/calibration months and minimum-two support, deterministic numeric ties, same-fold/target H0 recipe transfer, and the proposed 2,000-draw paired q3/AUC uncertainty reports. These technical details were not individually approved by answering G5. Final spec acceptance remains pending; implementation planning and execution are later steps.

## Final acceptance

Final technical acceptance recorded 2026-09-25 (user, via Claude session): design.md v0.2 defaults accepted in full (six X1–X6 bundles/squared error; latest-three scoring and calibration months with minimum two; 1e-12 tie set then AUC, none<shift<isotonic, bundle order, direct<residual; same fold/target/arm H0 recipe transfer; 2,000-draw paired q3/AUC bootstrap). implement.md v0.1 approved, including once-per-fold H0 selection reuse (with identical-pool assertion) and q3-only OOF fitting. Claude executes the full training run.
