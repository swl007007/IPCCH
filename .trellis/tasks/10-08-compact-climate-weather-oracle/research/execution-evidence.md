# Execution evidence: seven-run compact suite and final verification (2026-10-08/09)

Executor: Claude Opus 5.5 (1M), Herdr w11:p4. All fits at committed implementation `40060dd4135cd301347f63ffddaa63384b07264c`
with unchanged committed fitting code at both launches. The pilot launch had a clean worktree; the full-suite launch
recorded only the two untracked pilot-evidence files (`research/pilot-check.json`, `research/pilot_check.py`).
`results/experiments/compact_climate_weather_oracle_v1/logs/launch_records.jsonl` records HEAD, porcelain, fit-code sha256
and runtime. Inputs: build 2 (planning HEAD 928d080 + uncommitted implementation,
recorded in its manifest), manifest sha256 `456360536a3929e1571d96ba9f16e2f0de54bc1b20019f797bbe62c0c89732ca`.
Fit-code sha256 unchanged from launch to final verification. Runtime: Python 3.12.3, NumPy 2.4.4, pandas 3.0.3,
scikit-learn 1.8.0, XGBoost 3.2.0 (`/home/swl007007/.venvs/ipcch-geo/bin/python`); seed 42, half-life 24, threshold 0.2, n_jobs 16.

## Commands, exit codes, resources

| step | command | exit | wall / peak RSS |
|---|---|---|---|
| pilot (first suite batch) | `PYTHONPATH=src /usr/bin/time -v ~/.venvs/ipcch-geo/bin/python scripts/modeling/run_compact_climate_weather_oracle_suite.py --runs compact_baseline/0m --block-years 2022` | 0 (PARTIAL by design) | 41.0 s / 1.55 GB; batch 23.2 s |
| pilot checks | `PYTHONPATH=src ~/.venvs/ipcch-geo/bin/python .trellis/tasks/10-08-compact-climate-weather-oracle/research/pilot_check.py .trellis/tasks/10-08-compact-climate-weather-oracle/research/pilot-check.json` | 0, passed | 4 models reloaded, max replay diff 0.0; fit keys/ages/weights == parent reference protocol |
| full suite | `setsid nohup bash -c 'PYTHONPATH=src /usr/bin/time -v ~/.venvs/ipcch-geo/bin/python scripts/modeling/run_compact_climate_weather_oracle_suite.py'` (PID 679187) | 0 | 14:46 / 2.01 GB; 7 runs COMPLETE, 110-137 s each; batches 22-34 s, <= 1.97 GB; pilot batch resumed ("verified existing batch"), not refit |
| final verifier | `setsid nohup bash -c 'PATH=/tmp/ipcch-windows-git-bin:$PATH PYTHONPATH=src /usr/bin/time -v ~/.venvs/ipcch-geo/bin/python scripts/postprocessing/verify_compact_climate_weather_oracle.py --stage all'` | **0, passed=true, problems=[]** | 3:53 / 4.43 GB |

Logs: `results/experiments/compact_climate_weather_oracle_v1/logs/` (pilot_suite.log, full_suite.log, per-run logs,
suite_ledger.jsonl, verify_all.log, launch_records.jsonl, *.pid). Per-batch timing: `verification/batch_timing.csv`.

## Final verification (verification/verification_summary.json)

- Runs 7/7, batches 28, models reloaded 112 (all four years of every run), max model replay |diff| 0.0 (tolerance 1e-6),
  artifacts re-hashed 168, fitting rows checked 740,622; fitting keys/ages/weights equal across arms and equal to the parent
  reference protocol for every (H, year).
- Fingerprints recomputed from current state for all 7 runs: payload, digest and every batch fingerprint match.
- Metrics: 2,800 cells (7 runs x global + regions 0-8 x 2022-2025 + pooled x 8 metrics) replayed with scikit-learn,
  atol 1e-12, identical undefined masks; runner global metrics also match the replay. Regions partition every prediction
  row exactly once (`comparison_metadata.json`); region map sha256 18ab5099...611d; no bootstrap, no regional training.
- Inputs re-verified in the same run: 372,800 independent exact-arithmetic feature cells, 0 mismatches; oracle replay from
  source exact; baseline projection parity; pinned sources/cohort/contract equal frozen references.
- Actual-input codebook verified: 308 rows, expected == actual positions for all 7 runs; every run's fitted feature hash
  equals the frozen contract (`model_run_index.csv`).
- Legacy no-overwrite: 740/740 files unchanged.
- Undefined metric cells: 56 cells from empty region-year groups (7 runs x 8 metrics, "no eligible samples") and one "zero f2
  denominator" cell (`verification/undefined_reasons.csv`).

## Headline global pooled 2022-2025 (point estimates, single seed, no intervals)

| H | arm | exact acc | 3+ acc | prec 3+ | recall 3+ | F2 3+ | R² 3+ | MAE 3+ | ordinal MAE |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | baseline | 0.6485 | 0.7946 | 0.7498 | 0.8705 | 0.8433 | 0.5214 | 0.0887 | 0.3598 |
| 3 | oracle - baseline | +0.0060 | +0.0094 | +0.0161 | -0.0076 | -0.0018 | +0.0018 | -0.0003 | -0.0066 |
| 6 | oracle - baseline | -0.0046 | -0.0024 | -0.0117 | +0.0239 | +0.0144 | +0.0042 | -0.0001 | +0.0053 |
| 12 | oracle - baseline | +0.0101 | +0.0114 | +0.0060 | +0.0230 | +0.0188 | +0.0257 | -0.0012 | -0.0128 |

Full annual/regional tables: `reports/compact_climate_weather_oracle_v1/report.md`, `verification/{global,regional}_{metrics,deltas}.csv`.
Differences are single-seed point estimates; sign changes across years and regions are common (e.g. H6 pooled exact accuracy
is lower with the oracle while recall/F2 are higher), and small regions (6: 310 rows, 8: 29 rows) are unstable.

## Unresolved limitations

- No intervals/bootstrap (out of scope); annual and regional differences are not significance statements.
- Availability proxy = observation month; release vintages and climatology-fitting samples unverified.
- Near-constant but non-identical source histories keep finite, possibly huge same-month z (approved; no clipping).
- D16 changes missingness relative to older versions (H0/H3/H6 restored 184,203/179,835/83,784 cells), so comparisons with
  the old full-feature runs are not attributable to feature deletion alone.
- Origins after a source grid's last month would blank windows; none in the frozen cohort; future cohorts out of scope.
- `rollback.md` post-implementation section is owned by Codex.

## Output hashes (sha256)

```
57fbaecf0b270be2cd29175a21058b3ceeee4c42282917e6b2a1139726e04ab0  results/experiments/compact_climate_weather_oracle_v1/verification/verification_summary.json
c3a92268159ee525cf2f518357b22ec76f4bd7eac194ace58e3bc6996d8c0d2a  results/experiments/compact_climate_weather_oracle_v1/verification/global_metrics.csv
0a811ac9c8da0180fa9c0908a18b89ea86797e4bc04b9ef369567cf0a7f9c27e  results/experiments/compact_climate_weather_oracle_v1/verification/global_deltas.csv
af4eae407cb1c81c03c023e002bdaabe2e507a1a3d7aa628a7559faa187a8d10  results/experiments/compact_climate_weather_oracle_v1/verification/regional_metrics.csv
c39198341e68b0db04c2bf5cb4302ce2091d8daf0f92ca034a051039a363d74e  results/experiments/compact_climate_weather_oracle_v1/verification/regional_deltas.csv
fb4bb1384485bafe36fcfe8640eb449ea2ad263ef9ae73f661837fc88fbebaf2  results/experiments/compact_climate_weather_oracle_v1/verification/all_metrics_long.csv
58bfc9b6a9c0a17cf14df1e01c2687c0022a838d85e00b06f98311040fff9a85  results/experiments/compact_climate_weather_oracle_v1/verification/comparison_metadata.json
0e98fc8734a9678ebc237ee4dc1b23cb7f1b3ecb13dca993d22ea9067908ff96  results/experiments/compact_climate_weather_oracle_v1/verification/artifact_inventory.csv
357e7ab361b62e7b18fb1d5420e4e548608804815131a44cdf1305537badc9ed  results/experiments/compact_climate_weather_oracle_v1/verification/undefined_reasons.csv
a53553985b858ecb60d752fce90477e54fa9227f3d8f685d5a3a4699ee100ced  results/experiments/compact_climate_weather_oracle_v1/verification/batch_timing.csv
337cb2c74fd9f6f8fb442424911f6f658f356e3649a7a788fe297b330b94cdd9  results/experiments/compact_climate_weather_oracle_v1/verification/legacy_hash_inventory_after.csv
a7317a58777d59cb71d30b50067954675ab569f084d7988f3550f7814ada5e0e  reports/compact_climate_weather_oracle_v1/report.md
d3946f2509d9e60d8b6590a75c47c4fdd3da9ffc93d6473694c34d99249060dd  reports/compact_climate_weather_oracle_v1/model_run_codebook/IPCCH_compact_climate_weather_oracle_model_run_codebook_en.csv
84080e7e928784ce4f1ef203e3177fb4f8b9ef809a5e1b3f63a54fbf39ba13d1  reports/compact_climate_weather_oracle_v1/model_run_codebook/expected_vs_actual_inputs.csv
734129be190e3bf7cd982ec4b67966d31fdad8b65a22c3f938caa28bd34e2cec  reports/compact_climate_weather_oracle_v1/model_run_codebook/model_run_index.csv
948ea12a5b32199acfd833906a6fb705aed6248dfdd674d0a064ed5664e47ab3  results/experiments/compact_climate_weather_oracle_v1/runs/compact_baseline/0m/run_metadata.json
b61008794da8d59051082b51450342a3671db4968e8e24f96d7b4a92bb706e33  results/experiments/compact_climate_weather_oracle_v1/runs/compact_baseline/12m/run_metadata.json
bd1e69e8ee6ac9f6b12e99960a847d586e52a97e5767dce78ef533aa4fb542d7  results/experiments/compact_climate_weather_oracle_v1/runs/compact_baseline/3m/run_metadata.json
9d9b8866b07b0d3477ee3419f28a943218e65e90de914dc9935498902b84c158  results/experiments/compact_climate_weather_oracle_v1/runs/compact_baseline/6m/run_metadata.json
097a9967f9fd55bdc081ab78549a3f902e9840d7c267de5663e7d31200d14ac4  results/experiments/compact_climate_weather_oracle_v1/runs/compact_weather_oracle/12m/run_metadata.json
75c723c5ecae7afbae0b356db14756504f7195de67802d8410721c62c8a889ef  results/experiments/compact_climate_weather_oracle_v1/runs/compact_weather_oracle/3m/run_metadata.json
29f130de674a5f44a42f6d1a7c7ac9f0fbd2a3127f9fb24d7cd72008e93e4579  results/experiments/compact_climate_weather_oracle_v1/runs/compact_weather_oracle/6m/run_metadata.json
c5622d18ca6c2528f94e24d6e79aa242ffe1d328dd593b33c53e2eb338b9b11f  results/experiments/compact_climate_weather_oracle_v1/runs/compact_baseline/0m/metrics/metrics_overall.csv
c1645fae700dc4b000c4559adab0acf7d68493b3db1f401e94d5420b1740d2e6  results/experiments/compact_climate_weather_oracle_v1/runs/compact_baseline/12m/metrics/metrics_overall.csv
4002d18ad35be166498d71be2bea28c859552fd06ab5f2f82b30d12f9ddad341  results/experiments/compact_climate_weather_oracle_v1/runs/compact_baseline/3m/metrics/metrics_overall.csv
395e49600ba96fb9b413a99e944280b222843d73d4a5a5dbc03e5fc66d9c80d0  results/experiments/compact_climate_weather_oracle_v1/runs/compact_baseline/6m/metrics/metrics_overall.csv
6728b41422fe12a8463c36d7e2095a26d0e32023209030636569ad570192864d  results/experiments/compact_climate_weather_oracle_v1/runs/compact_weather_oracle/12m/metrics/metrics_overall.csv
46fff337a5637dbd66b6ae1613c30e071594059c12469e03f72c607b4edec425  results/experiments/compact_climate_weather_oracle_v1/runs/compact_weather_oracle/3m/metrics/metrics_overall.csv
47b7cdb77e0ab9b6a3deea7bdf84ee564c43e00f5acc1e783153d0e88aeb4a7e  results/experiments/compact_climate_weather_oracle_v1/runs/compact_weather_oracle/6m/metrics/metrics_overall.csv
```
