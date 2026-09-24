# Focused planning evidence — 2026-09-24

Read-only exploration to inform brainstorming, not a completed model/data audit. No model training was run.

## Existing model contract

- `scripts/modeling/run_deep_feature_weight_decay_forecasting.py:264-295,322-345` fits four XGBRegressors (`phase2_worse` through `phase5_worse`), with phase-3-specific parameters and cumulative phase conversion. It is not a bagged or multi-seed average. Reuse this project's cumulative-model ensemble as requested.
- The same script at `172-203,697-704` filters training and evaluation to Somalia through the country lookup. Its `252-270` loads static hyperparameter JSONs; this entrypoint does not perform a hyperparameter search. The provenance/date scope of the existing parameter selection has not been established.
- `src/ipcch/forecasting_weight_decay.py:194-237` selects numeric predictors by exclusion patterns; `331-352` drops missing target rows per model and leaves predictor NaNs. `287-302` weights by age relative to test-year January, with a default 24-month half-life. The requested per-origin fitting requires an explicit weighting reference in the design.
- `src/ipcch/forecasting_weight_decay.py:240-257` uses all-prior-target-history annual splits for fixed test years 2022–2025. This must be adapted for the newly approved candidate windows plus per-O cutoff.
- `src/ipcch/forecasting_weight_decay.py:368-415` reports phase accuracy, P3+ precision/recall/F2, and P3+ share R-squared.
- `scripts/modeling/run_region_models.py:301-355,809-815` is a separate older region workflow with 2022–2024 tests; it is not the preferred Somalia-specific entrypoint.

## Reuse checks required before fitting

- Current fs3 input contains `overall_phase_lag1`, which the broad numeric selector may admit. `src/ipcch/launch_nowcasting.py:998-1007` explicitly excludes that field as target-derived. Trace/reconstruct its availability relative to each O or exclude it; retaining original variables does not authorize leakage.
- `scripts/modeling/run_deep_feature_weight_decay_forecasting.py:283-287` removes rows with nonpositive summed cumulative truth/predictions during phase conversion. Verify resulting eligibility and phase-1 handling; predictions must not silently select the scoring denominator.
- fs3 is labeled only `forecasting` in `src/ipcch/forecasting_weight_decay.py:41-52`. Its external input has `asof12` columns. External metadata `assembled_IPCCH/metadata/forecasting_subset_IPCCH_2026_target_corrected_deep_features_forecasting_ready_summary.md:38-43` describes t-12 dynamic features; this does not prove the full new O/T availability contract.

## Label and weather availability

- `src/ipcch/paths.py:12-39` resolves the raw `assembled_IPCCH/raw/IPCCH_2026_completed.csv`, model-ready feature scopes, and forecast weather inputs. Focused header inspection of seven related CSVs found year/month or forecast time, but no separate label publication/availability timestamps. This is a limitation of the inspected artifacts, not proof that upstream release records do not exist.
- The existing fs0 model-ready source has 905 labeled Somalia rows in 2026: one in January (`area_id=100011`) and 904 in April. Raw `IPCCH_2026_completed.csv` has no Somalia labels in January–March and 904 in April. The isolated January model-ready label requires provenance reconciliation before inclusion.
- Raw Somalia rain and temperature fields are populated for 904 areas in each month January–April 2026. March and April values are exactly equal for all 904 paired areas in BOTH `Rainf_f_tavg_mean` and `Tair_f_tavg_mean`. This is a provenance warning, not proof of the copying mechanism; April values must not be called independent realized April observations without tracing their source.
- The default `cds_api_tif_values_by_area_time.csv` provides forecast weather for May–October 2026 (905 Somalia rows/month). These are forecasts and cannot substitute for the requested realized oracle weather.
- Therefore test-year 2026 currently means the eligible observed portion of that year, not established full-year coverage. Exact inclusion and oracle-weather provenance require resolution before execution/claims.

## Foundation documents read by the main agent

- `specs/001-deep-feature-weight-decay/spec.md`
- `specs/001-deep-feature-weight-decay/research.md`

The task's newer user decisions supersede those documents' old all-prior-history/four-test-year defaults, while preserving the cumulative XGBoost model family and project output conventions.

## Food_Crisis_Cluster rich-history reference

Reference root: sibling repository `Food_Crisis_Cluster`. Main agent read `.trellis/tasks/archive/2026-09/09-21-ipcch-population-history-xgb/technical-contract.md` and `design.md` in full. These are reuse references, not authorization to import that experiment's models, source-year choices, horizon schedule or evaluation protocol.

- `IPCCHPopulationHistoryExperiment/prepare_data.py:291-340,384-399,540-745` defines eight series from normalized P1–P5 shares: q2/q3/q4/q5 cumulative shares, weighted severity, normalized entropy, concentration, and q4/q3 severe fraction (missing for q3=0).
- The ordered 468 history additions in `config/feature-schema.json:126-615` contain 48 observed levels (eight series x last six observations), 10 timing fields, 80 differences/rates, 16 trends, 240 window statistics, 29 support fields, five prior binary states, 12 threshold-distance fields, 20 window crisis fields, and eight event/run fields. Its total561 includes a separate original93 baseline not used by the current IPCCH task. Five aliases reference original93 fields and require explicit resolution if ported; 468 is not automatically the new task's final added width.
- Last-six means actual prior valid observations, not six consecutive calendar months. Windows are 6/12/24/36 months and all prior observations. Changes use observed month gaps. Missing support remains NaN; mean requires one value, standard deviation two, slope three. The reference has no explicit weather-times-history multiplication block.
- Reference history cutoff is U<=O, with all reference horizons >=1. This task's H=0 additionally needs U<T. Reference histories use the full valid source ledger, not just fitting-window rows. The user subsequently approved pre-2022 feature history and earlier test-year history known by O, without expanding supervised fitting windows.
- `IPCCHGeoRFExperiment/prepare_data.py:237-288,334-362` applies a share QC/normalization contract (P1–P4 required, missing P5=0, values in [0,1], sum in [.90,1.10], positive population). This describes the reference, not the adopted sum gate: G4 subsequently approved finite nonnegative positive-sum normalization in `design.md` sections 2/5, retaining the flagged missing-P5 fallback for history only.
- Current IPCCH fs0/fs1/fs2/fs3 CSV headers contain current `phase1_percent` through `phase5_percent` as targets, but no lagged percentage history. Existing category-history fields include `overall_phase_prev_observed_asof_s0/s3/s6` and/or `overall_phase_lag1`. Thus A is not necessarily a no-history baseline; D adds richer distribution history.

## Grill data check: temporal validation support and impossible shares

Read-only label-support screening used the canonical raw `assembled_IPCCH/raw/IPCCH_2026_completed.csv`, filtering ISO3=SOM. Raw verified target-month candidates are April/July/September/October 2025 and April2026. The proposed latest-three-inner-month procedure has three nonempty inner folds with pooled crisis/noncrisis support at H=12 for each of these targets; H=0/3/6 also pass this necessary label-support screen. This is not a check of feature availability, oracle provenance or runnable models, and no training was executed.

| H12 outer target | Outer origin | Inner target months | Pooled crisis/noncrisis after q-valid label screen |
|---|---|---|---|
| 2025-04 | 2024-04 | 2023-03, 2023-08, 2024-01 | 549 / 476 |
| 2025-07 | 2024-07 | 2023-08, 2024-01, 2024-07 | 518 / 540 |
| 2025-09 | 2024-09 | 2023-08, 2024-01, 2024-07 | 518 / 540 |
| 2025-10 | 2024-10 | 2023-08, 2024-01, 2024-07 | 518 / 540 |
| 2026-04 | 2025-04 | 2024-01, 2024-07, 2025-04 | 716 / 898 |

The source also contains 23 April2026 Somalia rows with q2=P2+P3+P4+P5 between 1.10 and 1.20, out of 904 rows having complete shares and reported phase. One October2022 row has q2=1.01. Removing these solely for the historical support screen leaves 881 April2026 records (518 crisis/363 noncrisis), but this exclusion is superseded by G4 normalization. Neither 881 nor the inner-support counts above define final support: recompute from the normalized ledger, then apply source, weather and feature eligibility. The model-ready and raw sources also disagree on some earlier month counts; never silently mix their target ledgers.

Main-agent spot check independently read raw CSV record 1,152,237: area1981, SOM, April2026, reported phase4, P1=.15/P2=.25/P3=.60/P4=.25/P5=0. Thus q2=1.10 and the full distribution sums to1.25. Preserve this raw evidence; normalization is not proof of the correct original distribution. G4 subsequently resolved handling: the user explicitly approved proportional normalization to unit sum for targets and history, preserving raw records and reported phase. The prior q2>1 exclusion counts are historical screening evidence, not the final cohort policy.

## Audit setup recorded during brainstorming

- Exact enrolled repository: `/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/Google fund/Analysis/2.source_code/Step5_Geo_RF_trial/IPCCH`.
- Registration verified Claude pane `wD:p2`, terminal `term_65c3ebdc967b05`, session `5ac278d6-9e26-49b5-8d96-7e54266aa71e`.
- Controller boot and subsequent status returned `running: true` (controller pane `wD:p4`); `active_runs` was empty.
- These describe setup at that check, not a live audit verdict. Reverify before starting implementation. Task has stayed planning, with no audit run/base SHA or completion audit for this task.

## Addendum A — preflight evidence for implementation (2026-09-24, read-only)

- Upstream scope-file builder is `Step5_Geo_RF_trial/assemble_latest_IPCCH/build_multiscope_ipcch_features.py` (BMS). `_sH` families are the `_asof12` column shifted by `12-H` rows within area (BMS:258-263; scenarios BMS:42-46), so their latest source month is exactly T−H (s0 uses month T: a nowcast at O=T). `asof12`/`l12..l24`/`hist_same_month_*_l12` come from `build_deep_ipcch_features.py` (BDF:401,436) and use <=T−12. `nino34_anom__forecast_sequence_sH` is the observed value at T−H (BMS:579-581), not a forecast; `l12_delayed_control` is T−12.
- `overall_phase_prev_observed_asof_sH` = `groupby(area).overall_phase.shift(max(1,H))` (BMS:664-666): exact calendar month T−max(1,H); valid for U<=O and U<T.
- `overall_phase_lag1` is added by `organize_ipcch_ml_data_folder.py:98-130,167` and equals the previous observed row's phase regardless of gap; it post-dates O for 1,640 / 17,218 / 36,369 rows at H=3/6/12 → blocked.
- `estimated_population` is corrected with the targets from IPC/CH polygons (`03_correct_ipcch_targets.ipynb`) and varies within area → target-side; blocked as predictor.
- Model-ready Somalia label ledger (fs0∪fs1∪fs2∪fs3): 6,759 labeled keys, zero cross-file value conflicts; 18 `overall_phase==0` rows with zero shares; 232 raw sums >1.001, 182 sums in (0,.999); 5 rows with nonpositive/missing population. Raw vs model-ready reported phase disagree on 252/729 (2022) … 0 (2025, 2026) keys; 2025–2026 keys agree exactly except model-ready-only `area 1917, 2026-01`.
- Raw weather (`IPCCH_2026_completed.csv`, Somalia 904 areas): no area-month before 2025-02 equals its previous month in both rain and temperature; from 2025-02 through 2026-03, 772 areas are frozen at their 2025-01 values; in 2026-04 all 904 equal March 2026. The 133 non-frozen areas never repeat the previous month, 12- or 24-month-earlier values. Verification rule in `implement.md` follows from this.
- V2 Somalia: 905 areas × 5 season-years × 2 seasons, all `gs_calendar_valid=1`; no equal-ended season ambiguity; incomplete available windows only in 2026 (57 s1, 3 s2 rows), which end after every evaluation origin except those with O>=season end.
- No alternative realized GLDAS-style monthly weather source was found under `1.Source Data` or `IPCCH_shared_folder`.
