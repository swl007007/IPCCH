# compact_cds_launch_v1: April 2026-origin compact launch with CDS forecast weather

Prediction summaries only (no actual-label scoring, bootstrap or SHAP). Origin O = 2026-04; targets 2026-04 (H0, one shared fit), 2026-10 (H6) and 2027-04 (H12). Fixed April 2026 population with the legacy country cap (raw > 110% of the 2025 reference -> 95%).
Verification passed: `True`; see `results/launch/nowcasting_2026_04_compact_cds_v1/verification.json`.

## Global predicted population (capped denominators; repaired disjoint shares)

| arm | H | target | population | P3+ share | P3+ people | P4+ share | P4+ people |
|---|---:|---|---:|---:|---:|---:|---:|
| compact_baseline | 0 | 2026-04 | 1,429,568,874 | 0.2324 | 332,230,839 | 0.0412 | 58,935,539 |
| compact_baseline | 6 | 2026-10 | 1,429,568,874 | 0.2150 | 307,396,483 | 0.0433 | 61,832,481 |
| compact_baseline | 12 | 2027-04 | 1,429,568,874 | 0.2598 | 371,419,610 | 0.0793 | 113,364,613 |
| compact_cds_weather | 0 | 2026-04 | 1,429,568,874 | 0.2324 | 332,230,839 | 0.0412 | 58,935,539 |
| compact_cds_weather | 6 | 2026-10 | 1,429,568,874 | 0.2170 | 310,187,607 | 0.0449 | 64,146,517 |
| compact_cds_weather | 12 | 2027-04 | 1,429,568,874 | 0.2454 | 350,881,765 | 0.0643 | 91,943,823 |

## CDS weather minus baseline (global)

| H | target | delta P3+ share | delta P3+ people | delta P4+ share |
|---:|---|---:|---:|---:|
| 0 | 2026-04 | +0.00000 | +0 | +0.00000 |
| 6 | 2026-10 | +0.00195 | +2,791,124 | +0.00162 |
| 12 | 2027-04 | -0.01437 | -20,537,845 | -0.01498 |

## Definitions and limits

- Raw cumulative predictions and the canonical class (highest phase with unrounded score >= 0.2) are kept unchanged; population tables use reporting-only repaired shares (cumulative differences, clip to [0,1], normalize). Categorical maps use the raw class; continuous and difference maps use repaired P3+ shares.
- Weather arm: trained on realized compact oracle anomalies (observed, declared 1991-2020 reference); inferred on ECMWF system51 April 2026 forecast anomalies (1993-2016 model reference): official May-September, October constructed and validated on September. Fixed containing-cell point sampling. These lineages differ by design.
- October temperature uses 6-hourly instantaneous samples valid in (Oct 1 00, Nov 1 00] UTC. This window was empirically verified against the supplied system51 September absolute monthly ensemble mean and September anomaly products (the initial [start, end) window failed both); official primary documents do not explicitly state endpoint inclusivity.
- Original accumulated precipitation shows small endpoint decreases (worst about 0.17 mm) beyond the final GRIB packing bounds in some members/cells; ECMWF documents spurious decrements in packed cumulative fields, but the upstream cause of the excess is unverified. Raw signed end-minus-start totals were used unchanged (no clipping or member removal); the September precipitation overlap passed its frozen bound.
- 2027 targets have every existing year indicator 0 (unseen year); no population growth projection; static snapshots and population completion are not vintage-certified; inference IPC history uses reports through 2026-03 only.
- H0 is one shared baseline fit; its weather-minus-baseline difference is 0 by construction.
