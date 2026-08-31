# Specification Quality Checklist: Nigeria Weather-Land XGBoost Rerun

**Purpose**: Gate execution until reverse stress testing converges  
**Created**: 2026-08-25  
**Feature**: [spec.md](../spec.md)

## Contract Quality

- [x] Baseline architecture is unambiguous
- [x] Input release and scope mapping are explicit
- [x] No-leak holdout boundary is preserved
- [x] Threshold, seed, half-life, identifiers, and hyperparameters are frozen
- [x] Historical outputs cannot be overwritten
- [x] Dirty-worktree provenance is addressed
- [x] Structural and failed-source missingness are addressed
- [x] Partial completion semantics are defined
- [x] All-null predictor handling is confirmed by the user
- [x] No open Blocker or Major decision remains

## Execution Gate

- [x] User confirms shared understanding and authorizes execution

## Validation

- [x] Enhanced preflight manifest reports PASS for all assertions
- [x] Native dry-run completes for fs0, fs1, and fs2 without fitting
- [x] Full fs0, fs1, and fs2 runs exit successfully
- [x] Each scope contains 13 result files and 3 report files
- [x] Prediction keys and row counts match the historical eligible evaluation samples
- [x] Paired overall-phase MAE comparison contains 12 scope-year rows
- [x] Historical experiment artifacts predate all new experiment artifacts

Execution and validation completed on 2026-08-25. No unchecked contract item remains.
