"""Build climate2015_v1 model-ready datasets: current fs0-fs3 files with old FLDAS/MODIS climate
features replaced by features engineered from the 2015-2026 climate release.

Writes ``masked`` (primary; scope-anchored features NaN where the old Rainf scope lag is NaN) and
``unmasked`` variants for fs0-fs2, and one dataset for fs3 (no scope block), plus a feature manifest
and build summary. See ``.trellis/tasks/10-05-global-climate-2015-features/design.md``.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = next(path for path in Path(__file__).resolve().parents if (path / "src").exists())
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import numpy as np
import pandas as pd

from ipcch import climate2015_features as cf
from ipcch import paths

SHARED = Path("/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/IPCCH_shared_folder")
MONTHLY_PATH = SHARED / "climate_monthly_2015_2026_MODELING_READY.csv"
SEASONAL_PATH = SHARED / "climate_2015_2026_MODELING_READY.csv"
INTERIM_PATH = paths.SOURCE_DATA_DIR / "assembled_IPCCH" / "interim" / "IPCCH_2026_target_corrected_nino34_wbfood.csv"
OUT_DIR = paths.SOURCE_DATA_DIR / "assembled_IPCCH" / "model_ready" / "climate2015_v1"
KEYS = ["area_id", "year", "month"]
# fs -> (paths key, scope anchor or None, output stem, expected old-climate columns removed)
SCOPES = {
    "fs0": ("deep_features_scope_0m_model_ready_dataset", 0, "scope_0m_model_ready", 142),
    "fs1": ("deep_features_scope_3m_model_ready_dataset", 3, "scope_3m_model_ready", 142),
    "fs2": ("deep_features_scope_6m_model_ready_dataset", 6, "scope_6m_model_ready", 142),
    "fs3": ("deep_features_forecasting_dataset", None, "forecasting_ready", 97),
}
SCOPE_ANCHORED_BLOCKS = ("scope_s", "seasonal")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 22), b""):
            digest.update(chunk)
    return digest.hexdigest()


def output_path(out_dir: Path, stem: str, variant: str) -> Path:
    return out_dir / f"forecasting_subset_IPCCH_2026_climate2015_v1_{variant}_{stem}.csv"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--scopes", nargs="+", default=list(SCOPES), choices=list(SCOPES))
    parser.add_argument("--monthly", default=str(MONTHLY_PATH))
    parser.add_argument("--seasonal", default=str(SEASONAL_PATH))
    parser.add_argument("--interim", default=str(INTERIM_PATH), help="Source of area coordinates for neighbours (as upstream).")
    parser.add_argument("--out-dir", default=str(OUT_DIR))
    parser.add_argument("--sample-areas", type=int, help="Smoke mode: keep rows of this many seeded areas.")
    parser.add_argument("--no-hash", action="store_true", help="Skip input sha256 (smoke runs).")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    t0 = time.time()
    out_dir = Path(args.out_dir)
    planned = []
    for fs in args.scopes:
        _, anchor, stem, _ = SCOPES[fs]
        planned += [output_path(out_dir, stem, v) for v in (("masked", "unmasked") if anchor is not None else ("masked",))]
    existing = [str(p) for p in planned if p.exists()]
    if existing and not args.overwrite:
        raise SystemExit("outputs exist (use --overwrite): " + "; ".join(existing))
    out_dir.mkdir(parents=True, exist_ok=True)

    monthly = pd.read_csv(args.monthly, usecols=["admin_code", "year", "month", *cf.MONTHLY_VARIABLES]).rename(columns={"admin_code": "area_id"})
    grid = cf.Grid.from_long(monthly, cf.MONTHLY_VARIABLES)
    del monthly
    seasons = pd.read_csv(args.seasonal, usecols=["admin_code", "season_year", "season", "gs_start_date", "gs_end_date_exclusive", *cf.SEASONAL_VARIABLES])
    coords = pd.read_csv(args.interim, usecols=["admin_code", "lat", "lon"]).groupby("admin_code")[["lat", "lon"]].mean().reindex(grid.area_ids)
    valid = coords["lat"].between(-90, 90).to_numpy() & coords["lon"].between(-180, 180).to_numpy()
    neighbors = cf.build_neighbors(coords["lat"].to_numpy(), coords["lon"].to_numpy(), valid)
    print(f"[load] grid {grid.values[cf.MONTHLY_VARIABLES[0]].shape}, seasons {len(seasons)}, valid coords {valid.sum()} ({time.time()-t0:.0f}s)", flush=True)

    summary = {"inputs": {}, "scopes": {}, "git_head": subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=PROJECT_ROOT).stdout.strip(),
               "versions": {"numpy": np.__version__, "pandas": pd.__version__}, "sample_areas": args.sample_areas,
               "grid": {"first_month": f"{grid.first_ord // 12}-{grid.first_ord % 12 + 1:02d}", "n_months": grid.n_months, "n_areas": len(grid.area_ids)}}
    for label, p in (("monthly", args.monthly), ("seasonal", args.seasonal), ("interim_coords", args.interim)):
        summary["inputs"][label] = {"path": str(p), "sha256": None if args.no_hash else sha256(Path(p))}
    manifests = []
    for fs in args.scopes:
        key, anchor, stem, expected_removed = SCOPES[fs]
        src_path = paths.external_path(key)
        df = pd.read_csv(src_path, low_memory=False)
        if args.sample_areas:
            rng = np.random.default_rng(42)
            keep = rng.choice(df["area_id"].unique(), size=args.sample_areas, replace=False)
            df = df[df["area_id"].isin(keep)].reset_index(drop=True)
        old = [c for c in df.columns if cf.is_old_climate_column(c)]
        if len(old) != expected_removed:
            raise ValueError(f"{fs}: expected {expected_removed} old climate columns, found {len(old)}")
        context_cols = [cf.ENSO_SHARE, "popdensity", "market_access"]
        features, manifest = cf.build_scope_features(grid, seasons, df[KEYS], anchor, neighbors, valid, df[context_cols])
        clash = set(features.columns) & set(df.columns)
        if clash:
            raise ValueError(f"{fs}: new features collide with existing columns: {sorted(clash)[:5]}")
        kept = df.drop(columns=old)
        man = pd.DataFrame(manifest).assign(scope=fs)
        manifests.append(man)
        scope_cols = man.loc[man["block"].str.startswith(SCOPE_ANCHORED_BLOCKS), "feature_name"].tolist()
        info = {"source": {"path": str(src_path), "sha256": None if args.no_hash else sha256(src_path)}, "rows": len(df),
                "removed_old_climate": len(old), "kept_columns": kept.shape[1], "added": features.shape[1], "scope_anchored_added": len(scope_cols), "outputs": {}}
        variants = {"masked": None, "unmasked": None} if anchor is not None else {"masked": None}
        for variant in variants:
            feats = features
            if variant == "masked" and anchor is not None:
                mask = df[f"Rainf_f_tavg_mean__l{anchor}_s{anchor}"].isna().to_numpy()
                feats = features.copy()
                feats.loc[mask, scope_cols] = np.nan
                info["masked_rows"] = int(mask.sum())
                info["masked_rows_by_year"] = {int(y): int(n) for y, n in pd.Series(mask).groupby(df["year"].to_numpy()).sum().items()}
            out = pd.concat([kept, feats], axis=1)
            if not out[KEYS].equals(df[KEYS]):
                raise ValueError(f"{fs}: row keys changed")
            target = output_path(out_dir, stem, variant)
            out.to_csv(target, index=False)
            new_test = feats[df["year"].between(2022, 2025).to_numpy()]
            info["outputs"][variant] = {"path": str(target), "columns": out.shape[1],
                                        "new_feature_nan_share_test_years": float(new_test.isna().to_numpy().mean())}
            print(f"[{fs}/{variant}] rows {len(out)} cols {out.shape[1]} (removed {len(old)}, added {feats.shape[1]}) -> {target.name} ({time.time()-t0:.0f}s)", flush=True)
        summary["scopes"][fs] = info
    pd.concat(manifests).to_csv(out_dir / "climate2015_v1_feature_manifest.csv", index=False)
    summary["elapsed_seconds"] = round(time.time() - t0, 1)
    (out_dir / "climate2015_v1_build_summary.json").write_text(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
