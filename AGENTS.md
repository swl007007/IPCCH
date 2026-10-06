<claude-mem-context>
# Memory Context

# [IPCCH] recent context, 2026-10-06 1:27pm EDT

Legend: 🎯session 🔴bugfix 🟣feature 🔄refactor ✅change 🔵discovery ⚖️decision 🚨security_alert 🔐security_note
Format: ID TIME TYPE TITLE
Fetch details: get_observations([IDs]) | Search: mem-search skill

Stats: 50 obs (27,718t read) | 444,689t work | 94% savings

### Oct 5, 2026
S518 Recolor non-crisis areas in Somalia April 2026 alert map PNG from gray (#d9d8d4) to green, overwriting original file in place (Oct 5, 6:24 PM)
S522 Trellis task: global-climate-2015-features — fork IPCCH pipeline with new climate CSVs, feature engineering, rerun 0m/3m/6m/12m global metrics (11 total runs: baseline×4, masked×4, unmasked×3) (Oct 5, 6:36 PM)
3062 7:27p ⚖️ New Trellis Task Planned: IPCCH Pipeline Fork with Updated Climate Features
3063 7:29p 🔵 climate_2015_2026_MODELING_READY.csv: Audit Findings and Conditional Usability
3064 " 🔵 climate_monthly_2015_2026_MODELING_READY.csv: Schema Confirmed
3065 " 🔵 IPCCH Repository State: Experiments, Specs, and Trellis Status
3066 7:30p 🔵 Existing Global Model Feature Schema: GLDAS/FLDAS Variables vs New CHIRPS/ERA5 Climate CSVs
3067 7:31p 🔵 Climate CSV Coverage Check: Full admin overlap, monthly data through August 2026
3068 " 🔵 Trellis task.py create Requires --description Flag
3069 " 🟣 Trellis Task Created: Global Climate 2015-2026 Feature Rerun (0m/3m/6m/12m)
3071 " 🔵 Upstream Deep Feature Engineering Code Located at build_deep_ipcch_features.py
3070 7:32p 🔵 Pipeline Dataset Resolution and Feature Column Selection Logic
3072 7:38p 🔵 build_deep_ipcch_features.py: Full Feature Engineering Architecture
3073 7:39p 🔵 build_multiscope_ipcch_features.py: Scope Anchor Lags and Nigeria Precedent Pattern
3074 " 🔵 Exact Feature Counts and Naming Patterns Per Scope in Existing Model-Ready CSVs
3075 7:40p 🔵 Stress Signal Thresholds and Rolling Feature Implementation Details
3076 " 🔵 New Climate Variable Distributions: Stress Threshold Calibration Data
3077 7:44p 🔵 Pipeline Core Code Unchanged Since Baseline Global Runs (2026-05-31)
3080 " 🔵 Deep Feature Family Formulas: All Use t-12 Anchor with group-by-area_id Operations
3081 7:51p 🔵 build_multiscope_ipcch_features.py Architecture: Takes Pre-Engineered Deep Features, Applies Time Shift Per Scope
3082 " 🔵 Interaction Pairs and Spatial Spillover Are Hardcoded to Old GLDAS Column Names
3083 7:52p 🔵 Machine Resources and Interim Panel Confirmation
3084 " 🟣 Trellis PRD Written: Climate 2015 Feature Rerun Spec with Full Design Decisions
3085 7:53p 🔵 Panel Preparation: admin_code→area_id Rename and Static Context Columns
3089 " 🔵 Quality guidelines: forbidden patterns, 12 pre-existing test failures, safe_divide behavior
3090 " 🔵 forecasting_ready.csv header: exact column positions and old interaction names confirmed
3091 7:56p 🔴 src/ipcch/climate2015_features.py written: complete feature engineering module
3092 7:57p 🔴 Three patches applied to climate2015_features.py; import smoke test passed
3094 7:58p 🔴 check_climate2015_fork_fidelity.py written: fidelity gate script comparing recomputed vs saved FLDAS families
3095 " 🔴 Fidelity check ran in 35s: scope-block NaN-tail mismatch expected, but neighbour mean shows genuine value discrepancy up to 0.139
3096 " 🔴 Fidelity block summary: asof12 block has only 2 mismatches; neighbour mean is the only real discrepancy; all 39 s0 mismatches are the expected NaN-tail
3097 8:01p 🔴 Scope-block NaN artifact quantified: baseline scope files have 0% NaN in training rows but 60%/46%/2% NaN in 2025 for s0/s3/s6; new direct-anchor fills these
3099 8:02p 🔴 tests/unit/test_climate2015_features.py written: 8 unit tests covering anchor safety, naming, stress thresholds, spell helpers, same-month history, season completion, old-column detector, and ragged grid
3104 8:08p 🔴 run_climate2015_global_suite.py written — 11-run orchestration script for implement.md step 8
3109 8:09p 🟣 climate2015_v1 pipeline fork: all scripts written, builds and runs in progress
3115 " 🔵 Implementation status checkpoint: all scripts written, compute in progress — ~2-3 hours remain
3116 " 🔵 Build progress at 750s: fs0/fs1/fs2-masked done; baseline_rerun_0m training at 2690% CPU, 342 min CPU time
3108 " 🔴 compare_climate2015_global_metrics.py written — implement.md step 9 complete
3118 8:13p 🔵 Build stalled at fs2/masked (750s) — fs2/unmasked and fs3 still pending after repeated status checks
3110 8:14p 🔵 Full build progress: fs0 complete (52521 rows, 847 cols), baseline_rerun/0m started; memory at 10/15GB
3119 8:20p 🔵 Full dataset build timing: each scope variant takes ~180s for masked + ~95s for unmasked on full 52K-row panel
3120 8:26p 🔵 Full dataset build complete: exit 0 at 1059s — 7 files written, 4065MB total, all column counts correct
3121 " 🟣 Trellis check agent launched (a0c2501d85a969df7) to review code against prd/design specs
S525 Status check (现在怎么样了) on deep_feature_weight_decay_forecasting climate2015 experiment comparing 2015–2026 climate features vs FLDAS baseline (Oct 5, 8:41 PM)
3177 9:48p 🔵 Climate2015 Deep Feature Experiment Suite Progress Check
3178 " 🔵 Masked vs Baseline Model Interim Metrics: Climate2015 Deep Feature Experiment
S523 Status check on climate2015 deep feature weight decay forecasting experiment — masked vs baseline model comparison (Oct 5, 9:48 PM)
S526 Status check (现在怎么样了) — full run completion and diagnostic investigation of 0m/2025 R² regression (Oct 5, 9:50 PM)
S528 Climate2015 global model experiment — full completion summary presented to user; session wrapping up pending merge and Trellis close (Oct 5, 10:16 PM)
3193 10:17p 🟣 Climate2015 experiment report and evidence.md finalized
3194 " 🔵 Baseline drift in 3m/6m scopes traced to pre-rebuild fs1/fs2 inputs
3195 " ✅ Climate2015 lessons added to quality-guidelines.md and all files staged for commit
3197 " 🔵 Staged climate2015 changes confirmed low-risk by gitnexus (all new files, no symbol modifications)
3198 " 🟣 Climate2015 feature swap committed to IPCCH repo at 585640b
S529 User approved submission — complete Trellis task, push branch, merge to main (Oct 5, 10:17 PM)
S530 User approved final submission: complete Trellis task, push branch, merge to main — session in wrap-up phase (Oct 5, 10:18 PM)
S527 Status check on climate2015 global model experiment — full completion, results, diagnosis, and commit (Oct 5, 10:18 PM)
3202 10:26p ✅ Trellis task 10-05-global-climate-2015-features archived and session journal recorded
3203 " 🟣 Climate2015 feature branch pushed to GitHub and fast-forward merged into main
S531 完成 Trellis 任务、push 分支、合并到 main — climate2015 feature swap 全流程完成 (Oct 5, 10:26 PM)
**Investigated**: Trellis task state (in_progress → archived); remote/branch relationships confirmed (main ancestor of feature branch, main in sync with origin/main before merge)

**Learned**: - fast-forward merge was possible because main was a direct ancestor of feat/global-climate2015-features (no divergence)
    - results/ and reports/ are gitignored — comparison report and metrics CSV exist locally only, not in the remote repo
    - Trellis archive and session journal each auto-commit, adding 2 extra commits on top of the feature commit

**Completed**: - Trellis task 10-05-global-climate-2015-features archived to .trellis/tasks/archive/2026-10/ (commit 3040185)
    - Session journal recorded (commit df8acaf) with full experiment summary tied to commit 585640b
    - feat/global-climate2015-features pushed to origin with tracking set up
    - main fast-forwarded from 871112a to df8acaf (4 commits added) and pushed to origin/main
    - GitHub remote (https://github.com/swl007007/IPCCH.git) is fully up to date; working directory clean
    - Full climate2015 Trellis lifecycle closed: implement → evidence → archive → journal → push → merge

**Next Steps**: - Optionally delete feat/global-climate2015-features branch locally and on remote (no outstanding work)
    - Run `node .gitnexus/run.cjs analyze` to refresh GitNexus index (stale after commits)
    - Remaining open Trellis task: 00-bootstrap-guidelines (planning stage, unrelated to this work)


Access 445k tokens of past work via get_observations([IDs]) or mem-search skill.
</claude-mem-context>

# Project Guidance Addendum

## Interpretability and SHAP Workflows

Interpretability artifacts intended for comparison or reporting must record the model target, sample source, feature matrix construction, fitted feature order, aggregation metric, and relevant input artifact paths in machine-readable metadata. Comparison helpers should combine artifacts from explicit paths or metadata-recorded paths, not unconstrained recursive directory scans.

Nowcasting grouped SHAP is optional and enabled with `--compute-grouped-shap` in `scripts/modeling/run_launch_nowcasting_2026_04.py`. It currently supports train-and-predict runs only, explains only the fitted `phase3_worse` cumulative regressor, and must use the exact phase-3 training feature matrix with the fitted feature order. It groups features by the six-category crosswalk plus a seventh group named exactly `weather forecast`; runtime weather forecast proxy features take precedence before crosswalk matching. Unmatched features are diagnostics-only and must not be assigned to an `other` fallback group unless a future spec explicitly changes that. Scope comparisons use canonical order `0m`, `3m`, `6m`, `12m`.

## Spec Kit Artifact Alignment

When updating Spec Kit artifacts, use the current implementation plus explicit user design clarifications as the baseline. Record implementation-vs-design drift in `evidence.md` and `task-evidence-trace.md`; do not change `tasks.md` checkboxes as proof of implementation or validation. `Evidence Status: Ready` means the evidence artifact is ready for grounding only; if `Validation Status` is `Not Executed`, do not claim tests, CLI checks, artifact generation, or final acceptance were validated.

Current feature baselines to preserve: Spec002 alert-risk maps are single-scope CLI runs (`--scope global` or an ISO3 such as `SOM`) and global/Somalia deliverables require separate invocations; Spec005 launch scopes are `0`, `3`, `6`, and `12` months, with April 2026 + `12m` targeting April 2027; Spec006 phase-3 SHAP runs one selected `--fs` per invocation, and full four-scope 96-row/four-heatmap deliverables are assembled across `fs0`/`fs1`/`fs2`/`fs3` runs or downstream aggregation.

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **IPCCH** (3579 symbols, 5533 relationships, 163 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> Index stale? Run `node .gitnexus/run.cjs analyze` from the project root — it auto-selects an available runner. No `.gitnexus/run.cjs` yet? `npx gitnexus analyze` (npm 11 crash → `npm i -g gitnexus`; #1939).

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows. For regression review, compare against the default branch: `detect_changes({scope: "compare", base_ref: "main"})`.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `query({search_query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `context({name: "symbolName"})`.
- For security review, `explain({target: "fileOrSymbol"})` lists taint findings (source→sink flows; needs `analyze --pdg`).

## Never Do

- NEVER edit a function, class, or method without first running `impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `rename` which understands the call graph.
- NEVER commit changes without running `detect_changes()` to check affected scope.

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/IPCCH/context` | Codebase overview, check index freshness |
| `gitnexus://repo/IPCCH/clusters` | All functional areas |
| `gitnexus://repo/IPCCH/processes` | All execution flows |
| `gitnexus://repo/IPCCH/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->
<!-- TRELLIS:START -->
# Trellis Instructions

These instructions are for AI assistants working in this project.

This project is managed by Trellis. The working knowledge you need lives under `.trellis/`:

- `.trellis/workflow.md` — development phases, when to create tasks, skill routing
- `.trellis/spec/` — package- and layer-scoped coding guidelines (read before writing code in a given layer)
- `.trellis/workspace/` — per-developer journals and session traces
- `.trellis/tasks/` — active and archived tasks (PRDs, research, jsonl context)

If a Trellis command is available on your platform (e.g. `/trellis:finish-work`, `/trellis:continue`), prefer it over manual steps. Not every platform exposes every command.

If you're using Codex or another agent-capable tool, additional project-scoped helpers may live in:
- `.agents/skills/` — reusable Trellis skills
- `.codex/agents/` — optional custom subagents

Managed by Trellis. Edits outside this block are preserved; edits inside may be overwritten by a future `trellis update`.

<!-- TRELLIS:END -->
