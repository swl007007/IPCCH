# Evidence: origin_safe_climate_idp_v1

Evidence for prd.md R1–R10 / AC1–AC5. Paths are relative to the IPCCH repo unless absolute. External inputs live
under `1.Source Data/assembled_IPCCH/model_ready/origin_safe_climate_idp_v1/` (here `$INPUTS`).

## Lifecycle

- Audit run `3a9127b8b73e42318fc83ffd5e141cda`, base_sha `9e66cc5`, executor Claude session
  `cb41f664-60a8-49e5-9221-ab4b33b84dee` / terminal `term_65d3065df8dc98`, started 2026-10-06 14:49 EDT.
- Code commits: `c57ab03` (implementation), `7cffb5a` (pooled-metrics fix + verifier), followed by the
  evidence commit. The pre-existing user change to `AGENTS.md` was never staged.

## Inputs and provenance (AC1, AC2, AC3)

Builder: `scripts/preprocessing/build_origin_safe_climate_idp_inputs.py`, run 2026-10-06 (678 s, exit 0).
Manifest: `$INPUTS/origin_safe_climate_idp_v1_manifest.json` — sha256 of every input (interim panel, four scope
files, climate monthly/seasonal, DTM admin0 monthly, country lookup, identifier source) and output, per-arm
feature order and hash, code sha256. The manifest's `git_head` is the planning commit `9e66cc5` because the
build ran on the uncommitted working tree; the recorded code sha256 values equal the files in `c57ab03`
(checked before launching the suite), so code identity rests on those hashes.

- **Cohort (R8).** 52,521 reported phase 1–5 keys of the corrected interim panel. All four scope files contain
  exactly these keys (fs1/fs2's extra 736 phase-0 rows are dropped) and their label/share columns equal the
  interim projection exactly. 52,306 keys have valid shares; evaluation keys 28,205 =
  5,599 / 6,064 / 5,127 / 11,415 (2022–2025), equal to the projection; frozen in `$INPUTS/..._cohort_keys.csv`
  (2,805 genuine phase-1 evaluation keys kept; 355 evaluation rows whose raw shares do not sum to ~1 are
  normalized only in the derived targets).
- **Safe history (R2, R4, AC1).** `origin_safe.build_safe_history` (Nigeria latest-three algorithm, extended to
  H=12 and to a separate label table). Ledgers `$INPUTS/..._history_ledger_h{H}.csv` hold the real source month
  of each value. Checks: builder's pure-Python replay on all 52,521 rows × 4 horizons; the verifier's
  separate merge_asof replay from the dataset labels (all rows, all horizons: equal). Minimum source age on
  evaluation rows = 1 / 3 / 6 / 12 months for H = 0 / 3 / 6 / 12. Evaluation-row history counts
  (0/1/2/3 values): H0 1,548/2,380/2,694/21,583; H3 1,570/2,500/2,809/21,326; H6 2,537/2,609/2,351/20,708;
  H12 3,799/2,525/2,301/19,580.
- **Legacy inputs removed (R4, R9).** Per horizon the builder removed 142 (H0/3/6) or 97 (H12) old FLDAS
  climate columns, `overall_phase_prev_observed_asof_s{H}` / `overall_phase_lag1`, and `estimated_population`
  (`results/experiments/origin_safe_climate_idp_v1/input_checks/feature_classification_h{H}.csv`).
- **Retained inherited predictors (R7, AC2).** 29 static snapshot columns (per-area invariance verified) and
  339 (H0/3/6) or 250 (H12) dynamic columns. Each dynamic column was recomputed from interim source months
  with `src/ipcch/retained_feature_recipes.py` at its declared anchor (t−12 for asof12 families, t−H for
  `_sH` families and the ENSO "forecast_sequence", t−12 for the delayed control): 0 value mismatches and 0
  saved values without recipe support; 3–4 columns have extra saved NaN (kept as genuine missingness).
  The interim panel is contiguous per area, so upstream row shifts are month shifts. Reproducing upstream
  needed one modelling detail: grid months without a panel row are NaN (neighbour means and carrier rows).
- **Climate2015 block (R7, AC2).** 468 (H0/3/6) or 341 (H12) columns from the 14 monthly/GS ensemble
  indicators, built directly at anchor H (plus asof12) with no old carrier-tail mask; two latest seasons with
  `gs_end_date_exclusive <= first day of O+1`. NaN share on evaluation rows 0.84–0.89 %.
- **Source-support perturbation (AC2).** For cutoffs 2022-06 and 2024-03, every monthly source value after the
  cutoff (interim sources and climate grid) and every season ending after the origin month was perturbed;
  0 changed values on rows with origin <= cutoff, for every retained and climate column at every horizon
  (`input_checks/source_support_h{H}.csv`: 807 columns at H0/3/6, 591 at H12). The perturbation changed later
  rows of every column except 3 per horizon — the two `gs_last*__months_since_end` counters (depend on season
  dates, not values) and `nino34_anom__enso_stress__any12_asof12` (flag already saturated) — so the test had
  power elsewhere. This is sampled at two cutoffs, not exhaustive.
- **National IDP (R6, AC3).** DTM `idp_admin0_monthly.csv`: one row per country-month (checked), non-null stock
  only on observed rows, `reportingDate` month equals row month, no negative or zero stocks. Join by lookup
  ISO3 (one row per area_id). 33 label countries have reports, 19 do not; Côte d'Ivoire's 31 areas
  (350 label rows) lack ISO3 in the lookup and stay NaN (DTM has no CIV rows either; ISO3 was not inferred).
  Latest report <= O; age = O − report. Evaluation rows with a value: 24,577 / 24,457 / 24,357 / 23,981
  (H0/3/6/12); median age 4 / 3 / 2 / 2 months, maximum 122–128 months (stale context). Checked by the builder's
  replay and the verifier's independent replay from the raw DTM table (all rows equal).
- **Not verified / limits.** Climate climatology/standardization fitted samples are undocumented (approved
  limitation). Static snapshots and revised observations are fixed retrospective context. Observation month
  is an availability proxy, not a publication vintage. Identifier features (lat/lon, target-month/year
  dummies) are known at the target date; with annual blocks the training rows of block Y never contain year Y
  (cutoff Jan(Y) − max(H,1)), so `year_Y` is constant 0 in that fit and carries no information.
  Inherited `_sH` columns keep their saved carrier-tail NaN, whose pattern depends on where the upstream panel
  ends (structural, not label information; quantified in `verification/missingness_carrier_tail.csv`).

## Protocol and code (R3, R5, R9, AC4)

- `--protocol origin-safe` (global CLI; annual blocks since the 2026-10-06 re-grill): mandatory gate before fitting — manifest COMPLETE, dataset/ledger/
  cohort sha256, frozen key hashes, arm adds exactly the 5 history / 2 IDP features, `forbidden_features`
  (legacy history, `estimated_population`, labels/shares), history ledger (value-without-source, source after
  `min(O, T-1)`, horizon), IDP ledger (report after O, age). Global `--protocol annual` raises a migration
  message; country scopes unchanged.
- One fit per test year Y: fitting labels `<= Jan(Y) − max(H,1)` (the strictest `min(O,T−1)` of the year, so
  every scored month is safe), weights anchored at `Jan(Y) − H`. Each annual batch saves predictions
  (unrounded, `%.17g`, with each row's own origin and the fit cutoff), fit keys with age/weight, four `.ubj`
  model bundles and a record with fingerprint, cutoff, fit maximum, minimum age, key hashes, timings and sha256.
- Tests (frozen interpreter `~/.venvs/ipcch-geo`, Python 3.12.3, XGBoost 3.2.0, NumPy 2.4.4, pandas 3.0.3,
  scikit-learn 1.8.0): `tests/unit/test_origin_safe.py` 13 passed; `tests/smoke/test_origin_safe_cli.py`
  6 passed (global annual rejection; partial run + resume; reintroduced lag1 rejected before fit; ledger
  source after origin rejected before fit; changed dataset hash rejected; full 48-month plan assembles yearly +
  pooled metrics); `test_climate2015_features.py`, `test_forecasting_weight_decay_country.py`,
  `test_weight_decay_shap_cli.py` pass. The full repository suite was not run (known unrelated failures;
  not run concurrently with heavy fits).

## Review findings and repairs

Read-only trellis-check review of `c57ab03` (2026-10-06):

1. **Breaks required behaviour, no number changed** — pooled metrics passed `"pooled"` into
   `compute_metrics`, which applied `int()`: every run would crash at assembly and the suite would stop after
   run 1. Fixed in `forecasting_weight_decay.py` (not part of the run fingerprint; annual callers pass ints and
   are unchanged). Tests added: pooled unit test and full-plan CLI smoke test. The suite was relaunched; the 13
   finished batches were re-verified by fingerprint and reused.
2. Evidence/provenance only (8 items): carrier-tail missingness mechanism; identifier features unclassified;
   IDP gate checks area alignment only; history gate checks internal consistency only; fingerprint omits
   `forecasting_weight_decay.py` and run metadata lacks git/runtime versions; builder manifest `git_head`
   precedes the implementation; perturbation sampled at two cutoffs; GPP scope-feature missingness in 2025.
   Handled by the verifier (independent history/IDP replays on all rows, missingness attribution, timing class
   for every fitted feature, runtime/git/code hashes in `verification_summary.json`) and by this document.
   Fingerprinted files were not changed.

## Protocol change (re-grill 2026-10-06)

The first suite used one refit per target month. After run 1 of 12 had finished (and run 2 had partially run), the user stopped it: some months have only 10–50
evaluation rows (3 of 48 months < 50, 12 < 100, median 250). Decisions: annual blocks as above, report per
year + pooled, delete the monthly outputs (deleted), reuse the inputs unchanged. Monthly results are not
reported anywhere.

## Runs (R3, R5, R10, AC4)

PENDING — to be filled from `results/experiments/origin_safe_climate_idp_v1/` after the suite finishes.

## Verification and results (AC4, AC5)

PENDING.
