"""Independent read-only check of the Somalia-local historical pilot (compact_baseline H0 / 2022).

Different path from the production script: reads the parent compact H0 dataset and cohort directly (hash-checked against
the parent manifest), rebuilds the expected SOM fitting/evaluation keys, cutoff, ages, weights and normalized targets,
reloads the four UBJ boosters with plain xgboost, replays raw predictions on the parent rows and recomputes classes from
the reloaded values. Also checks the local manifest SHA against the accepted preflight and the frozen snapshot digest.

Run from the repository root:
  PYTHONPATH=src /home/swl007007/.venvs/ipcch-geo/bin/python .trellis/tasks/10-09-somalia-local-compact-cds-test/research/pilot_check.py
"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

R = Path(".trellis/tasks/10-09-somalia-local-compact-cds-test/research")
A = Path("/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/Google fund/Analysis/1.Source Data/assembled_IPCCH")
PARENT = A / "model_ready/compact_climate_weather_oracle_v1/compact_climate_weather_oracle_v1_manifest.json"
LOOKUP = A / "country_area_id_lookup.csv"
HIST = Path("results/experiments/compact_climate_weather_oracle_v1_somalia_local")
LAUNCH = Path("results/launch/nowcasting_2026_04_compact_cds_v1_somalia_local")
RUN = HIST / "runs/compact_baseline/0m"
BATCH = RUN / "batches/2022"
KEYS = ["area_id", "year", "month"]
TARGETS = ("phase2_worse", "phase3_worse", "phase4_worse", "phase5_worse")
PREDS = ("phase2_pred", "phase3_pred", "phase4_pred", "phase5_pred")
SHARES = [f"phase{k}_percent" for k in range(1, 6)]
PREFLIGHT = {"hist_manifest_sha256": "573b0d0bb074a2de9251afacf549dfe18a30321af8bce87dfce75ac0644fe228",
             "frozen_digest": "25c451084d015d94cd4a90fff08347e88f898d1fdf8688cc7de7613b03bbef36", "frozen_files": 491,
             "feature_sha256": "e97388f848e7095bf0535f0cfee1a2d798e0c1863dee843462e60cf6a36f9909"}


def sha(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def keys_sha(frame) -> str:  # same order-sensitive key text hash as origin_safe.keys_sha256
    return hashlib.sha256("\n".join("|".join(str(v) for v in r) for r in frame[KEYS].itertuples(index=False, name=None)).encode()).hexdigest()


checks, info = {}, {}
parent = json.loads(PARENT.read_text())
entry = parent["horizons"]["0"]["arms"]["compact_baseline"]
checks["parent_dataset_sha"] = sha(entry["dataset"]["path"]) == entry["dataset"]["sha256"]
checks["parent_cohort_sha"] = sha(parent["cohort"]["path"]) == parent["cohort"]["sha256"]
feats = list(entry["features"])
checks["features_296_frozen"] = len(feats) == 296 and hashlib.sha256("\n".join(feats).encode()).hexdigest() == PREFLIGHT["feature_sha256"]
lookup = pd.read_csv(LOOKUP, keep_default_na=False, na_values=[""])
members = set(lookup.loc[lookup["iso3"] == "SOM", "area_id"].astype(int))
checks["members_905"] = len(members) == 905
data = pd.read_csv(entry["dataset"]["path"], float_precision="round_trip", low_memory=False)
cohort = pd.read_csv(parent["cohort"]["path"])
checks["dataset_rows_equal_cohort"] = data[KEYS].equals(cohort[KEYS])
som = data["area_id"].isin(members).to_numpy()
ords = data["year"].to_numpy() * 12 + data["month"].to_numpy() - 1
cutoff, origin = 2022 * 12 - 1, 2022 * 12  # H0: labels <= 2021-12, weights anchored at Jan 2022
shares = data[SHARES].to_numpy(dtype=float)
valid = np.isfinite(shares).all(axis=1) & (shares >= 0).all(axis=1) & (shares.sum(axis=1) > 0)
checks["share_valid_equals_cohort"] = np.array_equal(valid, cohort["share_valid"].to_numpy(dtype=bool))
fit_mask = valid & som & (ords <= cutoff)
eval_mask = cohort["eval_key"].to_numpy(dtype=bool) & som & (data["year"].to_numpy() == 2022)
want_fit, want_eval = data.loc[fit_mask, KEYS].reset_index(drop=True), data.loc[eval_mask, KEYS].reset_index(drop=True)
with np.errstate(invalid="ignore", divide="ignore"):
    norm = shares / shares.sum(axis=1, keepdims=True)
indep = np.column_stack([norm[:, k:].sum(axis=1) for k in (1, 2, 3, 4)])

# saved batch
record = json.loads((BATCH / "batch_record.json").read_text())
meta = json.loads((RUN / "run_metadata.json").read_text())
local_manifest = HIST / "inputs" / "compact_climate_weather_oracle_v1_somalia_local_manifest.json"
checks["local_manifest_sha_equals_preflight"] = sha(local_manifest) == PREFLIGHT["hist_manifest_sha256"]
checks["run_metadata_partial_pilot"] = meta["status"] == "PARTIAL" and [b["block_year"] for b in meta["batches"]] == [2022] \
    and meta["local_manifest"]["sha256"] == PREFLIGHT["hist_manifest_sha256"] and meta["local_version"] == "compact_climate_weather_oracle_v1_somalia_local"
checks["fingerprint_consistent"] = record["fingerprint"] == meta["fingerprint"] == meta["batches"][0]["fingerprint"] \
    and meta["fingerprint_payload"]["local_manifest_sha256"] == PREFLIGHT["hist_manifest_sha256"] \
    and meta["fingerprint"] != meta["fingerprint_payload"]["parent_fingerprint"]
checks["artifact_set_and_hashes"] = set(record["artifacts"]) == {"predictions.csv", "fit_keys.csv.gz", *(f"model_{t}.ubj" for t in TARGETS)} \
    and all(sha(BATCH / n) == d for n, d in record["artifacts"].items()) and sorted(p.name for p in BATCH.iterdir()) == sorted([*record["artifacts"], "batch_record.json"])
fk = pd.read_csv(BATCH / "fit_keys.csv.gz", float_precision="round_trip")
checks["fit_keys_complete_som_set"] = fk[KEYS].equals(want_fit) and fk["area_id"].isin(members).all()
fords = fk["year"].to_numpy() * 12 + fk["month"].to_numpy() - 1
checks["fit_age_weight"] = np.array_equal(fk["age_months"].to_numpy(), origin - fords) and \
    np.allclose(fk["sample_weight"].to_numpy(), 0.5 ** ((origin - fords) / 24.0), rtol=0, atol=1e-15)
checks["fit_targets_finite"] = np.isfinite(indep[fit_mask]).all()
info["fit"] = {"rows": len(fk), "areas": int(fk["area_id"].nunique()), "max_label": f"{fords.max() // 12}-{fords.max() % 12 + 1:02d}",
               "min_label": f"{fords.min() // 12}-{fords.min() % 12 + 1:02d}", "keys_sha256": keys_sha(fk), "record_keys_sha256": record["fit_keys_sha256"],
               "weight_range": [float(fk["sample_weight"].min()), float(fk["sample_weight"].max())], "label_cutoff": record["fit_label_cutoff_month"]}
checks["fit_counts_901_139_max_2021_07"] = len(fk) == 901 and fk["area_id"].nunique() == 139 and info["fit"]["max_label"] == "2021-07" \
    and record["fit_label_cutoff_month"] == "2021-12" and keys_sha(fk) == record["fit_keys_sha256"]
pred = pd.read_csv(BATCH / "predictions.csv", float_precision="round_trip")
checks["eval_keys_complete_1129"] = pred[KEYS].equals(want_eval) and len(pred) == 1129 and keys_sha(pred) == record["eval_keys_sha256"]
rows = pd.MultiIndex.from_frame(data[KEYS]).get_indexer(pd.MultiIndex.from_frame(pred[KEYS]))
checks["truth_and_targets"] = np.array_equal(data["overall_phase"].to_numpy(dtype=float)[rows], pred["overall_phase"].to_numpy(dtype=float)) and \
    np.allclose(indep[rows], pred[list(TARGETS)].to_numpy(dtype=float), rtol=0, atol=1e-12)
X = data.iloc[rows][feats]
replayed, models = {}, {}
for target, column in zip(TARGETS, PREDS):
    b = xgb.Booster()
    b.load_model(str(BATCH / f"model_{target}.ubj"))
    again = b.predict(xgb.DMatrix(X, feature_names=feats)).astype(float)
    replayed[column] = again
    models[target] = {"sha256": sha(BATCH / f"model_{target}.ubj"), "bytes": (BATCH / f"model_{target}.ubj").stat().st_size,
                      "feature_names_equal_manifest": list(b.feature_names) == feats, "num_features": b.num_features(),
                      "boosted_rounds": b.num_boosted_rounds(), "max_abs_replay_diff": float(np.abs(again - pred[column].to_numpy(dtype=float)).max()),
                      "finite": bool(np.isfinite(again).all())}
checks["boosters_schema_296"] = all(m["feature_names_equal_manifest"] and m["num_features"] == 296 for m in models.values())
checks["raw_replay_within_1e-6"] = all(m["max_abs_replay_diff"] <= 1e-6 and m["finite"] for m in models.values())


def classes(frame):
    s = frame[list(PREDS)].to_numpy(dtype=float)
    return np.select([s[:, 3] >= 0.2, s[:, 2] >= 0.2, s[:, 1] >= 0.2, s[:, 0] >= 0.2], [5, 4, 3, 2], default=1)


checks["classes_saved_rule"] = np.array_equal(classes(pred), pred["overall_phase_pred"].to_numpy())
checks["classes_from_reloaded_exact"] = np.array_equal(classes(pd.DataFrame(replayed)), pred["overall_phase_pred"].to_numpy())
checks["row_origin_and_cutoff_columns"] = (pred["fit_origin_month"] == "2022-01").all() and (pred["fit_label_cutoff_month"] == "2021-12").all() \
    and (pred["horizon"] == 0).all() and (pred["arm"] == "compact_baseline").all()
info["eval"] = {"rows": len(pred), "areas": int(pred["area_id"].nunique()), "keys_sha256": keys_sha(pred),
                "class_counts": {int(k): int(v) for k, v in pred["overall_phase_pred"].value_counts().sort_index().items()},
                "observed_counts": {int(k): int(v) for k, v in pred["overall_phase"].value_counts().sort_index().items()}}
info["models"] = models
info["batch_record"] = {k: record[k] for k in ("fit_rows", "eval_rows", "fit_seconds", "batch_seconds", "peak_rss_mb", "fit_origin_month", "fit_label_cutoff_month")}
info["fingerprint"] = meta["fingerprint"]
info["parent_fingerprint"] = meta["fingerprint_payload"]["parent_fingerprint"]
# only the pilot was fitted; frozen snapshot preserved for later comparison
checks["only_pilot_batch_exists"] = sorted(str(p.relative_to(HIST / "runs")) for p in (HIST / "runs").rglob("batch_record.json")) == ["compact_baseline/0m/batches/2022/batch_record.json"]
checks["no_launch_fit"] = not (LAUNCH / "runs").exists() and not (LAUNCH / "inputs").exists()
snaps = [HIST / "preflight/frozen_inventory_before.csv", LAUNCH / "preflight/frozen_inventory_before.csv"]
snap = pd.read_csv(snaps[0])
checks["frozen_snapshot_491_matches_preflight"] = all(p.exists() for p in snaps) and snaps[0].read_bytes() == snaps[1].read_bytes() \
    and len(snap) == PREFLIGHT["frozen_files"] and sha(snaps[0]) == PREFLIGHT["frozen_digest"]
checks = {k: bool(v) for k, v in checks.items()}
result = {"passed": all(checks.values()), "checks": checks, **info}
(R / "pilot-independent-check.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({"passed": result["passed"], "failed": [k for k, v in checks.items() if not v], "fit": info["fit"], "eval": info["eval"],
                  "max_replay": max(m["max_abs_replay_diff"] for m in models.values())}, indent=1))
sys.exit(0 if result["passed"] else 1)
