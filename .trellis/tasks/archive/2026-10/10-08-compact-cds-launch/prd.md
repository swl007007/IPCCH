# Compact CDS launch: April 2026 origin

Specification status: approved for implementation on2026-10-09 by the user's continuous supervisor/executor goal request.
Execution status: Not Executed. No new weather download, feature build, model fitting, prediction or figure generation is implied.

## Goal and background

Recreate the forecast-weather launch on `compact_climate_weather_oracle_v1`, predicting April2026, October2026 and April2027 from April2026 origin. Train the weather arm on realized oracle anomalies and substitute CDS forecasts at inference. Deliver predicted population shares/counts and crisis maps, with a paired no-oracle compact baseline. “Metrics” means these forecast summaries, not actual-label performance scores.

The requested older reports are `reports/launch/nowcasting_2026_04_forecasted_weather` and `..._scopes`. Existing launch alignment differs from compact: old weather includes O, old predictions are rounded/clipped, and old scoped inference retains origin calendar. The approved compact feature/target-calendar/raw-prediction rules govern this version. Evidence: `research/launch-input-findings.md`; `launch_nowcasting.py:332-358,1042-1055`; `compact_features.py:116-147,403-412`.

## Requirements

| ID | Requirement |
|---|---|
| R1 | Keep the current Git branch. Use version `compact_cds_launch_v1` and new output directories; preserve older inputs, models and reports. Stay planning until the latest formal plan is reviewed and explicitly approved. |
| R2 | Use H0/H6/H12 only, all O=2026-04, targeting2026-04/2026-10/2027-04. Five unique model sets: baselineH0/H6/H12 and CDS-weatherH6/H12. H0 is one shared fit/result. Each set fits four cumulative regressors:20 models total. |
| R3 | Preserve the exact compact296/308 ordered feature schemas and ordinary/z/stress/two-season/latest-major/history/IDP recipes. No numeric-column discovery, added deep engineering, fixed-asof12 block, NDVI, FAO, WB inflation, B6, extra lags or extra weather summaries. |
| R4 | Fit only current compact-cohort rows with reported phase1–5, finite nonnegative phase shares and positive share total, whose target month is before2026-04-01. Normalize training shares with the existing compact rule. Use the same fitting keys/targets/weights across paired arms; missing features do not remove rows. |
| R5 | Inference IPC history is capped at2026-03 for every H. Historical fitting rows retain their own `min(T-H,T-1)` history rule within the same available-label source. Ordinary sources/IDP are allowed through O=April; growing seasons retain the existing completed-season rule. |
| R6 | Retain target-calendar month/year columns. For2027, all existing year_2014..year_2026 indicators are0; record unseen-year status only in metadata. No year_2027 predictor or year2026 substitution. |
| R7 | Training oracle is the pinned realized precipitation/temperature anomaly at O+1..O+6. Inference uses ECMWF system51 April1,2026 forecasts for true May–October, converted to mm/month and temperature-difference degreesC, in the same12 literal columns. H12 does not use later weather. |
| R8 | Accept the declared observed1991–2020 training reference versus CDS model1993–2016 reference and the existing fixed-point extraction. Record both source/baseline/spatial definitions; do not claim identical lineage. |
| R9 | Correct the statistical-month interpretation. Official monthly leads2..6 supply true May–September. Construct true October from the same April-init original-frequency forecast and1993–2016 system51 hindcasts; validate the construction on an overlapping official monthly anomaly before acceptance. Do not use shifted processed labels, actual future observations, later initialization or an unapproved NA fallback. |
| R10 | Predict the complete6,188-area April source cohort independent of labels; do not use the2,774-row labeled compact April subset as the launch universe or require future target rows. Preserve missing static inputs and zero-population areas. |
| R11 | Fix every target/arm's population to the existing complete April2026 population source. Retain old country cap: when raw country sum exceeds110% of the2025 reference, scale it to95%; apply the same country factor to each area's population/counts for every target/arm. Save uncapped values and factors. |
| R12 | Keep raw unrounded model predictions/classification. For population reporting only, difference cumulative predictions into five disjoint shares, clip components to[0,1], normalize to sum1; counts equal repaired share×population. P3+/P4+ are sums of corresponding repaired phase shares/counts. No new model calibration or rounding before classification. |
| R13 | Output area/country/region/global tables for phases1–5 and P3+/P4+, raw/capped population and counts, shares, coverage and paired CDS-minus-baseline differences. Aggregate shares as sum(counts)/sum(population). Region uses `data/reference/area_id_country_region_mapping.csv`, including0..8. Global means this launch's covered areas. |
| R14 | Produce predicted-only crisis/non-crisis maps and P3+ population-share maps for both arms/three targets. Categorical crisis is canonical raw-derived phase>=3; continuous maps/differences use repaired shares, in percent/percentage points, matching tables. Preserve source/mapped coverage and explicit figure metadata. |
| R15 | Use the frozen modeling interpreter/configs, seed42, half-life24, threshold0.2, n_jobs16 and independent P3 config. Anchor weights at April2026. Save fitted feature order, models, matrices, fit keys/targets/weights, source/config/code/runtime/contract identities and model replay evidence. |

## Acceptance criteria

| ID | Observable outcome | Requirements |
|---|---|---|
| A1 | Five completed unique fits,20 reloadable models; fitted ordered columns equal the contract at296/308; H0 shared output is identical in both views. | R2,R3,R15 |
| A2 | Identical valid fitting keys, normalized targets and weights across paired arms; all label/history source cutoffs proven by keyed ledgers; future-source perturbations do not affect ordinary inputs. | R4,R5 |
| A3 | All three targets retain the same6,188 area keys; no label/prediction-dependent loss. Calendar flags match T;2027 year indicators are all0, metadata marks unseen year. | R6,R10 |
| A4 | Every CDS inference weather cell is linked to April-init system51, correct statistical month, source units, extraction point and applicable reference period. Full May–October coverage and accepted overlap validation exist. | R7–R9 |
| A5 | Complete April population source matches the pinned reference; common country scaling is reconciled at area/country/region/global levels. Zero population is retained; invalid/missing population is reported and stops acceptance. | R10,R11 |
| A6 | Repaired shares sum1, phase counts sum the same population, P3+/P4+ counts equal their phase sums. Independent arithmetic recomputation verifies all four aggregation levels and paired differences. | R12,R13 |
| A7 | Maps cover every predicted area with a valid geometry join, duplicate keys fail, and continuous/difference values equal saved repaired-share table values. All target/arm labels and coverage are recorded. | R14 |
| A8 | All20 fitted models are reloaded against saved ordered inference matrices, reproducing raw predictions with atol1e-6/rtol0 and exact phase classification. Resume requires the complete matching artifact inventory. | R15 |
| A9 | New outputs are versioned and archived-task-safe; older artifacts/helpers retain their selection paths/bytes. Report says prediction summaries; no scoring/bootstrap/SHAP is run. | R1–R15 |

## Out of scope

Actual-label scoring or actual-vs-predicted panels; bootstrap/intervals; B6; July/H3; SHAP; tuning; new feature engineering; country-specific models; later weather initialization; population-growth projection; new country-code repair or climate-provider recalibration; changing legacy launch/annual runner behavior; automatic additional audit enrollment.

## Technical limitations and evidence status

The realized climate export's upstream climatology fitting/spatial weights are not verified. CDS model anomalies and point sampling are explicitly accepted approximations.2027 year effects are unlearned. Existing population completion and static snapshot vintages are not certified; preserve their provenance/missingness. Raw-field October retrieval/aggregation and full launch tests are not executed; they are execution gates, not assumed successes. Exact sources, hashes, helper anchors and deferred provider verification are in `design.md` and `research/launch-input-findings.md`.

No blocking user-owned choice remains after the confirmed design decisions. Final plan review is approved; execution evidence and acceptance are tracked separately.
