# Design: origin_safe_weather_oracle_v1

Approved design contract for the accompanying PRD (user approval 2026-10-07). Implementation and experiment validation had not been executed at approval; execution progress is recorded in PROGRESS.md.

## Data flow and compatibility

Pinned parent inputs + shared monthly source → append oracle/B6 columns and lineage → explicit version/arm validation → existing strict annual global fitter → six new runs → keyed global comparisons → region3 extraction and paired bootstrap of saved predictions.

Use namespace `origin_safe_weather_oracle_v1` under the existing model-ready, experiment-results and report roots. Reference existing `origin_safe_climate_idp_v1/runs/climate_safe_history_idp/{0,3,6,12}m` by explicit paths. New arms are `climate_safe_history_idp_oracle` and `climate_safe_history_idp_oracle_b6`. Keep the legacy suite's VERSION, default arms and output behavior unchanged. No implicit directory discovery, duplicated full trainer or general experiment framework is needed.

Reuse `origin_safe.py` timing/target/key/metric helpers and the origin-safe branch of `run_deep_feature_weight_decay_forecasting.py`. It consumes manifest feature order. Add an explicit allowed-version/exact-schema contract for the new arms at input loading; current code does not have a generic weather timing gate to simply relax. Retain legacy history/IDP/cohort/hash checks. Bind added helper/recipe hashes into the new manifest/fingerprint. Detailed integration anchors and legacy verifier limitations are in `research/integration-surfaces.md`.

## Frozen reference and preflight

- Parent manifest: `Analysis/1.Source Data/assembled_IPCCH/model_ready/origin_safe_climate_idp_v1/origin_safe_climate_idp_v1_manifest.json`, SHA256 `3b479c80498e9f2d6d20b88936fce468f297d2e0ccd6f0cb32c61a7470a209bf`. Resolve exact source paths through this manifest, including shared monthly/GS and national IDP inputs; hash all consumed artifacts and keep its source-vintage disclosures.
- Evaluation key hash: `f0193c1402d0609556755844b476227b7188f9671323d21317336d7ef58d2e0f`; 28,205 rows, annual counts 5,599/6,064/5,127/11,415 for 2022–2025. Use the existing tuple-hash convention; a CSV-byte hash is a different quantity.
- Interpreter: `/home/swl007007/.venvs/ipcch-geo/bin/python`; Python3.12.3, XGBoost3.2.0, NumPy2.4.4, pandas3.0.3, sklearn1.8.0. Verify installed versions before execution; do not substitute system Python.
- Configs: `configs/forecasting_hyperparameters.json` SHA256 `3742300661466f22eba8198e5d4f9c2a277615ba59562fbf27f251ecc932dd76`; `configs/forecasting_hyperparameters_p3.json` SHA256 `cdc0e55aa15bdda932465088568b9ee717d226208ffb32076f438fb274e6317b`. Preserve phase3-specific selection.
- Preserve the saved training fingerprints, which predate A01–A04 repairs, and separately record this verification's code identity. Never invoke the modified training runner into old outdirs merely to verify reference reuse: its code fingerprint intentionally differs.
- Inventory the reference's model, prediction, fit-key and batch-record hashes. Verify all four years at all four horizons: ordered features, normalized fitting targets, fitting keys/weights, cutoffs, cohort/truth, model replay and metric replay. Read numeric CSVs using `float_precision="round_trip"`; prediction tolerance atol1e-6/rtol0, metric tolerance atol1e-12 and identical undefined masks. Failed parity, missing artifacts or runtime drift stops execution; no automatic refit or cohort repair.

## Append-only feature contract

For every training and evaluation row, O=T−H and m=min(H,6). Sources are exactly `prcp_anom_month_ensmean` and `tmean_anom_month_ensmean` from the pinned shared monthly export, keyed uniquely by area/month. Calendar-month lookup must not turn missing months into shifted row offsets. Follow the parent origin-safe source path (`admin_code`→`area_id`, unmasked climate); do not introduce the older climate2015 Rainf-mask path or replace the parent row universe with climate-source rows. Keep parent R values as saved rather than reconstructing inherited cells through a potentially different CSV parser.

Raw column order is increasing future offset k, precipitation then temperature at each offset, named `oracle_{v}_o{k}`. Missing source months remain NaN; reject duplicate source keys and non-finite source values other than declared missingness. H0 has no appended columns or new arm fit.

For B6, append F, B, Q for precipitation, then F, B, Q for temperature:

| Term | Formula and dependencies | Column name |
|---|---|---|
| F | mean x_v(O+1…O+m); all m values finite | `oracle_{v}__wmean_o1_o{m}` |
| B | (R_v+F_v)/2; F, existing R and all past x_v(O−m+1…O) finite | `oracle_{v}__halfmean_roll{m}_o1_o{m}` |
| Q | F_v×1[overall_phase_history_1≥3]; F and safe history1 finite | `oracle_{v}__wmean_o1_o{m}__x__crisis_history_1_ge3` |

Use the existing R column `{v}__roll{m}_mean_asof{H}_s{H}` for H3/H6, and `{v}__roll6_mean_asof12` for H12. Its baseline missingness rules remain unchanged; the stricter complete-past requirement applies only to new B. With complete windows, B equals the mean of the 2m months. The IPC gate is internal, not an extra predictor. history1 is the latest safe report at or before min(O,T−1), not necessarily current crisis status.

If F is missing and gate=0, Q remains NaN. If the past is incomplete, F/Q may remain valid; if history is missing, F/B may remain valid. Precipitation missingness does not suppress temperature. Retain finite raw month values when a summary is missing. Do not fill, drop rows, add missingness indicators or change baseline preprocessing.

| Horizon | Reference features | +raw | +raw+B6 |
|---|---:|---:|---:|
| 0 | 870 | shared reference | shared reference |
| 3 | 870 | 876 | 882 |
| 6 | 870 | 882 | 888 |
| 12 | 654 | 666 | 672 |

Validate exact feature names/order and inherited matrix values/NaN masks, keys and labels against the reference, not merely feature-name hashes. The ledger binds each row's origin, future observation months, assumed forecast availability O, past-window months, per-variable past and future finite-month counts, history1 source month/staleness and source/recipe hashes. These diagnostics are not predictors. Record per-feature F/B/Q nonmissing counts/rates for fitting rows in each annual batch and evaluation rows by year/horizon; do not count repeated training rows across batches as unique observations.

The explicit oracle exception applies only to declared future weather and derived F/B/Q dependencies. Changing H12 O+7…O+12 must not affect new columns; changing weather at or before O must not affect raw/F, but may affect B. Future labels/IDP/GS remain prohibited. Record realized observation month honestly; hypothetical forecast availability is a separate field.

## Fitting and global evaluation

For each target year Y=2022…2025, fit four cumulative regressors using label cutoff Jan(Y)−max(H,1), weight origin Jan(Y)−H and half-life24. For fitting-row target month U, weight is `0.5**((fit_origin−U)/24)` in calendar months, not age measured from that row's origin U−H. Each input row keeps its own O. Retain seed42, threshold0.2, n_jobs16 and the saved normalization/classification protocol: continuous phase3 metrics use normalized `phase3_worse` versus `phase3_pred`; categorical truth is reported `overall_phase`, not reconstructed shares. The last oracle observation of a fitting row is U−H+min(H,6)≤U≤fit_origin, so no additional H-month subtraction is applied to fitting labels.

Only six new run combinations are allowed: two new arms × H3/H6/H12. Four annual batches per run give 96 regressors. No reference H0 duplication. Run sequentially to respect memory/resource limits. Each batch retains predictions, compressed fit keys, four UBJ models and its batch record, including ordered schema, inputs, fitting origin/cutoff, artifact hashes and fingerprint. Reuse existing resume integrity checks; keep new outputs isolated.

Eight metrics, annually and pooled: `exact_phase_accuracy`, `phase3plus_accuracy`, `precision_phase3plus`, `sensitivity_phase3plus`, `f2_phase3plus`, `r2_phase3plus`, `mae_phase3plus`, `ordinal_mae`. Preserve unrounded predictions and the global evaluator's undefined cases, including F2 with undefined precision/recall or zero denominator. Never substitute Somalia helper metric conventions silently. Compute raw−reference, B6−reference and B6−raw; H0 has one reference row. Reports state metric direction, support, undefined reasons and the perfect-forecast/representation interpretation limits from the PRD.

Metrics use observation-row weighting, with no training-decay weights in evaluation. Store accuracy/precision/recall/F2 and R² as dimensionless values, share MAE in normalized share units, and ordinal MAE in phase steps. If displaying share MAE or accuracy differences as percentage points, label the conversion explicitly and preserve raw machine-readable values.

Replay all four yearly batches of every reference and new run, not the legacy verifier's default two-year sample. Save explicit run paths and inventories in machine-readable comparison metadata; a COMPLETE flag alone is insufficient.

## Region3 saved-prediction comparison

Membership authority is `data/reference/area_id_country_region_mapping.csv`, SHA256 `18ab5099ce2d1154fb5686183ee399124e18427cc1594923f7abe2769da1611d`. Require unique `area_id` and join by that key, selecting `region=3`. Descriptive country set: AGO, LSO, MDG, MWI, MOZ, NAM, SWZ, ZAF, ZMB, ZWE; COD is region4 and TZA region1. These names never replace the membership join. The file has 1,104 region3 areas; 1,021 occur in the frozen evaluation cohort.

Use `Analysis/1.Source Data/assembled_IPCCH/country_area_id_lookup.csv`, SHA256 `e2baf6ae9481b42b127db5ce81f3c53ad784bb08ae56dfa56cea74e416b44c90`, solely to attach country strata. Validate unique lookup keys and country consistency per area. All baseline prediction keys map to a region; all selected region3 areas have country IDs. The 225 global empty-ISO3 rows are region2 and do not alter regional membership or global scoring. Missing region membership or selected-country IDs in new data is an error, not permission to silently drop rows.

Extract and compare all saved reference and new global predictions: 3,234 regional keys, 1,021 areas, ten countries; annual rows 703/514/594/1423. Years 2022–2024 each contain seven observed country strata; 2025 and the pooled period contain ten. Verify equal key sets, reported phases and normalized continuous targets across arms and horizons, then explicitly align vectors on a common sorted `(area_id, year, month)` index before computing the same eight point metrics and deltas. Record this sorting/hash convention separately from the parent manifest's order-sensitive key hash. Export local predictions and a membership/coverage ledger. This stage may only read predictions and metadata; never invoke a training runner or `run_region_models.py`.

### Country-stratified whole-area paired bootstrap

For each annual period and the pooled 2022–2025 period, sort country and area IDs deterministically. Within each country c containing N_c observed areas in that period, draw N_c areas with replacement; all rows of each sampled area receive its draw multiplicity. Singleton strata have multiplicity1. An area carries its entire selected-period time series, never separately sampled months.

Use 2,000 draws and one NumPy PCG64(seed42) generator per period, advancing sequentially through sorted countries and draws. Do not restart the same seed for each country. Generate a single draw bundle per period and reuse it for every arm, horizon, metric and delta. Preserve global observation-row weighting; do not equal-weight countries or areas after sampling.

Compute weighted metrics on each draw and subtract paired scores. In particular, use the draw-weighted target mean in R² and test target constancy on positive-weight rows using the global evaluator's exact-constant rule; floating-point `SS_tot>0` alone is insufficient. Confirm weighted results against explicit row duplication on a small uneven-country example using the global metric definitions, including undefined cases. The output intervals are 95% percentile intervals for the three paired differences at H3/H6/H12, with quantiles .025/.975 and linear interpolation. H0 is reference-only.

Undefined-draw policy selected by the user in G1: compute percentile intervals using only draws in which both compared metrics are defined, and explicitly label them as conditional on metric definability. Record total, valid and invalid paired draws and the invalid fraction for every period/horizon/metric/contrast; retain all original draws and the per-contrast validity mask for replay. The original shared multiplicities remain identical across contrasts; their usable draw subsets may differ. Never substitute zero or resample until enough valid draws exist. G2 freezes the reporting threshold at at least 1,000 valid paired draws out of the fixed 2,000 (50%). This threshold is a reporting rule, not a statistical adequacy guarantee.

If either observed point metric is undefined, no country stratum has at least two areas, or fewer than 1,000 paired draws are valid, mark only that interval unavailable with reason/counts. Keep any defined point difference. With exactly 1,000 valid draws and the other conditions met, report the conditional interval. Save period keys/key hash, sorted country/area IDs, multiplicities, metric/delta draws, seed/generator/quantile definitions and explicit prediction/source/code hashes for replay. Do not rerun models to generate intervals. This conditional-interval choice intentionally differs from the older Somalia helper's any-undefined-draw suppression policy while preserving the global metric definitions.

This procedure preserves dependence within an area over the selected period and fixes the observed country strata and each country's number of sampled areas. It does not fix each country's observation-row share: areas have different row counts. It does not model shared shocks across distinct areas within a country, fitting/seed uncertainty, new countries or future years. No country-block sensitivity analysis is included.

## Deliverables and stop conditions

Deliver one new input manifest and lineage/coverage evidence, six verified run directories, an explicit reference-reuse inventory, global comparison CSV/Markdown, region3 predictions/membership/metrics/deltas/bootstrap outputs, and verification metadata. Reports live in the new report namespace and place the original reference configuration first. Preserve code and compact evidence pointers/hashes in the task's tracked evidence because large data/results/reports are ignored.

Reuse existing serializers, metric helpers and model loaders; only add the small feature and regional resampling logic absent today. Fail on mismatched source hashes, duplicate/missing required keys, undeclared new columns, future non-oracle dependencies, inherited-cell changes or replay drift. Preserve prior and partial new artifacts with explicit incomplete status. Fix code only within approved scope; a material design change or baseline refit requires renewed review.
