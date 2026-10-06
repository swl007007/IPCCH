# Read-only planning evidence (2026-10-06)

No model builds, experiments, tests, or acceptance validation executed. Three independent exploration agents supplied evidence; main session spot-checked organizing merges, annual splits, Nigeria history selection, and the DTM raw header. All paths below are relative to IPCCH unless absolute.

## Label source chain

- `scripts/preprocessing/build_climate2015_model_ready.py:35-38,104-127` reads existing scope files (fs3 forecasting-ready), removes only old climate features and retains non-climate columns. `src/ipcch/paths.py:19-34` resolves baseline scope files under `Analysis/1.Source Data/assembled_IPCCH/model_ready/`.
- `src/ipcch/forecasting_weight_decay.py:194-234` accepts numeric `overall_phase_lag1` and `overall_phase_prev_observed_asof_*`; no source-date validation. CLI selects these at `scripts/modeling/run_deep_feature_weight_decay_forecasting.py:697-704`.
- `../assemble_latest_IPCCH/build_multiscope_ipcch_features.py:646-706` uses fixed row shifts `shift(max(1, blackout_months))`, not latest non-null observations. Its provenance dates are calculated offsets rather than actual source-row dates.
- `../assemble_latest_IPCCH/organize_ipcch_ml_data_folder.py:85-100,115-134` merges missing baseline columns into scope files on target keys. Persistent 3m/6m validation summaries record lag1 being excluded then added for readiness. fs0 retains no lag1.
- Existing fs3 lag1 generation remains unproven: full deep-feature source header lacks it; a historical notebook uses a different input. Equal values and target date intervals alone cannot identify a source row. Reconstruct safe history from declared labels instead of certifying this column.
- Agent scanned masked input headers: fs0 has prev_asof_s0; fs1/2 have prev_asof_s3/s6 plus lag1; fs3 has lag1. No history source-date columns.
- `estimated_population` is selected in all four scopes and appears among target variables in `../assemble_latest_IPCCH/03_correct_ipcch_targets.ipynb:191-223`; its static provenance needs classification before accepting it. Somalia separately blocks it (`src/ipcch/somalia_oracle/__init__.py:16`).

## Existing reuse and fitting-time risk

- `../assemble_latest_IPCCH/experiments/nga_aligned_ipc_history_20260918_v1/build_and_run.py:33-83` selects latest three non-null area observations at origin: H0 strict `< origin`, positive horizons `<= origin`. Two changes, missing history stays NaN, source-month sidecar and independent reference. Helper accepts only 0/3/6; surrounding executor is NGA-specific. Publication availability is explicitly approximated by observation month (`:135-136`).
- `src/ipcch/forecasting_weight_decay.py:249-275` splits by target calendar year, no horizon/origin. CLI fits once per year (`scripts/modeling/run_deep_feature_weight_decay_forecasting.py:719-729,763-768`). For January 2025 H12 predictions, training permits 2024 target labels although origin is January 2024. Correct input history alone does not resolve fitting-time validity.
- CLI prediction conversion can drop rows whose rounded predictions sum to zero (`:285-287,316,345-352`); arm comparisons need explicit cohort policy and prediction coverage diagnostics.
- Climate temporal tests cover synthetic monthly values after anchor, without spatial neighbors (`tests/unit/test_climate2015_features.py:20-31`). Seasonal selection is month-end (`src/ipcch/climate2015_features.py:288-304`). Preserved context/old predictors and publication timestamps remain outside this gate.
- Upstream anomaly climatology baseline was already unknown in the prior PRD. Cannot claim all-feature real-time availability solely from month alignment.

## IDP DTM feasibility

Root: `/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/Processed_Dataset/IDP_DTM`.

- Existing standardized CSV/Parquet admin0/1/2 long and monthly tables derive from one global API snapshot (`scripts/03_compile_admin.py:22-25,177-186`). Raw API covers 54 countries, admin2 49; dates 2010-06 through 2026-09, coverage irregular.
- Raw API header has `reportingDate` and present IDP individuals but no record-level publication, first-availability or revision date. Catalog modification timestamps do not provide historical vintages. Country Excel date semantics vary; not a substitute for availability dates without separate harmonization.
- Monthly tables retain NaN for unobserved months and do not forward-fill (`scripts/03_compile_admin.py:160-174`). No zero IDP values in these monthly tables; missing must not become zero.
- Counts use current IDP population, priority/operation aggregation (`scripts/03_compile_admin.py:104-157`); differences are not automatically displacement flows.
- Existing crosswalks map DTM via COD-AB to GAUL 2024, not IPCCH area_id (`scripts/05_crosswalk_gaul.py:241-261`). Many-to-many area weights, unmatched units and historical boundary assumptions require explicit handling. Target area_id identity not yet verified.
- Standard API panel is IDP, not a standardized refugee panel. Refugee-only datasets were excluded (`scripts/01_fetch_catalog.py:29-38,81-82`).
- Bounded source searches found no existing IPCCH/sibling ingestion. IDP could support a separate observation-month-based retrospective arm after key alignment; present files alone cannot prove historical publication availability.

## Availability decision and next decision

User selected the retrospective benchmark using observation/reporting month as an explicitly limited availability proxy (A, 2026-10-06), followed by refitting each origin month (A). Both feature sources and fitting labels must obey forecast origin. No claim of historical publication/vintage availability. Next decision: month-end versus month-start availability boundaries, including prohibition of current-target-month labels at 0m. History features and run arms remain subsequent decisions.
