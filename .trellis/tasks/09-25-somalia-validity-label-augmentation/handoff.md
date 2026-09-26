# Handoff to Claude Opus 5.5 — validity-label augmentation

2026-09-25. User requests checking controller/registration, starting the audited task, and handing execution to Claude Opus5.5. Codex completed brainstorm, spec v0.2 and G1-G2, checked lifecycle state, and is stopping. No derived labels, feature regeneration, model fits or code implementation were performed.

## Read first

Read this task's `prd.md`, `design.md`, `research.md`, `grill.md` in full. They contain accepted scientific decisions R1-R15 and final-review technical details. Latest user instruction follows the final spec review and asks for audit start/handoff. Do not reopen the resolved scientific choices. There is no `implement.md`; implement/check JSONL manifests remain empty; the task is planning and files are uncommitted. Prepare the minimal implementation plan and real spec/research manifests and satisfy the remaining plan-review/commit prerequisite before execution. No native start/archive bypass.

## Essential accepted decisions

- Retain existing raw covariates and raw label values; borrow only defensibly linked current-period validity metadata from the latest verified LOCAL snapshot `curl_new_data/outputs/areas_combined_2026-05-15.geojson`. Do not silently revise targets or match stale/projected records.
- Fill only fully empty six-field labels (overall phase plus five percentages); preserve existing/partial/invalid labels. Existing labels win; overlapping blank-month candidates use the latest original observation month; unresolved equal-date conflicts stay unfilled.
- Longer validity intentionally increases training influence: retain each copied month's normal per-row weights; no report balancing. Calibration/selection/evaluation remain row-based.
- Histories count original reports only, not copies. Exclude the scoring target's source family from history, residual/persistence and fitting/calibration dependencies. Both branches use the same protocol.
- Every copy inherits its original raw observation month-end as ideal availability. Validity is not publication. Preserve chronological/source-year eligibility and explicit lineage.
- Validation/calibration use up to three distinct original-report observation months, at least two supported rounds, keeping copied monthly rows and their weights inside each round.
- Refit/reselect BOTH original-label and augmented-label D with equal budgets: direct/residual/selected in each branch. Main comparison is on the same expanded evaluation truth; restricted original-sample results are secondary. Include persistence and all-crisis. Original branch uses no added training/calibration labels. v2 results are context, not an unchanged comparator under the new report exclusions.
- Inherit q3-first v2 model/selection/calibration and H0 focus, with H3/H6/H12 ancillary fixed-recipe refits and the existing disclosed recipe-selection leakage exception. No A-C rerun/new classifier.

## Current evidence gates

No authoritative complete admin/report/validity crosswalk has been established. Spatial proximity/name/date/value matches alone are not verified lineage. Raw2025 April/October labels differ in dates from current API Jan-March/July-September windows; observed same-place/month value conflicts are in research.md. Do not fabricate matches or overwrite labels. Nonzero verified additions are a preflight gate; if none, return augmentation_unavailable, not unchanged-model results labeled augmentation.

Full monthly deep features EXIST at `assembled_IPCCH/features/forecasting_subset_IPCCH_2026_target_corrected_deep_features.csv`. H0/H3/H6 scope recovery must use this complete baseline rather than filtered fs3; preserve monthly continuity, fixed neighbor/static features and check old-key parity. Rebuild target-derived history for fit-context exclusions. Do not use the corrected artifact's targets as raw label authority. Existing raw coverage ends April2026; API validity to June does not create future covariates.

Read-only whole-label missingness check found zero partially missing six-field rows in Somalia2022-26; counts are in research.md. This is NOT a validity mapping or augmentation coverage pass. Only document-consistency checks and read-only evidence investigation were done.

## Verified audit registration and controller

- Exact registered repo: `/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/Google fund/Analysis/2.source_code/Step5_Geo_RF_trial/IPCCH` (preserve spelling; do not separately register lower-case alias).
- Executor pane `wD:p2`, terminal `term_65c50aeb3b3762`, Claude session `4816e4c6-ebaf-4aa3-a15d-708bb775b09f`.
- Live pane was idle and displayed Opus5.5 (1M context). Registration exactly matched live terminal/session; no re-registration was needed.
- `trellis-audit boot` returned `already_running:true,running:true`; `status` had no active runs. New task has no run/base SHA/completion job/audit result.
- Controller state `/home/swl007007/.local/state/trellis-audit-controller/19ea69ef13d88fde`.

After approved planning artifacts are committed (GitNexus detect_changes required before commit), run FROM THIS VERIFIED CLAUDE SESSION:

```bash
trellis-audit --repo '/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/Google fund/Analysis/2.source_code/Step5_Geo_RF_trial/IPCCH' start somalia-validity-label-augmentation
```

Verify durable run/executor/base_sha and Trellis in_progress before implementation. Registration/controller startup is not task start, not experiment authorization by itself, and not an audit pass. Do not impersonate executor IDs or manufacture a historical baseline. If identity/state changed, inspect before retrying. Preserve previous q3 task state/artifacts.

Later, complete agreed checks/evidence, commit relevant changes and use the bound audit close wrapper. Codex spot/close review remains read-only; executor repairs findings through the controller workflow. Do not claim queued/launched audit passed.
