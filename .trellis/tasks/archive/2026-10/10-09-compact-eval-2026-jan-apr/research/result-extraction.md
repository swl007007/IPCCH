# Read-only extraction of generated historical comparisons

An independent default scout read only the stable numerical report CSVs. It checked 48 selected delta cells: both scopes, 2026 and expanded pooled periods, H3/H6/H12, and phase3plus accuracy/R2/share MAE/ordinal MAE. Saved paired absolute values match the absolute tables, and delta equals oracle minus baseline within 1e-12 (maximum discrepancy global 7.212e-18, SOM 8.6e-18). This extraction is supplementary numerical evidence, not a Trellis audit or final model acceptance.

Source roots: `results/experiments/compact_climate_weather_oracle_eval_2026_jan_apr_v1/report/` and `results/experiments/compact_climate_weather_oracle_eval_2026_jan_apr_v1_somalia_local/report/`.

## 2026 direction and absolute phase3plus accuracy

| scope | horizon | baseline accuracy | oracle accuracy | oracle minus baseline |
|---|---:|---:|---:|---:|
| global | 3 | 0.752253293 | 0.739311301 | -0.012941992 |
| global | 6 | 0.728218165 | 0.755951005 | 0.027732840 |
| global | 12 | 0.660041599 | 0.666974809 | 0.006933210 |
| SOM local | 3 | 0.633149171 | 0.624309392 | -0.008839779 |
| SOM local | 6 | 0.693922652 | 0.707182320 | 0.013259669 |
| SOM local | 12 | 0.628729282 | 0.635359116 | 0.006629834 |

Displayed values are rounded; comparison CSVs retain full precision. Global source `all_metrics_long.csv` baseline/oracle physical rows: 595/2275, 1155/2835, 1715/3395; delta rows `global_deltas.csv`: 35/91/147. SOM source `som_metrics_long.csv`: 91/259, 147/315, 203/371; delta rows `som_oracle_minus_baseline_deltas.csv`: 94/150/206.

For both scopes, 2026 H3 accuracy and ordinal MAE worsen while R2 and share MAE improve. At H6, accuracy and ordinal MAE improve, but share MAE worsens; SOM R2 also worsens. At H12 all four selected 2026 metrics improve. Expanded pooled directions differ, especially for SOM: its H12 selected pooled metrics all worsen despite the partial-2026 improvements. These are point estimates, not significance claims or evidence of CDS skill.

2026 support is 4327 rows/3823 areas globally and 905 rows/904 areas locally. SOM month support is 1/0/0/904; 904 of 905 rows come from April. Expanded pooled supports are 32532/6024 (global rows/areas) and 5838/905 (SOM). Monthly source: each `coverage_by_month.csv`, physical rows 2-5.
