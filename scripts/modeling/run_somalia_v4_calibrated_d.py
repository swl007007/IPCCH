#!/usr/bin/env python3
"""Somalia v4 calibrated D: original-only vs validity-expanded scenarios, 2022-2026 annual and pooled.

Each (setting, outer year, horizon, origin) selects its own recipe from 6 bundles x 4 decays x
direct/residual x none/shift/isotonic on origin-valid training-period OOF predictions.

Examples:
    PYTHONPATH=src python scripts/modeling/run_somalia_v4_calibrated_d.py --prepare-only --out-dir /tmp/somalia_v4_prepare
    PYTHONPATH=src python -u scripts/modeling/run_somalia_v4_calibrated_d.py --workers 12
    PYTHONPATH=src python -u scripts/modeling/run_somalia_v4_calibrated_d.py --workers 12 --pilot original:2024:0 --out-dir /tmp/somalia_v4_pilot
"""
from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing as mp
import subprocess
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from ipcch import paths
from ipcch.somalia_oracle import augexp as ax
from ipcch.somalia_oracle import data as sd
from ipcch.somalia_oracle import modeling as md
from ipcch.somalia_oracle import pipeline as pl
from ipcch.somalia_oracle import q3opt as qo

CONFIG_PATH = paths.CONFIG_DIR / "somalia_v4_calibrated_d.json"
DEFAULT_OUT = paths.RESULTS_DIR / "experiments" / "somalia_oracle" / "v4_calibrated_d"
DEFAULT_REPORT = paths.REPORTS_DIR / "somalia_oracle" / "v4_calibrated_d"


class V4Error(RuntimeError):
    """A v4 run-level contract does not hold."""


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--config", type=Path, default=CONFIG_PATH)
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    p.add_argument("--report-dir", type=Path, default=None, help="default: reports/somalia_oracle/v4_calibrated_d for the default out-dir, else <out-dir>/report")
    p.add_argument("--workers", type=int, default=1)
    p.add_argument("--prepare-only", action="store_true")
    p.add_argument("--skip-input-hash", action="store_true")
    p.add_argument("--pilot", action="append", default=[], help="restrict jobs to setting:year:horizon (repeatable); full recipe inventory per job")
    p.add_argument("--overwrite", action="store_true")
    for n in ("fs0", "fs1", "fs2", "fs3"):
        p.add_argument(f"--{n}-path", dest=f"{n}_path")
    return p.parse_args(argv)


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def run_pool(fn, tasks, workers, label):
    if not tasks:
        return []
    t0, out = time.time(), []
    if workers <= 1 or len(tasks) <= 1:
        for i, t in enumerate(tasks):
            out.append(fn(t))
    else:
        with ProcessPoolExecutor(max_workers=workers, mp_context=mp.get_context("fork")) as pool:
            for i, res in enumerate(pool.map(fn, tasks, chunksize=1)):
                out.append(res)
                if (i + 1) % max(1, len(tasks) // 20) == 0:
                    log(f"  {label}: {i + 1}/{len(tasks)} ({time.time() - t0:.0f}s)")
    log(f"{label}: {len(tasks)} done in {time.time() - t0:.0f}s")
    return out


def write(frame, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    return {"path": str(path), "rows": int(len(frame)), "sha256": sd.sha256_file(path)}


def load_config(path):
    cfg = json.loads(Path(path).read_text(encoding="utf-8"))
    bundle_path = Path(cfg["bundle_config"])
    bundle_path = bundle_path if bundle_path.is_absolute() else paths.PROJECT_ROOT / bundle_path
    if sd.sha256_file(bundle_path) != cfg["bundle_config_sha256"]:
        raise V4Error("tree bundle config does not match its pinned sha256")
    hl = [None if v is None else int(v) for v in cfg["half_life_months"]]
    if tuple(hl) != ax.V4_HALF_LIVES or tuple(cfg["calibration_methods"]) != qo.METHOD_ORDER or tuple(cfg["formulations"]) != qo.FORMULATION_ORDER:
        raise V4Error("declared search inventory drifted from the approved contract")
    bundles = md.load_candidates(bundle_path)  # validates the unchanged legacy file; only its tree/runtime dictionaries are used
    if len(ax.v4_candidates(bundles)) != int(cfg["declared_recipes_per_context"]):
        raise V4Error("recipe inventory is not the declared 144")
    if [None if v is None else int(v) for v in cfg["half_life_tie_order"]] != sorted(ax.V4_DECAY_ORDER, key=ax.V4_DECAY_ORDER.get):
        raise V4Error("half-life tie order drifted")
    return cfg, bundles, bundle_path


def check_runtime(cfg):
    rt = pl.runtime_identity()
    want = cfg["runtime"]
    got = {"python": rt["python"], "numpy": rt["numpy"], "pandas": rt["pandas"], "scikit_learn": rt["sklearn"], "xgboost": rt["xgboost"]}
    if got != want:
        raise V4Error(f"runtime {got} differs from the frozen {want}")
    return rt


def main(argv=None):
    args = parse_args(argv)
    out = args.out_dir
    report = args.report_dir or (DEFAULT_REPORT if out.resolve() == DEFAULT_OUT.resolve() else out / "report")
    if out.exists() and any(out.iterdir()) and not args.overwrite:
        raise SystemExit(f"{out} is not empty; pass --overwrite or use a new directory")
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    cfg, bundles, bundle_path = load_config(args.config)
    runtime = check_runtime(cfg)
    if args.workers > int(cfg["max_workers"]):
        raise V4Error(f"at most {cfg['max_workers']} workers")
    settings, years, horizons = list(cfg["data_settings"]), [int(y) for y in cfg["outer_years"]], [int(h) for h in cfg["horizons"]]
    if not args.skip_input_hash and sd.sha256_file(Path(cfg["inputs"]["v2"])) != cfg["climate_sha256"]:
        raise V4Error("climate source does not match its pinned sha256")
    inputs = pl.resolve_input_paths({**{n: getattr(args, f"{n}_path") for n in ("fs0", "fs1", "fs2", "fs3")}, "raw": cfg["inputs"]["raw"], "lookup": cfg["inputs"]["lookup"], "v2": cfg["inputs"]["v2"]})
    from ipcch.somalia_oracle import monthly_features as mf

    deep = mf.load_somalia_deep(sd.somalia_area_ids(pd.read_csv(inputs["lookup"])), Path(cfg["inputs"]["deep"]))
    log(f"deep monthly panel {deep.shape}")
    prep = ax.prepare(inputs, cfg, log=log, hash_inputs=not args.skip_input_hash, deep=deep, first_model_year=None, folds={})
    del deep
    hashes = dict(prep.input_hashes)
    hashes["deep"] = sd.sha256_file(Path(cfg["inputs"]["deep"])) if not args.skip_input_hash else "not_computed"
    written = {}
    ledger = prep.ledger
    written["label_ledger"] = write(ledger, out / "ledgers" / "label_ledger.csv.gz")
    written["augmentation_decisions"] = write(prep.decisions, out / "ledgers" / "augmentation_decisions.csv.gz")
    written["round_links"] = write(prep.links, out / "ledgers" / "round_links.csv")
    written["api_rounds"] = write(prep.rounds_api, out / "ledgers" / "api_rounds.csv")
    written["feature_parity"] = write(prep.parity, out / "ledgers" / "feature_parity.csv")
    written["label_diff_raw_vs_fs"] = write(prep.label_diff, out / "ledgers" / "label_diff_raw_vs_fs.csv.gz")
    fam = ledger.groupby("source_family").agg(n_rows=("target_ord", "size"), n_copies=("is_copy", "sum"), original_month_ord=("original_month_ord", "first"),
                                              n_original_months=("original_month_ord", "nunique")).reset_index()
    if (fam["n_original_months"] != 1).any():
        raise V4Error("a source family spans more than one original report month")
    written["source_families"] = write(fam, out / "ledgers" / "source_families.csv")
    support = ledger.assign(year=ledger["target_ord"] // 12).groupby(["year", "is_copy"]).agg(rows=("target_ord", "size"), valid_target=("valid_target", "sum"), valid_score=("valid_score", "sum"),
                                                                                               months=("target_ord", "nunique"), reports=("source_family", "nunique")).reset_index()
    written["label_support_by_year"] = write(support, out / "ledgers" / "label_support_by_year.csv")
    for h, f in prep.frames.items():
        keep = ["area_id", "target_ord", "origin_ord", "is_copy", "original_month_ord", "source_family", "source_available_ord", "history_cutoff_ord", "hist_q3_obs1", "history_obs1_source_ord",
                "oracle_all_verified", "v2_status", "v2_season_year", "v2_season", "v2_season_end_exclusive", "valid_score", "q3"]
        written[f"row_provenance_h{h:02d}"] = write(f[keep], out / "ledgers" / f"row_provenance_h{h:02d}.csv.gz")
        written[f"feature_matrix_h{h:02d}"] = write(f[["area_id", "target_ord", *prep.schemas[h]]], out / "features" / f"feature_matrix_h{h:02d}.csv.gz")
    (out / "features" / "feature_schema.json").write_text(json.dumps({f"h{h:02d}_D": c for h, c in prep.schemas.items()}, indent=1))

    cohort = ax.v4_freeze_cohorts(ledger, prep.frames, settings, years, horizons)
    written["cohort"] = write(cohort, out / "ledgers" / "cohort_ledger.csv.gz")
    slots = (cohort.groupby(["data_setting", "outer_year", "horizon", "status"]).size().unstack(fill_value=0).reset_index())
    slots["cohort_sha256"] = [ax.cohort_digest(cohort.loc[(cohort["data_setting"] == r.data_setting) & (cohort["outer_year"] == r.outer_year) & (cohort["horizon"] == r.horizon) & (cohort["status"] == "primary")])
                              for r in slots.itertuples(index=False)]
    written["cohort_slots"] = write(slots, out / "ledgers" / "cohort_slots.csv")
    jobs = ax.v4_jobs(cohort, prep.frames)
    if args.pilot:
        want = {tuple(p.split(":")) for p in args.pilot}
        jobs = jobs.loc[[(s, str(y), str(h)) in want for s, y, h in zip(jobs["data_setting"], jobs["outer_year"], jobs["horizon"])]].reset_index(drop=True)
        if jobs.empty:
            raise V4Error(f"pilot filter {args.pilot} selects no jobs")
    written["jobs"] = write(jobs, out / "ledgers" / "jobs.csv")
    n_copies = int(ledger["is_copy"].sum())
    manifest = {"experiment": "somalia_oracle_v4_calibrated_d", "task": "somalia-v4-calibrated-d",
                "git_head": subprocess.run(["git", "rev-parse", "HEAD"], cwd=paths.PROJECT_ROOT, capture_output=True, text=True).stdout.strip(),
                "git_dirty": subprocess.run(["git", "status", "--porcelain"], cwd=paths.PROJECT_ROOT, capture_output=True, text=True).stdout.splitlines(),
                "runtime": runtime, "inputs": {n: {"path": str(p), "sha256": hashes.get(n)} for n, p in {**inputs, "deep": Path(cfg["inputs"]["deep"])}.items()},
                "validity_snapshot": {"path": cfg["validity_snapshot"], "sha256": cfg["validity_snapshot_sha256"]}, "config_sha256": sd.sha256_file(args.config),
                "bundle_config": {"path": str(bundle_path), "sha256": cfg["bundle_config_sha256"]}, "pilot": args.pilot, "workers": args.workers,
                "earliest_supervised_year": int(ledger.loc[ledger["valid_target"], "target_ord"].min() // 12), "n_copies": n_copies,
                "copies_by_year": ledger.loc[ledger["is_copy"]].groupby(ledger["target_ord"] // 12).size().to_dict(), "notes": prep.notes}
    active = list(settings)
    if n_copies == 0:
        manifest["augmented_status"] = "augmentation_unavailable"
        active = [s for s in settings if s != "augmented"]
        jobs = jobs.loc[jobs["data_setting"] != "augmented"].reset_index(drop=True)
    # ---------------- contexts (frozen from label/pool support before any fit) ----------------
    pools = {(s, h): ax.PoolIndex(prep.frames[h], s, h) for s in active for h in horizons}
    contexts, ctx_rows, member_rows, cal_rows, final_cal_rows, spec_rows = {}, [], [], [], [], {}
    for job in jobs.to_dict("records"):
        s, y, h, o = job["data_setting"], job["outer_year"], job["horizon"], job["origin_ord"]
        ctx = ax.v4_plan_context(prep.frames[h], pools[(s, h)], s, y, h, o, [x for x in job["test_families"].split(";") if x], cfg)
        contexts[job["job_id"]] = ctx
        ctx_rows.append({"job_id": job["job_id"], "context_id": ctx.context_id, "selection_signature": ctx.selection_signature, "status": ctx.status, "reason": ctx.reason,
                         "data_setting": s, "outer_year": y, "horizon": h, "origin": sd.ord_label(o), "test_families": ";".join(ctx.test_families),
                         "rounds": ";".join(sd.ord_labels(ctx.rounds)), "scoring_rounds": ";".join(sd.ord_labels(ctx.scoring)), "n_scoring_keys": len(ctx.members),
                         "final_calibration_rounds": ";".join(sd.ord_labels(sorted(set(ctx.final_calibration["round"])))), "fit_spec_id": ctx.fit_spec.id if ctx.fit_spec else None,
                         "n_fit": int(pools[(s, h)].rows(ctx.fit_spec).size) if ctx.fit_spec else 0, "max_selection_label_ord": int(ctx.members["target_ord"].max()) if len(ctx.members) else None})
        f = prep.frames[h]
        for name, tab, store_to in (("members", ctx.members, member_rows), ("calibration", ctx.calibration, cal_rows), ("final_calibration", ctx.final_calibration, final_cal_rows)):
            if len(tab):
                store_to.append(tab.assign(job_id=job["job_id"], area_id=f["area_id"].to_numpy()[tab["row"].to_numpy()], is_copy=f["is_copy"].to_numpy()[tab["row"].to_numpy()]))
        for sid, sp in ctx.specs.items():
            if sid not in spec_rows:
                idx = pools[(s, h)].rows(sp)
                spec_rows[sid] = {**sp.describe(), "n_pool": int(idx.size), "pool_keys_sha256": ax.pool_hash(idx, f) if idx.size else None,
                                  "pool_max_target_ord": int(f["target_ord"].to_numpy()[idx].max()) if idx.size else None,
                                  "pool_max_source_available_ord": int(f["source_available_ord"].to_numpy()[idx].max()) if idx.size else None,
                                  "pool_n_copies": int(f["is_copy"].to_numpy()[idx].sum()) if idx.size else 0}
    ctx_table = pd.DataFrame(ctx_rows)
    written["contexts"] = write(ctx_table, out / "selection" / "contexts.csv")
    cat = lambda xs: pd.concat(xs, ignore_index=True) if xs else pd.DataFrame()
    written["scoring_keys"] = write(cat(member_rows), out / "selection" / "scoring_keys.csv.gz")
    written["calibration_keys"] = write(cat(cal_rows), out / "selection" / "calibration_keys.csv.gz")
    written["final_calibration_keys"] = write(cat(final_cal_rows), out / "selection" / "final_calibration_keys.csv.gz")
    written["pool_specs"] = write(pd.DataFrame(list(spec_rows.values())), out / "selection" / "pool_specs.csv.gz")
    log(f"jobs {len(jobs)}; contexts ok {int((ctx_table['status'] == 'ok').sum())}; unique selection signatures {ctx_table['selection_signature'].nunique()}; pool specs {len(spec_rows)}")

    # ---------------- OOF units: every declared recipe on every needed spec ----------------
    requests = {}
    for job_id, ctx in contexts.items():
        if ctx.status != "ok":
            continue
        need = pd.concat([ctx.members[["row", "spec_id"]], ctx.calibration[["row", "spec_id"]], ctx.final_calibration[["row", "spec_id"]]], ignore_index=True)
        for sid, g in need.groupby("spec_id"):
            for b in [c["id"] for c in bundles["candidates"]]:
                for hl in ax.V4_HALF_LIVES:
                    for form in ax.FORMULATIONS:
                        key = ax.v4_unit_key(sid, form, b, hl)
                        req = requests.setdefault(key, {"spec": ctx.specs[sid], "rows": set()})
                        req["rows"].update(int(r) for r in g["row"])
    tasks = []
    store = ax.V4UnitStore()
    for key, req in requests.items():
        sp = req["spec"]
        fit_idx = pools[(sp.setting, sp.horizon)].rows(sp)
        pred_idx = np.array(sorted(req["rows"]), dtype=np.int64)
        t = {"key": key, "horizon": sp.horizon, "formulation": key[1], "bundle": key[2], "half_life": key[3], "fit_idx": fit_idx, "pred_idx": pred_idx, "weight_origin": sp.available_by}
        if fit_idx.size == 0:
            store.add({"key": key, "status": "unsupported", "pred_idx": pred_idx, "raw_q3": np.full(pred_idx.size, np.nan), "n_fit": 0, "n_fit_used": 0, "fit_max_target_ord": None, "model_kind": None, "sum_weight": 0.0, "min_weight": np.nan})
            continue
        if int(prep.frames[sp.horizon]["target_ord"].to_numpy()[fit_idx].max()) > sp.label_cutoff or int(prep.frames[sp.horizon]["source_available_ord"].to_numpy()[fit_idx].max()) > sp.available_by:
            raise V4Error("a unit pool violates its own cutoff")
        tasks.append(t)
    tasks.sort(key=lambda t: -t["fit_idx"].size * (2 if t["bundle"] in ("X3", "X5") else 1))  # longest first
    log(f"OOF units: {len(requests)} requested, {len(tasks)} to fit")
    inv = pd.DataFrame([{"setting": req["spec"].setting, "horizon": req["spec"].horizon, "formulation": k[1], "bundle": k[2], "half_life": k[3], "n_pool": int(pools[(req["spec"].setting, req["spec"].horizon)].rows(req["spec"]).size),
                         "n_pred": len(req["rows"])} for k, req in requests.items()])
    if len(inv):
        written["unit_inventory"] = write(inv.groupby(["setting", "horizon", "formulation"]).agg(units=("n_pool", "size"), empty_pools=("n_pool", lambda x: int((x == 0).sum())), mean_pool=("n_pool", "mean"),
                                                                                               max_pool=("n_pool", "max"), pred_rows=("n_pred", "sum")).reset_index(), out / "selection" / "unit_inventory.csv")
    if args.prepare_only:
        manifest.update(mode="prepare_only", written=written, elapsed_seconds=time.time() - t0, n_oof_units=len(requests), n_oof_fits=len(tasks))
        (out / "manifest.json").write_text(json.dumps(manifest, indent=1, default=str))
        log("prepare-only done (inputs, cohorts, contexts and fit inventory frozen; no model fitted)")
        return 0
    ax.init_state(prep, bundles)
    for res in run_pool(ax.v4_unit_task, tasks, args.workers, "OOF units"):
        store.add(res)
    unit_rows, oof_parts = [], []
    for key, u in store.units.items():
        sp = requests[key]["spec"]
        f = prep.frames[sp.horizon]
        unit_rows.append({"unit_id": ax.v4_unit_id(key), "spec_id": key[0], "formulation": key[1], "bundle": key[2], "half_life": key[3], "setting": sp.setting, "horizon": sp.horizon,
                          "weight_origin_ord": sp.available_by, "status": u["status"], **{k: u[k] for k in ("n_fit", "n_fit_used", "fit_max_target_ord", "model_kind", "sum_weight", "min_weight")}, "n_pred": int(u["rows"].size)})
        oof_parts.append(pd.DataFrame({"unit_id": ax.v4_unit_id(key), "area_id": f["area_id"].to_numpy()[u["rows"]], "target_ord": f["target_ord"].to_numpy()[u["rows"]], "raw_q3": u["raw"]}))
    written["oof_units"] = write(pd.DataFrame(unit_rows), out / "selection" / "oof_units.csv.gz")
    written["oof_predictions"] = write(cat(oof_parts), out / "selection" / "oof_predictions.csv.gz")
    del oof_parts

    # ---------------- selection per unique frozen context ----------------
    tol = float(cfg["tie_tolerance"])
    by_sig, score_tables, sel_pred_parts, sel_rows = {}, [], [], []
    for job_id, ctx in contexts.items():
        sig = ctx.selection_signature
        if ctx.status != "ok" or sig in by_sig:
            continue
        scores, preds = ax.v4_score_context(store, prep.frames[ctx.horizon], ctx, bundles, cfg)
        best, tie = qo.select_candidate(scores, tol, True, extra_order=["decay_order"])
        by_sig[sig] = best
        score_tables.append(scores.assign(first_job_id=job_id))
        if best is not None:
            key = (best["bundle"], best["half_life"], best["formulation"], best["method"])
            p = preds[key]
            f = prep.frames[ctx.horizon]
            sel_pred_parts.append(p.assign(selection_signature=sig, area_id=f["area_id"].to_numpy()[p["row"].to_numpy()], is_copy=f["is_copy"].to_numpy()[p["row"].to_numpy()],
                                           q3=f["q3"].to_numpy()[p["row"].to_numpy()], actual_crisis=f["actual_crisis"].to_numpy()[p["row"].to_numpy()]))
        n_ok = int((scores["status"] == "ok").sum())
        log(f"select {ctx.context_id} [{sig}]: {n_ok}/144 supported -> " + ("none" if best is None else f"{best['formulation']} {best['bundle']} hl={best['half_life']} {best['method']} rmse={best['rmse']:.5f} tie={len(tie)}"))
    for job_id, ctx in contexts.items():
        best = by_sig.get(ctx.selection_signature) if ctx.status == "ok" else None
        sel_rows.append({"job_id": job_id, "context_id": ctx.context_id, "selection_signature": ctx.selection_signature, "data_setting": ctx.setting, "outer_year": ctx.year, "horizon": ctx.horizon,
                         "origin": sd.ord_label(ctx.origin), "status": "ok" if best is not None else "unsupported", "reason": ctx.reason if ctx.status != "ok" else (None if best is not None else "no supported candidate"),
                         **({} if best is None else {k: best[k] for k in ("formulation", "bundle", "half_life", "method", "rmse", "auc", "n")}),
                         "selection_max_scoring_ord": int(ctx.members["target_ord"].max()) if len(ctx.members) else None,
                         "selection_labels_after_origin": bool(len(ctx.members) and int(ctx.members["target_ord"].max()) > ctx.origin)})
    selected = pd.DataFrame(sel_rows)
    if selected["selection_labels_after_origin"].any():
        raise V4Error("a selection context scored labels after its outer origin")
    written["candidate_scores"] = write(cat(score_tables), out / "selection" / "candidate_scores.csv")
    written["selected_scoring_predictions"] = write(cat(sel_pred_parts), out / "selection" / "selected_scoring_predictions.csv.gz")
    written["selected_recipes"] = write(selected, out / "selection" / "selected_recipes.csv")

    # ---------------- final mappings and fits ----------------
    cohort_prim = cohort.loc[cohort["status"] == "primary"]
    ftasks, meta, map_rows = [], {}, []
    for job in jobs.to_dict("records"):
        ctx = contexts[job["job_id"]]
        rec = selected.loc[selected["job_id"] == job["job_id"]].iloc[0]
        if rec["status"] != "ok":
            continue
        h = job["horizon"]
        f = prep.frames[h]
        keys = cohort_prim.loc[(cohort_prim["data_setting"] == job["data_setting"]) & (cohort_prim["outer_year"] == job["outer_year"]) & (cohort_prim["horizon"] == h)
                               & (cohort_prim["target_ord"] - h == job["origin_ord"]), ["area_id", "target_ord"]]
        rowmap = pd.Series(np.arange(len(f)), index=pd.MultiIndex.from_arrays([f["area_id"].to_numpy(), f["target_ord"].to_numpy()]))
        pred_idx = rowmap.reindex(pd.MultiIndex.from_frame(keys)).to_numpy()
        if np.isnan(pred_idx.astype(float)).any():
            raise V4Error(f"{job['job_id']}: frozen test keys absent from the feature frame")
        pred_idx = pred_idx.astype(np.int64)
        fit_idx = pools[(job["data_setting"], h)].rows(ctx.fit_spec)
        if np.isin(f["source_family"].to_numpy()[fit_idx], list(ctx.test_families)).any():
            raise V4Error(f"{job['job_id']}: a test family entered its outer fitting pool")
        hl = ax.parse_half_life(rec["half_life"])
        maps = ax.v4_fit_mappings(store, f, ctx.final_calibration, rec["formulation"], rec["bundle"], hl, rec["method"], int(cfg["min_calibration_rounds"]))
        key = job["job_id"]
        meta[key] = {"job_id": key, "data_setting": job["data_setting"], "outer_year": job["outer_year"], "horizon": h, "origin": sd.ord_label(job["origin_ord"]), "context_id": ctx.context_id,
                     "selection_signature": ctx.selection_signature, "formulation": rec["formulation"], "bundle": rec["bundle"], "half_life": rec["half_life"], "method": rec["method"],
                     "fit_spec_id": ctx.fit_spec.id, "n_fit": int(fit_idx.size), "n_fit_copies": int(f["is_copy"].to_numpy()[fit_idx].sum()),
                     "fit_max_target_ord": int(f["target_ord"].to_numpy()[fit_idx].max()), "fit_max_source_available_ord": int(f["source_available_ord"].to_numpy()[fit_idx].max())}
        map_rows += [{"job_id": key, "prediction_branch": n, **m.describe()} for n, m in maps.items()]
        ftasks.append({"key": key, "horizon": h, "formulation": rec["formulation"], "bundle": rec["bundle"], "half_life": rec["half_life"], "origin_ord": job["origin_ord"], "fit_idx": fit_idx, "pred_idx": pred_idx, "mappings": maps})
    results = run_pool(ax.v4_final_task, ftasks, args.workers, "final fits")
    preds, fits, status_rows, model_rows = [], [], [], []
    mdir = out / "models"
    mdir.mkdir(parents=True, exist_ok=True)
    for t, res in zip(ftasks, results):
        m = meta[t["key"]]
        status_rows.append({**m, "status": res["status"], "reason": res.get("reason"), "calibration_status": res.get("calibration_status"), "calibration_reason": res.get("calibration_reason")})
        preds.append(res["predictions"].assign(**{k: m[k] for k in ("job_id", "data_setting", "outer_year", "horizon", "formulation", "bundle", "half_life", "method")}, calibration_status=res["calibration_status"]))
        fits.append(res["fit_ledger"].assign(job_id=m["job_id"]))
        for target, model in res["models"].items():
            if model is None:
                continue
            stem = mdir / f"{m['job_id']}_{target}"
            if model.kind == "xgboost":
                path = stem.with_suffix(".ubj")
                model.model.save_model(str(path))
            else:
                path = stem.with_suffix(".json")
                path.write_text(json.dumps({"kind": "constant", "value": model.constant, "n_rows": model.n_rows}))
            model_rows.append({"job_id": m["job_id"], "target": target, "kind": model.kind, "path": path.name, "sha256": sd.sha256_file(path),
                               "feature_order_sha256": hashlib.sha256("\n".join(prep.schemas[m["horizon"]]).encode()).hexdigest()})
    status_cols = ["job_id", "status", "reason", "calibration_status", "calibration_reason"]
    preds = cat(preds)
    if preds.empty:
        preds = pd.DataFrame(columns=["area_id", "target_ord", "q3_raw", "q3_final", "clipped", "prediction_branch", "job_id", "data_setting", "outer_year", "horizon"])
    written["final_predictions"] = write(preds, out / "predictions" / "final_predictions.csv.gz")
    written["final_status"] = write(pd.DataFrame(status_rows, columns=None if status_rows else status_cols), out / "fits" / "final_status.csv")
    written["fit_ledger"] = write(cat(fits), out / "fits" / "final_fit_ledger.csv.gz")
    written["calibration_mappings"] = write(pd.DataFrame(map_rows), out / "fits" / "calibration_mappings.csv")
    written["model_inventory"] = write(pd.DataFrame(model_rows), out / "models" / "model_inventory.csv")

    # ---------------- annual and pooled evaluation ----------------
    annual, pooled = ax.v4_evaluate(cohort, preds, prep.frames, active, years, horizons)
    if args.pilot:
        annual = annual.loc[[(s, str(y), str(h)) in {tuple(p.split(":")) for p in args.pilot} for s, y, h in zip(annual["data_setting"], annual["outer_year"], annual["horizon"])]]
        pooled = pooled.iloc[0:0]
    written["annual_metrics"] = write(annual, out / "metrics" / "annual_metrics.csv")
    written["pooled_metrics"] = write(pooled, out / "metrics" / "pooled_metrics.csv")
    manifest.update(mode="pilot" if args.pilot else "full", elapsed_seconds=time.time() - t0, written=written, n_oof_units=len(requests), n_oof_fits=len(tasks))
    report.mkdir(parents=True, exist_ok=True)
    write_report(annual, pooled, selected, cohort, manifest, report / "summary.md")
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1, default=str))
    log(f"done in {manifest['elapsed_seconds']:.0f}s")
    return 0


def _f(v, d=3):
    return "—" if v is None or (isinstance(v, float) and not np.isfinite(v)) else f"{v:.{d}f}"


def write_report(annual, pooled, selected, cohort, manifest, path):
    lines = ["# Somalia v4 calibrated D — results", "",
             f"Code `{manifest['git_head']}`; mode `{manifest['mode']}`. Two distinct label scenarios, each evaluated on its own population: **original** uses observed raw labels only in every role (fit, selection, calibration, test); **augmented** also admits permitted validity-period copies in every role. Score differences between the settings are not augmentation effects and are not ranked. Each (setting, outer year, horizon, origin) selected its own recipe from 6 bundles × 4 half-lives × direct/residual × none/shift/isotonic by pooled training-period OOF final-q3 RMSE (AUC only breaks numerical ties). Retrospective oracle-information evaluation (ideal label availability, realized future weather); not operational forecast skill.", "",
             f"Copies admitted to the augmented scenario: {manifest['n_copies']} ({', '.join(f'{y}: {n}' for y, n in manifest['copies_by_year'].items())}). Earliest supervised label year: {manifest['earliest_supervised_year']}.", ""]
    for setting in sorted(set(annual["data_setting"])):
        lines += [f"## {setting}: annual (each year's own frozen cohort)", "", "| Year | H | Status | n (copies) | Final R² | Raw R² | RMSE (pp) | MAE (pp) | Bias (pp) | Final AUC | F1 | Precision | Recall |", "|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
        for r in annual.loc[annual["data_setting"] == setting].sort_values(["horizon", "outer_year"]).to_dict("records"):
            if r["status"] != "complete":
                lines.append(f"| {r['outer_year']} | {r['horizon']} | {r['status']}: {r.get('reason')} | {r.get('n_primary', 0)} | | | | | | | | | |")
                continue
            lines.append(f"| {r['outer_year']} | {r['horizon']} | complete | {r['n']} ({r['n_copies']}) | {_f(r['final_r2'])} | {_f(r['raw_r2'])} | {_f(r['final_rmse'] * 100, 2)} | {_f(r['final_mae'] * 100, 2)} | {_f(r['final_bias'] * 100, 2)} | {_f(r['final_auc'])} | {_f(r['bin_f1'])} | {_f(r['bin_precision'])} | {_f(r['bin_recall'])} |")
        lines += ["", f"## {setting}: pooled 2022-2026 (concatenated annual out-of-sample rows, equal weight per area-month)", "", "| H | Status | Rows by year | n (copies) | Final R² | Raw R² | RMSE (pp) | Bias (pp) | Final AUC | F1 | Precision | Recall |", "|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
        for r in pooled.loc[pooled["data_setting"] == setting].sort_values("horizon").to_dict("records"):
            if r["status"] != "complete":
                lines.append(f"| {r['horizon']} | {r['status']}: {r.get('reason')} | | | | | | | | | | |")
                continue
            lines.append(f"| {r['horizon']} | complete | {r['rows_by_year']} | {r['n']} ({r['n_copies']}) | {_f(r['final_r2'])} | {_f(r['raw_r2'])} | {_f(r['final_rmse'] * 100, 2)} | {_f(r['final_bias'] * 100, 2)} | {_f(r['final_auc'])} | {_f(r['bin_f1'])} | {_f(r['bin_precision'])} | {_f(r['bin_recall'])} |")
        lines.append("")
    lines += ["## Selected recipes (per job)", "", "| Job | Status | Formulation | Bundle | Half-life | Calibration | Validation RMSE | Validation AUC |", "|---|---|---|---|---|---|---:|---:|"]
    for r in selected.sort_values(["data_setting", "horizon", "outer_year", "origin"]).to_dict("records"):
        lines.append(f"| {r['job_id']} | {r['status']}{'' if r['status'] == 'ok' else ': ' + str(r.get('reason'))} | {r.get('formulation', '—')} | {r.get('bundle', '—')} | {r.get('half_life', '—')} | {r.get('method', '—')} | {_f(r.get('rmse', np.nan), 5)} | {_f(r.get('auc', np.nan))} |")
    lines += ["", "Selection minimizes final-q3 RMSE; crisis AUC and fixed-threshold (q3 ≥ 0.2) F1/recall can move in either direction and are reported, not optimized. Augmented pooled labels include repeated monthly validity truth from one assessment, not independent monthly observations. Undefined R²/AUC are shown as —. No bootstrap intervals or cross-setting contrasts are produced by design."]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
