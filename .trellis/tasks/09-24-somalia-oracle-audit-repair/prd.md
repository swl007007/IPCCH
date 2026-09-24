# Somalia oracle audit repair

Repairs audit findings on the archived task `somalia-flood-food-crisis` (completion `264a986`). Scope is limited to these defects; the approved PRD/design of the original task remain the contract.

Sources: independent Codex gpt-6-astra (reasoning high) spot-audit `/tmp/som/spot-audit/result.json` (verdict incomplete: A01 major, A02/A03 minor, gaps G1/G2) and controller close-audit job `183ebb4c17904810f7b9582e` (A01 minor).

## Requirements

- R1 (spot A01): history crisis state uses exact decimal arithmetic on the source components: `5*(P3+P4+P5) > S` with S summed from the same exact decimals (reference `IPCCHGeoRFExperiment/prepare_data.py:198-222`). Regression: area 1602/2019-07 shares (.59,.21,.12,.08,0) → state 0.
- R2 (spot A02): history QC applies the G4 rule (finite, nonnegative components, positive finite sum) instead of a per-component `<=1` bound; the missing-P5 fallback and positive-population rule stay.
- R3 (spot A03): every retained base categorical-history field (`overall_phase_prev_observed_asof_sH`, source month `T-max(1,H)`) is masked to NaN unless its source key is a valid reported phase in the label ledger (including provenance). Regression: an excluded source key cannot enter any feature.
- R4 (close A01): the independent replay fails (records a failed coverage check) when any arm lacks a prediction for a frozen nonempty cohort key or a required contrast is missing.
- R5: rerun the full experiment from committed code, rerun replay, refresh evidence; report changed results honestly.
- Gaps G1 (V2 build/calibration provenance) and G2 (affirmative realized-weather provenance) cannot be produced from repository or available source evidence; they are recorded as disclosed limitations (the user accepted climate-feature calibration provenance in the close-audit session). No source files are modified.

## Acceptance

Focused unit tests for R1–R4 pass; full run completes; replay passes with the stricter coverage checks; evidence documents before/after metric changes.
