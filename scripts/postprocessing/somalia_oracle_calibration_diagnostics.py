#!/usr/bin/env python3
"""Post-hoc calibration and per-phase threshold diagnostics for the Somalia oracle run.

No refitting. Every adjustment is learned per (job, arm) on that job's saved
inner-validation predictions of its *selected* candidate (labels <= outer origin),
then applied to the job's outer test predictions. A separate "test-tuned ceiling"
tunes on the evaluation cohort itself and is leaky by construction: it bounds what
post-processing could achieve and must not be reported as performance.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import f1_score, roc_auc_score

from ipcch import paths
from ipcch.somalia_oracle import evaluation as ev

OUT = paths.RESULTS_DIR / "experiments" / "somalia_oracle" / "v1"
REPORT = paths.REPORTS_DIR / "somalia_oracle" / "v1"
Q = ["q2", "q3", "q4", "q5"]
QP = [f"{q}_pred" for q in Q]
GRID = np.round(np.arange(0.05, 0.525, 0.025), 3)


def to_phase(pred: np.ndarray, th) -> np.ndarray:
    th = np.broadcast_to(np.asarray(th, dtype=float), (4,))
    phase = np.ones(len(pred), dtype=int)
    for col, value in ((3, 5), (2, 4), (1, 3), (0, 2)):
        phase = np.where((phase == 1) & (pred[:, col] >= th[col]), value, phase)
    return phase


def scores(phase_true, phase_pred) -> dict:
    y, p = phase_true >= 3, phase_pred >= 3
    tp, fp, fn = (y & p).sum(), (~y & p).sum(), (y & ~p).sum()
    labels = sorted(set(phase_true) | set(phase_pred))
    return {
        "f2": 5 * tp / (5 * tp + 4 * fn + fp) if (5 * tp + 4 * fn + fp) else np.nan,
        "precision": tp / (tp + fp) if tp + fp else np.nan,
        "recall": tp / (tp + fn) if tp + fn else np.nan,
        "f1": 2 * tp / (2 * tp + fp + fn) if (2 * tp + fp + fn) else np.nan,
        "accuracy": float((phase_true == phase_pred).mean()),
        "macro_f1": f1_score(phase_true, phase_pred, labels=labels, average="macro", zero_division=0),
        "p4plus_recall": float(((phase_pred >= 4) & (phase_true >= 4)).sum() / max((phase_true >= 4).sum(), 1)) if (phase_true >= 4).any() else np.nan,
        "pred_p3_share": float((phase_pred == 3).mean()),
    }


def r2(y, p):
    ss = ((y - y.mean()) ** 2).sum()
    return float(1 - ((y - p) ** 2).sum() / ss) if ss > 0 else np.nan


def tune_global(pred, phase_true, objective):
    best = (-np.inf, 0.2)
    for t in GRID:
        s = scores(phase_true, to_phase(pred, t))[objective]
        if s > best[0] + 1e-12:
            best = (s, t)
    return np.full(4, best[1])


def tune_per_phase(pred, phase_true, objective, passes=3):
    th = np.full(4, 0.2)
    for _ in range(passes):
        for j in range(4):
            best = (-np.inf, th[j])
            for t in GRID:
                trial = th.copy()
                trial[j] = t
                s = scores(phase_true, to_phase(pred, trial))[objective]
                if s > best[0] + 1e-12:
                    best = (s, t)
            th[j] = best[1]
    return th


def calibrate(val_pred, val_true, test_pred, kind):
    out = np.empty_like(test_pred)
    for j in range(4):
        if kind == "shift":
            out[:, j] = np.clip(test_pred[:, j] - (val_pred[:, j] - val_true[:, j]).mean(), 0, 1)
        else:
            iso = IsotonicRegression(y_min=0, y_max=1, out_of_bounds="clip").fit(val_pred[:, j], val_true[:, j])
            out[:, j] = iso.predict(test_pred[:, j])
    return out


def benchmark_comparison(adjusted: pd.DataFrame, out: Path) -> tuple:
    """Calibrated D vs persistence and always-crisis on identical keys.

    Persistence carries forward the latest valid reported phase (U <= O, U < T); its
    share analogue carries forward the latest valid history observation's q3
    (``hist_q3_obs1``) and is the only benchmark with an R². Always-crisis is
    binary-only. Paired area-cluster bootstrap (2,000 draws, PCG64(42)) intervals are
    for Phase 3+ F2 differences.
    """
    specs = {"D_raw": "canonical_0.2", "D_calibrated": "val_isotonic_calib_0.2"}
    rows, contrast_rows = [], []
    for h in sorted(adjusted["horizon"].unique()):
        prov = pd.read_csv(out / "ledgers" / f"row_provenance_h{h:02d}.csv.gz", usecols=["area_id", "target_ord", "persistence_available", "persistence_phase"])
        hist = pd.read_csv(out / "features" / f"feature_matrix_h{h:02d}.csv.gz", usecols=["area_id", "target_ord", "hist_q3_obs1"])
        for year in sorted(adjusted.loc[adjusted["horizon"] == h, "test_year"].unique()):
            d = {name: adjusted.loc[(adjusted["test_year"] == year) & (adjusted["horizon"] == h) & (adjusted["arm"] == "D") & (adjusted["method"] == m)] for name, m in specs.items()}
            base = d["D_calibrated"][["area_id", "target_ord", "overall_phase", "q3", "phase_adj", "q3_adj"]].rename(columns={"phase_adj": "D_calibrated_phase", "q3_adj": "D_calibrated_q3"})
            base = base.merge(d["D_raw"][["area_id", "target_ord", "phase_adj", "q3_adj"]].rename(columns={"phase_adj": "D_raw_phase", "q3_adj": "D_raw_q3"}), on=["area_id", "target_ord"])
            base = base.merge(prov, on=["area_id", "target_ord"], how="left").merge(hist, on=["area_id", "target_ord"], how="left")
            for cohort, frame in (("primary", base), ("persistence_subset", base.loc[base["persistence_available"].fillna(False).astype(bool)])):
                if frame.empty:
                    continue
                frame = frame.sort_values(["area_id", "target_ord"]).reset_index(drop=True)
                truth = frame["overall_phase"].to_numpy().astype(int)
                meta = {"test_year": year, "horizon": h, "cohort": cohort, "n": len(frame), "n_areas": frame["area_id"].nunique()}
                vectors = {}
                for name in ("D_raw", "D_calibrated"):
                    phase = frame[f"{name}_phase"].to_numpy()
                    rows.append({**meta, "benchmark": name, **scores(truth, phase), "r2_q3": r2(frame["q3"].to_numpy(), frame[f"{name}_q3"].to_numpy()), "r2_n": len(frame)})
                    vectors[name] = phase >= 3
                rows.append({**meta, "benchmark": "always_crisis", **scores(truth, np.full(len(frame), 3)), "accuracy": np.nan, "macro_f1": np.nan, "pred_p3_share": np.nan, "r2_q3": np.nan, "r2_n": 0})
                vectors["always_crisis"] = np.ones(len(frame), dtype=bool)
                if cohort == "persistence_subset":
                    phase = frame["persistence_phase"].to_numpy().astype(int)
                    share = frame["hist_q3_obs1"].to_numpy()
                    ok = np.isfinite(share)
                    rows.append({**meta, "benchmark": "persistence", **scores(truth, phase), "r2_q3": r2(frame["q3"].to_numpy()[ok], share[ok]) if ok.sum() > 1 else np.nan, "r2_n": int(ok.sum())})
                    vectors["persistence"] = phase >= 3
                    # D on the share-persistence rows, so the R² comparison uses identical keys.
                    rows.append({**meta, "benchmark": "D_calibrated_on_share_persistence_rows", "n": int(ok.sum()), "r2_q3": r2(frame["q3"].to_numpy()[ok], frame["D_calibrated_q3"].to_numpy()[ok]) if ok.sum() > 1 else np.nan, "r2_n": int(ok.sum())})
                contrasts = [("D_calibrated", b) for b in ("persistence", "always_crisis", "D_raw") if b in vectors]
                crows, _ = ev.paired_bootstrap(frame, truth >= 3, vectors, contrasts)
                contrast_rows += [{**meta, **c} for c in crows]
    return pd.DataFrame(rows), pd.DataFrame(contrast_rows)


def _fmt(v):
    return "—" if pd.isna(v) else f"{v:.3f}"


def write_report(res: pd.DataFrame, auc: pd.DataFrame, bench: pd.DataFrame, bench_contrasts: pd.DataFrame, path: Path) -> None:
    """Group-meeting section: isotonic-calibrated arm D, emphasis on H=0 and H=3."""
    view = res.set_index(["test_year", "horizon", "arm", "method"])
    lines = [
        "# Calibration and threshold diagnostics (no refitting)",
        "",
        "Calibration maps and thresholds are learned per (job, arm) on that job's saved inner-validation predictions of its selected candidate (labels <= outer origin) and applied to outer test predictions. `LEAKY_*` rows tune on the evaluation cohort and only bound what post-processing could reach.",
        "",
        "## Headline: isotonic-calibrated D (full phase-percentage history)",
        "",
        "H=0 and H=3 are the horizons of primary interest to Somalia government users. 2026 covers April 2026 only; 2026 H=3 has no verified oracle-weather rows.",
        "",
        "| Year | H | n | R² q3 raw → calibrated | Accuracy raw → calibrated | Macro-F1 raw → calibrated | Crisis AUC | Within-month AUC |",
        "|---|---|---:|---|---|---|---:|---:|",
    ]
    for (year, h), _ in res.loc[res["arm"] == "D"].groupby(["test_year", "horizon"]):
        raw = view.loc[(year, h, "D", "canonical_0.2")]
        cal = view.loc[(year, h, "D", "val_isotonic_calib_0.2")]
        a = auc.set_index(["test_year", "horizon", "arm"]).loc[(year, h, "D")]
        lines.append(f"| {year} | {h} | {int(raw['n'])} | {_fmt(raw['r2_q3'])} → **{_fmt(cal['r2_q3'])}** | {_fmt(raw['accuracy'])} → {_fmt(cal['accuracy'])} | {_fmt(raw['macro_f1'])} → {_fmt(cal['macro_f1'])} | {_fmt(a['auc_crisis'])} | {_fmt(a['within_month_auc'])} |")
    lines += [
        "",
        "## Specification comparison on discrimination and calibrated R²",
        "",
        "| Year | H | Crisis AUC A / B / C / D | Within-month AUC A / B / C / D | Calibrated R² A / B / C / D |",
        "|---|---|---|---|---|",
    ]
    ai = auc.set_index(["test_year", "horizon", "arm"])
    for (year, h), _ in auc.groupby(["test_year", "horizon"]):
        arms = "ABCD"
        lines.append(
            f"| {year} | {h} | " + " / ".join(_fmt(ai.loc[(year, h, x), "auc_crisis"]) for x in arms)
            + " | " + " / ".join(_fmt(ai.loc[(year, h, x), "within_month_auc"]) for x in arms)
            + " | " + " / ".join(_fmt(view.loc[(year, h, x, "val_isotonic_calib_0.2"), "r2_q3"]) for x in arms) + " |"
        )
    lines += [
        "",
        "## Calibrated D versus simple benchmarks",
        "",
        "Identical keys within each year/horizon. Persistence = latest valid reported phase with U <= O and U < T; its R² uses the carried-forward q3 share of the latest valid history observation (`hist_q3_obs1`), and the D R² in brackets is recomputed on exactly those rows. Always-crisis predicts Phase 3+ everywhere (binary only). Δ F2 intervals: paired area-cluster bootstrap, 2,000 draws, PCG64(42).",
        "",
        "| Year | H | Cohort | n | Benchmark | F2 | Precision | Recall | Accuracy | Macro-F1 | R² q3 |",
        "|---|---|---|---:|---|---:|---:|---:|---:|---:|---|",
    ]
    order = {"D_calibrated": 0, "D_raw": 1, "persistence": 2, "always_crisis": 3}
    same_rows = bench.loc[bench["benchmark"] == "D_calibrated_on_share_persistence_rows"].set_index(["test_year", "horizon", "cohort"])
    for r in bench.loc[bench["benchmark"].isin(order)].assign(o=lambda x: x["benchmark"].map(order)).sort_values(["test_year", "horizon", "cohort", "o"]).itertuples(index=False):
        r2_text = _fmt(r.r2_q3)
        if r.benchmark == "persistence":
            r2_text = f"{_fmt(r.r2_q3)} (n={int(r.r2_n)}; D calibrated {_fmt(same_rows.loc[(r.test_year, r.horizon, r.cohort), 'r2_q3'])})"
        lines.append(f"| {r.test_year} | {r.horizon} | {r.cohort} | {r.n} | {r.benchmark} | {_fmt(r.f2)} | {_fmt(r.precision)} | {_fmt(r.recall)} | {_fmt(r.accuracy)} | {_fmt(r.macro_f1)} | {r2_text} |")
    lines += ["", "| Year | H | Cohort | Contrast | Δ F2 | 95% interval |", "|---|---|---|---|---:|---|"]
    for r in bench_contrasts.itertuples(index=False):
        interval = f"[{_fmt(r.ci_low)}, {_fmt(r.ci_high)}]" if r.interval_status == "ok" else r.interval_reason
        lines.append(f"| {r.test_year} | {r.horizon} | {r.cohort} | {r.contrast} | {_fmt(r.point_delta_f2)} | {interval} |")
    lines += [
        "",
        "## Findings",
        "",
        "- Discrimination, not calibration, is the bottleneck for A/B/C (crisis AUC mostly ≈0.5). D is the only specification with consistently useful within-month ranking.",
        "- Isotonic calibration on inner validation removes most of the upward bias in q3 predictions at H=0/3/6, lifting D's R² to 0.21 (2026 H=0) and 0.10 (2025 H=0). At H=12 the validation bias does not transfer across years and calibration hurts R².",
        "- Per-phase thresholds mainly trade F2 for macro-F1; Phase 4 recall stays <0.1 without an F2-style low threshold. Even the leaky test-tuned ceiling keeps accuracy ≤0.63.",
        "- Phase 3+ F2 is a poor selection criterion here: with crisis prevalence 0.45–0.60 and many shares near 0.2, F2-optimal models collapse to predicting Phase 3 almost everywhere and cannot beat always-crisis.",
        "- Against simple benchmarks: calibrated D beats persistence on F2 at H=0/3/6 in 2025 (Δ +0.12 to +0.20, intervals exclude zero) and on share R² everywhere except 2026 H=0, where carried-forward q3 is as good (0.220 vs 0.214). Persistence has higher accuracy and macro-F1 than calibrated D at H=0 in both years (2026: 0.606 vs 0.480; 0.492 vs 0.356) because it predicts Phase 2 and 4 when those were last observed.",
        "- Calibrated D never significantly beats always-crisis on F2 (2025 H=0 Δ −0.001 [−0.011, 0.010]); at 2026 H=0 and at H=12 it is significantly worse on F2.",
        "- The R² of 0.21 at 2026 H=0 is therefore not a gain over the naive share-persistence benchmark; the 2025 H=0/H=3 R² gains over persistence (0.106 vs −0.624; 0.095 vs −0.464) are.",
        "",
        "## Recommendations",
        "",
        "- Present calibrated D at H=0 and H=3 for the next group meeting together with persistence and always-crisis on the same keys; frame 2025 H=0/H=3 as the evidence of added value and 2026 H=0 as matching persistence.",
        "- Do not select future models on F2. Use calibrated share R², crisis AUC / within-month AUC and macro-F1 as primary criteria, always reported relative to persistence and always-crisis on identical keys.",
        "- Judge new signals (e.g. flooding) by within-month AUC and calibrated R² gains over calibrated D and over share persistence, and by whether they close the accuracy/macro-F1 gap to persistence.",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out-dir", type=Path, default=OUT)
    parser.add_argument("--report-dir", type=Path, default=REPORT)
    args = parser.parse_args(argv)
    out = args.out_dir
    ledger = pd.read_csv(out / "ledgers" / "label_ledger.csv.gz")[["area_id", "target_ord", "overall_phase", *Q]]
    preds = pd.read_csv(out / "predictions" / "predictions.csv.gz")
    val = pd.read_csv(out / "fits" / "validation_predictions.csv.gz")
    status = pd.read_csv(out / "fits" / "arm_job_status.csv")
    cohort = pd.read_csv(out / "ledgers" / "cohort_ledger.csv.gz")
    primary = cohort.loc[cohort["status"] == "primary", ["test_year", "horizon", "area_id", "target_ord"]]

    val = val.merge(status[["job_id", "arm", "selected_candidate"]], on=["job_id", "arm"])
    val = val.loc[val["candidate"] == val["selected_candidate"]].merge(ledger, on=["area_id", "target_ord"], validate="many_to_one")
    test = preds.merge(ledger, on=["area_id", "target_ord"], validate="many_to_one")

    methods = {
        "canonical_0.2": lambda vp, vt, vq, tp: (tp, np.full(4, 0.2)),
        "val_global_th_f2": lambda vp, vt, vq, tp: (tp, tune_global(vp, vt, "f2")),
        "val_global_th_macro_f1": lambda vp, vt, vq, tp: (tp, tune_global(vp, vt, "macro_f1")),
        "val_perphase_th_macro_f1": lambda vp, vt, vq, tp: (tp, tune_per_phase(vp, vt, "macro_f1")),
        "val_perphase_th_accuracy": lambda vp, vt, vq, tp: (tp, tune_per_phase(vp, vt, "accuracy")),
        "val_shift_calib_0.2": lambda vp, vt, vq, tp: (calibrate(vp, vq, tp, "shift"), np.full(4, 0.2)),
        "val_isotonic_calib_0.2": lambda vp, vt, vq, tp: (calibrate(vp, vq, tp, "isotonic"), np.full(4, 0.2)),
        "val_isotonic_then_perphase_macro_f1": None,
    }
    rows, thresholds = [], []
    for (job, arm), t in test.groupby(["job_id", "arm"]):
        v = val.loc[(val["job_id"] == job) & (val["arm"] == arm)]
        if v.empty:
            continue
        vp, vt, vq = v[QP].to_numpy(), v["overall_phase"].to_numpy().astype(int), v[Q].to_numpy()
        tp = t[QP].to_numpy()
        for name, fn in methods.items():
            if name == "val_isotonic_then_perphase_macro_f1":
                vcal = calibrate(vp, vq, vp, "isotonic")
                th = tune_per_phase(vcal, vt, "macro_f1")
                adj = calibrate(vp, vq, tp, "isotonic")
            else:
                adj, th = fn(vp, vt, vq, tp)
            frame = t[["test_year", "horizon", "area_id", "target_ord", "overall_phase", "q3"]].copy()
            frame["arm"], frame["method"], frame["phase_adj"], frame["q3_adj"] = arm, name, to_phase(adj, th), adj[:, 1]
            rows.append(frame)
            thresholds.append({"job_id": job, "arm": arm, "method": name, "t2": th[0], "t3": th[1], "t4": th[2], "t5": th[3]})
    adjusted = pd.concat(rows, ignore_index=True).merge(primary, on=["test_year", "horizon", "area_id", "target_ord"])

    results = []
    for (year, h, arm, method), g in adjusted.groupby(["test_year", "horizon", "arm", "method"]):
        truth = g["overall_phase"].to_numpy().astype(int)
        results.append({"test_year": year, "horizon": h, "arm": arm, "method": method, "n": len(g), **scores(truth, g["phase_adj"].to_numpy()), "r2_q3": r2(g["q3"].to_numpy(), g["q3_adj"].to_numpy())})
    # Leaky ceiling: per-phase thresholds tuned on the evaluation cohort itself.
    base = adjusted.loc[adjusted["method"] == "canonical_0.2"].merge(preds[["test_year", "horizon", "arm", "area_id", "target_ord", *QP]], on=["test_year", "horizon", "arm", "area_id", "target_ord"])
    for (year, h, arm), g in base.groupby(["test_year", "horizon", "arm"]):
        truth = g["overall_phase"].to_numpy().astype(int)
        th = tune_per_phase(g[QP].to_numpy(), truth, "macro_f1")
        results.append({"test_year": year, "horizon": h, "arm": arm, "method": "LEAKY_test_perphase_macro_f1", "n": len(g), **scores(truth, to_phase(g[QP].to_numpy(), th)), "r2_q3": np.nan})
        thresholds.append({"job_id": f"y{year}_h{h:02d}_pooled", "arm": arm, "method": "LEAKY_test_perphase_macro_f1", "t2": th[0], "t3": th[1], "t4": th[2], "t5": th[3]})
    for (year, h), g in base.loc[base["arm"] == "A"].groupby(["test_year", "horizon"]):
        truth = g["overall_phase"].to_numpy().astype(int)
        results.append({"test_year": year, "horizon": h, "arm": "-", "method": "always_crisis", "n": len(g), **scores(truth, np.full(len(g), 3)), "r2_q3": np.nan})

    diag = out / "diagnostics"
    diag.mkdir(exist_ok=True)
    res = pd.DataFrame(results)
    # Rank discrimination of raw q3 predictions (unaffected by monotone post-processing).
    auc_rows = []
    for (year, h, arm), g in base.groupby(["test_year", "horizon", "arm"]):
        crisis = g["overall_phase"].to_numpy() >= 3
        months = [roc_auc_score(x["overall_phase"] >= 3, x["q3_pred"]) for _, x in g.groupby("target_ord") if (x["overall_phase"] >= 3).nunique() == 2]
        auc_rows.append({"test_year": year, "horizon": h, "arm": arm, "auc_crisis": roc_auc_score(crisis, g["q3_pred"]) if len(set(crisis)) == 2 else np.nan, "within_month_auc": float(np.mean(months)) if months else np.nan})
    auc = pd.DataFrame(auc_rows)
    auc.to_csv(diag / "discrimination_auc.csv", index=False)
    bench, bench_contrasts = benchmark_comparison(adjusted, out)
    bench.to_csv(diag / "calibrated_d_vs_benchmarks.csv", index=False)
    bench_contrasts.to_csv(diag / "calibrated_d_vs_benchmarks_contrasts.csv", index=False)
    write_report(res, auc, bench, bench_contrasts, args.report_dir / "calibration_diagnostics.md")
    res.to_csv(diag / "calibration_threshold_metrics.csv", index=False)
    pd.DataFrame(thresholds).to_csv(diag / "calibration_thresholds.csv", index=False)
    pd.set_option("display.width", 250)
    print(res.round(3).to_string(index=False))


if __name__ == "__main__":
    raise SystemExit(main())
