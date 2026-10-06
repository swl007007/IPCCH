"""Run the origin_safe_climate_idp_v1 suite: 3 arms x 4 horizons x 4 annual fits, one process at a time.

Each arm/horizon is one ``--protocol origin-safe`` CLI run; the CLI checkpoints every annual block and
resumes only batches whose record matches the run fingerprint and artifact hashes. A run counts as done
only when its ``run_metadata.json`` says COMPLETE (metrics files alone are not completion).
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

from ipcch import origin_safe as osf
from ipcch import paths

VERSION = "origin_safe_climate_idp_v1"
CLI = PROJECT_ROOT / "scripts" / "modeling" / "run_deep_feature_weight_decay_forecasting.py"
MANIFEST = paths.SOURCE_DATA_DIR / "assembled_IPCCH" / "model_ready" / VERSION / f"{VERSION}_manifest.json"
RESULTS = paths.RESULTS_DIR / "experiments" / VERSION / "runs"
FIXED = ["--half-life-months", "24", "--phase-threshold", "0.2", "--seed", "42"]


def run_dir(arm: str, horizon: int) -> Path:
    return RESULTS / arm / f"{horizon}m"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--manifest", default=str(MANIFEST))
    parser.add_argument("--horizons", type=int, nargs="+", default=list(osf.HORIZONS), choices=osf.HORIZONS)
    parser.add_argument("--arms", nargs="+", default=list(osf.ARMS), choices=list(osf.ARMS))
    parser.add_argument("--n-jobs", type=int, default=16)
    parser.add_argument("--log-dir", default=str(RESULTS.parent / "logs"))
    args = parser.parse_args()
    log_dir = Path(args.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    ledger = log_dir / "suite_ledger.jsonl"
    for horizon in args.horizons:
        for arm in args.arms:
            out = run_dir(arm, horizon)
            meta = out / "run_metadata.json"
            cmd = [sys.executable, str(CLI), "--protocol", "origin-safe", "--origin-manifest", args.manifest,
                   "--horizon", str(horizon), "--arm", arm, "--out-dir", str(out), "--n-jobs", str(args.n_jobs), *FIXED]
            t0 = time.time()
            print(f"[run] {arm} H={horizon}", flush=True)
            with open(log_dir / f"{arm}_{horizon}m.log", "a") as log:
                code = subprocess.run(cmd, cwd=PROJECT_ROOT, stdout=log, stderr=subprocess.STDOUT,
                                      env={**os.environ, "PYTHONPATH": str(PROJECT_ROOT / "src"), "PYTHONUNBUFFERED": "1"}).returncode
            status = json.loads(meta.read_text())["status"] if meta.exists() else None
            record = {"arm": arm, "horizon": horizon, "returncode": code, "status": status, "seconds": round(time.time() - t0, 1),
                      "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "cmd": cmd}
            with open(ledger, "a") as fh:
                fh.write(json.dumps(record) + "\n")
            print(f"[done] {arm} H={horizon} rc={code} status={status} {record['seconds']}s", flush=True)
            if code != 0 or status != "COMPLETE":
                return code or 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
