# Implementation and verification plan

Status: planning only; awaiting approval of the final summary. Spec/code generation order: PRD/design/plan -> expected contract -> final review -> implementation. No experiment has run.

## Ownership and execution contract

Codex owns specification, decisions, supervision, final verification and commits. The user explicitly requests Claude Opus5.5 with1M context as executor; use that verified runtime, not a default Codex substitute. The local `trellis-channel` skill provides durable supervisor/executor messaging and file/jsonl context injection. CLI capability was checked: Trellis0.6.16 and Claude Code2.1.280 exist; actual requested model/context resolution is not yet verified.

After final approval, verify model ID/context in the real Claude session before sending implementation instructions. A CLI accepting a model string is not sufficient evidence of resolved runtime. Record provider, model, context, session/channel IDs and launch configuration; if unavailable, stop with the exact runtime issue instead of switching models. Read default agent configuration rather than selecting prohibited explorer/worker roles. Use explicit `--provider claude`, verified `--model`, stable executor handle, task files and `implement.jsonl`; use text-file/stdin instructions. Monitor durable done/error events and progress. No Herdr dependency is required by this task.

The user explicitly opted out of additional audit registration for this task. Do not invoke trellis-audit register/start/close or change existing audit gates. After approval use the ordinary task lifecycle consistent with this exception. Keep repository-local PROGRESS.md as execution ledger; reconcile with Git and evidence on resume, not as approval authority. Prefer Windows Git executable and the existing temporary shim for Trellis Git calls.

## Scope and reuse

- Add a small `src/ipcch/compact_features.py` for ordered schema, direct-source recipe construction, seasonal major identity and compact-version validation. Reuse Grid/rolling/same_month_history/stress primitives. Do not rewrite source producers or change legacy helper default outputs.
- Add `scripts/preprocessing/build_compact_climate_weather_oracle_inputs.py` to consume the frozen parent, rebuild approved blocks, append existing raw oracle, write input/coverage/lineage/manifest and verify baseline parity. Reuse existing source loaders/key/history/IDP/target checks; do not instantiate a deep-feature pipeline merely to compute discarded columns.
- Extend the explicit named-version/arm path in `scripts/modeling/run_deep_feature_weight_decay_forecasting.py` for this compact manifest. Preserve every old version's behavior and validation; never bypass gates globally. Include compact recipe/source/contract hashes in fingerprints.
- Reuse the existing suite runner/orchestration where it accepts explicit version/arms/paths; otherwise add only a thin `scripts/modeling/run_compact_climate_weather_oracle_suite.py` driver for seven ordered runs. Do not copy the trainer.
- Add a focused saved-prediction reporting/verifier entry under `scripts/postprocessing/` for this version and all-region point metrics. Reuse global metric helpers and artifact replay pieces; no bootstrap stage or regional trainer.
- Add focused tests for new recipes/schema/region aggregation and extend origin-safe CLI smoke coverage. Existing callers, fixtures and version-specific resume validation must remain compatible.
- Preserve explicit legacy and compact manifest selection; add rollback.md with exact version/source/schema/commit/run identities and selection examples. Test both selection paths without rerunning the full legacy experiment. Future changes must not overwrite the frozen compact version.
- Add actual-input codebook export using contract descriptions plus independently checked fitted lists, not ad-hoc all-numeric schema inference. Keep large artifacts in existing ignored roots and tracked task evidence with explicit paths/hashes.

Before editing existing symbols, run GitNexus impact upstream and report direct callers/processes/risk. Warn on HIGH/CRITICAL. If stale/not-found, resolve the index limitation before editing; do not pretend an empty result proves no impact. Run detect_changes before commits. Scope is limited to approved recipe/builder/trainer integration/report/test/documentation paths; preserve unrelated changes.

## Ordered stages and evidence dependencies

1. **Approval and preflight.** Record final user approval, frozen plan identity and Windows Git status; commit approved planning artifacts before implementation after scope verification. Verify actual Claude runtime and context. Verify pinned numerical environment, parent/config/source hashes, region map and all required input paths. No builder/training if drift occurs.
2. **Implement compact schema and recipes.** Follow design literals/order and source lists. Reconstruct at O without carrier masks; preserve old stress behavior. Season lookup ledger must drive both selected climate values and latest-season major dummy so identities cannot drift. Unit checks pass before full input generation.
3. **Integrate manifest and CLI.** Admit only the two compact arms and specified horizons. Assert ordered expected schema, non-oracle timing, history/IDP ledgers, targets/cohort, baseline projection parity and output isolation. Hash all consumed helpers. Dry-run returns without output writes. Resume requires full model inventory, matching fingerprints and artifact bytes.
4. **Build inputs.** New namespace only. Validate serialized matrices with round-trip parsing, no Inf, duplicate keys or unknown fields. Save feature availability by fitting batch/eval year, old comparable-cell NA restorations, source/grid/season/oracle timing and source hashes. Do not copy old masks. Complete input validation precedes training.
5. **Fit sequential suite.** Start with one real annual batch of compact baseline/H0, measure resources and verify artifacts; then complete all remaining batches/runs with unchanged numerical settings. Pilot is part of the seven runs, not an extra arm. No edits to fingerprinted code during a suite; a necessary change invalidates/restarts affected new batches with truthful provenance.
6. **Score saved predictions.** Annual and pooled eight metrics globally and regions0–8, paired deltas for H3/H6/H12. Check region partition, no small-group omission, reported truth and normalized continuous truth. No retraining/bootstrap.
7. **Verify and report.** Reload all112 models; check fitted order against contract, replay28 batches, reconstruct fitting keys/targets/weights and all metrics. Write actual codebook, expected-vs-actual diff and complete artifact inventory. Final Codex verification checks concrete evidence, not executor prose.
8. **Finish.** Record checks, deviations and provenance in task evidence/PROGRESS.md; use Windows Git, detect_changes, focused commits and normal Trellis wrap-up without audit enrollment. No completion claim while required artifacts/checks are missing.

## Required meaningful tests

- Ordinary value/MA/SD on a tiny irregular calendar series: min-count boundaries, ddof1, absent current month, H0/3/6/12 alignment, no compressed-row lagging.
- Same-month z: strictly earlier years only, two-history minimum, zero SD, z-before-MA with hand-calculated distinct values, no secondary z on excluded indices.
- Stress: all seven thresholds and equality boundaries; current NA; missing year-ago GPP and missing/zero WFP comparator remain0; months_since through NA; run breaking and six-valid windows.
- D16 regression: source at O exists but O+12 carrier absent; new inputs retain the source value and supported rolling values. No imputation of genuinely absent sources.
- Season: exclusive-end exact boundary, cross-year dates, two ranks, tied ends/later starts, missing seasons, s1/s2 longer/shorter/tie/unavailable; major derives from the same selected latest record.
- Leakage: perturb post-O non-oracle sources/labels and verify earlier features unchanged; oracle changes only declared future months, and H12 ignores O+7..O+12; do not perturb fixed paired calendar context as if it were realized future climate.
- Contract: exact names/order/counts per seven runs, disallowed blocks absent; identical baseline prefix values/NA/keys/truths in oracle; target/diagnostic additions rejected.
- CLI/version/resume: tiny four-year smoke with exact schema, changed fingerprints and missing one model artifact rejected; old supported versions remain admitted; compact outputs cannot target old directories; full seven-run plan, H0 single fit.
- Metrics: independent formulas for class threshold and eight metrics; zero-positive/no-predicted-positive/constant-target/empty/small groups, region0 inclusion, missing mapping failure, unequal-key failure, pooled score from rows; no bootstrap invocation.

## Validation commands and artifacts

Use `PYTHONPATH=src /home/swl007007/.venvs/ipcch-geo/bin/python -m pytest tests/unit/test_compact_features.py tests/unit/test_origin_safe.py tests/unit/test_origin_safe_weather_oracle.py tests/unit/test_climate2015_features.py tests/smoke/test_origin_safe_cli.py -q`, including the new regional test file once named. Run focused additions before regression tests; avoid heavy suites during training. Existing global test failures in unrelated launch/map paths are historical notes, not automatic waivers for new failures.

Exact builder/suite/report CLI flags must be captured from implemented --help and the actual invocation into evidence, together with exit codes and output paths. Do not present proposed CLI names as executed commands. Input manifests, per-batch records, prediction/model replay report, metrics tables, coverage ledgers, actual codebook and hashes constitute completion evidence.

## Limits and rollback

The requested model/context and numerical runtime are preflight checks, not assumed available. Upstream price vintages/climate standardization provenance remain disclosed limitations. No retrospective raw-data edits, no old-output overwrites and no extra sensitivity arms. Stop the new suite on scientific contract failures, preserve incomplete results and return the specific discrepancy to the supervisor.
