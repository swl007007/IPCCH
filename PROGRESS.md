# Global origin-safe climate and IDP benchmark

Current active task (2026-10-08): `.trellis/tasks/10-08-compact-climate-weather-oracle`; the earlier entry below is preserved as historical context.

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
- Supervisor accepted the implementation checkpoint after fresh manifest/helper/runtime/contract checks and actual legacy baseline/H0 and oracle/H3 dry-runs (870/876 columns, no outputs). Full seven-run compact dry-run passed. Executor is paused before real fitting; Codex now commits the implementation and continues the already-approved pilot/full suite.

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
