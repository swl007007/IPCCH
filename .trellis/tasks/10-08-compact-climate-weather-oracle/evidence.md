# Compact climate and raw weather-oracle acceptance

Evidence Status: Ready
Validation Status: Executed and passed

Approved planning commit: `928d08081376311b298358cbad5eb8b21ad7fc35`.
Implementation commit: `40060dd4135cd301347f63ffddaa63384b07264c`.
Executor: verified Claude Opus5.5,1M context, Herdr `w11:p4`, session
`579e6ba5-f2a2-483c-b465-4b2e3cca1ed3`. No additional Trellis audit enrollment or lifecycle calls.

## Acceptance trace

| Criterion | Concrete validation |
|---|---|
| A1: literal fitted inputs | Seven ordered metadata schemas and112 reloaded boosters exactly match the approved contract: baseline296 at every H; oracle302/308/308. Actual codebook308 union rows, no extra predictors; all expected-vs-actual positions match. |
| A2: recipes and timing | Focused93-test checkpoint; source-support checks; independent exact-arithmetic replay of372800 sampled feature cells with0 mismatches; frozen source/contract/runtime/config hashes checked. This is sampled recipe replay, not a full formula replay of every input cell. |
| A3: completed seasons and major | Focused boundary/tie/missing-pair tests, source-derived season identity/duration ledgers and independent sampled seasonal replay. Latest-season major shares the selected climate record. |
| A4: input parity and coverage | Full serialized oracle baseline projections equal compact baseline; parent keys/labels/background preserved. D16 mask restorations and numerical corrections are recorded separately. Raw oracle columns independently replayed from source. |
| A5: complete fitting | Seven COMPLETE runs,28 batches,112 UBJ models; pilot resumed without refitting. Full replay checked740622 fitting rows, keys/weights/targets and all model bundles. |
| A6: global and regional scoring | All2800 metric cells independently replayed with matching undefined masks; all120 global and1080 regional deltas checked. Every row belongs to exactly one region0–8. Empty/small groups retained; pooled metrics computed from pooled saved rows. |
| A7: actual codebook and provenance | Codebook status `fitted_verified_all_batches`; actual membership/order checked against saved models. Supervisor freshly rehashed203 artifact inventory entries and pinned final tables/report/codebook hashes. Legacy740/740 files unchanged; rollback selections validated. |

Detailed machine-readable acceptance: `research/supervisor-final-acceptance.json`.
Separate read-only fitted-model and prediction/region checks: `research/final-readonly-checks.json`.
Executor commands/resources/output hashes: `research/execution-evidence.md`.
Focused test command and exit0/93-pass record: `research/supervisor-test-checkpoint.json`.

## Explicit deliverables

- Report: `reports/compact_climate_weather_oracle_v1/report.md`.
- Actual English codebook and run index: `reports/compact_climate_weather_oracle_v1/model_run_codebook/`.
- Global/regional annual and pooled metrics and oracle-minus-baseline deltas:
  `results/experiments/compact_climate_weather_oracle_v1/verification/{global,regional}_{metrics,deltas}.csv`.
- Complete verification: `results/experiments/compact_climate_weather_oracle_v1/verification/verification_summary.json`.
- Input manifest: external `assembled_IPCCH/model_ready/compact_climate_weather_oracle_v1/compact_climate_weather_oracle_v1_manifest.json`,
  SHA256 `456360536a3929e1571d96ba9f16e2f0de54bc1b20019f797bbe62c0c89732ca`.
- Version selection/rollback: `rollback.md`, execution appendix; approved contract copies remain in the external input namespace.

## Scope and limits

No bootstrap,B6,retuning,SHAP or regional fitting. No legacy refits or overwritten historical artifacts. Configured lint/type
checks are absent from pyproject.toml; none are claimed. Product code remained unchanged after the implementation commit.

Both input builds retain truthful planning-HEAD/uncommitted-code provenance. Pilot fitting launched from a clean worktree;
full-suite launch recorded only two untracked pilot evidence files, with identical committed fitting code. Supervisor corrected
the executor evidence's initial clean-worktree wording and empty-group metric-cell count; no scientific artifacts were changed.

The oracle assumes realized future weather available at origin. Observation months proxy availability; historical release
vintages and upstream climatology-fitting samples are unverified. Near-constant non-identical histories retain potentially huge
finite z values without clipping. D16 changes missingness as well as membership, so old-versus-new differences are not attributable
to feature deletion alone. All reported contrasts are single-seed point estimates; no intervals or significance statements.
