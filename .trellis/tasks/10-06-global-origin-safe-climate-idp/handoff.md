# Execution handoff to Claude Opus 5.5

## Authorization and ownership

User explicitly requested: register Trellis audit, start controller, transfer control to another active Claude Opus 5.5 and execute the spec. This approves the final planning artifacts. You are the implementation/execution owner. Do not repeat grilling or ask for approval of already agreed decisions. Resolve repository facts directly; if a material contract must change, explain the evidence and obtain approval of the changed scope.

Verified destination: Herdr wP:p3; terminal term_65d3065df8dc98; Claude session cb41f664-60a8-49e5-9221-ab4b33b84dee. UI: Opus 5.5 (1M context), high effort. Repo and exact registered path:

`/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/Google fund/Analysis/2.source_code/Step5_Geo_RF_trial/IPCCH`

## First actions in your own session

1. Read AGENTS.md, this task's prd.md, design.md and implement.md in full. Read research.md, research-followup.md and research-cohort-fit.md, plus applicable guidelines/context manifests. Startup hook reported malformed JSON; manually load Trellis context and required skills if injection failed. Parent has already completed planning; do not recreate tasks.
2. Confirm registration points at your current real terminal/session and controller is running. Planning artifacts are committed before audit start; use current Git HEAD as actual baseline, not the old climate commit. Codex will perform operator registration and controller boot.
3. From YOUR bound Claude session run:

```bash
trellis-audit --repo '/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/Google fund/Analysis/2.source_code/Step5_Geo_RF_trial/IPCCH' start global-origin-safe-climate-idp
```

Verify durable run base_sha/executor/task in_progress before implementing. Do not use native task.py start/archive. If ambiguous, inspect durable status before retrying. Do not rebind an active run or replace session identity. Immediately record run ID, baseline SHA and execution start in PROGRESS.md and report them in your pane so Codex can verify the handoff.
4. Execute implement.md to completion: safe input/history construction, mandatory global prefit guards, monthly fitting protocol, focused checks, full3arm×4horizon suite, independent artifact/metric verification and report. Own code modifications and exact source reading; explorers default read-only, explicit clean fork and repo dispatch rules. Maintain PROGRESS.md as operational ledger, not approval evidence.

## Scientific contract reminders

- Retrospective month proxy, origin at month end; H0 labels strictly before target, H>0 labels<=origin; global training label cutoff across all areas. Features of each historical training row use that row's own origin. Four horizons and2022–2025 target years; monthly refit, fixed configs/seed42/half-life24/threshold0.2.
- Three paired arms: climate_no_history, climate_safe_history, climate_safe_history_idp. Five history predictors: latest3 reported phases plus2differences; provenance must reflect real source rows, not matching numbers or inferred fixed offsets. Country-level latest reported IDP stock+age<=origin via ISO3; missing remains NaN.
- Use fourteen supplied monthly/GS ensemble indicators and two completed seasons without old artificial climate tail mask. Preserve non-climate coverage after verified timing classification. Remove old lag1/prev_asof and target-side estimated_population. No upstream climate regeneration or subnational IDP GIS.
- Normalize derived share targets, retain raw labels/shares, freeze common valid target keys (currently28205). No prediction-based drops, no deletion of genuine Phase1; unrounded scores for thresholds/R². Upstream climatology/standardization remains explicitly incomplete; no full-chain or real-time validity claim.
- Preserve current interpreter ~/.venvs/ipcch-geo/bin/python, inputs and prior outputs. Measure pilot; at most576monthly batches/2304estimators, no runtime promise. Sequential bounded-memory, durable validated checkpoints; metrics-file existence alone is not completion.

## Finish and boundaries

Unrelated pre-existing AGENTS.md modification is user-owned; do not revert or sweep it into task commits. No remote push/merge authorization is included. All relevant nonignored task/code/test/evidence changes must be committed before your own audit close. Close via exact registered repo path from your bound session, retain job/result paths and unresolved evidence. Reviewers remain read-only; audit queued/launched is not passed. Do not waive findings or manually clear gates. Report results and actual acceptance state accurately.
