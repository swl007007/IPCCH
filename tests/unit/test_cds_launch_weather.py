import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ipcch import cds_launch_weather as cw
from ipcch import weather_oracle as wo


def _keys(lat1=89.5, lon1=0.5, nj=180, ni=360, d=1.0, **over):
    keys = {"gridType": "regular_ll", "Ni": ni, "Nj": nj, "iDirectionIncrementInDegrees": d, "jDirectionIncrementInDegrees": d,
            "latitudeOfFirstGridPointInDegrees": lat1, "longitudeOfFirstGridPointInDegrees": lon1,
            "latitudeOfLastGridPointInDegrees": lat1 - (nj - 1) * d, "longitudeOfLastGridPointInDegrees": (lon1 + (ni - 1) * d),
            "jScansPositively": 0, "iScansNegatively": 0, "jPointsAreConsecutive": 0}
    keys.update(over)
    return keys


# --------------------------------------------------------------------------- calendar, literals, units


def test_oracle_literals_and_true_months():
    assert cw.oracle_columns() == wo.raw_features(12)
    assert cw.TRUE_MONTHS == tuple((2026, m) for m in range(5, 11))
    assert cw.OFFICIAL_LEADS == {2: (2026, 5), 3: (2026, 6), 4: (2026, 7), 5: (2026, 8), 6: (2026, 9)}  # lead 1 = April


def test_forecast_hours_and_temperature_windows():
    assert cw.month_bounds_hours(2026, (2026, 10)) == (4392, 5136)
    assert cw.month_bounds_hours(1993, (2026, 10)) == (4392, 5136)  # same for every hindcast year
    assert cw.original_precipitation_hours() == [3672, 4392, 5136]
    sep = cw.temperature_sample_hours(2026, (2026, 9))
    oct_ = cw.temperature_sample_hours(2026, (2026, 10))
    assert cw.TEMPERATURE_CONVENTION == "end_inclusive"  # verified (start, end] window
    assert len(sep) == 120 and sep[0] == 3678 and sep[-1] == 4392  # (Sep 1 00, Oct 1 00] UTC
    assert len(oct_) == 124 and oct_[0] == 4398 and oct_[-1] == 5136  # (Oct 1 00, Nov 1 00] UTC
    initial = cw.temperature_sample_hours(2026, (2026, 10), "start_inclusive")
    assert initial[0] == 4392 and initial[-1] == 5130 and len(initial) == 124
    hours = cw.original_temperature_hours()
    assert hours[0] == 3672 and hours[-1] == 5136 and len(hours) == 245


def test_unit_conversions():
    assert cw.rate_to_mm_per_month(1e-8, 2026, 10) == pytest.approx(1e-8 * 1000 * 86400 * 31)
    assert cw.rate_to_mm_per_month(1e-8, 2026, 9) == pytest.approx(1e-8 * 1000 * 86400 * 30)
    assert cw.seconds_in_month(2026, 9) == 30 * 86400


# --------------------------------------------------------------------------- grids and containing cells


def test_grid_accepts_only_half_degree_centred_one_degree():
    g = cw.grid_from_keys(_keys())
    assert g["north_edge"] == 90.0 and g["west_edge"] == 0.0
    crop = cw.grid_from_keys(_keys(lat1=39.5, lon1=-92.5, nj=76, ni=221))
    assert crop["west_edge"] == -93.0
    with pytest.raises(ValueError, match="half-degree"):
        cw.grid_from_keys(_keys(lat1=90.0, lon1=0.0, nj=91, ni=180, d=2.0))  # integer-centred 2-degree
    with pytest.raises(ValueError, match="half-degree"):
        cw.grid_from_keys(_keys(lat1=90.0, lon1=0.0, nj=181, ni=360))  # integer-centred 1-degree (old system5 style)
    with pytest.raises(ValueError, match="scanning"):
        cw.grid_from_keys(_keys(jScansPositively=1))


def test_containing_cell_matches_rasterio_floor_semantics_and_crop_identity():
    lat = np.array([4.726143, -34.04142, 38.1087, 12.0, -0.0])
    lon = np.array([-7.772501, 126.967, -91.9315, 30.0, -180.0 + 1e-9])
    g = cw.grid_from_keys(_keys())
    c = cw.containing_cells(g, lat, lon)
    # GeoTIFF of the same grid shifted to -180..180: col = floor(lon + 180), row = floor(90 - lat)
    tif_lon_centre = np.floor(lon + 180.0) - 180.0 + 0.5
    tif_lat_centre = 90.0 - np.floor(90.0 - lat) - 0.5
    assert np.allclose(c["cell_lon"], tif_lon_centre) and np.allclose(c["cell_lat"], tif_lat_centre)
    assert c.loc[3, "cell_lon"] == 30.5 and c.loc[3, "cell_lat"] == 11.5  # points on edges fall east / south
    crop = cw.grid_from_keys(_keys(lat1=39.5, lon1=-92.5, nj=76, ni=221))
    cc = cw.containing_cells(crop, lat[:4], lon[:4])
    assert cw.same_cells(c.iloc[:4].reset_index(drop=True), cc)
    outside = cw.containing_cells(crop, np.array([50.0]), np.array([0.0]))
    assert not outside["inside"].iloc[0]


# --------------------------------------------------------------------------- arithmetic and bounds


def test_ensemble_anomaly_is_forecast_mean_minus_equal_year_hindcast_mean():
    f = np.array([[1.0, 2.0], [3.0, 4.0]])
    h = {1993: np.array([[0.0, 1.0], [2.0, 1.0]]), 1994: np.array([[4.0, 3.0]])}
    out = cw.ensemble_monthly_anomaly(f, h)
    assert np.allclose(out["anomaly"], [2.0 - (1.0 + 4.0) / 2, 3.0 - (1.0 + 3.0) / 2])


def test_overlap_bounds_and_message_error():
    # precipitation inputs are already per-total bounds (start + end endpoint of the month's own accumulations)
    b = cw.overlap_bounds(6e-4, 6e-4, 6e-5, 1.2e-4, 6e-5, 4e-12, (2026, 9))
    assert b["tmean_K"] == pytest.approx(1.26e-3 + 1e-9)
    assert b["prcp_m_per_s"] == pytest.approx((1.2e-4 + 6e-5) / (30 * 86400) + 4e-12 + 1e-15)
    assert cw.packing_half_step(-10, 0) == 2 ** -10 / 2
    assert cw.message_error({"binaryScaleFactor": -10, "decimalScaleFactor": 0, "packingError": 6.1e-4}) == 6.1e-4
    assert cw.message_error({"binaryScaleFactor": -14, "decimalScaleFactor": 0, "packingError": None}) == 2 ** -14 / 2


# --------------------------------------------------------------------------- identities


def _found(**over):
    base = {"messages": 51, "system": ["51"], "data_dates": [20260401], "short_names": ["2t"], "members_by_date": {20260401: list(range(51))},
            "steps": [3672], "forecast_months": [], "verifying_months": [], "duplicate_messages": 0}
    base.update(over)
    return base


def test_identity_problems_reject_wrong_system_init_members_steps():
    ds, req = cw.request_plan(probe=True)["probe_original_tmean_2026_sep1"]
    exp = cw.expected_identity("k", ds, req)
    assert cw.identity_problems("k", exp, _found()) == []
    assert cw.identity_problems("k", exp, _found(system=["5"]))
    assert cw.identity_problems("k", exp, _found(data_dates=[20260501]))
    assert cw.identity_problems("k", exp, _found(members_by_date={20260401: list(range(50))}, messages=50))
    assert cw.identity_problems("k", exp, _found(steps=[3678]))
    ds, req = cw.request_plan(probe=True)["anomaly_official_leads2to6"]
    exp = cw.expected_identity("a", ds, req)
    good = _found(messages=10, short_names=["2ta", "tpara"], members_by_date={20260401: [0]}, steps=[], forecast_months=[2, 3, 4, 5, 6],
                  verifying_months=[202605, 202606, 202607, 202608, 202609])
    assert cw.identity_problems("a", exp, good) == []
    assert cw.identity_problems("a", exp, dict(good, verifying_months=[202606, 202607, 202608, 202609, 202610]))  # shifted labels


def test_hindcast_identity_expects_25_members_per_year():
    ds, req = cw.request_plan(probe=False)["original_prcp_hindcast"]
    exp = cw.expected_identity("h", ds, req)
    assert exp["messages"] == 24 * 25 * 3 and exp["members_by_year"][1993] == 25 and len(exp["data_dates"]) == 24


def test_probe_report_fails_on_empty_or_partial_ledger():
    pts = pd.DataFrame({"area_id": [1], "lat": [1.0], "lon": [1.0]})
    empty = cw.probe_report({"requests": {}}, pts)
    assert not empty["passed"] and empty["problems"]
    partial = cw.probe_report({"requests": {"anomaly_official_leads2to6": {"file_sha256": None}}}, pts)
    assert not partial["passed"]


# --------------------------------------------------------------------------- ledger: resume by ID, durable status, cache recovery


class FakeRemote:
    def __init__(self, rid, status):
        self.request_id, self.status = rid, status


class FakeResults:
    def __init__(self, payload: bytes, fail: bool = False):
        self.payload, self.fail = payload, fail
        self.asset = {"file:size": len(payload), "type": "application/x-grib", "href": "https://x/cache/abc.grib?token=secret"}
        self.content_length = len(payload)

    def download(self, target):
        if self.fail:
            raise TimeoutError("download timed out")
        Path(target).write_bytes(self.payload)
        return target


class FakeClient:
    def __init__(self, status="accepted", payload=b"GRIB", fail=False):
        self.submitted, self.status, self.payload, self.fail = [], status, payload, fail

    def submit(self, dataset, request):
        self.submitted.append((dataset, request))
        return FakeRemote(f"id-{len(self.submitted)}", "accepted")

    def get_remote(self, rid):
        return FakeRemote(rid, self.status)

    def get_results(self, rid):
        return FakeResults(self.payload, self.fail)


def test_submit_never_resubmits_a_recorded_request(tmp_path):
    plan = {"a": ("ds", {"x": 1}), "b": ("ds", {"x": 2})}
    ledger_path = tmp_path / "ledger.json"
    client = FakeClient()
    cw.submit_missing(client, plan, ledger_path, log=lambda *_: None)
    cw.submit_missing(client, plan, ledger_path, log=lambda *_: None)
    assert len(client.submitted) == 2
    with pytest.raises(ValueError, match="differs from the plan"):
        cw.submit_missing(client, {"a": ("ds", {"x": 9})}, ledger_path, log=lambda *_: None)
    ledger = json.loads(ledger_path.read_text())
    ledger["requests"]["b"]["status"] = "failed"
    ledger_path.write_text(json.dumps(ledger))
    cw.submit_missing(client, plan, ledger_path, log=lambda *_: None)
    assert len(client.submitted) == 3 and json.loads(ledger_path.read_text())["requests"]["b"]["previous_attempts"]


def test_success_status_is_durable_before_a_download_timeout(tmp_path):
    ledger_path = tmp_path / "ledger.json"
    cw.submit_missing(FakeClient(), {"a": ("ds", {"x": 1})}, ledger_path, log=lambda *_: None)
    with pytest.raises(TimeoutError):
        cw.poll_and_download(FakeClient(status="successful", fail=True), ledger_path, tmp_path / "raw", log=lambda *_: None)
    entry = json.loads(ledger_path.read_text())["requests"]["a"]
    assert entry["status"] == "successful" and "file_sha256" not in entry and entry["request_id"] == "id-1"


def test_missing_or_replaced_cache_file_is_downloaded_again_by_the_same_request_id(tmp_path):
    ledger_path = tmp_path / "ledger.json"
    client = FakeClient(status="successful", payload=b"GRIB-1")
    cw.submit_missing(client, {"a": ("ds", {"x": 1})}, ledger_path, log=lambda *_: None)
    cw.poll_and_download(client, ledger_path, tmp_path / "raw", log=lambda *_: None)
    entry = json.loads(ledger_path.read_text())["requests"]["a"]
    assert entry["asset"]["href_path"] == "/cache/abc.grib"  # no query token stored
    Path(entry["file"]).write_bytes(b"tampered")
    cw.poll_and_download(client, ledger_path, tmp_path / "raw", log=lambda *_: None)
    entry = json.loads(ledger_path.read_text())["requests"]["a"]
    assert Path(entry["file"]).read_bytes() == b"GRIB-1" and entry["redownloads"][0]["reason"] == "bytes changed"
    Path(entry["file"]).unlink()
    cw.poll_and_download(client, ledger_path, tmp_path / "raw", log=lambda *_: None)
    entry = json.loads(ledger_path.read_text())["requests"]["a"]
    assert Path(entry["file"]).exists() and entry["redownloads"][1]["reason"] == "missing"
    assert len(client.submitted) == 1 and entry["request_id"] == "id-1"


def _meta(short="2t", step=3672, date=20260401, time_=0, **over):
    from datetime import datetime, timedelta

    valid = datetime(date // 10000, 4, 1) + timedelta(hours=step)
    m = {"shortName": short, "centre": "ecmf", "system": 51, "method": 1, "dataDate": date, "dataTime": time_, "stepUnits": 1,
         "stepType": "instant", "timeRangeIndicator": 10,
         "startStep": step, "endStep": step, "validityDate": int(valid.strftime("%Y%m%d")), "validityTime": int(valid.strftime("%H%M")),
         **cw.MESSAGE_SEMANTICS[short]}
    m.update(over)
    return m


def test_original_message_semantics():
    assert cw.message_semantics_problems(_meta("2t", 3678), cw.ORIGINAL) == []
    # tp: provider-defined accumulation since start, encoded in GRIB1 as a single forecast time; accepted as such
    assert cw.message_semantics_problems(_meta("tp", 4392), cw.ORIGINAL) == []
    assert cw.message_semantics_problems(_meta("2t", time_=1200), cw.ORIGINAL)  # not 00 UTC
    assert cw.message_semantics_problems(_meta("2t", date=20260501), cw.ORIGINAL)  # not April 1
    assert cw.message_semantics_problems(_meta("2t", validityDate=20260902), cw.ORIGINAL)  # validity != init + step
    assert cw.message_semantics_problems(_meta("2t", stepType="avg"), cw.ORIGINAL)  # temperature must be instantaneous
    assert cw.message_semantics_problems(_meta("2t", startStep=3666), cw.ORIGINAL)
    assert cw.message_semantics_problems(_meta("tp", units="mm"), cw.ORIGINAL)
    assert cw.message_semantics_problems(_meta("2t"), cw.POSTPROCESSED)  # wrong product
    assert cw.message_semantics_problems(_meta("2t", centre="kwbc"), cw.ORIGINAL)  # not ECMWF
    assert cw.message_semantics_problems(_meta("tp", method=2), cw.ORIGINAL)  # not method 1
    assert cw.message_semantics_problems(_meta("2t", system=5), cw.ORIGINAL)  # not system51


def test_official_message_semantics():
    good = _meta("2ta", 1464, forecastMonth=2, verifyingMonth=202605)
    assert cw.message_semantics_problems(good, cw.POSTPROCESSED) == []
    assert cw.message_semantics_problems(_meta("tpara", 1464, forecastMonth=2, verifyingMonth=202605), cw.POSTPROCESSED) == []
    assert cw.message_semantics_problems(dict(good, verifyingMonth=202606), cw.POSTPROCESSED)  # shifted month label
    assert cw.message_semantics_problems(dict(good, units="degC"), cw.POSTPROCESSED)
    assert cw.message_semantics_problems(_meta("tpara", 1464, forecastMonth=2, verifyingMonth=202605, units="m"), cw.POSTPROCESSED)
