# Grill-with-docs and final alignment, 2026-10-07

Status: read-only code/artifact inspection and planning-document alignment completed; G1 resolved as B and G2 as A. No scientific design choice remains open. User subsequently approved execution and Herdr Claude handoff on 2026-10-07. No implementation, tests, bootstrap draws, input build, model replay or fitting was run during this alignment check. This document is not experiment acceptance evidence.

## Scope and terminology

Applied `/home/swl007007/.codex/skills/grill-with-docs/SKILL.md`, which invokes grilling and domain-modeling. Task-relevant resolved terms are in root `CONTEXT.md`; scientific decisions remain in PRD/design, avoiding a duplicate ADR. The three-arm/seed42/six-run/B6/region3/area-bootstrap choices were already made and are not reopened.

Two independent read-only scouts checked temporal integration and regional metric/bootstrap behavior. Main session spot-checked the global F2/R² definitions, existing undefined-interval rule and training-weight formula. Source anchors below are the evidence boundary; source-wide value/hash parity and model replay remain future acceptance work.

## Alignment findings and clarifications

| Contract | Evidence | Finding |
|---|---|---|
| B past-window mean | `src/ipcch/climate2015_features.py:30,104-122,200-207,326-327,374-379` | Existing R spans O−m+1…O with the design's exact H3/H6/H12 names. Existing min_periods is 2 for m3 and 3 for m6; only new B adds full-past completeness. |
| Annual fit timing | `scripts/modeling/run_deep_feature_weight_decay_forecasting.py:989-999,1024-1026`; `src/ipcch/origin_safe.py:313-325` | Fit cutoff/origin match design. Weight age is fit_origin minus fitting target month U, not minus row origin U−H. Each row retains its own origin. Latest fitting-row oracle month U−H+min(H,6)≤U≤fit_origin. |
| Safe history gate | `src/ipcch/origin_safe.py:157-177` | Q consumes the existing latest safely reported phase; no target/current-state substitution. |
| Shared source and inherited features | `scripts/preprocessing/build_origin_safe_climate_idp_inputs.py:277-278,325-332,357-362`; `src/ipcch/climate2015_features.py:73-92` | Source path renames admin_code and uses unmasked climate, without new scaling/filling. Parent row universe and inherited cells stay fixed. The old masked climate fork is not this parent. Source parser differences must not reconstruct parent cells. |
| Metric boundaries | `src/ipcch/forecasting_weight_decay.py:378-420`; `src/ipcch/origin_safe.py:125-134,387-409` | Classification uses reported phase; continuous target uses normalized shares. Global F2 is undefined when TP=0. R² uses exact target-constancy and sample-count checks. Preserve observation-row metric weighting/units. |
| Metric reuse limit | `src/ipcch/somalia_oracle/evaluation.py:19-44,139-146`; `src/ipcch/somalia_oracle/q3eval.py:25-36,139-148` | Somalia's F2 boundary differs. Its any-undefined-draw interval suppression was explicitly rejected in G1; preserve global metrics, and apply the selected conditional interval rule instead. Linear percentile calculation remains reusable. |
| Pairing | `src/ipcch/origin_safe.py:26,76-79` and saved predictions below | Keys are area_id/year/month and their hashes depend on order. Set equality must be followed by explicit common ordering, and both reported and continuous truths checked. |
| Regional target | Existing region map plus country lookup and saved predictions below | region3 agrees across all reference horizons; annual observed strata vary. Country stratification fixes area-sampling slots, not each country's row share. |

The design now spells out these technical clarifications without changing the chosen experiment. New tests in the execution plan cover explicit reordered pairing, exact constant-target detection and the selected invalid-draw behavior.

## Read-only regional support inventory

Sources: `results/experiments/origin_safe_climate_idp_v1/runs/climate_safe_history_idp/{0,3,6,12}m/predictions/predictions_{2022,2023,2024,2025}.csv`, the region mapping and manifest country lookup. All 16 files have unique evaluation keys; sorted keys, reported phase and normalized phase3 target agree across horizons. Both lookup keys are unique; selected metric inputs contain no missing values; each period's continuous target is nonconstant. These are inspections of existing outputs, not replays of fitted models.

| Period | Rows | Areas | Country strata | Observed IPC3+ rows | TP H3/H6/H12 |
|---|---:|---:|---:|---:|---|
| 2022 | 703 | 648 | 7 | 223 | 176 / 140 / 169 |
| 2023 | 514 | 458 | 7 | 233 | 120 / 156 / 188 |
| 2024 | 594 | 507 | 7 | 414 | 225 / 269 / 314 |
| 2025 | 1423 | 1017 | 10 | 712 | 511 / 568 / 661 |
| Pooled | 3234 | 1021 | 10 | 1582 | 1032 / 1133 / 1332 |

No singleton country stratum occurs in these periods. The reference support is not sparse; this does not establish support in the new, unfitted arms or validity of their bootstrap draws.

## Concrete stress cases

1. H3 past `[1, NaN, 3]` gives existing R=2; future `[4,5,6]` gives F=5. New B must be NaN, not 3.5. This preserves baseline R while enforcing the new completeness rule.
2. Y2022/H3 fits through target U=2021-10 at fit origin2021-10. That fitting row's own O is2021-07 and oracle months are2021-08…10: no training weather beyond the annual fit origin. Future weather is still counterfactual origin-available for that row.
3. H12 O+7…O+12 cannot affect new columns. H3 at O=2014-12 may have complete future2015-01…03 but no past source months; raw/F can be present with B missing. Neither case permits dropping the row.
4. One country with two areas: A contributes one TP; B contributes one FP and one FN. Global point F2=0.5. Sampling B twice has probability1/4, yielding precision=recall=0 and undefined global F2, although the Somalia helper would return0. This distinguishes metric definition from the interval-handling choice.

## G1 — interval behavior when a paired draw is undefined

Resolved: user explicitly selected B (conditional intervals from valid paired draws, disclosing invalid proportion). The earlier A recommendation was not adopted. Alternatives are retained below as decision history.

- **A, originally recommended, not selected:** any undefined paired draw makes only that period/horizon/metric/contrast CI unavailable. Keep a defined point difference and report reason plus valid/invalid counts. This preserves the full specified resampling distribution and follows the existing helper's interval policy.
- **B, selected:** form a conditional interval from valid paired draws only and label the conditioning explicitly, with invalid count/fraction. This changes the interval's interpretation; G2 below freezes its minimum-valid-draw requirement.

No changing F2 to zero, drawing replacements until 2,000 valid draws, country-block sensitivity or refitting is implied by either choice. G1 is incorporated into PRD/design/plan. The common original draw bundle remains paired across arms/horizons; each contrast's conditional interval uses its own joint-validity mask and reports counts/fraction, with all original draws retained.

## G2 — minimum valid draw count for the selected conditional interval

Resolved: user selected A, at least 1,000 valid paired draws out of the fixed 2,000 (50%). B, at least 1,900 (95%), was not selected. Below 1,000, retain any defined point difference and mark only that interval unavailable; at 1,000 the count requirement is satisfied. This is a predeclared reporting threshold, not a guarantee of statistical adequacy. Do not replenish invalid draws. PRD R7/AC5, design, implementation steps/tests and glossary now agree with both decisions.
