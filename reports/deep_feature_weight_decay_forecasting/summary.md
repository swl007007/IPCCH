# Deep Feature Weighted Decay Forecasting Summary

Run timestamp: `2026-05-21T21:32:06.770105+00:00`

## Data source replacement

Dataset source: `{'key': 'deep_features_forecasting_dataset', 'path': '/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/Google fund/Analysis/1.Source Data/assembled_IPCCH/forecasting_subset_IPCCH_2026_target_corrected_deep_features_forecasting_ready.csv'}`
Somalia lookup source: `{'key': 'ipcch_2026_completed_dataset', 'path': '/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/Google fund/Analysis/1.Source Data/assembled_IPCCH/IPCCH_2026_completed.csv'}`

## Time-decay weighting

Formula: `weight = 0.5 ** (distance_months / half_life_months)`
Half-life months: `24.0`

## Split rule

all-prior-history annual holdout: train date < January 1 of test year; test rows in test calendar year

## Overall metrics

| test_year | n_samples | accuracy | precision_phase3plus | sensitivity_phase3plus | r2_phase3plus | f2_phase3plus |
| --- | --- | --- | --- | --- | --- | --- |
| 2022.0000 | 5599.0000 | 0.5612 | 0.7742 | 0.7327 | 0.3930 | 0.7406 |
| 2023.0000 | 6064.0000 | 0.5956 | 0.7074 | 0.9064 | 0.4795 | 0.8581 |
| 2024.0000 | 5127.0000 | 0.6156 | 0.6880 | 0.8078 | 0.3778 | 0.7806 |
| 2025.0000 | 11415.0000 | 0.5139 | 0.5789 | 0.9567 | 0.2088 | 0.8462 |

## Somalia-only metrics

| test_year | n_samples | accuracy | precision_phase3plus | sensitivity_phase3plus | r2_phase3plus | f2_phase3plus |
| --- | --- | --- | --- | --- | --- | --- |
| 2022.0000 | 1129.0000 | 0.4154 | 0.7391 | 0.5651 | -0.6061 | 0.5930 |
| 2023.0000 | 1217.0000 | 0.5201 | 0.6226 | 0.9704 | 0.0142 | 0.8729 |
| 2024.0000 | 711.0000 | 0.4149 | 0.4699 | 0.8864 | -0.0131 | 0.7529 |
| 2025.0000 | 1876.0000 | 0.5144 | 0.5559 | 0.9573 | -0.0234 | 0.8365 |

## Notebook discipline

Original notebook modified: `false`
