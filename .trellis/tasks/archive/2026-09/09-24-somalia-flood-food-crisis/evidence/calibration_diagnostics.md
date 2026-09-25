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

## Findings

- Discrimination, not calibration, is the bottleneck for A/B/C (crisis AUC mostly ≈0.5). D is the only specification with consistently useful within-month ranking.
- Isotonic calibration on inner validation removes most of the upward bias in q3 predictions at H=0/3/6, lifting D's R² to 0.21 (2026 H=0) and 0.10 (2025 H=0). At H=12 the validation bias does not transfer across years and calibration hurts R².
- Per-phase thresholds mainly trade F2 for macro-F1; Phase 4 recall stays <0.1 without an F2-style low threshold. Even the leaky test-tuned ceiling keeps accuracy ≤0.63.
- Phase 3+ F2 is a poor selection criterion here: with crisis prevalence 0.45–0.60 and many shares near 0.2, F2-optimal models collapse to predicting Phase 3 almost everywhere and cannot beat always-crisis.

## Recommendations

- Present calibrated D at H=0 and H=3 as the main result for the next group meeting.
- Do not select future models on F2. Use calibrated share R², crisis AUC / within-month AUC and macro-F1 as primary criteria; report F2 only alongside them.
- Judge new signals (e.g. flooding) by within-month AUC and calibrated R² gains over calibrated D.
