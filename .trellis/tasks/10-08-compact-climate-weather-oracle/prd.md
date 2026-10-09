# Compact climate and raw weather-oracle comparison

## Status and goal

Planning converged on 2026-10-08; formal specification prepared for final user review. Implementation, input generation, training and executor dispatch have not started. This task reduces feature engineering at the advisor's request and measures the incremental value of raw perfect-weather information under the compact feature set.

## Requirements

| ID | Approved requirement | Acceptance |
|---|---|---|
| R1 | At each row's origin O=T-H, H in {0,3,6,12}, retain 24 ordinary sources with value, MA3, MA6, MA12 and SD12 (120 columns). | A1,A2 |
| R2 | Retain both ordinary and same-month-z families for the 14 eligible sources; z itself and MA3/6/12 of monthly z (56 columns). No extra lag12. | A1,A2 |
| R3 | Retain seven existing stress signals and four existing summaries at O (28 columns), with old thresholds and missingness. | A1,A2 |
| R4 | Retain the latest two completed growing seasons, 13 indicators plus age each; add one major dummy for the latest season (29 columns). | A1,A3 |
| R5 | Preserve 29 static, 27 coordinate/target-calendar, five safe IPC-history and two national-IDP inputs and definitions (63 columns). | A1,A2 |
| R6 | Remove fixed T-12/asof12 duplicate blocks, NDVI, FAO prices, WB food inflation, explicit products/interactions, neighbors and other deep transformations. | A1 |
| R7 | Preserve WFP and the existing RTP-derived WB index; retain all four BBG composites under original definitions. No new RTP ingestion. | A1,A2 |
| R8 | Reconstruct monthly dynamic inputs directly from source grids at O. Do not preserve carrier-tail or saved-extra-NA masks. Preserve real source missingness and approved algorithms. | A2,A4 |
| R9 | Refit compact baseline at four horizons; raw-oracle arm only at H3/H6/H12; H0 shared. Seven runs, four annual batches each, four regressors each =112 fits. | A5,A6 |
| R10 | Preserve 2022–2025 cohort, annual cutoffs, weights, fixed hyperparameters, target processing and eight metric definitions. No retuning. | A5,A6 |
| R11 | Global and region0–8 tables: annual and pooled metrics, paired oracle-minus-baseline deltas, support and undefined reasons; use saved global predictions. | A6 |
| R12 | Persist spec first, then an English CSV of expected literal fitted inputs, in the style of the supplied HHA codebook. Verify actual fitted membership/order afterwards. | A1,A7 |
| R13 | Codex supervisor, Claude Opus 5.5 1M executor after final approval; prefer Windows Git. No additional Trellis audit registration/start/close for this task. | A7 |
| R14 | Preserve separately selectable legacy and compact feature versions, manifests, schemas, inputs and outputs; maintain a rollback recipe without overwriting artifacts or adding an experiment arm. | A7 |

## Confirmed decisions and trace

The design contains executable formulas, literal source lists, names and order. This table preserves every grilling decision without leaving historical questions open.

| Decision | User response / outcome | Owning requirement |
|---|---|---|
| D1 | Adopted: compute strictly earlier-year same-calendar-month z per month first, then its moving averages; sample SD. | R2 |
| D2 | Remove independent fixed T-12/asof12 group; H12 still naturally has O=T-12. | R1,R6 |
| D3 | Add RTP/local-price clarification, major-season dummy, regional metrics and post-spec contract; omit FAO/inflation/bootstrap. | R4,R7,R11,R12 |
| D4 | Preserve existing RTP-derived food_price_index_WB definition; simplify engineering only. Supersedes a new RTP ingestion interpretation of D3. | R7 |
| D5 | Major = longer of s1/s2 for the same area/season_year, using end_exclusive-start calendar days. | R4 |
| D6 | Major dummy longer=1, shorter=0; equal, unavailable comparison or no completed season=NA. | R4 |
| D7 | Confirmed all four BBG groups, including oil/gas, with original members and arithmetic means. | R7 |
| D8 | Ordinary and eligible same-month-z families enter simultaneously. | R1,R2 |
| D9 | Keep share12, months_since, longest_run12, any12; remove interactions and neighbors. | R3,R6 |
| D10 | Keep two completed seasons; major dummy only for latest. No monthly MA/SD expansion of seasonal inputs. | R4 |
| D11 | Keep all 63 existing background/calendar/history/IDP columns. | R5 |
| D12 | Adopt 14 z sources; no second standardization of prcp_z, sm_z, spi03, spei03; no new BBG/conflict z. | R2 |
| D13 | Adopt MA minimums2/3/6 and SD12 minimum6; same-month z needs two past same-month values and nonzero sample SD. | R1,R2 |
| D14 | Retain old stress implementation, including false/0 for unavailable year-ago comparator or zero price denominator. | R3 |
| D15 | Adopt seven runs, unchanged annual protocol/cohort/configs, all-region annual/pooled eight metrics and differences. | R9,R10,R11 |
| D16 | User said “同意” after the concrete carrier-row explanation: directly use available source values at O; remove artificial inherited masks. | R8 |
| D17 | User requires a rollback option for this feature version: freeze compact and preserve the legacy feature path, selectable by explicit manifest/version. | R14 |

## Expected fitted schema

| Family | Columns |
|---|---:|
| Ordinary | 120 |
| Same-month z | 56 |
| Stress | 28 |
| Completed seasons and major dummy | 29 |
| Static, coordinates/calendar, safe history, IDP | 63 |
| Baseline total, every horizon | 296 |
| Raw oracle H3 / H6 / H12 totals | 302 / 308 / 308 |

These are expected counts, not fitting evidence. A preliminary conversational total of360 was an arithmetic error, corrected to296 without changing membership.

## Evidence and definitions

- Previous actual reference: `origin_safe_climate_idp_v1/climate_safe_history_idp`; previous oracle: `origin_safe_weather_oracle_v1/climate_safe_history_idp_oracle`. The completed codebook under `reports/origin_safe_weather_oracle_v1/model_run_codebook/` records their actual fitted columns; it is not the new expected contract.
- Prior designs: `.trellis/tasks/archive/2026-10/10-06-global-origin-safe-climate-idp/design.md`; `.trellis/tasks/archive/2026-10/10-07-origin-safe-no-weather-oracle-baseline/design.md:13-20,51-61`. This task supersedes their mask, feature-arm and bootstrap scope where explicitly stated.
- Monthly/seasonal climate sources: `src/ipcch/climate2015_features.py:18-23`; rolling/minimum counts `:26-30,113-128,194-234`; historical z `:160-188`; stress thresholds/summaries `:33-40,131-157,246-251`; completed seasons `:288-320,392-396`.
- Inherited sources, BBG, stress and prior shifted z: `src/ipcch/retained_feature_recipes.py:20-29,36-66,92-95,123-129`. Carrier masking and saved-extra-NA: `:135-177,180-204`; detailed observations in `research/compact-source-missingness.md`.
- WB index: `Analysis/1.Source Data/WB_RTP_price/filter.ipynb:830,842-843,866`, (open food-price index + close food-price index)/2, already inherited as `food_price_index_WB`. No alternate commodity feed.
- Seasonal source header: `IPCCH_shared_folder/climate_2015_2026_MODELING_READY.csv:1`; 74,724 checked area/year pairs: s1 longer26,154; s2 longer48,198; ties372; no invalid calendar rows; date-derived duration agrees with stored duration; fixed SOS/EOS per area. No provider major-season label. See `research/source-and-region-facts.md`.
- History/IDP names `src/ipcch/origin_safe.py:30-37`, selection `:143-180,256-276`; metrics `:387-424`. Target calendar `src/ipcch/forecasting_weight_decay.py:153-186`.
- Raw oracle timing/order `src/ipcch/weather_oracle.py:25-94`; regions `data/reference/area_id_country_region_mapping.csv`: unique6,227 area IDs, regions0–8. Region0 is a valid group.
- Requested codebook template: `C:\\Users\\swl00\\IFPRI Dropbox\\Weilun Shi\\Kenya-MUAC data\\Processed_data\\HHA_ward_model_run_v4_codebook_en.csv`.

## Acceptance criteria

- **A1:** Expected contract has one row per literal input; projecting its run membership/order yields exactly296/302/308 columns. No forbidden columns. Every saved fitted booster and metadata feature order equals its approved run schema.
- **A2:** Formula checks on small calendar-keyed examples and real-row samples establish source timing, MA/z semantics, old stress behavior, safe history/IDP and unchanged background definitions. Future non-oracle source/label perturbation cannot affect earlier-origin inputs.
- **A3:** Two completed seasons and major classification replay from saved season identity/dates; tie, absent-pair, absent-season and exclusive-end cases tested.
- **A4:** Baseline projection of oracle inputs equals newly rebuilt compact baseline cell-for-cell, including NA masks, order, keys and labels. Record source coverage, restored old missing cells and unresolved source-vintage limitations without adding predictors.
- **A5:** All seven runs and28 batches complete with112 UBJ models, fitting keys/weights, predictions, metadata, hashes and exact-resume checks. Cohort remains28,205 keys with annual counts5,599/6,064/5,127/11,415 and original tuple hash.
- **A6:** Replay all batches, models and all global/regional metrics from explicit artifact paths; predictions atol1e-6/rtol0, metrics atol1e-12 with identical undefined masks. Regions partition every prediction exactly once. No bootstrap/B6/regional retraining.
- **A7:** Final codebook reflects actual fitted membership, expected-vs-actual comparison passes, source/config/runtime/code provenance and execution evidence are saved. Report unresolved checks honestly. No claim of experiment completion during planning.

## Out of scope and limits

No B6, bootstrap, tuning, additional price feeds, NDVI, interactions, neighbor summaries, SHAP or alternate model families. No raw-data or historical-output overwrite. Version rollback selects a pinned feature manifest and its matching outputs; it does not overwrite a newer version. No new audit enrollment or audit-controller lifecycle for this task; user override is explicit.

Observation/report month remains the availability proxy. Historical release vintages and upstream climate climatology-fitting samples are unverified; supplied source definitions are not upstream ETL certification. BBG mixed quote scales and original stress missingness are deliberately preserved. Major means calendar duration, not certified agronomic importance. D16 changes old missingness as well as feature count, so do not attribute differences from old runs solely to deleting features.

## Planning and execution boundary

No unresolved user-owned feature/evaluation decisions remain. `design.md`, `implement.md`, real context manifests and the expected contract are prepared before final review. Execution depends on a subsequent approval of the final planning summary. Claude CLI/channel capability is available locally; actual Opus5.5 and1M session resolution must be verified before dispatching work, with no silent fallback. Numerical runtime and pinned input hashes must also pass preflight.
