"""Run the six origin_safe_weather_oracle_v1 fits: 2 oracle arms x H3/H6/H12 x 4 annual blocks, one process at a time.

Only these six combinations exist; H0 and the oracle-free reference are reused from origin_safe_climate_idp_v1 by
explicit path and never refit here. Each combination is one ``--protocol origin-safe`` CLI run into its own
directory under ``results/experiments/origin_safe_weather_oracle_v1/runs``; the CLI resumes only batches whose
record matches the fingerprint and artifact hashes. A run is done only when ``run_metadata.json`` says COMPLETE.
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
from ipcch import weather_oracle as wo

CLI = PROJECT_ROOT / "scripts" / "modeling" / "run_deep_feature_weight_decay_forecasting.py"
MANIFEST = paths.SOURCE_DATA_DIR / "assembled_IPCCH" / "model_ready" / wo.ORACLE_VERSION / f"{wo.ORACLE_VERSION}_manifest.json"
RESULTS = paths.RESULTS_DIR / "experiments" / wo.ORACLE_VERSION / "runs"
FIXED = ["--half-life-months", "24", "--phase-threshold", "0.2", "--seed", "42", "--n-jobs", "16"]
PLAN = [(arm, horizon) for arm in wo.ORACLE_ARMS for horizon in wo.ORACLE_HORIZONS]


def run_dir(arm: str, horizon: int) -> Path:
    out = RESULTS / arm / f"{horizon}m"
    if wo.PARENT_VERSION in out.parts:
        raise ValueError(f"{out} is inside the reference namespace")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true", help="Run the CLI's validating dry run for every combination (writes nothing).")
    args = parser.parse_args()
    log_dir = RESULTS.parent / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    ledger = log_dir / ("suite_dry_run_ledger.jsonl" if args.dry_run else "suite_ledger.jsonl")
    for arm, horizon in PLAN:
        out = run_dir(arm, horizon)
        meta = out / "run_metadata.json"
        cmd = [sys.executable, str(CLI), "--protocol", "origin-safe", "--origin-manifest", str(MANIFEST), "--horizon", str(horizon),
               "--arm", arm, "--out-dir", str(out), *FIXED, *(["--dry-run"] if args.dry_run else [])]
        t0 = time.time()
        print(f"[run] {arm} H={horizon}{' (dry run)' if args.dry_run else ''}", flush=True)
        with open(log_dir / f"{arm}_{horizon}m{'_dry_run' if args.dry_run else ''}.log", "a") as log:
            code = subprocess.run(cmd, cwd=PROJECT_ROOT, stdout=log, stderr=subprocess.STDOUT,
                                  env={**os.environ, "PYTHONPATH": str(PROJECT_ROOT / "src"), "PYTHONUNBUFFERED": "1"}).returncode
        status = "DRY_RUN_OK" if args.dry_run and code == 0 else (json.loads(meta.read_text())["status"] if meta.exists() else None)
        record = {"arm": arm, "horizon": horizon, "returncode": code, "status": status, "seconds": round(time.time() - t0, 1),
                  "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "cmd": cmd}
        with open(ledger, "a") as fh:
            fh.write(json.dumps(record) + "\n")
        print(f"[done] {arm} H={horizon} rc={code} status={status} {record['seconds']}s", flush=True)
        if code != 0 or status not in ("COMPLETE", "DRY_RUN_OK"):
            return code or 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
