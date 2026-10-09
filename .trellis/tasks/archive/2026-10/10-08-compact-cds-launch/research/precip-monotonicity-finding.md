# Weather stage REJECTED: accumulated-precipitation monotonicity (2026-10-09 06:05 UTC)

Status: **weather stage stopped; no cube written; September overlap comparison NOT run; no inputs assembled; no fitting.**
Command: `PYTHONPATH=src <CDS_API>/.venv/bin/python scripts/preprocessing/build_compact_cds_launch_inputs.py --weather-only --process`
-> exit 1 after 7:07 (peak 190 MB); log `CDS_API/compact_cds_launch_v1/logs/process.log`; REJECTED provenance
`CDS_API/compact_cds_launch_v1/processed/cds_weather_provenance.json` (copy: `research/weather-stage-rejected-provenance.json`).
Code at run: weather `edcb8c7d…`, CLI `21609b08…` (`logs/process_code_sha256.txt`).

## What passed before the stop

All 28 files decoded with the strict identity/semantics gate (centre ecmf, system 51, method 1, April 1 00 UTC, single
forecast time, validity = init + step, parameter/units/MARS type, exact members/years/steps, one half-degree-centred grid):
0 identity problems. Temperature: 2026 12,495 messages, each hindcast year 6,125; precipitation 153 (2026) and 1,800 (hindcast).
Completeness passed: the REJECTED provenance lists 32 problems, all of class "accumulated precipitation decreases"; support
records 51 forecast members, 25 members in each of the 24 hindcast years, and per-member temperature samples Sep 120 / Oct 124
(both conventions), with every tp endpoint present.

## What failed

The executor-added check "accumulated tp non-decreasing between endpoints within decoding bounds" (bound per pair =
max(half-step, ecCodes packingError) of the start message + of the end message, i.e. 6.1e-5 + 6.1e-5 m in most messages):

| file | member-intervals with a decrease beyond the bound (any grid cell / a launch point's cell) | worst decrease | worst / bound |
|---|---|---|---|
| original_prcp_2026 | 20 / 17 of 102 | -1.66e-4 m (0.17 mm) | 1.36 |
| original_prcp_hindcast | 236 / 94 of 1,200 | -1.65e-4 m | 2.01 |

Script/output: `research/precip_monotonicity_diag.py`, `research/precip_monotonicity_diag_output.txt`.

## Evidence on semantics

- Accumulation since forecast start is unambiguous in magnitude: mean over the grid 0.42-0.49 m at Sep 1 (step 3672),
  0.50-0.59 m at Oct 1 (4392), 0.58-0.69 m at Nov 1 (5136); minima 0, maxima 3-6.6 m; consistent in 2026 and all hindcast years.
- Decreases occur where accumulations are small (dry cells, start values 0.5-57 mm) and are at most 0.17 mm.
- Plausible mechanism (not provable from the downloaded metadata): the delivered GRIB1 16-bit packing re-quantizes values that
  were already quantized/regridded upstream, so true per-value error can exceed the delivered half-step (ratio up to ~2 fits a
  second quantization of similar size). The downloaded files carry no metadata about upstream packing/interpolation.

## Why the executor stopped here

The approved acceptance criterion for October is the September overlap gate with bounds frozen from downloaded metadata
before comparison; the monotonicity requirement was an additional executor-designed proof of accumulation semantics. Its
failure is "not explained by independently computed (delivered) packing bounds". Changing or removing the check, or widening
any bound, after seeing this outcome would be outcome-driven tuning. The September overlap comparison has deliberately not been
computed so it cannot influence that decision.

## Options for the supervisor (no action taken)

A. Keep monotonicity as a hard gate -> the October construction cannot be accepted -> stop weather acceptance and fitting
   (spec: investigate, no fallback).
B. Record monotonicity as an evidence diagnostic (counts/magnitudes as above) and bind tp accumulation semantics by provider
   documentation + endpoints/units/validity (as the supervisor's earlier note describes), keeping the September overlap gate and
   its already-coded metadata-derived bounds unchanged as the acceptance criterion. If that gate then fails, stop as specified.
C. Another rule decided a priori (e.g. an explicitly justified upstream-quantization term) before the overlap is computed.

The executor recommends a decision before any September comparison is run.
