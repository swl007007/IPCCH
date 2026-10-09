"""Build compact_cds_launch_v1 inputs in two explicit stages.

``--weather-only`` (CDS_API/.venv interpreter; imports only ``ipcch.cds_launch_weather``): submit/resume CDS requests by
recorded request ID, download, decode and aggregate ECMWF system51 April-2026 forecasts into the May-October weather cube
with provenance and the September overlap gate. ``--probe`` runs the small grid/cell gate before bulk requests.

``--assemble-only`` (frozen model interpreter): build every compact fitting/inference matrix from pinned sources and the
explicit weather cube. Never retrieves weather. Design: ``.trellis/tasks/10-08-compact-cds-launch/design.md``.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = next(path for path in Path(__file__).resolve().parents if (path / "src").exists())
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from ipcch import paths  # noqa: E402  (stdlib only)

VERSION = "compact_cds_launch_v1"
WEATHER_ROOT = paths.SOURCE_DATA_DIR / "CDS_API" / VERSION
INPUT_ROOT = paths.SOURCE_DATA_DIR / "assembled_IPCCH" / "model_ready" / VERSION
POINTS = paths.SOURCE_DATA_DIR / "assembled_IPCCH" / "spatial" / "unique_area_id_lat_lon.csv"
POINTS_SHA256 = "3bf8f115ec70cd1e1c907031309b797410a8024cdc1d39265be123ae636d2862"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    stage = parser.add_mutually_exclusive_group(required=True)
    stage.add_argument("--weather-only", action="store_true", help="CDS environment: retrieve/decode/aggregate the forecast cube.")
    stage.add_argument("--assemble-only", action="store_true", help="Frozen model environment: build compact matrices from the cube.")
    parser.add_argument("--probe", action="store_true", help="weather-only: small representative grid/cell gate instead of bulk requests.")
    parser.add_argument("--download-weather", action="store_true", help="weather-only: submit missing requests (resume by recorded ID) and download.")
    parser.add_argument("--poll-seconds", type=int, default=120, help="weather-only: seconds between provider status refreshes.")
    parser.add_argument("--max-hours", type=float, default=48.0, help="weather-only: stop polling after this many hours (state stays resumable).")
    parser.add_argument("--process", action="store_true", help="weather-only: decode downloaded GRIBs and write the cube/provenance/overlap gate.")
    parser.add_argument("--weather-root", default=str(WEATHER_ROOT))
    parser.add_argument("--input-root", default=str(INPUT_ROOT))
    parser.add_argument("--weather-cube", help="assemble-only: explicit weather cube CSV written by the weather-only stage.")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def log(message: str) -> None:
    print(f"[{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}] {message}", flush=True)


def load_points():
    import pandas as pd
    from ipcch import cds_launch_weather as cw

    if cw.file_sha256(POINTS) != POINTS_SHA256:
        raise SystemExit("fixed extraction points differ from the pinned sha256")
    pts = pd.read_csv(POINTS, float_precision="round_trip")
    import numpy as np

    if pts["area_id"].duplicated().any() or not np.isfinite(pts[["lat", "lon"]].to_numpy(dtype=float)).all():
        raise SystemExit("fixed points are not unique/finite")
    return pts.sort_values("area_id", kind="mergesort").reset_index(drop=True)


def retrieve(plan_name: str, plan: dict, root: Path, args) -> dict:
    from ipcch import cds_launch_weather as cw

    ledger_path = root / f"requests_{plan_name}.json"
    root.mkdir(parents=True, exist_ok=True)
    status_path = root / f"status_{plan_name}.json"
    client = cw.datastores_client()
    ledger = cw.submit_missing(client, plan, ledger_path, log)
    deadline = time.time() + args.max_hours * 3600
    while True:
        ledger = cw.poll_and_download(client, ledger_path, root / "raw" / plan_name, log)
        states = {k: e.get("status") for k, e in ledger["requests"].items()}
        done = all(e.get("file_sha256") for e in ledger["requests"].values())
        failed = sorted(k for k, s in states.items() if s in ("failed", "rejected", "dismissed", "deleted"))
        status_path.write_text(json.dumps({"updated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "plan": plan_name,
                                           "states": states, "complete": done, "failed": failed}, indent=2))
        if done or failed:
            log(f"{plan_name}: complete={done} failed={failed}")
            return ledger
        if time.time() > deadline:
            log(f"{plan_name}: polling window ended; requests stay recorded for resume")
            return ledger
        time.sleep(args.poll_seconds)


def main() -> int:
    args = parse_args()
    if args.assemble_only:
        from ipcch import compact_launch as cl  # model environment only

        return cl.assemble_main(args)
    from ipcch import cds_launch_weather as cw

    root = Path(args.weather_root)
    if any(part in ("compact_climate_weather_oracle_v1", "origin_safe_climate_idp_v1") for part in root.parts):
        raise SystemExit("refusing a legacy namespace")
    plan_name = "probe" if args.probe else "bulk"
    if args.download_weather:
        retrieve(plan_name, cw.request_plan(probe=args.probe), root, args)
    if args.probe and (args.process or args.download_weather):
        report = cw.probe_report(cw.load_ledger(root / "requests_probe.json"), load_points())
        out = root / "probe_grid_report.json"
        out.write_text(json.dumps(report, indent=2, default=str))
        log(f"probe report {out}: passed={report['passed']} problems={report['problems']}")
        return 0 if report["passed"] else 1
    if args.process:
        from ipcch import cds_launch_weather as cw2  # noqa: F401

        return process_main(root, args)
    return 0


def process_main(root: Path, args) -> int:
    from ipcch import cds_launch_weather as cw

    return cw.process_weather(root, load_points(), Path(args.input_root), log)


if __name__ == "__main__":
    raise SystemExit(main())
