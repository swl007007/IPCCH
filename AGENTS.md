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

## Local MLflow registration (IPCCH Forecasting)

After any new model fit or result change that should be browsable, register it incrementally in the shared local MLflow store with `IPCCHMLflow/` (contract: `.trellis/spec/backend/local-mlflow-registration.md`; commands: `IPCCHMLflow/README.md`). New fit: add a new `source_key` to `IPCCHMLflow/sources.json` (plus vocabulary/extractor if needed), then plan, backup, snapshot, import, verify, dashboard, dashboard-verify and compare. Evaluation-only change: freeze the imported snapshot (`"frozen": true`) and add a `revision_of` entry that reuses its registered versions. Port 5000 needs `--live`; never edit SQL or rebuild the shared store. Record failures and rerun the same command to resume. Excluded families (Nigeria Sep18, `climate2015_v1`) and models fitted before September 2026 stay out. This is an agent workflow, not a watcher or a hook on training scripts.

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **IPCCH** (4349 symbols, 7100 relationships, 198 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> Index stale? Run `node .gitnexus/run.cjs analyze` from the project root — it auto-selects an available runner. No `.gitnexus/run.cjs` yet? `npx gitnexus analyze` (npm 11 crash → `npm i -g gitnexus`; #1939).


### MLflow principles: model cards, tags and assistant (shared local store, since 2026-10-14)

The local MLflow store (`/home/swl007007/.local/share/ipcch-mlflow`, http://127.0.0.1:5000, basic-auth, optional tunnel
https://mlflow.weilunshi.com) serves both projects. MLflow here is for research version and feature management and a
temporary internal dashboard; keep raw data, scripts and small metadata/results, not model packages or full-store backups.

- **Experiments** (IDs fixed): `IPCCH detailed runs` (1), `IPCCH dashboard` (2), `IPCCH forecasting detailed runs` (3),
  `IPCCH forecasting dashboard` (4). Detailed runs are the source records; dashboards hold one row and one external
  (not loadable) logged model per family x arm x lead (x seed or snapshot). Every logged model lives in its project's
  dashboard and is registered (`IPCCH <...>` / `IPCCH Forecasting <...>`).
- **Model card = logged-model description** (`mlflow.note.content`, <= 8000 chars, English, written for the AI assistant).
  It is generated, never hand-edited, from `Food_Crisis_Cluster/IPCCHMLflow/model_cards.json` by `model_cards.py`. Sections in
  order: `## card`, `## identity`, `## summary`, `## status`, `## catalog`, `## data`, `## features` (feature_set, n_features,
  groups with counts, construction and example columns), `## feature_engineering`, `## architecture` (+ arm difference),
  `## settings` (exact hyperparameters, window/refit/weights/threshold, plus the setting selected at this lead),
  `## environment`, `## evaluation`, `## observed` (forecasting params such as n_inputs), `## sources`.
  The registered-model description is the short card (<= 5000 chars: no feature engineering/evaluation/environment);
  version descriptions are left as registered.
- **Facts rules** (`model_cards.json`, one entry per family with per-arm overrides, values may be per lead as `{"3": ...}`
  or contain `{H}`): every fact comes from the run's own archived config/report/manifest/runtime record and cites it in
  `sources`; anything not recorded is written as "not recorded", never inferred from current code or lock files.
- **Human tags** (same on logged and registered models, model names unchanged
  `<family title> | <arm> | <lead>[ | window] | seed N|snapshot ...`):
  `project` (IPCCH / IPCCH forecasting), `model_type`, `feature_set` (short code: `compact296`, `compact296+ae128`,
  `rich561`, `rich561+mask561`, `rich601`, `origin_safe870+oracle12`, `somalia_D1009`, ...), `n_features` (exact model
  input count at that lead), `target`, `role` (baseline / candidate / diagnostic / oracle / comparison), `status` (short
  accepted conclusion), `scope`. Logged models also carry `card.feature_list` =
  `label=<runs:/RUN_ID/artifact/path | /abs/local/file[.tar!member]>#column[?col=value&col~H]` (`;`-separated blocks,
  `@header` = header columns after the key, `~` = JSON list contains the lead); its total length must equal `n_features`.
- **New or changed model**: register it with its importer, add/adjust its family and arm in `model_cards.json` (with
  sources), then `model_cards.py plan` -> review -> `apply --plan-fingerprint FP` -> `verify` (credentials:
  `MLFLOW_TRACKING_USERNAME/PASSWORD`). The IPCCH dashboard writer (`summary_catalog.py`) builds the same cards and tags.
- **Lookup**: `ipcch-model families|search|get|registered|features` (read-only; installed by `IPCCHMLflow/manage.sh start`;
  `get` accepts words from the model name).
  UI assistant = Gemini 3.8 Flash via the MLflow AI Gateway (Vertex AI, project manuel-remote-sensing), local and tunnel,
  running only read-only `mlflow`/`ipcch-model` commands as the READ-only user `assistant` (`IPCCHMLflow/assistant_patch.py`,
  MLflow 3.17.0 only).
- **IPCCH forecasting importer (this repo)**: on 2026-10-14 the experiments were renamed (`IPCCH Forecasting - detailed runs`
  -> `IPCCH forecasting detailed runs`, `IPCCH Forecasting - dashboard` -> `IPCCH forecasting dashboard`) and the forecasting
  logged models were moved from the detailed experiment to the dashboard by a one-off SQL change (IDs and versions
  unchanged). `IPCCHMLflow/naming.py` here still uses the old names and placement: update it before the next registration,
  then run `Food_Crisis_Cluster/IPCCHMLflow/model_cards.py plan|apply|verify` for the new models. Under the research
  storage policy the pre-registration full-store backup is optional.

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
