# Preflight checkpoint — compact_cds_launch_v1

Status: **passed** (2026-10-09T05:05:36Z, 189.8 s). Machine record: `research/preflight-checkpoint.json`.

Command (repository root): `PATH=/tmp/ipcch-windows-git-bin:$PATH PYTHONPATH=src /usr/bin/time -v /home/swl007007/.venvs/ipcch-geo/bin/python .trellis/tasks/10-08-compact-cds-launch/research/preflight.py` -> exit 0. A first run exited 0 with `passed=false` only because the CDS-environment probe referenced a non-existent `cdsapi.__version__`; the probe was fixed (package metadata) and the whole preflight rerun.

## Identity

- Git HEAD b19d36d210bcb59ca090b9e1e961657225f44d39 on `task/compact-climate-weather-oracle`; porcelain at run: task files only.
- Model runtime: {"python": "3.12.3", "numpy": "2.4.4", "pandas": "3.0.3", "sklearn": "1.8.0", "xgboost": "3.2.0", "executable": "/home/swl007007/.venvs/ipcch-geo/bin/python"}
- CDS runtime (weather-only stage): {"python": "3.12.3", "executable": "/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/Google fund/Analysis/1.Source Data/CDS_API/.venv/bin/python", "numpy": "2.4.6", "pandas": "3.0.3", "xarray": "2026.4.0", "cfgrib": "0.9.15.1", "eccodes_python": "2.47.1", "eccodes_lib": "2.47.1", "cdsapi": "0.7.7", "ecmwf_datastores_client": "0.5.1", "rasterio": "1.5.0"}
- Configs: forecasting 3742300661466f22…, P3 cdc0e55aa15bdda9… (match). Helper sha256 snapshot of 13 reused/legacy files recorded.
- Disk free 243.8 GB. `~/.cdsapirc` exists/readable; contents not read.

## Sources

- All 12 pinned design sources match their SHA256; 39 files consumed through the compact/parent manifests (datasets, history/IDP/season/oracle ledgers, cohort, contract copies, parent inputs) match; compact build-code bytes equal the manifest.
- Contract: 308 unique literals; all five projections (296/296/296/308/308) equal the metadata lists, the compact manifest arms and the run-index schema hashes.
- Approved spec/contract bytes copied to `/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/Google fund/Analysis/1.Source Data/assembled_IPCCH/model_ready/compact_cds_launch_v1/approved_spec` (13 files, hashes equal).

## Cohort, static, population, joins

- April 2026 comprehensive source: 6188 rows, 6188 unique areas, no duplicates. Population: 0 missing/negative/nonfinite, 6 zero (Sudan [3320, 3359, 3368, 3373, 3378, 3570]), total 2106501620.657281; equals the old launch area table for all 6188 areas (max diff 0).
- Static29 equals all 2774 compact April rows (values and NA); popdensity NA 4880.
- Country lookup: 0 unmapped, 53 countries; empty ISO3 ["Cote d'Ivoire"] (31 areas); empty ISO2 ['Namibia']. Reference: 53 exact names one-to-one; Namibia lookup_code_used ['NA']; as-of ['2025/7/1'].
- Cap arithmetic: 19 capped countries / 4004 areas; raw 2106501620.657281 -> effective 1429568874.4239516.
- Region map columns ['area_id', 'region']; 0 unmapped; counts {'0': 1045, '1': 858, '2': 1059, '3': 1100, '4': 801, '5': 365, '6': 50, '7': 904, '8': 6}.
- Coordinates: identifier April rows 6188 (no missing for the cohort); CDS points unique/finite; max |identifier - point| lat/lon 5.0e-11/5.0e-11; 39 points outside the cohort.
- Source grids: interim to 2026-04, climate to 2026-08; 0 cohort areas whose interim span ends before April; reported phases in April 2026 2774 (excluded from fitting/history by the March cap), after April 0.
- Geometry `ipcch_admin_geometry.shp`: 6227 rows, EPSG:4326, 0 duplicate ids, 0 unmatched cohort areas, 39 outside the cohort; sidecar hashes recorded.
- Old artifact inventory (no-overwrite baseline): 488 files under results/launch, reports/launch, CDS_API -> `/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/Google fund/Analysis/2.source_code/Step5_Geo_RF_trial/IPCCH/results/launch/nowcasting_2026_04_compact_cds_v1/preflight/old_artifact_inventory_before.csv`.

## Deferred to the weather stage

- CDS provider retrieval, response identities, GRIB decoding, member/year/step completeness and September overlap validation (weather stage)
- Original-frequency grid/longitude convention of the new GRIBs (checked on retrieval)
- Provider grid note (supervisor, research/provider-grid-check.md): system51 is half-degree-centred 1x1; actual new-field grids/cells are verified on a small representative retrieval before bulk requests.
