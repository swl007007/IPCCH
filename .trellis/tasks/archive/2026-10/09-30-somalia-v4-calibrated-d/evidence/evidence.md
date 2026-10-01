# Evidence — somalia-v4-calibrated-d

Evidence Status: Ready. Validation Status: Executed (focused tests, synthetic smoke, real prepare-only, bounded real pilot, full production run, independent replay, full suite).

Execution authorized by the user's goal on 2026-09-30 ("完成目前落盘的spec，并按照trellis audit skill唤起codex astra xhigh进行spot audit和close audit"). Audit run `0e231056d9a04cf18d13ebb9495d1920`, base `5b053ff`.

## Commits

| Commit | Content |
|---|---|
| `e0757fc` | v4 implementation: `augexp` v4 section (PoolSpec/PoolIndex, contexts, OOF units, 144-recipe scoring, cohorts, keyed evaluation), `decay_weights(half_life=None)`, `select_candidate(extra_order)`, optional `prepare(first_model_year, folds)`; runner, replay, unit and smoke tests, `configs/somalia_v4_calibrated_d.json` |
| `5fbe597` | Fix from the internal trellis-check review: a residual model is required exactly on rows with a permitted baseline (scoring, calibration, final); a learned mapping whose required unit failed on any calibration key is unsupported instead of being fitted on fewer keys. Replay mirrors the rule; stronger cross-setting check; augmentation-unavailable slots kept; spec lessons |
| `a88a1f5` | `--final-workers` (resource only; recipe unchanged) after the OOM of attempt 2 |
| `a787257` | Round-1 audit repairs (see below): context-specific history recomputation for rows exposed to an excluded report family; replay rebuilt from raw/snapshot sources with full dependency, slot and metric coverage; strict cohort keys in the evaluator; partial original reports kept for ledger QC |

## Runs and tests

| Item | Code | Command | Outcome |
|---|---|---|---|
| Focused unit tests | `a787257` | `pytest tests/unit/test_somalia_v4.py` | 24 passed (incl. history recomputation identity/exclusion, history-only pool exclusions, key `hx`, strict cohort keys, partial originals) |
| Synthetic smoke + replay | `a787257` + replay vectorization | `pytest tests/smoke/test_somalia_v4_pipeline.py` | 1 passed (synthetic 2016-2026 panel with an overlapping Jan-Mar 2023 window and partial March reports, so test-row history overrides occur; replay of its output passes every check) |
| Legacy Somalia regression | `a787257` | `pytest tests/unit/test_somalia_{q3opt,augment,oracle}.py tests/smoke/test_somalia_{augment,q3opt,oracle}_pipeline.py` | 55 passed |
| Real prepare-only | `e0757fc`+wip | `run_somalia_v4_calibrated_d.py --prepare-only --out-dir /tmp/somalia_v4_prepare` | inputs, cohorts, 142 jobs, 142 supported contexts (62 unique), 331 pool specs, 10,320 OOF fits planned, 0 empty pools |
| Bounded real pilot | `e0757fc` | `--workers 12 --pilot augmented:2024:0 --pilot original:2023:12 --out-dir /tmp/somalia_v4_pilot` | exit 0, 611 s, 1,056 OOF fits, 9 final fits; replay 94/94 (`pilot_replay_summary.json`); free memory fell to ~200 MB in the final-fit phase |
| Production attempt 1 | `e0757fc` | `--workers 10` | stopped by the executor at 50% OOF after the review finding (no outputs kept) |
| Production attempt 2 | `5fbe597` | `--workers 10` | OOF + selection completed; final fits OOM-killed (BrokenProcessPool) at 35/142 (`run_attempt2_oom_log.txt`); outputs discarded |
| Production run, round 1 | `a88a1f5` | `--workers 10 --final-workers 4` | exit 0, 5,180 s; replay 95/95; superseded by the round-1 repairs (`round1_run/`) |
| **Production run (evidence)** | **`a787257`** (only unrelated untracked `scripts/reporting/somalia_oracle_wrapup.py`) | `PYTHONPATH=src python -u scripts/modeling/run_somalia_v4_calibrated_d.py --workers 10 --final-workers 4 --overwrite` (output root held only an undeletable empty directory) | exit 0, 5,301 s; 10,320 OOF fits, 62 selections × 144 recipes, 142 final fits, 49 history-override test rows (`run_manifest.json`, `run_log.txt`, `history_overrides.csv.gz`); history identity gate identical at all horizons (`history_identity_check.csv`) |
| Independent replay | `a787257` | `scripts/postprocessing/replay_somalia_v4.py --out-dir results/experiments/somalia_oracle/v4_calibrated_d` | **105/105** checks (`replay_checks.csv`): label ledger rebuilt from the raw panel + validity snapshot (keys, copies, lineage, availability, values), realized-weather verification rebuilt from raw, config/input/snapshot digests, 40/8 slot inventory, job/context reconciliation, cohorts + digests, every pool rebuilt from its spec with exposed rows recomputed, member/calibration/final-calibration/final-fit temporal, family and history isolation incl. `hx`, 49 override baselines rebuilt, final-fit decay weights, 8,928 candidate scores and all 142 selections, final test keys/mappings/bounds, 43,864 saved-model probe rows (49 with override features), every reported annual/pooled metric field and composition |
| Full suite | `a787257` | `pytest tests` | 12 failed / 290 passed; the 12 are the known pre-existing alert-risk-map / launch-CLI baseline (`full_suite_result.txt`) |

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
| AC7 evidence/checks | Focused tests cover each boundary in implement.md §5 (24 unit tests incl. context-specific history, copied-row origin, transitive purge, H12 origin, unsupported-not-shrunk, residual-required-on-baseline, keyed joins, G9, round-trip floats); replay above |
| AC8 lifecycle | `lifecycle.md`; run `0e231056…`, executor session `7cea05f8…`, base `5b053ff` |

## Results (retrospective oracle-information evaluation; `results_summary.md`)

Pooled 2022-2026, each setting on its own population (not comparable across settings; not an augmentation effect):

| Setting | H | n | Final R² | RMSE (pp) | Final AUC | F1 |
|---|---|---:|---:|---:|---:|---:|
| original | 0 | 5,228 | −0.118 | 20.25 | 0.673 | 0.754 |
| original | 3 | 2,723 | −0.471 | 26.20 | 0.648 | 0.759 |
| original | 6 | 2,723 | −0.618 | 27.48 | 0.542 | 0.619 |
| original | 12 | 3,680 | −1.400 | 31.63 | 0.423 | 0.523 |
| augmented | 0 | 9,017 | 0.166 | 18.99 | 0.747 | 0.793 |
| augmented | 3 | 6,512 | −0.193 | 24.22 | 0.671 | 0.736 |
| augmented | 6 | incomplete | | | | |
| augmented | 12 | 7,469 | −1.051 | 30.93 | 0.420 | 0.569 |

Annual slots: 35 complete, 4 structurally empty (2026 H3/H6 in both settings: no verified realized weather after the 2025 forward-fill), 1 incomplete. Largest errors are in 2022-2023 (e.g. original 2022 H0 bias −22 pp, 2023 H0 +21 pp): training labels before 2022 cover only 73-74 coarse areas, while 2022 onwards covers ~350-900 areas.

### Incomplete slot (G9)

`augmented 2023 H6` (origins 2023-02, 2023-03; 696 of 2,013 keys) selected residual X6 / 12-month / isotonic on its scoring keys. The final mapping must be refit on the latest three rounds (2022-05/07/10); at H6 the 348 areas first labelled in 2022-07 have no history before T−6, so the residual branch has 2 baseline rows in a single round (minimum two rounds). Per G9 the selected mapping stays unavailable — no clipped-raw substitution and no switch of method — so this annual slot and the augmented H6 pooled result are reported incomplete. The other 39 slots and seven pooled results are unaffected. Selecting only recipes whose final mapping is supported would be a change to the approved selection contract and was not made after seeing this outcome.

## Audit round 1 (Codex gpt-6-astra, xhigh; `audits/close_audit_1.json`, `audits/spot_audit_1.json`) and repairs

Both audits of `fef36dd` returned `findings`. Classification (user rule: does it change a result?):

| Finding | Class | Changes a result? | Repair (`a787257`) |
|---|---|---|---|
| spot A02 / close A03: excluded report families still reach rows through precomputed history features / residual baselines | correctness | **Yes**: 49 outer test rows of `augmented_y2023_h00_o2023-03` used the held-out January 2023 report as history/baseline (no OOF pool affected) | `V4History`: rows of a context whose history contains an excluded family (fitting rows, OOF prediction rows, outer test rows) get rich history, residual baseline and categorical history recomputed without it; pool specs keep history-only exclusions; keys carry `hx`/`base_ok`; identity gate |
| close A01 / spot A01: replay does not rebuild source labels or traverse history/final-calibration dependencies | reproducibility (evidence) | No | Replay rebuilds labels/copies from raw + snapshot and weather verification from raw, checks digests, traverses final calibration and history exposure, rebuilds override baselines |
| close A02 / spot A03: replay misses slot inventory, some metric fields, context reconciliation | reproducibility (evidence) | No | 40/8 inventory, job/context/selection reconciliation (`n_cand == 144 × contexts`), every metric field + composition |
| spot A05: evaluator silently ignores prediction keys outside the cohort | data integrity | No (production keys matched) | `v4_evaluate` raises; replay checks per-slot keys |
| A04 (both): partial original reports dropped before history QC | contract (inherited) | No (no partial blocks in raw) | `mark_partial_originals` keeps them as originals for ledger QC |

Numeric effect of the repair (all other 38 annual and 7 pooled slots identical to round 1): augmented 2023 H0 final R² −0.192 → −0.209, RMSE 22.68 → 22.84 pp, AUC 0.826 → 0.824; augmented pooled H0 final R² 0.170 → 0.166, AUC 0.749 → 0.747.

## Audit round 2 (`audits/close_audit_2.json`, `audits/spot_audit_2.json`, completion `6fde76f`) and closure decision

Both round-2 audits confirm that the result-changing round-1 defect (held-out history; all 49 affected rows) and the partial-original omission are resolved, and that production labels, memberships, seasonal values, repaired features and metrics match their independent checks. Remaining findings, none of which changes a reported number:

- major, reproducibility (both audits): the replay can still pass on deliberately damaged artifacts (contexts/recipes relabelled unsupported skip selection replay; a deleted final-fit ledger passes vacuously; derived truth/QC fields and calibration memberships are trusted rather than rebuilt);
- minor: some reported metric metadata (coverage counts, F2, undefined-metric reasons, pooled years, cells of incomplete slots) is not compared; the evaluator silently drops predictions placed in empty or undeclared slots; `--final-workers` is not capped by `max_workers` (the run used 10/4).

Under the user's repair-loop rule (same class reported again in round 2) the executor stopped and asked. Cost so far: two manual audit rounds, one repair pass, two complete and two aborted production runs (~15 h wall time); numbers changed only by the round-1 repair (augmented 2023 H0 and augmented pooled H0). **User decision (2026-10-01): "Close now"** — keep the round-2 findings as audit debt (reproducibility/minor are non-gating under the controller policy) and close through `trellis-audit close`, without a further repair loop.

## Known limitations

- Oracle information (ideal label availability, realized future weather); retrospective on years partly inspected in v1-v3.
- H>0 outer cohorts keep only verified-weather rows (inherited rule); 2025 H3/H6 keep 275/1,876 rows, 2025 H12 1,100, 2026 H12 132.
- Copies of one assessment are repeated monthly truth, not independent observations; augmented pooled scores weight long validity windows more.
- 1,008 of 8,928 context×recipe evaluations are unsupported, all residual learned mappings lacking calibration support; recorded with reasons in `candidate_scores.csv.gz`.
- Upstream climate QA/provenance gaps listed in research.md are inherited, not repaired.

## Closure (2026-10-01)

`trellis-audit close` from pane `wJ:p1` was refused ("Repository is not registered to this executor session"): after the conversation was resumed, Herdr reports Claude session `1e0a5209-65ee-4cb5-ab9b-e8b00bc45f0f` on terminal `term_65cc540c2e07c1`, while run `0e231056d9a04cf18d13ebb9495d1920` is owned by session `7cea05f8-50d5-408d-aada-1948f70c734c` / `term_65cb900f23bc17`; an active run cannot change owner. The failed attempt changed nothing (run still active; the temporary local `.git/info/exclude` entry for the unrelated untracked wrapup script was restored).

User decision (2026-10-01, answering the close-path question): **"Native archive + waiver"** — record this authorization, archive the task with native `task.py archive`, and mark run `0e231056` closed with `waived: true` in the controller DB after a backup (same procedure as `somalia-auc-r2-optimization`, run `b909fb2c`). No controller close-audit job is enqueued. The audit record for this task is the two rounds of manual Codex gpt-6-astra xhigh spot and close audits in `audits/` (round 2: findings, non-result-changing, accepted as audit debt by the user's "Close now" decision). No audit pass is claimed.
