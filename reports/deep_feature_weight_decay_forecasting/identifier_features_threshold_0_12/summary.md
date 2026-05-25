# Deep Feature Weighted Decay Forecasting Summary

Run timestamp: `2026-05-22T04:39:06.593875+00:00`

## Data source replacement

Dataset source: `{'key': 'deep_features_forecasting_dataset', 'path': '/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/Google fund/Analysis/1.Source Data/assembled_IPCCH/forecasting_subset_IPCCH_2026_target_corrected_deep_features_forecasting_ready.csv'}`
Somalia lookup source: `{'key': 'ipcch_2026_completed_dataset', 'path': '/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/Google fund/Analysis/1.Source Data/assembled_IPCCH/IPCCH_2026_completed.csv'}`

## Time-decay weighting

Formula: `weight = 0.5 ** (distance_months / half_life_months)`
Half-life months: `24.0`

## Phase conversion

Cumulative phase threshold: `0.12`

## Identifier feature option

Identifier source: `{'key': 'ipcch_2026_completed_dataset', 'path': '/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/Google fund/Analysis/1.Source Data/assembled_IPCCH/IPCCH_2026_completed.csv'}`
Identifier feature columns: `['lat', 'lon', 'month_1', 'month_2', 'month_3', 'month_4', 'month_5', 'month_6', 'month_7', 'month_8', 'month_9', 'month_10', 'month_11', 'month_12', 'year_2014', 'year_2015', 'year_2016', 'year_2017', 'year_2018', 'year_2019', 'year_2020', 'year_2021', 'year_2022', 'year_2023', 'year_2024', 'year_2025', 'year_2026']`

## Split rule

all-prior-history annual holdout: train date < January 1 of test year; test rows in test calendar year

## Overall metrics

| test_year | n_samples | accuracy | precision_phase3plus | sensitivity_phase3plus | r2_phase3plus | f2_phase3plus |
| --- | --- | --- | --- | --- | --- | --- |
| 2022.0000 | 5599.0000 | 0.5183 | 0.6787 | 0.9325 | 0.3435 | 0.8676 |
| 2023.0000 | 6064.0000 | 0.5203 | 0.6559 | 0.9672 | 0.5080 | 0.8834 |
| 2024.0000 | 5127.0000 | 0.5896 | 0.6272 | 0.9583 | 0.3847 | 0.8668 |
| 2025.0000 | 11415.0000 | 0.4263 | 0.5263 | 1.0000 | 0.2328 | 0.8474 |

## Somalia-only metrics

| test_year | n_samples | accuracy | precision_phase3plus | sensitivity_phase3plus | r2_phase3plus | f2_phase3plus |
| --- | --- | --- | --- | --- | --- | --- |
| 2022.0000 | 1129.0000 | 0.5474 | 0.7574 | 0.9809 | -0.8152 | 0.9262 |
| 2023.0000 | 1217.0000 | 0.4593 | 0.6105 | 1.0000 | 0.1324 | 0.8868 |
| 2024.0000 | 711.0000 | 0.3910 | 0.4465 | 1.0000 | -0.0127 | 0.8013 |
| 2025.0000 | 1876.0000 | 0.4856 | 0.5368 | 1.0000 | 0.0620 | 0.8528 |

## Notebook discipline

Original notebook modified: `false`
