# Implementation plan — Somalia validity-period label augmentation

Version 0.1 — 2026-09-25 (Claude Opus 5.5, after Codex handoff). Implements PRD R1–R16 and design v0.2 sections 1–10 without reopening G1–G3. Additive only: v1/v2 code, configs, results, the archived q3 task and all external sources stay untouched.

## Resolved mechanics (implementation choices within the approved spec)

1. **Label authority.** Label ledger is built from the raw panel (`IPCCH_2026_completed.csv`, Somalia, all years) with the existing `data.build_label_ledger` QC/normalization (raw passed as both source and provenance set). This differs from v1/v2, which used the target-corrected fs ledger; key-level raw-vs-fs label differences are reported, not reconciled by overwriting (design §2, R7).
2. **Source families.** Every raw original gets `source_key=(area_id, original_month, raw_snapshot_sha)`. Rounds linked by R16 get `family=anl_id`; all other originals get `family=local:<month>` (never expanded). Copies inherit family, raw values, `original_month`, `source_available_at = original_month` month-end, `valid_from/valid_to`.
3. **Augmentation.** For linked rounds, enumerate inclusive months `from..to`, keep only months with a raw row (≤2026-04) whose six label fields are all missing (R15), and assign the copy from the latest original month among candidates; equal-date conflicting candidates stay unfilled (R12). Gate: ≥1 addition else `augmentation_unavailable` and stop after diagnostics.
4. **Features (design §8).** Load Somalia rows of the full monthly deep file once (chunked). H12 X = full deep columns (fs3 schema; `overall_phase_lag1` blocked). H0/H3/H6 X rebuilt in memory by importing the upstream `build_multiscope_ipcch_features` functions (`build_ordinary_features`, `build_enso_features`, `build_interactions`) on the complete per-area monthly panel, with the full deep file as baseline block instead of filtered fs3; `scenario_build`/`write_artifacts` are not called (no writes). `overall_phase_prev_observed_asof_sH` is recomputed report-aware: the original (never a copy) raw phase at month T−max(1,H), NaN if that source's family equals the target row's family or it is unavailable at the origin. V2 join and oracle weather reuse `data.v2_block`/`data.oracle_block` per row origin. Parity gate: on v2 labeled keys, every non-label feature column equals the saved fs0/fs1/fs2/fs3 value (NaN-equal), except the listed rebuilt history fields.
5. **History (R8).** Rich history index uses the original valid-history ledger only (copies never enter). For copy rows the visible cutoff is `min(O, T−1, F0−1)` where `F0` is the family's original month; assert no other original of that area lies in `(F0, min(O,T−1)]`, which makes the cutoff identical to excluding that single source. Original rows keep `min(O, T−1)`. Residual baseline and share/phase persistence read the same per-row history.
6. **Report isolation (R9, R10).** A fitting pool for context (target month v, horizon H, exclusion set E) = branch rows with `target_ord ≤ min(v−H, v−1)`, `source_available_at ≤ v−H`, target year and original year in the fold window, and `family ∉ E`. OOF fits are cached by the hash of their exact pool row set, so purged fits are shared only when pools are identical. The E of an OOF fit at month v is the union of families of that month's scoring rows; the calibration OOF predictions used for scoring context v are produced by fits whose pools exclude v's families (checked; a purged fit is generated if needed).
7. **Rounds (R14, G1).** Selection rounds = latest three distinct original-report months in the fold window with supported pools (≥2 required); round rows = the branch's rows of those reports (originals, plus copies in the augmented branch). Calibration for a scoring round = up to three earlier rounds (≥2) whose member months are all `< v`, `≤ v−H` and available at `O_v`. Final mapping = latest three rounds ≤ outer origin (≥2). Frozen to `selection/rounds_plan.csv` per branch before any score.
8. **Weights (R11).** Model rows keep `0.5**((fit_origin − target_month)/24)`; calibration and scoring rows are unweighted; no division by copies. Per-family counts and summed weights are saved.
9. **Search and views.** Per branch: D-direct and D-residual × X1–X6 × {none, shift, isotonic}; strict pooled final-q3 RMSE, 1e-12 tie set, AUC tie-break, method/bundle/formulation order (reusing `q3opt.select_candidate`, `fit_mapping`, `bound_share`). D-selected = exact globally selected recipe. H3/H6/H12 refit each branch's H0 recipe (same fold), no search, later-label flags recorded.
10. **Evaluation.** Outer evaluation rows are the raw original 2025/2026 labels; primary cohort uses the v1 cohort rules (oracle verification) recomputed on the raw ledger and is identical for both branches. Main table: original vs augmented D-direct/residual/selected, share persistence (history-supported subset), phase persistence, all-crisis, per year/horizon, via `q3eval`. Paired area-cluster bootstrap (2,000 draws, PCG64(42)): augmented − original for each D view; each branch's D-selected − share persistence.

## Code layout

- `configs/somalia_validity_augmentation.json` — snapshot path + sha256, linked rounds, exclusions, reused q3 config/bundle hashes, bootstrap.
- `src/ipcch/somalia_oracle/augment.py` — raw label ledger, round linking, augmentation ledger, source families/availability.
- `src/ipcch/somalia_oracle/monthly_features.py` — Somalia monthly panel load, upstream scope-feature recovery, report-aware categorical history, parity check.
- `src/ipcch/somalia_oracle/augexp.py` — per-branch frames, report-aware history, pools, OOF cache, rounds, selection, final fits, transfer.
- `scripts/modeling/run_somalia_validity_augmentation.py` — CLI (`--prepare-only`, `--workers`, `--overwrite`), output root `results/experiments/somalia_oracle/v3_validity/`, report `reports/somalia_oracle/v3_validity/`.
- `scripts/postprocessing/replay_somalia_validity.py` — independent replay (labels, isolation, rounds, selection, metrics, bootstrap, saved models).
- `tests/unit/test_somalia_augment.py`, `tests/smoke/test_somalia_augment_pipeline.py`.

## Ordered checklist

1. Commit planning artifacts; `trellis-audit --repo '<exact path>' start somalia-validity-label-augmentation` from pane wD:p2; verify run/executor/base SHA and `in_progress`.
2. `augment.py` + tests: blank-only six-field filling, inclusive months, existing-label precedence, latest-original overlap, equal-date conflict unfilled, no copy beyond covariates, family/availability inheritance, gate.
3. `monthly_features.py` + tests; real `--prepare-only`: parity gate on v2 keys; label diff report raw vs fs.
4. `augexp.py` + tests: copy-row history cutoff, report-aware categorical history, pool purge/availability/source-year rules, OOF cache identity, rounds (distinct original months, copies not counted), calibration dependency check, equal budgets.
5. CLI + synthetic smoke (both branches, all views, replay); pilot timing; full run alone (no concurrent pytest).
6. Replay; evidence bundle; trellis-check; full suite vs the known 12-failure baseline; GitNexus `detect_changes`; commit; `trellis-audit close`; verify job; Codex spot audit per goal.

## Validation commands

```bash
PYTHONPATH=src ~/.venvs/ipcch-geo/bin/python -m pytest tests/unit/test_somalia_augment.py -q
PYTHONPATH=src ~/.venvs/ipcch-geo/bin/python -m pytest tests/smoke/test_somalia_augment_pipeline.py -q
PYTHONPATH=src ~/.venvs/ipcch-geo/bin/python scripts/modeling/run_somalia_validity_augmentation.py --prepare-only --out-dir /tmp/v3_prep
PYTHONPATH=src ~/.venvs/ipcch-geo/bin/python -u scripts/modeling/run_somalia_validity_augmentation.py --workers 12 --overwrite
PYTHONPATH=src ~/.venvs/ipcch-geo/bin/python scripts/postprocessing/replay_somalia_validity.py
```

## Gates and rollback

- Mapping gate: additions > 0 (expected 3,807); otherwise stop with `augmentation_unavailable`.
- Feature gate: non-label parity on v2 keys; any mismatch stops the run and is reported.
- Memory: 15 GB; load the 5 GB deep file chunked (Somalia only); ≤12 workers; never alongside pytest.
- No change to rounds, grid, calibration inventory or metrics after seeing outer scores.
- Rollback: revert the additive commits.
