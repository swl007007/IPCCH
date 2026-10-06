"""Compare climate2015_v1 global runs with the rerun baseline (and the 2026-05-31 baseline outputs)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = next(path for path in Path(__file__).resolve().parents if (path / "src").exists())
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import pandas as pd

from ipcch import paths

EXP = paths.RESULTS_DIR / "experiments" / "deep_feature_weight_decay_forecasting"
RESULTS = EXP / "climate2015_v1"
REPORTS = paths.REPORTS_DIR / "deep_feature_weight_decay_forecasting" / "climate2015_v1"
MAY_BASELINE = {
    "0m": "0m_global_identifier_features_threshold_0_20",
    "3m": "3m_global_identifier_features_threshold_0_20",
    "6m": "6m_global_identifier_features_threshold_0_20",
    "12m": "forecasting_global_identifier_features_threshold_0_20",
}
ARMS = {"baseline_rerun": "baseline", "climate2015_masked": "masked", "climate2015_unmasked": "unmasked"}
METRICS = {"accuracy": "Accuracy", "precision_phase3plus": "Precision 3+", "sensitivity_phase3plus": "Sensitivity 3+", "r2_phase3plus": "R² 3+", "f2_phase3plus": "F2 3+"}


def read_metrics(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df = df[df["scope"] == "overall"]
    return df.melt(id_vars=["test_year", "n_samples"], value_vars=list(METRICS), var_name="metric", value_name="value")


def load_all() -> pd.DataFrame:
    frames = []
    for scope, folder in MAY_BASELINE.items():
        frames.append(read_metrics(EXP / folder / "metrics" / "metrics_overall.csv").assign(scope=scope, arm="baseline_2026_05_31"))
        for arm_dir, arm in ARMS.items():
            path = RESULTS / arm_dir / scope / "metrics" / "metrics_overall.csv"
            if path.exists():
                frames.append(read_metrics(path).assign(scope=scope, arm=arm))
    long = pd.concat(frames, ignore_index=True)
    wide = long.pivot_table(index=["scope", "test_year", "metric"], columns="arm", values="value").reset_index()
    n = long[long["arm"] == "baseline"].drop_duplicates(["scope", "test_year"])[["scope", "test_year", "n_samples"]]
    wide = wide.merge(n, on=["scope", "test_year"], how="left")
    for arm in ("masked", "unmasked"):
        if arm in wide:
            wide[f"delta_{arm}"] = wide[arm] - wide["baseline"]
    wide["drift_rerun_vs_may"] = wide["baseline"] - wide["baseline_2026_05_31"]
    order = {"0m": 0, "3m": 1, "6m": 2, "12m": 3}
    return wide.sort_values(["scope", "metric", "test_year"], key=lambda s: s.map(order) if s.name == "scope" else s).reset_index(drop=True)


def fmt(x, signed=False):
    if pd.isna(x):
        return "–"
    return f"{x:+.3f}" if signed else f"{x:.3f}"


def report(wide: pd.DataFrame) -> str:
    lines = ["# Global model: 2015–2026 climate features vs current climate features", ""]
    lines += [
        "Annual holdouts 2022–2025, trained on all earlier rows. Identical code and flags in every arm: half-life 24 months, threshold 0.2, identifier features, seed 42.",
        "",
        "- **baseline**: the current features, rerun with the current code.",
        "- **masked** (primary comparison): FLDAS climate features replaced by the 2015–2026 climate features. Scope-anchored features are blank wherever the baseline's own scope features are blank, so only the climate source differs.",
        "- **unmasked**: the same, but the late-2025 scope features are not blanked (see Caveats).",
        "",
        "## Mean over the four test years",
        "",
        "| Scope | Metric | Baseline | Masked | Δ masked | Unmasked | Δ unmasked |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    mean = wide.groupby(["scope", "metric"], sort=False)[[c for c in ("baseline", "masked", "unmasked") if c in wide]].mean().reset_index()
    for _, r in mean.iterrows():
        dm = r.get("masked", float("nan")) - r["baseline"]
        du = r.get("unmasked", float("nan")) - r["baseline"]
        lines.append(f"| {r['scope']} | {METRICS[r['metric']]} | {fmt(r['baseline'])} | {fmt(r.get('masked'))} | {fmt(dm, True)} | {fmt(r.get('unmasked'))} | {fmt(du, True)} |")
    lines += ["", "## By test year (Δ = masked − baseline)", ""]
    for scope in wide["scope"].unique():
        sub = wide[wide["scope"] == scope]
        lines += [f"### {scope}", "", "| Test year | n | " + " | ".join(METRICS.values()) + " |", "|---|---:|" + "---:|" * len(METRICS)]
        for year, g in sub.groupby("test_year"):
            g = g.set_index("metric")
            cells = [f"{fmt(g.loc[m, 'masked'])} ({fmt(g.loc[m, 'delta_masked'], True)})" if m in g.index and "masked" in g else "–" for m in METRICS]
            lines.append(f"| {year} | {int(g['n_samples'].iloc[0])} | " + " | ".join(cells) + " |")
        lines.append("")
    drift = wide["drift_rerun_vs_may"].abs()
    lines += ["## Baseline reproducibility", "",
              f"Rerun baseline vs 2026-05-31 outputs: max |difference| over all scopes, years and metrics = {drift.max():.4f}; mean = {drift.mean():.4f}.", "",
              "0m and 12m reproduce exactly. The May 3m/6m outputs (dated 2026-05-26) predate the 2026-05-30 rebuild of the fs1/fs2 files, which added one feature (539 → 540). The drift therefore comes from the inputs, not the code, and all deltas above use the rerun baseline.", ""]
    lines += ["## Interpretation", "",
              "- The main effect is higher phase 3+ sensitivity, and so higher F2: 0m +0.05, 3m +0.03, 12m +0.03 averaged over the years. Precision is flat or slightly lower, so the model calls more areas 3+ rather than becoming more accurate overall.",
              "- Most of the gain comes from 2022: sensitivity +0.13 at 0m, +0.11 at 3m and +0.10 at 12m. For 2023–2025 most differences are within ±0.02.",
              "- 6m barely changes.",
              "- The one large loss is 0m R² in 2025 (0.351 → 0.183):",
              "  - It is concentrated in the 59.7% of 2025 rows whose scope features are blank, where R² falls from 0.336 to 0.119.",
              "  - Yemen is about a third of the extra squared error: its under-prediction deepens.",
              "  - East and Southern Africa move to over-prediction, with bias up 4–8 points in Somalia, the DRC, Mozambique, Zambia and Kenya.",
              "  - Filling in contemporaneous climate (the unmasked arm) recovers part of it (0.241).",
              "",
              "## Caveats", "",
              "- One seed and no uncertainty intervals. Differences of about ±0.01 should not be read as real changes.",
              "- Upstream builds scope features by shifting rows, so they are blank for targets after 2025-04 (0m), 2025-07 (3m) and 2025-10 (6m). This blanks 59.7%, 46.1% and 1.6% of 2025 rows respectively, for every dynamic source, not just climate. The masked arm keeps this gap; the unmasked arm fills it for climate only.",
              "- The new climate data start in 2015, so training rows from 2014–2016 have little or no new climate history (NaN). The FLDAS baseline had full history for these rows.",
              "- Source-data caveats from the shared-folder audit (2026-09-30): a 2025 coverage break for the Terra NDVI/EVI and CPC sources, and an undocumented climatology baseline for the anomalies.",
              ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-csv", default=str(RESULTS / "comparison_metrics.csv"))
    parser.add_argument("--out-md", default=str(REPORTS / "comparison.md"))
    args = parser.parse_args()
    wide = load_all()
    Path(args.out_csv).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_md).parent.mkdir(parents=True, exist_ok=True)
    wide.to_csv(args.out_csv, index=False)
    Path(args.out_md).write_text(report(wide))
    print(Path(args.out_md).read_text())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
