# Execution plan

Authorized mode: Codex supervisor, Herdr Claude Opus 5.5 (1M) executor.
No Trellis audit. Supervisor owns scope, checkpoint review and final acceptance.
Executor owns integration code/tests/docs and evidence; no parallel code writers.
Keep `PROGRESS.md` in this task directory current at each boundary/failure.

## C0 — freeze the import plan

- [ ] Read PRD/design/naming/source list/research, current AGENTS/CLAUDE and reference
      current naming/import/catalog contracts. Check source and service identities.
- [ ] Expand explicit source inventory, map all arms/setting/period/cohort/metric
      identifiers and required models/recipe members; explain duplicate/reused fits.
- [ ] Produce exact expected object/member counts and a small human-readable
      name/tag/description preview for every family. Resolve aliases explicitly.
- [ ] Save pre-existing dirty paths and read-only reference-store inventory.
      Do not backfill excluded families through mixed artifacts.
- [ ] STOP; report C0 files and proposed smallest code layout. Await supervisor.

## C1 — offline implementation

- [ ] Implement independent IPCCH integration using compatible reference patterns;
      no fitted-script changes, no writes to source model outputs or reference repo.
- [ ] Add explicit naming/extraction contracts and strict required-member checks.
- [ ] Implement plan/import/verify, external registry objects, dataset associations,
      latest dashboard selection, append-only source revisions and resumability.
- [ ] Add focused tests with source-shaped fixtures: 0-month naming, q3/phase
      semantics, v4 NA/incomplete, original/augmented truth, H0 aliases, extension
      reuse/versioning, exclusion of mixed reports, source conflict before write,
      interrupted resume and repeat no-op, and same-name/different-truth rejection.
- [ ] Run an isolated scratch MLflow integration with import/readback/download,
      repeat and injected interruption recovery. Do not use port 5000 for tests.
- [ ] Draft README reading/maintenance guide and matching AGENTS/CLAUDE additions;
      document future model and evaluation-only updates using working commands.
- [ ] Run focused tests, syntax/lint checks available for the changed code and
      source-content unchanged checks. Do not train or run the unrelated full suite.
- [ ] STOP; report code diff, exact commands/results, known limits and live plan.
      Await supervisor's C1 review before live service writes.

## C2 — authorized live import after C1 release

- [ ] Refresh shared-store baseline, acquire compatible lock, take verified backup
      and run isolated restore-check. Preserve reference-service configuration.
- [ ] Apply the frozen plan to the two new experiments and prefixed model names.
      Imports are sequential/resumable. Log failures outside source directories.
- [ ] Deep-verify every imported value/dataset/member/descriptor/version and exact
      counts against the approved plan. Download model artifacts and compare hashes.
- [ ] Repeat unchanged import and dashboard maintenance; assert no duplicate runs,
      metrics, datasets or model versions and no unexpected write to prior objects.
- [ ] Compare existing FCC object and artifact inventories before/after.
- [ ] Check dashboard, detailed run, Models/version and Inputs in browser; save
      screenshots. Verify readable names, descriptions, partial-year support,
      incomplete flags and scope distinctions; report actual 100-row payload size.
- [ ] STOP; report C2 result/evidence and any remaining defects for supervisor review.

## Final checkpoint

- [ ] Fix supervisor findings in executor-owned files, with targeted regression
      verification; no wholesale reruns after checks pass without a reason.
- [ ] Finalize docs and local MLflow spec, reconcile PROGRESS and task metadata.
- [ ] Supervisor reviews full task diff and confirms scope/integration evidence.
      Run GitNexus detect_changes before any commit; for any existing symbol edit,
      obtain impact first and document callers/processes/risk. If unavailable,
      record the tool failure and use pinned source inspection; do not silently
      claim graph verification.
- [ ] Commit only authorized task changes after supervisor review. No amend,
      push/merge, or archival before acceptance. No Trellis audit lifecycle calls.

## Commands and evidence

MLflow Python: `/home/swl007007/.venvs/ipcch-mlflow/bin/python`.
Test commands/CLI names are finalized at C0/C1 and must be copied literally into
the README and checkpoint logs. Capture return codes and output, plus plan SHA,
source inventory SHA, git diff/baseline, source fingerprints, server identity,
backup path and restore/readback reports. Prior archived verification is background
evidence, never represented as a check run in this task.

Use `/tmp/ipcch-windows-git-bin` at the front of PATH for Git on this DrvFS repo.
Do not include unrelated dirty PNG or pre-existing generated AGENTS timestamp
hunk in task commits. User's execution approval is already recorded in PRD.
