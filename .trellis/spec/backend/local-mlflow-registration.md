# Local MLflow registration of IPCCH Forecasting models

Contract for `IPCCHMLflow/` in this repository (task 10-09-ipcch-mlflow-sep-oct-registration). Use it when
adding a fitted model snapshot or an evaluation-only result update to the shared local MLflow store.

## Scope / trigger

Agent workflow, not a watcher: after a model fit or result change that should be browsable, an agent adds
an explicit source entry and runs plan → backup → snapshot → import → verify → dashboard → compare.
Eligible: models actually fitted in September–October 2026 or later. Excluded: Nigeria Sep18 and
`climate2015_v1` families (also as content inside uploaded files) and pre-period models.

## Signatures

```bash
PY=/home/swl007007/.venvs/ipcch-mlflow/bin/python
$PY IPCCHMLflow/catalog.py plan|import|verify|dashboard|dashboard-verify [--source KEY] --tracking-uri URI [--live]
$PY IPCCHMLflow/store.py backup|restore-check|snapshot|compare ...
```

## Contracts

- Experiments `IPCCH Forecasting - detailed runs` / `- dashboard`; registered models `IPCCH Forecasting
  <family> | <arm> | <N>-month`; provenance tags `zz_prov.*` written after readable tags.
- Snapshot key (`source_key`) is immutable; content fingerprint covers inventory, vocabulary output and
  importer version. Same key + different fingerprint fails before writes; a complete unchanged snapshot is
  deep-verified and not written.
- Registered model = family × arm × lead; version = source snapshot; annual/origin/phase/calibration
  members live in the version's `members.json`. Alias views (H0 shared fits) have no own registered model;
  evaluation-only revisions (`revision_of`) reuse the prior version after a byte-identical member check.
- Evaluation dataset identity = sorted keys + truth + definition + support + scope; the reporting role
  (`primary`, `original`, `year_YYYY`) is a view association, not identity. One name = one digest.
  Somalia crisis truth = reported phase ≥ 3. Required cohorts are kept when predictions are missing.
- Only finite source values are metrics; undefined values go to `view/na.json` with the source reason;
  finite zero support is kept. Unknown numeric source columns stop the plan.
- Old-store preservation: compare a complete pre-import snapshot (every row of every table by primary key,
  every artifact hash) with the post-import store; old rows must be byte-identical, new rows must be owned
  by the IPCCH Forecasting namespace.

## Validation & error matrix

| Condition | Result |
|---|---|
| Unknown arm/cohort/region/metric/period | `SourceConflict` at plan |
| Model member missing or digest differs from its batch/artifact record | `SourceConflict` at plan |
| Excluded-family content in an uploadable text file | `SourceConflict` at plan |
| Dataset name with two contents (any source) | `SourceConflict` at plan |
| Stored fingerprint differs | stop before any write; register a new snapshot key |
| Revision whose members differ | stop; it is a new fit, not an evaluation-only update |
| Port 5000 without `--live`; scratch server on an occupied port | refused |

## Tests

`tests/unit/test_ipcch_mlflow_naming_extract.py` (vocabulary, extraction semantics, fixtures) and
`tests/unit/test_ipcch_mlflow_catalog.py` (scratch server: import, interruption resume, repeat no-op with
identical DB snapshot, HTTP download hash checks, source change before write, corruption detection,
evaluation-only revision with unchanged version count, dashboard resume/no-op, old-object preservation).

## Wrong vs correct

- Wrong: count booster files as model versions, or re-upload reused weights. Correct: versions per
  snapshot; reused members point to the earlier parent's `models.tar`.
- Wrong: re-plan an imported snapshot from rewritten files. Correct: freeze it and add a `revision_of` entry.
- Wrong: threshold actual q3 for Somalia crisis truth. Correct: reported overall phase ≥ 3.
