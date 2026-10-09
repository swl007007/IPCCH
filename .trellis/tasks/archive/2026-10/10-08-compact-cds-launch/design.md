# Design: compact_cds_launch_v1

Status: approved formal plan. Execution/launch validation: Not Executed; later evidence is recorded separately.

## Version, outputs and isolation

Retain branch `task/compact-climate-weather-oracle`. Use one task with sequential, independently checkable data/input/fitting/report stages; no separately deployed child component is needed.

- Raw/cache weather: `Analysis/1.Source Data/CDS_API/compact_cds_launch_v1/`.
- Processed inputs/contract copies: `assembled_IPCCH/model_ready/compact_cds_launch_v1/`.
- Machine artifacts: `results/launch/nowcasting_2026_04_compact_cds_v1/`.
- Reports/figures: `reports/launch/nowcasting_2026_04_compact_cds_v1/`.

Existing raw files, forecast-weather launches, compact experiments and archived planning artifacts remain intact. No mutable global default changes. Executable manifests refer to contract/spec copies in the new version root, not a live task directory that will move on archival.

## Model/run contract

| Run | Training input arm | H | Origin | Target | Features |
|---|---|---:|---|---|---:|
| compact_baseline/0m | compact_baseline | 0 | 2026-04 | 2026-04 | 296 |
| compact_baseline/6m | compact_baseline | 6 | 2026-04 | 2026-10 | 296 |
| compact_baseline/12m | compact_baseline | 12 | 2026-04 | 2027-04 | 296 |
| compact_cds_weather/6m | compact_weather_oracle | 6 | 2026-04 | 2026-10 | 308 |
| compact_cds_weather/12m | compact_weather_oracle | 12 | 2026-04 | 2027-04 | 308 |

H0 is one baseline fit referenced by both display arms. CDS is not an extra H0 feature. Four regressors per unique run: phase2_worse..phase5_worse,20 fitted models total. `expected_run_index.csv` and `expected_feature_contract.csv` freeze the five projections of308 union literals; `expected_feature_contract_metadata.json` records their hashes, inherited source identities and ordered lists. Baseline schema SHA256 is `e97388f848e7095bf0535f0cfee1a2d798e0c1863dee843462e60cf6a36f9909`; H6/H12 oracle schema is `3e54c4496d92a76df4f99246a5e9117eccce8ee80a9e3eb8d2d9778c817a2a3e` (newline-joined ordered names, without trailing newline). Expected status is not fitted evidence.

Baseline order: static29, ordinary120, same-month-z56, stress28, growing-season29, coordinates/calendar27, history5, IDP2. Inherit exact compact recipes/order, source-native NA, sample SD/minimum counts, strict earlier-year z-before-MA, original stress missing-comparator behavior, stable two completed seasons and latest-major dummy. No carrier tail mask or extra fixed T-12 block. Keys, population, labels, raw/repaired predictions and diagnostics never enter the allowlist.

## Pinned source roles

`D` means `C:\Users\swl00\IFPRI Dropbox\Weilun Shi\Google fund\Analysis\1.Source Data`; `A=D\assembled_IPCCH`.

| Source role | Path | SHA256 |
|---|---|---|
| Current training/recipe manifest | A/model_ready/compact_climate_weather_oracle_v1/compact_climate_weather_oracle_v1_manifest.json | 456360536a3929e1571d96ba9f16e2f0de54bc1b20019f797bbe62c0c89732ca |
| Parent manifest | A/model_ready/origin_safe_climate_idp_v1/origin_safe_climate_idp_v1_manifest.json | 3b479c80498e9f2d6d20b88936fce468f297d2e0ccd6f0cb32c61a7470a209bf |
| Ordinary sources and label observations | A/interim/IPCCH_2026_target_corrected_nino34_wbfood.csv | a91719e8e603e11b58e3e44c9a2f4378e4218e1ac408afe03ca54d1b50fb0484 |
| Monthly realized climate | IPCCH_shared_folder/climate_monthly_2015_2026_MODELING_READY.csv | 8082b72ea5fa5c30a7b975b89c1fbbb4530f27a9ce6c5ba4d0e1a4f923320c89 |
| Completed seasons | IPCCH_shared_folder/climate_2015_2026_MODELING_READY.csv | f024a66c8979fb4a8c66fba1f04e7e69355fa75b499793d29001a146d8c2958e |
| Full April keys/static29/population | A/features/forecasting_subset_IPCCH_2026_target_corrected_deep_features.csv | 60610cd601e4b0c700cc475903fe807f072f131a97c543dc22f169b2824917e4 |
| Coordinates only, canonical identifier source | A/raw/IPCCH_2026_completed.csv | ae696087c3bbb280537ae269a05924133acdb51060d31290523404fa8a717673 |
| CDS fixed extraction points | A/spatial/unique_area_id_lat_lon.csv | 3bf8f115ec70cd1e1c907031309b797410a8024cdc1d39265be123ae636d2862 |
| Country/IDP lookup | A/country_area_id_lookup.csv | e2baf6ae9481b42b127db5ce81f3c53ad784bb08ae56dfa56cea74e416b44c90 |
| IDP observations | Weilun Shi/Processed_Dataset/IDP_DTM/output/idp_admin0_monthly.csv | a1ebb82a8e14fc0fb8103d6086217b93da351fc4a8f7fcfbe9eaa44a9df602e1 |
| Country population reference | reports/launch/nowcasting_2026_04/population_projection/countries_2025_population_merged.csv | c348cc30cd2b5beae93a11974c4712a3dd6dd822ee902f5458a778effad389b0 |
| Region mapping | data/reference/area_id_country_region_mapping.csv | 18ab5099ce2d1154fb5686183ee399124e18427cc1594923f7abe2769da1611d |

Read required columns only; resolve training CSVs/ledgers/commodity members and their hashes from the current and parent manifests. Recheck all consumed bytes before execution. Freeze geometry sidecar identities when staging. Source checks already done during planning are detailed in research; all un-rehashed manifest declarations remain execution preflight gates.

The comprehensive April source has6,188 unique areas,53 countries, population exactly matching the old area table, and static29 matching all2,774 available compact April rows (values/NA). Interim April population is missing for3,414 unlabeled areas and cannot be the full denominator source. Comprehensive popdensity has4,880 NA; retain it. Reading selected static/population columns from a file named deep_features does not admit its dynamic engineering to the model.

Country/reporting joins use the pinned exact `country` names because Namibia ISO2 is empty and Cote d'Ivoire ISO3 is empty in the source lookup. Preserve display fields/blanks/literal strings such as lookup_code_used=`NA`; never guess missing codes. IDP continues using existing ISO3 lookup, with unmapped stock/age NA. Country population names match all53 source countries one-to-one.

## Training and complete inference matrices

Training selects current compact model-ready rows whose target month U is strictly before2026-04-01 and satisfies `origin_safe.share_validity`; normalize with `normalized_cumulative_targets`. Reuse their frozen static/dynamic/calendar/history/IDP/oracle values rather than rebuild all historical inputs. Prove row/order/target parity between arms, and recheck consumed source ledgers. Historical per-row O=U-H and history cutoff min(O,U-1) remain unchanged. No target population is fitted.

Construct launch keys from the complete comprehensive April cohort, without reading April labels for eligibility. Exactly6,188 areas per target;39 geometry/point-only areas outside that cohort are recorded as outside coverage, not silently added with guessed population. Future target rows need not exist.

Build ordinary/z/stress/season blocks directly at April O from the pinned source grids, without needing a future carrier row. Source grids must include April; stop if O exceeds their last month, do not blank valid trailing windows. Static29 is the April snapshot. Coordinates use the canonical parent's identifier-source April rows. CDS extraction uses its separate pinned fixed-point source; record their tiny coordinate rounding difference, not a new interpolation.

Calendar is target T: H0 April2026, H6 October2026, H12 April2027. Generate the fixed existing dummy literals by equality to T, so2027 has all existing year flags0. Save `target_year_seen_in_training=false` as metadata only.

Filter the phase-observation source through March2026 before calling `build_safe_history`, for all inference horizons. Retain latest3 eligible reports and both differences; do not restore April phase through another background path. Build IDP from observed reports<=April using existing helpers/lookup. Season metrics and major flag must share the exact selected-record ledger. All noncalendar baseline features are identical across these three same-origin inference matrices; each paired weather prefix equals its baseline exactly, including NA/order.

## CDS weather acquisition and monthly definition

Use the existing home `.cdsapirc` only at execution; never save/print secrets. Save requests, response identities and checksums under the new version cache. Use `originating_centre=ecmwf`, system51, initialization2026-04-01, ensemble means; no later initialization.

Old local GRIB is true April–September. Its verifyingMonth/local monthly-mean/statistical-end metadata is authoritative; validityDate is the next boundary. Do not consume the old mislabeled May–October CSV as ready anomalies. Evidence and official URLs are in `research/launch-input-findings.md`.

For true May–September use `seasonal-postprocessed-single-levels`, ensemble_mean, leadtime_month2..6, variables `2m_temperature_anomaly` and `total_precipitation_anomalous_rate_of_accumulation`. Confirm retrieved statistical months/units/system/init, not merely filenames.

- Temperature anomaly in K difference is numerically degreesC difference; never subtract273.15 from it.
- Precipitation anomaly rate m/s ×1000×86400×days_in_statistical_month gives mm/month anomaly.

For true October use `seasonal-original-single-levels`, same system/init, temperature6-hour instantaneous K and precipitation m accumulated since forecast start. April1→October1 is4392h; April1→November1 is5136h. Public constraints expose both bounds and steps through5160h for2026 and reference years1993–2016. Catalogue availability is not retrieval proof.

Construct each member/year's October precipitation total from accumulated P(5136)-P(4392), in mm. Construct October temperature mean from the original instantaneous samples under the documented calendar-month boundary convention. Initial convention is UTC samples within [October1,November1); do not treat forecast interval end as the next month's mean. Verify provider timestamp semantics and freeze the exact rule before acceptance.

Use all qualifying actual forecast members (expected51) and each of the24 April-init hindcast years1993–2016 (expected25 members/year); validate retrieved identities/completeness. Compute each year's monthly member mean and the equal-year hindcast mean, then subtract it from the2026 monthly forecast mean. Save member/year/support counts. No observed-climatology subtraction, z standardization, bias calibration or missing-year/member replacement.

Use the same raw algorithm on overlapping September and compare its resulting anomalies with the official September monthly anomaly at every selected point. Accept only differences explainable by independently computed source packing/quantization and floating reduction bounds; freeze those bounds from downloaded GRIB metadata before comparison, not from prediction outcomes. Missing/unexplained deviations, time-window mismatch, incomplete baseline or incompatible grids stop October acceptance and fitting; investigate rather than tune or silently choose an NA fallback. This retrieval/packing/member verification is explicitly deferred to execution without changing the approved output behavior.

All six months use the same fixed containing-cell extraction (`rasterio.sample` behavior), with verified CRS/grid orientation/longitude handling and unique finite points. No polygon/crop weighting or interpolation. October is marked locally constructed; May–September official. Model reference is1993–2016, distinct from the declared observed-source1991–2020 training reference. Provider/spatial differences are accepted approximations, not proven matching lineage.

Append offset-major precipitation then temperature, k1..6, in existing `oracle_*_o{k}` columns. Fitting reads realized values from compact inputs; inference only reads this CDS cube. Require complete finite forecast values on the6,188 cohort×6 months×2 variables. H0 remains no-op. No fallback to actual weather after April.

## Fitting, persistence and replay

Model environment: `/home/swl007007/.venvs/ipcch-geo/bin/python`, Python3.12.3, NumPy2.4.4, pandas3.0.3, sklearn1.8.0, XGBoost3.2.0. Weather acquisition/decoding/aggregation uses the existing CDS_API `.venv/bin/python`, whose NumPy is2.4.6. The preprocessing CLI has two explicit stages: weather-only under that CDS interpreter writes the forecast cube and provenance; assemble-only under the frozen model interpreter reads those files and builds every compact matrix. Weather-only must not import compact runtime/fitting code; modeling must not require ecCodes/cfgrib/xarray imports. Recheck and snapshot both environments separately; no silent interpreter substitution or dependency installation. Planning package/import evidence is in research; this is not successful decoding or numerical execution evidence.

Reuse `launch_nowcasting.resolve_hyperparameters` and its generic `_fit_model` unchanged; supply canonical configs with explicit n_jobs16 and random_state42. Only phase3 uses the P3 config. Config hashes are3742300661466f22eba8198e5d4f9c2a277615ba59562fbf27f251ecc932dd76 andcdc0e55aa15bdda932465088568b9ee717d226208ffb32076f438fb274e6317b respectively. Use `origin_safe.origin_weights`: w(U)=0.5**((April2026-U)/24). All four targets use the same valid fitting rows/weights.

Do not use old `predict_april`/`validate_and_clip_predictions`, raw-share target derivation or target-filtering test-matrix helpers. Select literal columns strictly; retain NaN for XGBoost; finite raw predictions required. Use `origin_safe.classify_cumulative` on unrounded raw scores, highest qualifying phase>=0.2; default1. Keep raw scores without clipping/rounding.

Run fits sequentially, first a measured sharedH0 fit, then the remaining four. Save each model_<target>.ubj, ordered feature schema, fit keys/normalized targets/weights and raw inference matrix/predictions. Complete records bind all artifacts, Git/code/source/input/spec/contract/config/runtime identities and settings. Resume skips only complete inventories with identical fingerprints; incomplete/stale records are not acceptance. Reload all20 boosters, verify feature order and reproduce raw predictions atol1e-6/rtol0 and exact classification.

## Population and aggregation formulas

Let raw p_a be the complete April population; N_c=sum(p_a) for country c; R_c the2025 reference (reference date2025-07-01). s_c=0.95R_c/N_c if N_c>1.10R_c, else1. Effective p*_a=s_c p_a. Pin this denominator and factor for every target/arm, including0m. Planning reference gives19 capped countries/4,004 areas; raw total2,106,501,620.657281, effective total approximately1,429,568,874.423952. Arithmetic is revalidated on execution inputs.

For raw cumulative q2..q5, d=[1-q2,q2-q3,q3-q4,q4-q5,q5]. b=clip(d,0,1); repaired shares r=b/sum(b). Require finite inputs/positive finite denominator. Report repair/clipping flags; preserve q and the raw-derived phase separately. No rounding before computation.

phase-k count (raw/capped)=r_k×p_a or r_k×p*_a. P3+=sum(k3..5); P4+=sum(k4..5). At country/region/global levels, sum counts and the same population denominator, then divide; also provide uncapped comparison totals using their corresponding raw denominator. Zero-population areas remain in prediction/map counts, contribute0 population, and retain model shares; an aggregate zero denominator yields undefined share with an explicit reason. Negative/nonfinite/missing population stops acceptance.

Join region byarea_id, include0..8 and no support-size filtering. Exact country names handle code gaps; each area maps once. Sum regional and country totals to the same covered-area global total. Paired deltas are CDS-minus-baseline after matching area/target and equal population; H0 is identically0, marked shared, with no duplicate fit.

## Output inventory

Each unique `runs/<arm>/<H>m/` contains model UBJs, feature_schema.json, fit_keys.csv.gz, fit_targets.csv.gz, fit_weights.csv.gz, inference_features.csv.gz, predictions_raw.csv, run_metadata.json and a complete artifact record. Root input/forecast manifests and ledgers record source identities, monthly timing, IPC/IDP/season selections, full cohort and weather overlap checks.

`population/` contains area_population_predictions.csv, country_population_summary.csv, regional_population_summary.csv, global_population_summary.csv, corresponding four paired difference tables, and country_population_cap_audit.csv. Every table includes version/run/arm/H/origin/target identifiers, population reference/cap status, raw/effective denominators, phase1..5 and P3+/P4+ shares/counts, coverage and undefined reasons where applicable. H0 can appear in both arm views by explicit shared-run reference.

`visualizations/` machine records provide keyed categorical/share/difference values, source CSV/geometry hashes and coverage. Reports contain five categorical PNGs (one per unique run), one2×3 P3+ share comparison PNG (rows baseline/CDS; columns April2026,October2026,April2027), and one1×2 weather-minus-baseline P3+ difference PNG (October2026,April2027). Shared0m is repeated only in the overview; H0 delta is recorded as0. Continuous colors span0–100%; difference limits are symmetric and shared across the two panels. Figures are predicted-only, preserve existing geographic style/Latin-America inset where practical, and do not require a basemap download.

Produce launch_summary.md, population-summary CSV copies, model_run_codebook_en.csv verified from all20 boosters against the expected contract, and verification.json with the complete inventory and independent arithmetic/replay results. There are no accuracy/F1/R2/actual comparisons, bootstrap or SHAP artifacts.

## Minimal code boundary and safeguards

Add `src/ipcch/cds_launch_weather.py` for this specific forecast cube, and `src/ipcch/compact_launch.py` for input assembly, five fits, population reporting and map orchestration. Thin CLIs: `scripts/preprocessing/build_compact_cds_launch_inputs.py` and `scripts/modeling/run_compact_cds_launch.py`. Reuse existing recipe/history/IDP/fitting/geographic helpers; frozen helper/annual runner/legacy CLI/config bytes remain unchanged. No generic provider/version manager, plugin, registry, new model abstraction or new dependency is planned. Add only required focused unit/smoke tests.

Stop on source/helper/schema drift, duplicate/changed keys, missing required mappings, unapproved future dependencies, invalid population, incomplete CDS window/overlap, nonfinite predictions, inconsistent totals or replay mismatch. Preserve diagnostics/partial outputs. Rollback selects existing explicit manifests/output roots; do not overwrite or delete previous versions. No audit registration or external executor dispatch has occurred in planning.
