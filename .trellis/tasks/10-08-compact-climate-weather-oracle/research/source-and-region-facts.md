# Source and regional facts — 2026-10-08

Read-only planning evidence. This is not an approved specification or execution result. Paths beginning with `Analysis/1.Source Data` are relative to `Google fund`; `IPCCH_shared_folder` is under `IFPRI Dropbox/Weilun Shi`.

## Existing World Bank RTP index

- `Analysis/1.Source Data/WB_RTP_price/filter.ipynb:830,842-843,866` selects food-price-index open/close fields, computes `food_price_index_WB=(o_food_price_index+c_food_price_index)/2`, exposes inflation as `food_inflation_wb`, and exports `wb_food_price_index.csv`.
- The derived header is `inflation_food_price_index,year,month,lat,lon,food_price_index_WB,food_inflation_wb`.
- `src/ipcch/retained_feature_recipes.py:20-28` includes these existing series. D4 retains the original RTP index definition and excludes inflation; no new commodity feed is requested.
- Raw `WLD_RTFP_mkt_2026-04-20.csv` has 781 columns, 755,647 rows, 40 countries and 3,325 distinct market IDs; `(ISO3,geo_id,DATES)` is unique. Dates span 2007-01 through 2026-04. The raw file includes market-level/national-average series, metadata, commodity fields and `o_/h_/l_/c_/inflation_/trust_` series.
- Neither raw nor derived schema provides row-specific release/vintage fields. `last_survey_point` can refer to March 2026 even on a 2007 observation row; it cannot certify historical availability. Inherited source-to-area provenance should be checked, without inventing a new mapping or retrospective release dates.

## Latest completed growing season versus major-season identity

- `IPCCH_shared_folder/climate_2015_2026_MODELING_READY.csv:1` contains `admin_code,season_year,season,gs_sos,gs_eos,gs_cross_year,gs_calendar_valid,gs_start_date,gs_end_date_exclusive` and related support fields. It contains no major/main/primary flag.
- This table has 149,448 rows, 6,227 areas, and two labels `s1/s2`, each with 74,724 rows. Example area0/year2015 has s1 beginning 2015-06-23 and ending exclusive 2015-12-06, while s2 begins 2014-11-25 and ends exclusive 2015-05-01. Numbering alone does not establish timing order or agronomic importance.
- `climate_feature_sample/workload documentation.docx`, XML paragraph3: "Each administrative unit contains two potential growing seasons, identified as s1 and s2." It does not establish s1=major.
- `climate_feature_sample/Climate_Exposure_Data_Sources_and_Methods_Updated.docx`, XML paragraph8 identifies WorldCereal S1/S2 day-of-year SOS/EOS and cross-year rules, without a major-season mapping.
- The available `climate_agriculture_varlist.xlsx` was also searched for major/main/primary/S1/S2; no major-season rule was found. This absence is limited to inspected supplied files and does not establish upstream WorldCereal semantics.
- `src/ipcch/climate2015_features.py:288-320` selects the latest two seasons with exclusive end <= first day of O+1, prefers later-starting seasons on tied end dates, and emits metrics/age only. It currently does not return the season label or apply a calendar-valid/full-window filter.
- Older Somalia V2 `src/ipcch/somalia_oracle/data.py:282-296` has additional completeness logic; it is a different source contract and must not be silently applied to the current source.
- User defined major as the longer of s1/s2 (D5). Compare date-derived calendar durations, never realized rainfall or partial available support. Full read-only scan: 74,724 pairs, s1-longer26,154, s2-longer48,198, equal372; no invalid rows, date-derived and stored recalculated durations agree, and SOS/EOS calendars are fixed per area across years. D6 resolves equal/uncomparable/no-season cases as NA; D10 retains two completed seasons with a major dummy only for the latest.

## All-region metrics without bootstrap

- `data/reference/area_id_country_region_mapping.csv:1` contains only `area_id,region`; 6,227 unique IDs, no missing IDs/regions.
- Region0..8 counts: 1045,859,1059,1104,833,366,50,905,6. Include region0 in scope unless explicitly excluded by the user; do not invent labels for numeric regions.
- The full mapping ID set equals the seasonal-source admin-code set. Final prediction cohort coverage still requires validation.
- `src/ipcch/origin_safe.py:387-424` exposes the existing eight metrics, support and undefined-value reasons and does not bootstrap.
- `scripts/postprocessing/evaluate_region3_saved_predictions.py:66-75,148,166` provides strict missing-membership checks and calls the common metrics, but hardcodes region3 and subsequently bootstraps; do not run it unchanged for this requirement.
- `scripts/modeling/compare_global_vs_regional_by_region.py:180-232,333-361` is not an exact substitute: it tolerates/drops some unmapped rows, skips groups under5 rows, and computes only four metrics.

## Coverage limits

No model or raw data was changed. No upstream RTP method/vintage or WorldCereal major-season definition was independently certified. Repository searches used Windows Git where Git was needed; some WSL directory scans had intermittent I/O errors.
