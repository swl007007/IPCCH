# Contract: 2025 Alert Risk Maps CLI

## Command

```bash
PYTHONPATH=src python scripts/reporting/plot_2025_alert_risk_maps.py [OPTIONS]
```

The command runs from the repository root and generates the four requested 2025 final figures. The workflow year is fixed at 2025 for this feature.

## Inputs

### Path inputs

| Option | Required | Description |
|--------|----------|-------------|
| `--prediction-root PATH` | No | Root directory containing existing deep-feature weight-decay prediction outputs. Defaults to the project experiment root when available. |
| `--spatial-path PATH` | No | External spatial boundary file, expected to support `area_id` joins. Defaults through project path configuration when available. |
| `--out-report-dir PATH` | No | Directory for final human-readable figures. Must resolve under `reports/` unless user intentionally supplies an allowed reports subdirectory. |
| `--out-results-dir PATH` | No | Directory for optional validation summaries. Must resolve under `results/`. |
| `--horizon-0m-file PATH` | Conditional | Explicit 0m prediction CSV. Required when discovery is ambiguous. |
| `--horizon-3m-file PATH` | Conditional | Explicit 3m prediction CSV. Required when discovery is ambiguous for actual-vs-predicted maps. |
| `--horizon-6m-file PATH` | Conditional | Explicit 6m prediction CSV. Required when discovery is ambiguous for actual-vs-predicted maps. |
| `--somalia-horizon-0m-file PATH` | Conditional | Explicit Somalia-scope 0m prediction CSV from global-grouping/global-Somalia outputs. Required when Somalia discovery is ambiguous. |
| `--somalia-horizon-3m-file PATH` | Conditional | Explicit Somalia-scope 3m prediction CSV from global-grouping/global-Somalia outputs. Required when Somalia discovery is ambiguous. |
| `--somalia-horizon-6m-file PATH` | Conditional | Explicit Somalia-scope 6m prediction CSV from global-grouping/global-Somalia outputs. Required when Somalia discovery is ambiguous. |

### Behavior options

The workflow always filters to year 2025.

| Option | Default | Description |
|--------|---------|-------------|
| `--overwrite` | `false` | Allows replacing existing final figures and validation summaries. Without it, existing targets cause failure before writing. |
| `--write-validation-summary` | `true` | Writes machine-readable validation/run summary under `results/`. |
| `--no-basemap` | `false` | Disables contextual basemap tiles while keeping data overlays interpretable. |
| `--figure-format FORMAT` | `png` | Final figure format. Must still produce clear report filenames. |

## Required prediction columns

### Actual-vs-predicted maps

- `area_id`
- `overall_phase`
- `overall_phase_pred`
- a usable temporal field: `date`, or `year` plus `month`

### Top-risk maps

- `area_id`
- `phase3_worse`
- `phase3_pred`
- a usable temporal field: `date`, or `year` plus `month`

## Required spatial columns

- `area_id`, or a documented equivalent that the workflow normalizes to `area_id`
- geometry
- country-identifying attribute for Somalia filtering when Somalia filtering cannot be derived from prediction inputs

## Outputs

### Final figures under `reports/`

Expected filename pattern:

```text
ipcch_2025_<scope>_<horizon_group>_<map_type>.<format>
```

Required final figures:

```text
ipcch_2025_global_0m-3m-6m_actual_vs_predicted_alert_map.png
ipcch_2025_somalia_0m-3m-6m_actual_vs_predicted_alert_map.png
ipcch_2025_global_0m_top30_phase3_risk_comparison_map.png
ipcch_2025_somalia_0m_top30_phase3_risk_comparison_map.png
```

### Optional validation summaries under `results/`

Suggested filename pattern:

```text
ipcch_2025_alert_risk_maps_validation_summary.json
```

The validation summary includes selected files, duplicate filtering counts, spatial join counts, rejected Somalia-local candidates, planned outputs, and status/errors.

## Success behavior

The command exits successfully only when:

1. Required prediction and spatial inputs are present.
2. Each requested horizon has exactly one selected prediction file, or explicit files resolve ambiguity.
3. Somalia-only inputs are global-grouping/global-Somalia outputs, not Somalia-local outputs.
4. Prediction records are filtered to 2025 before latest-record selection.
5. Each horizon/scope dataset has at most one row per `area_id` after filtering.
6. 100% of filtered prediction `area_id` records join to spatial boundaries.
7. Final output files do not already exist, or `--overwrite` is set.
8. Four final figures are saved under `reports/`.

## Failure behavior

The command exits non-zero and writes no final figure when any of the following occurs:

- Missing prediction root, prediction file, spatial file, or output directory permission.
- Missing required prediction or spatial columns.
- No 2025 records for a required horizon/scope.
- Duplicate latest records remain for any `area_id`.
- Ambiguous horizon discovery without explicit file input.
- Somalia-local model output selected or indistinguishable from a valid Somalia global-grouping output.
- Any filtered prediction `area_id` fails to join to spatial boundaries.
- Joined spatial records duplicate an `area_id`.
- Existing output file conflict without `--overwrite`.

Failure messages must name the affected horizon, scope, file, column, `area_id` sample, or output path where applicable.

## Lightweight validation commands

```bash
PYTHONPATH=src python scripts/reporting/plot_2025_alert_risk_maps.py --help
PYTHONPATH=src python -c "import ipcch.alert_risk_maps"
```

Tiny smoke tests should use synthetic prediction CSVs and a small synthetic spatial file; they must not run model training or notebooks.
