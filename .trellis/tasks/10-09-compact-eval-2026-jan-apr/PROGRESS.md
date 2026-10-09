# Progress ledger: compact 2026 January-April historical evaluation

## Current state

- Date:2026-10-09; ordinary Trellis start confirmed `in_progress` in supervisor session.
- Repository baseline observed: `644c2e0095a1fea669203a6af6c59d7af787a632`, branch `task/compact-climate-weather-oracle`.
- Requirements convergence: explicitly approved by the user after five scientific/scope choices.
- Written-plan implementation approval: explicitly received (`A：批准 spec，开始执行（推荐）`); exact bounded execution authorized.
- Approved-plan commit: `16d2e92a8948e7f235541a6facb452e375ac4f5d` (planning files only).
- Executor verified in Herdr: name `somalia-local-executor`, pane `w11:p4`, terminal `term_65d6ae54981a13`, Claude session `579e6ba5-f2a2-483c-b465-4b2e3cca1ed3`; visible UI confirms `Opus 5.5 (1M context)`. Dispatch delivered and working activity observed; executor remains in this same session.
- Audit policy: user explicitly requested no Trellis audit.

## Completed planning work

- Read-only code/data/report/identity exploration; primary annual/local mask boundary spot-checks.
- Formal PRD/design/implementation plan, expected14-run contract, requirement-approval record and grounded research evidence written after convergence approval.
- Curated implementation/check context manifests prepared for the approved scope.
- Coordinator read the PRD/design/plan end-to-end; planning-only assertions checked all required docs, every JSONL reference/reason, fourteen distinct expected runs,56newboosters, scope/arm/date/feature/evaluation counts and `planning` state. The four named existing test files are present. This is document validation, not extension model/test acceptance.

## Implementation checkpoint

- Opus implemented only the two approved new product files. Coordinator read the initial entrypoint/tests end-to-end and returned four bounded fixes in `research/supervisor-code-review.md`.
- Coordinator inspected the corrected accepted-inventory checks, fixed parameters, full support/split-table verification, final reporting status, and tiny synthetic test settings. No existing product source/config was edited.
- Focused/affected tests: **82 passed in 130.35s; pytest exit 0**, recorded in `research/focused_tests.log`. Both product file hashes match `research/focused_tests_code_sha256.txt` after the run.
- Corrected real no-write preflight passed for global and SOM with exit 0. Coordinator checked both saved outputs, all 14 run records, current script hashes, exact old schema counts and absent output roots. Heavy fitting remains behind the coordinator source-freeze checkpoint.
- Independent coordinator protection baseline: 961 files, 6,090,454,088 bytes, in `research/supervisor-protected-before.json`.

## Not executed yet

Heavy fitting, new model/metric replay, report/codebook generation and final A1-A8 acceptance have not run. Passing synthetic tests and planning/schema validation do not establish real fitted-model acceptance.

## Preserved unrelated work

Existing dirty `AGENTS.md` and archived superseded launch PNG remain outside this task. No protected old input/result/report/launch/config/source bytes are to be changed.

This ledger records operations and evidence, not approval authority. Reconcile with the actual user approval and Git state before resuming.

## Executor implementation checkpoint (2026-10-09; paused at source-freeze barrier)

- Executor bound with ordinary `task.py start` (source `session:claude_579e6ba5-…`; task.json byte-identical). HEAD `16d2e92`; no audit, no commit, no fit.
- New files only: `scripts/modeling/run_compact_eval_2026_extension.py` (sha256 `cbc1f88b…`), `tests/unit/test_compact_eval_2026_extension.py` (`952bd849…`). No existing symbol/helper/config/input/output edited.
- Supervisor code review findings 1–4 addressed (accepted-inventory reconciliation + prior pass + fixed parameters; full support and exact split tables; truthful pending→verified/verification_failed finalization; tiny test-only hyperparameters) with tests.
- Focused command (implement.md): **82 passed in 130.35 s, pytest exit 0** (log `research/focused_tests.log`; hashes unchanged during run).
- `--scope global --validate-only`: exit 0, 2:46.47, 1.66 GB; `--scope SOM --validate-only`: exit 0, 2:36.77, 1.00 GB. Both passed with no problems and wrote nothing; all expected 2026 fit/eval sets, cutoffs and feature counts match `expected_runs.csv`; original parity 2,800/280 cells; original fingerprints reproduced. Details: `research/implementation-checkpoint.md`.
- Next (only after supervisor commit/freeze and phase release): global then SOM `--approve-training`, `--report`, `--verify`.
