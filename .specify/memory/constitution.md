<!--
Sync Impact Report
==================
Version change: 1.4.0 → 1.5.0

Bump rationale (MINOR):
  - Added Spec Kit artifact-alignment guidance: current implementation plus
    explicit user design clarifications are the baseline for spec/evidence
    updates, checked tasks are claims rather than validation proof, and
    Evidence Status is separate from Validation Status.
  - Recorded current feature baselines for single-scope alert-risk maps,
    launch scopes `0`/`3`/`6`/`12`, and selected-`--fs` phase-3 SHAP runs.

Modified principles:
  - Development Workflow & Quality Gates — expanded to define Spec Kit evidence
    and artifact-alignment semantics.

Added sections:
  - Development Workflow & Quality Gates: Spec Kit evidence and artifact alignment
  - Development Workflow & Quality Gates: Current feature baselines

Removed sections: none

Templates requiring updates:
  - ⚠️ .specify/templates/plan-template.md — should add an interpretability
        metadata/checkpoint item when future features add SHAP or feature
        importance artifacts.
  - ✅ CLAUDE.md — updated to document Spec Kit artifact-alignment and current feature-baseline rules.
  - ✅ AGENTS.md — updated to document Spec Kit artifact-alignment and current feature-baseline rules.

Follow-up TODOs:
  - Update Spec Kit templates if another interpretability feature is planned.
  - Consider adding the Spec Kit evidence-status distinction to Speckit templates if future evidence workflows recur.
-->

# IPCCH Constitution

## Core Principles

### I. Temporal Validation Integrity (NON-NEGOTIABLE)

For each test year, the training set MUST contain only observations strictly
prior to the first observation in the test window. No record from the test year
may be used for model fitting, hyperparameter tuning, feature scaling, target
encoding, rolling-window summaries, threshold selection, sample-weight
calibration, label mapping calibration, model selection, or any other operation
that influences fitted parameters or reported metrics.

Each feature specification MUST declare its annual split policy before
implementation. Acceptable split policies include:

- **All-prior-history annual holdout**: train on all eligible records with dates
  strictly before January 1 of the test year, then test on records in that test
  year. Example: 2025 test trains on records before 2025-01 and tests on 2025;
  2024 test trains on records before 2024-01 and tests on 2024.
- **Fixed-window annual holdout**: train on a feature-declared historical window
  that ends strictly before January 1 of the test year, then test on records in
  that test year. Example: a 2024 fixed-window test may train on 2021–2023 and
  test on 2024 when the feature explicitly declares that window.

Reported metrics for canonical regressors, experimental classifiers, and any
feature-added metrics MUST be produced only from the declared split policy for
that feature. If a feature changes the split policy from a prior experiment, the
spec or plan MUST document the change and why it is appropriate.

**Rationale**: Food security forecasting is meaningless if evaluation leaks future
information. This principle is the single most important guarantee the project
makes to downstream stakeholders (IFPRI, FEWS NET consumers of phase forecasts).
All-prior-history and fixed-window policies are both valid when declared, because
the critical guarantee is that no test-window or future information influences
training or evaluation outside its own test period.

### II. Shared Utilities Live in `ipcch` Package

All reusable Python code MUST live in `src/ipcch/` and be imported as
`from ipcch.<module> import …`. Notebooks and scripts MUST NOT redefine pipeline
primitives locally and MUST NOT import from a root-level `food_crisis_functions.py`
or other ad-hoc module paths. New utility functions MUST be added to the package
(or a new submodule of it) rather than duplicated across notebooks.

The canonical entry points are:

- `ipcch.food_crisis_functions` — model pipeline, metrics, feature constants,
  Earth Engine helpers.
- `ipcch.paths` — repository-root paths, config/data/result/report directories,
  and external data path defaults.

**Rationale**: Notebook-driven research drifts quickly. A single package import
path keeps `convert_prob_to_phase`, `all_metrics`, feature sets, and threshold
constants identical across every experiment.

### III. Reproducible, Path-Agnostic Pipeline

Code MUST NOT hardcode absolute filesystem paths. Repository-internal paths MUST
be resolved through `ipcch.paths` (which locates `PROJECT_ROOT` self-relatively).
External data paths (source CSVs, GeoJSONs, intermediate caches outside the repo)
MUST be resolved through `ipcch.paths.external_path()` with defaults documented
in `configs/paths.example.json` and machine-specific overrides placed in the
git-ignored `configs/paths.local.json`.

Scripts MUST expose path-bearing inputs as CLI flags with sensible defaults from
`ipcch.paths`; they MUST run from the repository root with
`pip install -e .` (or `PYTHONPATH=src`) without further environment setup.
Experimental classifier workflows MUST expose the phase class mapping as a CLI
flag or config option rather than requiring notebook-cell edits.

**Rationale**: The project is developed across Windows (Dropbox-mirrored) and
WSL, and shared with collaborators. Hardcoded paths break every handoff;
`paths.local.json` keeps machine-specific overrides out of git.

### IV. Separation of Inputs, Generated Artifacts, and Reports

The repository MUST maintain a strict three-way split:

- **Tracked inputs**: `configs/*.json` (hyperparameters, path examples) and
  `data/reference/*.csv` (region mappings, lookup tables). These are
  authoritative project inputs and changes MUST be reviewed.
- **Machine-readable generated outputs**: everything under `results/`
  (predictions, experiments, metrics). Large prediction CSVs under
  `results/predictions/` are git-ignored; they are reproducible from the
  pipeline.
- **Human-readable generated artifacts**: figures, tables, and reports under
  `reports/`. These are the deliverable surface for the manuscript and slides.

Raw external source data (under `Analysis/1.Source Data/`) MUST NOT be copied
into this repository. Documentation belongs in `docs/`; the editable
architecture diagram is `docs/IPCCH.drawio`. Experimental classifier outputs
MUST be separated from canonical regressor outputs and labeled with the selected
class mapping in artifact paths, filenames, or metadata.

**Rationale**: Conflating inputs, intermediate artifacts, and final reports
makes it impossible to know what is authoritative, what is reproducible, and
what is a deliverable. The split keeps git history meaningful and prevents
accidental commits of multi-gigabyte prediction tables.

### V. Safe Execution & Notebook Discipline

Heavy model-training notebook cells MUST NOT be executed by automation
(Claude Code, CI, batch agents) unless the user explicitly requests it.
Validation by automation is limited to: import checks, CLI `--help`, small
smoke tests on tiny slices, and static inspection of code.

Notebooks (`Table1_*.ipynb` family) MUST follow the established two-cell-per-test-year
structure:

1. Training loop cell (one per test year: 2024, 2023, 2022).
2. Post-processing cell that saves a CSV and calls `%reset -f` to free memory.

After `%reset -f`, the next cell MUST re-import dependencies and reload data
from scratch. `convert_prob_to_phase()` MUST be called with exactly `y_pred`,
`y_test`, and the phase columns; only the phase-5 frame may carry `test_index`.
Default working scope is Nigeria
(`Table1_Forecasting_main_withlag_NGA.ipynb`) unless the user specifies
otherwise.

Automation MUST NOT commit large notebook outputs, regenerated execution counts,
or incidental metadata-only notebook diffs. Notebook edits MUST be reviewed as
source changes, with outputs cleared unless the user explicitly requests saved
outputs.

**Rationale**: Training runs are slow and expensive, and notebook state is
fragile. Following the established cell structure prevents the index-alignment
and memory bugs that have already been diagnosed and fixed. Treating notebooks
as reviewable source — not output dumps — keeps diffs meaningful and prevents
multi-megabyte cell outputs from bloating git history.

## Data & Model Standards

- **Canonical model architecture**: 4 separate XGBoost regressors per
  configuration, targeting cumulative phases `phase2_worse`, `phase3_worse`,
  `phase4_worse`, `phase5_worse`. Hyperparameters MUST be loaded from the JSON
  files in `configs/`: `forecasting_hyperparameters.json` (+ `_p3.json`
  variant) and `contemporaneous_hyperparameters.json` (+ `_p3.json` variant).
  Phase 3 uses its own tuned hyperparameter file.
- **Phase conversion**: Discrete phase labels (1–5) MUST be produced by
  `convert_prob_to_phase()` with the top-down threshold `th=0.2`. Changing
  the threshold requires a MINOR constitution amendment.
- **Spatial identifier**: `area_id` is the canonical spatial key joining
  observations, regions, countries, and coordinates. Ground truth is
  `overall_phase`; predictions are `overall_phase_pred`.
- **Regional models**: Region splits MUST use
  `data/reference/area_id_country_region_mapping.csv`. Known sparsity issues
  for region-year combinations are tracked in `docs/ISSUES_FIXED.md`.

**Experimental / Alternative classifier workflows**: Experimental workflows MAY
train a multi-class XGBoost classifier directly on class labels derived from
`overall_phase`. Such workflows MUST declare the class mapping before
implementation. Supported mappings include:

- **5-class**: `1`, `2`, `3`, `4`, `5`.
- **3-class**: `1-2`, `3`, `4-5`.
- **4-class**: `1`, `2`, `3`, `4-5`.
- **Binary**: `1-2` versus `3+`.

Classifier workflows MUST NOT silently replace the canonical cumulative regressor
workflow or its reported metrics. Output artifacts, metrics, and reports MUST be
labeled with the selected class mapping.

**Interpretability and SHAP workflows**: SHAP, feature-importance, and related
interpretability artifacts MUST identify the model target, sample source, feature
matrix construction, fitted feature order, aggregation metric, and relevant input
artifacts in machine-readable metadata when those artifacts are intended for
comparison or reporting. Interpretability comparisons across years, scopes,
regions, or runs MUST combine artifacts from explicit paths or metadata-recorded
paths; they MUST NOT rely on unconstrained recursive directory scans that can mix
outputs from unrelated runs.

Nowcasting grouped SHAP is an optional train-and-predict workflow enabled by
`--compute-grouped-shap`. It explains only the fitted `phase3_worse` cumulative
regressor using the exact phase-3 training feature matrix and fitted feature
order. It groups features by the project six-category crosswalk plus a seventh
group named exactly `weather forecast`; runtime weather forecast proxy features
MUST be assigned to `weather forecast` before crosswalk matching. Unmatched
features remain diagnostics-only and MUST NOT be assigned to an `other` fallback
group unless a future requirement explicitly changes that. Scope comparisons MUST
use canonical scope order `0m`, `3m`, `6m`, `12m`.

**Target-related leakage exclusions**: When `overall_phase` or any derived phase
class is the target, phase-percentage columns such as `phase1_percent`,
`phase2_percent`, `phase3_percent`, `phase4_percent`, and `phase5_percent` MUST
be excluded from model features because they are directly related to the target.
Any target-derived or contemporaneous phase columns used only for label
construction MUST be removed from the feature matrix before training. Specs and
plans for classifier workflows MUST explicitly document the excluded
target-related columns.

**Classifier metrics**: Multi-class classifier workflows MUST report metrics
appropriate to the declared class mapping. At minimum, they MUST report overall
accuracy, macro-F1, weighted-F1, per-class precision/recall/F1, and a confusion
matrix. For any mapping that includes a crisis-positive concept, they MUST report
binary crisis metrics for `3+` versus `1-2` when applicable. Metrics MUST be
generated only from the declared temporal split policy and MUST NOT use
test-window information for training, feature scaling, label mapping
calibration, sample weighting, threshold tuning, or model selection.

**Classifier CLI/config**: Classifier workflows MUST expose the class mapping as
a CLI flag or config option. Switching among mappings MUST NOT require editing
notebook cells. The recommended flag is `--phase-class-map`, with values such as
`five_class`, `three_class_123_45`, `four_class_123_45`, and `binary_12_3plus`.

## Development Workflow & Quality Gates

- **Branching**: Feature work proceeds on Spec Kit feature branches
  (`###-feature-name`) created by `/speckit-specify`. The default branch is
  `main`.
- **Spec Kit flow**: `/speckit-specify` → `/speckit-clarify` (optional) →
  `/speckit-plan` → `/speckit-tasks` → `/speckit-implement`. Each `/speckit-plan`
  invocation MUST include a Constitution Check that verifies the plan does not
  violate Principles I–V; any violation requires a Complexity Tracking entry
  with explicit justification.
- **Commits**: Auto-commit hooks defined in `.specify/extensions.yml` may run
  after each Spec Kit phase; they are optional and require user approval.
  Generated commits MUST NOT include raw source data or files matching
  `results/predictions/` glob patterns.
- **Reviews**: Pull requests touching `src/ipcch/`, `configs/*.json`, or
  `data/reference/` MUST be reviewed before merge, since these are tracked
  pipeline inputs that affect every downstream experiment.

### Spec Kit Evidence and Artifact Alignment

When updating Spec Kit artifacts after implementation exists, the current implementation plus explicit user design clarifications are the baseline for reconciling `spec.md`, `plan.md`, `tasks.md`, `evidence.md`, and `task-evidence-trace.md`. Implementation-vs-design drift MUST be recorded in evidence or trace artifacts before specs are revised. Checked tasks are implementation claims, not proof of validation, and MUST NOT be edited merely to make task status match an evidence pass.

`Evidence Status: Ready` means the evidence artifact is ready for repository grounding; it does not certify that tests, CLI checks, artifact generation, production runs, or final acceptance have completed. Evidence artifacts MUST keep Validation Status and Acceptance Readiness separate. If validation commands were not run or provided, guidance and summaries MUST state `Validation Status: Not Executed` and avoid claiming validated acceptance.

Current feature baselines to preserve unless a later spec explicitly supersedes them: Spec002 alert-risk maps use one selected `--scope` per CLI run (`global` or an ISO3 such as `SOM`), so global and Somalia deliverables require separate invocations; Spec005 launch forecast scopes are `0`, `3`, `6`, and `12` months, with April 2026 + `12m` targeting April 2027; Spec006 phase-3 SHAP runs one selected `--fs` per invocation, and complete four-scope 96-row/four-heatmap deliverables are assembled from `fs0`, `fs1`, `fs2`, and `fs3` runs or downstream aggregation.

### Constitution Check (Quality Gates)

Every `/speckit-plan` invocation MUST run a Constitution Check that explicitly
verifies all of the following before Phase 0 research and again after Phase 1
design:

1. **Temporal validation** uses no test-window or future information and declares
   the feature's split policy (Principle I).
2. **Reusable code** lives in `src/ipcch/` and is imported through `ipcch`
   (Principle II).
3. **Paths** are resolved through `ipcch.paths` or documented CLI flags;
   no hardcoded absolute paths in code or notebooks (Principle III).
4. **Inputs, generated machine-readable outputs, and human-readable reports
   remain separated** across `configs/`+`data/reference/`, `results/`, and
   `reports/` (Principle IV).
5. **Automation avoids heavy notebook training** unless the user explicitly
   requests it; validation uses imports, `--help`, and small smoke tests
   (Principle V).
6. **Changes to `src/ipcch/`, `configs/*.json`, or `data/reference/`** are
   review-gated (Principle II + Reviews policy).
7. **Classifier workflows**, when present, declare the class mapping, exclude
   target-related phase columns from features, select mapping-appropriate
   metrics, expose mapping through CLI/config, and keep classifier artifacts
   separate from canonical regressor artifacts.
8. **Interpretability workflows**, when present, identify the model target,
   sample source, feature matrix, fitted feature order, aggregation metric, and
   deterministic artifact inputs used for comparison/reporting.
9. **Spec Kit evidence artifacts**, when present, separate Evidence Status,
   Validation Status, and Acceptance Readiness, and do not treat checked tasks as
   validation proof.

Any failure on items 1–9 MUST be either resolved before proceeding or
documented in the plan's Complexity Tracking table with explicit justification.

## Governance

This constitution supersedes ad-hoc conventions captured in CLAUDE.md, project
memory, or individual notebook comments. Where this document and other
guidance disagree, this document wins; the conflicting guidance MUST be
updated to match.

Amendments follow semantic versioning:

- **MAJOR**: Backward-incompatible removal or redefinition of a principle
  (e.g., removing the temporal-integrity guarantee, abandoning the `ipcch`
  package, changing the canonical cumulative-phase target structure).
- **MINOR**: Addition of a new principle or materially expanded guidance
  (e.g., adding an experimental model workflow, adding a metric, changing the
  phase-conversion threshold, adding a new mandatory section).
- **PATCH**: Wording clarifications, typo fixes, non-semantic refinements.

Amendments MUST update `LAST_AMENDED_DATE`, increment `CONSTITUTION_VERSION`
according to the rules above, and re-run the consistency-propagation checklist
against `.specify/templates/*.md` and CLAUDE.md.

Compliance is verified by the Constitution Check gate in
`.specify/templates/plan-template.md` and by reviewers on PRs that touch
tracked pipeline inputs.

**Version**: 1.5.0 | **Ratified**: 2026-05-12 | **Last Amended**: 2026-06-03
