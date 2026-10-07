# Existing integration surfaces (read-only planning facts, 2026-10-07)

Two bounded read-only explorers inspected code, saved metadata and package metadata. No dataset rebuild, tests, model replay or training. This note does not certify the artifacts for reuse.

## Fit entry and feature contract

- `src/ipcch/origin_safe.py:23-48` fixes three legacy arms and forbidden feature regex. `scripts/modeling/run_deep_feature_weight_decay_forecasting.py:134,900-902` parses those arms and validates history/IDP subsets.
- `load_origin_inputs` at `:891-941` enforces COMPLETE, hashes, ordered feature lists, history/IDP ledger timing, labels/cohort; it does NOT currently enforce a manifest-version allowlist or a generic weather source-month boundary. New named oracle versions need exact per-arm feature/lineage validation rather than treating absence of a forbidden name as authorization. Preserve the existing history/IDP/target gates.
- Origin-safe branches before generic annual feature selection (`:699-700`); fitting consumes manifest features verbatim (`:1000-1001`) and compares fitted names (`:1015-1016`). No downstream automatic selection removes new columns.
- Fingerprints (`:935-941`) cover manifest bytes, dataset/order, H/arm, params, seed/weight/threshold/n_jobs, XGBoost and whole CLI/origin_safe files. Helper recipe hashes must enter the new manifest/fingerprint. Do not call the modified runner against old output directories to verify reuse: code-hash changes intentionally reject resume.
- `verify_batch` (`:962-977`) requires six artifacts: predictions, fit keys and four UBJ models. `run_origin_safe` (`:1056-1080`) dry-run validates and returns before writing; dry-run does not validate existing output-directory resume records. Resume rejects altered fingerprint/artifact inventory.
- `run_origin_safe_climate_idp_suite.py:23-50` fixes VERSION/results, and defaults to all legacy arms/horizons. Passing a new manifest alone writes into the old namespace. Preserve old defaults and give the new experiment an explicit isolated output path and only the six approved nonzero-horizon arm runs.

## Baseline reuse and verification

- Saved `climate_safe_history_idp` metadata for all four horizons is COMPLETE, seed42, half-life24, threshold0.2, n_jobs16,28205 predictions;870 features at H0/3/6 and654 at H12. Saved verification passed, but has not been replayed in this task.
- Original interpreter `/home/swl007007/.venvs/ipcch-geo/bin/python` currently retains Python3.12.3, numpy2.4.4, pandas3.0.3, sklearn1.8.0, xgboost3.2.0. System Python is not an acceptable substitute (different NumPy/pandas, missing XGBoost).
- Fixed config SHA256 matches saved fingerprints: `configs/forecasting_hyperparameters.json`=3742300661466f22eba8198e5d4f9c2a277615ba59562fbf27f251ecc932dd76; `_p3.json`=cdc0e55aa15bdda932465088568b9ee717d226208ffb32076f438fb274e6317b. Only phase3_worse uses the latter (`run_deep_feature_weight_decay_forecasting.py:267-285,1005-1013`).
- `verify_origin_safe_climate_idp.py:184-246` verifies ordered features, records, all six artifact hashes, fitting keys/weights, cohort/truth/classes; model replay uses fitted order with rtol0/atol1e-6. Its default samples two years per run, not all four. `:259-285` checks cross-arm keys and metric replay (atol1e-12, same NaN mask).
- Verifier version/arms/results/report paths are hardcoded (`:26-37,110-118,288-401`). Reuse existing metric/format helpers where suitable, but the new comparison requires explicit three-arm paths and new delta pairs. Do not invoke old verifier with only a changed manifest.
- No existing check proves that appending columns leaves every baseline cell unchanged. New input verification must compare baseline projection values/NaN masks/order and labels on keys. A feature-list SHA binds names/order, not matrix values.
- Original code fingerprints predate A01-A04 repairs; archived evidence says fitting/predictions unchanged. Preserve old training identity and later verification identity separately. A changed current code hash does not authorize overwriting old provenance or automatic baseline refitting.
- Missing/corrupt artifacts, environment drift or failed matrix/label/key/weight/replay parity means stop and report the discrepancy; do not silently substitute models, alter cohorts or refit the baseline.

## Saved prediction and metric contracts

- Batch files: `batches/{Y}/predictions.csv`, `fit_keys.csv.gz`, `model_phase{2,3,4,5}_worse.ubj`, `batch_record.json`. Records include fingerprint, H/arm/year, fit_origin_month, fit_label_cutoff_month, fit_keys_sha256, eval_keys_sha256, feature_sha256, artifacts map.
- Run prediction files: `predictions/predictions_{2022,2023,2024,2025}.csv`. Columns include area_id/year/month, horizon/arm, row_origin_month/fit_origin_month/fit_label_cutoff_month, overall_phase, phase1_percent..phase5_percent, phase2_worse..phase5_worse, phase2_pred..phase5_pred, overall_phase_pred. Following the user's mapping correction, join regional membership from `data/reference/area_id_country_region_mapping.csv` by area_id; attach country lookup only for bootstrap strata. Do not guess either field from the prediction schema.
- Fitting-key tuple hash, feature-order hash and compressed-file bytes SHA are distinct. `origin_safe.py:76-83` defines tuple/string hashing; do not compare to the verifier's differently serialized CSV hash.
- Eight metrics: exact_phase_accuracy, phase3plus_accuracy, precision_phase3plus, sensitivity_phase3plus, f2_phase3plus, r2_phase3plus, mae_phase3plus, ordinal_mae. Continuous phase3 metrics use normalized phase3_worse vs phase3_pred; classification uses reported overall_phase>=3. Retain undefined statuses/reasons. Earlier mislabeled accuracy tables are not authoritative.

## Existing checks to extend after approval

- `tests/unit/test_origin_safe.py`: timing/history/IDP/weights/forbidden features/season boundaries.
- `tests/smoke/test_origin_safe_cli.py`: forbidden lag1, future history, changed dataset hashes, dry-run, resume inventory and full annual protocol. Some smoke cases train tiny models; none were run in planning.
- New bounded tests must cover exact oracle windows/B6 dependency missingness, named-version schemas, H0 reference-only, isolated output paths and inherited-feature equality. Region3 and country-stratified paired-bootstrap checks are now specified in design.md and implement.md.

## Live audit state at this planning check

`trellis-audit --repo <exact registered IPCCH path> status`: controller running=false, active_runs=[], IPCCH still registered to the historical Claude executor. Prior task job ae81c0e0a9a141f8cfcf37ad is done/major with gate_open0; this is not a passed audit. Reverify live session, registration and controller at approved start; do not reuse historical executor identity or change gates manually.
