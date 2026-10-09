# compact_cds_launch_v1: implementation and input checkpoint (Stage 3), 2026-10-09

Status: **real inputs assembled and all prefit gates pass. No fitting has been performed.** Fitting stays closed until the
supervisor authorizes the Codex Windows-Git implementation commit and the shared H0 pilot. The remaining four fits stay closed
after that.

Machine-readable record: `research/input-checkpoint.json` (generated from the manifest, provenance and logs).

## Code pins (match the build manifest; no source edit since)

| file | sha256 |
|---|---|
| src/ipcch/compact_launch.py | ed10b701bdfb86624fca4f0975c81e677819db048ed7473d0ade3c4efb4f992d |
| src/ipcch/cds_launch_weather.py | be74e2a3f87d124b26c7fd7440dd5c52ad516dc1b8bcd5ff84aaf750cf755e33 |
| scripts/preprocessing/build_compact_cds_launch_inputs.py | 21609b085a29db895e8ec73339fdfd69ecc11a2d3f231f727197f59ba880ad78 |
| scripts/modeling/run_compact_cds_launch.py | c58be4f4336bd3940c4bfe826796f3354a866d119283188a8651fbea08216db4 |
| tests/unit/test_compact_launch.py | bb0300c3b4946eed4a1b1cf0d4892bcbc67cb07e8770c5884b452669fe105379 |

- Focused tests: **32 passed** (unit compact_launch, CLI smoke, unit weather).
- Runtime: frozen model env `/home/swl007007/.venvs/ipcch-geo/bin/python`, with Python 3.12.3, NumPy 2.4.4, pandas 3.0.3,
  sklearn 1.8.0 and XGBoost 3.2.0.
- The manifest records git HEAD b19d36d.

## Round-trip fix (supervisor-preferred narrow form)

- `save_csv` reads the file back for checking only. Every column that is not numeric in the in-memory frame is read as
  `dtype=str`, and only empty fields count as missing.
- CSV bytes are unchanged.
- `same_frame` is restored to bitwise comparison for numeric columns and text comparison otherwise.
- The broader `_numeric_or_none` comparator was removed.
- Impact order is recorded honestly in `research/gitnexus-impact-roundtrip-fix.md`:
  - The first edit came before its impact call.
  - The revision came after impact(save_csv) returned "not found" (the module is unindexed).

## Assembly history

| attempt | outcome |
|---|---|
| 1 | Exit 1 at the `history_h0.csv` round-trip check: object int/None IDs were read back as float. Log: `logs/assemble_attempt1_failed_roundtrip.log`. |
| 2 | `_numeric_or_none` comparator. Stopped with SIGTERM (exit 143) before the ledgers were written. Log: `logs/assemble_attempt2_superseded_stopped.log`. |
| **3** | **Exit 0.** Wall time 4:24.32, max RSS 2.9 GB. COMPLETE manifest. Log: `logs/assemble_attempt3.log`. |

- All 11 files that attempt 1 wrote are **byte-identical** in attempt 3:
  - 5 fit selections;
  - 5 inference matrices;
  - `history_h0.csv` itself.
- Pins: `logs/assemble_attempt1_partial_outputs_sha256.txt` and `logs/assemble_attempt3_code_sha256.txt`.

Manifest: `assembled_IPCCH/model_ready/compact_cds_launch_v1/compact_cds_launch_v1_manifest.json`, sha256
**b2e73812cb8adc34356447b5785db10e6cb04481c303e97550421488f6c5cafe** (the supervisor's acceptance cites the same hash).

## Run plan in the manifest (exactly 5 runs)

| run | training arm | target | features | fit rows (labels) | inference |
|---|---|---|---:|---|---|
| compact_baseline/0m | compact_baseline | 2026-04 | 296 | 49,532 (2014-01..2026-03) | 6188 × 299 |
| compact_baseline/6m | compact_baseline | 2026-10 | 296 | 49,532 | 6188 × 299 |
| compact_baseline/12m | compact_baseline | 2027-04 | 296 | 49,532 | 6188 × 299 |
| compact_cds_weather/6m | compact_weather_oracle | 2026-10 | 308 | 49,532 | 6188 × 311 (CDS cube) |
| compact_cds_weather/12m | compact_weather_oracle | 2027-04 | 308 | 49,532 | 6188 × 311 (CDS cube) |

- All five fit selections are byte-identical (sha256 bb08f69a…), with one fit-key hash (1c55e510…).
- Feature lists match the literal contract and its order:
  - CSV 6a16ccd4…, metadata 6295074f…, run index 25fff00d….
  - Baseline feature hash e97388f8…; weather feature hash 3e54c449….
- Training settings:
  - Labels are restricted to months before 2026-04-01.
  - Weight = `0.5 ** ((2026-04 - U)/24)`, where U is the label month.
  - Seed 42, threshold 0.2, n_jobs 16, independent P3 config (applied at fit time).

## Manifest checks (all true or zero)

- **Future perturbation:** 233 features checked, 0 cells changed. The perturbation covered source months after 2026-04 and
  seasons ending after 2026-05-01.
- **Inference history:**
  - 6188 rows per target.
  - 17,771 history values present.
  - 2774 April-or-later observations excluded; history uses reports through 2026-03 only.
- **IDP:** present for 5650 of 6188 areas.
- **Season ledger:** 6188 rows.
- **Cohort and population:**
  - Cohort is all 6188 areas.
  - Population total is 2,106,501,620.66, with 6 zero-population areas.
- **Inference matrices:**
  - Non-calendar inputs are identical across targets.
  - Each weather matrix's prefix equals the baseline matrix.
  - H0 identifiers equal the `add_identifier` features.
  - All 2027 year flags are false.
  - Paired training selections are identical.

## Weather (accepted v3, unchanged)

- Files:
  - Cube sha256 8745e7af…; provenance 408e8090…; status ACCEPTED.
  - Bounds (frozen before comparison) 8db6bda0….
- September overlap gate at 6227 points / 1398 cells:

  | variable | max abs diff | frozen bound | points over |
  |---|---:|---:|---:|
  | temperature | 0.000551 K | 0.002259 K | 0 |
  | precipitation | 0.011 mm/month | 0.249 mm/month | 0 |

- Temperature convention: (month start 00 UTC, next month start 00 UTC], end_inclusive.
  - This was empirically verified for the supplied system51 September data.
  - Official primary documents do not state which boundary sample is included.
- Negative tp increments in the source are recorded as a diagnostic and are listed under the provenance limitations.
- The supervisor's independent October reduction check gave a 0 difference.

## Validate-only

- Command: `run_compact_cds_launch.py --validate-only`.
- Result: exit 0, 0:45.06. All inputs and prefit gates passed for the 5 runs (296/296/296/308/308 features). Nothing was written.
- Log: `results/launch/nowcasting_2026_04_compact_cds_v1/logs/validate_only_attempt3.log`.

## Next (requires supervisor authorization)

1. Codex makes the Windows-Git implementation commit.
2. Shared H0 pilot (`--approve-training --runs compact_baseline/0m`) with replay.
3. The remaining 4 fits stay closed until separately authorized.
