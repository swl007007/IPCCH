# Extend compact historical evaluation through January-April 2026

## Goal and approval state

Add a separately reported 2026 historical evaluation block to both the saved global compact experiment and the genuinely Somalia-local experiment. Show each arm's absolute performance and its paired oracle-minus-baseline difference, with five annual blocks and explicitly named expanded and original pooled periods.

Requirements and this written implementation plan were explicitly approved by the user on 2026-10-09. This is the approved specification, not an execution report. No extension fitting, reporting run, model replay or acceptance validation had run at approval; current execution state belongs in `PROGRESS.md`.

## Background

The seven frozen compact matrices already contain the January-April 2026 labels and origin-aligned features. The parent cohort marks these rows `share_valid=True` but `eval_key=False` because the original evaluation years are 2022-2025 (`src/ipcch/origin_safe.py:24`; `scripts/preprocessing/build_origin_safe_climate_idp_inputs.py:226-239`). Changing the shared year constant or parent cohort would invalidate the old input/run identity (`src/ipcch/compact_features.py:82-85,479-515`).

The original experiments each have seven runs, 28 annual batches and 112 saved cumulative-target boosters. Their existing verification artifacts record successful acceptance; the extension must recheck imported identities and keyed evidence rather than treat an old success flag as sufficient (`scripts/postprocessing/verify_origin_safe_weather_oracle.py:126-209`; `scripts/modeling/run_somalia_local_compact_test.py:1323-1398`).

## Confirmed decisions

| Decision | User selection |
|---|---|
| D1: 2026 fitting | Fixed annual fit, one fit per arm/horizon for the January-April block; no 2026 fitting labels |
| D2: Labels | All existing valid January-April labels; no new label source or fabricated months |
| D3: Pooled periods | Main pooled 2022-2026; retain independently recomputed pooled 2022-2025 |
| D4: Old years | Verify and reuse 2022-2025 fitted artifacts and predictions; fit only 2026; publish a new version |
| D5: Horizons | Preserve 0m, 3m, 6m and 12m in both historical experiments |
| D6: Convergence | User explicitly confirmed this complete scope before this spec was written |

## R1. Experiment scope and arms

- Two model scopes: `global`, and `SOM` with model scope exactly `Somalia local`.
- Canonical local membership is the exact `iso3 == "SOM"` join to `assembled_IPCCH/country_area_id_lookup.csv`. Both fitting and scoring masks must be local, not merely a subset of global predictions (`run_somalia_local_compact_test.py:61-68,435-458`).
- Reuse `compact_features.RUN_PLAN`: `compact_baseline` at H0/H3/H6/H12 and `compact_weather_oracle` at H3/H6/H12 (`src/ipcch/compact_features.py:37-41`). H0 is shared; never fit an oracle H0.
- Keep the realized-weather oracle at `O+1..O+min(H,6)`. This is the historical oracle estimand, distinct from the future CDS launch.
- Global results include overall scores and all existing regions 0-8 from saved global predictions. Region scores do not imply regional fitting (`src/ipcch/regional_point_metrics.py:1-6,23-44`).

## R2. Frozen 2026 evaluation cohort

Select from the unchanged parent data/cohort: valid reported phase and normalized-share eligibility, `year == 2026`, `month in {1,2,3,4}`; intersect with canonical SOM membership for the local scope. Use the inherited `share_validity` rules (`origin_safe.py:114-122`). Freeze selected keys before fitting. Require complete key sets, no duplicate keys, and identical truth and base features across paired arms.

| Target month | Global rows | Somalia-local rows |
|---|---:|---:|
| January | 679 | 1 |
| February | 643 | 0 |
| March | 231 | 0 |
| April | 2774 | 904 |
| Total | 4327 | 905 |

Global 2026 covers 3823 unique areas; SOM covers 904. SOM's January key is `(1917,2026,1)` and it also occurs in April; 905 rows do not mean 905 distinct evaluation areas. Canonical SOM membership remains 905 areas; area 3146 has no eligible 2026 row. All seven existing matrices contain precisely these candidate keys and labels. See `research/contracts.md` for sources and hashes.

Report the table and the partial-year qualification in both machine-readable metadata and Markdown. Do not report February/March SOM coverage as populated, or interpolate labels. Monthly support is required; extra monthly performance tables are not required.

## R3. Fitting and temporal contract

Use the unchanged `run_origin_batch(..., year=2026, ...)` primitive after the original parent gates (`scripts/modeling/run_deep_feature_weight_decay_forecasting.py:1078-1149`). Retain every row's own feature origin `O=T-H`. The annual fit anchor is January 2026 minus H, with labels no later than January 2026 minus `max(H,1)`.

| H | Fit origin | Latest permitted label | Global fit rows / areas | SOM fit rows / areas |
|---|---|---|---|---|
| 0 | 2026-01 | 2025-12 | 47979 / 6225 | 5834 / 905 |
| 3 | 2025-10 | 2025-10 | 47796 / 6225 | 5834 / 905 |
| 6 | 2025-07 | 2025-07 | 42715 / 6203 | 4926 / 905 |
| 12 | 2025-01 | 2025-01 | 38536 / 6169 | 3958 / 891 |

These are expected eligible sets under frozen inputs, not evidence of executed fitting. Require exact complete eligible keys, weights anchored at the fit origin, normalized cumulative targets and identical fit keys/targets/weights across paired arms.

Retain the frozen hyperparameters/config hashes, seed 42, half-life 24 months, phase threshold 0.2, 16 threads, numerical environment and predictor order. Baseline has 296 inputs; oracle has 302 at H3 and 308 at H6/H12. Preserve native NaN values and the existing `year_2026` feature; do not impute, tune, add predictors or change target reconstruction. Scores remain unrounded before classification.

There are exactly 14 new annual batches across the two scopes, with four phase2-through-phase5 cumulative regressors each: **56 new boosters**. Together with verified old artifacts there are 140 boosters per scope: 112 reused, 28 newly fitted.

## R4. Reuse, identity and publication

Original model/output roots, parent inputs, manifests, contracts, frozen helper files, configs and launch artifacts must remain unchanged. Use a separate extension entrypoint and new output namespaces. Verify old input/runtime/code identities, all referenced artifact hashes, COMPLETE run/batch coverage, keyed predictions/truth and fitting provenance before reuse; fail if any check disagrees. No silent repair, old-year refit or new fingerprint assigned to an old fit.

Record separate old and new fingerprints, artifact paths/hashes and year-level provenance. The combined run has `reused_years=[2022,2023,2024,2025]` and `fitted_here_years=[2026]`. Do not present all five years as fitted by the extension script. Existing saved old verification is prior evidence; fresh prediction replay is required for the new 56 boosters.

Output versions:

- Global: `compact_climate_weather_oracle_eval_2026_jan_apr_v1`.
- SOM: `compact_climate_weather_oracle_eval_2026_jan_apr_v1_somalia_local`.

Machine-readable results live in the corresponding `results/experiments/<version>/`; human-readable reports/codebooks in `reports/<version>/`. A saved, manifest-bound copy of this approved spec must survive task archival. Explicit artifact references are required; do not discover arbitrary latest files recursively.

## R5. Metrics and comparisons

Preserve these eight definitions and canonical undefined reasons: `exact_phase_accuracy`, `phase3plus_accuracy`, `precision_phase3plus`, `sensitivity_phase3plus`, `f2_phase3plus`, `r2_phase3plus`, `mae_phase3plus`, `ordinal_mae` (`origin_safe.py:387-414`; `run_somalia_local_compact_test.py:1254-1274`). Binary truth uses reported `overall_phase >= 3`; continuous P3+ metrics use normalized `phase3_worse` versus raw `phase3_pred`.

Explicit periods: `2022`, `2023`, `2024`, `2025`, `2026`, `pooled_2022_2026` (main), `pooled_2022_2025` (original). Recompute pooled metrics from the specified rows, never average annual metrics. Expanded pooled rows are 32532 global and 5838 SOM; original pooled rows remain 28205 global and 4933 SOM, per run. Original-period metric values, support and undefined status/reasons must match the preserved outputs.

For every required period show absolute values for both arms plus raw `oracle - baseline` at H3/H6/H12, support counts and undefined reasons. Global H0 has only the shared baseline, as before. SOM retains its existing shared-H0 zero-difference presentation where defined; undefined H0 metrics remain undefined (`run_somalia_local_compact_test.py:755-767`).

All global regions 0-8 remain present. The 2026 empty regions 2/6 must retain undefined annual cells, and region 8's single row has undefined R-squared. Never substitute zero or drop unsupported groups. Preserve support columns including `n_rows`, `n_areas` and observed/predicted P3+ counts (`regional_point_metrics.py:59-81,85-108`).

## R6. Reports and actual-input codebooks

Publish the updated global/regional and SOM metric/difference/undefined CSVs, comparison metadata, coverage, artifact/provenance inventories and Markdown reports. Reports identify 2026 as January-April only, the sample imbalance, local/global fitting distinction, two pooled ranges and reused/new counts.

Update actual fitted-input codebooks, expected-versus-actual inputs and model run indexes for the five-year version. Admit actual checked fitted features only, retaining source limitations. Record 112 reused and 28 new boosters per scope, rather than carrying forward a misleading all-112-current-version status. Do not add historical PNG/HTML products or rerun the old local `--report` command, which also regenerates launch outputs (`run_somalia_local_compact_test.py:1972`).

## Acceptance criteria

| ID | Observable result | Requirements |
|---|---|---|
| A1 | Both full parent input gates pass; old and new selected key hashes, month support and paired labels/base feature matrices are checked against pinned data | R1-R2, R4 |
| A2 | All 2022-2025 import inventories and COMPLETE records reconcile; old prediction rows/truth and fit-key cutoff/scope/weights are valid; original annual/pooled metrics and undefined masks/reasons reproduce | R3-R5 |
| A3 | Exactly 14 new batches/56 new boosters; complete expected fitting/evaluation sets, correct annual anchors and no 2026 fitting labels; no old-year refits or oracle H0 | R1-R3 |
| A4 | Reload all new boosters, require exact fitted feature order, score replay atol1e-6/rtol0 and exact thresholded classes; inspect actual fitted order in all reused/new model bundles | R3-R4, R6 |
| A5 | Independent saved-prediction metric/difference replay at atol1e-12 with identical statuses/reasons; five annual and two correctly filtered pooled periods; all regions and absolute values present | R5 |
| A6 | All required reports/codebooks, coverage, explicit old/new lineage, approved-spec copies and complete artifact inventories are recorded with hashes; final verification is nonzero on any missing evidence | R4-R6 |
| A7 | Focused extension and affected existing tests pass; no-write validation and stale/incomplete resume rejection are demonstrated | R3-R6 |
| A8 | Protected old input/results/report/launch/code/config file hashes are unchanged; task progress/evidence is accurate; executor identity is verified before dispatch | R4, governance |

## Governance, limits and exclusions

Execution preference carries forward: Herdr Claude Opus 5.5 with 1M context executes; Codex supervises. Verify the live session/model before dispatch; do not assume the previous pane/session is still valid. The user explicitly requested **no Trellis audit**: no register/start/close/controller audit workflow. Ordinary Trellis start is permitted only after fresh approval of this written plan.

No upstream label-source acquisition, validity augmentation, rebuilding old matrices, 2026 label leakage, model/feature/runtime/tuning changes, old-year retraining, bootstrap inference, pooled equal-year weighting, CDS/provider requests, launch/map changes or external presentation products are included. Calendar/source availability remains the established retrospective proxy, not a claim of publication-vintage real-time availability. 2026 is a partial-year comparison and SOM performance is almost entirely April-supported.

Blocking product questions are resolved. The user explicitly approved this written plan for implementation; see `approval.md`.
