# Follow-up source exploration (2026-10-06)

Read-only findings from three independent agents; no crosswalk generated, model run, test, or acceptance validation. Main session read the complete project quality guidelines. This is planning evidence, not certification of all upstream inputs.

## IDP geographical join

- Existing IDP `output/crosswalk_dtm_admin2_to_gaul2024_l2.csv` has 4056 rows; join `(gaul_iso3,gaul2_code)` to assembled IPCCH `country_area_id_lookup.csv` `(iso3,area_id)` yields zero matches. Bare-code overlap is not identity evidence. DTM Pcode must be paired with ISO3.
- Assembled IPCCH `spatial/ipcch_admin_geometry.shp` has 6227 unique admin_code, whose set equals the lookup's 6227 area_id. Coordinates/geometry identity still needs verification: `assembled_IPCCH/code/build_ipcch_admin_geometry_shapefile.py:153-215` includes unrestricted nearest-coordinate fallback at `:191-201`. No durable fallback-count/distance log located.
- Scaffold generates IDs from lat/lon groups (`../Step0_Initialization_and_construct_Scaffold/01_extract_locations_and_scaffold.ipynb:689-690`, relative to the Analysis code hierarchy); supplementary CH codes are generated separately. Area_id is not a GAUL code.
- IDP admin2 monthly table has 196334 rows, no duplicate country/Pcode/month, 61194 observed non-null stocks. Latest-observation lookup needs to recompute age from origin minus the actual source month, because the monthly grid stops at each unit's last report. Missing spatial support cannot become zero stock.
- A country-level arm can use standardized admin0 stocks joined by verified ISO3, avoiding unproven subnational crosswalks. A district-level arm requires verified DTM/COD-AB to canonical IPCCH geometry mapping and explicit partial-coverage diagnostics.

## Remaining inherited predictors

- Four masked headers retain 379/380/380/290 non-new-climate columns, including keys/targets and 29 empirically invariant static predictors. Dynamic families are GPP, nightlights, conflict, prices/inflation, Nino3.4 and four commodity composites. Their common asof12 block has 250 columns; 0/3/6 scopes add scope features.
- `../assemble_latest_IPCCH/build_deep_ipcch_features.py:355-385` verifies static value invariance, not historical availability. Ordinary common dynamics are anchored t-12; trailing same-month statistics use expanding then shift (`:743-759`).
- `../assemble_latest_IPCCH/build_multiscope_ipcch_features.py:258-267` constructs scope blocks by shifting future carrier rows backward. This produces structural tail NaNs even when actual origin-month values exist. Current climate builder additionally masks 157 new climate/GS columns using that old tail missingness (`scripts/preprocessing/build_climate2015_model_ready.py:115-126`). These are separate defects from history leakage.
- ENSO forecast-sequence naming describes shifted observed Nino3.4, not a verified issued-forecast product (`../assemble_latest_IPCCH/build_multiscope_ipcch_features.py:579-590`). Preserve accurate semantics; no future source dates were proven for this column.
- `estimated_population` is target-side according to the complete project quality guideline (`.trellis/spec/backend/quality-guidelines.md:24`); global selector still admits it. It must not remain silently inherited into an origin-safe experiment.
- Existing CLI drops evaluation rows according to prediction sums; project guidelines prohibit this (`quality-guidelines.md:28-29`). Evaluation keys must be frozen before predictions and shared by all arms.

## Climate standardization evidence gap

- Current 14 ensemble inputs: prcp_anom, prcp_z, rainy_days, cdd, tmean_anom, tmax_anom, hot_days_p95, gdd, edd, sm_z, spi03, spei03, ndvi_anom, evi_anom. Builder directly consumes their monthly/GS ensmean columns (`src/ipcch/climate2015_features.py:18-23`; `scripts/preprocessing/build_climate2015_model_ready.py:81,84`).
- Shared-folder workbook `climate_agriculture_varlist.xlsx` recommends 1991–2020 weather normals/p95 (VARLIST E5/E6/E9/E10/E11), 1983–2020 SPI/SPEI (E14/E15), 2001–2020 soil z (E16), 2003–2020 vegetation (E17/E18). NAMING_QC E25:E28 repeats periods. This recommendation is not tied to an actual export build manifest; source/naming differences exist.
- Shared folder contains no producer scripts/build manifest/actual fitted parameters. Source-period timing can be checked under the chosen proxy, but actual standardization fitted samples remain incomplete. Do not claim historical real-time or complete upstream no-look-ahead validity.
- Found methodological documents for main-session reading: `IPCCH_shared_folder/climate_feature_sample/Climate_Exposure_Data_Sources_and_Methods_Updated.docx`, `climate_feature_sample/workload documentation.docx`, `TOR climate notes.docx`. Agents did not read these foundational documents.

## Next user decision

National DTM context and three paired arms have been selected. The remaining material risk decision concerns current climate exports' unverified upstream standardization. Climate masking and preservation scope will be made explicit in the final spec review.

## Main-session reading of methodological documents

Main session fully read all paragraphs in the three DOCX files by extracting their document XML; no documents were delegated for interpretation. Paragraph numbers below refer to the Word document paragraph sequence.

- `Climate_Exposure_Data_Sources_and_Methods_Updated.docx` P89 specifies precipitation z baseline 1991–2020; P100 specifies SPI 1991–2020, differing from the workbook's recommended 1983–2020. P105–112 describes an empirical-CDF SPEI with a fixed 1991–2020 baseline for a January test, not the classical log-logistic distribution. P175–180 requires baseline and source-version QA. P186–204 distinguishes January test from future full production. It is not a producer manifest for current 2015–2026 exports.
- `workload documentation.docx` P3–4 describes a 2022–2026 release of 62270 rows/87 columns, not the current 2015–2026 release. P8 says whole-polygon exposure without crop weighting; P29 describes agricultural weighting, an internal ambiguity. P66–71 describes soil z threshold abs(z)>20, differing from current monthly abs_ge6 QC column names. P98–99 documents source-wise ensemble means/no post-ensemble standardization; no fitted keys or actual climatology period supplied.
- `TOR climate notes.docx` is intended work, not production evidence; P5 allows interpolation/gap filling without an operational as-of contract. Do not infer that current exports used those techniques.
- These documents improve method interpretation but do not establish actual build version, fitted baseline keys, distribution parameters or source support cutoffs for current exports. Upstream standardization remains incomplete; temporal input/label gates alone cannot certify it.
