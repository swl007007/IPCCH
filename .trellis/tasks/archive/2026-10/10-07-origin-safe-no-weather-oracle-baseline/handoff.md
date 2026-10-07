# Approved execution handoff — idle Herdr Claude

User approval on 2026-10-07, after the final planning summary: “批准，交给herdr pane另一个空闲的claude进入执行。” This authorizes the implementation, six new global runs, saved-prediction regional evaluation and audited lifecycle specified here. Do not repeat planning/task-creation consent. Prior research/proposal notes saying approval was pending are historical snapshots, superseded by this approval and current PRD/design.

## Identity and first action

- Exact registered repo spelling: `/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/Google fund/Analysis/2.source_code/Step5_Geo_RF_trial/IPCCH`.
- Task directory: `.trellis/tasks/10-07-origin-safe-no-weather-oracle-baseline`; task ID: `origin-safe-no-weather-oracle-baseline`.
- Selected live executor: Herdr `wP:p3`, Claude Opus5.5, session `87476d84-19ad-495a-916d-8c43808150f5`, terminal `term_65d3f9b52ca837`. Confirm these match your actual session. The earlier Fable5.1 discussion session and historical registered Claude are not this executor.
- Operator will commit these planning artifacts, register this executor and boot the audit controller before dispatching you. Inspect `trellis-audit --repo '<exact repo above>' status`; verify registration, no conflicting active run and HEAD containing this approved plan. Then YOU run `trellis-audit --repo '<exact repo above>' start origin-safe-no-weather-oracle-baseline`. Do not invoke native task.py start/archive or invent a baseline. If start is ambiguous, inspect durable state before any retry. Record run ID, executor, base_sha and task in_progress in PROGRESS.md.
- Read the real AGENTS.md, root CONTEXT.md, both context JSONLs and their entries, then prd.md, design.md, implement.md. The task remains planning until the bound wrapper start; approval has already been granted. Use trellis-before-dev and required GitNexus impact before symbol edits.

## Frozen scientific scope

1. Reference `origin_safe_climate_idp_v1/climate_safe_history_idp` already excludes oracle and retains new shared monthly climate, completed GS, safe IPC history and national IDP. Verify then reuse H0/H3/H6/H12; never refit automatically or write into old outdirs. Preserve original training fingerprints separately from current verification identity.
2. New namespace `origin_safe_weather_oracle_v1`. Exactly two new arms (raw oracle; raw+B6) at H3/H6/H12: six sequential runs, 24 annual batches, 96 regressors. Seed42, fixed configs/strict annual protocol/common28,205 keys. H0 is one reference only. No tuning, extra seeds or A4 runs.
3. Two shared monthly weather anomalies at O+1..O+min(H,6), interpreted as perfect forecasts assumed available at O. Keep actual observation month separate. No exception for future IPC/IDP/GS/history. H12 gets only the first six months.
4. B6 is F, B=(existing R+F)/2 and safe-history IPC3+-gated Q for each variable. Full future completeness for F; full past too for B; Q requires both F and safe history. Missing F with zero gate is still NaN. Do not alter inherited baseline cells/missingness, drop rows or add diagnostics as predictors. Follow design formulas, exact schema/order and ledgers.
5. Region3 is selected by data/reference/area_id_country_region_mapping.csv area_id join, not SADC/country whitelist. Compare the 3,234 saved GLOBAL-model prediction rows annually and pooled. Regional addendum invokes no training pipeline/refits/local models.
6. Country-stratified whole-area paired bootstrap, 2,000 PCG64(seed42) draws, shared multiplicities across arms/horizons/metrics. FINAL G1/B and G2/A: conditional 95% percentile intervals from jointly valid draws, at least1,000 required, otherwise unavailable. Disclose conditional interpretation and invalid counts/fractions, save all original draws and joint masks, no replenishment/zero substitution. Keep global F2/R² definitions; old Somalia metric and CI helpers differ at boundaries.

## Execution and acceptance

Use `/home/swl007007/.venvs/ipcch-geo/bin/python` with frozen package/config/source hashes. Work through implement.md; keep PROGRESS.md current. Primary preflight is parent value/label/key/weight parity and all-four-year model replay; failure stops dependent runs and is reported, not patched by changing the cohort or fitting protocol. New suite/verifier paths must be isolated from old defaults. Reuse existing fitter/metrics/artifact helpers without a new framework.

Produce baseline-first global and regional reports, the three contrasts, coverage and complete provenance/evidence for AC1–AC6. Run the focused checks and all specified replay/verification. Before commits use GitNexus detect_changes and exclude unrelated AGENTS.md edits. Commit all relevant nonignored work; no push authorization is implied. At completion YOU run trellis-audit close from this bound session, inspect job/result, and follow controller remediation/re-audit if needed. A queued/launched job or archived task is not an accepted audit. Historical waived/major results remain distinct; never manually clear gates.

Start now after reading the contracts and lifecycle verification. First report the actual audit run ID/base_sha and next execution stage in your pane, then continue implementation without waiting for another operator prompt. If a genuine scientific mismatch or lifecycle blocker appears, preserve evidence and report it explicitly instead of expanding the scope.
