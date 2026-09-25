# Evidence — somalia-oracle-audit-repair

Evidence Status: Ready. Validation Status: Executed.

## Findings addressed

| Source | ID | Severity | Fix (commit `f576e69`) | Regression check |
|---|---|---|---|---|
| Spot audit (Codex gpt-6-astra high) | A01 | major | `data._exact_crisis_state` sums S from the same exact decimals as P3+P4+P5 | `test_history_crisis_state_exact_at_twenty_percent_boundary` (area 1602/2019-07 .59/.21/.12/.08/0 → 0) |
| Spot audit | A02 | minor | history QC keeps finite/nonnegative/positive-sum (G4), missing-P5 and population rules; no per-component ≤1 bound | `test_history_qc_follows_g4_without_component_upper_bound` |
| Spot audit | A03 | minor | `data.mask_unverified_category_history` blanks `overall_phase_prev_observed_asof_sH` unless its source month `T-max(1,H)` is a valid ledger phase | `test_category_history_masked_when_source_label_invalid`; run masks 4 (H=3) and 3 (H=6) values |
| Close audit job 183ebb4c | A01 | minor | replay records `prediction_coverage`, `contrast_present`, `contrast_vectors_available`, `bootstrap_bundle_present` checks | smoke test drops one A prediction → replay fails; on saved v1 outputs the same perturbation yields 6 failed checks |

Measured feature impact before refit: 8 history crisis states changed; changed feature-matrix rows 3/7/6/3 of 5,837 at H=0/3/6/12; frozen cohort ledger identical.

## Runs and tests

- Full rerun from `f576e69` (manifest `run_manifest.json`, HEAD recorded; only this task's `task.json` dirty): exit 0, 80/80 arm cells completed.
- Replay with stricter coverage: 630/630 checks passed (`replay_checks.csv`).
- `pytest tests/unit/test_somalia_oracle.py` → 23 passed; smoke test in an isolated clone at `f576e69` → 1 passed (655 s).

## Result changes (`metrics_before_after.csv`, `contrasts_before_after.csv`)

23 of 86 metric rows changed, all at H=3/H=6 (H=0 and H=12 unchanged). Example: 2025 H=3 primary F2 A .813→.803, B .803→.786, C .803→.793, D .754 (unchanged, accuracy .531→.556). Direction-relevant changes: 2025 H=3 D−C is now −0.039 [−0.086, 0.000] (previously excluded zero); 2025 H=3 C−B is +0.007 [−0.005, 0.024]; 2025 H=6 B−A +0.010 [−0.008, 0.032]. The overall reading — small, mixed within-horizon specification differences, always-crisis F2 comparable to or above the models, all arms above persistence — is unchanged.

## Remaining disclosed gaps (not repairable from available evidence)

- G1: V2 generation/calibration provenance (climatology periods, SPI/SPEI fitting windows) is not bound to the V2 file hash. No build manifest exists in `IPCCH_shared_folder`; the user accepted climate-feature calibration provenance in the controller close-audit session ("气候特征校准来源可以给通过").
- G2: affirmative source-product evidence that retained raw monthly rain/temperature are independent realized observations is not available; the implementation uses a conservative screen (finite and not an exact previous-month repeat) and excludes the frozen/forward-filled months. This remains a stated limitation of the oracle arm, not a verified provenance claim.
