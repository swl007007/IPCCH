#!/usr/bin/env python3
"""Somalia-local reruns of the compact historical experiment and the April 2026 compact/CDS launch.

Task ``10-09-somalia-local-compact-cds-test`` (prd.md R1-R11, design.md). One fixed scope: canonical membership
``iso3 == "SOM"`` of the pinned country lookup; every model is refit on Somalia rows only.

- Historical stage (``compact_climate_weather_oracle_v1_somalia_local``): compact_baseline H0/H3/H6/H12 and
  compact_weather_oracle H3/H6/H12 (H0 shared), annual blocks 2022..2025, four cumulative regressors per block
  (7 runs, 28 batches, 112 models). The unchanged parent gate ``load_origin_inputs`` validates the complete parent
  inputs first; then BOTH ``share_valid`` and ``eval_key`` are intersected with the membership and the parent
  fingerprint is replaced by a local one before the unchanged ``run_origin_batch`` fits each block.
- Launch stage (``nowcasting_2026_04_compact_cds_v1_somalia_local``): compact_baseline H0/H6/H12 and
  compact_cds_weather H6/H12 (H0 shared), origin April 2026 (5 fits, 20 models). The unchanged parent gate
  ``compact_launch.validate_inputs`` runs on the full parent manifest; local fit-selection and inference projections
  are exact membership filters of the parent files, bound by a hashed local manifest, and fitted by the unchanged
  ``compact_launch.fit_run``.

Modes: ``--validate-only`` (all read-only gates, writes nothing), ``--approve-training [--pilot]`` (historical then
launch fits; ``--pilot`` fits only historical compact_baseline H0 / 2022), ``--report`` and ``--verify`` (saved
artifacts only; never fit). Fixed seed 42, half-life 24, threshold 0.2, n_jobs 16, frozen configs/runtime.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import os
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


# unchanged frozen modules: the origin-safe compact runner (gate + batch fitter) and the scikit-learn metric replay
runner = _load("compact_origin_safe_runner", "scripts/modeling/run_deep_feature_weight_decay_forecasting.py")
legacy = _load("origin_safe_sklearn_replay", "scripts/postprocessing/verify_origin_safe_climate_idp.py")

ISO3 = "SOM"
COUNTRY = "Somalia"
MODEL_SCOPE = "Somalia local"
HIST_VERSION = f"{cpf.VERSION}_somalia_local"
LAUNCH_VERSION = "nowcasting_2026_04_compact_cds_v1_somalia_local"
A = paths.SOURCE_DATA_DIR / "assembled_IPCCH"
MEMBERSHIP = A / "country_area_id_lookup.csv"
HIST_MANIFEST = A / "model_ready" / cpf.VERSION / f"{cpf.VERSION}_manifest.json"
LAUNCH_MANIFEST = cl.INPUT_ROOT / cl.MANIFEST_NAME
HIST_RESULTS = paths.RESULTS_DIR / "experiments" / HIST_VERSION
HIST_REPORTS = paths.REPORTS_DIR / HIST_VERSION
LAUNCH_RESULTS = paths.RESULTS_DIR / "launch" / LAUNCH_VERSION
LAUNCH_REPORTS = paths.REPORTS_DIR / "launch" / LAUNCH_VERSION
TASK_DIR = PROJECT_ROOT / ".trellis" / "tasks" / "10-09-somalia-local-compact-cds-test"
SPEC_FILES = ("prd.md", "design.md", "implement.md", "expected_runs.csv", "approval.md")
PARAMS = {"seed": 42, "half_life_months": 24.0, "phase_threshold": 0.2, "n_jobs": 16}
KEYS = list(osf.KEYS)
YEARS = tuple(osf.TARGET_YEARS)
HIST_RUNS = tuple(cpf.RUN_PLAN)
LAUNCH_RUNS = tuple(cl.RUNS)
ORACLE_H = (3, 6, 12)
PILOT = (cpf.BASELINE_ARM, 0, 2022)
# parent namespaces this script must never write into (the local roots carry a distinct suffix)
PARENT_NAMESPACES = (cpf.VERSION, cl.VERSION, "nowcasting_2026_04_compact_cds_v1", *cpf.LEGACY_NAMESPACES)
# approved Somalia facts (prd.md R7/R8, design.md "Membership and coverage" and "Population and reports")
EXPECTED = {
    "members": 905,
    "hist_eval_rows": 4933, "hist_eval_by_year": {2022: 1129, 2023: 1217, 2024: 711, 2025: 1876},
    "hist_eval_areas_by_year": {2022: 585, 2023: 705, 2024: 372, 2025: 904}, "hist_eval_union_areas": 905,
    "launch_fit_rows": 5835, "launch_fit_areas": 905, "launch_inference_areas": 904, "launch_excluded": [3146],
    "population": {"country": COUNTRY, "raw": 62695007.0, "reference": 19654739.0, "cap_factor": 0.29782279233177217,
                   "effective": 18672002.05, "areas": 904},
}
CODEBOOK_EXPECTED_SENTENCES = (" This is an expected input, not a fitted result.", "Expected inputs only; no fit verified. ")
SHARE_NAMES = list(cl.SHARE_NAMES)
METRIC_LABELS = {"exact_phase_accuracy": "exact acc", "phase3plus_accuracy": "3+ acc", "precision_phase3plus": "prec 3+",
                 "sensitivity_phase3plus": "recall 3+", "f2_phase3plus": "F2 3+", "r2_phase3plus": "R² 3+",
                 "mae_phase3plus": "MAE 3+", "ordinal_mae": "ordinal MAE"}


class LocalError(ValueError):
    pass


def log(message: str) -> None:
    print(f"[{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}] {message}", file=sys.stderr, flush=True)  # stdout carries the JSON result


def sha(path) -> str:
    return osf.file_sha256(path)


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json_default(value):
    if isinstance(value, (np.integer, np.floating, np.bool_)):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"not JSON serializable: {type(value)}")


def canonical_json(payload) -> bytes:
    """Deterministic bytes for hashed local manifests (sorted keys, no timestamps)."""
    return (json.dumps(payload, indent=2, sort_keys=True, default=_json_default) + "\n").encode("utf-8")


def digest(payload) -> str:
    return sha_bytes(json.dumps(payload, sort_keys=True, default=_json_default).encode("utf-8"))


def csv_bytes(frame: pd.DataFrame) -> bytes:
    return frame.to_csv(index=False, float_format="%.17g", lineterminator="\n").encode("utf-8")


def read_csv(path, **kw) -> pd.DataFrame:
    return pd.read_csv(path, float_precision="round_trip", low_memory=False, keep_default_na=False, na_values=[""], **kw)


def run_id(arm: str, horizon: int) -> str:
    return f"{arm}/{horizon}m"


def ym(o: int) -> str:
    return osf.ord_label(int(o))


def assert_local_root(path: Path) -> Path:
    parts = Path(path).resolve().parts
    hit = [ns for ns in PARENT_NAMESPACES if ns in parts]
    if hit:
        raise LocalError(f"refusing to write into a parent namespace {hit}: {path}")
    return Path(path)


def write_once(path: Path, data: bytes) -> dict:
    """Create ``path`` with ``data``; an existing file must already hold exactly these bytes (immutable local inputs)."""
    path = Path(path)
    if path.exists():
        if path.read_bytes() != data:
            raise LocalError(f"{path} exists with different bytes (changed membership/spec/code/parent?); use a new root")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_bytes(data)
        os.replace(tmp, path)
    return {"path": str(path), "sha256": sha_bytes(data), "bytes": len(data)}


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, default=_json_default) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def save_table(frame: pd.DataFrame, path: Path) -> dict:
    """Report table with an exact CSV round-trip check (only empty fields missing; text columns compared as text)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = frame.reset_index(drop=True)
    path.write_bytes(csv_bytes(frame))
    text = {c: str for c in frame.columns if not pd.api.types.is_numeric_dtype(frame[c])}
    if not cl.same_frame(read_csv(path, dtype=text), frame):
        raise LocalError(f"CSV round trip changed {path.name}")
    return {"path": str(path), "sha256": sha(path), "rows": len(frame), "columns": frame.shape[1]}


# --------------------------------------------------------------------------- context (injectable for tiny fixtures)


def _default_boundaries():
    from ipcch import alert_risk_maps as arm

    return arm.load_spatial_boundaries(cl.GEOMETRY)


def default_parent_cap_audit(parent: Mapping[str, object]) -> pd.DataFrame:
    """The original complete cap audit of the parent April population ledger (all reference countries)."""
    population = pd.read_csv(parent["ledgers"]["population"]["path"], float_precision="round_trip")
    mapping = cl.mapping_frame(population["area_id"].to_numpy())
    return cl.cap_audit(population, mapping)


def default_frozen_paths() -> List[Tuple[str, Path]]:
    """Frozen code/config/parent-input/old-output files whose bytes must not change (inventoried before and after)."""
    code = sorted(set(cl.CODE_FILES) | set(cl.FIT_CODE) | set(cpf.FIT_CODE) | {
        "scripts/postprocessing/verify_origin_safe_climate_idp.py", "scripts/postprocessing/verify_origin_safe_weather_oracle.py",
        "scripts/postprocessing/verify_compact_climate_weather_oracle.py", "scripts/modeling/run_compact_climate_weather_oracle_suite.py",
        "src/ipcch/regional_point_metrics.py", "src/ipcch/paths.py", "configs/forecasting_hyperparameters.json",
        "configs/forecasting_hyperparameters_p3.json"})
    out = [("code", PROJECT_ROOT / rel) for rel in code]
    for role, root in (("parent_inputs", A / "model_ready" / cpf.VERSION), ("parent_inputs", cl.INPUT_ROOT),
                       ("old_results", paths.RESULTS_DIR / "experiments" / cpf.VERSION),
                       ("old_results", cl.RESULTS_ROOT), ("old_reports", paths.REPORTS_DIR / cpf.VERSION), ("old_reports", cl.REPORTS_ROOT)):
        out += [(role, p) for p in sorted(root.rglob("*")) if p.is_file()]
    out += [("membership", MEMBERSHIP), ("geometry", cl.GEOMETRY), *(("geometry", cl.GEOMETRY.with_suffix(s)) for s in (".shx", ".dbf", ".prj", ".cpg")),
            ("reference", cl.PINNED["country_population_reference"][0]), ("reference", cl.PINNED["region_map"][0])]
    return [(r, p) for r, p in out if p.exists()]


@dataclass
class Ctx:
    membership: Path = MEMBERSHIP
    hist_manifest: Path = HIST_MANIFEST
    launch_manifest: Path = LAUNCH_MANIFEST
    hist_results: Path = HIST_RESULTS
    hist_reports: Path = HIST_REPORTS
    launch_results: Path = LAUNCH_RESULTS
    launch_reports: Path = LAUNCH_REPORTS
    spec_dir: Path = TASK_DIR
    script: Path = Path(__file__).resolve()
    expected: Optional[dict] = field(default_factory=lambda: json.loads(json.dumps(EXPECTED)))
    hist_contract_sha256: Optional[Mapping[str, str]] = field(default_factory=lambda: dict(cpf.FROZEN_CONTRACT_SHA256))
    launch_contract_sha256: Optional[Mapping[str, str]] = field(default_factory=lambda: dict(cl.CONTRACT_SHA256))
    frozen_feature_sha256: Optional[Mapping[Tuple[str, int], str]] = field(default_factory=lambda: dict(cpf.FROZEN_FEATURE_SHA256))
    load_hist_inputs: Callable = runner.load_origin_inputs
    hyperparameters: Callable = runner.load_hyperparameters
    validate_launch_parent: Callable = cl.validate_inputs
    parent_cap_audit: Callable = default_parent_cap_audit
    load_boundaries: Callable = _default_boundaries
    geometry_files: Sequence[Path] = field(default_factory=lambda: [cl.GEOMETRY.with_suffix(s) for s in (".shp", ".shx", ".dbf", ".prj", ".cpg")
                                                                    if cl.GEOMETRY.with_suffix(s).exists()])
    frozen_paths: Callable = default_frozen_paths

    def roots(self) -> List[Path]:
        return [self.hist_results, self.hist_reports, self.launch_results, self.launch_reports]


def expect(ctx: Ctx, key: str):
    return None if ctx.expected is None else ctx.expected.get(key)


def gate_equal(label: str, got, want) -> None:
    if want is not None and json.loads(json.dumps(got, default=_json_default)) != json.loads(json.dumps(want, default=_json_default)):
        raise LocalError(f"{label}: got {got}, approved {want}")


# --------------------------------------------------------------------------- membership, spec and identity


def load_membership(ctx: Ctx) -> dict:
    """Exact ``iso3 == "SOM"`` rows of the pinned lookup; no name fallback."""
    lookup = pd.read_csv(ctx.membership, keep_default_na=False, na_values=[""])
    if not {"area_id", "iso3"} <= set(lookup.columns):
        raise LocalError("membership lookup lacks area_id/iso3")
    if lookup["area_id"].isna().any() or lookup["area_id"].duplicated().any():
        raise LocalError("membership lookup has missing or duplicate area_id")
    rows = lookup[lookup["iso3"] == ISO3]
    ids = sorted(int(a) for a in rows["area_id"])
    if not ids:
        raise LocalError(f"no area has iso3 == {ISO3}")
    if "country" not in rows.columns or sorted(rows["country"].unique()) != [COUNTRY]:
        raise LocalError(f"{ISO3} members do not map to exactly the country name {COUNTRY!r}")
    gate_equal("SOM members", len(ids), expect(ctx, "members"))
    return {"path": str(ctx.membership), "sha256": sha(ctx.membership), "column": "iso3", "value": ISO3, "country": COUNTRY,
            "n_areas": len(ids), "area_ids_sha256": osf.list_sha256(str(i) for i in ids), "area_ids": ids}


def membership_identity(membership: Mapping[str, object]) -> dict:
    return {k: membership[k] for k in ("path", "sha256", "column", "value", "country", "n_areas", "area_ids_sha256")}


def spec_files(ctx: Ctx, local_manifest: Path) -> Dict[str, bytes]:
    """Approved spec bytes: the active task directory while it exists; after ordinary task archival the copies bound by the
    stage's local manifest (exact hashes required). No archive path enters any identity."""
    active = Path(ctx.spec_dir)
    if all((active / name).exists() for name in SPEC_FILES):
        return {name: (active / name).read_bytes() for name in SPEC_FILES}
    if not Path(local_manifest).exists():
        raise LocalError(f"approved spec is neither at the active task path {active} nor bound by a local manifest {local_manifest}")
    bound = json.loads(Path(local_manifest).read_text(encoding="utf-8"))["files"]
    out = {}
    for name in SPEC_FILES:
        copy = Path(local_manifest).parent / "approved_spec" / name
        item = bound.get(f"approved_spec/{name}")
        if item is None or not copy.exists() or sha(copy) != item["sha256"]:
            raise LocalError(f"archived-task spec copy {copy} is missing or differs from its local manifest hash")
        out[name] = copy.read_bytes()
    return out


def local_code_identity(ctx: Ctx) -> dict:
    return {"script": str(ctx.script), "sha256": sha(ctx.script)}


def runtime_identity() -> dict:
    runtime = cpf.runtime_identity()
    drift = {k: (runtime[k], v) for k, v in cpf.FROZEN_RUNTIME.items() if runtime[k] != v}
    if drift:
        raise LocalError(f"numerical runtime differs from the frozen versions: {drift}")
    return runtime


def frozen_inventory(ctx: Ctx) -> pd.DataFrame:
    rows = [{"role": role, "path": str(p), "bytes": p.stat().st_size, "sha256": sha(p)} for role, p in ctx.frozen_paths()]
    return pd.DataFrame(rows, columns=["role", "path", "bytes", "sha256"])


# --------------------------------------------------------------------------- historical stage


def hist_args(ctx: Ctx, arm: str, horizon: int) -> argparse.Namespace:
    """Exactly the arguments the original seven-run suite passes to the origin-safe CLI (no country scope)."""
    return argparse.Namespace(
        protocol="origin-safe", origin_manifest=str(ctx.hist_manifest), horizon=horizon, arm=arm, out_dir=str(hist_run_dir(ctx, arm, horizon)),
        seed=PARAMS["seed"], half_life_months=PARAMS["half_life_months"], phase_threshold=PARAMS["phase_threshold"], n_jobs=PARAMS["n_jobs"],
        country_iso3=None, region_scope=0, country_name=None, enable_shap=False, add_identifier_features=False, dataset=None,
        dataset_key=None, sample_rows=None, block_years=None, dry_run=False)


def hist_manifest_path(ctx: Ctx) -> Path:
    return Path(ctx.hist_results) / "inputs" / f"{HIST_VERSION}_manifest.json"


def launch_manifest_path(ctx: Ctx) -> Path:
    return Path(ctx.launch_results) / "inputs" / f"{LAUNCH_VERSION}_manifest.json"


def hist_run_dir(ctx: Ctx, arm: str, horizon: int) -> Path:
    return Path(ctx.hist_results) / "runs" / arm / f"{horizon}m"


def hist_parent_manifest(ctx: Ctx) -> dict:
    manifest = json.loads(Path(ctx.hist_manifest).read_text(encoding="utf-8"))
    if manifest.get("version") != cpf.VERSION or manifest.get("status") != "COMPLETE":
        raise LocalError(f"historical parent manifest is not a COMPLETE {cpf.VERSION} build")
    if sha(manifest["cohort"]["path"]) != manifest["cohort"]["sha256"]:
        raise LocalError("parent cohort bytes differ from the historical parent manifest")
    files = manifest["contract"]["files"]
    for name, item in files.items():
        if sha(item["path"]) != item["sha256"]:
            raise LocalError(f"parent contract {name} bytes differ from the historical parent manifest")
    if ctx.hist_contract_sha256 is not None and {k: v["sha256"] for k, v in files.items()} != dict(ctx.hist_contract_sha256):
        raise LocalError("historical parent manifest does not bind the approved compact contract bytes")
    return manifest


def hist_selection(ctx: Ctx, manifest: Mapping[str, object], members: Sequence[int]) -> dict:
    """Local SOM keys from the parent frozen cohort (keys/share_valid/eval_key equal every run's dataset by the parent gate)."""
    cohort = pd.read_csv(manifest["cohort"]["path"])
    som = cohort["area_id"].isin(members).to_numpy()
    valid = cohort["share_valid"].to_numpy(dtype=bool)
    evalk = cohort["eval_key"].to_numpy(dtype=bool)
    eval_keys = cohort.loc[evalk & som, KEYS].reset_index(drop=True)
    valid_keys = cohort.loc[valid & som, KEYS].reset_index(drop=True)
    by_year = {int(y): int(n) for y, n in eval_keys["year"].value_counts().sort_index().items()}
    areas_by_year = {int(y): int(g["area_id"].nunique()) for y, g in eval_keys.groupby("year")}
    summary = {"label_keys": len(cohort), "parent_eval_rows": int(evalk.sum()), "parent_share_valid_rows": int(valid.sum()),
               "som_label_keys": int(som.sum()), "fit_valid_rows": len(valid_keys), "fit_valid_keys_sha256": osf.keys_sha256(valid_keys),
               "eval_rows": len(eval_keys), "eval_keys_sha256": osf.keys_sha256(eval_keys), "eval_by_year": by_year,
               "eval_areas_by_year": areas_by_year, "eval_union_areas": int(eval_keys["area_id"].nunique()),
               "eval_nonmember_rows": int((~eval_keys["area_id"].isin(members)).sum())}
    gate_equal("historical SOM evaluation rows", summary["eval_rows"], expect(ctx, "hist_eval_rows"))
    gate_equal("historical SOM evaluation rows by year", by_year, expect(ctx, "hist_eval_by_year"))
    gate_equal("historical SOM evaluation areas by year", areas_by_year, expect(ctx, "hist_eval_areas_by_year"))
    gate_equal("historical SOM evaluation area union", summary["eval_union_areas"], expect(ctx, "hist_eval_union_areas"))
    if sorted(by_year) != list(YEARS):
        raise LocalError(f"historical SOM evaluation years {sorted(by_year)} are not {list(YEARS)}")
    return {"som": som, "share_valid": valid & som, "eval_key": evalk & som, "keys": cohort[KEYS].reset_index(drop=True),
            "eval_keys": eval_keys, "valid_keys": valid_keys, "summary": summary}


def hist_local_files(ctx: Ctx, manifest: Mapping[str, object], membership: Mapping[str, object], selection: Mapping[str, object]) -> Dict[str, bytes]:
    """Every immutable local input file (relative to ``<hist_results>/inputs``) as exact bytes."""
    files = {f"approved_spec/{k}": v for k, v in spec_files(ctx, hist_manifest_path(ctx)).items()}
    files.update({f"parent_contract/{k}": Path(v["path"]).read_bytes() for k, v in manifest["contract"]["files"].items()})
    files["som_membership_area_ids.csv"] = csv_bytes(pd.DataFrame({"area_id": membership["area_ids"]}))
    files["som_eval_keys.csv"] = csv_bytes(selection["eval_keys"])
    files["som_fit_valid_keys.csv"] = csv_bytes(selection["valid_keys"])
    return files


def hist_local_manifest(ctx: Ctx, manifest: Mapping[str, object], membership: Mapping[str, object], selection: Mapping[str, object],
                        files: Mapping[str, bytes]) -> dict:
    inputs = Path(ctx.hist_results) / "inputs"
    return {
        "version": HIST_VERSION, "status": "COMPLETE", "stage": "historical", "scope": ISO3, "model_scope": MODEL_SCOPE,
        "parent": {"manifest": {"path": str(ctx.hist_manifest), "sha256": sha(ctx.hist_manifest)}, "model_contract_version": cpf.VERSION,
                   "cohort": {k: manifest["cohort"][k] for k in ("path", "sha256", "label_keys_sha256", "eval_keys_sha256")}},
        "membership": membership_identity(membership),
        "cohort": selection["summary"],
        "runs": {run_id(a, h): {"arm": a, "horizon": h, "test_years": list(YEARS),
                                "feature_count": len(manifest["horizons"][str(h)]["arms"][a]["features"]),
                                "feature_sha256": manifest["horizons"][str(h)]["arms"][a]["feature_sha256"]} for a, h in HIST_RUNS},
        "files": {name: {"path": str(inputs / name), "sha256": sha_bytes(data), "bytes": len(data)} for name, data in sorted(files.items())},
        "local_code": local_code_identity(ctx), "params": dict(PARAMS), "frozen_configs_sha256": dict(cpf.FROZEN_CONFIG_SHA256),
        "frozen_runtime": dict(cpf.FROZEN_RUNTIME),
        "split_rule": "test year Y: fit labels <= Jan(Y) - max(H, 1) on SOM valid shares; weights 0.5 ** ((Jan(Y) - H - U) / 24); "
                      "evaluate every SOM frozen evaluation key of Y; features keep each row's origin T - H",
    }


def hist_prepare(ctx: Ctx, write: bool) -> dict:
    manifest = hist_parent_manifest(ctx)
    membership = load_membership(ctx)
    selection = hist_selection(ctx, manifest, membership["area_ids"])
    files = hist_local_files(ctx, manifest, membership, selection)
    local = hist_local_manifest(ctx, manifest, membership, selection, files)
    data = canonical_json(local)
    path = hist_manifest_path(ctx)
    if write:
        assert_local_root(ctx.hist_results)
        for name, payload in files.items():
            write_once(path.parent / name, payload)
        write_once(path, data)
    elif path.exists() and path.read_bytes() != data:
        raise LocalError(f"{path} exists with different bytes (membership/spec/code/parent changed); use a new root")
    return {"parent": manifest, "membership": membership, "selection": selection, "local": local, "path": path, "sha256": sha_bytes(data)}


def hist_localize(ctx: Ctx, prep: Mapping[str, object], inputs: Mapping[str, object], arm: str, horizon: int) -> dict:
    """Parent-gated inputs with BOTH masks restricted to SOM and a genuinely local fingerprint."""
    sel = prep["selection"]
    data = inputs["data"]
    if not data[KEYS].reset_index(drop=True).equals(sel["keys"]):
        raise LocalError(f"{run_id(arm, horizon)}: dataset keys differ from the frozen cohort rows")
    som = data["area_id"].isin(prep["membership"]["area_ids"]).to_numpy()
    if not np.array_equal(som, sel["som"]):
        raise LocalError("membership mask differs between dataset and cohort")
    share_valid = np.asarray(inputs["share_valid"], dtype=bool) & som
    eval_key = np.asarray(inputs["eval_key"], dtype=bool) & som
    if not (np.array_equal(share_valid, sel["share_valid"]) and np.array_equal(eval_key, sel["eval_key"])):
        raise LocalError(f"{run_id(arm, horizon)}: local masks differ from the SOM cohort selection")
    features = list(inputs["features"])
    frozen = None if ctx.frozen_feature_sha256 is None else ctx.frozen_feature_sha256[(arm, horizon)]
    if osf.list_sha256(features) != (frozen or osf.list_sha256(features)) \
            or osf.list_sha256(features) != prep["local"]["runs"][run_id(arm, horizon)]["feature_sha256"]:
        raise LocalError(f"{run_id(arm, horizon)}: fitted schema differs from the inherited contract")
    payload = {"local_version": HIST_VERSION, "stage": "historical", "scope": ISO3, "model_scope": MODEL_SCOPE, "arm": arm, "horizon": int(horizon),
               "local_manifest_sha256": prep["sha256"], "parent_fingerprint": inputs["fingerprint"],
               "parent_fingerprint_payload": inputs["fingerprint_payload"], "membership_area_ids_sha256": prep["membership"]["area_ids_sha256"],
               "fit_valid_keys_sha256": prep["selection"]["summary"]["fit_valid_keys_sha256"],
               "eval_keys_sha256": prep["selection"]["summary"]["eval_keys_sha256"], "local_code_sha256": sha(ctx.script), "params": dict(PARAMS)}
    return dict(inputs, share_valid=share_valid, eval_key=eval_key, fingerprint=digest(payload), fingerprint_payload=payload)


def expected_hist_fit(data: pd.DataFrame, share_valid: np.ndarray, year: int, horizon: int) -> Tuple[pd.DataFrame, np.ndarray]:
    ords = data["year"].to_numpy() * 12 + data["month"].to_numpy() - 1
    cutoff = year * 12 - max(horizon, 1)
    mask = share_valid & (ords <= cutoff)
    return data.loc[mask, KEYS].reset_index(drop=True), ords[mask]


def hist_train(ctx: Ctx, prep: Mapping[str, object], pilot: bool) -> List[dict]:
    plan = [(PILOT[0], PILOT[1])] if pilot else list(HIST_RUNS)
    years = [PILOT[2]] if pilot else list(YEARS)
    done = []
    for arm, horizon in plan:
        rid = run_id(arm, horizon)
        args = hist_args(ctx, arm, horizon)
        inputs = hist_localize(ctx, prep, ctx.load_hist_inputs(args), arm, horizon)
        run_dir = assert_local_root(hist_run_dir(ctx, arm, horizon))
        meta_path = run_dir / "run_metadata.json"
        if meta_path.exists() and json.loads(meta_path.read_text()).get("fingerprint") != inputs["fingerprint"]:
            raise LocalError(f"{run_dir} holds a run with a different local fingerprint; refusing to mix runs")
        hp, hp3 = ctx.hyperparameters()
        records = []
        log(f"historical {rid}: {len(inputs['features'])} features, blocks {years}")
        for year in years:
            batch_dir = run_dir / "batches" / str(year)
            if batch_dir.exists() and any(batch_dir.iterdir()) and not (batch_dir / "batch_record.json").exists():
                raise LocalError(f"{batch_dir} has files but no batch record; refusing to resume or overwrite an incomplete batch "
                                 "(partial diagnostics preserved; use a new root)")
            record = runner.verify_batch(batch_dir, inputs["fingerprint"])
            if record is None:
                record = runner.run_origin_batch(inputs, args, year, hp, hp3, batch_dir)
                log(f"  {rid} {year}: fit {record['fit_rows']} SOM rows (labels <= {record['fit_label_cutoff_month']}), eval {record['eval_rows']}, "
                    f"{record['batch_seconds']} s, rss {record['peak_rss_mb']} MB")
            else:
                log(f"  {rid} {year}: verified existing batch")
            want_fit, _ = expected_hist_fit(inputs["data"], inputs["share_valid"], year, horizon)
            want_eval = prep["selection"]["eval_keys"]
            want_eval = want_eval[want_eval["year"] == year]
            if record["fit_rows"] != len(want_fit) or record["fit_keys_sha256"] != osf.keys_sha256(want_fit) \
                    or record["eval_rows"] != len(want_eval) or record["eval_keys_sha256"] != osf.keys_sha256(want_eval):
                raise LocalError(f"{rid} {year}: batch keys are not the complete SOM fitting/evaluation sets")
            records.append(record)
        full = years == list(YEARS)
        write_hist_run_metadata(ctx, prep, inputs, arm, horizon, records, full)
        done.append({"run_id": rid, "status": "COMPLETE" if full else "PARTIAL", "batches": [r["block_year"] for r in records]})
        del inputs
    return done


def write_hist_run_metadata(ctx: Ctx, prep, inputs, arm: str, horizon: int, records: List[dict], full: bool) -> None:
    run_dir = hist_run_dir(ctx, arm, horizon)
    metadata = {
        "protocol": "origin-safe", "local_version": HIST_VERSION, "scope": ISO3, "model_scope": MODEL_SCOPE,
        "parent_model_contract_version": cpf.VERSION, "status": "COMPLETE" if full else "PARTIAL",
        "fingerprint": inputs["fingerprint"], "fingerprint_payload": inputs["fingerprint_payload"],
        "local_manifest": {"path": str(prep["path"]), "sha256": prep["sha256"]}, "manifest": str(ctx.hist_manifest),
        "arm": arm, "horizon": horizon, "feature_count": len(inputs["features"]), "features": list(inputs["features"]),
        "split_rule": prep["local"]["split_rule"], "decay_formulation": "weight = 0.5 ** ((Jan(Y) - H - label month) / half_life_months)",
        **PARAMS, "batches": records, "written_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    if full:
        frames = [pd.read_csv(run_dir / "batches" / str(r["block_year"]) / "predictions.csv", float_precision="round_trip") for r in records]
        predictions = pd.concat(frames, ignore_index=True)
        if len(predictions) != int(inputs["eval_key"].sum()) or predictions.duplicated(KEYS).any() \
                or not predictions[KEYS].sort_values(KEYS).reset_index(drop=True).equals(
                    prep["selection"]["eval_keys"].sort_values(KEYS).reset_index(drop=True)):
            raise LocalError("assembled predictions do not cover the SOM evaluation keys exactly once")
        (run_dir / "predictions").mkdir(exist_ok=True)
        (run_dir / "metrics").mkdir(exist_ok=True)
        rows = []
        for year in YEARS:
            part = predictions[predictions["year"] == year]
            part.to_csv(run_dir / "predictions" / f"predictions_{year}.csv", index=False, float_format="%.17g")
            rows.append(osf.flatten_origin_metrics(osf.origin_metrics(part, ISO3, year)))
        rows.append(osf.flatten_origin_metrics(osf.origin_metrics(predictions, ISO3, "pooled")))
        pd.DataFrame(rows).to_csv(run_dir / "metrics" / "metrics_overall.csv", index=False)
        metadata["prediction_rows"] = len(predictions)
    write_json(run_dir / "run_metadata.json", metadata)


# --------------------------------------------------------------------------- launch stage


def launch_run_dir(ctx: Ctx, arm: str, horizon: int) -> Path:
    return Path(ctx.launch_results) / "runs" / arm / f"{horizon}m"


def independent_targets(data: pd.DataFrame) -> np.ndarray:
    shares = data[list(osf.SHARE_COLUMNS)].to_numpy(dtype=float)
    with np.errstate(invalid="ignore", divide="ignore"):
        norm = shares / shares.sum(axis=1, keepdims=True)
    return np.column_stack([norm[:, k:].sum(axis=1) for k in (1, 2, 3, 4)])


def launch_prepare(ctx: Ctx, write: bool) -> dict:
    """Full parent gate, exact SOM projections with complete-set/target/weight/pairing/round-trip gates, local manifest."""
    parent_path = Path(ctx.launch_manifest)
    parent = ctx.validate_launch_parent(parent_path)
    membership = load_membership(ctx)
    members = set(membership["area_ids"])
    files: Dict[str, bytes] = {f"approved_spec/{k}": v for k, v in spec_files(ctx, launch_manifest_path(ctx)).items()}
    contract_dir = Path(parent["contract"]["dir"])
    for name in sorted(parent["contract"]["sha256"]):
        data = (contract_dir / name).read_bytes()
        if sha_bytes(data) != parent["contract"]["sha256"][name] or (ctx.launch_contract_sha256 is not None and sha_bytes(data) != ctx.launch_contract_sha256[name]):
            raise LocalError(f"parent launch contract {name} differs from the approved bytes")
        files[f"parent_contract/{name}"] = data
    inputs = Path(ctx.launch_results) / "inputs"
    runs, frames, checks = {}, {}, {}
    for arm, horizon in LAUNCH_RUNS:
        rid = run_id(arm, horizon)
        entry = parent["runs"][rid]
        fit = read_csv(entry["fit_selection"]["path"])
        inf = read_csv(entry["inference"]["path"])
        local_fit = fit[fit["area_id"].isin(members)].reset_index(drop=True)
        local_inf = inf[inf["area_id"].isin(members)].reset_index(drop=True)
        # complete eligible set: every valid SOM label strictly before April 2026 of the training dataset, in dataset order
        train = pd.read_csv(entry["training_dataset"]["path"], usecols=KEYS + ["overall_phase", *osf.SHARE_COLUMNS], float_precision="round_trip")
        tords = osf.month_ord(train["year"], train["month"])
        eligible = osf.share_validity(train) & (tords <= cl.LABEL_CUTOFF_ORD) & train["area_id"].isin(members).to_numpy()
        want_keys = train.loc[eligible, KEYS].reset_index(drop=True)
        if not local_fit[KEYS].equals(want_keys):
            raise LocalError(f"{rid}: SOM fit selection is not the complete eligible SOM set before April 2026")
        want_targets = independent_targets(train.loc[eligible])
        if not np.allclose(local_fit[list(osf.CUMULATIVE_TARGETS)].to_numpy(dtype=float), want_targets, rtol=0, atol=1e-12):
            raise LocalError(f"{rid}: SOM fitting targets differ from the independent share normalization")
        ford = local_fit["year"].to_numpy() * 12 + local_fit["month"].to_numpy() - 1
        if not (np.array_equal(local_fit["fit_ord"].to_numpy(), ford) and np.array_equal(local_fit["age_months"].to_numpy(), cl.ORIGIN_ORD - ford)
                and np.allclose(local_fit["sample_weight"].to_numpy(dtype=float), 0.5 ** ((cl.ORIGIN_ORD - ford) / 24.0), rtol=0, atol=1e-15)
                and ford.max() <= cl.LABEL_CUTOFF_ORD):
            raise LocalError(f"{rid}: SOM fitting ordinals/ages/April-anchored weights are inconsistent")
        frozen = None if ctx.frozen_feature_sha256 is None else ctx.frozen_feature_sha256[(cl.TRAINING_ARM[arm], horizon)]
        if osf.list_sha256(entry["features"]) != entry["feature_sha256"] or (frozen and entry["feature_sha256"] != frozen):
            raise LocalError(f"{rid}: parent run schema differs from the inherited frozen contract")
        if list(local_inf.columns) != KEYS + list(entry["features"]) or local_inf["area_id"].duplicated().any():
            raise LocalError(f"{rid}: SOM inference matrix is not keys + the inherited feature order")
        gate_equal(f"{rid} SOM fitting rows", len(local_fit), expect(ctx, "launch_fit_rows"))
        gate_equal(f"{rid} SOM fitting areas", int(local_fit["area_id"].nunique()), expect(ctx, "launch_fit_areas"))
        gate_equal(f"{rid} SOM inference areas", len(local_inf), expect(ctx, "launch_inference_areas"))
        fb, ib = csv_bytes(local_fit), csv_bytes(local_inf)
        # serialized round-trip parity with the parent projection (values, NA masks, order, dtypes-as-text)
        for label, frame, raw in (("fit selection", local_fit, fb), ("inference", local_inf, ib)):
            import io

            text = {c: str for c in frame.columns if not pd.api.types.is_numeric_dtype(frame[c])}
            back = pd.read_csv(io.BytesIO(raw), float_precision="round_trip", low_memory=False, keep_default_na=False, na_values=[""], dtype=text)
            if not cl.same_frame(back, frame):
                raise LocalError(f"{rid}: serialized SOM {label} differs from the parent projection")
        tag = f"{arm}_h{horizon}"
        files[f"training/fit_selection_{tag}.csv"] = fb
        files[f"inference/inference_{tag}.csv"] = ib
        frames[(arm, horizon)] = (local_fit, local_inf)
        runs[rid] = {
            "arm": arm, "horizon": horizon, "training_arm": entry["training_arm"], "target_month": entry["target_month"],
            "features": list(entry["features"]), "feature_count": len(entry["features"]), "feature_sha256": entry["feature_sha256"],
            "training_dataset": dict(entry["training_dataset"]),
            "fit_selection": {"path": str(inputs / "training" / f"fit_selection_{tag}.csv"), "sha256": sha_bytes(fb), "rows": len(local_fit), "columns": local_fit.shape[1]},
            "fit_rows": len(local_fit), "fit_keys_sha256": osf.keys_sha256(local_fit), "fit_areas": int(local_fit["area_id"].nunique()),
            "fit_label_months": [ym(ford.min()), ym(ford.max())],
            "inference": {"path": str(inputs / "inference" / f"inference_{tag}.csv"), "sha256": sha_bytes(ib), "rows": len(local_inf), "columns": local_inf.shape[1]},
            "inference_keys_sha256": osf.keys_sha256(local_inf), "weather_inference": entry["weather_inference"],
            "parent_fit_selection": dict(entry["fit_selection"]), "parent_inference": dict(entry["inference"]),
        }
    base_ids = frames[(cl.BASELINE, 0)][1]["area_id"].tolist()
    for (arm, horizon), (fit, inf) in frames.items():
        if inf["area_id"].tolist() != base_ids:
            raise LocalError(f"{run_id(arm, horizon)}: SOM inference cohort differs across runs")
    for horizon in (6, 12):
        bf, bi = frames[(cl.BASELINE, horizon)]
        wf, wi = frames[(cl.WEATHER, horizon)]
        bcols = list(bi.columns)
        if not cl.same_frame(bf, wf) or list(wi.columns[: len(bcols)]) != bcols or not cl.same_frame(wi[bcols], bi):
            raise LocalError(f"H{horizon}: paired SOM fitting keys/targets/weights or baseline inference prefix differ")
    # inference cohort = parent April population cohort intersected with SOM; exclusions recorded, never invented
    population = read_csv(parent["ledgers"]["population"]["path"])
    pop_som = population[population["area_id"].isin(members)].sort_values("area_id", kind="mergesort").reset_index(drop=True)
    if sorted(base_ids) != pop_som["area_id"].tolist():
        raise LocalError("SOM inference areas differ from the parent April population cohort intersected with SOM")
    excluded = sorted(members - set(base_ids))
    gate_equal("SOM areas outside launch coverage", excluded, expect(ctx, "launch_excluded"))
    audit = ctx.parent_cap_audit(parent)
    row = audit[audit["country"] == COUNTRY]
    if len(row) != 1:
        raise LocalError(f"parent cap audit has no unique {COUNTRY} row")
    row = row.iloc[0]
    raw_total = float(pop_som["estimated_population"].sum())
    if not np.isclose(float(row["raw_population"]), raw_total, rtol=1e-12, atol=1e-6) or int(row["areas"]) != len(pop_som):
        raise LocalError("parent cap audit Somalia row does not describe the SOM inference cohort")
    pop_expected = expect(ctx, "population")
    if pop_expected is not None:
        got = {"country": COUNTRY, "raw": raw_total, "reference": float(row["reference_population"]), "cap_factor": float(row["cap_factor"]),
               "effective": round(float(row["effective_population"]), 2), "areas": int(row["areas"])}
        if got["country"] != pop_expected["country"] or got["areas"] != pop_expected["areas"] or got["raw"] != pop_expected["raw"] \
                or got["reference"] != pop_expected["reference"] or got["cap_factor"] != pop_expected["cap_factor"] \
                or abs(got["effective"] - pop_expected["effective"]) > 0.005:
            raise LocalError(f"Somalia population/cap {got} differs from the approved values {pop_expected}")
    audit_bytes = csv_bytes(audit)
    cap_ledger = audit[audit["country"] == COUNTRY].reset_index(drop=True).assign(parent_cap_audit_sha256=sha_bytes(audit_bytes),
                                                                                  parent_population_ledger_sha256=parent["ledgers"]["population"]["sha256"])
    hist_manifest = json.loads(Path(ctx.hist_manifest).read_text(encoding="utf-8"))
    cohort = pd.read_csv(hist_manifest["cohort"]["path"])
    cohort = cohort[cohort["area_id"].isin(members)]
    coverage = pd.DataFrame({"area_id": sorted(members)})
    hist_eval = cohort[cohort["eval_key"]].groupby("area_id").size()
    last = cohort.assign(o=cohort["year"] * 12 + cohort["month"] - 1).groupby("area_id")["o"].max()
    coverage["historical_label_keys"] = coverage["area_id"].map(cohort.groupby("area_id").size()).fillna(0).astype(int)
    coverage["historical_eval_keys"] = coverage["area_id"].map(hist_eval).fillna(0).astype(int)
    coverage["historical_last_label_month"] = coverage["area_id"].map(last).map(lambda o: ym(o) if pd.notna(o) else "")
    coverage["in_parent_april_population"] = coverage["area_id"].isin(pop_som["area_id"])
    coverage["in_launch_inference"] = coverage["area_id"].isin(base_ids)
    coverage["launch_status"] = np.where(coverage["in_launch_inference"], "covered",
                                         "outside launch coverage: no April 2026 row in the parent population ledger/inference cohort; population not invented")
    files["ledgers/population_april_2026_som.csv"] = csv_bytes(pop_som[["area_id", "estimated_population"]])
    files["ledgers/country_population_cap_audit_som.csv"] = csv_bytes(cap_ledger)
    files["ledgers/parent_country_population_cap_audit.csv"] = audit_bytes
    files["ledgers/som_launch_coverage.csv"] = csv_bytes(coverage)
    files["som_membership_area_ids.csv"] = csv_bytes(pd.DataFrame({"area_id": membership["area_ids"]}))
    checks.update({"inference_areas": len(base_ids), "excluded_areas": excluded, "fit_rows": {r: v["fit_rows"] for r, v in runs.items()},
                   "population_raw": raw_total, "cap_factor": float(row["cap_factor"]), "population_effective": float(row["effective_population"]),
                   "reference_population": float(row["reference_population"]), "paired_training_identical": True, "weather_prefix_equals_baseline": True})
    local = {
        "version": LAUNCH_VERSION, "status": "COMPLETE", "stage": "launch", "scope": ISO3, "model_scope": MODEL_SCOPE,
        "parent_model_contract_version": cl.VERSION,
        "parent": {"manifest": {"path": str(parent_path), "sha256": sha(parent_path)}, "weather": parent["weather"],
                   "population_ledger": parent["ledgers"]["population"]},
        "membership": membership_identity(membership),
        "contract": {"dir": str(inputs / "parent_contract"), "sha256": dict(parent["contract"]["sha256"])},
        "origin": parent["origin"], "targets": parent["targets"], "training_label_cutoff_exclusive": parent["training_label_cutoff_exclusive"],
        "inference_ipc_history_max_month": parent["inference_ipc_history_max_month"], "weight_rule": parent["weight_rule"],
        "runs": runs,
        "ledgers": {name.split("/")[-1].replace(".csv", ""): {"path": str(inputs / name), "sha256": sha_bytes(data)}
                    for name, data in files.items() if name.startswith("ledgers/")},
        "files": {name: {"path": str(inputs / name), "sha256": sha_bytes(data), "bytes": len(data)} for name, data in sorted(files.items())},
        "checks": checks, "local_code": local_code_identity(ctx), "params": dict(PARAMS),
        "frozen_configs_sha256": dict(cpf.FROZEN_CONFIG_SHA256), "frozen_runtime": dict(cpf.FROZEN_RUNTIME),
    }
    local["ledgers"]["population"] = local["ledgers"].pop("population_april_2026_som")
    data = canonical_json(local)
    path = launch_manifest_path(ctx)
    if write:
        assert_local_root(ctx.launch_results)
        for name, payload in files.items():
            write_once(inputs / name, payload)
        write_once(path, data)
        for rid, entry in runs.items():  # serialized parity of what fit_run will read
            for label in ("fit_selection", "inference"):
                if sha(entry[label]["path"]) != entry[label]["sha256"]:
                    raise LocalError(f"{rid}: written {label} bytes differ from the local manifest")
    elif path.exists() and path.read_bytes() != data:
        raise LocalError(f"{path} exists with different bytes (membership/spec/code/parent changed); use a new root")
    return {"parent": parent, "membership": membership, "local": local, "path": path, "sha256": sha_bytes(data), "audit": audit}


def launch_train(ctx: Ctx, prep: Mapping[str, object]) -> List[dict]:
    assert_local_root(ctx.launch_results)
    out = []
    scope = {}
    for arm, horizon in LAUNCH_RUNS:
        rid = run_id(arm, horizon)
        record = cl.fit_run(prep["path"], prep["local"], rid, Path(ctx.launch_results))
        fp, _ = cl.fingerprint(prep["path"], prep["local"], rid)
        if record["fingerprint"] != fp:
            raise LocalError(f"{rid}: fit record fingerprint differs from the local manifest fingerprint")
        run_dir = launch_run_dir(ctx, arm, horizon)
        scope[rid] = {"fingerprint": fp, "artifact_record_sha256": sha(run_dir / "artifact_record.json"),
                      "run_metadata_sha256": sha(run_dir / "run_metadata.json")}
        out.append({"run_id": rid, "fingerprint": fp})
        log(f"launch {rid}: complete record {fp[:12]}")
    write_json(Path(ctx.launch_results) / "scope" / "run_scope.json",
               {"local_version": LAUNCH_VERSION, "scope": ISO3, "model_scope": MODEL_SCOPE, "parent_model_contract_version": cl.VERSION,
                "local_manifest": {"path": str(prep["path"]), "sha256": prep["sha256"]}, "runs": scope,
                "note": "fit_run records keep the parent model-contract version; the hashed local manifest (bound in every fingerprint) "
                        "and this sidecar carry the local experiment identity"})
    return out


# --------------------------------------------------------------------------- historical reporting


def hist_predictions(ctx: Ctx, arm: str, horizon: int) -> pd.DataFrame:
    run_dir = hist_run_dir(ctx, arm, horizon)
    meta = json.loads((run_dir / "run_metadata.json").read_text())
    if meta.get("status") != "COMPLETE" or meta.get("local_version") != HIST_VERSION:
        raise LocalError(f"{run_id(arm, horizon)}: run is not a COMPLETE {HIST_VERSION} run")
    frames = [pd.read_csv(run_dir / "predictions" / f"predictions_{y}.csv", float_precision="round_trip") for y in YEARS]
    return pd.concat(frames, ignore_index=True)


def som_metric_rows(pred: pd.DataFrame, arm: str, horizon: int) -> List[dict]:
    rows = rpm.metric_rows(pred, run_id(arm, horizon), arm, horizon, regions=("global",))
    for row in rows:
        row["scope"] = ISO3
    return rows


def hist_delta_table(metrics: pd.DataFrame) -> pd.DataFrame:
    rows = rpm.delta_rows(metrics, cpf.ORACLE_ARM, cpf.BASELINE_ARM, ORACLE_H)
    base0 = metrics[(metrics["arm"] == cpf.BASELINE_ARM) & (metrics["horizon"] == 0)]
    for r in base0.itertuples():
        defined = pd.notna(r.value)
        rows.append({"horizon": 0, "scope": r.scope, "region": r.region, "period": r.period, "metric": r.metric,
                     "contrast": "shared H0 (no oracle fit at H0; the oracle view is the compact baseline)", "oracle_value": r.value,
                     "baseline_value": r.value, "delta": 0.0 if defined else None, "status": "shared_h0_zero" if defined else "undefined",
                     "reason": None if defined else f"baseline {r.reason or 'undefined'}", "n_rows": int(r.n_rows), "n_areas": int(r.n_areas),
                     "observed_3plus": int(r.observed_3plus), "oracle_predicted_3plus": int(r.predicted_3plus),
                     "baseline_predicted_3plus": int(r.predicted_3plus)})
    out = pd.DataFrame(rows)
    return out.sort_values(["horizon", "period", "metric"], kind="mergesort").reset_index(drop=True)


def fmt(value, digits=4) -> str:
    return "undefined" if value is None or pd.isna(value) else f"{value:.{digits}f}"


def hist_fitted_lists(ctx: Ctx) -> Dict[str, List[str]]:
    """Feature order of every saved booster (112); each run's boosters must agree with its recorded schema."""
    import xgboost as xgb

    out = {}
    for arm, horizon in HIST_RUNS:
        run_dir = hist_run_dir(ctx, arm, horizon)
        meta = json.loads((run_dir / "run_metadata.json").read_text())
        for year in YEARS:
            for target in osf.CUMULATIVE_TARGETS:
                booster = xgb.Booster()
                booster.load_model(str(run_dir / "batches" / str(year) / f"model_{target}.ubj"))
                if list(booster.feature_names) != meta["features"]:
                    raise LocalError(f"{run_id(arm, horizon)} {year} {target}: booster feature order differs from the run schema")
        out[run_id(arm, horizon)] = list(meta["features"])
    return out


def write_hist_codebook(ctx: Ctx, local: Mapping[str, object], fitted: Mapping[str, List[str]]) -> dict:
    out_dir = Path(ctx.hist_reports) / "model_run_codebook"
    out_dir.mkdir(parents=True, exist_ok=True)
    contract = Path(local["files"]["parent_contract/expected_feature_contract.csv"]["path"])
    if sha(contract) != local["files"]["parent_contract/expected_feature_contract.csv"]["sha256"]:
        raise LocalError("local copy of the historical contract differs from the local manifest")
    with open(contract, encoding="utf-8-sig", newline="") as fh:
        expected_rows = list(csv.DictReader(fh))
    runs = [run_id(a, h) for a, h in HIST_RUNS]
    positions = {r: {f: i + 1 for i, f in enumerate(fitted[r])} for r in runs}
    union = list(dict.fromkeys(f for r in runs for f in fitted[r]))
    keep = ["predictor", "group", "description", "unit", "source", "time_relative_to_origin", "formula", "missing_semantics", "input_type"]
    tail = ["horizons_months", "family", "source_variable", "base_source_definition", "definition_evidence", "limitations"]
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
        row["limitations"] = clean_limitations(base["limitations"])
        row["model_scope"] = MODEL_SCOPE
        row["fit_status"] = "fitted_somalia_local_all_112_boosters_checked"
        rows.append(row)
        exp = json.loads(base["expected_model_positions"])
        comparison.append({"predictor": name, "expected_model_positions": json.dumps(exp, sort_keys=True),
                           "actual_model_positions": json.dumps(act, sort_keys=True), "match": exp == act})
    for name in sorted(set(by_name) - set(union)):
        comparison.append({"predictor": name, "expected_model_positions": by_name[name]["expected_model_positions"], "actual_model_positions": "{}", "match": False})
    comp = pd.DataFrame(comparison)
    if not comp["match"].all() or len(union) != len(expected_rows):
        raise LocalError(f"actual fitted inputs differ from the contract for {int((~comp['match']).sum())} predictors")
    path = out_dir / "IPCCH_compact_climate_weather_oracle_somalia_local_model_run_codebook_en.csv"
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")
    comp.to_csv(out_dir / "expected_vs_actual_inputs.csv", index=False)
    index = pd.DataFrame([{"run_id": r, "arm": r.split("/")[0], "horizon_months": int(r.split("/")[1][:-1]), "actual_feature_count": len(fitted[r]),
                           "actual_feature_sha256": osf.list_sha256(fitted[r]),
                           "expected_feature_sha256": local["runs"][r]["feature_sha256"], "run_path": str(hist_run_dir(ctx, *_split(r)))} for r in runs])
    index["match"] = index["actual_feature_sha256"] == index["expected_feature_sha256"]
    index.to_csv(out_dir / "model_run_index.csv", index=False)
    if not index["match"].all():
        raise LocalError("a run's fitted feature hash differs from the inherited contract")
    return {"codebook": str(path), "sha256": sha(path), "rows": len(rows), "expected_rows": len(expected_rows),
            "expected_vs_actual": {"path": str(out_dir / "expected_vs_actual_inputs.csv"), "sha256": sha(out_dir / "expected_vs_actual_inputs.csv")},
            "model_run_index": {"path": str(out_dir / "model_run_index.csv"), "sha256": sha(out_dir / "model_run_index.csv")}}


def clean_limitations(text: str) -> str:
    """Drop only the obsolete expected-contract sentences; every scientific limitation is kept verbatim."""
    for sentence in CODEBOOK_EXPECTED_SENTENCES:
        text = text.replace(sentence, "")
    if "expected input" in text.lower() or "no fit verified" in text.lower():
        raise LocalError(f"unrecognized expected-contract wording in a codebook limitation: {text!r}")
    return text.strip()


def _split(rid: str) -> Tuple[str, int]:
    arm, h = rid.split("/")
    return arm, int(h[:-1])


def hist_report(ctx: Ctx) -> dict:
    local_path = hist_manifest_path(ctx)
    local = json.loads(local_path.read_text())
    out_dir = Path(ctx.hist_results) / "report"
    rows = []
    for arm, horizon in HIST_RUNS:
        rows += som_metric_rows(hist_predictions(ctx, arm, horizon), arm, horizon)
    metrics = pd.DataFrame(rows)
    deltas = hist_delta_table(metrics)
    undefined = metrics[metrics["value"].isna()].groupby(["arm", "horizon", "period", "metric", "reason"]).size().rename("cells").reset_index()
    written = {"metrics": save_table(metrics, out_dir / "som_metrics_long.csv"), "deltas": save_table(deltas, out_dir / "som_oracle_minus_baseline_deltas.csv"),
               "undefined": save_table(undefined, out_dir / "som_undefined_reasons.csv")}
    codebook = write_hist_codebook(ctx, local, hist_fitted_lists(ctx))
    report_md = write_hist_markdown(ctx, metrics, deltas, local)
    meta = {"local_version": HIST_VERSION, "scope": ISO3, "model_scope": MODEL_SCOPE, "parent_model_contract_version": cpf.VERSION,
            "local_manifest": {"path": str(local_path), "sha256": sha(local_path)}, "runs": {run_id(a, h): str(hist_run_dir(ctx, a, h)) for a, h in HIST_RUNS},
            "periods": [*map(str, YEARS), "pooled"], "metrics": list(osf.ORIGIN_METRICS),
            "contrast": f"{cpf.ORACLE_ARM} - {cpf.BASELINE_ARM} at H3/H6/H12; H0 shared (zero difference where defined)",
            "pairing": "sorted (area_id, year, month); identical keys and truths required", "evaluation_weights": "rows",
            "bootstrap": "not run (out of scope)", "outputs": written, "codebook": codebook,
            "report_md": {"path": str(report_md), "sha256": sha(report_md)}}
    write_json(out_dir / "comparison_metadata.json", meta)
    return meta


def write_hist_markdown(ctx: Ctx, metrics: pd.DataFrame, deltas: pd.DataFrame, local: Mapping[str, object]) -> Path:
    Path(ctx.hist_reports).mkdir(parents=True, exist_ok=True)
    names = list(osf.ORIGIN_METRICS)
    head = "| arm | period | n | areas | obs 3+ | " + " | ".join(METRIC_LABELS[m] for m in names) + " |"
    sep = "|---|---|---:|---:|---:|" + "---:|" * len(names)
    c = local["cohort"]
    lines = [f"# {HIST_VERSION}: Somalia-local compact features with and without the realized-weather oracle", "",
             f"Scope: canonical membership `iso3 == \"{ISO3}\"` ({local['membership']['n_areas']} areas); model scope: {MODEL_SCOPE} (every model "
             "refit on Somalia rows only). Evaluation keys: the frozen parent cohort intersected with SOM, "
             f"{c['eval_rows']} rows over {c['eval_union_areas']} areas (2022/2023/2024/2025: "
             + "/".join(str(c["eval_by_year"][str(y)] if str(y) in c["eval_by_year"] else c["eval_by_year"][y]) for y in YEARS) + ").",
             "Machine-readable sources: `results/experiments/" + HIST_VERSION + "/report/`. Values are computed from saved unrounded predictions; "
             "the independent verifier replays them with scikit-learn.", "",
             "The oracle arm appends realized monthly precipitation/temperature anomalies at O+1..O+min(H,6) as a perfect forecast: it measures "
             "the value of ideal weather information and is not CDS forecast skill. Units: accuracies/precision/recall are row shares; MAE 3+ "
             "is a normalized population share; ordinal MAE is in phase steps; differences are raw differences. Evaluation weights are rows.", ""]
    for h in (0, 3, 6, 12):
        lines += [f"## H = {h} months", "", head, sep]
        part = metrics[metrics["horizon"] == h]
        for (arm, period), g in part.groupby(["arm", "period"], sort=True):
            g = g.set_index("metric")
            first = g.iloc[0]
            lines.append(f"| {arm} | {period} | {first.n_rows} | {first.n_areas} | {first.observed_3plus} | " + " | ".join(fmt(g.loc[m, "value"]) for m in names) + " |")
        d = deltas[deltas["horizon"] == h]
        for period, g in d.groupby("period", sort=True):
            g = g.set_index("metric")
            label = "**oracle - baseline**" if h else "**shared H0 difference**"
            lines.append(f"| {label} | {period} | | | | " + " | ".join(fmt(g.loc[m, "delta"]) for m in names) + " |")
        lines.append("")
    lines += ["## Limits", "", "- Single seed (42) and one fit per annual block: differences are point estimates without intervals; no bootstrap.",
              "- Fixed global hyperparameters may suit the smaller Somalia sample imperfectly; no tuning was done.",
              "- Undefined metrics stay undefined with their reasons (`report/som_undefined_reasons.csv`).", ""]
    path = Path(ctx.hist_reports) / "report.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


# --------------------------------------------------------------------------- launch reporting


def launch_local(ctx: Ctx) -> Tuple[Path, dict]:
    path = launch_manifest_path(ctx)
    manifest = json.loads(path.read_text())
    if manifest.get("version") != LAUNCH_VERSION or manifest.get("status") != "COMPLETE":
        raise LocalError("local launch manifest is not COMPLETE")
    for name, item in manifest["files"].items():
        if sha(item["path"]) != item["sha256"]:
            raise LocalError(f"local launch input {name} changed since the local manifest")
    return path, manifest


def launch_predictions(ctx: Ctx, manifest: Mapping[str, object], arm: str, horizon: int) -> pd.DataFrame:
    path = launch_run_dir(ctx, arm, horizon) / "predictions_raw.csv"
    frame = pd.read_csv(path, float_precision="round_trip")
    want = pd.read_csv(manifest["ledgers"]["population"]["path"])["area_id"].tolist()
    frame = frame.sort_values("area_id", kind="mergesort").reset_index(drop=True)
    if frame["area_id"].tolist() != want:
        raise LocalError(f"{path} is not exactly the SOM inference cohort")
    return frame


def launch_area_table(ctx: Ctx, manifest: Mapping[str, object]) -> pd.DataFrame:
    population = pd.read_csv(manifest["ledgers"]["population"]["path"], float_precision="round_trip").sort_values("area_id").reset_index(drop=True)
    cap = read_csv(manifest["ledgers"]["country_population_cap_audit_som"]["path"])
    if len(cap) != 1 or cap.loc[0, "country"] != COUNTRY:
        raise LocalError("local cap ledger is not the single Somalia row")
    factor = float(cap.loc[0, "cap_factor"])
    frames = []
    for arm, horizon in cl.DISPLAY:
        src_arm, src_h = cl.source_run(arm, horizon)
        pred = launch_predictions(ctx, manifest, src_arm, src_h)
        if not np.array_equal(pred["area_id"].to_numpy(), population["area_id"].to_numpy()):
            raise LocalError("prediction and population keys differ")
        rep = cl.repaired_shares(pred[list(osf.PRED_COLUMNS)].to_numpy(dtype=float))
        f = pd.DataFrame({"version": LAUNCH_VERSION, "scope": ISO3, "model_scope": MODEL_SCOPE, "display_arm": arm, "source_run_id": run_id(src_arm, src_h),
                          "shared_h0_fit": horizon == 0, "horizon": horizon, "origin_month": ym(cl.ORIGIN_ORD), "target_month": pred["target_month"].to_numpy(),
                          "area_id": pred["area_id"].to_numpy(), "country": COUNTRY, "iso3": ISO3, "population_reference_month": ym(cl.ORIGIN_ORD),
                          "population_raw": population["estimated_population"].to_numpy(dtype=float), "cap_factor": factor})
        f["cap_applied"] = f["cap_factor"] < 1.0
        f["population_effective"] = f["population_raw"] * f["cap_factor"]
        for c in osf.PRED_COLUMNS:
            f[f"raw_{c}"] = pred[c].to_numpy(dtype=float)
        f["overall_phase_pred_raw"] = pred["overall_phase_pred"].to_numpy()
        f["crisis_raw_phase3plus"] = f["overall_phase_pred_raw"] >= 3
        f["repair_negative_component"] = rep["any_negative_component"]
        f["repair_clipped"] = rep["any_clipped"]
        f["repair_normalization_sum"] = rep["normalization_sum"]
        shares = rep["shares"]
        for i, k in enumerate(cl.PHASES):
            f[f"share_phase{k}"] = shares[:, i]
        f["share_p3plus"] = shares[:, 2:].sum(axis=1)
        f["share_p4plus"] = shares[:, 3:].sum(axis=1)
        for kind in ("raw", "effective"):
            pop = f[f"population_{kind}"].to_numpy()
            for k in cl.PHASES:
                f[f"count_{kind}_phase{k}"] = f[f"share_phase{k}"].to_numpy() * pop
            f[f"count_{kind}_p3plus"] = f[[f"count_{kind}_phase{k}" for k in (3, 4, 5)]].sum(axis=1)
            f[f"count_{kind}_p4plus"] = f[[f"count_{kind}_phase{k}" for k in (4, 5)]].sum(axis=1)
        frames.append(f)
    return pd.concat(frames, ignore_index=True)


def launch_population_tables(area: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    som = cl.aggregate(area, "country")
    som.insert(1, "scope", ISO3)
    som.insert(2, "model_scope", MODEL_SCOPE)
    som["version"] = LAUNCH_VERSION
    area_diff = cl.paired_differences(area, ["area_id"]).assign(version=LAUNCH_VERSION, scope=ISO3)
    som_diff = cl.paired_differences(som, ["country"]).assign(version=LAUNCH_VERSION, scope=ISO3)
    return {"area_population_predictions": area, "som_population_summary": som,
            "area_population_paired_differences": area_diff, "som_population_paired_differences": som_diff}


def _text_inside(fig) -> List[str]:
    """Visible titles/legend/colorbar labels must lie fully inside the canvas (no clipped titles)."""
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    box = fig.bbox
    texts = [fig._suptitle] if fig._suptitle is not None else []
    for ax in fig.axes:
        texts += [ax.title, ax.xaxis.label]
        if ax.axison:
            texts += [t for t in ax.get_xticklabels() + ax.get_yticklabels() if t.get_visible()]
    for leg in fig.legends:
        texts += list(leg.get_texts())
    bad = []
    for t in texts:
        if t is None or not t.get_text().strip() or not t.get_visible():
            continue
        e = t.get_window_extent(renderer)
        if e.x0 < box.x0 - 0.5 or e.x1 > box.x1 + 0.5 or e.y0 < box.y0 - 0.5 or e.y1 > box.y1 + 0.5:
            bad.append(t.get_text())
    return bad


def write_launch_maps(ctx: Ctx, area: pd.DataFrame) -> dict:
    """Seven SOM maps: five categorical (raw class >= 3), 2x3 repaired P3+ shares, 1x2 CDS-minus-baseline differences."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib as mpl
    import matplotlib.pyplot as plt

    from ipcch import alert_risk_maps as arm
    from ipcch import launch_visualizations as lv

    _, listed_cmap, patch = arm._require_matplotlib()
    boundaries = ctx.load_boundaries()
    vis_dir, fig_dir = Path(ctx.launch_results) / "visualizations", Path(ctx.launch_reports) / "figures"
    vis_dir.mkdir(parents=True, exist_ok=True)
    fig_dir.mkdir(parents=True, exist_ok=True)
    n = int(area[(area["display_arm"] == cl.BASELINE) & (area["horizon"] == 0)]["area_id"].nunique())
    meta = {"scope": ISO3, "model_scope": MODEL_SCOPE, "local_version": LAUNCH_VERSION,
            "geometry": {Path(p).suffix: {"path": str(p), "sha256": sha(p)} for p in ctx.geometry_files}, "basemap": "none (no download)",
            "style": "inherited launch map style (green/red crisis, YlOrRd shares 0-100, RdBu_r symmetric differences)", "figures": {}}

    def check_and_save(fig, path, dpi):
        bad = _text_inside(fig)
        if bad:
            plt.close(fig)
            raise LocalError(f"{path.name}: text outside the canvas {bad}")
        fig.savefig(path, dpi=dpi)
        plt.close(fig)

    for arm_, horizon in LAUNCH_RUNS:
        sub = area[(area["display_arm"] == arm_) & (area["horizon"] == horizon)][["area_id", "overall_phase_pred_raw", "target_month"]]
        pred = sub.rename(columns={"overall_phase_pred_raw": "overall_phase_pred"})
        join = lv.join_for_two_panel(pred, pred.iloc[0:0], boundaries)
        if join.unmatched_prediction or join.mapped_predicted_count != n:
            raise LocalError(f"{run_id(arm_, horizon)}: map join covers {join.mapped_predicted_count}/{n} areas, unmatched {join.unmatched_prediction[:5]}")
        lv._ensure_crisis_columns(join)
        target = str(sub["target_month"].iloc[0])
        name = f"crisis_categorical_{arm_}_{horizon}m_{target}"
        fig, ax = plt.subplots(1, 1, figsize=(7.5, 8.5))
        title = f"Predicted crisis (phase >= 3), target {target}, n={n} areas"
        lv._panel(ax, join.predicted_joined, "predicted_crisis", title, listed_cmap, False, True)
        fig.legend(handles=[patch(color=arm.NO_ALERT_COLOR, label="No crisis (phase 1-2)"), patch(color=arm.ALERT_COLOR, label="Crisis (phase 3+)")],
                   loc="lower center", ncol=2)
        shared = " (shared H0 fit)" if horizon == 0 else ""
        sup = f"IPCCH Somalia local launch, origin 2026-04: {arm_} H{horizon}{shared}\nPredicted-only view; actual-outcome panels are excluded by design."
        fig.suptitle(sup, fontsize=11)
        fig.subplots_adjust(left=0.04, right=0.96, bottom=0.09, top=0.86)
        fig_path = fig_dir / f"{name}.png"
        check_and_save(fig, fig_path, 300)
        record = pred.assign(predicted_crisis=pred["overall_phase_pred"] >= 3, run_id=run_id(arm_, horizon), scope=ISO3)
        rec_path = vis_dir / f"{name}.csv"
        record.to_csv(rec_path, index=False)
        meta["figures"][name] = {"figure": str(fig_path), "figure_sha256": sha(fig_path), "record": str(rec_path), "record_sha256": sha(rec_path),
                                 "value": "raw-derived overall_phase_pred >= 3", "mapped_areas": join.mapped_predicted_count, "run_id": run_id(arm_, horizon),
                                 "target_month": target, "panel_title": title, "suptitle": sup}
    joined, share_rows = {}, []
    for arm_, horizon in cl.DISPLAY:
        sub = area[(area["display_arm"] == arm_) & (area["horizon"] == horizon)][["area_id", "share_p3plus", "target_month", "source_run_id"]].copy()
        sub["p3plus_percent"] = sub["share_p3plus"] * 100.0
        g = boundaries.rename(columns={"area_id": "join_key"}).merge(sub.assign(join_key=arm.normalize_area_id(sub["area_id"])), on="join_key",
                                                                     how="inner", validate="one_to_one")
        if len(g) != n:
            raise LocalError("continuous map join does not cover the SOM inference cohort")
        joined[(arm_, horizon)] = g
        share_rows.append(sub.assign(display_arm=arm_, horizon=horizon, scope=ISO3))
    fig, axes = plt.subplots(2, 3, figsize=(15, 12))
    for i, arm_ in enumerate((cl.BASELINE, cl.WEATHER)):
        for j, horizon in enumerate((0, 6, 12)):
            g = joined[(arm_, horizon)]
            shared = " (shared H0 fit)" if horizon == 0 else ""
            cl._continuous_panel(axes[i, j], g, "p3plus_percent", f"{arm_} H{horizon}{shared}\ntarget {g['target_month'].iloc[0]}", "YlOrRd", 0.0, 100.0)
    sm = mpl.cm.ScalarMappable(norm=mpl.colors.Normalize(0, 100), cmap="YlOrRd")
    fig.colorbar(sm, ax=axes, orientation="horizontal", fraction=0.035, pad=0.04, shrink=0.6).set_label("Predicted repaired Phase 3+ population share (%)")
    fig.suptitle("Somalia local launch (origin 2026-04): predicted Phase 3+ share by area\nprediction summaries, not scores", fontsize=13, weight="bold")
    p_path = fig_dir / "p3plus_share_comparison_2x3.png"
    check_and_save(fig, p_path, 200)
    rec = vis_dir / "p3plus_share_comparison_2x3.csv"
    pd.concat(share_rows, ignore_index=True).to_csv(rec, index=False, float_format="%.17g")
    meta["figures"]["p3plus_share_comparison_2x3"] = {"figure": str(p_path), "figure_sha256": sha(p_path), "record": str(rec), "record_sha256": sha(rec),
                                                      "value": "repaired share_p3plus x 100 (percent)", "color_limits": [0, 100], "mapped_areas": n}
    diffs = []
    for horizon in (6, 12):
        d = joined[(cl.WEATHER, horizon)][["area_id", "p3plus_percent"]].merge(
            joined[(cl.BASELINE, horizon)][["area_id", "p3plus_percent", "geometry", "target_month"]], on="area_id", suffixes=("_cds", "_baseline"),
            validate="one_to_one")
        if len(d) != n:
            raise LocalError(f"difference map H{horizon} does not cover the SOM inference cohort")
        d["p3plus_pp_difference"] = d["p3plus_percent_cds"] - d["p3plus_percent_baseline"]
        diffs.append((horizon, d))
    limit = max(float(np.abs(d["p3plus_pp_difference"]).max()) for _, d in diffs) or 1.0
    fig, axes = plt.subplots(1, 2, figsize=(12, 8))
    gpd = arm._require_geopandas()
    for ax, (horizon, d) in zip(axes, diffs):
        g = gpd.GeoDataFrame(d, geometry="geometry", crs=boundaries.crs)
        cl._continuous_panel(ax, g, "p3plus_pp_difference", f"CDS weather minus baseline, H{horizon}\ntarget {d['target_month'].iloc[0]}", "RdBu_r", -limit, limit)
    sm = mpl.cm.ScalarMappable(norm=mpl.colors.Normalize(-limit, limit), cmap="RdBu_r")
    fig.colorbar(sm, ax=axes, orientation="horizontal", fraction=0.05, pad=0.05, shrink=0.7).set_label(
        "Difference in predicted repaired Phase 3+ share (percentage points)")
    fig.suptitle("Somalia local launch: CDS-weather minus baseline\nprediction differences, not performance", fontsize=12, weight="bold")
    d_path = fig_dir / "p3plus_share_difference_1x2.png"
    check_and_save(fig, d_path, 200)
    rec = vis_dir / "p3plus_share_difference_1x2.csv"
    pd.concat([d.drop(columns="geometry").assign(horizon=h, scope=ISO3) for h, d in diffs], ignore_index=True).to_csv(rec, index=False, float_format="%.17g")
    meta["figures"]["p3plus_share_difference_1x2"] = {"figure": str(d_path), "figure_sha256": sha(d_path), "record": str(rec), "record_sha256": sha(rec),
                                                      "value": "(CDS - baseline) repaired share_p3plus x 100 (percentage points)",
                                                      "color_limits": [-limit, limit], "h0_difference": 0.0, "mapped_areas": n}
    write_json(vis_dir / "figure_metadata.json", meta)
    return meta


def write_launch_codebook(ctx: Ctx, manifest: Mapping[str, object]) -> dict:
    """Actual fitted-input codebook from all 20 boosters; training (realized oracle) and inference (CDS) fields from the contract."""
    import xgboost as xgb

    with open(Path(manifest["contract"]["dir"]) / "expected_feature_contract.csv", encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    actual = {}
    for arm, horizon in LAUNCH_RUNS:
        lists = []
        for target in osf.CUMULATIVE_TARGETS:
            booster = xgb.Booster()
            booster.load_model(str(launch_run_dir(ctx, arm, horizon) / f"model_{target}.ubj"))
            lists.append(list(booster.feature_names))
        if any(lst != lists[0] for lst in lists) or lists[0] != manifest["runs"][run_id(arm, horizon)]["features"]:
            raise LocalError(f"{run_id(arm, horizon)}: boosters disagree with the run schema")
        actual[run_id(arm, horizon)] = lists[0]
    doc_fields = ("training_source", "inference_source", "training_formula", "inference_formula", "training_missing_semantics",
                  "inference_missing_semantics", "training_reference_period", "inference_reference_period", "training_spatial_definition",
                  "inference_spatial_definition")
    out_rows = []
    for r in rows:
        name = r["predictor"]
        row = {k: r[k] for k in ("position", "predictor", "group", "description", "unit", "source", "time_relative_to_origin", "formula",
                                 "missing_semantics", "input_type")}
        positions = {rid: feats.index(name) + 1 for rid, feats in actual.items() if name in feats}
        for rid in actual:
            row[rid.replace("/", "_")] = "true" if rid in positions else "false"
            row[f"{rid.replace('/', '_')}_expanded_count"] = 1 if rid in positions else 0
        row["actual_model_columns"] = json.dumps([name]) if positions else "[]"
        row["actual_model_positions"] = json.dumps(positions, separators=(",", ":"))
        expected = json.loads(r["expected_model_positions"]) if r["expected_model_positions"] else {}
        row["expected_matches_actual"] = expected == positions
        for k in ("family", "source_variable", "base_source_definition", "definition_evidence"):
            row[k] = r.get(k, "")
        row["limitations"] = clean_limitations(r.get("limitations", ""))
        for k in doc_fields:
            row[k] = r.get(k, "")
        row["model_scope"] = MODEL_SCOPE
        row["fit_status"] = "fitted_somalia_local_all_20_boosters_checked"
        out_rows.append(row)
    table = pd.DataFrame(out_rows)
    if not table["expected_matches_actual"].all():
        raise LocalError("actual fitted launch inputs differ from the contract")
    if table["limitations"].str.contains("expected input|no fit verified", case=False, regex=True).any():
        raise LocalError("codebook still carries expected-contract wording")
    path = Path(ctx.launch_reports) / "model_run_codebook_en.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(path, index=False, encoding="utf-8-sig")
    return {"path": str(path), "sha256": sha(path), "rows": len(table), "runs": {k: len(v) for k, v in actual.items()}}


def write_launch_summary(ctx: Ctx, manifest: Mapping[str, object], tables: Mapping[str, pd.DataFrame]) -> Path:
    som = tables["som_population_summary"]
    diff = tables["som_population_paired_differences"]
    chk = manifest["checks"]
    lines = [f"# {LAUNCH_VERSION}: Somalia-local April 2026-origin compact launch with CDS forecast weather", "",
             f"Scope: SOM; model scope: {MODEL_SCOPE} (all 20 models refit on {chk['fit_rows'][run_id(cl.BASELINE, 0)]} Somalia observations with labels "
             f"before April 2026). Prediction summaries only (no scoring, bootstrap or SHAP). Inference covers {chk['inference_areas']} of "
             f"{manifest['membership']['n_areas']} member areas; outside launch coverage: {chk['excluded_areas']} (no April 2026 row in the parent "
             "population ledger/inference cohort; its population is not invented; see `inputs/ledgers/som_launch_coverage.csv`).", "",
             f"Fixed April 2026 population: raw {chk['population_raw']:,.0f}; inherited country cap factor {chk['cap_factor']:.17g} (reference "
             f"{chk['reference_population']:,.0f}); effective {chk['population_effective']:,.2f}. Every arm/target uses the same area populations.", "",
             "## Somalia predicted population (capped denominators; repaired disjoint shares)", "",
             "| arm | H | target | population | P3+ share | P3+ people | P4+ share | P4+ people |", "|---|---:|---|---:|---:|---:|---:|---:|"]
    for _, r in som.sort_values(["display_arm", "horizon"]).iterrows():
        lines.append(f"| {r.display_arm} | {r.horizon} | {r.target_month} | {r.population_effective:,.0f} | {r.share_effective_p3plus:.4f} | "
                     f"{r.count_effective_p3plus:,.0f} | {r.share_effective_p4plus:.4f} | {r.count_effective_p4plus:,.0f} |")
    lines += ["", "## CDS weather minus baseline (Somalia)", "", "| H | target | delta P3+ share | delta P3+ people | delta P4+ share |", "|---:|---|---:|---:|---:|"]
    for _, r in diff.sort_values("horizon").iterrows():
        lines.append(f"| {r.horizon} | {r.target_month} | {r.delta_share_effective_p3plus:+.5f} | {r.delta_count_effective_p3plus:+,.0f} | {r.delta_share_effective_p4plus:+.5f} |")
    lines += ["", "## Definitions and limits", "",
              "- Raw cumulative predictions and the canonical class (highest phase with unrounded score >= 0.2) are unchanged; tables use "
              "reporting-only repaired shares (cumulative differences, clip to [0,1], normalize). Categorical maps use the raw class.",
              "- Weather arm: trained on realized compact oracle anomalies; inferred on the accepted ECMWF system51 April 2026 CDS cube "
              "(May-October). Inherited limits of that weather stage (October (start,end] temperature window, raw signed precipitation "
              "endpoints) apply unchanged; no new retrieval.",
              "- Fixed global hyperparameters may suit the smaller Somalia sample imperfectly; 2027 targets have every year flag 0; inherited "
              "population is not a vintage certification. H0 is one shared fit; its difference is 0 by construction.", ""]
    path = Path(ctx.launch_reports) / "launch_summary.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def launch_report(ctx: Ctx) -> dict:
    _, manifest = launch_local(ctx)
    area = launch_area_table(ctx, manifest)
    tables = launch_population_tables(area)
    pop_dir = Path(ctx.launch_results) / "population"
    written = {name: save_table(t, pop_dir / f"{name}.csv") for name, t in tables.items()}
    copy_dir = Path(ctx.launch_reports) / "population"
    copy_dir.mkdir(parents=True, exist_ok=True)
    for name in ("som_population_summary", "som_population_paired_differences"):
        (copy_dir / f"{name}.csv").write_bytes((pop_dir / f"{name}.csv").read_bytes())
    maps = write_launch_maps(ctx, area)
    codebook = write_launch_codebook(ctx, manifest)
    summary = write_launch_summary(ctx, manifest, tables)
    out = {"population": written, "maps": maps, "codebook": codebook, "summary": {"path": str(summary), "sha256": sha(summary)}}
    write_json(Path(ctx.launch_results) / "report_outputs.json", out)
    return out


# --------------------------------------------------------------------------- independent verification


def _close(a, b, atol, rtol=0.0) -> bool:
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    return a.shape == b.shape and np.array_equal(np.isnan(a), np.isnan(b)) and np.allclose(a[~np.isnan(a)], b[~np.isnan(b)], atol=atol, rtol=rtol)


def replayed_class_problems(label: str, pred: pd.DataFrame, replayed: Mapping[str, np.ndarray], threshold: float) -> List[str]:
    """Classes of the RELOADED raw predictions must equal the saved classes exactly (1e-6 raw tolerance can cross 0.2)."""
    if set(replayed) != set(osf.PRED_COLUMNS):
        return [f"{label}: not every cumulative regressor was replayed"]
    frame = pd.DataFrame({c: np.asarray(replayed[c], dtype=float) for c in osf.PRED_COLUMNS})
    out = []
    if not np.array_equal(legacy.classes(frame, threshold), pred["overall_phase_pred"].to_numpy()):
        out.append(f"{label}: classes of the reloaded predictions differ from the saved classes")
    if not np.array_equal(legacy.classes(pred, threshold), pred["overall_phase_pred"].to_numpy()):
        out.append(f"{label}: saved classes differ from the unrounded >= threshold rule")
    return out


def expected_metric_status(part: pd.DataFrame) -> Dict[str, Tuple[str, Optional[str]]]:
    """Independent undefined conditions with the canonical status/reason of each of the eight metrics (rows, no weights)."""
    if len(part) == 0:
        return {m: ("unavailable", "no eligible samples") for m in osf.ORIGIN_METRICS}
    observed = part["overall_phase"].to_numpy(dtype=float) >= 3
    predicted = part["overall_phase_pred"].to_numpy(dtype=float) >= 3
    truth = part["phase3_worse"].to_numpy(dtype=float)
    out = {m: ("ok", None) for m in osf.ORIGIN_METRICS}
    if not predicted.any():
        out["precision_phase3plus"] = ("unavailable", "zero predicted phase3plus denominator")
    if not observed.any():
        out["sensitivity_phase3plus"] = ("unavailable", "zero observed phase3plus denominator")
    if out["precision_phase3plus"][0] != "ok" or out["sensitivity_phase3plus"][0] != "ok":
        out["f2_phase3plus"] = ("unavailable", "precision or recall unavailable")
    elif not (observed & predicted).any():
        out["f2_phase3plus"] = ("unavailable", "zero f2 denominator")
    if len(truth) < 2:
        out["r2_phase3plus"] = ("unavailable", "fewer than two valid samples")
    elif np.unique(truth).size < 2:
        out["r2_phase3plus"] = ("unavailable", "constant target")
    return out


def _text(value) -> Optional[str]:
    return None if value is None or (isinstance(value, float) and np.isnan(value)) or str(value) == "" else str(value)


def _same_value(a, b, atol=1e-12) -> bool:
    a = np.nan if a is None or pd.isna(a) else float(a)
    b = np.nan if b is None or pd.isna(b) else float(b)
    return np.isnan(a) == np.isnan(b) and (np.isnan(a) or abs(a - b) <= atol)


def _recorded(problems: List[str], label: str, item: Mapping[str, object], canonical: Path) -> None:
    """A report output must sit at its canonical path, exist and match its recorded sha256."""
    if item is None or Path(item.get("path", "")) != Path(canonical) or not Path(canonical).exists() or sha(canonical) != item.get("sha256"):
        problems.append(f"{label}: missing, not at {canonical}, or differs from its recorded sha256")


HIST_REPORT_FILES = ("som_metrics_long.csv", "som_oracle_minus_baseline_deltas.csv", "som_undefined_reasons.csv", "comparison_metadata.json")
HIST_CODEBOOK = "IPCCH_compact_climate_weather_oracle_somalia_local_model_run_codebook_en.csv"
LAUNCH_TABLES = ("area_population_predictions", "som_population_summary", "area_population_paired_differences", "som_population_paired_differences")
LAUNCH_REPORT_COPIES = ("som_population_summary", "som_population_paired_differences")


def verify_hist(ctx: Ctx, problems: List[str], checks: dict) -> None:
    import xgboost as xgb

    prep = hist_prepare(ctx, write=False)  # parent manifest/cohort/contract + local manifest byte identity
    path = prep["path"]
    if not path.exists():
        problems.append("historical local manifest missing")
        return
    for name, item in prep["local"]["files"].items():
        if not Path(item["path"]).exists() or sha(item["path"]) != item["sha256"]:
            problems.append(f"historical local input {name} missing or changed")
    sel = prep["selection"]
    members = prep["membership"]["area_ids"]
    preds, fit_digests = {}, {}
    for arm, horizon in HIST_RUNS:
        rid = run_id(arm, horizon)
        inputs = hist_localize(ctx, prep, ctx.load_hist_inputs(hist_args(ctx, arm, horizon)), arm, horizon)
        data, features = inputs["data"], list(inputs["features"])
        run_dir = hist_run_dir(ctx, arm, horizon)
        required = [run_dir / "run_metadata.json", run_dir / "metrics" / "metrics_overall.csv", *(run_dir / "predictions" / f"predictions_{y}.csv" for y in YEARS)]
        missing = [str(p) for p in required if not p.exists()]
        if missing:
            problems.append(f"{rid}: mandatory run outputs missing {missing}")
            continue
        meta = json.loads((run_dir / "run_metadata.json").read_text())
        if meta.get("status") != "COMPLETE" or meta.get("fingerprint") != inputs["fingerprint"] or meta.get("local_version") != HIST_VERSION \
                or meta.get("local_manifest", {}).get("sha256") != prep["sha256"]:
            problems.append(f"{rid}: run metadata status/local fingerprint/version/local manifest differs")
        if meta["features"] != features or any(meta.get(k) != v for k, v in PARAMS.items()):
            problems.append(f"{rid}: run schema or fixed parameters differ")
        targets = independent_targets(data)
        fitter_targets = inputs["targets"][list(osf.CUMULATIVE_TARGETS)].to_numpy(dtype=float)
        position = pd.MultiIndex.from_frame(data[KEYS])
        if sorted(b["block_year"] for b in meta["batches"]) != list(YEARS):
            problems.append(f"{rid}: annual blocks incomplete")
        frames = []
        for record in meta["batches"]:
            year = record["block_year"]
            bdir = run_dir / "batches" / str(year)
            disk = json.loads((bdir / "batch_record.json").read_text())
            if disk != json.loads(json.dumps(record)) or disk["fingerprint"] != inputs["fingerprint"]:
                problems.append(f"{rid} {year}: batch record differs from run metadata/local fingerprint")
            if set(disk["artifacts"]) != set(osf.REQUIRED_BATCH_ARTIFACTS):
                problems.append(f"{rid} {year}: artifact inventory incomplete")
            for name, d in disk["artifacts"].items():
                checks["artifacts_rehashed"] += 1
                if not (bdir / name).exists() or sha(bdir / name) != d:
                    problems.append(f"{bdir / name}: missing or sha256 mismatch")
            origin, cutoff = year * 12 - horizon, year * 12 - max(horizon, 1)
            fk = pd.read_csv(bdir / "fit_keys.csv.gz", float_precision="round_trip")
            want_fit, _ = expected_hist_fit(data, sel["share_valid"], year, horizon)
            ford = fk["year"].to_numpy() * 12 + fk["month"].to_numpy() - 1
            if not fk[KEYS].equals(want_fit) or not fk["area_id"].isin(members).all():
                problems.append(f"{rid} {year}: fit keys are not the complete SOM valid set <= {ym(cutoff)}")
            if len(fk) == 0 or ford.max() > cutoff or not np.array_equal(fk["age_months"].to_numpy(), origin - ford) \
                    or not np.allclose(fk["sample_weight"].to_numpy(), 0.5 ** ((origin - ford) / 24.0), rtol=0, atol=1e-15):
                problems.append(f"{rid} {year}: fit cutoff/age/weight check failed")
            rows = position.get_indexer(pd.MultiIndex.from_frame(fk[KEYS]))
            # the fitter's own target matrix on every fitting row against the independent share normalization
            if (rows < 0).any() or not np.isfinite(targets[rows]).all() or not _close(fitter_targets[rows], targets[rows], 1e-12):
                problems.append(f"{rid} {year}: fitter targets on fitting rows differ from the independent normalization")
            checks["fit_rows_checked"] += len(fk)
            fit_digests.setdefault((horizon, year), {})[rid] = osf.keys_sha256(fk, KEYS + ["age_months", "sample_weight"])
            pred = pd.read_csv(bdir / "predictions.csv", float_precision="round_trip")
            want_eval = sel["eval_keys"][sel["eval_keys"]["year"] == year].reset_index(drop=True)
            if not pred[KEYS].equals(want_eval):
                problems.append(f"{rid} {year}: evaluation keys are not the complete SOM frozen keys")
                continue
            prow = position.get_indexer(pd.MultiIndex.from_frame(pred[KEYS]))
            if not np.array_equal(data["overall_phase"].to_numpy(dtype=float)[prow], pred["overall_phase"].to_numpy(dtype=float)):
                problems.append(f"{rid} {year}: truth differs from the reported phase")
            if not _close(targets[prow], pred[list(osf.CUMULATIVE_TARGETS)].to_numpy(), 1e-12):
                problems.append(f"{rid} {year}: normalized targets differ from the independent normalization")
            X = data.iloc[prow][features]
            replayed = {}
            for target, column in zip(osf.CUMULATIVE_TARGETS, osf.PRED_COLUMNS):
                booster = xgb.Booster()
                booster.load_model(str(bdir / f"model_{target}.ubj"))
                if list(booster.feature_names) != features:
                    problems.append(f"{rid} {year} {target}: booster feature order differs")
                again = booster.predict(xgb.DMatrix(X, feature_names=features)).astype(float)
                diff = float(np.max(np.abs(again - pred[column].to_numpy(dtype=float))))
                checks["max_model_replay_abs_diff"] = max(checks["max_model_replay_abs_diff"], diff)
                if not diff <= 1e-6:
                    problems.append(f"{rid} {year} {target}: reloaded model differs by {diff}")
                replayed[column] = again
                checks["models_reloaded"] += 1
            problems.extend(replayed_class_problems(f"{rid} {year}", pred, replayed, PARAMS["phase_threshold"]))
            saved_year = pd.read_csv(run_dir / "predictions" / f"predictions_{year}.csv", float_precision="round_trip")
            if not saved_year.equals(pred):
                problems.append(f"{rid} {year}: run-level predictions differ from the batch predictions")
            frames.append(pred)
            checks["batches"] += 1
        if len(frames) == len(YEARS):
            preds[(arm, horizon)] = pd.concat(frames, ignore_index=True)
        del inputs, data
        log(f"verify historical {rid}: {len(problems)} problems so far")
    for (h, year), d in fit_digests.items():
        if len(set(d.values())) != 1:
            problems.append(f"H{h} {year}: fitting keys/ages/weights differ across arms")
    first = None
    for key, pred in preds.items():
        part = pred[KEYS + ["overall_phase", "phase3_worse"]].sort_values(KEYS).reset_index(drop=True)
        if first is None:
            first = part
        elif not part.equals(first):
            problems.append(f"{run_id(*key)}: evaluation keys/truths differ from the other runs")
    verify_hist_reports(ctx, prep, preds, problems, checks)
    checks.update({"historical_runs": len(preds), "eval_keys": len(sel["eval_keys"]), "eval_keys_sha256": sel["summary"]["eval_keys_sha256"]})


def verify_hist_reports(ctx: Ctx, prep, preds, problems: List[str], checks: dict) -> None:
    """Every mandatory report output; metric values AND undefined status/reason replayed independently; deltas; codebook."""
    rep, cb_dir = Path(ctx.hist_results) / "report", Path(ctx.hist_reports) / "model_run_codebook"
    required = [rep / n for n in HIST_REPORT_FILES] + [Path(ctx.hist_reports) / "report.md", cb_dir / HIST_CODEBOOK,
                                                       cb_dir / "expected_vs_actual_inputs.csv", cb_dir / "model_run_index.csv"]
    missing = [str(p) for p in required if not p.exists()]
    if missing:
        problems.append(f"historical mandatory report outputs missing: {missing}")
        return
    meta = json.loads((rep / "comparison_metadata.json").read_text())
    if meta.get("local_manifest", {}).get("sha256") != prep["sha256"] or meta.get("scope") != ISO3:
        problems.append("historical comparison metadata binds a different local manifest/scope")
    outs = meta.get("outputs", {})
    for key, name in (("metrics", "som_metrics_long.csv"), ("deltas", "som_oracle_minus_baseline_deltas.csv"), ("undefined", "som_undefined_reasons.csv")):
        _recorded(problems, f"historical report {name}", outs.get(key), rep / name)
    _recorded(problems, "historical report.md", meta.get("report_md"), Path(ctx.hist_reports) / "report.md")
    cbm = meta.get("codebook", {})
    _recorded(problems, "historical codebook", {"path": cbm.get("codebook"), "sha256": cbm.get("sha256")}, cb_dir / HIST_CODEBOOK)
    for key, name in (("expected_vs_actual", "expected_vs_actual_inputs.csv"), ("model_run_index", "model_run_index.csv")):
        _recorded(problems, f"historical {name}", cbm.get(key), cb_dir / name)
    if len(preds) != len(HIST_RUNS):
        problems.append("historical report replay skipped: not every run verified")
        return
    saved = read_csv(rep / "som_metrics_long.csv")
    saved["period"] = saved["period"].astype(str)
    replayed, expected_undefined = {}, []
    for (arm, horizon), pred in preds.items():
        rm = read_csv(hist_run_dir(ctx, arm, horizon) / "metrics" / "metrics_overall.csv")
        rm["test_year"] = rm["test_year"].astype(str)
        for period in (*YEARS, "pooled"):
            part = pred if period == "pooled" else pred[pred["year"] == period]
            ref, status = legacy.replay(part), expected_metric_status(part)
            r_run = rm[rm["test_year"] == str(period)]
            for metric in osf.ORIGIN_METRICS:
                value = np.nan if ref[metric] is None else float(ref[metric])
                want_status, want_reason = status[metric]
                if (want_status == "ok") == np.isnan(value):
                    problems.append(f"{run_id(arm, horizon)} {period} {metric}: independent undefined condition disagrees with the sklearn replay")
                replayed[(arm, horizon, str(period), metric)] = (value, want_status, want_reason)
                if want_status != "ok":
                    expected_undefined.append((arm, horizon, str(period), metric, want_reason))
                cell = saved[(saved["arm"] == arm) & (saved["horizon"] == horizon) & (saved["period"] == str(period)) & (saved["metric"] == metric)]
                if len(cell) != 1 or len(r_run) != 1:
                    problems.append(f"{run_id(arm, horizon)} {period} {metric}: missing/duplicate report or run metric cell")
                    continue
                cell = cell.iloc[0]
                for label, got, got_status, got_reason in (("report table", cell["value"], cell["status"], cell["reason"]),
                                                           ("run metrics", r_run[metric].iloc[0], r_run[f"{metric}_status"].iloc[0], r_run[f"{metric}_reason"].iloc[0])):
                    if not _same_value(value, got) or _text(got_status) != want_status or _text(got_reason) != want_reason:
                        problems.append(f"{run_id(arm, horizon)} {period} {metric}: {label} ({got}, {got_status}, {got_reason}) differs from "
                                        f"the independent replay ({value}, {want_status}, {want_reason})")
                if int(cell["n_rows"]) != len(part) or int(cell["n_areas"]) != part["area_id"].nunique() \
                        or int(cell["observed_3plus"]) != int((part["overall_phase"].to_numpy(dtype=float) >= 3).sum()):
                    problems.append(f"{run_id(arm, horizon)} {period}: support counts differ")
                checks["metric_cells_replayed"] += 1
    undefined = read_csv(rep / "som_undefined_reasons.csv")
    got = sorted((r.arm, int(r.horizon), str(r.period), r.metric, r.reason, int(r.cells)) for r in undefined.itertuples())
    want = sorted((a, h, p, m, r, 1) for a, h, p, m, r in expected_undefined)
    if got != want:
        problems.append(f"undefined-reasons table differs from the independent undefined conditions ({len(got)} vs {len(want)} rows)")
    checks["undefined_cells"] = len(want)
    deltas = read_csv(rep / "som_oracle_minus_baseline_deltas.csv")
    deltas["period"] = deltas["period"].astype(str)
    for horizon in (0, *ORACLE_H):
        if horizon:
            try:
                rpm.align_pair(preds[(cpf.ORACLE_ARM, horizon)], preds[(cpf.BASELINE_ARM, horizon)])
            except ValueError as exc:
                problems.append(f"H{horizon}: {exc}")
        oracle_arm = cpf.BASELINE_ARM if horizon == 0 else cpf.ORACLE_ARM
        for period in (*map(str, YEARS), "pooled"):
            for metric in osf.ORIGIN_METRICS:
                ov, os_, or_ = replayed[(oracle_arm, horizon, period, metric)]
                bv, bs, br = replayed[(cpf.BASELINE_ARM, horizon, period, metric)]
                defined = not (np.isnan(ov) or np.isnan(bv))
                if horizon == 0:
                    want_status, want_reason = ("shared_h0_zero", None) if defined else ("undefined", f"baseline {br}")
                else:
                    want_status = "ok" if defined else "undefined"
                    want_reason = None if defined else "; ".join(f"{side} {r}" for side, v, r in (("oracle", ov, or_), ("baseline", bv, br)) if np.isnan(v))
                want_delta = (ov - bv) if defined else np.nan
                cell = deltas[(deltas["horizon"] == horizon) & (deltas["period"] == period) & (deltas["metric"] == metric)]
                if len(cell) != 1:
                    problems.append(f"H{horizon} {period} {metric}: missing/duplicate delta row")
                    continue
                cell = cell.iloc[0]
                if not (_same_value(cell["delta"], want_delta) and _same_value(cell["oracle_value"], ov) and _same_value(cell["baseline_value"], bv)
                        and _text(cell["status"]) == want_status and _text(cell["reason"]) == want_reason):
                    problems.append(f"H{horizon} {period} {metric}: delta row ({cell['oracle_value']}, {cell['baseline_value']}, {cell['delta']}, "
                                    f"{cell['status']}, {cell['reason']}) differs from the independent values ({ov}, {bv}, {want_delta}, {want_status}, {want_reason})")
                checks["delta_cells_replayed"] += 1
    if len(deltas) != 4 * (len(YEARS) + 1) * len(osf.ORIGIN_METRICS):
        problems.append(f"delta table has {len(deltas)} rows, not the complete H0/H3/H6/H12 x periods x metrics set")
    book = pd.read_csv(cb_dir / HIST_CODEBOOK, encoding="utf-8-sig", keep_default_na=False)
    for arm, horizon in HIST_RUNS:
        rid = run_id(arm, horizon)
        feats = json.loads((hist_run_dir(ctx, arm, horizon) / "run_metadata.json").read_text())["features"]
        listed = book.loc[book[rid.replace("/", "_")].astype(str).str.lower() == "true", "predictor"].tolist()
        pos = {r.predictor: json.loads(r.actual_model_positions).get(rid) for r in book.itertuples()}
        if sorted(listed) != sorted(feats) or any(pos.get(f) != i + 1 for i, f in enumerate(feats)):
            problems.append(f"{rid}: historical codebook membership/positions differ from the fitted boosters")
    if book["limitations"].str.contains("expected input|no fit verified", case=False, regex=True).any():
        problems.append("historical codebook carries expected-contract wording")
    if not (pd.read_csv(cb_dir / "expected_vs_actual_inputs.csv")["match"].astype(str).str.lower() == "true").all() \
            or not (pd.read_csv(cb_dir / "model_run_index.csv")["match"].astype(str).str.lower() == "true").all():
        problems.append("historical expected-vs-actual inputs or run index do not all match")


def launch_expected_fit(manifest: Mapping[str, object], rid: str, members) -> Tuple[pd.DataFrame, np.ndarray]:
    """Every valid SOM label strictly before April 2026 of the run's training dataset (independent validity rule)."""
    data = pd.read_csv(manifest["runs"][rid]["training_dataset"]["path"], usecols=KEYS + list(osf.SHARE_COLUMNS) + ["overall_phase"],
                       float_precision="round_trip")
    ords = data["year"].to_numpy() * 12 + data["month"].to_numpy() - 1
    shares = data[list(osf.SHARE_COLUMNS)].to_numpy(dtype=float)
    valid = np.isfinite(shares).all(axis=1) & (shares >= 0).all(axis=1) & (shares.sum(axis=1) > 0)
    eligible = valid & (ords <= cl.LABEL_CUTOFF_ORD) & data["area_id"].isin(members).to_numpy()
    return data.loc[eligible].reset_index(drop=True), ords[eligible]


def verify_launch(ctx: Ctx, problems: List[str], checks: dict) -> None:
    import xgboost as xgb

    prep = launch_prepare(ctx, write=False)  # full parent gate + exact recomputation of every local projection/ledger
    path = prep["path"]
    if not path.exists() or sha(path) != prep["sha256"]:
        problems.append("local launch manifest missing or differs from the recomputed projection")
        return
    manifest = prep["local"]
    for name, item in manifest["files"].items():
        if not Path(item["path"]).exists() or sha(item["path"]) != item["sha256"]:
            problems.append(f"local launch input {name} missing or changed")
    members = set(prep["membership"]["area_ids"])
    fit_frames, fingerprints = {}, {}
    for arm, horizon in LAUNCH_RUNS:
        rid = run_id(arm, horizon)
        run_dir = launch_run_dir(ctx, arm, horizon)
        fp, _ = cl.fingerprint(path, manifest, rid)
        fingerprints[rid] = fp
        if not (run_dir / "artifact_record.json").exists():
            problems.append(f"{rid}: no artifact record")
            continue
        try:
            cl.verify_run_record(run_dir, fp)
        except cl.LaunchError as exc:
            problems.append(f"{rid}: {exc}")
            continue
        feats = manifest["runs"][rid]["features"]
        frozen = None if ctx.frozen_feature_sha256 is None else ctx.frozen_feature_sha256[(cl.TRAINING_ARM[arm], horizon)]
        if json.loads((run_dir / "feature_schema.json").read_text())["features"] != feats or osf.list_sha256(feats) != (frozen or osf.list_sha256(feats)):
            problems.append(f"{rid}: saved schema differs from the inherited contract")
        inf = pd.read_csv(run_dir / "inference_features.csv.gz", float_precision="round_trip", low_memory=False)
        pred = pd.read_csv(run_dir / "predictions_raw.csv", float_precision="round_trip")
        local_inf = pd.read_csv(manifest["runs"][rid]["inference"]["path"], float_precision="round_trip", low_memory=False)
        if not cl.same_frame(inf, local_inf) or not inf[KEYS].equals(pred[KEYS]) or not pred["area_id"].isin(members).all() \
                or len(pred) != manifest["checks"]["inference_areas"]:
            problems.append(f"{rid}: inference/prediction keys differ from the SOM projection")
        replayed = {}
        for target, column in zip(osf.CUMULATIVE_TARGETS, osf.PRED_COLUMNS):
            booster = xgb.Booster()
            booster.load_model(str(run_dir / f"model_{target}.ubj"))
            if list(booster.feature_names) != feats:
                problems.append(f"{rid} {target}: booster feature order differs")
            again = booster.predict(xgb.DMatrix(inf[feats], feature_names=feats)).astype(float)
            saved = pred[column].to_numpy(dtype=float)
            if not (np.isfinite(again).all() and np.isfinite(saved).all()):
                problems.append(f"{rid} {target}: nonfinite predictions")
                continue
            diff = float(np.max(np.abs(again - saved)))
            checks["max_model_replay_abs_diff"] = max(checks["max_model_replay_abs_diff"], diff)
            if not diff <= 1e-6:
                problems.append(f"{rid} {target}: replay differs by {diff}")
            replayed[column] = again
            checks["models_reloaded"] += 1
        problems.extend(replayed_class_problems(rid, pred, replayed, cl.THRESHOLD))
        keys = pd.read_csv(run_dir / "fit_keys.csv.gz")
        targets = pd.read_csv(run_dir / "fit_targets.csv.gz", float_precision="round_trip")
        weights = pd.read_csv(run_dir / "fit_weights.csv.gz", float_precision="round_trip")
        want, wards = launch_expected_fit(manifest, rid, members)
        want_keys = want[KEYS]
        for label, frame in (("fit_keys", keys), ("fit_targets", targets), ("fit_weights", weights)):
            if not frame[KEYS].equals(want_keys):
                problems.append(f"{rid}: {label} keys are not exactly the ordered complete valid SOM labels before April 2026")
        if not np.array_equal(keys["fit_ord"].to_numpy(), wards):
            problems.append(f"{rid}: fit_ord differs from the independent calendar ordinal")
        if not (np.array_equal(weights["age_months"].to_numpy(), cl.ORIGIN_ORD - wards)
                and np.allclose(weights["sample_weight"], 0.5 ** ((cl.ORIGIN_ORD - wards) / 24.0), rtol=0, atol=1e-15)) or wards.max() > cl.LABEL_CUTOFF_ORD:
            problems.append(f"{rid}: April-anchored age/weight check failed")
        if not _close(independent_targets(want), targets[list(osf.CUMULATIVE_TARGETS)].to_numpy(), 1e-12):
            problems.append(f"{rid}: fitting targets differ from the independent normalization")
        checks["launch_fit_rows_checked"] += len(keys)
        fit_frames[rid] = (keys, targets, weights)
    for horizon in (6, 12):
        a, b = fit_frames.get(run_id(cl.BASELINE, horizon)), fit_frames.get(run_id(cl.WEATHER, horizon))
        if not (a and b) or not all(x.equals(y) for x, y in zip(a, b)):
            problems.append(f"H{horizon}: paired fitting keys/targets/weights differ or are missing")
        bi = pd.read_csv(manifest["runs"][run_id(cl.BASELINE, horizon)]["inference"]["path"], float_precision="round_trip", low_memory=False)
        wi = pd.read_csv(manifest["runs"][run_id(cl.WEATHER, horizon)]["inference"]["path"], float_precision="round_trip", low_memory=False)
        if list(wi.columns[: bi.shape[1]]) != list(bi.columns) or not cl.same_frame(wi[list(bi.columns)], bi):
            problems.append(f"H{horizon}: weather inference baseline prefix differs")
    scope_path = Path(ctx.launch_results) / "scope" / "run_scope.json"
    if not scope_path.exists():
        problems.append("launch scope sidecar missing")
    else:
        scope = json.loads(scope_path.read_text())
        if scope.get("local_manifest", {}).get("sha256") != prep["sha256"] or set(scope.get("runs", {})) != set(fingerprints):
            problems.append("launch scope sidecar binds a different local manifest or run set")
        for rid, fp in fingerprints.items():
            entry = scope.get("runs", {}).get(rid, {})
            run_dir = launch_run_dir(ctx, *_split(rid))
            if entry.get("fingerprint") != fp or not (run_dir / "artifact_record.json").exists() \
                    or entry.get("artifact_record_sha256") != sha(run_dir / "artifact_record.json"):
                problems.append(f"{rid}: scope sidecar fingerprint/artifact-record hash differs")
    verify_launch_population(ctx, manifest, prep, problems, checks)
    verify_launch_maps(ctx, manifest, problems, checks)
    verify_launch_reports(ctx, manifest, problems, checks)


def verify_launch_reports(ctx: Ctx, manifest, problems: List[str], checks: dict) -> None:
    """Mandatory launch deliverables and every hash recorded in report_outputs.json; codebook versus the boosters."""
    res, rep = Path(ctx.launch_results), Path(ctx.launch_reports)
    ro_path = res / "report_outputs.json"
    required = [ro_path, rep / "launch_summary.md", rep / "model_run_codebook_en.csv", res / "visualizations" / "figure_metadata.json",
                *(res / "population" / f"{n}.csv" for n in LAUNCH_TABLES), *(rep / "population" / f"{n}.csv" for n in LAUNCH_REPORT_COPIES)]
    missing = [str(p) for p in required if not p.exists()]
    if missing:
        problems.append(f"launch mandatory outputs missing: {missing}")
        return
    ro = json.loads(ro_path.read_text())
    if set(ro.get("population", {})) != set(LAUNCH_TABLES):
        problems.append("report_outputs.json does not record exactly the four population tables")
    for name in LAUNCH_TABLES:
        _recorded(problems, f"launch table {name}", ro.get("population", {}).get(name), res / "population" / f"{name}.csv")
    for name in LAUNCH_REPORT_COPIES:
        if (rep / "population" / f"{name}.csv").read_bytes() != (res / "population" / f"{name}.csv").read_bytes():
            problems.append(f"report copy of {name} differs from the machine-readable table")
    _recorded(problems, "launch codebook", {"path": ro.get("codebook", {}).get("path"), "sha256": ro.get("codebook", {}).get("sha256")},
              rep / "model_run_codebook_en.csv")
    _recorded(problems, "launch summary", ro.get("summary"), rep / "launch_summary.md")
    if ro.get("maps") != json.loads((res / "visualizations" / "figure_metadata.json").read_text()):
        problems.append("report_outputs.json map record differs from figure_metadata.json")
    book = pd.read_csv(rep / "model_run_codebook_en.csv", encoding="utf-8-sig", keep_default_na=False)
    for arm, horizon in LAUNCH_RUNS:
        rid = run_id(arm, horizon)
        feats = manifest["runs"][rid]["features"]
        listed = book.loc[book[rid.replace("/", "_")].astype(str).str.lower() == "true", "predictor"].tolist()
        pos = {r.predictor: json.loads(r.actual_model_positions).get(rid) for r in book.itertuples()}
        if sorted(listed) != sorted(feats) or any(pos.get(f) != i + 1 for i, f in enumerate(feats)):
            problems.append(f"{rid}: launch codebook membership/positions differ from the fitted boosters")
    if book["limitations"].str.contains("expected input|no fit verified", case=False, regex=True).any():
        problems.append("launch codebook carries expected-contract wording")


def verify_launch_population(ctx: Ctx, manifest, prep, problems: List[str], checks: dict) -> None:
    """Independent arithmetic: Somalia cap factor from the parent ledger/reference, then shares/counts/sums/deltas."""
    pop_dir = Path(ctx.launch_results) / "population"
    if not all((pop_dir / f"{n}.csv").exists() for n in LAUNCH_TABLES):
        problems.append("launch population tables missing")
        return
    read = lambda n: read_csv(pop_dir / f"{n}.csv")  # noqa: E731
    parent_pop = pd.read_csv(prep["parent"]["ledgers"]["population"]["path"], float_precision="round_trip")
    som_pop = parent_pop[parent_pop["area_id"].isin(prep["membership"]["area_ids"])].sort_values("area_id")
    ids = som_pop["area_id"].to_numpy()
    raw = som_pop["estimated_population"].to_numpy(dtype=float)
    audit = prep["audit"].set_index("country")
    ref = float(audit.loc[COUNTRY, "reference_population"])
    n_c = float(np.add.reduce(raw))
    fac = 0.95 * ref / n_c if n_c > 1.10 * ref else 1.0
    if not (abs(fac - float(audit.loc[COUNTRY, "cap_factor"])) <= 1e-15 and abs(n_c - float(audit.loc[COUNTRY, "raw_population"])) <= 1e-6):
        problems.append("Somalia cap factor/raw population differ from the independent recomputation")
    eff = raw * fac
    checks.update({"population_raw_total": n_c, "population_effective_total": float(eff.sum()), "cap_factor": fac, "inference_areas": len(ids)})
    area = read("area_population_predictions")
    expected = {}
    for arm, horizon in cl.DISPLAY:
        src = cl.source_run(arm, horizon)
        pred = pd.read_csv(launch_run_dir(ctx, *src) / "predictions_raw.csv", float_precision="round_trip").sort_values("area_id")
        if not np.array_equal(pred["area_id"].to_numpy(), ids):
            problems.append(f"{arm} H{horizon}: prediction keys differ from the SOM population cohort")
            continue
        q = pred[list(osf.PRED_COLUMNS)].to_numpy(dtype=float)
        comps = [1.0 - q[:, 0], q[:, 0] - q[:, 1], q[:, 1] - q[:, 2], q[:, 2] - q[:, 3], q[:, 3]]
        comps = [np.minimum(np.maximum(c, 0.0), 1.0) for c in comps]
        tot = comps[0] + comps[1] + comps[2] + comps[3] + comps[4]
        s = np.column_stack([c / tot for c in comps])
        named = {f"phase{k}": s[:, i] for i, k in enumerate(cl.PHASES)} | {"p3plus": s[:, 2] + s[:, 3] + s[:, 4], "p4plus": s[:, 3] + s[:, 4]}
        sub = area[(area["display_arm"] == arm) & (area["horizon"] == horizon)].sort_values("area_id")
        if not np.array_equal(sub["area_id"].to_numpy(), ids) or not np.array_equal(sub["crisis_raw_phase3plus"].to_numpy(dtype=bool), pred["overall_phase_pred"].to_numpy() >= 3):
            problems.append(f"{arm} H{horizon}: area keys or raw crisis flags differ")
            continue
        cols = {}
        for kind, pop in (("raw", raw), ("effective", eff)):
            if not _close(sub[f"population_{kind}"], pop, 1e-6, 1e-12):
                problems.append(f"{arm} H{horizon}: area population_{kind} differs")
            den = float(np.add.reduce(pop))
            cols[f"population_{kind}"] = den
            for nme, share in named.items():
                count = share * pop
                if not _close(sub[f"count_{kind}_{nme}"], count, 1e-6, 1e-12):
                    problems.append(f"{arm} H{horizon}: area count_{kind}_{nme} differs")
                total = float(np.add.reduce(count))
                cols[f"count_{kind}_{nme}"] = total
                cols[f"share_{kind}_{nme}"] = total / den if den > 0 else np.nan
                checks["population_columns_checked"] += 1
        for nme, share in named.items():
            if not _close(sub[f"share_{nme}"], share, 1e-12):
                problems.append(f"{arm} H{horizon}: area share_{nme} differs")
        expected[(arm, horizon)] = cols
    summary = read("som_population_summary")
    if len(summary) != len(cl.DISPLAY):
        problems.append(f"SOM summary has {len(summary)} rows, not one per displayed arm/horizon")
    for (arm, horizon), cols in expected.items():
        row = summary[(summary["display_arm"] == arm) & (summary["horizon"] == horizon)]
        if len(row) != 1 or row["country"].iloc[0] != COUNTRY or int(row["n_areas"].iloc[0]) != len(ids):
            problems.append(f"{arm} H{horizon}: SOM summary row missing or wrong cohort")
            continue
        for column, want in cols.items():
            tol = (1e-12, 0.0) if column.startswith("share_") else (1e-6, 1e-12)
            if not _close(row[column], [want], *tol):
                problems.append(f"{arm} H{horizon}: SOM {column} differs from the independent sum")
    for level, key in (("som", "country"), ("area", "area_id")):
        saved = read(f"{level}_population_paired_differences")
        for horizon in (0, 6, 12):
            part = saved[saved["horizon"] == horizon]
            src = area if level == "area" else summary
            b = src[(src["display_arm"] == cl.BASELINE) & (src["horizon"] == horizon)].set_index(key)
            w = src[(src["display_arm"] == cl.WEATHER) & (src["horizon"] == horizon)].set_index(key)
            part = part.set_index(key)
            if len(part) != len(b) or not part.index.equals(b.index) or not w.index.equals(b.index):
                problems.append(f"H{horizon} {level}: paired difference rows missing")
                continue
            for column in [c for c in b.columns if c.startswith(("share_", "count_")) and not c.endswith(("_status", "_reason"))]:
                want = w[column].to_numpy(dtype=float) - b[column].to_numpy(dtype=float)
                got = part[f"delta_{column}"].to_numpy(dtype=float)
                if not _close(got, want, 1e-12 if column.startswith("share_") else 1e-6, 0.0 if column.startswith("share_") else 1e-12):
                    problems.append(f"H{horizon} {level}: delta_{column} differs")
                if horizon == 0 and not np.all((got == 0) | np.isnan(got)):
                    problems.append(f"H0 {level}: delta_{column} is not exactly 0 for the shared fit")
                checks["difference_columns_checked"] += 1


def map_names() -> List[str]:
    return [f"crisis_categorical_{a}_{h}m_{cl.TARGETS[h][0]}-{cl.TARGETS[h][1]:02d}" for a, h in LAUNCH_RUNS] + [
        "p3plus_share_comparison_2x3", "p3plus_share_difference_1x2"]


def verify_launch_maps(ctx: Ctx, manifest, problems: List[str], checks: dict) -> None:
    vis_dir, fig_dir = Path(ctx.launch_results) / "visualizations", Path(ctx.launch_reports) / "figures"
    names = map_names()
    pngs = sorted(p.name for p in fig_dir.glob("*.png")) if fig_dir.exists() else []
    if pngs != sorted(f"{n}.png" for n in names) or any((fig_dir / f).stat().st_size == 0 for f in pngs):
        problems.append(f"figures are not exactly the seven required PNGs: {pngs}")
    meta_path = vis_dir / "figure_metadata.json"
    if not meta_path.exists():
        problems.append("figure metadata missing")
        return
    meta = json.loads(meta_path.read_text())
    if meta.get("scope") != ISO3 or meta.get("local_version") != LAUNCH_VERSION:
        problems.append("figure metadata scope/version differ")
    want_geo = {Path(p).suffix: str(p) for p in ctx.geometry_files}
    geo = meta.get("geometry", {})
    if not want_geo or ".shp" not in want_geo or set(geo) != set(want_geo):
        problems.append(f"figure metadata geometry components {sorted(geo)} are not the complete set {sorted(want_geo)}")
    for ext, p in want_geo.items():
        item = geo.get(ext, {})
        if item.get("path") != p or not Path(p).exists() or sha(p) != item.get("sha256"):
            problems.append(f"geometry {ext} path/sha256 differs from the drawn maps")
    ids = np.sort(pd.read_csv(manifest["ledgers"]["population"]["path"])["area_id"].to_numpy())
    n = len(ids)
    figures = meta.get("figures", {})
    if sorted(figures) != sorted(names):
        problems.append(f"figure metadata entries {sorted(figures)} are not exactly the seven maps")
    for name in names:
        entry = figures.get(name)
        if entry is None:
            continue
        fig_path, rec_path = fig_dir / f"{name}.png", vis_dir / f"{name}.csv"
        if entry.get("figure") != str(fig_path) or entry.get("record") != str(rec_path) or not fig_path.exists() or not rec_path.exists() \
                or sha(fig_path) != entry.get("figure_sha256") or sha(rec_path) != entry.get("record_sha256") or entry.get("mapped_areas") != n:
            problems.append(f"figure {name}: canonical paths, hashes or mapped_areas={entry.get('mapped_areas')} (want {n}) differ")
    # reconstruct the join: unique normalized geometry keys, one non-empty geometry for every SOM inference area
    boundaries = ctx.load_boundaries()
    gkeys = boundaries["area_id"].astype(str).str.strip()
    if gkeys.duplicated().any():
        problems.append("geometry has duplicate normalized area ids")
    geom = pd.DataFrame({"join_key": gkeys.to_numpy(), "has_geometry": (boundaries.geometry.notna() & ~boundaries.geometry.is_empty).to_numpy()})
    joined = pd.DataFrame({"join_key": [str(i) for i in ids]}).merge(geom.drop_duplicates("join_key"), on="join_key", how="left", validate="one_to_one")
    if len(joined) != n or not joined["has_geometry"].fillna(False).astype(bool).all():
        problems.append("geometry join does not give exactly one non-empty geometry for every SOM inference area")
    checks["map_join_areas"] = int(joined["has_geometry"].fillna(False).astype(bool).sum())
    area = read_csv(Path(ctx.launch_results) / "population" / "area_population_predictions.csv")
    rec = pd.read_csv(vis_dir / "p3plus_share_comparison_2x3.csv", float_precision="round_trip")
    for arm, horizon in cl.DISPLAY:
        part = rec[(rec["display_arm"] == arm) & (rec["horizon"] == horizon)].set_index("area_id")
        want = area[(area["display_arm"] == arm) & (area["horizon"] == horizon)].set_index("area_id")["share_p3plus"].reindex(ids) * 100.0
        if len(part) != n or sorted(part.index) != list(ids) or not _close(part["p3plus_percent"].reindex(ids), want, 1e-10):
            problems.append(f"2x3 map record {arm} H{horizon} incomplete or differs from the area table")
        checks["map_values_checked"] += len(part)
    drec = pd.read_csv(vis_dir / "p3plus_share_difference_1x2.csv", float_precision="round_trip")
    for horizon in (6, 12):
        part = drec[drec["horizon"] == horizon].set_index("area_id")
        b = area[(area["display_arm"] == cl.BASELINE) & (area["horizon"] == horizon)].set_index("area_id")["share_p3plus"].reindex(ids)
        w = area[(area["display_arm"] == cl.WEATHER) & (area["horizon"] == horizon)].set_index("area_id")["share_p3plus"].reindex(ids)
        if len(part) != n or sorted(part.index) != list(ids) or not _close(part["p3plus_pp_difference"].reindex(ids), (w - b) * 100.0, 1e-10):
            problems.append(f"1x2 difference record H{horizon} incomplete or differs from the tables")
        checks["map_values_checked"] += len(part)
    for arm, horizon in LAUNCH_RUNS:
        target = cl.TARGETS[horizon]
        cat = pd.read_csv(vis_dir / f"crisis_categorical_{arm}_{horizon}m_{target[0]}-{target[1]:02d}.csv").set_index("area_id")
        pred = pd.read_csv(launch_run_dir(ctx, arm, horizon) / "predictions_raw.csv").set_index("area_id").reindex(ids)
        if len(cat) != n or sorted(cat.index) != list(ids) or \
                not np.array_equal(cat.reindex(ids)["predicted_crisis"].to_numpy(dtype=bool), pred["overall_phase_pred"].to_numpy() >= 3):
            problems.append(f"categorical record {run_id(arm, horizon)} incomplete or differs from the raw class")
        checks["map_values_checked"] += len(cat)


def inventory(roots: Sequence[Path], skip: Sequence[str] = ("verification.json",)) -> List[dict]:
    return [{"path": str(p), "sha256": sha(p), "bytes": p.stat().st_size} for root in roots if Path(root).exists()
            for p in sorted(Path(root).rglob("*")) if p.is_file() and p.name not in skip]


def frozen_check(ctx: Ctx, problems: List[str], checks: dict) -> None:
    """The before-snapshot must be the complete unique frozen membership; then every listed byte must be unchanged."""
    snapshots = [Path(ctx.hist_results) / "preflight" / "frozen_inventory_before.csv", Path(ctx.launch_results) / "preflight" / "frozen_inventory_before.csv"]
    if not all(p.exists() for p in snapshots):
        problems.append("frozen inventory snapshot missing")
        return
    if snapshots[0].read_bytes() != snapshots[1].read_bytes():
        problems.append("historical and launch frozen snapshots differ")
    before = pd.read_csv(snapshots[0], keep_default_na=False)
    if before.empty or list(before.columns) != ["role", "path", "bytes", "sha256"]:
        problems.append("frozen inventory snapshot is empty or malformed")
        return
    if before["path"].duplicated().any():
        problems.append("frozen inventory snapshot has duplicate paths")
    listed = set(zip(before["role"], before["path"]))
    current = {(role, str(p)) for role, p in ctx.frozen_paths()}
    missing, added = sorted(listed - current), sorted(current - listed)
    if missing:
        problems.append(f"frozen artifacts missing/removed or re-roled: {[p for _, p in missing][:5]}")
    if added:
        problems.append(f"frozen locations gained files since the snapshot: {[p for _, p in added][:5]}")
    changed = [r.path for r in before.itertuples() if Path(r.path).exists() and sha(r.path) != r.sha256]
    if changed:
        problems.append(f"frozen artifacts changed: {changed[:5]}")
    checks.update({"frozen_files_checked": len(before), "frozen_files_changed": len(changed), "frozen_files_missing": len(missing),
                   "frozen_files_added": len(added)})


def verify_main(ctx: Ctx) -> dict:
    runtime = runtime_identity()
    hist_problems, launch_problems, shared = [], [], []
    hc = {"batches": 0, "models_reloaded": 0, "artifacts_rehashed": 0, "fit_rows_checked": 0, "max_model_replay_abs_diff": 0.0,
          "metric_cells_replayed": 0, "delta_cells_replayed": 0}
    lc = {"models_reloaded": 0, "max_model_replay_abs_diff": 0.0, "launch_fit_rows_checked": 0, "population_columns_checked": 0,
          "difference_columns_checked": 0, "map_values_checked": 0}
    for stage, fn, problems, checks in (("historical", verify_hist, hist_problems, hc), ("launch", verify_launch, launch_problems, lc)):
        try:
            fn(ctx, problems, checks)
        except Exception as exc:  # a failed gate is a verification failure with its diagnostic, never a pass
            problems.append(f"{stage} verification stopped: {type(exc).__name__}: {exc}")
    fc = {}
    frozen_check(ctx, shared, fc)
    hist_ok = not hist_problems and not shared and hc["batches"] == 28 and hc["models_reloaded"] == 112
    launch_ok = not launch_problems and not shared and lc["models_reloaded"] == 20
    common = {"runtime": runtime, "local_code": local_code_identity(ctx), "frozen": fc, "frozen_problems": shared,
              "created_utc": pd.Timestamp.now(tz="UTC").isoformat(),
              "tolerances": {"model_replay": "atol 1e-6, rtol 0; classes of reloaded predictions exact", "metrics/deltas": "atol 1e-12, identical undefined status/reason",
                             "counts/sums": "atol 1e-6, rtol 1e-12", "shares": "atol 1e-12", "csv": "float_precision=round_trip"}}
    hist = {"local_version": HIST_VERSION, "scope": ISO3, "passed": hist_ok, "problems": hist_problems, "checks": hc,
            "inventory": inventory([ctx.hist_results, ctx.hist_reports]), **common}
    launch = {"local_version": LAUNCH_VERSION, "scope": ISO3, "passed": launch_ok, "problems": launch_problems, "checks": lc,
              "inventory": inventory([ctx.launch_results, ctx.launch_reports]), **common}
    write_json(Path(ctx.hist_results) / "verification" / "verification.json", hist)
    write_json(Path(ctx.launch_results) / "verification.json", launch)
    return {"passed": hist_ok and launch_ok, "historical": {k: hist[k] for k in ("passed", "problems", "checks")},
            "launch": {k: launch[k] for k in ("passed", "problems", "checks")}, "frozen": fc, "frozen_problems": shared}


# --------------------------------------------------------------------------- modes


def validate_main(ctx: Ctx) -> dict:
    """Every read-only gate (full parent gates, local selections/projections/ledgers, identities); writes nothing."""
    runtime = runtime_identity()
    for name, d in cpf.FROZEN_CONFIG_SHA256.items():
        if sha(paths.CONFIG_DIR / name) != d:
            raise LocalError(f"config {name} differs from the frozen sha256")
    prep = hist_prepare(ctx, write=False)
    runs = {}
    for arm, horizon in HIST_RUNS:
        inputs = hist_localize(ctx, prep, ctx.load_hist_inputs(hist_args(ctx, arm, horizon)), arm, horizon)
        per_year = {}
        for year in YEARS:
            fit, ords = expected_hist_fit(inputs["data"], inputs["share_valid"], year, horizon)
            per_year[year] = {"fit_rows": len(fit), "fit_areas": int(fit["area_id"].nunique()), "fit_label_cutoff": ym(year * 12 - max(horizon, 1)),
                              "fit_max_label": ym(ords.max()) if len(ords) else None, "eval_rows": int((inputs["eval_key"] & (inputs["data"]["year"].to_numpy() == year)).sum())}
        runs[run_id(arm, horizon)] = {"features": len(inputs["features"]), "feature_sha256": osf.list_sha256(inputs["features"]),
                                      "parent_fingerprint": inputs["fingerprint_payload"]["parent_fingerprint"], "local_fingerprint": inputs["fingerprint"],
                                      "years": per_year}
        log(f"validate historical {run_id(arm, horizon)}: parent gate passed; local fingerprint {inputs['fingerprint'][:12]}")
        del inputs
    lprep = launch_prepare(ctx, write=False)
    log("validate launch: parent gate passed; SOM projections, pairing, population/cap and coverage gates passed")
    inv = frozen_inventory(ctx)
    return {"mode": "validate-only (nothing written)", "runtime": runtime, "local_code": local_code_identity(ctx),
            "membership": membership_identity(prep["membership"]),
            "historical": {"local_manifest_sha256_if_written": prep["sha256"], "cohort": prep["selection"]["summary"], "runs": runs,
                           "spec_sha256": {k: v["sha256"] for k, v in prep["local"]["files"].items() if k.startswith("approved_spec/")}},
            "launch": {"local_manifest_sha256_if_written": lprep["sha256"], "checks": lprep["local"]["checks"],
                       "runs": {rid: {k: e[k] for k in ("fit_rows", "fit_areas", "fit_label_months", "fit_keys_sha256", "inference_keys_sha256",
                                                        "feature_count", "feature_sha256")} | {"fit_selection_sha256": e["fit_selection"]["sha256"],
                                                                                               "inference_sha256": e["inference"]["sha256"]}
                                for rid, e in lprep["local"]["runs"].items()},
                       "parent_manifest": lprep["local"]["parent"]["manifest"],
                       "fit_run_fingerprints": "computed by --approve-training after the local manifest is written; each binds the local "
                                               "manifest sha256 reported above (no temporary output in validate-only)"},
            "frozen_inventory": {"files": len(inv), "bytes": int(inv["bytes"].sum()) if len(inv) else 0,
                                 "digest": sha_bytes(csv_bytes(inv)), "by_role": inv.groupby("role").size().to_dict() if len(inv) else {}},
            "roots_exist": {str(r): Path(r).exists() for r in ctx.roots()}}


def train_main(ctx: Ctx, pilot: bool) -> dict:
    runtime_identity()
    for root in ctx.roots():
        assert_local_root(root)
    snap = Path(ctx.hist_results) / "preflight" / "frozen_inventory_before.csv"
    if not snap.exists():
        inv = frozen_inventory(ctx)
        write_once(snap, csv_bytes(inv))
        write_once(Path(ctx.launch_results) / "preflight" / "frozen_inventory_before.csv", csv_bytes(inv))
    prep = hist_prepare(ctx, write=True)
    hist = hist_train(ctx, prep, pilot)
    if pilot:
        return {"historical": hist, "launch": "not started (pilot)"}
    lprep = launch_prepare(ctx, write=True)
    return {"historical": hist, "launch": launch_train(ctx, lprep)}


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate-only", action="store_true", help="All read-only gates; no directory or file is written.")
    mode.add_argument("--approve-training", action="store_true", help="Fit the fixed historical (7 runs x 4 years) then launch (5 runs) plan.")
    mode.add_argument("--report", action="store_true", help="Somalia tables, maps, codebooks and summaries from saved artifacts (no fitting).")
    mode.add_argument("--verify", action="store_true", help="Independent verification of every saved model, table and map (no fitting).")
    parser.add_argument("--pilot", action="store_true", help="With --approve-training: only historical compact_baseline H0 / 2022 (run stays PARTIAL).")
    args = parser.parse_args(argv)
    if args.pilot and not args.approve_training:
        parser.error("--pilot requires --approve-training")
    return args


def main(argv=None, ctx: Optional[Ctx] = None) -> int:
    args = parse_args(argv)
    ctx = ctx or Ctx()
    if args.validate_only:
        print(json.dumps(validate_main(ctx), indent=1, default=_json_default), flush=True)
        return 0
    if args.approve_training:
        print(json.dumps(train_main(ctx, args.pilot), indent=1, default=_json_default), flush=True)
        return 0
    if args.report:
        out = {"historical": hist_report(ctx), "launch": launch_report(ctx)}
        print(json.dumps({"historical": out["historical"]["outputs"], "launch_figures": sorted(out["launch"]["maps"]["figures"])}, indent=1, default=_json_default))
        return 0
    result = verify_main(ctx)
    print(json.dumps(result, indent=1, default=_json_default), flush=True)
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
