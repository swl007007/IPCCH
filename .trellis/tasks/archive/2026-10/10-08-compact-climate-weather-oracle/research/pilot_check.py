"""Pilot checks for compact_baseline/0m block 2022 (first batch of the suite)."""
import hashlib, importlib.util, json, sys
from pathlib import Path
import numpy as np, pandas as pd, xgboost as xgb
sys.path.insert(0, "src")
from ipcch import compact_features as cpf, origin_safe as osf, paths
spec = importlib.util.spec_from_file_location("cv", "scripts/postprocessing/verify_compact_climate_weather_oracle.py")
cv = importlib.util.module_from_spec(spec); spec.loader.exec_module(cv)
ov, legacy = cv.ov, cv.legacy
P = []
man_path = cv.MANIFEST
man = json.loads(man_path.read_text())
run = cv.run_dir("compact_baseline", 0); b = run / "batches" / "2022"
meta = json.loads((run / "run_metadata.json").read_text()); rec = json.loads((b / "batch_record.json").read_text())
feat = man["horizons"]["0"]["arms"]["compact_baseline"]["features"]
want = cpf.fingerprint_payload(man, legacy.sha(man_path), "compact_baseline", 0,
                               {k: ov.FROZEN["protocol"][k] for k in ("seed", "half_life_months", "phase_threshold", "n_jobs")},
                               cpf.fit_code_sha256(paths.PROJECT_ROOT), cpf.runtime_identity())
digest = hashlib.sha256(json.dumps(want, sort_keys=True).encode()).hexdigest()
if meta["fingerprint_payload"] != json.loads(json.dumps(want)) or meta["fingerprint"] != digest or rec["fingerprint"] != digest: P.append("fingerprint")
if meta["features"] != feat or rec["feature_sha256"] != osf.list_sha256(feat): P.append("feature order")
inv = {}
for name, sha in rec["artifacts"].items():
    inv[name] = legacy.sha(b / name)
    if inv[name] != sha: P.append(f"hash {name}")
if set(rec["artifacts"]) != legacy.REQUIRED_ARTIFACTS: P.append("artifact set")
data = pd.read_csv(man["horizons"]["0"]["arms"]["compact_baseline"]["dataset"]["path"], float_precision="round_trip", low_memory=False)
cohort = pd.read_csv(man["cohort"]["path"])
labels = ov.load_labels(data, cohort)
valid = cohort["share_valid"].to_numpy(bool)
fk = pd.read_csv(b / "fit_keys.csv.gz", float_precision="round_trip")
ref = pd.read_csv(cv.PARENT_RUNS / "0m" / "batches" / "2022" / "fit_keys.csv.gz", float_precision="round_trip")
if not fk.equals(ref): P.append("fit keys/ages/weights differ from parent reference protocol")
cut = 2022 * 12 - 1; origin = 2022 * 12
exp_fit = labels.loc[valid & (labels["ord"] <= cut).to_numpy(), ["area_id", "year", "month"]].reset_index(drop=True)
ford = fk.year * 12 + fk.month - 1
if not fk[["area_id", "year", "month"]].equals(exp_fit) or not np.allclose(fk.sample_weight, 0.5 ** ((origin - ford) / 24.0), rtol=0, atol=1e-15) \
        or (fk.age_months != origin - ford).any(): P.append("fit rows/weights")
pred = pd.read_csv(b / "predictions.csv", float_precision="round_trip")
ek = cohort.loc[cohort.eval_key & (cohort.year == 2022), ["area_id", "year", "month"]].reset_index(drop=True)
if not pred[["area_id", "year", "month"]].equals(ek): P.append("eval keys")
pos = pd.MultiIndex.from_frame(data[["area_id", "year", "month"]]).get_indexer(pd.MultiIndex.from_frame(pred[["area_id", "year", "month"]]))
lab = labels.iloc[pos]
if not np.array_equal(lab.overall_phase.to_numpy(float), pred.overall_phase.to_numpy(float)) or \
        not np.allclose(lab[list(osf.CUMULATIVE_TARGETS)].to_numpy(), pred[list(osf.CUMULATIVE_TARGETS)].to_numpy(), rtol=0, atol=1e-12): P.append("truth/targets")
if not np.array_equal(legacy.classes(pred, 0.2), pred.overall_phase_pred.to_numpy()): P.append("class rule")
X = data.iloc[pos][feat]; maxdiff = 0.0
for t, c in zip(osf.CUMULATIVE_TARGETS, osf.PRED_COLUMNS):
    bst = xgb.Booster(); bst.load_model(str(b / f"model_{t}.ubj"))
    if list(bst.feature_names) != feat: P.append(f"{t} booster feature names")
    d = float(np.max(np.abs(bst.predict(xgb.DMatrix(X, feature_names=feat)) - pred[c].to_numpy()))); maxdiff = max(maxdiff, d)
    if d > 1e-6: P.append(f"{t} replay {d}")
m_run = osf.flatten_origin_metrics(osf.origin_metrics(pred, "overall", 2022)); m_sk = legacy.replay(pred)
for m in osf.ORIGIN_METRICS:
    a, c = m_run[m], m_sk[m]
    if (a is None) != (c is None) or (a is not None and abs(a - c) > 1e-12): P.append(f"metric {m}")
ref_pred = pd.read_csv(cv.PARENT_RUNS / "0m" / "batches" / "2022" / "predictions.csv", float_precision="round_trip")
ref_m = legacy.replay(ref_pred)
out = {"passed": not P, "problems": P, "fingerprint": digest, "models_reloaded": 4, "max_model_replay_abs_diff": maxdiff,
       "fit_rows": len(fk), "eval_rows": len(pred), "artifact_sha256": inv, "batch_seconds": rec["batch_seconds"], "peak_rss_mb": rec["peak_rss_mb"],
       "metrics_compact_baseline_h0_2022": {m: m_sk[m] for m in osf.ORIGIN_METRICS},
       "context_old_full_reference_h0_2022": {m: ref_m[m] for m in osf.ORIGIN_METRICS}}
json.dump(out, open(sys.argv[1], "w"), indent=2, default=float)
print(json.dumps(out, indent=1, default=float))
