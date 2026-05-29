# Phase 1 Data Model: April 2026 Global Nowcasting Launch

Entities are data frames / records and the on-disk artifacts the launch produces. All `area_id` keys are normalized as strings (stripped) consistent with `alert_risk_maps.normalize_area_id`.

---

## 1. Comprehensive Feature Source (input)

The single authoritative CSV for both training and April 2026 X_test.

| Field | Type | Notes |
|---|---|---|
| `area_id` | str | Canonical spatial key (required) |
| `year` | int | Required |
| `month` | int | Required (1–12) |
| `date` | date | Constructed from `year`/`month` if absent (`add_monthly_date`) |
| `overall_phase` | int (1–5) or null | Target label; `0`/null ⇒ not a valid training row |
| `phase1_percent`…`phase5_percent` | float | Target-percentage columns; **excluded from features** |
| `phase2_worse`…`phase5_worse` | float [0,1] | Cumulative targets; derived (`derive_cumulative_targets`) if absent |
| `lat`, `lon` | float | Identifier-derived features (via canonical identifier-feature setting) |
| country/region/name fields | str | Reporting only; never model features |
| many deep-feature columns | numeric | Model feature candidates |

**Validation (FR-006)**: file exists & readable; `area_id`/`year`/`month` present; date constructable; ≥1 valid-target training row before 2026-04-01; ≥1 April-2026 row; four cumulative targets derivable for training; April X_test constructable without actuals.

---

## 2. Training Dataset (derived)

Rows strictly before 2026-04-01 with `overall_phase` present and ≠ 0, and with the four cumulative targets derivable/present (FR-007). April 2026 rows excluded. Features selected by `select_numeric_feature_columns()` after applying the canonical identifier-feature setting and the FR-011b exclusion patterns.

- **Targets**: `phase2_worse`, `phase3_worse`, `phase4_worse`, `phase5_worse` (each NaN-dropped per-target via `prepare_target_matrices`).
- **Optional weights**: `time_decay_weights(date, anchor=2026-04, half_life)` (R5).

## 3. Launch X_test — April 2026 (derived)

All rows with `year=2026, month=4` (FR-008), preserving every eligible `area_id` regardless of missing labels. Aligned to the trained feature column order. **Duplicate `area_id` → default hard-stop (FR-009); optional `--dedup-rule latest-date` (only if a date/timestamp column exists and the chosen row is deterministic) writes a duplicate-resolution report (duplicated `area_id`s, candidate counts, selected date, dropped rows). Never silently keep an arbitrary duplicate.** No inner join to actuals.

---

## 4. Feature Schema (derived) → `feature_schema_report.csv`

One row per source column with columns:

| Column | Meaning |
|---|---|
| `column` | source column name |
| `role` | one of `model_feature`, `identifier_derived_feature`, `raw_identifier_reporting`, `target`, `target_derived_excluded`, `non_numeric_excluded`, `other_excluded` |
| `included_in_model` | bool |
| `exclusion_reason` | text (pattern matched, target, non-numeric, etc.) |
| `present_in_training` | bool |
| `present_in_xtest` | bool |
| `expected_identifier_feature_missing` | bool (FR-011a item c) |

Drives the FR-011a listing (identifier-derived included / raw excluded / expected-missing) and the training-vs-X_test schema comparison (FR-013, SC-005). Non-numeric model-feature survivors ⇒ flagged failure.

---

## 5. April 2026 Predictions (output) → `predictions_2026_04_all_area_id.csv`

One row per eligible April 2026 `area_id` (FR-030):

| Field | Type | Notes |
|---|---|---|
| `area_id` | str | |
| `year`, `month` | int | 2026, 4 |
| `date` / `launch_month` | str | `2026-04` |
| country/region fields | str | if available |
| `phase2_worse_pred`…`phase5_worse_pred` | float [0,1] | clipped/rounded (R7); aliases `phase{2..5}_pred` supported |
| `overall_phase_pred` | int (1–5) | from finite validated cumulatives via `th=0.2` (R6) |
| `model_workflow` | str | e.g., `deep_feature_weight_decay_cumulative_regression` |
| `scale` | str | `global` |
| `threshold` | float | `0.2` |
| `training_cutoff` | str | `2026-04-01` |
| `comprehensive_source` | str | source path/name |
| `run_id` | str | per-run provenance id |

**Invariants**: 100% of rows have all four cumulative preds and `overall_phase_pred ∈ {1..5}`; no non-finite cumulative silently produced a phase (SC-002/SC-002a). Rows excluded under R7 are reported, not silently dropped.

---

## 6. Prediction Validation Summary (output) → `prediction_validation_summary.json` / `prediction_distribution_summary.csv`

Counts of: clipped-low, clipped-high, non-finite per target; rows excluded/failed due to invalid predictions; per-target prediction distribution (min/median/max/quantiles); predicted phase distribution (→ `predicted_phase_distribution.csv`).

---

## 7. April Actual Crisis Layer (comparison input, post-prediction) → `actual_crisis_2026_04_by_area.csv`

April 2026 actuals only — **April 2026 only; no pooling, no latest-across-months selection** (single month, 2026-04):

| Field | Type |
|---|---|
| `area_id` | str |
| `actual_month` | str (always `2026-04`) |
| `actual_overall_phase` | int (1–5) if available |
| `actual_crisis` | bool (`overall_phase >= 3` by default, or documented flag) |

Loaded only after predictions (FR-023, Constitution I).

## 8. Comparison Table (output) → `comparison_*` family

Join of April predictions to April actuals by `area_id` (FR-020). Per-area record (FR-032):

`area_id`, `actual_month`, `actual_overall_phase?`, `actual_crisis`, `predicted_overall_phase`, `predicted_crisis` (`overall_phase_pred >= 3`), predicted cumulatives, `coverage_status`, `comparison_eligible`, `spatial_join_eligible`, `reason_not_compared?`.

**Coverage report** (`actual_coverage_summary_2026_04.csv`): predicted-area count, April-actual-covered count, intersection count, coverage share.
**Metrics on covered subset (where computable, FR-022)** → `comparison_metrics_actual_2026_04_vs_prediction_2026_04.csv`, `class_distribution_…csv`, `confusion_matrix_…csv`, `binary_crisis_metrics_…csv`: accuracy, macro-F1, weighted-F1; 3+ & 4+ precision/recall/F1/F2; true-4-as-3 and true-2-as-3 rates; class distributions (actual & predicted-on-covered). All labeled **descriptive** (not validation/selection/tuning). Partial/unavailable coverage ⇒ warnings + denominator scoping (FR-023, SC-006).

---

## 9. Visualization Input (output) → map join validation feed

Per area (FR-033): `area_id`, `actual_month` (2026-04), `actual_overall_phase`, `actual_crisis`, `predicted_overall_phase`, `predicted_crisis`, `comparison_eligible`, `actual_coverage_status`, `prediction_coverage_status`, `spatial_join_status`.

## 10. Two-Panel Map + Validation Summary (output)

- Figure → `reports/launch/nowcasting_2026_04/visualizations/ipcch_2026_04_global_actual_vs_predicted_crisis_map.png` (2×1: April actual top, April predicted bottom; alert/no-alert colors; LatAm inset for global; no-basemap supported).
- Validation summary (FR-027) → `results/launch/nowcasting_2026_04/visualizations/april_2026_crisis_map_validation_summary.json` + `april_2026_crisis_map_join_validation.csv`: actual source path, prediction source path, spatial boundary source path, actual month (2026-04), prediction month (2026-04), predicted area count, April actual-covered count, mapped-predicted count, mapped-actual count, **unmatched prediction `area_id` values**, **unmatched actual `area_id` values**, **duplicate spatial key count/list** (0/empty on success — duplicates hard-fail before rendering and are surfaced in the error message + an error validation summary), output path. Unmatched IDs are recorded (not dropped); the matched subset may render with mapped-coverage disclosure.

---

## 11. Run Metadata (output)

- `run_summary.json` (FR-031): scale, comprehensive source, training cutoff, launch month, threshold, model workflow, **execution mode + supplied model/prediction artifact paths**, row counts (training/X_test/predicted), feature counts, output paths, visualization paths (when generated).
- `launch_config_resolved.json`: fully resolved CLI/config.
- `input_validation_summary.json` (FR-006), `training_data_summary.csv` (incl. min/max date + per-month counts, R4), `x_test_area_coverage.csv`, `april_2026_area_id_eligibility.csv`, model-aligned X_test artifact (`.csv`/`.parquet`), `model_artifacts/phase{2..5}_worse_model.*` (Mode 1) + persisted feature-column order.

## 12. Execution Mode (control entity)

| Mode | Flags | Required supplied inputs | Trains? | Predicts? |
|---|---|---|---|---|
| 1 train-and-predict (default) | (none) | — (approval-gated) | yes | yes |
| 2 predict-with-supplied-models | `--skip-training --model-artifact-dir <dir>` | fitted models + feature order | no | yes |
| 3 report-from-supplied-predictions | `--skip-prediction --predictions <csv>` | April prediction CSV | no | no |

Missing required artifact for the selected mode ⇒ CLI fails with a clear message (FR-036).

---

## Human-readable reports (output)

Under `reports/launch/nowcasting_2026_04/`: `launch_summary.md`, `prediction_distribution_summary.md`, `actual_comparison_summary.md`, `data_coverage_and_warnings.md` — covering launch month/global scale, fallback source path + nowcasting comparability caveat, training cutoff/rows/date coverage, predicted-area count, X_test coverage, feature schema status, predicted phase distribution, phase2–5 worse distributions, April covered-subset comparison + descriptive-only statement, two-panel map interpretation, partial-coverage warnings, and the production-launch statement (SC-010).
