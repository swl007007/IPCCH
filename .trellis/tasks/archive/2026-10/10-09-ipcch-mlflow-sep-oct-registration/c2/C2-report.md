# Checkpoint C2: live registration (executor report)

Status: **accepted by the supervisor**. Independent checks: `supervisor-counts.json` (112 models,
126 versions, 202 detailed runs, 174 dashboard runs, 512 detailed dataset names, 0 unfinished runs),
`supervisor-browser.md` + `browser/`, `supervisor-download.json` (36 member hashes), `supervisor-payload.json`.
Live links: dashboard http://localhost:5000/#/experiments/4, detailed runs http://localhost:5000/#/experiments/3.

Live service `http://127.0.0.1:5000` (MLflow 3.17.0, existing store). Implementation commit 142229b.
Run driver: `c2/c2_driver.py`. It builds one plan and then calls the tested functions under the shared
`import.lock`: `store.snapshot`, `plan.build_plans`/`check_global`/`write_plans`, `catalog.import_sources`,
`verify_sources`, `apply_dashboard`, `verify_dashboard`, `store.compare`. Wall time: 749 s
(2026-10-10T01:24:27Z to 01:36:30Z). Step log: `c2/c2-log.jsonl`.

## Backup and baseline

- A fresh full live snapshot (every table row + 2,223 artifact hashes) was **identical** to the C1
  backup (digest `62e85b88…ad9d` on both).
- That backup was moved to `~/ipcch-mlflow-backups/20261010-before-ipcch-forecasting/` (db sha256
  `7bd1d168…c9e2`, 2,223 artifact files). Its C1 restore-check on port 5091 (6/6 downloads matched)
  covers this baseline, so no second restore was run.
- The complete pre-import snapshot is saved at
  `~/ipcch-mlflow-backups/20261010-ipcch-forecasting-before-snapshot.json`.

## Results

| Step | Result (file) |
|---|---|
| Plan | 112 registered models, 126 versions, 190 children, 174 dashboard rows, 2,458 boosters, 584 fit units, 512 datasets, 50,446 metrics, 2,846 NA (`plan.json`); all equal to the frozen counts |
| Import | 2 experiments created; 12 parents + 190 children; 126 logged models; 112 registered models; 126 versions; 50,446 metrics; 1,356 dataset inputs; 768 artifacts (`import.json`) |
| Verify (deep) | 12 sources, 190 children, 50,446 metrics read back; tar members hashed; one metric-history row per key (`verify.json`) |
| Dashboard | 174 rows created and verified (`dashboard.json`, `dashboard-verify.json`) |
| Unchanged repeat | import `sources_noop: 12`; dashboard `dashboard_noop: 1`; store snapshot identical before/after (`repeat.json`) |
| Old-store compare | ok, 0 problems; all pre-existing rows byte-identical by primary key; 2,223 pre-existing artifacts unchanged; every new row is in the IPCCH Forecasting namespace (`compare.json`) |
| 100-row dashboard search | 2,946,272 bytes for 100 rows (max 294 metrics per row; next page exists) |

New rows: 376 runs (202 detailed + 174 dashboard), 81,510 metrics (50,446 detailed + 31,064 dashboard),
1,010 dataset entities, 2,766 inputs. The existing experiments `IPCCH - detailed runs` (126 runs) and
`IPCCH - dashboard` (136 runs), and their 68 models / 100 versions, are unchanged.

The supervisor's browser and download checks are in `c2/browser/`, `supervisor-browser.md` and
`supervisor-download.json`; they are not repeated here.

## Residuals

- Staging tars (3.7 GB) remain under `~/.local/share/ipcch-mlflow/ipcch-forecasting/staging/`. They are only
  needed to resume an interrupted import and can be deleted.
- The 7.9 GB durable backup is retained, as instructed.
- The lineage limits in README "Lineage limits" are disclosure only. Executor did not commit, push, merge, archive or audit; supervisor performs the final evidence commit and native archive.
