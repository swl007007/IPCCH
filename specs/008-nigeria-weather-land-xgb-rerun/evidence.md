# Execution Evidence: Nigeria Weather-Land XGBoost Rerun

**Execution date**: 2026-08-25  
**Validation status**: Executed and passed

## Frozen Inputs and Provenance

- Release: `nga-weather-land-20260825-v1`
- Release manifest SHA-256: `f5eec437693a4e28ba32ce3c39ba581fa7532023ca527e2300a67921c8a64573`
- Git HEAD at preflight: `28a16725790e1e2d7e38cc0c0be799cabd3a01ff`
- Exact input, runner, selector, lookup, identifier source, and hyperparameter hashes are recorded in `results/preflight/nga-weather-land-20260825-v1/preflight_manifest.json` and copied to each new scope as `metadata/experiment_provenance.json`.
- The dirty worktree was preserved; no existing user changes were reverted.

## Preflight Evidence

The enhanced preflight command completed with `Preflight PASS` and verified for every scope:

- 6,538 rows and 545 Nigeria areas;
- no duplicate area/year/month keys;
- exactly 16 added, non-empty weather-land predictors;
- expected inherited all-null legacy-column contract;
- exact equality with the 4,100 historical eligible evaluation keys;
- clear final output directories;
- dependency hashes and Git dirty state;
- SPI QA status counts.

The original runner's three independent dry-runs also exited zero and printed `Dry run completed without fitting models.` Feature counts were:

| Scope | Historical | New | Difference |
|---|---:|---:|---:|
| 0m / fs0 | 528 | 544 | +16 |
| 3m / fs1 | 529 | 545 | +16 |
| 6m / fs2 | 529 | 545 | +16 |

All scopes retained the same split diagnostics: 2022–2025 holdouts, strictly earlier training records, and monotonic time-decay weights.

## Full-Run Evidence

The sequential fs0→fs1→fs2 full-run command exited zero. Each scope produced:

- 13 machine-readable result files: 4 predictions, 4 annual metric JSONs, 2 consolidated metric CSVs, split diagnostics, runner metadata, and experiment provenance;
- 3 report files;
- no SHAP artifacts;
- prediction rows of 883, 1,069, 1,058, and 1,090 for 2022–2025;
- unique prediction keys, Nigeria-only metadata, seed 42, threshold 0.20, half-life 24, and the expected feature count.

Historical experiment artifact modification times were all earlier than the new experiment artifacts, consistent with the explicit non-overlapping output paths and absence of `--overwrite`.

## Paired Overall-Phase MAE

MAE is a derived comparison diagnostic added for this rerun; it was not stored as a formal metric by the historical experiment.

| Scope | Year | Old MAE | New MAE | New − Old |
|---|---:|---:|---:|---:|
| 0m | 2022 | 0.509626 | 0.502831 | -0.006795 |
| 0m | 2023 | 0.376988 | 0.375117 | -0.001871 |
| 0m | 2024 | 0.125709 | 0.125709 | 0.000000 |
| 0m | 2025 | 0.101835 | 0.100000 | -0.001835 |
| 3m | 2022 | 0.518686 | 0.514156 | -0.004530 |
| 3m | 2023 | 0.370440 | 0.374181 | +0.003742 |
| 3m | 2024 | 0.123819 | 0.120038 | -0.003781 |
| 3m | 2025 | 0.101835 | 0.103670 | +0.001835 |
| 6m | 2022 | 0.511891 | 0.498301 | -0.013590 |
| 6m | 2023 | 0.372311 | 0.373246 | +0.000935 |
| 6m | 2024 | 0.115312 | 0.118147 | +0.002836 |
| 6m | 2025 | 0.101835 | 0.099083 | -0.002752 |

The machine-readable table is `reports/deep_feature_weight_decay_forecasting/nga_weather_land_v1_paired_mae.csv`.

## Final Verification Command Result

A fresh assertion-based verification exited zero and reported:

```text
0m PASS result_files=13 report_files=3 features=544 prediction_rows=[883,1069,1058,1090]
3m PASS result_files=13 report_files=3 features=545 prediction_rows=[883,1069,1058,1090]
6m PASS result_files=13 report_files=3 features=545 prediction_rows=[883,1069,1058,1090]
paired_mae PASS rows=12
preflight_manifest PASS all assertions true
historical_artifact_mtime_boundary PASS
```
