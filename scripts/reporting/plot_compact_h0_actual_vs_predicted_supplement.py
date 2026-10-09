#!/usr/bin/env python3
"""Supplemental April 2026 actual-vs-predicted crisis maps for the compact_baseline H0 launch fits (global and Somalia-local).

Two 2-row x 1-column PNGs (actual above predicted) in the style of the earlier launch comparison map: light CartoDB
Positron base geography, red/green binary crisis colors, one shared geographic extent per figure, global Latin America
inset, common legend, 300 dpi. Predictions are the frozen saved H0 predictions of each model (the Somalia panel uses the
Somalia-LOCAL fit, not a subset of global predictions); actuals are the valid reported April 2026 phases of the frozen
compact H0 matrix. Areas without an actual label are not drawn in the actual panel (never shown as "no crisis").

Writes only to the two supplement roots below; existing launch/historical outputs and helpers are read, never changed.
Rerun: PATH=/tmp/ipcch-windows-git-bin:$PATH PYTHONPATH=src /home/swl007007/.venvs/ipcch-geo/bin/python \
       scripts/reporting/plot_compact_h0_actual_vs_predicted_supplement.py
"""
from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = next(path for path in Path(__file__).resolve().parents if (path / "src").exists())
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import numpy as np
import pandas as pd

from ipcch import alert_risk_maps as arm
from ipcch import launch_visualizations as lv
from ipcch import paths

NAME = "nowcasting_2026_04_compact_h0_actual_vs_predicted_supplement"
REPORTS = paths.REPORTS_DIR / "launch" / NAME
RESULTS = paths.RESULTS_DIR / "launch" / NAME
A = paths.SOURCE_DATA_DIR / "assembled_IPCCH"
PRED = {"global": (paths.RESULTS_DIR / "launch/nowcasting_2026_04_compact_cds_v1/runs/compact_baseline/0m/predictions_raw.csv",
                   "e07b733c99daa0a37f0fbb843a4a09f83bb3a8606a80daa5046aa11d024b0277"),
        "somalia_local": (paths.RESULTS_DIR / "launch/nowcasting_2026_04_compact_cds_v1_somalia_local/runs/compact_baseline/0m/predictions_raw.csv",
                          "38d089714323f168d3c61840883a32eaea11c3410790e9dd4589230c6400a940")}
MATRIX = (A / "model_ready/compact_climate_weather_oracle_v1/compact_climate_weather_oracle_v1_compact_baseline_h0.csv",
          "92def8b5bdef5e217abebdadaa21fce490021551a792ed225a78406f61a58012")
COHORT = (A / "model_ready/origin_safe_climate_idp_v1/origin_safe_climate_idp_v1_cohort_keys.csv",
          "136095f1070a30f41f6011ad85d8170618043e6f8a109a6452fd474593a21ec3")
MEMBERSHIP = (A / "country_area_id_lookup.csv", "e2baf6ae9481b42b127db5ce81f3c53ad784bb08ae56dfa56cea74e416b44c90")
GEOMETRY = A / "spatial" / "ipcch_admin_geometry.shp"
SHARES = [f"phase{k}_percent" for k in range(1, 6)]
PREDS = ["phase2_pred", "phase3_pred", "phase4_pred", "phase5_pred"]
THRESHOLD, CRISIS = 0.2, 3
EXPECTED = {"global": {"actual": 2774, "predicted": 6188, "actual_phases": {1: 192, 2: 1041, 3: 1245, 4: 296}, "actual_crisis": 1541},
            "somalia_local": {"actual": 904, "predicted": 904, "actual_phases": {2: 363, 3: 350, 4: 191}, "actual_crisis": 541}}
LABEL = {"global": "Global", "somalia_local": "Somalia"}
MODEL = {"global": "compact_baseline H0, global model", "somalia_local": "compact_baseline H0, Somalia-local model"}
BASEMAP_ALPHA = 0.4  # as alert_risk_maps._add_basemap / the reference figure
BASEMAP_CHANGE = ("CartoDB.Positron (the reference figure's provider) now returns an identical 'API KEY REQUIRED' placeholder tile "
                  "(2049 bytes) for every request from this machine; the approved look is a shallow-gray base geography, so the "
                  "key-free contextily provider Esri.WorldGrayCanvas is used. Tiles are probed and rejected if they are placeholders.")


def basemap_source():
    import contextily as ctx

    return ctx.providers.Esri.WorldGrayCanvas


def probe_basemap() -> dict:
    """A placeholder/error service repeats one tile everywhere: every land-region probe mosaic must hold more than one distinct
    256-px tile, and real tonal detail."""
    import contextily as ctx

    src, out = basemap_source(), {}
    for name, (w, s, e, n) in {"horn_of_africa": (40.0, -2.0, 52.0, 12.0), "west_africa": (-18.0, 4.0, -6.0, 18.0)}.items():
        img, _ = ctx.bounds2img(w, s, e, n, zoom=5, source=src, ll=True)
        assert img.shape[0] % 256 == 0 and img.shape[1] % 256 == 0, f"{name} probe mosaic is not whole 256-px tiles: {img.shape}"
        tiles = [hashlib.sha256(np.ascontiguousarray(img[r:r + 256, c:c + 256]).tobytes()).hexdigest()
                 for r in range(0, img.shape[0], 256) for c in range(0, img.shape[1], 256)]
        arr = np.asarray(img[..., :3], dtype=float)
        out[name] = {"shape": list(img.shape), "tiles": len(tiles), "distinct_tile_sha256": sorted(set(tiles)),
                     "gray_std": float(arr.mean(axis=2).std()), "distinct_colors": int(len(np.unique(img[..., :3].reshape(-1, 3), axis=0)))}
        assert len(set(tiles)) > 1, f"{name} probe repeats a single tile (placeholder/error service)"
        assert out[name]["gray_std"] > 2.0 and out[name]["distinct_colors"] > 50, f"{name} probe has no geographic detail"
    return out


def sha(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def pinned(path: Path, digest: str) -> dict:
    got = sha(path)
    assert got == digest, f"{path} sha256 {got} differs from the frozen {digest}"
    return {"path": str(path), "sha256": got}


def classes_from_scores(frame: pd.DataFrame) -> np.ndarray:
    """Highest phase whose unrounded cumulative score is >= 0.2 (phase5 first); phase 1 otherwise."""
    q = frame[PREDS].to_numpy(dtype=float)
    return np.select([q[:, 3] >= THRESHOLD, q[:, 2] >= THRESHOLD, q[:, 1] >= THRESHOLD, q[:, 0] >= THRESHOLD], [5, 4, 3, 2], default=1)


def load_predictions(scope: str) -> tuple[pd.DataFrame, dict]:
    path, digest = PRED[scope]
    ident = pinned(path, digest)
    pred = pd.read_csv(path, float_precision="round_trip")
    assert pred["area_id"].is_unique and pred[PREDS].notna().all().all() and np.isfinite(pred[PREDS].to_numpy()).all()
    assert (pred["target_month"] == "2026-04").all() and (pred["origin_month"] == "2026-04").all() and (pred["horizon"] == 0).all()
    assert (pred["run_id"] == "compact_baseline/0m").all() and pred["year"].eq(2026).all() and pred["month"].eq(4).all()
    assert not any(c in pred.columns for c in ("overall_phase", *SHARES)), "saved predictions unexpectedly carry actual labels"
    assert np.array_equal(classes_from_scores(pred), pred["overall_phase_pred"].to_numpy()), "saved classes differ from the unrounded >= 0.2 rule"
    pred["predicted_crisis"] = pred["overall_phase_pred"] >= CRISIS
    return pred, ident


def load_actuals() -> tuple[pd.DataFrame, dict]:
    """Valid reported April 2026 phases of the frozen compact H0 matrix (eval_key is NOT used: it excludes 2026 by design)."""
    ident = {"matrix": pinned(*MATRIX), "cohort": pinned(*COHORT)}
    data = pd.read_csv(MATRIX[0], usecols=["area_id", "year", "month", "overall_phase", *SHARES], float_precision="round_trip")
    april = data[(data["year"] == 2026) & (data["month"] == 4)].reset_index(drop=True)
    shares = april[SHARES].to_numpy(dtype=float)
    valid = np.isfinite(shares).all(axis=1) & (shares >= 0).all(axis=1) & (shares.sum(axis=1) > 0) & april["overall_phase"].isin([1, 2, 3, 4, 5]).to_numpy()
    cohort = pd.read_csv(COHORT[0], usecols=["area_id", "year", "month", "share_valid"])
    cohort = cohort[(cohort["year"] == 2026) & (cohort["month"] == 4)].set_index("area_id")["share_valid"]
    assert cohort.index.is_unique and set(cohort.index) == set(april["area_id"]), "cohort April keys differ from the matrix April keys"
    shares_ok = np.isfinite(shares).all(axis=1) & (shares >= 0).all(axis=1) & (shares.sum(axis=1) > 0)
    assert np.array_equal(cohort.reindex(april["area_id"]).to_numpy(dtype=bool), shares_ok), "share validity differs from the frozen cohort"
    actual = april.loc[valid, ["area_id", "overall_phase"]].reset_index(drop=True)
    actual["overall_phase"] = actual["overall_phase"].astype(int)
    assert actual["area_id"].is_unique
    actual["actual_crisis"] = actual["overall_phase"] >= CRISIS
    ident["april_candidate_rows"] = int(len(april))
    return actual, ident


def somalia_members() -> tuple[set, dict]:
    ident = pinned(*MEMBERSHIP)
    lookup = pd.read_csv(MEMBERSHIP[0], keep_default_na=False, na_values=[""])
    assert lookup["area_id"].is_unique
    ids = set(lookup.loc[lookup["iso3"] == "SOM", "area_id"].astype(int))
    assert len(ids) == 905
    return ids, ident


def scope_data(scope: str, actual_all: pd.DataFrame, members: set) -> dict:
    pred, pred_ident = load_predictions(scope)
    if scope == "somalia_local":
        assert set(pred["area_id"]) <= members, "local predictions outside SOM membership"
        actual = actual_all[actual_all["area_id"].isin(members)].reset_index(drop=True)
    else:
        actual = actual_all
    exp = EXPECTED[scope]
    phases = {int(k): int(v) for k, v in actual["overall_phase"].value_counts().sort_index().items()}
    assert len(actual) == exp["actual"] and len(pred) == exp["predicted"], (len(actual), len(pred))
    assert phases == exp["actual_phases"] and int(actual["actual_crisis"].sum()) == exp["actual_crisis"], phases
    actual_ids, pred_ids = set(actual["area_id"]), set(pred["area_id"])
    assert actual_ids <= pred_ids, "an actual area has no saved prediction"
    coverage = {"actual_rows": len(actual), "predicted_rows": len(pred), "actual_phase_counts": phases, "actual_crisis": int(actual["actual_crisis"].sum()),
                "predicted_phase_counts": {int(k): int(v) for k, v in pred["overall_phase_pred"].value_counts().sort_index().items()},
                "predicted_crisis": int(pred["predicted_crisis"].sum()), "actual_not_predicted": sorted(actual_ids - pred_ids),
                "predicted_without_actual": len(pred_ids - actual_ids)}
    if scope == "somalia_local":
        coverage["membership_areas"] = len(members)
        coverage["members_without_prediction"] = sorted(members - pred_ids)
        assert coverage["members_without_prediction"] == [3146]
    return {"pred": pred, "actual": actual, "prediction_source": pred_ident, "coverage": coverage}


def text_outside(fig) -> list:
    fig.canvas.draw()
    renderer, box = fig.canvas.get_renderer(), fig.bbox
    texts = [fig._suptitle] + [t for ax in fig.axes for t in (ax.title, *ax.texts)] + [t for leg in fig.legends for t in leg.get_texts()] + list(fig.texts)
    bad = []
    for t in texts:
        if t is None or not t.get_visible() or not t.get_text().strip():
            continue
        e = t.get_window_extent(renderer)
        if e.x0 < box.x0 - 0.5 or e.x1 > box.x1 + 0.5 or e.y0 < box.y0 - 0.5 or e.y1 > box.y1 + 0.5:
            bad.append(t.get_text())
    return bad


def draw(scope: str, joined_pred, joined_actual, out_png: Path) -> dict:
    """Actual above predicted; both axes share the predicted full-scope main extent; basemap added visibly (no silent fallback)."""
    import contextily as ctx

    plt, listed_cmap, patch = arm._require_matplotlib()
    use_latam = scope == "global"
    pred3857, act3857 = joined_pred.to_crs(epsg=3857), joined_actual.to_crs(epsg=3857)
    layers = {}
    for name, gdf, col in (("actual", act3857, "actual_crisis"), ("predicted", pred3857, "predicted_crisis")):
        latam = arm._latam_mask(gdf) if use_latam else np.zeros(len(gdf), dtype=bool)
        layers[name] = (gdf[~np.asarray(latam)].copy(), gdf[np.asarray(latam)].to_crs(epsg=4326), col)
    main_pred = layers["predicted"][0]
    extent_src = main_pred[main_pred.geometry.centroid.x.ge(arm.AFRICA_MIN_X_M)] if use_latam else main_pred
    minx, miny, maxx, maxy = extent_src.total_bounds
    pad_x, pad_y = (maxx - minx) * 0.03, (maxy - miny) * 0.03
    xlim, ylim = (minx - pad_x, maxx + pad_x), (miny - pad_y, maxy + pad_y)
    width, height = (10, 12) if scope == "global" else (9, 12)
    fig, axes = plt.subplots(2, 1, figsize=(width, height))
    n_act, n_pred = joined_actual["area_id"].nunique(), joined_pred["area_id"].nunique()
    titles = {"actual": f"Actual crisis (phase >= 3), 2026-04 — areas with a reported phase (n={n_act})",
              "predicted": f"Predicted crisis (phase >= 3), compact_baseline H0 — all predicted areas (n={n_pred})"}
    basemap = {}
    for ax, name in zip(axes, ("actual", "predicted")):
        main, latam, col = layers[name]
        arm._plot_binary_layer(main, col, ax, listed_cmap)
        ax.set_xlim(*xlim)
        ax.set_ylim(*ylim)
        before = len(ax.images)
        ctx.add_basemap(ax, source=basemap_source(), attribution=False, alpha=BASEMAP_ALPHA)  # raises on failure
        img = np.asarray(ax.images[-1].get_array())
        gray = img[..., :3].astype(float).mean(axis=2)
        basemap[name] = {"images_added": len(ax.images) - before, "image_shape": list(img.shape), "gray_std": float(gray.std()),
                         "image_sha256": hashlib.sha256(np.ascontiguousarray(img).tobytes()).hexdigest()}
        assert basemap[name]["images_added"] >= 1 and basemap[name]["gray_std"] > 2.0, f"{name} panel has no real basemap image"
        ax.set_xlim(*xlim)
        ax.set_ylim(*ylim)
        if use_latam:
            if len(latam):
                arm._add_latam_inset(ax, latam, col, listed_cmap)
            else:  # keep the frame comparable; missing actual coverage is stated, never drawn as "no crisis"
                inset = ax.inset_axes([0.67, 0.09, 0.30, 0.28])
                inset.set_xticks([])
                inset.set_yticks([])
                inset.set_title("Latin America", fontsize=7, pad=1.5)
                inset.text(0.5, 0.5, "no 2026-04 actual coverage", ha="center", va="center", fontsize=7, color="0.35", transform=inset.transAxes)
                inset.patch.set_facecolor("white")
                inset.patch.set_alpha(0.92)
        ax.set_title(titles[name], fontsize=11, weight="bold", pad=6)
        ax.set_axis_off()
        basemap[name]["latam_rows"] = int(len(latam))
        basemap[name]["main_rows"] = int(len(main))
    fig.legend(handles=[patch(color=arm.NO_ALERT_COLOR, label="No crisis (phase 1-2)"), patch(color=arm.ALERT_COLOR, label="Crisis (phase 3+)")],
               loc="lower center", ncol=2, fontsize=10)
    fig.suptitle(f"IPCCH 2026-04 {LABEL[scope]} Actual vs Predicted Crisis\n{MODEL[scope]}\n"
                 "Areas without a reported 2026-04 phase are left blank in the actual panel.", fontsize=11.5)
    fig.text(0.99, 0.005, f"Basemap: {basemap_source().attribution}", ha="right", va="bottom", fontsize=6.5, color="0.4")
    fig.subplots_adjust(left=0.03, right=0.97, bottom=0.06, top=0.88, hspace=0.12)
    bad = text_outside(fig)
    assert not bad, f"text outside the canvas: {bad}"
    lims = [(tuple(ax.get_xlim()), tuple(ax.get_ylim())) for ax in axes]
    assert lims[0] == lims[1] == (xlim, ylim), "panels do not share one extent"
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=300)
    plt.close(fig)
    return {"extent_epsg3857": {"xmin": xlim[0], "xmax": xlim[1], "ymin": ylim[0], "ymax": ylim[1]}, "shared_extent": True,
            "extent_source": "predicted full-scope main panel" + (" (Latin America in inset; areas west of the Africa cut-off excluded)" if use_latam else ""),
            "basemap": {"provider": "Esri.WorldGrayCanvas", "url": basemap_source().build_url(), "attribution": basemap_source().attribution,
                        "alpha": BASEMAP_ALPHA, "panels": basemap, "provider_change_reason": BASEMAP_CHANGE,
                        "status": "added (direct contextily call; failures raise; placeholder/blank tiles rejected)"}}


def git_head() -> str:
    exe = "/mnt/c/Program Files/Git/cmd/git.exe"
    exe = exe if Path(exe).exists() else "git"
    return subprocess.run([exe, "rev-parse", "HEAD"], capture_output=True, text=True, cwd=PROJECT_ROOT).stdout.strip()


def main() -> int:
    import contextily
    import geopandas
    import matplotlib
    import sklearn
    import xgboost

    for root in (REPORTS, RESULTS):
        assert NAME in root.parts and "nowcasting_2026_04_compact_cds_v1" not in root.parts
    probe = probe_basemap()
    actual_all, actual_ident = load_actuals()
    members, member_ident = somalia_members()
    boundaries = arm.load_spatial_boundaries(GEOMETRY)
    assert boundaries["area_id"].is_unique
    geometry = {ext: {"path": str(GEOMETRY.with_suffix(ext)), "sha256": sha(GEOMETRY.with_suffix(ext))}
                for ext in (".shp", ".shx", ".dbf", ".prj", ".cpg") if GEOMETRY.with_suffix(ext).exists()}
    meta = {"name": NAME, "description": "April 2026 actual vs compact_baseline H0 predicted crisis maps (supplement; prediction maps unchanged)",
            "binary_definitions": {"actual_crisis": "reported overall_phase >= 3 (valid shares, phase 1-5)",
                                   "predicted_crisis": "saved overall_phase_pred >= 3; overall_phase_pred = highest phase whose unrounded cumulative score >= 0.2, else 1",
                                   "colors": {"crisis": arm.ALERT_COLOR, "no_crisis": arm.NO_ALERT_COLOR}, "missing_actual": "not drawn (blank)"},
            "sources": {"actual": actual_ident, "membership": member_ident, "geometry": geometry},
            "basemap_probe": probe, "scopes": {}}
    for scope in ("global", "somalia_local"):
        d = scope_data(scope, actual_all, members)
        jp = lv.join_for_two_panel(d["pred"][["area_id", "overall_phase_pred", "predicted_crisis"]],
                                   d["actual"][["area_id", "overall_phase", "actual_crisis"]], boundaries)
        lv._ensure_crisis_columns(jp)
        assert not jp.unmatched_prediction and not jp.unmatched_actual, "geometry keys lost in the join"
        assert jp.mapped_predicted_count == len(d["pred"]) and jp.mapped_actual_count == len(d["actual"])
        assert jp.predicted_joined["area_id"].is_unique and jp.actual_joined["area_id"].is_unique
        assert jp.actual_joined["actual_crisis"].notna().all() and jp.actual_joined["overall_phase"].between(1, 5).all()
        assert np.array_equal(jp.actual_joined.sort_values("area_id")["actual_crisis"].to_numpy(dtype=bool),
                              (jp.actual_joined.sort_values("area_id")["overall_phase"] >= CRISIS).to_numpy())
        png = REPORTS / f"ipcch_2026_04_compact_baseline_h0_{scope}_actual_vs_predicted_crisis_map.png"
        drawn = draw(scope, jp.predicted_joined, jp.actual_joined, png)
        values = pd.concat([pd.DataFrame({"area_id": d["actual"]["area_id"], "panel": "actual", "phase": d["actual"]["overall_phase"],
                                          "crisis": d["actual"]["actual_crisis"]}),
                            pd.DataFrame({"area_id": d["pred"]["area_id"], "panel": "predicted", "phase": d["pred"]["overall_phase_pred"],
                                          "crisis": d["pred"]["predicted_crisis"]})], ignore_index=True).sort_values(["panel", "area_id"])
        values.insert(0, "scope", scope)
        rec = RESULTS / f"{scope}_plotted_values.csv"
        rec.parent.mkdir(parents=True, exist_ok=True)
        values.to_csv(rec, index=False)
        meta["scopes"][scope] = {"title": LABEL[scope], "model": MODEL[scope], "prediction_source": d["prediction_source"], "coverage": d["coverage"],
                                 "join": {"unmatched_prediction": len(jp.unmatched_prediction), "unmatched_actual": len(jp.unmatched_actual),
                                          "mapped_predicted": jp.mapped_predicted_count, "mapped_actual": jp.mapped_actual_count},
                                 **drawn, "figure": {"path": str(png), "sha256": sha(png), "dpi": 300},
                                 "plotted_values": {"path": str(rec), "sha256": sha(rec), "rows": len(values)}}
    meta["code"] = {"script": str(Path(__file__).resolve()), "sha256": sha(Path(__file__).resolve()), "git_head": git_head()}
    meta["runtime"] = {"executable": sys.executable, "python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__,
                       "sklearn": sklearn.__version__, "xgboost": xgboost.__version__, "geopandas": geopandas.__version__,
                       "matplotlib": matplotlib.__version__, "contextily": contextily.__version__}
    meta["reproduce"] = ("PATH=/tmp/ipcch-windows-git-bin:$PATH PYTHONPATH=src /home/swl007007/.venvs/ipcch-geo/bin/python "
                         "scripts/reporting/plot_compact_h0_actual_vs_predicted_supplement.py")
    (RESULTS / "metadata.json").write_text(json.dumps(meta, indent=2, default=str) + "\n")
    print(json.dumps({s: {"figure": m["figure"], "coverage": {k: m["coverage"][k] for k in ("actual_rows", "predicted_rows", "actual_crisis", "predicted_crisis")},
                          "basemap_images": {k: v["images_added"] for k, v in m["basemap"]["panels"].items()}} for s, m in meta["scopes"].items()}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
