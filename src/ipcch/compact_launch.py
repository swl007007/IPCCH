"""compact_cds_launch_v1: April 2026-origin compact launch, oracle-trained weather arm with CDS inference weather.

Contract (task ``10-08-compact-cds-launch``; ``prd.md`` R1-R15, ``design.md``):

- Five unique fits x four cumulative regressors: compact_baseline H0/H6/H12 (296 features), compact_cds_weather H6/H12
  (308; trained on the realized compact oracle, inferred on the CDS forecast cube). H0 is one shared baseline fit.
- Origin O = 2026-04 for every target: H0 -> 2026-04, H6 -> 2026-10, H12 -> 2027-04.
- Fitting rows: current compact model-ready rows of the matching arm/H with target month before 2026-04-01 and valid
  shares; normalized cumulative targets; weights 0.5 ** ((April 2026 - U) / 24); seed 42, n_jobs 16, fixed configs.
- Inference rows: the complete 6,188-area April 2026 cohort for every target, independent of labels. Static29 from the
  April snapshot; ordinary/z/stress/season blocks rebuilt at O = April with the frozen compact recipes; coordinates from
  the canonical identifier source's April rows; target-calendar dummies by equality to T (2027 -> all year flags 0);
  safe IPC history from reported phases through 2026-03 only; national IDP reports <= April.
- Raw unrounded predictions and ``origin_safe.classify_cumulative`` classes are kept. Population reporting only:
  cumulative differences -> component clip to [0, 1] -> normalize; fixed April population with the legacy country cap.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from ipcch import cds_launch_weather as cw
from ipcch import climate2015_features as cf
from ipcch import compact_features as cpf
from ipcch import origin_safe as osf
from ipcch import paths

VERSION = "compact_cds_launch_v1"
ORIGIN = (2026, 4)
ORIGIN_ORD = 2026 * 12 + 3
LABEL_CUTOFF_ORD = ORIGIN_ORD - 1  # 2026-03: last fitting label month and last inference IPC-history month
TARGETS = {0: (2026, 4), 6: (2026, 10), 12: (2027, 4)}
BASELINE, WEATHER = "compact_baseline", "compact_cds_weather"
TRAINING_ARM = {BASELINE: cpf.BASELINE_ARM, WEATHER: cpf.ORACLE_ARM}
RUNS = ((BASELINE, 0), (BASELINE, 6), (BASELINE, 12), (WEATHER, 6), (WEATHER, 12))
DISPLAY = tuple((arm, h) for arm in (BASELINE, WEATHER) for h in (0, 6, 12))  # WEATHER H0 shows the shared baseline fit
SEED, HALF_LIFE, THRESHOLD, N_JOBS = 42, 24.0, 0.2, 16
COHORT_SIZE = 6188
CAP_TRIGGER, CAP_TARGET = 1.10, 0.95
KEYS = list(osf.KEYS)
PHASES = (1, 2, 3, 4, 5)

A = paths.SOURCE_DATA_DIR / "assembled_IPCCH"
SHARED = Path("/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/IPCCH_shared_folder")
INPUT_ROOT = A / "model_ready" / VERSION
WEATHER_ROOT = paths.SOURCE_DATA_DIR / "CDS_API" / VERSION
RESULTS_ROOT = paths.RESULTS_DIR / "launch" / "nowcasting_2026_04_compact_cds_v1"
REPORTS_ROOT = paths.REPORTS_DIR / "launch" / "nowcasting_2026_04_compact_cds_v1"
MANIFEST_NAME = f"{VERSION}_manifest.json"
PINNED = {
    "compact_manifest": (A / "model_ready/compact_climate_weather_oracle_v1/compact_climate_weather_oracle_v1_manifest.json",
                         "456360536a3929e1571d96ba9f16e2f0de54bc1b20019f797bbe62c0c89732ca"),
    "parent_manifest": (A / "model_ready/origin_safe_climate_idp_v1/origin_safe_climate_idp_v1_manifest.json",
                        "3b479c80498e9f2d6d20b88936fce468f297d2e0ccd6f0cb32c61a7470a209bf"),
    "interim": (A / "interim/IPCCH_2026_target_corrected_nino34_wbfood.csv", "a91719e8e603e11b58e3e44c9a2f4378e4218e1ac408afe03ca54d1b50fb0484"),
    "climate_monthly": (SHARED / "climate_monthly_2015_2026_MODELING_READY.csv", "8082b72ea5fa5c30a7b975b89c1fbbb4530f27a9ce6c5ba4d0e1a4f923320c89"),
    "climate_seasonal": (SHARED / "climate_2015_2026_MODELING_READY.csv", "f024a66c8979fb4a8c66fba1f04e7e69355fa75b499793d29001a146d8c2958e"),
    "comprehensive_april": (A / "features/forecasting_subset_IPCCH_2026_target_corrected_deep_features.csv",
                            "60610cd601e4b0c700cc475903fe807f072f131a97c543dc22f169b2824917e4"),
    "identifier_source": (A / "raw/IPCCH_2026_completed.csv", "ae696087c3bbb280537ae269a05924133acdb51060d31290523404fa8a717673"),
    "cds_points": (A / "spatial/unique_area_id_lat_lon.csv", "3bf8f115ec70cd1e1c907031309b797410a8024cdc1d39265be123ae636d2862"),
    "country_lookup": (A / "country_area_id_lookup.csv", "e2baf6ae9481b42b127db5ce81f3c53ad784bb08ae56dfa56cea74e416b44c90"),
    "idp_admin0_monthly": (Path("/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/Processed_Dataset/IDP_DTM/output/idp_admin0_monthly.csv"),
                           "a1ebb82a8e14fc0fb8103d6086217b93da351fc4a8f7fcfbe9eaa44a9df602e1"),
    "country_population_reference": (paths.REPORTS_DIR / "launch/nowcasting_2026_04/population_projection/countries_2025_population_merged.csv",
                                     "c348cc30cd2b5beae93a11974c4712a3dd6dd822ee902f5458a778effad389b0"),
    "region_map": (paths.REFERENCE_DATA_DIR / "area_id_country_region_mapping.csv", "18ab5099ce2d1154fb5686183ee399124e18427cc1594923f7abe2769da1611d"),
}
CONTRACT_SHA256 = {"expected_feature_contract.csv": "6a16ccd49085ab08cfb1747ea2e851879cab54b72e73158936a64c4568e7cb82",
                   "expected_feature_contract_metadata.json": "6295074fa8a94f45e75c695ea3997a8b6927f1b1b00bb8358ab290c4416de410",
                   "expected_run_index.csv": "25fff00d23b6a2df22f81900832f8b884909eb172d4bd07832544591cf87b616"}
GEOMETRY = A / "spatial" / "ipcch_admin_geometry.shp"
CODE_FILES = ("src/ipcch/compact_launch.py", "src/ipcch/cds_launch_weather.py", "scripts/preprocessing/build_compact_cds_launch_inputs.py",
              "scripts/modeling/run_compact_cds_launch.py", *cpf.FIT_CODE, "src/ipcch/launch_nowcasting.py",
              "src/ipcch/launch_visualizations.py", "src/ipcch/alert_risk_maps.py", "src/ipcch/plot_forecast_weather_phase3plus_maps.py")


class LaunchError(ValueError):
    pass


def log(message: str) -> None:
    print(f"[{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}] {message}", flush=True)


def run_id(arm: str, horizon: int) -> str:
    return f"{arm}/{horizon}m"


def ym(o: int) -> str:
    return osf.ord_label(o)


def sha(path) -> str:
    return osf.file_sha256(path)


def git(*args: str) -> str:
    exe = "/mnt/c/Program Files/Git/cmd/git.exe"
    exe = exe if Path(exe).exists() else "git"
    return subprocess.run([exe, *args], capture_output=True, text=True, cwd=paths.PROJECT_ROOT).stdout.strip()


def code_sha256() -> Dict[str, str]:
    return {rel: sha(paths.PROJECT_ROOT / rel) for rel in CODE_FILES if (paths.PROJECT_ROOT / rel).exists()}


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    osf.dump_json(path, payload)


# --------------------------------------------------------------------------- gates


def check_frozen_runtime() -> Dict[str, str]:
    runtime = cpf.runtime_identity()
    drift = {k: (runtime[k], v) for k, v in cpf.FROZEN_RUNTIME.items() if runtime[k] != v}
    if drift:
        raise LaunchError(f"model runtime differs from the frozen versions: {drift}")
    for name, digest in cpf.FROZEN_CONFIG_SHA256.items():
        if sha(paths.CONFIG_DIR / name) != digest:
            raise LaunchError(f"config {name} differs from the frozen sha256")
    return runtime


def check_pinned_sources(roles: Optional[Sequence[str]] = None) -> Dict[str, dict]:
    out = {}
    for role, (path, digest) in PINNED.items():
        if roles is not None and role not in roles:
            continue
        cur = sha(path)
        if cur != digest:
            raise LaunchError(f"pinned source {role} sha256 differs: {path}")
        out[role] = {"path": str(path), "sha256": cur}
    return out


def load_contract(spec_dir: Path) -> dict:
    """The approved contract bytes copied into the versioned input root (archive-safe), fully parsed.

    Checks the copies against the approved hashes and against the hashes the metadata itself records, projects every
    run from the complete CSV (contiguous ``expected_model_positions``) and re-hashes each ordered list."""
    import csv

    for name, digest in CONTRACT_SHA256.items():
        if sha(spec_dir / name) != digest:
            raise LaunchError(f"approved contract copy {name} differs from the approved bytes")
    meta = json.loads((spec_dir / "expected_feature_contract_metadata.json").read_text(encoding="utf-8-sig"))
    if meta["contract_sha256"] != sha(spec_dir / "expected_feature_contract.csv") or meta["run_index_sha256"] != sha(spec_dir / "expected_run_index.csv"):
        raise LaunchError("contract CSV/run index bytes differ from the hashes recorded in the contract metadata")
    if meta["training_manifest"]["sha256"] != PINNED["compact_manifest"][1]:
        raise LaunchError("contract metadata binds a different training manifest")
    with open(spec_dir / "expected_feature_contract.csv", encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    names = [r["predictor"] for r in rows]
    if len(names) != 308 or len(set(names)) != 308:
        raise LaunchError("contract does not hold 308 unique literals")
    with open(spec_dir / "expected_run_index.csv", encoding="utf-8-sig", newline="") as fh:
        index = {r["run_id"]: r for r in csv.DictReader(fh)}
    for arm, horizon in RUNS:
        rid = run_id(arm, horizon)
        pos = {}
        for r in rows:
            mapping = json.loads(r["expected_model_positions"]) if r["expected_model_positions"] else {}
            if rid in mapping:
                pos[int(mapping[rid])] = r["predictor"]
        if sorted(pos) != list(range(1, len(pos) + 1)):
            raise LaunchError(f"{rid}: contract positions are not contiguous")
        projected = [pos[i] for i in range(1, len(pos) + 1)]
        listed = meta["features_by_run"][rid]
        digest = osf.list_sha256(listed)
        if projected != listed or digest != meta["schema_sha256_by_run"][rid] or digest != index[rid]["schema_sha256"] \
                or int(index[rid]["feature_count"]) != len(listed):
            raise LaunchError(f"{rid}: CSV projection, metadata list and run index disagree")
    if set(index) != {run_id(a, h) for a, h in RUNS}:
        raise LaunchError("run index is not the five approved runs")
    return {"features_by_run": meta["features_by_run"], "dir": str(spec_dir), "sha256": dict(CONTRACT_SHA256)}


def expected_features(contract: dict, arm: str, horizon: int, compact_manifest: dict) -> List[str]:
    """Contract projection; must equal the current compact manifest arm and its frozen schema hash."""
    feats = list(contract["features_by_run"][run_id(arm, horizon)])
    current = compact_manifest["horizons"][str(horizon)]["arms"][TRAINING_ARM[arm]]["features"]
    if feats != current or osf.list_sha256(feats) != cpf.FROZEN_FEATURE_SHA256[(TRAINING_ARM[arm], horizon)]:
        raise LaunchError(f"{run_id(arm, horizon)}: contract schema differs from the current compact schema")
    return feats


# --------------------------------------------------------------------------- training selection


def training_frame(compact_manifest: dict, arm: str, horizon: int) -> Tuple[pd.DataFrame, List[str]]:
    """Compact model-ready rows of the training arm/H with a valid label strictly before 2026-04-01."""
    entry = compact_manifest["horizons"][str(horizon)]["arms"][TRAINING_ARM[arm]]
    if sha(entry["dataset"]["path"]) != entry["dataset"]["sha256"]:
        raise LaunchError(f"{run_id(arm, horizon)}: compact dataset sha256 differs from its manifest")
    data = pd.read_csv(entry["dataset"]["path"], float_precision="round_trip", low_memory=False)
    ords = osf.month_ord(data["year"], data["month"])
    valid = osf.share_validity(data)
    keep = valid & (ords <= LABEL_CUTOFF_ORD)
    frame = data.loc[keep].reset_index(drop=True)
    targets = osf.normalized_cumulative_targets(frame)
    if targets[list(osf.CUMULATIVE_TARGETS)].isna().any().any():
        raise LaunchError("a fitting row lacks a finite normalized target")
    ords = osf.month_ord(frame["year"], frame["month"])
    extra = pd.DataFrame({**{c: targets[c].to_numpy() for c in osf.CUMULATIVE_TARGETS}, "fit_ord": ords,
                          "sample_weight": osf.origin_weights(ords, ORIGIN_ORD, HALF_LIFE)})
    frame = pd.concat([frame.drop(columns=[c for c in extra.columns if c in frame.columns]), extra], axis=1)
    return frame, list(entry["features"])


# --------------------------------------------------------------------------- inference assembly


def april_cohort(columns: Sequence[str]) -> pd.DataFrame:
    """Complete April 2026 rows of the comprehensive source (keys, static29, population); selected columns, chunked."""
    chunks = []
    for ch in pd.read_csv(PINNED["comprehensive_april"][0], usecols=["area_id", "year", "month", *columns], chunksize=200_000,
                          float_precision="round_trip", low_memory=False):
        chunks.append(ch[(ch["year"] == ORIGIN[0]) & (ch["month"] == ORIGIN[1])])
    april = pd.concat(chunks, ignore_index=True).sort_values("area_id", kind="mergesort").reset_index(drop=True)
    if len(april) != COHORT_SIZE or april["area_id"].duplicated().any():
        raise LaunchError(f"April cohort is {len(april)} rows / {april['area_id'].nunique()} areas, expected {COHORT_SIZE}")
    return april


def interim_and_labels(members: Mapping[str, Sequence[str]]) -> Tuple[cf.Grid, pd.DataFrame]:
    member_cols = [c for cols in members.values() for c in cols]
    panel = pd.read_csv(PINNED["interim"][0], usecols=["admin_code", "year", "month", "overall_phase", *cpf.INTERIM_SOURCES[:7], *member_cols])
    panel = panel.rename(columns={"admin_code": "area_id"})
    if panel.duplicated(KEYS).any():
        raise LaunchError("interim panel has duplicate keys")
    labels = panel.loc[pd.to_numeric(panel["overall_phase"], errors="coerce").isin(osf.VALID_PHASES), KEYS + ["overall_phase"]]
    grid = cpf.interim_grid(panel.drop(columns=["overall_phase"]), members)
    return grid, labels.sort_values(KEYS, kind="mergesort").reset_index(drop=True)


def calendar_block(keys: pd.DataFrame, literals: Sequence[str]) -> pd.DataFrame:
    """Fixed existing month_*/year_* literals by equality to the target month (a 2027 target has every year flag False)."""
    out = {}
    for name in literals:
        kind, value = name.split("_")
        out[name] = (keys["month" if kind == "month" else "year"].to_numpy() == int(value))
    return pd.DataFrame(out)


def future_perturbation_check(interim: cf.Grid, climate: cf.Grid, seasons: pd.DataFrame, keys_april: pd.DataFrame,
                              base_monthly: pd.DataFrame, base_seasons: pd.DataFrame) -> Dict[str, int]:
    """Source months after April and seasons ending after May 1 must not change any at-origin input."""
    rng = np.random.default_rng(20261009)

    def late(grid):
        months = np.arange(grid.n_months) + grid.first_ord
        cols = months > ORIGIN_ORD
        values = {}
        for v, arr in grid.values.items():
            arr = arr.copy()
            arr[:, cols] = arr[:, cols] + rng.normal(100.0, 10.0, arr[:, cols].shape)
            values[v] = arr
        return cf.Grid(grid.area_ids, grid.first_ord, grid.n_months, values)

    pert = cpf.monthly_block(late(interim), late(climate), keys_april, [0])[0]
    ps = seasons.copy()
    late_season = (pd.to_datetime(ps["gs_end_date_exclusive"]) > pd.Timestamp(2026, 5, 1)).to_numpy()
    for m in cpf.SEASON_METRICS:
        ps.loc[late_season, m] = ps.loc[late_season, m] + 100.0
    pert_s, _ = cpf.completed_seasons(ps, keys_april["area_id"].to_numpy(), np.full(len(keys_april), ORIGIN_ORD))
    changed = {}
    for a, b in ((base_monthly, pert), (base_seasons, pert_s)):
        x, y = a.to_numpy(dtype=float), b.to_numpy(dtype=float)
        same = (x == y) | (np.isnan(x) & np.isnan(y))
        for name, n in zip(a.columns, (~same).sum(axis=0)):
            changed[name] = int(n)
    bad = {k: v for k, v in changed.items() if v}
    if bad:
        raise LaunchError(f"post-origin source perturbation changed at-origin inputs: {list(bad)[:5]}")
    return {"features_checked": len(changed), "changed_cells": 0, "perturbed_source_months_after": ym(ORIGIN_ORD),
            "perturbed_seasons_ending_after": "2026-05-01"}


def load_weather_cube(cube_path: Path, provenance_path: Path, cohort_ids: np.ndarray) -> Tuple[pd.DataFrame, dict]:
    provenance = json.loads(provenance_path.read_text())
    if provenance.get("status") != "ACCEPTED" or sha(cube_path) != provenance["cube"]["sha256"]:
        raise LaunchError("weather cube is not an ACCEPTED weather-stage output or its bytes changed")
    cube = pd.read_csv(cube_path, float_precision="round_trip")
    if cube["area_id"].duplicated().any():
        raise LaunchError("weather cube has duplicate area_id")
    cube = cube.set_index("area_id").reindex(cohort_ids)
    cols = cw.oracle_columns()
    values = cube[cols].to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise LaunchError(f"weather cube lacks finite values for {int((~np.isfinite(values)).any(axis=1).sum())} cohort areas")
    return cube[cols].reset_index(drop=True), provenance


def build_inference(compact_manifest: dict, contract: dict, cube: Optional[pd.DataFrame]) -> Tuple[Dict[Tuple[str, int], pd.DataFrame], dict]:
    """Ordered inference matrices for the five runs, plus keyed ledgers and checks."""
    parent_features = json.loads(PINNED["parent_manifest"][0].read_text())["horizons"]["0"]["arms"][cpf.PARENT_ARM]["features"]
    groups = cpf.background_groups(parent_features)
    april = april_cohort([*groups["static"], "estimated_population"])
    area = april["area_id"].to_numpy()
    keys_april = pd.DataFrame({"area_id": area, "year": ORIGIN[0], "month": ORIGIN[1]})
    members = compact_manifest["commodity_members"]
    interim, labels = interim_and_labels(members)
    if interim.first_ord + interim.n_months - 1 < ORIGIN_ORD:
        raise LaunchError("interim grid ends before the April origin")
    monthly = pd.read_csv(PINNED["climate_monthly"][0], usecols=["admin_code", "year", "month", *cpf.CLIMATE_SOURCES]).rename(columns={"admin_code": "area_id"})
    climate = cf.Grid.from_long(monthly, cpf.CLIMATE_SOURCES)
    del monthly
    if climate.first_ord + climate.n_months - 1 < ORIGIN_ORD:
        raise LaunchError("climate grid ends before the April origin")
    seasons = pd.read_csv(PINNED["climate_seasonal"][0],
                          usecols=["admin_code", "season_year", "season", "gs_start_date", "gs_end_date_exclusive", *cpf.SEASON_METRICS])
    dyn = cpf.monthly_block(interim, climate, keys_april, [0])[0]
    season_block, season_ledger = cpf.completed_seasons(seasons, area, np.full(len(area), ORIGIN_ORD))
    perturbation = future_perturbation_check(interim, climate, seasons, keys_april, dyn, season_block)
    dynamic = pd.concat([dyn, season_block], axis=1)
    if list(dynamic.columns) != cpf.dynamic_features():
        raise LaunchError("dynamic block order differs from the compact contract")
    ident = pd.read_csv(PINNED["identifier_source"][0], usecols=["admin_code", "year", "month", "lat", "lon"], float_precision="round_trip")
    ident = ident[(ident["year"] == ORIGIN[0]) & (ident["month"] == ORIGIN[1])].rename(columns={"admin_code": "area_id"})
    if ident["area_id"].duplicated().any():
        raise LaunchError("identifier source has duplicate April rows")
    coords = ident.set_index("area_id").reindex(area)[["lat", "lon"]].reset_index(drop=True)
    if coords.isna().any().any():
        raise LaunchError("cohort areas lack canonical April coordinates")
    observations = osf.valid_phase_observations(labels)
    lookup = pd.read_csv(PINNED["country_lookup"][0])
    if lookup["area_id"].duplicated().any():
        raise LaunchError("country lookup has duplicate area_id")
    iso = lookup.set_index("area_id")["iso3"].reindex(area).to_numpy(dtype=object)
    iso = np.where(pd.isna(iso), None, iso)
    idp_obs = osf.idp_observations(pd.read_csv(PINNED["idp_admin0_monthly"][0]))
    matrices, ledgers = {}, {"history": {}, "idp": {}}
    checks = {"perturbation": perturbation, "history_reference": {}, "idp_reference": {}}
    for horizon, (ty, tm) in TARGETS.items():
        keys = pd.DataFrame({"area_id": area, "year": ty, "month": tm})
        history, hist_ledger, hist_check = inference_history(observations, keys, horizon)
        checks["history_reference"][horizon] = hist_check
        idp, idp_ledger = osf.build_idp_features(idp_obs, keys, iso, horizon)
        checks["idp_reference"][horizon] = osf.reference_idp_check(idp_obs, idp_ledger, idp)
        if not np.array_equal(idp_ledger["origin_ord"].to_numpy(), np.full(len(keys), ORIGIN_ORD)):
            raise LaunchError("IDP origin is not April 2026")
        calendar_cols = calendar_block(keys, groups["identifier"][2:])
        ident_block = pd.concat([coords, calendar_cols], axis=1)
        if list(ident_block.columns) != groups["identifier"]:
            raise LaunchError("identifier block order differs")
        base = pd.concat([keys, april[groups["static"]], dynamic, ident_block, history, idp], axis=1)
        feats = expected_features(contract, BASELINE, horizon, compact_manifest)
        matrices[(BASELINE, horizon)] = base[KEYS + feats]
        ledgers["history"][horizon] = hist_ledger
        ledgers["idp"][horizon] = idp_ledger
        if horizon in (6, 12):
            if cube is None:
                raise LaunchError("weather arm needs the accepted CDS cube")
            wfeats = expected_features(contract, WEATHER, horizon, compact_manifest)
            weather = pd.concat([base[KEYS + feats], cube], axis=1)
            matrices[(WEATHER, horizon)] = weather[KEYS + wfeats]
    # same-origin non-calendar inputs identical across targets; weather prefix equals the baseline
    noncal = [c for c in matrices[(BASELINE, 0)].columns if c not in KEYS and not c.startswith(("month_", "year_"))]
    for horizon in (6, 12):
        if not matrices[(BASELINE, horizon)][noncal].equals(matrices[(BASELINE, 0)][noncal]):
            raise LaunchError(f"non-calendar inference inputs differ between H0 and H{horizon}")
        if cube is not None and not matrices[(WEATHER, horizon)].iloc[:, : len(KEYS) + 296].equals(matrices[(BASELINE, horizon)]):
            raise LaunchError(f"weather H{horizon} prefix differs from the baseline matrix")
    h0_ident = add_identifier_check(keys_april, PINNED["identifier_source"][0], matrices[(BASELINE, 0)], groups["identifier"])
    checks.update({"cohort_areas": len(area), "noncalendar_identical_across_targets": True, "weather_prefix_equals_baseline": cube is not None,
                   "h0_identifier_equals_add_identifier_features": h0_ident,
                   "year_2027_flags_all_false": bool(not matrices[(BASELINE, 12)][[c for c in groups["identifier"] if c.startswith("year_")]].any().any()),
                   "season_ledger_rows": len(season_ledger), "population": population_checks(april)})
    season_ledger.insert(0, "area_id", area)
    ledgers["season"] = season_ledger
    ledgers["population"] = april[["area_id", "estimated_population"]]
    return matrices, {"ledgers": ledgers, "checks": checks, "groups": groups}


def inference_history(observations: pd.DataFrame, keys: pd.DataFrame, horizon: int) -> Tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Safe history for launch rows from reported phases through 2026-03 only (an April 2026 report is never used, at
    any horizon), with the existing latest-three rule, differences and keyed source ledger."""
    obs_safe = observations[observations["ord"] <= LABEL_CUTOFF_ORD].reset_index(drop=True)
    history, ledger = osf.build_safe_history(obs_safe, keys, horizon)
    check = osf.reference_history_check(obs_safe, ledger, history)
    src = ledger[[f"history_{k}_source_ord" for k in (1, 2, 3)]].to_numpy(dtype=float)
    if np.isfinite(src).any() and np.nanmax(src) > LABEL_CUTOFF_ORD:
        raise LaunchError("inference IPC history uses a report after 2026-03")
    ledger["inference_ipc_history_max_month"] = ym(LABEL_CUTOFF_ORD)
    return history, ledger, check | {"observations_excluded_after_march": int((observations["ord"] > LABEL_CUTOFF_ORD).sum())}


def add_identifier_check(keys_april: pd.DataFrame, identifier_path: Path, h0: pd.DataFrame, literals: Sequence[str]) -> bool:
    """For the April target, the explicit calendar/coordinate construction equals the existing helper's output."""
    from ipcch.forecasting_weight_decay import add_identifier_features

    ident = pd.read_csv(identifier_path, usecols=["admin_code", "year", "month", "lat", "lon"], float_precision="round_trip")
    ident = ident[(ident["year"] == ORIGIN[0]) & (ident["month"] == ORIGIN[1])]
    helper = add_identifier_features(keys_april.copy(), ident)
    for c in literals:
        want = helper[c].to_numpy(dtype=float) if c in helper.columns else np.zeros(len(helper))
        if not np.array_equal(want, h0[c].to_numpy(dtype=float)):
            raise LaunchError(f"H0 {c} differs from add_identifier_features")
    return True


def population_checks(april: pd.DataFrame) -> dict:
    pop = april["estimated_population"]
    if pop.isna().any() or (pop < 0).any() or not np.isfinite(pop).all():
        raise LaunchError("April population is missing, negative or nonfinite")
    return {"total": float(pop.sum()), "zero_areas": sorted(april.loc[pop == 0, "area_id"].astype(int).tolist())}


# --------------------------------------------------------------------------- mappings, population and cap


def mapping_frame(area_ids: Sequence[int]) -> pd.DataFrame:
    """Exact country name, display codes and region per area; every cohort area maps exactly once (no guessed codes)."""
    lookup = pd.read_csv(PINNED["country_lookup"][0], keep_default_na=False, na_values=[""])
    region = pd.read_csv(PINNED["region_map"][0])
    if list(region.columns) != ["area_id", "region"] or region["area_id"].duplicated().any() or not region["region"].isin(range(9)).all():
        raise LaunchError("region map is not unique area_id -> region 0..8")
    if lookup["area_id"].duplicated().any():
        raise LaunchError("country lookup has duplicate area_id")
    frame = pd.DataFrame({"area_id": np.asarray(area_ids)}).merge(lookup[["area_id", "country", "iso3", "country_code"]], on="area_id",
                                                                   how="left", validate="one_to_one")
    frame = frame.merge(region, on="area_id", how="left", validate="one_to_one")
    if frame["country"].isna().any() or (frame["country"].astype(str).str.strip() == "").any():
        raise LaunchError("cohort areas without an exact country name")
    if frame["region"].isna().any():
        raise LaunchError("cohort areas without a region")
    frame["region"] = frame["region"].astype(int)
    return frame


def country_reference() -> pd.DataFrame:
    ref = pd.read_csv(PINNED["country_population_reference"][0], keep_default_na=False)
    if ref["country"].duplicated().any():
        raise LaunchError("country population reference has duplicate names")
    pop = pd.to_numeric(ref["population_2025_total"], errors="coerce")
    if pop.isna().any() or (pop <= 0).any():
        raise LaunchError("country population reference has a nonpositive/missing total")
    return ref


def cap_audit(population: pd.DataFrame, mapping: pd.DataFrame) -> pd.DataFrame:
    """Legacy cap: if sum of April area population > 110% of the 2025 reference, scale every area to 95% of it."""
    ref = country_reference()
    frame = population.merge(mapping[["area_id", "country"]], on="area_id", validate="one_to_one")
    totals = frame.groupby("country", sort=True).agg(raw_population=("estimated_population", "sum"), areas=("area_id", "size"),
                                                     zero_population_areas=("estimated_population", lambda s: int((s == 0).sum()))).reset_index()
    if sorted(totals["country"]) != sorted(ref["country"]):
        raise LaunchError("cohort countries and the population reference are not one-to-one by exact name")
    audit = totals.merge(ref[["country", "country_code", "country_en", "population_2025_total", "population_as_of_date", "lookup_code_used"]],
                         on="country", validate="one_to_one")
    audit["reference_population"] = audit["population_2025_total"].astype(float)
    audit["raw_to_reference_ratio"] = audit["raw_population"] / audit["reference_population"]
    audit["cap_trigger_ratio"] = CAP_TRIGGER
    audit["cap_applied"] = audit["raw_population"] > CAP_TRIGGER * audit["reference_population"]
    audit["cap_factor"] = np.where(audit["cap_applied"], CAP_TARGET * audit["reference_population"] / audit["raw_population"], 1.0)
    audit["effective_population"] = audit["raw_population"] * audit["cap_factor"]
    return audit.drop(columns=["population_2025_total"])


def repaired_shares(q: np.ndarray) -> Dict[str, np.ndarray]:
    """Reporting-only: d = [1-q2, q2-q3, q3-q4, q4-q5, q5] -> clip [0, 1] -> divide by row sum."""
    q = np.asarray(q, dtype=float)
    if not np.isfinite(q).all():
        raise LaunchError("nonfinite raw cumulative predictions")
    d = np.column_stack([1 - q[:, 0], q[:, 0] - q[:, 1], q[:, 1] - q[:, 2], q[:, 2] - q[:, 3], q[:, 3]])
    b = np.clip(d, 0.0, 1.0)
    total = b.sum(axis=1)
    if not (np.isfinite(total).all() and (total > 0).all()):
        raise LaunchError("repaired share denominator is not positive/finite")
    return {"raw_components": d, "shares": b / total[:, None], "any_negative_component": (d < 0).any(axis=1),
            "any_clipped": ((d < 0) | (d > 1)).any(axis=1), "normalization_sum": total}


# --------------------------------------------------------------------------- input build (assemble-only)


def same_frame(a: pd.DataFrame, b: pd.DataFrame) -> bool:
    """Exact value/NA equality after a CSV round trip: numeric columns bitwise (NaN-aware), others as text."""
    if list(a.columns) != list(b.columns) or len(a) != len(b):
        return False
    for column in a.columns:
        x, y = a[column], b[column]
        if pd.api.types.is_numeric_dtype(x) and pd.api.types.is_numeric_dtype(y):
            if not np.array_equal(x.to_numpy(dtype=float), y.to_numpy(dtype=float), equal_nan=True):
                return False
        elif not np.array_equal(x.where(x.notna(), "").astype(str).to_numpy(), y.where(y.notna(), "").astype(str).to_numpy()):
            return False
    return True


def save_csv(frame: pd.DataFrame, path: Path) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, float_format="%.17g")
    # only empty fields are missing on read-back, so literal strings such as Namibia's lookup code "NA" survive; columns
    # that were object/string in memory are read back as text, so their written spelling is compared exactly
    text = {c: str for c in frame.columns if not pd.api.types.is_numeric_dtype(frame[c])}
    check = pd.read_csv(path, float_precision="round_trip", low_memory=False, keep_default_na=False, na_values=[""], dtype=text)
    if not same_frame(check, frame.reset_index(drop=True)):
        raise LaunchError(f"CSV round trip changed {path.name}")
    return {"path": str(path), "sha256": sha(path), "rows": len(frame), "columns": frame.shape[1]}


def assemble_main(args) -> int:
    t0 = time.time()
    input_root = Path(args.input_root)
    if any(ns in input_root.resolve().parts for ns in cpf.LEGACY_NAMESPACES + (cpf.VERSION,)):
        raise SystemExit("refusing to write compact launch inputs into another version namespace")
    manifest_path = input_root / MANIFEST_NAME
    if manifest_path.exists() and not args.overwrite:
        raise SystemExit(f"{manifest_path} exists (use --overwrite)")
    if not args.weather_cube:
        raise SystemExit("--assemble-only needs --weather-cube from the accepted weather stage")
    provenance_path = Path(args.weather_cube).with_name("cds_weather_provenance.json")
    if not provenance_path.exists() or json.loads(provenance_path.read_text()).get("status") != "ACCEPTED":
        raise SystemExit("weather cube provenance is missing or not ACCEPTED; refusing to assemble")
    runtime = check_frozen_runtime()
    sources = check_pinned_sources()
    contract = load_contract(input_root / "approved_spec")
    cman = json.loads(PINNED["compact_manifest"][0].read_text())
    for rel, digest in cman["code_sha256"].items():
        if sha(paths.PROJECT_ROOT / rel) != digest:
            raise SystemExit(f"compact helper {rel} differs from the code that built the compact inputs")
    cube_path = Path(args.weather_cube)
    points = pd.read_csv(PINNED["cds_points"][0], float_precision="round_trip")
    if points["area_id"].duplicated().any() or not np.isfinite(points[["lat", "lon"]].to_numpy(dtype=float)).all():
        raise SystemExit("fixed extraction points are not unique/finite")
    log("gates passed; building training selections")
    out = {"version": VERSION, "status": "BUILDING", "created_utc": pd.Timestamp.now(tz="UTC").isoformat(),
           "git_head": git("rev-parse", "HEAD"), "git_status_porcelain": git("status", "--porcelain"), "runtime": runtime,
           "code_sha256": code_sha256(), "sources": sources, "contract": contract | {"features_by_run": None},
           "compact_manifest": {"path": str(PINNED["compact_manifest"][0]), "sha256": PINNED["compact_manifest"][1]},
           "origin": ym(ORIGIN_ORD), "targets": {str(h): f"{y}-{m:02d}" for h, (y, m) in TARGETS.items()},
           "training_label_cutoff_exclusive": "2026-04-01", "inference_ipc_history_max_month": ym(LABEL_CUTOFF_ORD),
           "weight_rule": "0.5 ** ((2026-04 - U) / 24) on the label month U", "runs": {}, "checks": {}}
    selections = {}
    for arm, horizon in RUNS:
        frame, feats = training_frame(cman, arm, horizon)
        if feats != expected_features(contract, arm, horizon, cman):
            raise SystemExit(f"{run_id(arm, horizon)}: training features differ from the contract")
        selections[(arm, horizon)] = (frame, feats)
    for horizon in (6, 12):
        b, bf = selections[(BASELINE, horizon)]
        w, wf = selections[(WEATHER, horizon)]
        cols = KEYS + list(osf.CUMULATIVE_TARGETS) + ["sample_weight"]
        if not b[cols].equals(w[cols]) or not w[bf].equals(b[bf]) or wf[: len(bf)] != bf:
            raise SystemExit(f"H{horizon}: paired fitting keys/targets/weights/baseline inputs differ")
    cube, provenance = load_weather_cube(cube_path, provenance_path, april_cohort([])["area_id"].to_numpy())
    log("weather cube accepted; building inference matrices")
    matrices, extra = build_inference(cman, contract, cube)
    for arm, horizon in RUNS:
        rid = run_id(arm, horizon)
        frame, feats = selections[(arm, horizon)]
        if frame["fit_ord"].max() > LABEL_CUTOFF_ORD:
            raise SystemExit(f"{rid}: fitting label after 2026-03")
        fit = frame[KEYS + ["fit_ord", *osf.CUMULATIVE_TARGETS, "sample_weight"]].copy()
        fit["age_months"] = ORIGIN_ORD - fit["fit_ord"]
        tag = f"{arm}_h{horizon}"
        entry = cman["horizons"][str(horizon)]["arms"][TRAINING_ARM[arm]]
        out["runs"][rid] = {
            "arm": arm, "horizon": horizon, "training_arm": TRAINING_ARM[arm], "target_month": out["targets"][str(horizon)],
            "features": feats, "feature_count": len(feats), "feature_sha256": osf.list_sha256(feats),
            "training_dataset": entry["dataset"], "fit_selection": save_csv(fit, input_root / "training" / f"fit_selection_{tag}.csv"),
            "fit_rows": len(fit), "fit_keys_sha256": osf.keys_sha256(fit), "fit_label_months": [ym(int(fit["fit_ord"].min())), ym(int(fit["fit_ord"].max()))],
            "inference": save_csv(matrices[(arm, horizon)], input_root / "inference" / f"inference_{tag}.csv"),
            "inference_keys_sha256": osf.keys_sha256(matrices[(arm, horizon)]),
            "weather_inference": "CDS cube (accepted weather stage)" if arm == WEATHER else "none",
        }
        log(f"{rid}: {len(fit)} fitting rows, {len(matrices[(arm, horizon)])} inference rows, {len(feats)} features")
    led = extra["ledgers"]
    out["ledgers"] = {f"history_h{h}": save_csv(led["history"][h], input_root / "ledgers" / f"history_h{h}.csv") for h in TARGETS}
    out["ledgers"].update({f"idp_h{h}": save_csv(led["idp"][h], input_root / "ledgers" / f"idp_h{h}.csv") for h in TARGETS})
    out["ledgers"]["season"] = save_csv(led["season"], input_root / "ledgers" / "season_h_all_origin_2026_04.csv")
    out["ledgers"]["population"] = save_csv(led["population"], input_root / "ledgers" / "population_april_2026.csv")
    out["weather"] = {"cube": {"path": str(cube_path), "sha256": sha(cube_path)}, "provenance": {"path": str(provenance_path), "sha256": sha(provenance_path)},
                      "status": provenance["status"], "training_definition": "realized compact oracle (observed 1991-2020 declared reference)",
                      "inference_definition": provenance.get("definition")}
    out["checks"] = extra["checks"] | {"paired_training_identical": True}
    out["status"] = "COMPLETE"
    out["elapsed_seconds"] = round(time.time() - t0, 1)
    write_json(manifest_path, out)
    log(f"manifest {manifest_path} ({out['elapsed_seconds']} s)")
    return 0


# --------------------------------------------------------------------------- fitting and raw predictions


FIT_ARTIFACTS = ("feature_schema.json", "fit_keys.csv.gz", "fit_targets.csv.gz", "fit_weights.csv.gz", "inference_features.csv.gz",
                 "predictions_raw.csv", *(f"model_{t}.ubj" for t in osf.CUMULATIVE_TARGETS))
FIT_CODE = (*cpf.FIT_CODE, "src/ipcch/launch_nowcasting.py", "src/ipcch/compact_launch.py", "scripts/modeling/run_compact_cds_launch.py")


def load_manifest(path: Path) -> dict:
    manifest = json.loads(path.read_text())
    if manifest.get("version") != VERSION or manifest.get("status") != "COMPLETE":
        raise LaunchError("input manifest is not a COMPLETE compact_cds_launch_v1 build")
    return manifest


def validate_inputs(manifest_path: Path) -> dict:
    """Prefit gate: frozen runtime/configs, pinned sources, contract bytes, input bytes/schemas and mapping invariants."""
    manifest = load_manifest(manifest_path)
    check_frozen_runtime()
    check_pinned_sources()
    contract = load_contract(Path(manifest["contract"]["dir"]))
    cman = json.loads(PINNED["compact_manifest"][0].read_text())
    for rid, entry in manifest["runs"].items():
        arm, horizon = entry["arm"], entry["horizon"]
        if entry["features"] != expected_features(contract, arm, horizon, cman):
            raise LaunchError(f"{rid}: manifest features differ from the contract")
        for label in ("training_dataset", "fit_selection", "inference"):
            if sha(entry[label]["path"]) != entry[label]["sha256"]:
                raise LaunchError(f"{rid}: {label} bytes differ from the manifest")
    for item in [*manifest["ledgers"].values(), manifest["weather"]["cube"], manifest["weather"]["provenance"]]:
        if sha(item["path"]) != item["sha256"]:
            raise LaunchError(f"{item['path']} bytes differ from the manifest")
    points = pd.read_csv(PINNED["cds_points"][0], float_precision="round_trip")
    if points["area_id"].duplicated().any() or not np.isfinite(points[["lat", "lon"]].to_numpy(dtype=float)).all():
        raise LaunchError("fixed points are not unique/finite")
    population = pd.read_csv(manifest["ledgers"]["population"]["path"], float_precision="round_trip")
    if len(population) != COHORT_SIZE or population["area_id"].duplicated().any() or population["estimated_population"].isna().any() \
            or (population["estimated_population"] < 0).any():
        raise LaunchError("population ledger is not the complete valid cohort")
    mapping = mapping_frame(population["area_id"].to_numpy())
    cap_audit(population, mapping)
    if not points["area_id"].isin(population["area_id"]).sum() == COHORT_SIZE:
        raise LaunchError("cohort areas lack a fixed extraction point")
    return manifest


def fingerprint(manifest_path: Path, manifest: dict, rid: str) -> Tuple[str, dict]:
    entry = manifest["runs"][rid]
    payload = {"version": VERSION, "run": rid, "manifest_sha256": sha(manifest_path), "feature_sha256": entry["feature_sha256"],
               "training_dataset_sha256": entry["training_dataset"]["sha256"], "fit_selection_sha256": entry["fit_selection"]["sha256"],
               "inference_sha256": entry["inference"]["sha256"], "contract_sha256": dict(CONTRACT_SHA256),
               "configs_sha256": dict(cpf.FROZEN_CONFIG_SHA256), "runtime": cpf.runtime_identity(),
               "params": {"seed": SEED, "half_life_months": HALF_LIFE, "phase_threshold": THRESHOLD, "n_jobs": N_JOBS},
               "fit_code_sha256": {rel: sha(paths.PROJECT_ROOT / rel) for rel in FIT_CODE}}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest(), payload


def verify_run_record(run_dir: Path, digest: str) -> Optional[dict]:
    record_path = run_dir / "artifact_record.json"
    if not record_path.exists():
        if run_dir.exists() and any(run_dir.iterdir()):
            raise LaunchError(f"{run_dir} has files but no artifact record; refusing to resume an incomplete run")
        return None
    record = json.loads(record_path.read_text())
    if record.get("fingerprint") != digest:
        raise LaunchError(f"{run_dir} was produced with a different fingerprint; use a new output root")
    if set(record.get("artifacts", {})) != set(FIT_ARTIFACTS) | {"run_metadata.json"}:
        raise LaunchError(f"{run_dir} artifact record is not the complete inventory")
    for name, digest_ in record["artifacts"].items():
        if not (run_dir / name).exists() or sha(run_dir / name) != digest_:
            raise LaunchError(f"{run_dir / name} is missing or changed since its record")
    return record


def fit_run(manifest_path: Path, manifest: dict, rid: str, results_root: Path) -> dict:
    import resource

    from ipcch import launch_nowcasting as ln

    entry = manifest["runs"][rid]
    run_dir = results_root / "runs" / entry["arm"] / f"{entry['horizon']}m"
    digest, payload = fingerprint(manifest_path, manifest, rid)
    record = verify_run_record(run_dir, digest)
    if record is not None:
        log(f"{rid}: verified existing complete run")
        return record
    t0 = time.time()
    feats = entry["features"]
    data = pd.read_csv(entry["training_dataset"]["path"], float_precision="round_trip", low_memory=False)
    fit = pd.read_csv(entry["fit_selection"]["path"], float_precision="round_trip")
    rows = pd.MultiIndex.from_frame(data[KEYS]).get_indexer(pd.MultiIndex.from_frame(fit[KEYS]))
    if (rows < 0).any():
        raise LaunchError(f"{rid}: fitting keys absent from the compact dataset")
    X = data.iloc[rows][feats].reset_index(drop=True)
    weights = pd.Series(fit["sample_weight"].to_numpy(dtype=float), index=X.index)
    if not np.allclose(weights, osf.origin_weights(fit["fit_ord"], ORIGIN_ORD, HALF_LIFE), rtol=0, atol=0):
        raise LaunchError(f"{rid}: stored weights differ from the April 2026 decay rule")
    inference = pd.read_csv(entry["inference"]["path"], float_precision="round_trip", low_memory=False)
    if list(inference.columns) != KEYS + feats:
        raise LaunchError(f"{rid}: inference matrix columns are not keys + the contract order")
    X_inf = inference[feats]
    hp, hp3, provenance = ln.resolve_hyperparameters(SimpleNamespace(hyperparameter_set="canonical", hyperparameters_path=None,
                                                                     hyperparameters_p3_path=None))
    hp, hp3 = dict(hp, n_jobs=N_JOBS), dict(hp3, n_jobs=N_JOBS)
    run_dir.mkdir(parents=True, exist_ok=True)
    preds, fit_seconds = {}, {}
    for target, column in zip(osf.CUMULATIVE_TARGETS, osf.PRED_COLUMNS):
        y = pd.Series(fit[target].to_numpy(dtype=float), index=X.index)
        if not np.isfinite(y).all():
            raise LaunchError(f"{rid}: nonfinite {target}")
        t_fit = time.time()
        model = ln._fit_model(X, y, weights, target, hp, hp3, SEED)
        fit_seconds[target] = round(time.time() - t_fit, 2)
        if list(model.get_booster().feature_names) != feats:
            raise LaunchError(f"{rid}: fitted feature order differs from the contract")
        model.save_model(run_dir / f"model_{target}.ubj")
        values = model.predict(X_inf).astype(float)
        if not np.isfinite(values).all():
            raise LaunchError(f"{rid}: nonfinite raw predictions for {target}")
        preds[column] = values
    out = inference[KEYS].copy()
    out.insert(3, "run_id", rid)
    out.insert(4, "horizon", entry["horizon"])
    out.insert(5, "origin_month", ym(ORIGIN_ORD))
    out.insert(6, "target_month", entry["target_month"])
    for column, values in preds.items():
        out[column] = values
    out["overall_phase_pred"] = osf.classify_cumulative(out, THRESHOLD)
    out.to_csv(run_dir / "predictions_raw.csv", index=False, float_format="%.17g")
    write_json(run_dir / "feature_schema.json", {"run_id": rid, "features": feats, "feature_count": len(feats), "feature_sha256": osf.list_sha256(feats)})
    fit[KEYS + ["fit_ord"]].to_csv(run_dir / "fit_keys.csv.gz", index=False)
    fit[KEYS + list(osf.CUMULATIVE_TARGETS)].to_csv(run_dir / "fit_targets.csv.gz", index=False, float_format="%.17g")
    fit[KEYS + ["age_months", "sample_weight"]].to_csv(run_dir / "fit_weights.csv.gz", index=False, float_format="%.17g")
    inference.to_csv(run_dir / "inference_features.csv.gz", index=False, float_format="%.17g")
    metadata = {"version": VERSION, "run_id": rid, "status": "COMPLETE", "fingerprint": digest, "fingerprint_payload": payload,
                "git_head": git("rev-parse", "HEAD"), "git_status_porcelain": git("status", "--porcelain"),
                "hyperparameters": provenance, "hyperparameters_effective": {"phase2/4/5": hp, "phase3": hp3},
                "input_manifest": str(manifest_path), "features": feats, "feature_count": len(feats), "fit_rows": len(fit),
                "inference_rows": len(out), "fit_seconds": fit_seconds, "run_seconds": round(time.time() - t0, 2),
                "peak_rss_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1),
                "target_year_seen_in_training": entry["target_month"][:4] != "2027",
                "classification": "highest phase with unrounded cumulative score >= 0.2; default 1", "finished_utc": pd.Timestamp.now(tz="UTC").isoformat()}
    write_json(run_dir / "run_metadata.json", metadata)
    artifacts = {name: sha(run_dir / name) for name in (*FIT_ARTIFACTS, "run_metadata.json")}
    record = {"fingerprint": digest, "run_id": rid, "artifacts": artifacts}
    write_json(run_dir / "artifact_record.json", record)
    log(f"{rid}: fitted {len(fit)} rows in {metadata['run_seconds']} s, peak RSS {metadata['peak_rss_mb']} MB")
    return record


# --------------------------------------------------------------------------- population reporting


SHARE_NAMES = [f"phase{k}" for k in PHASES] + ["p3plus", "p4plus"]


def source_run(arm: str, horizon: int) -> Tuple[str, int]:
    """Display arm/H -> unique fit; the weather arm's H0 is the shared baseline fit."""
    return (BASELINE, 0) if horizon == 0 else (arm, horizon)


def read_predictions(results_root: Path, arm: str, horizon: int) -> pd.DataFrame:
    path = results_root / "runs" / arm / f"{horizon}m" / "predictions_raw.csv"
    frame = pd.read_csv(path, float_precision="round_trip")
    if len(frame) != COHORT_SIZE or frame["area_id"].duplicated().any():
        raise LaunchError(f"{path} is not the complete cohort")
    return frame.sort_values("area_id", kind="mergesort").reset_index(drop=True)


def area_table(manifest: dict, results_root: Path) -> Tuple[pd.DataFrame, pd.DataFrame]:
    population = pd.read_csv(manifest["ledgers"]["population"]["path"], float_precision="round_trip").sort_values("area_id").reset_index(drop=True)
    mapping = mapping_frame(population["area_id"].to_numpy())
    audit = cap_audit(population, mapping)
    factor = mapping["country"].map(audit.set_index("country")["cap_factor"]).to_numpy(dtype=float)
    frames = []
    for arm, horizon in DISPLAY:
        src_arm, src_h = source_run(arm, horizon)
        pred = read_predictions(results_root, src_arm, src_h)
        if not np.array_equal(pred["area_id"].to_numpy(), population["area_id"].to_numpy()):
            raise LaunchError("prediction and population keys differ")
        rep = repaired_shares(pred[list(osf.PRED_COLUMNS)].to_numpy(dtype=float))
        f = pd.DataFrame({"version": VERSION, "display_arm": arm, "source_run_id": run_id(src_arm, src_h), "shared_h0_fit": horizon == 0,
                          "horizon": horizon, "origin_month": ym(ORIGIN_ORD), "target_month": pred["target_month"].to_numpy(),
                          "area_id": pred["area_id"].to_numpy(), "country": mapping["country"].to_numpy(), "region": mapping["region"].to_numpy(),
                          "iso3": mapping["iso3"].to_numpy(), "population_reference_month": ym(ORIGIN_ORD),
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
        for i, k in enumerate(PHASES):
            f[f"share_phase{k}"] = shares[:, i]
        f["share_p3plus"] = shares[:, 2:].sum(axis=1)
        f["share_p4plus"] = shares[:, 3:].sum(axis=1)
        for kind in ("raw", "effective"):
            pop = f[f"population_{kind}"].to_numpy()
            for k in PHASES:
                f[f"count_{kind}_phase{k}"] = f[f"share_phase{k}"].to_numpy() * pop
            f[f"count_{kind}_p3plus"] = f[[f"count_{kind}_phase{k}" for k in (3, 4, 5)]].sum(axis=1)
            f[f"count_{kind}_p4plus"] = f[[f"count_{kind}_phase{k}" for k in (4, 5)]].sum(axis=1)
        frames.append(f)
    return pd.concat(frames, ignore_index=True), audit


def aggregate(area: pd.DataFrame, level: str) -> pd.DataFrame:
    keys = ["version", "display_arm", "source_run_id", "shared_h0_fit", "horizon", "origin_month", "target_month"]
    by = keys + ([] if level == "global" else [level])
    count_cols = [f"count_{kind}_{n}" for kind in ("raw", "effective") for n in SHARE_NAMES]
    g = area.groupby(by, sort=True, dropna=False)
    out = g[["population_raw", "population_effective", *count_cols]].sum().reset_index()
    out["n_areas"] = g.size().to_numpy()
    out["n_zero_population_areas"] = g["population_raw"].apply(lambda s: int((s == 0).sum())).to_numpy()
    out["n_capped_areas"] = g["cap_applied"].sum().to_numpy().astype(int)
    for kind in ("raw", "effective"):
        den = out[f"population_{kind}"].to_numpy()
        for n in SHARE_NAMES:
            with np.errstate(invalid="ignore", divide="ignore"):
                out[f"share_{kind}_{n}"] = np.where(den > 0, out[f"count_{kind}_{n}"].to_numpy() / den, np.nan)
        out[f"share_{kind}_status"] = np.where(den > 0, "ok", "undefined")
        out[f"share_{kind}_reason"] = np.where(den > 0, "", "zero population denominator")
    if level == "global":
        out.insert(len(keys), "scope", "global (covered launch areas)")
    return out


def paired_differences(table: pd.DataFrame, key: Sequence[str]) -> pd.DataFrame:
    """compact_cds_weather minus compact_baseline on matching keys/target with identical population."""
    value_cols = [c for c in table.columns if c.startswith(("share_", "count_")) and not c.endswith(("_status", "_reason"))]
    base = table[table["display_arm"] == BASELINE].set_index(["horizon", *key])
    wthr = table[table["display_arm"] == WEATHER].set_index(["horizon", *key])
    if not base.index.equals(wthr.index):
        raise LaunchError("paired arms do not share keys")
    for pop in ("population_raw", "population_effective"):
        if not np.array_equal(base[pop].to_numpy(dtype=float), wthr[pop].to_numpy(dtype=float)):
            raise LaunchError("paired arms have different population denominators")
    out = pd.DataFrame(index=base.index)
    out["version"] = VERSION
    out["contrast"] = f"{WEATHER} - {BASELINE}"
    out["target_month"] = base["target_month"]
    out["shared_h0_fit"] = base["shared_h0_fit"]
    out["population_raw"] = base["population_raw"]
    out["population_effective"] = base["population_effective"]
    for c in value_cols:
        x, y = wthr[c].to_numpy(dtype=float), base[c].to_numpy(dtype=float)
        out[f"delta_{c}"] = x - y
    out["delta_status"] = np.where(np.isfinite(out[[f"delta_{c}" for c in value_cols]].to_numpy()).all(axis=1), "ok", "undefined_in_part")
    return out.reset_index()


def write_population(manifest: dict, results_root: Path, reports_root: Path) -> Dict[str, dict]:
    area, audit = area_table(manifest, results_root)
    pop_dir = results_root / "population"
    pop_dir.mkdir(parents=True, exist_ok=True)
    tables = {"area": area, "country": aggregate(area, "country"), "region": aggregate(area, "region"), "global": aggregate(area, "global")}
    keys = {"area": ["area_id"], "country": ["country"], "region": ["region"], "global": ["scope"]}
    names = {"area": "area_population_predictions", "country": "country_population_summary", "region": "regional_population_summary",
             "global": "global_population_summary"}
    written = {}
    for level, table in tables.items():
        written[names[level]] = save_csv(table, pop_dir / f"{names[level]}.csv")
        diff = paired_differences(table, keys[level])
        written[f"{level}_paired_differences"] = save_csv(diff, pop_dir / f"{level}_population_paired_differences.csv")
    written["country_population_cap_audit"] = save_csv(audit, pop_dir / "country_population_cap_audit.csv")
    copy_dir = reports_root / "population"
    copy_dir.mkdir(parents=True, exist_ok=True)
    for name in ("country_population_summary", "regional_population_summary", "global_population_summary"):
        (copy_dir / f"{name}.csv").write_bytes((pop_dir / f"{name}.csv").read_bytes())
    return written


# --------------------------------------------------------------------------- maps


def _continuous_panel(ax, joined, column: str, title: str, cmap: str, vmin: float, vmax: float) -> None:
    from ipcch import alert_risk_maps as arm

    plot_gdf = joined.copy()
    latam = arm._latam_mask(plot_gdf)
    latam_gdf, plot_gdf = plot_gdf[latam].copy(), plot_gdf[~latam].copy()
    extent_source = plot_gdf.to_crs(epsg=4326) if getattr(plot_gdf, "crs", None) is not None else plot_gdf
    main_extent = plot_gdf[extent_source.geometry.bounds["minx"].ge(arm.AFRICA_MIN_LON)].copy()
    plot_gdf.plot(column=column, cmap=cmap, linewidth=0.08, edgecolor="white", ax=ax, vmin=vmin, vmax=vmax)
    arm._set_padded_extent(ax, main_extent if not main_extent.empty else plot_gdf)
    if len(latam_gdf):
        inset = ax.inset_axes([0.62, 0.06, 0.34, 0.30])
        latam_gdf.plot(column=column, cmap=cmap, linewidth=0.08, edgecolor="white", ax=inset, vmin=vmin, vmax=vmax)
        minx, miny, maxx, maxy = latam_gdf.total_bounds
        inset.set_xlim(minx - (maxx - minx) * 0.05, maxx + (maxx - minx) * 0.05)
        inset.set_ylim(miny - (maxy - miny) * 0.12, maxy + (maxy - miny) * 0.12)
        inset.set_xticks([])
        inset.set_yticks([])
        inset.set_title("Latin America", fontsize=6.5, pad=1.5)
    ax.set_title(title, fontsize=10, weight="bold", pad=5)
    ax.set_axis_off()


def write_maps(area: pd.DataFrame, results_root: Path, reports_root: Path) -> dict:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib as mpl
    import matplotlib.pyplot as plt

    from ipcch import alert_risk_maps as arm
    from ipcch import launch_visualizations as lv

    boundaries = arm.load_spatial_boundaries(GEOMETRY)
    vis_dir, fig_dir = results_root / "visualizations", reports_root / "figures"
    vis_dir.mkdir(parents=True, exist_ok=True)
    fig_dir.mkdir(parents=True, exist_ok=True)
    meta = {"geometry": {ext: {"path": str(GEOMETRY.with_suffix(ext)), "sha256": sha(GEOMETRY.with_suffix(ext))}
                         for ext in (".shp", ".shx", ".dbf", ".prj", ".cpg") if GEOMETRY.with_suffix(ext).exists()},
            "basemap": "none (no download)", "figures": {}}
    # categorical: one per unique fit, raw-derived phase >= 3
    for arm_, horizon in RUNS:
        sub = area[(area["display_arm"] == arm_) & (area["horizon"] == horizon)][["area_id", "overall_phase_pred_raw", "target_month"]]
        pred = sub.rename(columns={"overall_phase_pred_raw": "overall_phase_pred"})
        join = lv.join_for_two_panel(pred, pred.iloc[0:0], boundaries)
        if join.unmatched_prediction or join.mapped_predicted_count != COHORT_SIZE:
            raise LaunchError(f"{run_id(arm_, horizon)}: map join covers {join.mapped_predicted_count} areas, unmatched {join.unmatched_prediction[:5]}")
        target = str(sub["target_month"].iloc[0])
        name = f"crisis_categorical_{arm_}_{horizon}m_{target}"
        fig_path = fig_dir / f"{name}.png"
        lv.plot_predicted_only(join, fig_path, scope="global", no_basemap=True, target_period=f"{target} ({run_id(arm_, horizon)}, origin 2026-04)")
        record = pred.assign(predicted_crisis=pred["overall_phase_pred"] >= 3, run_id=run_id(arm_, horizon))
        rec_path = vis_dir / f"{name}.csv"
        record.to_csv(rec_path, index=False)
        meta["figures"][name] = {"figure": str(fig_path), "record": str(rec_path), "record_sha256": sha(rec_path), "value": "raw-derived overall_phase_pred >= 3",
                                 "mapped_areas": join.mapped_predicted_count, "run_id": run_id(arm_, horizon), "target_month": target}
    # continuous 2x3 repaired P3+ share and 1x2 difference
    joined = {}
    share_rows = []
    for arm_, horizon in DISPLAY:
        sub = area[(area["display_arm"] == arm_) & (area["horizon"] == horizon)][["area_id", "share_p3plus", "target_month", "source_run_id"]].copy()
        sub["p3plus_percent"] = sub["share_p3plus"] * 100.0
        # boundaries carry string-normalized ids; join on a normalized key, keep the integer area_id of the tables
        g = boundaries.rename(columns={"area_id": "join_key"}).merge(sub.assign(join_key=arm.normalize_area_id(sub["area_id"])),
                                                                     on="join_key", how="inner", validate="one_to_one")
        if len(g) != COHORT_SIZE:
            raise LaunchError("continuous map join does not cover the cohort")
        joined[(arm_, horizon)] = g
        share_rows.append(sub.assign(display_arm=arm_, horizon=horizon))
    shares_record = pd.concat(share_rows, ignore_index=True)
    fig, axes = plt.subplots(2, 3, figsize=(19, 11))
    for i, arm_ in enumerate((BASELINE, WEATHER)):
        for j, horizon in enumerate((0, 6, 12)):
            g = joined[(arm_, horizon)]
            shared = " (shared H0 fit)" if horizon == 0 else ""
            _continuous_panel(axes[i, j], g, "p3plus_percent", f"{arm_} H{horizon}{shared}\ntarget {g['target_month'].iloc[0]}", "YlOrRd", 0.0, 100.0)
    sm = mpl.cm.ScalarMappable(norm=mpl.colors.Normalize(0, 100), cmap="YlOrRd")
    fig.colorbar(sm, ax=axes, orientation="horizontal", fraction=0.035, pad=0.04, shrink=0.6).set_label(
        "Predicted repaired Phase 3+ population share (%)")
    fig.suptitle("Compact launch (origin 2026-04): predicted Phase 3+ population share by area — prediction summaries, not scores", fontsize=13, weight="bold")
    p_path = fig_dir / "p3plus_share_comparison_2x3.png"
    fig.savefig(p_path, dpi=200)
    plt.close(fig)
    rec = vis_dir / "p3plus_share_comparison_2x3.csv"
    shares_record.to_csv(rec, index=False, float_format="%.17g")
    meta["figures"]["p3plus_share_comparison_2x3"] = {"figure": str(p_path), "record": str(rec), "record_sha256": sha(rec),
                                                      "value": "repaired share_p3plus x 100 (percent)", "color_limits": [0, 100]}
    diffs = []
    for horizon in (6, 12):
        d = joined[(WEATHER, horizon)][["area_id", "p3plus_percent"]].merge(joined[(BASELINE, horizon)][["area_id", "p3plus_percent", "geometry", "target_month"]],
                                                                            on="area_id", suffixes=("_cds", "_baseline"), validate="one_to_one")
        if len(d) != COHORT_SIZE:
            raise LaunchError(f"difference map H{horizon} does not cover the cohort")
        d["p3plus_pp_difference"] = d["p3plus_percent_cds"] - d["p3plus_percent_baseline"]
        diffs.append((horizon, d))
    limit = max(float(np.abs(d["p3plus_pp_difference"]).max()) for _, d in diffs) or 1.0
    fig, axes = plt.subplots(1, 2, figsize=(14, 6.2))
    gpd = arm._require_geopandas()
    for ax, (horizon, d) in zip(axes, diffs):
        g = gpd.GeoDataFrame(d, geometry="geometry", crs=boundaries.crs)
        _continuous_panel(ax, g, "p3plus_pp_difference", f"CDS weather minus baseline, H{horizon}\ntarget {d['target_month'].iloc[0]}", "RdBu_r", -limit, limit)
    sm = mpl.cm.ScalarMappable(norm=mpl.colors.Normalize(-limit, limit), cmap="RdBu_r")
    fig.colorbar(sm, ax=axes, orientation="horizontal", fraction=0.05, pad=0.05, shrink=0.6).set_label(
        "Difference in predicted repaired Phase 3+ population share (percentage points)")
    fig.suptitle("Compact launch: CDS-weather minus no-oracle baseline (prediction differences, not performance)", fontsize=12, weight="bold")
    d_path = fig_dir / "p3plus_share_difference_1x2.png"
    fig.savefig(d_path, dpi=200)
    plt.close(fig)
    rec = vis_dir / "p3plus_share_difference_1x2.csv"
    pd.concat([d.drop(columns="geometry").assign(horizon=h) for h, d in diffs], ignore_index=True).to_csv(rec, index=False, float_format="%.17g")
    meta["figures"]["p3plus_share_difference_1x2"] = {"figure": str(p_path.with_name(d_path.name)), "record": str(rec), "record_sha256": sha(rec),
                                                      "value": "(CDS - baseline) repaired share_p3plus x 100 (percentage points)",
                                                      "color_limits": [-limit, limit], "h0_difference": 0.0}
    write_json(vis_dir / "figure_metadata.json", meta)
    return meta


# --------------------------------------------------------------------------- codebook and summary


def write_codebook(manifest: dict, results_root: Path, reports_root: Path) -> dict:
    """Actual fitted-input codebook from all 20 boosters, checked against the contract."""
    import csv

    import xgboost as xgb

    contract_dir = Path(manifest["contract"]["dir"])
    with open(contract_dir / "expected_feature_contract.csv", encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    actual = {}
    for arm, horizon in RUNS:
        lists = []
        for target in osf.CUMULATIVE_TARGETS:
            booster = xgb.Booster()
            booster.load_model(str(results_root / "runs" / arm / f"{horizon}m" / f"model_{target}.ubj"))
            lists.append(list(booster.feature_names))
        if any(l != lists[0] for l in lists) or lists[0] != manifest["runs"][run_id(arm, horizon)]["features"]:
            raise LaunchError(f"{run_id(arm, horizon)}: boosters disagree with the run schema")
        actual[run_id(arm, horizon)] = lists[0]
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
        for k in ("family", "source_variable", "base_source_definition", "definition_evidence", "limitations"):
            if k in r:
                row[k] = r[k]
        row["inference_source"] = "CDS forecast cube (ECMWF system51 April 2026 init)" if r.get("family") == "weather_oracle" else "compact recipe at origin 2026-04"
        row["fit_status"] = "fitted_verified_all_20_boosters"
        out_rows.append(row)
    table = pd.DataFrame(out_rows)
    if not table["expected_matches_actual"].all():
        raise LaunchError("actual fitted inputs differ from the contract")
    path = reports_root / "model_run_codebook_en.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(path, index=False, encoding="utf-8-sig")
    return {"path": str(path), "sha256": sha(path), "rows": len(table), "runs": {k: len(v) for k, v in actual.items()}}


def write_summary(manifest: dict, results_root: Path, reports_root: Path, verification: dict) -> Path:
    glob = pd.read_csv(results_root / "population" / "global_population_summary.csv", float_precision="round_trip")
    diff = pd.read_csv(results_root / "population" / "global_population_paired_differences.csv", float_precision="round_trip")
    lines = [f"# {VERSION}: April 2026-origin compact launch with CDS forecast weather", "",
             "Prediction summaries only (no actual-label scoring, bootstrap or SHAP). Origin O = 2026-04; targets 2026-04 (H0, one shared fit), "
             "2026-10 (H6) and 2027-04 (H12). Fixed April 2026 population with the legacy country cap (raw > 110% of the 2025 reference -> 95%).",
             f"Verification passed: `{verification.get('passed')}`; see `results/launch/nowcasting_2026_04_compact_cds_v1/verification.json`.", "",
             "## Global predicted population (capped denominators; repaired disjoint shares)", "",
             "| arm | H | target | population | P3+ share | P3+ people | P4+ share | P4+ people |", "|---|---:|---|---:|---:|---:|---:|---:|"]
    for _, r in glob.sort_values(["display_arm", "horizon"]).iterrows():
        lines.append(f"| {r.display_arm} | {r.horizon} | {r.target_month} | {r.population_effective:,.0f} | {r.share_effective_p3plus:.4f} | "
                     f"{r.count_effective_p3plus:,.0f} | {r.share_effective_p4plus:.4f} | {r.count_effective_p4plus:,.0f} |")
    lines += ["", "## CDS weather minus baseline (global)", "", "| H | target | delta P3+ share | delta P3+ people | delta P4+ share |", "|---:|---|---:|---:|---:|"]
    for _, r in diff.sort_values("horizon").iterrows():
        lines.append(f"| {r.horizon} | {r.target_month} | {r.delta_share_effective_p3plus:+.5f} | {r.delta_count_effective_p3plus:+,.0f} | {r.delta_share_effective_p4plus:+.5f} |")
    lines += ["", "## Definitions and limits", "",
              "- Raw cumulative predictions and the canonical class (highest phase with unrounded score >= 0.2) are kept unchanged; population "
              "tables use reporting-only repaired shares (cumulative differences, clip to [0,1], normalize). Categorical maps use the raw class; "
              "continuous and difference maps use repaired P3+ shares.",
              "- Weather arm: trained on realized compact oracle anomalies (observed, declared 1991-2020 reference); inferred on ECMWF system51 "
              "April 2026 forecast anomalies (1993-2016 model reference): official May-September, October constructed and validated on September. "
              "Fixed containing-cell point sampling. These lineages differ by design.",
              "- October temperature uses 6-hourly instantaneous samples valid in (Oct 1 00, Nov 1 00] UTC. This window was empirically "
              "verified against the supplied system51 September absolute monthly ensemble mean and September anomaly products (the initial "
              "[start, end) window failed both); official primary documents do not explicitly state endpoint inclusivity.",
              "- Original accumulated precipitation shows small endpoint decreases (worst about 0.17 mm) beyond the final GRIB packing bounds "
              "in some members/cells; ECMWF documents spurious decrements in packed cumulative fields, but the upstream cause of the excess is "
              "unverified. Raw signed end-minus-start totals were used unchanged (no clipping or member removal); the September precipitation "
              "overlap passed its frozen bound.",
              "- 2027 targets have every existing year indicator 0 (unseen year); no population growth projection; static snapshots and population "
              "completion are not vintage-certified; inference IPC history uses reports through 2026-03 only.",
              "- H0 is one shared baseline fit; its weather-minus-baseline difference is 0 by construction.", ""]
    path = reports_root / "launch_summary.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


# --------------------------------------------------------------------------- independent verification


def _independent_shares(q: np.ndarray) -> np.ndarray:
    """Per-component construction written separately from ``repaired_shares`` (min/max instead of clip)."""
    comps = [1.0 - q[:, 0], q[:, 0] - q[:, 1], q[:, 1] - q[:, 2], q[:, 2] - q[:, 3], q[:, 3]]
    comps = [np.minimum(np.maximum(c, 0.0), 1.0) for c in comps]
    total = comps[0] + comps[1] + comps[2] + comps[3] + comps[4]
    return np.column_stack([c / total for c in comps])


REQUIRED_FIGURES = tuple(f"crisis_categorical_{a}_{h}m_{TARGETS[h][0]}-{TARGETS[h][1]:02d}.png" for a, h in RUNS) + (
    "p3plus_share_comparison_2x3.png", "p3plus_share_difference_1x2.png")


def verify_outputs(manifest_path: Path, results_root: Path, reports_root: Path) -> dict:
    """Independent saved-artifact verification (different arithmetic path from the production reporting helpers)."""
    import xgboost as xgb

    manifest = load_manifest(manifest_path)
    problems: List[str] = []
    checks = {"models_reloaded": 0, "max_replay_abs_diff": 0.0, "population_columns_checked": 0, "difference_columns_checked": 0}

    def close(a, b, atol, rtol=0.0):
        a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
        return a.shape == b.shape and np.array_equal(np.isnan(a), np.isnan(b)) and np.allclose(a[~np.isnan(a)], b[~np.isnan(b)], atol=atol, rtol=rtol)

    # ---- fits: records, schemas, finite replay, keys/targets/weights
    fit_frames = {}
    for arm, horizon in RUNS:
        rid = run_id(arm, horizon)
        run_dir = results_root / "runs" / arm / f"{horizon}m"
        digest, _ = fingerprint(manifest_path, manifest, rid)
        try:
            verify_run_record(run_dir, digest)
        except LaunchError as exc:
            problems.append(f"{rid}: {exc}")
            continue
        feats = manifest["runs"][rid]["features"]
        schema = json.loads((run_dir / "feature_schema.json").read_text())
        if schema["features"] != feats or osf.list_sha256(feats) != cpf.FROZEN_FEATURE_SHA256[(TRAINING_ARM[arm], horizon)]:
            problems.append(f"{rid}: saved schema differs from the frozen contract")
        inf = pd.read_csv(run_dir / "inference_features.csv.gz", float_precision="round_trip", low_memory=False)
        pred = pd.read_csv(run_dir / "predictions_raw.csv", float_precision="round_trip")
        if not inf[KEYS].equals(pred[KEYS]) or len(pred) != COHORT_SIZE or pred["area_id"].nunique() != COHORT_SIZE:
            problems.append(f"{rid}: inference/prediction keys differ or cohort incomplete")
        if not same_frame(inf, pd.read_csv(manifest["runs"][rid]["inference"]["path"], float_precision="round_trip", low_memory=False)):
            problems.append(f"{rid}: saved inference matrix differs from the input build")
        for target, column in zip(osf.CUMULATIVE_TARGETS, osf.PRED_COLUMNS):
            booster = xgb.Booster()
            booster.load_model(str(run_dir / f"model_{target}.ubj"))
            if list(booster.feature_names) != feats:
                problems.append(f"{rid} {target}: booster feature order differs")
            again = booster.predict(xgb.DMatrix(inf[feats], feature_names=feats)).astype(float)
            saved = pred[column].to_numpy(dtype=float)
            if not (np.isfinite(again).all() and np.isfinite(saved).all()):
                problems.append(f"{rid} {target}: nonfinite replayed or saved predictions")
                continue
            diff = float(np.max(np.abs(again - saved)))
            checks["max_replay_abs_diff"] = max(checks["max_replay_abs_diff"], diff)
            if not diff <= 1e-6:
                problems.append(f"{rid} {target}: replay differs by {diff}")
            checks["models_reloaded"] += 1
        q = pred[list(osf.PRED_COLUMNS)].to_numpy(dtype=float)
        cls = np.select([q[:, 3] >= THRESHOLD, q[:, 2] >= THRESHOLD, q[:, 1] >= THRESHOLD, q[:, 0] >= THRESHOLD], [5, 4, 3, 2], default=1)
        if not np.array_equal(cls, pred["overall_phase_pred"].to_numpy()):
            problems.append(f"{rid}: classification differs from the unrounded >= 0.2 rule")
        keys = pd.read_csv(run_dir / "fit_keys.csv.gz")
        targets = pd.read_csv(run_dir / "fit_targets.csv.gz", float_precision="round_trip")
        weights = pd.read_csv(run_dir / "fit_weights.csv.gz", float_precision="round_trip")
        ford = keys["year"].to_numpy() * 12 + keys["month"].to_numpy() - 1
        if ford.max() > LABEL_CUTOFF_ORD or not np.array_equal(weights["age_months"].to_numpy(), ORIGIN_ORD - ford) \
                or not np.allclose(weights["sample_weight"], 0.5 ** ((ORIGIN_ORD - ford) / 24.0), rtol=0, atol=1e-15):
            problems.append(f"{rid}: fitting label cutoff/age/weight check failed")
        data = pd.read_csv(manifest["runs"][rid]["training_dataset"]["path"], usecols=KEYS + list(osf.SHARE_COLUMNS) + ["overall_phase"],
                           float_precision="round_trip")
        rows = pd.MultiIndex.from_frame(data[KEYS]).get_indexer(pd.MultiIndex.from_frame(keys[KEYS]))
        sh = data.iloc[rows][list(osf.SHARE_COLUMNS)].to_numpy(dtype=float)
        norm = sh / sh.sum(axis=1, keepdims=True)
        expect = np.column_stack([norm[:, k:].sum(axis=1) for k in (1, 2, 3, 4)])
        if (rows < 0).any() or not np.allclose(expect, targets[list(osf.CUMULATIVE_TARGETS)].to_numpy(), rtol=0, atol=1e-12):
            problems.append(f"{rid}: fitting targets differ from the independent share normalization")
        valid = osf.share_validity(data) & (osf.month_ord(data["year"], data["month"]) <= LABEL_CUTOFF_ORD)
        if not keys[KEYS].equals(data.loc[valid, KEYS].reset_index(drop=True)):
            problems.append(f"{rid}: fitting keys are not every valid label before 2026-04")
        fit_frames[rid] = (keys, targets, weights)
    for horizon in (6, 12):
        a, b = fit_frames.get(run_id(BASELINE, horizon)), fit_frames.get(run_id(WEATHER, horizon))
        if not (a and b) or not all(x.equals(y) for x, y in zip(a, b)):
            problems.append(f"H{horizon}: paired fitting keys/targets/weights differ or are missing")

    # ---- population: every share/count/denominator at four levels, recomputed from raw predictions and sources
    pop_dir = results_root / "population"
    read = lambda name: pd.read_csv(pop_dir / f"{name}.csv", float_precision="round_trip", keep_default_na=False, na_values=[""])  # noqa: E731
    population = pd.read_csv(PINNED["comprehensive_april"][0], usecols=["area_id", "year", "month", "estimated_population"], chunksize=500_000,
                             float_precision="round_trip")
    population = pd.concat([c[(c["year"] == ORIGIN[0]) & (c["month"] == ORIGIN[1])] for c in population]).set_index("area_id")["estimated_population"]
    lookup = pd.read_csv(PINNED["country_lookup"][0], keep_default_na=False, na_values=[""]).set_index("area_id")["country"]
    ref = pd.read_csv(PINNED["country_population_reference"][0], keep_default_na=False).set_index("country")["population_2025_total"].astype(float)
    regions = pd.read_csv(PINNED["region_map"][0]).set_index("area_id")["region"]
    ids = np.sort(population.index.to_numpy())
    raw_pop = population.reindex(ids).to_numpy(dtype=float)
    country = lookup.reindex(ids).to_numpy()
    countries = sorted(set(country))
    cidx = np.array([countries.index(c) for c in country])
    n_c = np.zeros(len(countries))
    np.add.at(n_c, cidx, raw_pop)
    r_c = ref.reindex(countries).to_numpy()
    fac = np.where(n_c > 1.10 * r_c, 0.95 * r_c / n_c, 1.0)
    eff_pop = raw_pop * fac[cidx]
    audit = read("country_population_cap_audit").set_index("country").reindex(countries)
    if not close(audit["cap_factor"], fac, 1e-15) or not np.array_equal(audit["cap_applied"].to_numpy(dtype=bool), fac < 1) \
            or not close(audit["raw_population"], n_c, 1e-6, 1e-12) or not close(audit["effective_population"], n_c * fac, 1e-6, 1e-12):
        problems.append("cap audit differs from the independent recomputation")
    checks.update({"capped_countries": int((fac < 1).sum()), "capped_areas": int((fac[cidx] < 1).sum()),
                   "population_raw_total": float(raw_pop.sum()), "population_effective_total": float(eff_pop.sum())})
    levels = {"area": (np.arange(len(ids)), list(ids), "area_id", "area_population_predictions"),
              "country": (cidx, countries, "country", "country_population_summary"),
              "region": (regions.reindex(ids).to_numpy().astype(int), list(range(9)), "region", "regional_population_summary"),
              "global": (np.zeros(len(ids), dtype=int), ["global (covered launch areas)"], "scope", "global_population_summary")}
    pops = {"raw": raw_pop, "effective": eff_pop}
    expected = {}  # (arm, horizon, level) -> dict column -> array
    area_saved = read("area_population_predictions")
    for arm, horizon in DISPLAY:
        pred = read_predictions(results_root, *source_run(arm, horizon))
        if not np.array_equal(pred["area_id"].to_numpy(), ids):
            problems.append(f"{arm} H{horizon}: prediction keys differ from the population cohort")
            continue
        s = _independent_shares(pred[list(osf.PRED_COLUMNS)].to_numpy(dtype=float))
        named = {f"phase{k}": s[:, i] for i, k in enumerate(PHASES)} | {"p3plus": s[:, 2] + s[:, 3] + s[:, 4], "p4plus": s[:, 3] + s[:, 4]}
        sub = area_saved[(area_saved["display_arm"] == arm) & (area_saved["horizon"] == horizon)].sort_values("area_id")
        if not np.array_equal(sub["area_id"].to_numpy(), ids) or not np.array_equal(sub["crisis_raw_phase3plus"].to_numpy(dtype=bool),
                                                                                       pred["overall_phase_pred"].to_numpy() >= 3):
            problems.append(f"{arm} H{horizon}: area keys or raw crisis flags differ")
            continue
        for level, (index, labels, key, name) in levels.items():
            cols = {}
            for kind, pop in pops.items():
                den = np.zeros(len(labels))
                np.add.at(den, index, pop)
                cols[f"population_{kind}"] = den
                for n, share in named.items():
                    tot = np.zeros(len(labels))
                    np.add.at(tot, index, share * pop)
                    cols[f"count_{kind}_{n}"] = tot
                    if level == "area":
                        cols[f"share_{n}"] = share
                    else:
                        with np.errstate(invalid="ignore", divide="ignore"):
                            cols[f"share_{kind}_{n}"] = np.where(den > 0, tot / den, np.nan)
                if level != "area":
                    cols[f"share_{kind}_status"] = np.where(den > 0, "ok", "undefined")
            expected[(arm, horizon, level)] = cols
            saved = sub if level == "area" else read(name)
            if level != "area":
                saved = saved[(saved["display_arm"] == arm) & (saved["horizon"] == horizon)]
            saved = saved.set_index(key)
            if len(saved) != len(labels) or saved.index.duplicated().any():
                problems.append(f"{arm} H{horizon} {level}: table rows are not exactly the {len(labels)} groups")
                continue
            saved = saved.reindex(labels)
            for column, want in cols.items():
                checks["population_columns_checked"] += 1
                if column.endswith("_status"):
                    ok = np.array_equal(saved[column].astype(str).to_numpy(), want)
                else:
                    tol = (1e-12, 0.0) if column.startswith("share_") else (1e-6, 1e-12)
                    ok = close(saved[column], want, *tol)
                if not ok:
                    problems.append(f"{arm} H{horizon} {level}: {column} differs from the independent recomputation")
            if not close(np.column_stack([cols[f"count_effective_phase{k}"] for k in PHASES]).sum(axis=1), cols["population_effective"], 1e-6, 1e-12):
                problems.append(f"{arm} H{horizon} {level}: phase counts do not sum to the population")
    for level, (_, labels, key, name) in levels.items():
        saved = pd.read_csv(pop_dir / f"{level}_population_paired_differences.csv", float_precision="round_trip", keep_default_na=False, na_values=[""])
        for horizon in (0, 6, 12):
            b, w = expected.get((BASELINE, horizon, level)), expected.get((WEATHER, horizon, level))
            part = saved[saved["horizon"] == horizon].set_index(key)
            if b is None or w is None or len(part) != len(labels):
                problems.append(f"H{horizon} {level}: paired difference rows missing")
                continue
            part = part.reindex(labels)
            for column in (c for c in b if not c.endswith("_status") and not c.startswith("population_")):
                checks["difference_columns_checked"] += 1
                want = w[column] - b[column]
                if not close(part[f"delta_{column}"], want, 1e-12 if column.startswith("share_") else 1e-6, 0.0 if column.startswith("share_") else 1e-12):
                    problems.append(f"H{horizon} {level}: delta_{column} differs")
                if horizon == 0 and not np.all((part[f"delta_{column}"].to_numpy(dtype=float) == 0) | np.isnan(part[f"delta_{column}"].to_numpy(dtype=float))):
                    problems.append(f"H0 {level}: delta_{column} is not exactly 0 for the shared fit")

    # ---- figures: exactly the seven PNGs, complete records with matching hashes and table values
    fig_dir, vis_dir = reports_root / "figures", results_root / "visualizations"
    pngs = sorted(p.name for p in fig_dir.glob("*.png")) if fig_dir.exists() else []
    if pngs != sorted(REQUIRED_FIGURES) or any((fig_dir / f).stat().st_size == 0 for f in pngs):
        problems.append(f"figures are not exactly the seven required PNGs: {pngs}")
    meta_path = vis_dir / "figure_metadata.json"
    if not meta_path.exists():
        problems.append("figure metadata missing")
    else:
        meta = json.loads(meta_path.read_text())
        for name, entry in meta["figures"].items():
            if not Path(entry["record"]).exists() or sha(entry["record"]) != entry["record_sha256"] or not Path(entry["figure"]).exists():
                problems.append(f"figure {name}: record/figure missing or record hash differs")
        area = area_saved
        rec = pd.read_csv(vis_dir / "p3plus_share_comparison_2x3.csv", float_precision="round_trip")
        if sorted(rec.groupby(["display_arm", "horizon"]).size().items()) != sorted(((a, h), COHORT_SIZE) for a, h in DISPLAY):
            problems.append("2x3 map record is not six complete cohorts")
        for (arm, horizon), part in rec.groupby(["display_arm", "horizon"]):
            want = area[(area["display_arm"] == arm) & (area["horizon"] == horizon)].set_index("area_id")["share_p3plus"].reindex(ids) * 100.0
            if part["area_id"].nunique() != COHORT_SIZE or not close(part.set_index("area_id")["p3plus_percent"].reindex(ids), want, 1e-10):
                problems.append(f"map record {arm} H{horizon} differs from the area table")
        drec = pd.read_csv(vis_dir / "p3plus_share_difference_1x2.csv", float_precision="round_trip")
        if sorted(drec.groupby("horizon").size().items()) != [(6, COHORT_SIZE), (12, COHORT_SIZE)]:
            problems.append("1x2 difference record is not two complete cohorts")
        for horizon, part in drec.groupby("horizon"):
            b = area[(area["display_arm"] == BASELINE) & (area["horizon"] == horizon)].set_index("area_id")["share_p3plus"].reindex(ids)
            w = area[(area["display_arm"] == WEATHER) & (area["horizon"] == horizon)].set_index("area_id")["share_p3plus"].reindex(ids)
            if not close(part.set_index("area_id")["p3plus_pp_difference"].reindex(ids), (w - b) * 100.0, 1e-10):
                problems.append(f"difference map record H{horizon} differs from the tables")
        for arm, horizon in RUNS:
            target = TARGETS[horizon]
            path = vis_dir / f"crisis_categorical_{arm}_{horizon}m_{target[0]}-{target[1]:02d}.csv"
            cat = pd.read_csv(path)
            pred = read_predictions(results_root, arm, horizon).set_index("area_id").reindex(ids)
            if cat["area_id"].nunique() != COHORT_SIZE or len(cat) != COHORT_SIZE or \
                    not np.array_equal(cat.set_index("area_id").reindex(ids)["predicted_crisis"].to_numpy(dtype=bool), pred["overall_phase_pred"].to_numpy() >= 3):
                problems.append(f"categorical record {run_id(arm, horizon)} incomplete or differs from the raw class")
    # ---- inventory and old artifacts
    inventory = [{"path": str(p), "sha256": sha(p), "bytes": p.stat().st_size} for root in (results_root, reports_root) for p in sorted(root.rglob("*"))
                 if p.is_file() and p.name not in ("verification.json", "launch_summary.md")]
    old = pd.read_csv(results_root / "preflight" / "old_artifact_inventory_before.csv")
    changed = [r.path for r in old.itertuples() if not Path(r.path).exists() or sha(r.path) != r.sha256]
    if changed:
        problems.append(f"old artifacts changed: {changed[:5]}")
    checks.update({"old_artifacts_checked": len(old), "old_artifacts_changed": len(changed), "inventory_files": len(inventory), "figures": pngs})
    result = {"version": VERSION, "passed": not problems and checks["models_reloaded"] == 20, "problems": problems, "checks": checks,
              "tolerances": {"replay": "finite, atol 1e-6, rtol 0; classification exact", "shares": "atol 1e-12", "counts": "atol 1e-6, rtol 1e-12",
                             "csv": "float_precision=round_trip; only empty fields missing"},
              "manifest": {"path": str(manifest_path), "sha256": sha(manifest_path)}, "git_head": git("rev-parse", "HEAD"),
              "runtime": cpf.runtime_identity(), "inventory": inventory, "created_utc": pd.Timestamp.now(tz="UTC").isoformat(),
              "terminology": "prediction summaries; no scoring, bootstrap or SHAP"}
    write_json(results_root / "verification.json", result)
    return result


# --------------------------------------------------------------------------- CLI entry (scripts/modeling/run_compact_cds_launch.py)


def run_main(args) -> int:
    manifest_path = Path(args.input_manifest)
    results_root, reports_root = Path(args.results_root), Path(args.reports_root)
    for root in (results_root, reports_root):
        if any(part in root.resolve().parts for part in ("nowcasting_2026_04", "nowcasting_2026_04_forecasted_weather",
                                                          "nowcasting_2026_04_forecasted_weather_scopes")):
            raise SystemExit(f"refusing to write into an existing launch namespace: {root}")
    manifest = validate_inputs(manifest_path)
    plan = [(a, h) for a, h in RUNS if not args.runs or run_id(a, h) in args.runs]
    if args.validate_only:
        print(f"validate-only: inputs and prefit gates passed; runs {[run_id(a, h) for a, h in plan]}; features "
              f"{ {run_id(a, h): manifest['runs'][run_id(a, h)]['feature_count'] for a, h in plan} }; no fitting, nothing written", flush=True)
        return 0
    if args.approve_training:
        for arm, horizon in plan:
            fit_run(manifest_path, manifest, run_id(arm, horizon), results_root)
    if args.report:
        written = write_population(manifest, results_root, reports_root)
        area, _ = area_table(manifest, results_root)
        maps = write_maps(area, results_root, reports_root)
        codebook = write_codebook(manifest, results_root, reports_root)
        write_json(results_root / "report_outputs.json", {"population": written, "maps": maps, "codebook": codebook})
    if args.verify:
        result = verify_outputs(manifest_path, results_root, reports_root)
        write_summary(manifest, results_root, reports_root, result)
        print(json.dumps({k: result[k] for k in ("passed", "problems", "checks")}, indent=1, default=str), flush=True)
        return 0 if result["passed"] else 1
    return 0
