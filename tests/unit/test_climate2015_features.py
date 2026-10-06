import math

import numpy as np
import pandas as pd
import pytest

from ipcch import climate2015_features as cf


def _grid(n_areas=4, n_months=60, first_ord=2015 * 12, seed=0, nan_share=0.05):
    rng = np.random.default_rng(seed)
    values = {}
    for v in cf.MONTHLY_VARIABLES:
        x = rng.normal(size=(n_areas, n_months))
        x[rng.random(x.shape) < nan_share] = np.nan
        values[v] = x
    return cf.Grid(np.arange(n_areas), first_ord, n_months, values)


@pytest.mark.parametrize("anchor,scope_block", [(12, False), (0, True), (3, True), (6, True)])
def test_features_never_read_after_anchor(anchor, scope_block):
    grid = _grid()
    j = 45  # target month column
    base = dict(cf.monthly_feature_stream(grid, anchor, scope_block, None, None))
    perturbed = cf.Grid(grid.area_ids, grid.first_ord, grid.n_months, {k: v.copy() for k, v in grid.values.items()})
    for v in perturbed.values.values():
        v[:, j - anchor + 1 :] = 99.0  # months later than t - anchor
    after = dict(cf.monthly_feature_stream(perturbed, anchor, scope_block, None, None))
    assert base.keys() == after.keys()
    for name in base:
        np.testing.assert_array_equal(base[name][:, j], after[name][:, j], err_msg=name)


def test_feature_names_follow_upstream_pattern():
    grid = _grid()
    asof12 = [n for n, _ in cf.monthly_feature_stream(grid, 12, False, None, None)]
    scope = [n for n, _ in cf.monthly_feature_stream(grid, 3, True, None, None)]
    v = "prcp_z_month_ensmean"
    assert {f"{v}__l12", f"{v}__l24", f"{v}__roll3_mean_asof12", f"{v}__l12_ratio_l24", f"{v}__accel6_vs_prev6_asof12", f"{v}__hist_same_month_pctile_l12"} <= set(asof12)
    assert {f"{v}__l3_s3", f"{v}__roll12_mean_asof3_s3", f"{v}__slope12_asof3_s3", f"{cf.DEFICIT}__share12_asof3_s3"} <= set(scope)
    assert all(n.endswith("_s3") for n in scope)
    per_var = 21 * len(cf.MONTHLY_VARIABLES) + 3 * 4
    assert len(asof12) == per_var


def test_stress_threshold_boundaries():
    x = {v: np.zeros((1, 4)) for v in cf.MONTHLY_VARIABLES}
    x["spi03_month_ensmean"][0] = [-1.0, -0.999, np.nan, -2.0]
    x["tmean_anom_month_ensmean"][0] = [1.0, 0.999, np.nan, 3.0]
    x["evi_anom_month_ensmean"][0] = [-0.015, -0.0149, np.nan, -1.0]
    sig = cf.stress_signals(cf.Grid(np.array([0]), 0, 4, x))
    for name in (cf.DEFICIT, cf.HOT, cf.VEGETATION):
        np.testing.assert_array_equal(sig[name][0], [1.0, 0.0, np.nan, 1.0])


def _months_since_reference(values):
    out, last = [], math.nan
    for value in values:
        if value == 1:
            last = 0
            out.append(0.0)
        elif not math.isnan(last):
            last += 1
            out.append(last)
        else:
            out.append(math.nan)
    return np.array(out, dtype=float)


def test_spell_helpers_match_upstream_loops():
    rng = np.random.default_rng(1)
    s = rng.choice([0.0, 1.0, np.nan], p=[0.6, 0.3, 0.1], size=(5, 40))
    np.testing.assert_array_equal(cf.months_since(s), np.vstack([_months_since_reference(r) for r in s]))

    def longest(values):
        best = cur = 0
        for v in values:
            cur = cur + 1 if v == 1 else 0
            best = max(best, cur)
        return float(best)

    ref = pd.DataFrame(s.T).rolling(12, min_periods=6).apply(longest, raw=True).to_numpy().T
    np.testing.assert_array_equal(cf.longest_run(s), ref)


def test_same_month_history_uses_only_prior_years():
    x = np.arange(36, dtype=float).reshape(1, 36)  # 3 years, value = month index
    mean, std, rank = cf.same_month_history(x, first_ord=2015 * 12)
    assert np.isnan(mean[0, :12]).all()
    assert mean[0, 12] == 0.0 and mean[0, 24] == 6.0  # Jan: prior Januaries 0 ; 0,12
    assert np.isnan(std[0, 12]) and std[0, 24] == pytest.approx(np.std([0, 12], ddof=1))
    assert rank[0, 24] == 1.0


def _seasons():
    rows = []
    for (start, end) in [("2020-03-01", "2020-07-01"), ("2020-09-01", "2021-01-01"), ("2021-03-01", "2021-07-01")]:
        row = {"admin_code": 7, "gs_start_date": start, "gs_end_date_exclusive": end}
        row.update({v: float(pd.Timestamp(end).month) for v in cf.SEASONAL_VARIABLES})
        rows.append(row)
    return pd.DataFrame(rows)


def test_season_completion_boundary_and_order():
    seasons = _seasons()
    origins = np.array([cf.month_ord(2021, 6), cf.month_ord(2021, 5), cf.month_ord(2020, 12), cf.month_ord(2020, 5)])
    out = cf.last_completed_seasons(seasons, np.full(4, 7), origins)
    v = cf.SEASONAL_VARIABLES[0]
    # origin 2021-06: season ending exclusive 2021-07-01 (last day 2021-06-30) is complete
    assert out.loc[0, f"gs_last1__{v}"] == 7.0 and out.loc[0, f"gs_last2__{v}"] == 1.0
    assert out.loc[0, "gs_last1__months_since_end"] == 0
    # origin 2021-05: that season is not yet complete
    assert out.loc[1, f"gs_last1__{v}"] == 1.0 and out.loc[1, "gs_last1__months_since_end"] == 5
    assert out.loc[2, f"gs_last1__{v}"] == 1.0 and out.loc[2, f"gs_last2__{v}"] == 7.0
    # origin 2020-05: nothing complete
    assert np.isnan(out.loc[3, f"gs_last1__{v}"]) and np.isnan(out.loc[3, "gs_last1__months_since_end"])


def test_tied_season_end_dates_keep_start_order():
    # many areas with s1/s2 sharing an end date each year; an unstable sort must not reorder ties
    rows = []
    for area in range(300):
        for year in range(2015, 2027):
            for k, start_month in enumerate((1, 3)):
                row = {"admin_code": area, "gs_start_date": f"{year}-{start_month:02d}-01", "gs_end_date_exclusive": f"{year}-07-01"}
                row.update({v: float(year * 10 + k) for v in cf.SEASONAL_VARIABLES})
                rows.append(row)
    seasons = pd.DataFrame(rows).sample(frac=1.0, random_state=0)
    areas = np.repeat(np.arange(300), 3)
    origins = np.tile([cf.month_ord(2021, 6), cf.month_ord(2021, 9), cf.month_ord(2020, 8)], 300)
    out = cf.last_completed_seasons(seasons, areas, origins)
    v = cf.SEASONAL_VARIABLES[0]
    expected_last1 = np.tile([20211.0, 20211.0, 20201.0], 300)  # later-starting season of the tied pair
    expected_last2 = expected_last1 - 1.0  # its tie partner
    np.testing.assert_array_equal(out[f"gs_last1__{v}"].to_numpy(), expected_last1)
    np.testing.assert_array_equal(out[f"gs_last2__{v}"].to_numpy(), expected_last2)


def test_old_climate_detector_keeps_gpp():
    assert cf.is_old_climate_column("Rainf_f_tavg_mean__l12")
    assert cf.is_old_climate_column("nino34_anom__enso_stress__share12_asof12__x__Rainf_f_tavg_mean__deficit_stress__share12_asof12")
    assert cf.is_old_climate_column("neighbor3_mean__Rainf_f_tavg_mean__deficit_stress__share12_asof0_s0")
    assert cf.is_old_climate_column("EVI_mean__vegetation_stress__any12_asof12")
    assert not cf.is_old_climate_column("GPP_mean__vegetation_stress__any12_asof12")
    assert not cf.is_old_climate_column("nino34_anom__l12")


def test_ragged_grid_requires_contiguous_months():
    ok = pd.DataFrame({"area_id": [1, 1, 2], "year": [2015, 2015, 2015], "month": [1, 2, 1], "x": [1.0, 2.0, 3.0]})
    grid = cf.Grid.from_long(ok, ["x"], require_complete=False)
    assert np.isnan(grid.values["x"][1, 1])
    with pytest.raises(ValueError):
        cf.Grid.from_long(ok, ["x"], require_complete=True)
    gap = pd.DataFrame({"area_id": [1, 1], "year": [2015, 2015], "month": [1, 3], "x": [1.0, 2.0]})
    with pytest.raises(ValueError):
        cf.Grid.from_long(gap, ["x"], require_complete=False)
