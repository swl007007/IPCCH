# Evidence — somalia-v4-calibrated-d

Evidence Status: Ready. Validation Status: Executed (focused tests, synthetic smoke, real prepare-only, bounded real pilot, full production run, independent replay, full suite).

Execution authorized by the user's goal on 2026-09-30 ("完成目前落盘的spec，并按照trellis audit skill唤起codex astra xhigh进行spot audit和close audit"). Audit run `0e231056d9a04cf18d13ebb9495d1920`, base `5b053ff`.

## Commits

| Commit | Content |
|---|---|
| `e0757fc` | v4 implementation: `augexp` v4 section (PoolSpec/PoolIndex, contexts, OOF units, 144-recipe scoring, cohorts, keyed evaluation), `decay_weights(half_life=None)`, `select_candidate(extra_order)`, optional `prepare(first_model_year, folds)`; runner, replay, unit and smoke tests, `configs/somalia_v4_calibrated_d.json` |
| `5fbe597` | Fix from the internal trellis-check review: a residual model is required exactly on rows with a permitted baseline (scoring, calibration, final); a learned mapping whose required unit failed on any calibration key is unsupported instead of being fitted on fewer keys. Replay mirrors the rule; stronger cross-setting check; augmentation-unavailable slots kept; spec lessons |
| `a88a1f5` | `--final-workers` (resource only; recipe unchanged) after the OOM of attempt 2 |

## Runs and tests

| Item | Code | Command | Outcome |
|---|---|---|---|
| Focused unit tests | `a88a1f5` | `pytest tests/unit/test_somalia_v4.py` | 19 passed |
| Synthetic smoke + replay | `5fbe597` | `pytest tests/smoke/test_somalia_v4_pipeline.py` | 1 passed (full CLI on a synthetic 2016-2026 panel; replay of its output passes every check) |
| Legacy Somalia regression | `5fbe597` | `pytest tests/unit/test_somalia_{q3opt,augment,oracle}.py tests/smoke/test_somalia_{augment,q3opt,oracle}_pipeline.py` | all passed (72 with v4 tests before the fix; 54-test subset after) |
| Real prepare-only | `e0757fc`+wip | `run_somalia_v4_calibrated_d.py --prepare-only --out-dir /tmp/somalia_v4_prepare` | inputs, cohorts, 142 jobs, 142 supported contexts (62 unique), 331 pool specs, 10,320 OOF fits planned, 0 empty pools |
| Bounded real pilot | `e0757fc` | `--workers 12 --pilot augmented:2024:0 --pilot original:2023:12 --out-dir /tmp/somalia_v4_pilot` | exit 0, 611 s, 1,056 OOF fits, 9 final fits; replay 94/94 (`pilot_replay_summary.json`); free memory fell to ~200 MB in the final-fit phase |
| Production attempt 1 | `e0757fc` | `--workers 10` | stopped by the executor at 50% OOF after the review finding (no outputs kept) |
| Production attempt 2 | `5fbe597` | `--workers 10` | OOF + selection completed; final fits OOM-killed (BrokenProcessPool) at 35/142 (`run_attempt2_oom_log.txt`); outputs discarded |
| **Production run (evidence)** | **`a88a1f5`** (only unrelated untracked `scripts/reporting/somalia_oracle_wrapup.py`) | `PYTHONPATH=src python -u scripts/modeling/run_somalia_v4_calibrated_d.py --workers 10 --final-workers 4` | exit 0, 5,180 s; 10,320 OOF fits, 62 selections × 144 recipes, 142 final fits (`run_manifest.json`, `run_log.txt`) |
| Independent replay | `a88a1f5` | `scripts/postprocessing/replay_somalia_v4.py --out-dir results/experiments/somalia_oracle/v4_calibrated_d` | **95/95** checks (`replay_checks.csv`): cohorts rebuilt from the ledger + digests, every pool rebuilt from its spec (hash), member/calibration/final temporal and family isolation, final-fit decay weights, 8,928 candidate scores recomputed with independent isotonic/shift code, all 142 selections, final mappings/bounds, 43,864 saved-model probe rows, annual/pooled metrics (sklearn), setting-only prediction keys |
| Full suite | `a88a1f5` | `pytest tests` | 12 failed / 285 passed; the 12 are the known pre-existing alert-risk-map / launch-CLI baseline (same tests as v3's 12/265) |

Inputs (sha256 prefix, `run_manifest.json`): climate 2015-2026 `f024a66c…` (pinned), raw `ae696087…`, deep `60610cd6…`, lookup `e2baf6ae…`, fs0-3 parity references, validity snapshot `f5418154…` (pinned), tree bundles `9d572793…` (pinned). Runtime: Python 3.12.3, NumPy 2.4.4, pandas 3.0.3, scikit-learn 1.8.0, XGBoost 3.2.0 (checked against the config before running).

## Acceptance mapping

| AC | Evidence |
|---|---|
| AC1 planning artifacts / no open decisions | Planning commit `5b053ff` (G1-G9); `lifecycle.md` |
| AC2 seasonal source | `configs/somalia_v4_calibrated_d.json` pins path + sha; runner refuses a hash mismatch; 14 `V2_FEATURES` via `data.prepare_v2_seasons/v2_block` (date-based latest ended season, complete-export check, NaN block otherwise); `row_provenance_h*.csv.gz` record `v2_status`/season per row |
| AC3 calibrated D procedure | `v4_candidates` = 6 bundles × {12,24,48,none} × direct/residual × none/shift/isotonic = 144 (config check + unit test); selection = pooled final-q3 RMSE, AUC only inside the 1e-12 tie set, then method, bundle, formulation, half-life none/48/24/12 (`select_candidate(extra_order=["decay_order"])`); independent per (setting, year, H, origin) context (`contexts.csv`, `selected_recipes.csv`); replay `selected_recipes_replayed`, `selection_labels_after_origin` false for all jobs |
| AC4 two scenarios | `v4_freeze_cohorts`: original cohorts have 0 copies, augmented admits copies (2022-2024 tests: 1,374 / 995 / 1,420 copies); 4,409 copies over 2019-2024 incl. 620 pre-2022 (`label_support_by_year.csv`); every pool spec of `original` excludes copies (replay `pools_rebuilt_from_specs`); `predictions_stay_in_own_setting_cohort`; no cross-setting outputs |
| AC5 annual folds and isolation | Fold upper year Y-1 for recipient and source year, no lower bound (earliest supervised year 2017); per-row origin `v-H` for every scoring/calibration key incl. copies; own, served-scoring and outer-test families purged (`pool_specs.csv.gz`, replay `temporal_and_report_isolation`); `cohort_slots.csv` gives actual target coverage |
| AC6 pooled results | `v4_evaluate` concatenates each setting/H's annual keyed rows (equal weight), recomputes metrics, records `rows_by_year` and cohort hash; replay recomputes pooled metrics from rows |
| AC7 evidence/checks | Focused tests cover each boundary in implement.md §5 (19 unit tests incl. copied-row origin, transitive purge, H12 origin, unsupported-not-shrunk, residual-required-on-baseline, keyed joins, G9, round-trip floats); replay above |
| AC8 lifecycle | `lifecycle.md`; run `0e231056…`, executor session `7cea05f8…`, base `5b053ff` |

## Results (retrospective oracle-information evaluation; `results_summary.md`)

Pooled 2022-2026, each setting on its own population (not comparable across settings; not an augmentation effect):

| Setting | H | n | Final R² | RMSE (pp) | Final AUC | F1 |
|---|---|---:|---:|---:|---:|---:|
| original | 0 | 5,228 | −0.118 | 20.25 | 0.673 | 0.754 |
| original | 3 | 2,723 | −0.471 | 26.20 | 0.648 | 0.759 |
| original | 6 | 2,723 | −0.618 | 27.48 | 0.542 | 0.619 |
| original | 12 | 3,680 | −1.400 | 31.63 | 0.423 | 0.523 |
| augmented | 0 | 9,017 | 0.170 | 18.95 | 0.749 | 0.793 |
| augmented | 3 | 6,512 | −0.193 | 24.22 | 0.671 | 0.736 |
| augmented | 6 | incomplete | | | | |
| augmented | 12 | 7,469 | −1.051 | 30.93 | 0.420 | 0.569 |

Annual slots: 35 complete, 4 structurally empty (2026 H3/H6 in both settings: no verified realized weather after the 2025 forward-fill), 1 incomplete. Largest errors are in 2022-2023 (e.g. original 2022 H0 bias −22 pp, 2023 H0 +21 pp): training labels before 2022 cover only 73-74 coarse areas, while 2022 onwards covers ~350-900 areas.

### Incomplete slot (G9)

`augmented 2023 H6` (origins 2023-02, 2023-03; 696 of 2,013 keys) selected residual X6 / 12-month / isotonic on its scoring keys. The final mapping must be refit on the latest three rounds (2022-05/07/10); at H6 the 348 areas first labelled in 2022-07 have no history before T−6, so the residual branch has 2 baseline rows in a single round (minimum two rounds). Per G9 the selected mapping stays unavailable — no clipped-raw substitution and no switch of method — so this annual slot and the augmented H6 pooled result are reported incomplete. The other 39 slots and seven pooled results are unaffected. Selecting only recipes whose final mapping is supported would be a change to the approved selection contract and was not made after seeing this outcome.

## Known limitations

- Oracle information (ideal label availability, realized future weather); retrospective on years partly inspected in v1-v3.
- H>0 outer cohorts keep only verified-weather rows (inherited rule); 2025 H3/H6 keep 275/1,876 rows, 2025 H12 1,100, 2026 H12 132.
- Copies of one assessment are repeated monthly truth, not independent observations; augmented pooled scores weight long validity windows more.
- 1,008 of 8,928 context×recipe evaluations are unsupported, all residual learned mappings lacking calibration support; recorded with reasons in `candidate_scores.csv.gz`.
- Upstream climate QA/provenance gaps listed in research.md are inherited, not repaired.
