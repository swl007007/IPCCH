"""Fit, report and verify compact_cds_launch_v1 (five unique fits, 20 cumulative regressors, April 2026 origin).

Stages (frozen model interpreter): ``--validate-only`` runs every prefit gate and writes nothing; ``--approve-training``
fits the fixed run plan sequentially (complete matching runs are verified and skipped); ``--report`` writes population
tables, maps and the actual-input codebook; ``--verify`` writes the independent arithmetic/replay verification.json and
launch_summary.md. Design: ``.trellis/tasks/10-08-compact-cds-launch/design.md``.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = next(path for path in Path(__file__).resolve().parents if (path / "src").exists())
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from ipcch import compact_launch as cl  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--input-manifest", default=str(cl.INPUT_ROOT / cl.MANIFEST_NAME))
    parser.add_argument("--results-root", default=str(cl.RESULTS_ROOT))
    parser.add_argument("--reports-root", default=str(cl.REPORTS_ROOT))
    parser.add_argument("--runs", nargs="+", choices=[cl.run_id(a, h) for a, h in cl.RUNS], help="Subset of runs (pilot: compact_baseline/0m).")
    parser.add_argument("--validate-only", action="store_true", help="Run every prefit gate; no fitting, nothing written.")
    parser.add_argument("--approve-training", action="store_true", help="Fit the run plan (resume only complete matching runs).")
    parser.add_argument("--report", action="store_true", help="Population tables, maps and actual-input codebook from saved runs.")
    parser.add_argument("--verify", action="store_true", help="Independent arithmetic/replay verification and launch summary.")
    args = parser.parse_args()
    if not (args.validate_only or args.approve_training or args.report or args.verify):
        parser.error("choose --validate-only, --approve-training, --report and/or --verify")
    return args


def main() -> int:
    args = parse_args()
    try:
        return cl.run_main(args)
    except cl.LaunchError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
