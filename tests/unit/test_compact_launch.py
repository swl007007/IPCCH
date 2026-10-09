import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ipcch import compact_launch as cl
from ipcch import origin_safe as osf


# --------------------------------------------------------------------------- reporting arithmetic


def test_repaired_shares_difference_clip_normalize():
    q = np.array([[0.6, 0.3, 0.1, 0.0],      # valid monotone
                  [0.2, 0.25, 0.05, 0.01],   # q3 > q2: negative phase2 component clipped to 0
                  [1.2, 0.5, 0.2, 0.1]])     # q2 > 1: negative phase1, phase2 component 0.7
    out = cl.repaired_shares(q)
    s = out["shares"]
    assert np.allclose(s.sum(axis=1), 1.0, rtol=0, atol=1e-15)
    assert np.allclose(s[0], [0.4, 0.3, 0.2, 0.1, 0.0])
    b = np.array([0.8, 0.0, 0.2, 0.04, 0.01])
    assert np.allclose(s[1], b / b.sum()) and out["any_negative_component"].tolist() == [False, True, True]
    assert np.allclose(s, cl._independent_shares(q), rtol=0, atol=1e-15)
    with pytest.raises(cl.LaunchError, match="nonfinite"):
        cl.repaired_shares(np.array([[np.nan, 0, 0, 0]]))


def test_calendar_literals_for_2027_have_no_year_flag():
    literals = [f"month_{m}" for m in range(1, 13)] + [f"year_{y}" for y in range(2014, 2027)]
    keys = pd.DataFrame({"area_id": [1, 2], "year": [2027, 2026], "month": [4, 10]})
    block = cl.calendar_block(keys, literals)
    assert list(block.columns) == literals
    assert not block.loc[0, [c for c in literals if c.startswith("year_")]].any() and block.loc[0, "month_4"]
    assert block.loc[1, "year_2026"] and block.loc[1, "month_10"] and block.loc[1].sum() == 2


def _area(arm, horizon, pops, p3):
    n = len(pops)
    f = pd.DataFrame({"version": cl.VERSION, "display_arm": arm, "source_run_id": "x", "shared_h0_fit": horizon == 0, "horizon": horizon,
                      "origin_month": "2026-04", "target_month": "2026-10", "area_id": np.arange(n), "country": ["A", "A", "B"][:n],
                      "region": [0, 0, 8][:n], "population_raw": pops, "population_effective": pops, "cap_applied": False})
    shares = np.column_stack([1 - p3, np.zeros(n), p3, np.zeros(n), np.zeros(n)])
    for kind in ("raw", "effective"):
        for i, k in enumerate(cl.PHASES):
            f[f"count_{kind}_phase{k}"] = shares[:, i] * np.asarray(pops)
        f[f"count_{kind}_p3plus"] = f[[f"count_{kind}_phase{k}" for k in (3, 4, 5)]].sum(axis=1)
        f[f"count_{kind}_p4plus"] = f[[f"count_{kind}_phase{k}" for k in (4, 5)]].sum(axis=1)
    return f


def test_aggregate_is_count_weighted_and_flags_zero_denominators():
    area = _area(cl.BASELINE, 6, [100.0, 300.0, 0.0], np.array([0.5, 0.1, 0.9]))
    country = cl.aggregate(area, "country").set_index("country")
    assert country.loc["A", "share_effective_p3plus"] == pytest.approx((50 + 30) / 400)  # not the mean of 0.5 and 0.1
    assert np.isnan(country.loc["B", "share_effective_p3plus"]) and country.loc["B", "share_effective_reason"] == "zero population denominator"
    assert country.loc["B", "n_zero_population_areas"] == 1
    glob = cl.aggregate(area, "global")
    assert glob["share_effective_p3plus"].iloc[0] == pytest.approx(80 / 400) and glob["n_areas"].iloc[0] == 3


def test_paired_differences_need_equal_denominators_and_give_zero_for_shared_h0():
    b = pd.concat([_area(cl.BASELINE, 0, [100.0, 200.0], np.array([0.2, 0.4])), _area(cl.BASELINE, 6, [100.0, 200.0], np.array([0.2, 0.4]))])
    w = pd.concat([_area(cl.WEATHER, 0, [100.0, 200.0], np.array([0.2, 0.4])), _area(cl.WEATHER, 6, [100.0, 200.0], np.array([0.3, 0.4]))])
    table = cl.aggregate(pd.concat([b, w]), "region")
    diff = cl.paired_differences(table, ["region"]).set_index("horizon")
    assert diff.loc[0, "delta_count_effective_p3plus"] == 0.0
    assert diff.loc[6, "delta_count_effective_p3plus"] == pytest.approx(10.0)
    w2 = w.copy()
    w2["population_effective"] = w2["population_effective"] + 1
    with pytest.raises(cl.LaunchError, match="population"):
        cl.paired_differences(cl.aggregate(pd.concat([b, w2]), "region"), ["region"])


def test_cap_rule_scales_only_countries_above_110_percent(tmp_path, monkeypatch):
    ref = tmp_path / "ref.csv"
    pd.DataFrame({"country": ["A", "B"], "country_code": ["AA", ""], "country_en": ["A", "B"], "population_2025_total": [100.0, 100.0],
                  "population_as_of_date": "2025/7/1", "lookup_code_used": ["AA", "NA"]}).to_csv(ref, index=False)
    monkeypatch.setitem(cl.PINNED, "country_population_reference", (ref, "unused"))
    population = pd.DataFrame({"area_id": [1, 2, 3], "estimated_population": [60.0, 60.0, 109.0]})
    mapping = pd.DataFrame({"area_id": [1, 2, 3], "country": ["A", "A", "B"]})
    audit = cl.cap_audit(population, mapping).set_index("country")
    assert audit.loc["A", "cap_applied"] and audit.loc["A", "cap_factor"] == pytest.approx(95 / 120)
    assert not audit.loc["B", "cap_applied"] and audit.loc["B", "cap_factor"] == 1.0  # 109% does not trigger
    assert audit.loc["B", "lookup_code_used"] == "NA"  # literal kept, not parsed as missing
    with pytest.raises(cl.LaunchError, match="one-to-one"):
        cl.cap_audit(population, mapping.assign(country=["A", "A", "C"]))


def test_display_runs_share_h0():
    assert cl.source_run(cl.WEATHER, 0) == (cl.BASELINE, 0) and cl.source_run(cl.WEATHER, 6) == (cl.WEATHER, 6)
    assert len(cl.RUNS) == 5 and len(cl.DISPLAY) == 6


# --------------------------------------------------------------------------- fitting, persistence and resume


def _tiny_manifest(tmp_path: Path) -> Path:
    rng = np.random.default_rng(0)
    keys = pd.DataFrame([(a, y, m) for a in range(1, 13) for y in (2024, 2025, 2026) for m in range(1, 13) if (y, m) <= (2026, 3)], columns=cl.KEYS)
    data = keys.copy()
    shares = rng.dirichlet(np.ones(5), len(keys))
    for k, c in enumerate(osf.SHARE_COLUMNS):
        data[c] = shares[:, k]
    data["overall_phase"] = rng.integers(1, 6, len(keys)).astype(float)
    feats = ["f1", "f2", "month_4"]
    data["f1"], data["f2"] = rng.normal(size=len(keys)), rng.normal(size=len(keys))
    data["month_4"] = data["month"] == 4
    ds = tmp_path / "train.csv"
    data.to_csv(ds, index=False)
    fit = data[cl.KEYS].copy()
    fit["fit_ord"] = osf.month_ord(fit["year"], fit["month"])
    targets = osf.normalized_cumulative_targets(data)
    for c in osf.CUMULATIVE_TARGETS:
        fit[c] = targets[c].to_numpy()
    fit["sample_weight"] = osf.origin_weights(fit["fit_ord"], cl.ORIGIN_ORD, cl.HALF_LIFE)
    fit["age_months"] = cl.ORIGIN_ORD - fit["fit_ord"]
    sel = tmp_path / "fit.csv"
    fit.to_csv(sel, index=False, float_format="%.17g")
    inf = pd.DataFrame({"area_id": range(1, 13), "year": 2026, "month": 10, "f1": rng.normal(size=12), "f2": np.nan, "month_4": False})
    inp = tmp_path / "inf.csv"
    inf.to_csv(inp, index=False, float_format="%.17g")
    manifest = {"version": cl.VERSION, "status": "COMPLETE", "runs": {"compact_baseline/6m": {
        "arm": cl.BASELINE, "horizon": 6, "target_month": "2026-10", "features": feats, "feature_sha256": osf.list_sha256(feats),
        "training_dataset": {"path": str(ds), "sha256": osf.file_sha256(ds)}, "fit_selection": {"path": str(sel), "sha256": osf.file_sha256(sel)},
        "inference": {"path": str(inp), "sha256": osf.file_sha256(inp)}}}}
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest))
    return path


def test_fit_run_saves_exact_schema_raw_predictions_and_resumes_only_complete_matching_runs(tmp_path):
    import xgboost as xgb

    mpath = _tiny_manifest(tmp_path)
    manifest = json.loads(mpath.read_text())
    out = tmp_path / "results"
    record = cl.fit_run(mpath, manifest, "compact_baseline/6m", out)
    run_dir = out / "runs" / "compact_baseline" / "6m"
    assert set(record["artifacts"]) == set(cl.FIT_ARTIFACTS) | {"run_metadata.json"}
    pred = pd.read_csv(run_dir / "predictions_raw.csv", float_precision="round_trip")
    assert len(pred) == 12 and np.isfinite(pred[list(osf.PRED_COLUMNS)]).all().all()
    assert np.array_equal(pred["overall_phase_pred"], osf.classify_cumulative(pred, 0.2))
    inf = pd.read_csv(run_dir / "inference_features.csv.gz")
    for target, column in zip(osf.CUMULATIVE_TARGETS, osf.PRED_COLUMNS):
        booster = xgb.Booster()
        booster.load_model(str(run_dir / f"model_{target}.ubj"))
        assert list(booster.feature_names) == ["f1", "f2", "month_4"]
        assert np.allclose(booster.predict(xgb.DMatrix(inf[["f1", "f2", "month_4"]], feature_names=["f1", "f2", "month_4"])), pred[column], atol=1e-6, rtol=0)
    weights = pd.read_csv(run_dir / "fit_weights.csv.gz")
    assert weights["age_months"].min() == 1  # latest fitting label March 2026, origin April 2026
    assert cl.fit_run(mpath, manifest, "compact_baseline/6m", out) == record  # resume: verified, not refit
    (run_dir / "model_phase3_worse.ubj").write_bytes(b"x")
    with pytest.raises(cl.LaunchError, match="changed since its record"):
        cl.fit_run(mpath, manifest, "compact_baseline/6m", out)


def test_incomplete_run_directory_is_not_resumed(tmp_path):
    mpath = _tiny_manifest(tmp_path)
    run_dir = tmp_path / "results" / "runs" / "compact_baseline" / "6m"
    run_dir.mkdir(parents=True)
    (run_dir / "model_phase2_worse.ubj").write_bytes(b"partial")
    with pytest.raises(cl.LaunchError, match="no artifact record"):
        cl.fit_run(mpath, json.loads(mpath.read_text()), "compact_baseline/6m", tmp_path / "results")


# --------------------------------------------------------------------------- CSV policy, March-only history, future sources


def test_save_csv_keeps_literal_na_and_true_missing(tmp_path):
    frame = pd.DataFrame({"country": ["Namibia", "Chad"], "lookup_code_used": ["NA", None], "x": [1.0, np.nan], "flag": [True, False]})
    info = cl.save_csv(frame, tmp_path / "cap.csv")
    back = pd.read_csv(info["path"], keep_default_na=False, na_values=[""])
    assert back.loc[0, "lookup_code_used"] == "NA" and pd.isna(back.loc[1, "lookup_code_used"]) and np.isnan(back.loc[1, "x"])
    assert cl.same_frame(back, frame)
    assert not cl.same_frame(back.assign(x=[1.0, 2.0]), frame)
    # history ledgers hold object columns of integer area ids and None; the checker reads object columns as text
    ledger = pd.DataFrame({"history_1_source_area_id": pd.Series([0, None, 7], dtype=object), "label": ["a", "NA", None],
                           "code": ["01", "1", "007"], "value": [1.5, np.nan, 2.0]})
    info = cl.save_csv(ledger, tmp_path / "ledger.csv")  # passes: exact written spellings, missing kept missing
    back = pd.read_csv(info["path"], keep_default_na=False, na_values=[""], dtype={"history_1_source_area_id": str, "label": str, "code": str})
    assert back["code"].tolist() == ["01", "1", "007"] and back.loc[1, "label"] == "NA" and pd.isna(back.loc[1, "history_1_source_area_id"])
    assert cl.same_frame(back, ledger)
    assert not cl.same_frame(back.assign(code=["1", "1", "7"]), ledger)  # leading zeros are not numbers here
    assert not cl.same_frame(back.assign(history_1_source_area_id=["0", None, "8"]), ledger)
    assert not cl.same_frame(back.assign(value=[1.5, np.nan, 2.0000000001]), ledger)  # numeric columns stay exact


def test_inference_history_ignores_an_april_2026_report_at_every_horizon():
    labels = pd.DataFrame({"area_id": [1, 1, 1, 1, 2], "year": [2025, 2025, 2026, 2026, 2024], "month": [6, 11, 3, 4, 12],
                           "overall_phase": [2.0, 3.0, 4.0, 5.0, 1.0]})
    obs = osf.valid_phase_observations(labels)
    for horizon, (ty, tm) in cl.TARGETS.items():
        keys = pd.DataFrame({"area_id": [1, 2, 3], "year": ty, "month": tm})
        history, ledger, check = cl.inference_history(obs, keys, horizon)
        assert history.loc[0, "overall_phase_history_1"] == 4.0  # March 2026, not the April 2026 phase 5
        assert history.loc[0, "overall_phase_history_2"] == 3.0 and history.loc[0, "overall_phase_history_change_1_2"] == 1.0
        assert history.loc[1, "overall_phase_history_1"] == 1.0 and np.isnan(history.loc[2, "overall_phase_history_1"])
        assert np.nanmax(ledger[["history_1_source_ord", "history_2_source_ord", "history_3_source_ord"]].to_numpy()) <= cl.LABEL_CUTOFF_ORD
        assert check["observations_excluded_after_march"] == 1 and (ledger["inference_ipc_history_max_month"] == "2026-03").all()


def _grids():
    from ipcch import climate2015_features as cf
    from ipcch import compact_features as cpf

    rng = np.random.default_rng(4)
    first, n = 2023 * 12, 44  # 2023-01 .. 2026-08
    interim = cf.Grid(np.array([1, 2]), first, n, {s: rng.normal(size=(2, n)) + 5 for s in cpf.INTERIM_SOURCES})
    climate = cf.Grid(np.array([1, 2]), first, n, {s: rng.normal(size=(2, n)) for s in cpf.CLIMATE_SOURCES})
    seasons = pd.DataFrame([(a, y, s, f"{y}-{'03' if s == 's1' else '07'}-01", f"{y}-{'05' if s == 's1' else '10'}-01")
                            for a in (1, 2) for y in (2024, 2025, 2026) for s in ("s1", "s2")],
                           columns=["admin_code", "season_year", "season", "gs_start_date", "gs_end_date_exclusive"])
    for m in cpf.SEASON_METRICS:
        seasons[m] = rng.normal(size=len(seasons))
    return interim, climate, seasons


def test_post_origin_sources_do_not_move_at_origin_inputs():
    from ipcch import compact_features as cpf

    interim, climate, seasons = _grids()
    keys = pd.DataFrame({"area_id": [1, 2], "year": 2026, "month": 4})
    base = cpf.monthly_block(interim, climate, keys, [0])[0]
    base_s, ledger = cpf.completed_seasons(seasons, keys["area_id"].to_numpy(), np.full(2, cl.ORIGIN_ORD))
    assert ledger["gs_last1_season_year"].tolist() == [2026, 2026]  # the 2026 s1 season ending May 1 counts at origin April
    out = cl.future_perturbation_check(interim, climate, seasons, keys, base, base_s)
    assert out["changed_cells"] == 0 and out["features_checked"] == base.shape[1] + base_s.shape[1]
    leaky = cpf.monthly_block(interim, climate, keys.assign(month=5), [0])[0]  # a May origin would read a post-origin month
    with pytest.raises(cl.LaunchError, match="post-origin"):
        cl.future_perturbation_check(interim, climate, seasons, keys, leaky, base_s)


# --------------------------------------------------------------------------- maps (real write_maps path, synthetic geometry)


def test_write_maps_produces_seven_figures_with_keyed_records(tmp_path, monkeypatch):
    import geopandas as gpd
    from shapely.geometry import box

    geo = gpd.GeoDataFrame({"area_id": [11, 12, 13]}, geometry=[box(30, 0, 31, 1), box(31, 0, 32, 1), box(-72, 18, -71, 19)], crs="EPSG:4326")
    path = tmp_path / "geom.geojson"
    geo.to_file(path, driver="GeoJSON")
    monkeypatch.setattr(cl, "GEOMETRY", path)
    monkeypatch.setattr(cl, "COHORT_SIZE", 3)
    rows = []
    for arm, horizon in cl.DISPLAY:
        y, m = cl.TARGETS[horizon]
        p3 = np.array([0.1, 0.5, 0.9]) + (0.05 if arm == cl.WEATHER and horizon else 0.0)
        rows.append(pd.DataFrame({"display_arm": arm, "horizon": horizon, "area_id": [11, 12, 13], "target_month": f"{y}-{m:02d}",
                                  "source_run_id": cl.run_id(*cl.source_run(arm, horizon)), "share_p3plus": p3,
                                  "overall_phase_pred_raw": [1, 3, 4] if horizon != 12 else [2, 2, 3]}))
    area = pd.concat(rows, ignore_index=True)
    meta = cl.write_maps(area, tmp_path / "results", tmp_path / "reports")
    pngs = sorted(p.name for p in (tmp_path / "reports" / "figures").glob("*.png"))
    assert pngs == sorted(cl.REQUIRED_FIGURES)
    vis = tmp_path / "results" / "visualizations"
    rec = pd.read_csv(vis / "p3plus_share_comparison_2x3.csv")
    assert rec["area_id"].dtype.kind == "i" and len(rec) == 6 * 3
    merged = rec.merge(area, on=["display_arm", "horizon", "area_id"], suffixes=("", "_t"))
    assert np.allclose(merged["p3plus_percent"], merged["share_p3plus_t"] * 100)
    diff = pd.read_csv(vis / "p3plus_share_difference_1x2.csv")
    assert sorted(diff["horizon"].unique()) == [6, 12] and np.allclose(diff["p3plus_pp_difference"], 5.0)
    cat = pd.read_csv(vis / "crisis_categorical_compact_baseline_12m_2027-04.csv")
    assert cat.sort_values("area_id")["predicted_crisis"].tolist() == [False, False, True]
    assert all(entry["record_sha256"] == osf.file_sha256(entry["record"]) for entry in meta["figures"].values())
    assert meta["figures"]["p3plus_share_difference_1x2"]["color_limits"] == [-5.0, 5.0] or np.allclose(meta["figures"]["p3plus_share_difference_1x2"]["color_limits"], [-5, 5])
