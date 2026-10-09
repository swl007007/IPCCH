# Compact 2026 January–April extension — final execution evidence (2026-10-09)

Status: **all six authorized actions returned 0, and the executor verifier passed for both scopes. Reporting statuses are `verified`.**

- Waiting for coordinator acceptance; executor verification is not acceptance.
- No audit, commit, archive, push or provider call.

Machine-readable record (strict JSON): `research/final-execution-checkpoint.json`.

## Identity and pins

- HEAD `60578219` (tested implementation commit); approved plan `16d2e92`.
- Entrypoint `cbc1f88b…` and test `952bd849…`, equal to the frozen values.
- Same executor session `579e6ba5-…`, with the frozen interpreter (Python 3.12.3, NumPy 2.4.4, pandas 3.0.3, sklearn 1.8.0, XGBoost 3.2.0) and the Windows-Git shim.
- The entrypoint, test, Somalia-local helper and both config hashes were **identical before and after every action** (`research/execution/*_pins_{before,after}.txt`).

## Actions (sequential chain `research/execution/chain.sh`, stopping on the first nonzero return code)

Common prefix: `PATH=/tmp/ipcch-windows-git-bin:$PATH PYTHONPATH=src /usr/bin/time -v /home/swl007007/.venvs/ipcch-geo/bin/python scripts/modeling/run_compact_eval_2026_extension.py`

| action | return code | wall | max RSS | wrapper PID |
|---|---:|---:|---:|---:|
| `--scope global --approve-training` | 0 | 7:02.93 | 2.15 GB | 1616775 |
| `--scope SOM --approve-training` | 0 | 4:08.73 | 1.16 GB | 1652193 |
| `--scope global --report` | 0 | 0:12.39 | 0.33 GB | 1675612 |
| `--scope SOM --report` | 0 | 0:07.16 | 0.30 GB | 1676875 |
| `--scope global --verify` | 0 | 2:46.35 | 1.02 GB | 1677568 |
| `--scope SOM --verify` | 0 | 2:48.88 | 0.94 GB | 1692487 |

- Return codes are recorded in `research/execution/action_returncodes.txt`, which ends with "ALL DONE".
- Per-action stdout JSON and stderr/time logs are in `research/execution/` (outside every result/report root).
- The PIDs are those of the `/usr/bin/time` wrappers; each Python process is its child.

## Outputs

| | global | SOM |
|---|---|---|
| results root | `results/experiments/compact_climate_weather_oracle_eval_2026_jan_apr_v1` | `results/experiments/compact_climate_weather_oracle_eval_2026_jan_apr_v1_somalia_local` |
| reports root | `reports/compact_climate_weather_oracle_eval_2026_jan_apr_v1` | `reports/compact_climate_weather_oracle_eval_2026_jan_apr_v1_somalia_local` |
| files (results + reports) | 88 | 86 |
| extension manifest | `913fae43…` (= preflight) | `bce554fb…` (= preflight) |
| verification_summary.json | `8dee633f…` | `8980fb59…` |
| comparison_metadata.json (status `verified`) | `a5d0a2f0…` | `08359832…` |
| report.md | `a88209b3…` | `96ddfbab…` |
| actual-input codebook | `0904d7f3…` | `92369c59…` |

Hashes of every report table, run metadata and 2026 batch artifact are in the JSON. `verification/artifact_inventory.csv` lists every result and report file outside the verification folder.

## A1–A8 evidence

**A1 — parent gates, keys, support, pairing.**
- Both no-write preflights, training actions and final verification actions re-ran the unchanged frozen parent gate for all seven runs, then checked the copied 2026 / local masks. Reporting consumes the saved fitted artifacts and manifest identities without fitting.
- 2026 January–April evaluation:

  | | rows | areas | by month (1/2/3/4) | keys sha |
  |---|---:|---:|---|---|
  | global | 4,327 | 3,823 | 679/643/231/2,774 | `e925e0f4…` |
  | SOM | 905 | 904 | 1/0/0/904 | `e2a14c20…` |

- Original keys: global 28,205 (`f0193c14…`), SOM 4,933 (`5f8343c4…`).
- Paired baseline columns, labels and NaN are identical across arms (checked in the preflight). Truth and targets are checked in every verify.

**A2 — original imports.**
- For each scope, all 28 original batches were rehashed and reconciled with the accepted inventory (global: 203-entry `artifact_inventory.csv`; SOM: the `verification.json` inventory). Prior verification passed.
- Fixed parameters matched, original fingerprints were recomputed (global `b9f808ea…`…, SOM `d2524106…`…), and fit-key cutoffs, scope, ages and weights, evaluation keys, truth, targets and published predictions were all checked.
- **Original parity: global 2,800 and SOM 280 cells**, matching value, status, reason and all seven support columns. Original pooled is `pooled_2022_2025`.

**A3 — new fits only.**
- Exactly 7 new 2026 batches and 28 boosters per scope, so **14 batches / 56 new boosters** in total. There are no old-year batches in the extension roots and no oracle H0.
- Fit sets equal `expected_runs.csv`:

  | scope | H0 | H3 | H6 | H12 |
  |---|---|---|---|---|
  | global rows | 47,979 | 47,796 | 42,715 | 38,536 |
  | SOM rows | 5,834 | 5,834 | 4,926 | 3,958 |

- Cutoffs: 2025-12 / 10 / 07 / 01.
- Latest actual fitting labels: global 2025-12 / 10 / 07 / 01; SOM 2025-10 / 10 / 07 / 2024-07.
- No 2026 label was used, and the weights are anchored at Jan 2026 − H.

**A4 — replay and schemas.**
- All 28 new boosters per scope were reloaded; max replay difference **0.0**; classes from the reloaded predictions are exact.
- **140 fitted schemas inspected per scope** (112 reused + 28 new), so 280 in total, all in exact contract order (296 / 302 / 308).

**A5 — metrics and differences.**
- Independent sklearn replay plus independently reconstructed undefined status/reason and all seven support columns.
- Cell counts:

  | | global | SOM |
  |---|---|---|
  | metric cells | **3,920** (overall + regions 0–8; 5 annual + 2 pooled periods) | **392** |
  | delta cells | 1,680 | 224 (including shared H0) |

- Split tables equal their canonical subsets.
- Undefined cells: global 176. These are:
  - regions 2 and 6 with no 2026 rows: 112 cells, "no eligible samples";
  - region 8 2026 R², from a single row: 7 cells, "fewer than two valid samples";
  - inherited empty-region 2022 cells: 56;
  - region 2022 zero F2 denominator: 1.

  SOM has 1 undefined cell, the inherited oracle H12 / 2023 F2 ("zero f2 denominator").
- Pooled rows: `pooled_2022_2026` global 32,532 and SOM 5,838; `pooled_2022_2025` global 28,205 and SOM 4,933.

**A6 — reports and lineage.**
- Published:
  - metric, difference, undefined and coverage CSVs;
  - `comparison_metadata.json`;
  - `report.md`, marked "January–April only";
  - codebook, expected-vs-actual inputs and model run index (112 reused + 28 new boosters).
- Per-run `sources_by_year` gives reused versus fitted-here years, fingerprints, artifact hashes and the accepted-inventory reference. Approved-spec copies are manifest-bound.
- Statuses moved from `verification_pending` to **`verified`**, with refreshed report hashes.

**A7 — tests and validation.**
- 82 focused tests passed (pytest exit 0).
- No-write validate-only passed for both scopes.
- Tests cover stale and incomplete resume rejection.

**A8 — protection.**
- My protected inventory: **859 files, 0 changed, 0 missing, 0 added** for each scope.
- Covers old inputs, results and reports; launch inputs, results and reports; code; configs; membership; reference.
- The coordinator's separate 961-file baseline (`supervisor-protected-before.json`) remains for the coordinator to recheck.

## Headline results (point estimates; single seed; no intervals)

**Global, phase 3+ F2**

| run | 2026 (Jan–Apr) | pooled_2022_2026 | pooled_2022_2025 |
|---|---:|---:|---:|
| baseline H0 | 0.848 | 0.844 | 0.843 |
| baseline H3 | 0.854 | 0.834 | 0.830 |
| oracle H3 | 0.837 | 0.830 | 0.828 |
| baseline H6 | 0.835 | 0.838 | 0.838 |
| oracle H6 | 0.847 | 0.852 | 0.853 |
| baseline H12 | 0.869 | 0.797 | 0.783 |
| oracle H12 | 0.872 | 0.814 | 0.802 |

**SOM, phase 3+ F2**

| run | 2026 (Jan–Apr) | pooled_2022_2026 | pooled_2022_2025 |
|---|---:|---:|---:|
| baseline H0 | 0.861 | 0.723 | 0.697 |
| baseline H3 | 0.842 | 0.689 | 0.657 |
| oracle H3 | 0.839 | 0.670 | 0.635 |
| baseline H6 | 0.777 | 0.641 | 0.615 |
| oracle H6 | 0.761 | 0.635 | 0.611 |
| baseline H12 | 0.833 | 0.501 | 0.430 |
| oracle H12 | 0.844 | 0.530 | 0.463 |

**Oracle − baseline differences** are small and mixed in sign, for example:
- global 2026: H3 −0.017, H6 +0.012, H12 +0.004;
- SOM 2026: H3 −0.002, H6 −0.016, H12 +0.012.

Other metrics are in the report tables.

**Caveats**
- 2026 is January–April only and month-imbalanced. SOM is almost entirely April (904 of 905 keys).
- Continuous P3+ R² for 2026 is below the pooled values at every global horizon (0.19–0.37 vs 0.33–0.49). For SOM it is above its negative pooled values at every horizon (0.03–0.28 vs −0.36 to −0.01).
- The oracle measures ideal realized weather, not CDS skill.
- The availability proxy is retrospective.

Paused for coordinator acceptance.

## Coordinator acceptance after execution

The coordinator reviewed this executor evidence against the approved A1-A8 contracts, the actual command return codes, final saved verification records and current reporting hashes. Supplementary read-only numerical extraction and publication checks found no discrepancies. The independent 961-file / 6,090,454,088-byte baseline was rehashed after execution: no changes, missing files or additions in protected roots (`supervisor-protected-after.json`). A1-A8 are accepted for this bounded task. Ordinary evidence commit and Trellis archival follow; no Trellis audit was started.
