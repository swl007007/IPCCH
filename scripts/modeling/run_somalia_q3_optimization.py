#!/usr/bin/env python3
"""q3-first Somalia optimization: H0 selection by held-out final-q3 RMSE; H3/H6/H12 fixed-recipe refits.

Examples:
    PYTHONPATH=src python scripts/modeling/run_somalia_q3_optimization.py --prepare-only
    PYTHONPATH=src python -u scripts/modeling/run_somalia_q3_optimization.py --workers 14 --overwrite
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
from typing import Dict, List

import numpy as np
import pandas as pd

from ipcch import paths
from ipcch.somalia_oracle import FOLDS, HORIZONS
from ipcch.somalia_oracle import data as sd
from ipcch.somalia_oracle import pipeline as pl
from ipcch.somalia_oracle import q3eval as qe
from ipcch.somalia_oracle import q3opt as qo

DEFAULT_OUT = paths.RESULTS_DIR / "experiments" / "somalia_oracle" / "v2_q3"
DEFAULT_REPORT = paths.REPORTS_DIR / "somalia_oracle" / "v2_q3"
V1_DIR = paths.RESULTS_DIR / "experiments" / "somalia_oracle" / "v1"
MODEL_VIEWS = ("A", "B", "C", "D_direct", "D_residual")


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--v1-dir", type=Path, default=V1_DIR)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--only-horizon", type=int, choices=HORIZONS, action="append", help="Restrict receiving horizons (H0 selection always runs).")
    parser.add_argument("--skip-input-hash", action="store_true")
    parser.add_argument("--no-v1-check", action="store_true", help="Skip the cohort-ledger identity gate against v1 (synthetic runs only).")
    parser.add_argument("--config", type=Path, default=qo.CONFIG_PATH)
    parser.add_argument("--overwrite", action="store_true")
    for name in ("fs0", "fs1", "fs2", "fs3", "raw", "lookup", "v2"):
        parser.add_argument(f"--{name}-path", dest=f"{name}_path")
    return parser.parse_args(argv)


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def run_pool(fn, tasks, workers):
    if workers <= 1 or len(tasks) <= 1:
        return [fn(t) for t in tasks]
    with ProcessPoolExecutor(max_workers=workers, mp_context=mp.get_context("fork")) as pool:
        return list(pool.map(fn, tasks, chunksize=1))


def write(frame: pd.DataFrame, path: Path) -> Dict[str, object]:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    return {"path": str(path), "rows": int(len(frame)), "sha256": sd.sha256_file(path)}


def fold_pool_check(prepared, year, window):
    """All H0 jobs of a fold must share one clipped pool (implement.md decision 1)."""
    frame = prepared.frames[0]
    jobs = prepared.jobs.loc[(prepared.jobs["horizon"] == 0) & (prepared.jobs["test_year"] == year)]
    pools = {tuple(np.flatnonzero((frame["target_year"].isin(window) & (frame["target_ord"] <= o)).to_numpy())) for o in jobs["origin_ord"]}
    if len(pools) != 1:
        raise qo.Q3OptError(f"H0 jobs of fold {year} do not share one training pool; per-job selection required")
    return int(frame.loc[frame["target_year"].isin(window), "target_ord"].max())


def recipe_arm_form(view, recipe):
    if view == "D_selected":
        return "D", recipe["formulation"]
    return qo.VIEW_SPEC[view]


def reuse_source(view, recipe, per_view, horizon):
    """A view whose fixed recipe equals an already-fitted formulation view's recipe reuses its fits."""
    if view != "D_selected":
        return None
    src = "D_residual" if recipe["formulation"] == "residual" else "D_direct"
    other = per_view.get(src)
    if other is not None and (other["bundle"], other["method"], other["formulation"]) == (recipe["bundle"], recipe["method"], recipe["formulation"]):
        return src
    return None


def save_models(res, task, model_dir, feature_order):
    """Persist every final regressor (XGBoost UBJSON or constant JSON) with a hash inventory."""
    model_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for target, model in res["models"].items():
        if model is None:
            continue
        stem = model_dir / f"{task['job_id']}_{task['view']}_{target}"
        if model.kind == "xgboost":
            path = stem.with_suffix(".ubj")
            model.model.save_model(str(path))
        else:
            path = stem.with_suffix(".json")
            path.write_text(json.dumps({"kind": "constant", "value": model.constant, "n_rows": model.n_rows}), encoding="utf-8")
        rows.append({"job_id": task["job_id"], "view": task["view"], "target": target, "bundle": task["bundle"], "kind": model.kind, "n_rows": model.n_rows,
                     "path": path.name, "sha256": sd.sha256_file(path), "feature_order_sha256": hashlib.sha256("\n".join(feature_order).encode()).hexdigest()})
    return rows


def oof_tasks(scope, horizon, window, arm_forms, months):
    tasks = []
    for arm, formulation in arm_forms:
        for bundle in [c["id"] for c in qo._STATE["bundles"]["candidates"]]:
            for v in months:
                tasks.append({"scope": scope, "horizon": horizon, "arm": arm, "formulation": formulation, "bundle": bundle, "v": int(v), "window": list(window)})
    return tasks


def main(argv=None):
    args = parse_args(argv)
    out, report = args.out_dir, args.report_dir
    if out.exists() and any(out.iterdir()) and not args.overwrite:
        raise SystemExit(f"{out} is not empty; pass --overwrite")
    out.mkdir(parents=True, exist_ok=True)
    started = time.time()
    cfg, bundles = qo.load_config(args.config)
    overrides = {n: getattr(args, f"{n}_path") for n in ("fs0", "fs1", "fs2", "fs3", "raw", "lookup", "v2")}
    input_paths = pl.resolve_input_paths(overrides)
    prepared = pl.prepare(input_paths, log=log, hash_inputs=not args.skip_input_hash)
    written = {"cohort_ledger": write(prepared.cohort_ledger, out / "ledgers" / "cohort_ledger.csv.gz")}
    written["label_ledger"] = write(prepared.ledger[["area_id", "target_ord", "overall_phase", "valid_score", "actual_crisis", "q2", "q3", "q4", "q5"]], out / "ledgers" / "label_ledger.csv.gz")
    for h, f in prepared.frames.items():
        written[f"row_provenance_h{h:02d}"] = write(f[["area_id", "target_ord", "origin_ord", "hist_q3_obs1", "history_obs1_source_ord"]], out / "ledgers" / f"row_provenance_h{h:02d}.csv.gz")
        written[f"feature_matrix_h{h:02d}"] = write(f[["area_id", "target_ord", *prepared.schemas[(h, "D")]]], out / "features" / f"feature_matrix_h{h:02d}.csv.gz")
    (out / "features" / "feature_schema.json").write_text(json.dumps({f"h{h:02d}_{a}": c for (h, a), c in prepared.schemas.items()}, indent=1))
    if not args.no_v1_check:
        v1 = pd.read_csv(args.v1_dir / "ledgers" / "cohort_ledger.csv.gz")
        mine = prepared.cohort_ledger.reset_index(drop=True)
        if not v1[mine.columns].equals(mine.astype(v1[mine.columns].dtypes.to_dict())):
            raise qo.Q3OptError("prepared cohort ledger differs from v1; stop per implement.md gate")
        log("cohort ledger identical to v1")
    manifest = {
        "experiment": "somalia_oracle_v2_q3",
        "task": "somalia-auc-r2-optimization",
        "git_head": subprocess.run(["git", "rev-parse", "HEAD"], cwd=paths.PROJECT_ROOT, capture_output=True, text=True).stdout.strip(),
        "git_dirty": subprocess.run(["git", "status", "--porcelain"], cwd=paths.PROJECT_ROOT, capture_output=True, text=True).stdout.splitlines(),
        "runtime": pl.runtime_identity(),
        "inputs": {n: {"path": str(p), "sha256": prepared.input_hashes[n]} for n, p in input_paths.items()},
        "config": {"path": str(args.config), "sha256": sd.sha256_file(args.config)},
        "bundle_config": {"path": cfg["_bundle_path"], "sha256": cfg["bundle_config_sha256"]},
    }
    if args.prepare_only:
        manifest["mode"] = "prepare_only"
        manifest["written"] = written
        (out / "manifest.json").write_text(json.dumps(manifest, indent=1, default=str))
        log("prepare-only done")
        return 0

    qo.init_state(prepared.frames, prepared.schemas, cfg, bundles)
    store = qo.OOFStore()
    tol = float(cfg["tie_tolerance"])

    # ---------------- H0 selection per fold ----------------
    plans, selections, score_tables, score_preds, plan_rows = {}, {}, [], [], []
    for year, window in FOLDS.items():
        window = list(window)
        cutoff = fold_pool_check(prepared, year, window)
        plan = qo.selection_plan(prepared.frames[0], window, 0, cutoff, cfg)
        plans[year] = plan
        for v in plan["scoring"]:
            plan_rows.append({"test_year": year, "scoring_month": sd.ord_label(v), "calibration_months": ";".join(sd.ord_labels(plan["calibration"][v]))})
        plan_rows.append({"test_year": year, "scoring_month": "FINAL_MAPPING", "calibration_months": ";".join(sd.ord_labels(plan["final"]))})
        if plan["status"] != "ok":
            raise qo.Q3OptError(f"fold {year}: fewer than {cfg['min_scoring_months']} scoring months")
    write(pd.DataFrame(plan_rows), out / "selection" / "scoring_plan.csv")  # frozen before any score
    tasks = []
    for year, window in FOLDS.items():
        tasks += oof_tasks(year, 0, window, [("A", "direct"), ("B", "direct"), ("D", "direct"), ("D", "residual")], plans[year]["needed"])
    log(f"H0 OOF fits: {len(tasks)}")
    for r in run_pool(qo.oof_task, tasks, args.workers):
        store.add(r)
    log("H0 OOF done")
    for year in FOLDS:
        frame = prepared.frames[0]
        per_view = {}
        for view in qo.H0_SEARCH_VIEWS:
            scores, preds = qo.score_candidates(store, frame, plans[year], year, 0, view, cfg)
            scores["test_year"] = year
            score_tables.append(scores)
            if len(preds):
                score_preds.append(preds.assign(test_year=year))
            crisis = np.concatenate([frame.loc[(frame["target_ord"] == v) & frame["valid_score"], "actual_crisis"].to_numpy() for v in plans[year]["scoring"]])
            best, _ = qo.select_candidate(scores, tol, np.unique(crisis).size == 2)
            per_view[view] = best
        d_all = pd.concat([s for s in score_tables if s["test_year"].iloc[0] == year and s["view"].iloc[0] in ("D_direct", "D_residual")])
        best_d, _ = qo.select_candidate(d_all, tol, np.unique(crisis).size == 2)
        per_view["C"] = per_view["B"]
        # D_selected keeps the exact globally selected D recipe (formulation, bundle, method).
        per_view["D_selected"] = best_d
        selections[year] = per_view
        for view, row in per_view.items():
            log(f"fold {year} {view}: " + ("unsupported" if row is None else f"{row['formulation']} {row['bundle']} {row['method']} rmse={row['rmse']:.5f}"))
    scores_all = pd.concat(score_tables, ignore_index=True)
    written["candidate_scores"] = write(scores_all, out / "selection" / "candidate_scores.csv")
    if score_preds:
        written["scoring_predictions"] = write(pd.concat(score_preds, ignore_index=True), out / "selection" / "scoring_predictions.csv.gz")
    sel_rows = []
    for year, per_view in selections.items():
        for view, row in per_view.items():
            sel_rows.append({"test_year": year, "view": view, "status": "ok" if row is not None else "unsupported", **({} if row is None else {k: row[k] for k in ("formulation", "bundle", "method", "rmse", "auc", "n")}), "selection_max_label": sd.ord_label(max(plans[year]["scoring"])), "reused_from": "B" if view == "C" else None})
    written["selected_recipes"] = write(pd.DataFrame(sel_rows), out / "selection" / "selected_recipes.csv")

    # ---------------- receiving plans and their OOF fits ----------------
    receiving = []
    horizons = sorted(set(args.only_horizon or HORIZONS) | {0})
    for job in prepared.jobs.to_dict("records"):
        if job["horizon"] not in horizons:
            continue
        year, h = job["test_year"], job["horizon"]
        window = list(FOLDS[year])
        rplan = qo.receiving_plan(prepared.frames[h], window, h, job["origin_ord"], cfg) if h > 0 else {"final": plans[year]["final"]}
        for view in (*MODEL_VIEWS, "D_selected"):
            recipe = selections[year][qo.RECIPE_SOURCE.get(view, view) if h > 0 else view]
            receiving.append({"job": job, "view": view, "recipe": recipe, "months": rplan["final"]})
    need = {}
    for item in receiving:
        h = item["job"]["horizon"]
        if h == 0 or item["recipe"] is None or item["recipe"]["method"] == "none":
            continue
        arm, formulation = recipe_arm_form(item["view"], item["recipe"])
        forms = [("direct",), ("direct", "residual")][formulation == "residual"]
        for f in forms:
            for v in item["months"]:
                need[(item["job"]["test_year"], h, arm, f, item["recipe"]["bundle"], int(v))] = list(FOLDS[item["job"]["test_year"]])
    rtasks = [{"scope": k[0], "horizon": k[1], "arm": k[2], "formulation": k[3], "bundle": k[4], "v": k[5], "window": w} for k, w in need.items()]
    log(f"receiving-horizon OOF fits (mapping refits only): {len(rtasks)}")
    for r in run_pool(qo.oof_task, rtasks, args.workers):
        store.add(r)
    written["oof_ledger"] = write(pd.DataFrame(store.ledger), out / "selection" / "oof_fit_ledger.csv")
    oof_rows = []
    for (scope, h, arm, form, bundle, v), (idx, raw) in store.data.items():
        f = prepared.frames[h]
        oof_rows.append(pd.DataFrame({"scope": scope, "horizon": h, "arm": arm, "formulation": form, "bundle": bundle, "v": v, "row": idx,
                                      "area_id": f["area_id"].to_numpy()[idx], "target_ord": f["target_ord"].to_numpy()[idx], "raw_q3": raw}))
    written["oof_predictions"] = write(pd.concat(oof_rows, ignore_index=True), out / "selection" / "oof_predictions.csv.gz")

    # ---------------- final fits ----------------
    ftasks, skipped = [], []
    for item in receiving:
        job, view, recipe = item["job"], item["view"], item["recipe"]
        h, year = job["horizon"], job["test_year"]
        base = {"job_id": job["job_id"], "view": view, "horizon": h, "test_year": year}
        if recipe is None:
            skipped.append({**base, "status": "unavailable", "reason": "H0 recipe unavailable"})
            continue
        if h == 0 and view == "C":
            continue  # reused from B below
        src = reuse_source(view, recipe, selections[year], h)
        if src is not None:
            continue  # identical recipe already fitted under another view; reused below
        arm, formulation = recipe_arm_form(view, recipe)
        frame = prepared.frames[h]
        mappings = qo.fit_branch_mappings(store, frame, year, h, arm, formulation, recipe["bundle"], recipe["method"], item["months"], cfg)
        ftasks.append({**base, "arm": arm, "formulation": formulation, "bundle": recipe["bundle"], "method": recipe["method"], "window": list(FOLDS[year]), "origin_ord": job["origin_ord"], "mappings": mappings,
                       "recipe_selection_max_label_ord": int(max(plans[year]["scoring"])), "mapping_months": list(item["months"])})
    log(f"final fits: {len(ftasks)}")
    finals = run_pool(qo.final_task, ftasks, args.workers)
    pred_parts, mapping_rows, status_rows, fit_parts, model_rows = [], [], list(skipped), [], []
    for task, res in zip(ftasks, finals):
        meta = {"job_id": task["job_id"], "view": task["view"], "horizon": task["horizon"], "test_year": task["test_year"], "formulation": task["formulation"], "bundle": task["bundle"], "method": task["method"],
                "recipe_source_view": qo.RECIPE_SOURCE.get(task["view"], task["view"]) if task["horizon"] > 0 else task["view"], "recipe_selection_max_label": sd.ord_label(task["recipe_selection_max_label_ord"]),
                "receiving_origin": sd.ord_label(task["origin_ord"]), "selection_uses_later_labels": bool(task["recipe_selection_max_label_ord"] > task["origin_ord"]), "mapping_months": ";".join(sd.ord_labels(task["mapping_months"]))}
        status_rows.append({**meta, "status": res["status"], "reason": res.get("reason"), "calibration_status": res.get("calibration_status"), "calibration_reason": res.get("calibration_reason")})
        if res["status"] != "completed":
            continue
        pred_parts.append(res["predictions"].assign(**{k: meta[k] for k in ("job_id", "view", "horizon", "test_year")}, calibration_status=res["calibration_status"]))
        model_rows.extend(save_models(res, task, out / "models", prepared.schemas[(task["horizon"], task["arm"])]))
        mapping_rows += res["mappings"]
        fit_parts.append(res["fit_ledger"].assign(job_id=task["job_id"], view=task["view"]))
    preds = pd.concat(pred_parts, ignore_index=True)
    h0c = preds.loc[(preds["horizon"] == 0) & (preds["view"] == "B")].assign(view="C", reused_from="B")
    preds = pd.concat([preds, h0c], ignore_index=True)
    copies = []
    for item in receiving:
        job, view, recipe = item["job"], item["view"], item["recipe"]
        if recipe is None:
            continue
        src = reuse_source(view, recipe, selections[job["test_year"]], job["horizon"])
        if src is None:
            continue
        rows = preds.loc[(preds["job_id"] == job["job_id"]) & (preds["view"] == src)].assign(view=view, reused_from=src)
        copies.append(rows)
        status_rows += [{**r, "view": view, "reused_from": src} for r in list(status_rows) if r.get("view") == src and r.get("job_id") == job["job_id"]]
    preds = pd.concat([preds, *copies], ignore_index=True)
    written["final_predictions"] = write(preds, out / "predictions" / "final_predictions.csv.gz")
    written["final_status"] = write(pd.DataFrame(status_rows), out / "fits" / "final_status.csv")
    written["mappings"] = write(pd.DataFrame(mapping_rows), out / "fits" / "calibration_mappings.csv")
    written["final_fit_ledger"] = write(pd.concat(fit_parts, ignore_index=True), out / "fits" / "final_fit_ledger.csv.gz")
    written["model_inventory"] = write(pd.DataFrame(model_rows), out / "models" / "model_inventory.csv")

    # ---------------- evaluation ----------------
    metrics, contrasts, arrays = evaluate(prepared, preds, args.v1_dir, cfg)
    written["metrics"] = write(metrics, out / "metrics" / "metrics.csv")
    written["contrasts"] = write(contrasts, out / "metrics" / "contrasts.csv")
    np.savez_compressed(out / "metrics" / "bootstrap_draws.npz", **arrays)
    report.mkdir(parents=True, exist_ok=True)
    write_report(metrics, contrasts, pd.DataFrame(sel_rows), report / "summary.md", manifest)
    manifest["mode"] = "full"
    manifest["elapsed_seconds"] = time.time() - started
    manifest["written"] = written
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1, default=str))
    log(f"done in {manifest['elapsed_seconds']:.0f}s")
    return 0


def evaluate(prepared, preds, v1_dir, cfg):
    cohort = prepared.cohort_ledger
    ledger = prepared.ledger
    rows, crows, arrays = [], [], {}
    draws, seed = int(cfg["bootstrap"]["draws"]), int(cfg["bootstrap"]["seed"])
    have_v1 = (v1_dir / "predictions" / "predictions.csv.gz").exists()
    for (year, h), keys in cohort.groupby(["test_year", "horizon"]):
        primary = keys.loc[keys["status"] == "primary", ["area_id", "target_ord"]]
        base = {"test_year": year, "horizon": h, "n_primary": len(primary), "n_wider_only": int((keys["status"] == "wider_only").sum()), "n_excluded": int((keys["status"] == "excluded").sum())}
        if primary.empty:
            rows.append({**base, "cohort": "primary", "view": "all", "status": "unavailable", "reason": "empty primary cohort"})
            continue
        frame = prepared.frames[h]
        truth = primary.merge(frame[["area_id", "target_ord", "q3", "actual_crisis", "overall_phase", "hist_q3_obs1", "history_obs1_source_ord", "persistence_available", "persistence_phase"]], on=["area_id", "target_ord"])
        share_ok = np.isfinite(truth["hist_q3_obs1"]) & (truth["history_obs1_source_ord"] >= 0)
        views = {}
        for view in qo.VIEWS:
            p = preds.loc[(preds["test_year"] == year) & (preds["horizon"] == h) & (preds["view"] == view)]
            m = truth.merge(p[["area_id", "target_ord", "q2_raw", "q3_raw", "q4_raw", "q5_raw", "q3_final", "clipped", "branch", "calibration_status"]], on=["area_id", "target_ord"], how="left")
            if m["q3_raw"].isna().any():
                rows.append({**base, "cohort": "primary", "view": view, "status": "incomplete", "reason": f"{int(m['q3_raw'].isna().sum())} primary keys without predictions"})
                continue
            if (m["calibration_status"] != "ok").any():
                diag = m.assign(q3_final=np.clip(m["q3_raw"], 0, 1), clipped=np.clip(m["q3_raw"], 0, 1) != m["q3_raw"])
                rows.append({**base, "cohort": "primary", "view": view, "status": "calibrated_unavailable", "reason": "fixed calibration method could not be fitted; raw-bounded diagnostic", **qe.model_view_metrics(diag)})
                continue
            views[view] = m
            rows.append({**base, "cohort": "primary", "view": view, "status": "ok", "reason": None, **qe.model_view_metrics(m)})
            if share_ok.any():
                rows.append({**base, "cohort": "share_history_subset", "view": view, "status": "ok", "reason": None, **qe.model_view_metrics(m.loc[share_ok.to_numpy()])})
        # share persistence on its own supported subset
        sp = truth.loc[share_ok.to_numpy()]
        if len(sp):
            sm = qe.share_metrics(sp["q3"], sp["hist_q3_obs1"])
            rows.append({**base, "cohort": "share_history_subset", "view": "share_persistence", "status": "ok", "n": len(sp), **{f"final_{k}": v for k, v in sm.items()},
                         "final_auc": qe.pooled_auc(sp["actual_crisis"], sp["hist_q3_obs1"]), **{f"bin_{k}": v for k, v in qe.binary_metrics(sp["actual_crisis"], sp["hist_q3_obs1"].to_numpy() >= qe.BINARY_THRESHOLD).items()}})
        pp = truth.loc[truth["persistence_available"].fillna(False).astype(bool).to_numpy()]
        if len(pp):
            rows.append({**base, "cohort": "phase_persistence_subset", "view": "phase_persistence", "status": "ok", "n": len(pp), "legacy_phase_accuracy": float((pp["persistence_phase"] == pp["overall_phase"]).mean()),
                         **{f"bin_{k}": v for k, v in qe.binary_metrics(pp["actual_crisis"], pp["persistence_phase"].to_numpy() >= 3).items()}})
            for view, m in views.items():
                sub = m.loc[truth["persistence_available"].fillna(False).astype(bool).to_numpy()]
                rows.append({**base, "cohort": "phase_persistence_subset", "view": view, "status": "ok", "reason": None, **qe.model_view_metrics(sub)})
        rows.append({**base, "cohort": "primary", "view": "always_crisis", "status": "ok", "n": len(truth), **{f"bin_{k}": v for k, v in qe.binary_metrics(truth["actual_crisis"], np.ones(len(truth), dtype=bool)).items()}})
        v1 = None
        if have_v1:
            v1 = qe.v1_calibrated_d(v1_dir, keys.loc[keys["status"] == "primary", ["test_year", "horizon", "area_id", "target_ord"]], ledger)
            v1 = truth.merge(v1[["area_id", "target_ord", "v1_q3_raw", "v1_q3_cal"]], on=["area_id", "target_ord"], how="left")
            if not v1["v1_q3_cal"].isna().any():
                for label, col in (("v1_D_raw", "v1_q3_raw"), ("v1_D_isotonic", "v1_q3_cal")):
                    sm = qe.share_metrics(v1["q3"], v1[col])
                    rows.append({**base, "cohort": "primary", "view": label, "status": "ok", "n": len(v1), **{f"final_{k}": val for k, val in sm.items()}, "final_auc": qe.pooled_auc(v1["actual_crisis"], v1[col]),
                                 **{f"bin_{k}": val for k, val in qe.binary_metrics(v1["actual_crisis"], v1[col].to_numpy() >= qe.BINARY_THRESHOLD).items()}})
            else:
                v1 = None
        # priority paired contrasts
        pairs = []
        if "D_direct" in views and v1 is not None:
            pairs.append(("D_direct-v1_D_isotonic", "primary", views["D_direct"].assign(b=v1["v1_q3_cal"].to_numpy()), "q3_final", "b"))
        if "D_residual" in views and "D_direct" in views:
            pairs.append(("D_residual-D_direct", "primary", views["D_residual"].assign(b=views["D_direct"]["q3_final"].to_numpy()), "q3_final", "b"))
        if "D_selected" in views and share_ok.any():
            sel = views["D_selected"].loc[share_ok.to_numpy()]
            pairs.append(("D_selected-share_persistence", "share_history_subset", sel.assign(b=sel["hist_q3_obs1"].to_numpy()), "q3_final", "b"))
        for name, cname, frame_c, a, b in pairs:
            res = qe.paired_share_bootstrap(frame_c, "q3", "actual_crisis", a, b, draws, seed)
            key = f"y{year}_h{h:02d}_{name}"
            if "multiplicities" in res:
                arrays[f"{key}__multiplicities"] = res["multiplicities"]
            arrays[f"{key}__areas"] = res["areas"]
            for metric in ("r2", "rmse", "auc"):
                e = res[metric]
                if "draws" in e:
                    arrays[f"{key}__{metric}"] = e["draws"]
                crows.append({"test_year": year, "horizon": h, "cohort": cname, "contrast": name, "metric": metric, "n": res["n"], "n_areas": res["n_areas"], "point_delta": e["point"], "ci_low": e["ci_low"], "ci_high": e["ci_high"], "interval_status": e["status"], "interval_reason": e["reason"], "undefined_draws": e["undefined_draws"]})
    return pd.DataFrame(rows), pd.DataFrame(crows), arrays


def _f(v, d=3):
    return "—" if v is None or (isinstance(v, float) and np.isnan(v)) else f"{v:.{d}f}"


def write_report(metrics, contrasts, selected, path: Path, manifest):
    lines = [
        "# Somalia q3-first optimization (v2_q3) — results",
        "",
        f"Code `{manifest['git_head']}`; xgboost {manifest['runtime']['xgboost']}. D is the main specification; A–C are baselines. H0 recipes were selected by pooled held-out final-q3 RMSE on training-window chronological OOF predictions only (AUC breaks numerical ties). H3/H6/H12 are ancillary fixed-recipe refits whose recipes used labels later than their origins (disclosed leakage); they are not optimized or ranked. 2025/2026 outcomes were inspected in v1, so these are retrospective comparisons, not an untouched holdout.",
        "",
        "## Selected H0 recipes",
        "",
        "| Fold | View | Formulation | Bundle | Calibration | Validation RMSE | Validation AUC |",
        "|---|---|---|---|---|---:|---:|",
    ]
    for r in selected.itertuples(index=False):
        lines.append(f"| {r.test_year} | {r.view} | {getattr(r, 'formulation', '—')} | {getattr(r, 'bundle', '—')} | {getattr(r, 'method', '—')} | {_f(getattr(r, 'rmse', np.nan), 5)} | {_f(getattr(r, 'auc', np.nan))} |")
    lines += ["", "## Primary-cohort q3 results (nowcasting H0 first)", "", "| Year | H | View | n | Final R² | Raw R² | RMSE (pp) | Bias (pp) | Mean truth / pred (%) | Final AUC | Within-month AUC | Bin F1 | Bin recall | Clipped | Fallback |", "|---|---|---|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|"]
    prim = metrics.loc[metrics["cohort"] == "primary"].copy()
    prim["_h"] = prim["horizon"]
    for r in prim.sort_values(["_h", "test_year"]).itertuples(index=False):
        if r.status not in ("ok", "calibrated_unavailable"):
            lines.append(f"| {r.test_year} | {r.horizon} | {r.view} | — | {r.status}: {r.reason} | | | | | | | | | | |")
            continue
        g = lambda k: getattr(r, k, np.nan)
        mt = f"{_f(g('final_mean_truth') * 100, 1)} / {_f(g('final_mean_pred') * 100, 1)}" if not pd.isna(g("final_mean_truth")) else "—"
        tag = " (raw diag.)" if r.status == "calibrated_unavailable" else ""
        lines.append(f"| {r.test_year} | {r.horizon} | {r.view}{tag} | {int(g('n'))} | {_f(g('final_r2'))} | {_f(g('raw_r2'))} | {_f(g('final_rmse') * 100, 2)} | {_f(g('final_bias') * 100, 2)} | {mt} | {_f(g('final_auc'))} | {_f(g('final_within_month_auc'))} | {_f(g('bin_f1'))} | {_f(g('bin_recall'))} | {'' if pd.isna(g('n_clipped')) else int(g('n_clipped'))} | {'' if pd.isna(g('n_fallback_direct')) else int(g('n_fallback_direct'))} |")
    lines += ["", "## Share-history subset: D vs share persistence", "", "| Year | H | View | n | Final R² | RMSE (pp) | Bias (pp) | Final AUC |", "|---|---|---|---:|---:|---:|---:|---:|"]
    for r in metrics.loc[metrics["cohort"] == "share_history_subset"].sort_values(["horizon", "test_year"]).itertuples(index=False):
        if r.view in ("share_persistence", "D_selected", "D_direct", "D_residual"):
            lines.append(f"| {r.test_year} | {r.horizon} | {r.view} | {int(r.n)} | {_f(r.final_r2)} | {_f(r.final_rmse * 100, 2)} | {_f(r.final_bias * 100, 2)} | {_f(r.final_auc)} |")
    lines += ["", "## Paired area-cluster bootstrap (2,000 draws, PCG64(42)); Δ = first minus second", "", "| Year | H | Contrast | Metric | Δ | 95% interval |", "|---|---|---|---|---:|---|"]
    for r in contrasts.itertuples(index=False):
        interval = f"[{_f(r.ci_low, 4)}, {_f(r.ci_high, 4)}]" if r.interval_status == "ok" else r.interval_reason
        lines.append(f"| {r.test_year} | {r.horizon} | {r.contrast} | {r.metric} | {_f(r.point_delta, 4)} | {interval} |")
    lines += ["", "Missing-history rows in D-residual use the same-bundle D-direct model; that fallback branch's calibration mapping is fitted on all direct OOF rows of its calibration months (not only on no-history rows), as specified in design section 2.", ""]
    lines += ["", "Binary F1/recall use final q3 ≥ 0.2 against reported phase ≥ 3 (no threshold tuning). Legacy ordinal metrics are in `metrics.csv` (`legacy_*`). Climate-variable lineage was waived (2026-09-24). 2026 H3/H6 have no verified-oracle primary rows."]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
