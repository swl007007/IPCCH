import numpy as np
import pandas as pd
import pytest

from ipcch import origin_safe as osf
from ipcch import regional_bootstrap as rb


def frame_from(rows):
    """rows: (area_id, iso3, month, overall_phase, overall_phase_pred, phase3_worse, phase3_pred)."""
    df = pd.DataFrame(rows, columns=["area_id", "iso3", "month", "overall_phase", "overall_phase_pred", "phase3_worse", "phase3_pred"])
    df["year"] = 2022
    return df


def row_weights(frame, mult):
    position = {a: i for i, a in enumerate(mult["area_id"])}
    return mult["multiplicity"][:, frame["area_id"].map(position).to_numpy()]


def uneven_frame(seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    layout = {"AAA": {1: 3, 2: 1, 3: 5}, "BBB": {10: 2, 11: 4}, "CCC": {20: 1}}  # unequal areas per country and rows per area
    for iso, areas in layout.items():
        for area, n in areas.items():
            for k in range(n):
                y = int(rng.integers(1, 6))
                rows.append((area, iso, k + 1, y, int(rng.integers(1, 6)), float(rng.uniform()), float(rng.uniform())))
    return frame_from(rows)


def test_multiplicities_are_whole_area_stratified_and_deterministic():
    frame = uneven_frame()
    areas = frame[["area_id", "iso3"]].drop_duplicates()
    a = rb.stratified_area_multiplicities(areas, n_draws=50, seed=42)
    b = rb.stratified_area_multiplicities(areas.sample(frac=1, random_state=3), n_draws=50, seed=42)
    np.testing.assert_array_equal(a["multiplicity"], b["multiplicity"])
    assert list(a["area_id"]) == [1, 2, 3, 10, 11, 20] and a["stratum_sizes"] == {"AAA": 3, "BBB": 2, "CCC": 1}
    sums = {iso: a["multiplicity"][:, a["iso3"] == iso].sum(axis=1) for iso in ("AAA", "BBB", "CCC")}
    assert (sums["AAA"] == 3).all() and (sums["BBB"] == 2).all() and (a["multiplicity"][:, -1] == 1).all()  # singleton stratum
    W = row_weights(frame, a)
    for area in (1, 3, 11):  # every row of an area carries the area's multiplicity
        cols = W[:, (frame["area_id"] == area).to_numpy()]
        assert (cols == cols[:, :1]).all()


def test_weighted_metrics_equal_explicit_row_duplication_on_uneven_countries():
    frame = uneven_frame()
    mult = rb.stratified_area_multiplicities(frame[["area_id", "iso3"]].drop_duplicates(), n_draws=40, seed=42)
    W = row_weights(frame, mult)
    got = rb.weighted_metrics(frame, W)
    for d in range(40):
        want = rb.duplicated_metrics(frame, W[d])
        for metric in osf.ORIGIN_METRICS:
            value, defined = got[metric][0][d], got[metric][1][d]
            if want[metric] is None:
                assert not defined and np.isnan(value), (d, metric)
            else:
                assert defined and value == pytest.approx(want[metric], abs=1e-12), (d, metric)
    point = rb.weighted_metrics(frame, np.ones(len(frame)))
    reference = osf.origin_metrics(frame, "overall", 2022)
    for metric in osf.ORIGIN_METRICS:
        assert point[metric][0][0] == pytest.approx(reference[metric]["value"], abs=1e-12)


def test_f2_is_undefined_not_zero_when_a_draw_has_no_true_positive():
    # A: one TP; B: one FP and one FN. Point F2 = 0.5; sampling B twice leaves precision = recall = 0.
    frame = frame_from([(1, "AAA", 1, 3, 3, 0.5, 0.4), (2, "AAA", 1, 1, 3, 0.1, 0.3), (2, "AAA", 2, 4, 1, 0.6, 0.2)])
    point = rb.weighted_metrics(frame, np.ones(3))
    assert point["f2_phase3plus"][0][0] == pytest.approx(0.5)
    only_b = rb.weighted_metrics(frame, np.array([0, 2, 2]))
    assert only_b["precision_phase3plus"][0][0] == 0 and only_b["sensitivity_phase3plus"][0][0] == 0
    assert not only_b["f2_phase3plus"][1][0]
    assert rb.duplicated_metrics(frame, np.array([0, 2, 2]))["f2_phase3plus"] is None


def test_r2_constant_target_uses_positive_weight_rows_and_exact_equality():
    frame = frame_from([(1, "AAA", 1, 1, 1, 0.3, 0.2), (1, "AAA", 2, 1, 1, 0.3, 0.25), (2, "AAA", 1, 2, 2, 0.9, 0.5)])
    constant = rb.weighted_metrics(frame, np.array([2, 2, 0]))
    assert not constant["r2_phase3plus"][1][0] and rb.duplicated_metrics(frame, np.array([2, 2, 0]))["r2_phase3plus"] is None
    near = frame.copy()
    near.loc[1, "phase3_worse"] = 0.1 + 0.2  # 0.30000000000000004 != 0.3
    defined = rb.weighted_metrics(near, np.array([2, 2, 0]))
    assert defined["r2_phase3plus"][1][0]
    assert defined["r2_phase3plus"][0][0] == pytest.approx(rb.duplicated_metrics(near, np.array([2, 2, 0]))["r2_phase3plus"], rel=1e-9)  # ~-4e30
    single = rb.weighted_metrics(frame, np.array([1, 0, 0]))
    assert not single["r2_phase3plus"][1][0]


def test_conditional_interval_threshold_and_joint_masks():
    delta = np.linspace(-1, 1, 2000)
    valid = np.zeros(2000, dtype=bool)
    valid[:999] = True
    below = rb.conditional_interval(delta, valid, True, True)
    assert below["ci_status"] == "unavailable" and below["draws_valid"] == 999 and below["draws_invalid"] == 1001
    assert below["invalid_fraction"] == pytest.approx(1001 / 2000) and "999" in below["ci_reason"]
    valid[999] = True
    at = rb.conditional_interval(delta, valid, True, True)
    assert at["ci_status"] == "conditional" and at["draws_valid"] == 1000
    assert (at["ci_lower"], at["ci_upper"]) == tuple(np.quantile(delta[valid], [0.025, 0.975], method="linear"))
    assert rb.conditional_interval(delta, valid, False, True)["ci_reason"].startswith("observed point metric undefined")
    assert rb.conditional_interval(delta, valid, True, False)["ci_reason"] == "no country stratum with at least two areas"
    # per-contrast joint masks: same draws, different usable subsets, never replenished
    a, b, c = np.ones(2000, bool), np.ones(2000, bool), np.ones(2000, bool)
    b[:10], c[5:20] = False, False
    assert rb.conditional_interval(delta, a & b, True, True)["draws_valid"] == 1990
    assert rb.conditional_interval(delta, b & c, True, True)["draws_valid"] == 1980


def test_alignment_pairs_reordered_keys_and_rejects_changed_truth():
    base = pd.DataFrame({"area_id": [2, 1, 1], "year": [2022, 2022, 2023], "month": [1, 5, 2], "overall_phase": [1, 3, 2]})
    for column in (*osf.SHARE_COLUMNS, *osf.CUMULATIVE_TARGETS):
        base[column] = [0.1, 0.2, 0.3]
    base["phase3_pred"] = [0.5, 0.6, 0.7]
    shuffled = base.iloc[[2, 0, 1]].assign(phase3_pred=[7.0, 5.0, 6.0])
    aligned = rb.align_paired_predictions({"a": base, "b": shuffled})
    assert aligned["a"][["area_id", "year", "month"]].values.tolist() == [[1, 2022, 5], [1, 2023, 2], [2, 2022, 1]]
    assert aligned["b"]["phase3_pred"].tolist() == [6.0, 7.0, 5.0]
    changed = shuffled.copy()
    changed.loc[changed.index[0], "overall_phase"] = 5
    with pytest.raises(ValueError, match="overall_phase differs"):
        rb.align_paired_predictions({"a": base, "b": changed})
    with pytest.raises(ValueError, match="keys differ"):
        rb.align_paired_predictions({"a": base, "b": shuffled.iloc[:2]})
