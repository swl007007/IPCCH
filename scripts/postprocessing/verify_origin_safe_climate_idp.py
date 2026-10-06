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


def independent_history(labels: pd.DataFrame, horizon: int) -> np.ndarray:
    """Latest three reported phases <= min(O, T-1) via merge_asof + within-area positions (not the builder path)."""
    obs = labels.loc[labels["overall_phase"].isin([1, 2, 3, 4, 5]), ["area_id", "ord", "overall_phase"]].sort_values(["area_id", "ord"]).reset_index(drop=True)
    obs["pos"] = obs.groupby("area_id").cumcount()
    rows = pd.DataFrame({"row": np.arange(len(labels)), "area_id": labels["area_id"].to_numpy(), "cut": labels["ord"].to_numpy() - max(horizon, 1)})
    hit = pd.merge_asof(rows.sort_values("cut"), obs[["area_id", "ord", "pos"]].sort_values("ord"), left_on="cut", right_on="ord",
                        by="area_id", direction="backward").sort_values("row")
    by_pos = obs.set_index(["area_id", "pos"])["overall_phase"]
    out = np.full((len(labels), 3), np.nan)
    for k in range(3):
        pos = hit["pos"].to_numpy() - k
        ok = ~np.isnan(pos) & (pos >= 0)
        out[ok, k] = by_pos.reindex(pd.MultiIndex.from_arrays([hit["area_id"].to_numpy()[ok], pos[ok].astype(int)])).to_numpy()
    return out


def independent_idp(labels: pd.DataFrame, horizon: int, idp_raw: pd.DataFrame, iso_by_area: pd.Series) -> np.ndarray:
    rep = idp_raw.loc[idp_raw["idp_ind"].notna(), ["admin0Pcode", "year", "month", "idp_ind"]].copy()
    rep["rord"] = rep["year"] * 12 + rep["month"] - 1
    rows = pd.DataFrame({"row": np.arange(len(labels)), "iso3": iso_by_area.reindex(labels["area_id"]).to_numpy(),
                         "origin": labels["ord"].to_numpy() - horizon})
    known = rows["iso3"].notna()
    hit = pd.merge_asof(rows[known].sort_values("origin"), rep.rename(columns={"admin0Pcode": "iso3"})[["iso3", "rord", "idp_ind"]].sort_values("rord"),
                        left_on="origin", right_on="rord", by="iso3", direction="backward").sort_values("row")
    out = np.full((len(labels), 2), np.nan)
    out[hit["row"].to_numpy(), 0] = hit["idp_ind"].to_numpy()
    out[hit["row"].to_numpy(), 1] = (hit["origin"] - hit["rord"]).to_numpy()
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
    idp_raw = pd.read_csv(manifest["inputs"]["idp_admin0_monthly"]["path"])
    iso_by_area = pd.read_csv(manifest["inputs"]["country_lookup"]["path"]).set_index("area_id")["iso3"]
    panel_keys = pd.read_csv(manifest["inputs"]["interim"]["path"], usecols=["admin_code", "year", "month"])
    last_panel = (panel_keys["year"] * 12 + panel_keys["month"] - 1).groupby(panel_keys["admin_code"]).max()
    del panel_keys
    checks_dir = RESULTS / "input_checks"
    retained_by_h, climate_by_h = {}, {}
    for horizon in HORIZONS:
        cls = pd.read_csv(checks_dir / f"feature_classification_h{horizon}.csv")
        retained_by_h[horizon] = set(cls.loc[cls["decision"] == "retained", "feature"])
        climate_by_h[horizon] = set(pd.read_csv(checks_dir / f"climate_manifest_h{horizon}.csv")["feature_name"])
    tail_rows = []
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
        hist = independent_history(labels, horizon)
        if not np.array_equal(hist, data[[f"overall_phase_history_{k}" for k in (1, 2, 3)]].to_numpy(dtype=float), equal_nan=True):
            problems.append(f"h{horizon}: dataset history differs from the independent latest-three replay")
        idp = independent_idp(labels, horizon, idp_raw, iso_by_area)
        if not np.array_equal(idp, data[["idp_admin0_latest_stock", "idp_admin0_latest_age_months"]].to_numpy(dtype=float), equal_nan=True):
            problems.append(f"h{horizon}: dataset IDP differs from the independent DTM replay")
        checks["independent_history_idp_rows"] = checks.get("independent_history_idp_rows", 0) + len(data)
        tail = labels["ord"].to_numpy() + 12 - horizon > last_panel.reindex(labels["area_id"]).to_numpy()
        inherited_scope = [c for c in entry["arms"]["climate_no_history"]["features"] if c.endswith(f"_s{horizon}") and c in retained_by_h[horizon]] if horizon != 12 else []
        new_climate = [c for c in entry["arms"]["climate_no_history"]["features"] if c in climate_by_h[horizon]]
        ev = cohort["eval_key"].to_numpy(dtype=bool)
        for year in YEARS:
            m = ev & (labels["year"].to_numpy() == year)
            row = {"horizon": horizon, "test_year": year, "eval_rows": int(m.sum()), "carrier_tail_rows": int((m & tail).sum())}
            if inherited_scope:
                block = data.loc[m, inherited_scope].isna().to_numpy()
                row["inherited_scope_nan_share"] = float(block.mean())
                row["inherited_scope_nan_share_tail"] = float(data.loc[m & tail, inherited_scope].isna().to_numpy().mean()) if (m & tail).any() else None
                row["inherited_scope_nan_share_non_tail"] = float(data.loc[m & ~tail, inherited_scope].isna().to_numpy().mean()) if (m & ~tail).any() else None
            row["climate2015_nan_share"] = float(data.loc[m, new_climate].isna().to_numpy().mean())
            tail_rows.append(row)
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
    pd.DataFrame(tail_rows).to_csv(vdir / "missingness_carrier_tail.csv", index=False)
    feature_classes = []
    for horizon in HORIZONS:
        for f in manifest["horizons"][str(horizon)]["arms"]["climate_safe_history_idp"]["features"]:
            if f in retained_by_h[horizon]:
                kind = "inherited (static snapshot or recipe-verified dynamic)"
            elif f in climate_by_h[horizon]:
                kind = "climate2015 (monthly <= O, completed seasons)"
            elif f.startswith("overall_phase_history"):
                kind = "safe IPC history (<= min(O, T-1))"
            elif f.startswith("idp_admin0"):
                kind = "national DTM IDP (<= O)"
            elif f in ("lat", "lon"):
                kind = "identifier: static coordinates"
            elif f.startswith("month_") or f.startswith("year_"):
                kind = "identifier: calendar dummy of the target month (known at origin; year dummies act as a trend term)"
            else:
                kind = "UNCLASSIFIED"
                problems.append(f"h{horizon}: feature {f} unclassified")
            feature_classes.append({"horizon": horizon, "feature": f, "class": kind})
    pd.DataFrame(feature_classes).to_csv(vdir / "feature_timing_classes.csv", index=False)
    import platform
    import subprocess

    import sklearn
    import xgboost

    runtime = {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__, "sklearn": sklearn.__version__,
               "xgboost": xgboost.__version__,
               "git_head": subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=PROJECT_ROOT).stdout.strip(),
               "code_sha256": {p: sha(PROJECT_ROOT / p) for p in ("scripts/modeling/run_deep_feature_weight_decay_forecasting.py", "src/ipcch/origin_safe.py",
                                                                  "src/ipcch/forecasting_weight_decay.py", "scripts/postprocessing/verify_origin_safe_climate_idp.py")}}
    summary = {"problems": problems, "passed": not problems, **checks, "runtime": runtime, "eval_keys": len(eval_keys),
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
    if OLD_CONTEXT.exists():
        old = pd.read_csv(OLD_CONTEXT)
        old = old[old["metric"].isin(["accuracy", "precision", "sensitivity", "f2", "r2"])]
        lines += ["", "## Context only: earlier annual climate2015_v1 runs (not a paired baseline)", "",
                  "Annual target-year fits with legacy IPC history, `estimated_population`, raw (unnormalized) targets and rounded, "
                  "row-dropping postprocessing; their `n_samples` are after those drops.", "",
                  "| scope | year | metric | baseline_rerun | climate2015_masked | n |", "|---|---|---|---:|---:|---:|"]
        for _, r in old.iterrows():
            lines.append(f"| {r.scope} | {r.test_year} | {r.metric} | {fmt(r.baseline)} | {fmt(r.masked)} | {r.n_samples} |")
    lines += ["", "## Coverage on the frozen evaluation keys", "", coverage.to_markdown(index=False) if hasattr(coverage, "to_markdown") else coverage.to_string(index=False), "",
              "## Limits", ""] + [f"- {x}" for x in manifest["limits"]] + [
              "- Single seed (42), no confidence intervals: differences are point estimates on one fit per origin.",
              "- Old climate2015_v1 / baseline results used annual target-year fits, legacy history and rounded, row-dropping postprocessing; "
              "they are context, not a paired baseline, and differences mix timing, target-normalization and postprocessing corrections.", ""]
    (REPORTS / "report.md").write_text("\n".join(lines))


if __name__ == "__main__":
    raise SystemExit(main())
