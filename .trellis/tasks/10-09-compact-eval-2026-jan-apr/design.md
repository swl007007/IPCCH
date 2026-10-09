# Design: append 2026 fits without invalidating frozen historical artifacts

## State and change boundary

This design implements the user-confirmed requirements in `prd.md` and was explicitly approved for implementation on 2026-10-09. No extension artifact or fit existed at approval. Follow the fixed boundary below; record live execution state in `PROGRESS.md`.

The gap is in year-level orchestration and scoring: 2026 rows already exist, but frozen old masks/year lists exclude them. Keep the original input-loading gates and annual fitter byte-identical. Add one focused entrypoint, `scripts/modeling/run_compact_eval_2026_extension.py`, plus `tests/unit/test_compact_eval_2026_extension.py`. Runtime outputs and task evidence are separate artifacts; no new package, dependency, model abstraction or general year-configuration framework is needed.

Protected implementation files include `compact_features.FIT_CODE`, the existing SOM script, suite/verifiers, regional helpers, source builders and configs. No existing function/class/method is scheduled for editing. If an existing-symbol edit becomes necessary, first perform GitNexus upstream impact analysis, report callers/processes/risk and return to the coordinator before widening this boundary. Never monkeypatch `TARGET_YEARS`/`PERIODS` or bypass a parent gate.

## Existing boundaries and reusable functions

| Existing component | Use | Constraint |
|---|---|---|
| `runner.load_origin_inputs` / `load_compact_inputs` | Full frozen global parent validation and existing full data/targets/features | Original cohort/mask/hash must remain unchanged while these gates run |
| `runner.load_hyperparameters` | Existing fixed configs | No tuning or replacement |
| `runner.run_origin_batch` | Fit the requested year 2026 with inherited cutoffs, targets, weights and saved artifacts | Supply a separate validated extension mask and fingerprint after parent loading |
| `runner.verify_batch` | Complete fingerprint/hash resume check | Pass the original fingerprint for old batches and extension fingerprint for new ones |
| `osf` target/weight/classification/metric helpers | Preserve scientific semantics | Use explicit periods in the new coordinator; `TARGET_YEARS` stays four years |
| `regional_point_metrics` membership, support, pairing and delta helpers | Global regions and comparison contracts | Its old fixed-period loop cannot produce the new annual block; do not call it on five-year data expecting 2026 annual rows |
| Existing saved-prediction verifier metric path | Independent eight-metric replay | Keep undefined reasons, unrounded scores and exact class checks |
| Existing parent codebook contracts | Describe actually checked fitted features | Old/new identity and model counts must be explicit |

`run_origin_batch` computes cutoff from `year`, not `TARGET_YEARS`, and saves four boosters, prediction keys, weights and artifact hashes (`run_deep_feature_weight_decay_forecasting.py:1078-1149`). The existing localizer demonstrates safe post-gate mask/fingerprint adaptation (`run_somalia_local_compact_test.py:435-458`). Calling the old suite or `run_origin_safe` is unsuitable because its block plan/COMPLETE assembly is fixed to four years (`:1050-1057,1180-1205`).

## Explicit sources and namespaces

Use `ipcch.paths` for repository/source roots, while preserving the exact registered filesystem spelling in operational commands. The current repository is `/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/Google fund/Analysis/2.source_code/Step5_Geo_RF_trial/IPCCH`.

Parent inputs:

- `assembled_IPCCH/model_ready/compact_climate_weather_oracle_v1/compact_climate_weather_oracle_v1_manifest.json`.
- `assembled_IPCCH/model_ready/origin_safe_climate_idp_v1/origin_safe_climate_idp_v1_cohort_keys.csv`.
- `assembled_IPCCH/country_area_id_lookup.csv` and `data/reference/area_id_country_region_mapping.csv`.
- SOM original local manifest: `results/experiments/compact_climate_weather_oracle_v1_somalia_local/inputs/compact_climate_weather_oracle_v1_somalia_local_manifest.json`.

Original results roots are `results/experiments/compact_climate_weather_oracle_v1` and `.../compact_climate_weather_oracle_v1_somalia_local`. For each explicit root, the seven runs are `runs/<arm>/<H>m/`, with original `batches/<year>/`, published predictions and recorded metadata. Retain original references; no copying/refitting of old models.

New result versions are the two exact names in PRD R4. For each scope:

```text
results/experiments/<version>/
  inputs/extension_manifest.json
  inputs/approved_spec/                 # byte copies of approved task contracts
  runs/<arm>/<H>m/
    batches/2026/                     # only newly fitted year
    predictions/predictions_2022_2026.csv
    run_metadata.json                 # explicit sources_by_year, never invented old batches
  report/                             # global/regional or SOM CSVs, metadata and coverage
  verification/                       # verification summary and complete inventories
reports/<version>/
  report.md
  model_run_codebook/                  # actual codebook, expected-v-actual, run index
```

No caller-supplied arbitrary input versions, years, horizons, output roots or hyperparameter settings are needed. Scope is exactly `global` or `SOM`. Match existing CLI style with `--validate-only`, `--approve-training`, `--report`, `--verify`; require a selected scope and an explicit action. Validation has no output writes or fitting; report/verify never fit; training cannot overwrite unrelated or incomplete output. The implementation may organize these actions within this single file without creating an extra wrapper/module.

## Data flow

1. Load both fixed config identities and parent manifest; validate frozen parent code/runtime/contract/source/dataset/ledger identities using the unchanged loader. Reject drift before touching results. Recompute 2026 selections independently from the cohort and check each returned matrix against them.
2. For `global`, leave the inherited training-valid mask intact; for `SOM`, intersect it with canonical membership. Replace only the returned in-memory evaluation mask with valid 2026 January-April keys (and local membership for SOM). Do not change parent arrays in place: form a new mapping with new masks, preserving the gated parent fingerprint/payload.
3. Recompute the complete expected fitting set at each annual cutoff, targets, ages/weights and expected per-run evaluation key hash. Validate the counts in `expected_runs.csv`, native missingness and full paired baseline matrix equality before fitting.
4. Validate all original 2022-2025 artifacts for that scope and run. Rehash complete original inventories and batch records; require COMPLETE coverage and original fingerprint agreement, exact original selected keys/truth, normalized targets and complete fitting cutoff/scope/weights. Check published annual predictions against batch predictions using round-trip parsing. Preserve originals and their prior verification evidence.
5. During approved training, save the extension manifest, selected-key coverage and approved-contract copies. Bind the extension version, scope/model_scope, script SHA, parent fingerprints and manifest SHA, membership/region-map SHA, selected fitting/evaluation key hashes, parameters and runtime. Record old references separately. Specs are consumed from durable manifest-bound copies after task archival.
6. For each of seven runs, invoke unchanged `run_origin_batch` for 2026 sequentially, reusing only complete matching extension batches through `verify_batch`. Persist new batch artifacts exactly as the fitter emits them. H0 is not duplicated.
7. Concatenate checked original 2022-2025 annual predictions and new 2026 predictions in canonical key order into one explicit per-run five-year prediction file. Require complete/nonduplicated keys and exact preservation of original rows, including raw scores/classes. Combined metadata declares reused and newly fitted years and source fingerprints/paths/hashes by year.
8. Compute annual and explicitly filtered pooled metrics and paired differences; publish coverage, reports/codebooks and comparison metadata. Then independently verify saved predictions/metrics, new models and complete inventories. Mark accepted verification only after all required checks pass.

## Identity, completion and resume

The old FIT_CODE includes whole files, so a local change to their year handling would change old fingerprints even when fitting logic stayed the same (`compact_features.py:82-85,479-515`). The new standalone entrypoint avoids that conflict. Each new batch's extension fingerprint must bind its own masks/scope/script and the original gated parent, not pretend to be an original compact batch.

The extension manifest contains explicit old global/local source identities, unchanged configs/runtime, approved-spec copy hashes, new script hash, seven run schemas, cohort/coverage expectations and provenance. Approved contract copies are exactly `prd.md`, `design.md`, `implement.md`, `approval.md`, `expected_runs.csv` and `research/contracts.md`; the mutable progress ledger/task state is not a fingerprint input. A separate comparison metadata inventory identifies generated prediction/metric/report artifacts. Do not make a self-hash or live logfile part of its own inventory.

Refuse mismatched identities and nonempty partial batch directories lacking completion records; preserve diagnostics. A combined COMPLETE metadata record requires all four original years and a complete checked 2026 batch. Write completion only after the expected full artifact set is present and hashed. Report/verify revalidate identities and coverage without fitting. Verification failure remains failure with preserved diagnostics; neither a training COMPLETE marker nor a codebook is acceptance by itself.

Generated reports remain `verification_pending` until the full saved-artifact verification passes. On failure, retain unverified diagnostics/status rather than publishing a passed claim. Any final status/inventory refresh is reporting only and must leave fitted/prediction artifacts unchanged.

Capture protected old input/results/report/launch/code/config inventories before execution and compare afterward. Preserve the pre-existing unrelated `AGENTS.md` and superseded launch PNG modifications; do not attempt to clean or commit them as this task's work. Logs belong outside result/report inventories.

## Metric schema and output contract

Use `period` values `2022` through `2026`, `pooled_2022_2026` and `pooled_2022_2025`; metadata explicitly names the main pooled period and contributing years/months. Per scope/run/year grouping and eight-metric definitions follow PRD R5. Preserve existing metric, value/status/reason, paired-value and support columns, with model_scope and provenance in metadata.

Global report CSVs: `all_metrics_long.csv`, `global_metrics.csv`, `regional_metrics.csv`, `global_deltas.csv`, `regional_deltas.csv`, `undefined_reasons.csv`. SOM report CSVs: `som_metrics_long.csv`, `som_oracle_minus_baseline_deltas.csv`, `som_undefined_reasons.csv`. Both roots also publish `coverage_by_month.csv`, `comparison_metadata.json` and verification inventories/summary. Five annual blocks plus two pooled periods yield 3920 global/region absolute metric cells and 392 SOM cells. Keep zero-row region groups and side-specific undefined delta reasons.

Preserve global H0's single-arm presentation and SOM's inherited shared-H0 presentation (`run_somalia_local_compact_test.py:755-767`). Do not invent an oracle H0 fitted record. Keep raw differences in native units; an accuracy delta is not a percent change. Expanded pooled uses row-based weighting and includes only January-April 2026.

Each new report's three codebook/index CSVs follow the old version's conventions. Inspect actual fitted feature order for all 140 referenced boosters per scope, distinguish 112 reused from 28 new and include explicit model artifact sources/year coverage. Reuse verified original descriptions without preserving obsolete expected-only wording. No historical map/PNG/HTML product is added.

## Verification boundaries

- Old numerical replay need not be repeated across all 224 reused boosters; its accepted prior evidence remains pinned. Rehash originals, inspect all fitted schemas, validate full fitting/prediction lineage and independently recompute old metrics before reuse.
- New numerical replay covers all 56 new boosters and exact prediction keys/classes. Prediction tolerance is atol1e-6/rtol0; classes must be exact even if a score passes numeric tolerance.
- Independent metric/delta replay covers all years, both pooled periods and global regions. Metric tolerance is atol1e-12, with exactly matching undefined masks/status/reasons and integer support.
- Focused tests exercise actual new boundaries: a 2026 block after a valid old parent gate, H0/H3/H6/H12 cutoffs, mixed-country fitting/evaluation, two pooled masks, empty/single-row metrics, honest import identity, no-write validation and stale/incomplete resume rejection.

This task does not replay upstream label publication vintages or reconstruct feature builders. Parent gates and already verified frozen matrices remain the feature contract. Existing source-native weather NaNs remain NaNs. Acceptance depends on the approved A1-A8 evidence, not new task-checkbox states.
