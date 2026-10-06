# Design: climate2015_v1 feature swap for the global deep-feature model

## Boundary

```
climate_monthly_2015_2026 (6227 areas × 2015-01..2026-08, full grid)
climate_2015_2026 (6227 areas × 2015..2026 × s1/s2 seasons)
current fs0/fs1/fs2/fs3 model-ready CSVs (assembled_IPCCH/model_ready/)
        │
        ▼  scripts/preprocessing/build_climate2015_model_ready.py
        │    uses src/ipcch/climate2015_features.py (forked upstream recipe)
        ▼
model_ready/climate2015_v1/{scope_0m,scope_3m,scope_6m}_model_ready.csv, forecasting_ready.csv
  + feature_manifest.csv + build_summary.json
        │
        ▼  unchanged scripts/modeling/run_deep_feature_weight_decay_forecasting.py --dataset … --fs fsX
results/experiments/deep_feature_weight_decay_forecasting/climate2015_v1/{baseline_rerun,climate2015}/{0m,3m,6m,12m}/
        │
        ▼  scripts/reporting/compare_climate2015_global_metrics.py
results/.../climate2015_v1/comparison_metrics.csv ; reports/.../climate2015_v1/comparison.md
```

Training, metrics, split and weighting code is not edited. The new feature columns are picked up automatically, because `select_numeric_feature_columns` selects all numeric non-target columns.

## Old-column removal

A column is dropped from a scope file when its name contains any of `Rainf_f_tavg_mean`, `Tair_f_tavg_mean`, `SoilMoi00_10cm_tavg_mean` or `EVI_mean`. This covers the base families, stress spells, neighbour means and all interactions that use them (for example `nino34 × Rainf deficit` and `Rainf deficit × EVI vegetation`).

`GPP_mean*` columns are kept. Expected removals are 142 in fs0–fs2 and 97 in fs3; the builder asserts these counts from the header inventory taken on 2026-10-05.

## New monthly features

Source variables are `V ∈` the 14 `{x}_month_ensmean` columns: prcp_anom, prcp_z, rainy_days, cdd, tmean_anom, tmax_anom, hot_days_p95, gdd, edd, sm_z, spi03, spei03, ndvi_anom, evi_anom.

The panel is the full monthly grid sorted by (area_id, date). The builder asserts that the grid is complete, so a row shift equals a month shift.

`shift(k)` means the value at month `t−k`. Windows "ending at a" cover months `t−a−w+1 … t−a`. Rolling minimum periods are the upstream ones: {3: 2, 6: 3, 12: 6, 24: 12}.

### asof12 block (all four scopes; names identical to upstream with `V` substituted)

| Family | Columns |
|---|---|
| anchor | `V__l12`, `V__l15`, `V__l18`, `V__l24` |
| rolling | `V__roll{3,6,12}_mean_asof12` |
| seasonal gap | `V__l12_minus_l24`, `V__l12_ratio_l24` (zero denominator becomes NaN) |
| trend | `V__slope{6,12,24}_asof12 = (V[t−12] − V[t−12−w+1])/(w−1)`; `V__accel6_vs_prev6_asof12` |
| dispersion | `V__roll12_{std,min,max,iqr}_asof12` (upstream only for stress-source variables; here all 14, per the "full mirror on all 14" decision) |
| same-month history | `V__hist_same_month_{anom,pctnormal,z,pctile}_l12`: prior expanding stats by (area, calendar month), evaluated at `t−12` |

### Scope block (fs0/fs1/fs2 only, anchor `s ∈ {0,3,6}`, suffix `_s{s}`)

Upstream builds these by shifting the asof12 columns. Here they are computed directly at anchor `s`, which is equivalent and avoids NaN at the end of the grid.

- `V__l{s}_s{s}`
- `V__roll{3,6,12}_mean_asof{s}_s{s}`
- `V__slope{6,12}_asof{s}_s{s}`
- `V__roll12_{std,iqr}_asof{s}_s{s}`

### Stress signals

Each signal is 1 when the condition holds, 0 when it does not, and NaN when the source is NaN.

| Signal | Rule |
|---|---|
| `spi03_month_ensmean__deficit_stress` | spi03 ≤ −1 |
| `tmean_anom_month_ensmean__hot_stress` | tmean_anom ≥ 1.0 |
| `evi_anom_month_ensmean__vegetation_stress` | evi_anom ≤ −0.015 |

For each signal and each block (asof12, and asof{s}_s{s} in fs0–fs2) there are four features:
- `__share12`: rolling 12-month mean of the signal, min_periods 6;
- `__any12`: rolling 12-month max of the signal;
- `__months_since`: months since the most recent stress month, upstream loop;
- `__longest_run12`: longest consecutive stress run in the 12-month window, min_periods 6.

### Neighbours and interactions

- **Neighbour mean.** `neighbor3_mean__spi03_month_ensmean__deficit_stress__share12_asof12`, plus the `_asof{s}_s{s}` version in fs0–fs2. It is the mean over the 3 nearest areas by haversine distance between area centroids.
- **Neighbour coordinates.** Use `lat`/`lon` from `ipcch_admin_geometry` (admin_code, lat, lon). This is checked against the upstream neighbour feature in the fidelity test. If it does not reproduce, use the interim panel coordinates as upstream does.
- **asof12 interactions:**
  - deficit_share × vegetation_share;
  - `nino34_anom__enso_stress__share12_asof12` × deficit_share (nino column taken from the scope file);
  - deficit_share × popdensity;
  - deficit_share × market_access.
- **Scope interactions (fs0–fs2):**
  - `prcp_z_month_ensmean__l{s}_s{s}__x__market_access_s{s}`;
  - `tmean_anom_month_ensmean__l{s}_s{s}__x__popdensity_s{s}`.

  These mirror the upstream Rainf/Tair → market_access/popdensity pairing.

## New seasonal features

The anchor is `a = s` for fs0–fs2 and `a = 12` for fs3. The origin month is `o = t−a`. A season counts as completed at `o` when `gs_end_date_exclusive ≤ first day of month(o)+1`.

Partial 2026 seasons have their end date after 2026-09-01, so they are never selected for any origin up to 2026-08.

For the latest and second-latest completed seasons (ordered by end date, ties broken by start date), the features are:

- `gs_last{k}__{x}_gs_ensmean_asof{a}[_s{a}]` for the 14 seasonal variables;
- `gs_last{k}__months_since_end_asof{a}[_s{a}]`, the number of months from the season's end month to `o`.

That gives 30 columns per scope. They are computed per (area, origin month) with `merge_asof` on end dates.

## Expected shape

| Scope | Columns |
|---|---|
| fs0–fs2 | 521/522 − 142 + ~468 ≈ 847–848 |
| fs3 | 387 − 97 + ~341 ≈ 631 |

Rows and row keys are unchanged.

## Fidelity check (fork correctness)

1. Recompute these Rainf, Tair and EVI families from the interim raw panel (`interim/IPCCH_2026_target_corrected_nino34_wbfood.csv`) using the same functions, with the upstream ratio-based stress rules plugged in:
   - lags, rolling means, slopes, accel, dispersion, hist-same-month;
   - stress spells;
   - scope block at s=0;
   - the neighbour mean.
2. Compare with the values in the current fs0 for a seeded sample of areas.
3. Tolerance is 1e-6 relative. If a family does not match, investigate it and record it in `evidence.md`. This check concerns fidelity, not bit-identity.

## Scope-block masking (decision after the fidelity gate)

`masked` datasets (primary) set every scope-anchored new feature to NaN where the scope file's `Rainf_f_tavg_mean__l{s}_s{s}` is NaN. Scope-anchored features are the monthly scope block, the scope stress families, the scope neighbour mean, the scope interactions and the seasonal block. This mirrors the upstream shift artifact row by row. The `unmasked` datasets (fs0–fs2) keep the directly computed values.

## Runs

The same CLI flags are used for both sets, with `--fs fsX --dataset <path>`. Without `--dataset` the CLI reads the current files, which is the baseline. `fs3` corresponds to 12m.

Runs go sequentially (15 GB RAM). Output directories are under `results/experiments/deep_feature_weight_decay_forecasting/climate2015_v1/` and `reports/deep_feature_weight_decay_forecasting/climate2015_v1/`.

## Tradeoffs and known limitations

- **Redundant families.** Same-month z and ratio features on variables that are already anomalies are redundant. They are kept because the decision was a full mirror; XGBoost tolerates redundancy, at the cost of more columns.
- **Missing early history.** New climate history starts in 2015, so training rows from 2014–2016 have mostly NaN new features while the baseline had FLDAS history. This is part of "what the new release does", not a confound we remove.
- **Climatology baseline.** The anomaly/z climatology baseline of the source release is unknown. If it includes test years, there is a mild standardization look-ahead. This is reported, not fixed.
- **Single seed, no intervals.** Small deltas should not be read as improvements.

## Rollback

All changes are additive: new branch, new module and scripts, new external directory and new result directories. Rollback means deleting the branch and those directories. Canonical outputs are not touched.
