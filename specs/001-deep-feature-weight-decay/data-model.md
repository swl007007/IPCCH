# Data Model: Deep Feature Weighted Decay Forecasting

## ForecastingReadyDataset

Represents the corrected external modelling dataset used for the weighted-decay forecasting workflow.

### Required fields
- `area_id`: canonical spatial identifier.
- `year`: observation year, convertible to integer.
- `month`: observation month, convertible to integer in 1-12.
- `overall_phase`: observed IPC/CH phase label used for classification metrics.
- `phase1_percent`: observed population share in phase 1.
- `phase2_percent`: observed population share in phase 2.
- `phase3_percent`: observed population share in phase 3.
- `phase4_percent`: observed population share in phase 4.
- `phase5_percent`: observed population share in phase 5.
- Numeric forecasting-ready feature columns: already engineered, leakage-safe predictors.

### Derived fields
- `date`: first day of the month derived from `year` and `month`.
- `phase2_worse`: `phase2_percent + phase3_percent + phase4_percent + phase5_percent`.
- `phase3_worse`: `phase3_percent + phase4_percent + phase5_percent`.
- `phase4_worse`: `phase4_percent + phase5_percent`.
- `phase5_worse`: `phase5_percent`.

### Validation rules
- Required columns must exist before split preparation.
- `area_id` must be present or the workflow fails; incompatible identifiers are not accepted silently.
- `year` and `month` must form valid monthly dates.
- Candidate modelling features must be numeric and must exclude identifiers, dates, target columns, observed labels, predictions, metadata output fields, and target-derived leakage fields.
- Rows with missing target values are excluded only from the target-specific fitting or evaluation step where the target is required; exclusions must be reflected in diagnostics.

## AnnualHoldoutRun

Represents one annual evaluation for a single test year.

### Fields
- `test_year`: one of 2022, 2023, 2024, 2025.
- `test_start_date`: January 1 of `test_year`.
- `test_end_date`: January 1 of `test_year + 1`.
- `train_rows`: records with `date < test_start_date`.
- `test_rows`: records with `test_start_date <= date < test_end_date`.
- `feature_columns`: ordered list of selected non-target numeric predictors.
- `target_columns`: the four cumulative target columns.
- `time_decay_weights`: training weights aligned to train rows.
- `predictions`: per-row observed values, continuous predictions, and discrete phase prediction.
- `metrics`: overall annual metrics.

### Validation rules
- Exactly four runs are planned.
- No test-year or future record may enter `train_rows`.
- A run with no train rows or no test rows fails with a clear status rather than silently producing invalid metrics.
- Weight vectors must be aligned with target-specific training rows after dropping missing target values.

## TimeDecayWeights

Represents per-training-row sample weights for one annual holdout.

### Fields
- `half_life_months`: default 24 months, configurable.
- `distance_months`: whole months between the training row month and the holdout `test_start_date`.
- `weight`: exponential half-life weight.

### Validation rules
- `half_life_months` must be positive and finite.
- `distance_months` must be positive for all training rows under strict annual splits.
- More recent training rows must have larger weights than older rows.
- All final weights passed to fitting must be positive and finite.

## CumulativePhaseTarget

Represents one target in the four-model forecasting design.

### Values
- `phase2_worse`
- `phase3_worse`
- `phase4_worse`
- `phase5_worse`

### Relationships
- Each `AnnualHoldoutRun` trains one model per target.
- The phase-3 target uses phase-3-specific hyperparameter configuration when available.
- Continuous predictions for all four targets feed the existing discrete phase conversion convention.

## MetricsReport

Represents metric outputs for one or more annual holdouts.

### Fields
- `scope`: `overall` or `somalia`.
- `test_year`: annual holdout year.
- `n_samples`: number of evaluated test samples.
- `accuracy`: classification accuracy across phases 1-5, or unavailable with reason.
- `precision_phase3plus`: precision for phase 3+ crisis predictions, or unavailable with reason.
- `sensitivity_phase3plus`: recall for phase 3+ crisis observations, or unavailable with reason.
- `r2_phase3plus`: R2 for phase3_worse continuous predictions, or unavailable with reason.
- `f2_phase3plus`: F-beta score with beta 2 for discrete phase 3+ predictions, or unavailable with reason.
- `status`: completed, no eligible samples, or unavailable.
- `unavailable_reason`: populated when a metric or row is unavailable.

### Validation rules
- Undefined metrics are reported as unavailable with explicit reasons, not coerced to zero.
- Somalia metrics use the same field set as overall metrics.

## SomaliaAreaLookup

Represents the derived set of Somalia area identifiers used for country-specific filtering.

### Required source fields
- `area_id`.
- At least one country identifier field, preferably `ISO3`; otherwise a country-name field such as `country`, `country_en`, or equivalent.

### Derived fields
- `somalia_area_ids`: unique area identifiers where ISO3 is `SOM` or normalized country name is Somalia.

### Validation rules
- ISO3 matching takes precedence when an ISO3 field is present.
- Country-name matching is case-insensitive and normalized for whitespace.
- Duplicate area identifiers are de-duplicated.
- If no Somalia identifiers are found, Somalia metrics report a lookup failure or no eligible samples clearly.

## RunMetadata

Represents audit metadata for a workflow invocation.

### Fields
- `input_source_key_or_path`.
- `somalia_lookup_source_key_or_path`.
- `test_years`.
- `split_rule`.
- `target_columns`.
- `feature_count`.
- `decay_formulation`.
- `half_life_months`.
- `output_locations`.
- `run_timestamp`.
- `validation_mode`.

### Validation rules
- Metadata must be written for full runs and validation runs that plan outputs.
- Metadata must not contain copied raw data, only source identity and paths or keys.
