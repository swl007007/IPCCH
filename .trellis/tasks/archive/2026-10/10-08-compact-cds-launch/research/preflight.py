"""Execution preflight for compact_cds_launch_v1 (read-only except the versioned spec copy and this JSON).

Run from the repository root with the frozen model interpreter:
  PATH=/tmp/ipcch-windows-git-bin:$PATH PYTHONPATH=src /home/swl007007/.venvs/ipcch-geo/bin/python \
      .trellis/tasks/10-08-compact-cds-launch/research/preflight.py
"""
from __future__ import annotations

import csv
import hashlib
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / "src"))
from ipcch import compact_features as cpf  # noqa: E402
from ipcch import origin_safe as osf  # noqa: E402
from ipcch import paths  # noqa: E402

T0 = time.time()
TASK = ROOT / ".trellis/tasks/10-08-compact-cds-launch"
D = paths.SOURCE_DATA_DIR
A = D / "assembled_IPCCH"
S = Path("/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/IPCCH_shared_folder")
CDS = D / "CDS_API"
CDS_PY = CDS / ".venv/bin/python"
VERSION = "compact_cds_launch_v1"
INPUT_ROOT = A / "model_ready" / VERSION
GIT = "/mnt/c/Program Files/Git/cmd/git.exe"
PINNED = {
    "compact_manifest": (A / "model_ready/compact_climate_weather_oracle_v1/compact_climate_weather_oracle_v1_manifest.json",
                         "456360536a3929e1571d96ba9f16e2f0de54bc1b20019f797bbe62c0c89732ca"),
    "parent_manifest": (A / "model_ready/origin_safe_climate_idp_v1/origin_safe_climate_idp_v1_manifest.json",
                        "3b479c80498e9f2d6d20b88936fce468f297d2e0ccd6f0cb32c61a7470a209bf"),
    "interim": (A / "interim/IPCCH_2026_target_corrected_nino34_wbfood.csv", "a91719e8e603e11b58e3e44c9a2f4378e4218e1ac408afe03ca54d1b50fb0484"),
    "climate_monthly": (S / "climate_monthly_2015_2026_MODELING_READY.csv", "8082b72ea5fa5c30a7b975b89c1fbbb4530f27a9ce6c5ba4d0e1a4f923320c89"),
    "climate_seasonal": (S / "climate_2015_2026_MODELING_READY.csv", "f024a66c8979fb4a8c66fba1f04e7e69355fa75b499793d29001a146d8c2958e"),
    "comprehensive_april": (A / "features/forecasting_subset_IPCCH_2026_target_corrected_deep_features.csv",
                            "60610cd601e4b0c700cc475903fe807f072f131a97c543dc22f169b2824917e4"),
    "identifier_source": (A / "raw/IPCCH_2026_completed.csv", "ae696087c3bbb280537ae269a05924133acdb51060d31290523404fa8a717673"),
    "cds_points": (A / "spatial/unique_area_id_lat_lon.csv", "3bf8f115ec70cd1e1c907031309b797410a8024cdc1d39265be123ae636d2862"),
    "country_lookup": (A / "country_area_id_lookup.csv", "e2baf6ae9481b42b127db5ce81f3c53ad784bb08ae56dfa56cea74e416b44c90"),
    "idp_admin0_monthly": (Path("/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/Processed_Dataset/IDP_DTM/output/idp_admin0_monthly.csv"),
                           "a1ebb82a8e14fc0fb8103d6086217b93da351fc4a8f7fcfbe9eaa44a9df602e1"),
    "country_population_reference": (ROOT / "reports/launch/nowcasting_2026_04/population_projection/countries_2025_population_merged.csv",
                                     "c348cc30cd2b5beae93a11974c4712a3dd6dd822ee902f5458a778effad389b0"),
    "region_map": (ROOT / "data/reference/area_id_country_region_mapping.csv", "18ab5099ce2d1154fb5686183ee399124e18427cc1594923f7abe2769da1611d"),
}
CONFIG_SHA256 = {"forecasting_hyperparameters.json": "3742300661466f22eba8198e5d4f9c2a277615ba59562fbf27f251ecc932dd76",
                 "forecasting_hyperparameters_p3.json": "cdc0e55aa15bdda932465088568b9ee717d226208ffb32076f438fb274e6317b"}
HELPERS = ("src/ipcch/compact_features.py", "src/ipcch/climate2015_features.py", "src/ipcch/retained_feature_recipes.py",
           "src/ipcch/weather_oracle.py", "src/ipcch/origin_safe.py", "src/ipcch/forecasting_weight_decay.py",
           "src/ipcch/launch_nowcasting.py", "src/ipcch/launch_visualizations.py", "src/ipcch/alert_risk_maps.py",
           "src/ipcch/plot_forecast_weather_phase3plus_maps.py", "src/ipcch/paths.py",
           "scripts/modeling/run_deep_feature_weight_decay_forecasting.py", "scripts/modeling/run_launch_nowcasting_2026_04.py")
GEOMETRY = A / "spatial/ipcch_admin_geometry"
OLD_ROOTS = (ROOT / "results/launch", ROOT / "reports/launch", CDS)
OLD_AREA_TABLE = ROOT / "results/launch/nowcasting_2026_04/population_nowcast/area_level_nowcasting_predicted_population_2026_04.csv"
SPEC_FILES = ("prd.md", "design.md", "implement.md", "discussion-notes.md", "expected_feature_contract.csv",
              "expected_feature_contract_metadata.json", "expected_run_index.csv", "check.jsonl", "implement.jsonl",
              "research/launch-input-findings.md", "research/contract-reading.md", "research/supervisor-execution-brief.md",
              "research/executor-binding.json")
RUNS = {"compact_baseline/0m": ("compact_baseline", 0), "compact_baseline/6m": ("compact_baseline", 6),
        "compact_baseline/12m": ("compact_baseline", 12), "compact_cds_weather/6m": ("compact_weather_oracle", 6),
        "compact_cds_weather/12m": ("compact_weather_oracle", 12)}
out = {"version": VERSION, "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "checks": {}, "problems": [], "deferred": []}
P = out["problems"]


def log(msg):
    print(f"[{time.time() - T0:6.0f}s] {msg}", flush=True)


def sha(path):
    return osf.file_sha256(path)


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    return {"cmd": cmd if isinstance(cmd, str) else " ".join(map(str, cmd)), "exit": r.returncode, "stdout": r.stdout.strip(), "stderr": r.stderr.strip()[-2000:]}


# ------------------------------------------------------------------ Git, disk, credentials (existence only)
out["git"] = {k: run([GIT, *a])["stdout"] for k, a in (("head", ["rev-parse", "HEAD"]), ("branch", ["branch", "--show-current"]),
                                                       ("status_porcelain", ["status", "--porcelain"]))}
du = shutil.disk_usage(str(D))
out["disk"] = {"path": str(D), "free_gb": round(du.free / 1e9, 1), "total_gb": round(du.total / 1e9, 1)}
cdsrc = Path.home() / ".cdsapirc"
out["cds_credentials"] = {"path": str(cdsrc), "exists": cdsrc.exists(), "readable": cdsrc.exists() and bool(cdsrc.stat().st_mode & 0o400),
                          "contents_read": False}

# ------------------------------------------------------------------ runtimes
out["runtime_model"] = cpf.runtime_identity()
drift = {k: out["runtime_model"][k] for k, v in cpf.FROZEN_RUNTIME.items() if out["runtime_model"][k] != v}
if drift:
    P.append(f"model runtime drift {drift}")
probe = ("import sys, numpy, pandas, xarray, cfgrib, eccodes, cdsapi, rasterio, json; import importlib.metadata as md; "
         "print(json.dumps({'python': sys.version.split()[0], 'executable': sys.executable, 'numpy': numpy.__version__, 'pandas': pandas.__version__, "
         "'xarray': xarray.__version__, 'cfgrib': cfgrib.__version__, 'eccodes_python': eccodes.__version__, "
         "'eccodes_lib': eccodes.codes_get_api_version(), 'cdsapi': md.version('cdsapi'), 'ecmwf_datastores_client': md.version('ecmwf-datastores-client'), 'rasterio': rasterio.__version__}))")
r = run([str(CDS_PY), "-c", probe])
out["runtime_cds"] = json.loads(r["stdout"]) if r["exit"] == 0 else {"error": r}
if r["exit"] != 0:
    P.append("CDS interpreter import probe failed")
for name, digest in CONFIG_SHA256.items():
    if sha(paths.CONFIG_DIR / name) != digest:
        P.append(f"config {name} drift")
out["checks"]["configs"] = CONFIG_SHA256
out["helper_sha256"] = {h: sha(ROOT / h) for h in HELPERS}
log("git/runtime/config done")

# ------------------------------------------------------------------ pinned sources and manifest-consumed files
out["pinned"] = {}
for role, (path, digest) in PINNED.items():
    cur = sha(path)
    out["pinned"][role] = {"path": str(path), "sha256": cur, "expected": digest, "match": cur == digest}
    if cur != digest:
        P.append(f"pinned {role} sha256 differs")
cman = json.loads(PINNED["compact_manifest"][0].read_text())
pman = json.loads(PINNED["parent_manifest"][0].read_text())
consumed = {}
for h, e in cman["horizons"].items():
    for arm, ae in e["arms"].items():
        consumed[f"compact h{h} {arm} dataset"] = ae["dataset"]
    for k in ("history_ledger", "idp_ledger", "season_ledger", "oracle_ledger"):
        if k in e:
            consumed[f"compact h{h} {k}"] = e[k]
for k, v in cman["contract"]["files"].items():
    consumed[f"compact contract {k}"] = v
consumed["compact/parent cohort"] = cman["cohort"]
for k, v in cman["sources"].items():
    consumed[f"compact source {k}"] = v
for k, v in pman["inputs"].items():
    consumed[f"parent input {k}"] = v
out["manifest_consumed"] = {}
for label, item in consumed.items():
    cur = sha(item["path"])
    out["manifest_consumed"][label] = {"path": item["path"], "sha256": cur, "match": cur == item["sha256"]}
    if cur != item["sha256"]:
        P.append(f"{label} sha256 differs from its manifest")
build_code_ok = all(sha(ROOT / rel) == d for rel, d in cman["code_sha256"].items())
out["checks"]["compact_build_code_bytes_equal"] = build_code_ok
if not build_code_ok:
    P.append("compact build code bytes differ from the manifest")
log(f"pinned/manifest hashes done ({len(consumed)} consumed files)")

# ------------------------------------------------------------------ contract
meta = json.loads((TASK / "expected_feature_contract_metadata.json").read_text(encoding="utf-8-sig"))
with open(TASK / "expected_feature_contract.csv", encoding="utf-8-sig", newline="") as fh:
    rows = list(csv.DictReader(fh))
with open(TASK / "expected_run_index.csv", encoding="utf-8-sig", newline="") as fh:
    run_index = list(csv.DictReader(fh))
names = [r["predictor"] for r in rows]
contract = {"rows": len(rows), "unique": len(set(names)), "runs": {}}
if len(rows) != 308 or len(set(names)) != 308:
    P.append("contract does not have 308 unique literals")
for rid, (arm, h) in RUNS.items():
    pos = {}
    for r in rows:
        p = json.loads(r["expected_model_positions"]) if r["expected_model_positions"] else {}
        if rid in p:
            pos[int(p[rid])] = r["predictor"]
    proj = [pos[i] for i in range(1, len(pos) + 1)] if sorted(pos) == list(range(1, len(pos) + 1)) else None
    feats = meta["features_by_run"].get(rid)
    cur = cman["horizons"][str(h)]["arms"][arm]["features"]
    idx = next(r for r in run_index if r["run_id"] == rid)
    ok = proj is not None and proj == feats == cur and osf.list_sha256(cur) == idx["schema_sha256"] and int(idx["feature_count"]) == len(cur)
    contract["runs"][rid] = {"n": len(cur), "schema_sha256": osf.list_sha256(cur), "csv_projection_equals_metadata_and_compact_manifest": ok}
    if not ok:
        P.append(f"contract projection {rid} differs")
out["checks"]["contract"] = contract
out["contract_sha256"] = {f: sha(TASK / f) for f in ("expected_feature_contract.csv", "expected_feature_contract_metadata.json", "expected_run_index.csv")}

# ------------------------------------------------------------------ spec/contract copy into the versioned input root
spec_dir = INPUT_ROOT / "approved_spec"
spec_dir.mkdir(parents=True, exist_ok=True)
copied = {}
for rel in SPEC_FILES:
    src = TASK / rel
    dst = spec_dir / rel.replace("research/", "research__")
    shutil.copyfile(src, dst)
    if sha(dst) != sha(src):
        P.append(f"spec copy {rel} differs")
    copied[rel] = {"path": str(dst), "sha256": sha(dst)}
out["approved_spec_copy"] = {"dir": str(spec_dir), "files": copied, "source_task_dir": str(TASK), "source_head": out["git"]["head"]}
log("contract/spec copy done")

# ------------------------------------------------------------------ complete April cohort, static, population
static = cman_static = [c for c in cman["horizons"]["0"]["arms"]["compact_baseline"]["features"][:29]]
chunks = []
for ch in pd.read_csv(PINNED["comprehensive_april"][0], usecols=["area_id", "year", "month", *static, "estimated_population"],
                      chunksize=200_000, float_precision="round_trip", low_memory=False):
    chunks.append(ch[(ch["year"] == 2026) & (ch["month"] == 4)])
april = pd.concat(chunks, ignore_index=True)
del chunks
log(f"comprehensive April rows {len(april)}")
coh = {"rows": len(april), "unique_areas": int(april["area_id"].nunique()), "duplicate_keys": int(april.duplicated(["area_id"]).sum())}
pop = april["estimated_population"]
coh["population"] = {"missing": int(pop.isna().sum()), "negative": int((pop < 0).sum()), "zero": int((pop == 0).sum()),
                     "zero_area_ids": sorted(april.loc[pop == 0, "area_id"].astype(int).tolist()), "nonfinite": int((~np.isfinite(pop)).sum()),
                     "total": float(pop.sum())}
coh["static_missing"] = {c: int(april[c].isna().sum()) for c in static if april[c].isna().any()}
if coh["rows"] != 6188 or coh["unique_areas"] != 6188 or coh["duplicate_keys"]:
    P.append(f"April cohort is not 6188 unique areas: {coh['rows']}/{coh['unique_areas']}")
if coh["population"]["missing"] or coh["population"]["negative"] or coh["population"]["nonfinite"]:
    P.append("April population missing/negative/nonfinite")
old = pd.read_csv(OLD_AREA_TABLE, usecols=["area_id", "estimated_population"], float_precision="round_trip")
mm = april[["area_id", "estimated_population"]].merge(old, on="area_id", how="outer", suffixes=("", "_old"), indicator=True)
coh["population_vs_old_launch_area_table"] = {"both": int((mm["_merge"] == "both").sum()), "only_new": int((mm["_merge"] == "left_only").sum()),
                                               "only_old": int((mm["_merge"] == "right_only").sum()),
                                               "max_abs_diff": float((mm["estimated_population"] - mm["estimated_population_old"]).abs().max())}
if coh["population_vs_old_launch_area_table"]["only_new"] or coh["population_vs_old_launch_area_table"]["only_old"] \
        or coh["population_vs_old_launch_area_table"]["max_abs_diff"] != 0:
    P.append("April population differs from the old launch area table")
h0 = pd.read_csv(cman["horizons"]["0"]["arms"]["compact_baseline"]["dataset"]["path"], usecols=["area_id", "year", "month", *static],
                 float_precision="round_trip")
h0a = h0[(h0["year"] == 2026) & (h0["month"] == 4)].sort_values("area_id").reset_index(drop=True)
cmp = april.set_index("area_id").loc[h0a["area_id"], static].reset_index(drop=True)
same = np.array_equal(cmp.to_numpy(dtype=float), h0a[static].to_numpy(dtype=float), equal_nan=True)
coh["static_parity_with_compact_april_rows"] = {"compact_april_rows": len(h0a), "numeric_and_na_equal": bool(same)}
if not same:
    P.append("static29 differs from compact April rows")
lookup = pd.read_csv(PINNED["country_lookup"][0], keep_default_na=False, na_values=[""])
if lookup["area_id"].duplicated().any():
    P.append("country lookup duplicate area_id")
lk = april[["area_id"]].merge(lookup, on="area_id", how="left")
coh["country"] = {"unmapped": int(lk["country"].isna().sum()), "countries": int(lk["country"].nunique()),
                  "empty_iso3_areas": int(lk["iso3"].isna().sum()), "empty_iso3_countries": sorted(lk.loc[lk["iso3"].isna(), "country"].unique().tolist()),
                  "empty_country_code_countries": sorted(lk.loc[lk["country_code"].isna(), "country"].unique().tolist())}
ref = pd.read_csv(PINNED["country_population_reference"][0], keep_default_na=False)
coh["country_reference"] = {"rows": len(ref), "names_one_to_one": sorted(set(ref["country"])) == sorted(set(lk["country"].dropna())),
                            "namibia_lookup_code_used": ref.loc[ref["country"] == "Namibia", "lookup_code_used"].tolist(),
                            "as_of": sorted(ref["population_as_of_date"].unique().tolist())}
if coh["country"]["unmapped"] or coh["country"]["countries"] != 53 or not coh["country_reference"]["names_one_to_one"]:
    P.append("country mapping/reference join is not 53 exact names")
lk["pop"] = april["estimated_population"].to_numpy()
cs = lk.groupby("country")["pop"].sum().rename("N").reset_index().merge(ref[["country", "population_2025_total"]], on="country")
cs["factor"] = np.where(cs["N"] > 1.10 * cs["population_2025_total"], 0.95 * cs["population_2025_total"] / cs["N"], 1.0)
capped = cs[cs["factor"] < 1]["country"]
eff = (lk["pop"] * lk["country"].map(cs.set_index("country")["factor"])).sum()
coh["country_cap"] = {"capped_countries": int(len(capped)), "capped_areas": int(lk["country"].isin(capped).sum()), "raw_total": float(lk["pop"].sum()),
                      "effective_total": float(eff)}
region = pd.read_csv(PINNED["region_map"][0])
rg = april[["area_id"]].merge(region, on="area_id", how="left")
coh["region"] = {"columns": region.columns.tolist(), "unmapped": int(rg["region"].isna().sum()),
                 "counts": {int(k): int(v) for k, v in rg["region"].value_counts().sort_index().items()}}
if coh["region"]["unmapped"] or sorted(coh["region"]["counts"]) != list(range(9)):
    P.append("region map does not cover the cohort with regions 0..8")
out["checks"]["april_cohort"] = coh
log("cohort/static/population/country/region done")

# ------------------------------------------------------------------ coordinates and CDS points
ident = pd.read_csv(PINNED["identifier_source"][0], usecols=["admin_code", "year", "month", "lat", "lon"], float_precision="round_trip")
ia = ident[(ident["year"] == 2026) & (ident["month"] == 4)].rename(columns={"admin_code": "area_id"})
pts = pd.read_csv(PINNED["cds_points"][0], float_precision="round_trip")
cj = april[["area_id"]].merge(ia[["area_id", "lat", "lon"]], on="area_id", how="left").merge(pts, on="area_id", how="left", suffixes=("", "_pt"))
out["checks"]["coordinates"] = {
    "identifier_april_rows": len(ia), "identifier_duplicates": int(ia.duplicated("area_id").sum()),
    "cohort_missing_identifier_coords": int(cj[["lat", "lon"]].isna().any(axis=1).sum()),
    "cohort_missing_cds_points": int(cj[["lat_pt", "lon_pt"]].isna().any(axis=1).sum()),
    "points_unique": bool(not pts["area_id"].duplicated().any()), "points_finite": bool(np.isfinite(pts[["lat", "lon"]]).all().all()),
    "max_abs_lat_diff": float((cj["lat"] - cj["lat_pt"]).abs().max()), "max_abs_lon_diff": float((cj["lon"] - cj["lon_pt"]).abs().max()),
    "points_outside_cohort": int((~pts["area_id"].isin(april["area_id"])).sum())}
if out["checks"]["coordinates"]["cohort_missing_cds_points"] or out["checks"]["coordinates"]["cohort_missing_identifier_coords"]:
    P.append("cohort areas missing coordinates/points")

# ------------------------------------------------------------------ source grid ends and label availability
pnl = pd.read_csv(PINNED["interim"][0], usecols=["admin_code", "year", "month", "overall_phase"])
pnl["ord"] = pnl["year"] * 12 + pnl["month"] - 1
span = pnl.groupby("admin_code")["ord"].max()
cl_last = pd.read_csv(PINNED["climate_monthly"][0], usecols=["year", "month"]).eval("year * 12 + month - 1").max()
april_ord = 2026 * 12 + 3
coh_areas = set(april["area_id"])
phase = pd.to_numeric(pnl["overall_phase"], errors="coerce")
out["checks"]["source_grids"] = {
    "interim_last_month": osf.ord_label(int(pnl["ord"].max())), "climate_last_month": osf.ord_label(int(cl_last)),
    "cohort_areas_interim_span_ending_before_april": int(sum(1 for a in coh_areas if span.get(a, -1) < april_ord)),
    "noncohort_areas_in_interim": int(len(set(span.index) - coh_areas)),
    "reported_phase_rows_april_2026": int((phase.isin(osf.VALID_PHASES) & (pnl["ord"] == april_ord)).sum()),
    "reported_phase_rows_after_april_2026": int((phase.isin(osf.VALID_PHASES) & (pnl["ord"] > april_ord)).sum()),
    "latest_reported_phase_month": osf.ord_label(int(pnl.loc[phase.isin(osf.VALID_PHASES), "ord"].max()))}
if out["checks"]["source_grids"]["cohort_areas_interim_span_ending_before_april"] or cl_last < april_ord:
    P.append("a source grid ends before the April origin for a cohort area")
del pnl
log("coordinates/source-grid checks done")

# ------------------------------------------------------------------ geometry sidecars
geo = {}
for ext in (".shp", ".shx", ".dbf", ".prj", ".cpg"):
    f = Path(str(GEOMETRY) + ext)
    geo[ext] = {"path": str(f), "sha256": sha(f) if f.exists() else None}
gdf = __import__("geopandas").read_file(str(GEOMETRY) + ".shp")
aid = next(c for c in ("area_id", "admin_code") if c in gdf.columns)
geo["rows"] = len(gdf)
geo["crs"] = str(gdf.crs)
geo["duplicate_area_ids"] = int(gdf[aid].duplicated().sum())
geo["cohort_unmatched"] = int(len(coh_areas - set(pd.to_numeric(gdf[aid]).astype(int))))
geo["geometry_outside_cohort"] = int(len(set(pd.to_numeric(gdf[aid]).astype(int)) - coh_areas))
out["checks"]["geometry"] = geo
if geo["duplicate_area_ids"] or geo["cohort_unmatched"]:
    P.append("geometry duplicates or unmatched cohort areas")
log("geometry done")

# ------------------------------------------------------------------ old artifact identities (no-overwrite baseline)
inv = []
for root in OLD_ROOTS:
    for f in sorted(root.rglob("*")):
        if f.is_file() and ".venv" not in f.parts and "__pycache__" not in f.parts and VERSION not in f.parts \
                and "nowcasting_2026_04_compact_cds_v1" not in f.parts:
            inv.append({"path": str(f), "bytes": f.stat().st_size, "sha256": sha(f)})
inv_path = ROOT / "results/launch/nowcasting_2026_04_compact_cds_v1/preflight/old_artifact_inventory_before.csv"
inv_path.parent.mkdir(parents=True, exist_ok=True)
pd.DataFrame(inv).to_csv(inv_path, index=False)
out["old_artifact_inventory"] = {"path": str(inv_path), "files": len(inv), "roots": [str(r) for r in OLD_ROOTS], "sha256": sha(inv_path)}
log(f"old artifact inventory {len(inv)} files")

out["deferred"] = [
    "CDS provider retrieval, response identities, GRIB decoding, member/year/step completeness and September overlap validation (weather stage)",
    "Original-frequency grid/longitude convention of the new GRIBs (checked on retrieval)",
]
out["passed"] = not P
out["elapsed_seconds"] = round(time.time() - T0, 1)
json_path = TASK / "research/preflight-checkpoint.json"
json_path.write_text(json.dumps(out, indent=2, default=str))
print(json.dumps({"passed": out["passed"], "problems": P, "cohort": {k: coh[k] for k in ("rows", "unique_areas", "population", "country", "country_cap", "region")}}, indent=1, default=str))
