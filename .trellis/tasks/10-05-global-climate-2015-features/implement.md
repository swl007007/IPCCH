# Implement plan: climate2015_v1

## Checklist

1. `git switch -c feat/global-climate2015-features` from clean `main`.
2. `src/ipcch/climate2015_features.py`: the forked engineering helpers (shift, rolling as of anchor, trend, dispersion, stress spells, same-month history, neighbours, seasonal last-k) parameterized by anchor; the old-column detector; the variable lists and thresholds.
3. `tests/unit/test_climate2015_features.py`, synthetic panels:
   - anchor safety: perturbing months after `t−a` leaves features unchanged;
   - season completion rule and last-2 ordering;
   - threshold signals with NaN propagation;
   - old-column detector counts on a header fixture.
4. `scripts/preprocessing/build_climate2015_model_ready.py`:
   - loads the climate inputs (with sha256) and each scope file;
   - drops old columns and asserts the removal counts;
   - joins the new features on (area_id, year, month);
   - asserts row-key parity;
   - writes the dataset, `feature_manifest.csv` and `build_summary.json`;
   - supports `--scopes`, `--sample-areas` for smoke runs, and `--overwrite`.
5. Fidelity check script `scripts/preprocessing/check_climate2015_fork_fidelity.py`: recompute the FLDAS families on a seeded area sample from the interim panel and compare with the current fs0. Write `fidelity_report.csv` under the task `evidence/` folder.
6. Smoke test: build with `--sample-areas 50`, then run the CLI `--dry-run` on one sampled scope.
7. Full build of the four scopes.
8. Eleven runs, sequential, in the background, with logs (via `scripts/modeling/run_climate2015_global_suite.py`):
   - baseline: fs0, fs1, fs2, fs3 with no `--dataset`;
   - climate2015_masked: fs0, fs1, fs2, fs3 with `--dataset` (primary);
   - climate2015_unmasked: fs0, fs1, fs2 with `--dataset`.
   - Common flags: `--region-scope 0 --add-identifier-features --phase-threshold 0.2 --half-life-months 24 --test-years 2022 2023 2024 2025 --seed 42 --out-dir … --report-dir …`.
9. `scripts/reporting/compare_climate2015_global_metrics.py`: comparison CSV (scope × year × metric; climate2015, baseline rerun, delta, 2026-05-31 baseline) and a short markdown report with caveats.
10. Write `evidence.md` in the task: commands, input hashes, fidelity results, run timings, the comparison table, and any deviations.

## Validation commands

- `PYTHONPATH=src ~/.venvs/ipcch-geo/bin/python -m pytest tests/unit/test_climate2015_features.py -q`
- `… scripts/preprocessing/check_climate2015_fork_fidelity.py`
- `… scripts/modeling/run_deep_feature_weight_decay_forecasting.py --fs fs0 --dataset <new> --dry-run …`
- Check that each run has `metrics/metrics_overall.csv` with 4 test years.

## Review gates

- After step 5: if the fidelity check fails for a family, fix the fork before building the full datasets.
- After step 7: column counts are close to the design estimate, and row keys are equal.
- After step 9: run `gitnexus detect_changes` before committing. The commit covers the code, tests and Trellis artifacts only; data and results are outside git or gitignored.

## Rollback points

- Before step 7: delete the branch.
- After step 7: delete `model_ready/climate2015_v1/` and `results/.../climate2015_v1/`.
