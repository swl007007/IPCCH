"""Independent verification, metric replay and paired comparison for origin_safe_climate_idp_v1.

Uses a separate code path from the runner: re-hashes every batch artifact, rechecks fit cutoffs/weights and
cross-arm fit-key equality from the saved key files, re-derives classes and normalized targets itself, reloads
model bundles to reproduce saved predictions on sampled batches, and replays metrics with scikit-learn from the
saved unrounded predictions (round-trip float parsing). Writes machine-readable outputs under results/ and a
markdown report under reports/.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

PROJECT_ROOT = next(path for path in Path(__file__).resolve().parents if (path / "src").exists())
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, fbeta_score, mean_absolute_error, precision_score, r2_score, recall_score

from ipcch import paths

VERSION = "origin_safe_climate_idp_v1"
ARMS = ("climate_no_history", "climate_safe_history", "climate_safe_history_idp")
HORIZONS = (0, 3, 6, 12)
YEARS = (2022, 2023, 2024, 2025)
KEYS = ["area_id", "year", "month"]
TARGETS = ("phase2_worse", "phase3_worse", "phase4_worse", "phase5_worse")
PREDS = ("phase2_pred", "phase3_pred", "phase4_pred", "phase5_pred")
SHARES = tuple(f"phase{k}_percent" for k in range(1, 6))
RESULTS = paths.RESULTS_DIR / "experiments" / VERSION
REPORTS = paths.REPORTS_DIR / VERSION
MANIFEST = paths.SOURCE_DATA_DIR / "assembled_IPCCH" / "model_ready" / VERSION / f"{VERSION}_manifest.json"
OLD_CONTEXT = paths.RESULTS_DIR / "experiments" / "deep_feature_weight_decay_forecasting" / "climate2015_v1" / "comparison_metrics.csv"
METRICS = ("accuracy", "precision_phase3plus", "sensitivity_phase3plus", "f2_phase3plus", "r2_phase3plus", "mae_phase3plus", "ordinal_mae")


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def ym_ord(text: str) -> int:
    y, m = (int(x) for x in text.split("-"))
    return y * 12 + m - 1


def classes(pred: pd.DataFrame, threshold: float) -> np.ndarray:
    scores = pred[list(PREDS)].to_numpy(dtype=float)
    conditions = [scores[:, 3] >= threshold, scores[:, 2] >= threshold, scores[:, 1] >= threshold, scores[:, 0] >= threshold]
    return np.select(conditions, [5, 4, 3, 2], default=1)


def replay(df: pd.DataFrame) -> dict:
    """scikit-learn replay; undefined metrics are None with a reason."""
    out = {"n_samples": len(df)}
    y, p = df["overall_phase"].to_numpy(dtype=int), df["overall_phase_pred"].to_numpy(dtype=int)
    yb, pb = y >= 3, p >= 3
    out["accuracy"] = accuracy_score(y, p)
    out["precision_phase3plus"] = precision_score(yb, pb, zero_division=np.nan) if pb.any() else None
    out["sensitivity_phase3plus"] = recall_score(yb, pb, zero_division=np.nan) if yb.any() else None
    defined = out["precision_phase3plus"] is not None and out["sensitivity_phase3plus"] is not None and (yb & pb).any()
    out["f2_phase3plus"] = fbeta_score(yb, pb, beta=2) if defined else None  # 0/0 when there is no true positive
    t, s = df["phase3_worse"].to_numpy(dtype=float), df["phase3_pred"].to_numpy(dtype=float)
    out["r2_phase3plus"] = r2_score(t, s) if len(t) >= 2 and np.unique(t).size >= 2 else None
    out["mae_phase3plus"] = mean_absolute_error(t, s)
    out["ordinal_mae"] = float(np.abs(y - p).mean())
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--manifest", default=str(MANIFEST))
    parser.add_argument("--reload-models-per-run", type=int, default=2, help="batches per arm/horizon whose bundles are reloaded")
    args = parser.parse_args()
    manifest = json.loads(Path(args.manifest).read_text())
    vdir = RESULTS / "verification"
    vdir.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    cohort = pd.read_csv(manifest["cohort"]["path"])
    eval_keys = cohort.loc[cohort["eval_key"], KEYS].reset_index(drop=True)
    labels = None
    problems, checks = [], {"batches": 0, "artifacts_rehashed": 0, "models_reloaded": 0, "fit_rows_checked": 0}
    fit_hash = {}
    predictions = {}
    replay_rows, saved_rows = [], []
    rng = np.random.default_rng(7)
    for horizon in HORIZONS:
        entry = manifest["horizons"][str(horizon)]
        data = pd.read_csv(entry["dataset"]["path"], float_precision="round_trip", low_memory=False)
        if labels is None:
            labels = data[KEYS + ["overall_phase", *SHARES]].copy()
            shares = labels[list(SHARES)].to_numpy(dtype=float)
            total = shares.sum(axis=1)
            norm = shares / total[:, None]
            for k, column in zip((2, 3, 4, 5), TARGETS):
                labels[column] = norm[:, k - 1:].sum(axis=1)
            labels["ord"] = labels["year"] * 12 + labels["month"] - 1
            valid = cohort["share_valid"].to_numpy(dtype=bool)
        elif not data[KEYS + ["overall_phase"]].equals(labels[KEYS + ["overall_phase"]]):
            problems.append(f"h{horizon}: label rows differ across horizons")
        lookup = data.set_index(KEYS)
        for arm in ARMS:
            run = RESULTS / "runs" / arm / f"{horizon}m"
            meta_path = run / "run_metadata.json"
            if not meta_path.exists():
                problems.append(f"{arm} h{horizon}: missing run_metadata.json")
                continue
            meta = json.loads(meta_path.read_text())
            if meta.get("status") != "COMPLETE":
                problems.append(f"{arm} h{horizon}: status {meta.get('status')}")
            features = entry["arms"][arm]["features"]
            if meta["features"] != features:
                problems.append(f"{arm} h{horizon}: fitted feature order differs from manifest")
            threshold, half_life = meta["phase_threshold"], meta["half_life_months"]
            frames = []
            reload_targets = set(rng.choice([b["target_month"] for b in meta["batches"]], size=min(args.reload_models_per_run, len(meta["batches"])), replace=False))
            months = sorted(b["target_month"] for b in meta["batches"])
            if months != [f"{y}-{m:02d}" for y in YEARS for m in range(1, 13)]:
                problems.append(f"{arm} h{horizon}: batch months incomplete")
            for record in meta["batches"]:
                bdir = run / "batches" / record["target_month"]
                disk = json.loads((bdir / "batch_record.json").read_text())
                if disk != json.loads(json.dumps(record)) or disk["fingerprint"] != meta["fingerprint"]:
                    problems.append(f"{arm} h{horizon} {record['target_month']}: batch record differs from run metadata")
                for name, digest in disk["artifacts"].items():
                    checks["artifacts_rehashed"] += 1
                    if sha(bdir / name) != digest:
                        problems.append(f"{bdir / name}: sha256 mismatch")
                t = ym_ord(record["target_month"])
                origin, cutoff = t - horizon, t - max(horizon, 1)
                if ym_ord(record["origin_month"]) != origin or ym_ord(record["label_cutoff_month"]) != cutoff:
                    problems.append(f"{bdir}: origin/cutoff inconsistent with horizon")
                fk = pd.read_csv(bdir / "fit_keys.csv.gz", float_precision="round_trip")
                ford = fk["year"].to_numpy() * 12 + fk["month"].to_numpy() - 1
                expected_fit = labels.loc[valid & (labels["ord"] <= cutoff).to_numpy(), KEYS].reset_index(drop=True)
                if not fk[KEYS].equals(expected_fit):
                    problems.append(f"{bdir}: fit keys differ from all valid labels <= min(O, T-1)")
                if ford.max() > cutoff or (fk["age_months"].to_numpy() != origin - ford).any() or \
                        not np.allclose(fk["sample_weight"].to_numpy(), 0.5 ** ((origin - ford) / half_life), rtol=0, atol=1e-15):
                    problems.append(f"{bdir}: fit cutoff/age/weight check failed")
                checks["fit_rows_checked"] += len(fk)
                digest = hashlib.sha256(fk[KEYS].to_csv(index=False).encode()).hexdigest()
                fit_hash.setdefault((horizon, record["target_month"]), set()).add(digest)
                pred = pd.read_csv(bdir / "predictions.csv", float_precision="round_trip")
                expected_eval = eval_keys[(eval_keys["year"] * 12 + eval_keys["month"] - 1) == t].reset_index(drop=True)
                if not pred[KEYS].equals(expected_eval):
                    problems.append(f"{bdir}: evaluation keys differ from the frozen cohort")
                truth = lookup.loc[list(pred[KEYS].itertuples(index=False, name=None))]
                if not np.array_equal(truth["overall_phase"].to_numpy(dtype=float), pred["overall_phase"].to_numpy(dtype=float)):
                    problems.append(f"{bdir}: truth differs from reported phase")
                lab = labels.set_index(KEYS).loc[list(pred[KEYS].itertuples(index=False, name=None))]
                if not np.allclose(lab[list(TARGETS)].to_numpy(), pred[list(TARGETS)].to_numpy(), rtol=0, atol=1e-12):
                    problems.append(f"{bdir}: normalized targets differ")
                if not np.array_equal(classes(pred, threshold), pred["overall_phase_pred"].to_numpy()):
                    problems.append(f"{bdir}: class assignment differs from unrounded >= threshold rule")
                if record["target_month"] in reload_targets:
                    import xgboost as xgb

                    X = truth[features]
                    for target, column in zip(TARGETS, PREDS):
                        booster = xgb.Booster()
                        booster.load_model(str(bdir / f"model_{target}.ubj"))
                        if list(booster.feature_names) != features:
                            problems.append(f"{bdir}: model feature names differ")
                        again = booster.predict(xgb.DMatrix(X, feature_names=features))
                        if not np.allclose(again, pred[column].to_numpy(), rtol=0, atol=1e-6):
                            problems.append(f"{bdir}: reloaded {target} model does not reproduce saved predictions")
                        checks["models_reloaded"] += 1
                frames.append(pred)
                checks["batches"] += 1
            if not frames:
                continue
            allpred = pd.concat(frames, ignore_index=True)
            predictions[(arm, horizon)] = allpred
            for year in (*YEARS, "pooled"):
                part = allpred if year == "pooled" else allpred[allpred["year"] == year]
                replay_rows.append({"arm": arm, "horizon": horizon, "test_year": year, **replay(part)})
            saved = pd.read_csv(run / "metrics" / "metrics_overall.csv")
            saved["arm"], saved["horizon"] = arm, horizon
            saved_rows.append(saved)
    for key, digests in fit_hash.items():
        if len(digests) != 1:
            problems.append(f"h{key[0]} {key[1]}: fit keys differ across arms")
    truth_ref = None
    for key, pred in predictions.items():
        t = pred.sort_values(KEYS)[KEYS + ["overall_phase", *TARGETS]].reset_index(drop=True)
        if truth_ref is None:
            truth_ref = t
        elif not t.equals(truth_ref):
            problems.append(f"{key}: truth differs across arms/horizons")
        if len(pred) != len(eval_keys) or pred.duplicated(KEYS).any():
            problems.append(f"{key}: predictions do not cover the frozen keys exactly once")

    replayed = pd.DataFrame(replay_rows)
    replayed.to_csv(vdir / "metrics_replay.csv", index=False)
    agreement = []
    if saved_rows:
        saved = pd.concat(saved_rows, ignore_index=True)
        saved["test_year"] = saved["test_year"].astype(str)
        merged = replayed.assign(test_year=replayed["test_year"].astype(str)).merge(saved, on=["arm", "horizon", "test_year"], suffixes=("_replay", "_run"))
        for metric in METRICS:
            a, b = merged[f"{metric}_replay"].astype(float), merged[f"{metric}_run"].astype(float)
            both_nan = a.isna() & b.isna()
            diff = (a - b).abs().where(~both_nan, 0.0)
            agreement.append({"metric": metric, "cells": len(merged), "max_abs_diff": float(diff.max()), "nan_pattern_equal": bool((a.isna() == b.isna()).all())})
            if diff.max() > 1e-12 or not (a.isna() == b.isna()).all():
                problems.append(f"metric replay disagrees for {metric}")
    pd.DataFrame(agreement).to_csv(vdir / "metrics_replay_agreement.csv", index=False)

    deltas = []
    for (label, a, b) in (("history: safe_history - no_history", "climate_safe_history", "climate_no_history"),
                          ("idp: safe_history_idp - safe_history", "climate_safe_history_idp", "climate_safe_history")):
        for horizon in HORIZONS:
            for year in (*YEARS, "pooled"):
                ra = replayed[(replayed.arm == a) & (replayed.horizon == horizon) & (replayed.test_year == year)]
                rb = replayed[(replayed.arm == b) & (replayed.horizon == horizon) & (replayed.test_year == year)]
                if ra.empty or rb.empty:
                    continue
                row = {"comparison": label, "horizon": horizon, "test_year": year, "n_samples": int(ra["n_samples"].iloc[0])}
                for metric in METRICS:
                    x, y = ra[metric].iloc[0], rb[metric].iloc[0]
                    row[metric] = None if x is None or y is None or pd.isna(x) or pd.isna(y) else float(x) - float(y)
                deltas.append(row)
    deltas = pd.DataFrame(deltas)
    deltas.to_csv(vdir / "paired_deltas.csv", index=False)

    coverage = []
    for horizon in HORIZONS:
        h = manifest["horizons"][str(horizon)]
        coverage.append({"horizon": horizon, "eval_keys": len(eval_keys),
                         "history_count_distribution": json.dumps(h["history_count_distribution_eval"]),
                         "history1_age_median": h["history_source_age_months_eval"]["history_1"].get("50%"),
                         "idp_present_share": h["idp_present_eval"] / len(eval_keys),
                         "idp_age_median": h["idp_age_months_eval"].get("50%"), "idp_age_max": h["idp_age_months_eval"].get("max"),
                         "climate_new_nan_share": h["climate_new_nan_share_eval"],
                         "feature_counts": json.dumps({a: v["feature_count"] for a, v in h["arms"].items()})})
    pd.DataFrame(coverage).to_csv(vdir / "coverage.csv", index=False)
    summary = {"problems": problems, "passed": not problems, **checks, "eval_keys": len(eval_keys),
               "runs_found": len(predictions), "expected_runs": len(ARMS) * len(HORIZONS)}
    (vdir / "verification_summary.json").write_text(json.dumps(summary, indent=2))
    write_report(replayed, deltas, pd.DataFrame(coverage), summary, manifest)
    print(json.dumps({k: v for k, v in summary.items() if k != "problems"}, indent=2))
    for p in problems[:50]:
        print("PROBLEM:", p)
    return 0 if not problems and len(predictions) == len(ARMS) * len(HORIZONS) else 1


def fmt(value) -> str:
    return "undefined" if value is None or pd.isna(value) else f"{value:.4f}"


def write_report(replayed: pd.DataFrame, deltas: pd.DataFrame, coverage: pd.DataFrame, summary: dict, manifest: dict) -> None:
    lines = [f"# {VERSION}: origin-safe global climate, safe IPC history and national IDP", "",
             "Machine-readable sources: `results/experiments/origin_safe_climate_idp_v1/verification/`. "
             "All metrics are replayed with scikit-learn from saved unrounded predictions.", "",
             f"Verification passed: `{summary['passed']}`; runs {summary['runs_found']}/{summary['expected_runs']}; "
             f"batches {summary['batches']}; artifacts re-hashed {summary['artifacts_rehashed']}; models reloaded {summary['models_reloaded']}.", ""]
    for horizon in HORIZONS:
        lines += [f"## H = {horizon} months", "", "| arm | year | n | accuracy | precision 3+ | recall 3+ | F2 3+ | R² 3+ | MAE 3+ | ordinal MAE |",
                  "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
        for _, r in replayed[replayed.horizon == horizon].iterrows():
            lines.append(f"| {r.arm} | {r.test_year} | {r.n_samples} | " + " | ".join(fmt(r[m]) for m in METRICS) + " |")
        lines.append("")
    lines += ["## Paired differences (same frozen keys, same per-origin fitting keys)", "",
              "| comparison | H | year | accuracy | precision 3+ | recall 3+ | F2 3+ | R² 3+ | MAE 3+ | ordinal MAE |",
              "|---|---:|---|---:|---:|---:|---:|---:|---:|---:|"]
    for _, r in deltas.iterrows():
        lines.append(f"| {r.comparison} | {r.horizon} | {r.test_year} | " + " | ".join(fmt(r[m]) for m in METRICS) + " |")
    lines += ["", "## Coverage on the frozen evaluation keys", "", coverage.to_markdown(index=False) if hasattr(coverage, "to_markdown") else coverage.to_string(index=False), "",
              "## Limits", ""] + [f"- {x}" for x in manifest["limits"]] + [
              "- Single seed (42), no confidence intervals: differences are point estimates on one fit per origin.",
              "- Old climate2015_v1 / baseline results used annual target-year fits, legacy history and rounded, row-dropping postprocessing; "
              "they are context, not a paired baseline, and differences mix timing, target-normalization and postprocessing corrections.", ""]
    (REPORTS / "report.md").write_text("\n".join(lines))


if __name__ == "__main__":
    raise SystemExit(main())
