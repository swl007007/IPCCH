# Supervisor implementation checkpoint review

Reviewed on 2026-10-08 before real experiment fitting. This is task implementation verification, not an additional Trellis audit registration or lifecycle.

Two one-shot read-only scouts inspected compact recipe/prefit and replay/report paths. Codex read the approved foundations and checked the reported source locations. The existing Claude Opus5.5 1M executor at Herdr `w11:p4` remains the sole implementation writer.

## Confirmed input evidence

- Seven literal ordered schemas match the approved contract:296/296/296/296/302/308/308.
- Four baseline key/label/background blocks equal the corresponding frozen parent numerically including NA; oracle baseline projections equal the rebuilt baseline exactly after round-trip parsing.
- Focused executor regression reports85 passed. Read-only scout recipe tests24 passed and existing climate tests12 passed.
- The first independent input replay failed:372,800 cells checked,20 mismatches, including cdd z-MAs and WFP SD12. Log: `results/experiments/compact_climate_weather_oracle_v1/logs/verify_inputs.log`. Tolerances must not be relaxed to conceal formula/implementation differences.
- Legacy inventory before/after:740 files,0 changed/added/removed.

## Repairs requested through Herdr

1. Investigate exact windows/histories and floating point algorithms behind20 mismatches; reproduce before fixing approved formulas. Preserve legacy helpers/stress, genuinely nonconstant small variance and the failed build evidence.
2. `verify_compact_climate_weather_oracle.py:write_report`: replace multi-index `pivot_table(dropna=False)` Cartesian expansion with a real-group pivot; no fabricated oracle H0 groups.
3. Rehash all pinned sources/cohort/contracts; enforce frozen runtime/config/helper identities in the compact prefit path and bind full expected fingerprint and canonical digest during final verification.
4. Include fitting runtime/interpreter and the actual forecasting metric helper in compact-only resume fingerprints; keep legacy fingerprint behavior.
5. Do not label an actual codebook `fitted_verified_all_batches` when full verification contains failures.
6. Make suite dry-run perform no output mutations, consistent with its declared contract.

## Scoped limitation

For an origin beyond a source grid's global final month, the current gather also blanks trailing summaries even if historical support suffices. The frozen cohort has no such origin: interim ends2026-04, climate ends2026-08, target universe ends2026-04. Record this boundary; do not add future-cohort behavior to the current experiment.

The implementation remains unaccepted for real fitting until repaired tests and input verification pass. This internal supervisor checkpoint is covered by the user's existing execution approval and requires no new user permission.

## Repaired checkpoint accepted

All requested current-scope repairs were checked in source and by two further one-shot read-only numeric/identity scouts.
Supervisor full focused regression:93 passed in58.25s. Current build2 input verification:372,800 independent feature cells,
0 mismatches;740 legacy artifacts unchanged; sources/cohort/contract identities rechecked. Main verified current helper bytes,
manifest SHA `456360536a3929e1571d96ba9f16e2f0de54bc1b20019f797bbe62c0c89732ca`, stable copied contracts and frozen runtime.
Actual legacy baseline/H0 and raw-oracle/H3 dry-runs passed (870/876 features) without producing outputs. Seven compact
dry-runs passed without file changes. Numeric scout checked34,740 additional in-memory cells against exact Fraction
statistics. Formula replay samples400 rows per horizon; this is not a claim of independent formula replay of every input cell.

The failed first build is preserved. No real experiment fit has run. The executor settled at this checkpoint and will
continue the approved pilot/full suite after the supervisor's implementation commit; final acceptance still requires
all28 batches/112 models and complete prediction/metric/codebook verification.
