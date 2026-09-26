# Evidence — somalia-validity-label-augmentation

Evidence Status: Ready. Validation Status: Executed.

## Runs and tests

| Item | Code | Command | Outcome |
|---|---|---|---|
| Evidence run | `1f3bfce` (only this task's `task.json` dirty; `run_manifest.json`) | `PYTHONPATH=src ~/.venvs/ipcch-geo/bin/python -u -W ignore scripts/modeling/run_somalia_validity_augmentation.py --workers 12 --overwrite` | exit 0, 695 s; 288 H0 OOF fits, 94 mapping OOF fits, 120 final fits |
| Replay | `1f3bfce` | `scripts/postprocessing/replay_somalia_validity.py` | 933/933 checks (`replay_checks.csv`): augmentation rules vs raw panel, OOF/final isolation and availability, rounds, candidate scores and selection, mappings rebuilt from saved OOF predictions, primary metrics, identical outer keys, bootstrap, saved H0 models reproduce predictions |
| Reproducibility | previous run at `4d8474d` (differs by check fixes that remove 18 invalid-source copies which never entered any fit) | same CLI | every metric identical (max difference 0.0) |
| Unit / smoke | `1f3bfce` | `pytest tests/unit/test_somalia_augment.py tests/smoke/test_somalia_augment_pipeline.py` | 11 passed; 1 passed |
| Full suite | `aa2b5a1` | `pytest tests` | 12 failed / 265 passed; the 12 failures are the known pre-existing baseline |
| Feature parity gate | run | built into prepare | H0/H3/H6 recovered scope features and H12 deep features equal fs0/fs1/fs2/fs3 on all valid-phase keys (510/510/510/376 columns, 0 unmatched); 18 phase-0 fs1/fs2 rows excluded from the check |

## Acceptance mapping (PRD)

| Criterion | Evidence |
|---|---|
| Snapshot, mapping and report/window identity with conflict/unmatched counts | `run_manifest.json` (snapshot sha256 f5418154…); `api_rounds.csv`; `round_links.csv` (linked / no_current_round / excluded); `augmentation_decisions.csv` |
| Boundaries, overlap priority, value authority, coverage cap; originals traceable | 3,789 copies, all inside linked inclusive windows, ≤2026-04, training years only; decisions: 49 recipient_original, 1,808 no_covariate_row, 18 source_invalid; replay `copies_inside_linked_window`, `recipients_blank_in_raw`, `originals_unchanged_vs_raw` |
| Original values intact; each addition traced | `copy_values_equal_original`, `copy_family_is_linked_anl`; label ledger columns `original_month_ord`, `source_family`, `source_available_ord` |
| Main table with original/augmented D views and baselines | `metrics.csv` primary cohort (identical keys; the "expanded" cohort equals the original evaluation cohort per G3/R16), share/phase persistence subsets, always-crisis; `contrasts.csv` |
| Availability/report identity prevent leakage | OOF ledger `excluded_families`, `pool_families`, `pool_max_source_available_ord`; replay `oof_pools_exclude_round_families`, `oof_available_by_origin`, `final_fit_sources_available`, `final_fit_no_test_year` |
| History uses distinct original reports, excludes target report | copies `valid_history=False`; replay `copy_history_before_own_report_h*`, `history_cutoff_rule_h*`; report-aware categorical history |
| Per-fold isolation for both branches incl. OOF provenance | `oof_fit_ledger.csv`, `rounds_plan.csv`; `original_branch_oof_pools_have_no_copies` |
| Copies retain original availability | `copy_availability_is_original_month` |
| Per-row weights, no report balancing; counts/weights | `final_status.csv` `n_fit`, `n_fit_copies`, `sum_weight`; `source_families.csv` |
| Overlap decisions with provenance | `augmentation_decisions.csv` candidates/winner |
| Equal budgets; branch-specific selection; identical outer keys; D-selected before outer scores | `equal_search_budgets`, `selection_*`, `identical_keys_*` |
| Rounds = distinct original months (latest 3, min 2) | `rounds_plan.csv`; `rounds_distinct_originals_*` |
| Whole-block, blank-only recipients | `recipients_blank_in_raw`; unit tests |
| Inherited q3 behavior | q3 config sha pinned in `configs/somalia_validity_augmentation.json`; reuse of `q3opt.select_candidate/fit_mapping/bound_share` |

## Results (retrospective; `results_summary.md`)

Selected H0 recipes — original: 2025 direct X1 shift, 2026 direct X6 shift; augmented: 2025 direct X1 none, 2026 residual X2 shift.

| Year / H | View | Original R² | Augmented R² | Δ R² aug − orig [95% CI] |
|---|---|---:|---:|---|
| 2025 / 0 | D-selected (= direct) | −0.167 | −0.312 | −0.145 [−0.216, −0.083] |
| 2025 / 0 | D-residual | −0.000 | −0.011 | −0.010 [−0.037, 0.015] |
| 2025 / 3 | D-selected (= direct) | −0.339 | −0.286 | +0.053 [−0.027, 0.133] |
| 2026 / 0 | D-direct | 0.240 | −0.012 | −0.252 [−0.310, −0.197] |
| 2026 / 0 | D-selected | 0.240 | −0.172 | −0.412 [−0.484, −0.345] |

Share persistence R² on its subset: 2025 H0 −0.82, 2025 H3 −0.47, 2026 H0 0.22. Original D-selected beats share persistence in 2025 H0/H3 (ΔR² +0.66, +0.25) and matches it in 2026 H0 (+0.02 [−0.03, 0.07]); augmented D-selected is worse than persistence in 2026 H0 (−0.39).

Conclusion: under report isolation and round-level linking, validity-period copies do not improve D; at H0 they clearly hurt in 2026 and for direct in 2025, with no significant gain anywhere. These original-branch numbers are not comparable to v2 as an unchanged control (raw labels; 1,229 of 5,905 shared keys differ from the fs ledger, mostly 2017–2023; report isolation).

## Known limitations

- Linking is round-level (G3), not area-level; label values are nearest-centroid legacy assignments.
- Fold-2026 selection rounds include 2025-07 (64 cross-border spillover rows) and 2025-09 (4 rows).
- H12 residual OOF support is absent for early rounds; 12 contrast rows are flagged `diagnostic_only`.
- Copies of one assessment are not independent observations; area-cluster bootstrap does not model shared report dependence.

## Closure (2026-09-26)

User instruction: "彻底关掉这个task，跳过audit". The task had already been archived by `trellis-audit close` (completion `0ca97fe`), which queued controller close-audit job `077d9615e4fc14c427b496ca`. Its Codex reviewer (attempt 1) exited without writing `result.json`, leaving the job in `attention` and pausing the controller queue. Under the user's explicit waiver, the job was marked `waived` in the controller state DB (no audit result exists; the gate was not open; DB backed up as `state.db.bak-20260926-before-waive`), and the reviewer's Herdr workspace was closed. No audit verdict is claimed for this task.
