# Implementation status (executor; wave 1 only)

Status time: 2026-10-09, Stage 1.

- No production fitting has been done.
- No local results/reports root exists.
- No audit and no commit.

## Done

- Task bound to this Claude session (`session:claude_579e6ba5-…`). Status is in_progress; task.json is byte-identical.
- Two-file implementation written:
  - `scripts/modeling/run_somalia_local_compact_test.py`;
  - `tests/unit/test_somalia_local_compact_test.py`.
- No existing symbol was edited, so no GitNexus impact analysis was required. Frozen helpers are called unchanged.
- Supervisor findings in `/tmp/ipcch-somalia-supervisor-wave1-findings.md`, items 1–9, are all addressed in the two files and each has a test:

  | # | Correction |
  |---|---|
  | 1 | A non-empty batch directory without a batch record is rejected and preserved. |
  | 2 | Spec bytes are read from the manifest-bound copies after task archival, with exact hashes. The manifest identity is unchanged. A modified copy is rejected. |
  | 3 | Obsolete expected-only sentences are removed from the historical codebook too. Both verifiers check the wording. |
  | 4 | Classes are recomputed from the reloaded predictions and must match the saved classes exactly. |
  | 5 | Map metadata must be exactly the seven figures plus the complete geometry component set, with canonical paths, hashes and `mapped_areas`. The geometry join is reconstructed uniquely. |
  | 6 | The frozen snapshot must be non-empty and unique, and must reconcile to current membership (missing and added files), then match hashes. |
  | 7 | Mandatory historical and launch deliverables plus every recorded hash are checked. Missing outputs fail. |
  | 8 | Launch fit keys, targets and weights must each have exact ordered KEYS, plus calendar `fit_ord`, for every run including H0. Historical fitter targets are compared on every fitting row. |
  | 9 | Undefined status and reasons are reconstructed independently and compared across run metrics, the report table, the undefined table and the deltas (oracle and baseline values). |

- Validate-only writes nothing (no temporary output). Fit-run fingerprints are deferred until the local manifest is written; validate-only reports the manifest SHAs.
- Focused suite: 20 new tests plus the existing `test_compact_launch.py`. The latest run of the new file passed 20/20.

## Stage 1 complete (STOPPED)

- **Real `--validate-only`:** exit 0 in 6:47.85; all approved values reproduced; no local root created.
- **Combined focused suite:** the supervisor's independent run at the same hashes is the record (32 passed), so I did not rerun it.
- **Checkpoint:** `research/implementation-checkpoint.md` and `research/preflight-checkpoint.json`; PROGRESS.md entry appended.
- **Next:** waiting for supervisor acceptance before the H0/2022 pilot.

## Blockers

None so far.
