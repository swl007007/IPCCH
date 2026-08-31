<claude-mem-context>
# Memory Context

# [IPCCH] recent context, 2026-08-25 3:16pm EDT

Legend: 🎯session 🔴bugfix 🟣feature 🔄refactor ✅change 🔵discovery ⚖️decision 🚨security_alert 🔐security_note
Format: ID TIME TYPE TITLE
Fetch details: get_observations([IDs]) | Search: mem-search skill

Stats: 50 obs (20,932t read) | 458,352t work | 95% savings

### May 28, 2026
187 9:51p 🔵 Root Cause of `codex_apps` MCP Failure: Plugin-Provided Server with No Workspace Selected
188 9:52p 🔵 `codex doctor` Reveals Network Sandbox Blocks ChatGPT Backend — Root Cause of `codex_apps` MCP Failure
191 " ✅ `github@openai-curated` Plugin Removed to Eliminate `codex_apps` MCP Startup Error
193 " ✅ `codex_apps` Tool Cache Backed Up After Plugin Removal
190 9:53p 🔵 Root Cause of OOM: load_comprehensive_source Uses Plain pd.read_csv with No dtype Optimization
192 " 🔵 launch_nowcasting.py Model Architecture: Cumulative XGBoost with Time-Decay Weighting
195 " 🔵 IPCCH Launch Config Constants and CSV Column Structure Confirmed
196 " 🔴 OOM Fix: Two-Pass Row-Filter CSV Load in load_comprehensive_source
194 9:54p 🔵 Feature Pipeline Makes Multiple Full DataFrame Copies, Compounding OOM Risk
197 9:55p 🔵 pytest Fails to Import ipcch Module Without src/ on PYTHONPATH
199 9:56p 🔵 IPCCH pytest requires PYTHONPATH=src to resolve ipcch module
200 " 🔵 launch_nowcasting validate-only run: feature schema mismatch between train and April 2026 test set
201 9:58p 🟣 Launch Nowcasting 2026-04 Pipeline Executed End-to-End
198 " 🔴 All 16 Unit Tests Pass After OOM Fix — PYTHONPATH=src Required
202 10:13p 🟣 April 2026 IPC-CH Nowcasting Run Completed Successfully
203 10:20p 🔵 April 2026 IPC-CH Nowcast Prediction Distribution: Phase 3 Dominates at 81%
204 " ✅ Project Memory File Created for Launch Nowcasting 2026-04 Runbook
205 10:21p ✅ MEMORY.md Updated with Launch Nowcasting 2026-04 Pointer
206 10:23p 🔵 Comparison and Map Inputs Both Available for April 2026 Actuals
207 " 🔵 launch_comparison.py: Coverage-Aware April-Only Comparison Module Architecture
208 10:24p 🔵 launch_visualizations.py: Two-Panel Spatial Join Design with Hard-Fail on Duplicate Keys
209 10:25p 🔵 Shapefile Has No area_id Column — Spatial Join Will Fail Without Remapping
210 " 🔵 build_map() Delegates Boundary Loading to arm Module — admin_code Remapping May Happen There
211 10:26p 🔵 admin_code → area_id Remapping Handled Automatically by load_spatial_boundaries() via AREA_ID_ALIASES
212 " 🔵 April 2026 Actual Coverage: 2,774 of 6,188 Areas Labeled (44.8%) — All IDs Match Perfectly
213 " 🟣 Mode 3 Comparison and Map Run Launched as Background Process
214 " 🟣 Mode 3 Report and Map Completed Successfully — Comparison and Choropleth Outputs Written
215 " 🟣 Full Mode 3 Output Set Confirmed: Comparison CSVs, Confusion Matrix, and Crisis Map PNG Written
216 10:27p 🔵 April 2026 Nowcast Comparison Metrics: High Phase 3+ Recall (94%) but Zero Phase 4 Detection
217 10:30p 🔵 contextily Zoom Level 21 Warning When Mapping Labeled-Only Actual Subset
218 10:43p 🟣 Final Two-Panel Crisis Map PNG Confirmed — 1.17 MB, Correct Partial Coverage Reflected
219 10:44p ✅ Project Memory Runbook Updated with Complete Mode 3 Comparison and Map Gotchas
220 10:48p 🔵 alert_risk_maps.py Basemap Pattern: EPSG:3857 Reproject + CartoDB.Positron at alpha=0.4
221 " 🔵 alert_risk_maps.py Uses Africa-Constrained Extent Calculation to Prevent Basemap Over-Zoom
222 10:49p 🔵 launch_visualizations.py _panel() Missing EPSG:3857 Reprojection and Africa Extent Filter vs Reference
224 " 🔴 Basemap Fix Verified: zoom-level-21 Warning Eliminated After EPSG:3857 Reproject
223 " 🔴 launch_visualizations.py _panel() Fixed: EPSG:3857 Reproject + Africa Extent Filter Added
225 10:52p 🟣 Crisis Map PNG Now Includes Basemap Tiles — File Size Increased from 1.17MB to 1.89MB
S38 Threshold sweep diagnostic on April 2026 nowcast — investigating whether lowering th from 0.20 to 0.12 improves Phase 4 detection (May 28, 10:52 PM)
226 10:53p 🔵 Prediction Output CSV Schema: Dual Prediction Columns (worse + cumulative) Plus Full Metadata
227 " 🔵 reconstruct_phase_from_cumulative: Last-Phase-Wins Threshold Algorithm — Phase 4 Requires phase4_worse_pred ≥ 0.2
228 10:54p 🔵 Threshold Sweep Diagnostic: Phase 4 Recall Reaches 38% at th=0.10 but Overall Accuracy Drops to 39%
S39 Threshold sweep in the upward direction (0.22/0.25/0.30+) to reduce Phase 3 over-prediction in April 2026 nowcast (May 28, 10:55 PM)
229 11:01p 🔵 High-Threshold Sweep: th=0.25 Maximizes Macro-F1 (0.244); th=0.30 Maximizes Accuracy (0.573)
230 " 🔵 Per-Phase Thresholds Outperform Global — 0.20/0.30/0.10/0.08 Achieves Best Macro-F1 (0.284) with Phase 4+ Recall 38%
231 11:03p ✅ Project Memory Updated with Full Threshold Diagnostic Summary and Per-Phase Recommendation
S41 Stage and commit all changes and merge into main branch (May 28, 11:03 PM)
232 " 🟣 Alternative th=0.25 Prediction Set and Full Mode 3 Report Generated in Separate Output Directory
233 11:05p 🟣 th=0.25 Alternative Product Fully Generated: 17-File Output Set with Map PNG and Comparison CSVs
S40 Re-generate the crisis map and comparison outputs at th=0.25 to show the improved phase distribution compared to canonical th=0.20 (May 28, 11:05 PM)
S43 Session start — user greeted with "hello" (May 28, 11:05 PM)
234 11:09p 🔵 Feature Branch 004 Git Status: 13 New Source Files + 3 Modified Files to Commit; Results Directories Gitignored
235 " 🔵 AGENTS.md Is a Claude-Mem Context File — Should Likely Be Excluded from Commit
236 11:10p 🔵 AGENTS.md Is Untracked Claude-Mem File Not Covered by .gitignore — Must Be Excluded from Commit
S44 Session start — user said "hello" (May 28, 11:22 PM)
S42 Session start — user greeted with "hello" (May 28, 11:22 PM)
S45 Session start - user said "hello" (May 28, 11:28 PM)
S46 Run full April 2026 forecast-weather launch pipelines for 3m, 6m, and 12m scopes after validating the historical-weather fallback (May 28, 11:49 PM)
### Jun 2, 2026
237 5:07p 🔵 IPCCH completed raw data file location identified
S47 Validate and run full April 2026 forecast-weather launch pipelines for scopes 3m, 6m, and 12m after implementing the historical-weather fallback (Jun 2, 5:43 PM)
**Investigated**: Scope 12 validate-only output was observed, along with task state transitions and the launch of full production background jobs for scopes 3, 6, and 12. The commands used the real comprehensive deep-feature CSV, forecasted weather mode, the IPCCH admin geometry shapefile, --approve-training, --overwrite, and shared output/report roots.

**Learned**: Scope 12 forecast-weather validate-only completed successfully with status=validated, train_rows=49538, april_rows=6188, and features=406. As with other scopes, it emitted a non-fatal Train/X_test feature schema warning where only_train contains month dummy columns and year dummy columns through 2022, while only_xtest is empty. This remains expected because model-aligned reindexing handles missing X-test dummy columns.

**Completed**: Task 10 was marked completed, indicating the validation phase finished. Tasks 11, 12, and 13 were moved to in_progress for the full production pipeline phase. Full background production runs were started for scope 3 with backgroundTaskId bjvp1o15u, scope 6 with backgroundTaskId b7oz792er, and scope 12 with backgroundTaskId bvip9ju8p. Earlier completed work includes the forecast-weather training proxy fallback to assembled_IPCCH/raw/IPCCH_2026_completed.csv, passing unit tests with 35 passed, and successful validate-only runs for the relevant scopes.

**Next Steps**: Monitor or wait for the three background production jobs to complete. After completion, inspect each scope output directory and corresponding report directory, then summarize run summaries, predictions, validation summaries, feature schema, model-aligned X-test files, maps, markdown reports, runtime/resource usage, and any warnings or failures.


Access 458k tokens of past work via get_observations([IDs]) or mem-search skill.
</claude-mem-context>

# Project Guidance Addendum

## Interpretability and SHAP Workflows

Interpretability artifacts intended for comparison or reporting must record the model target, sample source, feature matrix construction, fitted feature order, aggregation metric, and relevant input artifact paths in machine-readable metadata. Comparison helpers should combine artifacts from explicit paths or metadata-recorded paths, not unconstrained recursive directory scans.

Nowcasting grouped SHAP is optional and enabled with `--compute-grouped-shap` in `scripts/modeling/run_launch_nowcasting_2026_04.py`. It currently supports train-and-predict runs only, explains only the fitted `phase3_worse` cumulative regressor, and must use the exact phase-3 training feature matrix with the fitted feature order. It groups features by the six-category crosswalk plus a seventh group named exactly `weather forecast`; runtime weather forecast proxy features take precedence before crosswalk matching. Unmatched features are diagnostics-only and must not be assigned to an `other` fallback group unless a future spec explicitly changes that. Scope comparisons use canonical order `0m`, `3m`, `6m`, `12m`.

## Spec Kit Artifact Alignment

When updating Spec Kit artifacts, use the current implementation plus explicit user design clarifications as the baseline. Record implementation-vs-design drift in `evidence.md` and `task-evidence-trace.md`; do not change `tasks.md` checkboxes as proof of implementation or validation. `Evidence Status: Ready` means the evidence artifact is ready for grounding only; if `Validation Status` is `Not Executed`, do not claim tests, CLI checks, artifact generation, or final acceptance were validated.

Current feature baselines to preserve: Spec002 alert-risk maps are single-scope CLI runs (`--scope global` or an ISO3 such as `SOM`) and global/Somalia deliverables require separate invocations; Spec005 launch scopes are `0`, `3`, `6`, and `12` months, with April 2026 + `12m` targeting April 2027; Spec006 phase-3 SHAP runs one selected `--fs` per invocation, and full four-scope 96-row/four-heatmap deliverables are assembled across `fs0`/`fs1`/`fs2`/`fs3` runs or downstream aggregation.