# Compact source reconstruction: read-only findings

Two independent read-only explorations checked source headers, parent feature lists and code on 2026-10-08. No builders or model fits were run. The supervisor spot-checked `retained_feature_recipes.py:130-204`.

## Available sources

The 13 retained climate series are the `CLIMATE_BASES` monthly ensemble means except NDVI (`src/ipcch/climate2015_features.py:18-23`), from `IPCCH_shared_folder/climate_monthly_2015_2026_MODELING_READY.csv`. The other 11 series come from `Analysis/1.Source Data/assembled_IPCCH/interim/IPCCH_2026_target_corrected_nino34_wbfood.csv`: GPP, nightlight, violence events, fatalities, WFP, WB index, Nino3.4, and four existing BBG composites. The composite series names end in `__composite_mean`, and definitions are the existing available-member arithmetic means (`src/ipcch/retained_feature_recipes.py:20-29,36-51,123-129`). Parent manifest records climate coverage 2015-01 through 2026-08 and interim coverage 2010-01 through 2026-04; 39 areas end before the interim maximum. These are manifest ranges, not per-source nonmissing coverage guarantees.

## Three kinds of missingness

1. Source-native missingness and insufficient rolling/historical support: governed by D13 and existing stress logic D14.
2. Carrier-row missingness: old features are computed as T-12 arrays, masked by whether that carrier row exists, then shifted to origin using `offset=12-H`. Thus the origin O feature can require a row at O+12 even when its actual source at O is available (`src/ipcch/retained_feature_recipes.py:135-150,162-170`).
3. Extra saved NA: `compare_columns` permits saved NA where the reconstructed recipe has a value, status `verified_saved_missing_retained` (`src/ipcch/retained_feature_recipes.py:180-204`). The old builder retains saved values (`scripts/preprocessing/build_origin_safe_climate_idp_inputs.py:344-357`). Existing H0 classification evidence records 25 such cells for GPP historical z and 1,586 for nightlight historical z (`results/experiments/origin_safe_climate_idp_v1/input_checks/feature_classification_h0.csv:357,361`). Their precise causes were not established in this exploration.

Concrete example from the source reader: area 3118, 2025-10 has nightlight=0, WB index=1.3849999999999998, Nino3.4=-0.5 in interim. The parent H0 model-ready row at line 22054 has all three corresponding origin fields missing. The old carrier would be 2026-10, beyond the interim maximum 2026-04. Rebuilding at O would restore these values; this example is source/code reasoning, not a new-builder run.

## Planning consequence

Filtering old fitted columns cannot implement the request: some newly required origin SDs, BBG rolling fields, and origin z/MA fields never existed (`src/ipcch/retained_feature_recipes.py:69-110,162-172`). All 24 ordinary sources are technically reconstructible directly at O using existing monthly grids, without carrier masks. The user subsequently approved D16: use source-native missingness, removing carrier-tail and saved-extra-NA masks. D14 freezes the stress algorithm, not the separate carrier-table masks.

## Exact schema checks

The four parent `results/experiments/origin_safe_climate_idp_v1/runs/climate_safe_history_idp/{0,3,6,12}m/run_metadata.json` files have `features` counts 870/870/870/654; hashes match the existing model-run index. The 29 static, 27 coordinate/calendar, five history and two IDP literals have identical relative order across horizons. H0 anchors are lines 30-58 and 866-899. Preserve their literal names and relative order. Calendar columns encode target T, not O (`src/ipcch/forecasting_weight_decay.py:160-162,183-185`). Expected compact count is 296; the seven-run expected counts are 296 baseline at all horizons and 302/308/308 for raw oracle H3/H6/H12.

No full source hash scan, new matrix generation, per-feature coverage calculation or original RTP-to-area ETL verification occurred in these explorations. The earlier RTP-definition evidence remains applicable. New compact column naming and final order are implementation contract details to specify in design/CSV after scope convergence.
