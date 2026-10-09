# Read-only contract evidence for the 2026 extension

Date: 2026-10-09. Evidence status: ready for specification grounding. Extension validation status: **not executed**. These are inspected sources/metadata/counts/hashes, not new fits or acceptance.

## Evidence ownership and limitations

Code/data scouts performed read-only source, CSV and hash inspection, without fits, file writes or provider calls. The coordinator inspected the annual fitter and localizer directly (`run_deep_feature_weight_decay_forecasting.py:1078-1149`; `run_somalia_local_compact_test.py:435-491,739-767`), read the quality/reuse/cross-layer guides and used GitNexus query for the existing loading/batch flows. GitNexus line numbers may be stale; the exact current source is authoritative. Main-session Git HEAD was `644c2e0095a1fea669203a6af6c59d7af787a632`, branch `task/compact-climate-weather-oracle`.

Existing unrelated dirty files are `AGENTS.md` and the archived superseded launch PNG under `10-08-compact-cds-launch/research/final_verify_attempt1/superseded_figures/`. Preserve their current bytes and exclude them from task commits.

No new CLI, model fitting, full old-model numerical replay, upstream label-source authenticity check or publication-vintage validation was performed. Existing fitted-result verification summaries are prior saved evidence, not new acceptance claims.

## Labels, keys and membership

Source interim: `assembled_IPCCH/interim/IPCCH_2026_target_corrected_nino34_wbfood.csv`, selected via the parent manifest. Eligibility is exactly `origin_safe.share_validity` (`src/ipcch/origin_safe.py:114-122`).

The source has 6188 candidate rows per 2026 month (24752 for Jan-Apr), including904 SOM candidate rows/month. Valid rows are4327 global and905 SOM; all are within the original cohort, no duplicate keys or valid keys outside that universe. Valid area unions are3823 global/904SOM. The original exact `iso3 == "SOM"` membership is905 areas, with3146 absent from the2026 candidate grid.

| Month | Global eligible | SOM eligible |
|---|---:|---:|
| 1 | 679 | 1 |
| 2 | 643 | 0 |
| 3 | 231 | 0 |
| 4 | 2774 | 904 |

All4327 cohort rows are `share_valid=True,eval_key=False`. SOM's unique January key `(1917,2026,1)` is phase2 and also has an April row. Current cohort evidence: `origin_safe_climate_idp_v1_cohort_keys.csv:12211-12212`.

Region membership is the explicit repository mapping, with no unmatched candidate key:

| Month | r0 | r1 | r2 | r3 | r4 | r5 | r6 | r7 | r8 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 0 | 117 | 0 | 60 | 501 | 0 | 0 | 1 | 0 |
| 2 | 0 | 379 | 0 | 93 | 17 | 154 | 0 | 0 | 0 |
| 3 | 81 | 0 | 0 | 0 | 0 | 150 | 0 | 0 | 0 |
| 4 | 397 | 437 | 0 | 706 | 329 | 0 | 0 | 904 | 1 |
| Total | 478 | 933 | 0 | 859 | 847 | 304 | 0 | 905 | 1 |

Regions2/6 have no eligible2026 row. Region8 has one, so annual R-squared is undefined. Region0 is valid. Source: `data/reference/area_id_country_region_mapping.csv`; constraints in `regional_point_metrics.py:23-44`.

## Matrix and source coverage

Seven existing matrices each contain52521 complete label-cohort rows and the same4327 candidate2026 keys. Labels/raw shares match the interim and each other. Baseline columns match their paired oracle by exact value/NaN/order on the candidates. Declared features exist, no candidate feature Inf, and native NaNs remain:

| Run | Features | Candidate NaN cells |
|---|---:|---:|
| Baseline0 | 296 | 160350 |
| Baseline3 | 296 | 153345 |
| Oracle3 | 302 | 153375 |
| Baseline6 | 296 | 133343 |
| Oracle6 | 308 | 133403 |
| Baseline12 | 296 | 111283 |
| Oracle12 | 308 | 111343 |

Interim covers2010-01..2026-04; climate monthly covers2015-01..2026-08. Each H has all4327 origins and51924 row-by-12month rolling source keys; SOM905/10860. All required oracle calendar keys exist:12981 atH3,25962 atH6/H12; SOM2715/5430. Source-key existence is not finite-value completeness: every lead has some source-native precipitation/temperature NA. These remain inherited missingness, not a reason to invent features or drop eligible labels.

All four existing season ledgers have selected last1/last2 records for candidate rows, with zero season ends after the allowed cutoff. Major-dummy NA counts are global33/33/33/34 atH0/3/6/12, SOM4each. Selection algorithms were not rebuilt in this inspection.

Expected training counts in `expected_runs.csv` were independently recomputed using valid shares and the annual cutoff, not by fitting. `run_origin_batch` computes cutoff `Jan(Y)-max(H,1)` and weights at `Jan(Y)-H` (`:1087-1098`), supporting2026 without changing the frozen year constants.

## SHA256 identities read during planning

The full source-data root is `/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/Google fund/Analysis/1.Source Data/assembled_IPCCH`.

| Identity | Actual SHA256 |
|---|---|
| Global parent manifest | `456360536a3929e1571d96ba9f16e2f0de54bc1b20019f797bbe62c0c89732ca` |
| Original local manifest (under local results/inputs) | `573b0d0bb074a2de9251afacf549dfe18a30321af8bce87dfce75ac0644fe228` |
| Parent cohort | `136095f1070a30f41f6011ad85d8170618043e6f8a109a6452fd474593a21ec3` |
| Canonical country membership | `e2baf6ae9481b42b127db5ce81f3c53ad784bb08ae56dfa56cea74e416b44c90` |
| Repository region map | `18ab5099ce2d1154fb5686183ee399124e18427cc1594923f7abe2769da1611d` |
| Interim | `a91719e8e603e11b58e3e44c9a2f4378e4218e1ac408afe03ca54d1b50fb0484` |
| Climate monthly | `8082b72ea5fa5c30a7b975b89c1fbbb4530f27a9ce6c5ba4d0e1a4f923320c89` |
| Climate seasonal | `f024a66c8979fb4a8c66fba1f04e7e69355fa75b499793d29001a146d8c2958e` |
| BaselineH0 dataset | `92def8b5bdef5e217abebdadaa21fce490021551a792ed225a78406f61a58012` |
| BaselineH3 dataset | `38cf35f7a864e8006c53468e28424c65c5399454ca5b6f1eb7b10de37d73a4c7` |
| OracleH3 dataset | `01802606985c8188e1f96932865e488a10e5f871202a6a6230736bf95c7380bb` |
| BaselineH6 dataset | `38b8e6d2ee49155e2c009695e322418e4f01be9656dceb5fa4c6c3ba729b5bd8` |
| OracleH6 dataset | `fd31cf0f505fa3172d2c09b7823b1970194e8ea7d8c86de8fded2b1ecf58c636` |
| BaselineH12 dataset | `e442a40d37a259f31aaaea337fcfeffaeb593d1ff7108112dc8f69313f12a811` |
| OracleH12 dataset | `aa7f299ca6c89d5243b91c6b1e045fc9dafeed386a9d89f390edc78d7502229d` |

Dataset paths are declared in the global manifest at lines501-505,853-857,1175-1179,1528-1532,1862-1866,2214-2218,2548-2552. Source and matrix hashes match that manifest. Revalidate all identities at execution, not merely at planning.

Frozen runtime/config/feature hashes are in `compact_features.py:63-85`. Original SOM script SHA is `88aee59be33033dd85f180bd9cc4e5f317bc9c033b1a32a972fe0acf82ea8c56`. Existing helper/build hash checks inspected during planning matched; old complete-batch revalidation remains an execution gate.

## Reuse evidence and limitations

Global saved verification: `results/experiments/compact_climate_weather_oracle_v1/verification/verification_summary.json:2-11,56-68` records7runs/28batches/112models,28205keys,zero reported replay difference and `passed=true`. Original eval-key hash: `f0193c1402d0609556755844b476227b7188f9671323d21317336d7ef58d2e0f`.

Local saved verification: `results/experiments/compact_climate_weather_oracle_v1_somalia_local/verification/verification.json:1-17` records28batches/112models,4933keys,zero reported replay difference and `passed=true`. Original eval-key hash: `5f8343c4b4ba92176b1a7fa2797dfb9c29d5805065f200df46c416efcea9f14a`.

Original inventories, batch artifact records and model schemas support fresh lightweight import checks. Required checks: all artifact hashes and COMPLETE/fingerprint coverage; exact published-v-batch predictions; pinned truth/targets; complete fit keys/cutoff/scope/ages/weights; pair key/truth/weights; independent original metric/status/reason parity. Relevant source: global verifier `verify_origin_safe_weather_oracle.py:126-209`; local verifier `run_somalia_local_compact_test.py:1323-1398`.

## Orchestration and reporting gates

- Parent loader validates original mask/year/key hashes (`runner:1016-1037`); do not edit cohort2026flags before gating.
- `block_plan` rejects2026 (`runner:1050-1057`); `run_origin_safe` aggregates only frozen years (`:1180-1205`). The new coordinator uses the annual primitive directly.
- Fitter depends on input masks/fingerprint but has no fixed-year gate (`:1078-1149`). The localizer shows post-gate copied mappings (`local:435-458`).
- Original global and local run fingerprints bind whole helper/runner/script bytes (`compact_features.py:82-85,479-515`; `local:453-457`); preserve them and assign a separate extension identity.
- Existing region metric `PERIODS` is fixed, but pooled consumes all passed rows (`regional_point_metrics.py:19,73-75`); passing2026through it alone silently omits annual2026while expanding pooled. Use explicit new period masks.
- Global outputs/codebook/report are emitted at `verify_compact_climate_weather_oracle.py:267-409,568-603`; local equivalents at `run_somalia_local_compact_test.py:774-919`. Preserve metric/support/undefined conventions and distinguish global region7 from genuinely locally fitted SOM.
- Existing local `--report` invokes both historical and launch reporting (`local:1972`). Do not use it for this task.

No historical PNG/HTML or combined historical-launch report was located in the checkout, including ignored roots. Such presentation products are outside this approved task; historical CSV/Markdown/codebooks are the current concrete reporting baseline.
