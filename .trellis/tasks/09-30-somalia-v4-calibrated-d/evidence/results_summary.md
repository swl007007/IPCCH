# Somalia v4 calibrated D — results

Code `a88a1f583c928064a3b565eb337b5ec7afb038b8`; mode `full`. Two distinct label scenarios, each evaluated on its own population: **original** uses observed raw labels only in every role (fit, selection, calibration, test); **augmented** also admits permitted validity-period copies in every role. Score differences between the settings are not augmentation effects and are not ranked. Each (setting, outer year, horizon, origin) selected its own recipe from 6 bundles × 4 half-lives × direct/residual × none/shift/isotonic by pooled training-period OOF final-q3 RMSE (AUC only breaks numerical ties). Retrospective oracle-information evaluation (ideal label availability, realized future weather); not operational forecast skill.

Outer cohorts at H>0 keep only rows whose realized weather at the oracle offsets is verified (inherited rule, frozen before fitting). Rows removed by this rule (removed / cohort): augmented 2025 H3 1601/1876, augmented 2025 H6 1601/1876, augmented 2025 H12 776/1876, augmented 2026 H3 904/904, augmented 2026 H6 904/904, augmented 2026 H12 772/904, original 2025 H3 1601/1876, original 2025 H6 1601/1876, original 2025 H12 776/1876, original 2026 H3 904/904, original 2026 H6 904/904, original 2026 H12 772/904. Pooled H>0 results are therefore weighted towards the years with verified weather.

Copies admitted to the augmented scenario: 4409 (2019: 146, 2020: 296, 2021: 178, 2022: 1374, 2023: 995, 2024: 1420). Earliest supervised label year: 2017.

## augmented: annual (each year's own frozen cohort)

| Year | H | Status | n (copies) | Final R² | Raw R² | RMSE (pp) | MAE (pp) | Bias (pp) | Final AUC | F1 | Precision | Recall |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2022 | 0 | complete | 2094.0 (1374.0) | -0.197 | -0.586 | 24.41 | 20.28 | -16.55 | 0.765 | 0.924 | 0.898 | 0.952 |
| 2023 | 0 | complete | 2013.0 (995.0) | -0.191 | 0.145 | 22.68 | 18.52 | 14.23 | 0.826 | 0.821 | 0.696 | 0.999 |
| 2024 | 0 | complete | 2130.0 (1420.0) | 0.367 | 0.367 | 12.49 | 9.97 | 1.32 | 0.761 | 0.675 | 0.592 | 0.786 |
| 2025 | 0 | complete | 1876.0 (0.0) | 0.125 | 0.125 | 12.14 | 9.56 | 1.62 | 0.724 | 0.729 | 0.658 | 0.817 |
| 2026 | 0 | complete | 904.0 (0.0) | -0.189 | 0.130 | 19.53 | 15.32 | -10.34 | 0.737 | 0.615 | 0.812 | 0.495 |
| 2022 | 3 | complete | 2094.0 (1374.0) | -1.218 | -1.218 | 33.24 | 28.01 | -25.49 | 0.624 | 0.699 | 0.863 | 0.587 |
| 2023 | 3 | complete | 2013.0 (995.0) | -0.267 | 0.148 | 23.38 | 19.03 | 15.32 | 0.820 | 0.818 | 0.693 | 0.999 |
| 2024 | 3 | complete | 2130.0 (1420.0) | 0.309 | 0.309 | 13.05 | 10.34 | 1.54 | 0.761 | 0.682 | 0.583 | 0.823 |
| 2025 | 3 | complete | 275.0 (0.0) | 0.058 | 0.058 | 12.68 | 10.19 | 1.67 | 0.697 | 0.660 | 0.590 | 0.750 |
| 2026 | 3 | empty_cohort: no source-eligible rows | 0 | | | | | | | | | |
| 2022 | 6 | complete | 2094.0 (1374.0) | -0.677 | -1.129 | 28.90 | 24.59 | -18.37 | 0.512 | 0.906 | 0.828 | 0.999 |
| 2023 | 6 | incomplete: 696 of 2013 required final predictions missing or unavailable | 2013 | | | | | | | | | |
| 2024 | 6 | complete | 2130.0 (1420.0) | -0.001 | -0.016 | 15.71 | 12.47 | 4.95 | 0.692 | 0.649 | 0.525 | 0.849 |
| 2025 | 6 | complete | 275.0 (0.0) | 0.063 | 0.063 | 12.65 | 10.28 | 1.57 | 0.701 | 0.687 | 0.602 | 0.800 |
| 2026 | 6 | empty_cohort: no source-eligible rows | 0 | | | | | | | | | |
| 2022 | 12 | complete | 2094.0 (1374.0) | -1.502 | -1.507 | 35.30 | 29.90 | -27.38 | 0.548 | 0.032 | 1.000 | 0.016 |
| 2023 | 12 | complete | 2013.0 (995.0) | -0.988 | -0.459 | 29.29 | 25.17 | 7.30 | 0.488 | 0.772 | 0.628 | 1.000 |
| 2024 | 12 | complete | 2130.0 (1420.0) | -3.900 | -0.588 | 34.76 | 29.71 | 26.84 | 0.488 | 0.622 | 0.452 | 0.993 |
| 2025 | 12 | complete | 1100.0 (0.0) | 0.053 | 0.053 | 13.55 | 10.51 | -0.39 | 0.669 | 0.641 | 0.591 | 0.699 |
| 2026 | 12 | complete | 132.0 (0.0) | 0.150 | 0.150 | 16.60 | 13.37 | -4.21 | 0.733 | 0.810 | 0.782 | 0.840 |

## augmented: pooled 2022-2026 (concatenated annual out-of-sample rows, equal weight per area-month)

| H | Status | Rows by year | n (copies) | Final R² | Raw R² | RMSE (pp) | MAE (pp) | Bias (pp) | Final AUC | F1 | Precision | Recall |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | complete | 2022:2094;2023:2013;2024:2130;2025:1876;2026:904 | 9017.0 (3789.0) | 0.170 | 0.164 | 18.95 | 14.72 | -1.06 | 0.749 | 0.793 | 0.732 | 0.865 |
| 3 | complete | 2022:2094;2023:2013;2024:2130;2025:275 | 6512.0 (3789.0) | -0.193 | -0.081 | 24.22 | 18.70 | -2.89 | 0.671 | 0.736 | 0.701 | 0.775 |
| 6 | incomplete: annual slots incomplete: 2023 | | | | | | | | | | | |
| 12 | complete | 2022:2094;2023:2013;2024:2130;2025:1100;2026:132 | 7469.0 (3789.0) | -1.051 | -0.421 | 30.93 | 25.43 | 1.81 | 0.420 | 0.569 | 0.553 | 0.586 |

## original: annual (each year's own frozen cohort)

| Year | H | Status | n (copies) | Final R² | Raw R² | RMSE (pp) | MAE (pp) | Bias (pp) | Final AUC | F1 | Precision | Recall |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2022 | 0 | complete | 720.0 (0.0) | -0.602 | -0.602 | 28.01 | 24.10 | -22.00 | 0.764 | 0.859 | 0.889 | 0.831 |
| 2023 | 0 | complete | 1018.0 (0.0) | -0.928 | 0.020 | 28.71 | 24.57 | 21.33 | 0.778 | 0.771 | 0.628 | 1.000 |
| 2024 | 0 | complete | 710.0 (0.0) | 0.370 | 0.370 | 12.46 | 9.72 | 1.05 | 0.790 | 0.707 | 0.617 | 0.827 |
| 2025 | 0 | complete | 1876.0 (0.0) | -0.043 | -0.043 | 13.25 | 10.58 | 3.93 | 0.688 | 0.729 | 0.634 | 0.857 |
| 2026 | 0 | complete | 904.0 (0.0) | -0.032 | 0.101 | 18.19 | 14.79 | -6.63 | 0.700 | 0.702 | 0.729 | 0.677 |
| 2022 | 3 | complete | 720.0 (0.0) | -1.058 | -1.058 | 31.74 | 26.60 | -24.35 | 0.716 | 0.813 | 0.887 | 0.751 |
| 2023 | 3 | complete | 1018.0 (0.0) | -1.268 | -0.006 | 31.15 | 27.04 | 24.97 | 0.789 | 0.772 | 0.628 | 1.000 |
| 2024 | 3 | complete | 710.0 (0.0) | 0.381 | 0.381 | 12.35 | 9.86 | 0.66 | 0.785 | 0.711 | 0.639 | 0.802 |
| 2025 | 3 | complete | 275.0 (0.0) | -0.037 | -0.037 | 13.30 | 10.89 | 2.77 | 0.645 | 0.611 | 0.541 | 0.700 |
| 2026 | 3 | empty_cohort: no source-eligible rows | 0 | | | | | | | | | |
| 2022 | 6 | complete | 720.0 (0.0) | -1.470 | -1.470 | 34.77 | 29.45 | -26.85 | 0.501 | 0.118 | 0.826 | 0.064 |
| 2023 | 6 | complete | 1018.0 (0.0) | -0.956 | 0.044 | 28.92 | 23.89 | 20.43 | 0.676 | 0.771 | 0.628 | 1.000 |
| 2024 | 6 | complete | 710.0 (0.0) | -0.663 | -0.116 | 20.25 | 15.95 | 9.32 | 0.620 | 0.650 | 0.530 | 0.840 |
| 2025 | 6 | complete | 275.0 (0.0) | 0.070 | 0.070 | 12.60 | 10.59 | 4.48 | 0.774 | 0.739 | 0.596 | 0.971 |
| 2026 | 6 | empty_cohort: no source-eligible rows | 0 | | | | | | | | | |
| 2022 | 12 | complete | 720.0 (0.0) | -2.146 | -2.146 | 39.24 | 33.28 | -32.35 | 0.442 | 0.000 | — | 0.000 |
| 2023 | 12 | complete | 1018.0 (0.0) | -1.029 | -0.558 | 29.46 | 24.36 | -4.45 | 0.528 | 0.485 | 0.614 | 0.401 |
| 2024 | 12 | complete | 710.0 (0.0) | -4.682 | -0.624 | 37.43 | 33.90 | 32.96 | 0.475 | 0.612 | 0.441 | 1.000 |
| 2025 | 12 | complete | 1100.0 (0.0) | -2.058 | -2.093 | 24.35 | 18.70 | 13.70 | 0.687 | 0.697 | 0.560 | 0.922 |
| 2026 | 12 | complete | 132.0 (0.0) | -0.001 | -0.001 | 18.01 | 14.51 | -5.39 | 0.649 | 0.608 | 0.672 | 0.556 |

## original: pooled 2022-2026 (concatenated annual out-of-sample rows, equal weight per area-month)

| H | Status | Rows by year | n (copies) | Final R² | Raw R² | RMSE (pp) | MAE (pp) | Bias (pp) | Final AUC | F1 | Precision | Recall |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | complete | 2022:720;2023:1018;2024:710;2025:1876;2026:904 | 5228.0 (0.0) | -0.118 | 0.118 | 20.25 | 15.77 | 1.53 | 0.673 | 0.754 | 0.680 | 0.847 |
| 3 | complete | 2022:720;2023:1018;2024:710;2025:275 | 2723.0 (0.0) | -0.471 | -0.038 | 26.20 | 20.82 | 3.35 | 0.648 | 0.759 | 0.685 | 0.850 |
| 6 | complete | 2022:720;2023:1018;2024:710;2025:275 | 2723.0 (0.0) | -0.618 | -0.200 | 27.48 | 21.94 | 3.42 | 0.542 | 0.619 | 0.602 | 0.637 |
| 12 | complete | 2022:720;2023:1018;2024:710;2025:1100;2026:132 | 3680.0 (0.0) | -1.400 | -0.808 | 31.63 | 25.90 | 2.70 | 0.423 | 0.523 | 0.534 | 0.512 |

## Selected recipes (per job)

| Job | Status | Formulation | Bundle | Half-life | Calibration | Validation RMSE | Validation AUC |
|---|---|---|---|---|---|---:|---:|
| augmented_y2022_h00_o2022-01 | ok | residual | X5 | none | shift | 0.07281 | 0.873 |
| augmented_y2022_h00_o2022-05 | ok | residual | X5 | none | shift | 0.07281 | 0.873 |
| augmented_y2022_h00_o2022-07 | ok | residual | X5 | none | shift | 0.07281 | 0.873 |
| augmented_y2022_h00_o2022-08 | ok | residual | X5 | none | shift | 0.07281 | 0.873 |
| augmented_y2022_h00_o2022-09 | ok | residual | X5 | none | shift | 0.07281 | 0.873 |
| augmented_y2022_h00_o2022-10 | ok | residual | X5 | none | shift | 0.07281 | 0.873 |
| augmented_y2022_h00_o2022-11 | ok | residual | X5 | none | shift | 0.07281 | 0.873 |
| augmented_y2022_h00_o2022-12 | ok | residual | X5 | none | shift | 0.07281 | 0.873 |
| augmented_y2023_h00_o2023-01 | ok | residual | X3 | 24 | shift | 0.17021 | 0.809 |
| augmented_y2023_h00_o2023-02 | ok | residual | X3 | 24 | shift | 0.17021 | 0.809 |
| augmented_y2023_h00_o2023-03 | ok | residual | X3 | 24 | shift | 0.17021 | 0.809 |
| augmented_y2023_h00_o2023-08 | ok | residual | X3 | 24 | shift | 0.17021 | 0.809 |
| augmented_y2023_h00_o2023-09 | ok | residual | X3 | 24 | shift | 0.17021 | 0.809 |
| augmented_y2024_h00_o2024-01 | ok | direct | X6 | 24 | none | 0.18169 | 0.800 |
| augmented_y2024_h00_o2024-02 | ok | direct | X6 | 24 | none | 0.18169 | 0.800 |
| augmented_y2024_h00_o2024-03 | ok | direct | X6 | 24 | none | 0.18169 | 0.800 |
| augmented_y2024_h00_o2024-07 | ok | direct | X6 | 24 | none | 0.18169 | 0.800 |
| augmented_y2024_h00_o2024-08 | ok | direct | X6 | 24 | none | 0.18169 | 0.800 |
| augmented_y2024_h00_o2024-09 | ok | direct | X6 | 24 | none | 0.18169 | 0.800 |
| augmented_y2025_h00_o2025-04 | ok | direct | X6 | 24 | none | 0.14525 | 0.744 |
| augmented_y2025_h00_o2025-07 | ok | direct | X6 | 24 | none | 0.14525 | 0.744 |
| augmented_y2025_h00_o2025-09 | ok | direct | X6 | 24 | none | 0.14525 | 0.744 |
| augmented_y2025_h00_o2025-10 | ok | direct | X6 | 24 | none | 0.14525 | 0.744 |
| augmented_y2026_h00_o2026-04 | ok | residual | X6 | 24 | shift | 0.10762 | 0.805 |
| augmented_y2022_h03_o2021-10 | ok | direct | X3 | none | none | 0.07697 | 0.851 |
| augmented_y2022_h03_o2022-02 | ok | direct | X3 | none | none | 0.07697 | 0.851 |
| augmented_y2022_h03_o2022-04 | ok | direct | X3 | none | none | 0.07697 | 0.851 |
| augmented_y2022_h03_o2022-05 | ok | direct | X3 | none | none | 0.07697 | 0.851 |
| augmented_y2022_h03_o2022-06 | ok | direct | X3 | none | none | 0.07697 | 0.851 |
| augmented_y2022_h03_o2022-07 | ok | direct | X3 | none | none | 0.07697 | 0.851 |
| augmented_y2022_h03_o2022-08 | ok | direct | X3 | none | none | 0.07697 | 0.851 |
| augmented_y2022_h03_o2022-09 | ok | direct | X3 | none | none | 0.07697 | 0.851 |
| augmented_y2023_h03_o2022-10 | ok | residual | X6 | 24 | shift | 0.20289 | 0.715 |
| augmented_y2023_h03_o2022-11 | ok | residual | X6 | 24 | shift | 0.18619 | 0.786 |
| augmented_y2023_h03_o2022-12 | ok | residual | X6 | 24 | shift | 0.17398 | 0.828 |
| augmented_y2023_h03_o2023-05 | ok | residual | X6 | 24 | shift | 0.17398 | 0.828 |
| augmented_y2023_h03_o2023-06 | ok | residual | X6 | 24 | shift | 0.17398 | 0.828 |
| augmented_y2024_h03_o2023-10 | ok | direct | X6 | none | none | 0.18440 | 0.798 |
| augmented_y2024_h03_o2023-11 | ok | direct | X6 | none | none | 0.18440 | 0.798 |
| augmented_y2024_h03_o2023-12 | ok | direct | X6 | none | none | 0.18440 | 0.798 |
| augmented_y2024_h03_o2024-04 | ok | direct | X6 | none | none | 0.18440 | 0.798 |
| augmented_y2024_h03_o2024-05 | ok | direct | X6 | none | none | 0.18440 | 0.798 |
| augmented_y2024_h03_o2024-06 | ok | direct | X6 | none | none | 0.18440 | 0.798 |
| augmented_y2025_h03_o2025-01 | ok | direct | X1 | none | none | 0.15224 | 0.728 |
| augmented_y2025_h03_o2025-04 | ok | direct | X1 | none | none | 0.15224 | 0.728 |
| augmented_y2025_h03_o2025-07 | ok | direct | X1 | none | none | 0.15224 | 0.728 |
| augmented_y2022_h06_o2021-07 | ok | residual | X1 | none | shift | 0.08278 | 0.841 |
| augmented_y2022_h06_o2021-11 | ok | residual | X1 | none | shift | 0.08170 | 0.838 |
| augmented_y2022_h06_o2022-01 | ok | residual | X1 | none | shift | 0.08170 | 0.838 |
| augmented_y2022_h06_o2022-02 | ok | residual | X1 | none | shift | 0.08170 | 0.838 |
| augmented_y2022_h06_o2022-03 | ok | residual | X1 | none | shift | 0.08170 | 0.838 |
| augmented_y2022_h06_o2022-04 | ok | residual | X1 | none | shift | 0.08170 | 0.838 |
| augmented_y2022_h06_o2022-05 | ok | residual | X1 | none | shift | 0.08170 | 0.838 |
| augmented_y2022_h06_o2022-06 | ok | residual | X1 | none | shift | 0.08170 | 0.838 |
| augmented_y2023_h06_o2022-07 | ok | direct | X1 | none | shift | 0.24292 | 0.486 |
| augmented_y2023_h06_o2022-08 | ok | residual | X3 | none | shift | 0.24718 | 0.456 |
| augmented_y2023_h06_o2022-09 | ok | residual | X2 | none | shift | 0.26014 | 0.472 |
| augmented_y2023_h06_o2023-02 | ok | residual | X6 | 12 | isotonic | 0.25615 | 0.539 |
| augmented_y2023_h06_o2023-03 | ok | residual | X6 | 12 | isotonic | 0.25615 | 0.539 |
| augmented_y2024_h06_o2023-07 | ok | residual | X6 | 12 | isotonic | 0.22954 | 0.642 |
| augmented_y2024_h06_o2023-08 | ok | residual | X1 | 48 | none | 0.18945 | 0.770 |
| augmented_y2024_h06_o2023-09 | ok | residual | X2 | none | none | 0.19083 | 0.741 |
| augmented_y2024_h06_o2024-01 | ok | residual | X2 | none | none | 0.19083 | 0.741 |
| augmented_y2024_h06_o2024-02 | ok | residual | X2 | none | none | 0.19083 | 0.741 |
| augmented_y2024_h06_o2024-03 | ok | residual | X2 | none | none | 0.19083 | 0.741 |
| augmented_y2025_h06_o2024-10 | ok | direct | X6 | none | none | 0.16421 | 0.687 |
| augmented_y2025_h06_o2025-01 | ok | direct | X6 | none | none | 0.16421 | 0.687 |
| augmented_y2025_h06_o2025-04 | ok | direct | X6 | none | none | 0.16421 | 0.687 |
| augmented_y2022_h12_o2021-01 | ok | direct | X6 | 12 | isotonic | 0.07619 | 0.809 |
| augmented_y2022_h12_o2021-05 | ok | direct | X6 | 12 | isotonic | 0.09202 | 0.734 |
| augmented_y2022_h12_o2021-07 | ok | direct | X1 | 12 | none | 0.09543 | 0.652 |
| augmented_y2022_h12_o2021-08 | ok | direct | X1 | 12 | none | 0.09599 | 0.647 |
| augmented_y2022_h12_o2021-09 | ok | direct | X1 | 12 | none | 0.09667 | 0.641 |
| augmented_y2022_h12_o2021-10 | ok | direct | X1 | 12 | none | 0.09667 | 0.641 |
| augmented_y2022_h12_o2021-11 | ok | direct | X1 | 12 | none | 0.09667 | 0.641 |
| augmented_y2022_h12_o2021-12 | ok | direct | X1 | 12 | none | 0.09667 | 0.641 |
| augmented_y2023_h12_o2022-01 | ok | residual | X6 | 12 | shift | 0.10597 | 0.624 |
| augmented_y2023_h12_o2022-02 | ok | residual | X6 | 12 | shift | 0.10597 | 0.624 |
| augmented_y2023_h12_o2022-03 | ok | residual | X6 | 12 | shift | 0.10597 | 0.624 |
| augmented_y2023_h12_o2022-08 | ok | direct | X6 | 12 | shift | 0.32262 | 0.517 |
| augmented_y2023_h12_o2022-09 | ok | direct | X6 | 12 | shift | 0.32124 | 0.519 |
| augmented_y2024_h12_o2023-01 | ok | direct | X6 | 12 | shift | 0.30847 | 0.472 |
| augmented_y2024_h12_o2023-02 | ok | direct | X6 | 12 | shift | 0.29960 | 0.436 |
| augmented_y2024_h12_o2023-03 | ok | direct | X1 | 12 | shift | 0.27147 | 0.398 |
| augmented_y2024_h12_o2023-07 | ok | direct | X1 | 12 | shift | 0.27147 | 0.398 |
| augmented_y2024_h12_o2023-08 | ok | direct | X3 | none | isotonic | 0.24381 | 0.507 |
| augmented_y2024_h12_o2023-09 | ok | direct | X3 | 12 | none | 0.24578 | 0.473 |
| augmented_y2025_h12_o2024-04 | ok | direct | X3 | 12 | none | 0.21933 | 0.498 |
| augmented_y2025_h12_o2024-07 | ok | direct | X5 | 24 | none | 0.20206 | 0.564 |
| augmented_y2025_h12_o2024-10 | ok | residual | X5 | none | none | 0.18870 | 0.636 |
| augmented_y2026_h12_o2025-04 | ok | direct | X5 | 24 | none | 0.17234 | 0.599 |
| original_y2022_h00_o2022-01 | ok | residual | X3 | none | none | 0.07528 | 0.846 |
| original_y2022_h00_o2022-05 | ok | residual | X3 | none | none | 0.07528 | 0.846 |
| original_y2022_h00_o2022-07 | ok | residual | X3 | none | none | 0.07528 | 0.846 |
| original_y2022_h00_o2022-10 | ok | residual | X3 | none | none | 0.07528 | 0.846 |
| original_y2023_h00_o2023-01 | ok | residual | X4 | none | shift | 0.17766 | 0.745 |
| original_y2023_h00_o2023-03 | ok | residual | X4 | none | shift | 0.17766 | 0.745 |
| original_y2023_h00_o2023-08 | ok | residual | X4 | none | shift | 0.17766 | 0.745 |
| original_y2024_h00_o2024-01 | ok | direct | X5 | none | none | 0.18173 | 0.767 |
| original_y2024_h00_o2024-07 | ok | direct | X5 | none | none | 0.18173 | 0.767 |
| original_y2025_h00_o2025-04 | ok | direct | X6 | none | none | 0.13839 | 0.751 |
| original_y2025_h00_o2025-07 | ok | direct | X6 | none | none | 0.13839 | 0.751 |
| original_y2025_h00_o2025-09 | ok | direct | X6 | none | none | 0.13839 | 0.751 |
| original_y2025_h00_o2025-10 | ok | direct | X6 | none | none | 0.13839 | 0.751 |
| original_y2026_h00_o2026-04 | ok | residual | X1 | none | shift | 0.10306 | 0.819 |
| original_y2022_h03_o2021-10 | ok | direct | X1 | none | none | 0.07558 | 0.854 |
| original_y2022_h03_o2022-02 | ok | direct | X1 | none | none | 0.07558 | 0.854 |
| original_y2022_h03_o2022-04 | ok | direct | X1 | none | none | 0.07558 | 0.854 |
| original_y2022_h03_o2022-07 | ok | direct | X1 | none | none | 0.07558 | 0.854 |
| original_y2023_h03_o2022-10 | ok | residual | X5 | none | shift | 0.20208 | 0.774 |
| original_y2023_h03_o2022-12 | ok | residual | X5 | none | shift | 0.20208 | 0.774 |
| original_y2023_h03_o2023-05 | ok | residual | X5 | none | shift | 0.20208 | 0.774 |
| original_y2024_h03_o2023-10 | ok | direct | X1 | 48 | none | 0.18203 | 0.792 |
| original_y2024_h03_o2024-04 | ok | direct | X1 | 48 | none | 0.18203 | 0.792 |
| original_y2025_h03_o2025-01 | ok | direct | X4 | 48 | none | 0.14262 | 0.749 |
| original_y2025_h03_o2025-04 | ok | direct | X4 | 48 | none | 0.14262 | 0.749 |
| original_y2025_h03_o2025-07 | ok | direct | X4 | 48 | none | 0.14262 | 0.749 |
| original_y2022_h06_o2021-07 | ok | residual | X6 | 12 | none | 0.08004 | 0.861 |
| original_y2022_h06_o2021-11 | ok | residual | X6 | 12 | none | 0.08004 | 0.861 |
| original_y2022_h06_o2022-01 | ok | residual | X6 | 12 | none | 0.08004 | 0.861 |
| original_y2022_h06_o2022-04 | ok | residual | X6 | 12 | none | 0.08004 | 0.861 |
| original_y2023_h06_o2022-07 | ok | direct | X1 | none | shift | 0.24794 | 0.562 |
| original_y2023_h06_o2022-09 | ok | direct | X1 | none | shift | 0.24794 | 0.562 |
| original_y2023_h06_o2023-02 | ok | direct | X1 | none | shift | 0.26072 | 0.543 |
| original_y2024_h06_o2023-07 | ok | direct | X2 | 24 | isotonic | 0.24224 | 0.535 |
| original_y2024_h06_o2024-01 | ok | residual | X1 | 48 | none | 0.20322 | 0.699 |
| original_y2025_h06_o2024-10 | ok | direct | X4 | none | none | 0.18010 | 0.645 |
| original_y2025_h06_o2025-01 | ok | direct | X4 | none | none | 0.18010 | 0.645 |
| original_y2025_h06_o2025-04 | ok | direct | X4 | none | none | 0.18010 | 0.645 |
| original_y2022_h12_o2021-01 | ok | direct | X2 | 12 | none | 0.09549 | 0.716 |
| original_y2022_h12_o2021-05 | ok | direct | X2 | 12 | none | 0.09549 | 0.716 |
| original_y2022_h12_o2021-07 | ok | direct | X1 | 24 | none | 0.09251 | 0.789 |
| original_y2022_h12_o2021-10 | ok | direct | X1 | 24 | none | 0.09251 | 0.789 |
| original_y2023_h12_o2022-01 | ok | direct | X5 | none | none | 0.11920 | 0.797 |
| original_y2023_h12_o2022-03 | ok | direct | X5 | none | none | 0.11920 | 0.797 |
| original_y2023_h12_o2022-08 | ok | direct | X1 | none | isotonic | 0.31435 | 0.460 |
| original_y2024_h12_o2023-01 | ok | direct | X1 | none | isotonic | 0.29345 | 0.391 |
| original_y2024_h12_o2023-07 | ok | direct | X6 | 12 | shift | 0.26252 | 0.456 |
| original_y2025_h12_o2024-04 | ok | residual | X6 | 12 | none | 0.21301 | 0.452 |
| original_y2025_h12_o2024-07 | ok | direct | X6 | 12 | none | 0.18045 | 0.519 |
| original_y2025_h12_o2024-10 | ok | direct | X6 | 12 | none | 0.18045 | 0.519 |
| original_y2026_h12_o2025-04 | ok | direct | X6 | 24 | none | 0.15813 | 0.628 |

Selection minimizes final-q3 RMSE; crisis AUC and fixed-threshold (q3 ≥ 0.2) F1/recall can move in either direction and are reported, not optimized. Augmented pooled labels include repeated monthly validity truth from one assessment, not independent monthly observations. Undefined R²/AUC are shown as —. No bootstrap intervals or cross-setting contrasts are produced by design.
