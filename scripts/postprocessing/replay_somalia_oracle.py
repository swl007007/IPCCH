#!/usr/bin/env python3
"""Independent replay of Somalia oracle metrics and bootstrap intervals from saved artifacts.

Recomputes every primary/persistence metric and paired delta-F2 interval from
``predictions.csv.gz``, the frozen cohort and label ledgers and the saved bootstrap
multiplicities, using scikit-learn metrics and a separate weighted-count path
(no import of ``ipcch.somalia_oracle.evaluation``). Writes a replay report and a
human-readable summary.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, fbeta_score, precision_score, r2_score, recall_score

from ipcch import paths

DEFAULT_OUT = paths.RESULTS_DIR / "experiments" / "somalia_oracle" / "v1"
DEFAULT_REPORT = paths.REPORTS_DIR / "somalia_oracle" / "v1"
ARMS = ("A", "B", "C", "D")


def label(o: int) -> str:
    return f"{o // 12:04d}-{o % 12 + 1:02d}"


def load(out: Path):
    predictions = pd.read_csv(out / "predictions" / "predictions.csv.gz")
    cohort = pd.read_csv(out / "ledgers" / "cohort_ledger.csv.gz")
    ledger = pd.read_csv(out / "ledgers" / "label_ledger.csv.gz")
    provenance = {h: pd.read_csv(out / "ledgers" / f"row_provenance_h{h:02d}.csv.gz") for h in (0, 3, 6, 12)}
    metrics = pd.read_csv(out / "metrics" / "metrics.csv")
    contrasts = pd.read_csv(out / "metrics" / "contrasts.csv")
    draws = np.load(out / "metrics" / "bootstrap_draws.npz")
    return predictions, cohort, ledger, provenance, metrics, contrasts, draws


def sk_metrics(truth_phase, truth_crisis, pred_phase, q3=None, q3_pred=None):
    y = np.asarray(truth_crisis) == 1
    p = np.asarray(pred_phase) >= 3
    out = {
        "f2": fbeta_score(y, p, beta=2, zero_division=np.nan) if (y.any() or p.any()) else np.nan,
        "precision": precision_score(y, p, zero_division=np.nan) if p.any() else np.nan,
        "recall": recall_score(y, p, zero_division=np.nan) if y.any() else np.nan,
        "accuracy": accuracy_score(truth_phase, pred_phase) if truth_phase is not None else np.nan,
    }
    if q3 is not None and len(q3) >= 2 and np.unique(q3).size > 1:
        out["r2_q3"] = r2_score(q3, q3_pred)
    else:
        out["r2_q3"] = np.nan
    return out


def required_contrasts(cohort: str) -> list:
    if cohort == "primary":
        return ["B-A", "C-B", "D-C"] + [f"{arm}-always_crisis" for arm in ARMS]
    return [f"{arm}-persistence" for arm in ARMS] + [f"{arm}-always_crisis" for arm in ARMS]


def weighted_f2(y: np.ndarray, p: np.ndarray, w: np.ndarray) -> np.ndarray:
    tp = (w * (y & p)).sum(axis=1)
    fp = (w * (~y & p)).sum(axis=1)
    fn = (w * (y & ~p)).sum(axis=1)
    d = 5 * tp + 4 * fn + fp
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(d > 0, 5 * tp / d, np.nan)


def replay(out: Path, predictions_override: "pd.DataFrame | None" = None):
    predictions, cohort, ledger, provenance, metrics, contrasts, draws = load(out)
    if predictions_override is not None:
        predictions = predictions_override
    truth = ledger.set_index(["area_id", "target_ord"])
    checks = []
    replayed = []
    for (year, horizon), keys in cohort.groupby(["test_year", "horizon"]):
        prov = provenance[horizon].set_index(["area_id", "target_ord"])
        primary = keys.loc[keys["status"] == "primary", ["area_id", "target_ord"]].sort_values(["area_id", "target_ord"])
        cohorts = {"primary": primary}
        pers_ok = prov.reindex(pd.MultiIndex.from_frame(primary))["persistence_available"].fillna(False).to_numpy(dtype=bool)
        cohorts["persistence_subset"] = primary.loc[pers_ok]
        for name, frame in cohorts.items():
            if frame.empty:
                continue
            idx = pd.MultiIndex.from_frame(frame)
            t = truth.reindex(idx)
            assert t["valid_score"].all(), "cohort contains an unscorable key"
            vectors = {}
            for arm in ARMS:
                sub = predictions.loc[(predictions["test_year"] == year) & (predictions["horizon"] == horizon) & (predictions["arm"] == arm)].set_index(["area_id", "target_ord"])
                if sub.index.duplicated().any():
                    raise AssertionError("duplicate prediction keys")
                pr = sub.reindex(idx)
                missing = int(pr["phase_pred"].isna().sum())
                checks.append({"check": "prediction_coverage", "year": year, "horizon": horizon, "arm": arm, "cohort": name, "pass": missing == 0, "detail": f"{missing} frozen cohort keys without predictions"})
                if missing:
                    continue
                # Phase must be reproducible from raw (unrounded) cumulative predictions.
                q = pr[["q2_pred", "q3_pred", "q4_pred", "q5_pred"]].to_numpy()
                phase = np.ones(len(q), dtype=int)
                for col, value in ((3, 5), (2, 4), (1, 3), (0, 2)):
                    phase = np.where((phase == 1) & (q[:, col] >= 0.2), value, phase)
                checks.append({"check": "phase_from_raw_predictions", "year": year, "horizon": horizon, "arm": arm, "cohort": name, "pass": bool((phase == pr["phase_pred"].to_numpy()).all())})
                m = sk_metrics(t["overall_phase"].to_numpy(), t["actual_crisis"].to_numpy(), pr["phase_pred"].to_numpy(), t["q3"].to_numpy(), pr["q3_pred"].to_numpy())
                replayed.append({"test_year": year, "horizon": horizon, "cohort": name, "specification": arm, **m})
                vectors[arm] = pr["phase_pred"].to_numpy() >= 3
            y = t["actual_crisis"].to_numpy() == 1
            vectors["always_crisis"] = np.ones(len(y), dtype=bool)
            replayed.append({"test_year": year, "horizon": horizon, "cohort": name, "specification": "always_crisis", **sk_metrics(None, y, np.full(len(y), 3))})
            if name == "persistence_subset":
                pp = prov.reindex(idx)["persistence_phase"].to_numpy()
                vectors["persistence"] = pp >= 3
                replayed.append({"test_year": year, "horizon": horizon, "cohort": name, "specification": "persistence", **sk_metrics(t["overall_phase"].to_numpy(), y, pp)})
            key = f"y{year}_h{horizon:02d}_{name}"
            has_bundle = f"{key}__multiplicities" in draws.files
            checks.append({"check": "bootstrap_bundle_present", "year": year, "horizon": horizon, "cohort": name, "pass": has_bundle or frame["area_id"].nunique() < 2})
            if not has_bundle:
                continue
            areas = draws[f"{key}__areas"]
            saved_keys = draws[f"{key}__cohort_keys"]
            same_keys = set(map(tuple, saved_keys.tolist())) == set(map(tuple, frame.to_numpy().tolist()))
            checks.append({"check": "bootstrap_cohort_keys_match", "year": year, "horizon": horizon, "cohort": name, "pass": bool(same_keys)})
            order = frame.reset_index(drop=True)
            w = draws[f"{key}__multiplicities"][:, np.searchsorted(areas, order["area_id"].to_numpy())].astype(float)
            sub_c = contrasts.loc[(contrasts["test_year"] == year) & (contrasts["horizon"] == horizon) & (contrasts["cohort"] == name)]
            required = required_contrasts(name)
            present = set(sub_c["contrast"])
            for contrast in required:
                checks.append({"check": "contrast_present", "year": year, "horizon": horizon, "cohort": name, "contrast": contrast, "pass": contrast in present})
            for row in sub_c.itertuples(index=False):
                a, b = row.contrast.split("-", 1)
                if a not in vectors or b not in vectors:
                    checks.append({"check": "contrast_vectors_available", "year": year, "horizon": horizon, "cohort": name, "contrast": row.contrast, "pass": False})
                    continue
                # Reorder saved-cohort vectors to the replay order (saved order == prediction merge order).
                delta = weighted_f2(y, vectors[a], w) - weighted_f2(y, vectors[b], w)
                saved = draws[f"{key}__delta::{row.contrast}"]
                ok = np.allclose(np.sort(delta[~np.isnan(delta)]), np.sort(saved[~np.isnan(saved)])) and np.isnan(delta).sum() == np.isnan(saved).sum()
                if row.interval_status == "ok":
                    low, high = np.quantile(delta, [0.025, 0.975])
                    ok = ok and np.isclose(low, row.ci_low) and np.isclose(high, row.ci_high)
                checks.append({"check": "bootstrap_interval_replay", "year": year, "horizon": horizon, "cohort": name, "contrast": row.contrast, "pass": bool(ok)})
    replayed = pd.DataFrame(replayed)
    saved = metrics.loc[metrics["status"] == "ok"].set_index(["test_year", "horizon", "cohort", "specification"])
    for row in replayed.itertuples(index=False):
        k = (row.test_year, row.horizon, row.cohort, row.specification)
        if k not in saved.index:
            checks.append({"check": "metric_row_present", "year": row.test_year, "horizon": row.horizon, "cohort": row.cohort, "arm": row.specification, "pass": False})
            continue
        s = saved.loc[k]
        for metric in ("f2", "precision", "recall", "accuracy", "r2_q3"):
            a, b = getattr(row, metric), s[metric]
            same = (pd.isna(a) and pd.isna(b)) or (not pd.isna(a) and not pd.isna(b) and np.isclose(a, b))
            checks.append({"check": f"metric_{metric}", "year": row.test_year, "horizon": row.horizon, "cohort": row.cohort, "arm": row.specification, "pass": bool(same)})
    return pd.DataFrame(checks), replayed, metrics, contrasts, cohort


def fmt(v, digits=3):
    return "—" if v is None or (isinstance(v, float) and np.isnan(v)) else f"{v:.{digits}f}"


def write_summary(report: Path, out: Path, metrics, contrasts, cohort, checks):
    manifest = json.loads((out / "manifest.json").read_text())
    lines = [
        "# Somalia oracle-information experiment — results summary",
        "",
        f"Git HEAD at run: `{manifest['git']['head']}`; runtime xgboost {manifest['runtime']['xgboost']}, numpy {manifest['runtime']['numpy']}, pandas {manifest['runtime']['pandas']}.",
        "Interpretation: conditional empirical ceiling of this model family under ideal publication and oracle realized weather; not causal, not an operational forecast skill claim. Horizons are separate conditions and are not ranked.",
        "",
        f"Independent replay: {int(checks['pass'].sum())}/{len(checks)} checks passed.",
        "",
        "## Coverage (frozen before fitting)",
        "",
        "| Test year | H | primary | wider-only (oracle weather unverified) | excluded | primary target months |",
        "|---|---|---:|---:|---:|---|",
    ]
    for (year, h), g in cohort.groupby(["test_year", "horizon"]):
        prim = g.loc[g["status"] == "primary"]
        months = ", ".join(f"{label(m)} ({(prim['target_ord'] == m).sum()})" for m in sorted(prim["target_ord"].unique())) or "none"
        lines.append(f"| {year} | {h} | {len(prim)} | {(g['status'] == 'wider_only').sum()} | {(g['status'] == 'excluded').sum()} | {months} |")
    lines += ["", "## Primary-cohort metrics (Phase 3+ F2 is the selection metric)", "", "| Year | H | Spec | n | F2 | Precision | Recall | Accuracy | R² q3 |", "|---|---|---|---:|---:|---:|---:|---:|---:|"]
    prim = metrics.loc[(metrics["cohort"] == "primary")]
    for r in prim.itertuples(index=False):
        if r.status != "ok":
            lines.append(f"| {r.test_year} | {r.horizon} | {r.specification} | {r.n_rows} | {r.status}: {r.reason} | | | | |")
            continue
        lines.append(f"| {r.test_year} | {r.horizon} | {r.specification} | {r.n_rows} | {fmt(r.f2)} | {fmt(r.precision)} | {fmt(r.recall)} | {fmt(r.accuracy)} | {fmt(r.r2_q3)} |")
    lines += ["", "## Paired area-cluster bootstrap Δ F2 (95% percentile, 2,000 draws, PCG64(42))", "", "| Year | H | Cohort | Contrast | Δ F2 | 95% interval | status |", "|---|---|---|---|---:|---|---|"]
    for r in contrasts.itertuples(index=False):
        interval = f"[{fmt(r.ci_low)}, {fmt(r.ci_high)}]" if r.interval_status == "ok" else r.interval_reason
        lines.append(f"| {r.test_year} | {r.horizon} | {r.cohort} | {r.contrast} | {fmt(r.point_delta_f2)} | {interval} | {r.interval_status} |")
    pers = metrics.loc[metrics["cohort"] == "persistence_subset"]
    lines += ["", "## Persistence-supported subset", "", "| Year | H | Spec | n | F2 | Accuracy |", "|---|---|---|---:|---:|---:|"]
    for r in pers.itertuples(index=False):
        if r.status == "ok":
            lines.append(f"| {r.test_year} | {r.horizon} | {r.specification} | {r.n_rows} | {fmt(r.f2)} | {fmt(r.accuracy)} |")
    lines += [
        "",
        "## Caveats",
        "",
        "- Realized monthly weather in the canonical raw panel is frozen for 772 Somalia areas from 2025-02 and for all areas in 2026-04; those months are treated as unverified oracle evidence, which restricts H=3/6/12 primary cohorts (fold 2026 H=3/6 has no verified oracle rows).",
        "- `overall_phase_lag1` and `estimated_population` were blocked from all arms after lineage review; arm A still contains exact-month categorical phase history (`overall_phase_prev_observed_asof_sH`).",
        "- Fold 2026 covers only April 2026 targets. Two test years cannot establish stable superiority; intervals exclude refitting/selection uncertainty and do not correct all spatial dependence.",
    ]
    report.mkdir(parents=True, exist_ok=True)
    (report / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args(argv)
    checks, replayed, metrics, contrasts, cohort = replay(args.out_dir)
    checks.to_csv(args.out_dir / "metrics" / "replay_checks.csv", index=False)
    replayed.to_csv(args.out_dir / "metrics" / "replayed_metrics.csv", index=False)
    write_summary(args.report_dir, args.out_dir, metrics, contrasts, cohort, checks)
    failed = checks.loc[~checks["pass"]]
    print(f"replay checks: {len(checks) - len(failed)}/{len(checks)} passed")
    if len(failed):
        print(failed.head(20).to_string(index=False))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
