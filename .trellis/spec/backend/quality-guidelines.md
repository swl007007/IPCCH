# Quality Guidelines

> Code quality standards for IPCCH modeling code (`src/ipcch/`, `scripts/`).

---

## Overview

IPCCH is a research pipeline; the dominant failure mode is silent temporal leakage or
silent sample changes, not crashes. Checks favour explicit contracts over convenience.

---

## Forbidden Patterns

- **Trusting a feature file's scope label as proof of as-of timing.** Verify lineage per
  feature family. Known facts about `assembled_IPCCH/model_ready` scope files (from the
  upstream builder `assemble_latest_IPCCH/build_multiscope_ipcch_features.py`):
  - `_sH` families are the `asof12` columns of the carrier row `t+12-H` of the same area
    (row shift on contiguous monthly rows), i.e. latest source month `T-H`; `_s0` therefore
    uses the target month itself (a month-end nowcast). Where the carrier row does not exist
    (panel ends 2026-04, or 2024-12 for 39 areas) the value is NaN — this tail is structural.
  - `overall_phase_prev_observed_asof_sH` is the label at the exact calendar month
    `T-max(1,H)` (NaN when that month has no label), not the latest observation.
  - `overall_phase_lag1`: generator unproven. It is merged into fs1/fs2/fs3 from the baseline
    on target keys by `organize_ipcch_ml_data_folder.py`; equal values are not source evidence
    and many values post-date the origin. Never fit on it.
  - `estimated_population` is corrected together with the targets for month T — target-side.
  - `ipcch.forecasting_weight_decay.select_numeric_feature_columns` admits both of the last two.
    The global CLI's annual protocol is therefore blocked (see "Origin-safe global protocol").
- **Rounding predictions before the 0.2 phase threshold** (old runner behaviour). Compare
  unrounded cumulative predictions with `>=`; round only for display.
- **Dropping rows by predicted or true cumulative sums** (`convert_phase_predictions`
  style). All-zero valid truth is phase 1; cohorts must be frozen before predictions exist.
- **Forward-filled weather treated as observations.** In `IPCCH_2026_completed.csv`,
  772 Somalia areas repeat their 2025-01 rain/temperature through 2026-03 and all areas
  repeat March in 2026-04. Detect exact repeats of the previous month and treat them as
  unverified.
- Recursive "latest file" discovery for inputs; resolve explicit paths via `ipcch.paths`.

---

## Required Patterns

- Month arithmetic with dense ordinals `year*12 + (month-1)`; origin `O = T - H`.
- History visible months `U <= min(O, T-1)` (H=0 must exclude the target month).
- Inner validation cutoffs per fold: fit labels `<= min(v-H, v-1)`; decay weights anchored
  at each fit's own origin.
- Machine-readable outputs under `results/`, human-readable under `reports/`; write a
  manifest with input sha256, git HEAD and runtime versions.
- Provide an independent replay (different code path, e.g. scikit-learn) for reported metrics.

---

## Testing Requirements

- `PYTHONPATH=src ~/.venvs/ipcch-geo/bin/python -m pytest tests/unit/... -q` for focused
  contract tests on tiny synthetic frames; boundary cases (.196/.2/.204, exclusive season
  ends, H=0 self-exclusion) must be explicit.
- Heavy training only when requested; synthetic smoke tests use tiny `n_estimators`.
- The existing suite has 12 pre-existing failures (alert-risk maps / launch CLI) on main;
  compare against that baseline rather than assuming a clean suite.

---

## Code Review Checklist

- Does any predictor's latest source month exceed the row's origin?
- Are fitting, tuning and threshold choices free of test-year labels?
- Are sample exclusions decided before predictions, identically across compared arms?
- Are undefined metrics reported as undefined (not zero, not dropped)?

## Lessons from the q3-first optimization (2026-09-25)

- Reading saved float predictions with `pd.read_csv` default parsing can change the last bit and split isotonic-calibration ties; replays of saved scores must use `float_precision="round_trip"`.
- Don't run the full pytest suite and a 12–14 worker XGBoost run concurrently on the 15 GB machine; the worker pool dies (`BrokenProcessPool`).
- Training-period validation choices (e.g. residual vs direct q3) can fail to transfer to the outer year; always report non-selected formulations alongside the selected view.

## Lessons from validity-label augmentation (2026-09-26)

- Never reuse a column name for two meanings: the per-row prediction branch (`direct/residual/fallback_direct`) was overwritten by the label branch (`original/augmented`); keep them as separate columns (`branch` vs `label_branch`).
- Augmentation sources must pass the same QC as supervised targets (sentinel phase 0 / zero-sum shares are complete but invalid blocks).
- Upstream `build_multiscope_ipcch_features` functions can recover scope features for unlabeled months in memory; gate on exact parity with the saved fs files on valid keys.

## Lessons from v4 calibrated D (2026-09-30)

- A validity round spans several target months. Every copied row needs its own origin `v-H` (labels `<= min(v-H, v-1)`, sources available `<= v-H`, decay anchored at `v-H`) and its own OOF fit; never reuse the round month's origin for its copies.
- Report isolation is transitive: a row's OOF pool must exclude its own source family, the scoring family it calibrates for, and the outer test families. Express each pool as an explicit spec (setting, H, label cutoff, availability cutoff, fold upper year, excluded families), normalize away ineffective constraints so identical pools share one fit, and persist the spec plus a key hash so a replay can rebuild every pool.
- Setting-specific label roles: filter copies per setting in every role (fit, selection, calibration, outer test). A blanket "exclude copies" filter silently turns the augmented scenario into the original one.
- An exhaustive per-origin search is large: 142 outer jobs → 62 unique selection contexts → 10,320 OOF XGBoost fits on ~1,000 D features. With 12 workers the 15 GB machine dropped to ~200 MB free during final fits; use ≤10 workers and run a measured pilot before a full run.

## Lessons from the climate2015 feature swap (2026-10-05)

- **Model-ready scope files lose their scope block at the end of the grid.** `assemble_latest_IPCCH/build_multiscope_ipcch_features.py` builds every `_sH` scope-block column (all dynamic sources, not only climate) by shifting the asof12 rows by −(12−H). The source grid ends 2026-04, so these columns are NaN for targets after 2025-04 (0m), 2025-07 (3m) and 2025-10 (6m). That blanks 59.7%, 46.1% and 1.6% of 2025 test rows.
  - When comparing feature sets, mask new scope-anchored features on exactly the rows where the old ones are NaN, so that only the feature source differs.
  - Report the unmasked effect as a separate arm.
- **Old run outputs are not a valid baseline after an input rebuild.** The 2026-05-26 3m/6m outputs used 539 features. The fs1/fs2 files rebuilt on 2026-05-30 have 540, which shifts metrics by up to 0.037. Rerun the baseline with the current code and inputs, and compare run metadata (`loaded_rows`, `feature_count`, feature hash) before trusting an old baseline.
- **Fork upstream feature recipes with a fidelity gate.** Recompute the old families from the interim panel with the forked code and compare them with the saved values, before swapping inputs (see `scripts/preprocessing/check_climate2015_fork_fidelity.py`).
- **Tie order in `merge_asof`.** Sort the right side with a stable sort on (key, tie-breaker). Some areas' s1/s2 growing seasons share an end date, and an unstable sort silently picks the wrong "latest" season.
- **Long background chains on this machine.** A session restart reaps backgrounded shells; the downstream steps of a chain never start. Launch multi-hour suites with `setsid nohup`, keep a run ledger, and make the runner skip completed runs.

## Origin-safe global protocol (2026-10-06, `origin_safe_climate_idp_v1`)

Global runs use `run_deep_feature_weight_decay_forecasting.py --protocol origin-safe`;
global `--protocol annual` raises a migration message before loading data (country scopes keep
annual). Contracts, implemented in `src/ipcch/origin_safe.py`:

- Availability proxy = observation/reporting month. `O = T - H`, month-end.
  IPC labels in features **and** fitting: `U <= min(O, T-1)` for every area. Monthly dynamic
  sources and DTM IDP reports: `U <= O`. Growing season: `gs_end_date_exclusive <= first day of O+1`.
- One fit per test year Y with the strictest cutoff of that year: labels `<= Jan(Y) - max(H, 1)`; weights
  `0.5 ** ((Jan(Y) - H - U) / 24)` (age 0 allowed for H > 0). Features of every row still use the row's own
  origin. Fixed configs, seed 42, threshold 0.2. (Monthly refits were tried and dropped: a target month can
  have only 10–50 evaluation rows.)
- History predictors = latest three reported phases of the same area within the cutoff plus two
  differences; missing stays NaN. A source ledger (real source month per value) is required at the
  CLI entrance; `forbidden_features` rejects legacy history, `estimated_population`, labels and shares.
- Targets: shares normalized to sum 1 before building phaseK_worse; raw shares kept; truth for
  classification is the reported phase. Fit/score rows need five finite non-negative shares with a
  positive total. The evaluation cohort (28,205 keys for 2022–2025) is frozen in a cohort file
  before any prediction; no prediction-dependent drops; classes from unrounded scores `>=` 0.2.
- Inputs are pinned by a builder manifest (sha256 of every input and output, feature order per
  arm, code sha256); batches are resumed only when their fingerprint and artifact hashes match.

Lessons:

- **Reproducing upstream row-shift families on a month grid**: mask grid cells where the area has
  no panel row. Otherwise neighbour means include neighbours without a row (228 mismatches) and the
  `_sH` realignment fills carrier-tail rows. With the mask, all 339/250 retained inherited dynamic
  columns reproduce from interim source months (`src/ipcch/retained_feature_recipes.py`).
- Check retained families twice: saved == recipe (row level), and recipe unchanged when every source
  month after a cutoff is perturbed (rows with origin <= cutoff).
- `compute_metrics` is shared; aggregate rows (e.g. "pooled") must not be coerced with `int()`.
  Smoke-test the **full** plan of a runner, not only a partial subset — the assembly branch only runs
  when every batch exists.
- XGBoost 3.2 hist: predictions were bit-identical at 8/16/32 threads; 16 threads was fastest on this
  32-core machine (110 s vs 169 s at 32 for a 47.8k-row, 870-feature 4-target batch, ~5.2 GB RSS).
  Depth-11 bundles are ~16 MB per 4-target fit set.
- Do not edit files hashed into a running suite's fingerprint; put fixes in non-hashed modules or
  accept a rerun.
- Name accuracies explicitly. "Accuracy" in the canonical regressor metrics is five-class; crisis work often
  means phase 3+ vs 1–2. Report `exact_phase_accuracy` and `phase3plus_accuracy` side by side; a verifier that
  reuses the same definition cannot catch a definition error.
- Prefit gates must check every fitted column derived from a ledger (e.g. history differences), not only the
  ledgered base values. Resume checks must require the full artifact set, not only what a record lists.
  `--dry-run` must short-circuit every protocol branch before outputs are created.

## Perfect-weather oracle on the origin-safe reference (2026-10-07, `origin_safe_weather_oracle_v1`)

The only declared exception to the origin-safe timing rules. Implemented in `src/ipcch/weather_oracle.py`.

- Scope: shared monthly `prcp_anom_month_ensmean` and `tmean_anom_month_ensmean` at `O+1 .. O+min(H, 6)` and the
  fixed B6 terms derived from them (F future mean, B = (R + F) / 2, Q = F × 1[safe history_1 ≥ 3]). Realized values
  are a counterfactual perfect forecast assumed available at `O`; the ledger keeps actual observation months and the
  assumed availability month as separate fields. IPC history, IDP, growing season and fitting labels keep their cutoffs.
- Look up source values by calendar month (`Grid.index_of`), never by row offset; months outside the grid are NaN.
- Dependency-specific missingness: F needs all future months; B additionally the saved parent R and every past month
  (stricter than R's own `min_periods`); Q needs F and history_1. A missing F stays NaN under a zero gate.
- The CLI admits oracle arms only with a manifest whose `version` is `origin_safe_weather_oracle_v1` (and admits no
  legacy arm with it), only at H3/H6/H12, only with features exactly equal to the parent reference list followed by the
  declared columns, and refuses output directories inside `origin_safe_climate_idp_v1`. F/B/Q are replayed from the
  dataset's raw columns, saved R, history_1 and the oracle ledger before fitting. Legacy manifests take the old path.
- Append-only inputs: re-read the written CSV with round-trip parsing and require `DataFrame.equals` on every parent
  column (values, NaN masks, order, keys, labels). A feature-list hash is not matrix parity.
- Reuse the reference by explicit path after an all-four-year replay (models, fit keys/weights, targets, metrics);
  never point the modified runner at old output directories (its code fingerprint changed on purpose).

## Regional evaluation of saved global predictions (2026-10-07)

Implemented in `src/ipcch/regional_bootstrap.py` and `scripts/postprocessing/evaluate_region3_saved_predictions.py`.

- Membership is the `area_id` join to `data/reference/area_id_country_region_mapping.csv` (e.g. `region == 3`); never a
  SADC/UN M49/country whitelist. The country lookup supplies bootstrap strata only. Missing membership or a missing
  country for a selected area is an error, not a silent drop. The regional step must not import fitting code.
- Pair runs on an explicit sorted `(area_id, year, month)` index and require equal keys and truths across runs; saved key
  hashes are order-sensitive.
- Country-stratified whole-area paired bootstrap: per period one `PCG64(42)` generator, countries sorted, one
  `(n_draws, N_c)` index block per country; all rows of an area carry its multiplicity; one bundle shared by every arm,
  horizon, metric and contrast. Metrics use integer row weights, equal to explicit row duplication through
  `osf.origin_metrics` (check both, including undefined cases). R² constancy is tested exactly over positive-weight rows.
- Paired-difference intervals are conditional: percentiles over jointly defined draws, reported only with ≥ 1,000 of
  2,000 valid draws; keep every original draw and the per-contrast joint mask, report invalid counts/fractions, never
  substitute zero or draw replacements. This deliberately differs from the Somalia helpers (any-undefined suppression,
  F2 = 0 conventions).

Lessons:

- A stale GitNexus index can miss new symbols (`impact` returns "not found"); `node .gitnexus/run.cjs analyze` also
  rewrites the stats line in `CLAUDE.md`/`AGENTS.md` — keep those out of task commits.

## Compact climate and raw oracle version (2026-10-08)

### Scope and trigger

`compact_climate_weather_oracle_v1` is an explicit feature version. Its approved task supersedes the older carrier/saved-NA
mask rules for this version only. Legacy inputs/results and their selection paths remain intact; returning to a version
selects its manifest and matching arm/output paths. No global feature default or destructive restore is needed.

### Signatures

- Builder: `scripts/preprocessing/build_compact_climate_weather_oracle_inputs.py --contract-dir <approved-contract-dir>`.
- Fitter: `run_deep_feature_weight_decay_forecasting.py --protocol origin-safe --origin-manifest <manifest> --arm
  compact_baseline|compact_weather_oracle --horizon <H> --out-dir <new-version-output>`.
- Seven-run driver: `scripts/modeling/run_compact_climate_weather_oracle_suite.py [--dry-run] [--runs compact_baseline/0m]
  [--block-years 2022]`; a one-year pilot is part of the suite and remains PARTIAL until all years exist.
- Verification/report: `scripts/postprocessing/verify_compact_climate_weather_oracle.py --stage inputs|all --manifest <manifest>`.

### Contracts

- Baseline order is static29, ordinary120, monthly-z56, stress28, two seasons plus latest-major29, calendar27, history5,
  IDP2:296 inputs at every H. Oracle appends raw prcp/tmean in offset-major order,302 at H3 and308 at H6/H12. H0 is shared.
- Reconstruct dynamics at each row's `O=T-H`; retain source-native missingness. Monthly z uses strictly earlier-year
  same-month history first, followed by MA3/6/12. MA minimums2/3/6; SD12 minimum6 and ddof1. No epsilon/clipping of z.
- Keep original stress hit/missing-comparator rules. Major means uniquely longer fixed calendar duration in the selected
  latest season's same-area/year s1/s2 pair; ties/unavailable comparisons are NA. The same ledger selects climate and major.
- Store approved contract bytes in the versioned input directory: a consumed path under an active task directory would
  break after task archival. Keep original task paths as provenance rather than a runtime dependency.
- Compact fingerprints bind manifest/dataset/schema/ledgers/parent/source/cohort/contract/build-code/fit-code/config/runtime
  and seed/half-life/threshold/thread settings. Runtime includes interpreter identity; fit-code includes the metric helper
  `forecasting_weight_decay.py`. Preserve the legacy fingerprint construction.

### Validation and error matrix

| Condition | Required outcome |
|---|---|
| Wrong version/arm/horizon, extra predictors, ledger disagreement | Reject before fitting |
| Frozen runtime/config or pinned file/helper bytes differ | Reject; do not substitute or silently resume |
| Compact output targets legacy namespace | Reject |
| Origin exceeds a source grid's final month | Builder rejects this unsupported cohort; do not silently blank supported windows |
| Child/suite dry-run | Validate without creating model, log or ledger outputs |
| Failed/incomplete full replay | Nonzero result and unverified diagnostic codebook; never claim fitted verification |
| Full verification | Require seven runs,28 batches,112 models, matching fitted order and complete artifact identities |

### Good, base and bad cases

H0 uses current-month dynamic sources while IPC history excludes the target month. H12 uses `O=T-12` once, with no extra
fixed-history block. Oracle H12 uses only `O+1..O+6`. Oracle H0 and a compact arm with a legacy manifest are invalid.
All regions0–8, including empty/small groups, are scored from saved global predictions; pooled metrics use pooled rows.

### Tests required

Check calendar gaps/minimum counts, exact constant and near-constant statistics, z-before-MA and future perturbations,
original stress boundaries, exclusive season ends/ties and the selected-record major dummy, baseline/oracle matrix parity,
legacy/compact selection and complete resume rejection, no phantom report groups, and independent global/regional metrics.
Reload all112 boosters and replay every batch (predictions atol1e-6/rtol0; metrics atol1e-12 with identical undefined masks).
Actual codebook membership comes from checked fitted lists; the approved expected CSV supplies descriptions only.

### Wrong versus correct

Pandas rolling add/remove statistics can leave a nonzero SD after a window becomes exactly constant; naive uncentred
mean/variance can distort z for prior values30.0 versus29.99999999999999. Compact `trailing`/`same_month_z` use per-window,
shift-centred calculations, tested against exact Fraction arithmetic. Keep the old helpers unchanged for legacy versions.
Use unique-group `pivot` for reports: `pivot_table(dropna=False)` on multiple index fields creates nonexistent run groups.
