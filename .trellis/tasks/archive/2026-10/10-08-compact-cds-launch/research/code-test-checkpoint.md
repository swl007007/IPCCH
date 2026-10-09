# Code/test checkpoint (non-fitting) — 2026-10-09 ~05:50 UTC

Executor: Claude Opus 5.5 (1M), Herdr `compact-cds-executor` w11:p4. Status: implementation code and focused tests complete for
review; **weather cube, overlap gate and production inputs are not yet built** (provider downloads in progress). No model fitted.
HEAD b19d36d (planning commit), implementation uncommitted.

## Files (sha256 at this checkpoint)

| sha256 | lines | path |
|---|---:|---|
| 2fedc6e2514853b44ee140d4de56e46b460c7602909ea7b128c6ef738cc663c3 | 834 | src/ipcch/cds_launch_weather.py |
| 13d3abf460e0364dd4a3cf517b920002057994560fb2199e8cf22c4e17d753b4 | 1349 | src/ipcch/compact_launch.py |
| 21609b085a29db895e8ec73339fdfd69ecc11a2d3f231f727197f59ba880ad78 | 124 | scripts/preprocessing/build_compact_cds_launch_inputs.py |
| c58be4f4336bd3940c4bfe826796f3354a866d119283188a8651fbea08216db4 | 46 | scripts/modeling/run_compact_cds_launch.py |
| b78012e9117c6c6a3661aac10136fd9a4b7de46344c874dcef4a5106972c0b2b | 251 | tests/unit/test_cds_launch_weather.py |
| a7d509cd48bcb31e638bb18b414bda7da6f40cccd86baa5da8638d361f65ea9a | 258 | tests/unit/test_compact_launch.py |
| c130592f94c5cfd9a4ba9792e8afec76fd67d99afa1a932c8dcd54f5020c96a7 | 50 | tests/smoke/test_compact_cds_launch_cli.py |

Only new files; no existing symbol, helper, runner, config or dependency was edited, so no existing-symbol GitNexus impact was
required. Frozen helpers (compact_features, climate2015_features, origin_safe, launch_nowcasting, alert_risk_maps, ...) are reused unchanged.

## Focused tests (frozen model interpreter)

`PYTHONPATH=src /home/swl007007/.venvs/ipcch-geo/bin/python -m pytest tests/unit/test_cds_launch_weather.py tests/unit/test_compact_launch.py tests/smoke/test_compact_cds_launch_cli.py -q`
-> **32 passed in 7.63 s**, exit 0 (weather 15, compact launch 12, CLI smoke 5). Weather tests import no ecCodes/cfgrib/xarray.

## Supervisor findings -> resolution

1. Message semantics: `message_semantics_problems` requires April 1 00 UTC, single forecast time in hours (TRI 10, instant,
   start = end step), validity = init + step, parameter/units/MARS type (2t 167 K fc/mmsf; tp 228 m fc/mmsf; 2ta 171167 K
   em/mmsa; tpara 173228 m s**-1 em/mmsa), official lead -> verifying month and month-start validity. tp is not required to be
   GRIB2-style accumulation; accumulation since forecast start is the provider definition (cited in the module docstring and
   provenance), proven in processing by non-decreasing endpoints within decoding bounds and by the September overlap.
   Real-file evidence: the strict probe report on the five real probe files passes with 0 semantic problems; one complete
   hindcast file (1999, 6,125 messages) passes identity/semantics with 0 problems (metadata pass 9.3 s, values pass 8.7 s).
2. September bounds: frozen before comparison from the 120 September temperature samples and the 3672/4392 precipitation
   endpoints only (per-message max(half-step, ecCodes packingError)); October messages do not enter.
3. Literal `NA`: `save_csv` re-reads with only empty fields as missing; regression `test_save_csv_keeps_literal_na_and_true_missing`.
4. Verifier: every phase1-5/P3+/P4+ share, raw/effective count and denominator at area/country/region/global; all four
   paired-difference tables (H0 exactly 0, undefined masks); finite-only replay (NaN cannot pass); exactly the seven required
   PNGs; complete keyed map records with matching hashes and table values; old-artifact after-inventory.
5. A2: `inference_history` filters reported phases to <= 2026-03 before `build_safe_history` (test with a tempting April 2026
   report at every horizon); `future_perturbation_check` (post-April source months and seasons ending after May 1 perturbed)
   with a synthetic positive/negative test. Real ledgers are written by the assembly (history/IDP per H, season, population).
6. Map join: continuous/difference maps join on a string-normalized key and keep integer `area_id` in records;
   `test_write_maps_produces_seven_figures_with_keyed_records` exercises the real `write_maps` path (3 synthetic areas incl. a
   Latin-America inset area): seven PNGs, integer keys, values equal the table, record hashes.

## Real-source dry run (not an accepted input build)

`build_inference` + `training_frame` on the real pinned sources with a clearly dummy all-zero weather cube (no files written,
170 s): five matrices 6,188 x (3 keys + 296/308) with the contract order; perturbation 233 features / 0 changed; non-calendar
inputs identical across H0/H6/H12; weather prefix equals baseline; H0 identifiers equal `add_identifier_features`; 2027 year
flags all False; 2,774 April 2026 reports excluded from history; IDP present for 5,650 areas; fitting 49,532 rows per run
(labels 2014-01..2026-03, weights 0.01433..0.97153).

## Weather retrieval state

28 recorded request IDs, none resubmitted; poller PID 1571471 (`CDS_API/compact_cds_launch_v1/logs/bulk.pid`, `bulk.log`,
`status_bulk.json`). Probe gate (strict) passed. Bulk processing (`--weather-only --process`) runs after all 28 downloads;
its September overlap gate decides acceptance. Assembly, input checkpoint and fitting remain closed until then.
