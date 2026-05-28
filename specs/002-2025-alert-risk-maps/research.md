# Research: 2025 Alert Risk Maps

## Decision: Implement as post-processing/reporting workflow only

**Rationale**: The feature explicitly forbids model retraining, threshold tuning, label recalibration, and mutation of prediction outputs. Existing prediction CSVs already include `date`, `overall_phase`, `overall_phase_pred`, `phase3_worse`, and `phase3_pred`, which are sufficient for all requested maps after filtering.

**Alternatives considered**:
- Re-run models to regenerate 2025 predictions: rejected because out of scope and violates execution discipline.
- Recalculate prediction labels from phase probability columns: rejected because the clarified alert definition uses existing `overall_phase_pred >= 3`.

## Decision: Use binary crisis alert status for actual-vs-predicted panels

**Rationale**: The clarified spec defines alert status as actual `overall_phase >= 3` and predicted `overall_phase_pred >= 3`. This matches the project’s crisis-positive interpretation and avoids introducing new thresholds.

**Alternatives considered**:
- `phase3_worse >= 0.2` and `phase3_pred >= 0.2`: rejected by clarification.
- Five-class phase maps: rejected by clarification and less aligned with “alert” maps.

## Decision: Use latest 2025 record per `area_id` based on temporal columns

**Rationale**: Prediction CSVs include `date`, `year`, and `month`; `date` should be the canonical ordering column when present. Filtering to year 2025 before selecting the latest row satisfies the spec and prevents duplicate areas from inflating maps or top-risk thresholds.

**Alternatives considered**:
- Use all 2025 records: rejected because duplicate `area_id` rows would distort outputs.
- Aggregate across 2025 records: rejected because spec requires retaining the temporally latest record.

## Decision: Fail on ambiguous horizon discovery unless explicit files are provided

**Rationale**: Multiple experiment subfolders can match a horizon and scope. Failing instead of guessing protects reproducibility and avoids accidentally mixing global-grouping Somalia outputs with Somalia-local model outputs.

**Alternatives considered**:
- Choose newest modified file: rejected because file timestamps are not scientific provenance.
- Choose first sorted match: rejected because it is deterministic but semantically arbitrary.

## Decision: Require 100% spatial join coverage

**Rationale**: Maps and top-risk comparisons are area-level deliverables. Dropping unmatched `area_id` records would silently change denominators, counts, and visual interpretation. The clarified spec requires failure unless every filtered prediction record joins to a spatial boundary.

**Alternatives considered**:
- Warn under 5% unmatched: rejected because even small unmatched sets can include important high-risk areas.
- Exclude unmatched records and report them: rejected because final figures would no longer represent the filtered prediction set.

## Decision: Use external `ipcch_admin_geometry.shp` as default spatial boundary candidate

**Rationale**: The external spatial directory contains `ipcch_admin_geometry.shp`, which is the likely assembled IPCCH admin geometry file. The workflow should accept an explicit spatial path and may default to this path through `ipcch.paths.external_path()` or CLI configuration, but must not copy it into the repo.

**Alternatives considered**:
- Copy shapefile into `data/reference/`: rejected because raw/external spatial source data must not be copied into the repository.
- Require only GeoJSON: rejected because the current external source is a shapefile.

## Decision: Somalia-only means geographic scope over global-grouping/global-Somalia outputs

**Rationale**: The spec clarification states that Somalia-only outputs must use Somalia-only or global-Somalia prediction outputs under the global experiment grouping, not Somalia-local model outputs. This must be enforced during discovery and validation.

**Alternatives considered**:
- Use any subfolder containing `somalia`: rejected because it may accidentally select Somalia-local model outputs.
- Always filter global output to Somalia: acceptable only when it corresponds to the intended global-grouping/global-Somalia output set and passes validation.

## Decision: Fail on output conflicts unless overwrite is explicit

**Rationale**: The clarified spec requires existing output files to block execution unless overwrite is explicitly enabled. This avoids accidental replacement of report figures or validation summaries.

**Alternatives considered**:
- Always overwrite: rejected because it can destroy previous deliverables.
- Auto-timestamp filenames: rejected because required filenames must be clear and stable enough to include year, scope, horizon group, and map type.

## Decision: Expose a CLI reporting contract

**Rationale**: The implementation must be runnable from the repository root, accept path-bearing inputs without hardcoded absolute paths, and support lightweight validation. A thin CLI in `scripts/reporting/` matches existing project patterns while keeping reusable logic in `src/ipcch/`.

**Alternatives considered**:
- Notebook-only workflow: rejected because the spec excludes notebook-heavy execution.
- Package-only function without CLI: rejected because the user needs a reproducible runnable workflow.
