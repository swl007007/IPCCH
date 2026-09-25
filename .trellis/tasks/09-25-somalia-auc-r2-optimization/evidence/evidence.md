# Evidence — somalia-auc-r2-optimization

Evidence Status: Ready. Validation Status: Executed.

## Runs and tests

| Item | Code | Command | Outcome |
|---|---|---|---|
| Evidence run | `244f212` (only this task's `task.json` dirty; `run_manifest.json`) | `PYTHONPATH=src ~/.venvs/ipcch-geo/bin/python -u -W ignore scripts/modeling/run_somalia_q3_optimization.py --workers 12 --overwrite` | exit 0, 534 s; 288 H0 OOF fits, 95 receiving-horizon OOF fits, 95 final fits |
| Reproducibility | first run at `d1509a8` (differs only in report text/status metadata) | same CLI, 14 workers | final predictions, metrics, candidate scores and selected recipes byte-identical |
| Replay | `244f212` | `scripts/postprocessing/replay_somalia_q3.py` | 426/426 checks (`replay_checks.csv`) |
| Cohort gate | `d1509a8` | `--prepare-only` | cohort ledger identical to v1 |
| Unit tests | — | `pytest tests/unit/test_somalia_q3opt.py` | 13 passed |
| Smoke | — | `pytest tests/smoke/test_somalia_q3opt_pipeline.py` | 1 passed |
| Full suite | — | `pytest tests` | 12 failed / 250 passed; the 12 failures are the pre-existing baseline (alert-risk maps, launch CLI) |

An intermediate rerun concurrently with the full pytest suite died with `BrokenProcessPool` (memory contention on the 15 GB machine); it wrote no outputs over the saved run. The evidence run above was executed alone.

## Acceptance mapping (PRD acceptance list)

| Criterion | Evidence |
|---|---|
| Share units, target, loss, selection score, aggregation, AUC truth/score, calibration validation, threshold | `configs/somalia_q3_optimization.json`; `candidate_scores.csv` (pooled unweighted final-q3 RMSE, AUC vs reported phase ≥3); `scoring_plan.csv` |
| H0 optimization vs H3/H6/H12 fixed-recipe refits; recipe source recorded | `selected_recipes.csv`; `final_status.csv` columns `recipe_source_view`, `recipe_selection_max_label`, `receiving_origin`, `selection_uses_later_labels`, `mapping_months` |
| Receiving refits keep configuration/method; eligible dates replayable | `final_status.csv`, `oof_fit_ledger.csv` (fit cutoffs ≤ min(v−H, v−1)); replay chronology checks |
| Matched-key comparisons against v1 and share persistence | `metrics.csv` cohorts `primary`, `share_history_subset`, `phase_persistence_subset`; views `v1_D_raw`, `v1_D_isotonic`, `share_persistence`; `contrasts.csv` |
| Direct vs residual on original q3 units, identical keys; baseline source dates | `D_residual-D_direct` contrasts; predictions carry `baseline_q3`, `baseline_source_ord`, `branch` |
| Missing-history fallback with counts/flags | `n_fallback_direct` in `metrics.csv` (2025 H0: 14; H3: 7; H6: 8; H12: 27); `share_history_subset` rows |
| Selection replayable from held-out final-pipeline predictions; chronological calibration separation; identity candidate included | `scoring_predictions.csv.gz` (results dir); replay `candidate_rmse_replay`, `selection_*`, `calibration_before_scoring_*` |
| Strict RMSE minimum, AUC only in ties, no threshold tuning | replay `selection_*`; config tie order |
| Exactly three calibration methods; final [0,1]; raw auditable | `candidate_scores.csv` methods; `q3_raw` vs `q3_final`, `clipped`, `n_clipped` |
| Raw/final AUC on declared columns vs reported phase ≥3; no classifier | `raw_auc`, `final_auc`, within-month AUC columns |
| Binary F1/recall at fixed final q3 ≥ .2; legacy ordinal separate | `bin_*` vs `legacy_*`, `q3_binary_vs_legacy_disagreements` |
| A–C information sets unchanged; residual only in D; formulation selection disclosed | selected recipes table; report text |

## Results (retrospective; see `results_summary.md`)

- Selected H0 recipes: D-residual in both folds (2025 X6+isotonic, 2026 X1+shift).
- 2025 H0 D-selected: final q3 R² 0.138 (raw −0.597), RMSE 12.04 pp, bias +2.07 pp; vs v1 calibrated D R² 0.101; vs share persistence ΔR² +0.77 [0.64, 0.90], ΔRMSE −4.5 pp [−5.1, −4.0]. Final AUC 0.714 (share persistence 0.759 on the same subset).
- 2025 H3 (fixed-recipe transfer, disclosed later-label selection): D-selected R² −0.001, RMSE 13.06 pp; beats share persistence (ΔR² +0.48 [0.26, 0.75]).
- 2026 H0: D-selected (residual) R² 0.062, RMSE 17.34 pp, bias −5.4 pp, worse than D-direct (0.213) and share persistence (0.220): ΔR² vs persistence −0.158 [−0.207, −0.109]. The training-period validation choice did not transfer to April 2026; D-direct matches v1 calibrated D (ΔR² −0.002 [−0.024, 0.020]).
- H12 residual transfers poorly (2025 R² −0.90; 2026 −1.65, strong negative bias); these are ancillary results, not optimized.
- 2026 H3/H6 primary cohorts remain empty (no verified oracle weather).
- Minor check notes addressed in `244f212`; the fallback-branch mapping is fitted on all direct OOF rows of its calibration months (disclosed in the report).
