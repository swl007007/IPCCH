# Supervisor review during implementation

Recorded 2026-10-09 UTC. This is the authorized supervisor/executor checkpoint workflow, not an additional audit registration or final acceptance. Planning HEAD: `b19d36d210bcb59ca090b9e1e961657225f44d39`; executor remains Herdr `compact-cds-executor`, pane `w11:p4`, Claude session `579e6ba5-f2a2-483c-b465-4b2e3cca1ed3` (actual UI: Opus 5.5, 1M).

## Confirmed observations

- Current preflight acceptance is limited to pinned sources/runtime/cohort/static/population/mappings/geometry (`supervisor-preflight-check.json`). It does not accept weather, assembled matrices, fitted models or reports.
- A read-only scout verified the five earlier weather boundary fixes at weather SHA256 `626f16554b0378cd0dc46830d676095b141ae74e6c340830bee4ffbb98c6ede4`: exact five-probe coverage; system/date/member/step identity; half-degree-centred 1-degree grid; rehash cached bytes and retain request IDs on redownload; persist provider status before a failed download. Main-session source spot checks agree. Code has since progressed, so this hash is a review snapshot, not the final implementation pin.
- Real probe files exist and the executor's strict probe report passed. Supervisor independently ran the three planned focused test files in the frozen model interpreter: **31 passed in 5.76s**, with seven code/test hashes unchanged during the run (`supervisor-focused-tests.json`). Subsequent map-path changes require an updated check; these tests do not certify real weather overlap or production artifacts.
- The complete retrieval has 28 recorded request IDs. At 05:32 UTC, nine downloads existed and the remaining provider requests were accepted/running. The durable bulk poller is PID 1571221. Requests, logs and raw data live only in the new version root. No supervisor API request was submitted.
- Main-session actual first-message GRIB checks confirmed April 1 00 UTC, system 51/method 1, temperature K, precipitation m, and correct September endpoint timestamps. Original precipitation GRIB1 encodes a single forecast time (`stepType=instant`, `startStep=endStep`); its accumulation interpretation comes from the provider definition and must be checked by endpoints and the September overlap. These spot checks are not full member/time coverage.

## Findings sent to the bound executor

1. Require per-message initialization time, parameter/units, validity-step and official statistical-month semantics. Interpret precipitation using documented GRIB1/provider semantics rather than erroneously requiring a GRIB2-style accumulation start of zero. Current source now contains `message_semantics_problems`; actual full-file evidence and focused regressions remain to be accepted.
2. Freeze September overlap bounds from the samples/endpoints used by September, with independent packing/reduction justification, before inspecting differences. Complete September/October data and actual overlap evidence remain outstanding.
3. Main-session synthetic reproduction: `save_csv` on a table containing Namibia's literal `lookup_code_used="NA"` raised `LaunchError: CSV round trip changed cap.csv`. Preserve the literal alongside true missing values; final corrected regression remains to be checked.
4. Independently verify all phase 1–5/P3+/P4+ shares/counts, raw/effective denominators, all four aggregation levels and all four paired-difference tables. The initial verifier checked only selected P3/P4 aggregates. Require finite model replays, exact expected map inventory/coverage and undefined-mask handling.
5. Demonstrate future-source perturbation invariance and March-only inference IPC history with a small synthetic check, plus the real keyed history/IDP/season ledgers.
6. After the 31-test snapshot, supervisor reproduced a continuous-map join failure: `load_spatial_boundaries` normalizes `area_id` to strings, while the new area's `area_id` is integer. `boundaries.merge(sub, on="area_id")` raises a pandas string/int64 merge error. Normalize the map join consistently, preserve saved table keys, and exercise the real seven-output map path with a tiny synthetic geometry fixture. This remains a routine implementation finding, not an external blocker.

## Gate status

**Heavy fitting gate remains closed.** Await complete code/focused tests, accepted six-month weather cube with overlap provenance, and validated complete compact input checkpoint. After acceptance, commit implementation, run and replay shared H0 pilot, then obtain supervisor go-ahead for the remaining four sequential fits. Final A1–A9 acceptance, all 20 models, tables/maps/codebook and old-artifact after checks remain pending.
