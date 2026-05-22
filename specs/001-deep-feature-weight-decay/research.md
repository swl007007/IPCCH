# Research: Deep Feature Weighted Decay Forecasting

## Decision: Implement as a new modelling CLI entry point plus small reusable package helpers

**Rationale**: The feature must not modify the original forecasting notebook, must be runnable from the repository root, and must expose configurable external paths and decay settings. Existing project conventions already place reusable Python utilities under `src/ipcch/` and modelling entry points under `scripts/modeling/`.

**Alternatives considered**:
- Modify `notebooks/modeling/Table1_Forecasting_main.ipynb`: rejected because the spec and constitution explicitly require preserving the notebook unchanged and avoiding automated heavy notebook execution.
- Put all logic in a standalone script: rejected because reusable path, split, weighting, and metric helpers would be harder to test and would duplicate project primitives.

## Decision: Use all eligible records before each test year for annual holdouts

**Rationale**: Clarification selected all-prior-history training even if the reference notebook uses a shorter fixed window. This preserves strict temporal integrity because every training record remains strictly before January 1 of the test year while allowing the corrected deep-feature dataset to use all historical training signal.

**Alternatives considered**:
- Preserve fixed three-year windows: rejected by clarification.
- Stop if the notebook differs: rejected by clarification; implementation should document the intentional split rule.

## Decision: Treat the all-prior-history split as constitution-aligned

**Rationale**: The constitution now allows feature-declared all-prior-history annual holdouts when training rows are strictly before the test year. This feature intentionally includes older records so the time-decay weights can downweight rather than exclude them.

**Alternatives considered**:
- Use fixed three-year windows: rejected by clarification because it would exclude older eligible observations instead of downweighting them.
- Treat the split as a constitution exception: rejected after the constitution was amended to make declared all-prior-history holdouts valid.

## Decision: Use an exponential half-life parameter with default 24 months

**Rationale**: Clarification selected a default half-life of 24 months. The half-life form is easier to interpret than a raw monthly decay rate: a row 24 months before the test start receives half the weight of a row at the test boundary under the same formula.

**Alternatives considered**:
- Require explicit parameter for every full run: rejected by clarification.
- Default raw decay rate: rejected because it is less directly interpretable for researchers.

## Decision: Preserve existing phase conversion and hyperparameter conventions

**Rationale**: The constitution and CLAUDE.md identify four cumulative XGBoost regressors, phase-3-specific hyperparameters, and top-down `convert_prob_to_phase()` threshold behavior as canonical project conventions. The feature adds weights and metrics but does not redesign model architecture.

**Alternatives considered**:
- Add a new thresholding method or tune thresholds on the new dataset: rejected because threshold selection could introduce leakage if not carefully nested and is outside scope.
- Train a single multiclass model: rejected because it changes the modelling design.

## Decision: Compute F2 on discrete phase 3+ labels and report undefined metrics as unavailable with a reason

**Rationale**: The spec clarifies phase 3+ as the crisis positive class and selected explicit unavailable statuses for undefined denominator or validity cases. This avoids treating mathematical undefined cases as zero performance.

**Alternatives considered**:
- Compute F2 on continuous phase-3+ scores: rejected because the feature asks for reporting alongside classification metrics and the project’s primary output is discrete phase classification.
- Use zero for undefined metrics: rejected by clarification because it could mislead scientific interpretation.

## Decision: Derive Somalia area identifiers from the configured completed IPCCH source, ISO3-first

**Rationale**: The Somalia-only analysis must not hardcode area IDs. Using ISO3 `SOM` when available is less ambiguous than country-name matching. Normalized country-name fallback handles lookup sources that lack ISO3.

**Alternatives considered**:
- Hardcode Somalia `area_id` values: rejected because source data can change and area lists should be derived from the authoritative external lookup.
- Require one exact country column name: rejected because the source may expose equivalent country fields.

## Decision: Add external path keys for the new forecasting-ready dataset and Somalia lookup

**Rationale**: `src/ipcch/paths.py` already resolves external paths through documented defaults and ignored `configs/paths.local.json`. Adding keys such as `deep_features_forecasting_dataset` and `ipcch_2026_completed_dataset` keeps machine-specific Windows paths out of source code.

**Alternatives considered**:
- Require path arguments every time: rejected because project scripts usually provide sensible defaults from `ipcch.paths`.
- Commit absolute Windows paths: rejected by constitution.

## Decision: Validation relies on dry-run, CLI help, import checks, and small/synthetic smoke tests

**Rationale**: The constitution prohibits automated heavy notebook/model training unless explicitly requested. The feature requires a lightweight validation mode that can inspect columns, splits, features, weights, and output plans without fitting full annual models.

**Alternatives considered**:
- Run full 2022-2025 training as validation: rejected as too expensive and against execution discipline.
- Validate only by static inspection: rejected because split and weight behavior should be exercised on real or synthetic data.
