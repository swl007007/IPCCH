"""Wrap-up table for the Somalia oracle experiments (H0, 2025/2026).

Reads the saved v2_q3 and v3_validity metrics.csv files (no refit) and writes
one long CSV of AUC, binary F1 and final q3 R2 for D_direct / D_residual /
D_selected, the always-crisis / persistence baselines and (v2 only) the v1 D
reference rows, per test year and as an n-weighted average of 2025 and 2026.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from ipcch.paths import REPORTS_DIR, RESULTS_DIR

RESULTS = RESULTS_DIR / "experiments" / "somalia_oracle"
SETTINGS = [
    ("v2_fs", "v2_q3", None),
    ("v3_original", "v3_validity", "original"),
    ("v3_augmented", "v3_validity", "augmented"),
]
D_VIEWS = ["D_direct", "D_residual", "D_selected"]
BASELINES = ["always_crisis", "share_persistence", "phase_persistence", "v1_D_raw", "v1_D_isotonic"]
METRICS = ["final_auc", "bin_f1", "final_r2"]
COUNTS = ["bin_tp", "bin_fp", "bin_fn"]


def load_setting(label: str, run: str, branch: str | None) -> pd.DataFrame:
    m = pd.read_csv(RESULTS / run / "metrics" / "metrics.csv")
    m = m[(m["horizon"] == 0) & (m["status"] == "ok")]
    is_d = m["view"].isin(D_VIEWS)
    if branch is not None:
        is_d &= m["branch"] == branch
    m = m[is_d | m["view"].isin(BASELINES)].copy()
    m["setting"] = label
    return m[["setting", "cohort", "view", "test_year", "n"] + METRICS + COUNTS]


def weighted(group: pd.DataFrame) -> pd.Series:
    out = {"n": group["n"].sum()}
    for col in METRICS:
        ok = group[col].notna()
        out[col] = (group.loc[ok, col] * group.loc[ok, "n"]).sum() / group.loc[ok, "n"].sum() if ok.all() else float("nan")
    tp, fp, fn = (group[c].sum() for c in COUNTS)
    out["pooled_f1"] = 2 * tp / (2 * tp + fp + fn)
    return pd.Series(out)


def build() -> pd.DataFrame:
    rows = pd.concat([load_setting(*s) for s in SETTINGS], ignore_index=True)
    rows = rows[rows["test_year"].isin([2025, 2026])]
    keys = ["setting", "cohort", "view"]
    per_year = rows.assign(period=rows["test_year"].astype(str), pooled_f1=float("nan"))
    avg = rows.groupby(keys).apply(weighted, include_groups=False).reset_index()
    avg["period"] = "2025+2026 n-weighted"
    cols = keys + ["period", "n"] + METRICS + ["pooled_f1"]
    return pd.concat([per_year[cols], avg[cols]], ignore_index=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=REPORTS_DIR / "somalia_oracle" / "wrapup_h0_d_vs_baselines.csv")
    args = parser.parse_args()
    table = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(args.out, index=False, float_format="%.4f")
    print(f"wrote {len(table)} rows to {args.out}")


if __name__ == "__main__":
    main()
