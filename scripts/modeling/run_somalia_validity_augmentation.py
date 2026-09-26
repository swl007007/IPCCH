#!/usr/bin/env python3
"""Somalia validity-period label augmentation: original- vs augmented-label D (direct/residual/selected).

Examples:
    PYTHONPATH=src python scripts/modeling/run_somalia_validity_augmentation.py --prepare-only
    PYTHONPATH=src python -u scripts/modeling/run_somalia_validity_augmentation.py --workers 12 --overwrite
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
from ipcch.somalia_oracle import FOLDS, HORIZONS
from ipcch.somalia_oracle import augexp as ax
from ipcch.somalia_oracle import augment as au
from ipcch.somalia_oracle import data as sd
from ipcch.somalia_oracle import pipeline as pl
from ipcch.somalia_oracle import q3eval as qe
from ipcch.somalia_oracle import q3opt as qo

DEFAULT_OUT = paths.RESULTS_DIR / "experiments" / "somalia_oracle" / "v3_validity"
DEFAULT_REPORT = paths.REPORTS_DIR / "somalia_oracle" / "v3_validity"


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    p.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT)
    p.add_argument("--workers", type=int, default=1)
    p.add_argument("--prepare-only", action="store_true")
    p.add_argument("--skip-input-hash", action="store_true")
    p.add_argument("--config", type=Path, default=au.CONFIG_PATH)
    p.add_argument("--q3-config", type=Path, default=qo.CONFIG_PATH)
    p.add_argument("--deep-path", type=Path)
    p.add_argument("--overwrite", action="store_true")
    for n in ("fs0", "fs1", "fs2", "fs3", "raw", "lookup", "v2"):
        p.add_argument(f"--{n}-path", dest=f"{n}_path")
    return p.parse_args(argv)


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def run_pool(fn, tasks, workers):
    if workers <= 1 or len(tasks) <= 1:
        return [fn(t) for t in tasks]
    with ProcessPoolExecutor(max_workers=workers, mp_context=mp.get_context("fork")) as pool:
        return list(pool.map(fn, tasks, chunksize=1))


def write(frame, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    return {"path": str(path), "rows": int(len(frame)), "sha256": sd.sha256_file(path)}


def main(argv=None):
    args = parse_args(argv)
    out, report = args.out_dir, args.report_dir
    if out.exists() and any(out.iterdir()) and not args.overwrite:
        raise SystemExit(f"{out} is not empty; pass --overwrite")
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    cfg = au.load_config(args.config)
    qcfg, bundles = qo.load_config(args.q3_config)
    inputs = pl.resolve_input_paths({n: getattr(args, f"{n}_path") for n in ("fs0", "fs1", "fs2", "fs3", "raw", "lookup", "v2")})
    deep = None
    if args.deep_path:
        from ipcch.somalia_oracle import monthly_features as mf

        lookup = pd.read_csv(inputs["lookup"])
        deep = mf.load_somalia_deep(sd.somalia_area_ids(lookup), args.deep_path)
    prep = ax.prepare(inputs, cfg, log=log, hash_inputs=not args.skip_input_hash, deep=deep)
    written = {}
    written["label_ledger"] = write(prep.ledger, out / "ledgers" / "label_ledger.csv.gz")
    written["augmentation_decisions"] = write(prep.decisions, out / "ledgers" / "augmentation_decisions.csv.gz")
    written["round_links"] = write(prep.links, out / "ledgers" / "round_links.csv")
    written["api_rounds"] = write(prep.rounds_api, out / "ledgers" / "api_rounds.csv")
    written["cohort"] = write(prep.cohort, out / "ledgers" / "cohort_ledger.csv.gz")
    written["jobs"] = write(prep.jobs, out / "ledgers" / "jobs.csv")
    written["feature_parity"] = write(prep.parity, out / "ledgers" / "feature_parity.csv")
    fam = prep.ledger.groupby("source_family").agg(n_rows=("target_ord", "size"), n_copies=("is_copy", "sum"), original_month=("original_month_ord", "first")).reset_index()
    written["source_families"] = write(fam, out / "ledgers" / "source_families.csv")
    for h, f in prep.frames.items():
        keep = ["area_id", "target_ord", "origin_ord", "is_copy", "original_month_ord", "source_family", "source_available_ord", "history_cutoff_ord", "hist_q3_obs1", "history_obs1_source_ord", "persistence_available", "persistence_phase", "persistence_source_ord", "oracle_all_verified", "valid_score", "q3"]
        written[f"row_provenance_h{h:02d}"] = write(f[keep], out / "ledgers" / f"row_provenance_h{h:02d}.csv.gz")
        written[f"feature_matrix_h{h:02d}"] = write(f[["area_id", "target_ord", *prep.schemas[h]]], out / "features" / f"feature_matrix_h{h:02d}.csv.gz")
    (out / "features" / "feature_schema.json").write_text(json.dumps({f"h{h:02d}_D": c for h, c in prep.schemas.items()}, indent=1))
    manifest = {"experiment": "somalia_oracle_v3_validity", "task": "somalia-validity-label-augmentation",
                "git_head": subprocess.run(["git", "rev-parse", "HEAD"], cwd=paths.PROJECT_ROOT, capture_output=True, text=True).stdout.strip(),
                "git_dirty": subprocess.run(["git", "status", "--porcelain"], cwd=paths.PROJECT_ROOT, capture_output=True, text=True).stdout.splitlines(),
                "runtime": pl.runtime_identity(), "inputs": {n: {"path": str(p), "sha256": prep.input_hashes.get(n)} for n, p in inputs.items()},
                "validity_snapshot": {"path": cfg["validity_snapshot"], "sha256": cfg["validity_snapshot_sha256"]},
                "config_sha256": sd.sha256_file(args.config), "q3_config_sha256": sd.sha256_file(args.q3_config), "notes": prep.notes}
    if prep.notes["n_copies"] == 0:
        manifest["mode"] = "augmentation_unavailable"
        (out / "manifest.json").write_text(json.dumps(manifest, indent=1, default=str))
        log("augmentation_unavailable: no defensible additions; stopping after diagnostics")
        return 0
    if args.prepare_only:
        manifest["mode"], manifest["written"] = "prepare_only", written
        (out / "manifest.json").write_text(json.dumps(manifest, indent=1, default=str))
        log("prepare-only done")
        return 0

    ax.init_state(prep, bundles)
    store = ax.RoundStore()
    tol = float(qcfg["tie_tolerance"])

    # ---------------- H0 plans (frozen before scoring) ----------------
    plans, plan_rows = {}, []
    for branch in ax.BRANCHES:
        for year, window in FOLDS.items():
            plan = ax.plan_rounds(prep.frames[0], branch, list(window), 0, cfg)
            if plan["status"] != "ok":
                raise ax.AugExpError(f"{branch} fold {year}: fewer than {cfg['min_selection_rounds']} supported rounds")
            plans[(branch, year)] = plan
            for r in plan["scoring"]:
                rows = ax.round_rows(prep.frames[0], branch, list(window), r)
                plan_rows.append({"branch": branch, "test_year": year, "scoring_round": sd.ord_label(r), "n_rows": len(rows), "n_copy_rows": int(prep.frames[0]["is_copy"].to_numpy()[rows].sum()),
                                  "calibration_rounds": ";".join(sd.ord_labels(plan["calibration"][r])), "families": ";".join(ax.round_families(prep.frames[0], r))})
    written["rounds_plan"] = write(pd.DataFrame(plan_rows), out / "selection" / "rounds_plan.csv")
    tasks, seen = [], set()
    for (branch, year), plan in plans.items():
        need = sorted(set(plan["scoring"]) | {c for cs in plan["calibration"].values() for c in cs})
        for form in ax.FORMULATIONS:
            for b in [c["id"] for c in bundles["candidates"]]:
                for r in need:
                    k = (branch, year, 0, form, b, r)
                    if k not in seen:
                        seen.add(k)
                        tasks.append(ax.oof_task_spec(prep.frames[0], branch, year, list(FOLDS[year]), 0, form, b, r))
    log(f"H0 OOF fits: {len(tasks)}")
    for res in run_pool(ax.oof_task, tasks, args.workers):
        store.add(res)

    # ---------------- selection ----------------
    selections, score_tables, score_preds, sel_rows = {}, [], [], []
    for (branch, year), plan in plans.items():
        frame = prep.frames[0]
        per = {}
        for form in ax.FORMULATIONS:
            s, p = ax.score_view(store, frame, plan, (branch, year, 0), form, cfg, bundles)
            score_tables.append(s)
            if len(p):
                score_preds.append(p)
            best, _ = qo.select_candidate(s, tol, True)
            per[f"D_{form}"] = best
        both = pd.concat([t for t in score_tables if t["branch"].iloc[0] == branch and t["fold"].iloc[0] == year])
        per["D_selected"], _ = qo.select_candidate(both, tol, True)
        selections[(branch, year)] = per
        for view, row in per.items():
            log(f"{branch} {year} {view}: " + ("unsupported" if row is None else f"{row['formulation']} {row['bundle']} {row['method']} rmse={row['rmse']:.5f}"))
            sel_rows.append({"branch": branch, "test_year": year, "view": view, "status": "ok" if row is not None else "unsupported", **({} if row is None else {k: row[k] for k in ("formulation", "bundle", "method", "rmse", "auc", "n")}),
                             "selection_max_round": sd.ord_label(max(plan["scoring"]))})
    written["candidate_scores"] = write(pd.concat(score_tables, ignore_index=True), out / "selection" / "candidate_scores.csv")
    written["scoring_predictions"] = write(pd.concat(score_preds, ignore_index=True), out / "selection" / "scoring_predictions.csv.gz")
    written["selected_recipes"] = write(pd.DataFrame(sel_rows), out / "selection" / "selected_recipes.csv")

    # ---------------- final fits (all horizons; H>0 inherit H0 recipe) ----------------
    ftasks, meta = [], {}
    for job in prep.jobs.to_dict("records"):
        h, year, origin = job["horizon"], job["test_year"], job["origin_ord"]
        frame = prep.frames[h]
        window = list(FOLDS[year])
        for branch in ax.BRANCHES:
            rplan = ax.plan_rounds(frame, branch, window, h, cfg, outer_origin=origin)
            fit_idx = ax.fit_pool(frame, branch, window, origin, origin)
            pred_idx = np.flatnonzero(((frame["target_year"] == year) & frame["valid_score"] & ~frame["is_copy"] & (frame["origin_ord"] == origin)).to_numpy())
            for view in ax.MODEL_VIEWS:
                recipe = selections[(branch, year)][view]
                if recipe is None:
                    continue
                key = (job["job_id"], branch, view)
                meta[key] = {"job_id": job["job_id"], "branch": branch, "view": view, "horizon": h, "test_year": year, "formulation": recipe["formulation"], "bundle": recipe["bundle"], "method": recipe["method"],
                             "receiving_origin": sd.ord_label(origin), "recipe_selection_max_round": sd.ord_label(max(plans[(branch, year)]["scoring"])),
                             "selection_uses_later_labels": bool(max(plans[(branch, year)]["scoring"]) > origin), "mapping_rounds": ";".join(sd.ord_labels(rplan["final"] or [])), "n_fit": int(fit_idx.size),
                             "n_fit_copies": int(frame["is_copy"].to_numpy()[fit_idx].sum()), "sum_weight": float(np.power(0.5, (origin - frame["target_ord"].to_numpy()[fit_idx]) / 24.0).sum())}
                ftasks.append({"key": key, "horizon": h, "formulation": recipe["formulation"], "bundle": recipe["bundle"], "method": recipe["method"], "origin_ord": origin, "fit_idx": fit_idx, "pred_idx": pred_idx,
                               "branch": branch, "fold": year, "rounds": rplan["final"] or []})
    # OOF fits needed for final mappings at every horizon
    otasks, seen = [], set(store.data)
    for t in ftasks:
        if t["method"] == "none":
            continue
        forms = ("direct",) if t["formulation"] == "direct" else ("direct", "residual")
        for form in forms:
            for r in t["rounds"]:
                k = (t["branch"], t["fold"], t["horizon"], form, t["bundle"], r)
                if k not in seen:
                    seen.add(k)
                    otasks.append(ax.oof_task_spec(prep.frames[t["horizon"]], t["branch"], t["fold"], list(FOLDS[t["fold"]]), t["horizon"], form, t["bundle"], r))
    log(f"mapping OOF fits: {len(otasks)}")
    for res in run_pool(ax.oof_task, otasks, args.workers):
        store.add(res)
    map_rows = []
    for t in ftasks:
        frame = prep.frames[t["horizon"]]
        maps = ax.fit_round_mappings(store, frame, (t["branch"], t["fold"], t["horizon"]), t["formulation"], t["bundle"], t["method"], t["rounds"], t["origin_ord"], t["origin_ord"], int(cfg["min_calibration_rounds"]))
        t["mappings"] = maps
        map_rows += [{**{k: meta[t["key"]][k] for k in ("job_id", "branch", "view", "horizon")}, "prediction_branch": n, **m.describe()} for n, m in maps.items()]
    log(f"final fits: {len(ftasks)}")
    results = run_pool(ax.final_task, ftasks, args.workers)
    preds, fits, status_rows, model_rows = [], [], [], []
    mdir = out / "models"
    mdir.mkdir(parents=True, exist_ok=True)
    for t, res in zip(ftasks, results):
        m = meta[t["key"]]
        status_rows.append({**m, "status": res["status"], "calibration_status": res.get("calibration_status"), "calibration_reason": res.get("calibration_reason")})
        if res["status"] != "completed":
            continue
        # "branch" in predictions is the per-row prediction branch (direct/residual/fallback_direct);
        # the label branch (original/augmented) is stored separately as "label_branch".
        preds.append(res["predictions"].assign(**{k: m[k] for k in ("job_id", "view", "horizon", "test_year")}, label_branch=m["branch"], calibration_status=res["calibration_status"]))
        fits.append(res["fit_ledger"].assign(job_id=m["job_id"], label_branch=m["branch"], view=m["view"]))
        for target, model in res["models"].items():
            if model is None:
                continue
            stem = mdir / f"{m['job_id']}_{m['branch']}_{m['view']}_{target}"
            if model.kind == "xgboost":
                path = stem.with_suffix(".ubj")
                model.model.save_model(str(path))
            else:
                path = stem.with_suffix(".json")
                path.write_text(json.dumps({"kind": "constant", "value": model.constant, "n_rows": model.n_rows}))
            model_rows.append({"job_id": m["job_id"], "branch": m["branch"], "view": m["view"], "target": target, "kind": model.kind, "path": path.name, "sha256": sd.sha256_file(path),
                               "feature_order_sha256": hashlib.sha256("\n".join(prep.schemas[m["horizon"]]).encode()).hexdigest()})
    preds = pd.concat(preds, ignore_index=True)
    written["final_predictions"] = write(preds, out / "predictions" / "final_predictions.csv.gz")
    written["final_status"] = write(pd.DataFrame(status_rows), out / "fits" / "final_status.csv")
    written["fit_ledger"] = write(pd.concat(fits, ignore_index=True), out / "fits" / "final_fit_ledger.csv.gz")
    written["calibration_mappings"] = write(pd.DataFrame(map_rows), out / "fits" / "calibration_mappings.csv")
    written["model_inventory"] = write(pd.DataFrame(model_rows), out / "models" / "model_inventory.csv")
    written["oof_ledger"] = write(pd.DataFrame(store.ledger), out / "selection" / "oof_fit_ledger.csv")
    oof_rows = []
    for (branch, fold, h, form, b, r), (idx, raw) in store.data.items():
        f = prep.frames[h]
        oof_rows.append(pd.DataFrame({"branch": branch, "fold": fold, "horizon": h, "formulation": form, "bundle": b, "round": r, "row": idx, "area_id": f["area_id"].to_numpy()[idx], "target_ord": f["target_ord"].to_numpy()[idx], "raw_q3": raw}))
    written["oof_predictions"] = write(pd.concat(oof_rows, ignore_index=True), out / "selection" / "oof_predictions.csv.gz")

    metrics, contrasts, arrays = evaluate(prep, preds, cfg)
    written["metrics"] = write(metrics, out / "metrics" / "metrics.csv")
    written["contrasts"] = write(contrasts, out / "metrics" / "contrasts.csv")
    np.savez_compressed(out / "metrics" / "bootstrap_draws.npz", **arrays)
    report.mkdir(parents=True, exist_ok=True)
    write_report(metrics, contrasts, pd.DataFrame(sel_rows), prep, report / "summary.md", manifest)
    manifest.update(mode="full", elapsed_seconds=time.time() - t0, written=written)
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1, default=str))
    log(f"done in {manifest['elapsed_seconds']:.0f}s")
    return 0


def evaluate(prep, preds, cfg):
    rows, crows, arrays = [], [], {}
    draws, seed = int(cfg["bootstrap"]["draws"]), int(cfg["bootstrap"]["seed"])
    for (year, h), keys in prep.cohort.groupby(["test_year", "horizon"]):
        primary = keys.loc[keys["status"] == "primary", ["area_id", "target_ord"]]
        base = {"test_year": year, "horizon": h, "n_primary": len(primary)}
        if primary.empty:
            rows.append({**base, "cohort": "primary", "branch": "all", "view": "all", "status": "unavailable", "reason": "empty primary cohort"})
            continue
        f = prep.frames[h]
        truth = primary.merge(f[["area_id", "target_ord", "q3", "actual_crisis", "overall_phase", "hist_q3_obs1", "history_obs1_source_ord", "persistence_available", "persistence_phase"]], on=["area_id", "target_ord"])
        share_ok = (np.isfinite(truth["hist_q3_obs1"]) & (truth["history_obs1_source_ord"] >= 0)).to_numpy()
        views = {}
        for branch in ax.BRANCHES:
            for view in ax.MODEL_VIEWS:
                p = preds.loc[(preds["test_year"] == year) & (preds["horizon"] == h) & (preds["label_branch"] == branch) & (preds["view"] == view)]
                m = truth.merge(p[["area_id", "target_ord", "q2_raw", "q3_raw", "q4_raw", "q5_raw", "q3_final", "clipped", "branch", "calibration_status"]], on=["area_id", "target_ord"], how="left")
                if m["q3_raw"].isna().any():
                    rows.append({**base, "cohort": "primary", "branch": branch, "view": view, "status": "incomplete", "reason": f"{int(m['q3_raw'].isna().sum())} keys without predictions"})
                    continue
                st = "ok"
                if (m["calibration_status"] != "ok").any():
                    m = m.assign(q3_final=np.clip(m["q3_raw"], 0, 1), clipped=np.clip(m["q3_raw"], 0, 1) != m["q3_raw"])
                    st = "calibrated_unavailable"
                views[(branch, view)] = m
                rows.append({**base, "cohort": "primary", "branch": branch, "view": view, "status": st, "reason": None, **qe.model_view_metrics(m)})
                if share_ok.any():
                    rows.append({**base, "cohort": "share_history_subset", "branch": branch, "view": view, "status": st, **qe.model_view_metrics(m.loc[share_ok])})
        sp = truth.loc[share_ok]
        if len(sp):
            sm = qe.share_metrics(sp["q3"], sp["hist_q3_obs1"])
            rows.append({**base, "cohort": "share_history_subset", "branch": "-", "view": "share_persistence", "status": "ok", "n": len(sp), **{f"final_{k}": v for k, v in sm.items()},
                         "final_auc": qe.pooled_auc(sp["actual_crisis"], sp["hist_q3_obs1"]), **{f"bin_{k}": v for k, v in qe.binary_metrics(sp["actual_crisis"], sp["hist_q3_obs1"].to_numpy() >= 0.2).items()}})
        pp = truth.loc[truth["persistence_available"].fillna(False).astype(bool).to_numpy()]
        if len(pp):
            rows.append({**base, "cohort": "phase_persistence_subset", "branch": "-", "view": "phase_persistence", "status": "ok", "n": len(pp), "legacy_phase_accuracy": float((pp["persistence_phase"] == pp["overall_phase"]).mean()),
                         **{f"bin_{k}": v for k, v in qe.binary_metrics(pp["actual_crisis"], pp["persistence_phase"].to_numpy() >= 3).items()}})
        rows.append({**base, "cohort": "primary", "branch": "-", "view": "always_crisis", "status": "ok", "n": len(truth), **{f"bin_{k}": v for k, v in qe.binary_metrics(truth["actual_crisis"], np.ones(len(truth), dtype=bool)).items()}})
        pairs = []
        for view in ax.MODEL_VIEWS:
            if ("augmented", view) in views and ("original", view) in views:
                pairs.append((f"augmented_{view}-original_{view}", "primary", views[("augmented", view)].assign(b=views[("original", view)]["q3_final"].to_numpy())))
        for branch in ax.BRANCHES:
            if (branch, "D_selected") in views and share_ok.any():
                s = views[(branch, "D_selected")].loc[share_ok]
                pairs.append((f"{branch}_D_selected-share_persistence", "share_history_subset", s.assign(b=s["hist_q3_obs1"].to_numpy())))
        for name, cname, fr in pairs:
            res = qe.paired_share_bootstrap(fr, "q3", "actual_crisis", "q3_final", "b", draws, seed)
            key = f"y{year}_h{h:02d}_{name}"
            arrays[f"{key}__areas"] = res["areas"]
            if "multiplicities" in res:
                arrays[f"{key}__multiplicities"] = res["multiplicities"]
            for metric in ("r2", "rmse", "auc"):
                e = res[metric]
                if "draws" in e:
                    arrays[f"{key}__{metric}"] = e["draws"]
                crows.append({"test_year": year, "horizon": h, "cohort": cname, "contrast": name, "metric": metric, "n": res["n"], "n_areas": res["n_areas"], "point_delta": e["point"], "ci_low": e["ci_low"], "ci_high": e["ci_high"], "interval_status": e["status"], "interval_reason": e["reason"]})
    return pd.DataFrame(rows), pd.DataFrame(crows), arrays


def _f(v, d=3):
    return "—" if v is None or (isinstance(v, float) and np.isnan(v)) else f"{v:.{d}f}"


def write_report(metrics, contrasts, selected, prep, path, manifest):
    n = prep.notes
    lines = ["# Somalia validity-period label augmentation (v3_validity) — results", "",
             f"Code `{manifest['git_head']}`. Training-label augmentation: {n['n_copies']} blank area-months inside verified current-period validity windows (round-level link, grill G3) received a full copy of the area's original label; copies keep the original's values, source family and availability, and never enter history. Outer 2025/2026 evaluation labels are unchanged, so original- and augmented-label D are scored on identical keys. Report isolation removes each scoring round's source family from fitting/calibration. Retrospective comparison on inspected years; H3/H6/H12 are ancillary fixed-recipe refits.", "",
             "Copies by month: " + ", ".join(f"{k} ({v})" for k, v in n["copies_by_month"].items()), "",
             "## Selected H0 recipes", "", "| Branch | Fold | View | Formulation | Bundle | Calibration | Validation RMSE | AUC |", "|---|---|---|---|---|---|---:|---:|"]
    for r in selected.itertuples(index=False):
        lines.append(f"| {r.branch} | {r.test_year} | {r.view} | {getattr(r, 'formulation', '—')} | {getattr(r, 'bundle', '—')} | {getattr(r, 'method', '—')} | {_f(getattr(r, 'rmse', np.nan), 5)} | {_f(getattr(r, 'auc', np.nan))} |")
    lines += ["", "## Primary cohort (identical keys for both branches)", "", "| Year | H | Branch | View | n | Final R² | Raw R² | RMSE (pp) | Bias (pp) | Final AUC | Within-month AUC | Bin F1 | Bin recall |", "|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    prim = metrics.loc[metrics["cohort"] == "primary"]
    for r in prim.sort_values(["horizon", "test_year"]).itertuples(index=False):
        g = lambda k: getattr(r, k, np.nan)
        if r.status not in ("ok", "calibrated_unavailable"):
            lines.append(f"| {r.test_year} | {r.horizon} | {r.branch} | {r.view} | — | {r.status}: {r.reason} | | | | | | | |")
            continue
        lines.append(f"| {r.test_year} | {r.horizon} | {r.branch} | {r.view}{' (raw diag.)' if r.status == 'calibrated_unavailable' else ''} | {int(g('n'))} | {_f(g('final_r2'))} | {_f(g('raw_r2'))} | {_f(g('final_rmse') * 100, 2)} | {_f(g('final_bias') * 100, 2)} | {_f(g('final_auc'))} | {_f(g('final_within_month_auc'))} | {_f(g('bin_f1'))} | {_f(g('bin_recall'))} |")
    lines += ["", "## Share-history subset vs share persistence", "", "| Year | H | Branch | View | n | Final R² | RMSE (pp) | Final AUC |", "|---|---|---|---|---:|---:|---:|---:|"]
    for r in metrics.loc[(metrics["cohort"] == "share_history_subset") & metrics["view"].isin(["D_selected", "share_persistence"])].sort_values(["horizon", "test_year"]).itertuples(index=False):
        lines.append(f"| {r.test_year} | {r.horizon} | {r.branch} | {r.view} | {int(r.n)} | {_f(r.final_r2)} | {_f(r.final_rmse * 100, 2)} | {_f(r.final_auc)} |")
    lines += ["", "## Paired area-cluster bootstrap (2,000 draws, PCG64(42)); Δ = first minus second", "", "| Year | H | Contrast | Metric | Δ | 95% interval |", "|---|---|---|---|---:|---|"]
    for r in contrasts.itertuples(index=False):
        lines.append(f"| {r.test_year} | {r.horizon} | {r.contrast} | {r.metric} | {_f(r.point_delta, 4)} | {'[' + _f(r.ci_low, 4) + ', ' + _f(r.ci_high, 4) + ']' if r.interval_status == 'ok' else r.interval_reason} |")
    lines += ["", "Copied labels are validity-period copies of one assessment, not independent monthly observations; area resampling does not model shared report dependence. Labels come from the raw panel (v1/v2 used the target-corrected fs ledger), so v2 numbers are context, not an unchanged comparator. Climate-variable lineage was waived (2026-09-24)."]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
