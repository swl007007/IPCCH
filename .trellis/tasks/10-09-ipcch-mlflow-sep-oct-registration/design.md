# Design

## Baseline and reference authority

IPCCH baseline: `b5fcc82116562422a2a07c9ae5467aa2c355f6df`.
Reference repo is sibling `Food_Crisis_Cluster`, observed HEAD
`38adbda938d8346bd14b89c06d3296e467d23764`; refresh identity before reusing code.
Read these documents and the relevant implementation directly:

- `.trellis/tasks/archive/2026-10/10-09-mlflow-readable-naming/prd.md`
- `IPCCHMLflow/README.md`, `naming.py`, `inventory.py`, `import_runs.py`,
  `summary_catalog.py`, `backup_restore.py`, `manage.sh`
- `.trellis/spec/backend/local-mlflow-import.md`
- `.trellis/spec/backend/local-mlflow-summary-catalog.md`

The existing store must NOT be rebuilt. Reference rebuild/reconcile instructions
are historical, not this task's rollout. Existing hardcoded family counts,
periods, arm names and 1/3/6/12 leads are not this import's expected inventory.

## Small implementation boundary

Add a standalone `IPCCHMLflow/` integration in this repository. Reuse the reference
import/catalog patterns and directly reusable utility code with provenance;
adapt the explicit source extractors and naming to IPCCH. Avoid a general plugin
framework and avoid importing the reference's hardcoded whole application.
Provide explicit plan/import/verify and incrementally updated catalog operations,
with a documented agent-facing maintenance command/sequence. A single CLI may
combine stages if that preserves independent dry planning and verification.
Tests live in `tests/unit/test_ipcch_mlflow*.py` or the integration's test folder.
Add one reusable `.trellis/spec/backend/local-mlflow-registration.md` and link it
from the backend index; AGENTS/CLAUDE point to actual commands and this contract.

Use the already isolated `/home/swl007007/.venvs/ipcch-mlflow` (MLflow 3.17.0)
and `http://127.0.0.1:5000`; verify the current setup before live writes. Model
environment `/home/swl007007/.venvs/ipcch-geo` remains unchanged. No model loading
is needed merely to catalog saved external descriptors. Keep task/import logs
outside existing inventoried result/report roots.

## Source inventory and exclusion

`sources.csv` pins the 12 permitted source snapshots, including original and
extended compact outputs. Build a deterministic detailed inventory only under
these explicit roots and their explicitly cited required inputs/reports. No
recursive latest-family discovery. Expand and review exact members at C0.
Record source SHA/size, model membership, fitting-date evidence, recipe identity,
required/optional role, reused-source pointer and the decision for every candidate.

Do not blindly upload entire task archives, scripts, manifests or mixed reports.
`verify_origin_safe_climate_idp.py:387-400` embeds excluded climate2015 results
in an otherwise allowed report. Use whitelisted included sections/fields with
source locators, or omit the mixed report and render an included-only catalog
description. Scan proposed artifact contents for excluded-family result leakage.
An exclusion ledger may live in the task, but excluded families get no MLflow
objects, metrics, reports or provenance-only records. Preserve truthful required
input lineage of included models without importing excluded model results.

## Identity and object layout

Detailed experiment: one parent per source snapshot retains the approved source
bundle once, and children represent family/setting × arm × lead. Multiple label
settings can share a source parent while child family names make settings clear.
Registered models use `IPCCH Forecasting <family short title> | <arm> | <lead>`.
Keep annual/origin/phase components inside the version's explicit member index.
All descriptor links resolve to its detailed child and parent artifact URIs.

Version identity is an immutable recipe/source snapshot, not import wall time.
Compact original/extended sources share registered model names but have distinct
versions. Extended versions reference old members and add the 2026 members; parent
bundles may link other verified parents rather than upload old weights twice.
No silent reference to arbitrary same-hash weights in another source.
Different recipes may share bytes; physical deduplication never erases job identity.

Initial counts are derived at C0 and frozen before implementation acceptance.
Count source roots, detailed parents/children, logical registered models, versions,
dashboard rows, datasets, required physical members, and actual fits separately.
Do not equate 2,000+ boosters with 2,000+ model versions.

## Naming, metrics and datasets

`naming.md` is the explicit mapping contract. Implement vocabulary centrally and
fail on unmapped scientific identifiers, rather than leaking raw shorthand.
Use compact readable tags (family, arm, arm_role, lead_months, model_scope,
stage, label_setting where relevant, source_status) and `_prov.*` for machine
identity. Do not mark scientific status passed just because catalog import passed.

Dashboard is wide, one row per currently displayed family/arm/lead snapshot.
Use `<period_role>.<cohort>.<metric>` keys and source-backed
`<A>_minus_<B>` contrasts. Region is part of cohort identity, not local fit scope.
Historical records must preserve exact five-phase accuracy separately from binary
crisis accuracy; never relabel five-phase metrics as four-class metrics.
Global/Somalia compact primary pooled = 2022–2026; original pooled retained as
a separately named role. Supported months, missing-month support and truth
definitions remain visible; the 2026 Somalia cohort is 1/0/0/904 by Jan–Apr.

Only finite source metrics are logged. Maintain separate NA/status/reason records
for undefined/empty/incomplete results; do not coerce to zero. Missing explanation
in a source is itself recorded, not invented. Record exact JSON/CSV cell locators
and original metric names. No new statistical calculation or bootstrap; any
display-only arithmetic must be explicitly identified and verified against saved
operands, and is unnecessary when saved differences exist.

Dataset descriptor binds keys AND truth AND cohort/label definition AND actual
support/period. Family-specific truth/cohort distinctions belong in names when
needed to ensure one name = one digest. Training descriptors describe the prepared
candidate pool and link exact per-fit keys; they do not falsely describe every
annual refit's actual rows as the entire pool. Launch Inputs describe the inference
population and forecast origin/target; population predictions are prediction
summaries, not evaluation scores. Do not generate future actual labels or metrics.

## Maintenance, idempotency and concurrency

Separate immutable source snapshot key from content fingerprint. Fingerprint
includes source inventory, vocabulary, extraction/import contract and source
provenance. Same key/different content fails before writes; unchanged complete
keys require full readback verification before no-op. Interrupted same-fingerprint
plans resume. Mark complete only after all metrics, artifacts, datasets, logged
models, registered versions and catalog projections verify.

Future training creates a new source snapshot and registered version; output-only
updates create a new detailed evaluation snapshot/projection that references the
existing unchanged model version. Do not create a phantom newly trained version
for a new plot or reevaluation. Preserve prior metric provenance when advancing
the latest dashboard projection; no silent overwriting immutable source records.
Agent maintenance adds explicit sources/mappings where needed, plans, verifies
inputs, backs up, applies, reads back, and records completion or pending failure.
Unsupported new formats fail with an actionable message; no automatic guessing.

Coordinate writes and backups with the existing shared store lock convention.
Use MLflow APIs for objects, not direct SQL editing. Snapshot existing reference
objects/metrics/tags/dataset associations/artifact hashes before live writes and
compare afterward. Store outputs in the existing service location but use an
IPCCH-specific plan/cache namespace so existing plans/journals do not collide.
Back up SQLite using its online backup API and preserve the matching artifacts;
restore-check on a separate scratch service/store, never port 5000. Retain backup.
Do not restore the whole live shared store blindly if others have since written;
stop writes and inspect the backup/current delta before any destructive repair.

## Frozen boundaries

Do not edit fitting scripts/helpers: their full file bytes are part of saved
fingerprints (origin_safe, compact_features, compact_launch, Somalia local and
2026 extension). Do not write inside existing result/report trees. AGENTS.md has
a pre-existing generated memory timestamp change and an old superseded PNG is
dirty; preserve them and do not attribute them to this task.

## Supervision

C0 reviews inventory/naming and baseline preservation evidence before integration
coding. C1 reviews code diff and offline/scratch checks before any live writes.
C2 reviews initial live result, artifact downloads, existing-store preservation,
repeat/no-op and resume evidence before final acceptance. These are supervisor
checkpoints, never Trellis audit jobs. Executor pauses at each boundary.
