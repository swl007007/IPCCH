# Global origin-safe climate and IDP benchmark

## Goal and background

Repair historical-label and fitting-time leakage in global IPCCH, prevent reuse of unsafe inputs, and quantify safe-history and national-IDP gains with supplied monthly and growing-season (GS) climate data.

Confirmed defects: climate replacement preserves legacy history; organizing restores excluded lag1; fitting cuts off by target year rather than forecast origin. Trace anchors: `scripts/preprocessing/build_climate2015_model_ready.py:104-127`; `../assemble_latest_IPCCH/organize_ipcch_ml_data_folder.py:85-134`; `src/ipcch/forecasting_weight_decay.py:194-234,249-257`. The exact fs3 lag1 generator remains unproven. Equal values alone are not source evidence. User's reported 1.4%/94% coverage and 74.6% suspect lag1 timing motivated this repair, not a quantified causal conclusion. Example: `1.Source Data/assembled_IPCCH/model_ready/climate2015_v1/forecasting_subset_IPCCH_2026_climate2015_v1_masked_forecasting_ready.csv:21`.

## Frozen requirements and decisions

All A selections below were explicitly approved during grilling on 2026-10-06.

- R1 — Retrospective availability proxy: observation/reporting month represents availability. No historical publication-vintage or full-chain no-look-ahead certification.
- R2 — Four horizons H=0/3/6/12 months; target T, month-end origin O=T-H. Monthly dynamic observations must be <=O; GS must be completed by end of O. Historical IPC and fitting labels must be <=min(O,T-1). Thus 0m excludes target-month labels from all areas and is a month-end nowcast. July2022/H12 labels stop at July2021.
- R3 — Refit at every origin month, score target years 2022–2025, aggregate by year and pooled keys. Keep fixed current XGB parameter files, seed42, threshold0.2, half-life24 months and global scope. Weight ages measured from each actual fit origin; age0 allowed for positive horizons. No new tuning, calibration or threshold selection.
- R4 — All horizons use three latest non-null valid reported overall_phase observations in the same area satisfying R2, plus history1-history2 and history1-history3. Keep missing history NaN and actual source keys/months. Remove all legacy lag1/prev_observed history columns and target-side estimated_population. Reuse the existing Nigeria selection algorithm, extend H12 and independently validate provenance.
- R5 — Three paired arms: climate_no_history; climate_safe_history; climate_safe_history_idp. Twelve arm/horizon outputs, at most576 monthly batches and2304 cumulative-regressor fits. Compare arm2-arm1 for history and arm3-arm2 for IDP. Old unsafe results are context only, not paired causal baselines.
- R6 — National DTM latest reported IDP stock and age in months, joined by verified ISO3. Latest non-null report <=O; stock unavailable before first report stays NaN, never zero. Old reports are explicitly stale context, not fresh counts. No subnational allocation or complete refugee panel. All arms use identical keys, including IDP-missing rows.
- R7 — Use all fourteen supplied monthly/GS ensemble indicators and current engineering families, with two most recently completed seasons. Cancel the artificial old scope-tail mask for new climate/GS; retain genuine missingness. Other inherited predictors retain their existing source values/coverage after timing classification; do not expand this task into rebuilding all non-climate scope-tail families.
- R8 — Preserve raw labels/shares. Require reported phase1–5 and complete finite nonnegative five shares with positive total for fitting/scoring. Normalize shares in derived targets, then construct phase2/3/4/5-or-worse targets. Classification truth stays original reported overall_phase. Genuine Phase1 remains eligible. Valid reported phase history is independent of missing share blocks. Current projected evaluation cohort is28205 keys (2022:5599,2023:6064,2024:5127,2025:11415), to be verified against frozen files. No prediction-dependent exclusions. Use unrounded cumulative predictions for thresholds and R², retain raw outputs; only presentation may round.
- R9 — Pin explicit input paths, SHA256, fitted feature order, cohort/fitting keys, model bundles, source-date ledgers and runtime/code identity. Run temporal checks before fitting and reject old history or missing/mismatched provenance at the global training entrance. Regression checks must catch the reintroduced-baseline-column failure as well as post-origin history/fitting labels.
- R10 — Preserve raw data, previous results and unrelated user changes. New versioned output directories; sequential bounded-memory resumable run after measured pilot. Report undefined metrics explicitly, prediction coverage and missingness/age by horizon. Metrics: phase3+ accuracy/precision/recall/F2, cumulative phase3+ R² and MAE, ordinal MAE; replay from saved unrounded predictions independently.

## Acceptance criteria

- AC1 (R2,R4,R9): real source ledgers pass independent latest-three checks for every eligible history row; zero forbidden source/fitting dates; all four horizons and month-end/0m boundaries tested. Legacy history/target-side population cannot enter new fits; missing provenance fails before training.
- AC2 (R7,R9): fourteen monthly/GS indicators use observable support ending no later than allowed cutoff; only completed seasons selected. New climate/GS is not masked by old carrier-row tails. Retained dynamic families have documented verified month anchors; source disagreements stop execution rather than receive invented provenance.
- AC3 (R6): country join cardinality, report cutoff and age checks pass; missing is not zero, future reports cannot change earlier features. Complete refugee coverage is never claimed.
- AC4 (R3,R5,R8): all twelve arm/horizon runs finish on the same28205 pinned valid target keys if current inputs match; four estimator targets per fit; model-dependent row drops forbidden. Per-origin fitting keys/model/schema are saved; selected tests and compatibility checks pass.
- AC5 (R1,R5,R10): paired yearly/pooled metrics and independent replay agree; report explains combined timing/target/postprocessing corrections relative to old results, single seed/no intervals, upstream limits and run resource measurements.

## Limits and exclusions

Supplied climatology/standardization fitted samples remain incomplete; user approved use with that disclosure. Static geospatial/context snapshots and revised observations are fixed retrospective context, not verified historical vintages. Source-support assertions cannot certify unobserved producer internals. No upstream climate rebuild, subnational GIS, refugee ingestion, hyperparameter/SHAP work, old-model rerun, or repair of unrelated models. Current global entry must fail safely rather than silently accept legacy annual/leaky inputs. Country-specific/oracle behavior is outside this execution scope.

## Artifacts and approval

Research: research.md, research-followup.md, research-cohort-fit.md. Technical design: design.md. Execution: implement.md. On 2026-10-06 the user approved execution of this final spec by directing Codex to register Trellis audit, start the controller, and hand control to another active Claude Opus 5.5. Task remains planning until the verified bound executor runs audit start. No product implementation, builds, training or acceptance validation has occurred at this handoff.
