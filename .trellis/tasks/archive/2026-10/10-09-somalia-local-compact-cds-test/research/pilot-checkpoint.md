# Somalia local historical pilot: compact_baseline H0 / 2022 (2026-10-09)

Status: **the pilot ran (exit 0) and passes the independent check. STOPPED for supervisor acceptance.**

- Nothing else was fitted: no other historical batch, no launch input or fit, no report and no full verification.
- No audit and no commit.

Machine-readable record: `research/pilot-checkpoint.json`.

## Run

- **Command** (frozen interpreter, Windows-Git shim on PATH):
  `PATH=/tmp/ipcch-windows-git-bin:$PATH PYTHONPATH=src /usr/bin/time -v /home/swl007007/.venvs/ipcch-geo/bin/python scripts/modeling/run_somalia_local_compact_test.py --approve-training --pilot`
- **Process:** detached, PID 758706. Exit 0, wall 1:14.90, max RSS 762,436 KB.
  - Most of the wall time is the parent gate plus the one-time 491-file frozen snapshot.
  - Batch time 4.32 s. Per-target fit time: phase2 2.52 s, phase3 0.19 s, phase4 0.98 s, phase5 0.31 s.
- **Logs:** `research/pilot.log`, `research/pilot_stdout.json` (`{"status": "PARTIAL", "batches": [2022]}`, launch "not started (pilot)"), `research/pilot.pid`.
- **Pins before and after are identical** (`research/pilot_pins_before.txt`, `pilot_pins_after.txt`):
  - HEAD `e563b0bd2ac7fba1094c0e30f7f5d889a1c99fa4`;
  - script `88aee59b…`, test `3c149547…`;
  - configs `37423006…` and `cdc0e55a…`.
- **Runtime:** Python 3.12.3, NumPy 2.4.4, pandas 3.0.3, sklearn 1.8.0, XGBoost 3.2.0, `/home/swl007007/.venvs/ipcch-geo/bin/python`.

## Identities

- **Historical local manifest:** `results/experiments/compact_climate_weather_oracle_v1_somalia_local/inputs/compact_climate_weather_oracle_v1_somalia_local_manifest.json`, sha256 **`573b0d0bb074…fe228`**. This equals the accepted preflight value.
- **Local fingerprint:** `d25241063045983210a415d8a09ebb4fdfa5794ed97ea89550e5f718a0edae4e`. Its prefix matches the preflight. The parent fingerprint is `b9f808eac345…`; the local one differs from it, as required.
- **Frozen before-snapshot:** 491 files, written to both local `preflight/` directories with identical bytes, sha256 `25c45108…` (equals the preflight digest). Preserved for the final comparison.
- **Local input copies:** approved spec ×5 (equal to `3ccf92a`), parent contract ×3, SOM membership/evaluation/valid-key CSVs. Their hashes are in the JSON.

## Fitting and evaluation keys

- **Fitting:** 901 SOM rows over 139 areas.
  - Labels 2017-01..**2021-07**, cutoff 2021-12, origin 2022-01.
  - Weights 0.17678–0.84090, equal to `0.5**((2022-01 − U)/24)` at atol 1e-15.
  - Keys sha256 `913c2f3e…` (equals the batch record).
  - These are exactly the complete valid SOM rows ≤ 2021-12, in parent dataset order.
- **Evaluation:** 1,129 keys over 585 areas, sha256 `53a24993…`. This is exactly the complete set of frozen SOM 2022 evaluation keys.
- **Features:** 296, frozen schema `e97388f8…`.

## Models (four UBJ)

| target | sha256 | bytes | schema | rounds | max replay diff |
|---|---|---:|---|---:|---:|
| phase2_worse | 39f19cbaf0fa…3d1e | 949,897 | 296, equal to manifest | 200 | 0.0 |
| phase3_worse | d35c3aa6b5d1…66ce | 159,239 | 296, equal to manifest | 200 | 0.0 |
| phase4_worse | 4d6af5c23e25…2d92d | 535,022 | 296, equal to manifest | 200 | 0.0 |
| phase5_worse | 6d4d1f75e80a…150ee | 164,274 | 296, equal to manifest | 200 | 0.0 |

- Other artifacts: `predictions.csv` `5f22e1ed…`, `fit_keys.csv.gz` `fc624ac3…`, `batch_record.json` `4e488c92…`, `run_metadata.json` `e28c8c59…` (status PARTIAL, local version and manifest bound).
- The batch directory holds exactly the six recorded artifacts plus the record.

## Independent check

Script: `research/pilot_check.py`. Result: `research/pilot-independent-check.json`, **passed**, all 24 checks true. The check takes a different path from the production script:
- It reads the parent H0 dataset and cohort directly, with hash checks.
- It rebuilds SOM membership from the lookup.
- It checks validity, cutoff, ages, weights and targets independently.
- It reloads the boosters with plain xgboost and replays them on the parent rows.
- It recomputes classes from the reloaded predictions (exact) and from the saved ones.
- It confirms the truth and the normalized targets.
- It confirms that only the pilot batch exists and that no launch inputs or runs exist.
- It checks the snapshot digest.

## Observation (fact, not an accuracy claim)

- Predicted classes: 1,000 phase 2 and 129 phase 3.
- Observed phases: 52 / 240 / 610 / 221 / 6 for phases 1–5 (837 observed phase 3+).
- The early Somalia fit is small (901 rows, 139 areas, labels through 2021-07) under the fixed global hyperparameters. Metrics come only at the report stage.

## Next

The remaining 27 historical batches, the 5 launch fits, the reports and the 132-model verification all remain closed until the supervisor independently accepts these four pilot models.
