#!/usr/bin/env python3
"""Independent replay of a Somalia v4 calibrated-D run from its saved artifacts and pinned sources.

Rebuilds the label ledger (originals and validity copies) from the raw panel and the
validity snapshot, realized-weather verification from the raw panel, every cohort, every
OOF pool and its history exposure, temporal/report isolation of every scoring,
calibration, final-calibration and final-fit dependency, the full 144-recipe selection,
final calibration mappings, saved-model predictions (with context-specific history
rows) and every reported annual/pooled metric field, without the runner's code paths
(pandas merges, plain loops and scikit-learn metrics/isotonic). Writes only <out-dir>/replay/.

    PYTHONPATH=src python scripts/postprocessing/replay_somalia_v4.py --out-dir results/experiments/somalia_oracle/v4_calibrated_d
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import f1_score, mean_absolute_error, mean_squared_error, precision_score, r2_score, recall_score, roc_auc_score

RT = {"float_precision": "round_trip"}
METHODS = ("none", "shift", "isotonic")
FORMS = ("direct", "residual")
HL_ORDER = {"none": 0, "48": 1, "24": 2, "12": 3}
LABELS = ["overall_phase", "phase1_percent", "phase2_percent", "phase3_percent", "phase4_percent", "phase5_percent"]
WEATHER = ["Rainf_f_tavg_mean", "Tair_f_tavg_mean"]


class Replay:
    def __init__(self, out: Path):
        self.out = out
        self.rows = []

    def check(self, name, ok, detail=""):
        self.rows.append({"check": name, "ok": bool(ok), "detail": str(detail)[:500]})
        return bool(ok)

    def read(self, rel, **kw):
        return pd.read_csv(self.out / rel, **RT, **kw)


def mo(y, m):
    return int(y) * 12 + int(m) - 1


def lab(o):
    return f"{int(o) // 12:04d}-{int(o) % 12 + 1:02d}"


def sha(path):
    d = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 22), b""):
            d.update(b)
    return d.hexdigest()


def keys_hash(frame):
    k = frame[["area_id", "target_ord"]].to_numpy().astype(np.int64)
    return hashlib.sha256(np.ascontiguousarray(k).tobytes()).hexdigest()[:16]


def sorted_digest(frame):
    k = frame[["area_id", "target_ord"]].astype(np.int64).sort_values(["area_id", "target_ord"], kind="mergesort").to_numpy()
    return hashlib.sha256(np.ascontiguousarray(k).tobytes()).hexdigest()


def fit_map(method, raw, truth, rounds, min_rounds):
    if method == "none":
        return ("ok", lambda x: np.asarray(x, float), None)
    if np.unique(rounds).size < min_rounds:
        return ("unsupported", None, None)
    if method == "shift":
        s = float(np.mean(raw - truth))
        return ("ok", lambda x, s=s: np.asarray(x, float) - s, s)
    if np.unique(raw).size < 2:
        return ("unsupported", None, None)
    iso = IsotonicRegression(y_min=0.0, y_max=1.0, increasing=True, out_of_bounds="clip").fit(raw, truth)
    return ("ok", iso.predict, iso)


def hx_set(x):
    return frozenset(v for v in str(x).split(";") if v) if isinstance(x, str) else frozenset()


def rebuild_labels(cfg, man):
    """Originals, partial originals and validity copies from the raw panel and snapshot (independent of augment.py)."""
    lookup = pd.read_csv(man["inputs"]["lookup"]["path"])
    iso = [c for c in lookup.columns if c.lower() == "iso3"][0]
    som = set(pd.to_numeric(lookup.loc[lookup[iso] == "SOM", "area_id"], errors="coerce").dropna().astype(int))
    parts = []
    for ch in pd.read_csv(man["inputs"]["raw"]["path"], usecols=["admin_code", "year", "month", *LABELS, *WEATHER], chunksize=200_000, **RT):
        ch = ch.loc[pd.to_numeric(ch["admin_code"], errors="coerce").isin(som)]
        if len(ch):
            parts.append(ch)
    raw = pd.concat(parts, ignore_index=True)
    raw["area_id"] = raw["admin_code"].astype(int)
    raw["t"] = raw["year"].astype(int) * 12 + raw["month"].astype(int) - 1
    present = raw[LABELS].notna()
    raw["full"], raw["blank"] = present.all(axis=1), ~present.any(axis=1)
    vals = raw[LABELS[1:]].to_numpy(float)
    raw["qc"] = raw["full"] & raw["overall_phase"].isin([1, 2, 3, 4, 5]) & np.isfinite(vals).all(axis=1) & (vals >= 0).all(axis=1) & (np.nan_to_num(vals).sum(axis=1) > 0)
    feats = json.loads(Path(cfg["validity_snapshot"]).read_text())["features"]
    win = {}
    for ft in feats:
        p = ft["properties"]
        if all(str(p.get(k)) == v for k, v in cfg["api_filter"].items()):
            f, t = pd.to_datetime(p["from"], format="%b %Y"), pd.to_datetime(p["to"], format="%b %Y")
            win.setdefault(str(p["anl_id"]), set()).add((mo(f.year, f.month), mo(t.year, t.month)))
    starts = {}
    for a, ws in win.items():
        (f, t), = ws
        starts.setdefault(f, []).append((a, t))
    excluded = {mo(*map(int, k.split("-"))) for k in cfg["excluded_raw_months"]}
    link = {}
    for m in sorted(set(raw.loc[raw["full"] & (raw["year"] >= cfg["augmentation_years"][0]), "t"])):
        if m not in excluded and len(starts.get(m, [])) == 1:
            link[m] = starts[m][0]
    lo, hi = mo(cfg["augmentation_years"][0], 1), mo(cfg["augmentation_years"][1], 12)
    blank = set(zip(raw.loc[raw["blank"], "area_id"], raw.loc[raw["blank"], "t"]))
    cand = {}
    src = raw.loc[raw["qc"]]
    for m, (a, t) in link.items():
        for r in src.loc[src["t"] == m].itertuples(index=False):
            for k in range(m, t + 1):
                if k != m and lo <= k <= hi:
                    cand.setdefault((r.area_id, k), []).append((m, a, tuple(getattr(r, c) for c in LABELS)))
    copies = {}
    for (area, k), cs in cand.items():
        if (area, k) not in blank:
            continue
        top = max(c[0] for c in cs)
        win_c = [c for c in cs if c[0] == top]
        if len({c[2] for c in win_c}) > 1:
            continue
        copies[(area, k)] = win_c[0]
    fam_of_month = lambda m: f"anl:{link[m][0]}" if m in link else f"local:{lab(m)}"
    orig = raw.loc[raw["full"] | (~raw["full"] & ~raw["blank"] & raw["overall_phase"].notna())]
    rows = [{"area_id": r.area_id, "target_ord": r.t, "is_copy": False, "original_month_ord": r.t, "source_family": fam_of_month(r.t), **{c: getattr(r, c) for c in LABELS}} for r in orig.itertuples(index=False)]
    rows += [{"area_id": a, "target_ord": k, "is_copy": True, "original_month_ord": m, "source_family": f"anl:{an}", **dict(zip(LABELS, v))} for (a, k), (m, an, v) in copies.items()]
    return pd.DataFrame(rows), raw


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--config", type=Path, default=None, help="default: configs/somalia_v4_calibrated_d.json")
    ap.add_argument("--probe-rows", type=int, default=0, help="model probe rows per job (0 = all)")
    ap.add_argument("--skip-large-input-hashes", action="store_true", help="do not rehash the multi-GB deep-feature file")
    args = ap.parse_args(argv)
    R = Replay(args.out_dir)
    man = json.loads((args.out_dir / "manifest.json").read_text())
    from ipcch import paths

    cfg_path = args.config or paths.CONFIG_DIR / "somalia_v4_calibrated_d.json"
    cfg = json.loads(Path(cfg_path).read_text())
    min_cal, tol = int(cfg["min_calibration_rounds"]), float(cfg["tie_tolerance"])
    settings, years, horizons = list(cfg["data_settings"]), [int(y) for y in cfg["outer_years"]], [int(h) for h in cfg["horizons"]]

    # ---------------- inputs and configuration ----------------
    R.check("config_digest_matches_manifest", sha(cfg_path) == man["config_sha256"])
    dig = []
    for name, rec in man["inputs"].items():
        if rec["sha256"] in (None, "not_computed") or (name == "deep" and args.skip_large_input_hashes):
            continue
        if sha(rec["path"]) != rec["sha256"]:
            dig.append(name)
    R.check("input_digests_match_manifest", not dig and man["inputs"]["v2"]["sha256"] in (cfg["climate_sha256"], "not_computed"), dig)
    R.check("validity_snapshot_digest", sha(cfg["validity_snapshot"]) == cfg["validity_snapshot_sha256"] == man["validity_snapshot"]["sha256"])

    # ---------------- labels rebuilt from raw + snapshot ----------------
    led = R.read("ledgers/label_ledger.csv.gz")
    exp, raw = rebuild_labels(cfg, man)
    k_led = set(zip(led["area_id"], led["target_ord"]))
    k_exp = set(zip(exp["area_id"], exp["target_ord"]))
    R.check("label_keys_rebuilt_from_raw_and_snapshot", k_led == k_exp, f"saved {len(k_led)} rebuilt {len(k_exp)}; only saved {list(k_led - k_exp)[:3]} only rebuilt {list(k_exp - k_led)[:3]}")
    m = led.merge(exp, on=["area_id", "target_ord"], suffixes=("", "_x"))
    same = (m["is_copy"] == m["is_copy_x"]) & (m["original_month_ord"] == m["original_month_ord_x"]) & (m["source_family"] == m["source_family_x"]) & (m["source_available_ord"] == m["original_month_ord_x"])
    for c in LABELS:  # values equal up to float parsing of the raw CSV (pandas default vs round-trip parser)
        same &= pd.Series(np.isclose(m[c].to_numpy(float), m[f"{c}_x"].to_numpy(float), rtol=1e-12, atol=0, equal_nan=True), index=m.index)
    R.check("label_values_lineage_and_availability_rebuilt", same.all() and len(m) == len(led), f"{int((~same).sum())} rows differ")
    copies = led.loc[led["is_copy"]]
    R.check("copies_never_history", not copies["valid_history"].any())
    R.check("copies_in_pre2022_years", (copies["target_ord"] // 12 < 2022).any(), copies["target_ord"].floordiv(12).value_counts().to_dict())

    # ---------------- realized-weather verification rebuilt from raw ----------------
    w = raw[["area_id", "t", *WEATHER]].sort_values(["area_id", "t"])
    prev = w.groupby("area_id")[["t", *WEATHER]].shift(1)
    rep = (prev["t"] == w["t"] - 1) & (w[WEATHER[0]] == prev[WEATHER[0]]) & (w[WEATHER[1]] == prev[WEATHER[1]])
    good = np.isfinite(w[WEATHER].to_numpy(float)).all(axis=1) & ~rep.to_numpy()
    ver = set(zip(w.loc[good, "area_id"], w.loc[good, "t"]))
    prov = {h: R.read(f"ledgers/row_provenance_h{h:02d}.csv.gz") for h in horizons}
    wbad = 0
    for h, p in prov.items():
        k = min(h, 6)
        for r in p.itertuples(index=False):
            wbad += all((r.area_id, r.origin_ord + j) in ver for j in range(1, k + 1)) != bool(r.oracle_all_verified)
    R.check("oracle_weather_verification_rebuilt", wbad == 0, wbad)

    # ---------------- cohorts and slot inventory ----------------
    cohort = R.read("ledgers/cohort_ledger.csv.gz")
    slots = R.read("ledgers/cohort_slots.csv")
    R.check("original_cohort_has_no_copies", not cohort.loc[cohort["data_setting"] == "original", "is_copy"].any())
    for s in settings:
        for y in years:
            for h in horizons:
                g = cohort.loc[(cohort["data_setting"] == s) & (cohort["outer_year"] == y) & (cohort["horizon"] == h)]
                pool = led.loc[(led["target_ord"] // 12 == y) & ((~led["is_copy"]) if s == "original" else True)]
                pv = prov[h].set_index(["area_id", "target_ord"])["oracle_all_verified"]
                expk = {(r.area_id, r.target_ord) for r in pool.itertuples(index=False) if r.valid_target and r.valid_score and (h == 0 or bool(pv.get((r.area_id, r.target_ord), False)))}
                prim = g.loc[g["status"] == "primary"]
                R.check(f"cohort_rebuilt_{s}_{y}_h{h}", set(zip(prim["area_id"], prim["target_ord"])) == expk and len(g) == len(pool), f"{len(prim)} vs {len(expk)}")
                srow = slots.loc[(slots["data_setting"] == s) & (slots["outer_year"] == y) & (slots["horizon"] == h)]
                R.check(f"cohort_digest_{s}_{y}_h{h}", (len(srow) == 1 and srow["cohort_sha256"].iloc[0] == sorted_digest(prim)) or (len(srow) == 0 and len(g) == 0))
    R.check("augmented_tests_admit_copies", cohort.loc[(cohort["data_setting"] == "augmented") & (cohort["status"] == "primary"), "is_copy"].sum() > 0)
    annual = R.read("metrics/annual_metrics.csv")
    pooled = R.read("metrics/pooled_metrics.csv")
    want_a = {(s, y, h) for s in settings for y in years for h in horizons}
    want_p = {(s, h) for s in settings for h in horizons}
    R.check("annual_slot_inventory", set(zip(annual["data_setting"], annual["outer_year"], annual["horizon"])) == want_a and len(annual) == len(want_a), len(annual))
    R.check("pooled_slot_inventory", set(zip(pooled["data_setting"], pooled["horizon"])) == want_p and len(pooled) == len(want_p), len(pooled))

    # ---------------- contexts, pools, temporal and report/history isolation ----------------
    jobs = R.read("ledgers/jobs.csv", dtype={"test_families": str})
    ctx = R.read("selection/contexts.csv", dtype={"test_families": str})
    ctx["test_families"] = ctx["test_families"].fillna("")
    R.check("every_job_has_one_context", sorted(jobs["job_id"]) == sorted(ctx["job_id"]) and not ctx["job_id"].duplicated().any())
    exp_jobs = set()
    prim_all = cohort.loc[cohort["status"] == "primary"]
    for (s, y, h), g in prim_all.groupby(["data_setting", "outer_year", "horizon"]):
        for o in set(g["target_ord"] - h):
            exp_jobs.add(f"{s}_y{y}_h{h:02d}_o{lab(o)}")
    R.check("jobs_cover_every_primary_origin", exp_jobs == set(jobs["job_id"]) or bool(man.get("pilot")), len(exp_jobs ^ set(jobs["job_id"])))
    specs = R.read("selection/pool_specs.csv.gz", dtype={"excluded_families": str})
    specs["excluded_families"] = specs["excluded_families"].fillna("")
    spec_by = specs.set_index("spec_id")
    orig = led.loc[~led["is_copy"]]
    rich = {f: dict(zip(g.loc[g["valid_history"], "area_id"], g.loc[g["valid_history"], "target_ord"])) for f, g in orig.groupby("source_family")}
    catp = {f: set(zip(g.loc[g["valid_phase"], "area_id"], g.loc[g["valid_phase"], "target_ord"])) for f, g in orig.groupby("source_family")}
    fam_all = led.set_index(["area_id", "target_ord"])["source_family"].to_dict()

    def exposing(h, area, cutoff, target, fams):
        own = fam_all[(area, target)]  # the row's own report is never in its frame history
        out = set()
        for f in fams:
            if f == own:
                continue
            m_ = rich.get(f, {}).get(area)
            if (m_ is not None and m_ <= cutoff) or (h < 12 and (area, target - max(1, h)) in catp.get(f, set())):
                out.add(f)
        return frozenset(out)

    def exposed_mask(h, df, fams):
        """Vectorized ``exposing`` over rows of df (area_id, target_ord, history_cutoff_ord, source_family)."""
        area, cut = df["area_id"].to_numpy(), df["history_cutoff_ord"].to_numpy()
        tgt, own = df["target_ord"].to_numpy(), df["source_family"].to_numpy(dtype=object)
        out = np.zeros(len(df), dtype=bool)
        for f in fams:
            mm = pd.Series(rich.get(f, {}), dtype=float).reindex(area).to_numpy(float)
            hit = np.isfinite(mm) & (mm <= cut)
            if h < 12 and catp.get(f):
                hit |= np.fromiter(((a, t - max(1, h)) in catp[f] for a, t in zip(area, tgt)), dtype=bool, count=len(df))
            out |= hit & (own != f)
        return out

    ovr = R.read("selection/history_overrides.csv.gz", dtype={"hx": str}) if (args.out_dir / "selection" / "history_overrides.csv.gz").stat().st_size > 30 else pd.DataFrame(
        columns=["scope", "role", "horizon", "area_id", "target_ord", "hx", "frame_hist_q3_obs1", "context_hist_q3_obs1", "context_obs1_source_ord", "context_base_ok"])
    ovr["hx"] = ovr["hx"].fillna("")
    fit_ovr = {(r.scope, r.area_id, r.target_ord) for r in ovr.loc[ovr["role"].isin(["fit", "final_fit"])].itertuples(index=False)}
    pool_rows, bad = {}, []
    for r in specs.itertuples(index=False):
        p = prov[r.horizon]
        base = (p["target_ord"] <= r.label_cutoff_ord) & (p["source_available_ord"] <= r.available_by_ord)
        if r.setting == "original":
            base &= ~p["is_copy"]
        if pd.notna(r.max_year):
            base &= (p["target_ord"] // 12 <= r.max_year) & (p["original_month_ord"] // 12 <= r.max_year)
        ex = set(v for v in r.excluded_families.split(";") if v)
        sub = p.loc[base & ~p["source_family"].isin(ex)]
        pool_rows[r.spec_id] = (p.loc[base], sub, ex)
        if (keys_hash(sub) if len(sub) else None) != (r.pool_keys_sha256 if isinstance(r.pool_keys_sha256, str) else None) or len(sub) != r.n_pool:
            bad.append(("hash", r.spec_id))
        if r.setting == "original" and sub["is_copy"].any():
            bad.append(("copy", r.spec_id))
        if ex and len(sub):  # every pool row exposed to an excluded family is fitted with recomputed history
            hit = exposed_mask(r.horizon, sub, ex)
            if any((f"spec:{r.spec_id}", a, t) not in fit_ovr for a, t in zip(sub["area_id"].to_numpy()[hit], sub["target_ord"].to_numpy()[hit])):
                bad.append(("unrecomputed_exposed_pool_row", r.spec_id))
    R.check("pools_rebuilt_and_exposed_rows_recomputed", not bad, bad[:5])
    mem = R.read("selection/scoring_keys.csv.gz", dtype={"hx": str})
    cal = R.read("selection/calibration_keys.csv.gz", dtype={"hx": str})
    fcal = R.read("selection/final_calibration_keys.csv.gz", dtype={"hx": str})
    for t in (mem, cal, fcal):
        t["hx"] = t["hx"].fillna("")
    fam_of = led.set_index(["area_id", "target_ord"])["source_family"]
    fam_by_round = led.loc[~led["is_copy"]].drop_duplicates("original_month_ord").set_index("original_month_ord")["source_family"]
    pv_cut = {h: p.set_index(["area_id", "target_ord"])["history_cutoff_ord"] for h, p in prov.items()}

    hist_cache = {}

    def key_ok(r, h, origin, tf, served, kind):
        sp = spec_by.loc[r.spec_id]
        base, sub, ex = pool_rows[r.spec_id]
        nominal = set(tf) | {fam_of[(r.area_id, r.target_ord)]} | ({served} if served else set())
        errs = []
        if sp.label_cutoff_ord != min(r.target_ord - h, r.target_ord - 1) or sp.available_by_ord != r.target_ord - h:
            errs.append(f"{kind}_own_origin")
        if r.target_ord > origin:
            errs.append(f"{kind}_after_origin")
        if nominal & set(sub["source_family"]):
            errs.append(f"{kind}_family_in_pool_labels")
        ck = (r.spec_id, frozenset(nominal))
        if ck not in hist_cache:
            rest = nominal - ex
            keep = ~base["source_family"].isin(nominal).to_numpy()
            hist_cache[ck] = bool(rest) and bool(exposed_mask(h, base.loc[keep], rest).any())
        if hist_cache[ck]:
            errs.append(f"{kind}_family_in_pool_history")
        if exposing(h, r.area_id, pv_cut[h][(r.area_id, r.target_ord)], r.target_ord, set(tf) | ({served} if served else set())) != hx_set(r.hx):
            errs.append(f"{kind}_hx")
        return errs

    viol = []
    for c in ctx.itertuples(index=False):
        tf = {x for x in c.test_families.split(";") if x}
        h = c.horizon
        origin = mo(*map(int, c.origin.split("-")))
        for r in mem.loc[mem["job_id"] == c.job_id].itertuples(index=False):
            viol += [(e, c.job_id) for e in key_ok(r, h, origin, tf, fam_by_round[r.round], "member")]
            if c.data_setting == "original" and r.is_copy:
                viol.append(("member_copy", c.job_id))
        for r in cal.loc[cal["job_id"] == c.job_id].itertuples(index=False):
            if not (r.target_ord < r.scoring_target_ord and r.target_ord <= r.scoring_target_ord - h and r.round < r.scoring_round):
                viol.append(("calibration_time", c.job_id))
            viol += [(e, c.job_id) for e in key_ok(r, h, origin, tf, fam_by_round[r.scoring_round], "calibration")]
            if c.data_setting == "original" and r.is_copy:
                viol.append(("calibration_copy", c.job_id))
        for r in fcal.loc[fcal["job_id"] == c.job_id].itertuples(index=False):
            if r.target_ord // 12 > c.outer_year - 1 or r.round // 12 > c.outer_year - 1:
                viol.append(("final_calibration_window", c.job_id))
            viol += [(e, c.job_id) for e in key_ok(r, h, origin, tf, None, "final_calibration")]
            if c.data_setting == "original" and r.is_copy:
                viol.append(("final_calibration_copy", c.job_id))
        if c.status == "ok" and isinstance(c.fit_spec_id, str):
            sp = spec_by.loc[c.fit_spec_id]
            base, sub, ex = pool_rows[c.fit_spec_id]
            if sp.label_cutoff_ord != origin or sp.available_by_ord != origin or set(sub["source_family"]) & tf or (sub["target_ord"] // 12 > c.outer_year - 1).any():
                viol.append(("fit_spec", c.job_id))
            if tf and len(sub):
                hit = exposed_mask(h, sub, tf)
                if any((f"job:{c.job_id}", a, t) not in fit_ovr for a, t in zip(sub["area_id"].to_numpy()[hit], sub["target_ord"].to_numpy()[hit])):
                    viol.append(("final_fit_history", c.job_id))
    R.check("temporal_report_and_history_isolation", not viol, sorted(set(viol))[:6])

    # override values rebuilt independently: latest permitted original of the area at or before the cutoff
    hq3 = orig.loc[orig["valid_history"]].copy()
    hq3["q3h"] = hq3[["h_p3", "h_p4", "h_p5"]].sum(axis=1)
    hq3_by_area = {a: g.sort_values("target_ord")[["target_ord", "source_family", "q3h"]].to_numpy(dtype=object) for a, g in hq3.groupby("area_id")}
    obad = 0
    for r in ovr.itertuples(index=False):
        if r.role == "fit":
            ex = {x for x in spec_by.loc[r.scope.split(":", 1)[1], "excluded_families"].split(";") if x}
        elif r.role == "final_fit":
            ex = {x for x in ctx.loc[ctx["job_id"] == r.scope.split(":", 1)[1], "test_families"].iloc[0].split(";") if x}
        else:
            ex = set(hx_set(r.hx))
        cut = pv_cut[r.horizon][(r.area_id, r.target_ord)]
        cand_ = [x for x in hq3_by_area.get(r.area_id, []) if x[0] <= cut and x[1] not in ex]
        exp_src = int(cand_[-1][0]) if cand_ else -1
        exp_b = float(cand_[-1][2]) if cand_ else np.nan
        if exp_src != r.context_obs1_source_ord or not ((np.isnan(exp_b) and np.isnan(r.context_hist_q3_obs1)) or np.isclose(exp_b, r.context_hist_q3_obs1, rtol=0, atol=1e-12)):
            obad += 1
    R.check("history_override_baselines_rebuilt", obad == 0, f"{obad} of {len(ovr)}")

    fit = R.read("fits/final_fit_ledger.csv.gz")
    fstat = R.read("fits/final_status.csv", dtype={"half_life": str})
    wviol = []
    for job_id, g in fit.groupby("job_id"):
        st = fstat.loc[fstat["job_id"] == job_id].iloc[0]
        c = ctx.loc[ctx["job_id"] == job_id].iloc[0]
        origin = mo(*map(int, c.origin.split("-")))
        hl = str(st["half_life"])
        age = origin - g["target_ord"]
        exp_w = np.ones(len(g)) if hl == "none" else 0.5 ** (age / float(hl))
        tf = {x for x in (c.test_families or "").split(";") if x}
        ok = (age >= 0).all() and (g["source_available_ord"] <= origin).all() and (g["target_ord"] // 12 <= c.outer_year - 1).all() and np.allclose(g["weight"], exp_w, rtol=0, atol=1e-15)
        ok &= not (c.data_setting == "original" and g["is_copy"].any()) and not g["source_family"].isin(tf).any()
        if not ok:
            wviol.append(job_id)
    R.check("final_fit_pools_and_decay_weights", not wviol, wviol[:5])

    # ---------------- selection replay ----------------
    units = R.read("selection/oof_units.csv.gz", dtype={"half_life": str})
    oof = R.read("selection/oof_predictions.csv.gz", dtype={"hx": str})
    oof["hx"] = oof["hx"].fillna("")
    oof_idx = {u: g.set_index(["area_id", "target_ord", "hx"])["raw_q3"] for u, g in oof.groupby("unit_id")}
    ukey = {(r.spec_id, r.formulation, r.bundle, r.half_life): (r.unit_id, r.status) for r in units.itertuples(index=False)}
    truth = led.set_index(["area_id", "target_ord"])
    scores = R.read("selection/candidate_scores.csv", dtype={"half_life": str})
    selected = R.read("selection/selected_recipes.csv", dtype={"half_life": str})
    hb_frame = {h: pd.Series(np.isfinite(p["hist_q3_obs1"].to_numpy(float)) & (p["history_obs1_source_ord"].to_numpy() >= 0), index=pd.MultiIndex.from_frame(p[["area_id", "target_ord"]])) for h, p in prov.items()}
    ovr_ok = {(r.area_id, r.target_ord, r.hx, r.horizon): bool(r.context_base_ok) for r in ovr.loc[ovr["role"].isin(["oof_prediction", "test_prediction"])].itertuples(index=False)}

    def has_base(keys, h):
        return np.array([ovr_ok[(a, t, x, h)] if x else bool(hb_frame[h][(a, t)]) for a, t, x in zip(keys["area_id"], keys["target_ord"], keys["hx"])], dtype=bool)

    def unit_raw(spec_id, form, bundle, hl, keys):
        uid, st = ukey.get((spec_id, form, bundle, hl), (None, "missing"))
        if st != "ok":
            return None
        return oof_idx[uid].reindex(pd.MultiIndex.from_frame(keys[["area_id", "target_ord", "hx"]])).to_numpy(dtype=float)

    def cand_raw(frame, form, bundle, hl, h):
        lbl = np.where(has_base(frame, h), "residual", "fallback_direct").astype(object) if form == "residual" else np.full(len(frame), "direct", dtype=object)
        raw_ = np.full(len(frame), np.nan)
        for sid, g in frame.groupby("spec_id"):
            pos = frame.index.get_indexer(g.index)
            for unit_form, want in (("direct", lbl[pos] != "residual"), ("residual", lbl[pos] == "residual")):
                if not want.any():
                    continue
                vals = unit_raw(sid, unit_form, bundle, hl, g.loc[want])
                if vals is None:
                    return None, None
                raw_[pos[want]] = vals
        return raw_, lbl

    def maps_for(calrows, form, bundle, hl, method, h):
        cr = calrows.reset_index(drop=True)
        names = ("direct",) if form == "direct" else ("residual", "fallback_direct")
        if method == "none":
            return {n: fit_map("none", None, None, None, min_cal) for n in names}
        y = truth.loc[list(zip(cr["area_id"], cr["target_ord"])), "q3"].to_numpy(dtype=float) if len(cr) else np.array([])
        hb = has_base(cr, h) if len(cr) else np.array([], dtype=bool)
        out = {}
        for name in names:
            unit_form = "residual" if name == "residual" else "direct"
            keep = hb if name == "residual" else np.ones(len(cr), dtype=bool)
            raw_ = np.full(len(cr), np.nan)
            failed = False
            for sid, g in cr.loc[keep].groupby("spec_id"):
                vals = unit_raw(sid, unit_form, bundle, hl, g)
                if vals is None:
                    failed = True
                    break
                raw_[g.index.to_numpy()] = vals
            if failed or not np.isfinite(raw_[keep]).all():
                out[name] = ("unsupported", None, None)
                continue
            out[name] = fit_map(method, raw_[keep], y[keep], cr["round"].to_numpy()[keep], min_cal)
        return out

    sel_mis, score_mis, n_cand, recon = [], [], 0, []
    ok_sigs = set(ctx.loc[ctx["status"] == "ok", "selection_signature"])
    for sig in sorted(ok_sigs):
        jobs_sig = ctx.loc[ctx["selection_signature"] == sig, "job_id"]
        job = jobs_sig.iloc[0]
        h = int(ctx.loc[ctx["job_id"] == job, "horizon"].iloc[0])
        m_ = mem.loc[mem["job_id"] == job].reset_index(drop=True)
        cc = cal.loc[cal["job_id"] == job]
        sc = scores.loc[scores["selection_signature"] == sig].drop_duplicates(["bundle", "half_life", "formulation", "method"])
        if len(sc) != 144:
            recon.append(("candidate_rows", sig))
        res = []
        for bundle in sorted(set(units["bundle"])):
            for hl in ("12", "24", "48", "none"):
                for form in FORMS:
                    raw_, lbl = cand_raw(m_, form, bundle, hl, h)
                    for method in METHODS:
                        n_cand += 1
                        if raw_ is None or not np.isfinite(raw_).all():
                            res.append({"bundle": bundle, "half_life": hl, "formulation": form, "method": method, "ok": False})
                            continue
                        fin = np.full(len(m_), np.nan)
                        fail = False
                        for (rr, v), gg in m_.groupby(["round", "target_ord"]):
                            pos = gg.index.to_numpy()
                            mp = maps_for(cc.loc[(cc["scoring_round"] == rr) & (cc["scoring_target_ord"] == v)], form, bundle, hl, method, h)
                            for name in np.unique(lbl[pos]):
                                st, fn, _ = mp[name]
                                if st != "ok":
                                    fail = True
                                    break
                                sel = pos[lbl[pos] == name]
                                fin[sel] = np.clip(fn(raw_[sel]), 0, 1)
                            if fail:
                                break
                        if fail:
                            res.append({"bundle": bundle, "half_life": hl, "formulation": form, "method": method, "ok": False})
                            continue
                        t = truth.loc[list(zip(m_["area_id"], m_["target_ord"]))]
                        y, crs = t["q3"].to_numpy(float), t["actual_crisis"].to_numpy(float)
                        auc = roc_auc_score(crs == 1, fin) if np.unique(crs).size == 2 else np.nan
                        res.append({"bundle": bundle, "half_life": hl, "formulation": form, "method": method, "ok": True, "rmse": float(np.sqrt(mean_squared_error(y, fin))), "auc": auc})
        rep = pd.DataFrame(res)
        mg = sc.merge(rep, on=["bundle", "half_life", "formulation", "method"], how="outer", validate="one_to_one")
        okm = mg["ok"].astype("boolean").fillna(False).astype(bool)
        both = mg.loc[(mg["status"] == "ok") & okm]
        if ((mg["status"] == "ok") != okm).any() or len(mg) != 144 or not np.allclose(both["rmse_x"], both["rmse_y"], rtol=1e-12, atol=1e-14):
            score_mis.append(sig)
        okc = rep.loc[rep["ok"]].copy()
        win = None
        if not okc.empty:
            best = okc["rmse"].min()
            tie = okc.loc[okc["rmse"] <= best + tol].copy()
            tie["m"], tie["b"] = tie["method"].map(METHODS.index), tie["bundle"].str[1:].astype(int)
            tie["f"], tie["d"] = tie["formulation"].map(FORMS.index), tie["half_life"].map(HL_ORDER)
            keys, asc = (["auc"], [False]) if (len(tie) > 1 and tie["auc"].notna().all()) else ([], [])
            win = tie.sort_values(keys + ["m", "b", "f", "d"], ascending=asc + [True] * 4, kind="mergesort").iloc[0]
        for job_id in jobs_sig:
            r = selected.loc[selected["job_id"] == job_id].iloc[0]
            if win is None:
                if r.status == "ok":
                    sel_mis.append(job_id)
            elif r.status != "ok" or (r.formulation, r.bundle, str(r.half_life), r.method) != (win["formulation"], win["bundle"], win["half_life"], win["method"]):
                sel_mis.append(job_id)
    for r in selected.itertuples(index=False):
        if ctx.loc[ctx["job_id"] == r.job_id, "status"].iloc[0] != "ok" and r.status == "ok":
            sel_mis.append(r.job_id)
    R.check("candidate_scores_replayed", not score_mis and not recon and n_cand == 144 * len(ok_sigs) and n_cand > 0, (score_mis[:3], recon[:3], n_cand))
    R.check("selected_recipes_replayed", not sel_mis and set(selected["job_id"]) == set(jobs["job_id"]), sel_mis[:5])

    # ---------------- final mappings, predictions and saved models ----------------
    preds = R.read("predictions/final_predictions.csv.gz", dtype={"half_life": str, "hx": str})
    preds["hx"] = preds["hx"].fillna("")
    maps_saved = R.read("fits/calibration_mappings.csv")
    fmis = []
    for r in selected.loc[selected["status"] == "ok"].itertuples(index=False):
        g = preds.loc[preds["job_id"] == r.job_id]
        c = ctx.loc[ctx["job_id"] == r.job_id].iloc[0]
        tf = {x for x in c.test_families.split(";") if x}
        keys_exp = cohort.loc[(cohort["data_setting"] == r.data_setting) & (cohort["outer_year"] == r.outer_year) & (cohort["horizon"] == r.horizon) & (cohort["status"] == "primary")]
        keys_exp = keys_exp.loc[keys_exp["target_ord"] - r.horizon == mo(*map(int, r.origin.split("-")))]
        if set(zip(g["area_id"], g["target_ord"])) != set(zip(keys_exp["area_id"], keys_exp["target_ord"])) or g.duplicated(["area_id", "target_ord"]).any():
            fmis.append((r.job_id, "test_keys"))
        for q in g.itertuples(index=False):
            if exposing(r.horizon, q.area_id, pv_cut[r.horizon][(q.area_id, q.target_ord)], q.target_ord, tf) != hx_set(q.hx):
                fmis.append((r.job_id, "test_hx"))
                break
        mp = maps_for(fcal.loc[fcal["job_id"] == r.job_id], r.formulation, r.bundle, str(r.half_life), r.method, r.horizon)
        exp_f = np.full(len(g), np.nan)
        ok_all = True
        for name in g["prediction_branch"].unique():
            st, fn, obj = mp[name]
            sel = (g["prediction_branch"] == name).to_numpy()
            if st != "ok":
                ok_all = False
                continue
            exp_f[sel] = np.clip(fn(g["q3_raw"].to_numpy(float)[sel]), 0, 1)
            sm = maps_saved.loc[(maps_saved["job_id"] == r.job_id) & (maps_saved["prediction_branch"] == name)]
            if r.method == "shift" and not np.isclose(sm["shift"].iloc[0], obj, rtol=0, atol=1e-15):
                fmis.append((r.job_id, "shift"))
        if ok_all:
            if not np.allclose(exp_f, g["q3_final"].to_numpy(float), rtol=0, atol=1e-12):
                fmis.append((r.job_id, "final"))
        elif g["q3_final"].notna().any():
            fmis.append((r.job_id, "unavailable_mapping_has_final"))
    R.check("final_test_keys_mappings_and_bounds_replayed", not fmis, fmis[:5])

    inv = R.read("models/model_inventory.csv")
    ofp = args.out_dir / "features" / "final_override_features.csv.gz"
    ofeat = R.read("features/final_override_features.csv.gz", dtype={"hx": str}) if ofp.exists() and ofp.stat().st_size > 30 else pd.DataFrame(columns=["job_id", "area_id", "target_ord"])
    import xgboost as xgb

    feats, schema = {}, json.loads((args.out_dir / "features" / "feature_schema.json").read_text())
    pmis, n_probe, n_probe_ovr = [], 0, 0
    for job_id, g in preds.groupby("job_id"):
        h = int(g["horizon"].iloc[0])
        cols = schema[f"h{h:02d}_D"]
        if h not in feats:
            fm = R.read(f"features/feature_matrix_h{h:02d}.csv.gz")
            feats[h] = fm.set_index(["area_id", "target_ord"])[cols]
        gg = g if not args.probe_rows else g.head(args.probe_rows)
        X = np.array(feats[h].loc[list(zip(gg["area_id"], gg["target_ord"]))].to_numpy(dtype=np.float32), copy=True)
        base = np.array(prov[h].set_index(["area_id", "target_ord"]).loc[list(zip(gg["area_id"], gg["target_ord"])), "hist_q3_obs1"].to_numpy(float), copy=True)
        ex_rows = np.flatnonzero(gg["hx"].to_numpy() != "")
        if ex_rows.size:
            o = ofeat.loc[ofeat["job_id"] == job_id].set_index(["area_id", "target_ord"])
            X[ex_rows] = o.loc[list(zip(gg["area_id"].to_numpy()[ex_rows], gg["target_ord"].to_numpy()[ex_rows])), cols].to_numpy(dtype=np.float32)
            ob = ovr.loc[(ovr["scope"] == f"job:{job_id}") & (ovr["role"] == "test_prediction")].set_index(["area_id", "target_ord"])["context_hist_q3_obs1"]
            base[ex_rows] = ob.loc[list(zip(gg["area_id"].to_numpy()[ex_rows], gg["target_ord"].to_numpy()[ex_rows]))].to_numpy(float)
            n_probe_ovr += ex_rows.size
        pr = {}
        for r in inv.loc[inv["job_id"] == job_id].itertuples(index=False):
            p = args.out_dir / "models" / r.path
            if sha(p) != r.sha256:
                pmis.append((job_id, "hash"))
            if r.kind == "xgboost":
                b = xgb.Booster()
                b.load_model(str(p))
                pr[r.target] = b.predict(xgb.DMatrix(X))
            else:
                pr[r.target] = np.full(len(gg), json.loads(p.read_text())["value"])
        q3 = np.where(gg["prediction_branch"] == "residual", base + pr.get("q3_residual_delta", np.full(len(gg), np.nan)), pr["q3_direct"])
        for t, col in (("q2", "q2_raw"), ("q4", "q4_raw"), ("q5", "q5_raw")):
            if not np.allclose(pr[t], gg[col].to_numpy(float), rtol=0, atol=1e-6):
                pmis.append((job_id, t))
        if not np.allclose(q3, gg["q3_raw"].to_numpy(float), rtol=0, atol=1e-6):
            pmis.append((job_id, "q3"))
        n_probe += len(gg)
    R.check("saved_models_reproduce_predictions", not pmis and n_probe > 0, pmis[:5])

    # ---------------- metrics (every reported field) ----------------
    def metrics(mm):
        y, c, f, raw_ = mm["q3"].to_numpy(float), mm["actual_crisis"].to_numpy(float) == 1, mm["q3_final"].to_numpy(float), mm["q3_raw"].to_numpy(float)
        out = {"n": len(mm), "n_areas": mm["area_id"].nunique(), "n_months": mm["target_ord"].nunique(), "n_original_reports": mm["source_family"].nunique(),
               "n_originals": int((~mm["is_copy"].astype(bool)).sum()), "n_copies": int(mm["is_copy"].astype(bool).sum())}
        for k, v in (("raw", raw_), ("final", f)):
            out[f"{k}_rmse"] = np.sqrt(mean_squared_error(y, v))
            out[f"{k}_mae"] = mean_absolute_error(y, v)
            out[f"{k}_bias"] = float(np.mean(v - y))
            out[f"{k}_mean_truth"], out[f"{k}_mean_pred"] = float(np.mean(y)), float(np.mean(v))
            out[f"{k}_r2"] = r2_score(y, v) if np.unique(y).size > 1 else np.nan
            out[f"{k}_auc"] = roc_auc_score(c, v) if np.unique(c).size == 2 else np.nan
        pb = f >= 0.2
        out["bin_f1"] = f1_score(c, pb, zero_division=np.nan)
        out["bin_precision"] = precision_score(c, pb, zero_division=np.nan)
        out["bin_recall"] = recall_score(c, pb, zero_division=np.nan)
        out["bin_tp"], out["bin_fp"] = int((c & pb).sum()), int((~c & pb).sum())
        out["bin_fn"], out["bin_tn"] = int((c & ~pb).sum()), int((~c & ~pb).sum())
        out["n_clipped"] = int(mm["clipped"].astype(bool).sum())
        out["n_fallback_direct"] = int((mm["prediction_branch"] == "fallback_direct").sum())
        out["n_residual_branch"] = int((mm["prediction_branch"] == "residual").sum())
        return out

    def compare(got, want, tag):
        errs = []
        for k, v in want.items():
            g = got.get(k)
            g_nan = g is None or pd.isna(g)
            v_nan = isinstance(v, float) and np.isnan(v)
            if g_nan or v_nan:
                if g_nan != v_nan:
                    errs.append((tag, k))
            elif not np.isclose(float(v), float(g), rtol=1e-9, atol=1e-12):
                errs.append((tag, k))
        return errs

    mmis, parts = [], {}
    tcols = led[["area_id", "target_ord", "q3", "actual_crisis"]]
    for r in annual.itertuples(index=False):
        prim = cohort.loc[(cohort["data_setting"] == r.data_setting) & (cohort["outer_year"] == r.outer_year) & (cohort["horizon"] == r.horizon) & (cohort["status"] == "primary"), ["area_id", "target_ord", "is_copy", "source_family"]]
        p = preds.loc[(preds["data_setting"] == r.data_setting) & (preds["outer_year"] == r.outer_year) & (preds["horizon"] == r.horizon)]
        if p.duplicated(["area_id", "target_ord"]).any() or not set(zip(p["area_id"], p["target_ord"])) <= set(zip(prim["area_id"], prim["target_ord"])):
            mmis.append((r.data_setting, r.outer_year, r.horizon, "keys"))
        mm = prim.merge(tcols, on=["area_id", "target_ord"], how="left").merge(p[["area_id", "target_ord", "q3_raw", "q3_final", "clipped", "prediction_branch"]], on=["area_id", "target_ord"], how="left")
        exp_status = "empty_cohort" if prim.empty else ("incomplete" if mm["q3_final"].isna().any() else "complete")
        if exp_status != r.status or (r.status != "augmentation_unavailable" and r.cohort_sha256 != sorted_digest(prim)):
            mmis.append((r.data_setting, r.outer_year, r.horizon, "status_or_digest"))
        if exp_status == "complete":
            parts.setdefault((r.data_setting, r.horizon), []).append(mm.assign(outer_year=r.outer_year))
            mmis += compare(r._asdict(), metrics(mm), (r.data_setting, r.outer_year, r.horizon))
    for r in pooled.itertuples(index=False):
        a = annual.loc[(annual["data_setting"] == r.data_setting) & (annual["horizon"] == r.horizon)]
        exp_status = "incomplete" if (a["status"] == "incomplete").any() else ("empty_cohort" if not parts.get((r.data_setting, r.horizon)) else "complete")
        if exp_status != r.status:
            mmis.append((r.data_setting, "pooled", r.horizon, "status"))
        if exp_status == "complete":
            mm = pd.concat(parts[(r.data_setting, r.horizon)], ignore_index=True)
            by_year = ";".join(f"{y}:{n}" for y, n in mm.groupby("outer_year").size().items())
            if r.rows_by_year != by_year or r.cohort_sha256 != sorted_digest(mm):
                mmis.append((r.data_setting, "pooled", r.horizon, "composition"))
            mmis += compare(r._asdict(), metrics(mm), (r.data_setting, "pooled", r.horizon))
    R.check("annual_and_pooled_metrics_replayed", not mmis, mmis[:8])
    leak = [s for s, g in preds.groupby("data_setting") if not set(zip(g["area_id"], g["target_ord"])) <= set(zip(prim_all.loc[prim_all["data_setting"] == s, "area_id"], prim_all.loc[prim_all["data_setting"] == s, "target_ord"]))]
    orig_pred_copies = preds.loc[preds["data_setting"] == "original"].merge(led[["area_id", "target_ord", "is_copy"]], on=["area_id", "target_ord"])["is_copy"].any()
    R.check("predictions_stay_in_own_setting_cohort", not leak and not orig_pred_copies, leak)
    R.check("no_cross_setting_contrast_outputs", not any(c.startswith(("delta", "contrast")) or "bootstrap" in c for c in [*annual.columns, *pooled.columns]) and not (args.out_dir / "metrics" / "contrasts.csv").exists())

    rep = pd.DataFrame(R.rows)
    (args.out_dir / "replay").mkdir(exist_ok=True)
    rep.to_csv(args.out_dir / "replay" / "replay_checks.csv", index=False)
    summary = {"checks": len(rep), "passed": int(rep["ok"].sum()), "failed": rep.loc[~rep["ok"], "check"].tolist(), "candidates_replayed": n_cand, "probe_rows": n_probe,
               "probe_rows_with_history_overrides": n_probe_ovr, "history_override_rows": int(len(ovr)), "run_mode": man.get("mode")}
    (args.out_dir / "replay" / "replay_summary.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))
    return 0 if rep["ok"].all() else 1


if __name__ == "__main__":
    sys.exit(main())
