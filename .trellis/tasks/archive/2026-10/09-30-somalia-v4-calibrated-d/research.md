# Somalia v4 planning evidence

Date: 2026-09-30. Read-only research; no model fits, feature regeneration, raw writes or lifecycle starts. Validation status for v4 implementation: Not Executed. Facts below distinguish current bounded source checks from statements in the existing source audit.

## Authoritative baseline read by the primary agent

Root: `.trellis/tasks/archive/2026-09/`.

- `09-25-somalia-validity-label-augmentation/prd.md:11-14`: two training-label settings, common outer cohort, q3-first inheritance. `:34-42`: authority, histories, source purges, availability, duration weights, overlap, branch separation and distinct-round/whole-block decisions. `:71-76`: final round-level mapping, no added 2025/2026 tests, recorded spec approval.
- Its `design.md:16` specifies supervised2022-24/test2025 and supervised2023-25/test2026; `:42-56` availability and per-context isolation; `:60-74` weighting, D/calibration/search and rounds; `:86-92` metrics, matched cohorts, area bootstrap and evidence.
- Its `implement.md:7-16` records concrete raw ledger, monthly feature recovery, source families, pools, rounds, search and reporting. `:24` identifies v3 results/reports roots.
- Its `grill.md:29-35` explains final G3 round-start linkage and excluded projection/spillover records.
- `09-25-somalia-auc-r2-optimization/design.md:20-29,48-78` specifies D-direct/residual, fallback, none/shift/isotonic, strict RMSE selection and the approved ancillary later-recipe-label exception.
- `09-24-somalia-flood-food-crisis/prd.md:49-57` names old seasonal source and 14 predictor fields; its `design.md:43-47` specifies actual-date latest-season join and incomplete-window handling. Other inherited contracts include normalization, realized weather and rich history.

The primary agent read these foundational PRD/design/plan/grill files in full. G8 now supersedes reuse of v3's common outer cohort, matched comparison and paired bootstrap: v4 evaluates original-only and validity-expanded scenarios separately. The baseline facts above remain historical evidence, not current v4 requirements. Historical text recording approval is not proof of a current accepted audit. HEAD at initial inspection was `99c6a3f`; its subject records a user-waived validity-task close audit. Do not call the historical v3 audit passed on this basis.

## Current growing-season source checks

Directory: `/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/IPCCH_shared_folder`.

| Source | Current SHA-256 | Bytes | Rows / columns |
|---|---|---:|---|
| `climate_2015_2026_MODELING_READY.csv` | `f024a66c8979fb4a8c66fba1f04e7e69355fa75b499793d29001a146d8c2958e` | 186792349 | 149448 / 92 |
| `climate_2022_2026_FINAL_MODEL_READY_V2.csv` | `fda5f0a0605d4fe536b69740b5c498d435a0194cfb12c6fbeba6a7c023a60ad3` | 83302226 | 62270 / 123 |

Default source remains old V2 (`src/ipcch/somalia_oracle/pipeline.py:45,68`); the v3 runner supports an explicit override (`scripts/modeling/run_somalia_validity_augmentation.py:46-47,77`). Saved v3 `manifest.json:43-45` agrees with the old source hash. No code change is needed to decide the new source in the plan.

One read-only scout streamed both CSVs and recalculated both hashes: unique `(admin_code,season_year,season)` keys; 6227 IDs; `s1/s2`; 12454 rows per source year. New years 2015-2026, old years 2022-2026. All 14 required seasonal columns exist in the new source.

Lookup: `Analysis/1.Source Data/assembled_IPCCH/country_area_id_lookup.csv`, `iso3=SOM`: 905 IDs. Both sources cover all 905, with 1810 rows per Somalia year. This is source coverage, not supervised outcome coverage.

The new CSV removes 31 QA columns relative to old V2. Its header retains actual dates, calendar validity, available window and recalculated duration. A cross-year sample begins 2014-11-25 and ends 2015-05-01 despite `season_year=2015`; actual dates must drive the join.

The primary read `audit_2015_2026_report.md` in full. Source-audit statements not independently rerun here: `:14-18` hidden QA exclusions, 2025 source-composition discontinuity and early-year source disagreement; `:38-43` unified export cutoff 2026-09-01; `:204-212` 4968 partial 2026 windows; `:244-248` upstream generation, climatology, spatial weighting and release-time provenance not verified. This v4 plan inherits 14-mean-only predictors and complete-season checks, without authorizing upstream repairs or declaring those audit gaps resolved.

## Current validity evidence and source limitations

- Config `configs/somalia_validity_augmentation.json:4-8` points to `Step0_Initialization_and_construct_Scaffold/curl_new_data/outputs/areas_combined_2026-05-15.geojson`, recorded hash `f5418154a0aafd8d353fb0ce1f379ba5f95cad212725d4961bc90d5d52016214`, SO/A/C, augmentation years 2022-2026, excluding 2025-07. Snapshot hash was not recalculated in this turn.
- Raw input recorded by v3 `manifest.json:35-37`: `Analysis/1.Source Data/assembled_IPCCH/raw/IPCCH_2026_completed.csv`.
- Existing full monthly deep-feature artifact is `Analysis/1.Source Data/assembled_IPCCH/features/forecasting_subset_IPCCH_2026_target_corrected_deep_features.csv`; v3 research describes ~5.05 GB and 386 columns. Not reloaded here. Its target-corrected outcome columns remain outside raw-truth authority.
- Existing v3 `ledgers/label_ledger.csv.gz` was streamed by a read-only scout: 9701 unique area-target rows. Year counts 2017:146, 2018:146, 2019:146, 2020:148, 2021:89, 2022:2103, 2023:2013, 2024:2130, 2025:1876, 2026:904. No 2015/2016 label rows.
- Existing copies total 3789: 2022:1374, 2023:995, 2024:1420; none in 2025/2026. These are existing artifact counts, not v4 replication results or an independently reconstructed label ledger.
- Source family, copy identity and availability are present in the existing ledger. Other retained artifacts include `round_links.csv`, `api_rounds.csv`, `source_families.csv`, `augmentation_decisions.csv.gz` and `cohort_ledger.csv.gz`.

Follow-up for G3 (primary read of both small ledgers): `api_rounds.csv:2-11` includes 2017-2021 current-period windows. Multi-month examples at `:7-11` are 2019 July-September, 2020 January-March/July-September, and 2021 January-March/July-September. V3's `round_links.csv:2-15` begins in 2022 because the config's augmentation-year scope begins there; pre-2022 linkage and added-row eligibility remain unexecuted. `round_links.csv:11-15` confirms no current round for 2025-04/09/10, the 2025-07 spillover exclusion, and the linked April-June2026 period. The latter cannot add May/June without existing covariates. These are existing saved source/decision records, not a new v4 augmentation result.

## Current workspace and audit setup

- Exact existing registered repository path: `/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/Google fund/Analysis/2.source_code/Step5_Geo_RF_trial/IPCCH`.
- Initial `trellis-audit status`: no active runs; controller `running=false`. Existing registered Claude session `4816e4c6-ebaf-4aa3-a15d-708bb775b09f`, terminal `term_65c50aeb3b3762`, is historical registration only. No live-runtime check performed yet; never assume this is the user's other running runtime.
- Initial branch: `feat/somalia-oracle-experiment`; unrelated untracked `scripts/reporting/somalia_oracle_wrapup.py` must remain untouched and outside task-only commits.
- Created task: `.trellis/tasks/09-30-somalia-v4-calibrated-d`, planning status. No audit registration/start/boot changes performed before grill convergence.

## Remaining technical checks, not user decisions

At authorized execution preflight: recompute all source identities; inspect raw covariate/label support for new annual folds; establish accepted validity links and augmented copied-test counts, with original copies required to be zero in every label role; verify seasonal join/complete export/metric provenance and shared-year value differences; reconstruct changed-history feature parity; verify per-context purges and OOF lineage; freeze keys separately for each setting before scores; independently replay each setting's annual and pooled results. Missing keyed/source evidence remains incomplete rather than pass.

## Current implementation reuse and incompatibilities (final planning pass)

Two read-only scouts inspected current source. GitNexus query located `augexp.prepare` and the validity runner; `list_repos` reported IPCCH indexed at `b3383ea02ab811b006b8d01713917622e7b74e91`, seven commits behind current HEAD. Graph output was used for navigation only; current source establishes the anchors below. No index mutation, model execution, feature generation or tests occurred.

Training/context evidence:

- `src/ipcch/somalia_oracle/__init__.py:12` hardcodes two rolling folds; `augexp.py:38,149` additionally clips model labels at 2022. Changing only folds would omit early supervised rows.
- `augexp.py:105-107` and `augment.py:102,114` separately restrict round links and copied recipients to configured augmentation years. The config currently begins at 2022.
- `augexp.py:185-201` excludes copied outer labels from both cohort and jobs; runner `scripts/modeling/run_somalia_validity_augmentation.py:181` excludes them again. The primary inspected the cohort/job source block directly. G8 requires setting-aware behavior: retain copy exclusion for original and admit permitted copies for augmented; do not remove the filter for both settings.
- Runner `:122-167` selects on H0 and keys recipes by setting/year; `:172-191` transfers those recipes across horizons, recording later-label flags rather than preventing them.
- `modeling.decay_weights:48-52` already accepts numeric half-life with negative-age rejection, but has no explicit no-decay path. V3 fitting calls (`augexp.py:340,359`) omit it and runner `:190` hardcodes weight reporting at 24 months. The primary read the weight and legacy candidate-loader source.
- `augexp.RoundStore.key:398-400` lacks decay, receiving-origin and dependency context; `fit_round_mappings:438-459` filters calibration rows but does not establish complete transitive held-out-family/history purges. The primary inspected both blocks. A legacy cache key or fit-key hash alone is not v4 isolation evidence.
- Reusable primitives: `augment.load_rounds/link_rounds/augment_labels:39-160`, `data.build_label_ledger:108-206`, `data.prepare_v2_seasons/v2_block:282-326`, `monthly_features.load_somalia_deep/scope_frame/parity_check:39-104`, `augexp.branch_mask/window_mask/fit_pool:230-246`, `q3opt.fit_cutoff:140-142`, mappings/bounds `:104-127`, selection `:392-405`.
- `augexp.final_task:361-375` actually fits/preserves q2/q4/q5 final outputs and same-bundle q3 direct fallback; only q3 drives recipe scoring. Preserve auxiliary outputs without adding their old ordinal comparison tables.

Reporting/replay evidence:

- `q3eval.share_metrics:21`, `pooled_auc:43` and `evaluation.binary_metrics:19` supply reusable weighted/undefined-aware metric primitives. The `model_view_metrics:71` wrapper also requires auxiliary/legacy fields and emits extra diagnostics; the v4 report can compose lower-level functions.
- Historical reporting primitive: `q3eval.paired_share_bootstrap:114-150` retains all rows of each area; unavailable handling is per metric at `:139-149`. G8 removes paired comparisons and bootstrap from v4, so this function is not a v4 reporting/replay dependency and must not be repurposed into an unrequested CI family.
- Runner `:286-288` replaces unavailable final mappings with clipped raw predictions in its report; the primary verified this directly. V4 explicitly prohibits using that fallback as final calibrated performance.
- Runner `:275,281,307` lacks explicit one-to-one merge validation and pairs comparison predictions by array position. V4 joins/validates truth and predictions by explicit keys within each setting and omits cross-setting pairing.
- `scripts/postprocessing/replay_somalia_validity.py:29` uses float round-trip reads; replay nevertheless hardcodes copied years<=2024 (`:61`), H0 selection truth (`:105-106`), three D views (`:159`) and H0 model probes (`:193`). Its historical bootstrap check at `:177-183` replays quantiles from saved deltas; G8 removes that path from v4 scope. New replay must instead verify setting-specific label eligibility and independently reconstruct each scenario's annual/pooled metrics.
- Existing unit/smoke anchors: `tests/unit/test_somalia_q3opt.py:165-195` covers threshold/undefined/bootstrap cases; `tests/smoke/test_somalia_augment_pipeline.py:88,103` asserts old copied-year/baseline behavior. Keep old regression checks; add meaningful v4 cases without treating the old acceptance matrix as v4.

Direct read-only runtime/version check succeeded: `/home/swl007007/.venvs/ipcch-geo/bin/python` reports Python3.12.3, NumPy2.4.4, pandas3.0.3, scikit-learn1.8.0, XGBoost3.2.0. SHA checks reproduced tree config `9d572793a3815baa42aa8c85a3304b0cc5aef8b52f191b1f7d3b7924aca9ef0f`, q3 config `581cb2a90eb66c76ae85b10b8e1c5f24a9c0863a1c0e48e6218eca0e4b50bbc6`, and validity config `45e0f7e811fe92f00d6481727ab9f609ceb8b421c0cc477f0414bcec41902422`. These checks establish configuration/runtime identity only, not a v4 test pass.

The primary read `/home/swl007007/projects/herdr-audit-controller/README.md` in full for the eventual handoff: operator registration verifies a chosen Claude pane; start must record the actual current commit and executor; active ownership cannot be replaced; boot starts the controller; close is separate and requires completed committed evidence. No live executor identification, registration, start or boot was performed before final review.

## Planning artifact verification

Earlier v1.0 snapshot, before the additional grill: the planning pass checked nine nonempty task artifacts, parsed both context manifests (six real existing-file entries each), verified the referenced tree-config SHA, enumerated exactly 144 unique recipes, checked five years/four horizons and 40 annual/eight pooled slots, and recorded G1-G6. Whitespace and placeholder checks passed. These checks do not establish acceptance of later revisions.

V1.2 revision: the user's G8 correction requires original-only labels in every original role and permitted validity-expanded labels in every augmented role. A read-only scout inspected all nine task artifacts for stale shared-test, matched-cohort, paired-delta and bootstrap dependencies; the primary rewrote the affected requirements, design, execution/check plans, config, metadata and provenance implications. Historical v3 facts remain labeled as historical. G1-G7 remain accepted; G8 is resolved by correction; G9 and consolidated acceptance remain pending. No product test, preflight, feature generation, model run, audit registration/start/boot or planning commit has occurred.

V1.2 document consistency check passed: nine nonempty artifacts with clean trailing whitespace; parsed JSON/JSONL; four explicit label-role policies per setting; 144 unique recipes; 40 annual/eight pooled slots; six valid source entries per manifest; pinned tree-config hash unchanged; no bootstrap/shared-test config; task still planning. The primary reread the revised PRD and implementation plan plus the changed design contracts. Live git status still shows only the new task directory and the pre-existing wrapup script. This is planning-document verification, not model or source-support validation.

V1.3 final-review candidate: G9 was accepted ("接受"); G1-G9 now have no unresolved individual design question. The PRD convergence pass moved the accepted failure policy into R9, retained every R1-R12/AC1-AC8 mapping and source anchor, removed the resolved-question paragraph, and was reread top to bottom. Document checks passed for the nine artifacts, explicit setting/failure policies, 144 recipes, 40 annual/eight pooled slots, six real references per manifest and the unchanged tree-config hash. Task remains planning; only consolidated package acceptance is pending. Git status still contains the task directory and pre-existing wrapup script. No product tests, experiments, commit or audit lifecycle operations were executed.

Final approval and setup preflight (2026-09-30): the user replied "确认" to the consolidated v1.3 summary. A fresh audit status check found no active runs and a stopped controller. Live Herdr agent list/get identified exactly one Claude in this exact repository: pane `wJ:p1`, terminal `term_65cb900f23bc17`, Claude session `7cea05f8-50d5-408d-aada-1948f70c734c`, idle; its recent output completed the unrelated wrapup report. This differs from the historical registered executor, so operator registration must bind the verified current pane before it starts v4. The unrelated wrapup script remains untracked and outside the planning commit. Setup outcomes will be recorded after durable verification.
