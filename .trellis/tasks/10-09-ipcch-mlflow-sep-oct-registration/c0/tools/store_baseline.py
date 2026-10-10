"""C0 read-only baseline of the shared local MLflow store (no writes to the store).

Reads the SQLite DB through a read-only URI, the tracking API (search/get only) and
hashes every artifact file. Output: JSON written outside the store.
"""
import hashlib, json, os, sqlite3, sys, time
from pathlib import Path

ROOT = Path("/home/swl007007/.local/share/ipcch-mlflow")
out = Path(sys.argv[1])

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()

con = sqlite3.connect(f"file:{ROOT/'mlflow.db'}?mode=ro", uri=True)
tables = [r[0] for r in con.execute("select name from sqlite_master where type='table' order by name")]
counts = {t: con.execute(f'select count(*) from "{t}"').fetchone()[0] for t in tables}
journal = con.execute("PRAGMA journal_mode").fetchone()[0]
exps = [dict(zip(("experiment_id", "name", "lifecycle_stage"), r))
        for r in con.execute("select experiment_id,name,lifecycle_stage from experiments order by experiment_id")]
for e in exps:
    e["runs"] = con.execute("select count(*) from runs where experiment_id=?", (e["experiment_id"],)).fetchone()[0]
    e["metrics_latest"] = con.execute(
        "select count(*) from latest_metrics m join runs r on r.run_uuid=m.run_uuid where r.experiment_id=?",
        (e["experiment_id"],)).fetchone()[0]
reg = [r[0] for r in con.execute("select name from registered_models order by name")]
mv = con.execute("select count(*) from model_versions").fetchone()[0]
prefix_hits = {"registered_models_IPCCH_Forecasting": [n for n in reg if n.startswith("IPCCH Forecasting")],
               "experiments_IPCCH_Forecasting": [e["name"] for e in exps if e["name"].startswith("IPCCH Forecasting")]}
# digest of run identities/tags/metrics so a post-change compare is cheap
h = hashlib.sha256()
for q in ("select run_uuid,experiment_id,name,status,lifecycle_stage,artifact_uri from runs order by run_uuid",
          "select run_uuid,key,value from tags order by run_uuid,key",
          "select run_uuid,key,value,step,timestamp from latest_metrics order by run_uuid,key",
          "select run_uuid,key,value from params order by run_uuid,key",
          "select name,version,source,run_id,status from model_versions order by name,version"):
    for row in con.execute(q):
        h.update(repr(row).encode())
db_logical_digest = h.hexdigest()
con.close()

art = {}
total = 0
for dp, _, fns in os.walk(ROOT / "artifacts"):
    for fn in fns:
        p = Path(dp) / fn
        rel = str(p.relative_to(ROOT / "artifacts"))
        st = p.stat()
        art[rel] = {"bytes": st.st_size, "sha256": sha(p)}
        total += st.st_size
art_digest = hashlib.sha256(json.dumps(art, sort_keys=True).encode()).hexdigest()

api = {}
try:
    os.environ["MLFLOW_DISABLE_AGENT_HINT"] = "1"
    from mlflow.tracking import MlflowClient
    c = MlflowClient("http://127.0.0.1:5000")
    api["experiments"] = [(e.experiment_id, e.name) for e in c.search_experiments()]
    api["registered_models"] = len(c.search_registered_models(max_results=1000))
except Exception as ex:  # read-only probe failure is recorded, not fatal
    api["error"] = repr(ex)

res = {"captured_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "store_root": str(ROOT),
       "db_bytes": (ROOT / "mlflow.db").stat().st_size, "db_journal_mode": journal, "table_counts": counts,
       "experiments": exps, "registered_models": reg, "model_versions": mv, "ipcch_forecasting_prefix_hits": prefix_hits,
       "db_logical_digest": db_logical_digest, "artifact_files": len(art), "artifact_bytes": total,
       "artifact_manifest_sha256": art_digest, "api_probe": api,
       "store_side_dirs": {d: sorted(os.listdir(ROOT / d)) for d in ("plans", "cache", "dashboard", "logs", "staging")}}
out.write_text(json.dumps(res, indent=1, sort_keys=True))
(out.with_suffix(".artifacts.json")).write_text(json.dumps(art, sort_keys=True))
print(json.dumps({k: res[k] for k in ("captured_utc", "db_logical_digest", "artifact_files", "artifact_bytes",
                                      "artifact_manifest_sha256", "model_versions", "ipcch_forecasting_prefix_hits")}, indent=1))
print([(e["name"], e["runs"]) for e in exps]); print(len(reg), "registered models")
