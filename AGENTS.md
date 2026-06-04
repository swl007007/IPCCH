<claude-mem-context>
# Memory Context

# [IPCCH] recent context, 2026-05-28 9:53pm EDT

Legend: 🎯session 🔴bugfix 🟣feature 🔄refactor ✅change 🔵discovery ⚖️decision 🚨security_alert 🔐security_note
Format: ID TIME TYPE TITLE
Fetch details: get_observations([IDs]) | Search: mem-search skill

Stats: 50 obs (21,854t read) | 903,786t work | 98% savings

### May 12, 2026
S16 Build 2025 CH centroid CSV: install geopandas, merge dec25 Excel with GeoJSON to get polygon centroid lat/lon, filter current/2025, progressive PCODE join adm3→adm2→adm1 (May 12, 2:11 PM)
S15 Initialize CLAUDE.md documentation for the IPCCH data subdirectory of an IFPRI food security research project (May 12, 2:11 PM)
S17 Build 2025 CH centroid CSV by merging dec25 Excel with GeoJSON centroids — pipeline complete, outputs verified, duplicates diagnosed (May 12, 2:55 PM)
S29 Validate generated tasks and analyze/remediate Spec Kit findings for 2025 alert risk maps (May 12, 2:56 PM)
139 5:26p ⚖️ ML Pipeline Standard Folder Structure Reorganization Planned
140 5:27p 🔵 IPCCH Project Existing Folder Structure Mapped
141 " 🔵 IPCCH Project Architecture and Dependency Graph Fully Documented
142 " 🔵 Regional Model Data Sparsity Problem Documented in ISSUES_FIXED.md
143 5:28p 🔵 Hardcoded Absolute Windows Paths Found in Multiple Python Scripts
144 " ⚖️ ML Pipeline Folder Reorganization Plan Formulated via Subagent Exploration
145 " 🔵 Git Status Expanded: settings.local.json Also Modified
146 5:29p 🔵 IPCCH Project: Comprehensive Dependency Audit Before ML Pipeline Reorganization
147 " ⚖️ ML Pipeline Reorganization Blocked: Zero Code Edits Constraint Cannot Be Satisfied
148 5:34p ⚖️ ML Pipeline Folder Structure Reorganization Requested
149 5:39p 🔵 IPCCH Food Security ML Project: Current Structure and Critical Dependency Risks
150 " ⚖️ 7-Phase ML Pipeline Reorganization Plan Produced for IPCCH Project
151 5:40p ✅ ML Pipeline Reorganization Plan Saved to Claude Plans Directory
152 " ⚖️ IPCCH ML Pipeline Folder Reorganization Plan Created
153 " ⚖️ IPCCH ML Pipeline Folder Reorganization Plan Created
154 5:50p 🔵 food_crisis_functions Import Dependency Scope Mapped
155 " 🔄 food_crisis_functions Converted to Installable ipcch Package
156 5:51p 🔄 All food_crisis_functions Imports Updated to ipcch Package Path
157 5:52p 🔵 Stale Comment in run_region_models.py References Old Module Name
158 " 🟣 Phase 1 Import Migration Verified Complete
159 " 🔄 Stale food_crisis_functions Comment Removed; Zero Old Import References Remain
160 " 🔵 Hard-coded Path Inventory Completed Before Phase 2 Moves
161 " 🔄 Config JSONs and Reference CSV Moved to Canonical Locations
162 5:53p 🟣 Path Resolution Module and Example Config Added to ipcch Package
163 " 🔄 run_region_models.py Gains Self-Locating PROJECT_ROOT and ipcch.paths Import
164 5:54p 🔄 run_region_models.py CLI Defaults Updated to Use CONFIG_DIR; --lat-lon-file Made Required
165 " 🟣 ipcch.paths Gains external_path() with Local Config Override and Hardened Defaults
166 " 🔴 paths.example.json Relative Paths Corrected to Match 3-Level Directory Depth
167 " 🔄 run_region_models.py --lat-lon-file Restored to Optional with external_path() Default
168 5:55p 🔄 cleanlab_label_analysis.py Updated with Self-Locating PROJECT_ROOT and ipcch.paths Imports
### May 27, 2026
170 2:05p ⚖️ 2025 alert risk maps planned as post-processing workflow
171 " ⚖️ Alert map semantics use IPC phase 3 crisis thresholds
172 " ⚖️ Prediction records require latest 2025 row per area_id
173 " ⚖️ Alert risk map workflow fails on ambiguous inputs and incomplete joins
174 " 🔵 2025 alert risk maps CLI contract defined expected inputs and outputs
S30 Resolve Spec Kit analyze findings for feature 002-2025-alert-risk-maps and continue post-remediation analysis (May 27, 2:31 PM)
S27 Generate and validate Spec Kit tasks for 2025 alert risk maps (May 27, 2:31 PM)
S28 Analyze Spec Kit artifacts and report consistency/coverage for 2025 alert risk maps (May 27, 2:31 PM)
S31 Post-remediation Spec Kit analysis for 2025 alert risk maps after resolving analyze findings (May 27, 2:35 PM)
S32 Complete post-remediation Spec Kit artifact analysis for 2025 alert risk maps (May 27, 2:39 PM)
### May 28, 2026
175 9:35p 🟣 April 2026 Global Nowcasting Launch CLI Implemented
176 " 🔵 Launch Environment Requires venv — paths.local.json Missing
177 " 🔵 ipcch-geo Venv Has Both XGBoost and GeoPandas — Use for Full Launch with Map
179 " 🔵 Prior Validate-Only Run Exists — Output Artifacts Conflict Without --overwrite
180 9:38p 🔵 Output Directory Contains Only Partial Validate-Only Artifacts — No Training Run Yet
178 9:40p 🔵 Launch CLI Successfully Imports and Runs with ipcch-geo Venv
182 " 🔵 IPCCH Nowcasting Launch Directory — Partial Output State
183 " 🔵 Launch Nowcasting Script Killed OOM Loading 5 GB CSV
181 9:41p 🔵 Validation Summary Confirms 49,538 Training Rows and 6,188 April 2026 Prediction Targets
189 9:42p 🔵 Launch Script Killed by OOM (Exit 137) on 5 GB CSV Load
S33 Launch the nowcasting_2026_04 pipeline using the newly implemented run_launch_nowcasting_2026_04.py script (May 28, 9:42 PM)
184 9:51p 🔵 MCP `codex_apps` Startup Fails with `invalid_workspace_selected` (403)
185 " 🔵 Codex `codex_apps` MCP Tool Cache and Config Location Identified
186 " 🔵 `codex_apps` GitHub MCP Was Previously Functional — Used to Ship fs0 Pipeline PR
187 " 🔵 Root Cause of `codex_apps` MCP Failure: Plugin-Provided Server with No Workspace Selected
188 9:52p 🔵 `codex doctor` Reveals Network Sandbox Blocks ChatGPT Backend — Root Cause of `codex_apps` MCP Failure

Access 904k tokens of past work via get_observations([IDs]) or mem-search skill.
</claude-mem-context>

# Project Guidance Addendum

## Interpretability and SHAP Workflows

Interpretability artifacts intended for comparison or reporting must record the model target, sample source, feature matrix construction, fitted feature order, aggregation metric, and relevant input artifact paths in machine-readable metadata. Comparison helpers should combine artifacts from explicit paths or metadata-recorded paths, not unconstrained recursive directory scans.

Nowcasting grouped SHAP is optional and enabled with `--compute-grouped-shap` in `scripts/modeling/run_launch_nowcasting_2026_04.py`. It currently supports train-and-predict runs only, explains only the fitted `phase3_worse` cumulative regressor, and must use the exact phase-3 training feature matrix with the fitted feature order. It groups features by the six-category crosswalk plus a seventh group named exactly `weather forecast`; runtime weather forecast proxy features take precedence before crosswalk matching. Unmatched features are diagnostics-only and must not be assigned to an `other` fallback group unless a future spec explicitly changes that. Scope comparisons use canonical order `0m`, `3m`, `6m`, `12m`.

## Spec Kit Artifact Alignment

When updating Spec Kit artifacts, use the current implementation plus explicit user design clarifications as the baseline. Record implementation-vs-design drift in `evidence.md` and `task-evidence-trace.md`; do not change `tasks.md` checkboxes as proof of implementation or validation. `Evidence Status: Ready` means the evidence artifact is ready for grounding only; if `Validation Status` is `Not Executed`, do not claim tests, CLI checks, artifact generation, or final acceptance were validated.

Current feature baselines to preserve: Spec002 alert-risk maps are single-scope CLI runs (`--scope global` or an ISO3 such as `SOM`) and global/Somalia deliverables require separate invocations; Spec005 launch scopes are `0`, `3`, `6`, and `12` months, with April 2026 + `12m` targeting April 2027; Spec006 phase-3 SHAP runs one selected `--fs` per invocation, and full four-scope 96-row/four-heatmap deliverables are assembled across `fs0`/`fs1`/`fs2`/`fs3` runs or downstream aggregation.