# Contract: Launch Scope CLI and Outputs

## Command Surface

Primary command:

```bash
PYTHONPATH=src python scripts/modeling/run_launch_nowcasting_2026_04.py [existing options] --scope {0,3,6}
```

## New CLI Argument

### `--scope`

- Type: integer choice
- Allowed values: `0`, `3`, `6`
- Default: `0`
- Meaning: number of calendar months between feature period and prediction target period

| Scope | Feature Period Example | Target Period Example | Expected Actual Requirement |
|-------|------------------------|-----------------------|-----------------------------|
| 0 | April 2026 | April 2026 | Actuals may be used when available |
| 3 | April 2026 | July 2026 | Future target/actual rows are not required for prediction |
| 6 | April 2026 | October 2026 | Future target/actual rows are not required for prediction |

## Validation Contract

The command must reject before model training begins when:

- `--scope` is not one of `0`, `3`, or `6`.
- required area/month period keys are missing.
- required predictor columns from config are missing.
- scoped training/evaluation alignment leaves no usable labeled records.
- launch prediction has no usable feature-period prediction records.
- static/time-varying classification cannot be generated, validated, or resolved according to project conventions.

The command must not reject launch prediction solely because target-period target or actual rows are unavailable for scope 3 or scope 6.

## Prediction Output Contract

Prediction CSV outputs must preserve existing canonical prediction columns and include or preserve these metadata concepts for scoped runs:

- `scope_months`
- `feature_period` or equivalent feature `year`/`month` fields
- `target_period` or equivalent target `year`/`month` fields
- existing launch metadata such as `launch_month`, `model_workflow`, `scale`, `threshold`, `training_cutoff`, `comprehensive_source`, and `run_id`

Scope 0 must preserve legacy prediction values and downstream-compatible outputs. Scope 3 and scope 6 outputs must be path- or filename-distinguished from scope 0.

## Visualization Contract

Visualization behavior is determined by target-period actual availability:

- If target-period actuals are unavailable, output predicted-only visualization.
- If target-period actuals are available and comparison mode is requested, actual-vs-predicted visualization may be produced.
- For scope 0 with target-period actuals available, existing actual-vs-predicted visualization behavior must remain available.
- For scope 3 and scope 6 launch runs, predicted-only maps are the default because future actuals are unavailable.

## Reporting Contract

Actual-dependent metrics, reports, and summaries must be skipped, marked unavailable, or omitted clearly when target-period actuals are missing. Prediction artifacts and forecast-only maps should still be produced.

## Compatibility Contract

- Existing scope 0 workflows without `--scope` behave as scope 0.
- Existing scope 0 output names/paths remain available unless intentionally migrated.
- Optional scope-qualified scope 0 copies or metadata may be emitted.
- Scope 3/6 artifacts must not overwrite scope 0 artifacts.
