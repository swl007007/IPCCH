# Coordinator source freeze and execution release

The user's written-plan execution approval is already recorded in `approval.md`. The coordinator accepts the corrected implementation checkpoint and releases the previously authorized fitting/report/verification stage. This is a coordination barrier release, not a new user approval or Trellis audit.

- Approved-plan commit: `16d2e92a8948e7f235541a6facb452e375ac4f5d`.
- Tested implementation commit: `60578219e89d2f4e8aa17c644703200096a4f22b`.
- Entrypoint SHA256: `cbc1f88b2758cf4c2ec87c83257fc6f7f269d54018bd13f98138389da18db678`.
- Test SHA256: `952bd849fee05bf5396df257d0b7beb2b98c15df6cf5f26268248b3648ffbfac`.
- Verified executor: `somalia-local-executor`, pane `w11:p4`, terminal `term_65d6ae54981a13`, Claude session `579e6ba5-f2a2-483c-b465-4b2e3cca1ed3`, visible Opus 5.5 (1M context).
- Reliable focused tests: 82 passed / pytest exit 0; both real no-write preflight actions passed / exit 0, original parity 2800 global/regional cells and 280 SOM cells.
- Staged GitNexus detect_changes: 15 files, low risk, no indexed existing symbol/process affected. The new standalone file is outside the prior index; actual Git scope and source review establish its boundary.

Use the exact repository spelling and frozen interpreter from `implement.md`, with `PYTHONPATH=src` and the Windows Git shim for Git reads. Confirm the two pinned source hashes, then execute sequentially:

1. `--scope global --approve-training`.
2. `--scope SOM --approve-training`.
3. `--scope global --report`, then `--scope SOM --report`.
4. `--scope global --verify`, then `--scope SOM --verify`.

Only 2026 may be fitted: seven batches/four targets per scope, 14 batches/56 new boosters total. Keep the 112 old boosters per scope as separately identified imports. Do not change fingerprint-bound script/spec/config/input/helper bytes during execution. Preserve diagnostics and stop on a failed action; do not relax gates or repair old artifacts. No provider/launch/CDS run, audit command, duplicate executor, code commit, task archive or push is authorized for the executor.

Capture each command, actual action return code, stdout JSON and stderr/time log outside result/report inventories. Update `PROGRESS.md` and write final A1-A8 execution evidence with result/report/verification paths and hashes, exact new batch/model counts, both pooled row counts, old parity, all schema/replay/metric/delta counts and protection results. Keep final report/codebook/comparison metadata statuses truthful. Return a completion checkpoint and pause for coordinator acceptance; the coordinator will recheck the separate 961-file baseline, commit relevant evidence and perform ordinary Trellis finish.
