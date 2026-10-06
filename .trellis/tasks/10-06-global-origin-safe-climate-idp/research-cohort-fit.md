# Label cohort and fitting protocol verification

Read-only agent inspection (2026-10-06); no tests/models or hashes executed.

## Canonical corrected labels

- Actual paths resolve through `src/ipcch/paths.py:19-34,47-53` to assembled_IPCCH/model_ready baseline forecasting_ready and scope0/3/6 files. Keys: area_id/year/month; truth: overall_phase and phase1_percent through phase5_percent.
- forecasting_ready and scope0 have 52521 keys, no duplicate/missing keys, all phase1–5. scope3/6 each have 53257 keys, their extra 736 keys all reported phase0. All shared truth fields equal across four inputs and the canonical corrected interim file.
- `interim/IPCCH_2026_target_corrected_nino34_wbfood.csv` has 1219868 unique area/month keys; its phase1–5 subset is exactly the same 52521 label keys/truth. Renaming admin_code to area_id is explicit. Use this corrected interim projection as the explicit source in the final spec, subject to validation/hashing.
- Target-year phase1–5 counts: 2022 5606, 2023 6064, 2024 5127, 2025 11415 =28212. Every target year has label coverage in all twelve months.
- Requiring complete, finite, nonnegative five shares with positive total leaves 5599/6064/5127/11415 =28205. Seven exclusions in 2022: three phase5-missing rows and four all-five-shares-zero rows whose reported phases are 2/3. True phase1 with positive phase1 share and zero higher shares must remain eligible.
- 359 complete eval rows have share sum not near one (default np.isclose), total range [0,1.35]; each share is in [0,1]. Raw cumulative truth currently sums these without normalization (`src/ipcch/forecasting_weight_decay.py:132-150`). Normalization policy is an unresolved scientific decision.
- Existing CLI `convert_phase_predictions():274-296` deletes rows by prediction sum and truth higher-phase cumulative sum, rounds cumulative predictions before threshold, and outputs classification truth from reported overall_phase (`:352-354`). Final spec must use frozen valid keys, keep zero predictions, and retain raw inputs with explicitly derived targets.

## Fit reuse and runtime

- Existing `fit_model` at `scripts/modeling/run_deep_feature_weight_decay_forecasting.py:252-271` uses fixed XGB configs and seed, no inner tuning/early stopping/calibration. Four independent cumulative regressors.
- Configs: ordinary target depth11,200 trees,lr0.1,subsample1,colsample0.5; phase3 depth9,200 trees,lr0.1,subsample0.5,colsample0.7. Keep exact parameter artifacts and hash/version, no new tuning.
- Current `time_decay_weights` anchors test-year Jan1 and rejects zero-age labels (`src/ipcch/forecasting_weight_decay.py:287-302`); new monthly weights need own origin anchor with distance zero allowed for H>0, weight=1, half-life24.
- `run_holdout` accepts explicit train/test sets but its conversion alters cohorts. Reuse fitting logic after correcting conversion and add monthly origin protocol; do not inherit annual target splits.
- Metadata currently records only feature hash and a first20 sample, not full order/fitting keys/fitted bundles. New artifacts need complete schemas and per-origin model/key records for verification.
- Existing global suite uses ~/.venvs/ipcch-geo/bin/python. Current package metadata: Python3.12.3, XGBoost3.2.0, NumPy2.4.4, pandas3.0.3, scikit-learn1.8.0. Successful current imports still need checking. Do not substitute repo .venv silently.
- Max576 batches ×4 targets=2304 individual estimator fits. Prior annual suite seconds are not evidence for monthly runtime. Run a measured resource pilot, then sequential bounded-memory batches with resumable validated completion records.
