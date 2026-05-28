# Data Model: 2025 Alert Risk Maps

## PredictionRoot

Represents the selected directory containing existing deep-feature weight-decay forecasting experiment outputs.

**Fields**
- `root_path`: directory path supplied by user or defaulted from project paths
- `horizon_candidates`: mapping from horizon label (`0m`, `3m`, `6m`) to candidate prediction files
- `scope_candidates`: mapping from map scope (`global`, `somalia`) to candidate prediction files
- `model_grouping`: label used to distinguish global-grouping/global-Somalia outputs from Somalia-local outputs
- `selected_files`: exactly one selected prediction CSV per requested horizon and scope

**Validation rules**
- Root path must exist and be readable.
- Missing horizon candidates fail validation.
- Multiple plausible candidates fail validation unless explicit files are provided.
- Somalia-only selection must exclude Somalia-local model outputs.

## PredictionRecord

Represents one prediction row for one `area_id` at one temporal observation.

**Fields**
- `area_id`: canonical spatial identifier; normalized consistently for joins
- `date`: temporal ordering value; preferred source for latest-record selection
- `year`: record year; used to filter to 2025 if present or derived from `date`
- `month`: month used with `year` when `date` needs reconstruction
- `overall_phase`: observed IPC/CH phase value
- `overall_phase_pred`: predicted IPC/CH phase value
- `actual_alert`: derived boolean; true when `overall_phase >= 3`
- `predicted_alert`: derived boolean; true when `overall_phase_pred >= 3`
- `phase3_worse`: actual proportion or score for phase 3-or-worse risk ranking
- `phase3_pred`: predicted phase 3-or-worse score for risk ranking

**Validation rules**
- Required columns for requested map type must exist and contain usable values.
- `overall_phase`, `overall_phase_pred`, `phase3_worse`, and `phase3_pred` must be numeric where used.
- Records must be filtered to year 2025 before duplicate handling.
- After latest-record filtering, each horizon dataset must have at most one row per `area_id`.
- Ties with multiple rows at the same latest timestamp for an `area_id` fail validation unless they are exact duplicates that can be safely de-duplicated without changing values.

## HorizonDataset

Represents one horizon’s prediction records after year filtering and latest-record selection.

**Fields**
- `horizon`: one of `0m`, `3m`, `6m`
- `scope`: `global` or `somalia`
- `source_file`: selected prediction CSV path
- `raw_2025_count`: number of rows after year filtering and before latest selection
- `retained_count`: number of rows after latest selection
- `duplicates_removed`: number of rows removed by latest-record filtering
- `records`: filtered prediction records with derived alert fields

**Validation rules**
- `raw_2025_count` must be greater than zero.
- `retained_count` must equal unique `area_id` count.
- Somalia scope must include only Somalia records and use global-grouping/global-Somalia inputs.

## SpatialBoundary

Represents a spatial polygon or multipolygon boundary for an IPCCH area.

**Fields**
- `area_id`: canonical spatial identifier
- `country` / `country_name` / `iso3` or equivalent: country-identifying attributes where available
- `geometry`: polygon or multipolygon geometry
- `crs`: coordinate reference system

**Validation rules**
- Boundary file must exist and be readable.
- `area_id` must be present or mappable from a documented equivalent field.
- Each normalized `area_id` must map to at most one geometry for this workflow.
- Invalid geometries must be repaired or fail clearly if they cannot be used.

## JoinedMapDataset

Represents a validated spatial join between a `HorizonDataset` and `SpatialBoundary` records.

**Fields**
- `horizon`: horizon label
- `scope`: map scope
- `joined_records`: spatial records with prediction attributes
- `matched_count`: number of filtered prediction records joined to boundaries
- `unmatched_area_ids`: list of filtered prediction `area_id` values that did not join
- `duplicate_join_area_ids`: list of identifiers that produced duplicate joined geometries

**Validation rules**
- `matched_count` must equal the retained prediction record count.
- `unmatched_area_ids` must be empty.
- `duplicate_join_area_ids` must be empty.
- No final figure is saved if any joined dataset fails validation.

## ActualVsPredictedFigure

Represents one final 2x3 alert map for one scope.

**Fields**
- `year`: fixed at 2025
- `scope`: `global` or `somalia`
- `horizons`: ordered list `0m`, `3m`, `6m`
- `actual_panels`: joined map datasets visualizing `actual_alert`
- `predicted_panels`: joined map datasets visualizing `predicted_alert`
- `output_path`: report figure path containing year, scope, horizon group, and map type

**Validation rules**
- Must contain exactly six panels: two rows by three columns.
- All panels must use consistent binary alert encoding.
- Output path must be under `reports/`.
- Existing output path fails unless overwrite is explicitly enabled.

## TopRiskComparisonFigure

Represents one final nowcasting top-risk comparison map for one scope.

**Fields**
- `year`: fixed at 2025
- `scope`: `global` or `somalia`
- `horizon`: fixed at `0m`
- `actual_top_area_ids`: top 30% after ranking `phase3_worse`
- `predicted_top_area_ids`: top 30% after ranking `phase3_pred`
- `risk_category`: one of `actual_only`, `predicted_only`, `both`, `background`
- `output_path`: report figure path containing year, scope, 0m/nowcasting indicator, and map type

**Validation rules**
- Top 30% thresholds are computed after filtering to one latest row per `area_id`.
- Each mapped area belongs to exactly one risk category.
- Somalia scope uses only Somalia records from global-grouping/global-Somalia inputs.
- Existing output path fails unless overwrite is explicitly enabled.

## ValidationResult

Represents the machine-readable summary of validation and run decisions.

**Fields**
- `selected_files`: selected prediction and spatial input paths
- `record_counts`: raw 2025 rows, retained rows, duplicates removed by horizon and scope
- `join_counts`: matched and unmatched counts by horizon and scope
- `somalia_local_rejections`: candidate inputs rejected because they are Somalia-local model outputs
- `output_paths`: planned figure and validation summary paths
- `status`: success or failure
- `errors`: actionable validation messages if failed

**Validation rules**
- Must not be written over an existing validation summary unless overwrite is explicitly enabled.
- Must not include raw spatial data copies.
