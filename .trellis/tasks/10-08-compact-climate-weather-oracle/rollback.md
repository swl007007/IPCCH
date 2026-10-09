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
