"""End-to-end preparation, execution and reporting for the Somalia oracle experiment."""
from __future__ import annotations

import json
import os
import platform
import re
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from ipcch import paths
from ipcch.somalia_oracle import (
    ARMS,
    BLOCKED_BASE_FEATURES,
    BOOTSTRAP_DRAWS,
    BOOTSTRAP_SEED,
    CUMULATIVE_COLUMNS,
    FOLDS,
    HORIZON_FS,
    HORIZONS,
    ORACLE_WEATHER_VARIABLES,
    PERCENT_COLUMNS,
    PREDICTION_COLUMNS,
    V2_FEATURES,
    oracle_feature_names,
)
from ipcch.somalia_oracle import data as sd
from ipcch.somalia_oracle import evaluation as ev
from ipcch.somalia_oracle import history as hist
from ipcch.somalia_oracle import modeling as md

FS_KEYS = {
    "fs0": "deep_features_scope_0m_model_ready_dataset",
    "fs1": "deep_features_scope_3m_model_ready_dataset",
    "fs2": "deep_features_scope_6m_model_ready_dataset",
    "fs3": "deep_features_forecasting_dataset",
}
DEFAULT_V2_PATH = Path("/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/IPCCH_shared_folder/climate_2022_2026_FINAL_MODEL_READY_V2.csv")
DEFAULT_LOOKUP_PATH = paths.SOURCE_DATA_DIR / "assembled_IPCCH" / "country_area_id_lookup.csv"
V2_COLUMNS = [
    "admin_code",
    "season_year",
    "season",
    "gs_start_date",
    "gs_end_date_exclusive",
    "gs_calendar_valid",
    "gs_calendar_quality",
    "gs_available_window_days",
    "gs_duration_recalculated_days",
    *V2_FEATURES,
]
RAW_COLUMNS = ["admin_code", "ISO3", "year", "month", "overall_phase", *PERCENT_COLUMNS, *ORACLE_WEATHER_VARIABLES]
FIRST_MODEL_YEAR = min(min(years) for years in FOLDS.values())


def resolve_input_paths(overrides: Optional[Mapping[str, str]] = None) -> Dict[str, Path]:
    overrides = dict(overrides or {})
    resolved = {name: Path(overrides.get(name) or paths.external_path(key)) for name, key in FS_KEYS.items()}
    resolved["raw"] = Path(overrides.get("raw") or paths.external_path("ipcch_2026_completed_dataset"))
    resolved["lookup"] = Path(overrides.get("lookup") or DEFAULT_LOOKUP_PATH)
    resolved["v2"] = Path(overrides.get("v2") or DEFAULT_V2_PATH)
    missing = [str(p) for p in resolved.values() if not p.exists()]
    if missing:
        raise FileNotFoundError("Missing inputs: " + "; ".join(missing))
    return resolved


INPUT_ROLES = {
    "fs0": "H=0 base predictors (upstream _s0 features, latest source month T)",
    "fs1": "H=3 base predictors (_s3, latest source month T-3)",
    "fs2": "H=6 base predictors (_s6, latest source month T-6)",
    "fs3": "H=12 base predictors (asof12/l12+, latest source month T-12)",
    "raw": "raw canonical panel: realized monthly weather and 2025+ label provenance",
    "lookup": "area_id -> country lookup (Somalia filter)",
    "v2": "V2 growing-season climate aggregates (14 ensemble means)",
}


@dataclass
class Prepared:
    input_paths: Dict[str, Path]
    input_hashes: Dict[str, str]
    ledger: pd.DataFrame
    weather: pd.DataFrame
    seasons: pd.DataFrame
    frames: Dict[int, pd.DataFrame]
    schemas: Dict[Tuple[int, str], List[str]]
    oracle_ledgers: Dict[int, pd.DataFrame]
    cohort_ledger: pd.DataFrame
    jobs: pd.DataFrame
    notes: Dict[str, object] = field(default_factory=dict)


def validate_scope_construction(columns: Sequence[str], horizon: int) -> None:
    """Every as-of/lag/scope suffix of an fs file must be >= its horizon (fs3 => 12)."""
    bad = []
    for column in columns:
        numbers = [int(n) for n in re.findall(r"asof(\d+)", column)]
        numbers += [int(n) for n in re.findall(r"_s(\d+)(?:$|__)", column)]
        numbers += [int(n) for n in re.findall(r"__l(\d+)", column)]
        if numbers and min(numbers) < horizon:
            bad.append(column)
    if bad:
        raise sd.DataContractError(f"H={horizon} feature file has predictors newer than the origin: {bad[:10]}")


def prepare(input_paths: Mapping[str, Path], log=print, hash_inputs: bool = True) -> Prepared:
    t0 = time.time()
    lookup = pd.read_csv(input_paths["lookup"])
    som = sd.somalia_area_ids(lookup)
    log(f"[prepare] Somalia areas: {len(som)}")
    raw = sd.read_area_rows(input_paths["raw"], som, "admin_code", usecols=RAW_COLUMNS)
    if not (raw["ISO3"].astype(str) == "SOM").all():
        raise sd.DataContractError("raw rows selected by the lookup are not all ISO3=SOM")
    raw_labeled = raw.loc[raw["overall_phase"].notna()]
    raw_keys = set(zip(raw_labeled["admin_code"].astype(int), sd.month_ord(raw_labeled["year"], raw_labeled["month"]).astype(int)))
    weather = sd.build_weather_ledger(raw)
    log(f"[prepare] raw rows {len(raw)}; weather verified share {weather['weather_verified'].mean():.3f} ({time.time()-t0:.0f}s)")

    fs_frames = {}
    for name in FS_KEYS:
        frame = sd.read_area_rows(input_paths[name], som, "area_id")
        if frame.duplicated(["area_id", "year", "month"]).any():
            raise sd.DataContractError(f"{name} has duplicate area/month keys")
        frame["target_ord"] = sd.month_ord(frame["year"], frame["month"])
        fs_frames[name] = frame
        log(f"[prepare] {name}: {frame.shape} ({time.time()-t0:.0f}s)")
    ledger = sd.build_label_ledger(fs_frames, raw_keys)
    history_ledger = ledger.loc[ledger["valid_history"]]
    history_index = hist.build_history_index(history_ledger)
    history_names = hist.history_feature_names()

    v2 = pd.read_csv(input_paths["v2"], usecols=V2_COLUMNS, low_memory=False)
    v2 = v2.loc[pd.to_numeric(v2["admin_code"], errors="coerce").isin(som)].copy()
    v2["admin_code"] = v2["admin_code"].astype(np.int64)
    v2_missing_areas = sorted(som - set(v2["admin_code"]))
    if v2_missing_areas:
        raise sd.DataContractError(f"{len(v2_missing_areas)} Somalia areas have no V2 rows, e.g. {v2_missing_areas[:5]}")
    seasons = sd.prepare_v2_seasons(v2)

    ledger_columns = [
        "area_id",
        "target_ord",
        "overall_phase",
        "valid_target",
        "valid_score",
        "actual_crisis",
        "share_derived_phase",
        "raw_sum",
        "normalization_changed",
        *CUMULATIVE_COLUMNS,
    ]
    frames: Dict[int, pd.DataFrame] = {}
    schemas: Dict[Tuple[int, str], List[str]] = {}
    oracle_ledgers: Dict[int, pd.DataFrame] = {}
    cohort_rows = []
    job_rows = []
    for horizon in HORIZONS:
        fs = fs_frames[HORIZON_FS[horizon]]
        base_columns = sd.base_feature_columns(fs)
        validate_scope_construction(base_columns, horizon)
        rows = fs.loc[:, ["area_id", "target_ord", *base_columns]].merge(
            ledger.loc[:, ledger_columns], on=["area_id", "target_ord"], how="inner", validate="one_to_one"
        )
        rows = rows.loc[rows["valid_target"] & (rows["target_ord"] // 12 >= FIRST_MODEL_YEAR)].copy()
        rows = rows.sort_values(["target_ord", "area_id"], kind="mergesort").reset_index(drop=True)
        rows["horizon"] = horizon
        rows["origin_ord"] = rows["target_ord"] - horizon
        rows["target_year"] = rows["target_ord"] // 12
        area = rows["area_id"].to_numpy(dtype=np.int64)
        origin = rows["origin_ord"].to_numpy(dtype=np.int64)
        target = rows["target_ord"].to_numpy(dtype=np.int64)
        cutoff = np.minimum(origin, target - 1)

        v2_block = sd.v2_block(seasons, area, origin)
        oracle, oracle_ledger = sd.oracle_block(weather, area, origin, horizon)
        oracle_ledger.insert(0, "area_id", area[oracle_ledger["row"].to_numpy()] if len(oracle_ledger) else [])
        oracle_ledger.insert(1, "target_ord", target[oracle_ledger["row"].to_numpy()] if len(oracle_ledger) else [])
        oracle_ledgers[horizon] = oracle_ledger.drop(columns="row")
        history_block = hist.build_history_block(history_index, area, origin, cutoff, history_names)
        history_frame = pd.DataFrame(history_block, columns=history_names)
        slots = hist.history_slot_sources(history_index, area, cutoff)
        persistence = sd.persistence_lookup(ledger, area, origin, target)
        overlap = set(base_columns) & (set(V2_FEATURES) | set(oracle_feature_names(horizon)) | set(history_names))
        if overlap:
            raise sd.DataContractError(f"feature name collision: {sorted(overlap)[:5]}")
        frame = pd.concat([rows, v2_block, oracle, history_frame, slots, persistence], axis=1)
        frame["history_cutoff_ord"] = cutoff
        frames[horizon] = frame
        schemas[(horizon, "A")] = list(base_columns)
        schemas[(horizon, "B")] = schemas[(horizon, "A")] + list(V2_FEATURES)
        schemas[(horizon, "C")] = schemas[(horizon, "B")] + oracle_feature_names(horizon)
        schemas[(horizon, "D")] = schemas[(horizon, "C")] + history_names

        for year, candidate_years in FOLDS.items():
            test_ledger = ledger.loc[ledger["target_ord"] // 12 == year]
            in_frame = set(zip(frame["area_id"], frame["target_ord"]))
            fs_keys = set(zip(fs["area_id"], fs["target_ord"]))
            verified = dict(zip(zip(frame["area_id"], frame["target_ord"]), frame["oracle_all_verified"]))
            for record in test_ledger.itertuples(index=False):
                key = (int(record.area_id), int(record.target_ord))
                if not record.valid_target:
                    status, reason = "excluded", f"target:{record.target_invalid_reason}"
                elif not record.valid_score:
                    status, reason = "excluded", "invalid_reported_phase"
                elif key not in fs_keys:
                    status, reason = "excluded", "missing_base_feature_row"
                elif key not in in_frame:
                    status, reason = "excluded", "not_in_model_frame"
                elif horizon > 0 and not verified[key]:
                    status, reason = "wider_only", "oracle_weather_unverified"
                else:
                    status, reason = "primary", None
                cohort_rows.append({"test_year": year, "horizon": horizon, "area_id": key[0], "target_ord": key[1], "status": status, "reason": reason})
            scorable = frame.loc[(frame["target_year"] == year) & frame["valid_score"]]
            for origin_ord, group in scorable.groupby("origin_ord"):
                pool = frame.loc[frame["target_year"].isin(candidate_years) & (frame["target_ord"] <= origin_ord)]
                job_rows.append(
                    {
                        "job_id": f"y{year}_h{horizon:02d}_o{sd.ord_label(origin_ord)}",
                        "test_year": year,
                        "horizon": horizon,
                        "origin_ord": int(origin_ord),
                        "origin_month": sd.ord_label(origin_ord),
                        "target_month": sd.ord_label(int(origin_ord) + horizon),
                        "candidate_years": list(candidate_years),
                        "n_eval_rows": int(len(group)),
                        "n_primary_rows": int((group["oracle_all_verified"] | (horizon == 0)).sum()),
                        "n_fit_pool": int(len(pool)),
                        "fit_pool_max_target": sd.ord_label(int(pool["target_ord"].max())) if len(pool) else None,
                    }
                )
        log(f"[prepare] H={horizon}: frame {frame.shape}, A/B/C/D widths {[len(schemas[(horizon, a)]) for a in ARMS]} ({time.time()-t0:.0f}s)")

    input_hashes = {name: (sd.sha256_file(path) if hash_inputs else "not_computed") for name, path in input_paths.items()}
    notes = {
        "somalia_areas": len(som),
        "ledger_keys": int(len(ledger)),
        "normalization_changed_valid_rows": int(ledger["normalization_changed"].sum()),
        "target_invalid_reasons": ledger.loc[~ledger["valid_target"], "target_invalid_reason"].value_counts().to_dict(),
        "history_invalid_reasons": ledger.loc[~ledger["valid_history"], "history_invalid_reason"].value_counts().to_dict(),
        "history_p5_filled": int(ledger["history_p5_filled"].sum()),
        "reported_vs_share_phase_disagreements": int(
            (ledger["valid_score"] & (ledger["overall_phase"] != ledger["share_derived_phase"])).sum()
        ),
        "weather_status_counts_from_2021": weather.loc[weather["month_ord"] >= (FIRST_MODEL_YEAR - 1) * 12, "weather_status"].value_counts().to_dict(),
        "v2_somalia_areas_without_rows": 0,
        "blocked_base_features": list(BLOCKED_BASE_FEATURES),
        "history_width": len(history_names),
    }
    return Prepared(
        input_paths=dict(input_paths),
        input_hashes=input_hashes,
        ledger=ledger,
        weather=weather,
        seasons=seasons,
        frames=frames,
        schemas=schemas,
        oracle_ledgers=oracle_ledgers,
        cohort_ledger=pd.DataFrame(cohort_rows),
        jobs=pd.DataFrame(job_rows),
        notes=notes,
    )


# --------------------------------------------------------------------------
# Execution
# --------------------------------------------------------------------------

_WORKER_STATE: Dict[str, object] = {}


def _arm_task(job: Mapping[str, object], arm: str, model_dir: Optional[str]) -> Dict[str, object]:
    prepared: Prepared = _WORKER_STATE["prepared"]
    config = _WORKER_STATE["config"]
    horizon = int(job["horizon"])
    frame = prepared.frames[horizon]
    eval_index = frame.index[(frame["target_year"] == job["test_year"]) & frame["valid_score"] & (frame["origin_ord"] == job["origin_ord"])]
    pool_index = frame.index[frame["target_year"].isin(job["candidate_years"]) & (frame["target_ord"] <= job["origin_ord"])]
    started = time.time()
    try:
        result = md.run_arm_job(job, arm, frame, prepared.schemas[(horizon, arm)], config, eval_index, pool_index, keep_models=model_dir is not None)
    except Exception as exc:  # a failing fit marks this cell incomplete; other cells are kept
        result = md.ArmJobResult(job_id=job["job_id"], arm=arm, status="failed", reason=f"{type(exc).__name__}: {exc}", selected_candidate=None)
    model_records = []
    if model_dir is not None:
        for model in result.final_models:
            stem = Path(model_dir) / f"{job['job_id']}_{arm}_{model.target}"
            if model.kind == "xgboost":
                path = stem.with_suffix(".ubj")
                model.model.save_model(str(path))
            else:
                path = stem.with_suffix(".json")
                path.write_text(json.dumps({"kind": "constant", "value": model.constant, "n_rows": model.n_rows}), encoding="utf-8")
            model_records.append({"job_id": job["job_id"], "arm": arm, "target": model.target, "kind": model.kind, "n_rows": model.n_rows, "path": path.name, "sha256": sd.sha256_file(path)})
    return {
        "job_id": job["job_id"],
        "arm": arm,
        "status": result.status,
        "reason": result.reason,
        "selected_candidate": result.selected_candidate,
        "seconds": time.time() - started,
        "inner_folds": result.inner_folds,
        "candidate_scores": result.candidate_scores,
        "validation_predictions": result.validation_predictions,
        "predictions": result.predictions,
        "fit_ledger": result.fit_ledger,
        "models": model_records,
    }


def arm_tasks(jobs: pd.DataFrame) -> List[Tuple[Dict[str, object], str]]:
    tasks = []
    for job in jobs.to_dict("records"):
        for arm in ARMS:
            if job["horizon"] == 0 and arm == "C":
                continue  # H=0: C is identical to B; its fit/predictions are reused.
            tasks.append((job, arm))
    return tasks


def execute(prepared: Prepared, config, workers: int, model_dir: Optional[Path], log=print, only_jobs: Optional[Sequence[str]] = None) -> List[Dict[str, object]]:
    _WORKER_STATE["prepared"] = prepared
    _WORKER_STATE["config"] = config
    jobs = prepared.jobs if only_jobs is None else prepared.jobs.loc[prepared.jobs["job_id"].isin(only_jobs)]
    tasks = arm_tasks(jobs)
    log(f"[execute] {len(tasks)} arm jobs on {workers} workers")
    results = []
    if workers <= 1:
        for job, arm in tasks:
            results.append(_arm_task(job, arm, str(model_dir) if model_dir else None))
            log(f"[execute] {job['job_id']} {arm}: {results[-1]['status']} {results[-1]['seconds']:.0f}s")
    else:
        import multiprocessing as mp

        with ProcessPoolExecutor(max_workers=workers, mp_context=mp.get_context("fork")) as pool:
            futures = {pool.submit(_arm_task, job, arm, str(model_dir) if model_dir else None): (job["job_id"], arm) for job, arm in tasks}
            for done, future in enumerate(as_completed(futures), start=1):
                results.append(future.result())
                log(f"[execute] {done}/{len(tasks)} {results[-1]['job_id']} {results[-1]['arm']}: {results[-1]['status']} {results[-1]['seconds']:.0f}s")
    for result in list(results):
        job = prepared.jobs.set_index("job_id").loc[result["job_id"]]
        if int(job["horizon"]) == 0 and result["arm"] == "B":
            clone = dict(result)
            clone["arm"] = "C"
            clone["reused_from"] = "B"
            for key in ("predictions", "validation_predictions", "fit_ledger"):
                if clone[key] is not None:
                    clone[key] = clone[key].assign(arm="C")
            clone["inner_folds"] = [dict(r, arm="C") for r in clone["inner_folds"]]
            clone["candidate_scores"] = [dict(r, arm="C") for r in clone["candidate_scores"]]
            results.append(clone)
    return sorted(results, key=lambda r: (r["job_id"], r["arm"]))


# --------------------------------------------------------------------------
# Evaluation tables
# --------------------------------------------------------------------------


def assemble_predictions(prepared: Prepared, results: Sequence[Mapping[str, object]]) -> pd.DataFrame:
    parts = [r["predictions"] for r in results if r["predictions"] is not None]
    if not parts:
        return pd.DataFrame()
    predictions = pd.concat(parts, ignore_index=True)
    jobs = prepared.jobs.set_index("job_id")
    predictions["horizon"] = jobs.loc[predictions["job_id"], "horizon"].to_numpy()
    predictions["test_year"] = jobs.loc[predictions["job_id"], "test_year"].to_numpy()
    return predictions


def evaluation_table(prepared: Prepared, predictions: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Dict[str, np.ndarray]]]:
    metrics_rows, contrast_rows = [], []
    bundles: Dict[str, Dict[str, np.ndarray]] = {}
    cohort = prepared.cohort_ledger
    truth_columns = ["area_id", "target_ord", "overall_phase", "actual_crisis", "q3", "persistence_available", "persistence_phase", "oracle_all_verified"]
    for year in FOLDS:
        for horizon in HORIZONS:
            frame = prepared.frames[horizon]
            keys = cohort.loc[(cohort["test_year"] == year) & (cohort["horizon"] == horizon)]
            primary_keys = keys.loc[keys["status"] == "primary", ["area_id", "target_ord"]]
            wider_keys = keys.loc[keys["status"].isin(["primary", "wider_only"]), ["area_id", "target_ord"]]
            truth = frame.loc[:, truth_columns]
            cohorts = {
                "primary": primary_keys.merge(truth, on=["area_id", "target_ord"]),
                "wider_labeled": wider_keys.merge(truth, on=["area_id", "target_ord"]),
            }
            cohorts["persistence_subset"] = cohorts["primary"].loc[cohorts["primary"]["persistence_available"]].reset_index(drop=True)
            arm_preds = {}
            for arm in ARMS:
                sub = predictions.loc[(predictions["test_year"] == year) & (predictions["horizon"] == horizon) & (predictions["arm"] == arm)] if len(predictions) else pd.DataFrame()
                arm_preds[arm] = sub
            for cohort_name, cohort_frame in cohorts.items():
                base = {"test_year": year, "horizon": horizon, "cohort": cohort_name, "n_rows": int(len(cohort_frame)), "n_areas": int(cohort_frame["area_id"].nunique()), "target_months": ";".join(sd.ord_labels(sorted(cohort_frame["target_ord"].unique()))), "cohort_sha256": ev.cohort_hash(cohort_frame[["area_id", "target_ord"]]) if len(cohort_frame) else None}
                if len(cohort_frame) == 0:
                    metrics_rows.append({**base, "specification": "all", "status": "unavailable", "reason": "empty cohort"})
                    continue
                arms_here = ARMS if cohort_name != "wider_labeled" else ("A", "B")
                vectors = {}
                complete = True
                for arm in arms_here:
                    merged = cohort_frame.merge(arm_preds[arm], on=["area_id", "target_ord"], how="left", validate="one_to_one") if len(arm_preds[arm]) else cohort_frame.assign(phase_pred=np.nan, q3_pred=np.nan)
                    if merged["phase_pred"].isna().any():
                        missing = int(merged["phase_pred"].isna().sum())
                        metrics_rows.append({**base, "specification": arm, "status": "incomplete", "reason": f"{missing} cohort rows without predictions"})
                        complete = False
                        continue
                    metrics_rows.append({**base, "specification": arm, "status": "ok", "reason": None, **ev.model_metrics(merged)})
                    vectors[arm] = merged["phase_pred"].to_numpy() >= 3
                if cohort_name == "persistence_subset":
                    metrics_rows.append({**base, "specification": "persistence", "status": "ok", "reason": None, **ev.persistence_metrics(cohort_frame)})
                    vectors["persistence"] = cohort_frame["persistence_phase"].to_numpy() >= 3
                if cohort_name in ("primary", "persistence_subset"):
                    metrics_rows.append({**base, "specification": "always_crisis", "status": "ok", "reason": None, **ev.always_crisis_metrics(cohort_frame)})
                    vectors["always_crisis"] = np.ones(len(cohort_frame), dtype=bool)
                if cohort_name == "wider_labeled":
                    continue
                contrasts = []
                if cohort_name == "primary":
                    contrasts += [(b, a) for a, b in (("A", "B"), ("B", "C"), ("C", "D"))]
                    contrasts += [(arm, "always_crisis") for arm in ARMS]
                else:
                    contrasts += [(arm, "persistence") for arm in ARMS] + [(arm, "always_crisis") for arm in ARMS]
                contrasts = [c for c in contrasts if c[0] in vectors and c[1] in vectors]
                rows, bundle = ev.paired_bootstrap(cohort_frame, cohort_frame["actual_crisis"].to_numpy() == 1, vectors, contrasts)
                bundle_key = f"y{year}_h{horizon:02d}_{cohort_name}"
                bundle["cohort_keys"] = cohort_frame[["area_id", "target_ord"]].to_numpy()
                bundles[bundle_key] = bundle
                for row in rows:
                    contrast_rows.append({**base, **row, "bootstrap_bundle": bundle_key, "comparison_complete": complete})
    return pd.DataFrame(metrics_rows), pd.DataFrame(contrast_rows), bundles


def runtime_identity() -> Dict[str, str]:
    import sklearn
    import xgboost

    return {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "sklearn": sklearn.__version__,
        "xgboost": xgboost.__version__,
        "executable": sys.executable,
        "platform": platform.platform(),
        "cpu_count": str(os.cpu_count()),
    }
