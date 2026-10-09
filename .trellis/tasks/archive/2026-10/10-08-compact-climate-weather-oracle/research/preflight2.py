"""Remaining row-level preflight checks for compact_climate_weather_oracle_v1 (read-only)."""
import csv, json, sys, time
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / "src"))
from ipcch import origin_safe as osf, climate2015_features as cf, retained_feature_recipes as rr
from ipcch.forecasting_weight_decay import add_identifier_features
T = ROOT / ".trellis/tasks/10-08-compact-climate-weather-oracle"
t0 = time.time()
out = {"checks": {}, "problems": []}
P = out["problems"]
def log(m): print(f"[{time.time()-t0:5.0f}s] {m}", flush=True)
meta = json.load(open(T / "expected_feature_contract_metadata.json", encoding="utf-8-sig"))
fbr = meta["features_by_run"]
rows = list(csv.DictReader(open(T / "expected_feature_contract.csv", encoding="utf-8-sig")))
# CSV expected_model_positions vs features_by_run
for run, feats in fbr.items():
    pos = {}
    for r in rows:
        p = json.loads(r["expected_model_positions"])
        if run in p: pos[p[run]] = r["predictor"]
        flag = r[run.replace("/", "_")] == "true"
        if flag != (run in p): P.append(f"{r['predictor']}: membership flag/position mismatch for {run}")
    proj = [pos[i] for i in range(1, len(pos) + 1)]
    if proj != feats: P.append(f"{run}: CSV positions projection differs from features_by_run")
out["checks"]["csv_positions_equal_features_by_run"] = True
base = fbr["compact_baseline/0m"]
pm = json.load(open(ROOT.parent.parent.parent / "1.Source Data/assembled_IPCCH/model_ready/origin_safe_climate_idp_v1/origin_safe_climate_idp_v1_manifest.json"))
# background from parent run metadata
bg_groups = {}
for h in (0, 3, 6, 12):
    rm = ROOT / f"results/experiments/origin_safe_climate_idp_v1/runs/climate_safe_history_idp/{h}m/run_metadata.json"
    if osf.file_sha256(rm) != meta["background_parent_metadata_sha256"][str(h)]: P.append(f"parent run_metadata h{h} sha differs")
    feats = json.load(open(rm))["features"]
    static = [f for f in feats if rr.is_static_name(f)]
    ident = [f for f in feats if f in ("lat", "lon") or f.startswith("month_") or f.startswith("year_")]
    hist = [f for f in feats if f in osf.HISTORY_FEATURES]
    idp = [f for f in feats if f in osf.IDP_FEATURES]
    bg_groups[h] = (static, ident, hist, idp)
    if pm["horizons"][str(h)]["arms"]["climate_safe_history_idp"]["features"] != feats: P.append(f"h{h}: run_metadata features != parent manifest arm features")
if len({json.dumps(v) for v in bg_groups.values()}) != 1: P.append("background order differs across parent horizons")
static, ident, hist, idp = bg_groups[0]
if base[:29] != static or base[262:289] != ident or base[289:294] != hist or base[294:296] != idp: P.append("contract background order != parent")
out["checks"]["background_counts"] = [len(static), len(ident), len(hist), len(idp)]
# parent datasets
cohort = pd.read_csv(pm["cohort"]["path"])
if osf.keys_sha256(cohort) != pm["cohort"]["label_keys_sha256"]: P.append("cohort label key hash")
ev = cohort["eval_key"].to_numpy(bool)
if osf.keys_sha256(cohort.loc[ev]) != "f0193c1402d0609556755844b476227b7188f9671323d21317336d7ef58d2e0f": P.append("eval key hash")
out["checks"]["eval_by_year"] = cohort.loc[ev, "year"].value_counts().sort_index().to_dict()
idf = pd.read_csv(pm["inputs"]["identifier_source"]["path"], usecols=["admin_code", "year", "month", "lat", "lon"])
ref_labels = ref_bg = None
for h in (0, 3, 6, 12):
    e = pm["horizons"][str(h)]
    d = pd.read_csv(e["dataset"]["path"], float_precision="round_trip", low_memory=False)
    hl = pd.read_csv(e["history_ledger"]["path"], float_precision="round_trip")
    il = pd.read_csv(e["idp_ledger"]["path"], float_precision="round_trip")
    osf.assert_history_ledger(d, hl, h); osf.assert_idp_ledger(d, il, h)
    if not d[list(osf.KEYS)].equals(cohort[list(osf.KEYS)]): P.append(f"h{h}: keys != cohort")
    lab = d[list(osf.KEYS) + ["overall_phase", *osf.SHARE_COLUMNS]]
    if ref_labels is None: ref_labels = lab
    elif not lab.equals(ref_labels): P.append(f"h{h}: labels differ from h0")
    tg = osf.normalized_cumulative_targets(d)
    if not np.array_equal(tg["share_valid"].to_numpy(), cohort["share_valid"].to_numpy(bool)): P.append(f"h{h}: share_valid")
    sb = d[static + ident]
    if ref_bg is None: ref_bg = sb
    else:
        # numeric equivalence with identical NA masks; saved per-horizon values and dtypes are kept as they are
        va, vb = sb.to_numpy(dtype=float), ref_bg.to_numpy(dtype=float)
        same_mask = np.array_equal(np.isnan(va), np.isnan(vb))
        same_vals = np.array_equal(va, vb, equal_nan=True)
        dtype_only = [c for c in sb.columns if sb[c].dtype != ref_bg[c].dtype]
        out["checks"][f"h{h}_static_identifier_vs_h0"] = {"numeric_equal": bool(same_vals), "na_mask_equal": bool(same_mask),
            "pandas_equals": bool(sb.equals(ref_bg)), "dtype_only_columns": {c: [str(ref_bg[c].dtype), str(sb[c].dtype)] for c in dtype_only}}
        if not (same_vals and same_mask): P.append(f"h{h}: static/identifier numeric values or NA masks differ from h0")
    inv = (d.groupby("area_id")[static].nunique(dropna=True) <= 1).all().all()
    if not inv: P.append(f"h{h}: static not area-invariant")
    ide = add_identifier_features(d[list(osf.KEYS)].copy(), idf)
    for c in ident:
        if not np.array_equal(ide[c].to_numpy(float), d[c].to_numpy(float), equal_nan=True): P.append(f"h{h}: identifier {c} not reproduced")
    # calendar dummies are a deterministic function of target year/month
    for mth in range(1, 13):
        if not np.array_equal(d[f"month_{mth}"].to_numpy(float), (d["month"] == mth).to_numpy(float)): P.append(f"h{h}: month_{mth}")
    for y in range(2014, 2027):
        if not np.array_equal(d[f"year_{y}"].to_numpy(float), (d["year"] == y).to_numpy(float)): P.append(f"h{h}: year_{y}")
    out["checks"][f"h{h}_bg_missing_cells"] = int(d[static + ident + hist + idp].isna().sum().sum())
    log(f"h{h} parent ok ({len(P)} problems)")
    del d
# region map coverage
reg = pd.read_csv(ROOT / "data/reference/area_id_country_region_mapping.csv")
if reg["area_id"].duplicated().any(): P.append("region map duplicate area_id")
miss = set(cohort["area_id"]) - set(reg["area_id"])
if miss: P.append(f"{len(miss)} cohort areas lack a region")
evr = cohort.loc[ev].merge(reg, on="area_id", how="left")
out["checks"]["eval_rows_by_region"] = evr["region"].value_counts().sort_index().to_dict()
out["checks"]["eval_rows_by_region_year"] = {f"{r}": evr[evr.region == r]["year"].value_counts().sort_index().to_dict() for r in sorted(evr.region.unique())}
out["checks"]["region_values"] = sorted(reg["region"].unique().tolist())
# commodity members and source coverage
inter = pm["inputs"]["interim"]["path"]
hdr = pd.read_csv(inter, nrows=0).columns
mem = rr.commodity_members(hdr)
if mem != pm["commodity_members"]: P.append("commodity_members differs from pinned")
srcs = ["GPP_mean", "nightlight_mean", "event_count_violence", "sum_fatalities_violence", "WFP_Price", "food_price_index_WB", "nino34_anom"]
panel = pd.read_csv(inter, usecols=["admin_code", "year", "month", *srcs, *[c for v in mem.values() for c in v]])
ords = osf.month_ord(panel.year, panel.month)
cov = {}
for c in srcs + [c for v in mem.values() for c in v]:
    x = pd.to_numeric(panel[c], errors="coerce")
    nn = x.notna()
    cov[c] = {"nonmissing": int(nn.sum()), "rows": len(x), "first": osf.ord_label(ords[nn].min()) if nn.any() else None, "last": osf.ord_label(ords[nn].max()) if nn.any() else None, "inf": int(np.isinf(x).sum())}
clim = pd.read_csv(pm["inputs"]["climate_monthly"]["path"], usecols=["admin_code", "year", "month", *cf.MONTHLY_VARIABLES])
co = osf.month_ord(clim.year, clim.month)
for c in cf.MONTHLY_VARIABLES:
    x = clim[c]; nn = x.notna()
    cov[c] = {"nonmissing": int(nn.sum()), "rows": len(x), "first": osf.ord_label(co[nn].min()), "last": osf.ord_label(co[nn].max()), "inf": int(np.isinf(x).sum())}
out["checks"]["source_coverage"] = cov
seas = pd.read_csv(pm["inputs"]["climate_seasonal"]["path"], usecols=["admin_code", "season_year", "season", "gs_start_date", "gs_end_date_exclusive"])
seas["dur"] = (pd.to_datetime(seas.gs_end_date_exclusive) - pd.to_datetime(seas.gs_start_date)).dt.days
pv = seas.pivot_table(index=["admin_code", "season_year"], columns="season", values="dur", aggfunc="count")
if not ((pv["s1"] == 1) & (pv["s2"] == 1)).all(): P.append("seasonal pairs not unique s1/s2")
dd = seas.pivot_table(index=["admin_code", "season_year"], columns="season", values="dur")
out["checks"]["season_pairs"] = {"pairs": len(dd), "s1_longer": int((dd.s1 > dd.s2).sum()), "s2_longer": int((dd.s2 > dd.s1).sum()), "tie": int((dd.s1 == dd.s2).sum()), "nonpositive": int((seas.dur <= 0).sum())}
out["passed"] = not P
out["elapsed_s"] = round(time.time() - t0, 1)
json.dump(out, open(T / "research/execution-preflight-rowlevel.json", "w"), indent=2, default=str)
print(json.dumps({k: v for k, v in out.items() if k != "checks"}, indent=1, default=str))
print(json.dumps({k: out["checks"][k] for k in ("background_counts", "eval_by_year", "eval_rows_by_region", "season_pairs")}, default=str))
