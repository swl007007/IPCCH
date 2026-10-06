"""Run the climate2015_v1 global comparison suite with the unchanged deep-feature CLI.

Arms: baseline_rerun (current fs files), climate2015_masked (primary), climate2015_unmasked (fs0-fs2).
Runs are sequential (15 GB machine); a run whose metrics_overall.csv exists is skipped.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = next(path for path in Path(__file__).resolve().parents if (path / "src").exists())
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from ipcch import paths

CLI = PROJECT_ROOT / "scripts" / "modeling" / "run_deep_feature_weight_decay_forecasting.py"
DATA_DIR = paths.SOURCE_DATA_DIR / "assembled_IPCCH" / "model_ready" / "climate2015_v1"
RESULTS = paths.RESULTS_DIR / "experiments" / "deep_feature_weight_decay_forecasting" / "climate2015_v1"
REPORTS = paths.REPORTS_DIR / "deep_feature_weight_decay_forecasting" / "climate2015_v1"
SCOPES = {"fs0": ("0m", "scope_0m_model_ready"), "fs1": ("3m", "scope_3m_model_ready"), "fs2": ("6m", "scope_6m_model_ready"), "fs3": ("12m", "forecasting_ready")}
ARMS = ("baseline_rerun", "climate2015_masked", "climate2015_unmasked")
COMMON = ["--region-scope", "0", "--add-identifier-features", "--phase-threshold", "0.2", "--half-life-months", "24",
          "--test-years", "2022", "2023", "2024", "2025", "--seed", "42"]


def plan(arms, scopes):
    for arm in arms:
        for fs in scopes:
            label, stem = SCOPES[fs]
            if arm == "climate2015_unmasked" and fs == "fs3":
                continue  # no scope block at 12m; identical to the masked dataset
            cmd = [sys.executable, str(CLI), "--fs", fs, *COMMON, "--out-dir", str(RESULTS / arm / label), "--report-dir", str(REPORTS / arm / label)]
            if arm != "baseline_rerun":
                variant = arm.split("_")[1]
                cmd += ["--dataset", str(DATA_DIR / f"forecasting_subset_IPCCH_2026_climate2015_v1_{variant}_{stem}.csv")]
            yield arm, label, cmd


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--arms", nargs="+", default=list(ARMS), choices=ARMS)
    parser.add_argument("--scopes", nargs="+", default=list(SCOPES), choices=list(SCOPES))
    parser.add_argument("--log-dir", default=str(RESULTS / "logs"))
    args = parser.parse_args()
    log_dir = Path(args.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    ledger = log_dir / "run_ledger.jsonl"
    for arm, label, cmd in plan(args.arms, args.scopes):
        done = RESULTS / arm / label / "metrics" / "metrics_overall.csv"
        if done.exists():
            print(f"[skip] {arm}/{label}", flush=True)
            continue
        t0 = time.time()
        print(f"[run] {arm}/{label}", flush=True)
        with open(log_dir / f"{arm}_{label}.log", "w") as log:
            code = subprocess.run(cmd, cwd=PROJECT_ROOT, stdout=log, stderr=subprocess.STDOUT, env={**os.environ, "PYTHONPATH": str(PROJECT_ROOT / "src")}).returncode
        record = {"arm": arm, "scope": label, "returncode": code, "seconds": round(time.time() - t0, 1), "cmd": cmd}
        with open(ledger, "a") as fh:
            fh.write(json.dumps(record) + "\n")
        print(f"[done] {arm}/{label} rc={code} {record['seconds']}s", flush=True)
        if code != 0:
            return code
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
