"""Every accumulated-tp decrease beyond the summed endpoint decoding bounds, with exact raw values (read-only)."""
import sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, "src")
from ipcch import cds_launch_weather as cw
W = Path("../../../1.Source Data/CDS_API/compact_cds_launch_v1")
pts = pd.read_csv("../../../1.Source Data/assembled_IPCCH/spatial/unique_area_id_lat_lon.csv")
rows = []
for key in ("original_prcp_2026", "original_prcp_hindcast"):
    f = W / f"raw/bulk/{key}.grib"
    grid = cw.first_grid(f)
    cells = cw.containing_cells(grid, pts.lat, pts.lon)
    point_cell = np.zeros(grid["ni"] * grid["nj"], dtype=bool)
    point_cell[cells["flat_index"].to_numpy()] = True
    n_points_in_cell = np.bincount(cells["flat_index"].to_numpy(), minlength=grid["ni"] * grid["nj"])
    vals, err, E = {}, {}, {}
    for meta, g, v in cw.iter_messages(f, None):
        k = (int(meta["dataDate"]) // 10000, int(meta["number"]), int(meta["endStep"]))
        vals[k], err[k], E[k] = v, cw.message_error(meta), int(meta["binaryScaleFactor"])
    for (y, m, s) in [k for k in vals if k[2] == 3672]:
        for a, b in ((3672, 4392), (4392, 5136)):
            inc = vals[(y, m, b)] - vals[(y, m, a)]
            bound = err[(y, m, a)] + err[(y, m, b)]
            idx = np.flatnonzero(inc < -bound)
            for i in idx:
                r, c = divmod(int(i), grid["ni"])
                rows.append({"file": key, "init_year": y, "member": m, "interval_h": f"{a}-{b}", "cell_lat": grid["north_edge"] - (r + 0.5),
                             "cell_lon": grid["west_edge"] + (c + 0.5), "launch_point_cell": bool(point_cell[i]), "points_in_cell": int(n_points_in_cell[i]),
                             "start_m": float(vals[(y, m, a)][i]), "end_m": float(vals[(y, m, b)][i]), "increment_m": float(inc[i]),
                             "endpoint_bound_m": bound, "excess_m": float(-inc[i] - bound), "E_start": E[(y, m, a)], "E_end": E[(y, m, b)]})
df = pd.DataFrame(rows)
out = Path(".trellis/tasks/10-08-compact-cds-launch/research/tp_decreases_beyond_endpoint_bounds.csv")
df.to_csv(out, index=False, float_format="%.17g")
print(len(df), "cases;", int(df.launch_point_cell.sum()), "in launch-point cells;", df.groupby("file").size().to_dict())
print("increment m: min", df.increment_m.min(), "median", df.increment_m.median(), "| excess m: max", df.excess_m.max(), "median", df.excess_m.median())
print("start value m quantiles:", df.start_m.quantile([0, .5, .9, .99, 1]).round(5).to_dict())
print("precision change between endpoints (E_start != E_end):", round(float((df.E_start != df.E_end).mean()), 3))
print("by interval:", df.groupby("interval_h").size().to_dict())
pc = df[df.launch_point_cell]
print("launch-point cells: unique cells", pc.groupby(["cell_lat", "cell_lon"]).ngroups, "points affected", int(pc.drop_duplicates(["cell_lat", "cell_lon"]).points_in_cell.sum()),
      "max |increment| mm", round(-pc.increment_m.min() * 1000, 4))
