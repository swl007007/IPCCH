# Deep Feature Weighted Decay Forecasting Summary

Run timestamp: `2026-05-22T05:03:04.089747+00:00`

## Data source replacement

Dataset source: `{'key': 'deep_features_forecasting_dataset', 'path': '/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/Google fund/Analysis/1.Source Data/assembled_IPCCH/forecasting_subset_IPCCH_2026_target_corrected_deep_features_forecasting_ready.csv'}`
Somalia lookup source: `{'key': 'ipcch_2026_completed_dataset', 'path': '/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/Google fund/Analysis/1.Source Data/assembled_IPCCH/IPCCH_2026_completed.csv'}`

## Time-decay weighting

Formula: `weight = 0.5 ** (distance_months / half_life_months)`
Half-life months: `24.0`

## Phase conversion

Cumulative phase threshold: `0.15`

## Identifier feature option

Identifier source: `{'key': 'ipcch_2026_completed_dataset', 'path': '/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/Google fund/Analysis/1.Source Data/assembled_IPCCH/IPCCH_2026_completed.csv'}`
Identifier feature columns: `['lat', 'lon', 'month_1', 'month_2', 'month_3', 'month_4', 'month_5', 'month_6', 'month_7', 'month_8', 'month_9', 'month_10', 'month_11', 'month_12', 'year_2014', 'year_2015', 'year_2016', 'year_2017', 'year_2018', 'year_2019', 'year_2020', 'year_2021', 'year_2022', 'year_2023', 'year_2024', 'year_2025', 'year_2026']`

## Split rule

all-prior-history annual holdout: train date < January 1 of test year; test rows in test calendar year

## Overall metrics

| test_year | n_samples | accuracy | precision_phase3plus | sensitivity_phase3plus | r2_phase3plus | f2_phase3plus |
| --- | --- | --- | --- | --- | --- | --- |
| 2022.0000 | 5599.0000 | 0.5406 | 0.7047 | 0.8650 | 0.3435 | 0.8274 |
| 2023.0000 | 6064.0000 | 0.5754 | 0.6922 | 0.9481 | 0.5080 | 0.8828 |
| 2024.0000 | 5127.0000 | 0.6189 | 0.6604 | 0.8929 | 0.3847 | 0.8342 |
| 2025.0000 | 11415.0000 | 0.4524 | 0.5290 | 0.9998 | 0.2328 | 0.8488 |

## Somalia-only metrics

| test_year | n_samples | accuracy | precision_phase3plus | sensitivity_phase3plus | r2_phase3plus | f2_phase3plus |
| --- | --- | --- | --- | --- | --- | --- |
| 2022.0000 | 1129.0000 | 0.5173 | 0.7840 | 0.8327 | -0.8152 | 0.8225 |
| 2023.0000 | 1217.0000 | 0.5201 | 0.6298 | 0.9960 | 0.1324 | 0.8922 |
| 2024.0000 | 711.0000 | 0.4037 | 0.4474 | 0.9937 | -0.0127 | 0.7987 |
| 2025.0000 | 1876.0000 | 0.4899 | 0.5368 | 1.0000 | 0.0620 | 0.8528 |

## Notebook discipline

Original notebook modified: `false`
