"""Read-only planning for the IPCCH Forecasting MLflow catalog.

``build_plans`` hashes every file under the explicit source roots (no discovery outside them),
classifies each file (model bundle member / archived source file / excluded with reason), adds
the explicitly cited external files with their pinned SHA256, scans uploadable text for excluded
family results, runs the format extractor and applies cross-source checks (one dataset name = one
digest, unique registered-model/version identities, frozen expected counts). Nothing is written
outside the IPCCH namespace's plans/ and cache/ directories.
"""

from __future__ import annotations

import fnmatch
import json
import os
import re
from collections import Counter
from pathlib import Path

import extract as X
import naming as N
from naming import SourceConflict

IMPORTER_VERSION = "ipcch-forecasting-import-v1"
HERE = Path(__file__).resolve().parent
REPO = HERE.parent
DEFAULT_STORE = Path("/home/swl007007/.local/share/ipcch-mlflow")
NAMESPACE = "ipcch-forecasting"
BINARY = (".ubj", ".gz", ".npz", ".npy", ".xlsx", ".png", ".tar")


def load_sources(path: Path | None = None) -> dict:
    cfg = json.loads((path or HERE / "sources.json").read_text())
    keys = [s["source_key"] for s in cfg["sources"]]
    if len(keys) != len(set(keys)):
        raise SourceConflict("duplicate source_key in sources.json")
    return cfg


class Hasher:
    """sha256 with a stat-keyed cache (size, mtime_ns) -- the cache is only a speed-up, never date evidence."""

    def __init__(self, cache: Path | None, rehash: bool = False):
        self.cache = cache
        self.data = {} if (rehash or cache is None or not cache.is_file()) else json.loads(cache.read_text())
        self.dirty = False

    def __call__(self, p: Path) -> dict:
        st = p.stat()
        k = str(p)
        hit = self.data.get(k)
        if hit and hit["bytes"] == st.st_size and hit["mtime_ns"] == st.st_mtime_ns:
            return {"bytes": st.st_size, "sha256": hit["sha256"]}
        h = X.sha_file(p)
        self.data[k] = {"bytes": st.st_size, "mtime_ns": st.st_mtime_ns, "sha256": h}
        self.dirty = True
        return {"bytes": st.st_size, "sha256": h}

    def save(self) -> None:
        if self.cache is not None and self.dirty:
            self.cache.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.cache.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.data))
            os.replace(tmp, self.cache)


def source_inventory(repo: Path, src: dict, hasher: Hasher) -> dict:
    root = repo / src["root"]
    if not root.is_dir():
        raise SourceConflict(f"{src['source_key']}: source root missing: {root}")
    inv = {}
    for dp, dns, fns in os.walk(root):
        dns.sort()
        for fn in sorted(fns):
            p = Path(dp) / fn
            inv[str(p.relative_to(repo))] = hasher(p)
    return inv


def matches(rel_in_root: str, globs: list) -> dict | None:
    for g in globs:
        if fnmatch.fnmatch(rel_in_root, g["glob"]) or fnmatch.fnmatch("/" + rel_in_root, "*/" + g["glob"].lstrip("*/")):
            return g
    return None


def leak_scan(repo: Path, paths: list, forbidden: list) -> list:
    pat = re.compile("|".join(re.escape(f) for f in forbidden), re.I)
    hits = []
    for rel in paths:
        if rel.endswith(BINARY):
            continue
        txt = (repo / rel).read_text(errors="ignore")
        m = pat.search(txt)
        if m:
            hits.append(f"{rel}: {m.group(0)}")
    return hits


def jsonable(obj):
    if isinstance(obj, dict):
        return {k: jsonable(v) for k, v in obj.items() if not k.startswith("_")}
    if isinstance(obj, (list, tuple)):
        return [jsonable(v) for v in obj]
    if isinstance(obj, set):
        return sorted(jsonable(v) for v in obj)
    return obj


def plan_source(cfg: dict, src: dict, repo: Path, hasher: Hasher, plans: dict) -> dict:
    inv = source_inventory(repo, src, hasher)
    external = {}
    for c in src.get("cited", []):
        rec = hasher(repo / c["path"])
        if rec["sha256"] != c["sha256"]:
            raise SourceConflict(f"{src['source_key']}: cited file changed since it was pinned: {c['path']}")
        external[c["path"]] = {**rec, "role": c["role"]}
    deps = {"plans": plans, "external": external}
    b = X.Builder(src, repo, inv, deps)
    X.EXTRACTORS[src["format"]](b)
    # file decisions
    own_members = {m["path"] for v in b.versions.values() for m in v["members"] if m["bundle_source"] == src["source_key"]}
    files, excluded = [], []
    for rel, rec in sorted(inv.items()):
        in_root = rel[len(src["root"]) + 1:]
        ex = matches(in_root, src.get("exclude", []))
        if ex:
            excluded.append({"path": rel, **rec, "reason": ex["reason"]})
            continue
        if rel in own_members:
            decision = "bundle:models.tar"
        elif rel in b.revision_members:
            decision = f"reference:{src['revision_of']} models.tar (unchanged model member; not re-uploaded)"
        elif matches(in_root, [{"glob": g} for g in src.get("diagnostics_globs", [])]):
            decision = "archive:source.tar (diagnostic; not imported as metrics)"
        else:
            decision = "archive:source.tar"
        files.append({"path": rel, **rec, "decision": decision})
    for rel, rec in sorted(external.items()):
        files.append({"path": rel, "bytes": rec["bytes"], "sha256": rec["sha256"], "decision": f"archive:source.tar (cited {rec['role']})"})
    missing_members = own_members - {f["path"] for f in files if f["decision"].startswith("bundle")}
    if missing_members:
        raise SourceConflict(f"{src['source_key']}: model members excluded or missing: {sorted(missing_members)[:5]}")
    hits = leak_scan(repo, [f["path"] for f in files], cfg["forbidden_content"])
    if hits:
        raise SourceConflict(f"{src['source_key']}: excluded-family content in uploadable files: {hits[:5]}")
    views = []
    for v in sorted(b.views.values(), key=lambda x: x["key"]):
        v = dict(v)
        if v["view_kind"] in ("alias", "reference", "evaluation_revision") and not v.get("alias_of"):
            raise SourceConflict(f"{src['source_key']} {v['key']}: alias/reference view without a target version")
        if v["view_kind"] == "fitted" and not v.get("version_key"):
            raise SourceConflict(f"{src['source_key']} {v['key']}: fitted view without a model version")
        v["view_key"] = v.pop("key")
        v["record_key"] = f"{src['source_key']}/{v['view_key']}"
        v["run_name"] = N.run_name(v["family"], v["arm"], v["lead"])
        v["slot_status_text"] = slot_text(v["slots"])
        statuses = {s.split(" ")[0] for s in v["slots"].values()}
        v["source_status"] = ("prediction_summary_only" if statuses == {"prediction_summary_only"} else
                              "incomplete_slots" if "incomplete" in statuses else
                              "empty_slots" if "empty_cohort" in statuses else
                              "complete_with_undefined_metrics" if (v["na"] or len(statuses - {"complete"}) > 0) else "complete")
        v["description"] = N.view_description(v, src)
        views.append(jsonable(v))
    plan = {"source_key": src["source_key"], "importer": IMPORTER_VERSION, "config": src,
            "families": src["families"], "parent_run_name": N.family(src["families"][0])["long"],
            "parent_description": N.parent_description(src["families"], src),
            "files": files, "excluded": excluded, "views": views,
            "datasets": jsonable(b.datasets), "versions": jsonable(b.versions), "cross_checks": b.cross_checks}
    plan["counts"] = {"files": len(files), "excluded": len(excluded), "views": len(views),
                      "views_by_kind": dict(Counter(v["view_kind"] for v in views)),
                      "versions": len(b.versions), "datasets": len(b.datasets),
                      "metrics": sum(len(v["metrics"]) for v in views), "na": sum(len(v["na"]) for v in views),
                      "boosters_own": sum(1 for f in files if f["path"].endswith(".ubj")),
                      "fit_units_new": sum(v["fit_units_new"] for v in b.versions.values())}
    plan["fingerprint"] = X.sha_bytes(X.canon({k: v for k, v in plan.items() if k != "fingerprint"}))
    return plan


def slot_text(slots: dict) -> str:
    """Per-slot status: non-complete slots listed by name, complete slots counted."""
    if not slots:
        return "no saved slot status."
    complete = sorted(k for k, s in slots.items() if s == "complete")
    other = sorted((k, s) for k, s in slots.items() if s != "complete")
    parts = [f"{len(complete)} slot(s) complete"] if complete else []
    parts += [f"{k}: {s}" for k, s in other[:12]]
    if len(other) > 12:
        parts.append(f"... {len(other) - 12} more non-complete slots in view/na.json")
    return "; ".join(parts) + "."


MUTABLE_CONFIG = ("frozen",)


def frozen_plan(ns: Path, src: dict) -> dict:
    """An imported snapshot whose source files may since have been rewritten (evaluation-only update):
    its stored plan (written at import) is authoritative; it is never re-planned from disk."""
    p = ns / "plans" / f"{src['source_key']}.json"
    if not p.is_file():
        raise SourceConflict(f"{src['source_key']}: frozen snapshot has no stored plan at {p}; import it before freezing")
    plan = json.loads(p.read_text())
    want = {k: v for k, v in src.items() if k not in MUTABLE_CONFIG}
    have = {k: v for k, v in plan["config"].items() if k not in MUTABLE_CONFIG}
    if want != have:
        raise SourceConflict(f"{src['source_key']}: a frozen snapshot's configuration cannot change")
    if X.sha_bytes(X.canon({k: v for k, v in plan.items() if k != "fingerprint"})) != plan["fingerprint"]:
        raise SourceConflict(f"{src['source_key']}: stored plan does not match its fingerprint")
    return plan


def order(cfg: dict, keys=None) -> list:
    by = {s["source_key"]: s for s in cfg["sources"]}
    want = set(keys or by)
    deps = lambda s: [d for d in (s.get("extends"), s.get("revision_of"), s.get("reference_source"),
                                  (s.get("region3") or {}).get("reference_source")) if d]
    out, seen = [], set()

    def visit(k, stack=()):
        if k in seen:
            return
        if k not in by:
            raise SourceConflict(f"unknown source {k!r}")
        if k in stack:
            raise SourceConflict(f"dependency cycle at {k}")
        for d in deps(by[k]):
            visit(d, stack + (k,))
        seen.add(k)
        out.append(k)
    for k in sorted(want):
        visit(k)
    return out


def superseded(cfg: dict) -> set:
    return {s["supersedes"] for s in cfg["sources"] if s.get("supersedes")}


def build_plans(cfg: dict, repo: Path = REPO, store: Path | None = None, keys=None, rehash: bool = False) -> dict:
    ns = (store or DEFAULT_STORE) / NAMESPACE
    hasher = Hasher(ns / "cache" / "hashes.json" if store is not False else None, rehash)
    plans = {}
    try:
        for k in order(cfg, keys):
            src = next(s for s in cfg["sources"] if s["source_key"] == k)
            plans[k] = frozen_plan(ns, src) if src.get("frozen") else plan_source(cfg, src, repo, hasher, plans)
    finally:
        hasher.save()
    check_global(cfg, plans, full=keys is None)
    return plans


def check_global(cfg: dict, plans: dict, full: bool) -> dict:
    names = {}
    for p in plans.values():
        for n, d in p["datasets"].items():
            if n in names and names[n] != d["full_sha256"]:
                raise SourceConflict(f"dataset name {n!r} has two contents across sources")
            names[n] = d["full_sha256"]
    rm, vkeys = Counter(), set()
    for p in plans.values():
        for vk, ver in p["versions"].items():
            if vk in vkeys:
                raise SourceConflict(f"duplicate version key {vk}")
            vkeys.add(vk)
            rm[ver["registered_model"]] += 1
    sup = superseded(cfg)
    rows = [v for k, p in plans.items() if k not in sup for v in p["views"]]
    proj = Counter(f"{v['family']}/{v['arm']}/{v['lead']:02d}" for v in rows)
    dup = [k for k, n in proj.items() if n > 1]
    if dup:
        raise SourceConflict(f"two current snapshots project to the same dashboard row: {dup[:5]}")
    totals = {"registered_models": len(rm), "model_versions": len(vkeys),
              "detailed_children": sum(len(p["views"]) for p in plans.values()), "dashboard_rows": len(rows),
              "booster_files": sum(p["counts"]["boosters_own"] for p in plans.values()),
              "fit_units_new": sum(p["counts"]["fit_units_new"] for p in plans.values()),
              "datasets": len(names), "metrics": sum(p["counts"]["metrics"] for p in plans.values()),
              "na": sum(p["counts"]["na"] for p in plans.values())}
    if full:
        bad = {k: (totals[k], v) for k, v in cfg["expected"].items() if totals.get(k) != v}
        if bad:
            raise SourceConflict(f"plan counts differ from the frozen expected counts: {bad}")
    return totals


def write_plans(plans: dict, store: Path) -> Path:
    d = store / NAMESPACE / "plans"
    d.mkdir(parents=True, exist_ok=True)
    for k, p in plans.items():
        tmp = d / f"{k}.json.tmp"
        tmp.write_text(json.dumps(p, sort_keys=True))
        os.replace(tmp, d / f"{k}.json")
    return d
