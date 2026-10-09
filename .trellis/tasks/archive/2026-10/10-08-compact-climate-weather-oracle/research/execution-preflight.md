# Execution preflight (partial) — 2026-10-08

Status: **PARTIAL — stopped at a safe checkpoint for handoff to the Herdr executor session (w11:p4).**
This was a preflight-only process (claude-opus-5-5[1m]). It did not edit product code, run builders, build matrices or fit models.
Machine-readable record: `research/execution-preflight.json` (includes all 23 parent-input hashes).

## Passed

| Check | Result |
|---|---|
| 9 approved artifacts vs `execution-approval.json` | all sha256 match working-tree bytes |
| Contract CSV/run index vs HEAD `928d080` | differ only by CRLF line endings (CR-stripped hashes equal); approved hashes bind the CRLF bytes |
| `features_by_run` | 296 ×4 baseline, 302 / 308 / 308 oracle; no duplicates; union 308 |
| Run-index `feature_sha256` | equals `osf.list_sha256` (`sha256("\n".join(features))`) for all 7 runs |
| CSV run-membership projection counts | match 296/302/308 |
| Runtime `~/.venvs/ipcch-geo/bin/python` | Python 3.12.3, XGBoost 3.2.0, NumPy 2.4.4, pandas 3.0.3, sklearn 1.8.0 (scipy 1.17.1); exit 0. 32 cores, 23 GB RAM, 16 GB swap |
| Config hashes | `forecasting_hyperparameters.json` 3742300…dd76, `_p3.json` cdc0e55…317b — match |
| Region map | 18ab509…611d — match |
| Parent manifest | 3b479c8…209bf — match; status COMPLETE; cohort eval hash f0193c1…2e0f, 5599/6064/5127/11415, 52,521 label keys (manifest values) |
| 23 parent-manifest inputs (10 sources incl. interim/climate monthly/seasonal/IDP/lookup/identifier/scope files, 4 datasets, 8 ledgers, cohort) | all sha256 match |
| Source headers | interim has sources 1–11 and exactly 19 `bbg_*` columns = pinned 5/3/2/9 members; climate monthly has all 13 retained `_month_ensmean`; seasonal has all 13 `_gs_ensmean` + `admin_code, season_year, season, gs_start_date, gs_end_date_exclusive` |

Commands: `sha256sum` on task files; Python `json`/`csv` contract checks; `hashlib` over manifest inputs (`/tmp/compact_preflight/hash_inputs.py`, log ALL_MATCH True); `python -c "import xgboost,numpy,pandas,sklearn"`.

## Not completed (must be done by the next executor)

- Row-level parent checks: keys identical across H0/3/6/12 and cohort; labels/shares equality; recompute label/eval key hashes from data.
- `osf.assert_history_ledger` / `assert_idp_ledger` on parent datasets.
- Extract the 63 background names from parent `run_metadata.json` (verify their sha256 vs `background_parent_metadata_sha256`) and compare with contract order; CSV `expected_model_positions` vs `features_by_run` order.
- Static/calendar invariance across horizons; identifier recomputation parity.
- Region-map coverage of all label/eval keys (0..8, unique area_id).
- Per-source nonmissing coverage/month ranges; seasonal s1/s2 pair scan; `rr.commodity_members` output == pinned members.
- GitNexus index freshness and `impact` for every symbol to be edited.
- Hash inventory of legacy inputs/results (no-overwrite baseline).

## Environment issue

`/tmp/ipcch-windows-git-bin` is on PATH but does not exist, so `git` resolves to `/usr/bin/git` 2.43.0. Windows Git exists at `/mnt/c/Program Files/Git/cmd/git.exe`.

## Implementation surfaces found (read-only)

- `src/ipcch/climate2015_features.py`: reusable `Grid.from_long/index_of`, `rolling`, `same_month_history` (strict earlier years; std count ≥ 2; `safe_divide` makes zero-SD NaN), `months_since`, `longest_run`, `stress_signals`/`STRESS_RULES` (spi03/tmean/evi), `last_completed_seasons` (stable end/start selection; returns no season identity/label — needs an identity-returning variant for the major dummy without changing default outputs).
- `src/ipcch/retained_feature_recipes.py`: `stress_signal` holds the D14 rules (GPP year-ago false-0, WFP zero/missing denominator false-0, conflict nonzero, ENSO |x|>0.5); `commodity_members`; carrier `row_exists` mask in `RetainedRecipes` (do **not** reuse for the compact block, per D16). Note the WB index is in `ORDINARY_SOURCES` with FAO/inflation, which the compact set drops.
- `src/ipcch/weather_oracle.py`: `raw_name`/`raw_features` give the exact contract oracle names and order; `calendar_lookup` does calendar-key lookup. B6 functions must stay unused.
- `src/ipcch/origin_safe.py`: history/IDP builders and ledger gates, `list_sha256`, `keys_sha256`, `origin_metrics`, `classify_cumulative`, `ARMS`.
- `scripts/modeling/run_deep_feature_weight_decay_forecasting.py`: `--arm` choices (line 135) and `load_origin_inputs` (lines 881–975) gate by manifest version (legacy vs `origin_safe_weather_oracle_v1`); a compact branch, namespace guard and compact code hashes in `fingerprint_payload` are needed. `run_origin_batch`, `verify_batch` and `run_origin_safe` are reusable unchanged.
- Suite pattern: `scripts/modeling/run_origin_safe_weather_oracle_suite.py` hardcodes version/plan, so a thin compact suite driver is needed.
- Regional scoring: `src/ipcch/regional_bootstrap.py` contains `align_paired_predictions`, but this task must not import bootstrap code. `evaluate_region3_saved_predictions.py` is region-3 only and bootstraps.
- Tests to extend: `tests/smoke/test_origin_safe_cli.py` (oracle version/arm gating tests at lines 180–266), `tests/unit/test_origin_safe_weather_oracle.py`, `tests/unit/test_climate2015_features.py`.
