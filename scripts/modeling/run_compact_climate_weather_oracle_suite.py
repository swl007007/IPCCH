"""Run the seven compact_climate_weather_oracle_v1 fits: compact_baseline H0/H3/H6/H12, compact_weather_oracle H3/H6/H12.

Each combination is one ``--protocol origin-safe`` CLI run (four annual blocks x four cumulative regressors) into
``results/experiments/compact_climate_weather_oracle_v1/runs/<arm>/<H>m``, one process at a time; the CLI resumes only
batches whose record matches the fingerprint and artifact hashes. H0 oracle is the shared compact baseline (no fit).
A run is done only when ``run_metadata.json`` says COMPLETE (or PARTIAL for an explicit ``--block-years`` pilot).
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

from ipcch import compact_features as cpf
from ipcch import paths

CLI = PROJECT_ROOT / "scripts" / "modeling" / "run_deep_feature_weight_decay_forecasting.py"
MANIFEST = paths.SOURCE_DATA_DIR / "assembled_IPCCH" / "model_ready" / cpf.VERSION / f"{cpf.VERSION}_manifest.json"
RESULTS = paths.RESULTS_DIR / "experiments" / cpf.VERSION / "runs"
FIXED = ["--half-life-months", "24", "--phase-threshold", "0.2", "--seed", "42", "--n-jobs", "16"]


def run_dir(arm: str, horizon: int) -> Path:
    out = RESULTS / arm / f"{horizon}m"
    if any(ns in out.parts for ns in cpf.LEGACY_NAMESPACES):
        raise ValueError(f"{out} is inside a legacy namespace")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true", help="Run the CLI's validating dry run for every combination; no directory, log or ledger is written.")
    parser.add_argument("--runs", nargs="+", help="Subset of run ids such as compact_baseline/0m (default: all seven, in plan order).")
    parser.add_argument("--block-years", nargs="+", help="Pilot: forward a subset of annual blocks to the CLI (run stays PARTIAL).")
    args = parser.parse_args()
    plan = [(arm, h) for arm, h in cpf.RUN_PLAN if not args.runs or f"{arm}/{h}m" in args.runs]
    unknown = sorted(set(args.runs or []) - {f"{a}/{h}m" for a, h in cpf.RUN_PLAN})
    if unknown:
        raise SystemExit(f"unknown run ids {unknown}; plan is {[f'{a}/{h}m' for a, h in cpf.RUN_PLAN]}")
    log_dir = RESULTS.parent / "logs"
    ledger = log_dir / "suite_ledger.jsonl"
    env = {**os.environ, "PYTHONPATH": str(PROJECT_ROOT / "src"), "PYTHONUNBUFFERED": "1"}
    for arm, horizon in plan:
        out = run_dir(arm, horizon)
        meta = out / "run_metadata.json"
        cmd = [sys.executable, str(CLI), "--protocol", "origin-safe", "--origin-manifest", str(MANIFEST), "--horizon", str(horizon),
               "--arm", arm, "--out-dir", str(out), *FIXED, *(["--block-years", *args.block_years] if args.block_years else []),
               *(["--dry-run"] if args.dry_run else [])]
        t0 = time.time()
        print(f"[run] {arm} H={horizon}{' (dry run)' if args.dry_run else ''}", flush=True)
        if args.dry_run:
            done = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True, env=env)
            code = done.returncode
            print(done.stdout.strip(), done.stderr.strip(), sep="\n", flush=True)
        else:
            log_dir.mkdir(parents=True, exist_ok=True)
            with open(log_dir / f"{arm}_{horizon}m.log", "a") as log:
                code = subprocess.run(cmd, cwd=PROJECT_ROOT, stdout=log, stderr=subprocess.STDOUT, env=env).returncode
        status = "DRY_RUN_OK" if args.dry_run and code == 0 else (json.loads(meta.read_text())["status"] if meta.exists() else None)
        record = {"arm": arm, "horizon": horizon, "returncode": code, "status": status, "seconds": round(time.time() - t0, 1),
                  "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "cmd": cmd}
        if not args.dry_run:
            with open(ledger, "a") as fh:
                fh.write(json.dumps(record) + "\n")
        print(f"[done] {arm} H={horizon} rc={code} status={status} {record['seconds']}s", flush=True)
        expected = ("DRY_RUN_OK",) if args.dry_run else (("PARTIAL", "COMPLETE") if args.block_years else ("COMPLETE",))
        if code != 0 or status not in expected:
            return code or 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
