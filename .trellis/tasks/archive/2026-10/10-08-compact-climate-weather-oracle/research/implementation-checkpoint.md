# Implementation checkpoint before real fitting (2026-10-08)

Executor: Claude Opus 5.5 (1M), Herdr pane w11:p4, session 579e6ba5-f2a2-483c-b465-4b2e3cca1ed3. Status: implementation
and input build 2 verified; **no real XGBoost fit has run** (only tiny synthetic smoke fits). Paused for supervisor review
and commit. Fingerprinted code must stay byte-stable from here (see hashes below).

## Provenance (truthful)

- Git HEAD during both input builds: planning commit `928d08081376311b298358cbad5eb8b21ad7fc35`, with the implementation
  **uncommitted** (manifest `git_status_porcelain` records it). Inputs were not rebuilt to hide that. After the supervisor's
  implementation commit, fit metadata will record the committed code hashes through the run fingerprint; the input manifest
  keeps its build-time HEAD/porcelain.
- Windows Git used for every git call (`/mnt/c/Program Files/Git/cmd/git.exe`, or the shim on PATH for builder subprocesses).
- Build 1 (failed independent verification) is preserved, renamed only:
  `1.Source Data/assembled_IPCCH/model_ready/compact_climate_weather_oracle_v1__superseded_build1/` (manifest sha256
  `1a020405e77dd28155907c17b2b7630629af54426d07430d801cf00a0dec4eca`) and
  `results/experiments/compact_climate_weather_oracle_v1/superseded_build1/` (input checks, failed verification, logs,
  old dry-run logs/ledger, README). Root cause and remedy: `research/numeric-root-cause.md`.

## Changed / new files (sha256 at checkpoint)

| sha256 | path |
|---|---|
| 923cae26335f9994043c178a0920a7736e7e80dc9c51a5fffa8d406f07fdf324 | src/ipcch/compact_features.py (new) |
| a10a5d847c8e6c5d724ffb0eb32b5ed98ff08a6d531d6574f9159efc913e5da4 | src/ipcch/regional_point_metrics.py (new) |
| fa10cee75402477e6f0f190c0881935a2891449ddbd6d3c3e5fe55c7419c1171 | scripts/preprocessing/build_compact_climate_weather_oracle_inputs.py (new) |
| b04ab8795da90351f5a0ae171488e52a11019d923c6704bbb30e3ddabc368149 | scripts/modeling/run_compact_climate_weather_oracle_suite.py (new) |
| 67729cf9f55c442ba3e748bfadbd56e9ecfe2692861a5103ac7cb08a003dc184 | scripts/modeling/run_deep_feature_weight_decay_forecasting.py (modified: import, `--arm` choices, compact dispatch, new `load_compact_inputs`; legacy/oracle-v1 code paths byte-unchanged) |
| 158ab55c470620ca427d15ce275cb02b9c965cdf74252d53dd448eebf0cfe052 | scripts/postprocessing/verify_compact_climate_weather_oracle.py (new) |
| 13dad7b9aa19b28e1841463ed588cde5bb4296c0615a430d035b06753ada7faf | tests/unit/test_compact_features.py (new) |
| aabf9d57bc62eb96e4e686b02b8b02a0dffa6e30bcf637c7c893c54242256ea6 | tests/unit/test_regional_point_metrics.py (new) |
| 9b6ad70b26c87582bee132802b3eef06a49b821eeaec97856472e51c8faac60d | tests/unit/test_compact_report.py (new) |
| 9303388840df273a98bb3d62b60806e761347015a638ccf665a0206b588cdc37 | tests/smoke/test_origin_safe_cli.py (compact tests appended) |

Not edited by the executor: legacy helpers (`climate2015_features`, `retained_feature_recipes`, `weather_oracle`,
`origin_safe`, `forecasting_weight_decay`), spec/approval files (prd/design/implement/rollback/contract/approval),
`.trellis/spec/backend/quality-guidelines.md` (supervisor's edit), AGENTS.md/CLAUDE.md (restored byte-identical after the
GitNexus re-index). `rollback.md` was not edited; its post-implementation section is left to Codex (paths below).

## Input build 2 (current)

- Manifest: `1.Source Data/assembled_IPCCH/model_ready/compact_climate_weather_oracle_v1/compact_climate_weather_oracle_v1_manifest.json`,
  sha256 `456360536a3929e1571d96ba9f16e2f0de54bc1b20019f797bbe62c0c89732ca`, status COMPLETE.
- Datasets (one per arm/H): baseline h0/h3/h6/h12 296 features; oracle h3 302, h6/h12 308; ledgers: season h0..h12,
  oracle h3/h6/h12; history/IDP ledgers are the parent's pinned files. Approved contract bytes copied to
  `.../compact_climate_weather_oracle_v1/contract/` (CSV, metadata JSON, run index; hashes equal the approval) and bound
  in the manifest; the original task-directory hashes and `execution-approval.json` hash are recorded under
  `contract.approved_source`.
- Build command: `PATH=/tmp/ipcch-windows-git-bin:$PATH PYTHONPATH=src /usr/bin/time -v ~/.venvs/ipcch-geo/bin/python
  scripts/preprocessing/build_compact_climate_weather_oracle_inputs.py` -> exit 0, 5:34.8 wall, peak RSS 2.7 GB
  (log `results/experiments/compact_climate_weather_oracle_v1/logs/build_inputs.log`).
- Builder gates passed: pinned parent/source/cohort/contract hashes; bbg members == pinned 5/3/2/9; history/IDP ledgers;
  calendar dummies == target calendar; season values == existing `last_completed_seasons` selection; schemas == contract
  `features_by_run`; CSV round-trip equality; oracle-input baseline projection == baseline (cells/NA/order/keys/labels);
  raw oracle == origin_safe_weather_oracle_v1 raw columns; source-support perturbation 1,864 non-oracle + 60 oracle
  feature/cutoff cells unchanged for origin <= cutoff; origins within source spans (0 after last month, all H).
- Same-month z exact-constant cells set NA (per source, full grid): GPP 660, nightlight 30,660, WB 9, cdd 449, others 0.
- Old-vs-new comparability (diagnostic, `input_checks/old_new_comparability.csv`): restored old-NA cells H0 184,203,
  H3 179,835, H6 83,784, H12 0. Value differences only in the intended numerical corrections: GPP/WFP SD12 (all H) and
  edd SD12 (H3) residues (max |diff| 3.9e-4), H12 z of near-constant cdd/rainy_days/hot_days histories; 48 old cdd z
  values now NA (exactly constant prior history).

## Verification commands and results

| command | result |
|---|---|
| `/tmp/compact_preflight/preflight2.py` (copy: `research/preflight2.py`) | passed; `research/execution-preflight-rowlevel.json` (h12 static int/float dtype-only, numeric+NA identical) |
| legacy inventory before (`research/legacy_inventory.py`) | 740 files hashed -> `results/.../preflight/legacy_hash_inventory_before.csv` |
| `PYTHONPATH=src ~/.venvs/ipcch-geo/bin/python scripts/postprocessing/verify_compact_climate_weather_oracle.py --stage inputs` (build 2) | exit 0, passed=true; 372,800 independently replayed cells (exact Fraction arithmetic) 0 mismatches; pinned sources/cohort/contract re-hashed equal to frozen parent/approved bytes; legacy 740/740 unchanged; 3:29 wall, 4.3 GB peak (`input_verification/verification_summary.json`, log `logs/verify_inputs.log`) |
| same, build 1 | exit 1, 20 mismatches (preserved under `superseded_build1/`) |
| `PYTHONPATH=src ~/.venvs/ipcch-geo/bin/python scripts/modeling/run_compact_climate_weather_oracle_suite.py --dry-run` (build 2) | exit 0; 7/7 DRY_RUN_OK (296/296/296/296/302/308/308 features; fit cutoffs H0 Dec, H3 Oct, H6 Jul, H12 Jan of Y-1); no file created/modified under the results namespace (before/after listing identical); output `research/suite_dry_run_build2.txt` |
| focused tests (executor, before last report-text edit) | 53 passed (compact unit + report + regional + origin-safe CLI smoke); earlier full focused set 85 passed |
| focused tests (supervisor, `research/supervisor-test-checkpoint.json`) | 93 passed |
| `tests/unit/test_compact_report.py` after the report-text edit | 1 passed |

## GitNexus evidence

- Before editing: `impact(load_origin_inputs, upstream)` LOW (direct caller `run_origin_safe`; `run` -> `main`; 1 process);
  `impact(parse_args, upstream)` LOW (caller `main`). Subprocess callers outside the static graph: the origin-safe suites and
  `tests/smoke/test_origin_safe_cli.py`. The runner's own sha256 is in every legacy fingerprint, so old legacy run
  directories cannot be resumed by the modified runner (expected; rollback refits need a fresh `--out-dir`).
- After re-index (AGENTS.md/CLAUDE.md restored byte-identical): `impact(load_compact_inputs)`, `impact(same_month_z)`,
  `impact(trailing)` all LOW, confined to the compact runner branch / `monthly_block`.
- `detect_changes(scope=all)`: risk medium; changed symbols `parse_args`, `load_origin_inputs`; `verify_batch` and
  `run_origin_batch` were reported "touched" only by line shifts (Windows Git diff of the runner shows additions only: one
  import, the `--arm` choices line, the compact dispatch and the new function).

## Supervisor findings addressed (items 1-6 and follow-ups)

1. Numeric root cause traced and fixed (shift-centred per-window statistics; exact-constant z -> NA; exact rational
   reference), regression tests on the real windows; legacy helpers untouched; tolerances unchanged.
2. Report pivot: `wide_metrics` unstacks only existing groups (all-undefined groups kept); test `test_compact_report.py`.
   Comparability text now reports actual counts and separates numerical corrections from restored NA.
3. Verifier re-hashes the three sources, cohort and contract copies against the frozen parent/approved references before
   the replay. CLI compact branch enforces frozen runtime (3.12.3/2.4.4/3.0.3/1.8.0/3.2.0), config hashes, helper bytes ==
   build `code_sha256`, pinned sources/cohort/contract; legacy branches unchanged.
4. Compact fingerprint = `compact_features.fingerprint_payload` (manifest/dataset/arm/H/feature/frozen schema, ledgers,
   parent, sources, cohort, contract, build code, fit code incl. runner + `forecasting_weight_decay`, configs, full runtime
   incl. interpreter, params). The verifier rebuilds it from current state and requires payload, digest and every batch
   fingerprint to match. Legacy fingerprint path unchanged.
5. Codebook is `fitted_verified_all_batches` only when every run/batch/model/replay check passed; otherwise
   `_UNVERIFIED` files with `unverified_diagnostic` status.
6. Suite `--dry-run` creates no directory/log/ledger, prints CLI output; real runs keep logs/ledger.
- Contract lifecycle: stable byte copy in the versioned input namespace (archive-safe), original provenance recorded.
- Limitation recorded (manifest `limits` + `origin_within_source_span`): origins after a grid's last month would blank
  supported windows; 0 such cohort rows; future cohorts out of scope.

## Unresolved / open

- No fitting evidence yet: 7 runs, 28 batches, 112 models, global/regional metrics, replay and actual codebook are pending
  the supervisor's commit and continuation.
- Near-constant but non-identical histories keep finite, possibly huge z (e.g. cdd area 101214 2023-01 z = -1.015e15);
  approved semantics, no clipping (documented limitation).
- `rollback.md` post-implementation paths/commit not yet appended (spec file; Codex owns). Paths for it: manifest above;
  runs `results/experiments/compact_climate_weather_oracle_v1/runs/{compact_baseline,compact_weather_oracle}/<H>m`.
- `.trellis/tasks/.../executor-binding.json` and supervisor research notes are untracked task files written by Codex.

## Planned continuation (after supervisor commit)

1. Pilot: `PYTHONPATH=src ~/.venvs/ipcch-geo/bin/python scripts/modeling/run_compact_climate_weather_oracle_suite.py
   --runs compact_baseline/0m --block-years 2022` (one real batch; measure time/RSS; verify artifacts).
2. Full: `setsid nohup ... run_compact_climate_weather_oracle_suite.py` (resumes the pilot batch by fingerprint), sequential.
3. `verify_compact_climate_weather_oracle.py --stage all` -> metrics, deltas, regional tables, codebook, report.
