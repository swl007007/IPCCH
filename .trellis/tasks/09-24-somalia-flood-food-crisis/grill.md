# Spec grill log

Status: G1–G6 resolved; spec v1.1 accepted 2026-09-24 (session goal). Implementation follows implement.md.

## G1 — A good F2 comparison is not necessarily useful beyond persistence

Question: Should reporting include an unfitted, as-of-origin persistence reference (carry the latest valid historical observed phase forward), in addition to A–D, to expose whether the enhanced model beats simply retaining the last observed state?

Recommendation: include it as a reporting reference, not a fifth tuned model arm. Apply U<=O and U<T; compare on the explicit subset with available prior reported phase, report its coverage, and never fabricate no-history predictions. This does not change A–D's main common cohort. A–D versus persistence comparisons must be on identical supported keys.

Decision: approved. User: "增加，好问题。这个baseline很重要。" Added to PRD R1/AC7b and design section 7 with explicit phase-only prediction and common-support reporting.

## G2 — F2 can be high for an always-crisis prediction

Question: Add an always-predict-Phase-3+ diagnostic reference so high crisis prevalence cannot be mistaken for discriminative performance?

Recommendation: report its binary confusion counts and metrics on the same evaluation cohorts, without training, tuning or selecting it as a model. If crisis prevalence is p, its F2 is 5p/(1+4p); for a hypothetical p=.8 it is about .952. This is not a claim about measured Somalia prevalence. It has no specific ordinal-phase or population-share prediction.

Decision: approved. Added the always-crisis binary diagnostic to PRD R1/AC7c and design section 7; primary selection remains F2.

## G3 — Rounding before phase conversion changes the effective threshold

Fact: `scripts/modeling/run_deep_feature_weight_decay_forecasting.py:283,290-294` rounds predicted cumulative shares to two decimals before comparing with the fixed .2 phase threshold. For example, .196 becomes .20 and crosses the threshold despite the original estimate being below .2.

Question: Use full-precision predictions for the .2 threshold and round only displayed values?

Recommendation: yes, consistently in inner selection and outer scoring for all A–D arms. Preserve the descending phase conversion convention, >= equality and fixed .2 threshold. Save raw predictions; display rounding must not affect decisions or metrics.

Decision: approved. User: "采用". PRD R6 and design section 7 now require full-precision thresholding and scoring. This explicitly changes the old runner's round-before-threshold behavior.

## G4 — Impossible population-share outcomes

Fact: the canonical raw source has 23 April2026 Somalia records with P2+P3+P4+P5=1.10–1.20. The main agent independently checked area1981/2026-04: P1=.15,P2=.25,P3=.60,P4=.25,P5=0; full sum1.25. Source details and the separate temporal-validation support screen are in `research.md`.

Question: Until verified source corrections exist, exclude these demonstrably invalid distributions from supervised fitting/scoring and percentage-history construction, retaining raw records and exclusion reasons rather than forcing them to sum to one?

Original recommendation: exclude pending source correction. Superseded by the user's decision below.

Decision: user explicitly directs proportional normalization to 100% ("直接按100%做比例归一化就可以了"). Normalize finite nonnegative positive-sum vectors before cumulative targets and percentage histories; preserve raw evidence and reported phase. Remove the prior sum-range exclusion. PRD R1/R5/AC1b and design sections 2/5 now implement this specification decision. No source file or model dataset has yet been changed.

## G5 — Horizon comparisons may change the sample as well as lead time

Fact: the approved primary common cohort is defined within year/horizon, while weather and feature availability may differ across H=0/3/6/12. Therefore a difference between horizon-level F2s need not be solely a forecasting-lead-time difference.

Question: Also report A–D results across horizons on the intersection of available `(area_id,target_month)` keys for all four horizons, reusing saved predictions without extra training?

Recommendation: yes. Keep each horizon's main coverage/results; add a clearly labeled same-sample horizon comparison with counts. If the four-horizon intersection is empty or insufficient, mark that comparison unavailable rather than silently relaxing it. Persistence comparisons additionally require persistence availability on the corresponding common keys.

Decision: rejected. User: "不用，关键是不同specification间的比较，horizon间本身不可比。" Do not add a cross-horizon common-cohort table or rank horizons. Compare specifications/baselines only within each test year/horizon on matched keys. PRD R1/out-of-scope and design section 7 record the correction.

## G6 — Uncertainty of within-horizon specification gains

Question: Add paired area-cluster bootstrap intervals for within-year/within-horizon delta F2, reusing saved predictions without model refitting?

Recommendation: yes. Resample area IDs, retaining all eligible target-month rows of each sampled area and sharing multiplicities between the compared specifications. Use only the same keys for each comparison; persistence contrasts stay on their history-supported cohort. Intervals quantify conditional prediction-comparison uncertainty and do not establish future-year performance or address all spatial dependence. No cross-horizon aggregation or ranking.

Decision: approved. User: "可以". PRD R6/AC7d and design section 7 now require paired area-cluster bootstrap 95% intervals. Reproducibility details proposed for final review: 2,000 draws, seed42/PCG64, percentile intervals and explicit unavailable status for undefined draws, with no refits or cross-horizon pooling.

## Grill closure and final review

All six questions have decisions recorded above. The consolidated specification retains the conditional empirical-ceiling interpretation, valid negative/mixed outcomes, source-provenance gates, partial2026 reporting, history parity and H=0 self-exclusion. These are requirements/preflight checks, not unanswered grill questions.

Final review covers the six candidate values, latest-three-month inner validation with at least two supported months, and reproducible bootstrap details. No additional scientific question is pending. Final spec acceptance has not yet been recorded; implementation planning and execution remain separate later steps.
