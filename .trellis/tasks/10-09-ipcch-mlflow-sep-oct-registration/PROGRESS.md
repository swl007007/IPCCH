# Execution ledger

Authority: prd.md, design.md, naming.md, sources.csv, implement.md in this task.
User authorized Herdr supervisor–executor implementation after the completed grill.
This file records operations, not new authority. No Trellis audit.

Baseline: main at b5fcc82116562422a2a07c9ae5467aa2c355f6df.
Supervisor: Codex, Herdr w11:p1, session 01a12183-f261-7e20-9bc9-641ccb5b5cda.
Executor candidate verified idle: Claude Opus 5.5 (1M), w11:p6,
session 074d329d-6842-4b1d-b871-37fb52cec8c7, same IPCCH working directory.

| Checkpoint | Status | Evidence / next action |
|---|---|---|
| Spec | component-complete | Persisted after user authorized start; validate and activate task |
| C0 inventory/naming | ACCEPTED by supervisor (see supervisor-checkpoints.md C0) | `c0/C0-report.md`, `c0/naming-preview.md` + CSV/JSON evidence; supervisor early-review items 1-5 applied; executor STOPPED, no C1 code, no live writes |
| C1 offline code/tests | executor-complete, awaiting supervisor review | c1/C1-report.md; 27 tests passed; all-source plan with frozen counts; backup + restore-check ok; STOPPED, no live writes |
| C2 live import/readback | pending | Backup, import, verify, idempotency, browser and preservation |
| Final diff/docs | pending | Supervisor accepts after evidence; no automatic push/merge |

Pre-existing dirty: old superseded compact launch PNG; AGENTS generated memory
timestamp (2026-10-09 7:30pm EDT). Preserve; exclude unrelated hunks from commits.

## C0 log (executor, 2026-10-09/10 UTC)

- Read task prd/design/implement/naming/sources/research, AGENTS/CLAUDE, FCC `38adbda` readable-naming PRD,
  IPCCHMLflow README/naming/import/backup/manage and both local-mlflow specs.
- Service/store identity checked read-only (3.17.0, 127.0.0.1:5000); baseline `c0/store-baseline.json`
  (126/136 runs, 68 models/100 versions, no `IPCCH Forecasting*` objects). Limitation recorded: full per-object
  preservation comparison against a fresh backup is a C1/C2 obligation.
- 3,626 source files hashed under the 12 roots; 2,458 boosters = 584 fitted units; 1,938 distinct byte contents.
- Frozen proposal: 12 parents, 190 children, 112 registered models, 126 versions, 174 dashboard rows,
  <=412 eval dataset names (digest-final at C1), 10 launch inference descriptors.
- Metric map 1,255 rows, 0 unresolved; exclusion scan: in-root climate2015 mentions are lineage only; the
  mixed report `reports/origin_safe_climate_idp_v1/report.md:132-171` will not be uploaded.
- Supervisor early review applied: zz_prov.*; 6-month extension cutoff 2025-07/308 inputs; Southern Africa for
  region 3 from code; preservation-check limitation; alias views/fit-unit counts spelled out.
- Open for supervisor: U2-U12 in `c0/C0-report.md` section 7. `supervisor-checkpoints.md` not edited by executor.

## C0 completion (executor)

Supervisor accepted C0 for offline implementation; U1-U12 resolved in supervisor-checkpoints.md C0.
Frozen object counts: 112 registered models / 126 versions / 190 children / 174 latest dashboard rows.
Exact dataset and metric counts are derived and frozen at C1 (C0's 412 dataset candidates are provisional).

## C1 progress (executor, ~15-minute checkpoint)

Baseline for the C1 diff: c9dcef1 (supervisor commit). Files so far (all new, executor-owned):
- `IPCCHMLflow/naming.py`: central vocabulary. zz_prov.*; region cohorts validated against REGIONS;
  Somalia crisis truth = reported phase >= 3 (data.py:172-175); launch "no attached scoring truth" wording.
- `IPCCHMLflow/extract.py`: explicit extractors (modern_runs incl. long/region3, launch, somalia_v1/v2/v3/v4);
  dataset identity = sorted keys + truth + definition + scope; period role is a view association only.
  No count-only datasets: v2 phase persistence is reconstructed from the saved label ledger + row_provenance origin_ord
  with the persistence_lookup rule, with n parity. Duplicate equal values must agree on dataset; provenance kept.
- `IPCCHMLflow/plan.py`: read-only planning (hash, classify, cited-file pins, leak scan, global checks).
- `IPCCHMLflow/sources.json`: 12 explicit snapshots, cited external files with SHA256, exclusions, frozen counts.

Check run (read-only, scratch cache /tmp/ipcch-c1): all 12 sources plan; frozen counts reproduced
(112 models / 126 versions / 190 children / 174 dashboard rows / 2,458 boosters / 584 fit units).
Derived at C1 for freezing: 511 dataset names (one digest each), 50,061 detailed metrics, 2,739 NA records.
v1 and v4 reconstructed cohort keys equal the sources' own cohort_sha256 on every slot.

Remaining: MLflow import/verify/dashboard (catalog.py), store.py (lock, backup, restore-check, full old-object
snapshot/compare), tests (fixtures + scratch server integration incl. interruption/repeat/source change), README,
spec doc, AGENTS/CLAUDE guidance, scratch rehearsal, C1 report.

## User scope correction (2026-10-09, C1)

User: provenance/lineage is not a blocker; disclose residual lineage limits and proceed. Supervisor findings 1-10 and the
evaluation-only revision path were implemented as concrete defects; no further evidence archaeology.

## C1 completion (executor)

Report: c1/C1-report.md (files, commands, frozen counts 112/126/190/174, datasets 512, metrics 50,446, NA 2,846,
proposed C2 sequence). Evidence: c1/plan-result.json, c1/restore-check.json, c1/backup-log.txt.
Tests: 27 passed. Supervisor findings 1-10, the revision path and the compare allowance for dashboard retirement are done.
Full real-source scratch import was cancelled per supervisor; it runs once in C2. Executor stopped at C1.
