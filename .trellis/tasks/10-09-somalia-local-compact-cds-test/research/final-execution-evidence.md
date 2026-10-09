# Somalia local compact/CDS test — final execution evidence (2026-10-09)

Status: **the full fixed plan was executed, and the executor verifier passed (exit 0). Awaiting independent Codex final acceptance.**

- Executor verifier success is not final acceptance.
- No Trellis audit (user override), no commit, no archive, no tuning.

Machine-readable record: `research/final-execution-checkpoint.json`.

## Identity

- Same executor (Claude Opus 5.5 1M, session `579e6ba5-…`), same branch, frozen implementation commit `e563b0bd2ac7…`.
- Script `88aee59b…` and test `3c149547…`.
- Frozen interpreter `/home/swl007007/.venvs/ipcch-geo/bin/python`, with Python 3.12.3, NumPy 2.4.4, pandas 3.0.3, sklearn 1.8.0 and XGBoost 3.2.0. Settings: seed 42, half-life 24, threshold 0.2, n_jobs 16.
- Windows-Git shim on PATH for all Git reads.
- The HEAD, code, config and 491-file snapshot pins were identical before and after each stage (`research/{train,report,verify}_pins_{before,after}.txt`).
- Logs, stdout and PID files are in task research, outside the inventoried roots.

## Commands (run sequentially, nothing overlapping)

Prefix for all three: `PATH=/tmp/ipcch-windows-git-bin:$PATH PYTHONPATH=src /usr/bin/time -v /home/swl007007/.venvs/ipcch-geo/bin/python scripts/modeling/run_somalia_local_compact_test.py`

| stage | flag | PID | exit | wall | max RSS | outcome |
|---|---|---:|---:|---:|---:|---|
| training | `--approve-training` | 788335 | 0 | 10:21.43 | 1.20 GB | Pilot batch verified, not refit. 27 new historical batches and 5 launch fits. |
| report | `--report` | 850626 | 0 | 0:42.44 | 0.61 GB | Historical tables, codebook and report.md; launch tables, seven maps, codebook and summary. |
| verify | `--verify` | 860066 | 0 | 7:34.52 | 0.95 GB | Historical PASS, launch PASS, frozen 491/491 unchanged. |

Outputs:
- Training stdout: `research/train_stdout.json`. The frozen `fit_run` prints five progress lines before the JSON.
- Report: `research/report_stdout.json`.
- Verify: `research/verify_stdout.json`; the live log is `research/verify.log`.

## Fits

**Historical (Somalia-local)**
- 7 runs: baseline H0/H3/H6/H12 and oracle H3/H6/H12. 28 batches, 112 UBJ models.
- Every batch fits all valid SOM labels up to `Jan(Y) − max(H,1)`.
- SOM fitting rows per year 2022–2025:

  | horizon | rows |
  |---|---|
  | H0/H3 | 901 / 2030 / 3247 / 3958 |
  | H6 | 901 / 1504 / 2899 / 3958 |
  | H12 | 858 / 944 / 2554 / 3603 |

- Evaluation keys per year: 1129 / 1217 / 711 / 1876 (4,933 in total over 905 areas), identical across all runs.

**Launch**
- 5 unique runs, 20 UBJ models; fingerprints `3a5337b1…`, `ab23a68e…`, `253d7458…`, `1a2f793d…`, `cd2db7ed…`.
- Each run fits on 5,835 SOM rows over 905 areas (labels 2017-01..2026-01) and predicts 904 areas.
- H0 is one shared fit.

**Manifests and records**
- Local manifests: historical `573b0d0b…` and launch `f76da064…`. Both equal the accepted preflight values.
- Scope sidecar `158e2165…`.
- Frozen snapshot `25c45108…` (491 files).

## Verification (`--verify`, independent arithmetic)

**Historical: PASS, no problems.**
- 28 batches; 112 models reloaded with max replay difference 0.0; classes from the reloaded predictions exact.
- 168 artifacts rehashed and 64,850 fitting rows checked (complete SOM sets, cutoffs, ages, weights, fitter targets).
- Fitting keys identical across arms.
- 280 metric cells replayed with sklearn and 160 delta cells, including the independent undefined status and reason.
- Codebook checked against the boosters; every report deliverable and recorded hash present.
- `results/.../compact_climate_weather_oracle_v1_somalia_local/verification/verification.json` `d65d04d3…` (inventory 259 files).

**Launch: PASS, no problems.**
- 20 models reloaded with replay difference 0.0; classes exact.
- 29,175 fitting rows checked (exact ordered keys and `fit_ord` for every run including H0; targets; April weights; paired runs identical).
- Inference prefixes match.
- 84 population columns and 147 difference columns checked (shared H0 differences exactly 0).
- Cap factor recomputed: 0.29782279233177217; raw 62,695,007; effective 18,672,002.05.
- 11,752 map values checked; the geometry join is unique for all 904 areas; seven-entry figure metadata and geometry hashes match.
- Every deliverable and recorded hash present; scope sidecar bound.
- `results/launch/.../verification.json` `c13835e3…` (inventory 110 files).

**Frozen:** 491 checked, 0 changed, 0 missing, 0 added.

**Stage inventories now:**

| root | files | MB |
|---|---:|---:|
| historical results | 256 | 143.1 |
| historical reports | 4 | 0.6 |
| launch results | 100 | 75.9 |
| launch reports | 11 | 3.6 |

Hashes of the report records, codebooks and the seven PNGs are in the JSON.

**Visual inspection:** I looked at the categorical H12 CDS map, the 2×3 share map and the 1×2 difference map. All titles are inside the canvas and legends and colorbars are present, in the inherited style.

## Historical results (SOM, evaluation weights = rows)

**Pooled 2022–2025 (n = 4,933 keys, 905 areas, 2,904 observed phase 3+)**

| arm | H | exact acc | 3+ acc | prec 3+ | recall 3+ | F2 3+ | R² 3+ | MAE 3+ | ordinal MAE | pred 3+ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| baseline | 0 | 0.5427 | 0.6262 | 0.6755 | 0.7025 | 0.6969 | −0.0650 | 0.1392 | 0.5115 | 3020 |
| baseline | 3 | 0.5289 | 0.5946 | 0.6549 | 0.6581 | 0.6574 | −0.0437 | 0.1380 | 0.5437 | 2918 |
| oracle | 3 | 0.5340 | 0.6011 | 0.6735 | 0.6257 | 0.6347 | −0.0811 | 0.1391 | 0.5402 | 2698 |
| baseline | 6 | 0.5163 | 0.5826 | 0.6582 | 0.6054 | 0.6152 | −0.1988 | 0.1462 | 0.5561 | 2671 |
| oracle | 6 | 0.5019 | 0.5672 | 0.6404 | 0.6040 | 0.6109 | −0.1820 | 0.1462 | 0.5725 | 2739 |
| baseline | 12 | 0.4144 | 0.4744 | 0.5764 | 0.4039 | 0.4296 | −0.3977 | 0.1613 | 0.6655 | 2035 |
| oracle | 12 | 0.3967 | 0.4549 | 0.5452 | 0.4463 | 0.4631 | −0.4484 | 0.1648 | 0.6834 | 2377 |

**Pooled oracle − baseline** (raw differences in metric units; H0 shared, so exactly 0)

| H | exact acc | 3+ acc | prec 3+ | recall 3+ | F2 3+ | R² 3+ | MAE 3+ | ordinal MAE |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 3 | +0.0051 | +0.0065 | +0.0186 | −0.0324 | −0.0227 | −0.0374 | +0.0011 | −0.0034 |
| 6 | −0.0144 | −0.0154 | −0.0178 | −0.0014 | −0.0043 | +0.0169 | −0.0000 | +0.0164 |
| 12 | −0.0176 | −0.0195 | −0.0312 | +0.0424 | +0.0334 | −0.0507 | +0.0035 | +0.0178 |

- **Annual values** (`results/.../report/som_metrics_long.csv`; `reports/compact_climate_weather_oracle_v1_somalia_local/report.md`):
  - 2022 is the weakest year at every horizon. Exact accuracy is 0.22–0.30.
  - Phase 3+ recall in 2022 is 0.151 (baseline H0) and 0.0096 (baseline and oracle H12).
  - Baseline H12 also has 2023 recall 0.0498. Later years recover; for example, H0 2023–2025 recall is 0.90–0.95.
- **Single undefined cell:** oracle H12 / 2023 F2 3+, status unavailable, reason "zero f2 denominator". There were no true positives, so precision = recall = 0. It is reported, not imputed.
- **What can and cannot be concluded:**
  - The pooled oracle − baseline differences are small (at most ±0.05) and mixed in sign. They are single-seed point estimates without intervals, so they do not establish a weather-information gain or loss for Somalia.
  - The oracle arm measures ideal realized weather, not CDS forecast skill.

## Launch results (SOM, prediction summaries, not scores)

- Fixed April 2026 population: raw 62,695,007; capped effective 18,672,002.05.
- All 904 areas are capped; there are no zero-population areas.

| arm | H | target | P3+ share | P3+ people | P4+ share | P4+ people | areas predicted phase 3 (raw class) |
|---|---:|---|---:|---:|---:|---:|---:|
| baseline (shared H0) | 0 | 2026-04 | 0.2783 | 5,195,565 | 0.0609 | 1,137,764 | 781 |
| baseline | 6 | 2026-10 | 0.2721 | 5,080,585 | 0.0775 | 1,446,418 | 664 |
| CDS weather | 6 | 2026-10 | 0.2772 | 5,175,301 | 0.0730 | 1,362,754 | 682 |
| baseline | 12 | 2027-04 | 0.2504 | 4,674,759 | 0.0761 | 1,421,617 | 755 |
| CDS weather | 12 | 2027-04 | 0.2649 | 4,946,702 | 0.0772 | 1,441,871 | 738 |

**CDS − baseline (Somalia, equal denominators)**

| H | target | ΔP3+ share | ΔP3+ people | ΔP4+ share | ΔP4+ people |
|---:|---|---:|---:|---:|---:|
| 0 | 2026-04 | 0 | 0 | 0 | 0 |
| 6 | 2026-10 | +0.0051 | +94,717 | −0.0045 | −83,664 |
| 12 | 2027-04 | +0.0146 | +271,943 | +0.0011 | +20,254 |

- Raw classes are only phases 2 and 3 in every view.
- The reporting-only share repair touched 27–80 of 904 areas per view (negative cumulative components); raw predictions and classes are unchanged.
- Coverage ledger: area 3146 is outside launch coverage.

## Limitations and open points for acceptance

- **Statistical uncertainty:** single seed and one fit per annual block; no bootstrap or intervals. Differences are point estimates.
- **Small early Somalia fits and early-year under-prediction:**
  - The early fits use fixed global hyperparameters on small samples: 2022 has 858–901 rows over 96–139 areas.
  - Early-year phase 3+ under-prediction is substantial: H0/2022 recall 0.151; H12/2022 recall 0.010. The accepted pilot already showed this (129 predicted 3+ vs 837 observed).
  - This is a reported result. No settings were changed.
- **Historical oracle:** it measures ideal-weather information, not CDS skill.
- **Launch:** levels for future targets cannot establish accuracy. The inherited CDS weather-stage limits apply unchanged, and there was no new retrieval.
- **Coverage and population:**
  - Area 3146 is outside launch coverage; its population is not invented.
  - All 904 launch areas carry the inherited Somalia cap factor. That is not a population-vintage certification.
- **Inherited data limits:** observation/report months remain an availability proxy, and upstream vintages and climatology lineage are inherited.

STOPPED for independent Codex final acceptance.
