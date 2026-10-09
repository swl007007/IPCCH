# September overlap: temperature time-window finding (2026-10-09 06:15 UTC)

Status: **evidence for a supervisor decision; no cube accepted; no inputs assembled; no fitting.**

## Diagnostic run

`PYTHONPATH=src <CDS_API>/.venv/bin/python .trellis/tasks/10-08-compact-cds-launch/research/september_overlap_diagnostic.py`
-> exit 0, 3:41 wall, 494 MB. Independent re-aggregation of all 28 downloaded files (production decode helpers, production
bound rule unchanged). Bounds frozen to `CDS_API/compact_cds_launch_v1/diagnostic/overlap_bounds_frozen_diagnostic.json`
(sha256 `769458525feb838bbf8e57e9f21673300286dfe6fb0fb7c0c1aed2f69d9b2af3`, 06:15:25 UTC) before any comparison.
Copies: `research/overlap_bounds_frozen_diagnostic.json`, `research/september_overlap_diagnostic.json`; per point
`diagnostic/september_overlap_by_point_diagnostic.csv`. Completeness: all 120 September samples per member and both
precipitation endpoints present for 51 forecast and 24 x 25 hindcast members.

| variable | frozen bound | max abs diff | points over bound (of 6,227) | max / bound |
|---|---:|---:|---:|---:|
| precipitation (end - start, as rate) | 9.60e-11 m/s (0.249 mm/month) | 4.25e-12 m/s (0.011 mm/month) | 0 | 0.044 |
| temperature, frozen convention [Sep 1 00, Oct 1 00) UTC | 0.002259 K | 0.01339 K | 3,250 | 5.93 |
| temperature, (Sep 1 00, Oct 1 00] UTC (diagnostic only) | 0.002259 K | 0.000551 K | 0 | 0.24 |

Frozen-convention temperature differences: median 0.0024 K, p99 0.0105 K, signed mean 2e-5 K (symmetric; consistent with
swapping one 00 UTC sample at each end of the month, not a bias or index error).

## Interpretation (evidence, not a decision)

- Precipitation passes the unchanged gate by a factor of ~23, despite the tp endpoint decrements, so the raw end-minus-start
  recipe reproduces the official September rate anomaly.
- Temperature fails under the initially frozen window [month start, next month start) but agrees within the same frozen bound
  at every point under (month start, next month start], i.e. the 06/12/18 UTC samples of the 1st through 00 UTC of the first day
  of the next month. That is the same interval-end convention as the precipitation accumulation (P(next month start) -
  P(month start)) and as the GRIB validity encoding (statistical fields valid at the interval end).
- No primary ECMWF/C3S document found states the 6-hourly window: ECMWF Set V says monthly means use the 00/06/12/18 UTC write-up
  times (https://www.ecmwf.int/en/forecasts/datasets/set-v); the C3S product description says monthly statistics are
  computed from the original sub-daily data for each calendar month
  (https://confluence.ecmwf.int/spaces/CKB/pages/340775655/C3S+seasonal+forecast+product+descriptions). Neither states the
  boundary sample.
- The spec (design: "Verify provider timestamp semantics and freeze the exact rule before acceptance"; time-window mismatch
  stops October acceptance) anticipates exactly this verification. Changing the convention now would be informed by the
  September comparison, so it is a supervisor decision, not an executor change.

## Options (no action taken)

A. Keep [start, end): the gate fails -> weather rejected -> fitting closed (spec stop).
B. Adopt (start, end] as the verified provider convention for both September validation and the October construction, citing
   this overlap evidence plus the interval-end consistency with precipitation, record it as a post-verification rule in
   provenance, and rerun the unchanged gate (same bound formula, freshly frozen before comparison).
C. Another explicitly documented convention source before any rerun.

The production v2 run under decision B (monotonicity as diagnostic) keeps the frozen [start, end) convention; its outcome is
reported separately and is expected to reject on temperature for the reason above.

## Addendum (06:35 UTC): production v2 result, GRIB metadata and the independent absolute-monthly probe

**Production v2 (decision B, unchanged frozen [start, end) convention):** `--weather-only --process` exit 1, 8:53 wall, 230 MB.
Identity 28 files / 0 problems; bounds frozen `processed/overlap_bounds_frozen.json` (sha256 `9c9eec37…`) before comparison;
gate: temperature max 0.013390422322402173 K vs 0.002259 K, 3,250 points over; precipitation max 0.011 mm/month vs 0.249
mm/month, 0 over -> **REJECTED: September overlap outside frozen bounds**. Identical to the independent diagnostic
(same max to all digits, same count). tp monotonicity recorded as diagnostic only: 176 beyond-bound cases at launch cells,
worst -0.143 mm (`processed/tp_monotonicity_diagnostic.csv`). Preserved: `CDS_API/compact_cds_launch_v1/rejected_v2/`
(provenance sha256 `cb617318…`, log, code pins weather `fc9c2af5…`); v1 in `rejected_v1/`.

**GRIB monthly metadata** (`research/monthly_t2m_metadata_capture.py/.json`): official anomaly and old absolute monthly 2t
messages are GRIB1 local definition 16, `averagingPeriod` 6, `timeIncrement` 6, `typeOfTimeIncrement` 3 (a transient ecCodes
conversion key per upstream local.98.16.def, supervisor note: not proof), encoded forecast time/validity at the next-month
boundary (September: endStep 4392, validity 2026-10-01 00 UTC); `numberOfTimeRanges` undefined in GRIB1. Original 6-hourly
support is contiguous 3672..5136 for 2026 and 1993 member 0, including both boundary samples. Supporting metadata only.

**Independent baseline-free probe** (`research/absolute_monthly_timestamp_probe.py`, results `research/absolute_probe_result.json`,
per point `diagnostic/absolute_probe_by_point.csv` sha256 `fc592cb9…`): official absolute monthly ensemble mean (old file
`c3s_seasonal_apr2026_all_leads.grib` sha256 `b657fcbe…`, message 11: ecmf, system 51, method 1, marsType em, stream msmm,
init 2026-04-01 00 UTC, verifyingMonth 202609, K) vs the 51 2026 forecast members alone (no hindcast, no anomaly). Bounds frozen
first (`diagnostic/absolute_probe_bounds_frozen.json`, sha256 `61fa2ba8…`): 0.002083 K for both conventions.

| convention | max abs diff | mean signed | points over bound (of 6,227) |
|---|---:|---:|---:|
| [Sep 1 00, Oct 1 00) | 0.0834 K | +0.0003 K | 5,290 |
| (Sep 1 00, Oct 1 00] | 0.00129 K | -0.0002 K | 0 |

Two independent official products (absolute monthly mean, and anomaly vs the 1993-2016 hindcast) agree within metadata-derived
bounds at every point only under (start, end], and both reject [start, end). No primary document states the boundary sample.
Decision on the October/September temperature convention remains with the supervisor; no production code has been changed.
