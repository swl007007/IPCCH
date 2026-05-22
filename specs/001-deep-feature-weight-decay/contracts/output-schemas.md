# Contract: Output Schemas

## Prediction CSV schema

One file per holdout year.

Required columns:
- `test_year`
- `area_id`
- `year`
- `month`
- `date`
- `overall_phase`
- `overall_phase_pred`
- `phase2_worse`
- `phase3_worse`
- `phase4_worse`
- `phase5_worse`
- `phase2_pred`
- `phase3_pred`
- `phase4_pred`
- `phase5_pred`

Optional diagnostic columns:
- source row index or stable row identifier, if needed for traceability.
- feature availability diagnostics, if generated.

Rules:
- Prediction rows must be test rows only.
- No training-only row may appear in prediction CSVs.
- Continuous phase prediction columns must correspond to the model target suffixes expected by the phase conversion utility.

## Metrics JSON schema

One JSON object per annual holdout year.

```json
{
  "test_year": 2024,
  "scope": "overall",
  "n_samples": 0,
  "accuracy": {"value": null, "status": "unavailable", "reason": "no eligible samples"},
  "precision_phase3plus": {"value": null, "status": "unavailable", "reason": "zero predicted phase3plus denominator"},
  "sensitivity_phase3plus": {"value": null, "status": "unavailable", "reason": "zero observed phase3plus denominator"},
  "r2_phase3plus": {"value": null, "status": "unavailable", "reason": "constant target"},
  "f2_phase3plus": {"value": null, "status": "unavailable", "reason": "precision or recall unavailable"}
}
```

Rules:
- Completed numeric metrics use `status: "ok"` and numeric `value`.
- Undefined metrics use `value: null`, `status: "unavailable"`, and a non-empty reason.
- Somalia metrics use the same metric object shape.

## Consolidated metrics CSV schema

Required columns:
- `scope`
- `test_year`
- `n_samples`
- `accuracy`
- `accuracy_status`
- `accuracy_reason`
- `precision_phase3plus`
- `precision_status`
- `precision_reason`
- `sensitivity_phase3plus`
- `sensitivity_status`
- `sensitivity_reason`
- `r2_phase3plus`
- `r2_status`
- `r2_reason`
- `f2_phase3plus`
- `f2_status`
- `f2_reason`

Rules:
- Missing numeric values must remain empty or null in CSV form and must be paired with an unavailable status and reason.

## Run metadata JSON schema

Required fields:
- `run_timestamp`
- `dataset_source`
- `somalia_lookup_source`
- `test_years`
- `split_rule`
- `target_columns`
- `feature_count`
- `feature_columns_hash_or_sample`
- `decay_formulation`
- `half_life_months`
- `output_locations`
- `dry_run`
- `notebook_modified`: must be false for this feature.

Rules:
- Metadata records source identity and paths/keys only; it must not embed raw source rows.
