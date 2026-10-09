# compact_cds_launch_v1: final execution evidence (2026-10-09)

Status: **all stages executed and final `--verify` passed (exit 0).** The task stays `in_progress` until the supervisor
accepts A1–A9. Nothing has been archived, pushed or audited.

## Bindings

- **Code:** HEAD `58dd9cd3e830de7ee049b6de3238831fe6c016ca`, the implementation commit made by Codex with Windows Git.
  - Branch: task/compact-climate-weather-oracle.
  - No source or config edits since the commit. Pins are in `research/final_verify_code_sha256.txt`.
  - The pins include compact_launch `ed10b701…` and run script `c58be4f4…`. Both hyperparameter configs are unchanged.
- **Runtime:** frozen interpreter `/home/swl007007/.venvs/ipcch-geo/bin/python`, with Python 3.12.3, NumPy 2.4.4, pandas 3.0.3,
  sklearn 1.8.0 and XGBoost 3.2.0.
- **Inputs:** manifest `b2e73812…cafe`; weather cube `8745e7af…`; provenance `408e8090…` (ACCEPTED).

## Fits (seed 42, half-life 24, threshold 0.2, n_jobs 16, independent P3 config)

| run | how | wall | fit time (internal) | peak RSS |
|---|---|---|---|---|
| compact_baseline/0m (shared H0) | pilot, `logs/pilot_h0.log` | 1:32.36 | 44.93 s | 1.96 GB |
| compact_baseline/6m, /12m, compact_cds_weather/6m, /12m | `logs/fits_remaining.log` (H0 "verified existing complete run", not refit) | 3:53.62 total | 44.8 / 45.4 / 46.5 / 48.4 s | 2.09 GB |

- **Replay:** every run passed the independent replay (`research/pilot_replay_check.py` → `research/replay/replay_*.json`).
  - All 20 reloaded boosters keep the contract feature order: 296 features for baseline runs, 308 for weather runs.
  - Raw predictions differ from the saved ones by at most 0.0, on both the saved and the manifest matrices. Classes match exactly.
  - Fit keys, targets and weights equal the manifest selection. Weights equal the independently recomputed decay rule.
  - Pilot detail: `research/pilot-check.json`.
- **Raw predictions:** the cumulative predictions are kept raw from four independent regressors. They may be non-monotone or
  negative, as approved. Non-monotone rows: H0 137, B6 3, B12 4, W6 41, W12 35. Repair happens only in the reporting shares.
- **Predicted classes per run (counts of the 6188 areas):**

  | run | phase 1 | phase 2 | phase 3 | phase 4 |
  |---|---:|---:|---:|---:|
  | H0 | 38 | 1690 | 4366 | 94 |
  | B6 | 0 | 2444 | 3733 | 11 |
  | B12 | 0 | 1443 | 4260 | 485 |
  | W6 | 0 | 2429 | 3746 | 13 |
  | W12 | 0 | 1281 | 4640 | 267 |

## Report stage

- Command: `--report`, `logs/report.log`. Exit 0 in 2:00.05, max RSS 1.31 GB.
- Population tables:
  - area, country, region and global tables;
  - 4 paired-difference tables;
  - country cap audit: 19 countries and 4004 areas capped.
- Population totals: raw 2,106,501,620.66; effective 1,429,568,874.42.
- Seven PNGs and the codebook.
- Global effective P3+ (repaired shares, prediction summaries only, not scores):

  | target | compact_baseline | compact_cds_weather |
  |---|---|---|
  | 2026-04 (H0, shared fit) | 332.2 M (23.24 %) | same fit |
  | 2026-10 (H6) | 307.4 M (21.50 %) | 310.2 M (21.70 %) |
  | 2027-04 (H12) | 371.4 M (25.98 %) | 350.9 M (24.54 %) |

## Documentation-only corrections (supervisor requests; after verify attempt 1)

- Script: `research/output_documentation_corrections.py` (sha256 `f8365314ae12…`).
- Log: `research/output_documentation_corrections.log`. Evidence: `research/output-documentation-corrections.json`.
- Frozen code hashes for compact_launch, launch_visualizations and alert_risk_maps were checked unchanged before and after.

**Codebook**
- Copied the 10 approved per-variable fields from the contract:
  - training_source and inference_source;
  - training and inference formula;
  - training and inference missing semantics;
  - training and inference reference period;
  - training and inference spatial definition.
- Removed the expected-contract sentences from limitations:
  - "This is an expected input, not a fitted result.";
  - "Expected inputs only; no fit verified." (the same kind of sentence, on the 12 weather rows).
- Appended an accepted-weather-stage outcome sentence to the 12 weather rows.
- Unchanged, and asserted by the script: 308 rows, predictor order, membership and expanded counts, actual_model_columns and
  positions, expected_matches_actual, fit_status.
- sha256: `50f353ee…` → `e563cbf0…`. Columns: 30 → 39.

**Five categorical PNGs**
- Re-rendered from the saved categorical records, with record hashes unchanged and classes equal to each run's predictions_raw.
- Rendering used the same geometry and the frozen helpers (join, `_panel` with the Latin-America inset, colors, legend),
  with the same size, margins, dpi and filenames.
- Text changes:
  - short panel title: "Predicted crisis (phase >= 3), target YYYY-MM, n=6188 areas";
  - suptitle: "IPCCH compact launch, origin 2026-04: <arm> H<h> [(shared H0 fit)] / Predicted-only view; actual-outcome panels
    are excluded by design for this launch."
- Text extents were asserted inside the canvas. Superseded PNGs: `research/final_verify_attempt1/superseded_figures/`.
- `figure_metadata.json` records `rendering_correction` (version 2) and the figure hashes. `report_outputs.json` maps and
  codebook hashes were refreshed.
- The 2×3 share and 1×2 difference figures are unchanged.
- The tiny polygon fragment just outside the top-right corner of the Latin-America inset also appears in v1; it comes from
  the frozen inset helper and was left unchanged.

## Final verification

- **Attempt 1:** before the corrections. Passed, exit 0, 1:41.88. Preserved in `research/final_verify_attempt1/`, including
  the stdout log, verification.json `369883107…`, report_outputs.json `577977e6…` and launch_summary.md.
- **Final (attempt 2):** `run_compact_cds_launch.py --verify`, run once after the corrections. Live stdout was written to
  `research/final_verify_stdout.log` (sha `f4db40b0…`), outside both inventory roots, and the log is now closed.
  - **Exit 0** in 1:39.37, max RSS 0.46 GB.
  - Result: passed, no problems.
  - 20 models reloaded, max replay difference 0.0.
  - 714 population columns and 315 difference columns checked.
  - **488 old artifacts checked, 0 changed.**
  - 107 inventory files; exactly the 7 required PNGs.
- `results/.../verification.json` sha256 `924f3bd7…`.
  - All 107 inventory hashes equal the current files.
  - The inventory contains only closed logs, and no task-research file.
  - The corrected codebook and the five corrected PNGs are the inventoried versions.
- `reports/.../launch_summary.md` (sha `33aa73cc…`) states:
  - the empirically verified (start, end] temperature window, noting that official primary documents do not state endpoint
    inclusivity;
  - the negative-tp source limitation.
