# Optimization planning evidence — 2026-09-25

Read-only source/artifact inspection; no new model fits or implementation tests. The main agent read v1 reports and the archived foundational design; focused agents inspected temporal support and reuse. Findings below inform a forthcoming spec, not completed experiment acceptance.

## Existing calibration and targets

- `scripts/postprocessing/somalia_oracle_calibration_diagnostics.py:83-91`: shift subtracts the mean validation prediction-minus-truth error and clips to [0,1]; isotonic uses `IsotonicRegression(y_min=0,y_max=1,out_of_bounds='clip')`. Identity is implemented separately at lines 238-245; passing `none` to `calibrate()` would incorrectly execute isotonic.
- Lines 227-271 fit mappings to the selected candidate's saved inner predictions and apply them to outer test predictions. This is reusable arithmetic, but it lacks a chronological calibration-fit/calibration-score split for selecting the full procedure.
- `src/ipcch/somalia_oracle/modeling.py:190-230` requires both crisis classes and selects by F2. A q3-RMSE job must not be rejected solely for lacking both crisis classes; AUC can be unavailable while regression error remains defined.
- Four output columns are q2/q3/q4/q5; q3 is index 1. `modeling.py:76-110,166-169` has independent regressors and constants, then column stacking, with no clipping. Missing-baseline rows cannot be passed as NaN residual targets into the unchanged all-target fit path.

## Historical baseline and information sets

- `history.py:78-103,320-338,527-538` constructs `hist_q3_obs1` from valid historical normalized shares; cutoff is U<=O,U<T. `pipeline.py:178-198` retains `history_obs1_source_ord`; absent source is -1 and feature is NaN.
- `pipeline.py:200-203` gives A original features, B adds V2, C adds oracle, D adds rich history. Saved H0 schemas have A=511, B=C=525, D=997 columns. A-C lack historical q3 columns; D includes `hist_q3_obs1`.
- Consequently, a residual baseline added to A-C changes their information set even if it is not an X column. The user subsequently approved restricting residual candidates to D, the main specification; A-C remain comparison baselines.
- Saved primary-cohort valid-share-history support: 2025 H0 1862/1876, H3 268/275, H6 267/275, H12 1073/1100; 2026 H0 904/904. Derived by joining `row_provenance_h*.csv.gz` to frozen cohort keys and checking `history_obs1_source_ord != -1`.
- Phase persistence uses valid reported phase, while share persistence uses `valid_history`; availability flags are not interchangeable (`data.py:365-386`, diagnostics script:126-133). All checked saved history source months obey cutoffs and match the saved source q3. Future history may permit flagged missing-P5 filling without being a valid supervised target.

## Chronological support

Data: `results/experiments/somalia_oracle/v1/ledgers/{label_ledger.csv.gz,jobs.csv,feature_matrix_h*.csv.gz,row_provenance_h*.csv.gz}` and `fits/{inner_folds.csv,validation_predictions.csv.gz}`. Labels were joined to feature keys; counts are feasibility evidence, not executed new calibration fits.

Valid scoring month counts: 2022-01 43, 05 43, 07 517, 10 526; 2023-01 524, 03 345, 08 348; 2024-01 356, 07 355; 2025-04 904, 07 64, 09 4, 10 904. The 2025-09 q3 values are all .45 and all four records are crisis. The 2025-07 labels have only two distinct q3 values. Pool squared errors on fixed keys; do not average undefined monthly R2 or confuse label counts with oracle support.

`modeling.py:128-153` fits an inner target v with labels up to min(v-H,v-1). Any earlier calibration label c must additionally be known at that scoring origin: c<=v-H and c<v. Merely ordering target months is insufficient.

For the ordinary H0 tail, latest three scoring months are 2023-08/2024-01/2024-07 (test2025) and 2025-07/09/10 (test2026). Each has respectively 5/6/7 earlier OOF-supported target months available for calibration. This supports exploring chronological calibration rather than reusing calibration-fit errors for selection; no statistical adequacy guarantee is implied.

Earliest H12 outer origins are 2024-04 (test2025, fit pool2702) and 2025-04 (test2026, fit pool2832). For H12 the latest three inner scoring months have only 0/0/1 earlier OOF-supported calibration months available at each inner scoring origin. Requiring two calibration months before each of three H12 scoring months is therefore infeasible in the current windows. **H12 is not being optimized in this task:** this limitation does not by itself preclude fitting a fixed calibration method on all eligible OOF predictions available at its outer origin. Specify the outer refit support independently of H0 method-selection support.

H3/H6 oracle coverage in training target2025-07 is 11/64 and target2025-09 is 0/4; gaps must not be counted as verified weather just because labels exist. The fixed-recipe source must also be selected without labels later than the receiving outer origin; copying a recipe chosen at a later H0 origin would violate that rule.

## Runtime and reuse boundary

v1 `manifest.json:11-16` records `/home/swl007007/.venvs/ipcch-geo/bin/python`, sklearn1.8.0 and XGBoost3.2.0; read-only imports verified those installed versions. System Python lacks XGBoost and is not the training interpreter. GitNexus queries returned peripheral older flows for the new oracle module; source/artifact anchors above are authoritative for this inspection.
