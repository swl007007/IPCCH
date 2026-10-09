"""Independent replay check of one fitted compact_cds_launch_v1 run (default: the shared H0 pilot).

Read-only, frozen model interpreter. Reloads the four saved UBJ boosters with plain xgboost, checks the fitted feature
order against the contract/manifest, re-predicts the saved raw inference matrix and the manifest inference CSV, compares
raw predictions (<= 1e-6) and re-derived classes (exact, own top-down rule), and checks every saved fit artifact against
the manifest inputs (keys, targets, weights recomputed from the decay rule, raw matrix) and artifact_record hashes.

Run from the repository root:
  PYTHONPATH=src /home/swl007007/.venvs/ipcch-geo/bin/python .trellis/tasks/10-08-compact-cds-launch/research/pilot_replay_check.py [run_id]
"""
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

RID = sys.argv[1] if len(sys.argv) > 1 else "compact_baseline/0m"
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(".trellis/tasks/10-08-compact-cds-launch/research/pilot-check.json")
IR = Path("../../../1.Source Data/assembled_IPCCH/model_ready/compact_cds_launch_v1")
RES = Path("results/launch/nowcasting_2026_04_compact_cds_v1")
MANIFEST = IR / "compact_cds_launch_v1_manifest.json"
KEYS = ["area_id", "year", "month"]
TARGETS = ("phase2_worse", "phase3_worse", "phase4_worse", "phase5_worse")
PREDS = ("phase2_pred", "phase3_pred", "phase4_pred", "phase5_pred")
ORIGIN_ORD, HALF_LIFE, THRESHOLD, TOL = 2026 * 12 + 3, 24.0, 0.2, 1e-6


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def read(p):
    return pd.read_csv(p, float_precision="round_trip", low_memory=False)


def classify(frame):
    out = np.ones(len(frame), dtype=int)
    for phase in (2, 3, 4, 5):  # bottom-up overwrite == top-down first hit
        out[frame[f"phase{phase}_pred"].to_numpy(dtype=float) >= THRESHOLD] = phase
    return out


t0 = time.time()
m = json.loads(MANIFEST.read_text())
entry = m["runs"][RID]
run_dir = RES / "runs" / entry["arm"] / f"{entry['horizon']}m"
feats = entry["features"]
contract = pd.read_csv(IR / "approved_spec" / "expected_feature_contract.csv", keep_default_na=False)
checks, info = {}, {"run_id": RID, "run_dir": str(run_dir), "manifest_sha256": sha(MANIFEST)}

# artifact record and metadata
record = json.loads((run_dir / "artifact_record.json").read_text())
meta = json.loads((run_dir / "run_metadata.json").read_text())
checks["artifact_hashes_match"] = all(sha(run_dir / n) == h for n, h in record["artifacts"].items())
EXPECTED = {"feature_schema.json", "fit_keys.csv.gz", "fit_targets.csv.gz", "fit_weights.csv.gz", "inference_features.csv.gz",
            "predictions_raw.csv", "run_metadata.json", *(f"model_{t}.ubj" for t in TARGETS)}
on_disk = {q.name for q in run_dir.iterdir() if q.is_file()} - {"artifact_record.json"}
checks["artifact_set_complete"] = set(record["artifacts"]) == EXPECTED == on_disk  # 6 fit files + 4 UBJ + metadata = 11
checks["metadata_complete"] = meta["status"] == "COMPLETE" and meta["fingerprint"] == record["fingerprint"]
info.update({"artifacts": record["artifacts"], "fingerprint": record["fingerprint"], "git_head": meta["git_head"],
             "git_status_porcelain": meta["git_status_porcelain"], "fit_seconds": meta["fit_seconds"], "run_seconds": meta["run_seconds"],
             "peak_rss_mb_self": meta["peak_rss_mb"], "hyperparameters": meta["hyperparameters"],
             "hyperparameters_effective": meta["hyperparameters_effective"]})
hp = json.loads(Path("configs/forecasting_hyperparameters.json").read_text())
hp3 = json.loads(Path("configs/forecasting_hyperparameters_p3.json").read_text())
eff = meta["hyperparameters_effective"]
checks["hyperparameters_are_config_plus_njobs16"] = eff["phase2/4/5"] == dict(hp, n_jobs=16) and eff["phase3"] == dict(hp3, n_jobs=16)

# feature schema / contract order
schema = json.loads((run_dir / "feature_schema.json").read_text())
run_col = [c for c in contract.columns if c.lower() in ("run_id", "run")]
checks["schema_equals_manifest_features"] = schema["features"] == feats and schema["feature_count"] == len(feats)
info["contract_columns"] = list(contract.columns)

# fit artifacts vs manifest fit selection
sel = read(entry["fit_selection"]["path"])
keys = pd.read_csv(run_dir / "fit_keys.csv.gz")
tgt = pd.read_csv(run_dir / "fit_targets.csv.gz", float_precision="round_trip")
wts = pd.read_csv(run_dir / "fit_weights.csv.gz", float_precision="round_trip")
checks["fit_keys_equal_selection"] = keys[KEYS + ["fit_ord"]].equals(sel[KEYS + ["fit_ord"]])
checks["fit_targets_equal_selection"] = all(np.array_equal(tgt[t].to_numpy(float), sel[t].to_numpy(float)) for t in TARGETS) and tgt[KEYS].equals(sel[KEYS])
checks["fit_label_months_before_2026_04"] = int(keys["fit_ord"].max()) < ORIGIN_ORD
w_rule = 0.5 ** ((ORIGIN_ORD - keys["fit_ord"].to_numpy(float)) / HALF_LIFE)
checks["fit_weights_equal_selection"] = np.array_equal(wts["sample_weight"].to_numpy(float), sel["sample_weight"].to_numpy(float))
info["weights_max_abs_vs_independent_rule"] = float(np.abs(wts["sample_weight"].to_numpy(float) - w_rule).max())
checks["fit_weights_match_independent_rule_1e-12"] = info["weights_max_abs_vs_independent_rule"] <= 1e-12
info.update({"fit_rows": len(keys), "fit_label_ord_range": [int(keys.fit_ord.min()), int(keys.fit_ord.max())],
             "weight_range": [float(wts.sample_weight.min()), float(wts.sample_weight.max())]})

# raw inference matrix vs manifest inference CSV
raw = pd.read_csv(run_dir / "inference_features.csv.gz", float_precision="round_trip", low_memory=False)
inf = read(entry["inference"]["path"])
checks["raw_matrix_columns_keys_plus_contract"] = list(raw.columns) == KEYS + feats
checks["raw_matrix_equals_manifest_inference"] = raw.shape == inf.shape and all(
    np.array_equal(raw[c].to_numpy(float), inf[c].to_numpy(float), equal_nan=True) for c in raw.columns)

# reload boosters, check order, re-predict
pred = pd.read_csv(run_dir / "predictions_raw.csv", float_precision="round_trip", low_memory=False)
checks["prediction_keys_equal_inference"] = pred[KEYS].equals(inf[KEYS]) and len(pred) == 6188
replay, boosters = {}, {}
for t, col in zip(TARGETS, PREDS):
    b = xgb.Booster()
    b.load_model(run_dir / f"model_{t}.ubj")
    boosters[t] = {"feature_names_equal_contract": list(b.feature_names) == feats, "num_features": b.num_features(),
                   "num_boosted_rounds": b.num_boosted_rounds()}
    d_raw = xgb.DMatrix(raw[feats], feature_names=feats)
    d_inf = xgb.DMatrix(inf[feats], feature_names=feats)
    r1, r2 = b.predict(d_raw).astype(float), b.predict(d_inf).astype(float)
    saved = pred[col].to_numpy(float)
    boosters[t]["max_abs_saved_vs_reload_raw"] = float(np.abs(saved - r1).max())
    boosters[t]["max_abs_saved_vs_reload_manifest_matrix"] = float(np.abs(saved - r2).max())
    boosters[t]["finite"] = bool(np.isfinite(saved).all())
    replay[col] = r1
checks["booster_feature_order_all"] = all(v["feature_names_equal_contract"] for v in boosters.values())
checks["raw_predictions_within_1e-6"] = all(max(v["max_abs_saved_vs_reload_raw"], v["max_abs_saved_vs_reload_manifest_matrix"]) <= TOL for v in boosters.values())
checks["predictions_finite"] = all(v["finite"] for v in boosters.values())
replay_cls = classify(pd.DataFrame(replay))
checks["classes_exact_saved_vs_independent_rederivation"] = np.array_equal(classify(pred), pred["overall_phase_pred"].to_numpy())
checks["classes_exact_saved_vs_reload"] = np.array_equal(replay_cls, pred["overall_phase_pred"].to_numpy())
checks["run_columns"] = list(pred.columns[:7]) == KEYS + ["run_id", "horizon", "origin_month", "target_month"] and \
    (pred.run_id == RID).all() and (pred.target_month == entry["target_month"]).all() and (pred.origin_month == "2026-04").all()
info["boosters"] = boosters
info["class_counts"] = {int(k): int(v) for k, v in pred["overall_phase_pred"].value_counts().sort_index().items()}
info["raw_prediction_summary"] = {c: {"min": float(pred[c].min()), "mean": float(pred[c].mean()), "max": float(pred[c].max())} for c in PREDS}
info["cumulative_monotone_rows_violating"] = int(((pred.phase2_pred < pred.phase3_pred) | (pred.phase3_pred < pred.phase4_pred) |
                                                  (pred.phase4_pred < pred.phase5_pred)).sum())
checks = {k: bool(v) for k, v in checks.items()}
result = {"mode": "independent replay (read-only)", "checked_utc": pd.Timestamp.now(tz="UTC").isoformat(), "passed": all(checks.values()),
          "checks": checks, **info, "elapsed_s": round(time.time() - t0, 1)}
OUT.write_text(json.dumps(result, indent=2, default=str))
print(json.dumps({"passed": result["passed"], "checks": checks, "class_counts": info["class_counts"],
                  "max_abs": {t: v["max_abs_saved_vs_reload_raw"] for t, v in boosters.items()}}, indent=1))
sys.exit(0 if result["passed"] else 1)
