# Somalia oracle-information experiment — results summary

Git HEAD at run: `a0c792e65ed6cb7a81684092b8b4f52a8428b95e`; runtime xgboost 3.2.0, numpy 2.4.4, pandas 3.0.3.
Interpretation: conditional empirical ceiling of this model family under ideal publication and oracle realized weather; not causal, not an operational forecast skill claim. Horizons are separate conditions and are not ranked.

Independent replay: 480/480 checks passed.

## Coverage (frozen before fitting)

| Test year | H | primary | wider-only (oracle weather unverified) | excluded | primary target months |
|---|---|---:|---:|---:|---|
| 2025 | 0 | 1876 | 0 | 0 | 2025-04 (904), 2025-07 (64), 2025-09 (4), 2025-10 (904) |
| 2025 | 3 | 275 | 1601 | 0 | 2025-04 (132), 2025-07 (11), 2025-10 (132) |
| 2025 | 6 | 275 | 1601 | 0 | 2025-04 (132), 2025-07 (11), 2025-10 (132) |
| 2025 | 12 | 1100 | 776 | 0 | 2025-04 (904), 2025-07 (64), 2025-10 (132) |
| 2026 | 0 | 904 | 0 | 1 | 2026-04 (904) |
| 2026 | 3 | 0 | 904 | 1 | none |
| 2026 | 6 | 0 | 904 | 1 | none |
| 2026 | 12 | 132 | 772 | 1 | 2026-04 (132) |

## Primary-cohort metrics (Phase 3+ F2 is the selection metric)

| Year | H | Spec | n | F2 | Precision | Recall | Accuracy | R² q3 |
|---|---|---|---:|---:|---:|---:|---:|---:|
| 2025 | 0 | A | 1876 | 0.855 | 0.544 | 0.997 | 0.497 | -0.383 |
| 2025 | 0 | B | 1876 | 0.843 | 0.540 | 0.981 | 0.489 | -0.197 |
| 2025 | 0 | C | 1876 | 0.843 | 0.540 | 0.981 | 0.489 | -0.197 |
| 2025 | 0 | D | 1876 | 0.848 | 0.603 | 0.944 | 0.575 | -0.325 |
| 2025 | 0 | always_crisis | 1876 | 0.853 | 0.537 | 1.000 | — | — |
| 2025 | 3 | A | 275 | 0.813 | 0.500 | 0.964 | 0.462 | -0.862 |
| 2025 | 3 | B | 275 | 0.803 | 0.496 | 0.950 | 0.458 | -0.833 |
| 2025 | 3 | C | 275 | 0.803 | 0.496 | 0.950 | 0.455 | -1.178 |
| 2025 | 3 | D | 275 | 0.754 | 0.555 | 0.829 | 0.531 | -0.302 |
| 2025 | 3 | always_crisis | 275 | 0.838 | 0.509 | 1.000 | — | — |
| 2025 | 6 | A | 275 | 0.827 | 0.527 | 0.964 | 0.491 | -0.020 |
| 2025 | 6 | B | 275 | 0.846 | 0.524 | 1.000 | 0.491 | -0.190 |
| 2025 | 6 | C | 275 | 0.841 | 0.531 | 0.986 | 0.502 | -0.239 |
| 2025 | 6 | D | 275 | 0.847 | 0.550 | 0.979 | 0.535 | -0.265 |
| 2025 | 6 | always_crisis | 275 | 0.838 | 0.509 | 1.000 | — | — |
| 2025 | 12 | A | 1100 | 0.761 | 0.485 | 0.887 | 0.419 | -0.205 |
| 2025 | 12 | B | 1100 | 0.773 | 0.485 | 0.907 | 0.416 | -0.136 |
| 2025 | 12 | C | 1100 | 0.808 | 0.493 | 0.961 | 0.430 | -0.223 |
| 2025 | 12 | D | 1100 | 0.774 | 0.511 | 0.889 | 0.472 | -0.143 |
| 2025 | 12 | always_crisis | 1100 | 0.828 | 0.490 | 1.000 | — | — |
| 2026 | 0 | A | 904 | 0.882 | 0.598 | 1.000 | 0.387 | -0.085 |
| 2026 | 0 | B | 904 | 0.882 | 0.598 | 1.000 | 0.388 | -0.117 |
| 2026 | 0 | C | 904 | 0.882 | 0.598 | 1.000 | 0.388 | -0.117 |
| 2026 | 0 | D | 904 | 0.866 | 0.637 | 0.952 | 0.438 | 0.100 |
| 2026 | 0 | always_crisis | 904 | 0.882 | 0.598 | 1.000 | — | — |
| 2026 | 3 | all | 0 | unavailable: empty cohort | | | | |
| 2026 | 6 | all | 0 | unavailable: empty cohort | | | | |
| 2026 | 12 | A | 132 | 0.800 | 0.645 | 0.852 | 0.447 | -0.062 |
| 2026 | 12 | B | 132 | 0.888 | 0.614 | 1.000 | 0.424 | -0.050 |
| 2026 | 12 | C | 132 | 0.856 | 0.611 | 0.951 | 0.409 | 0.048 |
| 2026 | 12 | D | 132 | 0.829 | 0.655 | 0.889 | 0.455 | 0.051 |
| 2026 | 12 | always_crisis | 132 | 0.888 | 0.614 | 1.000 | — | — |

## Paired area-cluster bootstrap Δ F2 (95% percentile, 2,000 draws, PCG64(42))

| Year | H | Cohort | Contrast | Δ F2 | 95% interval | status |
|---|---|---|---|---:|---|---|
| 2025 | 0 | primary | B-A | -0.011 | [-0.017, -0.006] | ok |
| 2025 | 0 | primary | C-B | 0.000 | [0.000, 0.000] | ok |
| 2025 | 0 | primary | D-C | 0.005 | [-0.009, 0.019] | ok |
| 2025 | 0 | primary | A-always_crisis | 0.002 | [-0.001, 0.004] | ok |
| 2025 | 0 | primary | B-always_crisis | -0.010 | [-0.016, -0.004] | ok |
| 2025 | 0 | primary | C-always_crisis | -0.010 | [-0.016, -0.004] | ok |
| 2025 | 0 | primary | D-always_crisis | -0.004 | [-0.016, 0.007] | ok |
| 2025 | 0 | persistence_subset | A-persistence | 0.120 | [0.096, 0.144] | ok |
| 2025 | 0 | persistence_subset | B-persistence | 0.108 | [0.083, 0.133] | ok |
| 2025 | 0 | persistence_subset | C-persistence | 0.108 | [0.083, 0.133] | ok |
| 2025 | 0 | persistence_subset | D-persistence | 0.114 | [0.092, 0.135] | ok |
| 2025 | 0 | persistence_subset | A-always_crisis | 0.002 | [-0.001, 0.004] | ok |
| 2025 | 0 | persistence_subset | B-always_crisis | -0.010 | [-0.016, -0.004] | ok |
| 2025 | 0 | persistence_subset | C-always_crisis | -0.010 | [-0.016, -0.004] | ok |
| 2025 | 0 | persistence_subset | D-always_crisis | -0.004 | [-0.016, 0.007] | ok |
| 2025 | 3 | primary | B-A | -0.010 | [-0.031, 0.010] | ok |
| 2025 | 3 | primary | C-B | 0.000 | [-0.015, 0.015] | ok |
| 2025 | 3 | primary | D-C | -0.049 | [-0.097, -0.007] | ok |
| 2025 | 3 | primary | A-always_crisis | -0.025 | [-0.049, -0.005] | ok |
| 2025 | 3 | primary | B-always_crisis | -0.035 | [-0.063, -0.011] | ok |
| 2025 | 3 | primary | C-always_crisis | -0.035 | [-0.062, -0.010] | ok |
| 2025 | 3 | primary | D-always_crisis | -0.084 | [-0.137, -0.033] | ok |
| 2025 | 3 | persistence_subset | A-persistence | 0.166 | [0.099, 0.238] | ok |
| 2025 | 3 | persistence_subset | B-persistence | 0.156 | [0.090, 0.230] | ok |
| 2025 | 3 | persistence_subset | C-persistence | 0.156 | [0.091, 0.228] | ok |
| 2025 | 3 | persistence_subset | D-persistence | 0.107 | [0.055, 0.163] | ok |
| 2025 | 3 | persistence_subset | A-always_crisis | -0.025 | [-0.050, -0.005] | ok |
| 2025 | 3 | persistence_subset | B-always_crisis | -0.036 | [-0.063, -0.011] | ok |
| 2025 | 3 | persistence_subset | C-always_crisis | -0.036 | [-0.062, -0.011] | ok |
| 2025 | 3 | persistence_subset | D-always_crisis | -0.085 | [-0.138, -0.033] | ok |
| 2025 | 6 | primary | B-A | 0.019 | [-0.001, 0.044] | ok |
| 2025 | 6 | primary | C-B | -0.005 | [-0.022, 0.008] | ok |
| 2025 | 6 | primary | D-C | 0.005 | [-0.018, 0.028] | ok |
| 2025 | 6 | primary | A-always_crisis | -0.011 | [-0.037, 0.010] | ok |
| 2025 | 6 | primary | B-always_crisis | 0.008 | [0.003, 0.014] | ok |
| 2025 | 6 | primary | C-always_crisis | 0.003 | [-0.014, 0.018] | ok |
| 2025 | 6 | primary | D-always_crisis | 0.008 | [-0.010, 0.024] | ok |
| 2025 | 6 | persistence_subset | A-persistence | 0.183 | [0.110, 0.262] | ok |
| 2025 | 6 | persistence_subset | B-persistence | 0.202 | [0.131, 0.280] | ok |
| 2025 | 6 | persistence_subset | C-persistence | 0.197 | [0.128, 0.276] | ok |
| 2025 | 6 | persistence_subset | D-persistence | 0.203 | [0.134, 0.277] | ok |
| 2025 | 6 | persistence_subset | A-always_crisis | -0.011 | [-0.038, 0.010] | ok |
| 2025 | 6 | persistence_subset | B-always_crisis | 0.008 | [0.003, 0.015] | ok |
| 2025 | 6 | persistence_subset | C-always_crisis | 0.003 | [-0.014, 0.018] | ok |
| 2025 | 6 | persistence_subset | D-always_crisis | 0.009 | [-0.011, 0.025] | ok |
| 2025 | 12 | primary | B-A | 0.012 | [-0.013, 0.035] | ok |
| 2025 | 12 | primary | C-B | 0.035 | [0.015, 0.055] | ok |
| 2025 | 12 | primary | D-C | -0.034 | [-0.054, -0.014] | ok |
| 2025 | 12 | primary | A-always_crisis | -0.067 | [-0.087, -0.048] | ok |
| 2025 | 12 | primary | B-always_crisis | -0.055 | [-0.073, -0.038] | ok |
| 2025 | 12 | primary | C-always_crisis | -0.020 | [-0.032, -0.008] | ok |
| 2025 | 12 | primary | D-always_crisis | -0.054 | [-0.074, -0.034] | ok |
| 2025 | 12 | persistence_subset | A-persistence | 0.052 | [0.011, 0.091] | ok |
| 2025 | 12 | persistence_subset | B-persistence | 0.065 | [0.025, 0.103] | ok |
| 2025 | 12 | persistence_subset | C-persistence | 0.100 | [0.062, 0.136] | ok |
| 2025 | 12 | persistence_subset | D-persistence | 0.066 | [0.030, 0.103] | ok |
| 2025 | 12 | persistence_subset | A-always_crisis | -0.068 | [-0.089, -0.048] | ok |
| 2025 | 12 | persistence_subset | B-always_crisis | -0.056 | [-0.074, -0.038] | ok |
| 2025 | 12 | persistence_subset | C-always_crisis | -0.021 | [-0.033, -0.009] | ok |
| 2025 | 12 | persistence_subset | D-always_crisis | -0.054 | [-0.075, -0.034] | ok |
| 2026 | 0 | primary | B-A | 0.000 | [0.000, 0.000] | ok |
| 2026 | 0 | primary | C-B | 0.000 | [0.000, 0.000] | ok |
| 2026 | 0 | primary | D-C | -0.016 | [-0.031, -0.002] | ok |
| 2026 | 0 | primary | A-always_crisis | 0.000 | [0.000, 0.000] | ok |
| 2026 | 0 | primary | B-always_crisis | 0.000 | [0.000, 0.000] | ok |
| 2026 | 0 | primary | C-always_crisis | 0.000 | [0.000, 0.000] | ok |
| 2026 | 0 | primary | D-always_crisis | -0.016 | [-0.031, -0.002] | ok |
| 2026 | 0 | persistence_subset | A-persistence | 0.053 | [0.025, 0.082] | ok |
| 2026 | 0 | persistence_subset | B-persistence | 0.053 | [0.025, 0.082] | ok |
| 2026 | 0 | persistence_subset | C-persistence | 0.053 | [0.025, 0.082] | ok |
| 2026 | 0 | persistence_subset | D-persistence | 0.038 | [0.014, 0.064] | ok |
| 2026 | 0 | persistence_subset | A-always_crisis | 0.000 | [0.000, 0.000] | ok |
| 2026 | 0 | persistence_subset | B-always_crisis | 0.000 | [0.000, 0.000] | ok |
| 2026 | 0 | persistence_subset | C-always_crisis | 0.000 | [0.000, 0.000] | ok |
| 2026 | 0 | persistence_subset | D-always_crisis | -0.016 | [-0.031, -0.002] | ok |
| 2026 | 12 | primary | B-A | 0.088 | [0.030, 0.154] | ok |
| 2026 | 12 | primary | C-B | -0.033 | [-0.072, -0.003] | ok |
| 2026 | 12 | primary | D-C | -0.026 | [-0.081, 0.029] | ok |
| 2026 | 12 | primary | A-always_crisis | -0.088 | [-0.154, -0.030] | ok |
| 2026 | 12 | primary | B-always_crisis | 0.000 | [0.000, 0.000] | ok |
| 2026 | 12 | primary | C-always_crisis | -0.033 | [-0.072, -0.003] | ok |
| 2026 | 12 | primary | D-always_crisis | -0.059 | [-0.118, -0.007] | ok |
| 2026 | 12 | persistence_subset | A-persistence | 0.190 | [0.072, 0.316] | ok |
| 2026 | 12 | persistence_subset | B-persistence | 0.278 | [0.176, 0.386] | ok |
| 2026 | 12 | persistence_subset | C-persistence | 0.245 | [0.131, 0.354] | ok |
| 2026 | 12 | persistence_subset | D-persistence | 0.219 | [0.122, 0.320] | ok |
| 2026 | 12 | persistence_subset | A-always_crisis | -0.088 | [-0.154, -0.030] | ok |
| 2026 | 12 | persistence_subset | B-always_crisis | 0.000 | [0.000, 0.000] | ok |
| 2026 | 12 | persistence_subset | C-always_crisis | -0.033 | [-0.072, -0.003] | ok |
| 2026 | 12 | persistence_subset | D-always_crisis | -0.059 | [-0.118, -0.007] | ok |

## Persistence-supported subset

| Year | H | Spec | n | F2 | Accuracy |
|---|---|---|---:|---:|---:|
| 2025 | 0 | A | 1864 | 0.856 | 0.499 |
| 2025 | 0 | B | 1864 | 0.844 | 0.490 |
| 2025 | 0 | C | 1864 | 0.844 | 0.490 |
| 2025 | 0 | D | 1864 | 0.850 | 0.578 |
| 2025 | 0 | persistence | 1864 | 0.736 | 0.601 |
| 2025 | 0 | always_crisis | 1864 | 0.854 | — |
| 2025 | 3 | A | 270 | 0.816 | 0.467 |
| 2025 | 3 | B | 270 | 0.806 | 0.463 |
| 2025 | 3 | C | 270 | 0.806 | 0.459 |
| 2025 | 3 | D | 270 | 0.757 | 0.537 |
| 2025 | 3 | persistence | 270 | 0.650 | 0.559 |
| 2025 | 3 | always_crisis | 270 | 0.841 | — |
| 2025 | 6 | A | 269 | 0.829 | 0.498 |
| 2025 | 6 | B | 269 | 0.849 | 0.498 |
| 2025 | 6 | C | 269 | 0.844 | 0.509 |
| 2025 | 6 | D | 269 | 0.849 | 0.546 |
| 2025 | 6 | persistence | 269 | 0.646 | 0.591 |
| 2025 | 6 | always_crisis | 269 | 0.840 | — |
| 2025 | 12 | A | 1077 | 0.762 | 0.422 |
| 2025 | 12 | B | 1077 | 0.775 | 0.421 |
| 2025 | 12 | C | 1077 | 0.810 | 0.434 |
| 2025 | 12 | D | 1077 | 0.776 | 0.477 |
| 2025 | 12 | persistence | 1077 | 0.710 | 0.545 |
| 2025 | 12 | always_crisis | 1077 | 0.830 | — |
| 2026 | 0 | A | 904 | 0.882 | 0.387 |
| 2026 | 0 | B | 904 | 0.882 | 0.388 |
| 2026 | 0 | C | 904 | 0.882 | 0.388 |
| 2026 | 0 | D | 904 | 0.866 | 0.438 |
| 2026 | 0 | persistence | 904 | 0.828 | 0.606 |
| 2026 | 0 | always_crisis | 904 | 0.882 | — |
| 2026 | 12 | A | 132 | 0.800 | 0.447 |
| 2026 | 12 | B | 132 | 0.888 | 0.424 |
| 2026 | 12 | C | 132 | 0.856 | 0.409 |
| 2026 | 12 | D | 132 | 0.829 | 0.455 |
| 2026 | 12 | persistence | 132 | 0.610 | 0.530 |
| 2026 | 12 | always_crisis | 132 | 0.888 | — |

## Caveats

- Realized monthly weather in the canonical raw panel is frozen for 772 Somalia areas from 2025-02 and for all areas in 2026-04; those months are treated as unverified oracle evidence, which restricts H=3/6/12 primary cohorts (fold 2026 H=3/6 has no verified oracle rows).
- `overall_phase_lag1` and `estimated_population` were blocked from all arms after lineage review; arm A still contains exact-month categorical phase history (`overall_phase_prev_observed_asof_sH`).
- Fold 2026 covers only April 2026 targets. Two test years cannot establish stable superiority; intervals exclude refitting/selection uncertainty and do not correct all spatial dependence.
