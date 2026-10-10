# Checkpoint C1: offline implementation (executor report)

Diff baseline c9dcef1. No writes to the live service (port 5000), source trees, frozen fitting
scripts, model environment or the FCC repo. No training, rescoring or Trellis audit.

## Files (all executor-owned)

New:
- `IPCCHMLflow/naming.py`: vocabulary.
- `IPCCHMLflow/extract.py`: explicit format extractors.
- `IPCCHMLflow/plan.py`: read-only planning and global checks.
- `IPCCHMLflow/catalog.py`: CLI for plan/import/verify/dashboard/dashboard-verify.
- `IPCCHMLflow/store.py`: lock, backup, restore-check, snapshot/compare.
- `IPCCHMLflow/sources.json`: 12 snapshots, cited files with SHA256, exclusions, frozen counts.
- `IPCCHMLflow/README.md`.
- `tests/unit/ipcch_mlflow_fixtures.py`, `tests/unit/test_ipcch_mlflow_naming_extract.py`, `tests/unit/test_ipcch_mlflow_catalog.py`.
- `.trellis/spec/backend/local-mlflow-registration.md`.

Edited: `.trellis/spec/backend/index.md` (link); `AGENTS.md` and `CLAUDE.md` (one matching
"Local MLflow registration" section each; the pre-existing AGENTS memory-timestamp hunk is untouched);
task `prd.md`/`design.md`/`PROGRESS.md` (user scope correction).

GitNexus `detect_changes` (repo IPCCH, scope all): risk low; 0 affected processes; changed symbols are
only AGENTS/CLAUDE document sections. No existing code symbol was edited, so no impact analysis was needed.

## Commands and results

| Check | Command | Result |
|---|---|---|
| Focused tests | `PYTHONPATH=tests/unit:IPCCHMLflow $PY -m pytest tests/unit/test_ipcch_mlflow_naming_extract.py tests/unit/test_ipcch_mlflow_catalog.py -q` | **27 passed** (66 s) |
| All-source plan | `$PY IPCCHMLflow/catalog.py plan --store /tmp/ipcch-c1/store --out /tmp/ipcch-c1/c1-plan.json` | rc 0; frozen counts reproduced |
| Source unchanged | re-hash of the 12 roots vs `c0/source_hashes.csv` | byte-identical (3,626 files) |
| Backup (live store, read-only, lock held) | `$PY IPCCHMLflow/store.py backup --dest /tmp/ipcch-c1/rehearsal/backup` | rc 0; 2,223 artifact files; DB counts equal to live |
| Restore-check | `$PY IPCCHMLflow/store.py restore-check --backup ... --port 5091` | ok; 3 experiments; 6 recursive downloads, all equal to backup hashes |

Full real-source scratch import/verify/repeat was cancelled on supervisor instruction; it belongs to C2 live.

## Frozen plan counts (sources.json `expected`; plan refuses any difference)

| Level | Count |
|---|---|
| Registered models / versions | 112 / 126 |
| Detailed parents / children | 12 / 190 |
| Dashboard rows (latest snapshot) | 174 |
| Booster files / new fit units | 2,458 / 584 |
| Evaluation + training + inference datasets (distinct names, one digest each) | 512 |
| Detailed metrics / NA records | 50,446 / 2,846 |

Reconciliation with C0: the object counts are unchanged. Datasets (C0 provisional ≤ 412 eval candidates)
now also include training and inference descriptors, and cover regional cohorts and v4 copies. Metrics now
include within-month AUC support counts, finite zero support, and region-3 contrasts bound to their
Southern Africa dataset.

Per-source fingerprints are in `/tmp/ipcch-c1/c1-plan.json` and are re-derived on every plan.

## Implemented contracts and fixed review findings

- **Dataset identity** = sorted keys + truth + definition + support + scope.
  - The reporting role is an association only; the original-snapshot `primary` and the extended
    snapshot's `original` share one dataset.
  - The same name with different truth is rejected across sources.
  - v1/v4 reconstructed keys equal the sources' own `cohort_sha256`.
  - The v2 persistence subset is rebuilt with the `persistence_lookup` rule from the saved label ledger
    and origin_ord, with n parity.
  - v4 copies keep their saved truth: changing a copy's q3 changes the digest.
- **Values:** NA values with reasons; finite zero kept; unknown numeric columns stop the plan; repeated
  equal values must share a dataset, and their provenance is retained.
- **Members:** batch/artifact-record digests are checked per booster. Extension versions = 4 new +
  reused original members, with links to the original `models.tar`. The v2 selected recipe = D_residual
  members (0 fits). H0 aliases have no registered model.
- **Evaluation-only revision:** set `frozen` on the old snapshot and add a `revision_of` entry. Member
  identity is checked and existing versions are reused; the test shows an unchanged version count and an
  intact old snapshot.
- **Store safety:**
  - Preflight before any write; `--live` is required for port 5000.
  - The scratch server refuses an occupied port.
  - A repeat import and an unchanged dashboard are true no-ops (identical DB snapshot).
  - Dashboard resume repairs retirement.
  - Readback covers dataset entities and input tags, logged-model tags/params/status, version
    run/source/tags/description/status, alias versions, and `row.json`.
  - compare: old rows byte-identical by primary key; new rows must be in our namespace; the only allowed
    old-row change is soft deletion of a superseded IPCCH Forecasting dashboard row.

## Proposed live plan (C2, after release)

```bash
PY=/home/swl007007/.venvs/ipcch-mlflow/bin/python; U=http://127.0.0.1:5000; B=~/ipcch-mlflow-backups/$(date +%Y%m%d-%H%M)-before-ipcch-forecasting
$PY IPCCHMLflow/catalog.py plan --out C2/plan.json                           # writes ipcch-forecasting/plans + cache
$PY IPCCHMLflow/store.py backup --dest $B && $PY IPCCHMLflow/store.py restore-check --backup $B --dest /tmp/ipcch-fc-restore --port 5091
$PY IPCCHMLflow/store.py snapshot --out C2/before.json
$PY IPCCHMLflow/catalog.py import --tracking-uri $U --live --out C2/import.json      # ~4 GB tars staged under ipcch-forecasting/staging
$PY IPCCHMLflow/catalog.py verify --tracking-uri $U --live --out C2/verify.json
$PY IPCCHMLflow/catalog.py dashboard --tracking-uri $U --live --out C2/dashboard.json
$PY IPCCHMLflow/catalog.py dashboard-verify --tracking-uri $U --live
$PY IPCCHMLflow/catalog.py import --tracking-uri $U --live --out C2/import-repeat.json   # expect sources_noop 12
$PY IPCCHMLflow/catalog.py dashboard --tracking-uri $U --live --out C2/dashboard-repeat.json  # expect dashboard_noop
$PY IPCCHMLflow/store.py compare --before C2/before.json --out C2/compare.json
```

The supervisor handles the browser check. Each CLI call re-plans all sources, which takes about 50 s.

## Known limits (disclosed, not gates)

- Some snapshots have only task-record fit dates.
- Source audit debt and waivers are quoted, not resolved.
- Country-level launch summaries and diagnostics stay in the detailed runs only.
- Logged-model metric associations include alias/reference views (same values, own datasets).
- The 8.3 GB C1 backup copy at `/tmp/ipcch-c1/rehearsal/backup` can be deleted after C2.
