# Somalia local compact/CDS test — Stage 1 implementation checkpoint (2026-10-09)

Status: **the implementation, the focused synthetic checks and the real read-only preflight are complete. No production fitting has been done.**

- No local results/reports root exists.
- No Trellis audit (user override, approval.md/R11) and no commit.
- STOPPED for supervisor acceptance.

Machine-readable record: `research/preflight-checkpoint.json`. It embeds the complete preflight JSON.

## Identity

- **Executor:** Claude Opus 5.5 (1M), session `579e6ba5-f2a2-483c-b465-4b2e3cca1ed3`.
  - `task.py current --source` gives `session:claude_579e6ba5-…`.
  - Task status is in_progress; task.json is byte-identical after `start`.
- **Repository:** HEAD `3ccf92a` (the approved plan commit) on branch task/compact-climate-weather-oracle.
  - The bound spec bytes (prd, design, implement, expected_runs, approval) equal `3ccf92a` exactly.
  - The `/tmp/ipcch-windows-git-bin` shim no longer exists. My git calls were read-only (rev-parse/status/show) through the system git.
- **Runtime:** `/home/swl007007/.venvs/ipcch-geo/bin/python`, with Python 3.12.3, NumPy 2.4.4, pandas 3.0.3, sklearn 1.8.0 and XGBoost 3.2.0. Fixed settings: seed 42, half-life 24, threshold 0.2, n_jobs 16.
- **Code** (new files only):

  | file | sha256 |
  |---|---|
  | scripts/modeling/run_somalia_local_compact_test.py | 88aee59be33033dd85f180bd9cc4e5f317bc9c033b1a32a972fe0acf82ea8c56 |
  | tests/unit/test_somalia_local_compact_test.py | 3c149547623e8cee33365e4575e23ac3fc4d5b8b098cf1f6c30fab6638a5ae27 |

- **Existing symbols edited: none.** GitNexus impact analysis was therefore not required.
  - Frozen primitives are called unchanged: `load_origin_inputs`, `run_origin_batch`, `verify_batch`, `compact_launch.validate_inputs`/`fit_run`/`fingerprint`/`verify_run_record`/`repaired_shares`/`aggregate`/`paired_differences`/`_continuous_panel`, `regional_point_metrics`, the legacy sklearn `replay`/`classes`, and the `launch_visualizations` join/panel.
  - Frozen code/config hashes (19 files) are recorded in the JSON.

## Design as implemented

**Modes**
- `--validate-only` writes nothing, not even a temporary file.
- `--approve-training [--pilot]`: `--pilot` fits only historical compact_baseline H0 / 2022, which stays PARTIAL.
- `--report` and `--verify` use saved artifacts only and never fit.

**Historical stage**
- The full parent gate runs first via `load_origin_inputs`.
- Both `share_valid` and `eval_key` are then intersected with the SOM membership (`iso3 == "SOM"`, exact; no name fallback).
- A local fingerprint binds:
  - the parent fingerprint;
  - the deterministic hashed local manifest (membership, cohort, spec copies, parent contract, script, parameters);
  - the local keys.
- The unchanged `run_origin_batch` then fits each block.
- A non-empty batch directory without a record is rejected and preserved.

**Launch stage**
- The full parent `validate_inputs` gate runs first.
- SOM fit-selection and inference projections are exact filters of the parent files, with these gates:
  - each must be the complete eligible set, recomputed independently from the training dataset;
  - targets must match an independent normalization;
  - `fit_ord`, ages and April-anchored weights are checked;
  - paired baseline/weather fit frames must be identical and the baseline inference prefix must match;
  - each projection must survive a serialized round trip unchanged.
- Population and cap:
  - the population ledger is the SOM subset of the parent April ledger;
  - the Somalia row comes from the original complete cap audit (approved values reproduced);
  - the coverage ledger records area 3146 as outside launch coverage (not invented).
- The local manifest preserves the parent fitting-entry format and adds local version/scope/membership/spec/code/parent hashes. The unchanged `fit_run` fits each run.
- A scope sidecar binds each fingerprint and artifact record. Inherited records keep the parent model-contract version.

**Reports**
- Historical:
  - annual and pooled SOM metric tables with support counts;
  - undefined reasons;
  - oracle − baseline deltas, including shared-H0 zero rows;
  - an actual-fitted codebook with expected-vs-actual and run index;
  - report.md.
- Launch:
  - area table, SOM summary and paired-difference tables;
  - seven SOM maps with titles checked to lie inside the canvas, in the inherited style;
  - actual codebook and summary.

**Verify** (independent arithmetic, different code path)
- Every model is reloaded and replayed (atol 1e-6), and classes are recomputed from the reloaded predictions (exact).
- Keys, targets and weights are checked for each run.
- Metrics, undefined status/reasons and deltas are replayed with sklearn and independent conditions (atol 1e-12).
- Population, cap, shares, counts and differences are recomputed.
- Map records, the seven-entry metadata, geometry components and a unique join are checked.
- Required deliverables and their recorded hashes are checked.
- Frozen-snapshot membership (missing and added files) and hashes are reconciled.
- Any failure is a non-pass, recorded with its diagnostic.

## Supervisor wave-1 findings: corrections and their tests

| # | Correction (in the two files) | Test |
|---|---|---|
| 1 | A non-empty batch dir without `batch_record.json` → `LocalError`; partial files are preserved | `test_incomplete_batch_directory_is_rejected_and_preserved` |
| 2 | After the task is archived, spec bytes come from the manifest-bound `inputs/approved_spec` copies with exact hashes; no archive path enters any identity | `test_archived_task_uses_manifest_bound_spec_copies`: same historical/launch manifest SHA, verify passes, modified copy rejected |
| 3 | `clean_limitations` drops only the two obsolete expected-only sentences, in both codebooks; both verifiers reject the wording | the historical report test (limitation kept: "Proxy month."); the launch map test |
| 4 | `replayed_class_problems`: classes of the four reloaded columns must equal the saved classes exactly | `test_replayed_classes_must_match_exactly_across_the_threshold` (0.19999995 vs 0.20000005) |
| 5 | Exactly seven metadata entries, the complete geometry component set, canonical paths, hashes and `mapped_areas == n`; unique geometry keys and a reconstructed one-to-one join | tamper test (a dropped map entry is detected) |
| 6 | The snapshot must be non-empty, unique and well-formed; the historical and launch snapshots must be identical; membership is reconciled (missing/added), then hashes | `test_frozen_snapshot_must_be_complete_and_unchanged` (added file, empty snapshot) plus the tamper test (changed file) |
| 7 | Mandatory historical/launch deliverables and every recorded hash (comparison_metadata, report_outputs, report copies, scope sidecar) | tamper test (missing report.md, changed table) |
| 8 | Launch fit_keys/fit_targets/fit_weights each have exact ordered KEYS, plus calendar `fit_ord`, per run including H0. Historical fitter `targets` are compared on every fitting row against independent normalization | full-plan verify passes; the gates run on all 5 + 28 records |
| 9 | `expected_metric_status` reconstructs undefined conditions and canonical status/reason; these are compared with the run metrics, report table, undefined table and deltas (oracle/baseline values, status, reason) | tamper test (a fabricated reason is detected) |

- Validate-only no longer writes a temporary manifest. Fit-run fingerprints are computed at training, after the manifest is written. The preflight reports the canonical local-manifest SHAs.
- Assembled-prediction ordering is checked by exact sorted key-set comparison. Batch order and within-batch parent order are kept, and the cross-run truth comparison is key-sorted.

## Focused tests

- Supervisor's independent run at the current hashes (`research/supervisor-focused-tests.json/.log`): `pytest tests/unit/test_somalia_local_compact_test.py tests/unit/test_compact_launch.py -q` → **32 passed in 68.47 s, exit 0**.
- My run of the new file at the same hashes: 20 passed in 58.55 s.
- `research/focused_tests.log` (28 passed) is from an earlier script hash and is superseded.
- The 20 tests use tiny mixed SOM/Kenya/Namibia fixtures and drive the real fitters through:
  - the pilot, then the complete 7×4 historical (112 models) and 5-run launch (20 models) plans, with resume;
  - report and independent verify, which passes;
  - membership-change and changed-artifact resume rejection;
  - validate-only with no file changes;
  - unchanged global country-scope rejection;
  - unchanged frozen code hashes.

## Real read-only preflight

- **Command:** `PYTHONPATH=src /usr/bin/time -v /home/swl007007/.venvs/ipcch-geo/bin/python scripts/modeling/run_somalia_local_compact_test.py --validate-only`
- **Result:** exit 0, 6:47.85 wall, max RSS 0.79 GB.
- **Files:**
  - stdout: `research/preflight_validate_stdout.json`;
  - log: `research/preflight_validate.log`;
  - code pins: `research/preflight_code_sha256.txt`.
- **Afterwards:** all four local roots are still absent.

**Parent gates and membership**
- All 7 historical parent gates passed, as did the launch parent gate (parent manifest `b2e73812…cafe`).
- Membership: 905 SOM areas; lookup sha `e2baf6ae…`, area-id list sha `fc171382…`.

**Historical**
- Evaluation keys: 4,933 (sha `5f8343c4…`); 2022/2023/2024/2025 = 1129/1217/711/1876 rows over 585/705/372/904 areas; union 905.
- 6,739 SOM share-valid rows.
- Local manifest SHA if written: `573b0d0b…`.
- Feature counts are 296/302/308 at the frozen hashes. Seven distinct local fingerprints, each differing from its parent fingerprint.
- SOM fitting rows per year (2022–2025):

  | horizon | rows | areas |
  |---|---|---|
  | H0/H3 | 901 / 2030 / 3247 / 3958 | 139 / 649 / 869 / 891 |
  | H6 | 901 / 1504 / 2899 / 3958 | — |
  | H12 | 858 / 944 / 2554 / 3603 | — |

**Launch**
- 5,835 fitting rows over 905 areas (labels 2017-01..2026-01) in each of the 5 runs, with identical paired keys/targets/weights and a matching weather baseline prefix.
- 904 inference areas; 3146 excluded.
- Population: raw 62,695,007; reference 19,654,739; factor 0.29782279233177217; effective 18,672,002.05.
- Local manifest SHA if written: `f76da064…`.

**Frozen inventory snapshot** (identities as of now; not a rerun of the earlier raw-vintage/provider checks)
- 491 files, 2.58 GB, digest `25c45108…`.
- By role: code 23, parent inputs 52, old results 392, old reports 16, geometry 5, membership 1, reference 2.

## Unresolved items and limits

- Production fitting stays closed until supervisor acceptance. The next step would be the measured historical H0/2022 pilot (`--approve-training --pilot`).
- The early Somalia fits are small under the fixed global hyperparameters (H0/2022: 901 rows; H12/2022: 858 rows over 96 areas). This is an inherited limit; no tuning was done.
- Local identity binds the active spec bytes and the script SHA. Any edit before training changes it, which is intended.
- Frozen-root membership is reconciled exactly, so files added to the parent result/report roots by others would fail verify. This is by design.
- Earlier raw-GRIB/provider/vintage verification is inherited from the accepted parents and was not rerun.

## Changed files

- New: `scripts/modeling/run_somalia_local_compact_test.py`, `tests/unit/test_somalia_local_compact_test.py`.
- Task research:
  - implementation-status.md, implementation-checkpoint.md, preflight-checkpoint.json;
  - preflight_validate_stdout.json, preflight_validate.log, preflight_code_sha256.txt;
  - focused_tests.log (superseded).
- PROGRESS.md: entry appended.
- Left untouched: AGENTS.md, the archived contract CSVs and task.json (unrelated working-tree edits by others).
