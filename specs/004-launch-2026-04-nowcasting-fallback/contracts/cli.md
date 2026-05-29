# CLI Contract: `run_launch_nowcasting_2026_04.py`

Runs from the repository root (`pip install -e .` or `PYTHONPATH=src`). No hardcoded absolute paths; all paths via `ipcch.paths` defaults or explicit flags.

```
python scripts/modeling/run_launch_nowcasting_2026_04.py [OPTIONS]
```

## Flags

### Core / paths
| Flag | Type | Default | Purpose |
|---|---|---|---|
| `--comprehensive-source` | path | resolved via `ipcch.paths.external_path("deep_features_2026_target_corrected_dataset")` | The single fallback CSV (training + X_test). **This key is workspace-local and expected in `configs/paths.local.json`** (it is intentionally NOT added to `paths.py` `DEFAULT_EXTERNAL_PATHS`). If the key is unresolved and `--comprehensive-source` is not passed explicitly, the CLI MUST fail with a clear, actionable message stating: the missing key name `deep_features_2026_target_corrected_dataset`; that the user can either pass `--comprehensive-source <path>` or add the key to `configs/paths.local.json`; and the expected target file `assembled_IPCCH/features/forecasting_subset_IPCCH_2026_target_corrected_deep_features.csv`. |
| `--launch-month` | str `YYYY-MM` | `2026-04` | Launch (prediction) month |
| `--scale` | str | `global` | Only `global` supported |
| `--training-cutoff` | str `YYYY-MM-DD` | `2026-04-01` | Train strictly before this date |
| `--out-root` | path | `RESULTS_DIR/launch/nowcasting_2026_04` | Machine-readable output root |
| `--report-root` | path | `REPORTS_DIR/launch/nowcasting_2026_04` | Human-readable output root |
| `--seed` | int | `42` | XGBoost random_state |
| `--dedup-rule` | str | none | Only `latest-date` accepted; resolves duplicate April `area_id` rows deterministically (requires a date/timestamp column). Absent ⇒ duplicates hard-stop (FR-009) |

### Canonical model settings (R2, R3, R5)
| Flag | Type | Default | Purpose |
|---|---|---|---|
| `--hyperparameter-set` | str `{canonical,custom}` | `canonical` | `canonical` uses the plan-R3 forecasting files; `custom` requires the override paths below |
| `--hyperparameters` | path | `configs/forecasting_hyperparameters.json` | Phase 2/4/5 hyperparameter JSON (override) |
| `--hyperparameters-p3` | path | `configs/forecasting_hyperparameters_p3.json` | Phase 3 hyperparameter JSON (override) |
| `--add-identifier-features / --no-identifier-features` | bool | **on** | Canonical identifier-feature setting (FR-011a) |
| `--identifier-source` | path | `external_path("ipcch_2026_completed_dataset")` | Identifier lookup (admin_code/year/month/lat/lon) for `add_identifier_features`. **Used only when expected identifier-derived columns are absent** from the comprehensive source; if construction is requested but no lookup is configured, `--validate-only`/run fails with a clear message |
| `--allow-missing-identifier-features` | flag | off | Override the FR-011a stop when identifier features cannot be produced |
| `--half-life-months` | float | `24.0` | Time-decay half-life (anchored at launch month) |
| `--no-time-decay` | flag | off | Fit unweighted instead of canonical time-decay |
| `--threshold` | float | `0.2` | **Fixed/informational** (provenance + config compatibility). Only `0.2` is accepted; any other value fails with a clear message that the launch is constitutionally fixed to canonical `th=0.2` (no tuning). Recorded as `threshold=0.2` in `run_summary.json` |
| `--drop-nonfinite-predictions` | flag | off | Documented fallback for non-finite cumulatives (else fail) (FR-017a) |

### Execution modes (FR-036)
| Flag | Type | Purpose |
|---|---|---|
| `--skip-training` + `--model-artifact-dir <dir>` | flag+path | **Mode 2**: load fitted models, predict |
| `--skip-prediction` + `--predictions <csv>` | flag+path | **Mode 3**: load prediction CSV, compare/report/map only |
| *(neither)* | — | **Mode 1**: train-and-predict (approval-gated) |

### Comparison & visualization (optional)
| Flag | Type | Default | Purpose |
|---|---|---|---|
| `--actual-source` | path | none | April 2026 actual labels for comparison |
| `--actual-crisis-flag` | str | none | Documented actual-crisis column (else `overall_phase>=3`) |
| `--spatial-path` | path | `alert_risk_maps.default_spatial_path()` | Boundaries for the map |
| `--make-map` / `--no-map` | bool | on if spatial available | Produce the two-panel map |
| `--no-basemap` | flag | off | Render without contextily basemap |
| `--overwrite` | flag | off | Allow replacing existing outputs (figures + artifacts) |

### Safety / validation
| Flag | Purpose |
|---|---|
| `--validate-only` / `--dry-run` | Validate inputs for the selected mode; **no training, no fitting** |
| `--approve-training` | Explicit approval required to run Mode 1 heavy training (automation must pass this) |
| `-h`, `--help` | Usage; no computation |

## Behavioral contract

1. **`--help` / `--validate-only`** never train and exit 0 on success, non-zero with a clear message on validation failure. Validate-only checks only the inputs required by the selected mode (FR-036, SC-004) and writes `input_validation_summary.json` + `feature_schema_report.csv`.
2. **No April 2026 rows in source** ⇒ exit non-zero: "a valid comprehensive source with April 2026 rows is required" (FR-010).
3. **Duplicate April `area_id`** ⇒ stop or apply the documented deterministic rule and report (FR-009).
4. **Missing required identifier-derived features** and no `--allow-missing-identifier-features` ⇒ stop with a clear message (FR-011a).
5. **Mode 1 without `--approve-training`** ⇒ refuse to train; instruct the user to pass `--approve-training` (Constitution V, FR-036).
6. **Skip mode without its artifact** (`--skip-training` w/o `--model-artifact-dir`, or `--skip-prediction` w/o `--predictions`) ⇒ fail with a clear message (FR-036).
7. **Non-finite cumulative predictions** ⇒ fail by default (listing `area_id`s) or, with `--drop-nonfinite-predictions`, exclude+report (FR-017a).
8. **Existing outputs** (predictions/summaries/figures) ⇒ refuse to overwrite without `--overwrite`/approval (FR-034, FR-028); mirror `alert_risk_maps.validate_output_conflicts`.
9. **Map**: exactly two vertical panels; duplicate spatial keys = hard failure; unmatched IDs recorded (not dropped); LatAm inset for global; `--no-basemap` must not fail when contextily is missing (FR-024–FR-028).
10. **`run_summary.json`** records the resolved execution mode and any supplied artifact paths (FR-031), plus the resolved hyperparameter set and file paths (default = the plan-R3 forecasting files; `--hyperparameter-set custom` requires both `--hyperparameters` and `--hyperparameters-p3` — supplying only one fails with a clear message).
11. All machine-readable outputs land under `--out-root` (default under `results/`); all figures/reports under `--report-root` (default under `reports/`) (FR-029, SC-009).

## Exit codes
- `0` success (including successful `--validate-only`).
- non-zero: validation failure, missing required artifacts, no-April-rows, duplicate keys, non-finite (default mode), output conflict without `--overwrite`, or Mode 1 without `--approve-training`.
