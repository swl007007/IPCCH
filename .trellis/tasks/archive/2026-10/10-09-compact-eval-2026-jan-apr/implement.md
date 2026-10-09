# Implementation plan: global and SOM 2026 historical extension

## Planning gate and ownership

User-confirmed requirements and fresh written-plan implementation approval are recorded in `approval.md`. The user explicitly authorized execution on 2026-10-09. Read `prd.md`, `design.md`, `expected_runs.csv`, `research/contracts.md` and both JSONL context manifests before executing the ordered work below.

Codex owns planning, scope decisions, coordination, progress/evidence review, commits and finish. Execution follows the user's explicit Herdr Claude Opus 5.5 (1M) preference; verify the live model, pane, terminal and session rather than reuse historical IDs blindly. The user opted out of Trellis audit for this work. Do not register/start/close an audit run, boot the controller or invoke an audit reviewer. Ordinary Trellis lifecycle is used after approval.

Implementation owns only:

1. New `scripts/modeling/run_compact_eval_2026_extension.py`.
2. New `tests/unit/test_compact_eval_2026_extension.py`.
3. This task's approved artifacts, progress and evidence.
4. New result/report roots specified by the design.

The executor is not alone in this workspace: preserve other agents' edits and the unrelated dirty AGENTS/old PNG files. Do not edit frozen modules, existing drivers/verifiers/report functions, inputs, configs, dependencies or launch artifacts. If a wider change is unavoidable, report the concrete reason and impact to the coordinator before proceeding.

## Ordered work

### 1. Freeze the approved plan and execution baseline

- Record fresh implementation approval in `approval.md`; do not treat requirements convergence as implementation approval.
- Complete a lossless PRD review: all R1-R6 requirements map to A1-A8, no unresolved product question, all context-manifest paths exist.
- Review Git status/HEAD and initialize this task's `PROGRESS.md`. Commit only approved planning files with the Windows Git shim, excluding unrelated modifications. Run GitNexus `detect_changes` before commits; document a stale-index limitation rather than reindexing frozen source files blindly.
- Verify Herdr environment and actual Claude Opus 5.5 (1M) executor identity before sending the self-contained file-reference handoff. Do not start a second duplicate executor or assume the prior session is idle/available.
- After approval and plan commit, ordinary `task.py start` is allowed. Confirm Trellis `in_progress`, approved-plan SHA and actual executor identity in the ledger. No audit lifecycle commands.

### 2. Implement the bounded standalone entrypoint

- Use existing loader, hyperparameter, batch-fitter, resume, target/weight, region/support/pairing and independent-metric helpers from explicit repository paths. Follow `trellis-before-dev` and `.trellis/spec/backend/quality-guidelines.md`.
- Keep all existing source symbols byte-identical. If editing an existing symbol becomes necessary, run GitNexus `impact` with upstream direction first; report blast radius/HIGH or CRITICAL risk and stop scope expansion for coordinator review.
- Add only the two-scope, fixed-version actions described in `design.md`; no arbitrary years/config/output framework or new dependency.
- Fully gate the unchanged parent input before forming copied in-memory 2026/local masks and a new fingerprint. Require complete expected keys, labels/targets/weights and paired base-feature equality; preserve native NaNs.
- Implement old imports with complete hash/schema/key/truth/cutoff/scope/weight checks and separate old/new identities. Never label reused fits as fitted by the new script.
- Persist durable approved-spec copies and identity in new roots; keep task paths as provenance only. Reject incomplete/stale resumption without overwriting diagnostics.
- Generate combined keyed prediction files, all five annual/two pooled periods, global regions, both arms' absolute metrics/differences and correct unsupported-group status/reasons.
- Generate only historical report/codebook/index deliverables. The old local `--report` action is prohibited because it also regenerates launch outputs.

### 3. Run focused synthetic checks before heavy work

Run the focused test command below. Tests must cover complete scientific cohorts rather than mimic implementation statements:

- 2026 January-April selection, including absent months, duplicate/missing keys and exact SOM membership on both masks.
- Four annual anchors/cutoffs and complete eligible fitting sets; no 2026 fitting label.
- Identical paired keys/truth/weights/base features and inherited feature order/counts.
- Distinct expanded/original pooled row selection and preserved original metric results.
- Empty regions, one-row R-squared, undefined deltas and defined/undefined shared H0.
- Original and extension fingerprint separation, missing referenced artifact and incorrect local provenance rejection.
- No-write validation, nonempty incomplete batch refusal and successful exact complete-batch resume.
- Tiny saved-booster replay, including a numeric-tolerance pass that still crosses the phase threshold and must fail class equality.

Affected existing tests are the compact input/report and origin-safe CLI smoke contracts listed below; add no broad unrelated full-suite gate. Do not run tests concurrently with heavy training.

### 4. Preflight both scopes, then fit only 2026

- Run `--validate-only` for `global` and `SOM`. Confirm it writes nothing; capture output outside inventoried roots. No label/feature-source rebuild or provider call is needed.
- Capture complete protected input/results/report/launch/code/config inventories and old-result verification references.
- Commit the tested entrypoint/tests before heavy fitting, then freeze the actual extension source bytes and approved contract copies; editing fingerprint-bound implementation/spec inputs during a run invalidates resume.
- Run `--approve-training` for global, then SOM, with the frozen interpreter and inherited settings. Execute sequentially: seven batches each scope, four cumulative targets each batch, 14 batches/56 new boosters total.
- Require the fitting/evaluation counts and anchors in `expected_runs.csv`; record actual maximum fitting label month, complete fit key/age/weight hashes and parent/new fingerprint values.
- Publish combined COMPLETE metadata only after all original-year imports and new-year artifacts are present and checked. Do not refit 2022-2025 or create oracle H0.

### 5. Report and independently verify

- Run `--report` for each scope to publish only its new historical namespace.
- Run `--verify` for each scope, without fitting. Reload all 56 new boosters, inspect all 280 old/new fitted schemas and require exact replay classes plus prediction tolerance.
- Independently recompute all metric cells, support, statuses/reasons and paired differences; verify original 2022-2025 annual/pooled parity and expanded pooled row filters. Check five annual/two pooled periods, every region and codebook/inventory membership.
- Rehash the protected inventories afterward. All old inputs/results/reports/launch/code/config artifacts remain unchanged relative to the captured baseline.
- Record A1-A8 evidence with commands, actual return codes, paths/hashes and material limitations. A report generation or training COMPLETE marker alone is insufficient acceptance.

### 6. Coordinator acceptance and ordinary finish

- Resolve implementation/test/evidence failures within the approved scope; do not relax failed acceptance gates or fabricate a historical fit identity.
- Reconcile task progress against Git and approved-plan SHA. Commit relevant nonignored code, tests, task/evidence and artifact references only; preserve unrelated dirty files. Run `detect_changes` before committing and verify actual Git scope.
- Codex confirms A1-A8 evidence before reporting completion. Follow ordinary Trellis finish/archive/journal instructions, with no audit wrappers/controller jobs.

## Planned commands (not yet executed)

Exact repository path:

```bash
cd '/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/Google fund/Analysis/2.source_code/Step5_Geo_RF_trial/IPCCH'
```

Focused tests after implementation:

```bash
PYTHONPATH=src /home/swl007007/.venvs/ipcch-geo/bin/python -m pytest tests/unit/test_compact_eval_2026_extension.py tests/unit/test_compact_report.py tests/unit/test_somalia_local_compact_test.py tests/unit/test_compact_features.py tests/smoke/test_origin_safe_cli.py -q
```

The commands below are authorized by the recorded written-plan approval and require implementing/testing the entrypoint first; they had not run at approval:

```bash
/home/swl007007/.venvs/ipcch-geo/bin/python scripts/modeling/run_compact_eval_2026_extension.py --scope global --validate-only
/home/swl007007/.venvs/ipcch-geo/bin/python scripts/modeling/run_compact_eval_2026_extension.py --scope SOM --validate-only
/home/swl007007/.venvs/ipcch-geo/bin/python scripts/modeling/run_compact_eval_2026_extension.py --scope global --approve-training
/home/swl007007/.venvs/ipcch-geo/bin/python scripts/modeling/run_compact_eval_2026_extension.py --scope SOM --approve-training
/home/swl007007/.venvs/ipcch-geo/bin/python scripts/modeling/run_compact_eval_2026_extension.py --scope global --report
/home/swl007007/.venvs/ipcch-geo/bin/python scripts/modeling/run_compact_eval_2026_extension.py --scope SOM --report
/home/swl007007/.venvs/ipcch-geo/bin/python scripts/modeling/run_compact_eval_2026_extension.py --scope global --verify
/home/swl007007/.venvs/ipcch-geo/bin/python scripts/modeling/run_compact_eval_2026_extension.py --scope SOM --verify
```

The four listed existing test files were confirmed present during planning; the new extension test is to be implemented. Use the frozen environment from the compact manifest: Python3.12.3, NumPy2.4.4, pandas3.0.3, scikit-learn1.8.0, XGBoost3.2.0. Do not silently substitute an interpreter.

## Risks, rollback and validation status

The main risks are silent partial-year/pooled mislabeling, global/local identity confusion, omitted empty groups and stale old/new fingerprints. The standalone entrypoint and explicit provenance/period checks address them. Somalia's partial 2026 block is almost exclusively April; source-native weather NaNs and retrospective publication-vintage limitations remain inherited.

Rollback is to stop using the new namespaces; originals are unchanged. Preserve failed new-run diagnostics rather than deleting or modifying accepted parent artifacts.

`Validation Status: Not Executed` for implementation tests, CLI runs, fitting, saved-model replay, generated reporting and final acceptance. Planning inspection is read-only repository/source/hash evidence only.
