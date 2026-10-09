"""Independent decoder (cfgrib/xarray) check of the tp decreases and lattice analysis (read-only)."""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd, xarray as xr, eccodes
sys.path.insert(0, "src")
from ipcch import cds_launch_weather as cw
W = Path("../../../1.Source Data/CDS_API/compact_cds_launch_v1")
out = {}
for key in ("original_prcp_2026", "original_prcp_hindcast"):
    f = W / f"raw/bulk/{key}.grib"
    ds = xr.open_dataset(f, engine="cfgrib", backend_kwargs={"indexpath": ""})
    tp = ds["tp"]
    dims = tp.dims
    steps_h = (tp["step"].values / np.timedelta64(1, "h")).astype(int).tolist()
    valid = [str(v)[:16] for v in np.atleast_1d(ds["valid_time"].values).ravel()[:3]]
    if "time" not in dims:
        tp = tp.expand_dims("time")
    tp = tp.transpose("time", "number", "step", "latitude", "longitude")
    arr = tp.values  # (time, number, step, lat, lon)
    # arr: (time, number, step, lat, lon)
    inc1 = arr[:, :, 1] - arr[:, :, 0]
    inc2 = arr[:, :, 2] - arr[:, :, 1]
    worst1 = float(inc1.min())
    worst2 = float(inc2.min())
    n_neg = int((inc1 < -1.22e-4).sum() + (inc2 < -1.22e-4).sum())
    out[key] = {"cfgrib_dims": list(dims), "shape": list(tp.shape), "steps_h": steps_h, "valid_time_sample": valid,
                "worst_inc_3672_4392_m": worst1, "worst_inc_4392_5136_m": worst2, "cells_with_decrease_below_minus_1.22e-4": n_neg,
                "times": [str(t)[:10] for t in np.atleast_1d(ds["time"].values)][:3]}
    # locate the worst decrease and compare with the eccodes reader at the same member/step/cell
    idx = np.unravel_index(np.argmin(np.minimum(inc1, inc2)), inc1.shape)
    t_i, m_i, la, lo = idx
    member = int(tp["number"].values[m_i])
    year = int(str(np.atleast_1d(tp["time"].values)[t_i])[:4])
    lat, lon = float(tp["latitude"].values[la]), float(tp["longitude"].values[lo])
    vals = {}
    with open(f, "rb") as fh:
        while True:
            h = eccodes.codes_grib_new_from_file(fh)
            if h is None:
                break
            if eccodes.codes_get(h, "number") == member and eccodes.codes_get(h, "dataDate") // 10000 == year:
                E = eccodes.codes_get(h, "binaryScaleFactor")
                ref = eccodes.codes_get(h, "referenceValue")
                v = eccodes.codes_get_values(h).reshape(eccodes.codes_get(h, "Nj"), eccodes.codes_get(h, "Ni"))[la, lo]
                k = (v - ref) / 2.0 ** E
                vals[eccodes.codes_get(h, "endStep")] = {"value": float(v), "E": int(E), "ref": float(ref), "lattice_k": float(k),
                                                         "on_lattice": bool(abs(k - round(k)) < 1e-6), "half_step": 2.0 ** E / 2}
            eccodes.codes_release(h)
    xv = arr[t_i, m_i, :, la, lo].tolist()
    ev = [vals[s]["value"] for s in (3672, 4392, 5136)]
    out[key]["worst_case"] = {"year": year, "member": member, "cell_lat": lat, "cell_lon": lon, "cfgrib_values": xv, "eccodes_values": ev,
                              "readers_agree": bool(np.allclose(xv, ev, rtol=0, atol=0)), "eccodes_detail": vals,
                              "min_true_pre_packing_decrease_m": float(min(ev[1] - ev[0], ev[2] - ev[1]) + max(d["half_step"] for d in vals.values()) * 2)}
print(json.dumps(out, indent=1, default=str))
json.dump(out, open("/tmp/compact_diag/tp_independent.json", "w"), indent=1, default=str)
