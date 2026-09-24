# Implementation plan — Somalia oracle-information experiment

Version: 1.0 — 2026-09-24
Authorization: the user's session goal (2026-09-24) directs completing the on-disk spec and running the Trellis audit lifecycle with Codex/Astra high spot and close audits. This is recorded as the final spec acceptance of `prd.md`/`design.md` v1.1 (including the proposed candidate values, latest-three-month inner validation with >=2 supported months, and the 2,000-draw PCG64(42) bootstrap) and as the implementation/execution approval required by AC10.

## Preflight decisions resolved from evidence (research.md addendum §A)

These close the preflight gaps named in design §8 using the spec's own rules; none expands scope.

| Gap | Resolution | Spec basis |
|---|---|---|
| `overall_phase_lag1` lineage | Blocked from every arm/horizon. Upstream code adds it as "previous observed row" with arbitrary gap; it post-dates O for H>=3 on 1,640/17,218/36,369 rows (3/6/12m). | design §2 "block affected features" |
| `estimated_population` | Blocked as a predictor (target-month IPC analysis population corrected with the targets). Still used only for history QC (positive population). | design §2 no target-derived covariates |
| Scope files per horizon | H=0→fs0, 3→fs1, 6→fs2, 12→fs3. Upstream builder shifts every `_sH` family to exactly T−H; `asof12`/`l12+` to <=T−12. `overall_phase_prev_observed_asof_sH` is the exact calendar month T−max(1,H) (<=O and <T). | R5, design §1 fs3 validation |
| Label ledger | Model-ready (target-corrected) ledger = union of labeled Somalia rows in fs0–fs3 (6,759 keys, zero cross-file conflicts). Raw canonical source is used for weather and 2025+ label provenance only; ledgers are never mixed. | design §2 explicit sources |
| Isolated 2026-01 label (area 1917) | Excluded everywhere with reason `provenance_unreconciled`: 2025+ keys must also be labeled in the raw canonical source (raw and model-ready agree on all other 2025–2026 keys). | research gap |
| Oracle weather verification | Area-month (a,m) is verified iff both `Rainf_f_tavg_mean` and `Tair_f_tavg_mean` are finite and NOT both exactly equal to (a,m−1). Before 2025-02 no area-month meets the equality signature; 772 areas are frozen from 2025-02 to 2026-04 and all 904 repeat in 2026-04. Unverified months are NaN in C/D features and make evaluation rows ineligible for the common cohort. | R4, design §4 |
| Oracle months on fitting/validation rows | Built identically at each row's own origin; unverified months become NaN (fitting eligibility stays shared across arms); counts recorded. | R4 "same construction", design §2 fitting support |
| History aliases | No semantically identical IPCCH base feature exists (IPCCH prev_observed is exact-month, not latest-observation), so `hist_age_obs1`, `hist_crisis_obs1`, `hist_crisis_age`, `hist_no_crisis` are materialized once; `hist_support_common_all_age` equals `hist_age_obs1` and is not duplicated. D adds 472 history columns. | design §5 |
| H=0 history cutoff | Visible observations U<=min(O, T−1); ages/windows keep O as reference, so H=0 windows end at O=T but can never contain month T. | R5 |
| Reference code | Ported into IPCCH (no sibling import at runtime); pinned Food_Crisis_Cluster `85bc505a5b99`, `prepare_data.py` sha256 `d582ebad…814fc`, `feature-schema.json` sha256 `c660d360…d344`. Parity test imports the reference when present. | design §1 |
| Evaluation targets | Fold 2025: 2025-04 (904), 2025-07 (64), 2025-09 (4), 2025-10 (904). Fold 2026: 2026-04 (904) only. | R2, R7 |

## Code layout (minimal, reuses `ipcch.forecasting_weight_decay` helpers)

- `src/ipcch/somalia_oracle/__init__.py` — constants (horizons, folds, blocked features, V2 list, weather vars).
- `src/ipcch/somalia_oracle/data.py` — label ledger + G4 normalization, weather ledger/oracle block, V2 as-of join, base feature loading per horizon, row universe.
- `src/ipcch/somalia_oracle/history.py` — port of the reference rich-history block with separate cutoff/origin, alias materialization, persistence lookup.
- `src/ipcch/somalia_oracle/modeling.py` — candidate loading, weights, phase conversion (unrounded), inner validation, selection, final fits, job execution.
- `src/ipcch/somalia_oracle/evaluation.py` — cohorts, metrics, persistence/always-crisis references, paired area-cluster bootstrap, independent replay.
- `scripts/modeling/run_somalia_oracle_experiment.py` — CLI: `--prepare-only`, `--pilot`, `--workers`, `--out-dir`, `--report-dir`, `--overwrite`; writes results/ and reports/ plus a hash manifest.
- `configs/somalia_oracle_candidates.json` — copy of task `candidate-configs.json` (frozen; hash recorded).
- `tests/unit/test_somalia_oracle.py`, `tests/smoke/test_somalia_oracle_pipeline.py`.

## Ordered checklist

1. Commit planning artifacts; `trellis-audit --repo '<exact path>' start somalia-flood-food-crisis` from bound pane wD:p2; verify run/base_sha/in_progress.
2. Implement data layer + unit tests (normalization, validity, V2 boundaries, oracle offsets/verification).
3. Implement history port + parity/irregular/q3=0/H=0 tests; persistence tests.
4. Implement modeling (weights, unrounded conversion boundary, inner cutoffs, tie, constant target, unsupported validation) + tests.
5. Implement evaluation (metrics rules, always-crisis, bootstrap replay determinism/shared multiplicities/undefined) + tests.
6. CLI + synthetic end-to-end smoke test (tiny XGBoost).
7. `--prepare-only` on real inputs: ledgers, cohorts, job inventory; inspect coverage.
8. `--pilot` (one job) to time fits; then full run with parallel workers (`n_jobs=1` per model).
9. Independent metrics/bootstrap replay from saved predictions; write report and evidence bundle into `.trellis/tasks/<task>/evidence/`.
10. trellis-check review; fix; full test suite; GitNexus `detect_changes`; commit.
11. `trellis-audit close`; verify close-audit job. Launch independent Codex (gpt-6-astra, reasoning high) spot-audit with the trellis-task-auditor Skill at HEAD. Address findings via controller remediation workflow if major/blocker.

## Validation commands

```bash
PYTHONPATH=src ~/.venvs/ipcch-geo/bin/python -m pytest tests/unit/test_somalia_oracle.py tests/smoke/test_somalia_oracle_pipeline.py -q
PYTHONPATH=src ~/.venvs/ipcch-geo/bin/python -m pytest tests -q
PYTHONPATH=src ~/.venvs/ipcch-geo/bin/python scripts/modeling/run_somalia_oracle_experiment.py --prepare-only --out-dir results/experiments/somalia_oracle/v1
PYTHONPATH=src ~/.venvs/ipcch-geo/bin/python scripts/modeling/run_somalia_oracle_experiment.py --workers 24 --out-dir results/experiments/somalia_oracle/v1 --report-dir reports/somalia_oracle/v1
```

## Review gates and rollback

- Gate after step 7: if the common cohort is empty for a cell, report it unavailable (no relaxation).
- Gate after step 8: pilot runtime extrapolation must fit the machine (15 GB RAM, 32 cores); otherwise reduce workers, never the candidate budget.
- Rollback: all changes are additive (new package, script, config, tests); revert the implementation commit. External sources are read-only.

## Execution record (2026-09-24)

Steps 1–10 completed: implementation commit `a0c792e65ed6`; evidence run and independent replay recorded in `evidence/evidence.md` (80/80 arm cells completed; replay 480/480; outputs reproducible byte-for-byte). Step 11 (close + audits) follows this commit.
