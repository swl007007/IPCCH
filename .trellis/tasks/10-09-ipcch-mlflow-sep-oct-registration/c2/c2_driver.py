"""C2 authorized live run driver (task evidence tool; not a product API).

One plan, then the tested IPCCHMLflow functions in the documented order, under the shared
import.lock: baseline match vs the C1 backup -> durable backup move -> snapshot before -> import ->
verify -> dashboard -> dashboard-verify -> unchanged repeat (import + dashboard) -> old-store compare.
Every step's result is written to this directory.
"""
import json
import shutil
import sys
import time
import traceback
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "IPCCHMLflow"))
import catalog as C  # noqa: E402
import plan as P  # noqa: E402
import store as S  # noqa: E402

OUT = Path(__file__).resolve().parent
STORE = P.DEFAULT_STORE
URI = "http://127.0.0.1:5000"
C1_BACKUP = Path("/tmp/ipcch-c1/rehearsal/backup")
DURABLE = Path.home() / "ipcch-mlflow-backups" / "20261010-before-ipcch-forecasting"


def log(step, **kw):
    rec = {"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "step": step, **kw}
    with open(OUT / "c2-log.jsonl", "a") as f:
        f.write(json.dumps(rec, default=str) + "\n")
    print(json.dumps(rec, default=str), flush=True)


def save(name, obj):
    (OUT / name).write_text(json.dumps(obj, indent=1, default=str))


def main():
    t0 = time.time()
    cfg = P.load_sources()
    with S.Lock(STORE):
        # 1. baseline: fresh live snapshot must equal the C1 backup (rows + artifact hashes)
        live = S.snapshot(STORE)
        src_backup = DURABLE if DURABLE.is_dir() else C1_BACKUP
        bk = S.snapshot(src_backup)
        same = live["tables"] == bk["tables"] and live["artifacts"] == bk["artifacts"]
        log("baseline_vs_c1_backup", identical=same, live_digest=live["digest"], backup_digest=bk["digest"],
            live_artifacts=len(live["artifacts"]), backup=str(src_backup))
        if not same:
            raise SystemExit("live store differs from the C1 backup: take a fresh backup before importing")
        if src_backup == C1_BACKUP:
            DURABLE.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(C1_BACKUP), str(DURABLE))
            log("backup_moved", dest=str(DURABLE))
        man = json.loads((DURABLE / "backup-manifest.json").read_text())
        log("backup_manifest", db_sha256=man["db_sha256"], artifact_files=len(man["artifacts"]))
        snap_path = DURABLE.parent / "20261010-ipcch-forecasting-before-snapshot.json"
        snap_path.write_text(json.dumps(live))
        log("before_snapshot_saved", path=str(snap_path), digest=live["digest"])
        # 2. one plan for the whole run
        full = P.build_plans(cfg, P.REPO, STORE)
        totals = P.check_global(cfg, full, True)
        P.write_plans(full, STORE)
        save("plan.json", {"totals": totals, "fingerprints": {k: p["fingerprint"] for k, p in full.items()}})
        log("plan", **totals)
        # 3. import + verify
        st = C.import_sources(C.Ctx(URI, STORE, live=True), full, full)
        P.write_plans(full, STORE)
        save("import.json", st)
        log("import", **st)
        ver = C.verify_sources(C.Ctx(URI, STORE, live=True), full, full)
        save("verify.json", ver)
        log("verify", sources=len(ver), children=sum(v["children"] for v in ver), metrics=sum(v["metrics"] for v in ver))
        # 4. dashboard
        d = C.apply_dashboard(C.Ctx(URI, STORE, live=True), cfg, full)
        save("dashboard.json", d)
        log("dashboard", **d)
        dv = C.verify_dashboard(C.Ctx(URI, STORE, live=True), cfg, full)
        save("dashboard-verify.json", dv)
        log("dashboard_verify", **dv)
        # 5. unchanged repeat must be a verified no-op with an identical store
        mid = S.snapshot(STORE)
        r1 = C.import_sources(C.Ctx(URI, STORE, live=True), full, full)
        r2 = C.apply_dashboard(C.Ctx(URI, STORE, live=True), cfg, full)
        end = S.snapshot(STORE)
        same_repeat = mid["digest"] == end["digest"] and mid["artifacts"] == end["artifacts"]
        save("repeat.json", {"import": r1, "dashboard": r2, "store_identical": same_repeat,
                             "mid_digest": mid["digest"], "end_digest": end["digest"]})
        log("repeat", import_=r1, dashboard=r2, store_identical=same_repeat)
        # 6. old-store preservation
        cmp_ = S.compare(live, end)
        save("compare.json", cmp_)
        log("compare", ok=cmp_["ok"], n_problems=cmp_["n_problems"], added_rows=cmp_["added_rows"],
            artifacts_checked=cmp_["artifacts"]["checked"])
    log("done", seconds=round(time.time() - t0))


if __name__ == "__main__":
    try:
        main()
    except BaseException as e:
        log("failed", error=repr(e), trace=traceback.format_exc()[-3000:])
        raise
