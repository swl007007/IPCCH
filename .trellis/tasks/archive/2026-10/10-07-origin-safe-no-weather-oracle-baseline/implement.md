# Execution plan

Status: approved for execution and Herdr Claude handoff on 2026-10-07; lifecycle start pending. All implementation/experiment steps below remained unexecuted at approval. PRD and design are the scope authority; checkboxes record progress, not proof of validation. See PROGRESS.md for current operational status.

## 1. Approved start and reference verification

- [x] Obtain explicit approval of the consolidated planning summary, including the resolved G1/B and G2/A in `research/final-alignment.md`. Run GitNexus `detect_changes()` and commit this task's approved planning artifacts plus the task-relevant root `CONTEXT.md` glossary; exclude the unrelated modified `AGENTS.md`.
- [x] Read `/home/swl007007/projects/herdr-audit-controller/README.md`, inspect durable audit status and Herdr live Claude identity. Keep exact registered repo path `/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/Google fund/Analysis/2.source_code/Step5_Geo_RF_trial/IPCCH`. Register the verified executor, boot the controller if needed, and have that bound Claude execute `trellis-audit --repo '<exact path>' start <task-id>`. Verify run ID, executor/session/terminal, base_sha and `in_progress`. No native task start, identity substitution or forced reset of an active run. Discussion pane identity is not automatic executor authorization.
- [x] Load task/spec context and maintain task-local `PROGRESS.md`. Confirm frozen interpreter/config/input hashes, run inventory, cohort and fitting protocol. Use existing read-only helpers to verify reference models/targets/weights and replay all four years per horizon, saving provenance; any failure stops reuse without a refit.

## 2. Minimal implementation and bounded validation

- [x] Before editing symbols, inspect exact code and use GitNexus upstream impact; report callers/processes/risk and warn on HIGH/CRITICAL. Primary surfaces: `src/ipcch/origin_safe.py`, the origin-safe global CLI, existing suite/verifier helpers. Reuse them without changing legacy suite defaults or copying the trainer.
- [x] Implement append-only raw oracle/B6 construction from parent inputs and shared monthly source, exact ordered schemas and source/availability ledger. Keep new feature logic small and isolated. Validate inherited values/NaN masks/labels/keys, not just schema names.
- [x] Add the explicit version/arm contract and isolated six-run orchestration/report verification path. Reject unapproved combinations and prevent new outputs from targeting old run directories. Include helper recipe hashes in fingerprints and all-year replay in verification.
- [x] Implement region3 saved-prediction extraction and country-stratified paired bootstrap using existing metric definitions/helpers. Keep this entry point free of training calls; use explicit input paths. Save reproducible multiplicities, draw values, provenance and unavailable reasons.
- [x] Add focused tests for calendar lookup and H12 excluded months, weather-only exception, future-history rejection, B6 dependency-specific NaNs/zero gate, inherited-matrix parity, exact version/schema, H0 reference-only and isolated outputs. Test region membership/paired truth and explicitly reordered keys, unequal country/area row counts, whole-area paired multiplicities, weighted-versus-duplicated metrics, exact constant-target detection and conditional intervals at 999/1,000 valid draws with per-contrast joint masks and invalid fractions. Include a tiny integrated assembly/dry-run check; no evaluation-driven feature selection.

Planned focused command (new test files do not yet exist):

```bash
PYTHONPATH=src /home/swl007007/.venvs/ipcch-geo/bin/python -m pytest \
  tests/unit/test_origin_safe.py \
  tests/unit/test_climate2015_features.py \
  tests/unit/test_origin_safe_weather_oracle.py \
  tests/unit/test_regional_prediction_evaluation.py \
  tests/smoke/test_origin_safe_cli.py -q
```

No lint/typecheck command is configured in `pyproject.toml`; do not invent one. Existing unrelated full-suite failures must not be presented as new regressions or silently claimed fixed. Record actual commands, exit codes and relevant failure scope.

## 3. Execute the six global runs

- [x] Build only new-version inputs, preserving parent files. Verify complete source/feature ledger, parent-projection equality, cohort/hash parity, feature counts and per-batch coverage. Run the existing CLI's validating dry-run for each approved combination; it does not write models and is not resume/artifact verification.
- [x] Fit sequentially: raw H3/H6/H12 and raw+B6 H3/H6/H12, seed42 only. Record all 24 annual batch outputs and 96 models. Reuse verified baseline H0/H3/H6/H12 through explicit paths; never use modified-runner resume against old outdirs.
- [x] Verify all new artifacts, fitting keys/weights/targets, feature names/order, temporal ledgers, hashes and all-year model replay. Recompute annual/pooled metrics from unrounded saved predictions with exact undefined patterns; compare on the frozen global keys.
- [x] Write baseline-first global report and three paired deltas, F/B/Q coverage and interpretation/source limitations. Preserve original training identity separately from current verification identity.

## 4. Region3 postprocessing — no fitting

- [x] Hash and validate mapping/country sources, extract saved global prediction rows by region=3, verify 3,234 keys and annual counts 703/514/594/1423 across every arm/horizon, and save coverage/selection evidence.
- [x] Compute the eight regional metrics and three deltas annually and pooled. Generate the shared country-stratified area multiplicities once per period; compute 2,000 paired draws and conditional intervals using per-contrast joint validity masks and at least 1,000 valid draws. Preserve global metric definitions. Persist all draws, masks, valid/invalid counts/fractions, conditional labels, unavailable reasons and metadata; do not replenish invalid draws.
- [x] Verify point scores, draw replay and weighted-versus-duplicated metric behavior. Confirm the addendum did not invoke any pipeline or model refit. Record bootstrap limitations and H0 reference-only handling in the regional report.

## 5. Evidence and audited close

- [x] Map AC1–AC6 to actual files, commands and results in `evidence.md`; inventory ignored result/report artifacts with hashes and pinned code/environment identities. Record any missing evidence as incomplete. Update relevant project guidelines with the named weather-only exception and regional evaluation contract if needed.
- [ ] Complete full task-scope verification, run GitNexus `detect_changes()` and inspect the expected diff. Commit relevant nonignored task/code/test/spec changes only, preserving unrelated user edits. Do not push without authorization.
- [ ] Bound Claude runs `trellis-audit close`; inspect controller `status` and `show <job-id>`, pinned SHAs/snapshots/result paths. Controller repair/re-audit handles major/blocker findings. Preserve historical failures/waivers separately; queued/launched/done alone is not acceptance. Finish only upon accepted audit result.

Rollback/stop boundary: old datasets/runs are immutable. A failed preflight, source drift, cohort mismatch or scientific-contract change stops dependent work and is reported; it never authorizes an automatic baseline rerun, different interpreter, cohort trimming, identity replacement or manually cleared audit gate.
