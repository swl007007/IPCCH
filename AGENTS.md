<claude-mem-context>
# Memory Context

# [ipcch] recent context, 2026-10-07 2:51pm EDT

No previous sessions found.
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

This project is indexed by GitNexus as **IPCCH** (4349 symbols, 7100 relationships, 198 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

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
