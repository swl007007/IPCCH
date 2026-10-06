# Global model rerun with 2015-2026 climate features (0m/3m/6m/12m)

## Goal

Measure what the new 2015–2026 climate release does to the canonical **global** IPCCH model at the 0m, 3m, 6m and 12m scopes.

The only change is to the features: the old FLDAS/MODIS climate features are replaced by features engineered from:

- `IPCCH_shared_folder/climate_monthly_2015_2026_MODELING_READY.csv` (monthly)
- `IPCCH_shared_folder/climate_2015_2026_MODELING_READY.csv` (growing season)

The training code, rows, hyperparameters, split policy and metrics stay the same. No Somalia local model is run.

## Decisions (grill, 2026-10-05)

| Topic | Decision |
|---|---|
| Fork | New git branch. Add a feature-builder module and script. Run the **unchanged** `run_deep_feature_weight_decay_forecasting.py` CLI on the new datasets via `--dataset`. |
| Feature mode | **Replace** old climate features. Old = every column built from `Rainf_f_tavg_mean`, `Tair_f_tavg_mean`, `SoilMoi00_10cm_tavg_mean` or `EVI_mean`, including their stress, neighbour and interaction columns. **GPP features are kept** because the new data has no GPP analog. |
| Monthly engineering | **Full mirror** of the existing upstream recipe (`assemble_latest_IPCCH/build_deep_ipcch_features.py` + `build_multiscope_ipcch_features.py`), applied to **all 14 `_month_ensmean` variables**. |
| Stress thresholds | Fixed standard thresholds: deficit = `spi03 ≤ −1`; hot = `tmean_anom ≥ +1 °C`; vegetation = `evi_anom ≤ −0.015`. Spell, neighbour and interaction families are mirrored on these. |
| Seasonal alignment | The **2 most recent growing seasons completed** by the end of the scope's origin month, with the 14 `_gs_ensmean` values and months since each season ended. |
| Scope origin | Keep the existing convention: latest source month is `t−s` (0m uses month `t`; 12m uses `t−12`). |
| Source columns | Only `*_ensmean` values are used. Per-source columns, `_n_sources` and `_ens_sd` are excluded, following the shared-folder audit of 2026-09-30. |
| Early rows | Training rows are unchanged. Pre-2015 history is missing in the new data, so its features are NaN and XGBoost handles them natively. |
| Test years | 2022, 2023, 2024, 2025, with all-prior-history annual holdouts as in the baseline. |
| Baseline | **Rerun the baseline** with the current code and the same flags, so that differences come from features only. Also compare against the 2026-05-31 baseline outputs to show any effect of code drift. |
| Data location | Derived datasets go to `1.Source Data/assembled_IPCCH/model_ready/climate2015_v1/`, outside the repo. |
| Scope-block gap (added after the fidelity gate) | Upstream builds `_sH` columns by shifting asof12 rows, so every scope-block feature is NaN for the last 12−H months of its source grid. For test year 2025 this means 59.7% of rows at 0m, 46.1% at 3m and 1.6% at 6m. **Primary comparison (`masked`)**: new scope-anchored features are set to NaN on exactly the rows where the old `Rainf_f_tavg_mean__l{H}_s{H}` is NaN, so only the climate source differs. **Extra arm (`unmasked`, fs0–fs2)**: no masking, which shows the value of contemporaneous climate in those rows. fs3 has no scope block and needs a single dataset. Total: 11 runs. |
| Out of scope | Somalia local models; SHAP; hyperparameter or threshold tuning; a 2026 test year; Trellis audit enrollment (not requested). |

## Requirements

1. A builder produces four model-ready datasets (fs0/fs1/fs2/fs3). Each has the same rows and the same non-climate columns as the current file for that scope. Old climate columns are removed and the new climate columns are added.
2. Every new feature uses only source months `≤ t−s` (seasonal: seasons whose end date is no later than the end of month `t−s`). Every derived family declares its anchor in a feature manifest.
3. The engineering code is a fork of the upstream recipe. Its fidelity is shown by recomputing old FLDAS features from the raw interim panel and matching the current dataset values for a sample of areas.
4. Eleven global runs (baseline × 4, masked climate2015 × 4, unmasked climate2015 × 3) with identical CLI flags apart from `--dataset` and output directories: see Decisions. Flags: `--region-scope 0 --add-identifier-features --phase-threshold 0.2 --half-life-months 24 --test-years 2022 2023 2024 2025 --seed 42`.
5. A comparison table and short report covering accuracy, precision and sensitivity for phase 3+, R² for phase 3+, and F2, per scope and test year, with climate2015 − rerun-baseline deltas.

## Acceptance Criteria

- [ ] Four datasets plus a manifest and build summary (input sha256, removed/added column counts, row-key parity) exist in the external directory. Row keys equal the source scope files.
- [ ] Unit tests pass. They cover anchor safety (no feature reads a month after `t−s`), the season-completion rule, threshold logic, and fidelity of the forked engineering code.
- [ ] The fidelity check reproduces sampled old FLDAS feature values within floating tolerance for each family type: lag, rolling, trend, dispersion, stress, same-month history and scope block. Any family that does not match is explained in `evidence.md`.
- [ ] All 11 runs finish. `metrics_overall.csv` is present for each.
- [ ] The comparison CSV and report are written, and the report states uncertainty (single seed, no intervals).
- [ ] The rerun baseline is compared with the 2026-05-31 baseline. Any material drift is reported, not hidden.

## Notes

- Shared-folder audit caveats are carried into the report rather than fixed here: the 2025 source-coverage break for Terra NDVI/EVI and CPC; partial 2026 seasons; and an unknown climatology baseline for the anomalies, which could carry a mild look-ahead in standardization.
