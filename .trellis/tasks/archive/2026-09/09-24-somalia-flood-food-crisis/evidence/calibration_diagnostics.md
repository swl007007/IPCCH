# Calibration and threshold diagnostics (no refitting)

Calibration maps and thresholds are learned per (job, arm) on that job's saved inner-validation predictions of its selected candidate (labels <= outer origin) and applied to outer test predictions. `LEAKY_*` rows tune on the evaluation cohort and only bound what post-processing could reach.

## Headline: isotonic-calibrated D (full phase-percentage history)

H=0 and H=3 are the horizons of primary interest to Somalia government users. 2026 covers April 2026 only; 2026 H=3 has no verified oracle-weather rows.

| Year | H | n | R² q3 raw → calibrated | Accuracy raw → calibrated | Macro-F1 raw → calibrated | Crisis AUC | Within-month AUC |
|---|---|---:|---|---|---|---:|---:|
| 2025 | 0 | 1876 | -0.325 → **0.101** | 0.575 → 0.579 | 0.282 → 0.260 | 0.650 | 0.742 |
| 2025 | 3 | 275 | -0.302 → **0.074** | 0.556 → 0.549 | 0.273 → 0.256 | 0.613 | 0.749 |
| 2025 | 6 | 275 | -0.238 → **0.060** | 0.531 → 0.542 | 0.235 → 0.242 | 0.668 | 0.742 |
| 2025 | 12 | 1100 | -0.143 → **-0.151** | 0.472 → 0.465 | 0.219 → 0.249 | 0.522 | 0.612 |
| 2026 | 0 | 904 | 0.100 → **0.214** | 0.438 → 0.480 | 0.292 → 0.356 | 0.774 | 0.774 |
| 2026 | 12 | 132 | 0.051 → **-0.178** | 0.455 → 0.432 | 0.307 → 0.317 | 0.631 | 0.631 |

## Specification comparison on discrimination and calibrated R²

| Year | H | Crisis AUC A / B / C / D | Within-month AUC A / B / C / D | Calibrated R² A / B / C / D |
|---|---|---|---|---|
| 2025 | 0 | 0.545 / 0.502 / 0.502 / 0.650 | 0.641 / 0.437 / 0.437 / 0.742 | 0.014 / -0.027 / -0.027 / 0.101 |
| 2025 | 3 | 0.335 / 0.553 / 0.628 / 0.613 | 0.374 / 0.619 / 0.676 / 0.749 | -0.088 / -0.073 / -0.082 / 0.074 |
| 2025 | 6 | 0.729 / 0.738 / 0.728 / 0.668 | 0.717 / 0.730 / 0.727 / 0.742 | 0.094 / 0.081 / 0.036 / 0.060 |
| 2025 | 12 | 0.465 / 0.491 / 0.481 / 0.522 | 0.548 / 0.546 / 0.642 / 0.612 | -0.144 / -0.199 / -0.141 / -0.151 |
| 2026 | 0 | 0.551 / 0.504 / 0.504 / 0.774 | 0.551 / 0.504 / 0.504 / 0.774 | -0.054 / -0.045 / -0.045 / 0.214 |
| 2026 | 12 | 0.581 / 0.497 / 0.573 / 0.631 | 0.581 / 0.497 / 0.573 / 0.631 | -0.298 / -0.204 / -0.204 / -0.178 |

## Calibrated D versus simple benchmarks

Identical keys within each year/horizon. Persistence = latest valid reported phase with U <= O and U < T; its R² uses the carried-forward q3 share of the latest valid history observation (`hist_q3_obs1`), and the D R² in brackets is recomputed on exactly those rows. Always-crisis predicts Phase 3+ everywhere (binary only). Δ F2 intervals: paired area-cluster bootstrap, 2,000 draws, PCG64(42).

| Year | H | Cohort | n | Benchmark | F2 | Precision | Recall | Accuracy | Macro-F1 | R² q3 |
|---|---|---|---:|---|---:|---:|---:|---:|---:|---|
| 2025 | 0 | persistence_subset | 1864 | D_calibrated | 0.854 | 0.593 | 0.959 | 0.582 | 0.262 | 0.106 |
| 2025 | 0 | persistence_subset | 1864 | D_raw | 0.850 | 0.607 | 0.944 | 0.578 | 0.284 | -0.304 |
| 2025 | 0 | persistence_subset | 1864 | persistence | 0.736 | 0.746 | 0.734 | 0.601 | 0.312 | -0.624 (n=1862; D calibrated 0.106) |
| 2025 | 0 | persistence_subset | 1864 | always_crisis | 0.854 | 0.540 | 1.000 | — | — | — |
| 2025 | 0 | primary | 1876 | D_calibrated | 0.852 | 0.589 | 0.959 | 0.579 | 0.260 | 0.101 |
| 2025 | 0 | primary | 1876 | D_raw | 0.848 | 0.603 | 0.944 | 0.575 | 0.282 | -0.325 |
| 2025 | 0 | primary | 1876 | always_crisis | 0.853 | 0.537 | 1.000 | — | — | — |
| 2025 | 3 | persistence_subset | 270 | D_calibrated | 0.826 | 0.563 | 0.935 | 0.556 | 0.260 | 0.096 |
| 2025 | 3 | persistence_subset | 270 | D_raw | 0.757 | 0.564 | 0.827 | 0.563 | 0.277 | -0.247 |
| 2025 | 3 | persistence_subset | 270 | persistence | 0.650 | 0.690 | 0.640 | 0.559 | 0.308 | -0.464 (n=268; D calibrated 0.095) |
| 2025 | 3 | persistence_subset | 270 | always_crisis | 0.841 | 0.515 | 1.000 | — | — | — |
| 2025 | 3 | primary | 275 | D_calibrated | 0.823 | 0.555 | 0.936 | 0.549 | 0.256 | 0.074 |
| 2025 | 3 | primary | 275 | D_raw | 0.754 | 0.555 | 0.829 | 0.556 | 0.273 | -0.302 |
| 2025 | 3 | primary | 275 | always_crisis | 0.838 | 0.509 | 1.000 | — | — | — |
| 2025 | 6 | persistence_subset | 269 | D_calibrated | 0.849 | 0.556 | 0.978 | 0.550 | 0.246 | 0.064 |
| 2025 | 6 | persistence_subset | 269 | D_raw | 0.848 | 0.553 | 0.978 | 0.543 | 0.240 | -0.185 |
| 2025 | 6 | persistence_subset | 269 | persistence | 0.646 | 0.719 | 0.630 | 0.591 | 0.317 | -0.379 (n=267; D calibrated 0.065) |
| 2025 | 6 | persistence_subset | 269 | always_crisis | 0.840 | 0.513 | 1.000 | — | — | — |
| 2025 | 6 | primary | 275 | D_calibrated | 0.847 | 0.550 | 0.979 | 0.542 | 0.242 | 0.060 |
| 2025 | 6 | primary | 275 | D_raw | 0.846 | 0.548 | 0.979 | 0.531 | 0.235 | -0.238 |
| 2025 | 6 | primary | 275 | always_crisis | 0.838 | 0.509 | 1.000 | — | — | — |
| 2025 | 12 | persistence_subset | 1077 | D_calibrated | 0.716 | 0.498 | 0.805 | 0.472 | 0.253 | -0.145 |
| 2025 | 12 | persistence_subset | 1077 | D_raw | 0.776 | 0.517 | 0.887 | 0.477 | 0.222 | -0.127 |
| 2025 | 12 | persistence_subset | 1077 | persistence | 0.710 | 0.665 | 0.722 | 0.545 | 0.335 | -0.967 (n=1073; D calibrated -0.144) |
| 2025 | 12 | persistence_subset | 1077 | always_crisis | 0.830 | 0.495 | 1.000 | — | — | — |
| 2025 | 12 | primary | 1100 | D_calibrated | 0.712 | 0.490 | 0.803 | 0.465 | 0.249 | -0.151 |
| 2025 | 12 | primary | 1100 | D_raw | 0.774 | 0.511 | 0.889 | 0.472 | 0.219 | -0.143 |
| 2025 | 12 | primary | 1100 | always_crisis | 0.828 | 0.490 | 1.000 | — | — | — |
| 2026 | 0 | persistence_subset | 904 | D_calibrated | 0.820 | 0.691 | 0.860 | 0.480 | 0.356 | 0.214 |
| 2026 | 0 | persistence_subset | 904 | D_raw | 0.866 | 0.637 | 0.952 | 0.438 | 0.292 | 0.100 |
| 2026 | 0 | persistence_subset | 904 | persistence | 0.828 | 0.830 | 0.828 | 0.606 | 0.492 | 0.220 (n=904; D calibrated 0.214) |
| 2026 | 0 | persistence_subset | 904 | always_crisis | 0.882 | 0.598 | 1.000 | — | — | — |
| 2026 | 0 | primary | 904 | D_calibrated | 0.820 | 0.691 | 0.860 | 0.480 | 0.356 | 0.214 |
| 2026 | 0 | primary | 904 | D_raw | 0.866 | 0.637 | 0.952 | 0.438 | 0.292 | 0.100 |
| 2026 | 0 | primary | 904 | always_crisis | 0.882 | 0.598 | 1.000 | — | — | — |
| 2026 | 12 | persistence_subset | 132 | D_calibrated | 0.667 | 0.667 | 0.667 | 0.432 | 0.317 | -0.178 |
| 2026 | 12 | persistence_subset | 132 | D_raw | 0.829 | 0.655 | 0.889 | 0.455 | 0.307 | 0.051 |
| 2026 | 12 | persistence_subset | 132 | persistence | 0.610 | 0.868 | 0.568 | 0.530 | 0.302 | -0.202 (n=132; D calibrated -0.178) |
| 2026 | 12 | persistence_subset | 132 | always_crisis | 0.888 | 0.614 | 1.000 | — | — | — |
| 2026 | 12 | primary | 132 | D_calibrated | 0.667 | 0.667 | 0.667 | 0.432 | 0.317 | -0.178 |
| 2026 | 12 | primary | 132 | D_raw | 0.829 | 0.655 | 0.889 | 0.455 | 0.307 | 0.051 |
| 2026 | 12 | primary | 132 | always_crisis | 0.888 | 0.614 | 1.000 | — | — | — |

| Year | H | Cohort | Contrast | Δ F2 | 95% interval |
|---|---|---|---|---:|---|
| 2025 | 0 | primary | D_calibrated-always_crisis | -0.001 | [-0.011, 0.010] |
| 2025 | 0 | primary | D_calibrated-D_raw | 0.004 | [-0.002, 0.010] |
| 2025 | 0 | persistence_subset | D_calibrated-persistence | 0.118 | [0.096, 0.140] |
| 2025 | 0 | persistence_subset | D_calibrated-always_crisis | -0.000 | [-0.011, 0.010] |
| 2025 | 0 | persistence_subset | D_calibrated-D_raw | 0.004 | [-0.002, 0.010] |
| 2026 | 0 | primary | D_calibrated-always_crisis | -0.062 | [-0.087, -0.038] |
| 2026 | 0 | primary | D_calibrated-D_raw | -0.047 | [-0.068, -0.028] |
| 2026 | 0 | persistence_subset | D_calibrated-persistence | -0.009 | [-0.027, 0.009] |
| 2026 | 0 | persistence_subset | D_calibrated-always_crisis | -0.062 | [-0.087, -0.038] |
| 2026 | 0 | persistence_subset | D_calibrated-D_raw | -0.047 | [-0.068, -0.028] |
| 2025 | 3 | primary | D_calibrated-always_crisis | -0.015 | [-0.052, 0.015] |
| 2025 | 3 | primary | D_calibrated-D_raw | 0.069 | [0.030, 0.113] |
| 2025 | 3 | persistence_subset | D_calibrated-persistence | 0.176 | [0.115, 0.243] |
| 2025 | 3 | persistence_subset | D_calibrated-always_crisis | -0.015 | [-0.052, 0.015] |
| 2025 | 3 | persistence_subset | D_calibrated-D_raw | 0.069 | [0.030, 0.115] |
| 2025 | 6 | primary | D_calibrated-always_crisis | 0.008 | [-0.010, 0.024] |
| 2025 | 6 | primary | D_calibrated-D_raw | 0.001 | [0.000, 0.003] |
| 2025 | 6 | persistence_subset | D_calibrated-persistence | 0.203 | [0.134, 0.277] |
| 2025 | 6 | persistence_subset | D_calibrated-always_crisis | 0.009 | [-0.011, 0.025] |
| 2025 | 6 | persistence_subset | D_calibrated-D_raw | 0.001 | [0.000, 0.003] |
| 2025 | 12 | primary | D_calibrated-always_crisis | -0.115 | [-0.141, -0.089] |
| 2025 | 12 | primary | D_calibrated-D_raw | -0.062 | [-0.085, -0.036] |
| 2025 | 12 | persistence_subset | D_calibrated-persistence | 0.006 | [-0.031, 0.043] |
| 2025 | 12 | persistence_subset | D_calibrated-always_crisis | -0.114 | [-0.140, -0.088] |
| 2025 | 12 | persistence_subset | D_calibrated-D_raw | -0.060 | [-0.085, -0.034] |
| 2026 | 12 | primary | D_calibrated-always_crisis | -0.221 | [-0.315, -0.132] |
| 2026 | 12 | primary | D_calibrated-D_raw | -0.163 | [-0.243, -0.089] |
| 2026 | 12 | persistence_subset | D_calibrated-persistence | 0.057 | [-0.065, 0.178] |
| 2026 | 12 | persistence_subset | D_calibrated-always_crisis | -0.221 | [-0.315, -0.132] |
| 2026 | 12 | persistence_subset | D_calibrated-D_raw | -0.163 | [-0.243, -0.089] |

## Findings

- Discrimination, not calibration, is the bottleneck for A/B/C (crisis AUC mostly ≈0.5). D is the only specification with consistently useful within-month ranking.
- Isotonic calibration on inner validation removes most of the upward bias in q3 predictions at H=0/3/6, lifting D's R² to 0.21 (2026 H=0) and 0.10 (2025 H=0). At H=12 the validation bias does not transfer across years and calibration hurts R².
- Per-phase thresholds mainly trade F2 for macro-F1; Phase 4 recall stays <0.1 without an F2-style low threshold. Even the leaky test-tuned ceiling keeps accuracy ≤0.63.
- Phase 3+ F2 is a poor selection criterion here: with crisis prevalence 0.45–0.60 and many shares near 0.2, F2-optimal models collapse to predicting Phase 3 almost everywhere and cannot beat always-crisis.
- Against simple benchmarks: calibrated D beats persistence on F2 at H=0/3/6 in 2025 (Δ +0.12 to +0.20, intervals exclude zero) and on share R² everywhere except 2026 H=0, where carried-forward q3 is as good (0.220 vs 0.214). Persistence has higher accuracy and macro-F1 than calibrated D at H=0 in both years (2026: 0.606 vs 0.480; 0.492 vs 0.356) because it predicts Phase 2 and 4 when those were last observed.
- Calibrated D never significantly beats always-crisis on F2 (2025 H=0 Δ −0.001 [−0.011, 0.010]); at 2026 H=0 and at H=12 it is significantly worse on F2.
- The R² of 0.21 at 2026 H=0 is therefore not a gain over the naive share-persistence benchmark; the 2025 H=0/H=3 R² gains over persistence (0.106 vs −0.624; 0.095 vs −0.464) are.

## Recommendations

- Present calibrated D at H=0 and H=3 for the next group meeting together with persistence and always-crisis on the same keys; frame 2025 H=0/H=3 as the evidence of added value and 2026 H=0 as matching persistence.
- Do not select future models on F2. Use calibrated share R², crisis AUC / within-month AUC and macro-F1 as primary criteria, always reported relative to persistence and always-crisis on identical keys.
- Judge new signals (e.g. flooding) by within-month AUC and calibrated R² gains over calibrated D and over share persistence, and by whether they close the accuracy/macro-F1 gap to persistence.
