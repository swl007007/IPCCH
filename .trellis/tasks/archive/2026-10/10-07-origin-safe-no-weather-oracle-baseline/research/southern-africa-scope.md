# Southern Africa local evaluation — existing region3 mapping

User addendum: extract regional rows from saved GLOBAL predictions after the new global experiment, compare arms and bootstrap. No pipeline rerun, no global refit, no regional/local training for this addendum. Bootstrap concerns saved-prediction evaluation, not training-seed variability. Global primary comparisons retain single seed42.

## Authoritative scope, following user correction (2026-10-07)

User explicitly directed priority to `data/reference/area_id_country_region_mapping.csv`. This file contains6227 unique area_id mappings and numeric region codes0..8; SHA25618ab5099ce2d1154fb5686183ee399124e18427cc1594923f7abe2769da1611d. Its region3 country composition is AGO,LSO,MDG,MWI,MOZ,NAM,SWZ,ZAF,ZMB,ZWE. COD is region4 and TZA region1. Selection must use the file's area_id->region relationship; country names are descriptive metadata only.

Joined the existing baseline predictions for all four horizons to this mapping: all28205 evaluation rows mapped at each horizon, regional key sets identical across horizons. Region3 has3234 rows,1021 distinct areas and10 countries. Year2022:703;2023:514;2024:594;2025:1423. All region3 areas also have country ISO3 in the country lookup. The globally missing225 ISO3 rows are Cote d'Ivoire in region2 and do not block the region3 selection.

Region3 mapping includes1104 areas in total, of which1021 have valid frozen evaluation rows. Do not fabricate predictions for the remainder, expand membership by country, or run `scripts/modeling/run_region_models.py`: that older script fits local models, which the user explicitly excludes.

Existing use of this mapping: `scripts/modeling/run_region_models.py:85-105,143-161` checks area_id/region columns and merges by area_id; `docs/README_run_region_models.md:23-26` references the same file. Historical README counts are not the current observed mapping inventory.

## Superseded exploratory country definitions (retained as evidence)

An earlier limited search of configs/src/scripts/docs/.trellis/spec missed data/reference. The earlier claim that the repository lacked a grouping was too broad; the user-provided file above supersedes that conclusion.

Read the manifest-recorded `country_area_id_lookup.csv` and the four saved 2022–2025 `climate_safe_history_idp/3m/predictions/predictions_{Y}.csv` files. Lookup area_id is unique. The frozen evaluation keys are shared across horizons; this count is from the existing H3 reference only, not yet a new-run extraction or acceptance check.

SADC candidate was initially selected then explicitly superseded by the existing region map; do not use it for extraction. Its exploratory whitelist was AGO,BWA,COM,COD,SWZ,LSO,MDG,MWI,MUS,MOZ,NAM,SYC,ZAF,TZA,ZMB,ZWE. Historical evaluation counts:

| ISO3 | Rows | Distinct areas |
|---|---:|---:|
| AGO | 14 | 14 |
| COD | 1608 | 407 |
| LSO | 69 | 13 |
| MDG | 594 | 81 |
| MOZ | 1434 | 580 |
| MWI | 168 | 36 |
| NAM | 89 | 15 |
| SWZ | 73 | 21 |
| TZA | 232 | 66 |
| ZAF | 17 | 9 |
| ZMB | 748 | 224 |
| ZWE | 28 | 28 |

Total5074 rows across12 countries. BWA/COM/MUS/SYC have no evaluated rows; do not treat absent countries as zero performance.

The also-superseded UN M49 Southern Africa candidate was BWA,SWZ,LSO,NAM,ZAF, with248 evaluated rows across4 countries. Neither this nor SADC is the selected project definition.

225 global evaluation rows have empty ISO3 in the existing lookup; new regional extraction must report mapping coverage/unknown membership rather than silently implying every global row was assigned. Counts do not change the original global cohort.

## Existing bootstrap helpers and selected protocol

- `src/ipcch/somalia_oracle/evaluation.py:99-131`: seeded whole-area multiplicities and paired area bootstrap; reuse candidate, not automatic approval of the same clustering for a multi-country region.
- `src/ipcch/somalia_oracle/q3eval.py:114-129`: paired whole-area bootstrap for continuous share metrics.
- `tests/unit/test_somalia_oracle.py:331-355` and `tests/unit/test_somalia_q3opt.py:179-186`: deterministic/shared draws and unavailable cases.

Membership is frozen by region3. User selected B for bootstrap: only country-stratified, whole-area paired resampling, preserving all selected-period rows of each sampled area. No country-block sensitivity analysis. All arms must use identical sampled keys/multiplicities; no model refitting. The interval does not account for dependence across different areas within the same country or for model-fitting/seed uncertainty. Final technical settings and outputs are frozen in design.md.

Final grill decisions: G1/B selects conditional percentile intervals using only jointly defined paired draws, disclosing invalid counts/fractions; G2/A requires at least1,000 valid draws out of the fixed2,000. Keep original shared draws, per-contrast validity masks and conditional labels; do not replenish draws or change the global metric definitions. This intentionally supersedes the older helpers' any-undefined-draw interval suppression policy. See research/final-alignment.md and design.md.
