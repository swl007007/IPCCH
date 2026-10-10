# Checkpoint C0 — frozen import plan (executor report)

Executor: Claude Opus 5.5 (1M), session 074d329d. Date 2026-10-09 (UTC 2026-10-10). No live
MLflow writes, no integration code, no source/result/report/reference-repo edits, no audit.
All tools under `c0/tools/` are read-only over sources and write only inside `c0/`.

## 0. Identities

| Item | Value |
|---|---|
| IPCCH HEAD / branch | `b7fca5c8f7d39fd8eea83257ba3134521b24414d` / `task/ipcch-mlflow-sep-oct-registration` |
| Pre-existing dirty (preserved, not task work) | ` M` superseded launch PNG; ` M AGENTS.md` (generated memory timestamp) — `c0/git-status-at-c0.txt` |
| Supervisor file | `supervisor-checkpoints.md` untouched (sha256 `6649f268…bdce` at read) |
| Reference repo | Food_Crisis_Cluster HEAD `38adbda938d8346bd14b89c06d3296e467d23764` (= design.md), clean for `IPCCHMLflow/` |
| MLflow service | `http://127.0.0.1:5000` health OK, version 3.17.0; `mlflow server --workers 1`, sqlite `~/.local/share/ipcch-mlflow/mlflow.db`, proxied artifacts |
| Runtime | `/home/swl007007/.venvs/ipcch-mlflow` (MLflow 3.17.0, Python 3.12.3); model venv `ipcch-geo` not touched |

## 1. Shared-store read-only baseline (`c0/store-baseline.json`, `.artifacts.json`)

Captured 2026-10-09T23:57:57Z via SQLite `mode=ro` + tracking search API (no writes).

- Experiments: `Default` (0 runs), `IPCCH - detailed runs` (126 runs), `IPCCH - dashboard` (136 runs).
- 68 registered models / 100 model versions; **no** existing `IPCCH Forecasting*` experiment or model.
- `db_logical_digest` (runs, tags, latest metrics, params, model versions) =
  `a405574936806624e910584c573df65e4b194ce1eea15c5050a868c405444ad1`.
- Artifacts: 2,223 files, 8,338,938,473 bytes, manifest sha256 `2e0a5a98…8141e` (per-file sha256 saved).
- Store side dirs owned by FCC: `plans/`, `cache/hashes.json`, `dashboard/`, `logs/`, `staging/`, `import.lock`
  (flock used by FCC `import_runs.py` and `backup_restore.py`). Existing backups in `~/ipcch-mlflow-backups/`.
- **Limitation (supervisor review item 4):** this digest covers selected fields and `latest_metrics` over all
  rows, so it is a C0 reference point only. Counts, or a whole-store digest taken after the addition, cannot
  prove preservation. C1/C2 plan: take a fresh verified backup, then compare **every pre-existing object
  keyed by its pre-existing ID** between the backup and the live store:
  - runs/experiments and all tags/params;
  - the **full `metrics` history**, not only latest;
  - datasets, `inputs`/`input_tags`, logged models with their params/tags/metrics;
  - registered models and versions with tags/aliases;
  - per-file artifact sha256.

  New rows are allowed only if they belong to the two `IPCCH Forecasting` experiments, the `IPCCH Forecasting*`
  registered models, or their logged models/datasets. Any changed or missing pre-existing row fails.

## 2. Source inventory (`c0/source_hashes.csv`, `c0/source_inventory.csv`)

3,626 files, 3,967,875,573 bytes, all sha256-hashed (`source_hashes.csv` sha256 `df416ec5…86cf`).
Exactly the 12 `sources.csv` roots; no recursive discovery outside them.

| source_key | files | MB | booster files | distinct booster bytes | saved boosters (own final fits) | detailed children | model versions | fitting-date evidence (not mtime) |
|---|---|---|---|---|---|---|---|---|
| somalia_oracle_v1 | 336 | 286.1 | 300 | 300 | 300 | 24 | 15 | manifest git HEAD `f576e69` (committed 2026-09-24T19:59-04:00) + task 09-24 evidence; run 3,614 s |
| somalia_oracle_v2_q3 | 427 | 285.5 | 400 | 384 | 400 | 44 | 23 | HEAD `d75378d` (2026-09-25T15:20-04:00) + task 09-25 evidence |
| somalia_oracle_v3_validity | 558 | 288.7 | 524 | 296 | 524 | 48 | 24 | HEAD `1f3bfce` (2026-09-25T23:47-04:00) + task 09-25 evidence |
| somalia_oracle_v4_calibrated_d | 672 | 595.2 | 626 | 402 | 626 | 8 | 8 | HEAD `a787257` (2026-10-01T07:10-04:00) + task 09-30 evidence; run 5,301 s |
| origin_safe_climate_idp_v1 | 469 | 807.3 | 192 | 192 | 192 | 12 | 12 | `logs/suite_ledger.jsonl` 12 COMPLETE, 2026-10-06T22:00:58Z–22:59:41Z |
| origin_safe_weather_oracle_v1 | 250 | 429.3 | 96 | 96 | 96 | 10 | 6 | `logs/suite_ledger.jsonl` 6 COMPLETE (+1 rc=-9 retried), 2026-10-07T20:04–20:38Z |
| compact_global_original | 295 | 619.1 | 112 | 112 | 112 | 8 | 7 | `logs/suite_ledger.jsonl` 7 COMPLETE (+pilot PARTIAL), 2026-10-09T02:26–02:42Z |
| compact_somalia_original | 256 | 143.1 | 112 | 112 | 112 | 8 | 7 | task 10-09 somalia-local acceptance `accepted_utc 2026-10-09T19:03:26Z` (no in-root ledger; see U7) |
| compact_global_2026_extension | 84 | 192.2 | 28 | 28 | 28 | 8 | 7 | task 10-09 final-execution-evidence: `--scope global --approve-training` rc 0 |
| compact_somalia_2026_extension | 82 | 69.0 | 28 | 28 | 28 | 8 | 7 | same, `--scope SOM --approve-training` rc 0 |
| compact_global_launch | 97 | 176.4 | 20 | 20 | 20 | 6 | 5 | task 10-08 compact-cds-launch acceptance (A1–A9 2026-10-09); `logs/fits_remaining*` (see U7) |
| compact_somalia_launch | 100 | 75.9 | 20 | 20 | 20 | 6 | 5 | task 10-09 somalia-local acceptance 2026-10-09T19:03:26Z |
| **total** | **3,626** | **3,967.9** | **2,458** | **1,938** | **2,458** | **190** | **126** | all fits 2026-09-24 … 2026-10-09 → eligible |

### Booster files vs fitted job/recipe units

| source | fitted job/recipe units | boosters per unit | booster files |
|---|---|---|---|
| somalia_oracle_v1 | 75 (A 20, B 20, C 15, D 20 origin-jobs) | 4 (q2–q5) | 300 |
| somalia_oracle_v2_q3 | 95 (A 20, B 20, C 15, D_direct 20, D_residual 20) | 4, +q3_residual_delta in 20 residual units | 400 |
| somalia_oracle_v3_validity | 120 (20 jobs × 2 label settings × 3 views) | 4, +q3_residual_delta in 44 | 524 |
| somalia_oracle_v4_calibrated_d | 142 (outer jobs across both settings) | 4, +q3_residual_delta in 58 | 626 |
| origin_safe_climate_idp_v1 | 48 annual batches (3 arms × 4 leads × 4 years) | 4 phase regressors | 192 |
| origin_safe_weather_oracle_v1 | 24 (2 arms × 3 leads × 4 years) | 4 | 96 |
| compact global / Somalia original | 28 + 28 (7 runs × 4 years) | 4 | 112 + 112 |
| compact global / Somalia extension | 7 + 7 (7 runs × 2026) | 4 | 28 + 28 |
| compact global / Somalia launch | 5 + 5 | 4 | 20 + 20 |
| **total** | **584 fitted units** | | **2,458** |

### Distinct fits vs duplicate bytes vs reused components

- **Saved boosters = 2,458 = booster files, produced by 584 fitted job/recipe units.** Every `.ubj` is written by a final-fit `save_model` call of its own unit
  (`run_somalia_q3_optimization.py:97-115,283`, `run_somalia_validity_augmentation.py:217-233`,
  `run_somalia_v4_calibrated_d.py:409-424`, batch writers for modern runs). OOF/inner-fold fits are never saved
  and are not counted as registered members.
- **Duplicate bytes (520 files)** are deterministic re-fits of identical recipe/pool, not copies:
  v2 16 (D_direct and D_residual sharing bundle X1 within a job); v3 228 (direct/residual/selected q2–q5
  components with the same bundle); v4 224 (identical pools/recipes across jobs). Physical dedup is allowed in
  storage; each member keeps its own path/job identity in `members.json`.
- **Explicit aliases/reuse (no fit, counted separately; `c0/model_members.csv` member_kind):**
  - `alias_h0_clone_of_B` 40 rows: v1 inventory lists the B 0-month files twice for C (20 rows), and v2 C 0-month
    reuses B (20 rows). The C 0-month view gets no registered model.
  - `alias_selected_recipe` 100: v2 `share_history_selected` = D_residual members (selected recipe is residual in
    2025 and 2026, `selection/selected_recipes.csv`; `reuse_source` at `run_somalia_q3_optimization.py:86-94`).
    Registered as its own version with 0 new fits (it is a distinct decision rule).
  - `alias_shared_h0_baseline` 80: compact historical `weather_oracle` 0-month (4 sources) and launch `cds_weather`
    0-month (2 sources) reuse the baseline 0-month fit. View only, no registered model.
  - `reused_from_original_snapshot` 224: compact extension versions reference the 2022–2025 original members
    (112 per scope); only the 28 new 2026 boosters per scope are new fits.
  - Weather-oracle `reference_safe_ipc_history_idp` rows (4 views) are metric-only and link to the origin-safe
    climate `safe_ipc_history_idp` versions (`verify_origin_safe_weather_oracle.py:386-392`); no second fit.

## 3. Expected object counts (frozen proposal; `c0/expected_counts.json`, `c0/views_counts.json`)

| Level | Count | Basis |
|---|---|---|
| Source roots / detailed parent runs | 12 / 12 | one parent per source snapshot (v3 and v4 parents each serve two label-setting families) |
| Detailed child runs | **190** | 126 fitted views + 8 H0 alias views + 52 metric-only baselines/references + 4 cross-source reference views (`c0/views_expected.csv`) |
| Logical families | 12 | `naming-preview.md` §1 |
| Fitted job/recipe units | 584 | each = one final fit set of 4 (or 5) boosters; see §2 |
| Registered models (family × arm × lead) | **112** | v1 15, v2 23, v3 12+12, v4 4+4, origin-safe climate 12, weather 6, compact global 7, compact Somalia 7, launch 5+5 |
| Model versions | **126** | 112 + 14 compact extension versions (version 1 = original, version 2 = extended, per family/arm/lead) |
| External LoggedModels | 126 | one per version |
| Version member references | 2,782 | 2,458 own fits + 224 reused original members + 100 selected-recipe aliases (`c0/model_versions_expected.csv`) |
| Required physical booster members | 2,458 files (1,938 distinct byte contents) | plus per-batch/record/schema/fit-key/calibration members listed in `source_inventory.csv` role `model_recipe_member` (398) and `fit_selection_calibration` (38) |
| Dashboard rows (latest snapshot) | **174** | 190 children minus the 16 superseded compact-original children (original rows stay browsable in detailed runs and as model version 1) |
| Evaluation dataset name candidates | ≤ 412 | unique (truth group, lead, period, cohort) from saved metric rows; no key maps to two n. Final count = distinct digests after keys+truth hashing in C1 (U4) |
| Launch inference descriptors | 10 | 2 scopes × 5 fitted runs (H0 alias reuses the baseline H0 descriptor) |
| Training-pool descriptors | 45 (+ ≤ 8) | one per family × fitted lead; extension pools only if their prepared candidate-pool digest differs (U10) |

Not equal: 2,458 boosters ≠ 584 fitted units ≠ 126 versions ≠ 112 registered models ≠ 190 children.

**Why 112 vs 126, and which views have no registered model:**
- 126 versions = 112 registered models + 14 second versions: the 7 compact global and 7 compact Somalia-local
  historical models each have version 1 (original 2022–2025) and version 2 (extended 2022–2026).
- The 8 alias views with **no registered model** (they link to the baseline/B version and say so):
  - Somalia oracle information `weather_oracle | 0-month` → `seasonal_climate | 0-month`.
  - Somalia q3 optimization `weather_oracle | 0-month` → `seasonal_climate | 0-month`.
  - compact global original and extended `weather_oracle | 0-month` → `baseline | 0-month` of the same snapshot.
  - compact Somalia-local original and extended `weather_oracle | 0-month` → `baseline | 0-month`.
  - global and Somalia-local launch `cds_weather | 0-month` → `baseline | 0-month`.
- Also with no registered model: the 52 metric-only baselines/references (persistence, always_crisis,
  share_persistence, `reference_*` raw/isotonic) and the 4 weather-oracle `reference_safe_ipc_history_idp`
  views, which link to the origin-safe climate version.
- **With** a registered model but 0 new fits: v2 `share_history_selected` (4 leads; members = D_residual).
- 190 children = 126 fitted views (one per version) + 8 + 52 + 4.

## 4. Metric / cohort map (`c0/metric_map.csv`)

1,255 rows (file × column × long-format metric), **0 unresolved**; every selected metric file is listed
explicitly (no globbing at import time). Finite cells / NA cells per source are in the table produced by
`build_c0.py`; NA values are carried with source status/reason, never logged as 0.

Key decisions:
- Compact extension 6-month example, global and Somalia-local alike (supervisor correction): 2026 fit origin and label
  cutoff 2025-07, 308 inputs. Concrete-lead text states the actual per-lead count and cutoff from
  `run_metadata.json`/`batch_record.json` (0-month 2025-12/296; 3-month 2025-10/296|302;
  12-month 2025-01/296|308), never a generic range.
- Modern 8-metric schema → `five_class.accuracy`, `binary.accuracy|precision|recall|f2`, `share_phase3plus_r2|mae`,
  `five_class.ordinal_mae`, `n_rows` (+ `_status`/`_reason` → `view/na.json`).
- Somalia v1 `accuracy` = exact five-class (`src/ipcch/somalia_oracle/evaluation.py:63-65`) → `five_class.accuracy`;
  binary counts `binary.count.tp|fp|fn|tn`; `r2_q3` → `share_phase3plus_r2`.
- Somalia v2–v4 keep raw vs final (calibrated) share families distinct: `share_phase3plus_raw.*`,
  `share_phase3plus_final.*`; AUC pooled vs within-month distinct: `binary.auc_pooled_raw|final`,
  `binary.auc_within_month_raw|final`; legacy phase-binary metrics → `legacy_phase_binary.*` (not merged with
  `binary.*`); `legacy_phase_accuracy` → `five_class.accuracy`.
- Contrasts and intervals only as saved: `delta.<A>_minus_<B>.<metric>[.ci_low|.ci_high|.draws_*]`. `oracle_value`
  / `baseline_value` columns in delta files are cross-checked equal to the arm rows, not re-logged.
- Launch: `prediction_summary.<scope>.(count|share)_(raw|effective)_(phase1..5|p3plus|p4plus)`, population,
  `n_capped_areas`; paired differences `paired_difference.cds_weather_minus_baseline.*`. Never called accuracy.
- Periods: Somalia v1–v3 `year_2025` / `year_2026` only (lead-specific target months); v4 `pooled` +
  `year_2022..2026` with actual years per lead (3/6-month pooled is 2022–2025 because 2026 is empty);
  origin-safe/compact original `primary` = pooled 2022–2025; compact extension `primary` = pooled 2022–2026
  (Jan–Apr), `original` = pooled 2022–2025, `year_2026` partial (Somalia-local monthly 1/0/0/904).
- Cohorts: `all_scored`, `primary`, `wider_labeled`, `phase_persistence_subset` (v1 `persistence_subset`),
  `share_history_subset`, `region_<name>_global_model`. Region labels are not invented. The mapping CSV
  `data/reference/area_id_country_region_mapping.csv` holds numeric `region` only. Names come from the saved
  extension report's `region_name` column: 0 Asia, 1 East Africa, 2 West Africa, 3 Southern Africa,
  4 Central Africa, 5 Latin America, 6 Mali, 7 Somalia, 8 Palestine. The weather-oracle region-3 files are
  labelled Southern Africa per `scripts/postprocessing/evaluate_region3_saved_predictions.py:1,279`. C1
  adds a test that the naming table equals these saved/code labels. Region scores of global models are
  never Somalia-local.
- v4 per-slot status (from `annual_metrics.csv`/`pooled_metrics.csv`): augmented 6-month 2023 **incomplete**
  (696/2013 missing) and pooled incomplete; 2026 3-/6-month **empty_cohort** in both settings (4 slots).
- v1 diagnostics (`diagnostics/*.csv`, incl. method `LEAKY_test_perphase_macro_f1`) → detailed D child only,
  `diagnostic.*` keys, flagged diagnostic/leaky, excluded from dashboard; no new registered model (U8).

## 5. Exclusions and mixed content

- No source root belongs to Nigeria Sep18 (`results/experiments/deep_feature_weight_decay_forecasting/*nigeria*`)
  or `climate2015_v1`; they get no MLflow object. Nigerian rows/country summaries inside allowed global models
  (e.g. launch `country_population_summary.csv`) are kept.
- Content scan (`excluded_family_mentions` column): 60 in-root files mention `climate2015`. All sampled
  contexts are **input lineage**, not results: code hash of `src/ipcch/climate2015_features.py` in
  run metadata/launch records, feature-source labels in `source_support_*`/`feature_classification_*`, codebook
  recipe citations. Allowed as lineage; C1 adds an automated allowlist check of these patterns.
- Result leakage exists only **outside** the roots: `reports/origin_safe_climate_idp_v1/report.md:132-171`
  ("Context only: earlier annual climate2015_v1 runs"). Not uploaded; the parent uses an included-only rendered
  description. Other cited reports (`reports/*/model_run_codebook/*.csv`) mention climate2015 only as lineage.
- File-level exclusions: 19 `compact_climate_weather_oracle_v1/superseded_build1/**` (superseded pre-fit
  input build, no model) and 6 `*.pid` files — listed with sha256 in an excluded manifest.

## 6. Proposed smallest code layout (C1; nothing written yet)

```
IPCCHMLflow/                      # standalone, this repo; adapted from FCC 38adbda with provenance notes
  README.md                       # reading guide, filters, maintenance sequence (literal commands)
  sources.json                    # the 12 snapshots: root, format, explicit metric files, member rules, cited reports, policy
  naming.py                       # sole vocabulary: families, arms, leads, periods, cohorts, leaves, descriptions; unknown -> error
  extract.py                      # explicit extractors: somalia_v1, somalia_v2v3, somalia_v4, origin_safe_runs,
                                  #   weather_region3, compact_long, launch_population; members + aliases
  catalog.py                      # plan / import / verify (detailed runs, artifacts, external models, registered
                                  #   versions, datasets, dashboard projection), fingerprints, journal, resume
  store.py                        # shared import.lock (same flock as FCC), online SQLite backup, scratch restore-check
                                  #   (port != 5000), read-only before/after store comparison
tests/unit/test_ipcch_mlflow_naming.py, test_ipcch_mlflow_extract.py, test_ipcch_mlflow_catalog.py
.trellis/spec/backend/local-mlflow-registration.md (+ backend index link); AGENTS.md / CLAUDE.md pointers
```

CLI (one entry, independent stages): `$PY IPCCHMLflow/catalog.py plan|import|verify|dashboard-plan|dashboard-apply|dashboard-verify`,
`$PY IPCCHMLflow/store.py baseline|backup|restore-check`. IPCCH-specific namespace inside the existing store:
`~/.local/share/ipcch-mlflow/ipcch-forecasting/{plans,cache,journal,logs}`; FCC `plans/`, `cache/`, `dashboard/`
untouched. Service start/stop stays with FCC `manage.sh` (status read-only here). Logs never under results/ or reports/.

## 7. Unresolved — supervisor decisions requested

| ID | Issue | Proposal |
|---|---|---|
| U1 | **Resolved by supervisor:** `zz_prov.*`, readable tags created first (reference README:117-120, import spec:134-137; task prd/design/naming updated by supervisor). | Adopted. |
| U2 | Alias policy | H0 C (v1/v2) and H0 weather_oracle/cds_weather: alias views only, no registered model. v2 share_history_selected: registered version of D_residual members (0 fits). |
| U3 | v3 baselines (persistence/always_crisis) have branch `-`/`all` | Duplicate the metric-only views into both validity families (same dataset digest); alternative: observed family only. |
| U4 | Dataset identity | ≤ 412 candidate names; C1 hashes keys+truth from saved predictions. If origin-safe and compact global cohorts differ, add a family qualifier to the name so one name = one digest. |
| U5 | 8 files without a role rule: v4 `alert_map_2026_04/*` (2), origin-safe `timing_audit/*` (3), weather `reference_preflight/*` (3) | Archive as ledgers/diagnostics; alert-map values not imported as metrics (plot data). |
| U6 | v1 evidence cites run commit `a0c792e` while manifest records HEAD `f576e69` | Record both in `zz_prov.*`; manifest is the run record. No eligibility impact. |
| U7 | Somalia-local historical/launch and global launch roots have no in-root minute-level fit ledger | Fitting date stated from task execution/acceptance records (2026-10-08/09); no mtime use. |
| U8 | v1 diagnostics incl. LEAKY method | Detailed D child `diagnostic.*`, labelled leaky, excluded from dashboard; calibrated-D postprocessing not registered. |
| U9 | Accepted conclusions per parent | C1 quotes verbatim from source closures; where none, the description says none is recorded. |
| U10 | Training-pool descriptors for compact extensions | Separate descriptor only if the extension's candidate pool digest differs from the original. |
| U11 | Cited reports outside roots | Upload codebooks/report CSVs only by explicit path; never `reports/origin_safe_climate_idp_v1/report.md`. |
| U12 | Existing `IPCCH - dashboard`/`IPCCH GeoXGB …` names share the `IPCCH` prefix | No collision (`IPCCH Forecasting` prefix verified absent); README filters use the full prefix. |

## 8. Artifact index (all under `.trellis/tasks/10-09-ipcch-mlflow-sep-oct-registration/c0/`)

`C0-report.md` (this), `naming-preview.md`, `store-baseline.json` + `.artifacts.json`, `source_hashes.csv`,
`source_inventory.csv`, `model_members.csv`, `model_versions_expected.csv`, `views_expected.csv`,
`eval_dataset_candidates.csv`, `metric_map.csv`, `expected_counts.json`, `views_counts.json`,
`git-status-at-c0.txt`, `tools/{store_baseline,hash_sources,build_c0,views_c0}.py`.
Reproduce: `python3 c0/tools/hash_sources.py . sources.csv OUT.csv`; `python3 c0/tools/build_c0.py . c0/source_hashes.csv c0`;
`python3 c0/tools/views_c0.py . c0`; `$PY c0/tools/store_baseline.py c0/store-baseline.json`.
