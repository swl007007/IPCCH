# Design: Somalia local compact experiment and launch

Specification status: Approved on 2026-10-09. Validation status: Not Executed; later evidence is recorded separately.

## Boundary and implementation size

One task owns two sequential experiment stages sharing membership and verification/reporting. No parent/child lifecycle split or generic country framework is needed. Add one Somalia-specific script, `scripts/modeling/run_somalia_local_compact_test.py`, and one focused test, `tests/unit/test_somalia_local_compact_test.py`. Reuse frozen input/model/report primitives; leave their source files unchanged. Main session owns design/final acceptance; the verified Herdr Claude Opus 5.5 executor with 1M context implements the approved scope. User explicitly opts out of Trellis audit for this task; use ordinary lifecycle and independent Codex supervisor acceptance.

## Roots and explicit inputs

Let `A=/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/Google fund/Analysis/1.Source Data/assembled_IPCCH`.

| Role | Path |
|---|---|
| Membership | `A/country_area_id_lookup.csv` |
| Historical parent manifest | `A/model_ready/compact_climate_weather_oracle_v1/compact_climate_weather_oracle_v1_manifest.json` |
| Launch parent manifest | `A/model_ready/compact_cds_launch_v1/compact_cds_launch_v1_manifest.json` |
| Historical local outputs | `results/experiments/compact_climate_weather_oracle_v1_somalia_local` |
| Historical local reports | `reports/compact_climate_weather_oracle_v1_somalia_local` |
| Launch local outputs | `results/launch/nowcasting_2026_04_compact_cds_v1_somalia_local` |
| Launch local reports | `reports/launch/nowcasting_2026_04_compact_cds_v1_somalia_local` |

Resolve dataset/ledger/weather/contract/config paths from explicit parent manifests, never recursive latest-file selection. Local copied contracts, key selections and launch matrices live under new roots' `inputs/`; runtime paths survive task archival. Local manifests distinguish parent model-contract version from local experiment identity/scope. No external source directory writes or weather downloads.

## Membership and coverage

Read exact `iso3 == "SOM"`, require 905 unique IDs, hash lookup bytes and sorted IDs. No name fallback. Full parent inputs pass existing schema/hash/ledger gates before local selection; preserve feature missingness and row/feature order.

Historical eval is the parent cohort intersected with SOM:4,933 keys across 905 areas. Annual2022/2023/2024/2025 rows1129/1217/711/1876, distinct areas585/705/372/904. Retain3146's eligible2022 keys. Launch fitting is original valid pre-April selection intersected with SOM:5,835 rows,905 areas; inference/population is full parent April cohort intersected with SOM:904 areas. Save excluded3146 and its missingApril source/population reason; do not carry its2024 population forward.

## Historical stage

Seven combinations in `expected_runs.csv`, four yearly batches each, four regressors per batch. Existing `load_compact_inputs` validates the complete parent schema/cohort/runtime/history/IDP/season/oracle evidence. Create local inputs with BOTH `share_valid &= SOM_membership` and `eval_key &= SOM_membership`, preserving aligned data/targets/ordinals. Replace parent-global fingerprint with a distinct local fingerprint before calling `run_origin_batch`. Keep the rejecting global CLI wrapper unchanged.

For yearY use `fit_origin=Jan(Y)-H`, label cutoff`Jan(Y)-max(H,1)`, weight`0.5**((fit_origin-U)/24)`. Features retain each row's `O=T-H`; IPC history through`min(O,T-1)`. Oracle appends realized precipitation/temperature at`O+1..O+min(H,6)`, offset-major prcp then tmean. Baseline 296; oracleH3=302,H6/H12=308; H0 shared.

Frozen seed 42/configs/phase3 config/n_jobs16; no tuning/imputation. Targets retain normalized shares, class truth reported phase, unrounded classification>=0.2. Evaluation metrics use observation rows, not fitting weights. Eight metrics: exact_phase_accuracy,phase3plus_accuracy,precision_phase3plus,sensitivity_phase3plus,f2_phase3plus,r2_phase3plus,mae_phase3plus,ordinal_mae. Annual and pooled metrics/deltas use exact paired keys/truths; undefined values retain reasons. H0 can display shared zero deltas without another fit.

Save original batch/run inventories and explicit SOM scope/cohort identity. Reuse independent sklearn metric/model-replay components with local keys; global-count/hash/report drivers are unsuitable local acceptance gates. Reports provide SOM annual/pooled absolute values, support/deltas and actual-fitted English codebook; no empty unrelated region/global groups.

## Launch stage

First call full original `validate_inputs`. Derive local fit-selection tables/inference matrices by exact SOM filtering; prove complete set equality and serialized round-trip matrix parity with parent projections. Leave original training datasets unchanged. Local launch manifest preserves the parent's fitting-entry format and adds local experiment/version/scope, member/cohort identities, parent manifest hash, local code/spec and generated-input hashes. Finish/hash this manifest before fitting; do not mutate it during a run.

Call unchanged `compact_launch.fit_run` with the explicit local manifest and new root. Parent full gate already ran; local gate independently verifies complete eligible SOM sets, targets/weights/schema/pairing and 904 inference areas. Inherited low-level records retain the parent model-contract version; hashed local manifest/scope records distinguish the local experiment. Bind scope sidecars in final inventory rather than silently rewriting fitter records.

April 2026 origin; baselineH0/H6/H12 and CDSH6/H12. Training target strictly beforeApril with April-anchored weights. Inference history cappedMarch; ordinary/IDP throughApril; inherited season/static/calendar rules. Targets April 2026/October2026/April 2027;2027 existing year dummies all0. H6/H12 use the same accepted May–October April-init CDS12-column cube, not later initialization or realized future substitution. Raw class uses unrounded cumulative scores.

## Population and reports

Validate the original complete population/cap audit, then take its entire SOM covered cohort/factor. Fixed raw 62,695,007; reference 19,654,739; inherited factor 0.29782279233177217; effective 18,672,002.05. Recheck these at execution; every arm/target uses identical area populations.

Reporting components are`[1-q2,q2-q3,q3-q4,q4-q5,q5]`, individually clip[0,1] then normalize; retain repair flags and original raw scores/classification. Counts use raw/effective populations; P3+/P4+ sum corresponding phases; country shares=sum(counts)/sum(population). Retain zero-population rows/undefined denominators. Paired CDS-minus-baseline requires equal keys/population; H0 shared delta0.

Save area/SOM summary and difference tables, cap/coverage ledgers, raw predictions and actual-fitted codebook. Preserve seven-map format scoped toSOM: five categorical maps,2×3 absoluteP3+ comparison,1×2 P3+ difference. Categorical maps raw-derivedphase>=3; continuous maps repaired shares. Record keyed plotted values/units/data/geometry hashes and complete904-area joins. Read applicable figure-style guidance before rendering and reuse current plot primitives without editing frozen helpers.

## Identity, validation and resume

Freeze parent source/input/helper/config identities and interpreter `/home/swl007007/.venvs/ipcch-geo/bin/python` (Python 3.12.3/NumPy 2.4.4/pandas 3.0.3/sklearn 1.8.0/XGBoost 3.2.0). Verify inherited config/contract/source hashes against current bytes. Local fingerprint also binds SOM lookup/IDs, complete selected ordered keys, local script bytes, copied approved spec, stage and parameters. Never reuse a global fingerprint after masks change; reject source/helper/config/runtime drift rather than rebuilding or substituting.

Run sequentially; historicalH0/2022 is measured pilot and part of 28 batches. No concurrent heavy training/tests. Resume only exact matching fingerprints and complete mandatory inventories/hashes; partial/stale outputs remain incomplete.

Independent verification reconstructs all local fit/eval/inference sets, targets/weights and paired matrices/schemas from explicit parents; reloads 132 models; replays predictions(atol1e-6,rtol0)/exact classes; independently recomputes metrics/deltas(atol1e-12,same undefined masks), counts/sums(atol1e-6,rtol1e-12),shares(atol1e-12) and plotted values. Require28 historical batches/112 models,5 launch records/20 models,seven maps and actual codebooks. Inventory all declared outputs and frozen parent identities. Failures preserve diagnostics and block acceptance.

## Proposed entrypoint

One fixed-scope script with existing-style `--validate-only`, `--approve-training`, `--report`, `--verify`. Validate performs read-only gates with no outputs; training completes fixed historical then launch fits; report/verify consume saved local artifacts and never fit. Defaults are explicit approved roots. No generic country/horizon/provider framework or extra model options.
