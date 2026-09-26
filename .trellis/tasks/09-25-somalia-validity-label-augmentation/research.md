# Read-only planning evidence — validity-period augmentation

2026-09-25. No source modifications, feature generation, model fits or remote pulls. Main agent read the two curl source documents and existing q3 design/implementation/report. Three focused read-only explorations checked source inventory, raw mapping and pipeline reuse. This is feasibility evidence, not a completed data/model audit.

## Authoritative local snapshot

Source root: `/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/Google fund/Analysis/2.source_code/Step0_Initialization_and_construct_Scaffold/curl_new_data`.

`IPC_API_discovery.md:30-53,82-94,119-142` distinguishes canonical area records from Population Tracking, defines Current versus Projected and warns that feature ids are not stable across periods/pulls. `ipc_ground_truth_geojson_comparison_report.md:5-20,122-159,213-247` recommends `outputs/areas_combined_2026-05-15.geojson`, whose values and windows differ from Apr27 rather than merely filtering it. Current inventory, including ignored files, finds May15 combined and annual2017-26 files; no later local snapshot and no locally present Apr27 predecessor or population outputs. `01_compare.py:21` has a stale Apr27 reference.

`00_curl.py:29-42,99-123` requests `/areas` with type=A,period=C and stamps retrieved_date/source_year. Combined metadata says May15 and17507 features. Annual Somalia2022-26 property records exactly match the combined subset after adding source_year. API country SO, condition A, period C; ids/anl_id are strings, dates `%b %Y`. Numeric checks below filter SO and group `(anl_id,from,to)`; these are API feature counts, not IPCCH admin counts.

| Year | Analysis | Validity | Source features |
|---|---|---|---:|
|2022|24755659|Jan-Jan|18|
|2022|25817951|May-May|18|
|2022|26601265|Jul-Sep|362|
|2022|26777665|Oct-Dec|372|
|2023|33607389|Jan-Mar|342|
|2023|54775925|Mar-Mar|348|
|2023|59090932|Aug-Sep|348|
|2024|65024769|Jan-Mar|355|
|2024|69455744|Jul-Sep|355|
|2025|77294491|Jan-Mar|355|
|2025|82913971|Jul-Sep|355|
|2026|93850564|Jan-Jan|328|
|2026|87143405|Jan-Jan|107|
|2026|87143416|Apr-Jun|107|

There are3770 features;2951 span multiple months. Inclusive endpoint-month expansion produces9324 feature-months before spatial mapping/deduplication. Month-inclusive semantics is a proposed interpretation, not an established day-level API contract. March2023 overlaps two analyses with161 shared titles and no shared feature ids. January2026's two analyses have no identical titles; spatial overlap is untested. The107 January records from87143405 and107 April-June records from87143416 have identical title sets but different feature ids.

Analyses metadata has `created/modified`, not `analysis_date`. Joining by anl_id shows created later than validity start for all3770 records and later than validity end-month for1181 records (2022:398,2023:348,2026:435). Do not automatically equate created with publication/availability or validity date. `analysis_date` appears in the separate Population Tracking parser `00_curl_population.py:47-71`, not in a verified local population artifact.

## Raw/source linkage gap

Raw: `Analysis/1.Source Data/assembled_IPCCH/raw/IPCCH_2026_completed.csv`, registered by `src/ipcch/paths.py:35`, keyed admin_code/year/month, with lat/lon, phase shares and overall_phase but no API row/analysis/validity fields. `data.py:114-133` source_files records fs input filenames, not raw API lineage.

Located upstream `assemble_latest_IPCCH/03_correct_ipcch_targets.ipynb`: lines1663-1665,1806-1820,2122,2152-2165 match same API from month and projected centroid distance<=1km; lines2606-2608 overwrite labels. GeometryCollection is excluded. Saved all-country output at2094-2097 reports21317/1219868 matched and63 multi-candidate rows; do not quote as Somalia coverage. Somalia API2024 has371/710 GeometryCollections;2025 has378/710. This existing matcher cannot be assumed sufficient or safe for validity assignment.

Raw nonempty labels include2024 Jan/Jul355 each;2025 Apr/Oct904 each plus Jul64/Sep4;2026 Apr904. API2025 current windows are Jan-Mar/Jul-Sep, hence no same-start-month current record for the904-row raw April/October snapshots. API2026 April has107 feature areas versus904 raw areas; many-to-one spatial relationship remains unquantified. No durable full crosswalk or complete unique-match/conflict rates were found.

Spot examples (raw point falls inside the named API geometry, not a completed boundary crosswalk):

| Raw admin/month | API feature / analysis | Comparison |
|---|---|---|
|1615 /2024-01|65024855 /65024769, Kismaayo (1), Jan-Mar|Both phase3 and shares .15/.50/.20/.15/0|
|1615 /2024-07|69456448 /69455744, Kismaayo (1), Jul-Sep|Raw phase2, shares .55/.30/.15/0/0; API phase3, shares .40/.40/.20/0/0|
|1612 /2024-01|65024901 /65024769, Kismaayo (3), Jan-Mar|Raw phase1, shares .90/.10/0/0/0; API phase2, shares .80/.15/.05/0/0|

These examples establish possible value conflicts, not authority to replace values or proof that a spatial candidate represents the original source report. Keeping raw values and attaching newer windows still needs report/version/period evidence.

## Existing pipeline constraints

- `pipeline.py:114-146` prepares fs frames/raw/V2 and label/history ledgers. `data.build_label_ledger:108-175` takes nonnull overall_phase from fs inputs; labels>=2025 without raw labeled-key provenance become `provenance_unreconciled`.
- `pipeline.py:170-174` inner-joins valid target keys to fs rows before building history/features. Actual Somalia fs0/fs3 have6741 rows, fs1/fs2 have6759, with no null overall_phase. Raw has177364 Somalia area-months/143 columns, no duplicate month keys;2022-24 has905 areas/month,2025 has904/month,2026 only Jan-Apr904/month. Thus unlabeled monthly raw covariates exist, but full monthly fs matrices do not.
- `data.mask_unverified_category_history:342-361` validates/masks preassembled overall_phase_prev_observed_asof_s0/s3/s6; it does not rebuild their values. fs3's overall_phase_lag1 is blocked. Expanding rich history without reconciling these category-history columns could mix source definitions.
- `history.py:129-155,320-338,527-538` constructs last-six actual valid observations and history windows from the ledger. `data.persistence_lookup:365-385` carries latest valid reported phase through min(origin,target-1). q3 residual baseline is hist_q3_obs1/history_obs1_source_ord (`configs/somalia_q3_optimization.json:17-18`, `q3opt.py:200-249`).
- `q3opt.py:140-170,253-265` uses target-month OOF cutoff min(v-H,v-1); calibration takes all rows in selected previous OOF months (`310-332,347-385`), selection uses unweighted pooled RMSE. No source-report grouping exists to separate expanded copies of a single report.
- Naive expansion would count copied months as multiple history observations, alter persistence/residual baseline, multiply weights of long-validity reports, and allow one report on both sides of a month-based split. Decide explicitly which of these changes is intended; do not infer independent information from monthly row counts.

## User steering captured

Expanded-cohort overall results are primary; original/common-sample results are secondary. Proposed main table scores both original-label and augmented-label models on identical expanded area-month truth, including persistence and all-crisis. User has approved raw-value preservation, target-report exclusion in histories and fitting/calibration, original-source availability, and latest-original-month overlap precedence. User rejected report-weight normalization: extended duration intentionally increases total training influence. No augmentation outcome has been computed; implementation and complete expanded-cohort coverage remain unvalidated.

## Follow-up: monthly feature recovery and original-key lineage

Main agent read sibling `assemble_latest_IPCCH/CONTEXT.md`, `specs/003-multiscope-ipcch-features/spec.md` and `specs/001-fix-ipcch-targets/spec.md` in full. These are historical construction contracts, not authority to supersede the new raw-value-preservation or report-exclusion rules. In particular, the old correction spec authorizes target overwrites; this new experiment does not.

- Full monthly deep features already exist at `Analysis/1.Source Data/assembled_IPCCH/features/forecasting_subset_IPCCH_2026_target_corrected_deep_features.csv` (about5.05GB,386 columns). Narrow key inspection confirmed area1615 rows2024-02/03/08/09 exist with missing overall_phase; Jan/Jul are labeled. `build_deep_ipcch_features.py:1103-1132,1147-1148` preserves the complete source row universe through prepare_panel, anchor/rolling, deep-family and spatial-spillover functions.
- Label filtering occurs later: `filter_forecasting_ready_deep_features.py:62-70` filters nonnull/nonzero phase; `organize_ipcch_ml_data_folder.py:109-140` filters scope outputs. Full deep schema differs from saved fs3 only by overall_phase_lag1, which the D pipeline blocks. Confirm exact numeric parity on existing keys before using this as an H12 replacement.
- H0/H3/H6 reuse `build_multiscope_ipcch_features.py:321-368` source/baseline loading and `:977-1017` scenario construction. Its old entrypoint joins a filtered fs3 baseline (`:1027-1047`), so added-month baseline values would be missing unless the full monthly deep artifact supplies that block. `scenario_build` writes files; do not invoke it in planning or assume it is a pure helper.
- Feature shifts use row positions (`build_multiscope_ipcch_features.py:258-267`; `build_deep_ipcch_features.py:396-403,423-468`), so preserve each area's continuous monthly panel when recovering features. Old categorical history uses groupby.shift (`multiscope:646-706`) and must be rebuilt using report-aware label history. Raw/model-target columns must not be taken from corrected-feature artifacts in place of the authoritative preserved labels.
- Rebuilding spatial/static features separately per label branch would change X: static verification depends on supplied panel variability (`deep:355-384`) and spillovers rebuild a three-neighbor graph from supplied areas (`deep:859-908`). Reuse one fixed complete artifact/neighbor definition across branches.
- Original scaffold `01_extract_invariables_and_scaffold.ipynb:53,85,631,671` inherits admin_code from `IPCCH_20260211_geometry.csv`; `:682,698` generates months and `:794,855` joins ACLED by admin_code/year/month. The referenced geometry CSV is currently absent at the inspected paths, and this notebook contains no original API/validity linkage. The nominal sibling `02_preprocess_and_combine.ipynb:20-21,54,189` handles FEWSNET rather than IPCCH. No defensible API crosswalk is established by these notebooks. This is a preflight evidence gap; do not promote proximity matching to verified report identity.

## Main-agent raw missingness check after G2

Read-only chunked pandas scan using `/home/swl007007/.venvs/ipcch-geo/bin/python`, usecols ISO3/year/month/overall_phase/phase1_percent..phase5_percent, chunksize100000; filter ISO3==SOM and year2022..2026. Six-field missingness uses the existing pandas CSV missing parser. No transformations or outputs were written.

| Year | Raw monthly rows | All six missing | Partly missing | All six present |
|---|---:|---:|---:|---:|
|2022|10860|10131|0|729|
|2023|10860|9842|0|1018|
|2024|10860|10150|0|710|
|2025|10848|8972|0|1876|
|2026|3616|2712|0|904|

These are raw missingness counts, not source-QC passes, defensible report matches or counts of added labels. Earlier fs-based valid-label/support counts describe a different source ledger and must not substitute for this task's raw-preservation baseline; reconcile source differences in preflight. The check confirms whole-block blank filling currently excludes no partly missing Somalia2022-26 records, but does not establish any validity match.

## Claude preflight evidence (2026-09-25, read-only, after handoff)

**Label lineage (reconstructed; no saved code or crosswalk).** A read-only search plus session memory show raw Somalia 2025–2026 labels were attached on 2026-05-12 by an unsaved script: features of the now-missing Apr-27 pull (mostly P/A periods) were reduced to area-weighted centroids keyed by year/month of `from`, with `anl_id/id/from/to/title/ipc_period` dropped (`Outcome/IPCCH/areas_combined_after_2024-12-31_with_cadre_harmonise_..._centroids.csv`, header `year,month,lat,lon,estimated_population,phase1..5_percent,overall_phase`), then joined to the admin scaffold by exact lat/lon or nearest point within 200 km. All match columns were dropped; the intermediate files are absent. Every raw SOM 2025-04/10 and 2026-04 label equals its nearest centroid-file point (904 areas from 355–367 source points; max 59.9 km); 2025-07 (64 rows) and 2025-09 (4 rows) are 126–173 km spillovers from Djibouti/Yemen-area polygons. 2022–2024 labels come from the older historical panel (`IPCCH_2017_2025_final_*`), whose construction script was not located. `spatial/ipcch_admin_geometry.dbf` has only `admin_code,lat,lon`. Conclusion: no area- or report-level crosswalk exists locally.

**Round-level timing check.** In the May-15 snapshot each Somalia `anl_id` has exactly one `(from,to)`. For every raw 2022–2024 label month there is exactly one current analysis whose `from` equals that month; 2025-04, 2025-09 and 2025-10 have none (they came from projection-period features); 2025-07 matches analysis 82913971 (Jul–Sep) only by month, but its 64 rows are cross-border spillovers.

| Raw month | Raw labels | Unique current round starting that month | Window end | Blank months that window would fill (≤2026-04) | Already labeled |
|---|---:|---|---|---:|---:|
| 2022-07 | 348 | 26601265 | 2022-09 | 696 | 0 |
| 2022-10 | 348 | 26777665 | 2022-12 | 696 | 0 |
| 2023-01 | 348 | 33607389 | 2023-03 | 647 | 49 |
| 2023-08 | 348 | 59090932 | 2023-09 | 348 | 0 |
| 2024-01 | 355 | 65024769 | 2024-03 | 710 | 0 |
| 2024-07 | 355 | 69455744 | 2024-09 | 710 | 0 |
| 2025-07 | 64 | 82913971 (month only) | 2025-09 | 124 | 4 |
| 2025-04/09/10 | 904/4/904 | none | — | 0 | — |
| 2026-04 | 904 | 87143416 | 2026-06 | 0 (no covariates after 2026-04) | — |

Candidate additions under round-level linking total 3,931 area-months (3,807 excluding 2025-07). All fall in 2022–2024 training years except the 2025-07 spillover; the 2025 and 2026 outer evaluation months gain no labels under this rule.

**Spatial value agreement (diagnostic only).** Raw point-in-polygon against same-`from` API features: 2024-01 344/355 matched (0 multi), overall phase equal 56.6%, exact share vector 7%; 2024-07 59.4%/13%; 2023-08 50.9%/8%; 2026-04 879/904 matched, 60.6%/13%. The API snapshot values are revised/different from the raw labels, so value equality cannot serve as report identity.

**Features.** The full monthly deep file (5.05 GB, 386 columns) equals the fs3 schema except for the blocked `overall_phase_lag1`.
