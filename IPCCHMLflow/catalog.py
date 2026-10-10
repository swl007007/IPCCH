"""IPCCH Forecasting MLflow catalog: plan / import / verify / dashboard (single CLI).

    PY=/home/swl007007/.venvs/ipcch-mlflow/bin/python
    $PY IPCCHMLflow/catalog.py plan   [--source KEY ...] [--rehash]                 # read-only
    $PY IPCCHMLflow/catalog.py import [--source KEY ...] --tracking-uri URI [--live]  # serial, resumable
    $PY IPCCHMLflow/catalog.py verify [--source KEY ...] --tracking-uri URI [--live]  # deep readback
    $PY IPCCHMLflow/catalog.py dashboard --tracking-uri URI [--live]                  # latest-snapshot rows
    $PY IPCCHMLflow/catalog.py dashboard-verify --tracking-uri URI [--live]

Writes only the experiments ``IPCCH Forecasting - detailed runs`` / ``- dashboard`` and registered
models named ``IPCCH Forecasting ...``. Records are keyed by ``zz_prov.record_key``; the source
snapshot's content fingerprint is ``zz_prov.import_fingerprint``. A completed record with the same
fingerprint is deep-verified and left unchanged (no-op); a different fingerprint stops before any
write. A record is marked complete only after its values, inputs, artifacts, logged model and
model version read back. The live service (port 5000) requires ``--live``.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sqlite3
import sys
import tarfile
import tempfile
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import extract as X  # noqa: E402
import naming as N  # noqa: E402
import plan as P  # noqa: E402
import store as S  # noqa: E402
from naming import PROV, SourceConflict  # noqa: E402

T_KEY, T_FP, T_STATUS, T_SOURCE = PROV + "record_key", PROV + "import_fingerprint", PROV + "import_status", PROV + "source_key"
T_VERSION = PROV + "version_key"
T_PROJ, T_ROWFP, T_ROWSTATUS = PROV + "projection_key", PROV + "row_fingerprint", PROV + "row_status"
EXEC_NOTE = {PROV + "execution": "historical import of a completed fit; MLflow did not execute it",
             PROV + "mlflow_timestamps": "MLflow start/metric times are registration times, not fit times"}


class Interrupt(RuntimeError):
    pass


def ordered(tags: dict) -> dict:
    """Readable tags first, zz_prov.* last (the run page lists tags in insertion order)."""
    return {k: str(tags[k]) for k in sorted(tags, key=lambda k: (k.startswith(PROV), k))}


def jbytes(obj) -> bytes:
    return json.dumps(obj, indent=1, sort_keys=True, ensure_ascii=False).encode()


# ------------------------------------------------------------------ context

class Ctx:
    def __init__(self, uri: str, store: Path, live: bool, repo: Path = P.REPO, artifact_root: Path | None = None):
        host = uri.split("//", 1)[-1].split("/", 1)[0]
        if host.endswith(":5000") and not live:
            raise SourceConflict("tracking URI is the live service (port 5000); pass --live only after supervisor release")
        os.environ["MLFLOW_DISABLE_AGENT_HINT"] = "1"
        os.environ["MLFLOW_SUPPRESS_PRINTING_URL_TO_STDOUT"] = "true"
        import mlflow
        from mlflow.tracking import MlflowClient
        mlflow.set_tracking_uri(uri)
        self.mlflow, self.client, self.uri, self.store, self.repo = mlflow, MlflowClient(uri), uri, store, repo
        self.ns = store / P.NAMESPACE
        self.artifact_root = artifact_root if artifact_root is not None else (store / "artifacts" if (store / "artifacts").is_dir() else None)
        self.db = store / "mlflow.db" if (store / "mlflow.db").is_file() else None
        self.stats = Counter()

    def experiment(self, name: str, description: str):
        e = self.client.get_experiment_by_name(name)
        if e is None:
            eid = self.client.create_experiment(name, tags={N.NOTE: description, "catalog": "ipcch_forecasting"})
            self.stats["experiments_created"] += 1
            return self.client.get_experiment(eid)
        if e.tags.get("catalog") != "ipcch_forecasting":
            raise SourceConflict(f"experiment {name!r} exists but is not an IPCCH Forecasting catalog experiment")
        if e.tags.get(N.NOTE) != description:
            self.client.set_experiment_tag(e.experiment_id, N.NOTE, description)
            self.stats["experiment_descriptions_updated"] += 1
        return e

    def runs_by_key(self, exp_id: str, deleted: bool = False) -> dict:
        out, token = defaultdict(list), None
        from mlflow.entities import ViewType
        while True:
            page = self.client.search_runs([exp_id], max_results=1000, page_token=token,
                                           run_view_type=ViewType.ALL if deleted else ViewType.ACTIVE_ONLY)
            for r in page:
                k = r.data.tags.get(T_KEY) or r.data.tags.get(T_PROJ)
                if k:
                    out[k].append(r)
            token = page.token
            if not token:
                return out

    def logged_models(self, exp_id: str) -> dict:
        out, token = {}, None
        while True:
            page = self.client.search_logged_models([exp_id], max_results=500, page_token=token)
            for m in page:
                k = m.tags.get(T_VERSION)
                if k:
                    if k in out:
                        raise SourceConflict(f"two logged models carry version key {k}")
                    out[k] = m
            token = page.token
            if not token:
                return out

    def artifact_sha(self, run, rel: str) -> str | None:
        uri = run.info.artifact_uri
        if self.artifact_root is not None and uri.startswith("mlflow-artifacts:/"):
            p = self.artifact_root / uri[len("mlflow-artifacts:/"):] / rel
            return S.sha(p) if p.is_file() else None
        with tempfile.TemporaryDirectory(prefix="ipcch-fc-dl-") as d:
            try:
                return S.sha(Path(self.client.download_artifacts(run.info.run_id, rel, d)))
            except Exception:
                return None

    def artifact_path(self, run, rel: str) -> Path | None:
        uri = run.info.artifact_uri
        if self.artifact_root is not None and uri.startswith("mlflow-artifacts:/"):
            p = self.artifact_root / uri[len("mlflow-artifacts:/"):] / rel
            return p if p.is_file() else None
        return None

    def upload(self, run_id: str, art_path: str, data: bytes | None = None, src: Path | None = None) -> None:
        d, name = art_path.rsplit("/", 1) if "/" in art_path else ("", art_path)
        with tempfile.TemporaryDirectory(prefix="ipcch-fc-up-") as tmp:
            local = Path(tmp) / name
            if data is not None:
                local.write_bytes(data)
            else:
                os.symlink(src, local)
            self.client.log_artifact(run_id, str(local), d or None)
        self.stats["artifacts_uploaded"] += 1

    def metric_history_counts(self, run_ids: list) -> dict:
        """Rows per (run, key) in the metrics table (read-only SQLite); >1 means a duplicate write."""
        if self.db is None:
            return {}
        con = S.ro(self.db)
        out = {}
        for i in range(0, len(run_ids), 500):
            chunk = run_ids[i:i + 500]
            q = f"select run_uuid, key, count(*) from metrics where run_uuid in ({','.join('?' * len(chunk))}) group by run_uuid, key"
            for rid, k, n in con.execute(q, chunk):
                out[(rid, k)] = n
        con.close()
        return out


# ------------------------------------------------------------------ bundles

def bundle_members(plan: dict) -> dict:
    out = {"models.tar": [], "source.tar": []}
    for f in plan["files"]:
        if f["decision"].startswith("bundle"):
            out["models.tar"].append(f)
        elif f["decision"].startswith("archive"):
            out["source.tar"].append(f)
    return out


def build_tar(repo: Path, members: list, out: Path) -> dict:
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".partial")
    with tarfile.open(tmp, "w", format=tarfile.PAX_FORMAT) as tar:
        for m in sorted(members, key=lambda x: x["path"]):
            p = repo / m["path"]
            ti = tarfile.TarInfo(m["path"])
            ti.size, ti.mtime, ti.mode, ti.uid, ti.gid, ti.uname, ti.gname = m["bytes"], 0, 0o644, 0, 0, "", ""
            data = p.read_bytes() if m["bytes"] < (64 << 20) else None
            if data is not None:
                if X.sha_bytes(data) != m["sha256"]:
                    raise SourceConflict(f"bundle member changed since planning: {p}")
                tar.addfile(ti, io.BytesIO(data))
            else:
                with open(p, "rb") as f:
                    tar.addfile(ti, f)
                if X.sha_file(p) != m["sha256"]:
                    raise SourceConflict(f"bundle member changed since planning: {p}")
    os.replace(tmp, out)
    return {"bytes": out.stat().st_size, "sha256": S.sha(out)}


def tar_check(path: Path, members: list) -> int:
    want = {m["path"]: m["sha256"] for m in members}
    seen = 0
    with tarfile.open(path, "r") as tar:
        for ti in tar:
            f = tar.extractfile(ti)
            h = __import__("hashlib").sha256()
            for b in iter(lambda: f.read(S.CHUNK), b""):
                h.update(b)
            if want.get(ti.name) != h.hexdigest():
                raise SourceConflict(f"{path}: tar member {ti.name} checksum mismatch")
            seen += 1
    if seen != len(want):
        raise SourceConflict(f"{path}: {seen} tar members, manifest {len(want)}")
    return seen


# ------------------------------------------------------------------ record content

def plan_summary(plan: dict) -> dict:
    return {"source_key": plan["source_key"], "fingerprint": plan["fingerprint"], "importer": plan["importer"],
            "families": plan["families"], "counts": plan["counts"], "config": plan["config"]}


def parent_tags(plan: dict, tar_info: dict) -> dict:
    src = plan["config"]
    t = {"record_kind": "family", "family": ";".join(plan["families"]),
         "family_title": "; ".join(N.family(f)["short"] for f in plan["families"]), "stage": src["stage"],
         "model_scope": src["model_scope"], "snapshot": src["snapshot_label"], "snapshot_role": src["snapshot_role"],
         N.NOTE: plan["parent_description"],
         T_KEY: plan["source_key"], T_SOURCE: plan["source_key"], T_FP: plan["fingerprint"],
         PROV + "importer_version": plan["importer"], PROV + "source_root": src["root"],
         PROV + "fit_date_evidence": src["fit_date_evidence"][:4000], PROV + "source.lifecycle_and_acceptance": src["status_text"][:4000],
         **EXEC_NOTE}
    if src.get("extends"):
        t[PROV + "extends_snapshot"] = src["extends"]
    for name, info in tar_info.items():
        t[f"{PROV}bundle.{name}.sha256"], t[f"{PROV}bundle.{name}.bytes"] = info["sha256"], info["bytes"]
    return t


def child_tags(plan: dict, v: dict, parent_id: str) -> dict:
    src = plan["config"]
    f = N.family(v["family"])
    t = {"record_kind": "evaluation", "family": v["family"], "family_title": f["short"], "arm": v["arm"],
         "arm_role": v["arm_role"], "lead_months": N.lead_tag(v["lead"]), "model_scope": f["scope"], "stage": f["stage"],
         "snapshot": src["snapshot_label"], "view_kind": v["view_kind"], "source_status": v["source_status"],
         N.NOTE: v["description"], "mlflow.parentRunId": parent_id,
         T_KEY: v["record_key"], T_SOURCE: plan["source_key"], T_FP: plan["fingerprint"],
         PROV + "importer_version": plan["importer"], PROV + "raw_arm": v["arm_raw"], **EXEC_NOTE}
    if f["label_setting"]:
        t["label_setting"] = f["label_setting"]
    for role, span in period_tags(plan, v).items():
        t[f"period.{role}"] = span
    if v.get("version_key"):
        t[T_VERSION] = v["version_key"]
    if v.get("alias_of"):
        t[PROV + "reuses_version"] = v["alias_of"]
    return t


def period_tags(plan: dict, v: dict) -> dict:
    out = {}
    for k, ds in sorted(v["metric_dataset"].items()):
        role, coh = k.split(".", 2)[:2]
        d = plan["datasets"].get(ds) or {}
        desc = d.get("descriptor", {})
        if desc.get("context") == "evaluation" and coh in ("all_scored", "primary") and role not in out:
            out[role] = desc["period"]
    return out


def all_datasets(plans: dict) -> dict:
    out = {}
    for p in plans.values():
        out.update(p["datasets"])
    return out


def view_docs(plan: dict, v: dict, datasets: dict) -> dict:
    used = sorted(v["datasets"])
    ev = {"record_key": v["record_key"], "description": v["description"],
          "metrics": {k: {"value": val, "dataset": v["metric_dataset"].get(k), **v["sources"][k]} for k, val in sorted(v["metrics"].items())},
          "datasets": {n: datasets[n]["digest"] for n in used}, "slots": v["slots"]}
    return {"view/evaluation_view.json": jbytes(ev), "view/na.json": jbytes(v["na"]),
            "view/datasets.json": jbytes({n: datasets[n] for n in used})}


def members_doc(ver: dict, parent_ids: dict) -> bytes:
    rows = []
    for m in ver["members"]:
        rid = parent_ids.get(m["bundle_source"])
        if rid is None:
            raise SourceConflict(f"{ver['version_key']}: bundle source {m['bundle_source']} has no imported parent run")
        rows.append({**m, "bundle": "models.tar", "bundle_run_id": rid, "bundle_uri": f"runs:/{rid}/models.tar"})
    return jbytes({"version_key": ver["version_key"], "registered_model": ver["registered_model"],
                   "logged_model": ver["logged_model"], "training_dataset": ver["training_dataset"],
                   "n_inputs": ver["n_inputs"], "boosters_total": ver["boosters_total"], "boosters_new": ver["boosters_new"],
                   "boosters_reused": ver["boosters_reused"], "boosters_alias": ver["boosters_alias"],
                   "fit_units_new": ver["fit_units_new"], "external_note": N.EXTERNAL_NOTE, "members": rows})


def dataset_entity(ds: dict):
    from mlflow.entities import Dataset
    d = ds["descriptor"]
    keep = {k: d.get(k) for k in ("context", "lead_months", "period", "cohort", "group", "n_keys", "n_required", "keys_sha256",
                                   "truth_sha256", "n_inputs", "label_setting", "prepared_pool_sha256", "feature_order_sha256",
                                   "origin", "target", "n_areas", "area_keys_sha256", "inference_features_sha256") if d.get(k) is not None}
    keep["descriptor_sha256"] = ds["full_sha256"]
    profile = {"num_rows": d.get("n_keys") or d.get("n_areas")} if d.get("n_keys") or d.get("n_areas") else {}
    return Dataset(name=ds["name"], digest=ds["digest"], source_type=f"ipcch_{d['context']}", source=json.dumps(keep, sort_keys=True),
                   schema=json.dumps({"key_columns": d.get("key_columns"), "truth_columns": d.get("truth_columns")}),
                   profile=json.dumps(profile))


def dataset_inputs(v: dict, datasets: dict):
    from mlflow.entities import DatasetInput, InputTag
    roles = defaultdict(set)
    for k, ds in v["metric_dataset"].items():
        roles[ds].add(k.split(".", 1)[0])
    out = []
    for n in sorted(v["datasets"]):
        ds = datasets[n]
        tags = [InputTag("mlflow.data.context", ds["descriptor"]["context"]), InputTag(PROV + "descriptor_sha256", ds["full_sha256"])]
        if roles.get(n):
            tags.append(InputTag("period_roles", ";".join(sorted(roles[n]))))
        out.append(DatasetInput(dataset_entity(ds), tags=tags))
    return out


def model_params(ver: dict) -> dict:
    return {"family": ver["family"], "arm": ver["arm"], "lead_months": ver["lead"], "n_inputs": ver["n_inputs"],
            "boosters_total": ver["boosters_total"], "boosters_new": ver["boosters_new"], "boosters_reused": ver["boosters_reused"],
            "fit_units_new": ver["fit_units_new"]}


def model_tags(plan: dict, ver: dict, members_sha: str) -> dict:
    f = N.family(ver["family"])
    return ordered({"family": ver["family"], "arm": ver["arm"], "lead_months": N.lead_tag(ver["lead"]), "model_scope": f["scope"],
                    "stage": f["stage"], "snapshot": plan["config"]["snapshot_label"], "catalog": "external_descriptor",
                    T_VERSION: ver["version_key"], T_SOURCE: plan["source_key"], T_FP: plan["fingerprint"],
                    PROV + "members_sha256": members_sha})


def version_description(plan: dict, ver: dict) -> str:
    src = plan["config"]
    reuse = ""
    if ver["boosters_reused"]:
        reuse = f" {ver['boosters_reused']} boosters are reused unchanged from snapshot {src.get('extends')}."
    if ver["boosters_alias"]:
        reuse += f" {ver['boosters_alias']} boosters are the selected recipe's existing component fits (no new fit)."
    return (f"Snapshot {src['snapshot_label']} ({plan['source_key']}): {ver['boosters_total']} booster members, "
            f"{ver['boosters_new']} fitted in this snapshot from {ver['fit_units_new']} fit unit(s).{reuse} {N.EXTERNAL_NOTE}")


# ------------------------------------------------------------------ import

def preflight(ctx: Ctx, exp_id: str, plans: dict) -> dict:
    """Stop before any write if a completed/in-progress record has another fingerprint."""
    by = ctx.runs_by_key(exp_id)
    for k, p in plans.items():
        recs = by.get(k, [])
        if len(recs) > 1:
            raise SourceConflict(f"{k}: {len(recs)} parent records share this source key")
        if recs and recs[0].data.tags.get(T_FP) != p["fingerprint"]:
            raise SourceConflict(f"{k}: stored snapshot has fingerprint {recs[0].data.tags.get(T_FP)}, plan has {p['fingerprint']}: "
                                 "source, vocabulary or importer changed. Register a new snapshot key instead of rewriting.")
        for v in p["views"]:
            rr = by.get(v["record_key"], [])
            if len(rr) > 1:
                raise SourceConflict(f"{v['record_key']}: duplicate child records")
            if rr and rr[0].data.tags.get(T_FP) != p["fingerprint"]:
                raise SourceConflict(f"{v['record_key']}: child of another fingerprint")
    return by


def import_sources(ctx: Ctx, plans: dict, all_plans: dict, fail_after: str | None = None) -> dict:
    existing = ctx.client.get_experiment_by_name(N.DETAILED_EXPERIMENT)
    if existing is not None:
        preflight(ctx, existing.experiment_id, plans)  # read-only; conflicts stop before any write
    exp = ctx.experiment(N.DETAILED_EXPERIMENT, detailed_description())
    by = preflight(ctx, exp.experiment_id, plans)
    datasets = all_datasets(all_plans)
    for k in P.order({"sources": [p["config"] for p in all_plans.values()]}, list(plans)):
        if k not in plans:
            continue
        import_one(ctx, exp, plans[k], by, datasets, fail_after)
        by = ctx.runs_by_key(exp.experiment_id)
    return dict(ctx.stats)


def parent_ids(ctx: Ctx, exp_id: str, by: dict, need: set) -> dict:
    out = {}
    for k in need:
        r = by.get(k, [])
        if not r or r[0].data.tags.get(T_STATUS) not in ("complete", "in_progress") or r[0].data.tags.get("record_kind") != "family":
            raise SourceConflict(f"bundle/reference source {k} is not imported; import it first")
        out[k] = r[0].info.run_id
    return out


def import_one(ctx: Ctx, exp, plan: dict, by: dict, datasets: dict, fail_after: str | None) -> None:
    c, key = ctx.client, plan["source_key"]
    rec = by.get(key, [])
    if rec and rec[0].data.tags.get(T_STATUS) == "complete":
        verify_one(ctx, exp, plan, by, datasets)
        ctx.stats["sources_noop"] += 1
        return
    bundles = bundle_members(plan)
    stage = ctx.ns / "staging" / key
    tar_info = {}
    for name, members in bundles.items():
        out = stage / name
        tar_info[name] = build_tar(ctx.repo, members, out) if not out.is_file() else {"bytes": out.stat().st_size, "sha256": S.sha(out)}
    if rec:
        parent = rec[0]
        if parent.data.tags.get(PROV + "bundle.models.tar.sha256") not in (None, tar_info["models.tar"]["sha256"]):
            raise SourceConflict(f"{key}: rebuilt models.tar differs from the in-progress record")
        ctx.stats["sources_resumed"] += 1
    else:
        parent = c.create_run(exp.experiment_id, run_name=plan["parent_run_name"],
                              tags=ordered({**parent_tags(plan, tar_info), T_STATUS: "in_progress"}))
        ctx.stats["parent_runs_created"] += 1
    pid = parent.info.run_id
    parent = c.get_run(pid)
    want = parent_tags(plan, tar_info)
    for k2, val in want.items():
        if k2 in parent.data.tags and parent.data.tags[k2] != str(val):
            raise SourceConflict(f"{key}: parent tag {k2} differs")
    ensure_params(c, parent, {"stage": plan["config"]["stage"], "model_scope": plan["config"]["model_scope"],
                              "n_views": len(plan["views"]), "n_versions": len(plan["versions"]),
                              "n_files": plan["counts"]["files"], "n_excluded": plan["counts"]["excluded"]})
    docs = {"manifests/plan-summary.json": jbytes(plan_summary(plan)), "manifests/inventory.json": jbytes(plan["files"]),
            "manifests/excluded.json": jbytes(plan["excluded"]), "manifests/plan.json": jbytes(plan)}
    for rel, data in docs.items():
        if ctx.artifact_sha(parent, rel) != X.sha_bytes(data):
            ctx.upload(pid, rel, data=data)
    for name, info in tar_info.items():
        if ctx.artifact_sha(parent, name) != info["sha256"]:
            ctx.upload(pid, name, src=stage / name)
    if fail_after == "parent-artifacts":
        raise Interrupt("injected interruption after parent artifacts")
    pids = parent_ids(ctx, exp.experiment_id, {**ctx.runs_by_key(exp.experiment_id)},
                      {m["bundle_source"] for ver in plan["versions"].values() for m in ver["members"]} | {key})
    models = ctx.logged_models(exp.experiment_id)
    kinds = {"fitted": 0, "reference": 1, "alias": 1, "evaluation_revision": 1, "metric_only": 2}
    for i, v in enumerate(sorted(plan["views"], key=lambda v: (kinds[v["view_kind"]], v["view_key"]))):
        import_child(ctx, exp, plan, v, pid, by, datasets, models, pids)
        if fail_after == f"child-{i}":
            raise Interrupt(f"injected interruption after child {i}")
    verify_one(ctx, exp, plan, ctx.runs_by_key(exp.experiment_id), datasets)
    c.set_tag(pid, T_STATUS, "complete")
    c.set_terminated(pid, "FINISHED")
    ctx.stats["sources_imported"] += 1


def ensure_params(c, run, params: dict) -> None:
    from mlflow.entities import Param
    have = run.data.params
    for k, v in params.items():
        if k in have and have[k] != str(v):
            raise SourceConflict(f"run {run.info.run_id}: param {k} already logged with a different value")
    ps = [Param(k, str(v)) for k, v in sorted(params.items()) if k not in have]
    for i in range(0, len(ps), 100):
        c.log_batch(run.info.run_id, params=ps[i:i + 100])


def import_child(ctx: Ctx, exp, plan: dict, v: dict, pid: str, by: dict, datasets: dict, models: dict, pids: dict) -> None:
    from mlflow.entities import LoggedModelInput, Metric, RunTag
    c = ctx.client
    rec = by.get(v["record_key"], [])
    tags = child_tags(plan, v, pid)
    if rec and rec[0].data.tags.get(T_STATUS) == "complete":
        ctx.stats["children_noop"] += 1
        return
    if rec:
        run = rec[0]
        ctx.stats["children_resumed"] += 1
    else:
        run = c.create_run(exp.experiment_id, run_name=v["run_name"], tags=ordered({**tags, T_STATUS: "in_progress"}))
        ctx.stats["children_created"] += 1
    rid = run.info.run_id
    run = c.get_run(rid)
    for k, val in tags.items():
        if k in run.data.tags and run.data.tags[k] != str(val):
            raise SourceConflict(f"{v['record_key']}: tag {k} differs")
    missing_tags = [RunTag(k, str(val)) for k, val in ordered(tags).items() if k not in run.data.tags]
    for i in range(0, len(missing_tags), 100):
        c.log_batch(rid, tags=missing_tags[i:i + 100])
    ver = plan["versions"].get(v.get("version_key") or "")
    model_id = None
    mdoc = None
    if ver is not None:
        mdoc = members_doc(ver, pids)
        mt = model_tags(plan, ver, X.sha_bytes(mdoc))
        lm = models.get(ver["version_key"])
        if lm is None:
            lm = ctx.mlflow.create_external_model(name=ver["logged_model"], source_run_id=rid, tags=mt,
                                                   params={k: str(x) for k, x in model_params(ver).items()},
                                                   model_type="external XGBoost booster bundle (catalog descriptor)",
                                                   experiment_id=exp.experiment_id)
            models[ver["version_key"]] = lm
            ctx.stats["logged_models_created"] += 1
        elif {k: lm.tags.get(k) for k in mt} != mt or lm.source_run_id != rid:
            raise SourceConflict(f"{ver['version_key']}: logged model exists with different tags or source run")
        model_id = lm.model_id
    elif v.get("alias_of"):
        lm = models.get(v["alias_of"])
        if lm is None:
            raise SourceConflict(f"{v['record_key']}: reused version {v['alias_of']} has no logged model (import its source first)")
        model_id = lm.model_id
    ensure_params(c, run, {"lead_months": v["lead"], "arm": v["arm"], "family": v["family"],
                           **({"n_inputs": v["n_inputs"]} if v.get("n_inputs") else {})})
    ts = int(time.time() * 1000)
    have = run.data.metrics
    mets = []
    for k, val in sorted(v["metrics"].items()):
        if k in have:
            if have[k] != val:
                raise SourceConflict(f"{v['record_key']}: metric {k} already logged with another value")
            continue
        dsn = v["metric_dataset"].get(k)
        ds = datasets[dsn] if dsn else None
        mets.append(Metric(k, float(val), ts, 0, model_id=model_id, dataset_name=ds["name"] if ds else None,
                           dataset_digest=ds["digest"] if ds else None))
    for i in range(0, len(mets), 1000):
        c.log_batch(rid, metrics=mets[i:i + 1000])
    ctx.stats["metrics_logged"] += len(mets)
    have_in = {(d.dataset.name, d.dataset.digest) for d in (run.inputs.dataset_inputs or [])}
    new_ds = [d for d in dataset_inputs(v, datasets) if (d.dataset.name, d.dataset.digest) not in have_in]
    for i in range(0, len(new_ds), 50):
        c.log_inputs(rid, datasets=new_ds[i:i + 50])
    if v.get("alias_of") and model_id and model_id not in {m.model_id for m in (run.inputs.model_inputs or [])}:
        c.log_inputs(rid, models=[LoggedModelInput(model_id)])
    ctx.stats["dataset_inputs_logged"] += len(new_ds)
    docs = view_docs(plan, v, datasets)
    if mdoc is not None:
        docs["members.json"] = mdoc
    for rel, data in docs.items():
        if ctx.artifact_sha(run, rel) != X.sha_bytes(data):
            ctx.upload(rid, rel, data=data)
    if ver is not None:
        ensure_version(ctx, plan, ver, rid, model_id)
    verify_child(ctx, c.get_run(rid), plan, v, pid, datasets, models, pids)
    c.set_tag(rid, T_STATUS, "complete")
    c.set_terminated(rid, "FINISHED")


def ensure_version(ctx: Ctx, plan: dict, ver: dict, rid: str, model_id: str) -> None:
    c = ctx.client
    name = ver["registered_model"]
    f = N.family(ver["family"])
    rm_tags = ordered({"family": ver["family"], "arm": ver["arm"], "lead_months": N.lead_tag(ver["lead"]), "model_scope": f["scope"],
                       "stage": f["stage"], "catalog": "external_descriptor", PROV + "catalog": "ipcch_forecasting"})
    desc = N.registered_model_description(ver["family"], ver["arm"], ver["lead"])
    try:
        rm = c.get_registered_model(name)
    except Exception:
        rm = None
    if rm is None:
        c.create_registered_model(name, tags=rm_tags, description=desc)
        ctx.stats["registered_models_created"] += 1
    elif {k: rm.tags.get(k) for k in rm_tags} != rm_tags or rm.description != desc:
        raise SourceConflict(f"registered model {name} exists with different tags/description")
    versions = {v.tags.get(T_VERSION): v for v in c.search_model_versions(f"name='{name}'")}
    if ver["version_key"] not in versions:
        c.create_model_version(name, source=f"models:/{model_id}", run_id=rid, model_id=model_id,
                               tags=ordered({"snapshot": plan["config"]["snapshot_label"], T_VERSION: ver["version_key"],
                                             T_SOURCE: plan["source_key"], T_FP: plan["fingerprint"]}),
                               description=version_description(plan, ver))
        ctx.stats["model_versions_created"] += 1


# ------------------------------------------------------------------ verify

def verify_child(ctx: Ctx, run, plan: dict, v: dict, pid: str, datasets: dict, models: dict, pids: dict) -> None:
    key = v["record_key"]
    want = {k: float(x) for k, x in v["metrics"].items()}
    if run.data.metrics != want:
        extra = set(run.data.metrics) - set(want)
        miss = set(want) - set(run.data.metrics)
        diff = [k for k in set(want) & set(run.data.metrics) if run.data.metrics[k] != want[k]]
        raise SourceConflict(f"{key}: metric readback differs (extra {sorted(extra)[:3]}, missing {sorted(miss)[:3]}, changed {diff[:3]})")
    for k, val in child_tags(plan, v, pid).items():
        if run.data.tags.get(k) != str(val):
            raise SourceConflict(f"{key}: tag {k} readback differs")
    check_inputs(run, dataset_inputs(v, datasets), key)
    ver = plan["versions"].get(v.get("version_key") or "")
    docs = view_docs(plan, v, datasets)
    if ver is not None:
        docs["members.json"] = members_doc(ver, pids)
        lm = models.get(ver["version_key"])
        if lm is None or lm.source_run_id != run.info.run_id:
            raise SourceConflict(f"{key}: logged model missing or bound to another run")
        mt = model_tags(plan, ver, X.sha_bytes(docs["members.json"]))
        if {k: lm.tags.get(k) for k in mt} != mt or lm.params != {k: str(x) for k, x in model_params(ver).items()}:
            raise SourceConflict(f"{key}: logged model tags/params differ")
        if "READY" not in str(lm.status):
            raise SourceConflict(f"{key}: logged model status {lm.status}")
        check_version(ctx, plan, ver, run.info.run_id, lm.model_id, key)
    if v.get("alias_of"):
        lm = models.get(v["alias_of"])
        if lm is None or lm.model_id not in {m.model_id for m in (run.inputs.model_inputs or [])}:
            raise SourceConflict(f"{key}: reused model input missing")
        target = alias_version(ctx, v["alias_of"], lm)
        if target is None:
            raise SourceConflict(f"{key}: reused registered version {v['alias_of']} missing")
    for rel, data in docs.items():
        if ctx.artifact_sha(run, rel) != X.sha_bytes(data):
            raise SourceConflict(f"{key}: artifact {rel} readback differs")


def check_inputs(run, want: list, key: str) -> None:
    """Dataset inputs: name, digest, source, schema, profile, source type and input tags all as planned."""
    def norm(d):
        return (d.dataset.name, d.dataset.digest, d.dataset.source_type, d.dataset.source, d.dataset.schema,
                d.dataset.profile, tuple(sorted((t.key, t.value) for t in (d.tags or []))))
    got = sorted(norm(d) for d in (run.inputs.dataset_inputs or []))
    if got != sorted(norm(d) for d in want):
        raise SourceConflict(f"{key}: dataset inputs differ from the plan ({len(got)} vs {len(want)})")


def check_version(ctx: Ctx, plan: dict, ver: dict, rid: str, model_id: str, key: str) -> None:
    name = ver["registered_model"]
    mv = [x for x in ctx.client.search_model_versions(f"name='{name}'") if x.tags.get(T_VERSION) == ver["version_key"]]
    want_tags = ordered({"snapshot": plan["config"]["snapshot_label"], T_VERSION: ver["version_key"],
                         T_SOURCE: plan["source_key"], T_FP: plan["fingerprint"]})
    if (len(mv) != 1 or mv[0].run_id != rid or mv[0].source != f"models:/{model_id}" or mv[0].status != "READY"
            or {k: mv[0].tags.get(k) for k in want_tags} != want_tags or mv[0].description != version_description(plan, ver)):
        raise SourceConflict(f"{key}: model version missing, duplicated or differs (run/model/tags/description/status)")
    rm = ctx.client.get_registered_model(name)
    if rm.description != N.registered_model_description(ver["family"], ver["arm"], ver["lead"]):
        raise SourceConflict(f"{key}: registered model description differs")


def alias_version(ctx: Ctx, version_key: str, lm):
    name = N.MODEL_PREFIX + " " + lm.name.rsplit(" | ", 1)[0]
    mv = [x for x in ctx.client.search_model_versions(f"name='{name}'") if x.tags.get(T_VERSION) == version_key]
    return mv[0] if len(mv) == 1 and mv[0].source == f"models:/{lm.model_id}" else None


def verify_one(ctx: Ctx, exp, plan: dict, by: dict, datasets: dict, deep_tars: bool = True) -> dict:
    key = plan["source_key"]
    rec = by.get(key, [])
    if len(rec) != 1:
        raise SourceConflict(f"{key}: expected one parent record, found {len(rec)}")
    parent = ctx.client.get_run(rec[0].info.run_id)
    if parent.data.tags.get(T_FP) != plan["fingerprint"]:
        raise SourceConflict(f"{key}: parent fingerprint differs")
    bundles = bundle_members(plan)
    for name, members in bundles.items():
        sha = parent.data.tags.get(f"{PROV}bundle.{name}.sha256")
        if ctx.artifact_sha(parent, name) != sha:
            raise SourceConflict(f"{key}: {name} artifact differs from its recorded digest")
        if deep_tars:
            p = ctx.artifact_path(parent, name)
            if p is None:
                with tempfile.TemporaryDirectory(prefix="ipcch-fc-tar-") as d:
                    tar_check(Path(ctx.client.download_artifacts(parent.info.run_id, name, d)), members)
            else:
                tar_check(p, members)
    for rel, data in {"manifests/plan-summary.json": jbytes(plan_summary(plan)), "manifests/inventory.json": jbytes(plan["files"]),
                      "manifests/excluded.json": jbytes(plan["excluded"]), "manifests/plan.json": jbytes(plan)}.items():
        if ctx.artifact_sha(parent, rel) != X.sha_bytes(data):
            raise SourceConflict(f"{key}: parent artifact {rel} differs")
    models = ctx.logged_models(exp.experiment_id)
    pids = parent_ids(ctx, exp.experiment_id, by, {m["bundle_source"] for ver in plan["versions"].values() for m in ver["members"]} | {key})
    child_ids = []
    for v in plan["views"]:
        rr = by.get(v["record_key"], [])
        if len(rr) != 1:
            raise SourceConflict(f"{v['record_key']}: expected one child record, found {len(rr)}")
        run = ctx.client.get_run(rr[0].info.run_id)
        if run.data.tags.get("mlflow.parentRunId") != parent.info.run_id:
            raise SourceConflict(f"{v['record_key']}: wrong parent")
        verify_child(ctx, run, plan, v, parent.info.run_id, datasets, models, pids)
        child_ids.append(run.info.run_id)
    dup = {k: n for k, n in ctx.metric_history_counts(child_ids).items() if n > 1}
    if dup:
        raise SourceConflict(f"{key}: duplicate metric history entries: {list(dup)[:3]}")
    return {"source": key, "children": len(child_ids), "metrics": sum(len(v["metrics"]) for v in plan["views"])}


def verify_sources(ctx: Ctx, plans: dict, all_plans: dict) -> list:
    exp = ctx.client.get_experiment_by_name(N.DETAILED_EXPERIMENT)
    if exp is None:
        raise SourceConflict("detailed experiment missing")
    by = ctx.runs_by_key(exp.experiment_id)
    datasets = all_datasets(all_plans)
    out = []
    for k in plans:
        if by.get(k, [None])[0] is None or by[k][0].data.tags.get(T_STATUS) != "complete":
            raise SourceConflict(f"{k}: not marked complete")
        out.append(verify_one(ctx, exp, plans[k], by, datasets))
    return out


# ------------------------------------------------------------------ dashboard

def dashboard_rows(cfg: dict, plans: dict) -> list:
    sup = P.superseded(cfg)
    rows = []
    for k, p in plans.items():
        if k in sup:
            continue
        for v in p["views"]:
            keep = {m: x for m, x in v["metrics"].items() if "diagnostic" not in m and ".country_" not in m}
            dsets = sorted({v["metric_dataset"][m] for m in keep if m in v["metric_dataset"]}
                           | {d for d in v["datasets"] if (p["datasets"].get(d) or {}).get("descriptor", {}).get("context") in ("training", "inference")})
            row = {"projection_key": f"{v['family']}/{v['arm']}/{N.lead_tag(v['lead'])}", "source_key": k,
                   "record_key": v["record_key"], "view": v, "metrics": keep,
                   "metric_dataset": {m: v["metric_dataset"][m] for m in keep if m in v["metric_dataset"]},
                   "datasets": dsets, "model_version": v.get("version_key") or v.get("alias_of"), "plan_fp": p["fingerprint"]}
            row["fingerprint"] = X.sha_bytes(X.canon({kk: row[kk] for kk in ("projection_key", "record_key", "metrics", "metric_dataset",
                                                                          "datasets", "model_version", "plan_fp")}))
            rows.append(row)
    return sorted(rows, key=lambda r: r["projection_key"])


def row_tags(plan: dict, row: dict, detailed_id: str, pid: str) -> dict:
    t = child_tags(plan, row["view"], pid)
    t.pop("mlflow.parentRunId")
    t.update({"record_kind": "dashboard_row", T_PROJ: row["projection_key"], T_ROWFP: row["fingerprint"],
              PROV + "detailed_run_id": detailed_id})
    t.pop(T_KEY)
    return t


def apply_dashboard(ctx: Ctx, cfg: dict, plans: dict, fail_after: str | None = None) -> dict:
    from mlflow.entities import LoggedModelInput, Metric, RunTag
    c = ctx.client
    det = c.get_experiment_by_name(N.DETAILED_EXPERIMENT)
    by = ctx.runs_by_key(det.experiment_id)
    models = ctx.logged_models(det.experiment_id)
    datasets = all_datasets(plans)
    exp = c.get_experiment_by_name(N.DASHBOARD_EXPERIMENT)
    if exp is not None and exp.tags.get("catalog_status") == "complete" and exp.tags.get(N.NOTE) == N.dashboard_description():
        try:
            verify_dashboard(ctx, cfg, plans)
            ctx.stats["dashboard_noop"] += 1
            return dict(ctx.stats)
        except SourceConflict:
            pass
    exp = ctx.experiment(N.DASHBOARD_EXPERIMENT, N.dashboard_description())
    c.set_experiment_tag(exp.experiment_id, "catalog_status", "incomplete")
    have = ctx.runs_by_key(exp.experiment_id)
    rows = dashboard_rows(cfg, plans)
    planned = {r["projection_key"] for r in rows}
    for i, row in enumerate(rows):
        plan = plans[row["source_key"]]
        drec = by.get(row["record_key"], [])
        if len(drec) != 1 or drec[0].data.tags.get(T_STATUS) != "complete":
            raise SourceConflict(f"{row['record_key']}: detailed record missing or incomplete")
        did = drec[0].info.run_id
        pid = drec[0].data.tags["mlflow.parentRunId"]
        tags = row_tags(plan, row, did, pid)
        current = [r for r in have.get(row["projection_key"], [])]
        same = [r for r in current if r.data.tags.get(T_ROWFP) == row["fingerprint"]]
        if len(same) > 1:
            raise SourceConflict(f"{row['projection_key']}: two rows with the same fingerprint")
        if same and same[0].data.tags.get(T_ROWSTATUS) == "complete":
            retire(ctx, [r for r in current if r.info.run_id != same[0].info.run_id], same[0].info.run_id)
            ctx.stats["rows_noop"] += 1
            continue
        run = same[0] if same else c.create_run(exp.experiment_id, run_name=row["view"]["run_name"],
                                                 tags=ordered({**tags, T_ROWSTATUS: "in_progress"}))
        ctx.stats["rows_resumed" if same else "rows_created"] += 1
        rid = run.info.run_id
        run = c.get_run(rid)
        miss = [RunTag(k, v) for k, v in ordered(tags).items() if k not in run.data.tags]
        for j in range(0, len(miss), 100):
            c.log_batch(rid, tags=miss[j:j + 100])
        lm = models.get(row["model_version"]) if row["model_version"] else None
        mid = lm.model_id if lm else None
        ensure_params(c, run, {"lead_months": row["view"]["lead"], "arm": row["view"]["arm"], "family": row["view"]["family"]})
        ts = int(time.time() * 1000)
        mets = []
        for k, val in sorted(row["metrics"].items()):
            if k in run.data.metrics:
                continue
            ds = datasets.get(row["metric_dataset"].get(k) or "")
            mets.append(Metric(k, float(val), ts, 0, model_id=mid, dataset_name=ds["name"] if ds else None, dataset_digest=ds["digest"] if ds else None))
        for j in range(0, len(mets), 1000):
            c.log_batch(rid, metrics=mets[j:j + 1000])
        vv = {**row["view"], "datasets": row["datasets"], "metric_dataset": row["metric_dataset"]}
        got = {(d.dataset.name, d.dataset.digest) for d in (run.inputs.dataset_inputs or [])}
        new = [d for d in dataset_inputs(vv, datasets) if (d.dataset.name, d.dataset.digest) not in got]
        for j in range(0, len(new), 50):
            c.log_inputs(rid, datasets=new[j:j + 50])
        if mid and mid not in {m.model_id for m in (run.inputs.model_inputs or [])}:
            c.log_inputs(rid, models=[LoggedModelInput(mid)])
        doc = row_doc(row, did)
        if ctx.artifact_sha(run, "dashboard/row.json") != X.sha_bytes(doc):
            ctx.upload(rid, "dashboard/row.json", data=doc)
        verify_row(ctx, c.get_run(rid), plan, row, did, pid, datasets, mid)
        c.set_tag(rid, T_ROWSTATUS, "complete")
        c.set_terminated(rid, "FINISHED")
        if fail_after == f"row-{i}-before-retire":
            raise Interrupt(f"injected interruption after dashboard row {i}, before retiring superseded rows")
        retire(ctx, [r for r in current if r.info.run_id != rid], rid)
        if fail_after == f"row-{i}":
            raise Interrupt(f"injected interruption after dashboard row {i}")
    for k, runs in have.items():
        if k not in planned:
            for r in runs:
                c.set_tag(r.info.run_id, PROV + "superseded_by", "no current snapshot")
                c.delete_run(r.info.run_id)
                ctx.stats["rows_retired"] += 1
    verify_dashboard(ctx, cfg, plans)
    c.set_experiment_tag(exp.experiment_id, "catalog_status", "complete")
    return dict(ctx.stats)


def retire(ctx: Ctx, runs: list, by_rid: str) -> None:
    """Soft-delete superseded dashboard rows (restorable); detailed snapshots are never touched."""
    for r in runs:
        ctx.client.set_tag(r.info.run_id, PROV + "superseded_by", by_rid)
        ctx.client.delete_run(r.info.run_id)
        ctx.stats["rows_retired"] += 1


def row_doc(row: dict, did: str) -> bytes:
    return jbytes({"projection_key": row["projection_key"], "detailed_run_id": did, "source_key": row["source_key"],
                   "model_version": row["model_version"], "metrics": {k: {"value": x, "dataset": row["metric_dataset"].get(k)}
                                                                       for k, x in sorted(row["metrics"].items())}})


def verify_row(ctx: Ctx, run, plan: dict, row: dict, did: str, pid: str, datasets: dict, mid: str | None) -> None:
    if run.data.metrics != {k: float(x) for k, x in row["metrics"].items()}:
        raise SourceConflict(f"{row['projection_key']}: dashboard metric readback differs")
    for k, v in row_tags(plan, row, did, pid).items():
        if run.data.tags.get(k) != str(v):
            raise SourceConflict(f"{row['projection_key']}: dashboard tag {k} differs")
    vv = {**row["view"], "datasets": row["datasets"], "metric_dataset": row["metric_dataset"]}
    check_inputs(run, dataset_inputs(vv, datasets), row["projection_key"])
    if mid and {m.model_id for m in (run.inputs.model_inputs or [])} != {mid}:
        raise SourceConflict(f"{row['projection_key']}: dashboard model input missing or extra")
    if ctx.artifact_sha(run, "dashboard/row.json") != X.sha_bytes(row_doc(row, did)):
        raise SourceConflict(f"{row['projection_key']}: dashboard/row.json differs")


def verify_dashboard(ctx: Ctx, cfg: dict, plans: dict) -> dict:
    c = ctx.client
    det = c.get_experiment_by_name(N.DETAILED_EXPERIMENT)
    exp = c.get_experiment_by_name(N.DASHBOARD_EXPERIMENT)
    by, have = ctx.runs_by_key(det.experiment_id), ctx.runs_by_key(exp.experiment_id)
    models, datasets = ctx.logged_models(det.experiment_id), all_datasets(plans)
    rows = dashboard_rows(cfg, plans)
    if exp is None or set(have) != {r["projection_key"] for r in rows}:
        raise SourceConflict("dashboard rows differ from the plan")
    ids = []
    for row in rows:
        rr = have[row["projection_key"]]
        if len(rr) != 1 or rr[0].data.tags.get(T_ROWFP) != row["fingerprint"]:
            raise SourceConflict(f"{row['projection_key']}: expected one current row with the planned fingerprint")
        d = by[row["record_key"]][0]
        lm = models.get(row["model_version"]) if row["model_version"] else None
        verify_row(ctx, c.get_run(rr[0].info.run_id), plans[row["source_key"]], row, d.info.run_id,
                   d.data.tags["mlflow.parentRunId"], datasets, lm.model_id if lm else None)
        ids.append(rr[0].info.run_id)
    dup = {k: n for k, n in ctx.metric_history_counts(ids).items() if n > 1}
    if dup:
        raise SourceConflict(f"dashboard duplicate metric history: {list(dup)[:3]}")
    return {"rows": len(rows)}


def detailed_description() -> str:
    return ("**IPCCH Forecasting - detailed runs**: one parent run per source snapshot (archived source files, models.tar, "
            "manifests) and one child run per family x arm x lead (every saved metric with its source locator, NA reasons, "
            "evaluation/training/inference datasets and model members). Start from the dashboard experiment for "
            "comparisons. Records are historical imports: MLflow times are registration times, not fit times; models are "
            "external descriptors without a prediction wrapper. See IPCCHMLflow/README.md in the IPCCH repository.")


# ------------------------------------------------------------------ CLI

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="IPCCH Forecasting MLflow catalog")
    ap.add_argument("cmd", choices=["plan", "import", "verify", "dashboard", "dashboard-verify"])
    ap.add_argument("--source", action="append", help="limit to source key(s); dependencies are planned as well")
    ap.add_argument("--tracking-uri")
    ap.add_argument("--store", type=Path, default=P.DEFAULT_STORE, help="store root (namespace dirs under ipcch-forecasting/)")
    ap.add_argument("--sources-json", type=Path)
    ap.add_argument("--repo", type=Path, default=P.REPO)
    ap.add_argument("--live", action="store_true", help="allow the live service on port 5000 (only after release)")
    ap.add_argument("--rehash", action="store_true")
    ap.add_argument("--fail-after", help=argparse.SUPPRESS)
    ap.add_argument("--out", type=Path, help="write a JSON result here")
    a = ap.parse_args(argv)
    cfg = P.load_sources(a.sources_json)
    full = P.build_plans(cfg, a.repo, a.store, None, a.rehash)
    sel = {k: full[k] for k in (P.order(cfg, a.source) if a.source else full) if not a.source or k in a.source}
    if a.cmd == "plan":
        d = P.write_plans(full, a.store)
        res = {"plans": str(d), "totals": P.check_global(cfg, full, True),
               "fingerprints": {k: p["fingerprint"] for k, p in full.items()}}
    else:
        if not a.tracking_uri:
            raise SystemExit("--tracking-uri is required")
        ctx = Ctx(a.tracking_uri, a.store, a.live, a.repo)
        with S.Lock(a.store):
            if a.cmd == "import":
                res = import_sources(ctx, sel, full, a.fail_after)
                P.write_plans({k: full[k] for k in sel}, a.store)
            elif a.cmd == "verify":
                res = {"verified": verify_sources(ctx, sel, full)}
            elif a.cmd == "dashboard":
                res = apply_dashboard(ctx, cfg, full, a.fail_after)
            else:
                res = verify_dashboard(ctx, cfg, full)
    text = json.dumps(res, indent=1, default=str)
    if a.out:
        a.out.write_text(text)
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
