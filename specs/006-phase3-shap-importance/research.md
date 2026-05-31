# Research: Phase-3 SHAP Six-Category Feature Importance

## Decision: SHAP execution is opt-in and fail-fast when unavailable

**Rationale**: The default forecasting workflow must remain unchanged. When a user explicitly requests SHAP, missing or incompatible explanation support means the requested deliverable cannot be produced, so the run should fail with a clear diagnostic rather than silently omitting outputs.

**Alternatives considered**:
- Continue predictions and warn: rejected because it can look like a successful SHAP run while omitting required artifacts.
- Auto-disable SHAP: rejected because it hides user intent and weakens reproducibility.

## Decision: Explain only the fitted `phase3_worse` cumulative regressor

**Rationale**: The feature is phase-3-only and must not explain final phase labels, phase-2, phase-4, phase-5, or classifier models. The SHAP feature matrix must use the exact columns, order, and preprocessing state used to fit the phase-3 model for that scope-year split.

**Alternatives considered**:
- Explain all four cumulative regressors: rejected as out of scope and likely to produce unwanted phase-4/phase-5 artifacts.
- Explain `overall_phase_pred`: rejected because it is a derived phase-conversion output, not the fitted regressor target.

## Decision: Default explanation sample is the phase-3 training feature matrix

**Rationale**: The reference research convention explains training rows. This default also provides stable feature-family summaries for the fitted model. The sample type must be recorded in captions, matrix tables, and metadata, especially when users select test rows or another supported sample.

**Alternatives considered**:
- Test rows by default: rejected because it diverges from the reference convention.
- Both train and test by default: rejected because it doubles work/output volume and complicates the 6 x 4 deliverable.

## Decision: Crosswalk validation enforces exactly six display groups

**Rationale**: The final deliverable is a six-row heatmap per scope. The crosswalk must define exactly six distinct feature-group labels; outputs preserve those labels for display. If implementation uses aliases or canonical normalization for validation, those rules must be documented in metadata.

**Alternatives considered**:
- Hardcode six category names in code: rejected because the crosswalk is the source of truth for display labels.
- Permit arbitrary category counts: rejected because it violates the required 6 x 4 heatmap shape.

## Decision: Missing feature mappings fail by default, with explicit unmapped exclusion mode

**Rationale**: Failing by default prevents accidental loss of explanatory mass. When users explicitly allow unmapped features, unmapped absolute SHAP values are excluded from the six-category denominator so the output remains six rows; diagnostics report mapped sum, unmapped sum, and unmapped share for each scope-year.

**Alternatives considered**:
- Add an `unmapped` category: rejected because it changes the six-row output contract.
- Assign unmapped features to a default group: rejected because it creates misleading category attribution.

## Decision: Zero mapped denominator produces six zero relative values plus diagnostics

**Rationale**: A zero-denominator scope-year should preserve table and heatmap shape while making the condition explicit. Six `0` relative values are less ambiguous than blank values and avoid fabricating equal importance.

**Alternatives considered**:
- Missing/blank cells: rejected because it weakens matrix completeness.
- Equal 1/6 allocation: rejected because it invents importance not present in the SHAP values.
- Fail the scope-year: rejected because zero SHAP values are a valid diagnostic state.

## Decision: Raw row-level SHAP export requires explicit opt-in and size guard

**Rationale**: Row-level SHAP matrices can be very large. Summary tables and heatmaps are the primary deliverables, while raw values require explicit opt-in. Oversized raw exports require a size override or maximum-row limit.

**Alternatives considered**:
- Always write raw outputs: rejected due to storage and accidental artifact risk.
- Auto-downsample silently: rejected because it obscures reproducibility.
- Skip silently: rejected because it hides missing requested outputs.

## Decision: Deterministic artifact names include target, scope where applicable, and artifact type

**Rationale**: Deterministic names make outputs reproducible, auditable, and script-friendly. Including `phase3_worse`, forecasting scope, and artifact type prevents confusion with non-SHAP or non-phase-3 files.

**Alternatives considered**:
- Timestamp-only names: rejected because they are harder to compare across reproducible runs.
- Generic names without scope/target: rejected because multi-scope outputs become ambiguous.
