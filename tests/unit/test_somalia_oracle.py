"""Focused contract checks for the Somalia oracle experiment (design.md section 8)."""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ipcch.somalia_oracle import PERCENT_COLUMNS, oracle_feature_names
from ipcch.somalia_oracle import data as sd
from ipcch.somalia_oracle import evaluation as ev
from ipcch.somalia_oracle import history as hist
from ipcch.somalia_oracle import modeling as md
from ipcch.somalia_oracle.pipeline import validate_scope_construction

REFERENCE_ROOT = Path(__file__).resolve().parents[3] / "Food_Crisis_Cluster"


def _mr_rows(rows):
    frame = pd.DataFrame(rows, columns=["area_id", "year", "month", "overall_phase", *PERCENT_COLUMNS, "estimated_population"])
    return {"fs0": frame}


# --- G4 normalization and label validity -----------------------------------


def test_g4_normalizes_positive_sum_and_keeps_reported_phase():
    frames = _mr_rows([[1981, 2026, 4, 4, 0.15, 0.25, 0.60, 0.25, 0.0, 100.0]])
    ledger = sd.build_label_ledger(frames, {(1981, sd.month_ord(2026, 4).item())})
    row = ledger.iloc[0]
    assert row["valid_target"] and row["normalization_changed"]
    assert row["raw_sum"] == pytest.approx(1.25)
    assert (row["p1"], row["p2"], row["p3"], row["p4"], row["p5"]) == pytest.approx((0.12, 0.20, 0.48, 0.20, 0.0))
    assert (row["q2"], row["q3"], row["q4"], row["q5"]) == pytest.approx((0.88, 0.68, 0.20, 0.0))
    assert row["overall_phase"] == 4 and row["actual_crisis"] == 1


def test_invalid_components_are_not_repaired():
    frames = _mr_rows(
        [
            [1, 2023, 1, 2, 0.5, np.nan, 0.1, 0.0, 0.0, 10.0],
            [2, 2023, 1, 2, 0.5, -0.1, 0.1, 0.0, 0.0, 10.0],
            [3, 2023, 1, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 10.0],
            [4, 2023, 1, 1, 1.0, 0.0, 0.0, 0.0, 0.0, 10.0],
        ]
    )
    ledger = sd.build_label_ledger(frames, set()).set_index("area_id")
    assert ledger.loc[1, "target_invalid_reason"] == "missing_component"
    assert ledger.loc[2, "target_invalid_reason"] == "negative_component"
    assert ledger.loc[3, "target_invalid_reason"] == "nonpositive_sum"
    assert ledger.loc[4, "valid_score"]  # all-zero cumulative truth is a valid phase-1 row
    assert ledger.loc[4, ["q2", "q3", "q4", "q5"]].tolist() == [0.0, 0.0, 0.0, 0.0]


def test_unreconciled_recent_label_is_excluded():
    frames = _mr_rows([[1917, 2026, 1, 2, 0.5, 0.35, 0.15, 0, 0, 10.0], [1917, 2024, 1, 2, 0.5, 0.35, 0.15, 0, 0, 10.0]])
    ledger = sd.build_label_ledger(frames, set()).set_index("target_ord")
    assert ledger.loc[sd.month_ord(2026, 1).item(), "target_invalid_reason"] == "provenance_unreconciled"
    assert ledger.loc[sd.month_ord(2024, 1).item(), "valid_target"]


def test_conflicting_model_ready_files_fail():
    a = _mr_rows([[1, 2023, 1, 2, 0.5, 0.4, 0.1, 0, 0, 10.0]])["fs0"]
    b = a.assign(overall_phase=3)
    with pytest.raises(sd.DataContractError):
        sd.build_label_ledger({"fs0": a, "fs1": b}, set())


# --- V2 latest-ended season -------------------------------------------------


def _seasons():
    rows = [
        # area 10: cross-year s2 ending 2024-02-24 (exclusive), s1 ending 2024-08-18
        [10, 2024, "s2", "2023-09-27", "2024-02-24", 1, "high", 150, 150, 1.0],
        [10, 2024, "s1", "2024-04-20", "2024-08-18", 1, "high", 120, 120, 2.0],
        [10, 2025, "s1", "2025-04-20", "2025-09-01", 1, "high", 100, 134, 3.0],
    ]
    cols = ["admin_code", "season_year", "season", "gs_start_date", "gs_end_date_exclusive", "gs_calendar_valid", "gs_calendar_quality", "gs_available_window_days", "gs_duration_recalculated_days", "prcp_anom_gs_ensmean"]
    frame = pd.DataFrame(rows, columns=cols)
    for c in sd.V2_FEATURES[1:]:
        frame[c] = np.nan
    return sd.prepare_v2_seasons(frame)


def test_v2_selects_latest_season_ended_by_month_end_boundary():
    seasons = _seasons()
    origins = sd.month_ord([2024, 2024, 2024, 2023, 2025], [1, 2, 8, 12, 9])
    block = sd.v2_block(seasons, np.full(5, 10), origins)
    # Jan 2024: boundary Feb 1 < Feb 24 -> no prior season
    assert block.loc[0, "v2_status"] == "no_prior_season" and np.isnan(block.loc[0, "prcp_anom_gs_ensmean"])
    # Feb 2024: boundary Mar 1 >= Feb 24 (exclusive end) -> cross-year s2
    assert block.loc[1, "v2_season"] == "s2" and block.loc[1, "prcp_anom_gs_ensmean"] == 1.0
    # Aug 2024: boundary Sep 1 >= Aug 18 -> s1 of 2024
    assert block.loc[2, "prcp_anom_gs_ensmean"] == 2.0
    assert block.loc[3, "v2_status"] == "no_prior_season"
    # Sep 2025: 2025 s1 ended (Sep 1 <= Oct 1) but export incomplete -> gap, not backfilled
    assert block.loc[4, "v2_status"] == "incomplete_export" and np.isnan(block.loc[4, "prcp_anom_gs_ensmean"])


# --- Oracle weather -----------------------------------------------------------


def _weather(values):
    rows = []
    for (year, month), (rain, temp) in values.items():
        rows.append({"admin_code": 5, "year": year, "month": month, "Rainf_f_tavg_mean": rain, "Tair_f_tavg_mean": temp})
    return sd.build_weather_ledger(pd.DataFrame(rows))


def test_oracle_offsets_per_horizon():
    assert oracle_feature_names(0) == []
    assert len(oracle_feature_names(3)) == 6
    assert len(oracle_feature_names(6)) == len(oracle_feature_names(12)) == 12
    assert oracle_feature_names(12)[-1] == "oracle_Tair_f_tavg_mean_o6"


def test_oracle_block_uses_origin_plus_k_and_rejects_repeats():
    months = {(2024, m): (float(m), 300.0 + m) for m in range(1, 13)}
    months[(2024, 5)] = months[(2024, 4)]  # forward-fill signature
    weather = _weather(months)
    features, ledger = sd.oracle_block(weather, np.array([5]), sd.month_ord([2024], [2]), 3)
    assert features.loc[0, "oracle_Rainf_f_tavg_mean_o1"] == 3.0
    assert features.loc[0, "oracle_Tair_f_tavg_mean_o2"] == 304.0
    assert np.isnan(features.loc[0, "oracle_Rainf_f_tavg_mean_o3"])  # 2024-05 repeats 2024-04
    assert not features.loc[0, "oracle_all_verified"]
    assert ledger["weather_status"].tolist() == ["verified", "verified", "repeats_previous_month"]
    features12, _ = sd.oracle_block(weather, np.array([5]), sd.month_ord([2024], [6]), 12)
    assert features12.filter(like="_o7").empty  # never beyond o+6
    missing, _ = sd.oracle_block(weather, np.array([5]), sd.month_ord([2024], [11]), 3)
    assert np.isnan(missing.loc[0, "oracle_Rainf_f_tavg_mean_o2"])  # 2025-01 absent -> no fill


def test_scope_validation_rejects_features_newer_than_origin():
    validate_scope_construction(["x__l3_s3", "x__roll3_mean_asof3_s3", "y__roll3_mean_asof12", "static"], 3)
    with pytest.raises(sd.DataContractError):
        validate_scope_construction(["x__l3_s3"], 6)
    with pytest.raises(sd.DataContractError):
        validate_scope_construction(["x__roll3_mean_asof3_s3"], 12)


# --- History ------------------------------------------------------------------


def _history_ledger(records):
    frame = pd.DataFrame(records, columns=["area_id", "target_ord", "p1", "p2", "p3", "p4", "p5"])
    for i in range(1, 6):
        frame[f"h_p{i}"] = frame[f"p{i}"]
    frame["history_crisis_state"] = ((frame["p3"] + frame["p4"] + frame["p5"]) * 5 > 1).astype(int)
    return frame


def test_history_h0_excludes_target_month_and_windows_are_origin_anchored():
    t = sd.month_ord(2024, 7).item()
    ledger = _history_ledger([[1, t - 12, 0.5, 0.3, 0.2, 0, 0], [1, t - 6, 0.4, 0.3, 0.3, 0, 0], [1, t, 0.1, 0.1, 0.8, 0, 0]])
    index = hist.build_history_index(ledger)
    names = hist.history_feature_names()
    block = pd.DataFrame(hist.build_history_block(index, np.array([1]), np.array([t]), np.array([t - 1]), names), columns=names)
    assert block.loc[0, "hist_q3_obs1"] == pytest.approx(0.3)  # the month-T observation is invisible
    assert block.loc[0, "hist_age_obs1"] == 6
    assert block.loc[0, "hist_support_common_m06_count"] == 0  # window [t-5, t]; t itself is invisible
    assert block.loc[0, "hist_support_common_m12_count"] == 1  # window [t-11, t] holds only t-6
    slots = hist.history_slot_sources(index, np.array([1]), np.array([t - 1]))
    assert slots.loc[0, "history_obs1_source_ord"] == t - 6 and slots.loc[0, "history_visible_count"] == 2


def test_history_irregular_gaps_q3_zero_ratio_and_no_history():
    base = sd.month_ord(2020, 1).item()
    ledger = _history_ledger([[2, base, 1.0, 0, 0, 0, 0], [2, base + 7, 0.5, 0.2, 0.2, 0.1, 0], [2, base + 9, 0.4, 0.2, 0.2, 0.2, 0]])
    index = hist.build_history_index(ledger)
    names = hist.history_feature_names()
    block = pd.DataFrame(hist.build_history_block(index, np.array([2, 3]), np.array([base + 12, base + 12]), np.array([base + 12, base + 12]), names), columns=names)
    row = block.loc[0]
    assert row["hist_gap_obs1_obs2"] == 2 and row["hist_gap_obs2_obs3"] == 7
    assert np.isnan(row["hist_severe_fraction_obs3"])  # q3 == 0 -> undefined ratio kept missing
    assert row["hist_q3_rate_obs1_obs2"] == pytest.approx((0.4 - 0.3) / 2)
    assert row["hist_support_severe_fraction_all_count"] == 2
    assert np.isnan(row["hist_q3_obs4"])
    no_history = block.loc[1]
    assert np.isnan(no_history["hist_q3_obs1"]) and no_history["hist_no_crisis"] == 1.0
    assert no_history["hist_support_common_all_count"] == 0


@pytest.mark.skipif(not (REFERENCE_ROOT / "IPCCHPopulationHistoryExperiment" / "prepare_data.py").exists(), reason="reference repository not available")
def test_history_port_matches_reference_for_h_ge_1():
    sys.path.insert(0, str(REFERENCE_ROOT))
    try:
        ref = importlib.import_module("IPCCHPopulationHistoryExperiment.prepare_data")
    finally:
        sys.path.remove(str(REFERENCE_ROOT))
    rng = np.random.default_rng(0)
    records = []
    for area in (11, 12, 13):
        months = np.sort(rng.choice(np.arange(24000, 24060), size=12, replace=False))
        for m in months:
            p = rng.dirichlet(np.ones(5))
            if rng.random() < 0.2:
                p = np.array([0.8, 0.2, 0, 0, 0])
            records.append([area, int(m), *p])
    ledger = _history_ledger(records)
    ours = hist.build_history_index(ledger)
    ref_valid = ledger.rename(columns={"area_id": "admin_code"}).assign(
        year=lambda d: d["target_ord"] // 12, month=lambda d: d["target_ord"] % 12 + 1, ipcch_food_crisis=ledger["history_crisis_state"]
    )
    for i, column in enumerate(ref.ipcch.NORMALIZED_PHASE_COLUMNS):
        ref_valid[column] = ledger[f"h_p{i + 1}"].map(repr)
    ref_index = ref.build_history_index(ref_valid)
    spec = ref.load_frozen_spec()
    admin = np.repeat([11, 12, 13, 14], 20)
    origin = np.tile(np.arange(24005, 24065, 3), 4)
    expected = ref.build_history_block(ref_index, admin, origin, spec.additional_features)
    names = hist.history_feature_names()
    actual = hist.build_history_block(ours, admin, origin, origin, names)
    width = len(spec.additional_features)
    assert names[:width] == list(spec.additional_features)
    np.testing.assert_array_equal(np.isnan(actual[:, :width]), np.isnan(expected))
    np.testing.assert_allclose(np.nan_to_num(actual[:, :width]), np.nan_to_num(expected), rtol=0, atol=1e-12)


# --- Persistence --------------------------------------------------------------


def test_persistence_uses_latest_valid_phase_before_target_and_origin():
    ledger = pd.DataFrame(
        {
            "area_id": [1, 1, 1, 2],
            "target_ord": [100, 106, 112, 100],
            "overall_phase": [2.0, 4.0, 3.0, 1.0],
            "valid_phase": [True, True, True, False],
        }
    )
    out = sd.persistence_lookup(ledger, np.array([1, 1, 1, 2]), np.array([112, 109, 103, 112]), np.array([112, 112, 106, 112]))
    assert out["persistence_phase"].tolist()[:3] == [4.0, 4.0, 2.0]  # H=0 excludes month 112 itself
    assert out["persistence_age_months"].tolist()[:3] == [6, 3, 3]
    assert out.loc[3, "persistence_status"] == "no_history" and np.isnan(out.loc[3, "persistence_phase"])


# --- Modeling -------------------------------------------------------------------


def test_unrounded_phase_threshold_boundary():
    pred = np.array([[0.9, 0.196, 0.0, 0.0], [0.9, 0.2, 0.0, 0.0], [0.9, 0.204, 0.0, 0.0], [0.1, 0.0, 0.0, 0.0], [0.9, 0.9, 0.9, 0.2]])
    assert md.phase_from_predictions(pred).tolist() == [2, 3, 3, 1, 5]
    with pytest.raises(md.ModelingError):
        md.phase_from_predictions(np.array([[np.nan, 0, 0, 0]]))


def test_decay_weights_reference_fit_origin():
    w = md.decay_weights(np.array([100, 88, 76]), 100)
    assert w.tolist() == pytest.approx([1.0, 0.5 ** 0.5, 0.5])
    with pytest.raises(md.ModelingError):
        md.decay_weights(np.array([101]), 100)


def _toy_frame(horizon):
    rng = np.random.default_rng(1)
    rows = []
    months = [sd.month_ord(2022, 7).item(), sd.month_ord(2023, 1).item(), sd.month_ord(2023, 8).item(), sd.month_ord(2024, 1).item(), sd.month_ord(2024, 7).item(), sd.month_ord(2025, 4).item()]
    for m in months:
        for area in range(30):
            x = rng.normal()
            q3 = float(np.clip(0.2 + 0.15 * x, 0, 0.9))
            rows.append({"area_id": area, "target_ord": m, "x": x, "q2": min(1.0, q3 + 0.2), "q3": q3, "q4": q3 / 3, "q5": 0.0})
    frame = pd.DataFrame(rows)
    frame["origin_ord"] = frame["target_ord"] - horizon
    frame["target_year"] = frame["target_ord"] // 12
    frame["valid_score"] = True
    frame["actual_crisis"] = (frame["q3"] >= 0.2).astype(float)
    return frame


def test_inner_folds_respect_origin_cutoff_including_h0():
    frame = _toy_frame(0)
    pool = frame.loc[frame["target_year"].isin([2022, 2023, 2024])]
    folds = md.plan_inner_folds(pool, 0, (2022, 2023, 2024))
    assert [f["validation_ord"] for f in folds] == sorted(pool["target_ord"].unique())[-3:]
    for fold in folds:
        assert frame.loc[fold["fit_rows"], "target_ord"].max() < fold["validation_ord"]
    folds12 = md.plan_inner_folds(pool, 12, (2022, 2023, 2024))
    for fold in folds12:
        if fold["supported"]:
            assert frame.loc[fold["fit_rows"], "target_ord"].max() <= fold["validation_ord"] - 12


def test_run_arm_job_selects_first_best_candidate_and_handles_constant_target():
    frame = _toy_frame(3)
    frame["q5"] = 0.0  # constant target -> recorded constant predictor
    config = md.load_candidates()
    for candidate in config["candidates"]:
        candidate["common"]["n_estimators"] = 5
    job = {"job_id": "toy", "horizon": 3, "origin_ord": sd.month_ord(2025, 1).item(), "candidate_years": [2022, 2023, 2024], "test_year": 2025}
    eval_index = frame.index[frame["target_year"] == 2025]
    pool_index = frame.index[frame["target_year"].isin([2022, 2023, 2024])]
    result = md.run_arm_job(job, "A", frame, ["x"], config, eval_index, pool_index, keep_models=True)
    assert result.status == "completed"
    scores = pd.DataFrame(result.candidate_scores)
    best = scores["f2"].max()
    assert result.selected_candidate == scores.loc[scores["f2"] == best, "candidate"].iloc[0]
    assert [m.kind for m in result.final_models][-1] == "constant"
    assert (result.predictions["q5_pred"] == 0.0).all()
    assert result.fit_ledger["target_ord"].max() <= job["origin_ord"]


def test_unsupported_validation_is_explicit():
    frame = _toy_frame(3)
    frame["actual_crisis"] = 1.0
    config = md.load_candidates()
    job = {"job_id": "toy", "horizon": 3, "origin_ord": sd.month_ord(2025, 1).item(), "candidate_years": [2022, 2023, 2024], "test_year": 2025}
    result = md.run_arm_job(job, "A", frame, ["x"], config, frame.index[frame["target_year"] == 2025], frame.index[frame["target_year"] < 2025])
    assert result.status == "unsupported" and "class" in result.reason and result.predictions is None


# --- Metrics and bootstrap -----------------------------------------------------


def test_binary_metrics_and_always_crisis_formula():
    truth = np.array([1, 1, 1, 0, 0], dtype=bool)
    m = ev.binary_metrics(truth, np.ones(5, dtype=bool))
    p = 0.6
    assert m["f2"] == pytest.approx(5 * p / (1 + 4 * p))
    assert (m["tp"], m["fp"], m["fn"], m["tn"]) == (3, 2, 0, 0)
    zero = ev.binary_metrics(truth, np.zeros(5, dtype=bool))
    assert zero["f2"] == 0.0 and zero["precision"] is None
    undefined = ev.binary_metrics(np.zeros(3, dtype=bool), np.zeros(3, dtype=bool))
    assert undefined["f2"] is None and undefined["f2_reason"]


def test_paired_bootstrap_is_deterministic_and_whole_area():
    cohort = pd.DataFrame({"area_id": [3, 3, 1, 2, 2, 4], "target_ord": [1, 2, 1, 1, 2, 1]})
    truth = np.array([1, 0, 1, 1, 0, 1], dtype=bool)
    a = np.array([1, 0, 1, 0, 0, 1], dtype=bool)
    rows1, bundle1 = ev.paired_bootstrap(cohort, truth, {"A": a, "B": a.copy(), "C": ~a}, [("B", "A"), ("C", "A")], draws=200)
    rows2, bundle2 = ev.paired_bootstrap(cohort, truth, {"A": a, "B": a.copy(), "C": ~a}, [("B", "A"), ("C", "A")], draws=200)
    np.testing.assert_array_equal(bundle1["multiplicities"], bundle2["multiplicities"])
    assert bundle1["areas"].tolist() == [1, 2, 3, 4]
    assert (bundle1["multiplicities"].sum(axis=1) == 4).all()
    identical = rows1[0]
    assert identical["point_delta_f2"] == 0.0 and identical["ci_low"] == identical["ci_high"] == 0.0
    assert rows1[1]["contrast"] == "C-A" and rows1[1]["undefined_draws"] >= 0
    # Replay one draw by hand: rows inherit their area's multiplicity.
    counts = bundle1["multiplicities"][7]
    w = counts[np.searchsorted(bundle1["areas"], cohort["area_id"].to_numpy())]
    expected = ev.binary_metrics(truth, ~a, w)["f2"] - ev.binary_metrics(truth, a, w)["f2"] if ev.binary_metrics(truth, ~a, w)["f2"] is not None else np.nan
    assert np.isclose(bundle1["delta::C-A"][7], expected, equal_nan=True)


def test_bootstrap_unavailable_with_one_area_or_undefined_draws():
    cohort = pd.DataFrame({"area_id": [1, 1], "target_ord": [1, 2]})
    rows, _ = ev.paired_bootstrap(cohort, np.array([1, 0], dtype=bool), {"A": np.array([1, 0], dtype=bool), "B": np.array([0, 0], dtype=bool)}, [("A", "B")], draws=50)
    assert rows[0]["interval_status"] == "unavailable" and rows[0]["interval_reason"] == "fewer than two areas"
    cohort2 = pd.DataFrame({"area_id": [1, 2], "target_ord": [1, 1]})
    rows2, _ = ev.paired_bootstrap(cohort2, np.array([1, 0], dtype=bool), {"A": np.array([0, 0], dtype=bool), "B": np.array([1, 1], dtype=bool)}, [("A", "B")], draws=200)
    assert rows2[0]["interval_status"] == "unavailable" and rows2[0]["undefined_draws"] > 0
