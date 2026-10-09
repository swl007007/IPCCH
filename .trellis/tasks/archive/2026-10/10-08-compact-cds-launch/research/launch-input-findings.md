# Launch input findings — 2026-10-08

Research only. This is not the approved specification, implementation plan, execution authorization, or model acceptance evidence. The task remains planning on the existing Git branch.

## Source locations

- `R`: current IPCCH repository.
- `D`: `C:\Users\swl00\IFPRI Dropbox\Weilun Shi\Google fund\Analysis\1.Source Data`.
- `C`: `D\CDS_API`.
- `A`: `D\assembled_IPCCH`.
- `S`: `C:\Users\swl00\IFPRI Dropbox\Weilun Shi\IPCCH_shared_folder`.

## Existing launch and compact boundaries

The two requested forecast-weather report roots use `scripts/modeling/run_launch_nowcasting_2026_04.py` and `src/ipcch/launch_nowcasting.py`. Saved runs use April 2026 as the origin; horizons 0/6/12 target April 2026, October 2026, and April 2027. They are not launches initialized in October 2026 or April 2027. The user requests these three targets; no July deliverable has been added.

Old H0 forecast-weather handling is a no-op (`launch_nowcasting.py:391-392,658-660`). Old H6/H12 append absolute realized-weather/forecast proxies over O..O+6, including April (`:332-358,440-473,663-680`). The compact baseline is 296 features, and H6/H12 oracle adds 12 anomaly features over O+1..O+6, excluding April (`src/ipcch/compact_features.py:403-412`; archived compact `design.md:104-119`). The old numeric selector and zero-filled alignment are not a compact contract (`launch_nowcasting.py:998-1010,1375-1380`).

The archived compact design was read directly, as were `specs/004-launch-2026-04-nowcasting-fallback/spec.md` and `specs/005-add-launch-scope/spec.md`. Old scoring/actual-comparison requirements do not define this task's outputs after the user's clarification.

Existing compact CSVs are label-selected: H0 has 52,521 rows, including 2,774 April 2026 areas, and no future-target rows. The full interim panel has 6,188 April areas; climate and geometry have 6,227 areas. Required launch keys must be constructed independently of actual-label availability, not taken from the compact labeled April subset (`build_origin_safe_climate_idp_inputs.py:226`; `build_compact_climate_weather_oracle_inputs.py:363-397`). No all-6,227 coverage requirement has yet been approved.

Compact background uses target T calendar dummies, with fixed year_2014..year_2026. Existing old scoped launch inference retains the April feature-row calendar. Launch-specific calendar and label-availability decisions are recorded below; the existing labeled cohort is not the full launch cohort (`compact_features.py:116-147`; `origin_safe.py:70-73,313-316`; `launch_nowcasting.py:687-806`). The annual compact trainer is not an April production-launch interface.

Subsequent user decision freezes common fitting-label and inference-history availability through March2026. Apply a label-source cap before2026-04-01; retain each historical fitting row's compact history cutoff `min(T-H,T-1)` within this source. For inference at April origin, this removes April labels for H6/H12 as well as H0. `origin_safe.py:70-73,143-159` establishes the inherited row-specific rule; old launch fitting uses a strict pre-cutoff target-date mask (`launch_nowcasting.py:687-705`). Ordinary April source features are still permitted. This is an observed-month availability convention; no release-vintage evidence has been supplied.

Direct calendar inspection (`build_compact_climate_weather_oracle_inputs.py:373-378`) confirms each literal is an exact target-month/year equality, and the fixed fitted-order hash disallows silently adding a2027 column (`compact_features.py:124-147`). The user selected all existing year dummies0 for2027, with target-month encoding and unseen-year metadata. This preserves the literal definition/schema; it does not imply learned future-year extrapolation. The existing2026 training data cannot learn a new2027 dummy.

## Population outputs

The user clarified that metrics means predicted population shares/counts and related launch summaries, not accuracy/F1 or actual-label scoring. The user selected a fixed April 2026 population denominator for all three targets.

Current references:

- `results/launch/nowcasting_2026_04/population_nowcast/area_level_nowcasting_predicted_population_2026_04.csv`: 6,188 areas; explicit April 2026 population reference and source path.
- `results/launch/nowcasting_2026_04/population_projection/area_level_predicted_population_combined_2026_07_2026_10.csv`: July/October each 6,188 areas; both use April population. There is no saved April 2027 population output in this reference.
- `reports/launch/nowcasting_2026_04/population_projection/countries_2025_population_merged.csv`: country population reference.

The old cap rule is explicit in `population_projection_summary.json:18`: if summed estimated country population exceeds 110% of the 2025 reference, set it to 95% of that reference and scale phase populations proportionally. Old October has 19 capped countries; total population changes from 2,106,501,620.657281 to 1,429,568,874.4239516 (`:4-9`). The user subsequently confirmed retaining this rule for the new task. Area and aggregate outputs must use one consistent denominator convention and preserve the raw counts/scaling factors.

Old population outputs contain disjoint phase shares and counts. Their P3+ counts equal the sum of disjoint phase3/4/5 counts, but differ from population × raw phase3_worse_pred in 36 April and 24 July rows. The old share-repair/cap producer was not found in the searched repository scripts/src/notebooks/docs/reports; original code lineage remains unresolved. The follow-up below reconstructs the saved shares numerically, without claiming the original implementation was located.

Follow-up read-only numerical reconstruction (frozen ipcch-geo interpreter, round-trip CSV parsing): let q2..q5 be saved cumulative predictions. Construct `[1-q2, q2-q3, q3-q4, q4-q5, q5]`, clip each component to[0,1], then divide by their row sum. This exactly reproduces all saved phase1..5 shares in the April6,188 rows and July/October12,376 rows, maximum difference0.0. There are36 April and24 July/October rows with a negative uncorrected component. This establishes a reproducible formula matching these artifacts, not original producer lineage or behavior outside these saved cases. The user selected this rule for new population reporting, with raw compact predictions saved separately. This does not authorize changing raw fitting/classification, adding a rounding step, or silently fixing invalid nonfinite predictions.

`prediction_distribution_summary`/`predicted_phase_distribution` in the old launch are area distribution statistics, not population-weighted aggregates (`launch_nowcasting.py:1413-1430`). Population is for postprocessing and is not added to the compact model features.

## CDS calendar finding: resolved statistical months

`C/c3s_seasonal_apr2026_all_leads.grib` SHA256:
`b657fcbef5dc1c0e3a12328c7664153a5d5d1097ddcc1b133e8c03f39abd939d`.

This is April 1, 2026 initialization, ECMWF system51, method1, ensemble mean, 12 GRIB1 messages. Actual statistical months are April–September, not May–October:

| Messages (temperature/rain) | forecastMonth | verifyingMonth | statistical interval ends | validityDate / existing processed label |
|---|---:|---:|---|---|
| 1/2 | 1 | 202604 | 2026-04-30 23:59:59 | 20260501 / May |
| 3/4 | 2 | 202605 | 2026-05-31 23:59:59 | 20260601 / June |
| 5/6 | 3 | 202606 | 2026-06-30 23:59:59 | 20260701 / July |
| 7/8 | 4 | 202607 | 2026-07-31 23:59:59 | 20260801 / August |
| 9/10 | 5 | 202608 | 2026-08-31 23:59:59 | 20260901 / September |
| 11/12 | 6 | 202609 | 2026-09-30 23:59:59 | 20261001 / October |

Read-only research used ecCodes 2.47.1 and verified original Section1 octets 56–59 (verifyingMonth), 60 (averagingPeriod), 61–62 (forecastMonth). The main session independently checked messages 1/2/11/12, including interval month/end and units. The statistical period is one month. `validityDate` is the following boundary. `stepType=instant`/startStep=endStep reflect the GRIB1 base encoding and do not override local monthly-mean semantics.

Official evidence:

- https://apps.ecmwf.int/codes/grib/format/grib1/local/16/ — local definition16 is seasonal forecast monthly mean data; verifyingMonth is the verifying YYYYMM; accumulated fields' monthly means are mean rates of accumulation.
- https://github.com/ecmwf/eccodes/blob/2.47.1/definitions/grib1/local.98.16.def — lines17,19-30,32-44 derive the month-end statistical interval and forecastTime=forecastMonth-1.

Current `C/postprocess_c3s_seasonal_grib.py:147-149` renames cfgrib valid_time to valid_month; fallback `:155` also adds forecastMonth without subtracting1. Thus both routes introduce a one-month label shift. Existing processed CSV `A/spatial/cds_api_tif_values_by_area_time.csv` (SHA256 `2bb7cb14660f1a80e49ce8349dd73cd78d61b56e3a3cad66ed183b9b69259809`) has 37,362 rows/6,227 areas and labels May–October, but these labels cannot establish actual May–October coverage.

Consequently compact O+1..O+6 requires May–October and the local raw GRIB lacks true October. Do not silently substitute September, realized October, or a later initialization. No data download or relabeling was executed.

### Official CDS catalogue checks

Public GET research on2026-10-08 confirms the current monthly surface products expose leadtime_month1..6 for ECMWF system51, year2026, April initialization. Official CDS instructions state that lead1 is the initialization month. True May–October would therefore require lead2..7, and October is not available through these monthly catalogue selections. The model's underlying215-day forecast length does not establish lead7 availability in the monthly CDS product. Other raw-frequency products were not checked.

- Monthly absolute dataset: `seasonal-monthly-single-levels`; constraints include ensemble_mean and hindcast_climate_mean for the specified system/date: https://object-store.os-api.cci2.ecmwf.int/cci2-prod-catalogue/resources/seasonal-monthly-single-levels/constraints_4234eabbf9ce84bf0d5e652d6e080fa0fa506182193f294c1f457843015cb7df.json
- Official lead definition: https://confluence.ecmwf.int/display/CKB/How+to+use+the+CDS+interactive+forms+and+CDS+API+for+seasonal+forecast+datasets
- Ready anomaly dataset: `seasonal-postprocessed-single-levels`, https://cds.climate.copernicus.eu/datasets/seasonal-postprocessed-single-levels?tab=overview
- Anomaly constraints: https://object-store.os-api.cci2.ecmwf.int/cci2-prod-catalogue/resources/seasonal-postprocessed-single-levels/constraints_a77e254b0195aed9ae3c48646495b7c52ac57088522e556f62df1f5c336102b2.json ; main session independently read array item35 and confirmed ECMWF51/year2026/April, leads1..6, ensemble_mean/monthly_mean and both required anomaly variables. Catalogue constraints are mutable; this is not proof of a successful data retrieval.

Anomaly variable `2m_temperature_anomaly` has units K of temperature difference, numerically equal to degreesC difference (do not subtract273.15 from an anomaly). `total_precipitation_anomalous_rate_of_accumulation` is a rate anomaly in m/s; converting to monthly mm anomaly multiplies by1000×86400×days_in_the_correct_statistical_month.

The official product definition subtracts each system's matching nominal initialization/lead hindcast mean from real-time member forecasts, then ensemble means average qualifying members. It is an absolute anomaly, not a z score. C3S products' common reference period is1993–2016; this is different from the observed-source1991–2020 compact declaration. Official definitions: https://confluence.ecmwf.int/display/CKB/C3S+seasonal+forecast+product+descriptions . ECMWF51 must use matching system51 hindcasts, not system5: https://confluence.ecmwf.int/display/CKB/Summary+of+available+data . Underlying ECMWF hindcast coverage may extend beyond the common product reference period; selectable archive years do not redefine that product baseline.

Using the official anomaly avoids inventing an observed climatology conversion, but does not prove equality with the observed multi-source anomaly or its spatial aggregation. The user accepted the1993–2016 model reference versus1991–2020 observed reference difference. Preserve both source/baseline definitions and do not claim same-data lineage.

### Original-frequency October coverage

Further public metadata research found a possible route for complete October from the same April initialization, not from a later vintage. Official catalogue: https://cds.climate.copernicus.eu/api/catalogue/v1/collections/seasonal-original-single-levels . It identifies constraints at https://object-store.os-api.cci2.ecmwf.int/cci2-prod-catalogue/resources/seasonal-original-single-levels/constraints_f425683807414ff1806175fadd4862fae5bfa54baad5524d89c59a087da5d191.json .

For ECMWF/system51/month04/day01, temperature rows87/1017 expose leadtime_hour6..5160 in6-hour increments, and precipitation rows93/1023 expose24..5160 in24-hour increments; years1981..2026 include all1993–2016 reference years and2026. April1→October1 is4392hours; April1→November1 is5136hours. Thus the advertised coverage permits a full October forecast and matching April-init hindcast baseline. Catalogue allowance does not prove a successful retrieval or complete downloaded fields.

Original dataset descriptions state temperature is6-hour instantaneous K and precipitation is m accumulated since forecast start, available at24-hour intervals: https://cds.climate.copernicus.eu/datasets/seasonal-original-single-levels?tab=overview . October precipitation total can be computed from accumulated fields at5136h minus4392h. Temperature requires a declared monthly sampling boundary/weight rule, not a guessed off-by-one timestamp window. A model anomaly requires aggregating matching1993–2016 hindcasts and subtracting their climatology.

This is a locally constructed October model anomaly, not a downloaded official October monthly-anomaly product. Exact provider aggregation/member treatment and numerical equivalence have not been established. The user confirmed this route to preserve the full six-month window. Verify aggregation against an overlapping official monthly product before accepting the October construction. Source identity, sampling, unit conversion, hindcast years/members and coverage must be recorded. No raw-frequency download or aggregation was executed. Stop and report if retrieval or aggregation validation fails; no missing-month fallback has been authorized.

Credential availability: user identified home `.cdsapirc`; checked `/home/swl007007/.cdsapirc` exists and is readable. No contents/keys were read or printed, and no retrieve job was submitted. Current stage remains planning.

## CDS physical values and anomaly-definition gap

Raw rain is mean rate m/s; temperature is K. The extractor samples raster values at area centroids, multiplies rain by3600 and leaves temperature unchanged (`C/extract_cds_tif_values_by_area_time.py:49-51,62-72`). Processed CSV rain is therefore m/hour. Unit conversion alone is:

- P_month_mm = CSV_rain ×1000 ×24 × days_in_correct_statistical_month.
- Tmean_C = CSV_temperature −273.15.

The user selected retaining the existing fixed-point extraction for newly downloaded forecasts and hindcasts. Reuse `A/spatial/unique_area_id_lat_lon.csv` after unique-area/finite-coordinate validation; sample the containing raster cell as the old `rasterio.sample` path does, without interpolation or a new polygon/crop-mask mean. Source grid/CRS/longitude orientation must be checked before extraction. Apply one spatial rule to all months and reference years, and preserve its source hash. This accepted choice does not verify equivalence to the observed export's spatial weights.

These are absolute values, not compact oracle anomalies. The compact realized source is `S/climate_monthly_2015_2026_MODELING_READY.csv`, SHA256 `8082b72ea5fa5c30a7b975b89c1fbbb4530f27a9ce6c5ba4d0e1a4f923320c89`, with two oracle variables `prcp_anom_month_ensmean,tmean_anom_month_ensmean`. Its header has source anomalies but no paired absolute values/climatology means, so the baseline cannot be recovered by absolute−anomaly from this CSV.

Declared varlist (`S/climate_agriculture_varlist.xlsx`, VARLIST!E5/E9) uses source-specific1991–2020 calendar-month climatology, crop-area polygon weighting and available-source equal mean (precipitation CHIRPS/PERSIANN/ERA5Land; temperature CPC/ERA5Land). These are declarations, not verified upstream generation lineage.

Documentation is inconsistent: `S/climate_feature_sample/workload documentation.docx`, XML paragraph8 says complete polygon without crop masking/weighting; paragraph29 says crop-mask agricultural weighting. That document describes 2022–2026 seasonal output and cannot certify the monthly2015–2026 export. `Climate_Exposure_Data_Sources_and_Methods_Updated.docx` paragraph7 declares ASAPv04 and crop_fraction×pixel_area weights. Local `D/ASAP_land_cover` contains v02, not v04. Existing polygons and crop_fraction do not establish the monthly export's raster weights.

Within S, CDS_API, assembled metadata/spatial, and adjacent local source scripts, research found no numerical1991–2020 per-area/month baseline, linked pixel-weight table, upstream climate-generation code, or ready CDS-to-compact-anomaly conversion. `C/USAGE.md:208-222` describes hindcasts generically. Repository builders already flag undocumented supplier climatology fitting (`build_origin_safe_climate_idp_inputs.py:211`; `build_compact_climate_weather_oracle_inputs.py:228`). Absence is limited to that searched local scope; GEE/cloud sources were not inspected.

Design must resolve the forecast-to-observed anomaly mapping and needed baseline/aggregation inputs explicitly. Directly filling K/m-hour into anomaly columns is invalid. Switching to the old absolute-weather oracle, model-climatology anomalies, a truncated window, or new spatial weights is a change of scientific contract and needs a user decision.

## Maps and output boundary

Existing categorical map rendering and spatial join guardrails are reusable. The geometry has 6,227 polygons; old launch maps joined all6,188 prediction areas. Existing continuous P3+ map helpers use raw cumulative×100 and hardcode four scopes (`plot_forecast_weather_phase3plus_maps.py:34-59`). The user selected both categorical and continuous maps for the two arms/three targets. Use explicit H0/H6/H12 inputs, with no invented H3 run. Categorical crisis is raw-derived overall_phase_pred>=3 (`launch_visualizations.py:107-110`); continuous population-share maps and paired difference maps must switch to approved repaired shares, preserving raw model columns separately. Record which statistic each figure uses and compare the plotted values with population-table values.

Read-only October9 aggregation check on the saved April area reference and current region mapping:6,188 unique areas,53 countries, exactly one region match per area, regions0..8 all represented. Region counts0..8 are1045/858/1059/1100/801/365/50/904/6. Population is nonmissing and nonnegative, with six zero-population Sudan areas3320/3359/3368/3373/3378/3570. All region population sums are positive. These are legacy reference checks, not regenerated compact launch population evidence. Preserve zero-population prediction rows and flag their population counts as zero rather than inventing a population imputation or deleting their model/map records. Negative/nonfinite population is not a valid population denominator. Population aggregation should sum phase counts and denominators, then form weighted shares; the old map's mean_percent is an area-weighted descriptive statistic, not a population share.

The old weather-group comparison is an explicit artifact, not an actual-label error map: `results/launch/nowcasting_2026_04_forecasted_weather_scopes/ipcch_2027_04_global_phase3_worse_pred_forecast_weather_diff_summary.json:3-5` defines forecast-weather P3+ minus without-weather P3+, with explicit paths to both old H12 launches. The user selected recreating paired compact launches. This requires fresh no-oracle H6/H12 fits, not reuse of old deep/annual-evaluation models. H0 is shared because it has no future-weather oracle: five unique model sets, four cumulative regressors per set,20 fitted models. No fitting has started.

### Complete April population/static and mapping source checks

Prior planning probes identified `A/features/forecasting_subset_IPCCH_2026_target_corrected_deep_features.csv` as the complete April source for keys/static29/population only; SHA256 `60610cd601e4b0c700cc475903fe807f072f131a97c543dc22f169b2824917e4`. Selected-column/chunked checks returned6,188 unique areas/53 countries; April population exactly matched the old launch per area, with no missing/negative values. Static29 matched the2,774 compact April rows, including NA masks. Comprehensive popdensity has4,880 missing values; the other28 static columns are complete. Interim April population has3,414 missing values and cannot be used for the full denominator. The six zero-population areas listed above remain in all predictions/maps. These findings are inherited planning evidence, not a new full-file scan or newly generated model inputs.

`A/country_area_id_lookup.csv`, SHA256 `e2baf6ae9481b42b127db5ce81f3c53ad784bb08ae56dfa56cea74e416b44c90`, has empty Namibia ISO2 and empty Cote d'Ivoire ISO3 for31 areas. Exact country names join all53 countries to the reference. Report/cap joins use those names; IDP retains existing ISO3 behavior and NA when unmapped. Preserve the population-reference literal Namibia `lookup_code_used="NA"`; default pandas NA parsing must not erase it. Do not invent missing country codes.

The country reference `reports/launch/nowcasting_2026_04/population_projection/countries_2025_population_merged.csv`, SHA256 `c348cc30cd2b5beae93a11974c4712a3dd6dd822ee902f5458a778effad389b0`, is dated2025-07-01. The retained full-cohort cap covers19 countries/4,004 areas. The raw/effective population totals are those recorded above. Region mapping SHA256 is `18ab5099ce2d1154fb5686183ee399124e18427cc1594923f7abe2769da1611d`; its actual header is `area_id,region`, without country columns. The user adopted area/country/region/global summaries and paired differences, retaining all region codes0..8.

Canonical model coordinates come only from the parent identifier source `A/raw/IPCCH_2026_completed.csv`, SHA256 `ae696087c3bbb280537ae269a05924133acdb51060d31290523404fa8a717673`; its forward-filled weather is forbidden. CDS extraction uses the separate fixed points `A/spatial/unique_area_id_lat_lon.csv`, SHA256 `3bf8f115ec70cd1e1c907031309b797410a8024cdc1d39265be123ae636d2862`. Preserve the distinction and tiny rounding differences. Production preflight must recheck every consumed source byte and join.

### Current interpreter/package boundary — read-only check, 2026-10-09

Both interpreters execute Python3.12.3 in separate venvs, with system-site-packages disabled. Metadata/spec checks found:

| Package | Frozen model venv | Existing CDS_API venv |
|---|---|---|
| NumPy / pandas | 2.4.4 / 3.0.3 | 2.4.6 / 3.0.3 |
| sklearn / XGBoost | 1.8.0 / 3.2.0 | absent / absent |
| pytest | 9.0.3 | absent |
| rasterio | 1.5.0 | 1.5.0 |
| geopandas / matplotlib | 1.1.3 / 3.10.9 | absent / absent |
| cdsapi | 0.7.7 | 0.7.7 |
| eccodes Python distribution / cfgrib / xarray | absent / absent / absent | 2.47.0 / 0.9.15.1 / 2026.4.0 |

Actual `import pytest` succeeded in the model venv. Actual `import eccodes,cfgrib,xarray,cdsapi` succeeded in the CDS venv; the linked ecCodes API is2.47.1 (`eccodeslib`2.47.1.20), distinct from the Python distribution version. No Client was instantiated, no credentials read and no GRIB decode/network request was performed. Package presence is not weather or launch acceptance.

Frozen runtime evidence: `src/ipcch/compact_features.py:75,457-475` declares/checks3.12.3/2.4.4/3.0.3/1.8.0/3.2.0. Therefore compact matrices cannot run under the CDS venv. The final plan uses the same preprocessing CLI in a weather-only CDS stage and an assemble-only model stage, with explicit cube/provenance files between them and imports separated. Pure weather arithmetic/metadata tests can run in model pytest; actual decoder/overlap evidence must come from the CDS stage. Existing CDS import/CLI examples are `C/download_c3s_seasonal_apr2026.py:11,31`, `C/postprocess_c3s_seasonal_grib.py:11-13,61-71`, `C/extract_cds_tif_values_by_area_time.py:10-11`, `C/USAGE.md:16-25`. No dependency installation is required by the inspected capability inventory.

No new fitting, downloading, processing, scoring, plotting, implementation, audit enrollment/start or final acceptance has occurred.
