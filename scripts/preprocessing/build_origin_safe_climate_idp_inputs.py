"""Build origin_safe_climate_idp_v1 model inputs for H = 0/3/6/12.

One dataset per horizon on the 52,521 reported-phase keys of the corrected interim panel:
retained inherited predictors (static context + dynamic families verified against interim source months),
unmasked 2015-2026 climate (14 monthly ensemble indicators, 2 completed growing seasons), safe IPC history
(latest three reported phases <= min(O, T-1)) and national DTM IDP stock/age (latest report <= O).
Legacy history columns and target-side ``estimated_population`` are removed. Ledgers, feature
classification, source-support perturbation checks and a manifest are written next to the data.
Design: ``.trellis/tasks/10-06-global-origin-safe-climate-idp/design.md``.
"""
from __future__ import annotations

import argparse
import json
import platform
import re
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = next(path for path in Path(__file__).resolve().parents if (path / "src").exists())
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import numpy as np
import pandas as pd

from ipcch import climate2015_features as cf
from ipcch import origin_safe as osf
from ipcch import paths
from ipcch import retained_feature_recipes as rr
from ipcch.forecasting_weight_decay import add_identifier_features

VERSION = "origin_safe_climate_idp_v1"
ASSEMBLED = paths.SOURCE_DATA_DIR / "assembled_IPCCH"
SHARED = Path("/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/IPCCH_shared_folder")
IDP_DTM = Path("/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/Processed_Dataset/IDP_DTM")
INPUTS = {
    "interim": ASSEMBLED / "interim" / "IPCCH_2026_target_corrected_nino34_wbfood.csv",
    "climate_monthly": SHARED / "climate_monthly_2015_2026_MODELING_READY.csv",
    "climate_seasonal": SHARED / "climate_2015_2026_MODELING_READY.csv",
    "idp_admin0_monthly": IDP_DTM / "output" / "idp_admin0_monthly.csv",
    "country_lookup": ASSEMBLED / "country_area_id_lookup.csv",
    "identifier_source": paths.external_path("ipcch_2026_completed_dataset"),
    "scope_fs0": paths.external_path("deep_features_scope_0m_model_ready_dataset"),
    "scope_fs1": paths.external_path("deep_features_scope_3m_model_ready_dataset"),
    "scope_fs2": paths.external_path("deep_features_scope_6m_model_ready_dataset"),
    "scope_fs3": paths.external_path("deep_features_forecasting_dataset"),
}
HORIZON_SCOPE = {0: "scope_fs0", 3: "scope_fs1", 6: "scope_fs2", 12: "scope_fs3"}
OUT_DIR = ASSEMBLED / "model_ready" / VERSION
CHECK_DIR = paths.RESULTS_DIR / "experiments" / VERSION / "input_checks"
KEYS = list(osf.KEYS)
LABEL_COLUMNS = ["overall_phase", *osf.SHARE_COLUMNS]
EXPECTED_LABEL_KEYS = 52521
EXPECTED_EVAL = {2022: 5599, 2023: 6064, 2024: 5127, 2025: 11415}
LEGACY_HISTORY = re.compile(r"^overall_phase_(lag|prev_observed)")
TARGET_SIDE = ("estimated_population",)
SUPPORT_CUTOFFS = ("2022-06", "2024-03")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--horizons", type=int, nargs="+", default=list(osf.HORIZONS), choices=osf.HORIZONS)
    parser.add_argument("--out-dir", default=str(OUT_DIR))
    parser.add_argument("--check-dir", default=str(CHECK_DIR))
    parser.add_argument("--support-cutoffs", nargs="*", default=list(SUPPORT_CUTOFFS), help="YYYY-MM cutoffs for source-support perturbation checks")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def ord_of(text: str) -> int:
    year, month = (int(x) for x in text.split("-"))
    return year * 12 + month - 1


def log(t0: float, message: str) -> None:
    print(f"[{time.time() - t0:6.0f}s] {message}", flush=True)


def load_interim(path: Path) -> pd.DataFrame:
    header = pd.read_csv(path, nrows=0).columns
    bbg = [c for c in header if c.startswith("bbg_")]
    usecols = ["admin_code", "year", "month", "lat", "lon", *LABEL_COLUMNS, *rr.COMPOUND_MODIFIERS,
               *rr.ORDINARY_SOURCES, rr.ENSO, *bbg]
    return pd.read_csv(path, usecols=usecols).rename(columns={"admin_code": "area_id"})


def classify_and_verify(df: pd.DataFrame, horizon: int, recipes: rr.RetainedRecipes):
    """Classify every scope-file column; return retained feature names and a classification table."""
    keys = df[KEYS]
    scope_anchor = None if horizon == 12 else horizon
    expected, anchors = recipes.expected(keys, scope_anchor, df)
    dynamic = [c for c in df.columns if "__" in c and not cf.is_old_climate_column(c)]
    comparison = rr.compare_columns(df[dynamic], expected).set_index("feature")
    rows, retained = [], []
    for column in df.columns:
        record = {"feature": column}
        if column in KEYS or column in LABEL_COLUMNS:
            record.update(role="key_or_label", decision="not_a_feature")
        elif cf.is_old_climate_column(column):
            record.update(role="old_climate", decision="removed_replaced_by_climate2015")
        elif LEGACY_HISTORY.match(column):
            record.update(role="legacy_ipc_history", decision="removed_replaced_by_safe_history")
        elif column in TARGET_SIDE:
            record.update(role="target_side", decision="removed_target_side")
        elif rr.is_static_name(column):
            per_area = df.groupby("area_id")[column].nunique(dropna=True)
            invariant = bool((per_area <= 1).all())
            record.update(role="static_context", decision="retained" if invariant else "STOP_not_invariant",
                          anchor="static_snapshot", missing=int(df[column].isna().sum()))
            if not invariant:
                raise ValueError(f"h{horizon}: static column {column} varies within area")
            retained.append(column)
        elif column in comparison.index:
            status = comparison.loc[column, "status"]
            record.update(role="dynamic_inherited", anchor=anchors.get(column), **comparison.loc[column].to_dict())
            if status not in ("verified", "verified_saved_missing_retained"):
                raise ValueError(f"h{horizon}: retained column {column} disagrees with its recipe ({status}); stopping")
            if anchors[column] < horizon:
                raise ValueError(f"h{horizon}: {column} anchor t-{anchors[column]} is after the origin")
            record["decision"] = "retained"
            retained.append(column)
        else:
            raise ValueError(f"h{horizon}: column {column} has no timing classification; stopping")
        rows.append(record)
    return retained, pd.DataFrame(rows)


def support_check_retained(panel: pd.DataFrame, static: pd.DataFrame, keys: pd.DataFrame, horizon: int, df: pd.DataFrame,
                           baseline: dict, cutoff: int, rng) -> pd.DataFrame:
    """Perturb every source month after ``cutoff``; values of rows with origin <= cutoff must not change."""
    perturbed = panel.copy()
    late = osf.month_ord(perturbed["year"], perturbed["month"]) > cutoff
    for column in [*rr.ORDINARY_SOURCES, rr.ENSO, *[c for c in perturbed.columns if c.startswith("bbg_")]]:
        values = pd.to_numeric(perturbed[column], errors="coerce").to_numpy(dtype=float).copy()
        values[late] = values[late] + rng.normal(100.0, 10.0, int(late.sum()))
        perturbed[column] = values
    recipes = rr.RetainedRecipes(perturbed, static)
    expected, _ = recipes.expected(keys, None if horizon == 12 else horizon, df)
    origin = osf.month_ord(keys["year"], keys["month"]) - horizon
    early, later = origin <= cutoff, origin > cutoff
    rows = []
    for name, base in baseline.items():
        new = expected[name]
        same = (base == new) | (np.isnan(base) & np.isnan(new))
        rows.append({"feature": name, "cutoff": osf.ord_label(cutoff), "rows_origin_le_cutoff": int(early.sum()),
                     "changed_rows_origin_le_cutoff": int((~same & early).sum()),
                     "changed_rows_origin_gt_cutoff": int((~same & later).sum())})
    return pd.DataFrame(rows)


def support_check_climate(grid, seasons, keys, scope_anchor, neighbors, valid, context, baseline: pd.DataFrame,
                          horizon: int, cutoff: int, rng) -> pd.DataFrame:
    """Perturb monthly values after ``cutoff`` and seasonal values of seasons ending after the origin month."""
    values = {}
    for v, arr in grid.values.items():
        arr = arr.copy()
        late_col = np.arange(grid.n_months) + grid.first_ord > cutoff
        arr[:, late_col] = arr[:, late_col] + rng.normal(100.0, 10.0, arr[:, late_col].shape)
        values[v] = arr
    pgrid = cf.Grid(grid.area_ids, grid.first_ord, grid.n_months, values)
    pseasons = seasons.copy()
    end = pd.to_datetime(pseasons["gs_end_date_exclusive"])
    first_day_after = pd.Timestamp(year=(cutoff + 1) // 12, month=(cutoff + 1) % 12 + 1, day=1)
    late_season = (end > first_day_after).to_numpy()
    for v in cf.SEASONAL_VARIABLES:
        pseasons.loc[late_season, v] = pseasons.loc[late_season, v] + 100.0
    feats, _ = cf.build_scope_features(pgrid, pseasons, keys, scope_anchor, neighbors, valid, context)
    origin = osf.month_ord(keys["year"], keys["month"]) - horizon
    early, later = origin <= cutoff, origin > cutoff
    rows = []
    for name in baseline.columns:
        base, new = baseline[name].to_numpy(dtype=float), feats[name].to_numpy(dtype=float)
        same = (base == new) | (np.isnan(base) & np.isnan(new))
        rows.append({"feature": name, "cutoff": osf.ord_label(cutoff), "rows_origin_le_cutoff": int(early.sum()),
                     "changed_rows_origin_le_cutoff": int((~same & early).sum()),
                     "changed_rows_origin_gt_cutoff": int((~same & later).sum())})
    return pd.DataFrame(rows)


def main() -> int:
    args = parse_args()
    t0 = time.time()
    out_dir, check_dir = Path(args.out_dir), Path(args.check_dir)
    manifest_path = out_dir / f"{VERSION}_manifest.json"
    if manifest_path.exists() and not args.overwrite:
        raise SystemExit(f"{manifest_path} exists (use --overwrite)")
    out_dir.mkdir(parents=True, exist_ok=True)
    check_dir.mkdir(parents=True, exist_ok=True)
    for name, path in INPUTS.items():
        if not Path(path).exists():
            raise FileNotFoundError(f"{name}: {path}")
    manifest = {
        "version": VERSION, "status": "BUILDING",
        "created_utc": pd.Timestamp.now(tz="UTC").isoformat(),
        "git_head": subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=PROJECT_ROOT).stdout.strip(),
        "git_status_porcelain": subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, cwd=PROJECT_ROOT).stdout,
        "runtime": {"python": sys.version, "platform": platform.platform(), "numpy": np.__version__, "pandas": pd.__version__},
        "code_sha256": {str(p.relative_to(PROJECT_ROOT)): osf.file_sha256(p) for p in (
            Path(__file__), PROJECT_ROOT / "src/ipcch/origin_safe.py", PROJECT_ROOT / "src/ipcch/retained_feature_recipes.py",
            PROJECT_ROOT / "src/ipcch/climate2015_features.py")},
        "inputs": {}, "timing_contract": {
            "availability_proxy": "observation/reporting month; no publication-vintage certification",
            "origin": "month-end O = T - H",
            "ipc_history_and_fit_labels": "month <= min(O, T-1)",
            "monthly_dynamic_and_idp": "month <= O",
            "growing_season": "gs_end_date_exclusive <= first day of month O+1",
        },
        "limits": [
            "Supplied climate climatology/standardization fitted samples are not documented; no full-chain or real-time validity claim.",
            "Static geospatial/context snapshots and revised observations are fixed retrospective context, not historical vintages.",
            "National DTM IDP stock is an IDP-only country-level context; old reports are stale; no subnational allocation or refugee coverage.",
            "Inherited non-climate predictors keep their saved values and missingness (including carrier-row tail NaN).",
        ],
        "horizons": {},
    }
    for name, path in INPUTS.items():
        manifest["inputs"][name] = {"path": str(path), "sha256": osf.file_sha256(path)}
    log(t0, "input hashes done")

    # ---------------------------------------------------------------- labels, cohort, history source
    panel = load_interim(INPUTS["interim"])
    if panel.duplicated(KEYS).any():
        raise ValueError("interim panel has duplicate keys")
    labels = panel.loc[pd.to_numeric(panel["overall_phase"], errors="coerce").isin(osf.VALID_PHASES), KEYS + LABEL_COLUMNS]
    labels = labels.sort_values(KEYS, kind="mergesort").reset_index(drop=True)
    if len(labels) != EXPECTED_LABEL_KEYS:
        raise ValueError(f"expected {EXPECTED_LABEL_KEYS} reported-phase keys, found {len(labels)}")
    observations = osf.valid_phase_observations(labels)
    targets = osf.normalized_cumulative_targets(labels)
    eval_mask = targets["share_valid"].to_numpy() & labels["year"].isin(osf.TARGET_YEARS).to_numpy()
    eval_by_year = labels.loc[eval_mask, "year"].value_counts().sort_index().to_dict()
    if {int(k): int(v) for k, v in eval_by_year.items()} != EXPECTED_EVAL:
        raise ValueError(f"evaluation cohort {eval_by_year} differs from the projected {EXPECTED_EVAL}")
    cohort = labels[KEYS].copy()
    cohort["share_valid"] = targets["share_valid"].to_numpy()
    cohort["share_total_raw"] = targets["share_total_raw"].to_numpy()
    cohort["eval_key"] = eval_mask
    cohort_path = out_dir / f"{VERSION}_cohort_keys.csv"
    cohort.to_csv(cohort_path, index=False)
    manifest["cohort"] = {
        "path": str(cohort_path), "sha256": osf.file_sha256(cohort_path), "label_keys": len(labels),
        "label_keys_sha256": osf.keys_sha256(labels), "share_valid": int(cohort["share_valid"].sum()),
        "eval_keys": int(eval_mask.sum()), "eval_by_year": {int(k): int(v) for k, v in eval_by_year.items()},
        "eval_keys_sha256": osf.keys_sha256(cohort.loc[eval_mask]),
        "share_sum_not_close_to_one_eval": int((~np.isclose(cohort.loc[eval_mask, "share_total_raw"], 1.0)).sum()),
        "phase1_eval": int((labels.loc[eval_mask, "overall_phase"] == 1).sum()),
    }
    log(t0, f"labels {len(labels)}, eval {int(eval_mask.sum())} {eval_by_year}")

    # ---------------------------------------------------------------- IDP and lookup
    lookup = pd.read_csv(INPUTS["country_lookup"])
    if lookup["area_id"].duplicated().any():
        raise ValueError("country lookup has duplicate area_id")
    iso_by_area = lookup.set_index("area_id")["iso3"]
    missing_area = sorted(set(labels["area_id"]) - set(iso_by_area.index))
    if missing_area:
        raise ValueError(f"{len(missing_area)} label areas absent from the country lookup")
    row_iso = iso_by_area.reindex(labels["area_id"]).to_numpy(dtype=object)
    row_iso = np.where(pd.isna(row_iso), None, row_iso)
    idp_obs = osf.idp_observations(pd.read_csv(INPUTS["idp_admin0_monthly"]))
    lookup_iso = set(iso_by_area.dropna())
    manifest["idp"] = {
        "countries_with_reports": sorted(set(idp_obs["iso3"])),
        "label_countries_with_reports": sorted(lookup_iso & set(idp_obs["iso3"])),
        "label_countries_without_reports": sorted(lookup_iso - set(idp_obs["iso3"])),
        "areas_without_iso3": {"count": int(lookup["iso3"].isna().sum()),
                               "countries": sorted(lookup.loc[lookup["iso3"].isna(), "country"].astype(str).unique()),
                               "label_rows": int(pd.isna(iso_by_area.reindex(labels["area_id"])).sum()),
                               "note": "ISO3 not inferred; DTM admin0 table has no report for these countries either"},
        "report_rows": len(idp_obs),
        "rule": "latest observed non-null national stock with report month <= O; age = O - report month; missing stays NaN",
    }

    # ---------------------------------------------------------------- climate inputs
    monthly = pd.read_csv(INPUTS["climate_monthly"], usecols=["admin_code", "year", "month", *cf.MONTHLY_VARIABLES]).rename(columns={"admin_code": "area_id"})
    grid = cf.Grid.from_long(monthly, cf.MONTHLY_VARIABLES)
    del monthly
    seasons = pd.read_csv(INPUTS["climate_seasonal"], usecols=["admin_code", "season_year", "season", "gs_start_date", "gs_end_date_exclusive", *cf.SEASONAL_VARIABLES])
    coords = panel.groupby("area_id")[["lat", "lon"]].mean()
    gcoords = coords.reindex(grid.area_ids)
    cvalid = gcoords["lat"].between(-90, 90).to_numpy() & gcoords["lon"].between(-180, 180).to_numpy()
    cneighbors = cf.build_neighbors(gcoords["lat"].to_numpy(), gcoords["lon"].to_numpy(), cvalid)
    manifest["climate_grid"] = {"first_month": osf.ord_label(grid.first_ord), "last_month": osf.ord_label(grid.first_ord + grid.n_months - 1),
                                "n_areas": len(grid.area_ids), "valid_coords": int(cvalid.sum()), "seasons": len(seasons)}
    log(t0, "climate loaded")

    # ---------------------------------------------------------------- retained recipes
    static = panel.groupby("area_id").agg(lat=("lat", "mean"), lon=("lon", "mean"),
                                          popdensity=("popdensity", "first"), market_access=("market_access", "first"))
    span = pd.DataFrame({"a": panel["area_id"], "o": osf.month_ord(panel["year"], panel["month"])}).groupby("a")["o"].agg(["min", "max", "count"])
    if ((span["max"] - span["min"] + 1) != span["count"]).any():
        raise ValueError("interim panel has internal month gaps; upstream row shifts would not be month shifts")
    manifest["interim_grid"] = {"areas": len(span), "contiguous_all_areas": True,
                                "first_month": osf.ord_label(span["min"].min()), "last_month": osf.ord_label(span["max"].max()),
                                "areas_ending_before_last_month": int((span["max"] < span["max"].max()).sum())}
    recipes = rr.RetainedRecipes(panel, static)
    manifest["commodity_members"] = recipes.members
    log(t0, "retained recipes computed")

    identifier = pd.read_csv(INPUTS["identifier_source"], usecols=["admin_code", "year", "month", "lat", "lon"])
    rng = np.random.default_rng(20261006)
    cutoffs = [ord_of(c) for c in args.support_cutoffs]

    for horizon in args.horizons:
        scope_key = HORIZON_SCOPE[horizon]
        df = pd.read_csv(INPUTS[scope_key], low_memory=False)
        df = df[pd.to_numeric(df["overall_phase"], errors="coerce").isin(osf.VALID_PHASES)]
        if df.duplicated(KEYS).any():
            raise ValueError(f"h{horizon}: duplicate keys")
        df = df.sort_values(KEYS, kind="mergesort").reset_index(drop=True)
        if not df[KEYS].equals(labels[KEYS]):
            raise ValueError(f"h{horizon}: scope-file reported-phase keys differ from the interim label keys")
        for column in LABEL_COLUMNS:
            a = pd.to_numeric(df[column], errors="coerce").to_numpy(dtype=float)
            b = pd.to_numeric(labels[column], errors="coerce").to_numpy(dtype=float)
            if not np.array_equal(a, b, equal_nan=True):
                raise ValueError(f"h{horizon}: label column {column} disagrees with the interim projection")
        keys = df[KEYS]
        retained, classification = classify_and_verify(df, horizon, recipes)
        classification.to_csv(check_dir / f"feature_classification_h{horizon}.csv", index=False)
        log(t0, f"h{horizon}: {len(retained)} retained columns verified")

        scope_anchor = None if horizon == 12 else horizon
        context = df[[cf.ENSO_SHARE, "popdensity", "market_access"]]
        climate, climate_manifest = cf.build_scope_features(grid, seasons, keys, scope_anchor, cneighbors, cvalid, context)
        clash = set(climate.columns) & set(df.columns)
        if clash:
            raise ValueError(f"h{horizon}: climate names collide with scope columns {sorted(clash)[:5]}")
        pd.DataFrame(climate_manifest).to_csv(check_dir / f"climate_manifest_h{horizon}.csv", index=False)
        log(t0, f"h{horizon}: climate block {climate.shape[1]} columns (unmasked)")

        history, history_ledger = osf.build_safe_history(observations, keys, horizon)
        history_stats = osf.reference_history_check(observations, history_ledger, history)
        idp, idp_ledger = osf.build_idp_features(idp_obs, keys, row_iso, horizon)
        idp_stats = osf.reference_idp_check(idp_obs, idp_ledger, idp)
        ident = add_identifier_features(keys.copy(), identifier)
        ident_cols = [c for c in ident.columns if c not in KEYS]
        log(t0, f"h{horizon}: history {history_stats}, idp {idp_stats}")

        support_rows = []
        retained_dynamic = [c for c in retained if not rr.is_static_name(c)]
        expected_now, _ = recipes.expected(keys, scope_anchor, df)
        base_retained = {c: expected_now[c] for c in retained_dynamic}
        for cutoff in cutoffs:
            support_rows.append(support_check_retained(panel, static, keys, horizon, df, base_retained, cutoff, rng).assign(block="retained"))
            support_rows.append(support_check_climate(grid, seasons, keys, scope_anchor, cneighbors, cvalid, context, climate,
                                                      horizon, cutoff, rng).assign(block="climate2015"))
        support = pd.concat(support_rows, ignore_index=True)
        support.to_csv(check_dir / f"source_support_h{horizon}.csv", index=False)
        if (support["changed_rows_origin_le_cutoff"] > 0).any():
            bad = support[support["changed_rows_origin_le_cutoff"] > 0]
            raise ValueError(f"h{horizon}: post-origin perturbation changed {len(bad)} feature/cutoff cells:\n{bad.head(20)}")
        log(t0, f"h{horizon}: source-support perturbation passed ({len(support)} feature/cutoff cells)")

        data = pd.concat([df[KEYS + LABEL_COLUMNS], df[retained], climate.reset_index(drop=True),
                          ident[ident_cols].reset_index(drop=True), history, idp], axis=1)
        if data.columns.duplicated().any():
            raise ValueError(f"h{horizon}: duplicate output columns")
        base_features = retained + list(climate.columns) + ident_cols
        arms = {arm: base_features + list(extra) for arm, extra in osf.ARMS.items()}
        for arm, features in arms.items():
            bad = osf.forbidden_features(features)
            if bad:
                raise ValueError(f"h{horizon} {arm}: forbidden features {bad}")
            non_numeric = [c for c in features if not pd.api.types.is_numeric_dtype(data[c]) and not pd.api.types.is_bool_dtype(data[c])]
            if non_numeric:
                raise ValueError(f"h{horizon} {arm}: non-numeric features {non_numeric[:5]}")
        data_path = out_dir / f"{VERSION}_h{horizon}.csv"
        hist_path = out_dir / f"{VERSION}_history_ledger_h{horizon}.csv"
        idp_path = out_dir / f"{VERSION}_idp_ledger_h{horizon}.csv"
        data.to_csv(data_path, index=False)
        history_ledger.to_csv(hist_path, index=False)
        idp_ledger.to_csv(idp_path, index=False)
        check = pd.read_csv(data_path, float_precision="round_trip", nrows=2000)
        for column in base_features[:50] + list(osf.HISTORY_FEATURES) + list(osf.IDP_FEATURES):
            a, b = check[column].to_numpy(dtype=float), data[column].iloc[:2000].to_numpy(dtype=float)
            if not np.array_equal(a, b, equal_nan=True):
                raise ValueError(f"h{horizon}: CSV round trip changed {column}")
        eval_rows = cohort["eval_key"].to_numpy()
        manifest["horizons"][str(horizon)] = {
            "scope_source": scope_key,
            "dataset": {"path": str(data_path), "sha256": osf.file_sha256(data_path), "rows": len(data), "columns": data.shape[1]},
            "history_ledger": {"path": str(hist_path), "sha256": osf.file_sha256(hist_path)},
            "idp_ledger": {"path": str(idp_path), "sha256": osf.file_sha256(idp_path)},
            "arms": {arm: {"feature_count": len(f), "feature_sha256": osf.list_sha256(f), "features": f} for arm, f in arms.items()},
            "counts": {
                "retained_static": int(sum(rr.is_static_name(c) for c in retained)),
                "retained_dynamic": len(retained_dynamic),
                "removed": classification.loc[classification["decision"].astype(str).str.startswith("removed"), "feature"].tolist(),
                "climate2015": climate.shape[1], "identifier": len(ident_cols),
            },
            "history_reference_check": history_stats,
            "idp_reference_check": idp_stats,
            "history_count_distribution_eval": history.loc[eval_rows, list(osf.HISTORY_VALUES)].notna().sum(axis=1).value_counts().sort_index().to_dict(),
            "history_source_age_months_eval": {
                f"history_{k + 1}": history_ledger.loc[eval_rows, "target_ord"].sub(history_ledger.loc[eval_rows, f"history_{k + 1}_source_ord"]).describe().to_dict()
                for k in range(3)},
            "idp_present_eval": int(idp.loc[eval_rows, osf.IDP_FEATURES[0]].notna().sum()),
            "idp_age_months_eval": idp.loc[eval_rows, osf.IDP_FEATURES[1]].describe().to_dict(),
            "climate_new_nan_share_eval": float(climate.loc[eval_rows].isna().to_numpy().mean()),
            "support_cutoffs": args.support_cutoffs,
            "support_power_changed_cells_origin_gt_cutoff": int(support["changed_rows_origin_gt_cutoff"].sum()),
        }
        log(t0, f"h{horizon}: wrote {data_path.name} ({data.shape[1]} columns)")
        del df, data, climate, history, idp

    manifest["status"] = "COMPLETE"
    manifest["elapsed_seconds"] = round(time.time() - t0, 1)
    osf.dump_json(manifest_path, manifest)
    osf.dump_json(check_dir / f"{VERSION}_manifest_copy.json", manifest)
    log(t0, f"manifest {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
