import numpy as np
import pandas as pd
import pytest

from ipcch import climate2015_features as cf
from ipcch import origin_safe as osf
from ipcch import weather_oracle as wo

P, T = wo.ORACLE_VARIABLES
FIRST = 2020 * 12  # grid starts 2020-01


def make_grid(n_months=48, areas=(1, 2), fill=None):
    values = {}
    for i, v in enumerate(wo.ORACLE_VARIABLES):
        arr = np.array([[1000 * a + 100 * i + m for m in range(n_months)] for a in areas], dtype=float)
        values[v] = arr
    grid = cf.Grid(np.array(areas), FIRST, n_months, values)
    if fill:
        fill(grid)
    return grid


def keys_for(rows):
    return pd.DataFrame(rows, columns=list(osf.KEYS))


def x(area, ord_, i, grid):
    return grid.values[wo.ORACLE_VARIABLES[i]][list(grid.area_ids).index(area), ord_ - FIRST]


def build(grid, keys, horizon, history1=None, rolling=None):
    n = len(keys)
    history1 = np.full(n, 2.0) if history1 is None else np.asarray(history1, dtype=float)
    if rolling is None:  # parent R = trailing mean of O-m+1..O
        m = wo.window(horizon)
        origin = osf.month_ord(keys["year"], keys["month"]) - horizon
        rolling = {v: np.array([np.nanmean([wo.calendar_lookup(grid, [a], [o - j])[v][0] for j in range(m)])
                                for a, o in zip(keys["area_id"], origin)]) for v in wo.ORACLE_VARIABLES}
    src = np.where(np.isfinite(history1), osf.month_ord(keys["year"], keys["month"]) - max(horizon, 1), np.nan)
    return wo.build_oracle_block(grid, keys, horizon, rolling, history1, src)


def test_schema_names_order_and_counts():
    assert wo.raw_features(3) == [f"oracle_{v}_o{k}" for k in (1, 2, 3) for v in (P, T)]
    assert len(wo.raw_features(6)) == 12 and len(wo.raw_features(12)) == 12
    assert wo.raw_features(12)[-1] == f"oracle_{T}_o6"
    assert wo.b6_features(3) == [f"oracle_{P}__wmean_o1_o3", f"oracle_{P}__halfmean_roll3_o1_o3", f"oracle_{P}__wmean_o1_o3__x__crisis_history_1_ge3",
                                 f"oracle_{T}__wmean_o1_o3", f"oracle_{T}__halfmean_roll3_o1_o3", f"oracle_{T}__wmean_o1_o3__x__crisis_history_1_ge3"]
    assert wo.parent_rolling_column(P, 3) == f"{P}__roll3_mean_asof3_s3"
    assert wo.parent_rolling_column(P, 6) == f"{P}__roll6_mean_asof6_s6"
    assert wo.parent_rolling_column(T, 12) == f"{T}__roll6_mean_asof12"
    with pytest.raises(ValueError, match="shared reference"):
        wo.window(0)
    parent = ["a", "b"]
    assert wo.arm_features(parent, wo.RAW_ARM, 6) == parent + wo.raw_features(6)
    assert wo.arm_features(parent, wo.B6_ARM, 12) == parent + wo.raw_features(12) + wo.b6_features(12)
    with pytest.raises(ValueError, match="collide"):
        wo.arm_features(wo.raw_features(3)[:1], wo.RAW_ARM, 3)
    with pytest.raises(ValueError, match="unknown oracle arm"):
        wo.appended_features("climate_safe_history_idp", 3)


def test_calendar_lookup_keeps_missing_months_in_place():
    def hole(grid):
        grid.values[P][0, 26] = np.nan  # area 1, 2022-03 missing
    grid = make_grid(fill=hole)
    keys = keys_for([(1, 2022, 5)])  # H3: O = 2022-02, future 2022-03..05
    block, ledger = build(grid, keys, 3)
    assert np.isnan(block.loc[0, f"oracle_{P}_o1"])
    assert block.loc[0, f"oracle_{P}_o2"] == x(1, 2022 * 12 + 3, 0, grid)  # 2022-04, not shifted onto o1
    assert block.loc[0, f"oracle_{P}_o3"] == x(1, 2022 * 12 + 4, 0, grid)
    assert np.isnan(block.loc[0, f"oracle_{P}__wmean_o1_o3"]) and np.isnan(block.loc[0, f"oracle_{P}__halfmean_roll3_o1_o3"])
    assert np.isnan(block.loc[0, f"oracle_{P}__wmean_o1_o3__x__crisis_history_1_ge3"])  # missing F never becomes 0 under gate 0
    assert np.isfinite(block.loc[0, f"oracle_{T}__wmean_o1_o3"])  # precipitation gap does not suppress temperature
    assert ledger.loc[0, f"{P}__future_finite_months"] == 2 and ledger.loc[0, f"{T}__future_finite_months"] == 3
    assert ledger.loc[0, "future_obs_months"] == "2022-03..2022-05" and ledger.loc[0, "assumed_forecast_available_month"] == "2022-02"


def test_outside_grid_months_are_missing_not_wrapped():
    grid = make_grid(n_months=27)  # 2020-01 .. 2022-03
    block, _ = build(grid, keys_for([(1, 2022, 5)]), 3)
    assert np.isfinite(block.loc[0, f"oracle_{P}_o1"]) and np.isnan(block.loc[0, f"oracle_{P}_o2"]) and np.isnan(block.loc[0, f"oracle_{P}_o3"])


def test_stress_case_incomplete_past_keeps_r_but_b_is_missing():
    def past_hole(grid):
        grid.values[P][0, 2021 * 12 + 10 - FIRST] = np.nan  # 2021-11 inside past window 2021-10..12
    grid = make_grid(fill=past_hole)
    keys = keys_for([(1, 2022, 3)])  # H3: O = 2021-12
    rolling = {P: np.array([2.0]), T: np.array([5.0])}
    block, ledger = build(grid, keys, 3, history1=[4.0], rolling=rolling)
    f = np.mean([x(1, 2022 * 12 + k, 0, grid) for k in range(3)])
    assert block.loc[0, f"oracle_{P}__wmean_o1_o3"] == f
    assert np.isnan(block.loc[0, f"oracle_{P}__halfmean_roll3_o1_o3"])  # existing R=2 stays, new B needs the full past
    assert block.loc[0, f"oracle_{P}__wmean_o1_o3__x__crisis_history_1_ge3"] == f  # history1 = 4 >= 3
    ft = np.mean([x(1, 2022 * 12 + k, 1, grid) for k in range(3)])
    assert block.loc[0, f"oracle_{T}__halfmean_roll3_o1_o3"] == (5.0 + ft) / 2
    assert ledger.loc[0, f"{P}__past_finite_months"] == 2 and ledger.loc[0, f"{T}__past_finite_months"] == 3


def test_gate_zero_missing_history_and_complete_window_b_equals_2m_mean():
    grid = make_grid()
    keys = keys_for([(1, 2022, 6), (2, 2022, 6), (2, 2022, 7)])
    block, ledger = build(grid, keys, 3, history1=[2.0, np.nan, 3.0])
    q = f"oracle_{P}__wmean_o1_o3__x__crisis_history_1_ge3"
    assert block.loc[0, q] == 0.0 and np.isnan(block.loc[1, q]) and block.loc[2, q] == block.loc[2, f"oracle_{P}__wmean_o1_o3"]
    assert np.isfinite(block.loc[1, f"oracle_{P}__wmean_o1_o3"]) and np.isfinite(block.loc[1, f"oracle_{P}__halfmean_roll3_o1_o3"])
    origin = 2022 * 12 + 5 - 3
    months = [x(1, origin + d, 0, grid) for d in range(-2, 4)]
    assert block.loc[0, f"oracle_{P}__halfmean_roll3_o1_o3"] == pytest.approx(np.mean(months), abs=1e-12)
    assert np.isnan(ledger.loc[1, "history_1_source_ord"]) and ledger.loc[0, "history_1_staleness_months"] == 0


def test_h12_uses_first_six_months_and_ignores_later_and_earlier_weather():
    grid = make_grid(n_months=72)
    keys = keys_for([(1, 2023, 6)])  # O = 2022-06, window 2022-07..12
    base, ledger = build(grid, keys, 12)
    assert list(base.columns) == wo.raw_features(12) + wo.b6_features(12)
    assert ledger.loc[0, "future_obs_last_ord"] - ledger.loc[0, "origin_ord"] == 6
    origin = 2022 * 12 + 5

    def later(g):  # O+7 .. O+12
        for v in wo.ORACLE_VARIABLES:
            g.values[v][:, origin + 7 - FIRST:origin + 13 - FIRST] += 1000.0
    after, _ = build(make_grid(n_months=72, fill=later), keys, 12)
    pd.testing.assert_frame_equal(base, after)

    def earlier(g):  # months <= O
        for v in wo.ORACLE_VARIABLES:
            g.values[v][:, :origin + 1 - FIRST] += 1000.0
    rolling = {v: np.array([0.5]) for v in wo.ORACLE_VARIABLES}
    a, _ = build(grid, keys, 12, rolling=rolling)
    b, _ = build(make_grid(n_months=72, fill=earlier), keys, 12, rolling=rolling)
    for name in wo.raw_features(12) + [c for c in wo.b6_features(12) if "__halfmean_" not in c]:
        assert a.loc[0, name] == b.loc[0, name]


def _frame_with(block, ledger, keys, history1, rolling, horizon):
    frame = keys.copy()
    frame[wo.HISTORY_GATE] = history1
    for v in wo.ORACLE_VARIABLES:
        frame[wo.parent_rolling_column(v, horizon)] = rolling[v]
    return pd.concat([frame, block], axis=1)


def test_prefit_gate_accepts_built_inputs_and_rejects_tampering():
    grid = make_grid()
    keys = keys_for([(1, 2022, 6), (2, 2022, 8), (1, 2023, 1)])
    history1 = np.array([3.0, 1.0, np.nan])
    rolling = {P: np.array([1.0, 2.0, 3.0]), T: np.array([4.0, np.nan, 6.0])}
    block, ledger = build(grid, keys, 3, history1=history1, rolling=rolling)
    frame = _frame_with(block, ledger, keys, history1, rolling, 3)
    wo.assert_oracle_inputs(frame, ledger, 3, wo.B6_ARM)
    bad = frame.copy()
    bad.loc[1, f"oracle_{P}__wmean_o1_o3__x__crisis_history_1_ge3"] = 7.0
    with pytest.raises(ValueError, match="declared function"):
        wo.assert_oracle_inputs(bad, ledger, 3, wo.B6_ARM)
    wo.assert_oracle_inputs(bad, ledger, 3, wo.RAW_ARM)  # raw arm does not fit B6 columns
    shifted = ledger.copy()
    shifted["future_obs_last_ord"] += 1
    with pytest.raises(ValueError, match="weather window"):
        wo.assert_oracle_inputs(frame, shifted, 3, wo.RAW_ARM)
    future_history = ledger.copy()
    future_history.loc[0, "history_1_source_ord"] = 2022 * 12 + 5  # target month itself
    with pytest.raises(ValueError, match="after min"):
        wo.assert_oracle_inputs(frame, future_history, 3, wo.RAW_ARM)
    counts = ledger.copy()
    counts.loc[0, f"{P}__future_finite_months"] = 2
    with pytest.raises(ValueError, match="finite-month counts"):
        wo.assert_oracle_inputs(frame, counts, 3, wo.RAW_ARM)


def test_infinite_source_values_are_rejected():
    def inf(g):
        g.values[T][1, 3] = np.inf
    with pytest.raises(ValueError, match="non-finite"):
        wo.assert_finite_or_missing(make_grid(fill=inf))
