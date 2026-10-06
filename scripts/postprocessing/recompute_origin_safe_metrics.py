"""Recompute origin_safe_climate_idp_v1 run metrics from saved predictions (no refitting).

Audit finding A03: the first metrics reported exact five-class accuracy under the name ``accuracy``. This script
re-derives every run's ``metrics/metrics_overall.csv`` with the current ``origin_safe.origin_metrics``
(``exact_phase_accuracy`` and ``phase3plus_accuracy``) from the saved unrounded yearly predictions, after checking
each prediction file against its batch record hash. The previous file is kept as ``metrics_overall_pre_a03.csv``.
Models, predictions and run fingerprints are untouched.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = next(path for path in Path(__file__).resolve().parents if (path / "src").exists())
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import pandas as pd

from ipcch import origin_safe as osf
from ipcch import paths

RUNS = paths.RESULTS_DIR / "experiments" / "origin_safe_climate_idp_v1" / "runs"


def main() -> int:
    code = {p: osf.file_sha256(PROJECT_ROOT / p) for p in ("src/ipcch/origin_safe.py", "src/ipcch/forecasting_weight_decay.py", Path(__file__).relative_to(PROJECT_ROOT).as_posix())}
    for arm in osf.ARMS:
        for horizon in osf.HORIZONS:
            run = RUNS / arm / f"{horizon}m"
            meta = json.loads((run / "run_metadata.json").read_text())
            if meta["status"] != "COMPLETE":
                raise ValueError(f"{run} is not COMPLETE")
            frames = []
            for record in meta["batches"]:
                path = run / "batches" / str(record["block_year"]) / "predictions.csv"
                if osf.file_sha256(path) != record["artifacts"]["predictions.csv"]:
                    raise ValueError(f"{path} differs from its batch record")
                frames.append(pd.read_csv(path, float_precision="round_trip"))
            predictions = pd.concat(frames, ignore_index=True)
            if len(predictions) != meta["prediction_rows"] or predictions.duplicated(list(osf.KEYS)).any():
                raise ValueError(f"{run}: predictions do not cover the frozen keys exactly once")
            rows = [osf.flatten_origin_metrics(osf.origin_metrics(predictions[predictions["year"] == y], "overall", y)) for y in osf.TARGET_YEARS]
            rows.append(osf.flatten_origin_metrics(osf.origin_metrics(predictions, "overall", "pooled")))
            target = run / "metrics" / "metrics_overall.csv"
            previous = run / "metrics" / "metrics_overall_pre_a03.csv"
            if not previous.exists():
                target.replace(previous)
            pd.DataFrame(rows).to_csv(target, index=False)
            osf.dump_json(run / "metrics" / "metrics_recomputed.json", {
                "reason": "audit finding A03: report exact_phase_accuracy and phase3plus_accuracy separately",
                "source": "saved batch predictions (sha256-checked against batch records); no refit",
                "previous_file": previous.name, "code_sha256": code,
                "recomputed_utc": datetime.now(timezone.utc).isoformat()})
            print(f"{arm} H={horizon}: recomputed {len(rows)} metric rows from {len(predictions)} predictions", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
