# Read-only research findings and source handles

These findings locate existing evidence; previous replay/acceptance results are
not fresh tests. C0 must confirm current bytes and expand exact inventory.

## Reference integration

Sibling Food_Crisis_Cluster `IPCCHMLflow/naming.py:433-490` implements lead labels,
zero-padded tags, family/arm run and model names, datasets. `:521-568` describes
families and views. Current spec is October 9 readable naming; old AGENTS names
and hardcoded counts are stale. External model descriptors reference child runs
and parent `models.tar`; same content fingerprints deep-verify then no-op, changed
content fails. Runtime `/home/swl007007/.venvs/ipcch-mlflow`; local store
`/home/swl007007/.local/share/ipcch-mlflow/`, service 127.0.0.1:5000, no autostart.
Check actual lock/backup semantics before adopting; do not rewrite shared store.

## Somalia

- `src/ipcch/somalia_oracle/pipeline.py:200-203`: A existing predictors, B adds
  fourteen seasonal V2 means, C realized rain/temp O+1..O+min(H,6), D adds rich
  share history. H0 C clones B (`:354-363`), not another fit.
- `scripts/modeling/run_somalia_q3_optimization.py:86-94,262-300`: selected recipe
  reuses exact direct/residual components; v2 selected is absent as a separate
  inventory view. H>0 recipe selection is retrospective/ancillary (`:408`).
- `scripts/modeling/run_somalia_validity_augmentation.py:182-239`: v3 selected
  actually refits/saves; inventory-declared hashes can equal selected counterpart.
  v3 original/augmented outer evaluation keys are identical; copies train only
  (`:336,357-360`). v3 original raw truth is not v2 target-corrected truth.
- `scripts/modeling/run_somalia_v4_calibrated_d.py:348-424`: selected D per context;
  original/augmented differ in all label roles including outer evaluation. Source
  member schemas include q2/q4/q5 plus q3_direct and q3_residual_delta components.
- v4 `metrics/annual_metrics.csv:33`: augmented 2023 H6 incomplete, 696 of 2013
  required final predictions unavailable. `pooled_metrics.csv:8` marks affected
  pooled incomplete. Four annual slots 2026 H3/H6 are `empty_cohort`.
- v4 archived `evidence/evidence.md:84-103` retains major/minor audit debt and a
  waiver, not audit pass. v3 archived closure is likewise not an audit pass.
- v1 diagnostics include `LEAKY_test_perphase_macro_f1`; these are diagnostic
  postprocessing, not new fitted models (`somalia_oracle_calibration_diagnostics.py`).

## Modern historical and launch

- `src/ipcch/origin_safe.py:30-38`: no history / safe IPC history / plus national
  IDP. `weather_oracle.py:5-14,25-37,80-85`: realized future weather, plus B6
  future mean, past/future mean, crisis-gated future mean for two weather variables.
- `verify_origin_safe_weather_oracle.py:386-392`: baseline weights/predictions
  reused, not refit. Do not register a second fit for reference comparison rows.
- Compact baseline296; H3 oracle302; H6/H12 oracle308. Historical H0 shared.
  `compact_features.py:33-41,136-143` and seven-run suite docstring.
- `run_compact_eval_2026_extension.py:817-826` indexes exact original/extension
  paths/fingerprints, reused years2022–2025 and fitted-here2026. Global/new keys
  4327, SOM/new905; SOM monthly support Jan–Apr =1/0/0/904. Two pooled periods.
- Annual phase bundles are `runs/<arm>/<lead>m/batches/<year>/` with four UBJs,
  predictions, fit keys and batch record. Run metadata pins fitted feature order.
- `compact_launch.py:1-15,44-48`: five fits, origin April2026, leads0/6/12,
  baseline or CDS. Weather training uses realized oracle inputs; inference uses
  CDS forecasts. Training reuse is not reuse of historical fitted boosters.
- Global launch6188 areas, SOM904; population summaries are predictions, not
  historical accuracy. Existing April H0 comparison supplement is a plot artifact,
  not a new fitted model. No 3-month compact launch exists.
- Regional evaluation of global models is a scoring subset, not local training;
  `run_compact_eval_2026_extension.py:891-893` explicitly distinguishes this.
- `verify_origin_safe_climate_idp.py:387-400` mixes excluded climate2015 context
  into a report: do not upload whole mixed report. Task/source code may likewise
  cite old results; explicit artifact/field selection is required.
- `run_deep_feature_weight_decay_forecasting.py:1177-1190` refreshes metadata time
  even when reporting existing batches; dates need training/task execution evidence.

## Frozen identity

`compact_features.py:74-85`, `compact_launch.py:605,646-665`,
`run_deep_feature_weight_decay_forecasting.py:964-974`, and
`run_compact_eval_2026_extension.py:130-140` bind existing code/data/result bytes.
Do not add hooks to these scripts. Independent registration plus agent guidance
was explicitly selected to preserve these fitting contracts.
