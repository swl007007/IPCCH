# PROGRESS — global-origin-safe-climate-idp

Operational ledger only; not approval or acceptance evidence.

## Lifecycle

- 2026-10-06T14:49-04:00 — `trellis-audit start` run from bound Claude session.
  - run ID: `3a9127b8b73e42318fc83ffd5e141cda` (phase active)
  - base_sha: `9e66cc5b8337b85b7f51c129cb1eaaf24bcc2e00` (= HEAD, approved planning commit)
  - executor: claude session `cb41f664-60a8-49e5-9221-ab4b33b84dee`, terminal `term_65d3065df8dc98`, Herdr pane `wP:p3`
  - Trellis task.json status: `in_progress`
  - Pre-existing user-owned `AGENTS.md` modification left untouched.

## Steps (implement.md)

- [x] 1. Planning committed (9e66cc5), audit start verified.
- [x] 2. Code inspection + GitNexus impact (2026-10-06 ~15:10). `run`/`parse_args` in the global CLI: LOW risk,
  one direct caller (`main`). Subprocess consumers: Nigeria audit uses `--country-iso3 NGA` (unaffected);
  `run_climate2015_global_suite.py` (global annual) is now blocked by design. `climate2015_features` reused,
  not modified; `select_numeric_feature_columns`/`annual_splits` untouched.
- [x] 3. Input build COMPLETE (678 s, exit 0): manifest
  `1.Source Data/assembled_IPCCH/model_ready/origin_safe_climate_idp_v1/origin_safe_climate_idp_v1_manifest.json`;
  recorded code sha256 == committed c57ab03 files. Arms H0/3/6: 863/868/870 features, H12: 647/652/654.
  Source-support perturbation (cutoffs 2022-06, 2024-03) changed 0 cells with origin <= cutoff in every horizon.
- (history of step 3) Versioned input builder `scripts/preprocessing/build_origin_safe_climate_idp_inputs.py` written;
  full build started 15:3x (`/tmp/osci/build.log`). Findings so far: cohort 52,521 label keys, eval 28,205
  (5,599/6,064/5,127/11,415) as projected; interim grid contiguous for all 6,227 areas (39 end 2024-12);
  every retained inherited dynamic column reproduces from interim source months at its declared anchor after
  masking non-existent carrier rows (0 value mismatches; a few columns have extra saved NaN, kept).
- [x] 4. CLI `--protocol monthly-origin` + prefit gate + global-annual block; suite orchestrator written.
- [x] 5. Focused checks: `tests/unit/test_origin_safe.py` (12 pass), `tests/smoke/test_origin_safe_cli.py` (5 pass).
- [x] 6. Selected tests in ~/.venvs/ipcch-geo (Py 3.12.3, XGB 3.2.0, NumPy 2.4.4, pandas 3.0.3, sklearn 1.8.0):
  40 passed (climate2015, origin_safe unit, origin_safe CLI smoke, weight-decay country, weight-decay SHAP CLI).
- [~] 7. Pilot (H0, idp arm, target 2025-12, 47,824 fit rows, 870 features): 110 s @16 threads, 112 s @8,
  169 s @32; peak RSS ~5.2 GB; predictions sha256 identical across thread counts. Bundles ~16 MB/batch.
  Pilot outputs in /tmp/osci (not reused). Suite launched 2026-10-06T15:28 with --n-jobs 16 (setsid nohup),
  sequential horizon-major; log `results/experiments/origin_safe_climate_idp_v1/logs/`. Code commit c57ab03.
- Read-only trellis-check review (15:3x–15:4x, no edits): no leakage/cohort/target/classification/arm/fit-key
  defect. One defect breaking required behaviour, no number changed: pooled metrics passed "pooled" into
  `compute_metrics` (`int(test_year)`) -> every run would crash at assembly and the suite would stop after
  run 1. Fixed in non-fingerprinted `forecasting_weight_decay.py` (`_year_label`, both helpers); added pooled
  unit test and a full 48-month CLI smoke test (the gap that let it through). Suite killed/relaunched
  ~15:55; 13 finished batches re-verified by fingerprint and reused. 8 evidence-only findings: handled in the
  verifier (independent history/IDP replay from raw sources on all rows — passes at all horizons —, carrier-tail
  missingness attribution, feature timing classes incl. identifiers, runtime/git identity) and in evidence.
- Run 1/12 (climate_no_history H0) COMPLETE 2026-10-06 ~16:53 (3,476 s incl. 13 reused batches); metrics
  assembled with pooled row; n_samples equal the frozen cohort. ~90–115 s per batch; ETA for all 12 runs
  roughly 2026-10-07 early morning (estimate only). Background waiter on suite exit.
- 2026-10-06 ~17:15 USER STOP + re-grill: a target month can have 10–50 evaluation rows (3 of 48 months < 50,
  12 < 100), monthly refits judged not meaningful. All suite processes killed. Decisions (AskUserQuestion):
  one fit per test year with cutoff Jan(Y) − max(H,1) and weights anchored at Jan(Y) − H; report year +
  pooled; delete monthly outputs (deleted: runs/ ~964 MB + logs + /tmp pilots); reuse inputs unchanged.
  prd R3/R5/AC4, design and implement.md amended (change record in prd.md).
- User asked to re-check that H12 (and other) features cannot leak: `scripts/postprocessing/
  audit_origin_safe_feature_timing.py` perturbs every source after 9 cutoffs (2018-12 … 2025-06) — interim
  sources, climate grid/seasons, IPC labels, DTM reports — and compares against the SAVED datasets.
- CLI switched to `--protocol origin-safe` (annual blocks, `--block-years`); suite/verifier/tests updated;
  19 origin-safe tests pass.
- Timing audit (9 cutoffs x 4 horizons, saved datasets): 0 changed eligible values; label-copy tripwire clean.
  Committed 98fc6cd; annual suite 17:55–19:00, 12/12 COMPLETE (3,879 s, peak RSS 5.4 GB).
- [x] 8. Verifier passed (12 runs, 48 batches, 288 artifacts re-hashed, 96 bundles reloaded, 1.28 M fit-key
  rows, independent history/IDP replay on 210 k rows, sklearn replay max |diff| 2.2e-16). Report
  `reports/origin_safe_climate_idp_v1/report.md`; evidence.md complete. Verifier report writer no longer needs
  `tabulate` (not installed; environment not changed).
- [~] 9. Guidelines updated; evidence written; commit + audit close next.
