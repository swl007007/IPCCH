# Implementation checkpoint: compact 2026 January–April extension (2026-10-09)

Status: **implementation and focused tests are complete, and the real no-write `--validate-only` passed for both scopes. PAUSED at the source-freeze barrier.**

- No heavy fit, no code commit, no extension output root, no Trellis audit.
- The supervisor commits and freezes the code and then releases the fitting phase.

## Identity

- **Executor:** Claude session `579e6ba5-…`; `task.py current --source` gives `session:claude_579e6ba5-…`. task.json is byte-identical after `start`.
- **Repository:** HEAD `16d2e92` (approved-plan commit) on branch task/compact-climate-weather-oracle. The Windows-Git shim was used for Git reads.
- **Runtime:** frozen interpreter `/home/swl007007/.venvs/ipcch-geo/bin/python`, with Python 3.12.3, NumPy 2.4.4, pandas 3.0.3, sklearn 1.8.0, XGBoost 3.2.0.
- **New files (my only code ownership):**

  | file | sha256 |
  |---|---|
  | scripts/modeling/run_compact_eval_2026_extension.py | cbc1f88b2758cf4c2ec87c83257fc6f7f269d54018bd13f98138389da18db678 |
  | tests/unit/test_compact_eval_2026_extension.py | 952bd849fee05bf5396df257d0b7beb2b98c15df6cf5f26268248b3648ffbfac |

- **No existing symbol, helper, config, input or old output was edited,** so GitNexus impact analysis was not required. Frozen modules are loaded unchanged:
  - the runner: `load_origin_inputs`, `run_origin_batch`, `verify_batch`, `load_hyperparameters`;
  - the legacy sklearn `replay`/`classes`;
  - `regional_point_metrics`;
  - the accepted Somalia-local script, used for original local fingerprint reconstruction and its generic helpers.
- Unrelated dirty files (AGENTS.md and the archived superseded PNG) are untouched.

## Implementation (design steps 1–8)

**Parent gate and masks**
- The unchanged frozen parent gate runs first with the original cohort masks.
- A copied mapping then gets:
  - the 2026 January–April evaluation mask;
  - for SOM, fitting and evaluation masks intersected with exact `iso3 == "SOM"`.
- A new extension fingerprint binds:
  - the deterministic extension manifest: parent, cohort, membership or region map, original evidence and accepted inventory, selection summary, run schemas and expectations, approved-spec copies, script SHA, the reused helper SHA, parameters, configs and runtime;
  - the parent fingerprint and the recomputed original run fingerprint.
- The extension fingerprint is never equal to an original fingerprint.
- No year constant is changed and no gate is bypassed.

**Fitting**
- Only `run_origin_batch(..., year=2026)`. Old years are never refit and there is no oracle H0.
- Resume only through `verify_batch` with the extension fingerprint. A non-empty batch directory without a record is refused and preserved.

**Original import (per run)**
- The original fingerprint is recomputed:
  - global: the parent gate fingerprint;
  - SOM: the accepted local script's `hist_localize` on the archived, hash-checked copies, requiring manifest `573b0d0b…`.
- The original run must be COMPLETE, with matching fingerprint, schema, years and **fixed parameters**.
- **Accepted-inventory reconciliation** (review finding 1): every applicable original file must be listed in the accepted inventory and have an unchanged hash. The prior verification must have passed (28 batches / 112 models).
  - global: `verification/artifact_inventory.csv`, 203 entries covering run_metadata and every batch artifact/record;
  - SOM: `verification/verification.json` inventory, which also covers published predictions and metrics.
- `verify_batch` is run with the original fingerprint.
- Fitting keys, cutoff, scope, ages and weights are checked as the complete expected set.
- Evaluation keys must equal the pinned originals; truth and normalized targets are checked, and the class rule is checked.
- Published predictions must equal the batch predictions.
- All 16 booster schemas per run are inspected.
- The lineage records the accepted-inventory reference per year.

**Combined predictions and metrics**
- `predictions_2022_2026.csv`: original rows are preserved exactly, plus the 2026 batch, in canonical key order.
- `sources_by_year` gives reused vs fitted-here years and their fingerprints.
- Metrics use explicit periods (2022..2026, `pooled_2022_2026` main, `pooled_2022_2025` original) over global plus regions 0–8 (empty and small groups kept) or SOM. Deltas come from `rpm.delta_rows`, plus the SOM shared-H0 rows.
- Global keeps the accepted display-only `region_name` mapping from the original verification summary.

**Reports and verify**
- `--report` writes the CSVs, coverage, comparison metadata, report.md and the three codebook files with status `verification_pending`.
- `--verify` checks:
  - all 28 new models are replayed (atol 1e-6), with **classes recomputed from the reloaded predictions**;
  - all 140 schemas are inspected;
  - every metric cell's value, status, reason and **all 7 support columns** match an independent recomputation (finding 2);
  - **split tables equal their canonical subsets**;
  - delta values, status, reasons and support are recomputed;
  - original-period parity covers value, status, reason and support;
  - the undefined-reason tallies, the codebook against the boosters, and every recorded output hash are checked;
  - the protected inventory reconciles (complete membership, then hashes).
- Then **truthful finalization** (finding 3): report.md, codebook `fit_status` and comparison metadata are set to `verified` or `verification_failed`, and only their hashes are refreshed. Models, predictions and fingerprints are untouched.

## Supervisor review (`research/supervisor-code-review.md`) — addressed

| # | Fix | Test |
|---|---|---|
| 1 | `accepted_inventory` (prior pass, complete applicable coverage, current hashes); fixed-parameter check; lineage `accepted_inventory` | tampered original → "not reconciled with the accepted inventory"; prior `passed=False` → rejected; published-prediction drift caught; lineage `entries_checked == 7` |
| 2 | `independent_support` (all 7 columns); exact split-table subsets; delta support; region names | n_areas-only tamper fails; `regional_metrics.csv` `true_positive_3plus` tamper fails |
| 3 | `finalize_reporting` → verified or verification_failed, refreshing only report/codebook/metadata hashes | pending before verify; verified after, with matching recorded hashes; failed status after a failing verify; verified again after restoration |
| 4 | Fixtures use tiny test-only hyperparameters (`n_estimators=4, max_depth=2`) for both the original and the extension toy fits | whole extension suite in 32 s (88 s before) |
| — | pytest return codes captured by redirecting to a log file and recording `$?`, not through a pipeline | see commands below |

## Commands and exits

1. Focused tests (implement.md command):
   `PYTHONPATH=src /home/swl007007/.venvs/ipcch-geo/bin/python -m pytest tests/unit/test_compact_eval_2026_extension.py tests/unit/test_compact_report.py tests/unit/test_somalia_local_compact_test.py tests/unit/test_compact_features.py tests/smoke/test_origin_safe_cli.py -q`
   - Result: **82 passed in 130.35 s, pytest exit 0**.
   - Log: `research/focused_tests.log`. Code pins (verified unchanged after the run): `research/focused_tests_code_sha256.txt`.
2. `PATH=/tmp/ipcch-windows-git-bin:$PATH PYTHONPATH=src /usr/bin/time -v /home/swl007007/.venvs/ipcch-geo/bin/python scripts/modeling/run_compact_eval_2026_extension.py --scope global --validate-only`
   - **exit 0**, 2:46.47, max RSS 1.66 GB.
   - Output: `research/validate_global_stdout.json` / `.log`.
3. The same command with `--scope SOM`.
   - **exit 0**, 2:36.77, max RSS 1.00 GB.
   - Output: `research/validate_SOM_stdout.json` / `.log`.

Pre-review runs (81 passed; both validations exit 0 at the earlier script hash `243fe253…`) are kept as superseded evidence in `research/superseded_pre_review/`.

## Real preflight facts (both passed, no problems, nothing written)

**Global**
- 2026 evaluation: 4,327 keys over 3,823 areas; by month 679/643/231/2,774; keys sha `e925e0f4…`.
- Original keys: 28,205 (`f0193c14…`, as pinned). Expanded pool 32,532 rows.
- Fit sets for 2026:

  | H | rows | areas | cutoff | latest actual label |
  |---|---:|---:|---|---|
  | 0 | 47,979 | 6,225 | 2025-12 | 2025-12 |
  | 3 | 47,796 | 6,225 | 2025-10 | 2025-10 |
  | 6 | 42,715 | 6,203 | 2025-07 | 2025-07 |
  | 12 | 38,536 | 6,169 | 2025-01 | 2025-01 |

- Features 296 / 302 / 308. 2026 NaN cells 160,350 … 111,343, equal to the contract table.
- Original fingerprints `b9f808ea…`, `1b55aff2…`, `11395c69…`, `09deda91…`, `12d3257d…`, `daf7e4bc…`, `eeb4884c…`. All 28 original batches import and all 112 schemas were inspected.
- **Original parity: 2,800 of 2,800 cells.**
- Extension manifest SHA if written: `913fae43…`.

**SOM**
- 2026 evaluation: 905 keys over 904 areas; by month 1/0/0/904; keys sha `e2a14c20…`.
- Original keys: 4,933 (`5f8343c4…`). Expanded pool 5,838 rows.
- Fit sets for 2026: H0/H3 5,834/905; H6 4,926/905; H12 3,958/891.
- Latest actual labels: H0 2025-10 (cutoff 2025-12); H12 2024-07 (cutoff 2025-01).
- Original local fingerprints `d2524106…`, `047bbd92…`, `389617f9…`, `06f08660…`, `fc56b83b…`, `36d9115b…`, `61239afd…` equal the accepted Somalia run identities.
- **Original parity: 280 of 280 cells.**
- Extension manifest SHA if written: `bce554fb…`.

**Protected inventory (my gate):** 859 files, 2.74 GB, digest `c9720c51…`.
- By role: code 24, parent inputs 20, old results 551, old reports 8, launch inputs 34, launch results 197, launch reports 23, membership 1, reference 1.
- The coordinator's independent baseline (`supervisor-protected-before.json`, 961 files) uses a wider membership. Both gates are checked again for A8.

## Limits and next step

- The 2026 block is partial (January–April) and month-imbalanced; Somalia is almost entirely April.
- Retrospective availability proxy; single seed; no bootstrap.
- **Next, after the supervisor commits and freezes the source:**
  1. `--scope global --approve-training`, then `--scope SOM --approve-training` (14 batches / 56 boosters).
  2. `--report` for each scope.
  3. `--verify` for each scope.
