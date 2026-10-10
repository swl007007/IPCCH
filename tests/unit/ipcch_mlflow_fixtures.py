"""Tiny source-shaped fixture trees for the IPCCH Forecasting MLflow catalog tests.

Each builder writes files with the same names/columns as the real saved sources (compact
original + 2026 extension, launch, Somalia v4) into a temporary repo. Boosters are random bytes:
the catalog never loads models.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[2] / "IPCCHMLflow"))

METRICS8 = ["exact_phase_accuracy", "phase3plus_accuracy", "precision_phase3plus", "sensitivity_phase3plus", "f2_phase3plus",
            "r2_phase3plus", "mae_phase3plus", "ordinal_mae"]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def write(p: Path, data) -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, pd.DataFrame):
        if p.suffix == ".gz":
            with gzip.open(p, "wt", newline="") as f:
                data.to_csv(f, index=False)
        else:
            data.to_csv(p, index=False)
    elif isinstance(data, (dict, list)):
        p.write_text(json.dumps(data, indent=1))
    elif isinstance(data, bytes):
        p.write_bytes(data)
    else:
        p.write_text(str(data))
    return p


def keys_for(year: int, months=(1, 4, 7), areas=(101, 102, 103)) -> pd.DataFrame:
    rows = [{"area_id": a, "year": year, "month": m} for a in areas for m in months]
    return pd.DataFrame(rows)


def preds(year: int, seed: int, truth_shift: float = 0.0) -> pd.DataFrame:
    k = keys_for(year)
    rng = np.random.default_rng(year)  # truth depends on keys only, not on the arm
    k["overall_phase"] = rng.integers(1, 5, len(k))
    k["phase3_worse"] = np.round(rng.random(len(k)), 6) + truth_shift
    k["overall_phase_pred"] = np.random.default_rng(seed).integers(1, 5, len(k))
    return k


def batch(run_dir: Path, year: int, seed: int) -> dict:
    bd = run_dir / "batches" / str(year)
    arts = {}
    for t in ("phase2_worse", "phase3_worse", "phase4_worse", "phase5_worse"):
        arts[f"model_{t}.ubj"] = sha(write(bd / f"model_{t}.ubj", os.urandom(64) + f"{seed}{year}{t}".encode()))
    arts["predictions.csv"] = sha(write(bd / "predictions.csv", preds(year, seed)))
    arts["fit_keys.csv.gz"] = sha(write(bd / "fit_keys.csv.gz", keys_for(year - 1)))
    write(bd / "batch_record.json", {"block_year": year, "artifacts": arts})
    return arts


def metrics_overall(years, seed) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for y in [*map(str, years), "pooled"]:
        r = {"scope": "overall", "test_year": y, "n_samples": 9 if y != "pooled" else 9 * len(years)}
        for m in METRICS8:
            r[m], r[f"{m}_status"], r[f"{m}_reason"] = float(rng.random()), "ok", None
        rows.append(r)
    return pd.DataFrame(rows)


RUNS = [("compact_baseline", 0, 296), ("compact_baseline", 6, 296), ("compact_weather_oracle", 6, 308)]


def compact_original(repo: Path, root="results/experiments/fx_compact_v1", years=(2022, 2023)) -> str:
    base = repo / root
    for arm, h, n in RUNS:
        rd = base / "runs" / arm / f"{h}m"
        for y in years:
            batch(rd, y, seed=hash((arm, h)) % 1000)
            write(rd / "predictions" / f"predictions_{y}.csv", preds(y, seed=hash((arm, h)) % 1000))
        write(rd / "run_metadata.json", {"feature_count": n, "features": [f"f{i}" for i in range(n)],
                                         "fingerprint_payload": {"dataset_sha256": "d" * 64, "manifest_sha256": "m" * 64},
                                         "split_rule": "fixture annual blocks"})
        write(rd / "metrics" / "metrics_overall.csv", metrics_overall(years, seed=h + n))
    write(base / "logs" / "suite_ledger.jsonl", '{"status": "COMPLETE"}\n')
    return root


def compact_extension(repo: Path, orig_root: str, root="results/experiments/fx_compact_ext", years=(2022, 2023)) -> str:
    base, orig = repo / root, repo / orig_root
    rows, deltas = [], []
    for arm, h, n in RUNS:
        rd = base / "runs" / arm / f"{h}m"
        batch(rd, 2026, seed=7)
        sby = {str(y): {"artifacts": json.loads((orig / "runs" / arm / f"{h}m" / "batches" / str(y) / "batch_record.json").read_text())["artifacts"]}
               for y in years}
        sby["2026"] = {"fitted_here": True}
        write(rd / "run_metadata.json", {"feature_count": n, "features": [f"f{i}" for i in range(n)], "reused_years": list(years),
                                         "fitted_here_years": [2026], "sources_by_year": sby,
                                         "new_batch": {"fit_origin_month": "2025-07", "fit_label_cutoff_month": "2025-07"},
                                         "fingerprint_payload": {"parent_fingerprint_payload": {"dataset_sha256": "d" * 64, "manifest_sha256": "m" * 64},
                                                                 "fit_valid_keys_sha256": "k" * 64}})
        allp = pd.concat([preds(y, 1) for y in (*years, 2026)], ignore_index=True)
        write(rd / "predictions" / "predictions_2022_2026.csv", allp)
        for per in (*map(str, years), "2026", "pooled_2022_2025", "pooled_2022_2026"):
            for m in METRICS8:
                rows.append({"run_id": f"{arm}/{h}m", "arm": arm, "horizon": h, "scope": "global", "region": None, "region_name": None,
                             "period": per, "metric": m, "value": 0.5 + h / 100, "status": "ok", "reason": None, "n_rows": 9,
                             "n_areas": 3})
        if arm == "compact_weather_oracle":
            for per in ("2026", "pooled_2022_2026"):
                deltas.append({"horizon": h, "scope": "global", "region": None, "region_name": None, "period": per, "metric": "f2_phase3plus",
                               "contrast": "compact_weather_oracle - compact_baseline", "oracle_value": 0.6, "baseline_value": 0.56,
                               "delta": 0.04, "status": "ok", "reason": None})
    write(base / "report" / "all_metrics_long.csv", pd.DataFrame(rows))
    write(base / "report" / "global_deltas.csv", pd.DataFrame(deltas))
    return root


def launch(repo: Path, root="results/launch/fx_launch") -> str:
    base = repo / root
    runs = [("compact_baseline", 0, 296, "2026-04"), ("compact_baseline", 6, 296, "2026-10"), ("compact_cds_weather", 6, 308, "2026-10")]
    summ, diffs = [], []
    for arm, h, n, target in runs:
        rd = base / "runs" / arm / f"{h}m"
        arts = {}
        for t in ("phase2_worse", "phase3_worse", "phase4_worse", "phase5_worse"):
            arts[f"model_{t}.ubj"] = sha(write(rd / f"model_{t}.ubj", os.urandom(32)))
        for name, df in (("fit_keys.csv.gz", keys_for(2025)), ("fit_targets.csv.gz", keys_for(2025)), ("fit_weights.csv.gz", keys_for(2025)),
                         ("inference_features.csv.gz", keys_for(2026, months=(4,)))):
            arts[name] = sha(write(rd / name, df))
        arts["feature_schema.json"] = sha(write(rd / "feature_schema.json", {"features": [f"f{i}" for i in range(n)]}))
        p = pd.DataFrame({"area_id": [101, 102, 103], "target_month": target})
        arts["predictions_raw.csv"] = sha(write(rd / "predictions_raw.csv", p))
        arts["run_metadata.json"] = sha(write(rd / "run_metadata.json", {"feature_count": n, "features": [f"f{i}" for i in range(n)],
                                                                         "fingerprint_payload": {"training_dataset_sha256": "t" * 64}}))
        write(rd / "artifact_record.json", {"run_id": f"{arm}/{h}m", "artifacts": arts})
        r = {"display_arm": arm, "source_run_id": f"{arm}/{h}m", "horizon": h, "target_month": target, "population_raw": 1000.0,
             "count_raw_p3plus": 100.0 + h, "share_raw_p3plus": 0.1, "share_raw_status": "ok", "share_raw_reason": None}
        summ.append(r)
    summ.append({**summ[0], "display_arm": "compact_cds_weather", "source_run_id": "compact_baseline/0m"})
    for h, t in ((0, "2026-04"), (6, "2026-10")):
        diffs.append({"horizon": h, "contrast": "compact_cds_weather - compact_baseline", "target_month": t,
                      "delta_count_raw_p3plus": 0.0 if h == 0 else 3.0, "delta_status": "ok"})
    write(base / "population" / "global_population_summary.csv", pd.DataFrame(summ))
    write(base / "population" / "global_population_paired_differences.csv", pd.DataFrame(diffs))
    return root


def somalia_v4(repo: Path, root="results/experiments/somalia_oracle/fx_v4", copy_q3: float = 0.5) -> str:
    """One setting (augmented), lead 0, years 2022 complete / 2023 incomplete / 2024 empty, plus pooled."""
    base = repo / root
    jobs, inv, st = [], [], []
    for y in (2022, 2023):
        j = f"augmented_y{y}_h00_o{y}-01"
        jobs.append({"job_id": j, "data_setting": "augmented", "outer_year": y, "horizon": 0, "origin_ord": y * 12})
        for t in ("q2", "q3_direct", "q4", "q5"):
            p = write(base / "models" / f"{j}_{t}.ubj", os.urandom(40))
            inv.append({"job_id": j, "target": t, "kind": "xgboost", "path": p.name, "sha256": sha(p), "feature_order_sha256": "x"})
        st.append({"job_id": j, "data_setting": "augmented", "outer_year": y, "horizon": 0, "formulation": "direct", "status": "completed"})
    write(base / "models" / "model_inventory.csv", pd.DataFrame(inv))
    write(base / "fits" / "final_status.csv", pd.DataFrame(st))
    write(base / "ledgers" / "jobs.csv", pd.DataFrame(jobs))
    write(base / "features" / "feature_schema.json", {"h00_D": ["a", "b", "c"]})
    for rel in ("fits/final_fit_ledger.csv.gz", "fits/calibration_mappings.csv", "selection/selected_recipes.csv",
                "selection/candidate_scores.csv", "selection/contexts.csv", "selection/pool_specs.csv.gz", "selection/oof_units.csv.gz",
                "selection/oof_predictions.csv.gz", "selection/calibration_keys.csv.gz", "selection/final_calibration_keys.csv.gz",
                "selection/history_overrides.csv.gz", "features/final_override_features.csv.gz"):
        write(base / rel, pd.DataFrame({"x": [1]}))
    coh = []
    for y, n, copies in ((2022, 3, 1), (2023, 3, 0)):
        for i in range(n):
            is_copy = i < copies
            coh.append({"data_setting": "augmented", "outer_year": y, "horizon": 0, "area_id": 200 + i, "target_ord": y * 12 + i,
                        "is_copy": is_copy, "source_family": "anl:1" if is_copy else f"local:{y}", "original_month_ord": y * 12 if is_copy else None,
                        "status": "primary", "reason": None})
    coh = pd.DataFrame(coh)
    write(base / "ledgers" / "cohort_ledger.csv.gz", coh)
    lab = coh[["area_id", "target_ord"]].copy()
    lab["overall_phase"], lab["actual_crisis"] = 3, 1.0
    lab["q3"] = [copy_q3 if c else 0.3 for c in coh.is_copy]
    write(base / "ledgers" / "label_ledger.csv.gz", lab)
    import extract as X
    slots, annual = [], []
    for y in (2022, 2023, 2024):
        c = coh[coh.outer_year == y]
        h_ = X.v4_hash(c) if len(c) else X.sha_bytes(b"")
        slots.append({"data_setting": "augmented", "outer_year": y, "horizon": 0, "excluded": 0, "primary": len(c), "cohort_sha256": h_})
        status = {2022: "complete", 2023: "incomplete", 2024: "empty_cohort"}[y]
        reason = {2022: None, 2023: "1 of 3 required final predictions missing or unavailable", 2024: "no source-eligible rows"}[y]
        annual.append({"data_setting": "augmented", "outer_year": y, "horizon": 0, "n_cohort": len(c), "n_primary": len(c),
                       "cohort_sha256": h_, "status": status, "reason": reason, "n": len(c) if y == 2022 else (2 if y == 2023 else None),
                       "final_r2": 0.4 if y == 2022 else None, "final_r2_reason": None if y == 2022 else reason,
                       "bin_f1": 0.7 if y == 2022 else None})
    write(base / "ledgers" / "cohort_slots.csv", pd.DataFrame(slots))
    write(base / "metrics" / "annual_metrics.csv", pd.DataFrame(annual))
    write(base / "metrics" / "pooled_metrics.csv", pd.DataFrame([{
        "data_setting": "augmented", "horizon": 0, "years": "2022;2023;2024", "status": "incomplete", "reason": "annual slots incomplete: 2023",
        "rows_by_year": None, "cohort_sha256": None, "n": None, "final_r2": None, "bin_f1": None}]))
    return root


def source(key, root, fmt, families, role="original", label="snapshot fixture", **kw) -> dict:
    return {"source_key": key, "root": root, "stage": kw.pop("stage", "historical"), "model_scope": kw.pop("model_scope", "global"),
            "format": fmt, "families": families, "snapshot_role": role, "snapshot_label": label, "eval_group": "fixture cohort",
            "status_text": "Fixture source.", "fit_date_evidence": "fixture", "cited": [], "exclude": [{"glob": "**/*.pid", "reason": "pid"}], **kw}


def config(sources: list, expected: dict | None = None) -> dict:
    return {"schema_version": "fixture", "forbidden_content": ["climate2015_v1", "nigeria_weather_land"],
            "expected": expected or {}, "sources": sources}


def compact_config(repo: Path) -> dict:
    o = compact_original(repo)
    e = compact_extension(repo, o)
    alias = [{"arm": "compact_weather_oracle", "of": "compact_baseline"}]
    return config([
        source("fx_orig", o, "modern_runs", ["compact_climate_global"], label="snapshot original", metrics_format="metrics_overall",
               h0_aliases=alias),
        source("fx_ext", e, "modern_runs", ["compact_climate_global"], role="extension", label="snapshot extended", metrics_format="long",
               metrics_long="report/all_metrics_long.csv", deltas=["report/global_deltas.csv"], extends="fx_orig", supersedes="fx_orig",
               training_qualifier="extended", h0_aliases=alias),
    ])
