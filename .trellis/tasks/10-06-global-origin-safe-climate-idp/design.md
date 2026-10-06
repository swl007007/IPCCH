# Design: one validated global path

## Inputs and lineage

Use explicit corrected interim `assembled_IPCCH/interim/IPCCH_2026_target_corrected_nino34_wbfood.csv` label projection (admin_code renamed area_id), verified against baseline scope labels. Reject duplicate keys, invalid reported phases and disagreeing shared labels. Valid shares define a frozen common scoring/fitting ledger; separately valid reported phases define historical observations.

Use current source scope inputs to retain existing non-climate predictors, removing legacy IPC-history and estimated_population. Classify every retained predictor against pinned recipe/manifest and grid checks. Common asof12 families are no later than t-12; scope families must have actual latest sources <=origin. Verify row-shift source grids instead of treating their nominal dates as evidence. Preserve existing non-climate missingness; do not interpolate it. Static values/coordinates are fixed retrospective context; record snapshot limits. Diagnostics/provenance never become predictors.

Reuse climate2015 engineering for all14 monthly indicators, common anchor12 and scope0/3/6, interactions/spatial families, and two completed GS. Build the new block directly at its declared anchors without old tail masking. Validate actual monthly/seasonal support, including GS end_exclusive<=first day after origin. Source-support checks remain distinct from unverified climatology/composite producer internals.

Use IDP_DTM/output/idp_admin0_monthly.csv via verified country_area_id_lookup.csv ISO3; inspect exact stock/report keys before selection. Latest non-null observed report<=origin supplies two predictors (stock, recomputed month age). Validate country/report duplicate rules and mappings. Keep missing NaN and report coverage/staleness. No population-denominator or flow features.

## Shared logic and global entry

Extract/reuse the small Nigeria latest-three algorithm (not its NGA-specific executor); extend H12 and preserve source area/month. Each training row's features are constructed at its own forecast origin. Each monthly outer fit additionally restricts all fitting labels to <=min(outer_origin,outer_target-1). No selection/tuning uses evaluation labels.

Reuse the existing fixed XGB fitting function/configs and target ordering. Add the minimal monthly-origin protocol to the current global CLI, with mandatory frozen manifest/source-ledger checks; global legacy annual execution or unsafe history inputs must fail with a clear migration message before fitting. Keep country/oracle paths compatible. Add origin weights0.5**(age/24), permitting age0 for H>0. Do not change annual helper semantics for unrelated consumers.

Global postprocessing preserves every frozen evaluation row: raw four cumulative regressor predictions, phase classification by highest unrounded score>=0.2 (default phase1), no deletion on zero sums. Truth is reported phase; normalize only derived share targets. Retain existing fitting model behavior; do not add a new calibration or projection layer.

## Evidence and execution

Versioned external model inputs and repository-local results/reports use a new origin_safe_climate_idp_v1 namespace. Manifest binds complete feature order, source data/QA hashes, git commit, CLI args and numerical environment. Save per-origin actual target fitting keys, model bundles, eval keys and raw predictions; yearly outputs concat only validated monthly batches. Completion requires all expected artifacts and matching fingerprints, not metrics-file existence.

Three arms vary only the five history predictors and then two IDP predictors. Eligible target keys are common across all four horizons; features may remain missing. Per-scope training features and sources are pinned; per-origin fitting keys must be equal across arms for each cumulative target. Metrics replay from saved values must use round-trip float parsing.

Sequential batches on15GB machine; measure one real pilot, bound XGB threads, checkpoint each validated batch and resume only exact matching inputs/configs. New outputs allow rollback without deleting prior data. Research pinning does not substitute validation.

## Lifecycle

This repo is enrolled with the audit controller at its exact current path spelling. Before code execution: approved plan commit; verify/rebind the actual Claude executor terminal/session, let that bound executor run trellis-audit start, verify base_sha/run identity/in_progress. Do not fabricate a session, native-start the task, or retroactively invent a baseline. After committed implementation/evidence, executor close queues read-only review; report any incomplete/blocked acceptance accurately. Main owns final choices/verification; planning explorers are read-only. Dispatch rules must preserve explicit role/context restrictions.
