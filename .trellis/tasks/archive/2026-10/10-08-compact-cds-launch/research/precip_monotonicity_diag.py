"""Diagnose non-monotone accumulated precipitation in the retrieved original-frequency tp files (read-only)."""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, "src")
from ipcch import cds_launch_weather as cw
W = Path("../../../1.Source Data/CDS_API/compact_cds_launch_v1")
pts = pd.read_csv("../../../1.Source Data/assembled_IPCCH/spatial/unique_area_id_lat_lon.csv")
for key in ("original_prcp_2026", "original_prcp_hindcast"):
    f = W / f"raw/bulk/{key}.grib"
    grid = cw.first_grid(f)
    rows = []
    vals = {}
    for meta, g, v in cw.iter_messages(f, None):
        y = int(meta["dataDate"]) // 10000
        vals[(y, int(meta["number"]), int(meta["endStep"]))] = v
        rows.append({"year": y, "member": int(meta["number"]), "step": int(meta["endStep"]), "err": cw.message_error(meta),
                     "E": meta["binaryScaleFactor"], "ref": meta["referenceValue"], "min": float(np.min(v)), "max": float(np.max(v)), "mean": float(np.mean(v))})
    meta_df = pd.DataFrame(rows)
    print(f"== {key}: messages {len(meta_df)}; value range per step (m):")
    print(meta_df.groupby("step")[["min", "max", "mean", "err"]].agg(["min", "max"]).to_string())
    cells = np.unique(cw.containing_cells(grid, pts.lat, pts.lon)["flat_index"].to_numpy())
    neg = []
    for (y, m, s), v in vals.items():
        if s == 3672:
            a, b, c = v, vals[(y, m, 4392)], vals[(y, m, 5136)]
            for lab, x, z in (("3672-4392", a, b), ("4392-5136", b, c)):
                inc = z - x
                ea = meta_df[(meta_df.year == y) & (meta_df.member == m) & (meta_df.step == (3672 if lab[:4] == "3672" else 4392))]["err"].iloc[0]
                eb = meta_df[(meta_df.year == y) & (meta_df.member == m) & (meta_df.step == (4392 if lab[:4] == "3672" else 5136))]["err"].iloc[0]
                bad_all = inc < -(ea + eb)
                bad_pts = bad_all[cells]
                neg.append({"year": y, "member": m, "interval": lab, "tol": ea + eb, "min_inc_global": float(inc.min()), "n_bad_global": int(bad_all.sum()),
                            "min_inc_points": float(inc[cells].min()), "n_bad_point_cells": int(bad_pts.sum()), "start_value_at_worst": float(x[np.argmin(inc)])})
    nd = pd.DataFrame(neg)
    print(f"-- {key}: member-intervals with any decrease beyond tol (all grid cells / point cells):",
          int((nd.n_bad_global > 0).sum()), "/", int((nd.n_bad_point_cells > 0).sum()), "of", len(nd))
    print(nd.sort_values("min_inc_global").head(8).to_string())
    print("ratio worst decrease / tol:", float((-nd.min_inc_global / nd.tol).max()))
