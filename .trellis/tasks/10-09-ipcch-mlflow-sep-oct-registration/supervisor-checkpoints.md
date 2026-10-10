# Supervisor checkpoint record

## Dispatch

- User explicitly authorized execution after the completed grill, using Herdr,
  idle Claude Opus 5.5 (1M), Codex supervision/diff review, and no Trellis audit.
- Reviewed specification checkpoint: commit `b7fca5c`, branch
  `task/ipcch-mlflow-sep-oct-registration`.
- Task manifests validated (three entries each); all 12 source roots and all 12
  fitting-date evidence paths exist. CSV expected booster sum = 2458.
- GitNexus detect_changes before spec commit reported only the pre-existing
  generated AGENTS timestamp section, zero affected processes, low risk.
- Native task activation changed planning to in_progress; no audit wrapper used.
- Herdr environment verified. Executor `w11:p6`, terminal `term_65d6ebf0b04a47`,
  Claude session `074d329d-6842-4b1d-b871-37fb52cec8c7`, same IPCCH cwd. UI explicitly
  showed `Opus 5.5 (1M context)` and idle before dispatch; subsequent get/read
  confirmed working on C0. Herdr prompt's 55-second timeout was only a wait
  timeout; delivery and work were independently confirmed. Prompt was not resent.
- Executor may prepare C0 evidence only until supervisor release. Integration
  coding follows C0; live MLflow writes follow C1. No commit/push/merge/archive
  by executor without checkpoint instructions.

## C0

Reviewed; source inventory, naming layout and alias policy accepted for C1.
Live MLflow writes remain prohibited until C1 review/release.

Early findings sent to executor:
- Reference final README:117-120 and import spec:134-137 require `zz_prov.*`
  (readable tags created first). Updated task PRD/design/naming to the final
  delivered convention; original reference PRD `_prov.*` wording was superseded.
- Preview 5a incorrectly said 6-month 2026 labels through 2025-12. Current
  extension weather-oracle/6m run metadata `new_batch.fit_label_cutoff_month`
  is `2025-07`; fitted input count is 308 for this lead.
- Preview cohort `region3_east_africa_global_model` mislabels region3.
  `evaluate_region3_saved_predictions.py:1,279` says Southern Africa.
- Existing baseline digest does not yet cover all object fields or isolate old
  rows from new ones; C1/C2 preservation verification must compare complete old
  object state (including descriptions/tags/dataset and logged-model associations,
  full metric histories) against the fresh backup, not only counts/latest metrics.

Verification: `supervisor-c0-checks.json` checks every member reference against
the source path/SHA inventory and independently rehashes one booster in each of
the 12 sources. 2458 unique fitted booster paths, 126 versions, 112 distinct
registered-model identities, 224 reused original members, 1255 mapped metric
entries; all assertions passed. This is not a numerical model replay.

Executor's C0 U1–U12 resolutions (implementation choices within approved scope):
- U1: final `zz_prov.*` convention as corrected above.
- U2: accept eight H0 alias views without duplicate registered models; selected
  v2 remains a registered recipe referencing its actual residual members.
- U3: keep v3 metric-only baselines in both label-setting families, provided
  identical keys/truth/definitions are checked before sharing dataset identity.
- U4: 412 evaluation candidates are provisional, not a frozen digest count.
  C1 must derive full key/truth/definition identities and freeze exact counts
  before live release; same name/different identity must fail or be explicitly
  disambiguated in the readable vocabulary.
- U5: the eight unclassified map/timing/reference files may be preserved as
  included-source diagnostics/ledgers; no plot-data-as-performance logging.
- U6/U7: preserve both manifest and execution commit evidence and date evidence
  from the tasks. Do not invent minute-level timestamps when absent.
- U8: leaky diagnostics only in detailed diagnostic namespaces, not dashboard.
- U9: quote acceptance/conclusions only where source evidence supports them;
  lifecycle completion/waiver is not scientific acceptance or an audit pass.
- U10: share training descriptors only for identical complete pool identity
  including scope, truth/label role and feature/schema or explicit arm variants.
  A baseline child must not misleadingly claim it trained on the oracle's 308
  columns. The proposed 45(+8) count may change for truthful descriptor identities.
- U11: external codebooks/report tables need explicit paths AND SHA/role entries
  in the final source fingerprint/inventory. Do not upload the mixed report.
- U12: full experiment/model prefix isolates the shared service.

C1 tests must preserve v4 required cohort vs available scored-row support for
incomplete slots; missing predictions cannot silently shrink a dataset or make
an incomplete score look complete. Final C1 plan must give exact metric/dataset
counts and reconcile any change from C0; no unexplained count relaxation.

## C1

Pending supervisor review; no live-write release yet.

Implementation diff baseline is `c9dcef1` (reviewed C0 evidence/spec correction).
Early naming.py review findings sent to executor while C1 proceeds:
- q3 optimization description must not define actual crisis as q3 >= 0.20.
  `somalia_oracle/data.py:175` defines actual crisis from phase >=3;
  `q3eval.py:78-89` thresholds predicted q3_final and evaluates against that truth.
- Launch description must say no scoring truth is attached to these saved
  summaries, rather than claiming no actual labels exist (April H0 has actuals).
- Region cohort helpers must reject unknown region vocabulary instead of
  accepting any `region_*_global_model` string.
- extract.py must reconstruct exact phase-persistence keys, not use count-only
  identity with the parent hash. Source rule is data.py:365-386 and saved v2 label
  ledger + row-provenance origin; v3 saves persistence_available explicitly.
- Reporting period role must not change dataset identity for identical Compact
  original-primary and extension-original keys/truth; keep the role on the view.
- Duplicate equal metric values must still check matching dataset association
  and retain their source locators, not silently mask different cohort bindings.

Naming/extract initial versions were read by supervisor; executor is applying
these findings. Final code/test verification is still pending at the C1 gate.

At approximately C1 minute 10 the executor briefly showed an API connection
retry; the same session was retained, with no replacement or production writes.


C1 second review (read-only probes + supervisor spot checks; sent to executor):
- v4 copy truth was nulled after joining the label ledger; dataset identity must
  retain actual copied labels as well as copy provenance. Mutating a copy label
  must alter the digest.
- Southern Africa contrast metrics had no dataset association; bind role/lead.
- v2/v3 omitted finite within-month AUC support counts; v1 zero n_rows became NA.
- Existing-store artifact namespace comparison mixed str/int experiment IDs.
- Restore check skipped directory contents, allowing zero actual downloads;
  recurse and compare downloaded content with the backup hashes. Scratch server
  must not accept another already healthy process on its requested port.
- Dashboard resume skipped old-row retirement after a crash at completion;
  unchanged dashboard also wrote status tags before verification.
- Deep readback omitted dataset descriptors/input tags, full external model and
  registered-version identity/status fields, reference versions and row.json.
- Source conflict preflight followed a possible experiment-description write.
All are C1 repair/verification obligations, not authorization for live writes.

## C2

Pending supervisor review; no completion/acceptance claim.

## User scope correction during C1

User explicitly instructed: “不把数据溯源当做blocker，不然没问没了了”。
This supersedes earlier strict provenance gates: missing/incomplete historical
lineage and exhaustive descriptor-proof gaps are disclosed, not blockers. No
additional lineage archaeology or user clarification. Checkpoints gate practical
import correctness, successful recoverable registration, no unintended duplicates,
and preservation of existing objects/source files. Fix available-data mapping bugs
proportionately, document residual limitations, and converge on live execution.
Sent to the existing Herdr executor; no scope reset or audit workflow.

### C1 verification scope and progress

- The 27 focused extraction/catalog tests passed (executor output: 55.33 s).
  Supervisor inspected the scratch tests covering import interruption/resume,
  unchanged store digest on no-op, corrupt artifact detection, source conflict,
  original/extended versions, result-only updates and existing-object preservation.
- Supervisor personally read the maintenance README/spec and matching AGENTS/CLAUDE
  diff. Requested one practical follow-up: preservation comparison must allow
  intended retirement of our own dashboard rows during later maintenance, while
  retaining protection for existing reference and detailed records.
- Backup/restore report `/tmp/ipcch-c1/rehearsal/restore-check.json` reports success:
  2,223 artifacts restored; six HTTP downloads matched backup hashes on port5091.
- Full real-source scratch import/repeat was deliberately skipped after supervisor
  adjustment: all-source offline planning plus passing scratch fixture integration
  suffice at C1; complete real-source readback/repeat runs once at live C2.
- Readable naming, value correctness, recovery, no-op and preservation remain gates;
  historical provenance incompleteness does not.

### C1 accepted; C2 released

Supervisor reviewed C1-report, final maintenance README/spec and matching agent
guidance, targeted implementation fixes, and focused test evidence (27 passed
after the maintenance correction, 66.20 s). Counts frozen: 112 models, 126
versions, 12 parents, 190 children, 174 latest rows, 512 datasets, 50,446 finite
detailed metrics, 2,846 NA records. Sources unchanged; training code untouched.
C1 accepted under the user's explicit nonblocking-provenance scope.

C2 is authorized: retain a durable verified backup; refresh current-store baseline;
import the 12 sources into the isolated IPCCH Forecasting namespaces; verify
values/artifacts/counts, repeat as no-op, compare existing records/artifacts.
Supervisor performs browser checks. No retraining, audit, push, merge or archival.
Executor stops for C2 review after evidence is saved.
