#!/usr/bin/env python3
"""Extend the compact historical evaluation (global and genuinely Somalia-local) with a January-April 2026 block.

Task ``10-09-compact-eval-2026-jan-apr`` (prd.md R1-R6, design.md). For each scope the seven compact runs (baseline
H0/H3/H6/H12, realized-weather oracle H3/H6/H12; H0 shared) keep their verified original 2022-2025 batches and gain one
new annual 2026 batch (labels <= Jan 2026 - max(H, 1), weights anchored at Jan 2026 - H) scored on every valid January-April
2026 key. Only 14 new batches / 56 boosters are fitted across both scopes.

- The unchanged frozen parent gate (``load_origin_inputs``) runs first with the original cohort masks; afterwards a COPIED
  mapping replaces the evaluation mask with the 2026 January-April keys (and, for SOM, both fitting and evaluation masks are
  intersected with the canonical ``iso3 == "SOM"`` membership). A new extension fingerprint binds the extension manifest,
  scope, keys, approved-spec copies and this script; it never relabels an original fit.
- The unchanged annual primitive ``run_origin_batch(..., year=2026)`` fits; ``verify_batch`` resumes only complete matching
  batches. Original 2022-2025 artifacts are re-hashed and checked against their recomputed original fingerprints, keys,
  truth, targets and fitting provenance before reuse; their schemas are inspected, their metrics recomputed.
- Periods: 2022..2026, ``pooled_2022_2026`` (main) and ``pooled_2022_2025`` (original); eight metrics, paired
  oracle - baseline differences, global regions 0..8 (no dropped groups) or SOM.

Modes: ``--scope {global,SOM}`` with ``--validate-only`` (read-only gates; writes nothing), ``--approve-training``,
``--report`` (saved artifacts only; status verification_pending) and ``--verify`` (independent replay; never fits).
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Mapping, Optional, Sequence, Tuple

PROJECT_ROOT = next(path for path in Path(__file__).resolve().parents if (path / "src").exists())
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import numpy as np
import pandas as pd

from ipcch import compact_features as cpf
from ipcch import compact_launch as cl
from ipcch import origin_safe as osf
from ipcch import paths
from ipcch import regional_point_metrics as rpm


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, PROJECT_ROOT / rel)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # dataclasses with postponed annotations resolve through sys.modules
    spec.loader.exec_module(module)
    return module


# unchanged frozen modules: origin-safe runner (gate, annual fitter, resume), scikit-learn metric replay, and the accepted
# Somalia-local script (original local fingerprint reconstruction and its generic CSV/metric/codebook helpers)
runner = _load("eval2026_origin_safe_runner", "scripts/modeling/run_deep_feature_weight_decay_forecasting.py")
legacy = _load("eval2026_sklearn_replay", "scripts/postprocessing/verify_origin_safe_climate_idp.py")
som = _load("eval2026_somalia_local_script", "scripts/modeling/run_somalia_local_compact_test.py")

SCOPES = ("global", "SOM")
VERSIONS = {"global": "compact_climate_weather_oracle_eval_2026_jan_apr_v1", "SOM": "compact_climate_weather_oracle_eval_2026_jan_apr_v1_somalia_local"}
MODEL_SCOPE = {"global": "global", "SOM": "Somalia local"}
ISO3 = "SOM"
NEW_YEAR, NEW_MONTHS = 2026, (1, 2, 3, 4)
OLD_YEARS = tuple(osf.TARGET_YEARS)
YEARS = (*OLD_YEARS, NEW_YEAR)
PERIOD_YEARS = {**{str(y): (y,) for y in YEARS}, "pooled_2022_2026": YEARS, "pooled_2022_2025": OLD_YEARS}
PERIODS = tuple(PERIOD_YEARS)
MAIN_POOLED, ORIGINAL_POOLED = "pooled_2022_2026", "pooled_2022_2025"
RUNS = tuple(cpf.RUN_PLAN)
ORACLE_H = (3, 6, 12)
KEYS = list(osf.KEYS)
PARAMS = dict(som.PARAMS)
SUPPORT = ["n_rows", "n_areas", "observed_3plus", "observed_1_2", "predicted_3plus", "true_positive_3plus", "distinct_phase3_worse"]
A = paths.SOURCE_DATA_DIR / "assembled_IPCCH"
PARENT_MANIFEST = A / "model_ready" / cpf.VERSION / f"{cpf.VERSION}_manifest.json"
MEMBERSHIP = A / "country_area_id_lookup.csv"
REGION_MAP = paths.REFERENCE_DATA_DIR / "area_id_country_region_mapping.csv"
REGION_MAP_SHA256 = "18ab5099ce2d1154fb5686183ee399124e18427cc1594923f7abe2769da1611d"
TASK_DIR = PROJECT_ROOT / ".trellis" / "tasks" / "10-09-compact-eval-2026-jan-apr"
SPEC_FILES = ("prd.md", "design.md", "implement.md", "approval.md", "expected_runs.csv", "research/contracts.md")
ORIG_GLOBAL = paths.RESULTS_DIR / "experiments" / cpf.VERSION
ORIG_SOM = paths.RESULTS_DIR / "experiments" / som.HIST_VERSION
# approved January-April 2026 support (prd.md R2) and pinned original evaluation identities (research/contracts.md)
MONTH_SUPPORT = {"global": {1: 679, 2: 643, 3: 231, 4: 2774}, "SOM": {1: 1, 2: 0, 3: 0, 4: 904}}
ORIGINAL_EVAL_SHA256 = {"global": "f0193c1402d0609556755844b476227b7188f9671323d21317336d7ef58d2e0f",
                        "SOM": "5f8343c4b4ba92176b1a7fa2797dfb9c29d5805065f200df46c416efcea9f14a"}
ORIGINAL_SOM_MANIFEST_SHA256 = "573b0d0bb074a2de9251afacf549dfe18a30321af8bce87dfce75ac0644fe228"
PROTECTED_NAMESPACES = (cpf.VERSION, som.HIST_VERSION, cl.VERSION, "nowcasting_2026_04_compact_cds_v1", som.LAUNCH_VERSION, *cpf.LEGACY_NAMESPACES)
CODEBOOK_NAME = {"global": "IPCCH_compact_climate_weather_oracle_eval_2026_jan_apr_model_run_codebook_en.csv",
                 "SOM": "IPCCH_compact_climate_weather_oracle_eval_2026_jan_apr_somalia_local_model_run_codebook_en.csv"}
REPORT_TABLES = {"global": ("all_metrics_long.csv", "global_metrics.csv", "regional_metrics.csv", "global_deltas.csv", "regional_deltas.csv",
                            "undefined_reasons.csv", "coverage_by_month.csv"),
                 "SOM": ("som_metrics_long.csv", "som_oracle_minus_baseline_deltas.csv", "som_undefined_reasons.csv", "coverage_by_month.csv")}

LocalError = som.LocalError
sha, sha_bytes, digest, canonical_json, csv_bytes = som.sha, som.sha_bytes, som.digest, som.canonical_json, som.csv_bytes
read_csv, write_once, write_json, save_table, log = som.read_csv, som.write_once, som.write_json, som.save_table, som.log


def run_id(arm: str, horizon: int) -> str:
    return f"{arm}/{horizon}m"


def ym(o: int) -> str:
    return osf.ord_label(int(o))


# --------------------------------------------------------------------------- context (injectable for tiny fixtures)


def default_original_fingerprint(scope: str) -> Callable:
    """Recompute each ORIGINAL run fingerprint from the current gated parent inputs (never trust a stored value alone)."""
    cache = {}

    def fp(inputs: Mapping[str, object], arm: str, horizon: int) -> str:
        if scope == "global":
            return inputs["fingerprint"]  # the original global runs used the parent gate fingerprint unchanged
        if "prep" not in cache:
            cache["ctx"] = som.Ctx()
            cache["prep"] = som.hist_prepare(cache["ctx"], write=False)  # read-only; archived spec copies are hash-checked
            if cache["prep"]["sha256"] != ORIGINAL_SOM_MANIFEST_SHA256:
                raise LocalError("original Somalia-local manifest identity differs from the accepted value")
        return som.hist_localize(cache["ctx"], cache["prep"], inputs, arm, horizon)["fingerprint"]

    return fp


def default_protected_paths() -> List[Tuple[str, Path]]:
    code = sorted(set(cpf.FIT_CODE) | set(cl.CODE_FILES) | set(cl.FIT_CODE) | {
        "scripts/modeling/run_somalia_local_compact_test.py", "scripts/modeling/run_compact_climate_weather_oracle_suite.py",
        "scripts/postprocessing/verify_compact_climate_weather_oracle.py", "scripts/postprocessing/verify_origin_safe_weather_oracle.py",
        "scripts/postprocessing/verify_origin_safe_climate_idp.py", "src/ipcch/regional_point_metrics.py", "src/ipcch/paths.py",
        "configs/forecasting_hyperparameters.json", "configs/forecasting_hyperparameters_p3.json"})
    out = [("code", PROJECT_ROOT / rel) for rel in code]
    roots = (("parent_inputs", A / "model_ready" / cpf.VERSION), ("launch_inputs", cl.INPUT_ROOT),
             ("old_results", ORIG_GLOBAL), ("old_results", ORIG_SOM), ("old_reports", paths.REPORTS_DIR / cpf.VERSION),
             ("old_reports", paths.REPORTS_DIR / som.HIST_VERSION), ("launch_results", cl.RESULTS_ROOT), ("launch_reports", cl.REPORTS_ROOT),
             ("launch_results", som.LAUNCH_RESULTS), ("launch_reports", som.LAUNCH_REPORTS))
    for role, root in roots:
        out += [(role, p) for p in sorted(Path(root).rglob("*")) if p.is_file()]
    parent = json.loads(PARENT_MANIFEST.read_text())
    out += [("parent_inputs", Path(parent["cohort"]["path"])), ("parent_inputs", Path(parent["parent_manifest"]["path"])),
            ("membership", MEMBERSHIP), ("reference", REGION_MAP)]
    return [(r, p) for r, p in out if p.exists()]


@dataclass
class Ctx:
    scope: str
    results: Optional[Path] = None
    reports: Optional[Path] = None
    original_results: Optional[Path] = None
    parent_manifest: Path = PARENT_MANIFEST
    membership: Path = MEMBERSHIP
    region_map: Path = REGION_MAP
    region_map_sha256: Optional[str] = REGION_MAP_SHA256
    spec_dir: Path = TASK_DIR
    script: Path = Path(__file__).resolve()
    month_support: Optional[Mapping[int, int]] = None
    original_eval_sha256: Optional[str] = None
    frozen_feature_sha256: Optional[Mapping[Tuple[str, int], str]] = field(default_factory=lambda: dict(cpf.FROZEN_FEATURE_SHA256))
    contract_sha256: Optional[Mapping[str, str]] = field(default_factory=lambda: dict(cpf.FROZEN_CONTRACT_SHA256))
    load_inputs: Callable = runner.load_origin_inputs
    hyperparameters: Callable = runner.load_hyperparameters
    original_fingerprint: Optional[Callable] = None
    protected_paths: Callable = default_protected_paths

    def __post_init__(self):
        if self.scope not in SCOPES:
            raise LocalError(f"scope must be one of {SCOPES}")
        version = VERSIONS[self.scope]
        self.results = Path(self.results or paths.RESULTS_DIR / "experiments" / version)
        self.reports = Path(self.reports or paths.REPORTS_DIR / version)
        self.original_results = Path(self.original_results or (ORIG_GLOBAL if self.scope == "global" else ORIG_SOM))
        self.month_support = MONTH_SUPPORT[self.scope] if self.month_support is None else self.month_support
        self.original_eval_sha256 = ORIGINAL_EVAL_SHA256[self.scope] if self.original_eval_sha256 is None else self.original_eval_sha256
        self.original_fingerprint = self.original_fingerprint or default_original_fingerprint(self.scope)

    @property
    def version(self) -> str:
        return VERSIONS[self.scope]


def assert_new_root(path: Path) -> Path:
    hit = [ns for ns in PROTECTED_NAMESPACES if ns in Path(path).resolve().parts]
    if hit:
        raise LocalError(f"refusing to write into a protected namespace {hit}: {path}")
    return Path(path)


def manifest_path(ctx: Ctx) -> Path:
    return ctx.results / "inputs" / "extension_manifest.json"


def run_dir(ctx: Ctx, arm: str, horizon: int) -> Path:
    return ctx.results / "runs" / arm / f"{horizon}m"


def original_run_dir(ctx: Ctx, arm: str, horizon: int) -> Path:
    return ctx.original_results / "runs" / arm / f"{horizon}m"


# --------------------------------------------------------------------------- approved spec, expectations, selection


def spec_files(ctx: Ctx) -> Dict[str, bytes]:
    """Approved contract bytes: the active task directory while it exists, afterwards the manifest-bound copies."""
    active = Path(ctx.spec_dir)
    if all((active / name).exists() for name in SPEC_FILES):
        return {name: (active / name).read_bytes() for name in SPEC_FILES}
    mpath = manifest_path(ctx)
    if not mpath.exists():
        raise LocalError(f"approved spec is neither at {active} nor bound by an extension manifest {mpath}")
    bound = json.loads(mpath.read_text())["files"]
    out = {}
    for name in SPEC_FILES:
        copy = mpath.parent / "approved_spec" / name
        item = bound.get(f"approved_spec/{name}")
        if item is None or not copy.exists() or sha(copy) != item["sha256"]:
            raise LocalError(f"archived-task spec copy {copy} is missing or differs from its manifest hash")
        out[name] = copy.read_bytes()
    return out


def expected_runs(ctx: Ctx, spec: Mapping[str, bytes]) -> Dict[str, dict]:
    import io

    table = pd.read_csv(io.BytesIO(spec["expected_runs.csv"]))
    part = table[table["scope"] == ctx.scope]
    out = {run_id(r.arm, int(r.horizon)): r._asdict() for r in part.itertuples(index=False)}
    if sorted(out) != sorted(run_id(a, h) for a, h in RUNS) or (part["model_scope"] != MODEL_SCOPE[ctx.scope]).any() \
            or (part["block_year"] != NEW_YEAR).any() or int(part["new_boosters"].sum()) != 28:
        raise LocalError("approved expected_runs.csv does not hold the seven 2026 runs of this scope")
    return out


def parent_manifest(ctx: Ctx) -> dict:
    manifest = json.loads(Path(ctx.parent_manifest).read_text())
    if manifest.get("version") != cpf.VERSION or manifest.get("status") != "COMPLETE":
        raise LocalError(f"parent manifest is not a COMPLETE {cpf.VERSION} build")
    if sha(manifest["cohort"]["path"]) != manifest["cohort"]["sha256"]:
        raise LocalError("parent cohort bytes differ from the parent manifest")
    files = manifest["contract"]["files"]
    for name, item in files.items():
        if sha(item["path"]) != item["sha256"]:
            raise LocalError(f"parent contract {name} differs from the parent manifest")
    if ctx.contract_sha256 is not None and {k: v["sha256"] for k, v in files.items()} != dict(ctx.contract_sha256):
        raise LocalError("parent manifest does not bind the approved compact contract bytes")
    return manifest


def membership(ctx: Ctx) -> Optional[dict]:
    if ctx.scope == "global":
        return None
    lookup = pd.read_csv(ctx.membership, keep_default_na=False, na_values=[""])
    if lookup["area_id"].isna().any() or lookup["area_id"].duplicated().any():
        raise LocalError("membership lookup has missing or duplicate area_id")
    rows = lookup[lookup["iso3"] == ISO3]
    ids = sorted(int(a) for a in rows["area_id"])
    if not ids or sorted(rows["country"].unique()) != ["Somalia"]:
        raise LocalError("SOM membership is empty or not exactly the country Somalia")
    return {"path": str(ctx.membership), "sha256": sha(ctx.membership), "column": "iso3", "value": ISO3, "n_areas": len(ids),
            "area_ids_sha256": osf.list_sha256(str(i) for i in ids), "area_ids": ids}


def region_series(ctx: Ctx) -> pd.Series:
    return rpm.load_region_map(ctx.region_map, ctx.region_map_sha256)


def selection(ctx: Ctx, manifest: Mapping[str, object], member: Optional[dict]) -> dict:
    """Frozen 2026 January-April evaluation keys and the scope's fitting-valid rows, from the unchanged cohort."""
    cohort = pd.read_csv(manifest["cohort"]["path"])
    if cohort[KEYS].duplicated().any():
        raise LocalError("parent cohort has duplicate keys")
    inscope = np.ones(len(cohort), dtype=bool) if member is None else cohort["area_id"].isin(member["area_ids"]).to_numpy()
    valid = cohort["share_valid"].to_numpy(dtype=bool)
    old_eval = cohort["eval_key"].to_numpy(dtype=bool) & inscope
    year, month = cohort["year"].to_numpy(), cohort["month"].to_numpy()
    if (cohort["eval_key"].to_numpy(dtype=bool) & (year == NEW_YEAR)).any():
        raise LocalError("parent cohort already marks 2026 keys as evaluation keys")
    new_eval = valid & inscope & (year == NEW_YEAR) & np.isin(month, NEW_MONTHS)
    keys = cohort[KEYS].reset_index(drop=True)
    new_keys, old_keys = keys[new_eval].reset_index(drop=True), keys[old_eval].reset_index(drop=True)
    support = {int(m): int(((month == m) & new_eval).sum()) for m in NEW_MONTHS}
    if dict(ctx.month_support) != support:
        raise LocalError(f"2026 January-April support {support} differs from the approved {dict(ctx.month_support)}")
    if osf.keys_sha256(old_keys) != ctx.original_eval_sha256:
        raise LocalError("original 2022-2025 evaluation keys differ from the pinned original identity")
    summary = {"label_keys": len(cohort), "new_eval_rows": len(new_keys), "new_eval_areas": int(new_keys["area_id"].nunique()),
               "new_eval_keys_sha256": osf.keys_sha256(new_keys), "month_support_rows": support,
               "month_support_areas": {int(m): int(new_keys.loc[new_keys["month"] == m, "area_id"].nunique()) for m in NEW_MONTHS},
               "old_eval_rows": len(old_keys), "old_eval_keys_sha256": osf.keys_sha256(old_keys),
               "old_eval_by_year": {int(y): int(n) for y, n in old_keys["year"].value_counts().sort_index().items()},
               "fit_valid_rows": int((valid & inscope).sum()), "fit_valid_keys_sha256": osf.keys_sha256(keys[valid & inscope]),
               "expanded_pooled_rows": len(old_keys) + len(new_keys)}
    if ctx.scope == "global":
        regions = region_series(ctx)
        reg = regions.reindex(new_keys["area_id"].to_numpy())
        if reg.isna().any():
            raise LocalError("2026 evaluation keys without a region")
        summary["region_month_rows"] = {int(r): {int(m): int(((reg.to_numpy() == r) & (new_keys["month"].to_numpy() == m)).sum()) for m in NEW_MONTHS}
                                        for r in rpm.REGIONS}
    return {"keys": keys, "inscope": inscope, "fit_valid": valid & inscope, "new_eval": new_eval, "old_eval": old_eval,
            "new_keys": new_keys, "old_keys": old_keys, "summary": summary}


def coverage_table(ctx: Ctx, sel: Mapping[str, object]) -> pd.DataFrame:
    new = sel["new_keys"]
    rows = []
    regions = region_series(ctx) if ctx.scope == "global" else None
    for m in NEW_MONTHS:
        part = new[new["month"] == m]
        row = {"scope": ctx.scope, "model_scope": MODEL_SCOPE[ctx.scope], "year": NEW_YEAR, "month": m, "rows": len(part),
               "areas": int(part["area_id"].nunique()), "populated": len(part) > 0}
        if regions is not None:
            reg = regions.reindex(part["area_id"].to_numpy()).to_numpy()
            row.update({f"region_{r}_rows": int((reg == r).sum()) for r in rpm.REGIONS})
        rows.append(row)
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- extension manifest and localization


def extension_files(ctx: Ctx, manifest, member, sel, spec) -> Dict[str, bytes]:
    files = {f"approved_spec/{k}": v for k, v in spec.items()}
    files["eval_keys_2026_jan_apr.csv"] = csv_bytes(sel["new_keys"])
    files["fit_valid_keys.csv"] = csv_bytes(sel["keys"][sel["fit_valid"]].reset_index(drop=True))
    files["coverage_by_month_2026.csv"] = csv_bytes(coverage_table(ctx, sel))
    if member is not None:
        files["som_membership_area_ids.csv"] = csv_bytes(pd.DataFrame({"area_id": member["area_ids"]}))
    return files


def original_evidence(ctx: Ctx) -> dict:
    if ctx.scope == "global":
        rel = {"verification_summary": "verification/verification_summary.json", "metrics": "verification/all_metrics_long.csv",
               "global_deltas": "verification/global_deltas.csv", "regional_deltas": "verification/regional_deltas.csv"}
    else:
        rel = {"verification": "verification/verification.json", "metrics": "report/som_metrics_long.csv",
               "deltas": "report/som_oracle_minus_baseline_deltas.csv", "local_manifest": f"inputs/{som.HIST_VERSION}_manifest.json"}
    if ctx.scope == "global":
        rel["artifact_inventory"] = "verification/artifact_inventory.csv"
    out = {}
    for key, r in rel.items():
        p = ctx.original_results / r
        if not p.exists():
            raise LocalError(f"original evidence {p} missing")
        out[key] = {"path": str(p), "sha256": sha(p)}
    if ctx.scope == "SOM" and out["local_manifest"]["sha256"] != ORIGINAL_SOM_MANIFEST_SHA256 and ctx.contract_sha256 is not None:
        raise LocalError("original Somalia-local manifest differs from the accepted identity")
    return out


def accepted_inventory(ctx: Ctx, evidence: Mapping[str, dict]) -> Dict[str, str]:
    """The ORIGINAL accepted verification and its saved artifact inventory (path -> sha256); prior verification must have passed."""
    if ctx.scope == "global":
        summary = json.loads(Path(evidence["verification_summary"]["path"]).read_text())
        passed = summary.get("passed") is True and summary.get("batches") == 28 and summary.get("models_reloaded") == 112 and not summary.get("problems")
        inv = pd.read_csv(evidence["artifact_inventory"]["path"], keep_default_na=False, na_values=[""])
        if (inv["recorded_sha256"].notna() & (inv["recorded_sha256"] != inv["current_sha256"])).any():
            raise LocalError("original accepted inventory records a hash mismatch")
        table = dict(zip(inv["path"], inv["current_sha256"]))
    else:
        summary = json.loads(Path(evidence["verification"]["path"]).read_text())
        checks = summary.get("checks", {})
        passed = summary.get("passed") is True and checks.get("batches") == 28 and checks.get("models_reloaded") == 112 and not summary.get("problems")
        inv = pd.DataFrame(summary.get("inventory", []))
        table = dict(zip(inv["path"], inv["sha256"])) if len(inv) else {}
    if not passed:
        raise LocalError("original accepted verification did not pass 28 batches / 112 models")
    if not table or len(table) != len(inv):
        raise LocalError("original accepted inventory is empty or has duplicate paths")
    return table


def prepare(ctx: Ctx, write: bool) -> dict:
    manifest = parent_manifest(ctx)
    member = membership(ctx)
    spec = spec_files(ctx)
    expected = expected_runs(ctx, spec)
    sel = selection(ctx, manifest, member)
    evidence = original_evidence(ctx)
    inventory = accepted_inventory(ctx, evidence)
    for rid, exp in expected.items():
        if int(exp["eval_rows"]) != sel["summary"]["new_eval_rows"] or int(exp["eval_areas"]) != sel["summary"]["new_eval_areas"]:
            raise LocalError(f"{rid}: 2026 evaluation set differs from the approved expected runs")
    files = extension_files(ctx, manifest, member, sel, spec)
    inputs_dir = manifest_path(ctx).parent
    local = {
        "version": ctx.version, "status": "COMPLETE", "scope": ctx.scope, "model_scope": MODEL_SCOPE[ctx.scope],
        "parent": {"manifest": {"path": str(ctx.parent_manifest), "sha256": sha(ctx.parent_manifest)}, "model_contract_version": cpf.VERSION,
                   "cohort": {k: manifest["cohort"][k] for k in ("path", "sha256")}},
        "membership": None if member is None else {k: member[k] for k in ("path", "sha256", "column", "value", "n_areas", "area_ids_sha256")},
        "region_map": {"path": str(ctx.region_map), "sha256": sha(ctx.region_map)},
        "original": {"results_root": str(ctx.original_results), "evidence": evidence, "accepted_inventory_entries": len(inventory), "reused_years": list(OLD_YEARS),
                     "eval_keys_sha256": ctx.original_eval_sha256},
        "selection": sel["summary"],
        "runs": {rid: {"arm": a, "horizon": h, "block_year": NEW_YEAR,
                       "feature_count": len(manifest["horizons"][str(h)]["arms"][a]["features"]),
                       "feature_sha256": manifest["horizons"][str(h)]["arms"][a]["feature_sha256"],
                       "expected": {k: (int(v) if isinstance(v, (int, np.integer)) else v) for k, v in expected[rid].items()}}
                 for rid, (a, h) in zip([run_id(a, h) for a, h in RUNS], RUNS)},
        "periods": {p: list(ys) for p, ys in PERIOD_YEARS.items()}, "main_pooled_period": MAIN_POOLED, "original_pooled_period": ORIGINAL_POOLED,
        "partial_year": "2026 holds January-April only (no 2026 fitting labels)",
        "files": {name: {"path": str(inputs_dir / name), "sha256": sha_bytes(data), "bytes": len(data)} for name, data in sorted(files.items())},
        "local_code": {"script": str(ctx.script), "sha256": sha(ctx.script)},
        "reused_helpers_sha256": {"run_somalia_local_compact_test.py": sha(PROJECT_ROOT / "scripts/modeling/run_somalia_local_compact_test.py")},
        "params": dict(PARAMS), "frozen_configs_sha256": dict(cpf.FROZEN_CONFIG_SHA256), "frozen_runtime": dict(cpf.FROZEN_RUNTIME),
    }
    data = canonical_json(local)
    mpath = manifest_path(ctx)
    if write:
        assert_new_root(ctx.results)
        for name, payload in files.items():
            write_once(inputs_dir / name, payload)
        write_once(mpath, data)
    elif mpath.exists() and mpath.read_bytes() != data:
        raise LocalError(f"{mpath} exists with different bytes (spec/code/parent/selection changed); use a new root")
    return {"parent": manifest, "membership": member, "spec": spec, "expected": expected, "selection": sel, "local": local,
            "path": mpath, "sha256": sha_bytes(data), "inventory": inventory}


def run_args(ctx: Ctx, arm: str, horizon: int) -> argparse.Namespace:
    """The original suite's origin-safe CLI arguments (global parent gate; no country scope)."""
    return argparse.Namespace(
        protocol="origin-safe", origin_manifest=str(ctx.parent_manifest), horizon=horizon, arm=arm, out_dir=str(run_dir(ctx, arm, horizon)),
        seed=PARAMS["seed"], half_life_months=PARAMS["half_life_months"], phase_threshold=PARAMS["phase_threshold"], n_jobs=PARAMS["n_jobs"],
        country_iso3=None, region_scope=0, country_name=None, enable_shap=False, add_identifier_features=False, dataset=None,
        dataset_key=None, sample_rows=None, block_years=None, dry_run=False)


def localize(ctx: Ctx, prep: Mapping[str, object], inputs: Mapping[str, object], arm: str, horizon: int) -> dict:
    """Copied mapping after the parent gate: 2026 Jan-Apr evaluation mask, scope fitting mask, extension fingerprint."""
    sel = prep["selection"]
    data = inputs["data"]
    if not data[KEYS].reset_index(drop=True).equals(sel["keys"]):
        raise LocalError(f"{run_id(arm, horizon)}: dataset keys differ from the frozen cohort rows")
    parent_valid = np.asarray(inputs["share_valid"], dtype=bool)
    if not np.array_equal(parent_valid & sel["inscope"], sel["fit_valid"]):
        raise LocalError(f"{run_id(arm, horizon)}: parent share validity differs from the cohort selection")
    if not np.array_equal(np.asarray(inputs["eval_key"], dtype=bool) & sel["inscope"], sel["old_eval"]):
        raise LocalError(f"{run_id(arm, horizon)}: parent evaluation mask differs from the original keys")
    features = list(inputs["features"])
    frozen = None if ctx.frozen_feature_sha256 is None else ctx.frozen_feature_sha256[(arm, horizon)]
    want = prep["local"]["runs"][run_id(arm, horizon)]
    if osf.list_sha256(features) != want["feature_sha256"] or (frozen and want["feature_sha256"] != frozen) or len(features) != int(want["expected"]["feature_count"]):
        raise LocalError(f"{run_id(arm, horizon)}: fitted schema differs from the inherited contract")
    original_fp = ctx.original_fingerprint(inputs, arm, horizon)
    payload = {"extension_version": ctx.version, "scope": ctx.scope, "model_scope": MODEL_SCOPE[ctx.scope], "arm": arm, "horizon": int(horizon),
               "block_year": NEW_YEAR, "extension_manifest_sha256": prep["sha256"], "parent_fingerprint": inputs["fingerprint"],
               "parent_fingerprint_payload": inputs["fingerprint_payload"], "original_run_fingerprint": original_fp,
               "new_eval_keys_sha256": sel["summary"]["new_eval_keys_sha256"], "fit_valid_keys_sha256": sel["summary"]["fit_valid_keys_sha256"],
               "membership_sha256": None if prep["membership"] is None else prep["membership"]["area_ids_sha256"],
               "region_map_sha256": prep["local"]["region_map"]["sha256"], "script_sha256": sha(ctx.script), "params": dict(PARAMS)}
    fingerprint = digest(payload)
    if fingerprint in (original_fp, inputs["fingerprint"]):
        raise LocalError("extension fingerprint collides with an original fingerprint")
    return dict(inputs, share_valid=sel["fit_valid"].copy(), eval_key=sel["new_eval"].copy(), fingerprint=fingerprint,
                fingerprint_payload=payload, original_fingerprint=original_fp)


def expected_fit(data: pd.DataFrame, fit_valid: np.ndarray, year: int, horizon: int) -> Tuple[pd.DataFrame, np.ndarray]:
    ords = data["year"].to_numpy() * 12 + data["month"].to_numpy() - 1
    mask = fit_valid & (ords <= year * 12 - max(horizon, 1))
    return data.loc[mask, KEYS].reset_index(drop=True), ords[mask]


def pre_fit_checks(ctx: Ctx, prep, local: Mapping[str, object], arm: str, horizon: int) -> dict:
    """Complete expected 2026 fitting set (counts/areas/no 2026 label) and evaluation set before any fit."""
    exp = prep["expected"][run_id(arm, horizon)]
    fit, ords = expected_fit(local["data"], local["share_valid"], NEW_YEAR, horizon)
    origin, cutoff = NEW_YEAR * 12 - horizon, NEW_YEAR * 12 - max(horizon, 1)
    got = {"fit_rows": len(fit), "fit_areas": int(fit["area_id"].nunique()), "fit_origin_month": ym(origin), "fit_label_cutoff_month": ym(cutoff),
           "fit_max_label_month": ym(ords.max()), "fit_keys_sha256": osf.keys_sha256(fit),
           "eval_rows": int(local["eval_key"].sum()), "feature_count": len(local["features"])}
    want = {k: (int(exp[k]) if k not in ("fit_origin_month", "fit_label_cutoff_month") else exp[k])
            for k in ("fit_rows", "fit_areas", "fit_origin_month", "fit_label_cutoff_month", "eval_rows", "feature_count")}
    if {k: got[k] for k in want} != want or ords.max() > cutoff or (ords >= NEW_YEAR * 12).any():
        raise LocalError(f"{run_id(arm, horizon)}: 2026 fitting/evaluation set {got} differs from the approved {want}")
    return got


# --------------------------------------------------------------------------- original 2022-2025 import checks


def check_original_run(ctx: Ctx, prep, local: Mapping[str, object], arm: str, horizon: int, problems: List[str]) -> Optional[dict]:
    """Rehash and key-check every original batch; inspect all 16 booster schemas; return reused predictions and lineage."""
    import xgboost as xgb

    rid = run_id(arm, horizon)
    odir = original_run_dir(ctx, arm, horizon)
    meta_path = odir / "run_metadata.json"
    if not meta_path.exists():
        problems.append(f"{rid}: original run_metadata.json missing")
        return None
    meta = json.loads(meta_path.read_text())
    ofp = local["original_fingerprint"]
    features = list(local["features"])
    if meta.get("status") != "COMPLETE" or meta.get("fingerprint") != ofp or meta.get("features") != features \
            or sorted(b["block_year"] for b in meta.get("batches", [])) != list(OLD_YEARS):
        problems.append(f"{rid}: original run is not COMPLETE with the recomputed original fingerprint/schema/years")
        return None
    if ctx.scope == "SOM" and meta.get("local_version") != som.HIST_VERSION:
        problems.append(f"{rid}: original Somalia run lacks its local version identity")
    if any(meta.get(k) != v for k, v in PARAMS.items()):
        problems.append(f"{rid}: original fixed parameters {{{', '.join(f'{k}={meta.get(k)}' for k in PARAMS)}}} differ from {PARAMS}")
    inv = prep["inventory"]
    inv_name = "artifact_inventory" if ctx.scope == "global" else "verification"
    inv_ref = prep["local"]["original"]["evidence"][inv_name]
    required = [meta_path] + [odir / "batches" / str(y) / n for y in OLD_YEARS for n in (*osf.REQUIRED_BATCH_ARTIFACTS, "batch_record.json")]
    if ctx.scope == "SOM":  # the local accepted inventory also covers the published predictions and run metrics
        required += [odir / "predictions" / f"predictions_{y}.csv" for y in OLD_YEARS] + [odir / "metrics" / "metrics_overall.csv"]
    uncovered = [str(p) for p in required if str(p) not in inv]
    drifted = [str(p) for p in required if str(p) in inv and (not p.exists() or sha(p) != inv[str(p)])]
    if uncovered or drifted:
        problems.append(f"{rid}: original artifacts not reconciled with the accepted inventory (uncovered {uncovered[:3]}, changed {drifted[:3]})")
        return None
    data = local["data"]
    sel = prep["selection"]
    targets = som.independent_targets(data)
    position = pd.MultiIndex.from_frame(data[KEYS])
    frames, lineage, schemas = [], {}, 0
    for record in meta["batches"]:
        year = record["block_year"]
        bdir = odir / "batches" / str(year)
        try:
            disk = runner.verify_batch(bdir, ofp)  # complete artifact set, original fingerprint, every artifact hash
        except ValueError as exc:
            problems.append(f"{rid} {year}: {exc}")
            continue
        if disk is None or disk != json.loads(json.dumps(record)):
            problems.append(f"{rid} {year}: original batch record missing or differs from the run metadata")
            continue
        origin, cutoff = year * 12 - horizon, year * 12 - max(horizon, 1)
        fk = pd.read_csv(bdir / "fit_keys.csv.gz", float_precision="round_trip")
        want_fit, wards = expected_fit(data, sel["fit_valid"], year, horizon)
        ford = fk["year"].to_numpy() * 12 + fk["month"].to_numpy() - 1
        if not fk[KEYS].equals(want_fit) or not np.array_equal(fk["age_months"].to_numpy(), origin - ford) \
                or not np.allclose(fk["sample_weight"].to_numpy(), 0.5 ** ((origin - ford) / 24.0), rtol=0, atol=1e-15) or ford.max() > cutoff:
            problems.append(f"{rid} {year}: original fit keys/cutoff/scope/ages/weights differ from the complete expected set")
        pred = pd.read_csv(bdir / "predictions.csv", float_precision="round_trip")
        want_eval = sel["old_keys"][sel["old_keys"]["year"] == year].reset_index(drop=True)
        if not pred[KEYS].equals(want_eval):
            problems.append(f"{rid} {year}: original evaluation keys differ from the pinned original keys")
            continue
        rows = position.get_indexer(pd.MultiIndex.from_frame(pred[KEYS]))
        if not np.array_equal(data["overall_phase"].to_numpy(dtype=float)[rows], pred["overall_phase"].to_numpy(dtype=float)) \
                or not som._close(targets[rows], pred[list(osf.CUMULATIVE_TARGETS)].to_numpy(), 1e-12) \
                or not np.array_equal(legacy.classes(pred, PARAMS["phase_threshold"]), pred["overall_phase_pred"].to_numpy()):
            problems.append(f"{rid} {year}: original truth/normalized targets/class rule differ")
        published = pd.read_csv(odir / "predictions" / f"predictions_{year}.csv", float_precision="round_trip")
        if not published.equals(pred):
            problems.append(f"{rid} {year}: published original predictions differ from the batch predictions")
        for target in osf.CUMULATIVE_TARGETS:
            booster = xgb.Booster()
            booster.load_model(str(bdir / f"model_{target}.ubj"))
            schemas += 1
            if list(booster.feature_names) != features:
                problems.append(f"{rid} {year} {target}: original booster feature order differs")
        frames.append(pred)
        lineage[year] = {"source": "original (reused, not refit)", "batch_dir": str(bdir), "fingerprint": ofp,
                         "accepted_inventory": {"path": inv_ref["path"], "sha256": inv_ref["sha256"],
                                                "entries_checked": sum(1 for p in required if f"/batches/{year}/" in str(p))},
                         "batch_record_sha256": sha(bdir / "batch_record.json"), "artifacts": dict(disk["artifacts"]),
                         "published_predictions": {"path": str(odir / "predictions" / f"predictions_{year}.csv"),
                                                   "sha256": sha(odir / "predictions" / f"predictions_{year}.csv")}}
    if len(frames) != len(OLD_YEARS):
        return None
    return {"predictions": pd.concat(frames, ignore_index=True), "lineage": lineage, "schemas": schemas, "fingerprint": ofp,
            "run_metadata_sha256": sha(meta_path), "accepted_inventory_checked": len(required)}


# --------------------------------------------------------------------------- training


def train(ctx: Ctx) -> dict:
    som.runtime_identity()
    assert_new_root(ctx.results)
    assert_new_root(ctx.reports)
    snap = ctx.results / "preflight" / "protected_inventory_before.csv"
    if not snap.exists():
        write_once(snap, csv_bytes(protected_inventory(ctx)))
    prep = prepare(ctx, write=True)
    hp, hp3 = ctx.hyperparameters()
    done = []
    for arm, horizon in RUNS:
        rid = run_id(arm, horizon)
        args = run_args(ctx, arm, horizon)
        local = localize(ctx, prep, ctx.load_inputs(args), arm, horizon)
        expected = pre_fit_checks(ctx, prep, local, arm, horizon)
        problems: List[str] = []
        original = check_original_run(ctx, prep, local, arm, horizon, problems)
        if problems or original is None:
            raise LocalError(f"{rid}: original 2022-2025 artifacts failed the import checks: {problems[:5]}")
        rdir = run_dir(ctx, arm, horizon)
        meta_path = rdir / "run_metadata.json"
        if meta_path.exists() and json.loads(meta_path.read_text()).get("fingerprint") != local["fingerprint"]:
            raise LocalError(f"{rdir} holds a run with a different extension fingerprint; refusing to mix runs")
        bdir = rdir / "batches" / str(NEW_YEAR)
        if bdir.exists() and any(bdir.iterdir()) and not (bdir / "batch_record.json").exists():
            raise LocalError(f"{bdir} has files but no batch record; refusing to resume or overwrite an incomplete batch (diagnostics preserved)")
        record = runner.verify_batch(bdir, local["fingerprint"])
        if record is None:
            record = runner.run_origin_batch(local, args, NEW_YEAR, hp, hp3, bdir)
            log(f"{ctx.scope} {rid} 2026: fit {record['fit_rows']} rows (labels <= {record['fit_label_cutoff_month']}, max {record['fit_max_label_month']}), "
                f"eval {record['eval_rows']}, {record['batch_seconds']} s, rss {record['peak_rss_mb']} MB")
        else:
            log(f"{ctx.scope} {rid} 2026: verified existing batch")
        if record["fit_rows"] != expected["fit_rows"] or record["fit_keys_sha256"] != expected["fit_keys_sha256"] \
                or record["eval_rows"] != expected["eval_rows"] or record["eval_keys_sha256"] != osf.keys_sha256(prep["selection"]["new_keys"]) \
                or record["fit_label_cutoff_month"] != expected["fit_label_cutoff_month"] or record["fit_origin_month"] != expected["fit_origin_month"]:
            raise LocalError(f"{rid}: 2026 batch keys/anchors differ from the complete expected sets")
        write_combined(ctx, prep, local, original, arm, horizon, record, expected)
        done.append({"run_id": rid, "fingerprint": local["fingerprint"], "original_fingerprint": original["fingerprint"], **expected})
        del local
    return {"scope": ctx.scope, "version": ctx.version, "runs": done}


def write_combined(ctx: Ctx, prep, local, original, arm: str, horizon: int, record: dict, expected: dict) -> None:
    rdir = run_dir(ctx, arm, horizon)
    bdir = rdir / "batches" / str(NEW_YEAR)
    new = pd.read_csv(bdir / "predictions.csv", float_precision="round_trip")
    old = original["predictions"]
    if list(new.columns) != list(old.columns):
        raise LocalError("2026 prediction columns differ from the original prediction columns")
    combined = pd.concat([old, new], ignore_index=True).sort_values(KEYS, kind="mergesort").reset_index(drop=True)
    want = pd.concat([prep["selection"]["old_keys"], prep["selection"]["new_keys"]]).sort_values(KEYS, kind="mergesort").reset_index(drop=True)
    if combined[KEYS].duplicated().any() or not combined[KEYS].equals(want):
        raise LocalError("combined predictions do not cover the original and 2026 keys exactly once")
    (rdir / "predictions").mkdir(parents=True, exist_ok=True)
    pred_path = rdir / "predictions" / "predictions_2022_2026.csv"
    pred_path.write_bytes(csv_bytes(combined))
    lineage = dict(original["lineage"])
    lineage[NEW_YEAR] = {"source": "extension (fitted here)", "batch_dir": str(bdir), "fingerprint": local["fingerprint"],
                         "batch_record_sha256": sha(bdir / "batch_record.json"), "artifacts": dict(record["artifacts"])}
    meta = {"protocol": "origin-safe annual block extension", "status": "COMPLETE", "extension_version": ctx.version, "scope": ctx.scope,
            "model_scope": MODEL_SCOPE[ctx.scope], "arm": arm, "horizon": horizon, "fingerprint": local["fingerprint"],
            "fingerprint_payload": local["fingerprint_payload"], "original_fingerprint": original["fingerprint"],
            "original_run": {"path": str(original_run_dir(ctx, arm, horizon)), "run_metadata_sha256": original["run_metadata_sha256"]},
            "extension_manifest": {"path": str(prep["path"]), "sha256": prep["sha256"]},
            "features": list(local["features"]), "feature_count": len(local["features"]), **PARAMS,
            "reused_years": list(OLD_YEARS), "fitted_here_years": [NEW_YEAR], "sources_by_year": {str(y): v for y, v in lineage.items()},
            "new_batch": {k: record[k] for k in ("fit_rows", "fit_origin_month", "fit_label_cutoff_month", "fit_max_label_month", "fit_keys_sha256",
                                                 "eval_rows", "eval_keys_sha256", "fit_seconds", "batch_seconds", "peak_rss_mb")},
            "predictions": {"path": str(pred_path), "sha256": sha(pred_path), "rows": len(combined),
                            "rows_by_year": {int(y): int(n) for y, n in combined["year"].value_counts().sort_index().items()}},
            "written_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    write_json(rdir / "run_metadata.json", meta)


# --------------------------------------------------------------------------- metrics, reports and codebook


def metric_rows(ctx: Ctx, pred: pd.DataFrame, arm: str, horizon: int, region_names: Mapping[int, str]) -> List[dict]:
    """Explicit periods (five annual, two pooled) x scope groups; empty groups kept with canonical undefined reasons."""
    groups = [("global", None, pred)] if ctx.scope == "global" else [(ISO3, None, pred)]
    if ctx.scope == "global":
        groups += [("region", r, pred[pred["region"] == r]) for r in rpm.REGIONS]
    rows = []
    for scope, region, group in groups:
        for period, years in PERIOD_YEARS.items():
            part = group[group["year"].isin(years)]
            result = osf.origin_metrics(part, scope if region is None else f"region{region}", period)
            sup = rpm.support(part)
            for metric in osf.ORIGIN_METRICS:
                value = result[metric]
                row = {"run_id": run_id(arm, horizon), "arm": arm, "horizon": horizon, "scope": scope, "region": region}
                if ctx.scope == "global":
                    row["region_name"] = None if region is None else region_names[int(region)]
                row.update({"period": period, "metric": metric, "value": value["value"], "status": value["status"], "reason": value["reason"], **sup})
                rows.append(row)
    return rows


def region_names(ctx: Ctx, prep) -> Dict[int, str]:
    if ctx.scope != "global":
        return {}
    summary = json.loads(Path(prep["local"]["original"]["evidence"]["verification_summary"]["path"]).read_text())
    names = {int(k): v for k, v in summary["region_name_annotation"]["region_names"].items()}
    if sorted(names) != list(rpm.REGIONS):
        raise LocalError("original region-name annotation does not name regions 0..8")
    return names


def combined_predictions(ctx: Ctx, arm: str, horizon: int) -> pd.DataFrame:
    meta = json.loads((run_dir(ctx, arm, horizon) / "run_metadata.json").read_text())
    if meta.get("status") != "COMPLETE" or meta.get("extension_version") != ctx.version:
        raise LocalError(f"{run_id(arm, horizon)}: extension run is not COMPLETE")
    path = Path(meta["predictions"]["path"])
    if sha(path) != meta["predictions"]["sha256"]:
        raise LocalError(f"{path} changed since its run metadata")
    return pd.read_csv(path, float_precision="round_trip")


def delta_table(ctx: Ctx, metrics: pd.DataFrame, names: Mapping[int, str]) -> pd.DataFrame:
    if ctx.scope == "SOM":
        return som.hist_delta_table(metrics)  # oracle - baseline at H3/H6/H12 plus the shared-H0 presentation
    deltas = pd.DataFrame(rpm.delta_rows(metrics, cpf.ORACLE_ARM, cpf.BASELINE_ARM, ORACLE_H))
    deltas.insert(3, "region_name", [None if pd.isna(r) else names[int(r)] for r in deltas["region"]])
    return deltas


def report(ctx: Ctx) -> dict:
    prep = prepare(ctx, write=False)
    if not prep["path"].exists():
        raise LocalError("extension manifest missing; run --approve-training first")
    names = region_names(ctx, prep)
    regions = region_series(ctx) if ctx.scope == "global" else None
    rows = []
    for arm, horizon in RUNS:
        pred = combined_predictions(ctx, arm, horizon)
        if regions is not None:
            pred = rpm.assign_regions(pred, regions)
        rows += metric_rows(ctx, pred, arm, horizon, names)
    metrics = pd.DataFrame(rows)
    deltas = delta_table(ctx, metrics, names)
    out_dir = ctx.results / "report"
    written = {}
    coverage = coverage_table(ctx, prep["selection"])
    if ctx.scope == "global":
        undefined = metrics[metrics["value"].isna()].groupby(["scope", "metric", "reason"]).size().rename("cells").reset_index()
        tables = {"all_metrics_long.csv": metrics, "global_metrics.csv": metrics[metrics["scope"] == "global"],
                  "regional_metrics.csv": metrics[metrics["scope"] == "region"], "global_deltas.csv": deltas[deltas["scope"] == "global"],
                  "regional_deltas.csv": deltas[deltas["scope"] == "region"], "undefined_reasons.csv": undefined, "coverage_by_month.csv": coverage}
    else:
        undefined = metrics[metrics["value"].isna()].groupby(["arm", "horizon", "period", "metric", "reason"]).size().rename("cells").reset_index()
        tables = {"som_metrics_long.csv": metrics, "som_oracle_minus_baseline_deltas.csv": deltas, "som_undefined_reasons.csv": undefined,
                  "coverage_by_month.csv": coverage}
    for name, table in tables.items():
        written[name] = save_table(table, out_dir / name)
    fitted = fitted_lists(ctx)
    codebook = write_codebook(ctx, prep, fitted)
    md = write_markdown(ctx, prep, metrics, deltas, coverage)
    meta = {"version": ctx.version, "scope": ctx.scope, "model_scope": MODEL_SCOPE[ctx.scope], "status": "verification_pending",
            "extension_manifest": {"path": str(prep["path"]), "sha256": prep["sha256"]},
            "runs": {run_id(a, h): {"extension_run": str(run_dir(ctx, a, h)), "original_run": str(original_run_dir(ctx, a, h))} for a, h in RUNS},
            "periods": {p: list(y) for p, y in PERIOD_YEARS.items()}, "main_pooled_period": MAIN_POOLED, "original_pooled_period": ORIGINAL_POOLED,
            "partial_year": "2026 = January-April only", "month_support": prep["selection"]["summary"]["month_support_rows"],
            "metrics": list(osf.ORIGIN_METRICS), "evaluation_weights": "rows; pooled metrics recomputed from pooled rows",
            "contrast": f"{cpf.ORACLE_ARM} - {cpf.BASELINE_ARM} at H3/H6/H12; H0 shared",
            "models": {"reused_boosters": 112, "new_boosters": 28, "referenced_boosters": 140},
            "reused_years": list(OLD_YEARS), "fitted_here_years": [NEW_YEAR], "outputs": written, "codebook": codebook,
            "report_md": {"path": str(md), "sha256": sha(md)}, "bootstrap": "not run (out of scope)"}
    if ctx.scope == "global":
        meta["regions"] = {"source": prep["local"]["region_map"], "names": {str(k): v for k, v in names.items()},
                           "note": "region scores come from the global fits; no regional fitting"}
    write_json(out_dir / "comparison_metadata.json", meta)
    return meta


def fitted_lists(ctx: Ctx) -> Dict[str, dict]:
    """Actual fitted order of all 140 referenced boosters (112 reused + 28 new) per scope."""
    import xgboost as xgb

    out = {}
    for arm, horizon in RUNS:
        meta = json.loads((run_dir(ctx, arm, horizon) / "run_metadata.json").read_text())
        n = 0
        for year, src in meta["sources_by_year"].items():
            for target in osf.CUMULATIVE_TARGETS:
                booster = xgb.Booster()
                booster.load_model(str(Path(src["batch_dir"]) / f"model_{target}.ubj"))
                if list(booster.feature_names) != meta["features"]:
                    raise LocalError(f"{run_id(arm, horizon)} {year} {target}: booster feature order differs from the run schema")
                n += 1
        if n != 20:
            raise LocalError(f"{run_id(arm, horizon)}: {n} referenced boosters, not 20")
        out[run_id(arm, horizon)] = {"features": list(meta["features"]), "meta": meta}
    return out


def write_codebook(ctx: Ctx, prep, fitted: Mapping[str, dict]) -> dict:
    out_dir = ctx.reports / "model_run_codebook"
    out_dir.mkdir(parents=True, exist_ok=True)
    contract = Path(prep["parent"]["contract"]["files"]["expected_feature_contract.csv"]["path"])
    with open(contract, encoding="utf-8-sig", newline="") as fh:
        expected_rows = list(csv.DictReader(fh))
    runs = [run_id(a, h) for a, h in RUNS]
    positions = {r: {f: i + 1 for i, f in enumerate(fitted[r]["features"])} for r in runs}
    union = list(dict.fromkeys(f for r in runs for f in fitted[r]["features"]))
    keep = ["predictor", "group", "description", "unit", "source", "time_relative_to_origin", "formula", "missing_semantics", "input_type"]
    tail = ["horizons_months", "family", "source_variable", "base_source_definition", "definition_evidence"]
    by_name = {r["predictor"]: r for r in expected_rows}
    rows, comparison = [], []
    for pos, name in enumerate(union, 1):
        base = by_name.get(name)
        if base is None:
            raise LocalError(f"fitted feature {name} has no contract row")
        row = {"position": pos, **{k: base[k] for k in keep}}
        for r in runs:
            col = r.replace("/", "_")
            row[col] = "true" if name in positions[r] else "false"
            row[f"{col}_expanded_count"] = 1 if name in positions[r] else 0
        act = {r: positions[r][name] for r in runs if name in positions[r]}
        row["actual_model_columns"] = json.dumps([name])
        row["actual_model_positions"] = json.dumps(act, separators=(",", ":"))
        row.update({k: base[k] for k in tail})
        row["limitations"] = som.clean_limitations(base["limitations"])
        row["model_scope"] = MODEL_SCOPE[ctx.scope]
        row["fit_status"] = f"{FIT_STATUS_BASE}; verification_pending"
        rows.append(row)
        exp = json.loads(base["expected_model_positions"])
        comparison.append({"predictor": name, "expected_model_positions": json.dumps(exp, sort_keys=True),
                           "actual_model_positions": json.dumps(act, sort_keys=True), "match": exp == act})
    for name in sorted(set(by_name) - set(union)):
        comparison.append({"predictor": name, "expected_model_positions": by_name[name]["expected_model_positions"], "actual_model_positions": "{}", "match": False})
    comp = pd.DataFrame(comparison)
    if not comp["match"].all() or len(union) != len(expected_rows):
        raise LocalError(f"actual fitted inputs differ from the contract for {int((~comp['match']).sum())} predictors")
    path = out_dir / CODEBOOK_NAME[ctx.scope]
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")
    comp.to_csv(out_dir / "expected_vs_actual_inputs.csv", index=False)
    index = []
    for r in runs:
        meta = fitted[r]["meta"]
        a, h = r.split("/")
        index.append({"run_id": r, "arm": a, "horizon_months": int(h[:-1]), "actual_feature_count": len(fitted[r]["features"]),
                      "actual_feature_sha256": osf.list_sha256(fitted[r]["features"]),
                      "expected_feature_sha256": prep["local"]["runs"][r]["feature_sha256"],
                      "reused_years": "|".join(map(str, meta["reused_years"])), "fitted_here_years": "|".join(map(str, meta["fitted_here_years"])),
                      "reused_boosters": 16, "new_boosters": 4, "original_fingerprint": meta["original_fingerprint"],
                      "extension_fingerprint": meta["fingerprint"], "original_run_path": meta["original_run"]["path"],
                      "extension_run_path": str(run_dir(ctx, a, int(h[:-1])))})
    index = pd.DataFrame(index)
    index["match"] = index["actual_feature_sha256"] == index["expected_feature_sha256"]
    index.to_csv(out_dir / "model_run_index.csv", index=False)
    if not index["match"].all():
        raise LocalError("a run's fitted feature hash differs from the inherited contract")
    return {"codebook": str(path), "sha256": sha(path), "rows": len(rows), "expected_rows": len(expected_rows),
            "expected_vs_actual": {"path": str(out_dir / "expected_vs_actual_inputs.csv"), "sha256": sha(out_dir / "expected_vs_actual_inputs.csv")},
            "model_run_index": {"path": str(out_dir / "model_run_index.csv"), "sha256": sha(out_dir / "model_run_index.csv")}}


FIT_STATUS_BASE = "actual_fitted_order_checked_140_boosters (112 reused 2022-2025 + 28 fitted 2026)"
STATUS_LINE = {
    "verification_pending": "**Status: verification_pending** — values below are computed from saved unrounded predictions; acceptance is recorded only "
                            "after the independent verifier passes (`verification/verification_summary.json`).",
    "verified": "**Status: verified** — the independent executor verifier passed for every new model, metric, difference, coverage and inventory "
                "check (`verification/verification_summary.json`); coordinator acceptance is recorded separately.",
    "verification_failed": "**Status: verification_failed** — the independent verifier reported problems (`verification/verification_summary.json`); "
                           "the values below are unverified diagnostics.",
}


def finalize_reporting(ctx: Ctx, status: str) -> dict:
    """After a verification run: set the truthful status in report.md, the codebook and comparison metadata, refreshing only their hashes."""
    rep, cb_path = ctx.results / "report", ctx.reports / "model_run_codebook" / CODEBOOK_NAME[ctx.scope]
    meta_path, md = rep / "comparison_metadata.json", ctx.reports / "report.md"
    if not meta_path.exists():
        return {"status": status, "updated": []}
    updated = []
    meta = json.loads(meta_path.read_text())
    if md.exists():
        lines = md.read_text(encoding="utf-8").split(chr(10))
        hit = [i for i, line in enumerate(lines) if line.startswith("**Status: ")]
        if hit:
            lines[hit[0]] = STATUS_LINE[status]
            md.write_text(chr(10).join(lines), encoding="utf-8")
            meta["report_md"] = {"path": str(md), "sha256": sha(md)}
            updated.append(str(md))
    if cb_path.exists():
        book = pd.read_csv(cb_path, encoding="utf-8-sig", keep_default_na=False, dtype=str)
        book["fit_status"] = f"{FIT_STATUS_BASE}; {status}"
        book.to_csv(cb_path, index=False, encoding="utf-8-sig")
        meta.setdefault("codebook", {})["sha256"] = sha(cb_path)
        updated.append(str(cb_path))
    meta["status"] = status
    meta["verification"] = {"summary": str(ctx.results / "verification" / "verification_summary.json"), "status": status,
                            "finalized_utc": pd.Timestamp.now(tz="UTC").isoformat()}
    write_json(meta_path, meta)
    updated.append(str(meta_path))
    return {"status": status, "updated": updated, "report_md_sha256": meta.get("report_md", {}).get("sha256"),
            "codebook_sha256": meta.get("codebook", {}).get("sha256"), "comparison_metadata_sha256": sha(meta_path)}


def fmt(value, digits=4) -> str:
    return "undefined" if value is None or pd.isna(value) else f"{value:.{digits}f}"


def write_markdown(ctx: Ctx, prep, metrics: pd.DataFrame, deltas: pd.DataFrame, coverage: pd.DataFrame) -> Path:
    s = prep["selection"]["summary"]
    names = list(osf.ORIGIN_METRICS)
    head = "| arm | period | n | areas | obs 3+ | " + " | ".join(som.METRIC_LABELS[m] for m in names) + " |"
    sep = "|---|---|---:|---:|---:|" + "---:|" * len(names)
    top = metrics[metrics["scope"] == ("global" if ctx.scope == "global" else ISO3)]
    lines = [f"# {ctx.version}: compact historical evaluation extended to January-April 2026 ({MODEL_SCOPE[ctx.scope]})", "",
             STATUS_LINE["verification_pending"], "",
             f"- Scope: {ctx.scope}; model scope: {MODEL_SCOPE[ctx.scope]}"
             + (" (every model fitted on Somalia rows only; distinct from the global fits' region 7)." if ctx.scope == "SOM" else
                " (one global fit per run and year; region rows are scored from the global fits, not regional fits)."),
             f"- 2026 is a **partial year (January-April only)**: {s['new_eval_rows']} keys over {s['new_eval_areas']} areas; by month "
             + ", ".join(f"{m}: {n} rows" for m, n in s["month_support_rows"].items()) + ". No 2026 label is used for fitting "
             "(annual fit with labels <= Jan 2026 - max(H, 1)).",
             f"- Original 2022-2025 fits are reused after verification (112 boosters); only the 2026 block is fitted here (28 boosters). "
             f"Main pooled period `{MAIN_POOLED}` ({s['expanded_pooled_rows']} rows, sample dominated by the full 2022-2025 years); "
             f"original pooled period `{ORIGINAL_POOLED}` ({s['old_eval_rows']} rows).",
             "- The oracle arm uses realized weather at O+1..O+min(H,6) as a perfect forecast: it measures ideal weather information, not CDS skill.",
             "- Units: accuracies/precision/recall are row shares; MAE 3+ is a normalized population share; ordinal MAE in phase steps; differences are raw.", "",
             "## 2026 coverage by month", "", "| month | rows | areas | populated |", "|---:|---:|---:|---|"]
    lines += [f"| {r.month} | {r.rows} | {r.areas} | {r.populated} |" for r in coverage.itertuples()]
    lines.append("")
    for h in (0, 3, 6, 12):
        lines += [f"## {'Global' if ctx.scope == 'global' else 'Somalia (local fits)'}, H = {h} months", "", head, sep]
        part = top[top["horizon"] == h]
        for (arm, period), g in part.groupby(["arm", "period"], sort=False):
            g = g.set_index("metric")
            f0 = g.iloc[0]
            lines.append(f"| {arm} | {period} | {f0.n_rows} | {f0.n_areas} | {f0.observed_3plus} | " + " | ".join(fmt(g.loc[m, "value"]) for m in names) + " |")
        d = deltas[(deltas["horizon"] == h) & (deltas["scope"] == ("global" if ctx.scope == "global" else ISO3))]
        for period, g in d.groupby("period", sort=False):
            g = g.set_index("metric")
            label = "**oracle - baseline**" if h else "**shared H0 difference**"
            lines.append(f"| {label} | {period} | | | | " + " | ".join(fmt(g.loc[m, "delta"]) for m in names) + " |")
        lines.append("")
    if ctx.scope == "global":
        lines += ["## Regions 0-8", "", "Annual and pooled regional metrics, support counts, undefined reasons and differences are in "
                  "`report/regional_metrics.csv` and `report/regional_deltas.csv`; regions with no 2026 rows keep undefined 2026 cells.", ""]
    lines += ["## Limits", "", "- Single seed (42), one fit per annual block; point estimates without intervals; no bootstrap.",
              "- 2026 is January-April only and month-imbalanced" + (" (Somalia: almost entirely April)." if ctx.scope == "SOM" else "."),
              "- Calendar/source availability is the established retrospective proxy, not publication-vintage real-time availability.",
              "- Undefined metrics stay undefined with canonical reasons; empty groups are kept.", ""]
    path = ctx.reports / "report.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


# --------------------------------------------------------------------------- independent verification


def protected_inventory(ctx: Ctx) -> pd.DataFrame:
    rows = [{"role": role, "path": str(p), "bytes": p.stat().st_size, "sha256": sha(p)} for role, p in ctx.protected_paths()]
    return pd.DataFrame(rows, columns=["role", "path", "bytes", "sha256"])


def protected_check(ctx: Ctx, problems: List[str], checks: dict) -> None:
    snap = ctx.results / "preflight" / "protected_inventory_before.csv"
    if not snap.exists():
        problems.append("protected inventory snapshot missing")
        return
    before = pd.read_csv(snap, keep_default_na=False)
    if before.empty or list(before.columns) != ["role", "path", "bytes", "sha256"] or before["path"].duplicated().any():
        problems.append("protected inventory snapshot is empty, malformed or has duplicate paths")
        return
    listed = set(zip(before["role"], before["path"]))
    current = {(r, str(p)) for r, p in ctx.protected_paths()}
    missing, added = sorted(listed - current), sorted(current - listed)
    changed = [r.path for r in before.itertuples() if Path(r.path).exists() and sha(r.path) != r.sha256]
    if missing:
        problems.append(f"protected files missing/removed: {[p for _, p in missing][:5]}")
    if added:
        problems.append(f"protected locations gained files: {[p for _, p in added][:5]}")
    if changed:
        problems.append(f"protected files changed: {changed[:5]}")
    checks.update({"protected_files": len(before), "protected_changed": len(changed), "protected_missing": len(missing), "protected_added": len(added)})


def verify(ctx: Ctx) -> dict:
    import xgboost as xgb

    runtime = som.runtime_identity()
    problems: List[str] = []
    checks = {"new_batches": 0, "new_models_replayed": 0, "max_new_replay_abs_diff": 0.0, "schemas_inspected": 0, "original_batches_checked": 0,
              "metric_cells_replayed": 0, "delta_cells_replayed": 0, "original_parity_cells": 0}
    try:
        prep = prepare(ctx, write=False)
        if not prep["path"].exists() or sha(prep["path"]) != prep["sha256"]:
            problems.append("extension manifest missing or differs from the recomputed identity")
        for name, item in prep["local"]["files"].items():
            if not Path(item["path"]).exists() or sha(item["path"]) != item["sha256"]:
                problems.append(f"extension input {name} missing or changed")
        regions = region_series(ctx) if ctx.scope == "global" else None
        names = region_names(ctx, prep)
        preds = {}
        for arm, horizon in RUNS:
            rid = run_id(arm, horizon)
            local = localize(ctx, prep, ctx.load_inputs(run_args(ctx, arm, horizon)), arm, horizon)
            expected = pre_fit_checks(ctx, prep, local, arm, horizon)
            original = check_original_run(ctx, prep, local, arm, horizon, problems)
            if original is None:
                problems.append(f"{rid}: original import failed")
                continue
            checks["original_batches_checked"] += len(original["lineage"])
            checks["schemas_inspected"] += original["schemas"]
            rdir = run_dir(ctx, arm, horizon)
            meta_path = rdir / "run_metadata.json"
            if not meta_path.exists():
                problems.append(f"{rid}: extension run_metadata.json missing")
                continue
            meta = json.loads(meta_path.read_text())
            if meta.get("status") != "COMPLETE" or meta.get("fingerprint") != local["fingerprint"] or meta.get("original_fingerprint") != original["fingerprint"] \
                    or meta.get("reused_years") != list(OLD_YEARS) or meta.get("fitted_here_years") != [NEW_YEAR] or meta.get("features") != list(local["features"]):
                problems.append(f"{rid}: extension run metadata identity/lineage differs")
            for y in OLD_YEARS:
                src = meta.get("sources_by_year", {}).get(str(y), {})
                if src.get("fingerprint") != original["fingerprint"] or src.get("artifacts") != original["lineage"][y]["artifacts"]:
                    problems.append(f"{rid} {y}: recorded original lineage differs from the original batch")
            bdir = rdir / "batches" / str(NEW_YEAR)
            try:
                record = runner.verify_batch(bdir, local["fingerprint"])
            except ValueError as exc:
                problems.append(f"{rid} 2026: {exc}")
                continue
            if record is None:
                problems.append(f"{rid} 2026: no complete batch record")
                continue
            if sorted(p.name for p in bdir.iterdir()) != sorted([*record["artifacts"], "batch_record.json"]):
                problems.append(f"{rid} 2026: batch directory holds unrecorded files")
            fk = pd.read_csv(bdir / "fit_keys.csv.gz", float_precision="round_trip")
            want_fit, wards = expected_fit(local["data"], local["share_valid"], NEW_YEAR, horizon)
            origin = NEW_YEAR * 12 - horizon
            ford = fk["year"].to_numpy() * 12 + fk["month"].to_numpy() - 1
            if not fk[KEYS].equals(want_fit) or len(fk) != expected["fit_rows"] or (ford >= NEW_YEAR * 12).any() \
                    or not np.array_equal(fk["age_months"].to_numpy(), origin - ford) \
                    or not np.allclose(fk["sample_weight"].to_numpy(), 0.5 ** ((origin - ford) / 24.0), rtol=0, atol=1e-15):
                problems.append(f"{rid} 2026: fit keys/ages/weights are not the complete expected set without 2026 labels")
            data = local["data"]
            targets = som.independent_targets(data)
            position = pd.MultiIndex.from_frame(data[KEYS])
            frows = position.get_indexer(pd.MultiIndex.from_frame(fk[KEYS]))
            fitter = local["targets"][list(osf.CUMULATIVE_TARGETS)].to_numpy(dtype=float)
            if (frows < 0).any() or not som._close(fitter[frows], targets[frows], 1e-12):
                problems.append(f"{rid} 2026: fitter targets differ from the independent normalization")
            pred = pd.read_csv(bdir / "predictions.csv", float_precision="round_trip")
            if not pred[KEYS].equals(prep["selection"]["new_keys"]):
                problems.append(f"{rid} 2026: evaluation keys are not the complete January-April set")
                continue
            prow = position.get_indexer(pd.MultiIndex.from_frame(pred[KEYS]))
            if not np.array_equal(data["overall_phase"].to_numpy(dtype=float)[prow], pred["overall_phase"].to_numpy(dtype=float)) \
                    or not som._close(targets[prow], pred[list(osf.CUMULATIVE_TARGETS)].to_numpy(), 1e-12):
                problems.append(f"{rid} 2026: truth/normalized targets differ")
            X = data.iloc[prow][list(local["features"])]
            replayed = {}
            for target, column in zip(osf.CUMULATIVE_TARGETS, osf.PRED_COLUMNS):
                booster = xgb.Booster()
                booster.load_model(str(bdir / f"model_{target}.ubj"))
                checks["schemas_inspected"] += 1
                if list(booster.feature_names) != list(local["features"]):
                    problems.append(f"{rid} 2026 {target}: booster feature order differs")
                again = booster.predict(xgb.DMatrix(X, feature_names=list(local["features"]))).astype(float)
                diff = float(np.max(np.abs(again - pred[column].to_numpy(dtype=float))))
                checks["max_new_replay_abs_diff"] = max(checks["max_new_replay_abs_diff"], diff)
                if not diff <= 1e-6:
                    problems.append(f"{rid} 2026 {target}: replay differs by {diff}")
                replayed[column] = again
                checks["new_models_replayed"] += 1
            problems.extend(som.replayed_class_problems(f"{rid} 2026", pred, replayed, PARAMS["phase_threshold"]))
            checks["new_batches"] += 1
            combined = pd.read_csv(Path(meta["predictions"]["path"]), float_precision="round_trip")
            want = pd.concat([original["predictions"], pred], ignore_index=True).sort_values(KEYS, kind="mergesort").reset_index(drop=True)
            if sha(meta["predictions"]["path"]) != meta["predictions"]["sha256"] or not combined.equals(want):
                problems.append(f"{rid}: combined five-year predictions differ from the original rows plus the 2026 batch")
            preds[(arm, horizon)] = rpm.assign_regions(combined, regions) if regions is not None else combined
            del local, data
            log(f"verify {ctx.scope} {rid}: {len(problems)} problems so far")
        if len(preds) == len(RUNS):
            verify_reports(ctx, prep, preds, names, problems, checks)
    except Exception as exc:  # a failed gate is a verification failure with its diagnostic, never a pass
        problems.append(f"verification stopped: {type(exc).__name__}: {exc}")
    protected_check(ctx, problems, checks)
    passed = not problems and checks["new_batches"] == 7 and checks["new_models_replayed"] == 28 and checks["schemas_inspected"] == 140 \
        and checks["original_batches_checked"] == 28
    final = finalize_reporting(ctx, "verified" if passed else "verification_failed")  # reporting files only; models/predictions untouched
    inv_roots = [ctx.results, ctx.reports]
    inventory = [{"path": str(p), "sha256": sha(p), "bytes": p.stat().st_size} for root in inv_roots if root.exists()
                 for p in sorted(root.rglob("*")) if p.is_file() and p.parent.name != "verification"]
    out = {"version": ctx.version, "scope": ctx.scope, "model_scope": MODEL_SCOPE[ctx.scope], "passed": passed,
           "status": "accepted_by_executor_verifier" if passed else "failed", "problems": problems, "checks": checks,
           "tolerances": {"new_model_replay": "atol 1e-6, rtol 0; classes of reloaded predictions exact",
                          "metrics/deltas": "atol 1e-12; identical status/reason/support", "csv": "float_precision=round_trip"},
           "runtime": runtime, "script": {"path": str(ctx.script), "sha256": sha(ctx.script)}, "final_reporting": final,
           "prior_evidence": "224 reused original boosters keep their accepted prior numerical replay; here they are re-hashed, schema-inspected "
                             "and their predictions/metrics independently checked", "created_utc": pd.Timestamp.now(tz="UTC").isoformat()}
    write_json(ctx.results / "verification" / "verification_summary.json", out)
    pd.DataFrame(inventory).to_csv(ctx.results / "verification" / "artifact_inventory.csv", index=False)
    return out


def independent_support(part: pd.DataFrame) -> Dict[str, int]:
    """Support columns recomputed with numpy (not regional_point_metrics.support)."""
    observed = part["overall_phase"].to_numpy(dtype=float) >= 3
    predicted = part["overall_phase_pred"].to_numpy(dtype=float) >= 3
    truth = part["phase3_worse"].to_numpy(dtype=float)
    return {"n_rows": int(len(part)), "n_areas": int(len(np.unique(part["area_id"].to_numpy()))), "observed_3plus": int(observed.sum()),
            "observed_1_2": int((~observed).sum()), "predicted_3plus": int(predicted.sum()), "true_positive_3plus": int((observed & predicted).sum()),
            "distinct_phase3_worse": int(len(np.unique(truth[~np.isnan(truth)])))}


def _expected_cells(ctx: Ctx, preds, names) -> Tuple[dict, list]:
    """Independent sklearn values, independently reconstructed undefined status/reason and support for every metric cell."""
    cells, undefined = {}, []
    for (arm, horizon), pred in preds.items():
        groups = [("global" if ctx.scope == "global" else ISO3, None, pred)]
        if ctx.scope == "global":
            groups += [("region", r, pred[pred["region"] == r]) for r in rpm.REGIONS]
        for scope, region, group in groups:
            for period, years in PERIOD_YEARS.items():
                part = group[group["year"].isin(years)]
                ref = legacy.replay(part) if len(part) else {m: None for m in osf.ORIGIN_METRICS}
                status = som.expected_metric_status(part)
                sup = independent_support(part)
                for metric in osf.ORIGIN_METRICS:
                    value = np.nan if ref[metric] is None else float(ref[metric])
                    cells[(arm, horizon, scope, region, period, metric)] = {"value": value, "status": status[metric][0], "reason": status[metric][1], "support": sup}
                    if status[metric][0] != "ok":
                        undefined.append((arm, horizon, scope, region, period, metric, status[metric][1]))
    return cells, undefined


def _cell_problem(cell: Mapping[str, object], r) -> Optional[str]:
    if not som._same_value(cell["value"], r.value) or som._text(r.status) != cell["status"] or som._text(r.reason) != cell["reason"]:
        return f"value/status/reason ({r.value}, {r.status}, {r.reason}) vs ({cell['value']}, {cell['status']}, {cell['reason']})"
    bad = [c for c in SUPPORT if int(getattr(r, c)) != cell["support"][c]]
    return f"support columns {bad} differ" if bad else None


def _key(r) -> tuple:
    return (r.arm, int(r.horizon), r.scope, None if pd.isna(r.region) else int(r.region), str(r.period), r.metric)


def verify_reports(ctx: Ctx, prep, preds, names, problems: List[str], checks: dict) -> None:
    rep, cb_dir = ctx.results / "report", ctx.reports / "model_run_codebook"
    required = [rep / n for n in REPORT_TABLES[ctx.scope]] + [rep / "comparison_metadata.json", ctx.reports / "report.md", cb_dir / CODEBOOK_NAME[ctx.scope],
                                                              cb_dir / "expected_vs_actual_inputs.csv", cb_dir / "model_run_index.csv"]
    missing = [str(p) for p in required if not p.exists()]
    if missing:
        problems.append(f"mandatory report outputs missing: {missing}")
        return
    meta = json.loads((rep / "comparison_metadata.json").read_text())
    if meta.get("extension_manifest", {}).get("sha256") != prep["sha256"] or meta.get("scope") != ctx.scope:
        problems.append("comparison metadata binds a different extension manifest/scope")
    for name in REPORT_TABLES[ctx.scope]:
        som._recorded(problems, f"report {name}", meta.get("outputs", {}).get(name), rep / name)
    som._recorded(problems, "report.md", meta.get("report_md"), ctx.reports / "report.md")
    cbm = meta.get("codebook", {})
    som._recorded(problems, "codebook", {"path": cbm.get("codebook"), "sha256": cbm.get("sha256")}, cb_dir / CODEBOOK_NAME[ctx.scope])
    for key, name in (("expected_vs_actual", "expected_vs_actual_inputs.csv"), ("model_run_index", "model_run_index.csv")):
        som._recorded(problems, name, cbm.get(key), cb_dir / name)
    if not read_csv(rep / "coverage_by_month.csv").equals(read_csv(Path(prep["local"]["files"]["coverage_by_month_2026.csv"]["path"]))):
        problems.append("published coverage differs from the manifest-bound coverage")
    cells, undefined = _expected_cells(ctx, preds, names)
    metrics_name = "all_metrics_long.csv" if ctx.scope == "global" else "som_metrics_long.csv"
    saved = read_csv(rep / metrics_name)
    saved["period"] = saved["period"].astype(str)
    index = {}
    for r in saved.itertuples(index=False):
        if _key(r) in index:
            problems.append(f"duplicate metric cell {_key(r)}")
        index[_key(r)] = r
    if set(index) != set(cells):
        problems.append(f"{metrics_name} cell keys differ from the complete expected set ({len(index)} vs {len(cells)})")
    for key, cell in cells.items():
        r = index.get(key)
        if r is None:
            continue
        issue = _cell_problem(cell, r)
        if issue:
            problems.append(f"metric cell {key}: {issue}")
        if ctx.scope == "global" and (som._text(r.region_name) != (None if key[3] is None else names[key[3]])):
            problems.append(f"metric cell {key}: region name differs")
        checks["metric_cells_replayed"] += 1
    if ctx.scope == "global":  # each split table must be exactly its scope's canonical subset of all_metrics_long
        for sub, scope in (("global_metrics.csv", "global"), ("regional_metrics.csv", "region")):
            want = saved[saved["scope"] == scope].reset_index(drop=True)
            got = read_csv(rep / sub)
            got["period"] = got["period"].astype(str)
            if list(got.columns) != list(saved.columns) or not cl.same_frame(got, want):
                problems.append(f"{sub} is not exactly the {scope} subset of all_metrics_long.csv")
        got = sorted((r.scope, r.metric, r.reason, int(r.cells)) for r in read_csv(rep / "undefined_reasons.csv").itertuples())
        tally: Dict[tuple, int] = {}
        for _, _, scope, _, _, metric, reason in undefined:
            tally[(scope, metric, reason)] = tally.get((scope, metric, reason), 0) + 1
        want_u = sorted((*k, v) for k, v in tally.items())
    else:
        got = sorted((r.arm, int(r.horizon), str(r.period), r.metric, r.reason, int(r.cells)) for r in read_csv(rep / "som_undefined_reasons.csv").itertuples())
        want_u = sorted((a, h, p, m, reason, 1) for a, h, _, _, p, m, reason in undefined)
    if got != want_u:
        problems.append(f"undefined-reasons table differs from the independent undefined conditions ({len(got)} vs {len(want_u)})")
    checks["undefined_cells"] = len(undefined)
    verify_deltas(ctx, cells, names, problems, checks)
    verify_original_parity(ctx, prep, cells, problems, checks)
    book = pd.read_csv(cb_dir / CODEBOOK_NAME[ctx.scope], encoding="utf-8-sig", keep_default_na=False)
    for arm, horizon in RUNS:
        rid = run_id(arm, horizon)
        feats = json.loads((run_dir(ctx, arm, horizon) / "run_metadata.json").read_text())["features"]
        listed = book.loc[book[rid.replace("/", "_")].astype(str).str.lower() == "true", "predictor"].tolist()
        pos = {r.predictor: json.loads(r.actual_model_positions).get(rid) for r in book.itertuples()}
        if sorted(listed) != sorted(feats) or any(pos.get(f) != i + 1 for i, f in enumerate(feats)):
            problems.append(f"{rid}: codebook membership/positions differ from the fitted boosters")
    if book["limitations"].str.contains("expected input|no fit verified", case=False, regex=True).any():
        problems.append("codebook carries expected-contract wording")
    idx = pd.read_csv(cb_dir / "model_run_index.csv")
    if len(idx) != 7 or int(idx["reused_boosters"].sum()) != 112 or int(idx["new_boosters"].sum()) != 28 \
            or not (idx["match"].astype(str).str.lower() == "true").all():
        problems.append("model run index does not record 7 runs, 112 reused and 28 new boosters with matching schemas")


def verify_deltas(ctx: Ctx, cells, names, problems: List[str], checks: dict) -> None:
    rep = ctx.results / "report"
    if ctx.scope == "global":
        parts = {"global": read_csv(rep / "global_deltas.csv"), "region": read_csv(rep / "regional_deltas.csv")}
        for scope, frame in parts.items():
            if set(frame["scope"]) != {scope}:
                problems.append(f"{scope} delta table holds rows of another scope")
        deltas = pd.concat(parts.values(), ignore_index=True)
    else:
        deltas = read_csv(rep / "som_oracle_minus_baseline_deltas.csv")
    deltas["period"] = deltas["period"].astype(str)
    horizons = (0, *ORACLE_H) if ctx.scope == "SOM" else ORACLE_H
    groups = [(ISO3, None)] if ctx.scope == "SOM" else [("global", None), *(("region", r) for r in rpm.REGIONS)]
    index = {}
    for r in deltas.itertuples(index=False):
        k = (int(r.horizon), r.scope, None if pd.isna(r.region) else int(r.region), r.period, r.metric)
        if k in index:
            problems.append(f"duplicate delta row {k}")
        index[k] = r
    want_keys = {(h, s, g, p, m) for h in horizons for s, g in groups for p in PERIODS for m in osf.ORIGIN_METRICS}
    if set(index) != want_keys:
        problems.append(f"delta rows differ from the complete expected set ({len(index)} vs {len(want_keys)})")
    for h, scope, region, period, metric in sorted(want_keys, key=str):
        r = index.get((h, scope, region, period, metric))
        if r is None:
            continue
        oracle_arm = cpf.BASELINE_ARM if h == 0 else cpf.ORACLE_ARM
        o, b = cells[(oracle_arm, h, scope, region, period, metric)], cells[(cpf.BASELINE_ARM, h, scope, region, period, metric)]
        ov, bv = o["value"], b["value"]
        defined = not (np.isnan(ov) or np.isnan(bv))
        if h == 0:
            want_status, want_reason = ("shared_h0_zero", None) if defined else ("undefined", f"baseline {b['reason']}")
        else:
            want_status = "ok" if defined else "undefined"
            want_reason = None if defined else "; ".join(f"{side} {c['reason']}" for side, c in (("oracle", o), ("baseline", b)) if np.isnan(c["value"]))
        sup = {"n_rows": o["support"]["n_rows"], "n_areas": o["support"]["n_areas"], "observed_3plus": o["support"]["observed_3plus"],
               "oracle_predicted_3plus": o["support"]["predicted_3plus"], "baseline_predicted_3plus": b["support"]["predicted_3plus"]}
        if not (som._same_value(r.delta, (ov - bv) if defined else np.nan) and som._same_value(r.oracle_value, ov)
                and som._same_value(r.baseline_value, bv) and som._text(r.status) == want_status and som._text(r.reason) == want_reason) \
                or any(int(getattr(r, c)) != v for c, v in sup.items()) or b["support"]["n_rows"] != o["support"]["n_rows"]:
            problems.append(f"delta H{h} {scope} {region} {period} {metric}: ({r.oracle_value}, {r.baseline_value}, {r.delta}, {r.status}, "
                            f"{r.reason}) differs from ({ov}, {bv}, {want_status}, {want_reason}) or its support")
        if ctx.scope == "global" and som._text(r.region_name) != (None if region is None else names[region]):
            problems.append(f"delta H{h} {scope} {region} {period} {metric}: region name differs")
        checks["delta_cells_replayed"] += 1


def verify_original_parity(ctx: Ctx, prep, cells, problems: List[str], checks: dict) -> None:
    """Original 2022-2025 annual and pooled cells (value, status, reason, every support column) must reproduce the preserved outputs."""
    ev = prep["local"]["original"]["evidence"]
    old = read_csv(ev["metrics"]["path"])
    old["period"] = old["period"].astype(str)
    seen = set()
    for r in old.itertuples(index=False):
        period = ORIGINAL_POOLED if r.period == "pooled" else r.period
        key = (r.arm, int(r.horizon), r.scope, None if pd.isna(r.region) else int(r.region), period, r.metric)
        seen.add(key)
        if key not in cells:
            problems.append(f"original cell {key} has no extension counterpart")
            continue
        issue = _cell_problem(cells[key], r)
        if issue:
            problems.append(f"original cell {key}: preserved output differs from the recomputation: {issue}")
        checks["original_parity_cells"] += 1
    want = {k for k in cells if k[4] in (*map(str, OLD_YEARS), ORIGINAL_POOLED)}
    if seen != want:
        problems.append(f"original parity covered {len(seen)} cells, not the complete {len(want)}")


# --------------------------------------------------------------------------- modes


def validate(ctx: Ctx) -> dict:
    """Read-only: frozen parent gates, 2026 selections, expected fitting sets, paired matrices, original imports and metric parity."""
    runtime = som.runtime_identity()
    prep = prepare(ctx, write=False)
    regions = region_series(ctx) if ctx.scope == "global" else None
    names = region_names(ctx, prep)
    runs, problems, preds, base_cols = {}, [], {}, {}
    for arm, horizon in RUNS:
        rid = run_id(arm, horizon)
        local = localize(ctx, prep, ctx.load_inputs(run_args(ctx, arm, horizon)), arm, horizon)
        expected = pre_fit_checks(ctx, prep, local, arm, horizon)
        original = check_original_run(ctx, prep, local, arm, horizon, problems)
        data = local["data"]
        rows = local["eval_key"] | local["share_valid"]
        frame = data.loc[rows, KEYS + ["overall_phase", *osf.SHARE_COLUMNS] + list(local["features"])].reset_index(drop=True)
        if arm == cpf.BASELINE_ARM:
            base_cols[horizon] = frame
        elif not cl.same_frame(frame[list(base_cols[horizon].columns)], base_cols[horizon]) \
                or list(frame.columns[: base_cols[horizon].shape[1]]) != list(base_cols[horizon].columns):
            problems.append(f"{rid}: paired baseline columns/labels/NaN differ from the baseline matrix")
        nan_cells = int(data.loc[local["eval_key"], list(local["features"])].isna().to_numpy().sum())
        runs[rid] = {**expected, "parent_fingerprint": local["fingerprint_payload"]["parent_fingerprint"], "original_fingerprint": local["original_fingerprint"],
                     "extension_fingerprint_if_manifest_written": local["fingerprint"], "eval_nan_cells_2026": nan_cells,
                     "original_import": None if original is None else {"batches": len(original["lineage"]), "schemas_inspected": original["schemas"]}}
        if original is not None:
            preds[(arm, horizon)] = rpm.assign_regions(original["predictions"], regions) if regions is not None else original["predictions"]
        log(f"validate {ctx.scope} {rid}: parent gate passed; fit {expected['fit_rows']} rows (max label {expected['fit_max_label_month']}), "
            f"eval {expected['eval_rows']}; original import {'ok' if original is not None else 'FAILED'}")
        del local, data
    parity = {"original_parity_cells": 0}
    if len(preds) == len(RUNS):
        cells, _ = _expected_cells(ctx, preds, names)
        verify_original_parity(ctx, prep, cells, problems, parity)
    inv = protected_inventory(ctx)
    return {"mode": "validate-only (nothing written)", "scope": ctx.scope, "version": ctx.version, "passed": not problems, "problems": problems,
            "runtime": runtime, "script": {"path": str(ctx.script), "sha256": sha(ctx.script)},
            "extension_manifest_sha256_if_written": prep["sha256"], "selection": prep["selection"]["summary"], "runs": runs, **parity,
            "protected_inventory": {"files": len(inv), "bytes": int(inv["bytes"].sum()) if len(inv) else 0, "digest": sha_bytes(csv_bytes(inv)),
                                    "by_role": inv.groupby("role").size().to_dict() if len(inv) else {}},
            "roots_exist": {str(ctx.results): ctx.results.exists(), str(ctx.reports): ctx.reports.exists()}}


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--scope", choices=SCOPES, required=True, help="global, or SOM (genuinely Somalia-local fits)")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate-only", action="store_true", help="Read-only gates; no directory or file is written.")
    mode.add_argument("--approve-training", action="store_true", help="Fit the seven 2026 batches (28 boosters) of the scope; reuse verified 2022-2025.")
    mode.add_argument("--report", action="store_true", help="Metric/difference/coverage tables, report.md and codebooks from saved artifacts.")
    mode.add_argument("--verify", action="store_true", help="Independent verification of the scope's saved artifacts (never fits).")
    return parser.parse_args(argv)


def main(argv=None, ctx: Optional[Ctx] = None) -> int:
    args = parse_args(argv)
    ctx = ctx or Ctx(scope=args.scope)
    if ctx.scope != args.scope:
        raise LocalError("context scope differs from --scope")
    dump = lambda obj: print(json.dumps(obj, indent=1, default=som._json_default), flush=True)  # noqa: E731
    if args.validate_only:
        out = validate(ctx)
        dump(out)
        return 0 if out["passed"] else 1
    if args.approve_training:
        dump(train(ctx))
        return 0
    if args.report:
        dump({k: v for k, v in report(ctx).items() if k in ("version", "scope", "status", "outputs", "codebook", "report_md")})
        return 0
    out = verify(ctx)
    dump({k: out[k] for k in ("version", "scope", "passed", "problems", "checks")})
    return 0 if out["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
