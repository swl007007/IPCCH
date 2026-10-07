# Evidence: origin_safe_weather_oracle_v1 (task origin-safe-no-weather-oracle-baseline)

Evidence status: executed 2026-10-07 by the bound executor (Herdr wP:p3, Claude Opus5.5, session
87476d84-19ad-495a-916d-8c43808150f5, terminal term_65d3f9b52ca837). Audit run `c00f3e7fe825490ca68ca17fa6be49f9`,
base_sha `1d24ce26c8a7be7797f7eba4bf4488df74ba33a6`. Acceptance requires the independent close audit; this file is
not that acceptance. Large data/results/reports are git-ignored; their paths and SHA256 are pinned here.

Roots: `MR` = `Analysis/1.Source Data/assembled_IPCCH/model_ready`; `RES` = `results/experiments/origin_safe_weather_oracle_v1`;
`REP` = `reports/origin_safe_weather_oracle_v1`; reference runs `results/experiments/origin_safe_climate_idp_v1/runs/climate_safe_history_idp/{0,3,6,12}m`.

## Code identity

Implementation commit `e657b41` (inputs built from, and all six runs fitted with, exactly these file versions: builder
manifest `code_sha256` and every run's `fingerprint_payload.code_sha256` / `oracle.code_sha256` equal the blobs at
`e657b41`). Verifier ledger-diagnostic addition and the region3 script were added after `e657b41` and committed with
this evidence; they read artifacts only. Runtime `/home/swl007007/.venvs/ipcch-geo/bin/python`: Python 3.12.3,
NumPy 2.4.4, pandas 3.0.3, scikit-learn 1.8.0, XGBoost 3.2.0 (checked by the verifier against frozen values).

## AC1 — reference reuse (R1)

- Frozen hashes verified: parent manifest `3b479c80…a209bf`, configs `37423006…dd76` / `cdc0e55a…317b`, mapping
  `18ab5099…611d`, country lookup `e2baf6ae…c44c90`, eval keys `f0193c14…2d0e0f` (28,205; 5,599/6,064/5,127/11,415).
- Preflight before any new fit: `verify_origin_safe_weather_oracle.py --stage reference` → exit 0, `passed: true`,
  4 runs × 4 years, 96 artifacts re-hashed, 64 models reloaded (max |Δprediction| 0.0), fit keys/ages/weights
  (atol 1e-15), normalized targets (independent normalization vs runner, atol 1e-12), cohort/truth, class rule,
  metric replay (atol 1e-12, identical undefined masks). `RES/reference_preflight/verification_summary.json`
  sha256 `17bcee1b9ef1e082554216e4bdbfb9141969b84c3cb97984eb4c25637c6866ef`.
- Final `--stage all` re-verified the reference with the final verifier code (below). Original training identities
  (fingerprints f1800fa6…/3928eb45…/c8a08525…/e52431b0…, code sha 5c197649…/3c0c7b93… that predate A01–A04) are
  recorded under `reference_original_training_identity`, separate from `current_verification_identity`.
- No reference artifact was written: reference runs were only read; all new outputs live in the new namespace and the
  CLI refuses oracle out-dirs inside `origin_safe_climate_idp_v1`. Artifact inventory with recorded vs current SHA256:
  `RES/verification/artifact_inventory.csv` (`d6215518…9ae843`).

## AC2 — schemas, ledgers, boundaries (R2–R3)

- Manifest `MR/origin_safe_weather_oracle_v1/origin_safe_weather_oracle_v1_manifest.json` sha256
  `525525ece38584277c74d4f8e8f7265c394fd386462c7f75cf934325587f8cb6`; datasets/ledgers:
  H3 `9ad7200b…01eb8c` / `638069fa…b763fe`; H6 `c5b6dc33…c0358e` / `d330e685…7314a0`; H12
  `74b2c42a47fa526e9f6b9de6375e375f713e8e6f9972570e9c3290a8a942a479` / `dd6e9526cffe565658b434611d32c4b6a84a87398c79fd70918187e0f22d3dcf`.
  No H0 dataset (`reference_only_horizons: [0]`).
- Exact counts 876/882 (H3), 882/888 (H6), 666/672 (H12): parent list + 6/12/12 raw + 6 B6, order checked by builder,
  CLI gate and verifier. Ledgers record origin, assumed availability month (= O), realized observation months, past
  window, per-variable finite counts, history_1 source month/staleness/value.
- Builder checks (`logs/build_inputs.log`): every parent column re-read with round-trip parsing `DataFrame.equals` the
  saved parent; saved R equals the O−m+1..O mean where complete (max |diff| 5.7e-14); post-window perturbation (cutoffs
  2022-06, 2024-03) changed 0 new cells, including 3,728 H12 rows whose O+7..O+12 were perturbed; past perturbation
  changed 0 raw/F/Q cells (`RES/input_checks/oracle_source_support_h{3,6,12}.csv`).
- Verifier `--stage all`: 127,153,341 parent cells equal; 48 oracle columns replayed independently from the shared
  monthly source (pandas merges; raw exact, F/B/Q atol 1e-12). Non-oracle gates (history/IDP ledgers, forbidden
  features, cohort) still run in the CLI for oracle arms.
- Tests: `tests/unit/test_origin_safe_weather_oracle.py` (calendar lookup with holes/outside grid, stress case
  past [1,NaN,3], zero gate with missing F, missing history, precipitation/temperature independence, H12 O+7..O+12 and
  ≤O perturbations, B = 2m mean, prefit-gate tampering) and CLI smoke tests (version/arm mismatch both ways, H0,
  old-namespace out-dir, tampered B6, dry run, tiny fit with oracle fingerprint).

## AC3 — six runs (R4)

- `scripts/modeling/run_origin_safe_weather_oracle_suite.py` (dry run: six `DRY_RUN_OK`; fit: `RES/logs/suite_ledger.jsonl`
  `b93e7e69…d0783b`). Raw H6 was SIGKILLed (rc −9, out of memory, swap exhausted) during block 2025 after blocks
  2022–2024 were recorded; the relaunched suite re-verified recorded batches by fingerprint/artifact hash and refit
  only the missing block. All six runs COMPLETE, 28,205 predictions each; fingerprints raw 52099c83/2ba2c28c/c3251f0e,
  B6 42f554db/b0ed87c5/9aa613b6 (H3/H6/H12).
- `--stage all` → exit 0, `passed: true`, 10 runs, 40 batches, 240 artifacts re-hashed, 160 model reloads on all
  four years (max |Δ| 0.0), 1,054,359 fitting rows checked, fit keys identical across the three arms per (H, year).
  `RES/verification/verification_summary.json` sha256 `1fd400731fb988e70b0840fb28d1405fe4c9001c4aaeb78b96ed65379a2aba84`.

## AC4 — global comparison (R5)

- `REP/global_report.md` (`8bd5b742…f2d554`), `RES/verification/global_comparison_baseline_first.csv` and
  `metrics_replay.csv` (`3532105b…92e6c3`), `paired_deltas.csv` (`9feb8da8…13b45`), `oracle_coverage.csv`
  (`398d4b6f…e88393`), `oracle_ledger_diagnostics.csv` (`fdd8fe52…d3`). Reference first; H0 reference only.
- Pooled point estimates (single seed 42; differences are raw shares/units, MAE lower is better):

| H | contrast | exact acc | 3+ acc | precision | recall | F2 | R² | MAE 3+ | ordinal MAE |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 3 | raw − ref | +0.0059 | +0.0067 | +0.0008 | +0.0191 | +0.0145 | +0.0015 | +0.0005 | −0.0080 |
| 3 | B6 − ref | +0.0034 | +0.0029 | −0.0014 | +0.0125 | +0.0090 | −0.0017 | +0.0003 | −0.0034 |
| 3 | B6 − raw | −0.0024 | −0.0038 | −0.0022 | −0.0066 | −0.0055 | −0.0032 | −0.0003 | +0.0046 |
| 6 | raw − ref | −0.0098 | −0.0100 | −0.0083 | −0.0101 | −0.0097 | +0.0008 | −0.0008 | +0.0098 |
| 6 | B6 − ref | −0.0159 | −0.0144 | −0.0180 | +0.0035 | −0.0026 | +0.0012 | +0.0000 | +0.0152 |
| 6 | B6 − raw | −0.0062 | −0.0045 | −0.0097 | +0.0136 | +0.0071 | +0.0004 | +0.0008 | +0.0055 |
| 12 | raw − ref | +0.0042 | +0.0055 | +0.0119 | −0.0167 | −0.0089 | +0.0047 | −0.0006 | −0.0048 |
| 12 | B6 − ref | +0.0103 | +0.0097 | +0.0136 | −0.0073 | −0.0015 | +0.0475 | −0.0045 | −0.0104 |
| 12 | B6 − raw | +0.0061 | +0.0042 | +0.0018 | +0.0094 | +0.0074 | +0.0428 | −0.0039 | −0.0056 |

  These are point estimates without global intervals; signs are mixed across horizons and metrics. The B6 − raw row
  is the whole fixed package increment, not an isolated IPC interaction or a causal effect.

## AC5 — region3 (R6–R7)

- `scripts/postprocessing/evaluate_region3_saved_predictions.py` → exit 0 (`RES/logs/region3.log`); requires the
  passed `--stage all` summary and records its hash. Membership: mapping `area_id` join, region 3 (1,104 mapped areas,
  1,021 evaluated), 3,234 keys (703/514/594/1,423), ten countries; identical sorted keys and truths across all ten runs.
  Outputs: `RES/region3/region3_predictions.csv`, `region3_membership_coverage.csv`, `region3_metrics.csv`
  (`9157999b…1fb8e25b6f`), `region3_paired_intervals.csv` (`7993a0bb…3b241`), `region3_metric_draws.csv.gz`,
  `region3_delta_draws.csv.gz` (joint masks), `multiplicities_{2022..2025,pooled}.npz`, `region3_metadata.json`
  (`826a173e4c9019a13656faa5c9f53de46d04033f7e556bb18a9a4836cd2d2e21`; regenerated after adding a reading note, intervals byte-identical); report `REP/region3_report.md` (`9e848b66…d271e`).
- Bootstrap: 2,000 draws, one PCG64(42) per period, shared bundle; 360 intervals (5 periods × 3 H × 3 contrasts × 8
  metrics), all `conditional`; 0 invalid paired draws in every cell (every metric defined in every draw), so each
  conditional interval used all 2,000 draws. Point metrics equal `osf.origin_metrics` (atol 1e-12, same definedness);
  weighted vs explicit row duplication agreed on all 1,440 checked cells; multiplicities replay from the seed for all
  five periods; `no_fitting`: xgboost and the training CLI not imported. Strata per period: 7/7/7/10/10.
- Unit tests: whole-area/stratified/deterministic multiplicities with uneven countries, weighted = duplicated
  (incl. undefined), F2 undefined at TP=0, exact constant R² over positive weights, 999/1,000 boundary, per-contrast
  masks, reordered-key alignment.

## AC6 — checks and lifecycle (R8)

- Focused command (implement.md) → `52 passed`, exit 0 (re-run before the final commit; result in PROGRESS.md).
- GitNexus: re-indexed (index predated `load_origin_inputs`); impact LOW for `load_origin_inputs` and `parse_args`;
  `detect_changes` before each commit. Unrelated `AGENTS.md` edits and the GitNexus stats line in `CLAUDE.md` are
  excluded from task commits.
- Close audit: pending at the time of writing; see PROGRESS.md for the job ID and result. Not claimed accepted.

## Independent pre-close check (report-only trellis-check agent)

No correctness defect found; recomputed all 360 regional intervals from the saved delta draws (≤1e-16), confirmed
multiplicity sums, duplication checks and the 52-test focused command. Three minor findings, all evidence/provenance
only (none changes a number), handled without touching fingerprinted code:

1. `Grid.from_long` coerces non-numeric source cells to NaN. Read-only check: the shared monthly source parses
   natively as float64 for both oracle variables (871,780 rows, no duplicate keys, 0 infinities, NaN 280 / 2,520 =
   the manifest's `missing_cells`), so no coercion occurred; the independent replay matched every raw cell exactly.
2. Draw/interval CSVs mix year integers and "pooled" in `period`; `region3_metadata.json` now documents
   `dtype={'period': str}`.
3. The CLI prefit gate checks raw oracle finite counts, not values against the source (documented in its docstring);
   values are checked by the builder (round-trip equality) and by the verifier's independent replay.

## Limitations carried into reports

Perfect-forecast counterfactual, not forecast-vintage evidence or an upper bound; single seed; B is not a crop-season
exposure; safe history_1 may be stale (median staleness 0–6 months and maximum ≤ 100 months by horizon/evaluation year); regional intervals
condition on fitted models and observed countries/years and ignore within-country shared shocks; parent source-vintage
and standardization limits remain.
