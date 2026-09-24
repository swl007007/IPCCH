# Evidence — somalia-flood-food-crisis

Evidence Status: Ready. Validation Status: Executed (commands and outcomes below).

## Runs

| Run | Code | Command | Outcome |
|---|---|---|---|
| Evidence run | commit `a0c792e65ed6` (implementation; only Trellis metadata/spec files dirty, listed in `run_manifest.json`) | `PYTHONPATH=src ~/.venvs/ipcch-geo/bin/python -u -W ignore scripts/modeling/run_somalia_oracle_experiment.py --workers 14 --overwrite` | exit 0, 3,454 s; 75 fitted arm jobs + 5 H=0 C reuses, all `completed` (`arm_job_status.csv`) |
| Replay | same | `PYTHONPATH=src ~/.venvs/ipcch-geo/bin/python scripts/postprocessing/replay_somalia_oracle.py` | exit 0, 480/480 checks (`replay_checks.csv`) |
| Reproducibility | pre-commit run (same algorithm; later commit only added a worker exception guard, a V2 area-coverage assertion and a manifest note rename) | same CLI, 16 workers | predictions/metrics/contrasts byte-identical after decompression (sha256 prefixes 7ba2ff4a…, 1310671f…, e7f73a48…) |
| Prepare artifacts | final code vs evidence run | `--prepare-only` | label/cohort/weather ledgers, jobs, schemas and all four feature matrices identical |

Runtime (`run_manifest.json`): Python 3.12.3, numpy 2.4.4, pandas 3.0.3, scikit-learn 1.8.0, xgboost 3.2.0, `~/.venvs/ipcch-geo`, 32 CPUs. Input sha256 (prefix): fs0 221a559e90d0, fs1 fa19b03d28f2, fs2 5af7d7d1f587, fs3 a5b452035f55, raw ae696087c3bb (matches the IPCCH_shared_folder manifest), lookup e2baf6ae9481, V2 fda5f0a0605d. Candidate config and history schema hashes are in the manifest. Full machine outputs: `results/experiments/somalia_oracle/v1/` (gitignored; predictions, models with sha256 inventory, ledgers, fits, bootstrap draws). Human report: `reports/somalia_oracle/v1/summary.md` (copied here as `results_summary.md`).

## Tests

- `PYTHONPATH=src ~/.venvs/ipcch-geo/bin/python -m pytest tests/unit/test_somalia_oracle.py -q` → 20 passed (includes exact parity of the 468 ported history columns with the pinned reference `Food_Crisis_Cluster@85bc505a5b99` for H>=1).
- `PYTHONPATH=src ~/.venvs/ipcch-geo/bin/python -m pytest tests/smoke/test_somalia_oracle_pipeline.py -q` → 1 passed (806 s; synthetic end-to-end CLI with tiny fits).
- Full suite without the smoke test: 12 failed / 230 passed; the same 12 failures occur on the pre-change tree (12 failed / 210 passed), in alert-risk-map and launch CLI tests unrelated to this task.

## Acceptance mapping

| AC | Evidence |
|---|---|
| AC1 | `jobs.csv`, `arm_job_status.csv`: arms A–D × folds 2025/2026 × H 0/3/6/12; H=0 C rows carry `reused_from=B`; smoke test asserts H=0 B/C prediction identity and identical schemas. |
| AC1b | `ledgers/label_ledger.csv.gz`: raw components, `raw_sum`, p1–p5, q2–q5, `normalization_changed` (414 valid rows), unchanged `overall_phase`; unit test on area 1981/2026-04 (.15,.25,.60,.25,0 → .12,.20,.48,.20,0). |
| AC2 | `fits/final_fit_ledger.csv.gz`: 0 fit labels after the outer origin, 0 in/after the test year, min fit year 2022. `inner_folds.csv`: 0 supported folds with fit labels after `min(v−H, v−1)`; 0 unsupported folds. |
| AC3 | `features/feature_schema.json` (B adds exactly the 14 ensemble means); `row_provenance_h*.csv.gz` season keys/dates; 0 selected seasons ending after the month-end boundary; unit test for cross-year/exclusive-end/no-prior/incomplete-export cases. |
| AC4 | `ledgers/oracle_weather_ledger_h*.csv.gz`: offsets {1..3} at H=3, {1..6} at H=6/12, none at H=0; 0 months ≤O, >O+6 or >T. Weather verification ledger: 46,192 verified / 11,712 exact previous-month repeats since 2021. |
| AC5 | History alias resolution in `configs/somalia_oracle_history_schema.json`; six source-month slots per row in `row_provenance_h*`; 0 history sources ≥T or >O at every H; reference parity test. |
| AC6 | `candidate_scores.csv` (6 candidates × each arm job, pooled TP/FP/FN, F2), `inner_folds.csv`, `configs/somalia_oracle_candidates.json` (threshold 0.2, half-life 24, weights anchored at each fit origin). |
| AC7 | `ledgers/cohort_ledger.csv.gz` frozen during preparation (before any fit); metrics include phase-1 rows; `replay_checks.csv` recomputes phase from raw predictions and metrics with scikit-learn. |
| AC7b | `persistence_subset` rows in `metrics.csv`/`contrasts.csv`; persistence source month/age/status in `row_provenance_h*`; 0 persistence sources ≥T or >O. |
| AC7c | `always_crisis` rows on primary and persistence cohorts with confusion counts and prevalence. |
| AC7d | `contrasts.csv` + `bootstrap_draws.npz` (ordered areas, cohort keys, multiplicities, per-draw deltas); replay recomputes every interval; all intervals `ok`, no undefined draws. |
| AC8 | `coverage_summary.csv`, `results_summary.md` caveats; 2026 reported as April 2026 only; unavailable cells (2026 H=3/6: no verified oracle rows) retained. |
| AC9 | `run_manifest.json` (git HEAD, runtime, input sha256, written-artifact sha256), model inventory with sha256. |
| AC10 | Planning commit `83d4d78`; audited start run `e21d6f75672d` base `476de007`; close/audit records follow. |

## Implementation-vs-design drift (recorded, not hidden)

- Bootstrap area order is ascending numeric (design text updated; the saved area list is authoritative).
- Preflight resolutions in `implement.md` (blocked `overall_phase_lag1`/`estimated_population`, weather verification rule, model-ready ledger choice, 2026-01 exclusion, materialized aliases) are implementation decisions derived from `research.md` addendum A.
- Oracle months that fail verification on fitting/validation rows are NaN features (rows retained); only evaluation rows require all oracle months verified.
- Wider labeled cohort metrics are reported for A/B only (C/D require verified oracle weather by design).

## Result headline (see `results_summary.md`)

Within-year/horizon contrasts are small and mixed: no enhanced arm consistently beats A or the always-crisis reference on F2; every arm beats persistence on its supported subset. Crisis prevalence is high (≈0.49–0.61), so always-crisis F2 is 0.83–0.89. These are conditional, two-year results with restricted oracle cohorts at H>0.
