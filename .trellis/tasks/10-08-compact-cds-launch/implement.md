# Implementation plan: compact_cds_launch_v1

Status: approved for execution by the user's2026-10-09 supervisor/executor goal request. All steps below are planned until evidence is recorded. A checkbox records work sequencing only, not validation evidence.

## Scope and context

Use `prd.md`, `design.md`, expected CSVs and the curated implement/check JSONL manifests. Keep the current branch. After explicit final-review approval, use the requested supervisor/executor workflow with Claude Opus5.5 and1M context; verify the actual Claude/Herdr executor identity and supported model/context before a handoff. Report unavailable requested capabilities rather than substituting another model. Do not reuse another task's execution approval or invent executor state. No additional audit enrollment is part of this plan.

Read `trellis-before-dev` and current backend quality guidance before code. Use Windows Git and the existing PATH shim for Trellis subprocesses. Run GitNexus impact before editing existing symbols; report high/critical scope. Preserve frozen compact helpers/annual runner/configs. Main session owns design decisions, review and final verification; the implementation/check manifests carry the approved spec/research.

## Ordered stages

### 1. Source/runtime and contract preflight — R1–R10,R15

- [ ] Verify all pinned source, manifest, input, ledger, helper and config bytes. Snapshot the geometry sidecars, current Git/runtime identity and source-role inventory.
- [ ] Check frozen modeling Python/packages and separately snapshot the existing CDS decoding environment. Report unavailable packages/interpreters; no silent substitutions or automatic dependency install.
- [ ] Check complete April cohort6188/53-country mapping, comprehensive population/static source, static parity on2774 compact April rows and canonical identifier coordinates. Preserve4880 popdensity NA, six zero populations, code gaps and allregion0..8.
- [ ] Copy approved spec/contract artifacts into the new external version root for archive-safe references. Validate the five ordered schema projections296/308; no product code/data build has happened during planning.

### 2. Weather source and October completion — R7–R9

- [ ] Add the narrowly scoped CDS reader/request/aggregation functions and preprocessing CLI. Existing raw/processed source files are read-only references; create only versioned new outputs.
- [ ] Run its weather-only stage in the CDS environment without importing compact/model code. Write the cube and provenance before handing their explicit paths to the assemble-only stage in the frozen model environment; do not construct compact matrices with CDS NumPy2.4.6.
- [ ] With later execution approval, request April-init system51 ensemble monthly anomalies for true May–September (lead2..6). Save public request parameters, retrieval identities and file hashes; credentials stay in home config.
- [ ] Retrieve only needed original-frequency forecast/hindcast fields for October and overlapping September, including precipitation boundary fields and complete temperature samples. Validate actual system/member/year/step/grid metadata and full1993–2016 reference support.
- [ ] Freeze monthly sampling/member/reference and packing-error validation bounds before evaluating overlap. Construct October model anomalies; require overlap agreement with the official September anomaly within independently justified decoding/reduction bounds. Stop on unexplained differences or missing data.
- [ ] Extract at the existing fixed points; convert units, resolve true statistical months, and write one area×month cube with source/baseline/method/support metadata. Verify all6188×6×2 launch cells finite; never fill missing future weather with actuals or later init.

### 3. Launch matrices — R3–R6,R10

- [ ] Select fitting rows from current compact inputs using normalized-share validity and strict March label cutoff. Assert identical ordered keys, targets/weights and paired baseline prefixes.
- [ ] Build inference keys for all three targets from the complete April cohort. Use April static/context and compact at-origin dynamics/season/IDP; filter IPC observations through March before generating histories and changes.
- [ ] Generate target-calendar dummies;2027 has existing year columns0 and metadata flag. Keep missing static/other source values; reject O beyond source-grid ends.
- [ ] Substitute CDS only into the12 oracle inference literals; save matrices and keyed history/IDP/season/weather ledgers. Prove paired prefix equality and same-origin noncalendar equality across horizons.
- [ ] Run focused unit/synthetic CLI tests before production fitting; validate-only must not fit, retrieve weather or create model artifacts.

### 4. Five unique fits and raw predictions — R2,R4,R15

- [ ] Add the specific compact launch CLI/module using existing canonical `_fit_model` and origin weights, explicit literal features and existing normalization/classification helpers.
- [ ] Fit sharedH0 first, measure memory/time, then remaining four sequentially. Use42/24/0.2/16 and pinned independent P3 config. No parallel heavy test/fitting pools or extra evaluation runs.
- [ ] Save20 UBJs, exact fitted feature order, fitting keys/targets/weights, inference matrices/raw predictions and complete fingerprints. Keep unrounded raw values; fail nonfinite predictions; no zero-fill schema alignment or prediction-based drops.
- [ ] Resume only complete matching artifacts. Reload every booster, confirm schemas and full prediction replay atol1e-6/rtol0, with identical discrete classifications.

### 5. Population tables and maps — R11–R14

- [ ] Implement approved disjoint clip/normalization reporting, common April population/country factors, raw/capped counts, repair flags and four aggregation levels. Country join uses pinned names, not guessed ISO codes; region joins onarea_id, including0..8.
- [ ] Compute four paired difference tables, sharedH0 zero differences and country cap ledger. Population denominators are identical across targets/arms.
- [ ] Render the planned five categorical maps,2×3 repaired P3+ comparison and1×2 repaired P3+ difference map; record exact CSV columns/units/paths/hashes/joins. Preserve old rendering helpers and do not alter raw classification to match repaired shares.
- [ ] Write verified actual-input codebook from all20 fitted lists, launch report and complete output inventory. No scores/bootstrap/SHAP or actual panels.

### 6. Independent acceptance and completion — A1–A9

- [ ] Independently recompute all repaired shares, population scaling/counts, country/region/global totals and paired differences from saved raw predictions and source population, without merely calling the production reporting helper twice.
- [ ] Check share/count arithmetic with round-trip reads: shares atol1e-12, people/count sums atol1e-6 and rtol1e-12; match undefined masks, cohorts and denominator identities exactly. Compare every continuous/difference plotted value to its table; categorical flags equal raw-derived phase>=3.
- [ ] Verify all20 replays, complete/source-safe inventories, coverage, helper/config/old-artifact nonchanges and reporting terminology. Persist keyed evidence and limitations; incomplete retrieval/build/replay is not acceptance.
- [ ] Run appropriate focused tests once; expand only for demonstrated concerns. Review changed scope and GitNexus detect_changes before any authorized commit. Keep PROGRESS.md as an execution ledger after start, not approval authority.

## Planned commands (entrypoints will be created in implementation)

Modeling `PY=/home/swl007007/.venvs/ipcch-geo/bin/python`; decoding `WEATHER_PY='<D>/CDS_API/.venv/bin/python'`; `INPUT_ROOT='<A>/model_ready/compact_cds_launch_v1'`. These are descriptive task variables, not changes to HOME/CODEX_HOME.

1. `$WEATHER_PY scripts/preprocessing/build_compact_cds_launch_inputs.py --weather-only --download-weather --input-root "$INPUT_ROOT"` after execution approval and source/request checks. This stage only obtains/decodes/aggregates weather and records its cube/provenance.
2. `$PY scripts/preprocessing/build_compact_cds_launch_inputs.py --assemble-only --weather-cube "$INPUT_ROOT/cds_weather_cube.csv" --input-root "$INPUT_ROOT"` constructs compact fitting/inference matrices under the frozen modeling environment; it must not retrieve weather.
3. `PYTHONPATH=src $PY -m pytest tests/unit/test_cds_launch_weather.py tests/unit/test_compact_launch.py tests/smoke/test_compact_cds_launch_cli.py -q` on synthetic fixtures, before heavy fitting. The weather unit tests exercise pure arithmetic/metadata with tiny fixtures and must not require ecCodes/cfgrib/xarray. Actual GRIB decoding and provider overlap checks run in the CDS stage and emit their own machine-readable evidence; model-environment pytest alone cannot certify them.
4. `$PY scripts/modeling/run_compact_cds_launch.py --input-manifest "$INPUT_ROOT/compact_cds_launch_v1_manifest.json" --validate-only` after completed weather/input build and focused tests.
5. `$PY scripts/modeling/run_compact_cds_launch.py --input-manifest "$INPUT_ROOT/compact_cds_launch_v1_manifest.json" --approve-training` for the fixed five-run plan, raw predictions and reporting, only after validation passes.

The CLI must preserve existing complete-run resume behavior and perform final independent saved-artifact verification; no new generic jobs/runner framework is needed. Detailed weather request/temporal quantization checks may stop the data stage before fitting without changing its approved scope. Do not execute these commands during planning.
