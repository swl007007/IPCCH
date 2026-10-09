"""Baseline-free timestamp probe: 2026 forecast 6-hourly 2t vs the official absolute September monthly ensemble mean.

Read-only (CDS interpreter). No hindcast/anomaly involved. Steps: verify the old monthly message is an ECMWF system51
April-2026 ensemble-mean 2t for verifying month 202609 (else record and stop); freeze per-convention bounds from message
packing metadata to a hashed file; only then aggregate the 51 members under [Sep 1 00, Oct 1 00) and (Sep 1 00, Oct 1 00]
and compare at every fixed point's containing cell. Outputs: CDS_API/compact_cds_launch_v1/diagnostic/absolute_probe_*.

Run from the repository root:
  PYTHONPATH=src "<Analysis>/1.Source Data/CDS_API/.venv/bin/python" .trellis/tasks/10-08-compact-cds-launch/research/absolute_monthly_timestamp_probe.py
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "src")
from ipcch import cds_launch_weather as cw  # noqa: E402

D = Path("../../../1.Source Data/CDS_API")
W = D / "compact_cds_launch_v1"
OUT = W / "diagnostic"
OUT.mkdir(parents=True, exist_ok=True)
MONTHLY = D / "c3s_seasonal_apr2026_all_leads.grib"
ORIG = W / "raw/bulk/original_tmean_2026.grib"
pts = pd.read_csv(D.parent / "assembled_IPCCH/spatial/unique_area_id_lat_lon.csv", float_precision="round_trip").sort_values("area_id").reset_index(drop=True)
result = {"mode": "DIAGNOSTIC timestamp probe (no acceptance)", "monthly_file": {"path": str(MONTHLY), "sha256": cw.file_sha256(MONTHLY)},
          "original_file": {"path": str(ORIG), "sha256": cw.file_sha256(ORIG)}}

# ---- 1. the official absolute monthly message: identity and ensemble-mean compatibility
mg = cw.first_grid(MONTHLY)
mcells = cw.containing_cells(mg, pts.lat, pts.lon)
monthly, mmeta, index = None, None, 0
import eccodes  # noqa: E402

with open(MONTHLY, "rb") as fh:
    while True:
        h = eccodes.codes_grib_new_from_file(fh)
        if h is None:
            break
        index += 1
        if eccodes.codes_get(h, "shortName") == "2t" and eccodes.codes_get(h, "verifyingMonth") == 202609:
            mmeta = {k: eccodes.codes_get(h, k) for k in ("centre", "system", "method", "dataDate", "dataTime", "number", "marsType", "marsStream",
                                                          "units", "forecastMonth", "verifyingMonth", "averagingPeriod", "endStep", "validityDate",
                                                          "binaryScaleFactor", "decimalScaleFactor", "packingError", "bitsPerValue")}
            mmeta["message_index"] = index
            monthly = eccodes.codes_get_values(h)[mcells["flat_index"].to_numpy()]
        eccodes.codes_release(h)
result["monthly_message"] = mmeta
compatible = mmeta is not None and mmeta["centre"] == "ecmf" and str(mmeta["system"]) == "51" and mmeta["method"] == 1 and \
    mmeta["dataDate"] == 20260401 and mmeta["dataTime"] == 0 and mmeta["marsType"] == "em" and mmeta["units"] == "K"
result["monthly_is_ensemble_mean_compatible"] = bool(compatible)
if not compatible:
    (OUT / "absolute_probe_result.json").write_text(json.dumps(result, indent=2, default=str))
    sys.exit("old monthly message is not an ECMWF system51 April-2026 ensemble-mean 2t; probe stopped")

# ---- 2. freeze per-convention bounds from metadata before any comparison
ocells = cw.containing_cells(cw.first_grid(ORIG), pts.lat, pts.lon)
assert cw.same_cells(mcells, ocells)
conv_steps = {c: set(cw.temperature_sample_hours(2026, (2026, 9), c)) for c in ("start_inclusive", "end_inclusive")}
step_err, ids, sums, counts = {}, {}, {c: np.zeros((51, len(pts))) for c in conv_steps}, {c: np.zeros(51, dtype=int) for c in conv_steps}
values_by = []
for meta, grid, v in cw.iter_messages(ORIG, ocells["flat_index"].to_numpy(), decode_values=False):
    s = int(meta["endStep"])
    step_err[s] = max(step_err.get(s, 0.0), cw.message_error(meta))
monthly_err = cw.message_error({"binaryScaleFactor": mmeta["binaryScaleFactor"], "decimalScaleFactor": mmeta["decimalScaleFactor"],
                                "packingError": mmeta["packingError"]})
bounds = {c: max(step_err[s] for s in steps) + monthly_err + cw.FLOAT_SLACK["tmean_K"] for c, steps in conv_steps.items()}
frozen = {"frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "bounds_K": bounds, "monthly_message_error_K": monthly_err,
          "max_6h_message_error_K": {c: max(step_err[s] for s in steps) for c, steps in conv_steps.items()},
          "rule": "|ensemble mean of member monthly means - official monthly ensemble mean| <= max per-value bound of the 6-hourly messages "
                  "used (max(half-step, packingError)) + the monthly message's bound + 1e-9 K",
          "conventions": {c: [min(s), max(s), len(s)] for c, s in conv_steps.items()}}
bpath = OUT / "absolute_probe_bounds_frozen.json"
bpath.write_text(json.dumps(frozen, indent=2))
result["bounds_frozen"] = {"path": str(bpath), "sha256": cw.file_sha256(bpath), **frozen}

# ---- 3. aggregate and compare (after freezing)
for meta, grid, v in cw.iter_messages(ORIG, ocells["flat_index"].to_numpy()):
    s, m = int(meta["endStep"]), int(meta["number"])
    for c, steps in conv_steps.items():
        if s in steps:
            sums[c][m] += v
            counts[c][m] += 1
rows = {"area_id": pts.area_id, "cell_lat": ocells.cell_lat, "cell_lon": ocells.cell_lon, "official_monthly_K": monthly}
for c in conv_steps:
    assert (counts[c] == len(conv_steps[c])).all()
    ens = (sums[c] / counts[c][:, None]).mean(axis=0)
    diff = ens - monthly
    rows[f"constructed_{c}_K"] = ens
    rows[f"diff_{c}_K"] = diff
    result[c] = {"bound_K": bounds[c], "max_abs_diff_K": float(np.abs(diff).max()), "mean_signed_diff_K": float(diff.mean()),
                 "p99_abs_diff_K": float(np.quantile(np.abs(diff), 0.99)), "points_over_bound": int((np.abs(diff) > bounds[c]).sum()),
                 "members": int(len(counts[c])), "samples_per_member": int(counts[c][0])}
pd.DataFrame(rows).to_csv(OUT / "absolute_probe_by_point.csv", index=False, float_format="%.17g")
(OUT / "absolute_probe_result.json").write_text(json.dumps(result, indent=2, default=str))
print(json.dumps({k: result[k] for k in ("monthly_message", "start_inclusive", "end_inclusive")}, indent=1, default=str))
print("bounds sha", result["bounds_frozen"]["sha256"][:12])
