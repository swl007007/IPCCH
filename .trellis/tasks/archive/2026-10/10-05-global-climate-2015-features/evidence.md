# Evidence: climate2015_v1

## Fidelity gate (2026-10-05)

`scripts/preprocessing/check_climate2015_fork_fidelity.py`: 400 seeded areas, 3,454 fs0 rows. FLDAS Rainf, Tair and EVI families were recomputed from `interim/IPCCH_2026_target_corrected_nino34_wbfood.csv` with the forked helpers and the upstream ratio stress rules. Report: `evidence/fidelity_report.csv`.

**asof12 block: 78 of 80 columns match** (rtol 1e-6). This covers lags, rolling means, gap/ratio, slopes, accel, dispersion, same-month history, all four stress-spell features, and the interactions with EVI vegetation, nino34 and market_access.

Two columns differ, and both differences are explained:
- `neighbor3_mean__Rainf…share12_asof12`: 28 of 3,454 rows differ. The likely cause is ties between areas with identical centroids, where the order of tied neighbours is arbitrary.
- `Rainf…share12_asof12__x__popdensity`: 168 rows differ only in NaN pattern; where both have values they agree (≤ 6e-14). The deep build used `popdensity` with more missing values than the column now in the fs files. The fork uses the current fs column.

**Scope s0 block: 39 columns.** Every value present in both versions agrees (max abs diff ≤ 1.4e-12), with two exceptions that share the asof12 causes above: `neighbor3_mean__Rainf…share12_asof0_s0` differs in value on 15 sampled rows (max 0.111; neighbour ties), and `Tair…l0_s0__x__popdensity_s0` differs only in NaN pattern (popdensity, as above). The saved file is NaN on 747 sampled rows where the fork computes values. Cause: upstream `shifted_from_asof12` shifts by −(12−H) rows on a grid ending 2026-04, so targets after 2025-04 (0m), 2025-07 (3m) and 2025-10 (6m) get NaN scope features. This affects every ordinary dynamic predictor, not only climate.

Share of baseline rows with an empty Rainf scope lag, by test year 2025: 0m 59.7%, 3m 46.1%, 6m 1.6%. For 2026 the share is 100%.

The user decided the masking described in prd/design.

## trellis-check review (2026-10-05)

Findings, classified as asked in the user's global instructions:

1. **Changes results (tiny, not leakage): season tie-break.**
   - **What went wrong.** `last_completed_seasons` sorted the `merge_asof` right side with an unstable sort. Where two seasons share `gs_end_date_exclusive`, the "latest" season could be the earlier-starting one.
   - **Scope.** Areas 1499, 1515 and 1516; 7 of about 52.5k rows per scope, across all 30 seasonal columns.
   - **Fix.** Sort by `(end, pos)` with mergesort.
   - **Regression test.** `test_tied_season_end_dates_keep_start_order` uses 300 areas with shuffled input. It **fails on the old code and passes on the fix** (both checked).
   - **Rebuild timing.** Datasets were rebuilt (`/tmp/c2015/build2.log`) before any climate2015 training started, so no climate run used the defective build. The baseline arm does not use these datasets.
2. **Evidence only.** The scope-s0 fidelity sentence was corrected by the checker. The s0 neighbour mean has 15 value mismatches from the same neighbour ties; the s0 Tair × popdensity interaction differs only in NaN pattern.
3. **Evidence only: neighbour coordinates.** The builder uses interim-panel coordinates, which is the upstream source and the design's fallback; `ipcch_admin_geometry` was not tried. Candidate neighbours are the 6,227 climate-grid areas, all of which have valid coordinates.
4. **Hygiene, no effect on 2022–2025:**
   - Rows with target months after the grid end (2026-09 onward) get NaN monthly features.
   - Partial 2026 seasons could only be selected for 2026 origins, which are not tested.
   - The manifest labels asof12 lags as `t-12` (an upper bound) instead of `t-15/18/24`.
   - The comparison script's `int(n)` assumes the baseline arm is present.
   - Not changed.

## Baseline rerun (2026-10-05)

`run_climate2015_global_suite.py --arms baseline_rerun`; all 4 runs returned rc=0.

| Scope | Runtime |
|---|---:|
| 0m | 1,479 s |
| 3m | 512 s |
| 6m | 638 s |
| 12m | 266 s |

The background shell later reported exit −1 because the session restarted; the run ledger and `metrics_overall.csv` confirm all four runs finished.

**Reproducibility against the 2026-05-31 outputs.**
- **0m and 12m:** zero difference on every metric and year. Rows, feature count and feature-column hash are identical.
- **3m and 6m:** differences up to 0.037 (mean |Δ| over all cells 0.006). The May 3m/6m outputs date from 2026-05-26 and used 539 features. The fs1/fs2 files were rebuilt on 2026-05-30 and now have 540 features (different hash, same rows).
- **Conclusion:** the drift comes from that input update, not from code changes. The comparison therefore uses the rerun baseline.

The datasets were rebuilt with the tie-break fix at 20:41–20:51 (`/tmp/c2015/build2.log`, exit 0). The climate arms started after the rebuild, launched detached with setsid/nohup.

## Climate arms and results (2026-10-05)

All 7 climate runs returned rc=0 (`/tmp/c2015/suite_climate.log`).

| Arm | 0m | 3m | 6m | 12m |
|---|---:|---:|---:|---:|
| masked | 524 s | 533 s | 731 s | 560 s |
| unmasked | 774 s | 758 s | 716 s | — |

Outputs:
- Comparison table: `results/experiments/deep_feature_weight_decay_forecasting/climate2015_v1/comparison_metrics.csv`
- Report: `reports/deep_feature_weight_decay_forecasting/climate2015_v1/comparison.md`

Mean Δ (masked − rerun baseline) over 2022–2025:

| Scope | Accuracy | Precision 3+ | Sensitivity 3+ | R² 3+ | F2 3+ |
|---|---:|---:|---:|---:|---:|
| 0m | −0.000 | −0.012 | +0.052 | −0.012 | +0.036 |
| 3m | +0.000 | −0.008 | +0.027 | +0.009 | +0.019 |
| 6m | +0.002 | −0.001 | +0.008 | +0.008 | +0.007 |
| 12m | +0.010 | +0.002 | +0.029 | +0.004 | +0.024 |

47 of 80 scope × year × metric cells improve. The gains concentrate in 2022.

**0m 2025 R² drop** (0.351 → 0.183 masked; 0.241 unmasked). Diagnosed from saved predictions:
- On rows with blank scope features (6,818), R² falls 0.336 → 0.119. On the other rows it falls 0.371 → 0.284.
- Yemen contributes 17.7 of the 53.1 extra squared error; its bias moves from −0.148 to −0.188.
- SOM, COD, MOZ, ZMB and KEN move toward over-prediction, with bias up 0.03–0.08.

**Classification:** this is a result finding, not a code defect, so no repair was made. The mechanism (which features drive the shift) was not traced further; SHAP is out of scope.
