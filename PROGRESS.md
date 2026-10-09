# Compact CDS launch — active execution

Task: `.trellis/tasks/10-08-compact-cds-launch`. Authoritative scope: approved `prd.md`, `design.md`, `implement.md` and expected contracts; this ledger is operational state only.

## 2026-10-09 supervisor/executor goal

- User approved the latest formal plan and requested continuous execution under the active goal, stopping only for a critical error.
- Current branch remains `task/compact-climate-weather-oracle`; use Windows Git.
- Verified executor: Herdr `compact-cds-executor`, pane `w11:p4`, terminal `term_65d5d6047bdfb4`, Claude session `579e6ba5-f2a2-483c-b465-4b2e3cca1ed3`. Current UI displays Opus5.5 (1M context). Supervisor is Codex pane `w11:p1`. Binding evidence: task `research/executor-binding.json`.
- No additional audit enrollment/start/close. Existing controller has no active run; prior registration is not this executor binding.
- Run contract: baseline H0/H6/H12 and weather H6/H12;20 regressors;296/308 exact schemas. Three targets share April population; area/country/region/global outputs and predicted maps/differences.
- Context CSV truncation was resolved by curated complete-contract reading instructions; CSV itself remains unchanged.
- Wave0 approval/binding: **component-complete**. Wave1 source/runtime/weather: **pending**. Wave2 compact matrices: **pending**. Wave3 five fits/replay: **pending**. Wave4 population/maps/final acceptance: **pending**.
- Source/schema planning checks passed; no weather retrieve, feature build, new model fit or map has run yet.
- Next: commit approved planning/binding artifacts, have this executor start the task normally, perform source/request/runtime preflight and proceed through staged checkpoints. Supervisor verifies actual files/diff and live process/job handles; a timeout does not prove work stopped.

---

# Global origin-safe climate and IDP benchmark

Completed task: `.trellis/tasks/archive/2026-10/10-08-compact-climate-weather-oracle`; the earlier entry below is preserved as historical context. Experiments completed2026-10-09 UTC (2026-10-08 America/New_York).

## 2026-10-08: compact features and raw oracle execution

- Final spec and expected-input contract approved by user: “可以执行”. Planning commit: `928d080`.
- Task started normally as `in_progress`; user explicitly excludes additional audit registration/start/close for this task.
- Expected schemas: compact baseline296 at H0/3/6/12; raw oracle302 at H3,308 at H6/H12. Seven runs,28 annual batches,112 regressors; no B6/bootstrap.
- Full and compact feature versions remain separately selectable; existing inputs/results are preserved.
- Claude runtime probe: configured `claude-opus-5-5[1m]`, canonical `claude-opus-5-5`, context window1,000,000; probe session `4abde8d2-2b01-4493-867c-c3e16f4bbcdb`.
- User explicitly requested Herdr communication. Verified executor: `w11:p4`, terminal `term_65d5d6047bdfb4`, Claude session `579e6ba5-f2a2-483c-b465-4b2e3cca1ed3`; visible UI shows Opus5.5 (1M context), same IPCCH cwd, idle before dispatch. The preflight-only background channel worker was stopped after saving research/execution-preflight.md/JSON; it never edited product code or trained models.
- Preflight passed frozen environment/config/region map/parent manifest and all23 consumed parent-input hash checks, plus row/history/IDP/season checks. Windows-Git shim was recreated and tested successfully.
- Context manifests validated without truncation; complete schema must be read from disk as directed in research/contract-reading.md.
- Implementation and seven input CSVs are present; schemas296/302/308 and full baseline projection/background parity were independently checked. Supervisor regression:93 passed; read-only scouts checked recipe/version, numeric and identity/report paths.
- Build1 failed independent replay on20 numerical cells; evidence is preserved. Stable compact-only computations and focused identity/report/dry-run/codebook corrections were verified before rebuild; legacy helpers are unchanged.
- Executor checkpoint (research/implementation-checkpoint.md): numeric root cause fixed (pandas running rolling sums and uncentred same-month means; shift-centred per-window statistics, exact-constant z -> NA, exact-rational verifier reference; research/numeric-root-cause.md). Build 1 preserved as `compact_climate_weather_oracle_v1__superseded_build1` (inputs) and `results/.../superseded_build1/`. Build 2 manifest sha256 `456360536a3929e1571d96ba9f16e2f0de54bc1b20019f797bbe62c0c89732ca`; input verification passed (372,800 cells, 0 mismatches; legacy 740/740 unchanged); true no-write seven-run dry run 7/7 OK. Both builds ran on planning HEAD 928d080 with uncommitted implementation (recorded in manifests).
- Supervisor accepted the implementation checkpoint after fresh manifest/helper/runtime/contract checks and actual legacy baseline/H0 and oracle/H3 dry-runs (870/876 columns, no outputs). Full seven-run compact dry-run passed. Implementation commit: `40060dd4135cd301347f63ffddaa63384b07264c` (`feat: add frozen compact climate and raw oracle suite`); Windows Git confirmed clean code before fitting.
- Execution wave status: **integration-complete**. The same verified Herdr executor completed the baseline/H0/2022 pilot:4 models reloaded, exact fitted order, prediction replay max absolute difference0, fit19774/eval5599 rows,23.22 seconds,1510.4 MB peak RSS (`research/pilot-check.json`). The full seven-run suite resumed that pilot without refitting and completed all28 batches/112 models; suite exit0,14:46 wall.
- Final `--stage all` verifier exit0:7/7 runs,28 batches,112 models reloaded, prediction replay difference0,740622 fitting rows checked,2800 independently replayed metric cells,372800 sampled input recipe cells with0 mismatches,740/740 legacy files unchanged. Actual codebook308 union rows is `fitted_verified_all_batches`, with exact296/302/308 run membership/order.
- Supervisor acceptance passed (`research/supervisor-final-acceptance.json`):203 inventory artifacts freshly rehashed; independent scouts checked all112 fitted orders and identical28205 prediction keys/truths. Global280/regional2520 metrics and global120/regional1080 deltas verified, including region8's empty2022 and three-row2023 groups. Report/codebook hashes pinned in acceptance; no fingerprinted code changed during fitting.
- Pooled oracle-minus-baseline F2: H3 -0.0018403613, H6 +0.0143561468, H12 +0.0188020704. Effects differ by metric/year/region; point estimates only, no significance claim. Rollback appendix records stable build2 manifest/contracts and validated legacy/compact selections.
- Execution evidence commit: `10dfc23` (`docs: record compact oracle experiment acceptance`). Current task archived via the ordinary lifecycle only; no other task was archived. Archive/journal bookkeeping commits follow the work commits. No audit lifecycle wrappers, push or additional experiments. No required scientific work remains.

Task: `.trellis/tasks/10-06-global-origin-safe-climate-idp`.
Operational ledger only; approved requirements live in prd.md/design.md/implement.md.

## 2026-10-06: approved planning and executor handoff

- Completed grilling: all ten scientific/scope decisions recorded in the final spec.
- Read-only exploration completed; sources and gaps in three task research files.
- Planning artifacts and context manifests checked; task is still planning pending audit start.
- User explicitly approved final spec execution and handoff to an active Claude Opus 5.5.
- Verified live candidate: Herdr `wP:p3`, terminal `term_65d3065df8dc98`, Claude session `cb41f664-60a8-49e5-9221-ab4b33b84dee`, same IPCCH cwd, idle, UI shows Opus 5.5 (1M context).
- Audit controller was running with no active run; registered IPCCH executor was stale. Registration/start verification will be recorded by executor after the planning commit.
- Product code, input data and old results have not been changed. Tests, input builds and model fits have not run for this task.
- Pre-existing `AGENTS.md` change belongs to the user; excluded from the planning commit.

Next: rebind verified executor, audit-start from its own Claude pane, verify baseline SHA/task status, then follow implement.md. Completion requires full run evidence and actual accepted audit result, not launch alone.
