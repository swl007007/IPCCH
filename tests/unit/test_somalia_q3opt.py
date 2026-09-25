"""Contract checks for the q3-first Somalia optimization (implement.md checklist 2-6)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ipcch.somalia_oracle import data as sd
from ipcch.somalia_oracle import q3eval as qe
from ipcch.somalia_oracle import q3opt as qo


def test_config_pins_v1_bundles_and_inventory():
    cfg, bundles = qo.load_config()
    assert cfg["calibration_methods"] == ["none", "shift", "isotonic"]
    assert [c["id"] for c in bundles["candidates"]] == ["X1", "X2", "X3", "X4", "X5", "X6"]
    assert cfg["tie_tolerance"] == 1e-12 and cfg["binary_q3_threshold"] == 0.2


# --- calibration -------------------------------------------------------------


def test_identity_is_not_isotonic_and_bound_keeps_raw():
    raw = np.array([-0.1, 0.3, 1.2])
    m = qo.fit_mapping("none", raw, raw, np.array([1, 2, 3]), 2)
    assert m.ok and np.array_equal(m.apply(raw), raw)
    final, clipped = qo.bound_share(m.apply(raw))
    assert final.tolist() == [0.0, 0.3, 1.0] and clipped.tolist() == [True, False, True]


def test_shift_and_isotonic_support_rules():
    raw = np.array([0.3, 0.4, 0.5, 0.6])
    truth = np.array([0.2, 0.3, 0.4, 0.5])
    shift = qo.fit_mapping("shift", raw, truth, np.array([1, 1, 2, 2]), 2)
    assert shift.shift == pytest.approx(0.1) and shift.apply(np.array([0.5]))[0] == pytest.approx(0.4)
    assert not qo.fit_mapping("shift", raw, truth, np.array([1, 1, 1, 1]), 2).ok  # one calibration month
    assert not qo.fit_mapping("isotonic", np.full(4, 0.3), truth, np.array([1, 1, 2, 2]), 2).ok  # <2 distinct scores
    iso = qo.fit_mapping("isotonic", raw, truth, np.array([1, 1, 2, 2]), 2)
    assert iso.ok and iso.apply(np.array([0.0, 2.0])).tolist() == pytest.approx([0.2, 0.5])  # clipped extrapolation
    with pytest.raises(qo.Q3OptError):
        qo.fit_mapping("platt", raw, truth, np.array([1, 2, 1, 2]), 2)


# --- chronology ---------------------------------------------------------------


def _frame(months, horizon=0, areas=4):
    rows = []
    for m in months:
        for a in range(areas):
            rows.append({"area_id": a, "target_ord": m, "valid_score": True})
    f = pd.DataFrame(rows)
    f["target_year"] = f["target_ord"] // 12
    f["origin_ord"] = f["target_ord"] - horizon
    return f


def test_selection_plan_h0_months_and_calibration_precede_scoring():
    cfg, _ = qo.load_config()
    months = [int(sd.month_ord(y, m)) for y, m in [(2022, 5), (2022, 7), (2022, 10), (2023, 1), (2023, 3), (2023, 8), (2024, 1), (2024, 7)]]
    frame = _frame(months)
    plan = qo.selection_plan(frame, [2022, 2023, 2024], 0, months[-1], cfg)
    assert plan["oof"] == months[1:]  # the first month has no earlier labels (H0 self-exclusion)
    assert plan["scoring"] == months[-3:] and plan["status"] == "ok"
    for v, cal in plan["calibration"].items():
        assert len(cal) == 3 and all(c < v for c in cal)
    assert plan["final"] == months[-3:]
    assert qo.fit_cutoff(months[4], 0) == months[4] - 1


def test_receiving_plan_respects_horizon_label_cutoff():
    cfg, _ = qo.load_config()
    months = [int(sd.month_ord(y, m)) for y, m in [(2022, 7), (2023, 1), (2023, 8), (2024, 1), (2024, 7)]]
    frame = _frame(months, horizon=12)
    origin = int(sd.month_ord(2024, 7))
    plan = qo.receiving_plan(frame, [2022, 2023, 2024], 12, origin, cfg)
    # an OOF month v needs a label <= v-12
    assert plan["oof"] == [int(sd.month_ord(2023, 8)), int(sd.month_ord(2024, 1)), int(sd.month_ord(2024, 7))]
    assert all(v <= origin for v in plan["final"])
    assert qo.calibration_months_for(int(sd.month_ord(2024, 7)), plan["oof"], 12, 3) == []  # none <= v-12 among OOF months


# --- selection ----------------------------------------------------------------


def _scores(rows):
    df = pd.DataFrame(rows, columns=["bundle", "method", "formulation", "rmse", "auc", "status"])
    df["bundle_order"] = df["bundle"].str[1].astype(int)
    df["method_order"] = df["method"].map({"none": 0, "shift": 1, "isotonic": 2})
    df["formulation_order"] = df["formulation"].map({"direct": 0, "residual": 1})
    return df


def test_strict_rmse_then_auc_only_inside_tie_set():
    s = _scores([["X1", "none", "direct", 0.100, 0.70, "ok"], ["X2", "shift", "direct", 0.102, 0.78, "ok"], ["X3", "isotonic", "direct", 0.100 + 5e-13, 0.75, "ok"], ["X4", "none", "residual", 0.05, 0.9, "unsupported"]])
    best, tie = qo.select_candidate(s, 1e-12, True)
    assert set(tie["bundle"]) == {"X1", "X3"} and best["bundle"] == "X3"  # higher AUC within the numerical tie
    best2, _ = qo.select_candidate(s, 1e-12, False)
    assert best2["bundle"] == "X1"  # AUC skipped -> none before isotonic
    assert qo.select_candidate(s.iloc[[3]], 1e-12, True)[0] is None


def test_deterministic_order_method_bundle_formulation():
    s = _scores([["X2", "none", "residual", 0.1, np.nan, "ok"], ["X2", "none", "direct", 0.1, np.nan, "ok"], ["X1", "shift", "direct", 0.1, np.nan, "ok"]])
    best, _ = qo.select_candidate(s, 1e-12, True)
    assert (best["method"], best["bundle"], best["formulation"]) == ("none", "X2", "direct")


# --- residual reconstruction / fallback via OOF store ----------------------------


def test_branch_predictions_fall_back_without_fabricating_baseline():
    store = qo.OOFStore()
    idx = np.array([0, 1, 2])
    store.add({"scope": 2025, "horizon": 0, "arm": "D", "formulation": "direct", "bundle": "X1", "v": 5, "pred_idx": idx, "raw_q3": np.array([0.1, 0.2, 0.3]), "status": "ok"})
    store.add({"scope": 2025, "horizon": 0, "arm": "D", "formulation": "residual", "bundle": "X1", "v": 5, "pred_idx": idx, "raw_q3": np.array([0.15, np.nan, 0.35]), "status": "ok"})
    i, raw, branch = qo.branch_predictions(store, 2025, 0, "D", "residual", "X1", 5)
    assert raw.tolist() == [0.15, 0.2, 0.35] and branch.tolist() == ["residual", "fallback_direct", "residual"]


def test_residual_baseline_rejects_future_source():
    cfg, _ = qo.load_config()
    frame = pd.DataFrame({"hist_q3_obs1": [0.3, np.nan, 0.2], "history_obs1_source_ord": [10, -1, 12], "origin_ord": [12, 12, 12], "target_ord": [12, 12, 12]})
    with pytest.raises(qo.Q3OptError):
        qo.baseline(frame, cfg)  # source 12 is not < T=12
    b, ok = qo.baseline(frame.iloc[:2], cfg)
    assert ok.tolist() == [True, False]


def test_oof_and_final_fits_end_to_end_small():
    cfg, bundles = qo.load_config()
    for c in bundles["candidates"]:
        c["common"]["n_estimators"] = 3
    rng = np.random.default_rng(0)
    months = [int(sd.month_ord(y, m)) for y, m in [(2023, 1), (2023, 8), (2024, 1), (2024, 7), (2025, 4)]]
    rows = []
    for m in months:
        for a in range(20):
            x = rng.normal()
            q3 = float(np.clip(0.25 + 0.1 * x, 0, 1))
            rows.append({"area_id": a, "target_ord": m, "x": x, "q2": min(1, q3 + 0.2), "q3": q3, "q4": q3 / 2, "q5": 0.0, "valid_score": True, "actual_crisis": float(q3 >= 0.2), "overall_phase": 3 if q3 >= 0.2 else 2,
                         "hist_q3_obs1": (np.nan if a < 3 else q3 + 0.05), "history_obs1_source_ord": (-1 if a < 3 else m - 6)})
    frame = pd.DataFrame(rows)
    frame["origin_ord"], frame["target_year"] = frame["target_ord"], frame["target_ord"] // 12
    qo.init_state({0: frame}, {(0, "D"): ["x", "hist_q3_obs1"]}, cfg, bundles)
    store = qo.OOFStore()
    for v in months[1:4]:
        for f in ("direct", "residual"):
            r = qo.oof_task({"scope": 2025, "horizon": 0, "arm": "D", "formulation": f, "bundle": "X1", "v": v, "window": [2023, 2024]})
            assert r["fit_max_target_ord"] < v  # H0 self-exclusion
            store.add(r)
    mappings = qo.fit_branch_mappings(store, frame, 2025, 0, "D", "residual", "X1", "shift", months[1:4], cfg)
    assert set(mappings) == {"residual", "fallback_direct"} and all(m.ok for m in mappings.values())
    res = qo.final_task({"job_id": "j", "view": "D_residual", "horizon": 0, "test_year": 2025, "arm": "D", "formulation": "residual", "bundle": "X1", "method": "shift", "window": [2023, 2024], "origin_ord": months[-1], "mappings": mappings})
    p = res["predictions"]
    assert res["status"] == "completed" and len(p) == 20
    assert (p.loc[p["area_id"] < 3, "branch"] == "fallback_direct").all() and (p.loc[p["area_id"] >= 3, "branch"] == "residual").all()
    assert p["q3_final"].between(0, 1).all() and np.isnan(p.loc[p["branch"] == "fallback_direct", "baseline_q3"]).all()
    assert res["fit_ledger"]["target_ord"].max() < months[-1]


# --- evaluation ----------------------------------------------------------------


def test_share_metrics_and_fixed_binary_threshold():
    m = qe.share_metrics(np.array([0.1, 0.3]), np.array([0.2, 0.4]))
    assert m["rmse"] == pytest.approx(0.1) and m["bias"] == pytest.approx(0.1) and m["r2"] == pytest.approx(1 - 0.02 / 0.02)
    frame = pd.DataFrame({"area_id": [1, 2, 3], "target_ord": [1, 1, 1], "q3": [0.1, 0.25, 0.3], "actual_crisis": [0, 1, 1], "overall_phase": [2, 3, 3],
                          "q3_raw": [0.196, 0.2, 0.204], "q3_final": [0.196, 0.2, 0.204], "q2_raw": [0.5] * 3, "q4_raw": [0.0] * 3, "q5_raw": [0.0] * 3, "clipped": [False] * 3, "branch": ["direct"] * 3})
    out = qe.model_view_metrics(frame)
    assert out["bin_tp"] == 2 and out["bin_fp"] == 0 and out["bin_fn"] == 0  # .196 below, .2 and .204 at/above
    assert out["final_auc"] == 1.0


def test_auc_undefined_for_one_class():
    assert np.isnan(qe.pooled_auc(np.array([1, 1]), np.array([0.1, 0.2])))


def test_paired_share_bootstrap_deterministic_and_shared():
    f = pd.DataFrame({"area_id": [1, 1, 2, 3, 4], "target_ord": [1, 2, 1, 1, 1], "q3": [0.1, 0.4, 0.3, 0.2, 0.5], "actual_crisis": [0, 1, 1, 0, 1], "a": [0.12, 0.35, 0.28, 0.25, 0.45], "b": [0.3, 0.3, 0.3, 0.3, 0.3]})
    r1 = qe.paired_share_bootstrap(f, "q3", "actual_crisis", "a", "b", 200, 42)
    r2 = qe.paired_share_bootstrap(f, "q3", "actual_crisis", "a", "b", 200, 42)
    assert np.array_equal(r1["multiplicities"], r2["multiplicities"]) and (r1["multiplicities"].sum(axis=1) == 4).all()
    same = qe.paired_share_bootstrap(f, "q3", "actual_crisis", "a", "a", 200, 42)
    assert same["rmse"]["point"] == 0 and same["rmse"]["ci_low"] == same["rmse"]["ci_high"] == 0
    one = qe.paired_share_bootstrap(f.loc[f["area_id"] == 1], "q3", "actual_crisis", "a", "b", 50, 42)
    assert one["r2"]["status"] == "unavailable"


def test_constant_truth_r2_is_undefined_despite_roundoff():
    truth = np.array([0.1, 0.1, 0.1]) * 3 / 3
    m = qe.share_metrics(truth, np.array([0.2, 0.1, 0.0]))
    assert np.isnan(m["r2"]) and m["rmse"] > 0
    weighted = qe.share_metrics(np.array([0.1, 0.1, 0.4]), np.array([0.1, 0.2, 0.4]), np.array([2.0, 1.0, 0.0]))
    assert np.isnan(weighted["r2"])  # active (positive-weight) truths are identical


def test_legacy_multiclass_macro_f1_is_separate_from_binary():
    frame = pd.DataFrame({"area_id": [1, 2, 3, 4], "target_ord": [1] * 4, "q3": [0.1, 0.3, 0.5, 0.05], "actual_crisis": [0, 1, 1, 0], "overall_phase": [2, 3, 4, 1],
                          "q3_raw": [0.1, 0.3, 0.5, 0.05], "q3_final": [0.1, 0.3, 0.5, 0.05], "q2_raw": [0.5, 0.6, 0.9, 0.1], "q4_raw": [0.0, 0.0, 0.3, 0.0], "q5_raw": [0.0] * 4, "clipped": [False] * 4, "branch": ["direct"] * 4})
    out = qe.model_view_metrics(frame)
    assert out["legacy_multiclass_macro_f1"] == pytest.approx(1.0)
    assert out["legacy_f1"] == pytest.approx(1.0) and "legacy_multiclass_macro_f1" != "legacy_f1"


def test_mapping_records_fit_rows_and_isotonic_knots():
    raw, truth = np.array([0.3, 0.4, 0.5, 0.6]), np.array([0.2, 0.3, 0.4, 0.5])
    m = qo.fit_mapping("isotonic", raw, truth, np.array([1, 1, 2, 2]), 2)
    m.fit_rows = (5, 6, 7, 8)
    d = m.describe()
    import json

    assert json.loads(d["fit_rows"]) == [5, 6, 7, 8] and len(json.loads(d["isotonic_x"])) == d["isotonic_thresholds"]
