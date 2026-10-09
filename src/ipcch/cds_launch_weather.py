"""compact_cds_launch_v1 forecast-weather cube: ECMWF system51, April 1 2026 initialization, true May-October 2026.

Contract (task ``10-08-compact-cds-launch``, ``design.md`` "CDS weather acquisition and monthly definition"):

- Inference-only substitute for the 12 compact oracle literals ``oracle_{prcp,tmean}_anom_month_ensmean_o{k}``,
  k = 1..6 = true statistical months May..October 2026. Training keeps the realized compact oracle values.
- True May-September: official ``seasonal-postprocessed-single-levels`` ensemble-mean monthly anomalies, leadtime_month
  2..6 (lead 1 is the initialization month April). The verifying month in the GRIB is authoritative, not file labels.
- True October: constructed from ``seasonal-original-single-levels`` of the same initialization: 2026 forecast members
  minus the equal-year mean of the 1993-2016 April-initialized system51 hindcast ensemble means. Temperature = mean of
  6-hourly instantaneous samples valid in (October 1 00, November 1 00] UTC; precipitation = accumulated P(Nov 1) - P(Oct 1).
  The temperature window was empirically verified against the supplied system51 September absolute monthly ensemble mean and
  September anomaly products (the initial [start, end) window failed both; production attempt v2 rejected); official primary
  documents (ECMWF Set V, C3S product descriptions) do not explicitly state endpoint inclusivity. The same algorithm on September must agree with the official September anomaly within bounds
  frozen from the retrieved GRIB packing metadata before acceptance.
- Original ``total_precipitation`` is accumulated since the forecast start (provider definition,
  https://cds.climate.copernicus.eu/datasets/seasonal-original-single-levels?tab=overview); the retrieved GRIB1 messages
  encode only a single forecast time (timeRangeIndicator 10, stepType instant, start = end step). Monthly totals are the raw
  signed end-minus-start differences (provider conversion table); decreases between endpoints are recorded as a keyed
  source diagnostic (ECMWF documents spurious decrements in packed cumulative fields), not a gate. Acceptance is the
  September overlap with the official rate anomaly within bounds frozen from the downloaded metadata.
- Units: temperature anomaly K is a temperature difference (= degC difference, never minus 273.15); precipitation
  anomaly rate m/s x 1000 x 86400 x days(month) = mm/month; accumulated m x 1000 = mm.
- Extraction: fixed containing-cell sampling at the pinned area points (``rasterio.sample`` semantics on the
  regular lat/lon grid: floor of the offset from the west/north cell edges, longitudes wrapped to the grid); no
  interpolation or polygon weighting. Model reference 1993-2016 differs from the observed 1991-2020 training reference.

Module level imports only the standard library, NumPy and pandas, so the pure arithmetic is testable in the frozen
model environment; ecCodes/cdsapi are imported inside the weather-only functions (CDS environment).
"""
from __future__ import annotations

import calendar
import datetime as dt
import hashlib
import json
import math
import os
import time
import urllib.parse
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

VERSION = "compact_cds_launch_v1"
CENTRE = "ecmwf"
SYSTEM = "51"
INIT_MONTH, INIT_DAY = 4, 1
FORECAST_YEAR = 2026
HINDCAST_YEARS = tuple(range(1993, 2017))
EXPECTED_MEMBERS = {"forecast": 51, "hindcast": 25}
REFERENCE_PERIOD = "1993-2016 April-initialized ECMWF system51 hindcasts"
POSTPROCESSED = "seasonal-postprocessed-single-levels"
ORIGINAL = "seasonal-original-single-levels"
ANOMALY_VARIABLES = {"tmean": "2m_temperature_anomaly", "prcp": "total_precipitation_anomalous_rate_of_accumulation"}
ORIGINAL_VARIABLES = {"tmean": "2m_temperature", "prcp": "total_precipitation"}
ORACLE_LITERALS = {"prcp": "prcp_anom_month_ensmean", "tmean": "tmean_anom_month_ensmean"}
TRUE_MONTHS = tuple((FORECAST_YEAR, m) for m in range(5, 11))  # offset k = index + 1 from origin April 2026
OFFICIAL_LEADS = {2: (2026, 5), 3: (2026, 6), 4: (2026, 7), 5: (2026, 8), 6: (2026, 9)}
OVERLAP_MONTH = (2026, 9)
CONSTRUCTED_MONTH = (2026, 10)
TEMPERATURE_STEP_HOURS = 6
# samples valid in (month start, next month start] UTC: empirically verified on supplied system51 September products
# (supervisor decision research/supervisor-temperature-convention-decision.md); the initial [start, end) window was rejected
TEMPERATURE_CONVENTION = "end_inclusive"
# versioned evidence (relative to the weather root) referenced with hashes in every provenance record
CONVENTION_EVIDENCE = ("diagnostic/overlap_bounds_frozen_diagnostic.json", "diagnostic/september_overlap_diagnostic.json",
                       "diagnostic/september_overlap_by_point_diagnostic.csv", "diagnostic/absolute_probe_bounds_frozen.json",
                       "diagnostic/absolute_probe_result.json", "diagnostic/absolute_probe_by_point.csv",
                       "rejected_v1/cds_weather_provenance.json", "rejected_v1/process.log", "rejected_v1/process_code_sha256.txt",
                       "rejected_v2/cds_weather_provenance.json", "rejected_v2/process_v2.log", "rejected_v2/process_v2_code_sha256.txt",
                       "rejected_v2/overlap_bounds_frozen.json", "rejected_v2/september_overlap_gate.json",
                       "rejected_v2/tp_monotonicity_diagnostic.csv", "evidence/supervisor-temperature-convention-decision.md",
                       "evidence/september-overlap-temperature-finding.md", "evidence/precip-monotonicity-finding.md",
                       "evidence/tp_decreases_beyond_endpoint_bounds.csv")
# Area request (north, west, south, east) covering every fixed point's containing 1-degree cell; cropping only.
AREA = [40, -93, -36, 128]
FLOAT_SLACK = {"tmean_K": 1e-9, "prcp_m_per_s": 1e-15}


# --------------------------------------------------------------------------- calendar and units


def oracle_column(var: str, k: int) -> str:
    """Existing compact literal (``weather_oracle.raw_name``) for variable ``prcp``/``tmean`` at offset ``k``."""
    return f"oracle_{ORACLE_LITERALS[var]}_o{k}"


def oracle_columns() -> List[str]:
    """Offset-major, precipitation then temperature (compact append order)."""
    return [oracle_column(v, k) for k in range(1, 7) for v in ("prcp", "tmean")]


def days_in_month(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1]


def month_start(year: int, month: int) -> dt.datetime:
    return dt.datetime(year, month, 1)


def next_month(year: int, month: int) -> Tuple[int, int]:
    return (year + 1, 1) if month == 12 else (year, month + 1)


def hours_since_init(init_year: int, when: dt.datetime) -> int:
    delta = when - dt.datetime(init_year, INIT_MONTH, INIT_DAY)
    hours = delta.total_seconds() / 3600
    if hours != int(hours):
        raise ValueError("non-integer forecast hour")
    return int(hours)


def month_bounds_hours(init_year: int, year_offset_month: Tuple[int, int]) -> Tuple[int, int]:
    """Lead hours of the month's start and of the next month's start, for an initialization in ``init_year``.

    ``year_offset_month`` is the forecast-year calendar month; hindcast years use the same calendar month of their own
    year (April-October contains no February, so the bounds are identical for every year)."""
    y, m = year_offset_month
    dy = y - FORECAST_YEAR
    start = month_start(init_year + dy, m)
    ny, nm = next_month(init_year + dy, m)
    return hours_since_init(init_year, start), hours_since_init(init_year, month_start(ny, nm))


def temperature_sample_hours(init_year: int, month: Tuple[int, int], convention: str = TEMPERATURE_CONVENTION) -> List[int]:
    start, end = month_bounds_hours(init_year, month)
    if convention == "start_inclusive":
        return list(range(start, end, TEMPERATURE_STEP_HOURS))
    if convention == "end_inclusive":
        return list(range(start + TEMPERATURE_STEP_HOURS, end + 1, TEMPERATURE_STEP_HOURS))
    raise ValueError(f"unknown convention {convention}")


def rate_to_mm_per_month(rate_m_per_s, year: int, month: int):
    return np.asarray(rate_m_per_s, dtype=float) * 1000.0 * 86400.0 * days_in_month(year, month)


def seconds_in_month(year: int, month: int) -> float:
    return 86400.0 * days_in_month(year, month)


# --------------------------------------------------------------------------- requests


def anomaly_request() -> dict:
    """Official ensemble-mean monthly anomalies for true May-September 2026 (leads 2..6), global 1x1 grid."""
    return {"originating_centre": CENTRE, "system": SYSTEM, "variable": [ANOMALY_VARIABLES["tmean"], ANOMALY_VARIABLES["prcp"]],
            "product_type": ["ensemble_mean"], "year": [str(FORECAST_YEAR)], "month": [f"{INIT_MONTH:02d}"],
            "leadtime_month": [str(lead) for lead in sorted(OFFICIAL_LEADS)], "data_format": "grib"}


def original_temperature_hours() -> List[int]:
    """6-hourly steps from September 1 00 UTC through November 1 00 UTC (both conventions computable)."""
    start, _ = month_bounds_hours(FORECAST_YEAR, OVERLAP_MONTH)
    _, end = month_bounds_hours(FORECAST_YEAR, CONSTRUCTED_MONTH)
    return list(range(start, end + 1, TEMPERATURE_STEP_HOURS))


def original_precipitation_hours() -> List[int]:
    sep_start, sep_end = month_bounds_hours(FORECAST_YEAR, OVERLAP_MONTH)
    oct_start, oct_end = month_bounds_hours(FORECAST_YEAR, CONSTRUCTED_MONTH)
    assert sep_end == oct_start
    return [sep_start, oct_start, oct_end]


def original_request(var: str, years: Sequence[int], hours: Optional[Sequence[int]] = None) -> dict:
    hours = list(hours) if hours is not None else (original_temperature_hours() if var == "tmean" else original_precipitation_hours())
    return {"originating_centre": CENTRE, "system": SYSTEM, "variable": [ORIGINAL_VARIABLES[var]], "year": [str(y) for y in years],
            "month": [f"{INIT_MONTH:02d}"], "day": [f"{INIT_DAY:02d}"], "leadtime_hour": [str(h) for h in hours],
            "area": list(AREA), "data_format": "grib"}


def request_plan(probe: bool) -> Dict[str, Tuple[str, dict]]:
    """Ordered request keys -> (dataset, request). ``probe``: the small grid/cell gate before bulk retrieval."""
    if probe:
        sep_start = original_temperature_hours()[0]
        return {
            "anomaly_official_leads2to6": (POSTPROCESSED, anomaly_request()),
            "probe_original_tmean_2026_sep1": (ORIGINAL, original_request("tmean", [FORECAST_YEAR], [sep_start])),
            "probe_original_tmean_1993_sep1": (ORIGINAL, original_request("tmean", [HINDCAST_YEARS[0]], [sep_start])),
            "probe_original_prcp_2026_sep1": (ORIGINAL, original_request("prcp", [FORECAST_YEAR], [sep_start])),
            "probe_original_prcp_1993_sep1": (ORIGINAL, original_request("prcp", [HINDCAST_YEARS[0]], [sep_start])),
        }
    plan = {"anomaly_official_leads2to6": (POSTPROCESSED, anomaly_request()),
            "original_prcp_2026": (ORIGINAL, original_request("prcp", [FORECAST_YEAR])),
            "original_prcp_hindcast": (ORIGINAL, original_request("prcp", HINDCAST_YEARS)),
            "original_tmean_2026": (ORIGINAL, original_request("tmean", [FORECAST_YEAR]))}
    for y in HINDCAST_YEARS:
        plan[f"original_tmean_{y}"] = (ORIGINAL, original_request("tmean", [y]))
    return plan


def request_sha256(dataset: str, request: Mapping) -> str:
    return hashlib.sha256(json.dumps({"dataset": dataset, "request": request}, sort_keys=True).encode()).hexdigest()


# --------------------------------------------------------------------------- grid and containing cells


def grid_from_keys(keys: Mapping[str, float]) -> Dict[str, float]:
    """Regular lat/lon grid description from GRIB keys; only north-to-south, west-to-east row-major is accepted, and only
    the system51 1-degree grid with cell centres at half-degree latitudes/longitudes (cell edges on whole degrees)."""
    if keys["gridType"] != "regular_ll":
        raise ValueError(f"unsupported gridType {keys['gridType']}")
    if int(keys["jScansPositively"]) != 0 or int(keys["iScansNegatively"]) != 0 or int(keys["jPointsAreConsecutive"]) != 0:
        raise ValueError("unsupported scanning mode (expected north-to-south rows, west-to-east, i consecutive)")
    di, dj = float(keys["iDirectionIncrementInDegrees"]), float(keys["jDirectionIncrementInDegrees"])
    ni, nj = int(keys["Ni"]), int(keys["Nj"])
    lat1, lon1 = float(keys["latitudeOfFirstGridPointInDegrees"]), float(keys["longitudeOfFirstGridPointInDegrees"])
    lat2, lon2 = float(keys["latitudeOfLastGridPointInDegrees"]), float(keys["longitudeOfLastGridPointInDegrees"])
    if not math.isclose(lat1 - (nj - 1) * dj, lat2, abs_tol=1e-6) or not math.isclose(((lon2 - lon1) % 360), ((ni - 1) * di) % 360, abs_tol=1e-6):
        raise ValueError("grid first/last points inconsistent with increments")
    if di != 1.0 or dj != 1.0 or not math.isclose((lat1 - 0.5) % 1.0, 0.0, abs_tol=1e-9) or not math.isclose((lon1 - 0.5) % 1.0, 0.0, abs_tol=1e-9):
        raise ValueError(f"grid is not the half-degree-centred 1-degree system51 grid (first point {lat1}/{lon1}, increments {dj}/{di})")
    return {"ni": ni, "nj": nj, "di": di, "dj": dj, "north_edge": lat1 + dj / 2.0, "west_edge": lon1 - di / 2.0,
            "first_lat": lat1, "first_lon": lon1, "last_lat": lat2, "last_lon": lon2}


def containing_cells(grid: Mapping[str, float], lat, lon) -> pd.DataFrame:
    """Row/column of the cell containing each point (``rasterio.sample`` floor semantics) and its centre."""
    lat = np.asarray(lat, dtype=float)
    lon = np.asarray(lon, dtype=float)
    col = np.floor(np.mod(lon - grid["west_edge"], 360.0) / grid["di"]).astype(int)
    row = np.floor((grid["north_edge"] - lat) / grid["dj"]).astype(int)
    inside = (row >= 0) & (row < grid["nj"]) & (col >= 0) & (col < grid["ni"])
    centre_lat = grid["north_edge"] - (row + 0.5) * grid["dj"]
    centre_lon = np.mod(grid["west_edge"] + (col + 0.5) * grid["di"] + 180.0, 360.0) - 180.0
    return pd.DataFrame({"row": row, "col": col, "inside": inside, "flat_index": row * grid["ni"] + col,
                         "cell_lat": centre_lat, "cell_lon": centre_lon})


def same_cells(a: pd.DataFrame, b: pd.DataFrame) -> bool:
    """Two grids select the same physical cell (identical centres) for every point."""
    return bool(np.allclose(a["cell_lat"], b["cell_lat"], rtol=0, atol=1e-9) and np.allclose(a["cell_lon"], b["cell_lon"], rtol=0, atol=1e-9)
                and a["inside"].all() and b["inside"].all())


# --------------------------------------------------------------------------- packing bounds and monthly arithmetic


def packing_half_step(binary_scale: int, decimal_scale: int) -> float:
    """Maximum simple-packing rounding error of one value: 0.5 * 2**E / 10**D."""
    return 0.5 * (2.0 ** int(binary_scale)) / (10.0 ** int(decimal_scale))


def overlap_bounds(q_forecast_t: float, q_hindcast_t: float, q_official_t: float, q_total_forecast_p: float, q_total_hindcast_p: float,
                   q_official_p: float, month: Tuple[int, int]) -> Dict[str, float]:
    """Absolute agreement bounds for the constructed vs official monthly anomaly, from per-value decoding bounds.

    Temperature: a mean of values each within e is within max e over the month's own samples, for the forecast mean and
    the hindcast mean, plus the official field's bound. Precipitation: ``q_total_*`` bounds one monthly total
    (start-endpoint + end-endpoint accumulation bounds of that month), for forecast and hindcast, converted to a rate,
    plus the official rate's bound. Only the month's own samples/endpoints enter (no other month's messages).
    """
    sec = seconds_in_month(*month)
    return {"tmean_K": q_forecast_t + q_hindcast_t + q_official_t + FLOAT_SLACK["tmean_K"],
            "prcp_m_per_s": (q_total_forecast_p + q_total_hindcast_p) / sec + q_official_p + FLOAT_SLACK["prcp_m_per_s"]}


def message_semantics_problems(meta: Mapping, dataset: str) -> List[str]:
    """Per-message time/parameter semantics: April 1 00 UTC initialization, single forecast time (start = end step,
    hours), validity = initialization + step, expected parameter/units/MARS type; official messages: lead -> verifying
    month and month-start validity boundary."""
    p = []
    short = str(meta.get("shortName"))
    want = MESSAGE_SEMANTICS.get(short)
    if want is None or (dataset == POSTPROCESSED) != (short in ("2ta", "tpara")):
        return [f"unexpected parameter {short} for {dataset}"]
    for k, v in want.items():
        if str(meta.get(k)) != str(v):
            p.append(f"{short}: {k}={meta.get(k)} != {v}")
    for k, v in SOURCE_IDENTITY.items():
        if str(meta.get(k)) != v:
            p.append(f"{short}: {k}={meta.get(k)} != {v}")
    date, time_ = int(meta["dataDate"]), int(meta["dataTime"])
    if date % 10000 != INIT_MONTH * 100 + INIT_DAY or time_ != 0:
        p.append(f"{short}: initialization {date} {time_:04d} is not April 1 00 UTC")
    if str(meta.get("stepUnits")) not in ("1", "h") or meta.get("stepType") != "instant" or str(meta.get("timeRangeIndicator")) != "10" \
            or meta.get("startStep") != meta.get("endStep"):
        p.append(f"{short}: step encoding {meta.get('stepUnits')}/{meta.get('stepType')}/TRI {meta.get('timeRangeIndicator')}/"
                 f"{meta.get('startStep')}-{meta.get('endStep')} is not a single forecast time in hours")
    init = dt.datetime(date // 10000, INIT_MONTH, INIT_DAY)
    valid = dt.datetime.strptime(f"{int(meta['validityDate'])}{int(meta['validityTime']):04d}", "%Y%m%d%H%M")
    if valid != init + dt.timedelta(hours=int(meta["endStep"])):
        p.append(f"{short}: validity {valid} != initialization + {meta['endStep']} h")
    if dataset == POSTPROCESSED:
        vm = int(meta["verifyingMonth"])
        ny, nm = next_month(vm // 100, vm % 100)
        if OFFICIAL_LEADS.get(int(meta["forecastMonth"])) != (vm // 100, vm % 100) or (valid.year, valid.month, valid.day, valid.hour) != (ny, nm, 1, 0):
            p.append(f"{short}: lead {meta['forecastMonth']} / verifying month {vm} / validity {valid} inconsistent")
    return p


def ensemble_monthly_anomaly(forecast_members: np.ndarray, hindcast_by_year: Mapping[int, np.ndarray]) -> Dict[str, np.ndarray]:
    """Forecast member mean minus the equal-year mean of hindcast ensemble means (arrays: members x points)."""
    f = np.asarray(forecast_members, dtype=float).mean(axis=0)
    years = sorted(hindcast_by_year)
    yearly = np.stack([np.asarray(hindcast_by_year[y], dtype=float).mean(axis=0) for y in years])
    clim = yearly.mean(axis=0)
    return {"forecast_mean": f, "hindcast_climatology": clim, "anomaly": f - clim}


def monthly_total_from_accumulations(p_start: np.ndarray, p_end: np.ndarray) -> np.ndarray:
    return np.asarray(p_end, dtype=float) - np.asarray(p_start, dtype=float)


# --------------------------------------------------------------------------- retrieval ledger (CDS environment)


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_ledger(path: Path) -> dict:
    return json.loads(path.read_text()) if path.exists() else {"version": VERSION, "requests": {}}


def save_ledger(path: Path, ledger: dict) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(ledger, indent=2))
    os.replace(tmp, path)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 22), b""):
            digest.update(chunk)
    return digest.hexdigest()


def datastores_client():
    """``ecmwf.datastores`` client configured from the home ``.cdsapirc`` by cdsapi (contents never read/printed here)."""
    import cdsapi

    return cdsapi.Client(quiet=True, progress=False, wait_until_complete=False).client


def submit_missing(client, plan: Mapping[str, Tuple[str, dict]], ledger_path: Path, log=print) -> dict:
    """Submit each planned request once; a request with a recorded ID is never resubmitted (resume by ID)."""
    ledger = load_ledger(ledger_path)
    for key, (dataset, request) in plan.items():
        entry = ledger["requests"].get(key)
        digest = request_sha256(dataset, request)
        if entry is not None:
            if entry["request_sha256"] != digest:
                raise ValueError(f"{key}: ledger request differs from the plan; refusing to mix requests")
            if entry.get("request_id") and entry.get("status") not in ("failed", "rejected", "dismissed", "deleted"):
                continue
        remote = client.submit(dataset, request)
        ledger["requests"][key] = {"dataset": dataset, "request": request, "request_sha256": digest, "request_id": remote.request_id,
                                   "submitted_utc": _now(), "status": "submitted", "history": [(_now(), "submitted")],
                                   "previous_attempts": (entry or {}).get("previous_attempts", []) + ([entry] if entry else [])}
        save_ledger(ledger_path, ledger)
        log(f"submitted {key}: request_id {remote.request_id}")
    return ledger


def poll_and_download(client, ledger_path: Path, raw_dir: Path, log=print) -> dict:
    """Refresh every request's provider state; download each successful result once, verifying its size."""
    ledger = load_ledger(ledger_path)
    raw_dir.mkdir(parents=True, exist_ok=True)
    for key, entry in ledger["requests"].items():
        if entry.get("file_sha256"):
            path = Path(entry["file"])
            if path.exists() and file_sha256(path) == entry["file_sha256"]:
                continue
            # cached file missing or replaced: keep the request ID, record the event and download it again
            entry.setdefault("redownloads", []).append({"utc": _now(), "previous_sha256": entry["file_sha256"],
                                                        "reason": "missing" if not path.exists() else "bytes changed"})
            for field in ("file", "file_bytes", "file_sha256", "downloaded_utc"):
                entry.pop(field, None)
            save_ledger(ledger_path, ledger)
            log(f"{key}: cached file {'missing' if not path.exists() else 'changed'}; re-downloading request {entry['request_id']}")
        remote = client.get_remote(entry["request_id"])
        status = remote.status
        if status != entry.get("status"):
            entry["history"].append((_now(), status))
            entry["status"] = status
            save_ledger(ledger_path, ledger)  # provider state is durable before any download attempt
        if status in ("failed", "rejected", "dismissed", "deleted"):
            log(f"{key}: provider status {status}")
        if status == "successful":
            results = client.get_results(entry["request_id"])
            asset = dict(results.asset)
            target = raw_dir / f"{key}.grib"
            tmp = raw_dir / f"{key}.grib.part"
            results.download(str(tmp))
            if tmp.stat().st_size != results.content_length:
                raise ValueError(f"{key}: downloaded size differs from the provider asset")
            os.replace(tmp, target)
            entry.update({"file": str(target), "file_bytes": target.stat().st_size, "file_sha256": file_sha256(target),
                          "downloaded_utc": _now(), "asset": {"file:size": asset.get("file:size"), "type": asset.get("type"),
                                                               "href_path": urllib.parse.urlparse(str(asset.get("href", ""))).path}})
            for attr in ("created_at", "started_at", "finished_at"):
                try:
                    value = getattr(remote, attr)
                    entry[attr] = value.isoformat() if value is not None else None
                except Exception:  # provider metadata is optional evidence
                    pass
            log(f"downloaded {key}: {entry['file_bytes']} bytes")
        save_ledger(ledger_path, ledger)
    return ledger


# --------------------------------------------------------------------------- GRIB decoding (CDS environment)

GRID_KEYS = ("gridType", "Ni", "Nj", "iDirectionIncrementInDegrees", "jDirectionIncrementInDegrees", "latitudeOfFirstGridPointInDegrees",
             "longitudeOfFirstGridPointInDegrees", "latitudeOfLastGridPointInDegrees", "longitudeOfLastGridPointInDegrees",
             "jScansPositively", "iScansNegatively", "jPointsAreConsecutive")
META_KEYS = ("edition", "centre", "shortName", "units", "dataDate", "dataTime", "number", "packingType", "bitsPerValue",
             "binaryScaleFactor", "decimalScaleFactor", "referenceValue")
OPTIONAL_KEYS = ("system", "method", "forecastMonth", "verifyingMonth", "startStep", "endStep", "stepRange", "stepType", "validityDate",
                 "validityTime", "typeOfStatisticalProcessing", "packingError", "productDefinitionTemplateNumber", "numberOfForecastsInEnsemble",
                 "stepUnits", "timeRangeIndicator", "paramId", "marsType", "marsStream")
# ECMWF system51 source identity required on every message (centre, forecasting system, method)
SOURCE_IDENTITY = {"centre": "ecmf", "system": SYSTEM, "method": "1"}
# Expected per-message semantics (verified on the retrieved GRIB1 files): parameter, units, MARS type/stream.
MESSAGE_SEMANTICS = {
    "2t": {"paramId": 167, "units": "K", "marsType": "fc", "marsStream": "mmsf"},
    "tp": {"paramId": 228, "units": "m", "marsType": "fc", "marsStream": "mmsf"},
    "2ta": {"paramId": 171167, "units": "K", "marsType": "em", "marsStream": "mmsa"},
    "tpara": {"paramId": 173228, "units": "m s**-1", "marsType": "em", "marsStream": "mmsa"},
}


def iter_messages(path: Path, cell_index: Optional[np.ndarray], decode_values: bool = True):
    """Yield (metadata dict, grid dict, sampled values at ``cell_index`` for the message's own grid); with
    ``decode_values=False`` only keys are read (values None)."""
    import eccodes

    with open(path, "rb") as fh:
        while True:
            h = eccodes.codes_grib_new_from_file(fh)
            if h is None:
                break
            try:
                try:
                    eccodes.codes_set(h, "stepUnits", "h")
                except Exception:
                    pass
                meta = {k: eccodes.codes_get(h, k) for k in META_KEYS}
                for k in OPTIONAL_KEYS:
                    try:
                        meta[k] = eccodes.codes_get(h, k)
                    except Exception:
                        meta[k] = None
                grid = {k: eccodes.codes_get(h, k) for k in GRID_KEYS}
                if not decode_values:
                    yield meta, grid, None
                    continue
                values = eccodes.codes_get_values(h)
                missing = eccodes.codes_get(h, "missingValue") if eccodes.codes_get(h, "bitmapPresent") else None
                sampled = values[cell_index] if cell_index is not None else values
                if missing is not None:
                    sampled = np.where(sampled == missing, np.nan, sampled)
                yield meta, grid, np.asarray(sampled, dtype=float)
            finally:
                eccodes.codes_release(h)


def first_grid(path: Path) -> Dict[str, float]:
    for _, grid, _ in iter_messages(path, None, decode_values=False):
        return grid_from_keys(grid)
    raise ValueError(f"{path}: no GRIB messages")


# --------------------------------------------------------------------------- expected identities and the probe gate


def expected_identity(key: str, dataset: str, request: Mapping) -> Dict[str, object]:
    """What a downloaded file for a planned request must contain (system, initialization dates, members, steps, names)."""
    years = [int(y) for y in request["year"]]
    out = {"dataset": dataset, "system": SYSTEM, "data_dates": sorted(y * 10000 + INIT_MONTH * 100 + INIT_DAY for y in years)}
    if dataset == POSTPROCESSED:
        out.update(short_names=["2ta", "tpara"], members=[0], forecast_months=[int(x) for x in request["leadtime_month"]],
                   verifying_months=sorted(y * 100 + m for lead, (y, m) in OFFICIAL_LEADS.items() if str(lead) in request["leadtime_month"]))
        out["messages"] = len(out["short_names"]) * len(out["forecast_months"])
    else:
        short = {"2m_temperature": "2t", "total_precipitation": "tp"}[request["variable"][0]]
        steps = sorted(int(h) for h in request["leadtime_hour"])
        n_members = sum(EXPECTED_MEMBERS["forecast" if y == FORECAST_YEAR else "hindcast"] for y in years)
        out.update(short_names=[short], steps=steps, members_by_year={y: EXPECTED_MEMBERS["forecast" if y == FORECAST_YEAR else "hindcast"] for y in years},
                   messages=n_members * len(steps))
    return out


def decoded_identity(path: Path) -> Tuple[Dict[str, object], Dict[str, float]]:
    """Decode every message's identity keys (no values kept) and the single grid of the file."""
    grids, rows, semantic = set(), [], []
    dataset = POSTPROCESSED if path.name.startswith(("anomaly", "probe_anomaly")) else ORIGINAL
    for meta, grid, _ in iter_messages(path, None, decode_values=False):
        grids.add(json.dumps(grid_from_keys(grid), sort_keys=True))
        rows.append(meta)
        semantic += message_semantics_problems(meta, dataset)
    if len(grids) != 1:
        raise ValueError(f"{path.name}: {len(grids)} grids")
    frame = pd.DataFrame(rows)
    found = {"messages": len(frame), "system": sorted(frame["system"].astype(str).unique().tolist()),
             "data_dates": sorted(frame["dataDate"].astype(int).unique().tolist()), "short_names": sorted(frame["shortName"].astype(str).unique().tolist()),
             "members_by_date": {int(d): sorted(g["number"].astype(int).unique().tolist()) for d, g in frame.groupby("dataDate")},
             "steps": sorted(frame["endStep"].astype(int).unique().tolist()),
             "forecast_months": sorted(frame["forecastMonth"].dropna().astype(int).unique().tolist()),
             "verifying_months": sorted(frame["verifyingMonth"].dropna().astype(int).unique().tolist()),
             "duplicate_messages": int(frame.duplicated(["shortName", "dataDate", "number", "endStep", "forecastMonth"]).sum()),
             "max_error_bound": float(max(message_error(m) for m in rows)), "units": sorted(frame["units"].astype(str).unique().tolist()),
             "data_times": sorted(frame["dataTime"].astype(int).unique().tolist()), "step_types": sorted(frame["stepType"].astype(str).unique().tolist()),
             "time_range_indicators": sorted(frame["timeRangeIndicator"].astype(str).unique().tolist()),
             "mars": sorted({f"{a}/{b}" for a, b in zip(frame["marsType"], frame["marsStream"])}),
             "param_ids": sorted(frame["paramId"].astype(int).unique().tolist()),
             "centres": sorted(frame["centre"].astype(str).unique().tolist()), "methods": sorted(frame["method"].astype(str).unique().tolist()),
             "semantic_problem_count": len(semantic), "semantic_problems": semantic[:20]}
    return found, json.loads(grids.pop())


def identity_problems(key: str, expected: Mapping, found: Mapping) -> List[str]:
    p = [f"{key}: {x}" for x in found.get("semantic_problems", [])]
    if found.get("semantic_problem_count", 0) > len(found.get("semantic_problems", [])):
        p.append(f"{key}: {found['semantic_problem_count']} message semantic problems in total")
    if found["system"] != [expected["system"]]:
        p.append(f"{key}: system {found['system']}")
    if found["data_dates"] != expected["data_dates"]:
        p.append(f"{key}: initialization dates {found['data_dates']} != {expected['data_dates']}")
    if found["short_names"] != sorted(expected["short_names"]):
        p.append(f"{key}: variables {found['short_names']}")
    if found["messages"] != expected["messages"] or found["duplicate_messages"]:
        p.append(f"{key}: {found['messages']} messages ({found['duplicate_messages']} duplicates), expected {expected['messages']}")
    if expected["dataset"] == POSTPROCESSED:
        if found["forecast_months"] != expected["forecast_months"] or found["verifying_months"] != expected["verifying_months"]:
            p.append(f"{key}: leads {found['forecast_months']} / verifying months {found['verifying_months']}")
        if any(m != [0] for m in found["members_by_date"].values()):
            p.append(f"{key}: not the ensemble mean")
    else:
        if found["steps"] != expected["steps"]:
            p.append(f"{key}: steps {found['steps'][:3]}... != expected")
        for y, k in expected["members_by_year"].items():
            if found["members_by_date"].get(y * 10000 + INIT_MONTH * 100 + INIT_DAY) != list(range(k)):
                p.append(f"{key}: {y} members are not 0..{k - 1}")
    return p


def probe_report(ledger: Mapping, points: pd.DataFrame) -> dict:
    """Small grid/cell gate: every planned probe request downloaded with the expected identity, one supported grid per
    file, every fixed point inside, and the same physical cells on the official and original grids."""
    plan = request_plan(probe=True)
    report = {"files": {}, "problems": []}
    if set(ledger.get("requests", {})) != set(plan):
        report["problems"].append(f"probe ledger keys {sorted(ledger.get('requests', {}))} != planned {sorted(plan)}")
    cells = {}
    for key, (dataset, request) in plan.items():
        entry = ledger.get("requests", {}).get(key)
        if not entry or not entry.get("file_sha256") or entry.get("request_sha256") != request_sha256(dataset, request):
            report["problems"].append(f"{key}: not downloaded for the planned request")
            continue
        path = Path(entry["file"])
        if not path.exists() or file_sha256(path) != entry["file_sha256"]:
            report["problems"].append(f"{key}: file missing or bytes differ from the ledger")
            continue
        try:
            found, grid = decoded_identity(path)
        except ValueError as exc:
            report["problems"].append(f"{key}: {exc}")
            continue
        report["problems"] += identity_problems(key, expected_identity(key, dataset, request), found)
        c = containing_cells(grid, points["lat"], points["lon"])
        cells[key] = c
        if not c["inside"].all():
            report["problems"].append(f"{key}: {int((~c['inside']).sum())} points outside the grid")
        report["files"][key] = {"request_id": entry["request_id"], "sha256": entry["file_sha256"], "grid": grid, "identity": found,
                                "points": len(c), "unique_cells": int(c.loc[c["inside"], "flat_index"].nunique())}
    base = cells.get("anomaly_official_leads2to6")
    report["cell_identity_vs_official_anomaly"] = {k: same_cells(base, c) for k, c in cells.items()} if base is not None else None
    if base is None or not all(report["cell_identity_vs_official_anomaly"].values()):
        report["problems"].append("official/original grids do not select the same physical cells for every point")
    report["passed"] = not report["problems"] and len(report["files"]) == len(plan)
    return report


# --------------------------------------------------------------------------- weather processing (CDS environment)


def message_error(meta: Mapping) -> float:
    """Per-value decoding error bound of one message: the larger of the packing half-step and ecCodes ``packingError``
    (the latter also covers the GRIB1 reference-value representation)."""
    half = packing_half_step(meta["binaryScaleFactor"], meta["decimalScaleFactor"])
    pe = meta.get("packingError")
    return float(max(half, float(pe))) if pe is not None else float(half)


def process_weather(root: Path, points: pd.DataFrame, input_root: Path, log=print) -> int:
    """Decode the bulk retrieval, run the September overlap gate and write the May-October point cube."""
    ledger = load_ledger(root / "requests_bulk.json")
    plan = request_plan(probe=False)
    missing = [k for k in plan if not ledger["requests"].get(k, {}).get("file_sha256")]
    if missing:
        raise ValueError(f"bulk retrieval incomplete: {missing}")
    for key, entry in ledger["requests"].items():
        if file_sha256(Path(entry["file"])) != entry["file_sha256"] or entry["request_sha256"] != request_sha256(*plan[key]):
            raise ValueError(f"{key}: file or request identity differs from the ledger")
    out_dir = root / "processed"
    out_dir.mkdir(parents=True, exist_ok=True)
    problems: List[str] = []
    identities, grids = {}, {}
    for key, (dataset, request) in plan.items():
        found, grid = decoded_identity(Path(ledger["requests"][key]["file"]))
        identities[key] = found
        grids[key] = grid
        problems += identity_problems(key, expected_identity(key, dataset, request), found)
    if len({json.dumps(g, sort_keys=True) for k, g in grids.items() if k != "anomaly_official_leads2to6"}) != 1:
        problems.append("original-frequency files use different grids")
    log(f"identity checks: {len(identities)} files, {len(problems)} problems")
    if problems:
        return _reject(input_root, out_dir, ledger, problems, {"identities": identities}, log)

    # ---- grids and cells
    official_path = Path(ledger["requests"]["anomaly_official_leads2to6"]["file"])
    official_grid = first_grid(official_path)
    official_cells = containing_cells(official_grid, points["lat"], points["lon"])
    original_grid = first_grid(Path(ledger["requests"]["original_tmean_2026"]["file"]))
    original_cells = containing_cells(original_grid, points["lat"], points["lon"])
    if not same_cells(official_cells, original_cells):
        raise ValueError("fixed points select different physical cells on the official and original grids")
    cell_ids = np.unique(original_cells["flat_index"].to_numpy())
    point_to_cell = np.searchsorted(cell_ids, original_cells["flat_index"].to_numpy())
    official_cell_ids = np.unique(official_cells["flat_index"].to_numpy())
    point_to_official = np.searchsorted(official_cell_ids, official_cells["flat_index"].to_numpy())
    n_cells = len(cell_ids)

    # ---- official monthly anomalies (true May-September)
    official: Dict[Tuple[str, Tuple[int, int]], np.ndarray] = {}
    official_meta = []
    for meta, grid, values in iter_messages(official_path, official_cell_ids):
        if grid_from_keys(grid) != official_grid:
            problems.append("official messages change grid")
        var = {"2ta": "tmean", "tpara": "prcp"}.get(meta["shortName"])
        month = (int(meta["verifyingMonth"]) // 100, int(meta["verifyingMonth"]) % 100)
        lead = int(meta["forecastMonth"])
        if var is None or int(meta["dataDate"]) != 20260401 or str(meta["system"]) != SYSTEM or OFFICIAL_LEADS.get(lead) != month:
            problems.append(f"unexpected official message {meta['shortName']} lead {lead} month {month}")
            continue
        if (var, month) in official:
            problems.append(f"duplicate official {var} {month}")
        official[(var, month)] = values
        official_meta.append({"variable": var, "lead": lead, "verifying_month": f"{month[0]}-{month[1]:02d}", "units": meta["units"],
                              "short_name": meta["shortName"], "error_bound": message_error(meta), "packing": meta["packingType"],
                              "bits": int(meta["bitsPerValue"])})
    if set(official) != {(v, m) for v in ("tmean", "prcp") for m in OFFICIAL_LEADS.values()}:
        problems.append("official anomalies do not cover tmean/prcp for true May-September")

    # ---- original-frequency forecasts and hindcasts
    years = (FORECAST_YEAR, *HINDCAST_YEARS)
    yidx = {y: i for i, y in enumerate(years)}
    months = (OVERLAP_MONTH, CONSTRUCTED_MONTH)
    conventions = ("start_inclusive", "end_inclusive")
    tsum = np.zeros((len(years), 51, 2, 2, n_cells))
    tcount = np.zeros((len(years), 51, 2, 2), dtype=int)
    p_hours = original_precipitation_hours()
    pacc = np.full((len(years), 51, len(p_hours), n_cells), np.nan)
    members_seen = {y: set() for y in years}
    step_error: Dict[Tuple[str, str, int], float] = {}  # (group, shortName, step) -> max per-value decoding bound
    sample_sets = {(m, c): set(temperature_sample_hours(FORECAST_YEAR, mo, c)) for m, mo in enumerate(months) for c in conventions}
    t_keys = [k for k in plan if k.startswith("original_tmean_")]
    for key in t_keys + ["original_prcp_2026", "original_prcp_hindcast"]:
        path = Path(ledger["requests"][key]["file"])
        n = 0
        for meta, grid, values in iter_messages(path, cell_ids):
            n += 1
            if grid_from_keys(grid) != original_grid:
                problems.append(f"{key}: grid change")
                break
            year = int(meta["dataDate"]) // 10000
            if int(meta["dataDate"]) % 10000 != 401 or str(meta["system"]) != SYSTEM or year not in yidx:
                problems.append(f"{key}: unexpected initialization {meta['dataDate']} / system {meta['system']}")
                continue
            member, step = int(meta["number"]), int(meta["endStep"])
            if member >= EXPECTED_MEMBERS["forecast" if year == FORECAST_YEAR else "hindcast"]:
                problems.append(f"{key}: unexpected member {member} for {year}")
                continue
            group = "forecast" if year == FORECAST_YEAR else "hindcast"
            members_seen[year].add(member)
            if meta["shortName"] == "2t":
                if meta["units"] != "K":
                    problems.append(f"{key}: temperature units {meta['units']}")
                step_error[(group, "2t", step)] = max(step_error.get((group, "2t", step), 0.0), message_error(meta))
                for mi in range(2):
                    for ci, conv in enumerate(conventions):
                        if step in sample_sets[(mi, conv)]:
                            tsum[yidx[year], member, mi, ci] += values
                            tcount[yidx[year], member, mi, ci] += 1
            elif meta["shortName"] == "tp":
                if meta["units"] != "m":
                    problems.append(f"{key}: precipitation units {meta['units']}")
                if step not in p_hours:
                    problems.append(f"{key}: unexpected precipitation step {step}")
                    continue
                step_error[(group, "tp", step)] = max(step_error.get((group, "tp", step), 0.0), message_error(meta))
                pacc[yidx[year], member, p_hours.index(step)] = values
            else:
                problems.append(f"{key}: unexpected shortName {meta['shortName']}")
        log(f"decoded {key}: {n} messages")

    # ---- completeness: members, years, samples, accumulations
    support = {"forecast_members": sorted(members_seen[FORECAST_YEAR]), "hindcast_members": {y: len(members_seen[y]) for y in HINDCAST_YEARS}}
    monotonicity: List[dict] = []
    expected_counts = {(mi, ci): len(sample_sets[(mi, conv)]) for mi in range(2) for ci, conv in enumerate(conventions)}
    for y in years:
        k = EXPECTED_MEMBERS["forecast" if y == FORECAST_YEAR else "hindcast"]
        if members_seen[y] != set(range(k)):
            problems.append(f"{y}: members {sorted(members_seen[y])[:5]}... ({len(members_seen[y])}) != 0..{k - 1}")
        for (mi, ci), want in expected_counts.items():
            got = tcount[yidx[y], :k, mi, ci]
            if (got != want).any():
                problems.append(f"{y}: temperature samples {sorted(set(got.tolist()))} != {want} for month {months[mi]} {conventions[ci]}")
        if np.isnan(pacc[yidx[y], :k]).any():
            problems.append(f"{y}: missing precipitation accumulation values")
            continue
        # source diagnostic only (supervisor decision B; not an acceptance gate): accumulated tp is defined since the
        # forecast start, but ECMWF documents spurious decrements in packed cumulative fields; record every signed raw
        # increment that falls below the summed final-packing endpoint bounds, keyed, without clipping or dropping members
        group = "forecast" if y == FORECAST_YEAR else "hindcast"
        for a, b in ((0, 1), (1, 2)):
            tol = step_error[(group, "tp", p_hours[a])] + step_error[(group, "tp", p_hours[b])]
            inc = pacc[yidx[y], :k, b] - pacc[yidx[y], :k, a]
            support.setdefault("precip_min_increment_m", {})[f"{y} {p_hours[a]}-{p_hours[b]}"] = float(inc.min())
            support.setdefault("precip_negative_increments", {})[f"{y} {p_hours[a]}-{p_hours[b]}"] = int((inc < 0).sum())
            for member, cell in zip(*np.nonzero(inc < -tol)):
                monotonicity.append({"init_year": y, "member": int(member), "interval_h": f"{p_hours[a]}-{p_hours[b]}",
                                     "cell_flat_index": int(cell_ids[cell]), "start_m": float(pacc[yidx[y], member, a, cell]),
                                     "end_m": float(pacc[yidx[y], member, b, cell]), "increment_m": float(inc[member, cell]),
                                     "max_endpoint_bound_m": float(tol)})
    support["temperature_samples_per_member"] = {f"{months[mi][0]}-{months[mi][1]:02d} {conventions[ci]}": want for (mi, ci), want in expected_counts.items()}
    mono = pd.DataFrame(monotonicity, columns=["init_year", "member", "interval_h", "cell_flat_index", "start_m", "end_m", "increment_m", "max_endpoint_bound_m"])
    mono_path = out_dir / "tp_monotonicity_diagnostic.csv"
    mono.to_csv(mono_path, index=False, float_format="%.17g")
    support["tp_monotonicity_diagnostic"] = {
        "path": str(mono_path), "sha256": file_sha256(mono_path), "cases_beyond_final_packing_bounds_at_launch_cells": len(mono),
        "worst_increment_m": float(mono["increment_m"].min()) if len(mono) else None,
        "status": "diagnostic only (not an acceptance gate)",
        "limitation": "ECMWF documents spurious decrements in packed cumulative precipitation; decreases exceeding the summed final "
                      "(delivered) packing bounds are not explained by final packing alone and their upstream cause is unverified. "
                      "Raw signed endpoint differences are used unchanged (no clipping, no member removal)."}
    if problems:
        return _reject(input_root, out_dir, ledger, problems, support, log)

    # ---- constructed member monthly values and anomalies (both months; frozen convention is index 0)
    def anomaly(values_by_year):  # values_by_year: year -> (members, cells)
        return ensemble_monthly_anomaly(values_by_year[FORECAST_YEAR], {y: values_by_year[y] for y in HINDCAST_YEARS})

    constructed = {}
    for mi, month in enumerate(months):
        for ci, conv in enumerate(conventions):
            tm = {y: tsum[yidx[y], :EXPECTED_MEMBERS["forecast" if y == FORECAST_YEAR else "hindcast"], mi, ci]
                  / tcount[yidx[y], :EXPECTED_MEMBERS["forecast" if y == FORECAST_YEAR else "hindcast"], mi, ci][:, None] for y in years}
            constructed[("tmean", month, conv)] = anomaly(tm)
        pt = {y: monthly_total_from_accumulations(pacc[yidx[y], :EXPECTED_MEMBERS["forecast" if y == FORECAST_YEAR else "hindcast"], mi],
                                                  pacc[yidx[y], :EXPECTED_MEMBERS["forecast" if y == FORECAST_YEAR else "hindcast"], mi + 1]) for y in years}
        constructed[("prcp", month)] = anomaly(pt)
        support[f"min_member_total_precip_m_{month[0]}-{month[1]:02d}"] = float(min(np.min(v) for v in pt.values()))
    np.savez_compressed(out_dir / "constructed_monthly_aggregates.npz", cell_ids=cell_ids, tsum=tsum, tcount=tcount, pacc=pacc,
                        years=np.array(years), precip_hours=np.array(p_hours))

    # ---- freeze September bounds from metadata BEFORE comparing
    sep_official_t = next(m["error_bound"] for m in official_meta if m["variable"] == "tmean" and m["verifying_month"] == "2026-09")
    sep_official_p = next(m["error_bound"] for m in official_meta if m["variable"] == "prcp" and m["verifying_month"] == "2026-09")
    sep_samples = temperature_sample_hours(FORECAST_YEAR, OVERLAP_MONTH, TEMPERATURE_CONVENTION)
    sep_start, sep_end = month_bounds_hours(FORECAST_YEAR, OVERLAP_MONTH)
    t_err = {g: max(step_error[(g, "2t", h)] for h in sep_samples) for g in ("forecast", "hindcast")}
    p_tot = {g: step_error[(g, "tp", sep_start)] + step_error[(g, "tp", sep_end)] for g in ("forecast", "hindcast")}
    bounds = overlap_bounds(t_err["forecast"], t_err["hindcast"], sep_official_t, p_tot["forecast"], p_tot["hindcast"], sep_official_p, OVERLAP_MONTH)
    frozen = {"frozen_utc": _now(), "month": "2026-09", "temperature_convention": TEMPERATURE_CONVENTION, "bounds": bounds,
              "inputs": {"t_error_forecast_sep_samples": t_err["forecast"], "t_error_hindcast_sep_samples": t_err["hindcast"],
                         "t_error_official_sep": sep_official_t, "p_total_error_forecast_m": p_tot["forecast"],
                         "p_total_error_hindcast_m": p_tot["hindcast"], "p_error_official_sep_m_per_s": sep_official_p,
                         "temperature_sample_steps": [sep_samples[0], sep_samples[-1], len(sep_samples)], "precipitation_endpoints": [sep_start, sep_end]},
              "rule": "per-value bound = max(packing half-step, ecCodes packingError) of the downloaded messages actually used for September: "
                      "temperature = max over the 120 September samples (forecast) + same (hindcast) + official September field; "
                      "precipitation = (start + end endpoint bounds, forecast) + (same, hindcast) per monthly total / seconds(September) "
                      "+ official September rate bound; plus float slack. October messages do not enter.", "float_slack": FLOAT_SLACK}
    bounds_path = out_dir / "overlap_bounds_frozen.json"
    bounds_path.write_text(json.dumps(frozen, indent=2))
    frozen_sha = file_sha256(bounds_path)
    log(f"overlap bounds frozen ({frozen_sha[:12]}): {bounds}")

    # ---- September overlap gate (official cells vs constructed cells, at every point)
    sec = seconds_in_month(*OVERLAP_MONTH)
    t_con = constructed[("tmean", OVERLAP_MONTH, TEMPERATURE_CONVENTION)]["anomaly"][point_to_cell]
    t_off = official[("tmean", OVERLAP_MONTH)][point_to_official]
    p_con = constructed[("prcp", OVERLAP_MONTH)]["anomaly"][point_to_cell] / sec
    p_off = official[("prcp", OVERLAP_MONTH)][point_to_official]
    dt_ = np.abs(t_con - t_off)
    dp_ = np.abs(p_con - p_off)
    other = "start_inclusive" if TEMPERATURE_CONVENTION == "end_inclusive" else "end_inclusive"
    alt = np.abs(constructed[("tmean", OVERLAP_MONTH, other)]["anomaly"][point_to_cell] - t_off)
    gate = {"bounds_sha256": frozen_sha, "points": len(points), "cells": n_cells,
            "tmean": {"max_abs_diff_K": float(dt_.max()), "bound_K": bounds["tmean_K"], "points_over_bound": int((dt_ > bounds["tmean_K"]).sum()),
                      "finite": bool(np.isfinite(t_con).all() and np.isfinite(t_off).all())},
            "prcp": {"max_abs_diff_m_per_s": float(dp_.max()), "bound_m_per_s": bounds["prcp_m_per_s"], "points_over_bound": int((dp_ > bounds["prcp_m_per_s"]).sum()),
                     "max_abs_diff_mm_per_month": float(dp_.max() * 1000 * sec), "finite": bool(np.isfinite(p_con).all() and np.isfinite(p_off).all())},
            f"diagnostic_{other}_tmean_max_abs_diff_K": float(alt.max())}
    pd.DataFrame({"area_id": points["area_id"], "cell_lat": original_cells["cell_lat"], "cell_lon": original_cells["cell_lon"],
                  "tmean_constructed_K": t_con, "tmean_official_K": t_off, "tmean_abs_diff_K": dt_,
                  "prcp_constructed_m_per_s": p_con, "prcp_official_m_per_s": p_off, "prcp_abs_diff_m_per_s": dp_}).to_csv(
        out_dir / "september_overlap_by_point.csv", index=False, float_format="%.17g")
    passed = (gate["tmean"]["points_over_bound"] == 0 and gate["prcp"]["points_over_bound"] == 0 and gate["tmean"]["finite"] and gate["prcp"]["finite"])
    (out_dir / "september_overlap_gate.json").write_text(json.dumps(gate | {"passed": passed}, indent=2))
    log(f"September overlap gate passed={passed}: {json.dumps(gate)}")
    if not passed:
        return _reject(input_root, out_dir, ledger, ["September overlap outside frozen bounds"], support | {"overlap": gate}, log)

    # ---- cube: true May-September official, October constructed
    long_rows = []
    wide = pd.DataFrame({"area_id": points["area_id"].to_numpy()})
    for k, (y, m) in enumerate(TRUE_MONTHS, start=1):
        for var in ("prcp", "tmean"):
            if (y, m) == CONSTRUCTED_MONTH:
                raw = constructed[("tmean", (y, m), TEMPERATURE_CONVENTION)]["anomaly"] if var == "tmean" else constructed[("prcp", (y, m))]["anomaly"]
                values = raw[point_to_cell] * (1000.0 if var == "prcp" else 1.0)
                source = f"constructed from {ORIGINAL} (2026 members minus 1993-2016 hindcast equal-year mean)"
            else:
                raw = official[(var, (y, m))][point_to_official]
                values = rate_to_mm_per_month(raw, y, m) if var == "prcp" else raw
                lead = next(lead for lead, mo in OFFICIAL_LEADS.items() if mo == (y, m))
                source = f"official {POSTPROCESSED} ensemble_mean leadtime_month {lead}"
            wide[oracle_column(var, k)] = values
            long_rows.append(pd.DataFrame({"area_id": points["area_id"], "offset_k": k, "statistical_month": f"{y}-{m:02d}", "variable": var,
                                           "oracle_column": oracle_column(var, k), "value": values,
                                           "unit": "mm/month anomaly" if var == "prcp" else "degC (K difference) anomaly", "source": source,
                                           "cell_lat": original_cells["cell_lat"], "cell_lon": original_cells["cell_lon"],
                                           "point_lat": points["lat"], "point_lon": points["lon"]}))
    wide = wide[["area_id", *oracle_columns()]]
    if not np.isfinite(wide[oracle_columns()].to_numpy()).all():
        return _reject(input_root, out_dir, ledger, ["nonfinite cube values"], support, log)
    input_root.mkdir(parents=True, exist_ok=True)
    cube_path = input_root / "cds_weather_cube.csv"
    wide.to_csv(cube_path, index=False, float_format="%.17g")
    long_path = out_dir / "cds_weather_cube_long.csv"
    pd.concat(long_rows, ignore_index=True).to_csv(long_path, index=False, float_format="%.17g")
    provenance = {
        "version": VERSION, "status": "ACCEPTED", "created_utc": _now(),
        "definition": "ECMWF system51 April 1 2026 initialization ensemble-mean anomalies vs the 1993-2016 system51 hindcast reference; "
                      "true May-September official monthly anomalies (leads 2-6), true October constructed from original-frequency data "
                      "and validated on September; fixed containing-cell point sampling; mm/month and degC difference",
        "cube": {"path": str(cube_path), "sha256": file_sha256(cube_path), "points": len(wide), "columns": oracle_columns()},
        "long_cube": {"path": str(long_path), "sha256": file_sha256(long_path)},
        "requests": {k: {kk: e.get(kk) for kk in ("dataset", "request", "request_sha256", "request_id", "status", "submitted_utc", "downloaded_utc",
                                                    "file", "file_sha256", "file_bytes", "asset", "created_at", "started_at", "finished_at")}
                     for k, e in ledger["requests"].items()},
        "official_messages": official_meta, "support": support, "overlap_gate": gate | {"passed": True}, "file_identities": identities,
        "overlap_bounds": {"path": str(bounds_path), "sha256": frozen_sha},
        "grids": {"official": official_grid, "original": original_grid, "points": len(points), "unique_cells": n_cells},
        "aggregates": {"path": str(out_dir / "constructed_monthly_aggregates.npz"), "sha256": file_sha256(out_dir / "constructed_monthly_aggregates.npz")},
        "temperature_convention": TEMPERATURE_CONVENTION, "reference_period": REFERENCE_PERIOD,
        "temperature_convention_basis": "(month start 00, next month start 00] UTC 6-hourly instantaneous samples; empirically verified "
                                        "against the supplied system51 September absolute monthly ensemble mean and September anomaly "
                                        "products; official primary documents do not explicitly state endpoint inclusivity; the initial "
                                        "[start, end) window failed both checks and production attempt v2 was rejected",
        "convention_evidence": {rel: ({"path": str(root / rel), "sha256": file_sha256(root / rel)} if (root / rel).exists() else "MISSING")
                                for rel in CONVENTION_EVIDENCE},
        "precipitation_accumulation": "provider-defined accumulation since forecast start; GRIB1 messages carry only the forecast time "
                                      "(TRI 10, instant, start = end step); raw signed end-minus-start totals; endpoint decreases kept as a "
                                      "keyed diagnostic (support.tp_monotonicity_diagnostic); acceptance by the September overlap",
        "limitations": ["Model anomalies (1993-2016 system51 reference) differ from the observed 1991-2020 training anomalies.",
                        "Temperature monthly window empirically verified on supplied September products, not an explicit published rule.",
                        "Accumulated tp has endpoint decreases beyond final-packing bounds (keyed diagnostic); upstream cause unverified; "
                        "raw signed end-minus-start totals used unchanged.",
                        "Fixed containing-cell point sampling does not reproduce the observed export's spatial weights.",
                        "October is locally constructed (validated on September), not an official monthly product."],
    }
    (cube_path.with_name("cds_weather_provenance.json")).write_text(json.dumps(provenance, indent=2, default=str))
    (out_dir / "cds_weather_provenance.json").write_text(json.dumps(provenance, indent=2, default=str))
    log(f"weather cube ACCEPTED: {cube_path}")
    return 0


def _reject(input_root: Path, out_dir: Path, ledger: dict, problems: List[str], support: dict, log) -> int:
    payload = {"version": VERSION, "status": "REJECTED", "created_utc": _now(), "problems": problems, "support": support,
               "requests": {k: e.get("request_id") for k, e in ledger["requests"].items()}}
    (out_dir / "cds_weather_provenance.json").write_text(json.dumps(payload, indent=2, default=str))
    log(f"weather stage REJECTED: {problems[:10]}")
    return 1
