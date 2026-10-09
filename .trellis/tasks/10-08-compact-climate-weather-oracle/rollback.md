# Feature-version rollback contract

Status: planning; selection examples describe current legacy flags and the compact integration requirement. No rollback or refit has been run. Implementation must append its pinned commit, final paths and successful selection checks here.

## Preserved versions

External source root: `C:/Users/swl00/IFPRI Dropbox/Weilun Shi/Google fund/Analysis/1.Source Data/assembled_IPCCH/model_ready`.

| Feature version | Manifest relative to source root | Arm | H | Saved result root |
|---|---|---|---|---|
| Previous full baseline | `origin_safe_climate_idp_v1/origin_safe_climate_idp_v1_manifest.json` | `climate_safe_history_idp` | 0,3,6,12 | `results/experiments/origin_safe_climate_idp_v1/runs/climate_safe_history_idp` |
| Previous full baseline + raw oracle | `origin_safe_weather_oracle_v1/origin_safe_weather_oracle_v1_manifest.json` | `climate_safe_history_idp_oracle` | 3,6,12 | `results/experiments/origin_safe_weather_oracle_v1/runs/climate_safe_history_idp_oracle` |
| Compact baseline, planned | `compact_climate_weather_oracle_v1/compact_climate_weather_oracle_v1_manifest.json` | `compact_baseline` | 0,3,6,12 | `results/experiments/compact_climate_weather_oracle_v1/runs/compact_baseline` |
| Compact + raw oracle, planned | Same compact manifest | `compact_weather_oracle` | 3,6,12 | `results/experiments/compact_climate_weather_oracle_v1/runs/compact_weather_oracle` |

H0 oracle uses the corresponding version's baseline. Existing B6 artifacts remain untouched but are excluded from this experiment.

## How selection works

The existing `scripts/modeling/run_deep_feature_weight_decay_forecasting.py` supports `--protocol origin-safe --origin-manifest <explicit manifest> --horizon <H> --arm <matching arm> --out-dir <new output directory>`. This interface must continue to select the legacy schemas, and must explicitly admit the compact schema after implementation. Use `--dry-run` plus the frozen numerical/configuration settings to validate selection without producing outputs. These flags were inspected in source; a final compact invocation has not yet been implemented or tested.

For viewing previous results, select the explicit saved result path; no model execution is needed. A refit of old features must use a fresh output directory and current truthful code identity. Do not resume old fitted directories with a modified runner or overwrite their fingerprints. No full legacy refit is authorized as part of the seven-run compact comparison.

Freeze the compact spec, contract, recipe commit, input manifest/source hashes and completed results. Later feature revisions require another namespace; returning to this compact version must be possible by selecting its pinned artifacts. No global mutable feature list, destructive Git reset or copied-over input files are required for rollback.

## Completion checks to record

- Legacy and compact manifest/arm/schema selection checks, including rejection of cross-version combinations.
- Final compact input manifest, ordered schema hashes and implementation commit.
- Hash inventory proving old input/result artifacts were not overwritten.
- Actual dry-run selection commands and results; these planning checkboxes are not validation evidence.

## Execution appendix: frozen implementations and selection

The preceding section is the approved planning snapshot. Its original bytes have SHA256
`37936290977a11d1865d3e6172247a0e64c677b02cfcbafca0cb66135b1de1c8` and remain retrievable from planning commit
`928d08081376311b298358cbad5eb8b21ad7fc35`. This appendix records execution; it does not change the frozen expected contract.

- Compact implementation commit: `40060dd4135cd301347f63ffddaa63384b07264c`.
- Final input build2 manifest: `compact_climate_weather_oracle_v1/compact_climate_weather_oracle_v1_manifest.json`,
  SHA256 `456360536a3929e1571d96ba9f16e2f0de54bc1b20019f797bbe62c0c89732ca` relative to the external source root above.
- Archive-safe expected contract, run index and schema metadata are byte-frozen in
  `compact_climate_weather_oracle_v1/contract/`. Their approved source paths are provenance only; selecting the version
  does not require the active Trellis task directory to exist.
- Actual legacy selection checks passed: baseline/H0=870 columns and raw-oracle/H3=876 columns; exit0 and no output
  directory created. Exact executed argv, stdout and no-write checks: `research/legacy-selection-dry-runs.json`.
- Actual compact seven-run selection passed: baseline296; oracle302/308/308; exit0 and no results changes.
  Exact executed suite output: `research/suite_dry_run_build2.txt`.
- All seven compact runs now record COMPLETE, with28 annual batches and112 saved UBJ models. The pilot was resumed
  exactly, without refitting. Final numerical replay and report acceptance are recorded separately in task evidence.

To reproduce the validated selection checks from the repository root (WSL shell, frozen Python), set:

```bash
IPCCH_MODEL_ROOT='/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/Google fund/Analysis/1.Source Data/assembled_IPCCH/model_ready'
IPCCH_PYTHON='/home/swl007007/.venvs/ipcch-geo/bin/python'
export PYTHONPATH=src
```

Previous full baseline selection:

```bash
"$IPCCH_PYTHON" scripts/modeling/run_deep_feature_weight_decay_forecasting.py --protocol origin-safe --origin-manifest "$IPCCH_MODEL_ROOT/origin_safe_climate_idp_v1/origin_safe_climate_idp_v1_manifest.json" --arm climate_safe_history_idp --horizon 0 --out-dir results/experiments/compact_climate_weather_oracle_v1/selection_dry_run_climate_safe_history_idp --half-life-months 24 --phase-threshold 0.2 --seed 42 --n-jobs 16 --dry-run
```

Previous full baseline plus raw oracle selection:

```bash
"$IPCCH_PYTHON" scripts/modeling/run_deep_feature_weight_decay_forecasting.py --protocol origin-safe --origin-manifest "$IPCCH_MODEL_ROOT/origin_safe_weather_oracle_v1/origin_safe_weather_oracle_v1_manifest.json" --arm climate_safe_history_idp_oracle --horizon 3 --out-dir results/experiments/compact_climate_weather_oracle_v1/selection_dry_run_climate_safe_history_idp_oracle --half-life-months 24 --phase-threshold 0.2 --seed 42 --n-jobs 16 --dry-run
```

All seven compact selections (the driver explicitly selects the compact manifest and its two arms):

```bash
"$IPCCH_PYTHON" scripts/modeling/run_compact_climate_weather_oracle_suite.py --dry-run
```

For an individual compact selection, use the same trainer flags with the compact manifest, `--arm compact_baseline`
at H0/3/6/12 or `--arm compact_weather_oracle` at H3/6/12, and an explicit output path. The supplied selection examples
use `--dry-run`; they do not train or write files. A future authorized legacy refit must use a fresh output directory:
the integrated runner's code fingerprint differs from the older fitted runs. To view any previous version, read its
saved result path directly. To return to this compact version, select its frozen manifest and matching saved outputs;
do not reset Git or copy new inputs over old ones.

Build1 failed independent numeric verification and is retained under the separate superseded-build1 namespaces.
Use only the build2 manifest above. Both input builds truthfully record planning HEAD928d080 plus uncommitted build
code; model fitting used committed implementation40060dd. Do not rewrite either provenance record.
