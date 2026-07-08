# 2025 0m Country Nowcast Panel Export Design

Date: 2026-07-08

## Purpose

Provide 2025 nowcast estimates as panel data for Lesotho, Nigeria, and
Burkina Faso. In this context, "nowcast" means the existing 2025 `0m` annual
holdout output, not the latest April 2026 launch nowcasting workflow.

The export is a post-processing deliverable. It reads existing prediction,
country lookup, and geometry artifacts; it does not retrain models, rerun
prediction, tune thresholds, or mutate existing experiment outputs.

## Source Artifacts

The default prediction source is:

```text
results/experiments/deep_feature_weight_decay_forecasting/0m_global_identifier_features_threshold_0_20/predictions/predictions_2025.csv
```

This source is the existing `fs0=0m` global, identifier-feature,
threshold-0.20 2025 prediction file. Its run metadata records source feature
scope `fs0`, dataset key `deep_features_scope_0m_model_ready_dataset`, and a
2025 holdout split with training rows before 2025-01-01 and test rows from
2025-01-01 through 2025-12-01.

The default country lookup source is:

```text
/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/Google fund/Analysis/1.Source Data/assembled_IPCCH/country_area_id_lookup.csv
```

The default geometry source is:

```text
/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/Google fund/Analysis/1.Source Data/assembled_IPCCH/spatial/ipcch_admin_geometry.shp
```

Reusable code should resolve these through repository path helpers or explicit
CLI options, not hardcoded machine-specific paths in library modules.

## Countries

The export covers exactly these ISO3 country codes:

| ISO3 | Country |
| --- | --- |
| `LSO` | Lesotho |
| `NGA` | Nigeria |
| `BFA` | Burkina Faso |

Country filtering is performed by joining prediction `area_id` values to
`country_area_id_lookup.csv`. ISO3 matching is the primary filter. Country
names are retained for readability but should not be the primary selection
rule when ISO3 is present.

## Deliverables

Write the package to a new export directory, for example:

```text
results/exports/nowcast_panel_2025_0m_lso_nga_bfa/
  nowcast_panel_2025_0m_LSO_NGA_BFA.csv
  nowcast_admin_geometries_2025_0m_LSO_NGA_BFA.shp
  nowcast_admin_geometries_2025_0m_LSO_NGA_BFA.shx
  nowcast_admin_geometries_2025_0m_LSO_NGA_BFA.dbf
  nowcast_admin_geometries_2025_0m_LSO_NGA_BFA.prj
  nowcast_admin_geometries_2025_0m_LSO_NGA_BFA.cpg
  export_validation_summary.json
```

The CSV is the primary panel-data artifact. The shapefile is an accompanying
admin-geometry layer with one row per admin unit, not one row per admin-month.
The two deliverables join through `area_id`.

## Panel CSV Schema

The panel CSV contains one row per `area_id x month` for the selected
countries. Required columns:

| Column | Meaning |
| --- | --- |
| `iso3` | Country ISO3 code, one of `LSO`, `NGA`, `BFA`. |
| `country` | Country name from the lookup source. |
| `area_id` | Canonical IPCCH admin identifier. |
| `test_year` | Holdout year, fixed at `2025`. |
| `year` | Prediction row year, fixed at `2025`. |
| `month` | Prediction row month. |
| `date` | Monthly date from the prediction source. |
| `overall_phase` | Observed IPC/CH phase in the 2025 holdout record. |
| `overall_phase_pred` | Predicted IPC/CH phase derived from cumulative predictions. |
| `phase2_worse` | Observed cumulative phase 2-or-worse share. |
| `phase3_worse` | Observed cumulative phase 3-or-worse share. |
| `phase4_worse` | Observed cumulative phase 4-or-worse share. |
| `phase5_worse` | Observed cumulative phase 5 share. |
| `phase2_pred` | Predicted cumulative phase 2-or-worse share. |
| `phase3_pred` | Predicted cumulative phase 3-or-worse share. |
| `phase4_pred` | Predicted cumulative phase 4-or-worse share. |
| `phase5_pred` | Predicted cumulative phase 5 share. |
| `nowcast_scope` | Fixed string `0m`. |
| `source_experiment` | Fixed string `0m_global_identifier_features_threshold_0_20`. |

The exporter may include additional non-breaking columns if they come directly
from the lookup source, but it must not add model features or raw training
columns to this final panel.

## Shapefile Schema

The shapefile contains one geometry per selected `area_id`. Required attribute
fields should stay short enough for ESRI shapefile DBF constraints:

| Field | Meaning |
| --- | --- |
| `area_id` | Join key to the panel CSV. |
| `iso3` | Country ISO3 code. |
| `country` | Country name. |
| `n_months` | Number of panel months exported for this admin unit. |
| `min_date` | First exported panel date for this admin unit. |
| `max_date` | Last exported panel date for this admin unit. |

The shapefile must preserve the source geometry CRS unless an explicit output
CRS option is added later. If geometries require validity repair, the summary
must record how many were repaired.

## Validation Rules

The exporter must fail clearly when:

- The prediction CSV, country lookup, or spatial boundary file is missing.
- Required prediction columns are missing.
- The country lookup lacks `area_id` and ISO3-compatible columns.
- Any selected prediction row cannot be assigned to one of `LSO`, `NGA`, or
  `BFA`.
- Any selected `area_id` cannot join to geometry.
- Geometry records contain duplicate `area_id` values after normalization.
- A selected `area_id x year x month` appears more than once.
- An output file already exists and overwrite was not requested.

The exporter must record, at minimum:

- Source paths.
- Source row counts.
- Selected country row counts.
- Distinct selected admin counts by country.
- Panel row counts by country and month.
- Geometry match counts and unmatched IDs, if any.
- Output paths.
- Run timestamp.
- Whether overwrite was used.

## User Interface

Add a small reporting/export command under `scripts/reporting/`, for example:

```bash
PYTHONPATH=src python scripts/reporting/export_2025_0m_country_nowcast_panel.py \
  --overwrite
```

Useful options:

- `--predictions PATH`: override the default 2025 `0m` prediction CSV.
- `--country-lookup PATH`: override the country-area lookup CSV.
- `--spatial-path PATH`: override the admin geometry shapefile.
- `--output-dir PATH`: override the export directory.
- `--countries LSO NGA BFA`: keep the default explicit but testable.
- `--overwrite`: allow replacing existing export artifacts.

The command should support `--help` and a lightweight validation path through
normal execution on small synthetic inputs in tests. It should not require
model-training dependencies beyond pandas/geopandas for the export itself.

## Out of Scope

- Training or rerunning the 2025 annual holdout workflow.
- Using April 2026 launch nowcasting outputs.
- Producing 3m, 6m, 12m, or latest operational launch estimates.
- Building maps or figures.
- Exporting raw model features.
- Copying source spatial data into the repository outside the generated export
  package.

## Testing and Acceptance

Implementation should include focused tests for:

- Country filtering by ISO3.
- One-row-per-`area_id x month` panel output.
- Shapefile geometry join with one row per selected `area_id`.
- Duplicate prediction key failure.
- Missing geometry failure with useful unmatched `area_id` examples.
- Output conflict handling without `--overwrite`.

Acceptance for the real export:

- The CSV contains only `LSO`, `NGA`, and `BFA`.
- Every CSV row has `nowcast_scope=0m`, `test_year=2025`, and `year=2025`.
- Every selected `area_id x month` appears once.
- The shapefile contains exactly one geometry record per selected `area_id`.
- Every shapefile `area_id` appears in the CSV, and every CSV `area_id`
  appears in the shapefile.
- `export_validation_summary.json` records the source artifacts and row-count
  reconciliation.
