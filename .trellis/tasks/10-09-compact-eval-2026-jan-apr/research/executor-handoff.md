# Authorized executor handoff: compact 2026 historical extension

This is a NEW task after the completed/archived Somalia-local task. The user explicitly approved the concrete written spec and asked for Herdr Claude Opus5.5(1M) execution with Codex supervision, without Trellis audit. The old instruction to remain stopped applied to the archived task; this new approved task supersedes it for the exact bounded work below.

## Identity and durable approval

- Repository exact path: `/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/Google fund/Analysis/2.source_code/Step5_Geo_RF_trial/IPCCH`.
- Task: `.trellis/tasks/10-09-compact-eval-2026-jan-apr`; supervisor ordinary-started it and verified `in_progress`.
- Approved-plan commit: `16d2e92a8948e7f235541a6facb452e375ac4f5d`.
- Branch: `task/compact-climate-weather-oracle`; do not create another worktree/branch or restore originals.
- Executor just verified: `somalia-local-executor`, pane `w11:p4`, terminal `term_65d6ae54981a13`, Claude session `579e6ba5-f2a2-483c-b465-4b2e3cca1ed3`; UI says `Opus5.5(1M context)`.
- Read `approval.md` for the requirements-convergence and separate written-plan execution approvals. Do not ask the human for these approvals again.

Read `prd.md`, `design.md`, `implement.md`, `expected_runs.csv`, `research/contracts.md`, both context JSONLs, `PROGRESS.md` and `.trellis/spec/backend/quality-guidelines.md` before editing. Activate this task in your own Claude session with ordinary `task.py start` if needed for native context injection. Never use `trellis-audit`, register, audit start/close, controller boot, audit enrollment or an audit reviewer. Do not archive this task yourself.

## Ownership and first checkpoint

You implement the approved new entrypoint and its focused tests yourself; Codex coordinates, reviews evidence and makes Git commits/finish. You are not alone: preserve existing changes and do not revert others. Your code ownership is ONLY:

- `scripts/modeling/run_compact_eval_2026_extension.py` (new).
- `tests/unit/test_compact_eval_2026_extension.py` (new).
- This task's progress and execution evidence.
- The exact NEW result/report namespaces in the design when the supervisor releases the fitting phase.

Existing source helpers/fitter, SOM script, original suites/verifiers/region helpers/configs/inputs/old outputs/launch outputs stay byte-identical. Preserve dirty `AGENTS.md` and the old archived superseded launch PNG. Use the Windows Git shim for Git inspection: `PATH=/tmp/ipcch-windows-git-bin:$PATH`. Frozen model Python: `/home/swl007007/.venvs/ipcch-geo/bin/python`.

First implement and run the focused synthetic/affected tests, then full no-write `--validate-only` for both scopes if the source is ready. Update PROGRESS with actual commands/return codes and write a concise implementation checkpoint. **Stop before the first heavy fit and before any code commit**; tell the supervisor you are ready for source review/commit. The human already authorized all planned experiments; this is an automatic coordinator barrier to commit/freeze tested code, not a new human approval request. Do not commit, start fitting, archive or push before the supervisor's phase-release prompt.

## Essential scientific and identity contract

- Global and genuinely SOM-local historical compact baseline/oracle, allH0/3/6/12; sharedH0,oracle only3/6/12.
-2026Jan-Apr only:4327global rows/3823areas;905SOM rows/904areas (Jan1,Feb0,Mar0,Apr904),membership905.
- Fixed annual origin/cutoff from the January anchor, no2026fitting labels; exact expected sets in14-row CSV.
- Original frozen parent gates FIRST; then copied in-memory2026eval mask and local fitting+scoring masks; unchanged annual `run_origin_batch` called directly for2026. Never edit/monkeypatch old year constants or bypass frozen gates.
- Verify/reuse original2022-25 predictions/models with original identities, only56newboosters total. New fingerprints bind the extension, source/manifests/scope/key hashes/approved-spec copies and script bytes; never relabel old fits.
- Five annual plus explicitly filtered `pooled_2022_2026` and `pooled_2022_2025`; eight absolute metrics plus paired deltas; global+regions0..8 and distinct localSOM; no dropped empty/small groups and canonical undefined reasons.
- New56model score replayatol1e-6/rtol0 plus EXACT classes; inspect all280referenced old/new fitted schemas; independent metric/delta replayatol1e-12 with exact support/status/reasons. Reused224oldnumerical replay need not be redone; its pinned prior evidence is separate from fresh hash/lineage/metric checks.
- Reports/codebooks remain unverified until complete checks pass. Do not invoke the old local `--report` (it also rewrites launch outputs). No CDS/provider calls, input rebuild, tuning or new features/dependencies.

If a real technical contradiction appears, report exact file:line/error to the supervisor and continue independent authorized work. Do not silently widen the spec, repair frozen parent files or substitute runtime/data. Preserve diagnostics. Keep live logs outside inventoried results/reports.
