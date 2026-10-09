# Somalia compact/CDS limited-test feasibility

Read-only planning research, 2026-10-09. No training, downloads or model-code changes. Main agent read the archived compact CDS PRD/design/implementation plan and current backend quality guidance in full. Two independent scouts inspected current source and explicit input/result artifacts; main agent spot-checked the launch constants/training-arm mapping and the country-scope loader rejection.

## Explicit source roots

`A = /mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/Google fund/Analysis/1.Source Data/assembled_IPCCH`

- Compact inputs: `A/model_ready/compact_climate_weather_oracle_v1/compact_climate_weather_oracle_v1_manifest.json`.
- Launch inputs: `A/model_ready/compact_cds_launch_v1/compact_cds_launch_v1_manifest.json` (COMPLETE).
- Country membership: `A/country_area_id_lookup.csv`, exact `iso3 == "SOM"`, 905 unique area IDs. Source role: `src/ipcch/compact_launch.py:74`.
- Historical label cohort: `A/model_ready/origin_safe_climate_idp_v1/origin_safe_climate_idp_v1_cohort_keys.csv`, bound by compact manifest lines 115–122.
- Launch results: `results/launch/nowcasting_2026_04_compact_cds_v1/runs/`, five explicit runs from `src/ipcch/compact_launch.py:47`.
- Historical results: `results/experiments/compact_climate_weather_oracle_v1/runs/`, baseline H0/H3/H6/H12 and oracle H3/H6/H12, annual predictions 2022–2025.

## Measured Somalia coverage

All five existing launch runs, filtered by canonical membership:

| Role | Rows | Unique areas |
|---|---:|---:|
| Fitting keys per run | 5,835 | 905 |
| Launch inference per run | 904 | 904 |
| Accepted weather cube Somalia subset | 905 | 905 |
| Historical label-cohort keys | 6,741 | 905 |
| Historical share-valid rows | 6,739 | not separately measured |
| Historical eval_key rows | 4,933 | 905 |

Fitting months observed: 2017-01 through 2026-01. Counts by year: 2017 190; 2018 190; 2019 190; 2020 192; 2021 139; 2022 1129; 2023 1217; 2024 711; 2025 1876; 2026 1. Training eligibility is the inherited valid-share selection strictly before April 2026; this is not evidence that every lookup area has an April launch row.

Launch lacks area 3146, identified by `A/country_area_id_lookup.csv:3110` (`3146,SOM,Somalia,SO,Somalia`). Follow-up evidence in `coverage.md` establishes that its source series ends December 2024, so the parent April 2026 cohort has no source/population row. Do not silently add it or claim full905-area launch coverage.

All seven historical run outputs had 1,129/1,217/711/1,876 Somalia prediction rows in 2022/2023/2024/2025 respectively, and 585/705/372/904 distinct areas. Combined 4,933 keys, 905 distinct areas; no duplicate `(area_id,year,month)` keys per run. Cross-run full key equality was not checked.

## Weather and modeling semantics

- `src/ipcch/compact_launch.py:40-50`: origin April 2026; H0 April 2026, H6 October 2026, H12 April 2027; H0 shared; four regressors per unique run; seed 42/half-life 24/threshold 0.2/n_jobs16.
- `compact_launch.py:46,205-222`: CDS-weather arm training uses `compact_weather_oracle` realized inputs; fitting labels strictly before April 2026. Weights anchored April 2026. Baseline 296 ordered predictors; weather 308 at H6/H12.
- `src/ipcch/cds_launch_weather.py:47-63`: ECMWF system51, April 1 2026 initialization, May–October forecast. Historical 1993–2016 hindcasts support October climatology; they are not assembled historical evaluation forecasts.
- Accepted launch cube `A/model_ready/compact_cds_launch_v1/cds_weather_cube.csv`: 6,227 rows, area_id plus12 weather columns. Long cube under the explicit `CDS_API/compact_cds_launch_v1/processed` root has 74,724 rows and only statistical months 2026-05..2026-10. Provenance status ACCEPTED; cube SHA256 `8745e7afdbf0e65f36e1ad584ecfc147fb7d6ad5abc8ed16178af33b886e89a4`.
- No historical multi-vintage CDS cube found in the inspected explicit roots. This is bounded evidence, not a claim about every disk path.
- Existing launch predictions have no observed future-target labels; `compact_launch.py:958` labels reporting as prediction summaries, not scores.
- Historical compact/oracle inputs have 52,521 rows and 296/308 feature schemas (305/317 total columns), with frozen annual origin-safe evaluation. Oracle uses realized future anomalies; cannot label its scores CDS performance.

## Reuse constraints

- `scripts/modeling/run_deep_feature_weight_decay_forecasting.py:882-905` explicitly rejects country scopes in origin-safe protocol. Old annual `--country-iso3 SOM` support is not equivalent to the compact protocol.
- Launch runner has no country selector and validates COHORT_SIZE=6188 (`compact_launch.py:50,228-237`). A local subset must use separate result/spec identity and cannot impersonate the complete global manifest/cohort.
- Reusable fitting primitives: `src/ipcch/launch_nowcasting.py:1294-1322` (`resolve_hyperparameters`, `_fit_model`), explicit compact input feature order, normalized targets, origin weights and unrounded cumulative classification.
- Paired launch invariants: `compact_launch.py:556-561`, equal fit keys, targets, weights and baseline feature prefix. Save/replay patterns: `compact_launch.py:674-744`.
- Inference history ends March 2026; ordinary sources/IDP through April; preserve completed-season timing. Training rows retain their own origin-safe history rules.
- Runtime/config contracts are frozen. New local work must not mutate pinned helpers/configs or write into existing accepted launch output directories.

## Confirmed scope clarification

The user explicitly corrected the scope on2026-10-09: BOTH the historical `results/experiments/compact_climate_weather_oracle_v1` experiment and the April 2026 CDS launch need Somalia local-model reruns. The earlier launch-only interpretation is superseded. Historical scoring uses realized-weather oracle, not historical CDS forecasts; no historical CDS retrieval is needed for the corrected request. Launch includes H0/H6/H12 and inherited population reporting (phase1–5/P3+/P4+ shares/counts, absolute levels and paired differences).

Main agent read the historical archived PRD/design/implementation plan in full. Original historical design runs H0/H3/H6/H12, four annual test years2022–2025, shared H0, unchanged fixed configs and eight annual/pooled metrics; anchors: `.trellis/tasks/archive/2026-10/10-08-compact-climate-weather-oracle/design.md:110-143`. The user adopted this complete historical horizon set; launch stays H0/H6/H12. Final PRD/design/implementation plan are ready for review, with execution not started.

## Verification limits

No raw-GRIB rereview, numeric matrix/NaN equality, model-internal inspection, cross-run key-set equality, training or test execution. Follow-up source/cohort coverage facts for 3146 are in `coverage.md`; its upstream removal cause is not certified. Evidence is feasibility research, not experiment acceptance.
