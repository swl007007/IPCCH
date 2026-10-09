# Somalia local compact historical experiment and CDS launch

Specification status: Approved on 2026-10-09. Execution status: Not Executed; subsequent evidence is recorded separately.

## Goal

Rerun the existing compact historical baseline/weather-oracle experiment and April 2026 compact/CDS launch with Somalia-only local fits. Show absolute performance or prediction levels alongside paired arm differences. The limited scope is the existing experiment with Somalia membership, not a new modeling method.

## Background and confirmed decisions

The user requested grilling, a persisted spec, then execution and explicitly authorized this Trellis task. The launch-only interpretation was explicitly corrected. Requirements below are the authoritative record of the adopted historical, launch, horizon and absolute-level decisions.

Source experiments: `results/experiments/compact_climate_weather_oracle_v1` and `results/launch/nowcasting_2026_04_compact_cds_v1`. Current source/data evidence is indexed in `research/feasibility.md` and `research/local-contract-surface.md`.

## Requirements

| ID | Requirement |
|---|---|
| R1 | Membership is the pinned canonical area lookup, exact `iso3 == "SOM"`. Filter fitting observations AND historical evaluation/launch inference. Refit every required model; filtering saved global predictions does not satisfy local modeling. |
| R2 | Historical baseline H0/H3/H6/H12 versus realized-weather oracle H3/H6/H12; shared H0. Preserve 2022–2025 annual evaluation, year-specific origin/label cutoffs and training weights. Seven runs,28 annual batches,112 cumulative-regression models. |
| R3 | Historical outputs include all eight existing metrics for each arm/horizon/year and pooled 2022–2025, support/undefined reasons, keyed predictions and oracle-minus-baseline deltas. Pooled metrics use pooled observations. |
| R4 | April 2026-origin launch baseline H0/H6/H12 versus CDS-weather H6/H12; shared H0. Targets April 2026,October2026,April 2027. Five unique fits,20 models; realized-weather training and existing accepted April-init May–October CDS inference. |
| R5 | Launch fitting preserves valid-share selection strictly before April 2026 and April-anchored weights. Inference IPC history ends March 2026; ordinary sources/IDP through April and inherited completed-season rules. |
| R6 | Preserve literal recipes/order/counts 296/302/308, normalization, four cumulative regressors, canonical phase3-specific configs, runtime, seed 42, half-life 24, threshold 0.2 and n_jobs16. No tuning, imputation, feature rebuilding or new calibration. |
| R7 | Historical cohort is the frozen evaluation cohort intersected with SOM:4,933 keys over 905 areas, yearly1129/1217/711/1876. Launch fit selection has 5,835 SOM observations; inference/population is the original April cohort intersected with SOM:904 areas. Retain area 3146 in eligible historical roles; record its absent April 2026 source row as outside launch coverage. Do not invent its2026 population. |
| R8 | Launch absolute outputs: area phase, phase1–5/P3+/P4+ population shares/counts, Somalia population-weighted totals, uncapped/capped population and existing country factor. Freeze April 2026 population for all targets/arms. Reporting-only difference/clip/normalization remains inherited; raw prediction/classification stays unrounded. Report CDS-minus-baseline deltas with equal denominators and shared-H0 zero differences. |
| R9 | Deliver Somalia reports in existing historical table/codebook and launch table/map formats: five unique categorical launch maps, one2×3 P3+ share comparison and one1×2 P3+ difference map. Keep explicit paths and metadata scope=SOM, model scope=Somalia local. |
| R10 | Use separate local result/report/input identities; preserve source/global code/config bytes, accepted models/results and selection paths. Bind local membership/cohort/spec/source/code/config/runtime identities to fingerprints and complete artifacts. Independently verify every model, cohort, metric and population/map table. |
| R11 | User approved the final summary and explicitly requested Herdr dispatch to Claude Opus 5.5 with 1M context, Codex supervision, and no Trellis audit. Commit the approved plan before implementation, use ordinary Trellis lifecycle, and require actual independent supervisor acceptance. Do not register/start/close an audit or change existing controller gates. |

## Acceptance criteria

| ID | Observable outcome | Requirements |
|---|---|---|
| A1 | Saved fit/evaluation/inference keys are SOM; actual ordered sets equal the COMPLETE eligible SOM sets per cutoff, not merely a subset. | R1,R2,R4,R5,R7 |
| A2 | Seven historical runs/28 batches/112 models and five launch runs/20 models complete. Shared H0 has one unique fit per stage. Every fitted ordered schema equals the inherited contract. | R2,R4,R6 |
| A3 | Historical annual and pooled cohorts match across arms/horizons; truth alignment and paired fit-key/target/weight equality pass. | R2,R3,R7 |
| A4 | Independent replay reproduces all historical metrics/deltas including undefined masks/reasons; all112 historical models reproduce keyed predictions. | R3,R10 |
| A5 | Launch fitting and inference sets, paired targets/weights/base prefixes, CDS values and timing/calendar contracts match the declared local projections. | R4–R7 |
| A6 | Independent shares/counts, population/cap factor, Somalia aggregation and paired deltas match tables. All20 launch models reload/replay. | R8,R10 |
| A7 | Seven SOM launch maps have data/geometry identities and complete904-area joins; plotted classes/continuous values match saved tables. | R9,R10 |
| A8 | Actual-fitted English codebooks, local manifests, fit/cohort ledgers, complete inventories, reports and verification JSON exist. Frozen global code/config/input/result identities remain unchanged. | R6,R9,R10 |
| A9 | Final evidence records actual commands/statuses/limits,132-model verification, verified Herdr executor/model/context and independent supervisor acceptance. No Trellis audit is started; its omission is the user's explicit choice, not an audit pass. Planning/checklists are not execution evidence. | R10,R11 |

## Technical notes and evidence anchors

- `src/ipcch/compact_launch.py:40-48`: launch origin/targets/training-arm mapping; `:674-745`: reusable fits/inventories. `scripts/modeling/run_deep_feature_weight_decay_forecasting.py:882-905` rejects direct country scopes; `:984-1046,1078-1149` provides validated inputs/annual fitting primitives.
- Coverage evidence is in `research/coverage.md`: area 3146's series ends 2024-12, so it remains historical but lacks April launch source/population. Original country factor produces effective 18,672,002.05 from raw 62,695,007; inherited reporting is not a population-vintage certification.
- `design.md` freezes technical boundaries/paths; `implement.md` records execution/check gates. `expected_runs.csv` is expected inventory, not fitted evidence.

## Out of scope and limits

No new CDS retrieval/historical CDS backtest, global refits, feature engineering, tuning, bootstrap/intervals, SHAP, extra model arms, reconstructed population for 3146, country/region expansion or changes to frozen global helpers. Observation/report month remains availability proxy; upstream vintages/climatology lineage remain inherited limits. Historical oracle measures ideal-weather information; future launch levels cannot establish accuracy. Fixed global hyperparameters may suit the smaller SOM sample imperfectly. Source drift, missing keyed evidence or replay failures block acceptance.
