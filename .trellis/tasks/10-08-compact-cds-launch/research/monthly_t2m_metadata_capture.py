"""Read-only capture of monthly t2m GRIB time metadata and original 6-hourly timestamp support (CDS interpreter)."""
import hashlib, json, sys
from pathlib import Path
import eccodes

D = Path("../../../1.Source Data/CDS_API")
W = D / "compact_cds_launch_v1"
KEYS = ("edition", "centre", "system", "method", "shortName", "paramId", "units", "dataDate", "dataTime", "number", "marsType", "marsStream",
        "localDefinitionNumber", "forecastMonth", "verifyingMonth", "averagingPeriod", "stepUnits", "startStep", "endStep", "stepRange", "stepType",
        "timeRangeIndicator", "P1", "P2", "unitOfTimeRange", "typeOfStatisticalProcessing", "numberOfTimeRanges", "timeIncrement",
        "indicatorOfUnitForTimeIncrement", "typeOfTimeIncrement", "lengthOfTimeRange", "validityDate", "validityTime",
        "yearOfEndOfOverallTimeInterval", "monthOfEndOfOverallTimeInterval", "dayOfEndOfOverallTimeInterval", "hourOfEndOfOverallTimeInterval")


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 22), b""):
            h.update(c)
    return h.hexdigest()


def keys_of(h):
    out = {}
    for k in KEYS:
        try:
            out[k] = eccodes.codes_get(h, k)
        except Exception:
            out[k] = None  # key not defined for this edition/template
    return out


result = {"note": "None = key not defined for this message (GRIB1 lacks GRIB2 statistical-time keys)", "files": {}}
for label, path, want in (("official_anomaly_new", W / "raw/bulk/anomaly_official_leads2to6.grib", {"2ta"}),
                          ("old_absolute_monthly_apr2026", D / "c3s_seasonal_apr2026_all_leads.grib", {"2t", "t2m", "167"})):
    msgs = []
    with open(path, "rb") as f:
        i = 0
        while True:
            h = eccodes.codes_grib_new_from_file(f)
            if h is None:
                break
            i += 1
            k = keys_of(h)
            if str(k["shortName"]) in want or str(k["paramId"]) in ("167", "171167"):
                msgs.append({"message_index": i, **k})
            eccodes.codes_release(h)
    result["files"][label] = {"path": str(path), "sha256": sha(path), "temperature_messages": msgs}
# original 6-hourly support around the month boundaries (2026 forecast member 0 and hindcast 1993 member 0)
support = {}
for key in ("original_tmean_2026", "original_tmean_1993"):
    path = W / f"raw/bulk/{key}.grib"
    rows = []
    with open(path, "rb") as f:
        i = 0
        while True:
            h = eccodes.codes_grib_new_from_file(f)
            if h is None:
                break
            i += 1
            if eccodes.codes_get(h, "number") == 0:
                rows.append({"message_index": i, "endStep": eccodes.codes_get(h, "endStep"), "stepType": eccodes.codes_get(h, "stepType"),
                             "validity": f"{eccodes.codes_get(h, 'validityDate')} {eccodes.codes_get(h, 'validityTime'):04d}"})
            eccodes.codes_release(h)
    steps = sorted(r["endStep"] for r in rows)
    pick = {s: r for r in rows for s in (3672, 3678, 4386, 4392, 4398, 5130, 5136) if r["endStep"] == s}
    support[key] = {"path": str(path), "sha256": sha(path), "member0_messages": len(rows), "first_step": steps[0], "last_step": steps[-1],
                    "contiguous_6h": steps == list(range(steps[0], steps[-1] + 1, 6)), "boundary_messages": pick}
result["original_6h_support"] = support
out = Path(".trellis/tasks/10-08-compact-cds-launch/research/monthly_t2m_metadata_capture.json")
out.write_text(json.dumps(result, indent=1, default=str))
for label, f in result["files"].items():
    print("==", label, f["sha256"][:12], len(f["temperature_messages"]), "temperature messages")
    for m in f["temperature_messages"]:
        print({k: m[k] for k in ("message_index", "localDefinitionNumber", "forecastMonth", "verifyingMonth", "averagingPeriod", "startStep", "endStep",
                                 "stepType", "timeRangeIndicator", "P1", "P2", "typeOfStatisticalProcessing", "numberOfTimeRanges", "timeIncrement",
                                 "typeOfTimeIncrement", "validityDate", "validityTime")})
for k, v in support.items():
    print("==", k, {x: v[x] for x in ("member0_messages", "first_step", "last_step", "contiguous_6h")})
    for s, r in sorted(v["boundary_messages"].items()):
        print("  ", s, r)
