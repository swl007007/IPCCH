# Spec grill — validity-period label augmentation

Status: G1-G2 approved; consolidated spec v0.2 awaits final technical review. No implementation or training authorized. Approved requirements R1-R15 are in prd.md; remaining detailed mechanics in design.md await final acceptance.

## G1 — Three copied months are not three independent reporting rounds

Fact: the current q3 pipeline uses its latest three labeled months for selection and up to three earlier OOF months for calibration. A validity period Jan-Mar creates three labeled months from one original report. Keeping that count unchanged can exhaust calibration/scoring support after the approved same-report exclusions or misleadingly count copied months as new reporting rounds.

Question: count the latest three distinct original-report observation months as selection/calibration rounds, while retaining every eligible copied monthly row and its full row weight inside those rounds?

Recommendation: adopt design section7, minimum two supported distinct rounds. Keep normal per-row RMSE/calibration weights, so longer-validity reports retain the extra influence the user requested. Cost: eligible rounds can reach farther back in time than a three-calendar-month tail; disclose the dates and support. Do not weaken same-report isolation to obtain more nominal months.

Decision: approved ("采用"). Latest three distinct original-report months, minimum two supported rounds; retain copied monthly rows and normal row weights within each round. PRD R14 and design section7 record the decision.

## G2 — A partially populated label is not an empty label block

Question: fill only recipients where overall_phase and all five phase percentages are missing, leaving partially populated or invalid original labels intact and listed for diagnosis?

Recommendation: adopt the whole-block rule in design section3. Copy all six fields from one verified original source into a genuinely empty month. Do not combine an existing overall_phase with another report's percentages, or fill individual missing phases piecemeal. This maintains the approved augmentation-only/raw-value-preservation boundary. Trade-off: some partly missing records remain unusable for q3 training, and will need a separate correction decision if desired.

Decision: approved ("采用"). Only fully missing six-field recipients may be filled with a complete single-source label. Partial/invalid existing labels remain unchanged. Recorded in PRD R15 and design section3. A subsequent read-only raw scan found zero partial six-field blocks for Somalia2022-26; no labels were modified.

## Grill closure

The scientific choices raised during brainstorming and both written-spec grill questions are resolved. Final technical review covers inclusive-month endpoints, source-family provenance/grouping, fit-context mechanics and inherited paired uncertainty calculations. Mapping coverage and full-month feature parity are explicitly unverified execution gates. If no defensible links produce additions, stop with augmentation_unavailable; do not silently weaken matching or claim a successful expanded experiment.

Final acceptance is pending; no implement.md or model execution is authorized by this closure note.

## G3 — Mapping evidence without an area-level crosswalk (Claude, 2026-09-25)

Fact (research.md, Claude preflight): no area/report crosswalk exists; raw labels were attached by nearest centroid with match metadata discarded. For each raw 2022–2024 label month, exactly one Somalia current analysis in the May-15 snapshot starts that month and each analysis has one (from,to) window. 2025-04/09/10 have no current analysis starting that month (projection-derived); 2025-07's 64 rows are cross-border spillovers.

Question: accept the round-level link (raw month equals the start of the unique current analysis) as the defensible report/period evidence required by R7/design section 2, filling blank months inside that analysis window?

Decision: approved ("Accept round-level link (Recommended)"). Link only rounds with a unique current analysis starting in the raw label month; exclude 2025-07 (spillover) and 2025-04/09/10 (no current round). Source family = anl_id. Label values stay raw. Outer 2025/2026 evaluation months receive no added labels, so this becomes training-label augmentation with an unchanged evaluation set; the "expanded evaluation cohort" of R1/R13 equals the original cohort for this round.
