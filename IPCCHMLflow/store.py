"""Shared-store safety for the IPCCH Forecasting catalog: lock, backup, restore-check, preservation.

The local MLflow store is shared with Food_Crisis_Cluster's IPCCH catalog. This module never edits
SQL; it reads the SQLite file read-only (``mode=ro``) and copies files.

- ``Lock``: the same ``import.lock`` flock the FCC importer and backup tool take, so writers exclude
  each other.
- ``backup``: SQLite online backup API + byte copy of ``artifacts/`` + manifest (row counts, hashes).
- ``restore_check``: copies a backup into a scratch root, starts a temporary server on its own port
  (5000 refused) and downloads artifacts through it.
- ``snapshot`` / ``compare``: complete pre-existing state (every row of every table, keyed by primary
  key, incl. descriptions, tags, dataset/model associations and full metric histories, plus every
  artifact file hash). After an import every old row must be byte-identical and every new row must
  belong to the IPCCH Forecasting namespace; counts are never used as proof.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

import naming as N
from naming import SourceConflict

DEFAULT_STORE = Path("/home/swl007007/.local/share/ipcch-mlflow")
VENV = Path("/home/swl007007/.venvs/ipcch-mlflow")
CHUNK = 1 << 22


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(CHUNK), b""):
            h.update(b)
    return h.hexdigest()


class Lock:
    def __init__(self, store: Path):
        self.path = store / "import.lock"

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.f = open(self.path, "a")
        try:
            fcntl.flock(self.f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit(f"another import/backup holds {self.path}; refusing concurrent run")
        return self

    def __exit__(self, *a):
        fcntl.flock(self.f, fcntl.LOCK_UN)
        self.f.close()


def ro(db: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{db}?mode=ro", uri=True)


def tree_manifest(root: Path) -> dict:
    out = {}
    if root.is_dir():
        for dp, dns, fns in os.walk(root):
            dns.sort()
            for fn in sorted(fns):
                p = Path(dp) / fn
                out[str(p.relative_to(root))] = {"bytes": p.stat().st_size, "sha256": sha(p)}
    return out


# ------------------------------------------------------------------ snapshot / compare

def tables(con) -> dict:
    out = {}
    for (t,) in con.execute("select name from sqlite_master where type='table' order by name"):
        info = list(con.execute(f'pragma table_info("{t}")'))
        cols = [r[1] for r in info]
        pk = [r[1] for r in sorted(info, key=lambda r: r[5]) if r[5]] or cols
        out[t] = (cols, pk)
    return out


def snapshot(store: Path, out: Path | None = None, artifacts: bool = True) -> dict:
    """Every row of every table (keyed by primary key) and every artifact file hash."""
    con = ro(store / "mlflow.db")
    data = {}
    for t, (cols, pk) in tables(con).items():
        rows = {}
        for r in con.execute(f'select * from "{t}"'):
            row = dict(zip(cols, r))
            key = json.dumps([row[c] for c in pk], default=str)
            if key in rows and t != "metrics":
                raise SourceConflict(f"{t}: duplicate primary key {key}")
            rows.setdefault(key, []).append(json.dumps(row, sort_keys=True, default=str))
        data[t] = {"columns": cols, "pk": pk, "rows": rows}
    con.close()
    snap = {"captured_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "store": str(store), "tables": data,
            "artifacts": tree_manifest(store / "artifacts") if artifacts else None}
    snap["digest"] = hashlib.sha256(json.dumps(snap["tables"], sort_keys=True).encode()).hexdigest()
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(snap))
    return snap


def ours(after: dict) -> dict:
    """Identities owned by the IPCCH Forecasting namespace in a snapshot."""
    def rows(t):
        return [json.loads(x) for v in after["tables"].get(t, {"rows": {}})["rows"].values() for x in v]
    exps = {str(r["experiment_id"]) for r in rows("experiments") if r["name"] in (N.DETAILED_EXPERIMENT, N.DASHBOARD_EXPERIMENT)}
    runs = {r["run_uuid"] for r in rows("runs") if str(r["experiment_id"]) in exps}
    models = {r["model_id"] for r in rows("logged_models") if str(r["experiment_id"]) in exps}
    dsets = {r["dataset_uuid"] for r in rows("datasets") if str(r["experiment_id"]) in exps}
    ids = runs | dsets | models
    inputs = {r["input_uuid"] for r in rows("inputs") if r["destination_id"] in ids or r["source_id"] in ids}
    dash = {str(r["experiment_id"]) for r in rows("experiments") if r["name"] == N.DASHBOARD_EXPERIMENT}
    return {"experiments": exps, "dashboard": dash, "runs": runs, "models": models, "datasets": dsets, "inputs": inputs}


def owned(t: str, row: dict, o: dict) -> bool:
    prefix = N.MODEL_PREFIX + " "
    if t in ("experiments", "experiment_tags", "datasets", "logged_models", "logged_model_params", "logged_model_tags",
             "logged_model_metrics"):
        return str(row["experiment_id"]) in o["experiments"]
    if t == "runs":
        return row["run_uuid"] in o["runs"]
    if t in ("tags", "params", "metrics", "latest_metrics"):
        return row["run_uuid"] in o["runs"]
    if t == "inputs":
        return row["input_uuid"] in o["inputs"]
    if t == "input_tags":
        return row["input_uuid"] in o["inputs"]
    if t in ("registered_models", "registered_model_tags", "registered_model_aliases", "model_versions", "model_version_tags"):
        return str(row["name"]).startswith(prefix)
    if t == "entity_associations":
        ids = o["runs"] | o["models"] | o["datasets"]
        return row["source_id"] in ids or row["destination_id"] in ids
    return False


RETIRE_FIELDS = {"lifecycle_stage", "deleted_time"}


def retired_dashboard_row(t: str, old: list, new: list, o: dict) -> bool:
    """The only allowed change to a pre-existing row: soft deletion of a superseded IPCCH Forecasting
    dashboard row (detailed records, other catalogs and all other fields stay immutable)."""
    if t != "runs" or len(old) != 1 or len(new) != 1:
        return False
    a, b = json.loads(old[0]), json.loads(new[0])
    if str(a.get("experiment_id")) not in o["dashboard"] or b.get("lifecycle_stage") != "deleted":
        return False
    return {k for k in a if a[k] != b.get(k)} <= RETIRE_FIELDS


def compare(before: dict, after: dict) -> dict:
    """Old rows unchanged (by primary key, full content); new rows only inside our namespace."""
    o = ours(after)
    problems, added = [], {}
    for t, b in before["tables"].items():
        a = after["tables"].get(t)
        if a is None:
            problems.append(f"table {t} disappeared")
            continue
        for key, rows in b["rows"].items():
            if a["rows"].get(key) is None:
                problems.append(f"{t}: pre-existing row {key} missing")
            elif t == "metrics":
                if not set(rows) <= set(a["rows"][key]):
                    problems.append(f"{t}: pre-existing metric history {key} changed")
            elif a["rows"][key] != rows and not retired_dashboard_row(t, rows, a["rows"][key], o):
                problems.append(f"{t}: pre-existing row {key} changed")
    for t, a in after["tables"].items():
        b = before["tables"].get(t, {"rows": {}})
        n = 0
        for key, rows in a["rows"].items():
            new = rows if key not in b["rows"] else [r for r in rows if r not in b["rows"][key]]
            for r in new:
                if not owned(t, json.loads(r), o):
                    problems.append(f"{t}: new row outside the IPCCH Forecasting namespace: {key}")
                n += 1
        if n:
            added[t] = n
    art = {"checked": 0}
    if before.get("artifacts") is not None and after.get("artifacts") is not None:
        for rel, rec in before["artifacts"].items():
            art["checked"] += 1
            if after["artifacts"].get(rel) != rec:
                problems.append(f"artifact {rel} changed or missing")
        for rel in set(after["artifacts"]) - set(before["artifacts"]):
            if rel.split("/", 1)[0] not in o["experiments"]:
                problems.append(f"new artifact outside our experiments: {rel}")
    return {"ok": not problems, "problems": problems[:200], "n_problems": len(problems), "added_rows": added,
            "artifacts": art, "before_digest": before.get("digest"), "after_digest": after.get("digest")}


# ------------------------------------------------------------------ backup / restore-check

def db_counts(db: Path) -> dict:
    con = ro(db)
    out = {t: con.execute(f'select count(*) from "{t}"').fetchone()[0] for t in tables(con)}
    con.close()
    return out


def backup(store: Path, dest: Path) -> dict:
    if dest.exists() and any(dest.iterdir()):
        raise SourceConflict(f"backup destination {dest} is not empty")
    dest.mkdir(parents=True, exist_ok=True)
    with Lock(store):
        src = sqlite3.connect(f"file:{store / 'mlflow.db'}?mode=ro", uri=True)
        dst = sqlite3.connect(dest / "mlflow.db")
        src.backup(dst)
        dst.close()
        src.close()
        shutil.copytree(store / "artifacts", dest / "artifacts", symlinks=False)
        man = {"created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "store": str(store),
               "db_sha256": sha(dest / "mlflow.db"), "db_counts": db_counts(dest / "mlflow.db"),
               "live_db_counts": db_counts(store / "mlflow.db"), "artifacts": tree_manifest(dest / "artifacts")}
    live_art = tree_manifest(store / "artifacts")
    if live_art != man["artifacts"] or man["db_counts"] != man["live_db_counts"]:
        raise SourceConflict("backup differs from the live store taken under the lock (concurrent writer?)")
    (dest / "backup-manifest.json").write_text(json.dumps(man, indent=1))
    return {"dest": str(dest), "db_sha256": man["db_sha256"], "artifact_files": len(man["artifacts"]), "db_counts": man["db_counts"]}


def _healthy(port: int) -> bool:
    import urllib.request
    try:
        return urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2).read().strip() == b"OK"
    except Exception:
        return False


def scratch_server(root: Path, port: int):
    """Start a server for a scratch store; refuse port 5000 and any port already served by someone else."""
    if int(port) == 5000:
        raise SourceConflict("scratch servers must not use port 5000 (live service)")
    if _healthy(port):
        raise SourceConflict(f"port {port} is already served; refusing to reuse another server")
    env = {**os.environ, "MLFLOW_DISABLE_AGENT_HINT": "1"}
    log = open(root / "server.log", "a")
    p = subprocess.Popen([str(VENV / "bin" / "mlflow"), "server", "--backend-store-uri", f"sqlite:///{root / 'mlflow.db'}",
                          "--artifacts-destination", str(root / "artifacts"), "--serve-artifacts", "--host", "127.0.0.1",
                          "--port", str(port), "--workers", "1"], stdout=log, stderr=log, env=env, start_new_session=True)
    for _ in range(90):
        if p.poll() is not None:
            raise SourceConflict(f"scratch server exited (code {p.returncode}); see {root / 'server.log'}")
        if _healthy(port) and (root / "mlflow.db").is_file():
            return p
        time.sleep(1)
    stop_server(p)
    raise SourceConflict(f"scratch server on port {port} did not start; see {root / 'server.log'}")


def stop_server(p) -> None:
    import signal
    try:
        os.killpg(p.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        p.wait(20)
    except subprocess.TimeoutExpired:
        os.killpg(p.pid, signal.SIGKILL)


def restore_check(backup_dir: Path, scratch: Path, port: int = 5001) -> dict:
    if scratch.exists() and any(scratch.iterdir()):
        raise SourceConflict(f"scratch {scratch} is not empty")
    man = json.loads((backup_dir / "backup-manifest.json").read_text())
    scratch.mkdir(parents=True, exist_ok=True)
    shutil.copy2(backup_dir / "mlflow.db", scratch / "mlflow.db")
    shutil.copytree(backup_dir / "artifacts", scratch / "artifacts")
    if sha(scratch / "mlflow.db") != man["db_sha256"] or db_counts(scratch / "mlflow.db") != man["db_counts"]:
        raise SourceConflict("restored database differs from the backup manifest")
    if tree_manifest(scratch / "artifacts") != man["artifacts"]:
        raise SourceConflict("restored artifacts differ from the backup manifest")
    p = scratch_server(scratch, port)
    try:
        from mlflow.tracking import MlflowClient
        c = MlflowClient(f"http://127.0.0.1:{port}")
        exps = {e.name: e.experiment_id for e in c.search_experiments()}
        downloads, problems = [], []

        def walk(rid, path=None):
            for fi in c.list_artifacts(rid, path):
                if fi.is_dir:
                    yield from walk(rid, fi.path)
                else:
                    yield fi
        for name in sorted(exps):
            for r in c.search_runs([exps[name]], max_results=2):
                for fi in list(walk(r.info.run_id))[:4]:
                    if (fi.file_size or 0) > 200_000_000:
                        continue
                    d = c.download_artifacts(r.info.run_id, fi.path, str(scratch / "dl" / r.info.run_id))
                    rel = r.info.artifact_uri.split("mlflow-artifacts:/", 1)[-1].lstrip("/") + "/" + fi.path
                    want = man["artifacts"].get(rel, {}).get("sha256")
                    got = sha(Path(d))
                    downloads.append({"experiment": name, "path": rel, "sha256": got, "matches_backup": got == want})
                    if got != want:
                        problems.append(rel)
        if man["artifacts"] and not downloads:
            problems.append("backup has artifacts but no artifact could be downloaded through the scratch server")
        return {"ok": not problems, "problems": problems, "port": port, "experiments": sorted(exps), "downloads": downloads,
                "db_counts": man["db_counts"], "artifact_files": len(man["artifacts"])}
    finally:
        stop_server(p)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("snapshot"); s.add_argument("--store", type=Path, default=DEFAULT_STORE); s.add_argument("--out", type=Path, required=True)
    s = sub.add_parser("compare"); s.add_argument("--before", type=Path, required=True); s.add_argument("--store", type=Path, default=DEFAULT_STORE); s.add_argument("--out", type=Path, required=True)
    s = sub.add_parser("backup"); s.add_argument("--store", type=Path, default=DEFAULT_STORE); s.add_argument("--dest", type=Path, required=True)
    s = sub.add_parser("restore-check"); s.add_argument("--backup", type=Path, required=True); s.add_argument("--dest", type=Path, required=True); s.add_argument("--port", type=int, default=5001)
    a = ap.parse_args(argv)
    if a.cmd == "snapshot":
        snap = snapshot(a.store, a.out)
        print(json.dumps({"digest": snap["digest"], "artifact_files": len(snap["artifacts"] or {}), "out": str(a.out)}))
    elif a.cmd == "compare":
        res = compare(json.loads(a.before.read_text()), snapshot(a.store))
        a.out.write_text(json.dumps(res, indent=1))
        print(json.dumps({k: res[k] for k in ("ok", "n_problems", "added_rows")}))
        return 0 if res["ok"] else 1
    elif a.cmd == "backup":
        print(json.dumps(backup(a.store, a.dest)))
    elif a.cmd == "restore-check":
        print(json.dumps(restore_check(a.backup, a.dest, a.port)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
