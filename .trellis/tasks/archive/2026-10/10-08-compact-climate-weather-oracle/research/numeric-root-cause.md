# Numeric root cause of the first compact input build's verification failure (2026-10-08)

Executor: Claude Opus 5.5 (1M), Herdr pane w11:p4. Status: diagnosed and fixed in code; inputs rebuilt (build 2). No model was fitted
from build 1.

## Finding

`verify_compact_climate_weather_oracle.py --stage inputs` on build 1 replayed 372,800 sampled real cells (400 rows per horizon,
every dynamic feature) with an independent pure-Python path and found 20 mismatches: 15 `cdd_month_ensmean` same-month z / z-MA
cells and 3 SD12 cells (WFP_Price area 4588 2024-11, sum_fatalities_violence area 4151 2025-06, GPP_mean area 101055 2024-09).
Everything else (pinned hashes, schemas, oracle replay, baseline parity, legacy inventory) passed.

## Root causes (reproduced on the full real series: `numeric_root_cause_real_series.py`, output alongside)

1. **pandas running rolling sums (`climate2015_features.rolling`)**. pandas updates a window by adding the entering and
   subtracting the leaving value. After varying values, a window of twelve identical values keeps a residue:
   SD12 = 5.5642656212723185e-06 (WFP 268.27392 x 12), 9.739e-07 (fatalities 0.0), 2.035e-04 (GPP 2762.0 x 12) where the exact
   sample SD is 0. The same mechanism leaves cancellation error in rolling means after a very large value (z ~ 1e15) leaves a
   z-MA window, which produced the z-MA mismatches of areas 101270/101274/101109/101172/101190/101022/101169. Not reproducible
   on short toy arrays (pandas' compensated sums), only with the long running state of a real column.
2. **Uncentred float mean in same-month z (`climate2015_features.same_month_history`)**. With near-constant histories the
   mean rounds to the nearest float before deviations are taken, destroying the significant digits of the numerator/SD.
   Area 101270 cdd, November 2023: prior = seven 30.0 and one 29.99999999999999, current 29.99999999999999. Exact rational
   z = -7/8 * sqrt(8) = -2.4748737341529163; old helper -2.6457513110645907; `statistics.fmean`-based reference
   -2.8284271247461903 (fmean rounds the mean to 30.0, ulp 3.6e-15, before the subtraction). Area 101214 cdd, January 2023:
   old -9.494e14 vs exact -1.0149666539382206e15. So the first independent reference was also inexact on these cells.

## Remedy (approved D13/ddof-1 formulas unchanged; no epsilon, clipping, winsorization or tolerance change)

- `compact_features.trailing`: each window is reduced from its own values (sliding window, no running sums). Mean and SD are
  shift-centred two-pass: values are taken relative to the window minimum (exact for nearby floats, Sterbenz), then mean and
  ddof-1 SD. A constant window gives its value as mean and exactly 0 SD. Used for every compact MA/SD12, z-MA and stress
  share12/any12 (max).
- `compact_features.same_month_z`: mean, SD and numerator relative to the first observed value of that calendar month
  (from a year no later than any prior year used), two-pass, ddof 1. Exactly constant prior history (min == max over
  >= 2 non-missing values) stays NA; any genuinely non-constant history stays finite, however small its spread.
- Legacy helpers (`climate2015_features.rolling`, `same_month_history`, stress rules) are unchanged; legacy versions keep
  their behaviour.
- Verifier reference now uses exact `fractions.Fraction` arithmetic for means, SDs and z numerators (one final rounding),
  not `statistics.fmean`, and keeps rtol 1e-7 / atol 1e-9 / identical NA.
- Regression tests (`tests/unit/test_compact_features.py`): the three real near-constant cdd histories against exact
  rational z (rel 1e-12), the real WFP and GPP constant windows (SD exactly 0, mean exactly the value), large-then-small
  windows against exact Fraction means, decimal exactly-constant history -> NA, nearby non-constant -> finite.

Classification for the supervisor: classes 1 and 2 changed feature values (SD residues up to 2e-4; z-MA errors up to ~0.17;
z of near-constant histories off by up to ~7%); no fitted result existed yet. The old saved inputs of the legacy versions are
not affected by this change.
