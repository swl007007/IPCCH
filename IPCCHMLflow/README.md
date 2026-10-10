# IPCCH Forecasting in the local MLflow store

Browsable catalog of IPCCH historical and launch models fitted in September–October 2026, in the
shared local MLflow service (the same service as Food_Crisis_Cluster's IPCCH catalog). It imports
saved metrics, datasets (keys + truth), recipes and weight bundles; nothing is retrained, rescored or
loaded. MLflow times are registration times, not fit times.

| Item | Value |
|---|---|
| URL | http://localhost:5000 (127.0.0.1 only; started with FCC `IPCCHMLflow/manage.sh start`); dashboard http://localhost:5000/#/experiments/4, detailed runs http://localhost:5000/#/experiments/3 (IDs as registered 2026-10-10) |
| Python | `/home/swl007007/.venvs/ipcch-mlflow/bin/python` (MLflow 3.17.0) |
| Store | `/home/swl007007/.local/share/ipcch-mlflow/`; this catalog's plans/cache/staging under `ipcch-forecasting/` |
| Sources | `sources.json` (12 explicit snapshots, cited files with SHA256, exclusions, frozen counts) |
| Vocabulary | `naming.py` (every name, tag and description; unknown identifiers stop the plan) |

## Reading guide

- **`IPCCH Forecasting - dashboard`**: start here. One row per family × arm × lead for the latest snapshot
  (174 rows). Names read `<family> | <arm> | <N>-month`.
- **`IPCCH Forecasting - detailed runs`**: one parent per source snapshot (12) with `models.tar`
  (weights + recipe members), `source.tar` (metrics, ledgers, predictions, logs, cited reports) and
  `manifests/`; one child per family × arm × lead (190) with every saved value (`view/evaluation_view.json`
  maps each key to file/row/column), `view/na.json` (undefined values + source reasons), `view/datasets.json`
  and, for model views, `members.json`.
- **Models**: 112 registered models `IPCCH Forecasting <family> | <arm> | <N>-month`, 126 versions. A version
  is an immutable source snapshot (compact global/Somalia-local historical models have version 1 =
  original 2022–2025 and version 2 = extended 2022–2026, which reuses the 2022–2025 weights). Versions are
  external descriptors: weights download from the parent run's `models.tar` (see `members.json`); there is no
  prediction wrapper.

Vocabulary: `lead_months` tag `00|03|06|12`; `model_scope` `global|somalia_local`; `stage`
`historical|launch`; `label_setting` `observed|training_augmented|role_augmented`; `view_kind`
`fitted|alias|reference|metric_only|evaluation_revision`; `source_status` is the source's scientific status per
slot (never import success). Metric keys `<period_role>.<cohort>.<metric>`: `five_class.*` (exact five
phases), `binary.*` (phase 3+ vs 1–2; Somalia crisis truth = reported phase ≥ 3), `share_phase3plus_*`
(Somalia `share_phase3plus_raw.*` vs `_final.*` = calibrated), saved contrasts `delta.<A>_minus_<B>.*`, launch
`prediction_summary.*` / `paired_difference.*` (predictions, not accuracy). Region cohorts
`region_<name>_global_model` are scores of a global model on a region's areas, not local fits.

Comparability: compare values only on the same evaluation dataset (run Inputs; one name = one digest of
keys + truth + definition). 2026 compact support is January–April only (Somalia-local 1/0/0/904 rows).
Weather oracles use realized future weather. Somalia v4 augmented 2023 6-month and its pooled value are
incomplete; four 2026 3/6-month v4 slots are empty. `0-month` weather-oracle / CDS views reuse the baseline
0-month fit (alias, no own registered model). Filters: `tags.lead_months = '06'`, `tags.family =
'compact_climate_global'`, `tags.stage = 'launch'`, `tags.model_scope = 'somalia_local'`.

Lineage limits (disclosed, not gates): fit dates come from run ledgers, recorded commits or task acceptance
records; some snapshots have no minute-level fit timestamp. Source audit debt/waivers are quoted in each
status text; no audit pass is claimed.

## Commands

```bash
PY=/home/swl007007/.venvs/ipcch-mlflow/bin/python
U=http://127.0.0.1:5000
$PY IPCCHMLflow/catalog.py plan                                   # read-only; hashes, extracts, checks counts
$PY IPCCHMLflow/store.py backup --dest ~/ipcch-mlflow-backups/$(date +%Y%m%d-%H%M)-ipcch-forecasting
$PY IPCCHMLflow/store.py restore-check --backup BACKUP --dest /tmp/ipcch-fc-restore --port 5091
$PY IPCCHMLflow/store.py snapshot --out BEFORE.json                 # complete pre-existing object state
$PY IPCCHMLflow/catalog.py import --tracking-uri $U --live          # serial; resumable; repeat = verified no-op
$PY IPCCHMLflow/catalog.py verify --tracking-uri $U --live          # deep readback incl. tar members
$PY IPCCHMLflow/catalog.py dashboard --tracking-uri $U --live       # latest-snapshot rows; unchanged = 0 writes
$PY IPCCHMLflow/catalog.py dashboard-verify --tracking-uri $U --live
$PY IPCCHMLflow/store.py compare --before BEFORE.json --out COMPARE.json   # old rows byte-identical, new rows ours
# (only allowed change to an old row: soft deletion of a superseded IPCCH Forecasting dashboard row)
```

`--live` is required for port 5000; without it the CLI refuses. Writers take the shared `import.lock`.
A changed source, vocabulary or importer changes the snapshot fingerprint and `import` stops before any
write. Interrupted imports resume (same fingerprint) without duplicates.

## Maintenance after new training or result changes (agents)

1. **New fit (training/retraining)**: add a new source entry to `sources.json` with a new `source_key`
   (and `extends`/`supersedes` if it continues a family); add vocabulary in `naming.py` and, for a new file
   format, an explicit extractor in `extract.py` with a fixture test. Then plan → backup → snapshot → import →
   verify → dashboard → dashboard-verify → compare. Update `expected` counts in `sources.json`.
2. **Evaluation-only update (same weights, new results/reports)**: set `"frozen": true` on every imported
   snapshot of that family whose files were rewritten (its stored plan becomes authoritative) and add a new entry
   with `"revision_of": <the FITTED snapshot that owns the versions>` and `"supersedes": <the snapshot currently
   on the dashboard>`. Example: first update of `compact_global_2026_extension` →
   `{"source_key": "compact_global_2026_extension_rev1", "revision_of": "compact_global_2026_extension",
   "supersedes": "compact_global_2026_extension", ...}`; a second update → `_rev2` with the same
   `revision_of: "compact_global_2026_extension"` and `supersedes: "compact_global_2026_extension_rev1"` (never
   `revision_of` a revision: revisions own no versions). Planning stops unless every model member is
   byte-identical to the fitted version;
   the new detailed runs reference the existing registered versions (no new version), and the dashboard
   retires the old rows (soft delete) after the new ones verify. Old detailed snapshots are never modified.
3. On failure: record the command, return code and message in the task/PROGRESS notes; rerun the same
   command to resume. Do not edit SQL, rebuild the shared store, or rename objects by hand.

Excluded families stay excluded (Nigeria Sep18 `nigeria_weather_land*`/`nigeria_identifier*` and
`climate2015_v1`); uploadable text is scanned for them. Models fitted before September 2026 are not added.

## Tests

```bash
PYTHONPATH=tests/unit:IPCCHMLflow $PY -m pytest tests/unit/test_ipcch_mlflow_naming_extract.py tests/unit/test_ipcch_mlflow_catalog.py -q
```

The catalog test starts its own scratch server on a free port (never 5000).
