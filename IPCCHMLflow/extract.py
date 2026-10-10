"""Explicit source extractors for the IPCCH Forecasting MLflow catalog (read-only over sources).

Each extractor reads named files of one saved source format and fills a ``Builder``:
views (one per family x arm x lead), metrics with exact file/row/column locators, NA records
with the source reason, evaluation datasets (sorted keys + truth + definition + scope),
training/inference descriptors and model versions with their required members. No metric is
computed here: values are copied; only key/truth hashes are derived for dataset identity.
"""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

import naming as N
from naming import SourceConflict

CHUNK = 1 << 22


def canon(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode()


def sha_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(CHUNK), b""):
            h.update(b)
    return h.hexdigest()


def read_csv(p: Path, **kw) -> pd.DataFrame:
    return pd.read_csv(p, float_precision="round_trip", low_memory=False, **kw)


def ym(ord_: int) -> str:
    return f"{int(ord_) // 12:04d}-{int(ord_) % 12 + 1:02d}"


def finite(v) -> bool:
    try:
        return v is not None and not (isinstance(v, str)) and math.isfinite(float(v))
    except (TypeError, ValueError):
        return False


def text(v) -> str | None:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    s = str(v)
    return None if s in ("", "nan", "None") else s


# ------------------------------------------------------------------ builder

class Builder:
    """Collects one source snapshot's planned objects."""

    def __init__(self, src: dict, repo: Path, inventory: dict, deps: dict):
        self.src, self.repo, self.inv, self.deps = src, repo, inventory, deps
        self.root = src["root"]
        self.views: dict = {}
        self.datasets: dict = {}
        self.versions: dict = {}
        self.cross_checks = 0
        self.revision_members: set = set()

    # ---- paths
    def rel(self, p: str) -> str:
        return f"{self.root}/{p}" if not p.startswith(self.root + "/") else p

    def path(self, rel: str) -> Path:
        return self.repo / rel

    def need(self, rel: str) -> dict:
        if rel not in self.inv:
            raise SourceConflict(f"{self.src['source_key']}: required file missing from the source inventory: {rel}")
        return self.inv[rel]

    # ---- views
    def view(self, fam: str, arm_raw: str, h, kind: str, **extra) -> dict:
        N.family(fam)
        arm_name, role = N.arm(arm_raw)
        key = f"{fam}/{arm_name}/{N.lead_tag(h)}"
        v = self.views.get(key)
        if v is None:
            v = self.views[key] = {"key": key, "family": fam, "arm_raw": arm_raw, "arm": arm_name, "arm_role": role,
                                   "lead": int(h), "view_kind": kind, "metrics": {}, "sources": {}, "na": {},
                                   "metric_dataset": {}, "datasets": set(), "slots": {}, "version_key": None,
                                   "alias_of": None, "alias_text": None}
        elif v["view_kind"] != kind and not (v["view_kind"] == "evaluation_revision" and kind == "fitted"):
            raise SourceConflict(f"{key}: view kind {v['view_kind']} vs {kind}")
        v.update({k: x for k, x in extra.items() if x is not None})
        return v

    def put(self, v: dict, key: str, value, file: str, row, col: str, original: str, dataset: str | None = None,
            reason: str | None = None, status: str | None = None) -> None:
        """Log a finite source value, else record NA with the source's reason."""
        if finite(value):
            value = float(value)
            if key in v["metrics"]:
                if v["metrics"][key] != value:
                    raise SourceConflict(f"{v['key']}: two source values map to {key} ({v['metrics'][key]} vs {value}; "
                                         f"{v['sources'][key]} vs {file}:{row}:{col})")
                if v["metric_dataset"].get(key) != dataset:
                    raise SourceConflict(f"{v['key']}: {key} repeated with a different evaluation dataset "
                                         f"({v['metric_dataset'].get(key)!r} vs {dataset!r}; {file}:{row}:{col})")
                v["sources"][key].setdefault("also", []).append({"file": file, "row": row, "column": col, "original": original})
                self.cross_checks += 1
                return
            if key in v["na"]:
                raise SourceConflict(f"{v['key']}: {key} is both NA and finite")
            v["metrics"][key] = value
            v["sources"][key] = {"file": file, "row": row, "column": col, "original": original}
            if dataset:
                v["metric_dataset"][key] = dataset
                v["datasets"].add(dataset)
        else:
            if key in v["metrics"]:
                raise SourceConflict(f"{v['key']}: {key} is both finite and NA")
            v["na"].setdefault(key, {"file": file, "row": row, "column": col, "original": original,
                                     "status": status or "undefined",
                                     "reason": reason or "source value missing; no reason recorded in the source"})

    def slot(self, v: dict, role: str, coh: str, status: str, detail: str | None = None) -> None:
        k = f"{role}.{coh}"
        v["slots"][k] = status + (f" ({detail})" if detail else "")

    # ---- datasets
    def eval_dataset(self, h, role: str, coh: str, group: str, keys: pd.DataFrame, truth_cols: list,
                     truth_definition: str, n_required: int | None = None, basis: str = "reconstructed",
                     source_hash: dict | None = None, extra_key_cols: tuple = (), months: list | None = None) -> str:
        """Dataset descriptor over sorted keys AND truth AND definition AND support AND scope."""
        if basis != "reconstructed":
            raise SourceConflict(f"{self.src['source_key']}: dataset {role}.{coh} H{h} has no reconstructable keys")
        k = keys.sort_values(["area_id", "target_ord", *extra_key_cols], kind="mergesort").reset_index(drop=True)
        if k.duplicated(["area_id", "target_ord", *extra_key_cols]).any():
            raise SourceConflict(f"{self.src['source_key']}: duplicate evaluation keys in {role}.{coh} H{h}")
        key_lines = "\n".join("|".join(str(x) for x in r) for r in k[["area_id", "target_ord", *extra_key_cols]].itertuples(index=False))
        truth_lines = "\n".join("|".join(repr(x) if isinstance(x, float) else str(x) for x in r)
                                for r in k[["area_id", "target_ord", *extra_key_cols, *truth_cols]].itertuples(index=False))
        n_keys = len(k)
        month_list = [ym(o) for o in sorted(set(int(x) for x in k["target_ord"]))]
        keys_sha, truth_sha = sha_bytes(key_lines.encode()), sha_bytes(truth_lines.encode())
        span = f"{month_list[0]}..{month_list[-1]}" if month_list else "no rows"
        coh_name = N.cohort(coh)
        desc = {"context": "evaluation", "lead_months": int(h), "period": span, "months": month_list,
                "cohort": coh_name, "cohort_definition": N.cohort_definition(coh_name), "group": group,
                "truth_definition": truth_definition, "truth_columns": truth_cols, "key_columns": ["area_id", "target_ord", *extra_key_cols],
                "n_keys": n_keys, "n_required": n_required if n_required is not None else n_keys,
                "keys_sha256": keys_sha, "truth_sha256": truth_sha, "source_cohort_hash": source_hash}
        name = N.eval_dataset_name(h, span, coh_name, group)
        return self._dataset(name, desc)

    def training_dataset(self, fam: str, h, n_inputs: int, desc: dict) -> str:
        name = N.training_dataset_name(fam, self.src.get("training_qualifier", ""), n_inputs, h)
        return self._dataset(name, {"context": "training", "lead_months": int(h), "n_inputs": n_inputs,
                                    "model_scope": N.family(fam)["scope"], **desc})

    def inference_dataset(self, scope_label: str, inputs_label: str, origin: str, target: str, desc: dict) -> str:
        name = N.inference_dataset_name(scope_label, inputs_label, origin, target)
        return self._dataset(name, {"context": "inference", "origin": origin, "target": target, **desc})

    def _dataset(self, name: str, desc: dict) -> str:
        full = sha_bytes(canon(desc))
        d = self.datasets.get(name)
        if d is not None and d["full_sha256"] != full:
            raise SourceConflict(f"dataset name {name!r} would have two contents in {self.src['source_key']}")
        self.datasets[name] = {"name": name, "digest": full[:32], "full_sha256": full, "descriptor": desc}
        return name

    # ---- versions
    def version(self, v: dict, members: list, training: str | None, n_inputs: int | None, fit_units: int) -> dict:
        rev = self.src.get("revision_of")
        if rev:
            return self._revision(v, rev, members, n_inputs)
        vk = f"{v['key']}@{self.src['source_key']}"
        missing = [m for m in members if m["path"] not in self.inv and m.get("bundle_source", self.src["source_key"]) == self.src["source_key"]]
        if missing:
            raise SourceConflict(f"{vk}: required member(s) missing: {[m['path'] for m in missing[:5]]}")
        for m in members:
            if m.get("bundle_source", self.src["source_key"]) == self.src["source_key"]:
                rec = self.inv[m["path"]]
                if m.get("sha256") and m["sha256"] != rec["sha256"]:
                    raise SourceConflict(f"{vk}: member {m['path']} sha differs from its source record")
                m["sha256"], m["bytes"] = rec["sha256"], rec["bytes"]
        boosters = [m for m in members if m["role"] == "booster"]
        if not boosters:
            raise SourceConflict(f"{vk}: no booster members")
        ver = {"version_key": vk, "view_key": v["key"], "family": v["family"], "arm": v["arm"], "lead": v["lead"],
               "registered_model": N.registered_model_name(v["family"], v["arm"], v["lead"]),
               "logged_model": N.logged_model_name(v["family"], v["arm"], v["lead"], self.src["snapshot_label"]),
               "members": sorted(members, key=lambda m: (m["role"], m["path"], m.get("job", ""))),
               "training_dataset": training, "n_inputs": n_inputs, "fit_units_new": fit_units,
               "boosters_total": len(boosters),
               "boosters_new": sum(1 for m in boosters if m["kind"] == "fitted"),
               "boosters_reused": sum(1 for m in boosters if m["kind"] == "reused_from_snapshot"),
               "boosters_alias": sum(1 for m in boosters if m["kind"] == "alias_selected_recipe")}
        self.versions[vk] = ver
        v["version_key"] = vk
        v["n_inputs"] = n_inputs
        return ver

    def _revision(self, v: dict, rev: str, members: list, n_inputs: int | None) -> dict:
        """Evaluation-only revision: the fitted members must equal the prior snapshot's version exactly;
        the view then reuses that registered version (no new version, no re-bundled weights)."""
        prior = self.deps["plans"].get(rev)
        if prior is None:
            raise SourceConflict(f"{self.src['source_key']}: revision_of {rev!r} is not planned")
        pk = f"{v['key']}@{rev}"
        if pk not in prior["versions"]:
            raise SourceConflict(f"{self.src['source_key']}: {v['key']} has no version in {rev}; a new fit needs a new training snapshot")
        want = {(m["path"], m["role"], m.get("sha256")) for m in prior["versions"][pk]["members"]}
        got = set()
        for m in members:
            rec = self.inv.get(m["path"]) if m.get("bundle_source", self.src["source_key"]) == self.src["source_key"] else m
            if rec is None:
                raise SourceConflict(f"{pk}: revision member missing: {m['path']}")
            got.add((m["path"], m["role"], rec["sha256"]))
        if got != want:
            raise SourceConflict(f"{self.src['source_key']}: model members of {v['key']} differ from {rev}; this is a new fit, "
                                 "not an evaluation-only revision -- register a new training snapshot")
        v["view_kind"], v["alias_of"], v["n_inputs"] = "evaluation_revision", pk, n_inputs
        v["alias_text"] = f"the unchanged model version of snapshot {rev}"
        self.revision_members |= {m[0] for m in want}
        return prior["versions"][pk]

    def member(self, rel: str, role: str, kind: str = "fitted", **kw) -> dict:
        return {"path": rel, "role": role, "kind": kind, "bundle_source": self.src["source_key"], **kw}


# ------------------------------------------------------------------ helpers shared by modern formats

TRUTH_MODERN = ("Reported overall IPC phase (five classes; crisis = phase 3 or worse) and the population share in phase "
                "3 or worse after normalizing the five shares to sum 1 (phase3_worse).")


def modern_keys(df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame({"area_id": df["area_id"].astype(np.int64),
                        "target_ord": (df["year"].astype(np.int64) * 12 + df["month"].astype(np.int64) - 1)})
    out["overall_phase"] = df["overall_phase"].astype(np.int64)
    out["phase3_worse"] = df["phase3_worse"].astype(float)
    return out


def check_batch(b: Builder, run_dir: str, year: int) -> list:
    """Members of one annual modern batch; batch_record artifacts must match the files."""
    bd = f"{run_dir}/batches/{year}"
    rec_rel = f"{bd}/batch_record.json"
    b.need(rec_rel)
    rec = json.loads(b.path(rec_rel).read_text())
    out = [b.member(rec_rel, "batch_record", job=str(year))]
    for name, digest in rec["artifacts"].items():
        rel = f"{bd}/{name}"
        if b.need(rel)["sha256"] != digest:
            raise SourceConflict(f"{rel}: batch_record digest differs from the file")
        role = "booster" if name.endswith(".ubj") else ("fit_keys" if name.startswith("fit_keys") else "batch_predictions")
        out.append(b.member(rel, role, job=str(year), target=name.replace("model_", "").replace(".ubj", "") if role == "booster" else None))
    if sum(1 for m in out if m["role"] == "booster") != 4:
        raise SourceConflict(f"{bd}: expected 4 phase boosters")
    return out


def region_map(b: Builder) -> pd.DataFrame:
    ref = b.src["region_map"]
    rec = b.deps["external"][ref]
    df = read_csv(b.repo / ref)
    if sha_file(b.repo / ref) != rec["sha256"]:
        raise SourceConflict(f"{ref}: region map changed since planning")
    return df[["area_id", "region"]].astype(np.int64)


def put_modern_row(b: Builder, v: dict, role: str, coh: str, row: pd.Series, file: str, idx, dataset: str | None,
                   metrics=("exact_phase_accuracy", "phase3plus_accuracy", "precision_phase3plus", "sensitivity_phase3plus",
                            "f2_phase3plus", "r2_phase3plus", "mae_phase3plus", "ordinal_mae")) -> None:
    for m in metrics:
        if m not in row.index:
            continue
        reason = text(row.get(f"{m}_reason"))
        status = text(row.get(f"{m}_status"))
        b.put(v, N.metric_key(role, N.cohort(coh), N.leaf(m)), row[m], file, idx, m, m, dataset, reason, status)
    for c in ("n_samples", "n_rows", "n_areas", "n_countries"):
        if c in row.index:
            b.put(v, N.metric_key(role, N.cohort(coh), N.leaf(c)), row[c], file, idx, c, c, dataset)


def modern_period(raw: str, extension: bool) -> str:
    raw = str(raw)
    if raw == "pooled":
        return "primary"
    if raw == "pooled_2022_2026":
        return "primary"
    if raw == "pooled_2022_2025":
        return "original" if extension else "primary"
    if raw.isdigit():
        return f"year_{raw}"
    raise SourceConflict(f"no period mapping for {raw!r}")


# ------------------------------------------------------------------ format: modern annual runs

def extract_modern_runs(b: Builder) -> None:
    src = b.src
    fam = src["families"][0]
    extension = src["snapshot_role"] == "extension"
    group = src["eval_group"]
    runs = sorted({p.split("/runs/")[1].split("/")[0] + "/" + p.split("/runs/")[1].split("/")[1]
                   for p in b.inv if p.startswith(b.root + "/runs/") and p.endswith("/run_metadata.json")})
    truth_by_lead: dict = {}
    for run in runs:
        arm_raw, hm = run.split("/")
        h = int(hm[:-1])
        rd = f"{b.root}/runs/{run}"
        meta = json.loads(b.path(f"{rd}/run_metadata.json").read_text())
        n_inputs = int(meta["feature_count"])
        v = b.view(fam, arm_raw, h, "fitted", n_inputs=n_inputs)
        # predictions -> evaluation datasets (keys + truth), equal across arms at a lead
        if extension:
            pf = f"{rd}/predictions/predictions_2022_2026.csv"
            pred = read_csv(b.path(b.need(pf) and pf))
        else:
            parts = []
            for p in sorted(x for x in b.inv if x.startswith(f"{rd}/predictions/predictions_") and x.endswith(".csv")):
                parts.append(read_csv(b.path(p)))
            pred = pd.concat(parts, ignore_index=True)
        kt = modern_keys(pred)
        prev = truth_by_lead.get(h)
        if prev is not None and not prev.sort_values(["area_id", "target_ord"]).reset_index(drop=True).equals(
                kt.sort_values(["area_id", "target_ord"]).reset_index(drop=True)):
            raise SourceConflict(f"{src['source_key']} H{h}: evaluation keys/truth differ between arms")
        truth_by_lead[h] = kt
        ds = {}
        years = sorted(set(int(x) for x in pred["year"]))
        for y in years:
            ds[f"year_{y}"] = b.eval_dataset(h, f"year_{y}", "all_scored", group, kt[kt.target_ord // 12 == y],
                                             ["overall_phase", "phase3_worse"], TRUTH_MODERN)
        if extension:
            ds["primary"] = b.eval_dataset(h, "primary", "all_scored", group, kt, ["overall_phase", "phase3_worse"], TRUTH_MODERN)
            ds["original"] = b.eval_dataset(h, "original", "all_scored", group, kt[kt.target_ord // 12 <= 2025],
                                            ["overall_phase", "phase3_worse"], TRUTH_MODERN)
        else:
            ds["primary"] = b.eval_dataset(h, "primary", "all_scored", group, kt, ["overall_phase", "phase3_worse"], TRUTH_MODERN)
        v["_ds"] = ds
        v["_pred"] = (pred, kt)
        # members
        members = [b.member(f"{rd}/run_metadata.json", "run_metadata_feature_order")]
        own_years = [int(x) for x in meta.get("fitted_here_years", years)] if extension else years
        for y in own_years:
            members += check_batch(b, rd, y)
        if extension:
            orig = b.deps["plans"][src["extends"]]
            okey = f"{v['key']}@{src['extends']}"
            if okey not in orig["versions"]:
                raise SourceConflict(f"{src['source_key']}: original version {okey} missing")
            sby = meta["sources_by_year"]
            reused = [int(y) for y in meta["reused_years"]]
            for m in orig["versions"][okey]["members"]:
                if m["role"] == "run_metadata_feature_order":
                    continue
                y = int(m.get("job") or 0)
                if y not in reused:
                    raise SourceConflict(f"{okey}: member year {y} not declared reused")
                if m["role"] == "booster":
                    want = sby[str(y)].get("artifacts", {}).get(Path(m["path"]).name)
                    if want is not None and want != m["sha256"]:
                        raise SourceConflict(f"{m['path']}: extension sources_by_year digest differs from original")
                members.append({**m, "kind": "reused_from_snapshot", "bundle_source": src["extends"]})
            v["fit_note"] = (f"2022-2025 annual fits reused unchanged from snapshot {src['extends']}; the 2026 fit is new "
                             f"(fit origin {meta['new_batch']['fit_origin_month']}, label cutoff "
                             f"{meta['new_batch']['fit_label_cutoff_month']}).")
        payload = meta.get("fingerprint_payload", {})
        if extension:
            payload = payload.get("parent_fingerprint_payload", payload)
        tds = b.training_dataset(fam, h, n_inputs, {
            "label_setting": "observed", "prepared_pool_sha256": payload.get("dataset_sha256"),
            "manifest_sha256": payload.get("manifest_sha256"), "feature_order_sha256": sha_bytes("\n".join(meta["features"]).encode()),
            "fit_valid_keys_sha256": meta.get("fingerprint_payload", {}).get("fit_valid_keys_sha256"),
            "pool_rule": meta.get("split_rule") or "annual origin-safe blocks; labels <= Jan(Y) - max(H, 1)",
            "per_fit_keys": "fit_keys members of each model version (members.json)"})
        b.version(v, members, tds, n_inputs, fit_units=len(own_years))
        v["datasets"].add(tds)
    # metrics
    if src["metrics_format"] == "metrics_overall":
        for run in runs:
            arm_raw, hm = run.split("/")
            h = int(hm[:-1])
            v = b.views[f"{fam}/{N.arm(arm_raw)[0]}/{N.lead_tag(h)}"]
            f = f"{b.root}/runs/{run}/metrics/metrics_overall.csv"
            d = read_csv(b.path(b.need(f) and f))
            for i, r in d.iterrows():
                role = modern_period(r["test_year"], extension)
                put_modern_row(b, v, role, "all_scored", r, f, int(i), v["_ds"][role])
                b.slot(v, role, "all_scored", "complete")
    else:
        extract_compact_long(b, fam, extension)
    if src.get("region3"):
        extract_region3(b, fam)
    for alias in src.get("h0_aliases", []):
        base = b.views[f"{fam}/{N.arm(alias['of'])[0]}/00"]
        a = b.view(fam, alias["arm"], 0, "alias", alias_of=base["version_key"] or base["alias_of"], alias_text=f"{base['arm']} 0-month",
                   n_inputs=base["n_inputs"],
                   compare_with=f"{base['arm']} 0-month gives identical predictions (shared fit); compare this arm with the baseline only at 3/6/12-month.")
        a["datasets"] |= {d for d in base["datasets"]}
        a["_ds"] = base["_ds"]
        for k, val in base["metrics"].items():
            b.put(a, k, val, base["sources"][k]["file"], base["sources"][k]["row"], base["sources"][k]["column"],
                  base["sources"][k]["original"] + " (shared 0-month fit)", base["metric_dataset"].get(k))
        for k, na in base["na"].items():
            a["na"].setdefault(k, {**na, "original": na["original"] + " (shared 0-month fit)"})
        a["slots"] = {**base["slots"], **a["slots"]}
    for v in b.views.values():
        v.pop("_pred", None)


def extract_compact_long(b: Builder, fam: str, extension: bool) -> None:
    src = b.src
    group = src["eval_group"]
    regions = region_map(b) if src.get("region_map") else None
    f = b.rel(src["metrics_long"])
    d = read_csv(b.path(b.need(f) and f))
    alias_arm = {a["arm"] for a in src.get("h0_aliases", [])}
    for i, r in d.iterrows():
        h = int(r["horizon"])
        v = b.views.get(f"{fam}/{N.arm(r['arm'])[0]}/{N.lead_tag(h)}")
        if v is None:
            raise SourceConflict(f"{f}:{i}: metric row for a run without models: {r['run_id']}")
        role = modern_period(r["period"], extension)
        if str(r["scope"]) == "region":
            coh = N.region_cohort(int(float(r["region"])))
            if N.REGIONS[int(float(r["region"]))] != str(r["region_name"]):
                raise SourceConflict(f"{f}:{i}: region {r['region']} named {r['region_name']}, vocabulary {N.REGIONS[int(float(r['region']))]}")
            ds = regional_dataset(b, v, role, coh, int(float(r["region"])), regions)
        else:
            coh = "all_scored"
            ds = v["_ds"][role]
        m = str(r["metric"])
        b.put(v, N.metric_key(role, coh, N.leaf(m)), r["value"], f, int(i), "value", m, ds, text(r["reason"]), text(r["status"]))
        for c in ("n_rows", "n_areas", "observed_3plus", "observed_1_2", "predicted_3plus", "true_positive_3plus", "distinct_phase3_worse"):
            if c in r.index:
                b.put(v, N.metric_key(role, coh, N.leaf(c)), r[c], f, int(i), c, c, ds)
        b.slot(v, role, coh, "complete" if str(r["status"]) == "ok" else "complete_with_undefined_metrics")
    for fd in src.get("deltas", []):
        f = b.rel(fd)
        d = read_csv(b.path(b.need(f) and f))
        for i, r in d.iterrows():
            h = int(r["horizon"])
            shared = str(r["contrast"]).startswith("shared H0")
            if shared:
                arm_raw = next(iter(alias_arm))
            elif str(r["contrast"]) == "compact_weather_oracle - compact_baseline":
                arm_raw = "compact_weather_oracle"
            else:
                raise SourceConflict(f"{f}:{i}: no contrast vocabulary for {r['contrast']!r}")
            key = f"{fam}/{N.arm(arm_raw)[0]}/{N.lead_tag(h)}"
            v = b.views.get(key) or b.view(fam, arm_raw, h, "alias")
            role = modern_period(r["period"], extension)
            if str(r["scope"]) == "region":
                coh = N.region_cohort(int(float(r["region"])))
                base = b.views[f"{fam}/baseline/{N.lead_tag(h)}"]
                ds = regional_dataset(b, base, role, coh, int(float(r["region"])), regions)
            else:
                coh = "all_scored"
                ds = b.views[f"{fam}/baseline/{N.lead_tag(h)}"]["_ds"][role]
            k = N.metric_key(role, coh, f"delta.{N.arm(arm_raw)[0]}_minus_baseline.{N.delta_metric(str(r['metric']))}")
            b.put(v, k, r["delta"], f, int(i), "delta", f"{r['contrast']}:{r['metric']}", ds, text(r["reason"]), text(r["status"]))


def regional_dataset(b: Builder, v: dict, role: str, coh: str, region: int, regions: pd.DataFrame) -> str:
    cache = v.setdefault("_regional", {})
    if (role, coh) in cache:
        return cache[(role, coh)]
    pred, kt = v.get("_pred") or b.views[f"{v['family']}/baseline/{N.lead_tag(v['lead'])}"]["_pred"]
    kt = kt.merge(regions, on="area_id", how="left")
    if kt["region"].isna().any():
        raise SourceConflict(f"{b.src['source_key']}: areas without region membership")
    sel = kt[kt.region == region]
    if role.startswith("year_"):
        sel = sel[sel.target_ord // 12 == int(role[5:])]
    elif role == "original":
        sel = sel[sel.target_ord // 12 <= 2025]
    name = b.eval_dataset(v["lead"], role, coh, b.src["eval_group"], sel[["area_id", "target_ord", "overall_phase", "phase3_worse"]],
                          ["overall_phase", "phase3_worse"], TRUTH_MODERN)
    cache[(role, coh)] = name
    return name


def extract_region3(b: Builder, fam: str) -> None:
    """Weather-oracle region3 (Southern Africa) scores of the global models, incl. the reused reference arm."""
    cfg = b.src["region3"]
    coh = N.region_cohort(3)
    pf = b.rel(cfg["predictions"])
    pred = read_csv(b.path(b.need(pf) and pf))
    if set(pred["region"].unique()) != {3}:
        raise SourceConflict(f"{pf}: rows outside region 3")
    ref_src = cfg["reference_source"]
    ref_plan = b.deps["plans"][ref_src]
    for h in sorted(set(int(x) for x in pred["run_horizon"])):
        rv_ver = f"origin_safe_climate_global/safe_ipc_history_idp/{N.lead_tag(h)}@{ref_src}"
        if rv_ver not in ref_plan["versions"]:
            raise SourceConflict(f"reference version {rv_ver} missing")
        ref_arm = "reference:climate_safe_history_idp"
        rv = b.view(fam, ref_arm, h, "reference", alias_of=rv_ver,
                    alias_text="the Origin-safe climate global historical safe_ipc_history_idp fit (same snapshot "
                               f"{ref_src})", compare_with="weather_oracle and weather_oracle_with_summaries at the same lead on the same dataset.")
    # global comparison rows for the reference arm (cross-checked equal for oracle arms)
    gf = b.rel(cfg["global_comparison"])
    g = read_csv(b.path(b.need(gf) and gf))
    ref_runs = {r["view_key"]: r for r in ref_plan["views"]}
    for i, r in g.iterrows():
        h = int(r["horizon"])
        if r["arm"] == "climate_safe_history_idp":
            v = b.views[f"{fam}/reference_safe_ipc_history_idp/{N.lead_tag(h)}"]
            ref_view = ref_runs[f"origin_safe_climate_global/safe_ipc_history_idp/{N.lead_tag(h)}"]
            role = modern_period(r["test_year"], False)
            ds = ref_view["metric_dataset"].get(N.metric_key(role, "all_scored", "five_class.accuracy"))
            v["_ds"] = v.get("_ds", {})
            put_modern_row(b, v, role, "all_scored", r, gf, int(i), ds)
            b.slot(v, role, "all_scored", "complete")
        # oracle-arm rows of this verification file are an independent replay of runs/*/metrics_overall.csv
        # (last-bit float differences); the run metrics are the imported record, so these rows are not re-logged.
    mf = b.rel(cfg["metrics"])
    m = read_csv(b.path(b.need(mf) and mf))
    r3_ds = {}
    for i, r in m.iterrows():
        h = int(r["horizon"])
        arm_raw = "reference:climate_safe_history_idp" if r["arm"] == "climate_safe_history_idp" else r["arm"]
        v = b.views[f"{fam}/{N.arm(arm_raw)[0]}/{N.lead_tag(h)}"]
        role = modern_period(r["period"], False)
        sel = pred[(pred.run_arm == r["arm"]) & (pred.run_horizon == h)]
        if role.startswith("year_"):
            sel = sel[sel.year == int(role[5:])]
        ds = b.eval_dataset(h, role, coh, b.src["eval_group"], modern_keys(sel), ["overall_phase", "phase3_worse"], TRUTH_MODERN)
        r3_ds[(r["arm"], h, role)] = ds
        if len(sel) != int(r["n_rows"]):
            raise SourceConflict(f"{mf}:{i}: n_rows {r['n_rows']} != {len(sel)} prediction keys")
        put_modern_row(b, v, role, coh, r, mf, int(i), ds)
        b.slot(v, role, coh, "complete")
    cf = b.rel(cfg["intervals"])
    c = read_csv(b.path(b.need(cf) and cf))
    contrast = {"raw_oracle - reference": ("climate_safe_history_idp_oracle", "reference_safe_ipc_history_idp"),
                "raw_oracle_b6 - raw_oracle (whole B6 package increment)": ("climate_safe_history_idp_oracle_b6", "weather_oracle"),
                "raw_oracle_b6 - reference": ("climate_safe_history_idp_oracle_b6", "reference_safe_ipc_history_idp")}
    for i, r in c.iterrows():
        if r["contrast"] not in contrast:
            raise SourceConflict(f"{cf}:{i}: no contrast vocabulary for {r['contrast']!r}")
        a_raw, bname = contrast[r["contrast"]]
        h = int(r["horizon"])
        v = b.views[f"{fam}/{N.arm(a_raw)[0]}/{N.lead_tag(h)}"]
        role = modern_period(r["period"], False)
        base = f"delta.{v['arm']}_minus_{bname}.{N.delta_metric(str(r['metric']))}"
        ds = r3_ds.get((a_raw, h, role))
        if ds is None or ds != r3_ds.get(("climate_safe_history_idp", h, role)):
            raise SourceConflict(f"{cf}:{i}: paired contrast without one shared region-3 dataset")
        for col in ("point_delta", "ci_lower", "ci_upper", "draws_total", "draws_valid", "draws_invalid", "invalid_fraction", "min_valid_draws"):
            k = N.metric_key(role, coh, base + N.DELTA_COLUMNS[col])
            b.put(v, k, r[col], cf, int(i), col, f"{r['contrast']}:{r['metric']}:{col}", ds,
                  text(r.get("ci_reason")) if col.startswith("ci") else None, text(r.get("ci_status")) if col.startswith("ci") else None)


# ------------------------------------------------------------------ format: launch

LAUNCH_INPUTS = {"compact_baseline": "baseline inputs", "compact_cds_weather": "CDS weather inputs"}


def extract_launch(b: Builder) -> None:
    src = b.src
    fam = src["families"][0]
    scope_label = src["inference_scope_label"]
    runs = sorted({p.split("/runs/")[1].rsplit("/", 1)[0] for p in b.inv if p.startswith(b.root + "/runs/") and p.endswith("/artifact_record.json")})
    for run in runs:
        arm_raw, hm = run.split("/")
        h = int(hm[:-1])
        rd = f"{b.root}/runs/{run}"
        meta = json.loads(b.path(f"{rd}/run_metadata.json").read_text())
        rec = json.loads(b.path(f"{rd}/artifact_record.json").read_text())
        members = [b.member(f"{rd}/artifact_record.json", "artifact_record")]
        roles = {"feature_schema.json": "feature_schema", "fit_keys.csv.gz": "fit_keys", "fit_targets.csv.gz": "fit_targets",
                 "fit_weights.csv.gz": "fit_weights", "inference_features.csv.gz": "inference_features",
                 "predictions_raw.csv": "launch_predictions", "run_metadata.json": "run_metadata_feature_order"}
        for name, digest in rec["artifacts"].items():
            rel = f"{rd}/{name}"
            if b.need(rel)["sha256"] != digest:
                raise SourceConflict(f"{rel}: artifact_record digest differs from the file")
            role = "booster" if name.endswith(".ubj") else roles[name]
            members.append(b.member(rel, role, job="2026-04", target=name[6:-4] if role == "booster" else None))
        if sum(1 for m in members if m["role"] == "booster") != 4:
            raise SourceConflict(f"{rd}: expected 4 boosters")
        n_inputs = int(meta["feature_count"])
        v = b.view(fam, arm_raw, h, "fitted", n_inputs=n_inputs)
        pred = read_csv(b.path(f"{rd}/predictions_raw.csv"))
        target = str(pred["target_month"].iloc[0])
        keys = "\n".join(str(x) for x in sorted(pred["area_id"].astype(np.int64)))
        inf = b.inference_dataset(scope_label, LAUNCH_INPUTS[arm_raw], "2026-04", target, {
            "n_areas": int(len(pred)), "area_keys_sha256": sha_bytes(keys.encode()),
            "inference_features_sha256": b.inv[f"{rd}/inference_features.csv.gz"]["sha256"],
            "population": "fixed April 2026 population (legacy country cap); no actual labels"})
        payload = meta.get("fingerprint_payload", {})
        tds = b.training_dataset(fam, h, n_inputs, {
            "label_setting": "observed", "prepared_pool_sha256": payload.get("training_dataset_sha256"),
            "fit_selection_sha256": payload.get("fit_selection_sha256"),
            "feature_order_sha256": sha_bytes("\n".join(meta["features"]).encode()),
            "pool_rule": "labels strictly before 2026-04, April-anchored decay weights",
            "weather_inputs": "realized anomalies in training" + ("; CDS forecasts at inference" if arm_raw == "compact_cds_weather" else ""),
            "per_fit_keys": "fit_keys/fit_targets/fit_weights members (members.json)"})
        b.version(v, members, tds, n_inputs, fit_units=1)
        v["datasets"] |= {inf, tds}
        v["_inf"] = inf
        v["target"] = target
    for alias in src.get("h0_aliases", []):
        base = b.views[f"{fam}/{N.arm(alias['of'])[0]}/00"]
        a = b.view(fam, alias["arm"], 0, "alias", alias_of=base["version_key"] or base["alias_of"], alias_text=f"{base['arm']} 0-month",
                   n_inputs=base["n_inputs"], target=base["target"],
                   compare_with="baseline 0-month gives identical predictions (shared fit; zero paired difference).")
        a["_inf"] = base["_inf"]
        a["datasets"] |= set(base["datasets"])
    for fs in src["summaries"]:
        f = b.rel(fs["file"])
        d = read_csv(b.path(b.need(f) and f))
        for i, r in d.iterrows():
            h = int(r["horizon"])
            if fs["kind"] == "summary":
                arm_raw = r["display_arm"]
                if r["source_run_id"] != f"{arm_raw}/{h}m":
                    if not (h == 0 and str(r["source_run_id"]) == "compact_baseline/0m"):
                        raise SourceConflict(f"{f}:{i}: source run {r['source_run_id']} for {arm_raw} H{h}")
            else:
                if r["contrast"] != "compact_cds_weather - compact_baseline":
                    raise SourceConflict(f"{f}:{i}: no contrast vocabulary for {r['contrast']!r}")
                arm_raw = "compact_cds_weather"
            v = b.views[f"{fam}/{N.arm(arm_raw)[0]}/{N.lead_tag(h)}"]
            if str(r["target_month"]) != v["target"]:
                raise SourceConflict(f"{f}:{i}: target month differs from the run")
            coh = launch_cohort(fs["unit"], r)
            for c in d.columns:
                if c.startswith(("count_", "share_", "delta_count", "delta_share")) or c in N.LAUNCH_EXTRA:
                    if c.endswith(("_status", "_reason")):
                        continue
                    if pd.api.types.is_numeric_dtype(d[c]) or c in N.LAUNCH_EXTRA:
                        reason = text(r.get("share_raw_reason" if "share_raw" in c else "share_effective_reason" if "share_eff" in c else None))
                        b.put(v, N.metric_key("prediction_summary", coh, N.launch_leaf(c)), r[c], f, int(i), c, c, v["_inf"], reason)
            b.slot(v, "prediction_summary", coh, "prediction_summary_only")


def launch_cohort(unit: str, r) -> str:
    if unit in ("global", "som"):
        return N.launch_cohort("all")
    if unit == "region":
        return N.launch_cohort("region", region=int(r["region"]), region_name=str(r["region_name"]))
    if unit == "country":
        return N.launch_cohort("country", country=str(r["country"]))
    raise SourceConflict(f"no launch unit {unit!r}")


# ------------------------------------------------------------------ Somalia shared

CRISIS_TRUTH = "crisis indicator = reported overall phase >= 3 (somalia_oracle/data.py:172-175), not a threshold on actual q3"
SOMALIA_TRUTH = {
    "v1": f"Reported overall phase (five classes), {CRISIS_TRUTH}, and actual q3 share, from the v1 row provenance of the frozen cohort.",
    "v2": f"Actual q3 share and reported overall phase from the v2 label ledger; {CRISIS_TRUTH}.",
    "v3": f"Raw reported q3 share and overall phase of the original outer keys (v3 label ledger); {CRISIS_TRUTH}.",
    "v4": (f"Reported q3/phase from the v4 label ledger for original and copied keys (copies keep their own saved "
           f"truth); {CRISIS_TRUTH}; copies also identified by source family and original month."),
}


PERSISTENCE_RULE = ("somalia_oracle/data.py:365-386 persistence_lookup: a valid reported phase (label ledger, valid_phase "
                    "<=> actual_crisis defined) of the same area at some month U <= min(O, T-1), O = T - H")


def persistence_rule(ledger: pd.DataFrame, keys: pd.DataFrame) -> pd.DataFrame:
    """Reconstruct persistence availability from saved ledgers with the source rule (no scoring).

    keys carries area_id, target_ord and the saved origin_ord (row provenance). valid_phase is recovered as
    actual_crisis defined (data.py:172-175 sets actual_crisis NaN exactly when valid_phase is False)."""
    valid = ledger[ledger["actual_crisis"].notna()][["area_id", "target_ord"]].astype(np.int64)
    first = valid.groupby("area_id").target_ord.min()
    k = keys[["area_id", "target_ord", "origin_ord"]].astype(np.int64)
    cutoff = np.minimum(k.origin_ord, k.target_ord - 1)
    has = k.area_id.map(first).le(cutoff).fillna(False).to_numpy()
    return k[has][["area_id", "target_ord"]]


def somalia_slot_months(cohort: pd.DataFrame) -> list:
    return [ym(o) for o in sorted(set(int(x) for x in cohort["target_ord"]))]


def v1_hash(keys: pd.DataFrame) -> str:
    """somalia_oracle/evaluation.py:94-96 cohort_hash (sorted CSV text)."""
    t = keys[["area_id", "target_ord"]].sort_values(["area_id", "target_ord"]).to_csv(index=False, lineterminator="\n")
    return sha_bytes(t.encode())


def v4_hash(keys: pd.DataFrame) -> str:
    """somalia_oracle/augexp.py:1169-1171 cohort_digest (int64 bytes, mergesort)."""
    k = keys[["area_id", "target_ord"]].astype(np.int64).sort_values(["area_id", "target_ord"], kind="mergesort").to_numpy()
    return sha_bytes(np.ascontiguousarray(k).tobytes())


def somalia_members(b: Builder, inv: pd.DataFrame, shared: list, booster_kind="fitted", alias_note=None) -> list:
    out = [b.member(b.rel(p), role) for p, role in shared]
    for r in inv.itertuples(index=False):
        out.append(b.member(b.rel(f"models/{r.path}"), "booster", booster_kind, job=r.job_id, target=r.target,
                            sha256=r.sha256, **({"alias_note": alias_note} if alias_note else {})))
    return out


def somalia_training(b: Builder, fam: str, h: int, schema_key: str, label_setting: str, schemas: dict) -> tuple:
    cols = schemas[schema_key]
    fm = b.rel(f"features/feature_matrix_h{h:02d}.csv.gz")
    pool = b.inv.get(fm, {}).get("sha256")
    desc = {"label_setting": label_setting, "prepared_pool_sha256": pool, "prepared_pool_file": fm if pool else None,
            "label_ledger_sha256": b.need(b.rel("ledgers/label_ledger.csv.gz"))["sha256"],
            "feature_order_sha256": sha_bytes("\n".join(cols).encode()), "feature_schema_key": schema_key,
            "per_fit_keys": "fits/final_fit_ledger.csv.gz rows of each job (members.json)"}
    if pool is None:
        desc["pool_note"] = "this snapshot saved no prepared feature matrix; identity is its feature schema and label ledger"
    return b.training_dataset(fam, h, len(cols), desc), len(cols)


# ------------------------------------------------------------------ format: Somalia v1

def extract_somalia_v1(b: Builder) -> None:
    fam = b.src["families"][0]
    group = b.src["eval_group"]
    schemas = json.loads(b.path(b.rel("features/feature_schema.json")).read_text())
    inv = read_csv(b.path(b.rel("models/model_inventory.csv")))
    inv["h"] = inv.job_id.str.extract(r"_h(\d\d)_")[0].astype(int)
    dup = inv.duplicated(["job_id", "arm", "target"], keep="first")
    alias_rows, inv = inv[dup], inv[~dup]
    if not ((alias_rows.arm == "B") & (alias_rows.h == 0)).all():
        raise SourceConflict("v1 inventory repeats rows other than the H0 B rows reused for C")
    jobs = read_csv(b.path(b.rel("ledgers/jobs.csv")))
    shared = [("models/model_inventory.csv", "model_inventory"), ("features/feature_schema.json", "feature_schema"),
              ("fits/final_fit_ledger.csv.gz", "fit_keys"), ("fits/arm_job_status.csv", "fit_status"),
              ("fits/candidate_scores.csv", "selection"), ("fits/inner_folds.csv", "selection"),
              ("ledgers/jobs.csv", "jobs")]
    for (arm_raw, h), g in inv.groupby(["arm", "h"]):
        njobs = int((jobs.horizon == h).sum())
        if g.job_id.nunique() != njobs or len(g) != 4 * njobs:
            raise SourceConflict(f"v1 {arm_raw} H{h}: {g.job_id.nunique()} jobs / {len(g)} boosters, expected {njobs} / {4 * njobs}")
        v = b.view(fam, arm_raw, h, "fitted")
        tds, n_in = somalia_training(b, fam, h, f"h{h:02d}_{arm_raw}", "observed", schemas)
        b.version(v, somalia_members(b, g, shared), tds, n_in, fit_units=njobs)
        v["datasets"].add(tds)
    for h in (0,):
        base = b.views[f"{fam}/seasonal_climate/00"]
        b.view(fam, "C", 0, "alias", alias_of=base["version_key"], alias_text="seasonal_climate 0-month (H0 C clones B)",
               n_inputs=base["n_inputs"], compare_with="seasonal_climate 0-month gives identical predictions; compare C with B at 3/6/12-month.")
    # cohorts + truth
    coh_l = read_csv(b.path(b.rel("ledgers/cohort_ledger.csv.gz")))
    prov = {h: read_csv(b.path(b.rel(f"ledgers/row_provenance_h{h:02d}.csv.gz"))) for h in (0, 3, 6, 12)}
    m = read_csv(b.path(b.rel("metrics/metrics.csv")))
    ds_cache = {}

    def ds_for(y, h, coh, n, src_hash):
        k = (y, h, coh)
        if k in ds_cache:
            return ds_cache[k]
        c = coh_l[(coh_l.test_year == y) & (coh_l.horizon == h)]
        status = ["primary"] if coh in ("primary", "persistence_subset") else ["primary", "wider_only"]
        keys = c[c.status.isin(status)][["area_id", "target_ord"]]
        p = prov[h][["area_id", "target_ord", "overall_phase", "actual_crisis", "q3", "persistence_available"]]
        kt = keys.merge(p, on=["area_id", "target_ord"], how="left")
        if kt["overall_phase"].isna().any():
            raise SourceConflict(f"v1 {y} H{h} {coh}: keys without truth")
        if coh == "persistence_subset":
            kt = kt[kt.persistence_available.fillna(False).astype(bool)]
        if len(kt) != n:
            raise SourceConflict(f"v1 {y} H{h} {coh}: {len(kt)} keys vs reported n_rows {n}")
        if src_hash and v1_hash(kt) != src_hash:
            raise SourceConflict(f"v1 {y} H{h} {coh}: reconstructed keys do not match the source cohort_sha256")
        name = b.eval_dataset(h, f"year_{y}", coh, group, kt.assign(actual_crisis=kt.actual_crisis.astype(int), overall_phase=kt.overall_phase.astype(int)),
                              ["overall_phase", "actual_crisis", "q3"], SOMALIA_TRUTH["v1"],
                              source_hash={"algorithm": "somalia_oracle/evaluation.py cohort_hash", "sha256": src_hash} if src_hash else None)
        ds_cache[k] = name
        return name

    f = b.rel("metrics/metrics.csv")
    leaves = ["tp", "fp", "fn", "tn", "precision", "recall", "f1", "f2", "prevalence", "accuracy", "r2_q3",
              "predicted_prevalence", "mean_q3_pred", "n_rows", "n_areas", *[f"n_actual_phase{k}" for k in range(1, 6)],
              *[f"n_pred_phase{k}" for k in range(1, 6)]]
    for i, r in m.iterrows():
        y, h, coh = int(r["test_year"]), int(r["horizon"]), str(r["cohort"])
        role = f"year_{y}"
        spec = str(r["specification"])
        if spec == "all":
            targets = [v for v in b.views.values() if v["lead"] == h]
            for v in targets:
                b.slot(v, role, N.cohort(coh), "empty_cohort" if r["status"] == "unavailable" else "complete", text(r["reason"]))
                if r["status"] == "unavailable":
                    b.put(v, N.metric_key(role, N.cohort(coh), "n_rows"), r["n_rows"], f, int(i), "n_rows",
                          "all:n_rows", None, text(r["reason"]), "empty_cohort")
            continue
        arm_raw = {"persistence": "persistence"}.get(spec, spec)
        kind = "fitted" if spec in ("A", "B", "C", "D") else "metric_only"
        if spec == "C" and h == 0:
            kind = "alias"
        v = b.view(fam, arm_raw, h, kind)
        ds = ds_for(y, h, coh, int(r["n_rows"]), text(r["cohort_sha256"])) if r["status"] == "ok" else None
        for c in leaves:
            if c not in r.index:
                continue
            b.put(v, N.metric_key(role, N.cohort(coh), N.leaf(c)), r[c], f, int(i), c, f"{spec}:{c}", ds,
                  text(r.get(f"{c}_reason")) or text(r["reason"]), text(r["status"]))
        b.slot(v, role, N.cohort(coh), "complete" if r["status"] == "ok" else "empty_cohort", text(r["reason"]))
    contrast_files(b, fam, "metrics/contrasts.csv", v1_contrast, ds_cache, diag=False)
    # diagnostics (primary cohort; LEAKY_* tunes on the evaluation cohort -> diagnostic_leaky)
    f = b.rel("diagnostics/discrimination_auc.csv")
    for i, r in read_csv(b.path(f)).iterrows():
        v = b.view(fam, r["arm"], int(r["horizon"]), "alias" if (r["arm"] == "C" and int(r["horizon"]) == 0) else "fitted")
        for c in ("auc_crisis", "within_month_auc"):
            b.put(v, N.metric_key(f"year_{int(r['test_year'])}", "primary", "diagnostic." + N.leaf(c)), r[c], f, int(i), c, c,
                  ds_cache.get((int(r["test_year"]), int(r["horizon"]), "primary")))
    f = b.rel("diagnostics/calibration_threshold_metrics.csv")
    for i, r in read_csv(b.path(f)).iterrows():
        arm_raw = "always_crisis" if r["arm"] == "-" else r["arm"]
        h = int(r["horizon"])
        v = b.view(fam, arm_raw, h, "metric_only" if arm_raw == "always_crisis" else ("alias" if (arm_raw == "C" and h == 0) else "fitted"))
        meth = str(r["method"])
        ns = ("diagnostic_leaky.threshold." + meth[6:]) if meth.startswith("LEAKY_") else ("diagnostic.threshold." + meth.replace(".", "_"))
        for c in ("n", "f2", "precision", "recall", "f1", "accuracy", "macro_f1", "p4plus_recall", "pred_p3_share", "r2_q3"):
            b.put(v, N.metric_key(f"year_{int(r['test_year'])}", "primary", f"{ns}.{N.leaf(c)}"), r[c], f, int(i), c, f"{meth}:{c}",
                  ds_cache.get((int(r["test_year"]), h, "primary")))
    f = b.rel("diagnostics/calibrated_d_vs_benchmarks.csv")
    for i, r in read_csv(b.path(f)).iterrows():
        h = int(r["horizon"])
        v = b.views[f"{fam}/weather_oracle_with_share_history/{N.lead_tag(h)}"]
        coh = N.cohort(str(r["cohort"]))
        for c in ("n", "n_areas", "f2", "precision", "recall", "f1", "accuracy", "macro_f1", "p4plus_recall", "pred_p3_share", "r2_q3", "r2_n"):
            b.put(v, N.metric_key(f"year_{int(r['test_year'])}", coh, f"diagnostic.benchmark.{r['benchmark']}.{N.leaf(c)}"),
                  r[c], f, int(i), c, f"{r['benchmark']}:{c}", ds_cache.get((int(r["test_year"]), h, str(r["cohort"]))))
    f = b.rel("diagnostics/calibrated_d_vs_benchmarks_contrasts.csv")
    for i, r in read_csv(b.path(f)).iterrows():
        h = int(r["horizon"])
        v = b.views[f"{fam}/weather_oracle_with_share_history/{N.lead_tag(h)}"]
        coh = N.cohort(str(r["cohort"]))
        a, bb = str(r["contrast"]).split("-", 1)
        base = f"diagnostic.delta.{a}_minus_{bb}.binary.f2"
        for c, suf in (("point_delta_f2", ""), ("ci_low", ".ci_low"), ("ci_high", ".ci_high"), ("valid_draws", ".draws_valid"), ("undefined_draws", ".draws_undefined")):
            b.put(v, N.metric_key(f"year_{int(r['test_year'])}", coh, base + suf), r[c], f, int(i), c, f"{r['contrast']}:{c}",
                  ds_cache.get((int(r["test_year"]), h, str(r["cohort"]))), text(r["interval_reason"]) if c.startswith("ci") else None)


def v1_contrast(name: str) -> tuple:
    a, bb = name.split("-", 1)
    return a, N.arm({"persistence": "persistence"}.get(bb, bb))[0], "f2"


def contrast_files(b: Builder, fam_of, rel: str, parse, ds_cache: dict, diag: bool, family_from_row=None) -> None:
    f = b.rel(rel)
    d = read_csv(b.path(b.need(f) and f))
    for i, r in d.iterrows():
        y, h, coh = int(r["test_year"]), int(r["horizon"]), str(r["cohort"])
        a_raw, bname, metric = parse(str(r["contrast"]) if "metric" not in r.index else (str(r["contrast"]), str(r["metric"])))
        fam = family_from_row(r) if family_from_row else fam_of
        v = None
        for kind in ("fitted", "alias", "metric_only"):
            key = f"{fam}/{N.arm(a_raw)[0]}/{N.lead_tag(h)}"
            if key in b.views:
                v = b.views[key]
                break
        if v is None:
            raise SourceConflict(f"{f}:{i}: contrast for unknown view {a_raw} H{h}")
        dm = N.delta_metric(metric) if metric not in ("f2",) else "binary.f2"
        prefix = "diagnostic.delta" if (diag or bool(r.get("diagnostic_only", False)) is True) else "delta"
        base = f"{prefix}.{v['arm']}_minus_{bname}.{dm}"
        ds = ds_cache.get((y, h, coh))
        for col in ("point_delta_f2", "point_delta", "ci_low", "ci_high", "valid_draws", "undefined_draws"):
            if col in r.index:
                b.put(v, N.metric_key(f"year_{y}", N.cohort(coh), base + N.DELTA_COLUMNS[col]), r[col], f, int(i), col,
                      f"{r['contrast']}:{col}", ds, text(r.get("interval_reason")) if col.startswith("ci") else None,
                      text(r.get("interval_status")) if col.startswith("ci") else None)


# ------------------------------------------------------------------ format: Somalia v2 / v3

def extract_somalia_v2v3(b: Builder) -> None:
    ver = b.src["format"]  # somalia_v2 | somalia_v3
    v3 = ver == "somalia_v3"
    fams = b.src["families"]  # v2: [fam]; v3: [observed, augmented]
    fam_of_branch = {"original": fams[0], "augmented": fams[-1]}
    group = b.src["eval_group"]
    schemas = json.loads(b.path(b.rel("features/feature_schema.json")).read_text())
    inv = read_csv(b.path(b.rel("models/model_inventory.csv")))
    inv["h"] = inv.job_id.str.extract(r"_h(\d\d)_")[0].astype(int)
    status = read_csv(b.path(b.rel("fits/final_status.csv")))
    shared = [("models/model_inventory.csv", "model_inventory"), ("features/feature_schema.json", "feature_schema"),
              ("fits/final_fit_ledger.csv.gz", "fit_keys"), ("fits/calibration_mappings.csv", "calibration"),
              ("fits/final_status.csv", "fit_status"), ("selection/selected_recipes.csv", "selection"),
              ("selection/candidate_scores.csv", "selection"), ("selection/oof_fit_ledger.csv", "calibration_inputs"),
              ("selection/oof_predictions.csv.gz", "calibration_inputs")]
    view_col = "view"
    groups = inv.groupby(["branch", view_col, "h"]) if v3 else inv.groupby([view_col, "h"])
    for key, g in groups:
        if v3:
            branch, view_raw, h = key
            fam, label = fam_of_branch[branch], ("observed" if branch == "original" else "training_augmented")
        else:
            view_raw, h = key
            fam, label, branch = fams[0], "observed", None
        st = status[(status.view == view_raw) & (status.horizon == h) & ((status.branch == branch) if v3 else True)]
        jobs = sorted(set(g.job_id))
        if sorted(set(st.job_id)) != jobs or (st.status != "completed").any():
            raise SourceConflict(f"{b.src['source_key']} {key}: model jobs differ from completed final_status jobs")
        for j in jobs:
            form = st[st.job_id == j].formulation.iloc[0]
            have = set(g[g.job_id == j].target)
            need = {"q2", "q3_direct", "q4", "q5"} | ({"q3_residual_delta"} if form == "residual" else set())
            if have != need:
                raise SourceConflict(f"{b.src['source_key']} {key} {j}: members {sorted(have)} != required {sorted(need)}")
        v = b.view(fam, view_raw, h, "fitted")
        tds, n_in = somalia_training(b, fam, h, f"h{h:02d}_{'D' if view_raw.startswith('D') else view_raw}"
                                     if f"h{h:02d}_{view_raw}" not in schemas else f"h{h:02d}_{view_raw}", label, schemas)
        b.version(v, somalia_members(b, g, shared), tds, n_in, fit_units=len(jobs))
        v["datasets"].add(tds)
        if not v3 and view_raw == "D_residual":
            sel = read_csv(b.path(b.rel("selection/selected_recipes.csv")))
            ds_ = sel[sel.view == "D_selected"]
            if not (ds_.formulation == "residual").all():
                raise SourceConflict("v2 D_selected is not the residual recipe in every year; alias mapping invalid")
            sv = b.view(fam, "D_selected", h, "fitted")
            b.version(sv, somalia_members(b, g, shared, "alias_selected_recipe",
                                          "D_selected reuses the D_residual fits (selected_recipes.csv; run_somalia_q3_optimization.py:86-94)"),
                      tds, n_in, fit_units=0)
            sv["datasets"].add(tds)
            sv["fit_note"] = "Selected recipe = residual in 2025 and 2026; members are the D_residual fits (no separate fit)."
    if not v3:
        for h in (0,):
            base = b.views[f"{fams[0]}/seasonal_climate/00"]
            b.view(fams[0], "C", 0, "alias", alias_of=base["version_key"], alias_text="seasonal_climate 0-month (H0 C reused from B)",
                   n_inputs=base["n_inputs"], compare_with="seasonal_climate 0-month gives identical predictions; compare C with B at 3/6/12-month.")
    # datasets
    coh_l = read_csv(b.path(b.rel("ledgers/cohort_ledger.csv.gz")))
    lab_full = read_csv(b.path(b.rel("ledgers/label_ledger.csv.gz")))
    lab = lab_full[["area_id", "target_ord", "overall_phase", "actual_crisis", "q3"]]
    prov = {h: read_csv(b.path(b.rel(f"ledgers/row_provenance_h{h:02d}.csv.gz"))) for h in (0, 3, 6, 12)}
    if v3:
        prov = {h: p[~p.is_copy.astype(bool)] for h, p in prov.items()}
    ds_cache = {}
    m = read_csv(b.path(b.rel("metrics/metrics.csv")))
    f = b.rel("metrics/metrics.csv")

    def ds_for(y, h, coh, n):
        k = (y, h, coh)
        if k in ds_cache:
            return ds_cache[k]
        c = coh_l[(coh_l.test_year == y) & (coh_l.horizon == h) & (coh_l.status == "primary")][["area_id", "target_ord"]]
        kt = c.merge(lab, on=["area_id", "target_ord"], how="left")
        if kt.q3.isna().any():
            raise SourceConflict(f"{b.src['source_key']} {y} H{h}: primary keys without truth")
        kt = kt.astype({"overall_phase": int, "actual_crisis": int})
        p = prov[h]
        basis_note = {}
        if coh == "share_history_subset":
            ok = p[np.isfinite(p.hist_q3_obs1) & (p.history_obs1_source_ord >= 0)][["area_id", "target_ord"]]
            kt = kt.merge(ok, on=["area_id", "target_ord"])
        elif coh == "phase_persistence_subset":
            if "persistence_available" in p.columns:
                ok = p[p.persistence_available.fillna(False).astype(bool)][["area_id", "target_ord"]]
            else:
                withorig = kt[["area_id", "target_ord"]].merge(p[["area_id", "target_ord", "origin_ord"]], on=["area_id", "target_ord"], how="left")
                if withorig.origin_ord.isna().any():
                    raise SourceConflict(f"{b.src['source_key']} {y} H{h}: primary keys without saved origin_ord")
                ok = persistence_rule(lab_full, withorig)
                basis_note["rule"] = PERSISTENCE_RULE
            kt = kt.merge(ok, on=["area_id", "target_ord"])
        if n is not None and len(kt) != n:
            raise SourceConflict(f"{b.src['source_key']} {y} H{h} {coh}: {len(kt)} reconstructed keys vs reported n {n}")
        name = b.eval_dataset(h, f"year_{y}", coh, group, kt, ["overall_phase", "actual_crisis", "q3"],
                              SOMALIA_TRUTH["v3" if v3 else "v2"], source_hash=basis_note.get("rule") and {"eligibility_rule": basis_note["rule"]})
        ds_cache[k] = name
        return name

    ids = {"test_year", "horizon", "n_primary", "n_wider_only", "n_excluded"} if not v3 else {"test_year", "horizon", "n_primary"}
    unknown = [c for c in m.columns if pd.api.types.is_numeric_dtype(m[c]) and c not in N.LEAF and c not in ids]
    if unknown:
        raise SourceConflict(f"{f}: numeric columns without a naming rule: {unknown}")
    leaves = [c for c in m.columns if c in N.LEAF and c not in ("test_year", "horizon")]
    for i, r in m.iterrows():
        y, h, coh, view_raw = int(r["test_year"]), int(r["horizon"]), str(r["cohort"]), str(r["view"])
        role = f"year_{y}"
        if view_raw == "all":
            for v in [v for v in b.views.values() if v["lead"] == h]:
                b.slot(v, role, N.cohort(coh), "empty_cohort", text(r["reason"]))
                b.put(v, N.metric_key(role, N.cohort(coh), "n_rows"), None, f, int(i), "n", "all:n", None, text(r["reason"]), "empty_cohort")
            continue
        branch = str(r["branch"]) if v3 else None
        fams_here = ([fam_of_branch[branch]] if branch in fam_of_branch else fams) if v3 else fams
        kind = "fitted" if view_raw in ("A", "B", "C", "D_direct", "D_residual", "D_selected") else "metric_only"
        if view_raw == "C" and h == 0:
            kind = "alias"
        if view_raw.startswith("v1_"):
            kind = "reference"
        n = int(r["n"]) if finite(r.get("n")) else None
        ds = ds_for(y, h, coh, n) if r["status"] in ("ok", "calibrated_unavailable") and n is not None else None
        st = str(r["status"])
        for fam in fams_here:
            extra = {}
            if kind == "reference":
                rk = f"somalia_oracle_information/weather_oracle_with_share_history/{N.lead_tag(h)}@{b.src['reference_source']}"
                if rk not in b.deps["plans"][b.src["reference_source"]]["versions"]:
                    raise SourceConflict(f"reference version {rk} missing")
                extra = {"alias_of": rk, "alias_text": "Somalia oracle information historical weather_oracle_with_share_history (v1 D)"}
            v = b.view(fam, view_raw, h, kind, **extra)
            ns = "diagnostic_raw_bounded." if st == "calibrated_unavailable" else ""
            for c in leaves:
                if c in ("n",):
                    b.put(v, N.metric_key(role, N.cohort(coh), "n_rows"), r[c], f, int(i), c, f"{view_raw}:{c}", ds)
                    continue
                b.put(v, N.metric_key(role, N.cohort(coh), ns + N.leaf(c)), r[c], f, int(i), c, f"{view_raw}:{c}", ds,
                      text(r["reason"]), st)
            b.slot(v, role, N.cohort(coh), {"ok": "complete", "calibrated_unavailable": "calibration_unavailable_raw_bounded_diagnostic"}.get(st, st), text(r["reason"]))

    def parse(cm):
        name, metric = cm
        a, bb = name.split("-", 1)
        if v3:
            def arm_of(x):
                for br in ("augmented", "original"):
                    if x.startswith(br + "_"):
                        return br, x[len(br) + 1:]
                return None, x
            ba, araw = arm_of(a)
            bb_br, braw = arm_of(bb)
            bname = N.arm(braw)[0]
            if bb_br and bb_br != ba:
                bname = ("observed_label_" if bb_br == "original" else "augmented_training_") + bname
            parse.fam = fam_of_branch[ba] if ba else fams[0]
            return araw, bname, metric
        return a, N.arm(bb)[0], metric

    contrast_files(b, fams[0], "metrics/contrasts.csv", parse, ds_cache, diag=False,
                   family_from_row=(lambda r: fam_of_branch[str(r["contrast"]).split("_", 1)[0]] if v3 else fams[0]))


# ------------------------------------------------------------------ format: Somalia v4

def extract_somalia_v4(b: Builder) -> None:
    fams = {"original": b.src["families"][0], "augmented": b.src["families"][1]}
    labels = {"original": "observed", "augmented": "role_augmented"}
    schemas = json.loads(b.path(b.rel("features/feature_schema.json")).read_text())
    inv = read_csv(b.path(b.rel("models/model_inventory.csv")))
    inv["setting"] = inv.job_id.str.split("_").str[0]
    inv["h"] = inv.job_id.str.extract(r"_h(\d\d)_")[0].astype(int)
    status = read_csv(b.path(b.rel("fits/final_status.csv")))
    jobs = read_csv(b.path(b.rel("ledgers/jobs.csv")))
    shared = [("models/model_inventory.csv", "model_inventory"), ("features/feature_schema.json", "feature_schema"),
              ("fits/final_fit_ledger.csv.gz", "fit_keys"), ("fits/calibration_mappings.csv", "calibration"),
              ("fits/final_status.csv", "fit_status"), ("selection/selected_recipes.csv", "selection"),
              ("selection/candidate_scores.csv", "selection"), ("selection/contexts.csv", "selection"),
              ("selection/pool_specs.csv.gz", "selection"), ("selection/oof_units.csv.gz", "calibration_inputs"),
              ("selection/oof_predictions.csv.gz", "calibration_inputs"), ("selection/calibration_keys.csv.gz", "calibration_inputs"),
              ("selection/final_calibration_keys.csv.gz", "calibration_inputs"), ("selection/history_overrides.csv.gz", "fit_inputs"),
              ("features/final_override_features.csv.gz", "fit_inputs"), ("ledgers/jobs.csv", "jobs")]
    for (setting, h), g in inv.groupby(["setting", "h"]):
        st = status[(status.data_setting == setting) & (status.horizon == h)]
        jj = jobs[(jobs.data_setting == setting) & (jobs.horizon == h)]
        if sorted(set(g.job_id)) != sorted(set(jj.job_id)) or sorted(set(st.job_id)) != sorted(set(jj.job_id)) or (st.status != "completed").any():
            raise SourceConflict(f"v4 {setting} H{h}: model jobs differ from jobs/final_status")
        for j in set(g.job_id):
            form = st[st.job_id == j].formulation.iloc[0]
            have = set(g[g.job_id == j].target)
            need = {"q2", "q3_direct", "q4", "q5"} | ({"q3_residual_delta"} if form == "residual" else set())
            if have != need:
                raise SourceConflict(f"v4 {j}: members {sorted(have)} != required {sorted(need)}")
        fam = fams[setting]
        v = b.view(fam, "D_calibrated", h, "fitted")
        tds, n_in = somalia_training(b, fam, h, f"h{h:02d}_D", labels[setting], schemas)
        b.version(v, somalia_members(b, g, shared), tds, n_in, fit_units=int(g.job_id.nunique()))
        v["datasets"].add(tds)
    coh_l = read_csv(b.path(b.rel("ledgers/cohort_ledger.csv.gz")))
    lab = read_csv(b.path(b.rel("ledgers/label_ledger.csv.gz")))[["area_id", "target_ord", "overall_phase", "actual_crisis", "q3"]]
    slots = read_csv(b.path(b.rel("ledgers/cohort_slots.csv")))
    group = b.src["eval_group"]

    def required(setting, h, years):
        c = coh_l[(coh_l.data_setting == setting) & (coh_l.horizon == h) & (coh_l.status == "primary") & coh_l.outer_year.isin(years)]
        kt = c[["area_id", "target_ord", "is_copy", "source_family", "original_month_ord"]].merge(lab, on=["area_id", "target_ord"], how="left")
        # copy rows carry their own saved truth in the label ledger (scored by augexp.py:1216,1232-1239)
        if kt["q3"].isna().any():
            raise SourceConflict(f"v4 {setting} H{h}: required keys without label-ledger truth")
        kt["is_copy"] = kt.is_copy.astype(bool).astype(int)
        kt["original_month_ord"] = kt.original_month_ord.fillna(-1).astype(np.int64)
        kt["overall_phase"] = kt.overall_phase.astype("Int64").astype(str)
        kt["actual_crisis"] = kt.actual_crisis.astype("Int64").astype(str)
        return c, kt

    for fname, kind in (("metrics/annual_metrics.csv", "annual"), ("metrics/pooled_metrics.csv", "pooled")):
        f = b.rel(fname)
        d = read_csv(b.path(f))
        for i, r in d.iterrows():
            setting, h = str(r["data_setting"]), int(r["horizon"])
            v = b.views[f"{fams[setting]}/calibrated_share_history/{N.lead_tag(h)}"]
            if kind == "annual":
                years, role = [int(r["outer_year"])], f"year_{int(r['outer_year'])}"
            else:
                years = [int(x) for x in str(r["years"]).split(";")]
                role = "pooled"
            st = str(r["status"])
            c, kt = required(setting, h, years)
            src_hash = text(r["cohort_sha256"])
            if src_hash and v4_hash(c) != src_hash:
                raise SourceConflict(f"v4 {setting} {role} H{h}: required keys do not match the source cohort_sha256")
            if kind == "annual":
                srow = slots[(slots.data_setting == setting) & (slots.outer_year == years[0]) & (slots.horizon == h)]
                if int(srow.primary.iloc[0]) != len(c):
                    raise SourceConflict(f"v4 {setting} {role} H{h}: cohort_slots primary {int(srow.primary.iloc[0])} != {len(c)}")
            ds = None
            if len(c):
                ds = b.eval_dataset(h, role, "primary", f"{group}, {labels[setting].replace('_', '-')} labels", kt,
                                    ["overall_phase", "actual_crisis", "q3"], SOMALIA_TRUTH["v4"], n_required=len(c),
                                    extra_key_cols=("is_copy", "source_family", "original_month_ord"),
                                    source_hash={"algorithm": "somalia_oracle/augexp.py cohort_digest", "sha256": src_hash})
            scored = int(r["n"]) if finite(r.get("n")) else 0
            if st == "complete" and scored != len(c):
                raise SourceConflict(f"v4 {setting} {role} H{h}: complete slot scored {scored} of {len(c)} required rows")
            for col in d.columns:
                if col in N.LEAF and col not in ("horizon",):
                    reason = text(r.get(f"{col}_reason")) or text(r["reason"])
                    b.put(v, N.metric_key(role, "primary", N.leaf(col)), r[col], f, int(i), col, col, ds, reason, st)
            b.put(v, N.metric_key(role, "primary", "n_rows_required"), len(c) if len(c) else None, f, int(i), "cohort_ledger",
                  "required primary keys (ledgers/cohort_ledger.csv.gz)", ds, text(r["reason"]), st)
            detail = text(r["reason"])
            if kind == "pooled":
                scored_years = [int(x.split(":")[0]) for x in str(r["rows_by_year"]).split(";")] if text(r["rows_by_year"]) else []
                detail = (detail + "; " if detail else "") + "declared years " + ",".join(map(str, years)) + (
                    "; scored years " + ",".join(map(str, scored_years)) if scored_years else "; no pooled score")
            b.slot(v, role, "primary", st, detail)


EXTRACTORS = {"modern_runs": extract_modern_runs, "launch": extract_launch, "somalia_v1": extract_somalia_v1,
              "somalia_v2": extract_somalia_v2v3, "somalia_v3": extract_somalia_v2v3, "somalia_v4": extract_somalia_v4}
