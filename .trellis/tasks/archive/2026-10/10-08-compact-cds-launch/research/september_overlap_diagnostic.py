"""DIAGNOSTIC September overlap for compact_cds_launch_v1 (CDS interpreter; never writes an ACCEPTED cube).

Independent re-aggregation of the 28 downloaded files with the production decode helpers and the production, unchanged
frozen-bound rule (per-message max(half-step, packingError); September samples/endpoints only; ``overlap_bounds``).
Order: decode -> completeness -> freeze bounds to a hashed file -> only then compare constructed vs official September.
Accumulated-tp monotonicity is recorded as evidence only. Outputs go to CDS_API/compact_cds_launch_v1/diagnostic/.

Run from the repository root:
  PYTHONPATH=src "<Analysis>/1.Source Data/CDS_API/.venv/bin/python" .trellis/tasks/10-08-compact-cds-launch/research/september_overlap_diagnostic.py
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "src")
from ipcch import cds_launch_weather as cw  # noqa: E402

W = Path("../../../1.Source Data/CDS_API/compact_cds_launch_v1")
OUT = W / "diagnostic"
OUT.mkdir(parents=True, exist_ok=True)
t0 = time.time()
ledger = cw.load_ledger(W / "requests_bulk.json")
plan = cw.request_plan(probe=False)
for key, entry in ledger["requests"].items():
    assert cw.file_sha256(Path(entry["file"])) == entry["file_sha256"] and entry["request_sha256"] == cw.request_sha256(*plan[key])
pts = pd.read_csv(W.parent.parent / "assembled_IPCCH/spatial/unique_area_id_lat_lon.csv", float_precision="round_trip").sort_values("area_id").reset_index(drop=True)
official_path = Path(ledger["requests"]["anomaly_official_leads2to6"]["file"])
og = cw.first_grid(official_path)
rg = cw.first_grid(Path(ledger["requests"]["original_tmean_2026"]["file"]))
oc, rc = cw.containing_cells(og, pts.lat, pts.lon), cw.containing_cells(rg, pts.lat, pts.lon)
assert cw.same_cells(oc, rc)
o_idx, r_idx = oc["flat_index"].to_numpy(), rc["flat_index"].to_numpy()

official, official_err = {}, {}
for meta, grid, v in cw.iter_messages(official_path, o_idx):
    vm = int(meta["verifyingMonth"])
    var = {"2ta": "tmean", "tpara": "prcp"}[meta["shortName"]]
    official[(var, vm)] = v
    official_err[(var, vm)] = cw.message_error(meta)

years = (cw.FORECAST_YEAR, *cw.HINDCAST_YEARS)
sep = cw.OVERLAP_MONTH
sep_steps = set(cw.temperature_sample_hours(cw.FORECAST_YEAR, sep, cw.TEMPERATURE_CONVENTION))
sep_alt = set(cw.temperature_sample_hours(cw.FORECAST_YEAR, sep, "end_inclusive"))
s0, s1 = cw.month_bounds_hours(cw.FORECAST_YEAR, sep)
tsum = {y: np.zeros((51, len(pts))) for y in years}
tsum_alt = {y: np.zeros((51, len(pts))) for y in years}
tcnt = {y: np.zeros(51, dtype=int) for y in years}
pacc = {y: np.full((51, 2, len(pts)), np.nan) for y in years}
step_err = {}
for key in [k for k in plan if k.startswith("original_")]:
    for meta, grid, v in cw.iter_messages(Path(ledger["requests"][key]["file"]), r_idx):
        y, m, s = int(meta["dataDate"]) // 10000, int(meta["number"]), int(meta["endStep"])
        g = "forecast" if y == cw.FORECAST_YEAR else "hindcast"
        short = meta["shortName"]
        step_err[(g, short, s)] = max(step_err.get((g, short, s), 0.0), cw.message_error(meta))
        if short == "2t":
            if s in sep_steps:
                tsum[y][m] += v
                tcnt[y][m] += 1
            if s in sep_alt:
                tsum_alt[y][m] += v
        elif s in (s0, s1):
            pacc[y][m, (s0, s1).index(s)] = v
members = {y: cw.EXPECTED_MEMBERS["forecast" if y == cw.FORECAST_YEAR else "hindcast"] for y in years}
completeness = {"temperature_samples_ok": all((tcnt[y][: members[y]] == len(sep_steps)).all() for y in years),
                "precip_endpoints_ok": all(np.isfinite(pacc[y][: members[y]]).all() for y in years)}
assert all(completeness.values()), completeness

# ---- freeze bounds from metadata BEFORE any comparison (production rule, unchanged)
t_err = {g: max(step_err[(g, "2t", h)] for h in sep_steps) for g in ("forecast", "hindcast")}
p_tot = {g: step_err[(g, "tp", s0)] + step_err[(g, "tp", s1)] for g in ("forecast", "hindcast")}
bounds = cw.overlap_bounds(t_err["forecast"], t_err["hindcast"], official_err[("tmean", 202609)], p_tot["forecast"], p_tot["hindcast"],
                           official_err[("prcp", 202609)], sep)
frozen = {"mode": "DIAGNOSTIC (no acceptance)", "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "bounds": bounds,
          "inputs": {"t_err": t_err, "p_total_err": p_tot, "official_t": official_err[("tmean", 202609)], "official_p": official_err[("prcp", 202609)]},
          "rule": "production rule unchanged: cds_launch_weather.overlap_bounds with September-only samples/endpoints",
          "code_sha256": cw.file_sha256(Path("src/ipcch/cds_launch_weather.py"))}
bpath = OUT / "overlap_bounds_frozen_diagnostic.json"
bpath.write_text(json.dumps(frozen, indent=2))
bsha = cw.file_sha256(bpath)
print("bounds frozen", bsha[:12], bounds, flush=True)

# ---- comparison (after freezing)
def anomaly(store):
    f = store[cw.FORECAST_YEAR][: members[cw.FORECAST_YEAR]].mean(axis=0)
    clim = np.mean([store[y][: members[y]].mean(axis=0) for y in cw.HINDCAST_YEARS], axis=0)
    return f - clim

t_month = {y: tsum[y] / len(sep_steps) for y in years}
t_month_alt = {y: tsum_alt[y] / len(sep_alt) for y in years}
p_total = {y: pacc[y][:, 1] - pacc[y][:, 0] for y in years}
t_con, t_alt = anomaly(t_month), anomaly(t_month_alt)
p_con_rate = anomaly(p_total) / cw.seconds_in_month(*sep)
t_off, p_off = official[("tmean", 202609)], official[("prcp", 202609)]
dt_, dp_ = np.abs(t_con - t_off), np.abs(p_con_rate - p_off)
neg_tot = {y: int((p_total[y][: members[y]] < 0).sum()) for y in years}
result = {
    "mode": "DIAGNOSTIC (no acceptance; no cube)", "bounds_sha256": bsha, "points": len(pts), "completeness": completeness,
    "tmean": {"bound_K": bounds["tmean_K"], "max_abs_diff_K": float(dt_.max()), "p99_abs_diff_K": float(np.quantile(dt_, 0.99)),
              "points_over_bound": int((dt_ > bounds["tmean_K"]).sum()), "max_ratio_to_bound": float(dt_.max() / bounds["tmean_K"]),
              "diagnostic_end_inclusive_max_abs_diff_K": float(np.abs(t_alt - t_off).max())},
    "prcp": {"bound_m_per_s": bounds["prcp_m_per_s"], "max_abs_diff_m_per_s": float(dp_.max()), "points_over_bound": int((dp_ > bounds["prcp_m_per_s"]).sum()),
             "max_ratio_to_bound": float(dp_.max() / bounds["prcp_m_per_s"]), "max_abs_diff_mm_per_month": float(dp_.max() * 1000 * cw.seconds_in_month(*sep)),
             "bound_mm_per_month": float(bounds["prcp_m_per_s"] * 1000 * cw.seconds_in_month(*sep))},
    "september_member_totals_negative_count_at_points": neg_tot,
    "elapsed_s": round(time.time() - t0, 1)}
pd.DataFrame({"area_id": pts.area_id, "cell_lat": rc.cell_lat, "cell_lon": rc.cell_lon, "tmean_constructed_K": t_con, "tmean_official_K": t_off,
              "tmean_abs_diff_K": dt_, "prcp_constructed_m_per_s": p_con_rate, "prcp_official_m_per_s": p_off, "prcp_abs_diff_m_per_s": dp_}).to_csv(
    OUT / "september_overlap_by_point_diagnostic.csv", index=False, float_format="%.17g")
(OUT / "september_overlap_diagnostic.json").write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=1))
