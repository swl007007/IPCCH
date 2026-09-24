#!/usr/bin/env python3
"""Somalia oracle-information experiment: arms A-D x folds 2025/2026 x H in {0,3,6,12}.

Examples:
    PYTHONPATH=src python scripts/modeling/run_somalia_oracle_experiment.py --prepare-only
    PYTHONPATH=src python scripts/modeling/run_somalia_oracle_experiment.py --workers 24 --overwrite
"""
from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path

import numpy as np
import pandas as pd

from ipcch import paths
from ipcch.somalia_oracle import ARMS, FOLDS, HORIZONS
from ipcch.somalia_oracle import data as sd
from ipcch.somalia_oracle import modeling as md
from ipcch.somalia_oracle import pipeline as pl

DEFAULT_OUT = paths.RESULTS_DIR / "experiments" / "somalia_oracle" / "v1"
DEFAULT_REPORT = paths.REPORTS_DIR / "somalia_oracle" / "v1"


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--prepare-only", action="store_true", help="Build ledgers, cohorts and the job inventory without fitting.")
    parser.add_argument("--pilot-job", help="Run only this job id (all arms) to measure runtime.")
    parser.add_argument("--no-save-models", action="store_true")
    parser.add_argument("--skip-input-hash", action="store_true", help="Skip sha256 of large inputs (not for evidence runs).")
    parser.add_argument("--overwrite", action="store_true")
    for name in ("fs0", "fs1", "fs2", "fs3", "raw", "lookup", "v2"):
        parser.add_argument(f"--{name}-path", dest=f"{name}_path")
    return parser.parse_args(argv)


def git_identity() -> dict:
    def run(*args):
        return subprocess.run(["git", *args], cwd=paths.PROJECT_ROOT, capture_output=True, text=True).stdout.strip()

    return {"head": run("rev-parse", "HEAD"), "dirty_paths": run("status", "--porcelain").splitlines()}


def write_csv(frame: pd.DataFrame, path: Path) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    return {"path": str(path.relative_to(paths.PROJECT_ROOT)) if path.is_relative_to(paths.PROJECT_ROOT) else str(path), "rows": int(len(frame))}


def write_prepared(prepared: pl.Prepared, out: Path) -> dict:
    written = {}
    ledger_cols = [c for c in prepared.ledger.columns if c not in ("estimated_population",)] + ["estimated_population"]
    written["label_ledger"] = write_csv(prepared.ledger.loc[:, ledger_cols].assign(target_month=lambda d: sd.ord_labels(d["target_ord"])), out / "ledgers" / "label_ledger.csv.gz")
    written["weather_ledger"] = write_csv(prepared.weather.assign(month=lambda d: sd.ord_labels(d["month_ord"])), out / "ledgers" / "weather_ledger.csv.gz")
    written["cohort_ledger"] = write_csv(prepared.cohort_ledger.assign(target_month=lambda d: sd.ord_labels(d["target_ord"])), out / "ledgers" / "cohort_ledger.csv.gz")
    written["jobs"] = write_csv(prepared.jobs.assign(candidate_years=prepared.jobs["candidate_years"].map(json.dumps)), out / "ledgers" / "jobs.csv")
    for horizon, frame in prepared.frames.items():
        provenance = ["area_id", "target_ord", "origin_ord", "history_cutoff_ord", "valid_score", "actual_crisis", "overall_phase", "share_derived_phase", "raw_sum", "normalization_changed", "q2", "q3", "q4", "q5", "v2_status", "v2_season_year", "v2_season", "v2_season_start", "v2_season_end_exclusive", "oracle_all_verified", "persistence_available", "persistence_phase", "persistence_source_ord", "persistence_age_months", "persistence_status", "history_visible_count"] + [f"history_obs{j}_source_ord" for j in range(1, 7)]
        written[f"row_provenance_h{horizon:02d}"] = write_csv(frame.loc[:, provenance], out / "ledgers" / f"row_provenance_h{horizon:02d}.csv.gz")
        written[f"oracle_ledger_h{horizon:02d}"] = write_csv(prepared.oracle_ledgers[horizon], out / "ledgers" / f"oracle_weather_ledger_h{horizon:02d}.csv.gz")
        written[f"feature_matrix_h{horizon:02d}"] = write_csv(frame.loc[:, ["area_id", "target_ord", *prepared.schemas[(horizon, "D")]]], out / "features" / f"feature_matrix_h{horizon:02d}.csv.gz")
    schema = {f"h{h:02d}_{arm}": cols for (h, arm), cols in prepared.schemas.items()}
    (out / "features").mkdir(parents=True, exist_ok=True)
    (out / "features" / "feature_schema.json").write_text(json.dumps(schema, indent=1), encoding="utf-8")
    written["feature_schema"] = {"path": "features/feature_schema.json", "widths": {k: len(v) for k, v in schema.items()}}
    return written


def coverage_summary(prepared: pl.Prepared) -> pd.DataFrame:
    cohort = prepared.cohort_ledger
    table = cohort.groupby(["test_year", "horizon", "status"]).size().unstack(fill_value=0).reset_index()
    months = cohort.loc[cohort["status"] == "primary"].groupby(["test_year", "horizon"])["target_ord"].agg(lambda s: ";".join(f"{sd.ord_label(m)}:{(s == m).sum()}" for m in sorted(s.unique())))
    return table.merge(months.rename("primary_target_month_counts").reset_index(), on=["test_year", "horizon"], how="left")


def write_results(results, prepared: pl.Prepared, out: Path) -> dict:
    written = {}
    status = pd.DataFrame([{k: r[k] for k in ("job_id", "arm", "status", "reason", "selected_candidate", "seconds")} | {"reused_from": r.get("reused_from")} for r in results])
    written["arm_job_status"] = write_csv(status, out / "fits" / "arm_job_status.csv")
    written["inner_folds"] = write_csv(pd.DataFrame([row for r in results for row in r["inner_folds"]]), out / "fits" / "inner_folds.csv")
    written["candidate_scores"] = write_csv(pd.DataFrame([row for r in results for row in r["candidate_scores"]]), out / "fits" / "candidate_scores.csv")
    val = [r["validation_predictions"] for r in results if r["validation_predictions"] is not None]
    if val:
        written["validation_predictions"] = write_csv(pd.concat(val, ignore_index=True), out / "fits" / "validation_predictions.csv.gz")
    fits = [r["fit_ledger"] for r in results if r["fit_ledger"] is not None]
    if fits:
        written["fit_ledger"] = write_csv(pd.concat(fits, ignore_index=True), out / "fits" / "final_fit_ledger.csv.gz")
    models = [m for r in results for m in r["models"]]
    if models:
        written["model_inventory"] = write_csv(pd.DataFrame(models), out / "models" / "model_inventory.csv")
    predictions = pl.assemble_predictions(prepared, results)
    written["predictions"] = write_csv(predictions.assign(target_month=lambda d: sd.ord_labels(d["target_ord"])) if len(predictions) else predictions, out / "predictions" / "predictions.csv.gz")
    return written, predictions


def write_evaluation(prepared, predictions, out: Path, report: Path) -> dict:
    metrics, contrasts, bundles = pl.evaluation_table(prepared, predictions)
    written = {"metrics": write_csv(metrics, out / "metrics" / "metrics.csv"), "contrasts": write_csv(contrasts, out / "metrics" / "contrasts.csv")}
    arrays = {}
    for key, bundle in bundles.items():
        arrays[f"{key}__areas"] = bundle["areas"]
        arrays[f"{key}__cohort_keys"] = bundle["cohort_keys"]
        if "multiplicities" in bundle:
            arrays[f"{key}__multiplicities"] = bundle["multiplicities"]
        for name, value in bundle.items():
            if name.startswith("delta::"):
                arrays[f"{key}__{name}"] = value
    np.savez_compressed(out / "metrics" / "bootstrap_draws.npz", **arrays)
    written["bootstrap_draws"] = {"path": "metrics/bootstrap_draws.npz", "bundles": sorted(bundles)}
    report.mkdir(parents=True, exist_ok=True)
    metrics.to_csv(report / "metrics.csv", index=False)
    contrasts.to_csv(report / "contrasts.csv", index=False)
    return written, metrics, contrasts


def main(argv=None) -> int:
    args = parse_args(argv)
    out, report = args.out_dir, args.report_dir
    if out.exists() and any(out.iterdir()) and not args.overwrite:
        raise SystemExit(f"{out} is not empty; pass --overwrite")
    out.mkdir(parents=True, exist_ok=True)
    started = time.time()
    overrides = {name: getattr(args, f"{name}_path") for name in ("fs0", "fs1", "fs2", "fs3", "raw", "lookup", "v2")}
    input_paths = pl.resolve_input_paths(overrides)
    config = md.load_candidates()
    prepared = pl.prepare(input_paths, hash_inputs=not args.skip_input_hash)
    manifest = {
        "experiment": "somalia_oracle_v1",
        "task": "somalia-flood-food-crisis",
        "git": git_identity(),
        "runtime": pl.runtime_identity(),
        "inputs": {name: {"path": str(path), "role": pl.INPUT_ROLES[name], "sha256": prepared.input_hashes[name]} for name, path in input_paths.items()},
        "candidate_config_sha256": sd.sha256_file(md.CANDIDATE_CONFIG_PATH),
        "history_schema_sha256": sd.sha256_file(pl.hist.SCHEMA_PATH),
        "folds": {str(k): list(v) for k, v in FOLDS.items()},
        "horizons": list(HORIZONS),
        "arms": list(ARMS),
        "notes": prepared.notes,
    }
    manifest["written"] = write_prepared(prepared, out)
    coverage = coverage_summary(prepared)
    manifest["written"]["coverage"] = write_csv(coverage, out / "ledgers" / "coverage_summary.csv")
    print(coverage.to_string(index=False))
    print(prepared.jobs[["job_id", "n_eval_rows", "n_primary_rows", "n_fit_pool", "fit_pool_max_target"]].to_string(index=False))
    if not args.prepare_only:
        only = [args.pilot_job] if args.pilot_job else None
        model_dir = None if args.no_save_models else out / "models"
        if model_dir:
            model_dir.mkdir(parents=True, exist_ok=True)
        results = pl.execute(prepared, config, args.workers, model_dir, only_jobs=only)
        written, predictions = write_results(results, prepared, out)
        manifest["written"].update(written)
        if not args.pilot_job:
            evaluation_written, metrics, contrasts = write_evaluation(prepared, predictions, out, report)
            manifest["written"].update(evaluation_written)
    manifest["elapsed_seconds"] = time.time() - started
    manifest["mode"] = "prepare_only" if args.prepare_only else ("pilot" if args.pilot_job else "full")
    for entry in manifest["written"].values():
        path = paths.PROJECT_ROOT / entry["path"] if not Path(entry["path"]).is_absolute() and (paths.PROJECT_ROOT / entry["path"]).exists() else out / entry["path"]
        if path.exists():
            entry["sha256"] = sd.sha256_file(path)
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1, default=str), encoding="utf-8")
    print(f"done in {manifest['elapsed_seconds']:.0f}s -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
