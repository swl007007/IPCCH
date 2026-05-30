# Research: Launch Forecast Scope

## Decision: Use period-aware scoped alignment, not row shifting

**Decision**: For scope `s`, construct training/evaluation rows by joining target rows `y(area_id, t)` to time-varying predictors from `X(area_id, t - s months)` within the same `area_id`, plus static predictors for that `area_id`.

**Rationale**: The spec explicitly requires preventing leakage and avoiding ambiguous dataframe shifts. A period-aware join makes the lag direction testable, supports sparse month histories, and prevents cross-area borrowing.

**Alternatives considered**:

- DataFrame `shift(s)` within each area: rejected because row order and missing months can make the shift represent records rather than calendar months.
- Shifting target dates forward instead of joining feature dates backward: equivalent if done carefully, but less transparent for validation.

## Decision: Launch prediction records are separate from training/evaluation records

**Decision**: Training/evaluation preparation requires target outcomes and aligned earlier feature rows. Launch prediction preparation requires valid feature-period predictor rows and computes target period as `feature_period + scope`; it must not require target-period target or actual rows.

**Rationale**: Scope 3 and scope 6 launch predictions target future periods where actuals and target rows are not expected to exist. Treating missing July/October 2026 rows as missing prediction records would block the main feature.

**Alternatives considered**:

- Reusing the training/evaluation alignment function for prediction: rejected because it would encourage target-period row requirements and confuse feature period with target period.
- Creating synthetic future target rows: rejected because it adds fake labels and increases leakage/reporting risk.

## Decision: Static feature classification remains config-driven, validated by area-level invariance

**Decision**: The workflow config remains the source of truth for static features. The config-recognized static list is generated or validated by scanning existing feature data for predictors whose observed non-missing values are invariant within each `area_id` across `year`/`month`. Missing classification is regenerated or validated according to existing conventions; unresolved inconsistency fails before training.

**Rationale**: The project already uses config-driven feature definitions, but the config list is derived from observed feature behavior. Validating this boundary prevents dynamic features from being mistakenly carried forward unshifted.

**Alternatives considered**:

- Manually declared static list only: rejected because it contradicts the project convention described by the spec.
- Infer static features on every run and ignore config: rejected because the config must remain the workflow source of truth.
- Treat all predictors as time-varying: rejected because static geographic and identifier-derived attributes should not be shifted by period.

## Decision: Preserve scope 0 legacy outputs and add scope-aware coexistence for new scopes

**Decision**: Scope 0 keeps legacy prediction values and downstream-compatible output names/paths unless intentionally migrated. Scope 3/6 outputs must be scope-qualified and cannot overwrite scope 0. The workflow may also emit scope-qualified scope 0 metadata or copies.

**Rationale**: Existing users and downstream scripts depend on the April 2026 scope 0 layout. Forward-scope artifacts need clear separation without breaking current behavior.

**Alternatives considered**:

- Move all outputs into scope-qualified directories immediately: rejected because it risks breaking existing scope 0 consumers.
- Keep a single output path for all scopes: rejected because it would overwrite artifacts and obscure target periods.

## Decision: Visualization/reporting is driven by target-period actual availability

**Decision**: If target-period actuals are unavailable, produce predicted-only visualization and skip/mark/omit actual-dependent metrics and reports. If actuals are available and comparison mode is requested, actual-vs-predicted visualization may run. Scope 0 keeps existing actual-vs-predicted behavior when actuals are available.

**Rationale**: Future actuals for July/October 2026 are unavailable during launch, but predictions and maps remain useful. The same rule also generalizes to future scoped runs once actuals become available.

**Alternatives considered**:

- Disable maps for scope 3/6: rejected because forecast-only maps are a required deliverable.
- Force two-panel maps with blank actual panels: rejected because it creates misleading visual output and noisy validation failures.

## Decision: Validate with unit/smoke tests and synthetic data only

**Decision**: Implement targeted unit tests for alignment, static validation, output metadata, and visualization behavior; use CLI `--help` and validation-only smoke tests. Do not run heavy model training or notebooks during implementation validation.

**Rationale**: The constitution forbids automation from executing heavy training unless explicitly requested. Synthetic frames can test all scope and leakage semantics without model cost.

**Alternatives considered**:

- End-to-end full launch training for verification: rejected for cost and user instruction constraints.
- Notebook validation: rejected because launch behavior is in reusable scripts/modules and notebooks are not the target.
