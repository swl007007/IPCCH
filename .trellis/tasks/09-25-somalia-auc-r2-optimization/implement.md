# Implementation plan — q3-first Somalia optimization

Version 0.1 — 2026-09-25 (Claude Opus 5.5, after Codex handoff). Status: approved 2026-09-25 together with design.md v0.2. Implements PRD R1–R15 and design sections 1–7 without changing any approved decision.

## Scope boundary

Additive only. v1 code paths, configs (`configs/somalia_oracle_candidates.json`, sha256 `9d572793…a9ef0f`), results (`results/experiments/somalia_oracle/v1/`) and reports stay untouched. Reuse `ipcch.somalia_oracle.pipeline.prepare()` unchanged for ledgers, feature frames, schemas, cohorts and the job inventory, so primary keys equal v1's (design section 1). No new classifier, loss, framework or sibling-repo edit.

## Implementation decisions (mechanics, not new science)

1. **H0 selection is computed once per fold.** Every H0 outer job of a fold has the same clipped pool (2025 H0 origins 2025-04..10 all postdate 2024; 2026 H0 origin 2026-04 postdates 2025), so one selection per (fold, arm/formulation) is identical to per-job selection. Guard: assert pool keys are identical before reuse; otherwise select per job.
2. **OOF/selection fits train only the q3 regressor** (direct q3, or residual delta for D-residual). q2/q4/q5 are fitted only in final outer fits (legacy ordinal diagnostics, design section 2). This changes cost, not any selected quantity.
3. **OOF months.** For fold window W, OOF targets are every labeled month v in W with a nonempty fit pool u<v, u in W (H0), plus u<=v-H for receiving horizons. Test2025: 2022-05 … 2024-07; test2026: 2023-03 … 2025-10. The scoring months (latest three with scorable truth and nonempty pools, ≥2 required) and their calibration months (latest three earlier OOF months with c<v and c<=v-H, ≥2 required) are frozen from label/pool support before any candidate score is computed and written to `selection/scoring_plan.csv`.
4. **Candidate grid per fold.** A-direct, B-direct (=C at H0, reused), D-direct, D-residual × X1–X6 × {none, shift, isotonic}. Calibration options reuse the same OOF raw predictions. D-residual rows without an eligible baseline use the same-bundle D-direct OOF model and its own direct-branch mapping (R8).
5. **Selection** exactly as design section 4: pooled unweighted squared error on the fixed scoring keys, global minimum final-q3 RMSE, tie set within 1e-12, then pooled final-score AUC (skipped if one class), then none<shift<isotonic, then bundle order, then direct<residual. An unsupported method/formulation on any scoring key is unsupported on the whole comparison. Separate views: D-direct best, D-residual best, D-selected (best across both), A/B/C-direct best.
6. **Final H0 fit:** selected bundle on the full outer pool (4 regressors; q3 residual where selected), mapping refit on the latest three eligible OOF months ≤ outer cutoff (≥2), final bound [0,1], unbounded raw kept.
7. **H3/H6/H12 transfer (design section 5):** same fold/target/arm-formulation H0 recipe (bundle + calibration method; D-selected also inherits formulation). Receiving OOF predictions at the receiving horizon's own cutoffs are generated only to refit the fixed mapping; no search. Unfittable mapping ⇒ calibrated cell unavailable, raw retained as labelled diagnostic. Records `recipe_selection_max_label`, `receiving_origin`, `selection_uses_later_labels`.
8. **Job inventory:** v1's (all outer jobs, H=0 C reuses B). Empty primary cells (2026 H3/H6) remain unavailable in reports; their jobs still run only if they have scorable wider-cohort rows, as in v1.
9. **Outputs:** `results/experiments/somalia_oracle/v2_q3/` and `reports/somalia_oracle/v2_q3/`, with manifest (git HEAD, runtime, input sha256, v1 config hash, new config hash).

## Code layout

- `configs/somalia_q3_optimization.json` — references v1 bundle file + hash; calibration methods; tie tolerance/order; scoring/calibration month counts; bootstrap settings.
- `src/ipcch/somalia_oracle/q3opt.py` — residual baseline/branching, OOF generation, chronological calibration (identity/shift/isotonic; identity not routed through `calibrate()`), selection, final fits, recipe transfer.
- `src/ipcch/somalia_oracle/q3eval.py` — q3 R²/RMSE/MAE/signed bias, raw/final pooled and within-month AUC, fixed q3>=.2 binary metrics, legacy ordinal metrics with disagreement counts, share/phase persistence on their own matched subsets, paired area-cluster bootstrap for ΔR²/ΔRMSE/ΔAUC (reuses `evaluation.bootstrap_multiplicities`).
- `scripts/modeling/run_somalia_q3_optimization.py` — CLI (`--prepare-only`, `--workers`, `--only-horizon`, `--overwrite`).
- `scripts/postprocessing/replay_somalia_q3.py` — independent replay (sklearn metrics, selection replay from saved OOF/scoring predictions, bootstrap intervals).
- `tests/unit/test_somalia_q3opt.py`, `tests/smoke/test_somalia_q3opt_pipeline.py`.

Existing symbols are not modified; if a helper must change, run GitNexus `impact` first and report blast radius.

## Ordered checklist

1. Final technical review accepted; commit planning artifacts; `trellis-audit --repo '<exact path>' start somalia-auc-r2-optimization` from pane wD:p2; verify run, executor, base SHA and `in_progress`.
2. Config + q3opt residual/branching/calibration primitives with unit tests (reconstruction, fallback flags, no fabricated baseline, identity≠isotonic, isotonic <2 distinct inputs unsupported, [0,1] bound with raw kept and clip counts).
3. OOF/scoring-plan generation with chronology tests (H0 self-exclusion, c<v and c<=v-H, frozen scoring keys, ≥2 support rules, H12 outer mapping support).
4. Selection with tests (strict RMSE, 1e-12 tie set, AUC tie-break/skip, deterministic order, whole-comparison unsupported rule, no crisis-class requirement).
5. Final fits + H>0 recipe transfer with tests (recipe mapping, later-label flags, origin-valid receiving fits, no H>0 search).
6. q3eval + bootstrap with tests (hand-checkable R²/RMSE/AUC, fixed .2 boundary .196/.2/.204, undefined AUC, shared multiplicities).
7. CLI + synthetic end-to-end smoke; `--prepare-only` on real inputs (assert cohort ledger equals v1).
8. Pilot one fold's H0 selection to time; full run; replay; report and evidence bundle.
9. trellis-check review; fix; full test suite vs the known 12-failure baseline; GitNexus `detect_changes`; commit; `trellis-audit close`; verify job.

## Validation commands

```bash
PYTHONPATH=src ~/.venvs/ipcch-geo/bin/python -m pytest tests/unit/test_somalia_q3opt.py tests/unit/test_somalia_oracle.py -q
PYTHONPATH=src ~/.venvs/ipcch-geo/bin/python -m pytest tests/smoke/test_somalia_q3opt_pipeline.py -q
PYTHONPATH=src ~/.venvs/ipcch-geo/bin/python scripts/modeling/run_somalia_q3_optimization.py --prepare-only --skip-input-hash --out-dir /tmp/q3_prep
PYTHONPATH=src ~/.venvs/ipcch-geo/bin/python -u scripts/modeling/run_somalia_q3_optimization.py --workers 14 --overwrite
PYTHONPATH=src ~/.venvs/ipcch-geo/bin/python scripts/postprocessing/replay_somalia_q3.py
```

## Review gates and rollback

- Gate after step 7: prepared cohort ledger must equal v1's; otherwise stop and report (design section 1).
- Gate after pilot: runtime must fit 15 GB/32 cores; reduce workers, never the candidate budget.
- No change to the approved grid, calibration inventory, threshold or metric priority after seeing any outer score.
- Rollback: revert the additive commits; v1 artifacts untouched.
