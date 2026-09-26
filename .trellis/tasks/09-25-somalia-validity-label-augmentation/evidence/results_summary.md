# Somalia validity-period label augmentation (v3_validity) — results

Code `1f3bfcec7c81bbaa7841f301112f3bd74b75cae9`. Training-label augmentation: 3789 blank area-months inside verified current-period validity windows (round-level link, grill G3) received a full copy of the area's original label; copies keep the original's values, source family and availability, and never enter history. Outer 2025/2026 evaluation labels are unchanged, so original- and augmented-label D are scored on identical keys. Report isolation removes each scoring round's source family from fitting/calibration. Retrospective comparison on inspected years; H3/H6/H12 are ancillary fixed-recipe refits.

Copies by month: 2022-08 (339), 2022-09 (339), 2022-11 (348), 2022-12 (348), 2023-02 (348), 2023-03 (299), 2023-09 (348), 2024-02 (355), 2024-03 (355), 2024-08 (355), 2024-09 (355)

## Selected H0 recipes

| Branch | Fold | View | Formulation | Bundle | Calibration | Validation RMSE | AUC |
|---|---|---|---|---|---|---:|---:|
| original | 2025 | D_direct | direct | X1 | shift | 0.15475 | 0.726 |
| original | 2025 | D_residual | residual | X1 | isotonic | 0.15840 | 0.721 |
| original | 2025 | D_selected | direct | X1 | shift | 0.15475 | 0.726 |
| original | 2026 | D_direct | direct | X6 | shift | 0.11037 | 0.776 |
| original | 2026 | D_residual | residual | X4 | shift | 0.11540 | 0.755 |
| original | 2026 | D_selected | direct | X6 | shift | 0.11037 | 0.776 |
| augmented | 2025 | D_direct | direct | X1 | none | 0.15458 | 0.723 |
| augmented | 2025 | D_residual | residual | X3 | isotonic | 0.15722 | 0.716 |
| augmented | 2025 | D_selected | direct | X1 | none | 0.15458 | 0.723 |
| augmented | 2026 | D_direct | direct | X3 | isotonic | 0.12041 | 0.744 |
| augmented | 2026 | D_residual | residual | X2 | shift | 0.11585 | 0.724 |
| augmented | 2026 | D_selected | residual | X2 | shift | 0.11585 | 0.724 |

## Primary cohort (identical keys for both branches)

| Year | H | Branch | View | n | Final R² | Raw R² | RMSE (pp) | Bias (pp) | Final AUC | Within-month AUC | Bin F1 | Bin recall |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2025 | 0 | original | D_direct | 1876 | -0.167 | -0.200 | 14.02 | -4.15 | 0.683 | 0.745 | 0.582 | 0.514 |
| 2025 | 0 | original | D_residual | 1876 | -0.000 | -0.929 | 12.98 | 4.91 | 0.727 | 0.702 | 0.725 | 0.955 |
| 2025 | 0 | original | D_selected | 1876 | -0.167 | -0.200 | 14.02 | -4.15 | 0.683 | 0.745 | 0.582 | 0.514 |
| 2025 | 0 | augmented | D_direct | 1876 | -0.312 | -0.312 | 14.86 | 5.73 | 0.708 | 0.708 | 0.728 | 0.861 |
| 2025 | 0 | augmented | D_residual | 1876 | -0.011 | -0.798 | 13.04 | 5.10 | 0.704 | 0.703 | 0.721 | 0.995 |
| 2025 | 0 | augmented | D_selected | 1876 | -0.312 | -0.312 | 14.86 | 5.73 | 0.708 | 0.708 | 0.728 | 0.861 |
| 2025 | 0 | - | always_crisis | 1876 | — | — | — | — | — | — | 0.699 | 1.000 |
| 2026 | 0 | original | D_direct | 904 | 0.240 | 0.213 | 15.61 | -1.40 | 0.772 | 0.772 | 0.778 | 0.891 |
| 2026 | 0 | original | D_residual | 904 | -0.070 | 0.149 | 18.52 | -8.39 | 0.740 | 0.740 | 0.666 | 0.586 |
| 2026 | 0 | original | D_selected | 904 | 0.240 | 0.213 | 15.61 | -1.40 | 0.772 | 0.772 | 0.778 | 0.891 |
| 2026 | 0 | augmented | D_direct | 904 | -0.012 | 0.236 | 18.01 | -7.36 | 0.686 | 0.686 | 0.498 | 0.348 |
| 2026 | 0 | augmented | D_residual | 904 | -0.172 | 0.108 | 19.38 | -9.47 | 0.703 | 0.703 | 0.593 | 0.494 |
| 2026 | 0 | augmented | D_selected | 904 | -0.172 | 0.108 | 19.38 | -9.47 | 0.703 | 0.703 | 0.593 | 0.494 |
| 2026 | 0 | - | always_crisis | 904 | — | — | — | — | — | — | 0.749 | 1.000 |
| 2025 | 3 | original | D_direct | 275 | -0.339 | -0.938 | 15.11 | 6.21 | 0.669 | 0.735 | 0.710 | 0.900 |
| 2025 | 3 | original | D_residual | 275 | -0.030 | -0.877 | 13.25 | 4.97 | 0.669 | 0.707 | 0.696 | 0.893 |
| 2025 | 3 | original | D_selected | 275 | -0.339 | -0.938 | 15.11 | 6.21 | 0.669 | 0.735 | 0.710 | 0.900 |
| 2025 | 3 | augmented | D_direct | 275 | -0.286 | -0.286 | 14.81 | 5.99 | 0.676 | 0.710 | 0.709 | 0.886 |
| 2025 | 3 | augmented | D_residual | 275 | -0.089 | -0.867 | 13.63 | 4.91 | 0.676 | 0.700 | 0.707 | 1.000 |
| 2025 | 3 | augmented | D_selected | 275 | -0.286 | -0.286 | 14.81 | 5.99 | 0.676 | 0.710 | 0.709 | 0.886 |
| 2025 | 3 | - | always_crisis | 275 | — | — | — | — | — | — | 0.675 | 1.000 |
| 2026 | 3 | all | all | — | unavailable: empty primary cohort | | | | | | | |
| 2025 | 6 | original | D_direct | 275 | 0.036 | -0.303 | 12.83 | -3.53 | 0.715 | 0.741 | 0.602 | 0.536 |
| 2025 | 6 | original | D_residual | 275 | -0.011 | -0.973 | 13.14 | 2.73 | 0.625 | 0.682 | 0.687 | 0.957 |
| 2025 | 6 | original | D_selected | 275 | 0.036 | -0.303 | 12.83 | -3.53 | 0.715 | 0.741 | 0.602 | 0.536 |
| 2025 | 6 | augmented | D_direct | 275 | -0.143 | -0.143 | 13.97 | 5.59 | 0.742 | 0.755 | 0.735 | 0.900 |
| 2025 | 6 | augmented | D_residual | 275 | 0.040 | -0.577 | 12.80 | 3.17 | 0.659 | 0.683 | 0.692 | 0.986 |
| 2025 | 6 | augmented | D_selected | 275 | -0.143 | -0.143 | 13.97 | 5.59 | 0.742 | 0.755 | 0.735 | 0.900 |
| 2025 | 6 | - | always_crisis | 275 | — | — | — | — | — | — | 0.675 | 1.000 |
| 2026 | 6 | all | all | — | unavailable: empty primary cohort | | | | | | | |
| 2025 | 12 | original | D_direct | 1100 | -0.353 | -0.919 | 16.20 | 2.90 | 0.483 | 0.686 | 0.583 | 0.755 |
| 2025 | 12 | original | D_residual (raw diag.) | 1100 | -3.660 | -3.743 | 30.06 | 19.60 | 0.637 | 0.709 | 0.631 | 0.874 |
| 2025 | 12 | original | D_selected | 1100 | -0.353 | -0.919 | 16.20 | 2.90 | 0.483 | 0.686 | 0.583 | 0.755 |
| 2025 | 12 | augmented | D_direct | 1100 | -0.300 | -0.300 | 15.88 | 7.24 | 0.607 | 0.621 | 0.675 | 0.991 |
| 2025 | 12 | augmented | D_residual (raw diag.) | 1100 | -0.637 | -0.723 | 17.82 | -2.67 | 0.681 | 0.674 | 0.611 | 0.616 |
| 2025 | 12 | augmented | D_selected | 1100 | -0.300 | -0.300 | 15.88 | 7.24 | 0.607 | 0.621 | 0.675 | 0.991 |
| 2025 | 12 | - | always_crisis | 1100 | — | — | — | — | — | — | 0.658 | 1.000 |
| 2026 | 12 | original | D_direct | 132 | -0.162 | 0.002 | 19.40 | -7.80 | 0.607 | 0.607 | 0.529 | 0.444 |
| 2026 | 12 | original | D_residual (raw diag.) | 132 | 0.077 | 0.077 | 17.29 | 1.39 | 0.653 | 0.653 | 0.745 | 0.938 |
| 2026 | 12 | original | D_selected | 132 | -0.162 | 0.002 | 19.40 | -7.80 | 0.607 | 0.607 | 0.529 | 0.444 |
| 2026 | 12 | augmented | D_direct | 132 | -0.328 | 0.099 | 20.74 | -11.84 | 0.715 | 0.715 | 0.168 | 0.099 |
| 2026 | 12 | augmented | D_residual (raw diag.) | 132 | 0.127 | 0.127 | 16.81 | 0.59 | 0.683 | 0.683 | 0.752 | 0.938 |
| 2026 | 12 | augmented | D_selected (raw diag.) | 132 | 0.127 | 0.127 | 16.81 | 0.59 | 0.683 | 0.683 | 0.752 | 0.938 |
| 2026 | 12 | - | always_crisis | 132 | — | — | — | — | — | — | 0.761 | 1.000 |

## Share-history subset vs share persistence

| Year | H | Branch | View | n | Final R² | RMSE (pp) | Final AUC |
|---|---|---|---|---:|---:|---:|---:|
| 2025 | 0 | original | D_selected | 1849 | -0.159 | 13.96 | 0.693 |
| 2025 | 0 | augmented | D_selected | 1849 | -0.288 | 14.71 | 0.715 |
| 2025 | 0 | - | share_persistence | 1849 | -0.820 | 17.49 | 0.752 |
| 2026 | 0 | original | D_selected | 904 | 0.240 | 15.61 | 0.772 |
| 2026 | 0 | augmented | D_selected | 904 | -0.172 | 19.38 | 0.703 |
| 2026 | 0 | - | share_persistence | 904 | 0.220 | 15.82 | 0.790 |
| 2025 | 3 | original | D_selected | 256 | -0.222 | 14.38 | 0.697 |
| 2025 | 3 | augmented | D_selected | 256 | -0.143 | 13.90 | 0.705 |
| 2025 | 3 | - | share_persistence | 256 | -0.470 | 15.77 | 0.733 |
| 2025 | 6 | original | D_selected | 255 | 0.036 | 12.71 | 0.736 |
| 2025 | 6 | augmented | D_selected | 255 | -0.064 | 13.35 | 0.765 |
| 2025 | 6 | - | share_persistence | 255 | -0.342 | 15.00 | 0.754 |
| 2025 | 12 | original | D_selected | 1048 | -0.346 | 16.20 | 0.481 |
| 2025 | 12 | augmented | D_selected | 1048 | -0.309 | 15.98 | 0.600 |
| 2025 | 12 | - | share_persistence | 1048 | -1.272 | 21.04 | 0.717 |
| 2026 | 12 | original | D_selected | 132 | -0.162 | 19.40 | 0.607 |
| 2026 | 12 | augmented | D_selected | 132 | 0.127 | 16.81 | 0.683 |
| 2026 | 12 | - | share_persistence | 132 | -0.202 | 19.73 | 0.718 |

## Paired area-cluster bootstrap (2,000 draws, PCG64(42)); Δ = first minus second

| Year | H | Contrast | Metric | Δ | 95% interval |
|---|---|---|---|---:|---|
| 2025 | 0 | augmented_D_direct-original_D_direct | r2 | -0.1452 | [-0.2163, -0.0830] |
| 2025 | 0 | augmented_D_direct-original_D_direct | rmse | 0.0085 | [0.0049, 0.0125] |
| 2025 | 0 | augmented_D_direct-original_D_direct | auc | 0.0247 | [0.0155, 0.0340] |
| 2025 | 0 | augmented_D_residual-original_D_residual | r2 | -0.0102 | [-0.0368, 0.0152] |
| 2025 | 0 | augmented_D_residual-original_D_residual | rmse | 0.0007 | [-0.0010, 0.0023] |
| 2025 | 0 | augmented_D_residual-original_D_residual | auc | -0.0238 | [-0.0368, -0.0110] |
| 2025 | 0 | augmented_D_selected-original_D_selected | r2 | -0.1452 | [-0.2163, -0.0830] |
| 2025 | 0 | augmented_D_selected-original_D_selected | rmse | 0.0085 | [0.0049, 0.0125] |
| 2025 | 0 | augmented_D_selected-original_D_selected | auc | 0.0247 | [0.0155, 0.0340] |
| 2025 | 0 | original_D_selected-share_persistence | r2 | 0.6610 | [0.5340, 0.7904] |
| 2025 | 0 | original_D_selected-share_persistence | rmse | -0.0353 | [-0.0410, -0.0296] |
| 2025 | 0 | original_D_selected-share_persistence | auc | -0.0596 | [-0.0739, -0.0456] |
| 2025 | 0 | augmented_D_selected-share_persistence | r2 | 0.5321 | [0.4303, 0.6428] |
| 2025 | 0 | augmented_D_selected-share_persistence | rmse | -0.0278 | [-0.0324, -0.0235] |
| 2025 | 0 | augmented_D_selected-share_persistence | auc | -0.0376 | [-0.0530, -0.0215] |
| 2025 | 3 | augmented_D_direct-original_D_direct | r2 | 0.0527 | [-0.0275, 0.1334] |
| 2025 | 3 | augmented_D_direct-original_D_direct | rmse | -0.0030 | [-0.0074, 0.0015] |
| 2025 | 3 | augmented_D_direct-original_D_direct | auc | 0.0063 | [-0.0214, 0.0327] |
| 2025 | 3 | augmented_D_residual-original_D_residual | r2 | -0.0593 | [-0.1268, 0.0082] |
| 2025 | 3 | augmented_D_residual-original_D_residual | rmse | 0.0038 | [-0.0005, 0.0079] |
| 2025 | 3 | augmented_D_residual-original_D_residual | auc | 0.0075 | [-0.0279, 0.0433] |
| 2025 | 3 | augmented_D_selected-original_D_selected | r2 | 0.0527 | [-0.0275, 0.1334] |
| 2025 | 3 | augmented_D_selected-original_D_selected | rmse | -0.0030 | [-0.0074, 0.0015] |
| 2025 | 3 | augmented_D_selected-original_D_selected | auc | 0.0063 | [-0.0214, 0.0327] |
| 2025 | 3 | original_D_selected-share_persistence | r2 | 0.2477 | [0.0465, 0.4636] |
| 2025 | 3 | original_D_selected-share_persistence | rmse | -0.0139 | [-0.0246, -0.0028] |
| 2025 | 3 | original_D_selected-share_persistence | auc | -0.0365 | [-0.0764, 0.0034] |
| 2025 | 3 | augmented_D_selected-share_persistence | r2 | 0.3272 | [0.1144, 0.5484] |
| 2025 | 3 | augmented_D_selected-share_persistence | rmse | -0.0186 | [-0.0290, -0.0066] |
| 2025 | 3 | augmented_D_selected-share_persistence | auc | -0.0283 | [-0.0762, 0.0166] |
| 2025 | 6 | augmented_D_direct-original_D_direct | r2 | -0.1790 | [-0.3897, 0.0158] |
| 2025 | 6 | augmented_D_direct-original_D_direct | rmse | 0.0114 | [-0.0011, 0.0234] |
| 2025 | 6 | augmented_D_direct-original_D_direct | auc | 0.0261 | [-0.0098, 0.0643] |
| 2025 | 6 | augmented_D_residual-original_D_residual | r2 | 0.0510 | [-0.0055, 0.1127] |
| 2025 | 6 | augmented_D_residual-original_D_residual | rmse | -0.0034 | [-0.0074, 0.0004] |
| 2025 | 6 | augmented_D_residual-original_D_residual | auc | 0.0341 | [-0.0145, 0.0795] |
| 2025 | 6 | augmented_D_selected-original_D_selected | r2 | -0.1790 | [-0.3897, 0.0158] |
| 2025 | 6 | augmented_D_selected-original_D_selected | rmse | 0.0114 | [-0.0011, 0.0234] |
| 2025 | 6 | augmented_D_selected-original_D_selected | auc | 0.0261 | [-0.0098, 0.0643] |
| 2025 | 6 | original_D_selected-share_persistence | r2 | 0.3782 | [0.1365, 0.6464] |
| 2025 | 6 | original_D_selected-share_persistence | rmse | -0.0229 | [-0.0367, -0.0085] |
| 2025 | 6 | original_D_selected-share_persistence | auc | -0.0186 | [-0.0747, 0.0384] |
| 2025 | 6 | augmented_D_selected-share_persistence | r2 | 0.2784 | [0.0747, 0.5007] |
| 2025 | 6 | augmented_D_selected-share_persistence | rmse | -0.0165 | [-0.0281, -0.0046] |
| 2025 | 6 | augmented_D_selected-share_persistence | auc | 0.0111 | [-0.0366, 0.0568] |
| 2025 | 12 | augmented_D_direct-original_D_direct | r2 | 0.0525 | [-0.0197, 0.1198] |
| 2025 | 12 | augmented_D_direct-original_D_direct | rmse | -0.0032 | [-0.0073, 0.0011] |
| 2025 | 12 | augmented_D_direct-original_D_direct | auc | 0.1242 | [0.0949, 0.1536] |
| 2025 | 12 | augmented_D_residual-original_D_residual | r2 | 3.0233 | [2.5713, 3.4983] |
| 2025 | 12 | augmented_D_residual-original_D_residual | rmse | -0.1225 | [-0.1355, -0.1089] |
| 2025 | 12 | augmented_D_residual-original_D_residual | auc | 0.0443 | [0.0122, 0.0759] |
| 2025 | 12 | augmented_D_selected-original_D_selected | r2 | 0.0525 | [-0.0197, 0.1198] |
| 2025 | 12 | augmented_D_selected-original_D_selected | rmse | -0.0032 | [-0.0073, 0.0011] |
| 2025 | 12 | augmented_D_selected-original_D_selected | auc | 0.1242 | [0.0949, 0.1536] |
| 2025 | 12 | original_D_selected-share_persistence | r2 | 0.9256 | [0.6902, 1.1887] |
| 2025 | 12 | original_D_selected-share_persistence | rmse | -0.0484 | [-0.0595, -0.0376] |
| 2025 | 12 | original_D_selected-share_persistence | auc | -0.2369 | [-0.2769, -0.1959] |
| 2025 | 12 | augmented_D_selected-share_persistence | r2 | 0.9622 | [0.7403, 1.2074] |
| 2025 | 12 | augmented_D_selected-share_persistence | rmse | -0.0507 | [-0.0610, -0.0405] |
| 2025 | 12 | augmented_D_selected-share_persistence | auc | -0.1177 | [-0.1535, -0.0807] |
| 2026 | 0 | augmented_D_direct-original_D_direct | r2 | -0.2521 | [-0.3102, -0.1972] |
| 2026 | 0 | augmented_D_direct-original_D_direct | rmse | 0.0240 | [0.0185, 0.0296] |
| 2026 | 0 | augmented_D_direct-original_D_direct | auc | -0.0862 | [-0.1125, -0.0604] |
| 2026 | 0 | augmented_D_residual-original_D_residual | r2 | -0.1017 | [-0.1261, -0.0793] |
| 2026 | 0 | augmented_D_residual-original_D_residual | rmse | 0.0086 | [0.0068, 0.0106] |
| 2026 | 0 | augmented_D_residual-original_D_residual | auc | -0.0372 | [-0.0543, -0.0212] |
| 2026 | 0 | augmented_D_selected-original_D_selected | r2 | -0.4119 | [-0.4837, -0.3446] |
| 2026 | 0 | augmented_D_selected-original_D_selected | rmse | 0.0377 | [0.0315, 0.0439] |
| 2026 | 0 | augmented_D_selected-original_D_selected | auc | -0.0691 | [-0.0957, -0.0437] |
| 2026 | 0 | original_D_selected-share_persistence | r2 | 0.0203 | [-0.0253, 0.0711] |
| 2026 | 0 | original_D_selected-share_persistence | rmse | -0.0021 | [-0.0072, 0.0027] |
| 2026 | 0 | original_D_selected-share_persistence | auc | -0.0180 | [-0.0391, 0.0046] |
| 2026 | 0 | augmented_D_selected-share_persistence | r2 | -0.3916 | [-0.4629, -0.3213] |
| 2026 | 0 | augmented_D_selected-share_persistence | rmse | 0.0357 | [0.0290, 0.0423] |
| 2026 | 0 | augmented_D_selected-share_persistence | auc | -0.0871 | [-0.1166, -0.0561] |
| 2026 | 12 | augmented_D_direct-original_D_direct | r2 | -0.1658 | [-0.2813, -0.0596] |
| 2026 | 12 | augmented_D_direct-original_D_direct | rmse | 0.0134 | [0.0048, 0.0224] |
| 2026 | 12 | augmented_D_direct-original_D_direct | auc | 0.1078 | [0.0148, 0.2023] |
| 2026 | 12 | augmented_D_residual-original_D_residual | r2 | 0.0500 | [-0.0166, 0.1199] |
| 2026 | 12 | augmented_D_residual-original_D_residual | rmse | -0.0048 | [-0.0107, 0.0016] |
| 2026 | 12 | augmented_D_residual-original_D_residual | auc | 0.0303 | [-0.0233, 0.0844] |
| 2026 | 12 | augmented_D_selected-original_D_selected | r2 | 0.2897 | [0.1264, 0.4706] |
| 2026 | 12 | augmented_D_selected-original_D_selected | rmse | -0.0259 | [-0.0403, -0.0113] |
| 2026 | 12 | augmented_D_selected-original_D_selected | auc | 0.0761 | [-0.0084, 0.1621] |
| 2026 | 12 | original_D_selected-share_persistence | r2 | 0.0396 | [-0.1496, 0.2459] |
| 2026 | 12 | original_D_selected-share_persistence | rmse | -0.0033 | [-0.0188, 0.0132] |
| 2026 | 12 | original_D_selected-share_persistence | auc | -0.1115 | [-0.2076, -0.0133] |
| 2026 | 12 | augmented_D_selected-share_persistence | r2 | 0.3293 | [0.1143, 0.5612] |
| 2026 | 12 | augmented_D_selected-share_persistence | rmse | -0.0292 | [-0.0464, -0.0109] |
| 2026 | 12 | augmented_D_selected-share_persistence | auc | -0.0353 | [-0.1091, 0.0331] |

## Label source and support disclosures

Labels come from the raw panel. Raw vs target-corrected fs labels on shared Somalia keys (differing / shared): 2017: 146/146, 2018: 144/146, 2019: 125/146, 2020: 127/148, 2021: 89/89, 2022: 407/729, 2023: 185/1018, 2024: 6/710, 2025: 0/1876, 2026: 0/904 (`ledgers/label_diff_raw_vs_fs.csv.gz`). The original branch therefore differs from v2 in labels as well as in report isolation.
Fold-2026 H0 selection/calibration rounds include 2025-07 (64 cross-border spillover rows, excluded from augmentation) and 2025-09 (4 rows); they satisfy the distinct-round rule but carry little Somalia-specific support.
At H12 early rounds have no history before T−12, so residual OOF fits are unsupported there and H12 residual/selected cells may be raw-clipped diagnostics (`calibrated_unavailable`); contrasts involving such cells are flagged `diagnostic_only` in `metrics/contrasts.csv`.

Copied labels are validity-period copies of one assessment, not independent monthly observations; area resampling does not model shared report dependence. Labels come from the raw panel (v1/v2 used the target-corrected fs ledger), so v2 numbers are context, not an unchanged comparator. Climate-variable lineage was waived (2026-09-24).
