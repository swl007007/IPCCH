# Design: compact_climate_weather_oracle_v1

Status: formal planning specification, awaiting final user review. No execution evidence is implied.

## Data flow and isolation

Pinned existing monthly sources + parent key/label/background/history/IDP inputs -> compact origin-aligned baseline -> raw-oracle append -> existing annual global fitter -> saved-prediction global/regional scoring -> actual-input codebook and verification.

Use version `compact_climate_weather_oracle_v1`; arms `compact_baseline` and `compact_weather_oracle`. Place model-ready inputs under the existing external assembled_IPCCH/model_ready/version root, runs under `results/experiments/compact_climate_weather_oracle_v1/runs/<arm>/<H>m`, reports under `reports/compact_climate_weather_oracle_v1`. Do not overwrite older versions. One task with sequential verifiable stages is sufficient; no independently deployed components or child tasks are required.

The parent manifest is `Analysis/1.Source Data/assembled_IPCCH/model_ready/origin_safe_climate_idp_v1/origin_safe_climate_idp_v1_manifest.json`, expected SHA256 `3b479c80498e9f2d6d20b88936fce468f297d2e0ccd6f0cb32c61a7470a209bf`. Resolve consumed source paths and hashes explicitly from it. Verify current bytes before execution; stop on drift.

Parent baseline datasets supply the row universe, labels, static/context/history/IDP values and their provenance. Preserve these values and NA masks on keys. Recreate the existing calendar dummies deterministically from the unchanged target year/month; they need not be stored columns in the parent input CSV. Rebuild only the approved monthly dynamic and seasonal block. Reuse and validate safe-history/IDP source ledgers, including derived history differences. Reject duplicate keys, unexpected labels, unmatched required area mappings and unapproved features. Do not drop rows because features are missing. The feature input matrix excludes keys, target shares, reported target phase, target population and all diagnostic fields.

## Feature-version rollback

Preserve both the pre-change full-feature versions (origin_safe_climate_idp_v1 and origin_safe_weather_oracle_v1) and this compact version. Existing legacy manifest/arm invocations must continue to work after compact integration; select a feature version through its explicit versioned manifest and matching arm/output namespace, not a mutable global default. Do not overwrite saved legacy inputs/models. Freeze compact recipe/spec/contract/source hashes so subsequent changes can return to this exact compact feature version as well. Deliver a short rollback.md with explicit manifest/run paths, matching arm/horizon choices, pinned implementation commit and verified invocation examples after implementation. Distinguish reading saved old results from refitting legacy features: old results keep their original code fingerprints; a requested refit needs a fresh output directory. No legacy refit is added to the seven-run experiment. Verify selection and rejection of cross-version schemas with small tests. There is no new general version-management framework or destructive restore command.

## Source lists and definitions

Let S be the ordered ordinary source list:

1. GPP_mean
2. nightlight_mean
3. event_count_violence
4. sum_fatalities_violence
5. WFP_Price
6. food_price_index_WB
7. nino34_anom
8. bbg_staple_food__composite_mean
9. bbg_oilgas__composite_mean
10. bbg_soybean_oil__composite_mean
11. bbg_global_food__composite_mean
12. prcp_anom_month_ensmean
13. prcp_z_month_ensmean
14. rainy_days_month_ensmean
15. cdd_month_ensmean
16. tmean_anom_month_ensmean
17. tmax_anom_month_ensmean
18. hot_days_p95_month_ensmean
19. gdd_month_ensmean
20. edd_month_ensmean
21. sm_z_month_ensmean
22. spi03_month_ensmean
23. spei03_month_ensmean
24. evi_anom_month_ensmean

Sources1–11 derive from `assembled_IPCCH/interim/IPCCH_2026_target_corrected_nino34_wbfood.csv`, using `admin_code -> area_id`; the climate fields derive from `IPCCH_shared_folder/climate_monthly_2015_2026_MODELING_READY.csv`. Use existing supplied numeric series; do not substitute completed/forward-filled older climate series. Preserve all available historical months in these sources (recorded grid starts:2010-01 interim,2015-01 climate); never use source months after the permitted origin except the declared oracle.

WB RTP retains the existing area-level `food_price_index_WB`; no new market mapping. The existing index definition is (open+close)/2. Bloomberg uses the exact parent `commodity_members` lists for all four composites (5/3/2/9 members), arithmetic mean of nonmissing numeric members per area/month, NA if all missing, no quote-scale normalization. Pin members in the new manifest, rather than allowing new prefix matches to change groups silently.

The z-eligible ordered subset Z is S1,S2,S5,S6,S7 followed by the climate sources with bases prcp_anom,rainy_days,cdd,tmean_anom,tmax_anom,hot_days_p95,gdd,edd,evi_anom (14 total).

## Monthly recipes, names and time

For target calendar month T and horizon H, O=T-H using calendar-month ordinals. Use a dense keyed area/month grid; missing months never shift observation positions. New names are horizon-independent and end `_at_origin`; run metadata provides H. An H12 origin is T-12, with no second fixed-history block.

For each x in S, emit in this order:

- `{x}__value_at_origin`: x[O].
- `{x}__ma3_at_origin`, `__ma6_at_origin`, `__ma12_at_origin`: mean of nonmissing x[O-w+1..O], requiring2/3/6 values respectively.
- `{x}__sd12_at_origin`: sample SD (ddof=1) over O-11..O, requiring6 values.

For each x in Z and each monthly u, construct z[u]=(x[u]-mean(P[u]))/sample_sd(P[u]), where P[u] contains this area's nonmissing observations in strictly earlier years of u's calendar month. Require finite x[u], at least2 history observations and nonzero historical sample SD, else NA. Then emit:

- `{x}__hist_same_month_z_at_origin`: z[O].
- `{x}__hist_same_month_z_ma3_at_origin`, `_ma6_at_origin`, `_ma12_at_origin`: mean of the individually computed monthly z[u] within O-w+1..O; same minimums2/3/6.
Do not compute a z of a raw rolling average. Do not re-standardize prcp_z,sm_z,spi03,spei03. Do not add BBG/conflict z or seasonal z expansions.

D16 overrides historical carrier-mask conventions: build all monthly dynamic recipes directly at O; do not require an O+12 row and do not copy extra NA from saved engineered tables. No interpolation or extra forward fill. Keep source-native NA and D13/D14 behavior. A trailing window can be defined despite a missing current source if its own minimum count is met. Record coverage and old-NA-restoration diagnostics for genuinely comparable old/new features on matched keys; do not force parity with superseded masks or invent comparability for new recipes.

## Stress recipes

Ordered signals:

| Signal stem | Monthly hit rule |
|---|---|
| GPP_mean__vegetation_stress | x[u] < 0.9*x[u-12] |
| event_count_violence__nonzero_stress | x[u] > 0 |
| WFP_Price__price_shock_stress | (x[u]-x[u-12])/x[u-12] > 0.10 |
| nino34_anom__enso_stress | abs(x[u]) > 0.5 |
| spi03_month_ensmean__deficit_stress | x[u] <= -1 |
| tmean_anom_month_ensmean__hot_stress | x[u] >= 1 |
| evi_anom_month_ensmean__vegetation_stress | x[u] <= -0.015 |

Reuse existing numeric behavior: current source NA -> signal NA; missing GPP year-ago comparator yields false0; missing/zero WFP year-ago denominator yields false0. No missingness correction. Ordinary future-perturbation checks must allow the internal year-ago dependency without treating it as an extra input column.

For each stem emit `__share12_at_origin`, `__months_since_at_origin`, `__longest_run12_at_origin`, `__any12_at_origin`:

- share12 = mean of valid binary signals in O-11..O; at least6 valid.
- months_since = O minus the most recent observed hit month <=O, searching all available source history; NA until a first hit; elapsed time advances through missing months.
- longest_run12 = longest consecutive run of hits in the last12 calendar months; NA breaks a run; at least6 valid.
- any12 = maximum valid signal in last12 calendar months; at least6 valid.
No new stress source and no carrier-row masks.

## Growing seasons and major dummy

Source: `IPCCH_shared_folder/climate_2015_2026_MODELING_READY.csv`. Retain exactly two latest completed records per area using existing stable selection: end_exclusive <= first day of O+1, sorted end then start, later start wins tied end; retain source order for residual exact ties. No new support-completeness filter. Missing selected source metrics remain NA.

Ordered seasonal metric bases match S12–S24 with `_month_ensmean` replaced by `_gs_ensmean`. For k=1 then2, emit `gs_last{k}__{metric}__at_origin` for all13, then `gs_last{k}__months_since_end_at_origin` = O minus the calendar month containing end_exclusive-1day. No season -> all that rank's inputs NA.

Then emit `gs_last1__is_major_at_origin`. Match the selected latest record to its same-area/same-season_year s1/s2 pair. Calendar duration=end_exclusive-start in days. Uniquely longer=1; uniquely shorter=0; equal/missing/invalid duration, uncomparable pair or no completed latest season=NA. Never use realized future climate/support days for this comparison. Calendar is fixed retrospective context; the paired season need not be completed to compare fixed calendar durations. Do not include second-season dummy, season IDs/dates or support counts as model inputs. Save selected identities, durations, source dates and classification in a diagnostic ledger.

## Background and exact fitted order

Preserve literal names and relative order from parent H0 `run_metadata.json.features` for the static29, coordinate/calendar27, safe-history5 and IDP2 groups; assert all parent horizons agree. Calendar refers to target T, with month1–12 and year2014–2026 full dummy sets. History consists of latest3 eligible same-area reported phases with source month <=min(O,T-1), plus differences1-2 and1-3. IDP is latest nonmissing national stock report<=O and its age, with verified country mapping.

Full order: static29 -> ordinary120 (source-major) -> z56 (source-major) -> stress28 (signal-major) -> season29 -> coordinates/calendar27 -> history5 -> IDP2 =296. `expected_feature_contract.csv` supplies each literal and its 1-based run positions. No auto numeric-column selector may add diagnostics or targets.

## Raw oracle and run matrix

Oracle sources are precipitation anomaly and temperature anomaly from the same pinned monthly climate export. Append `oracle_prcp_anom_month_ensmean_o{k}`, then `oracle_tmean_anom_month_ensmean_o{k}`, in increasing k=1..min(H,6). Each equals x[O+k] by calendar key, NA if absent; no summaries or interactions. Record actual observation month and the counterfactual assumption of availability at O separately. H12 must ignore O+7..O+12.

| H | compact_baseline | compact_weather_oracle |
|---|---:|---:|
| 0 | 296 | shared baseline; no fit |
| 3 | 296 | 302 |
| 6 | 296 | 308 |
| 12 | 296 | 308 |

Baseline projection in each oracle input must equal that horizon's newly rebuilt baseline (all values/NA/order/keys/labels), using round-trip parsing after serialization. Old deep-feature runs are provenance references, not reused compact models. No old-mask baseline or extra sensitivity arm.

## Annual fitting and scoring

Frozen evaluation tuple hash `f0193c1402d0609556755844b476227b7188f9671323d21317336d7ef58d2e0f`;28,205 rows, yearly counts5599/6064/5127/11415. Reuse parent training eligible-key universe and labels; compare per-batch fitting keys/targets/weights to parent protocol, without imposing old feature values. No prediction-dependent row deletion.

For Y=2022..2025: fit labels through Jan(Y)-max(H,1); weight origin Jan(Y)-H; weight for fitting target U =0.5**((Jan(Y)-H-U)/24). Each fitting row retains its own O=U-H. Fit phase2_worse,phase3_worse,phase4_worse,phase5_worse using the existing XGB function, seed42,n_jobs16,half-life24. Preserve normalization, reported-phase truth, highest unrounded cumulative score>=0.2 classification (default1), and existing continuous-score treatment. No rounding before classification, new calibration, clipping or monotonicity layer.

Interpreter `/home/swl007007/.venvs/ipcch-geo/bin/python`: Python3.12.3, XGBoost3.2.0, NumPy2.4.4,pandas3.0.3,sklearn1.8.0. Recheck before execution; no substitution. Config hashes:

- `configs/forecasting_hyperparameters.json`: `3742300661466f22eba8198e5d4f9c2a277615ba59562fbf27f251ecc932dd76`
- `configs/forecasting_hyperparameters_p3.json`: `cdc0e55aa15bdda932465088568b9ee717d226208ffb32076f438fb274e6317b`
Only phase3 uses p3 config. Run sequentially with one measured batch, exact fingerprints/checkpoints and complete-artifact resume validation. No simultaneous large test/training pools.

Eight metrics: exact_phase_accuracy,phase3plus_accuracy,precision_phase3plus,sensitivity_phase3plus,f2_phase3plus,r2_phase3plus,mae_phase3plus,ordinal_mae. Use existing global semantics, including F2 undefined cases. Continuous phase3 truth is normalized phase3_worse; class truth is reported overall_phase. Evaluation weights are observation rows, not temporal training weights. Preserve raw dimensionless scores, normalized-share MAE and phase-step ordinal MAE; label any presentation-only percent conversion.

## Regional tables

Join `data/reference/area_id_country_region_mapping.csv` on area_id, expected SHA256 `18ab5099ce2d1154fb5686183ee399124e18427cc1594923f7abe2769da1611d`. Unique area keys required. Every scored key must match one region in0..8; region0 is valid. Do not use country grouping, guessed region names or old helpers that skip n<5. Score all regions and preserve empty/small groups with n and metric-specific undefined reasons; no minimum-support exclusion beyond mathematical metric validity.

Align arms on sorted (area_id,year,month) and verify identical truths before differences. For every run, report global and region metrics for2022/2023/2024/2025 and pooled2022–2025, using pooled saved rows directly rather than averaging annual scores. Deltas = oracle minus baseline for H3/H6/H12; if either value is undefined, delta is undefined with reason. H0 is one baseline result. Require regional row counts to sum to global and no membership loss.

Write `global_metrics.csv`, `global_deltas.csv`, `regional_metrics.csv`, `regional_deltas.csv`, coverage/undefined reasons, concise Markdown report and explicit comparison metadata. Long tables contain run/arm/H, period, region when applicable, metric,value,status,reason,n_rows,n_areas and relevant positive/negative support. No bootstrap imports/execution or intervals. Regional scoring must not train models.

## Contract, evidence and acceptance

After this design is persisted, generate `expected_feature_contract.csv` and companion `expected_run_index.csv` / `expected_feature_contract_metadata.json` in the task directory. English columns follow the HHA template: position,predictor,group,description,unit,source,time_relative_to_origin,formula,missing_semantics,input_type, followed by explicit seven-run membership, expanded_count=1 per included literal, expected_model_columns and expected_model_positions, source definition/evidence/limitations. There are308 union rows; run projection gives296/302/308. Position is union display order; expected_model_positions is authoritative fitted order. All rows have status expected_not_fitted. Metadata binds spec/contract bytes and schema hashes; no claim of training.

At completion generate actual `model_run_codebook_en.csv` from saved ordered feature metadata checked against every booster, plus run index, provenance and expected-vs-actual report. Do not simply relabel the expected contract as actual. Each model/batch must have prediction, fit-key, model, batch-record and manifest hashes; all28 batches replay, not a two-year sample. Predictions tolerance atol1e-6/rtol0; metric tolerance atol1e-12 and identical undefined masks. Validate metrics through an independent calculation path on saved predictions, not only a second call to the same helper. Persist source/recipe/spec/contract/config/runtime identities and diagnostic ledgers without fitting diagnostic columns.

Stop on drift, duplicate/missing keys, schema mismatch, undeclared future dependencies, unmatched regions, matrix mismatch or replay failure. Preserve incomplete artifacts and report limits; do not silently repair cohorts, substitute runtimes or broaden scope. Rollback consists of stopping new work and leaving old artifacts intact.
