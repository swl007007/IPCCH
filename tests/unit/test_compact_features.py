import numpy as np
import pandas as pd
import pytest

from ipcch import climate2015_features as cf
from ipcch import compact_features as cpf
from ipcch import origin_safe as osf
from ipcch import weather_oracle as wo

STATIC = ["AEZ_32000", "AEZ_34000", "AEZ_36000", "AEZ_38000", "AEZ_42000", "AEZ_7000", "crop", "elevation", "market_access",
          "popdensity", "range", "ruggedness", "slope", "AEZ_10000", "AEZ_12000", "AEZ_17000", "AEZ_19000", "AEZ_20000",
          "AEZ_25000", "AEZ_28000", "AEZ_30000", "AEZ_31000", "AEZ_33000", "AEZ_35000", "AEZ_4000", "AEZ_40000",
          "AEZ_43000", "AEZ_9000", "coastline_dist"]
IDENT = ["lat", "lon", *(f"month_{m}" for m in range(1, 13)), *(f"year_{y}" for y in range(2014, 2027))]
# parent order: static, old dynamic families, identifier, history, IDP
PARENT = STATIC + ["GPP_mean__l12", "prcp_z_month_ensmean__l3_s3"] + IDENT + list(osf.HISTORY_FEATURES) + list(osf.IDP_FEATURES)


# --------------------------------------------------------------------------- schema


@pytest.mark.parametrize("arm,horizon,count", [(cpf.BASELINE_ARM, 0, 296), (cpf.BASELINE_ARM, 12, 296),
                                               (cpf.ORACLE_ARM, 3, 302), (cpf.ORACLE_ARM, 6, 308), (cpf.ORACLE_ARM, 12, 308)])
def test_run_schema_matches_frozen_contract(arm, horizon, count):
    features = cpf.run_features(PARENT, arm, horizon)
    assert len(features) == count
    assert features[:29] == STATIC and features[262:289] == IDENT and features[289:296] == list(osf.HISTORY_FEATURES + osf.IDP_FEATURES)
    assert features[29:262] == cpf.dynamic_features()
    if arm == cpf.ORACLE_ARM:
        assert features[296:] == wo.raw_features(horizon)
    assert not osf.forbidden_features(features)
    banned = ("ndvi", "FAO_price", "food_inflation_wb", "neighbor3", "__x__", "_asof12", "_s3", "__l12")
    assert not [f for f in features if any(b in f for b in banned)]


def test_family_counts():
    dyn = cpf.dynamic_features()
    assert len(dyn) == 233
    assert sum(f.endswith(("__value_at_origin", "__sd12_at_origin")) or ("__ma" in f and "__hist_same_month_z" not in f) for f in dyn) == 120
    assert sum("__hist_same_month_z" in f for f in dyn) == 56
    assert sum("_stress__" in f for f in dyn) == 28
    assert sum(f.startswith("gs_last") for f in dyn) == 29


def test_cross_version_and_horizon_combinations_are_rejected():
    with pytest.raises(ValueError, match="has no run"):
        cpf.run_features(PARENT, cpf.ORACLE_ARM, 0)
    with pytest.raises(ValueError, match="has no run"):
        cpf.run_features(PARENT, wo.RAW_ARM, 3)
    with pytest.raises(ValueError, match="frozen contract"):
        cpf.run_features(STATIC[1:2] + STATIC[:1] + STATIC[2:] + PARENT[29:], cpf.BASELINE_ARM, 3)
    with pytest.raises(ValueError, match="history/IDP"):
        cpf.background_groups(PARENT[:-7] + ["overall_phase_history_2", "overall_phase_history_1", *PARENT[-5:]])


# --------------------------------------------------------------------------- ordinary recipes


def test_ordinary_value_ma_sd_minimums_and_absent_current_month():
    x = np.array([[1.0, np.nan, 3.0, np.nan, np.nan, 6.0, 7.0, 8.0, np.nan, 10.0, 11.0, 12.0]])
    arr = dict(cpf.ordinary_arrays("s", x))
    np.testing.assert_array_equal(arr["s__value_at_origin"], x)
    ma3 = arr["s__ma3_at_origin"][0]
    assert np.isnan(ma3[1]) and ma3[2] == 2.0  # 1 valid -> NaN; months 0..2 hold 1 and 3
    assert np.isnan(ma3[4])  # months 2..4 hold only 3
    assert ma3[8] == 7.5  # current month missing, window 6..8 holds 7, 8 (>= 2)
    ma6 = arr["s__ma6_at_origin"][0]
    assert np.isnan(ma6[4]) and ma6[5] == pytest.approx((1 + 3 + 6) / 3)
    sd = arr["s__sd12_at_origin"][0]
    assert np.isnan(sd[6])  # 1, 3, 6, 7: four valid values < 6
    assert sd[9] == pytest.approx(np.std([1, 3, 6, 7, 8, 10], ddof=1))
    valid = x[0, :11][~np.isnan(x[0, :11])]
    assert sd[10] == pytest.approx(np.std(valid, ddof=1))
    assert np.isnan(sd[5])  # 4 valid values < 6


def test_sd12_needs_six_values():
    x = np.array([[1.0, 2.0, 4.0, 8.0, 16.0, np.nan, 32.0]])
    sd = dict(cpf.ordinary_arrays("s", x))["s__sd12_at_origin"][0]
    assert np.isnan(sd[5]) and sd[6] == pytest.approx(np.std([1, 2, 4, 8, 16, 32], ddof=1))


# --------------------------------------------------------------------------- same-month z


def _yearly(values_by_year, month=0, first_year=2015):
    """One area; ``values_by_year`` placed in calendar month ``month`` of consecutive years, other months NaN."""
    n_years = len(values_by_year)
    x = np.full((1, n_years * 12), np.nan)
    for y, v in enumerate(values_by_year):
        x[0, y * 12 + month] = v
    return x, first_year * 12


def test_same_month_z_hand_calculated_strictly_earlier_years_and_two_history_minimum():
    x, first = _yearly([1.0, 3.0, 8.0, 2.0])
    z = cpf.same_month_z(x, first)[0, ::12]
    assert np.isnan(z[0]) and np.isnan(z[1])  # 0 and 1 prior values
    assert z[2] == pytest.approx((8 - 2) / np.std([1, 3], ddof=1))
    assert z[3] == pytest.approx((2 - 4) / np.std([1, 3, 8], ddof=1))  # its own year excluded


def test_same_month_z_exact_constant_decimal_history_is_missing_but_nearby_values_are_not():
    x, first = _yearly([0.1, 0.1, 0.1, 0.1, 0.7])
    mean, std, _ = cf.same_month_history(x, first)
    assert std[0, 36] > 0  # three prior 0.1 values: float rounding leaves an SD near 1.7e-17
    assert np.isfinite(cf.safe_divide(0.1 - mean[0, 36], std[0, 36]))  # a spurious finite z the exact guard removes
    z = cpf.same_month_z(x, first)[0, ::12]
    assert np.isnan(z).all()
    near, first = _yearly([0.1, 0.1000000001, 0.1, 0.7])
    z_near = cpf.same_month_z(near, first)[0, ::12]
    assert np.isfinite(z_near[2]) and np.isfinite(z_near[3])
    assert z_near[3] == pytest.approx((0.7 - np.mean([0.1, 0.1000000001, 0.1])) / np.std([0.1, 0.1000000001, 0.1], ddof=1))
    zeros, first = _yearly([0.0, 0.0, 5.0])
    assert np.isnan(cpf.same_month_z(zeros, first)[0, 24])
    with_gap, first = _yearly([2.0, np.nan, 2.0, 9.0])  # missing year does not break the constant test
    assert np.isnan(cpf.same_month_z(with_gap, first)[0, 36])


def _exact_mean_sd(values):
    from fractions import Fraction

    vals = [Fraction(v) for v in values]
    mean = sum(vals) / len(vals)
    var = sum((v - mean) ** 2 for v in vals) / (len(vals) - 1)
    return mean, float(var) ** 0.5


def _exact_z(prior, current):
    from fractions import Fraction

    mean, sd = _exact_mean_sd(prior)
    return float(Fraction(current) - mean) / sd


@pytest.mark.parametrize("prior,current", [
    ([30.0] * 7 + [29.99999999999999], 29.99999999999999),  # area 101270 cdd November history (first build: -2.65)
    ([30.000000000000004] * 5 + [30.00000000000001], 30.00000000000001),  # area 101274 analogue
    ([31.000000000000004] * 7 + [31.0, 29.72512680866888, 31.0, 31.0], 28.590480249386623),  # area 101214 January
])
def test_same_month_z_is_accurate_for_near_constant_real_histories(prior, current):
    x, first = _yearly(prior + [current])
    z = cpf.same_month_z(x, first)[0, 12 * len(prior)]
    want = _exact_z(prior, current)
    assert np.isfinite(z) and z == pytest.approx(want, rel=1e-12)
    mean, std, _ = cf.same_month_history(x, first)  # the uncentred float mean of the old helper drifts here
    legacy = (current - mean[0, 12 * len(prior)]) / std[0, 12 * len(prior)]
    assert not legacy == pytest.approx(want, rel=1e-6) or len(set(prior)) > 2


@pytest.mark.parametrize("preceding,value", [
    ([251.15313, 261.57843, 265.18115, 267.13721, 264.16357000000005, 266.4865], 268.27392),  # WFP area 4588 to 2024-11
    ([3412.2, 3412.2, 14958.0, 26722.3333333, 26722.3333333, 3412.2], 2762.0),  # GPP area 101055 to 2024-09
])
def test_constant_window_after_varying_values_has_exact_zero_sd_and_exact_mean(preceding, value):
    x = np.array([preceding + [value] * 12])
    assert dict(cpf.ordinary_arrays("s", x))["s__sd12_at_origin"][0, -1] == 0.0
    assert dict(cpf.ordinary_arrays("s", x))["s__ma12_at_origin"][0, -1] == value
    assert dict(cpf.ordinary_arrays("s", x))["s__ma3_at_origin"][0, -1] == value


def test_trailing_mean_has_no_residue_after_a_huge_value_leaves_the_window():
    from fractions import Fraction

    rng = np.random.default_rng(11)
    tail = rng.normal(size=30)
    x = np.array([[-9.494144e14, 3.2e14, *tail]])
    got = cpf.trailing(x, 12, 6, "mean")[0]
    for j in range(13, x.shape[1]):
        want = float(sum(Fraction(v) for v in x[0, j - 11 : j + 1]) / 12)
        assert got[j] == pytest.approx(want, rel=1e-12, abs=1e-15)
    sd = cpf.trailing(x, 12, 6, "std")[0, -1]
    assert sd == pytest.approx(_exact_mean_sd(x[0, -12:])[1], rel=1e-12)


def test_z_moving_average_is_mean_of_monthly_z_not_z_of_mean():
    rng = np.random.default_rng(3)
    x = rng.normal(size=(1, 72)) * np.arange(1, 73)
    arr = dict(cpf.z_arrays("s", x, 2015 * 12))
    z = cpf.same_month_z(x, 2015 * 12)
    j = 70
    assert arr["s__hist_same_month_z_ma3_at_origin"][0, j] == pytest.approx(np.nanmean(z[0, j - 2 : j + 1]))
    assert arr["s__hist_same_month_z_ma12_at_origin"][0, j] == pytest.approx(np.nanmean(z[0, j - 11 : j + 1]))
    ma3_raw = cf.rolling(x, 3, 2, "mean")
    z_of_ma = cpf.same_month_z(ma3_raw, 2015 * 12)
    assert arr["s__hist_same_month_z_ma3_at_origin"][0, j] != pytest.approx(z_of_ma[0, j])


def test_excluded_standardized_sources_have_no_second_z():
    dyn = cpf.dynamic_features()
    for v in ("prcp_z_month_ensmean", "sm_z_month_ensmean", "spi03_month_ensmean", "spei03_month_ensmean",
              "bbg_oilgas__composite_mean", "event_count_violence"):
        assert f"{v}__hist_same_month_z_at_origin" not in dyn
        assert f"{v}__value_at_origin" in dyn


# --------------------------------------------------------------------------- stress


def _interim(values: dict, n: int, first_ord: int = 2015 * 12) -> cf.Grid:
    base = {s: np.full((1, n), np.nan) for s in cpf.INTERIM_SOURCES}
    for k, v in values.items():
        base[k] = np.asarray(v, dtype=float)[None, :]
    return cf.Grid(np.array([1]), first_ord, n, base)


def _climate(n: int, first_ord: int = 2015 * 12) -> cf.Grid:
    return cf.Grid(np.array([1]), first_ord, n, {v: np.full((1, n), np.nan) for v in cpf.CLIMATE_SOURCES})


def test_inherited_stress_rules_keep_old_missing_comparator_behaviour():
    n = 26
    gpp = np.full(n, 10.0)
    gpp[12] = 8.0  # year-ago missing below -> false 0 even though below 0.9 * anything
    gpp[0] = np.nan
    gpp[13] = 8.99  # < 0.9 * 10
    gpp[14] = 9.0  # boundary: not < 9.0
    gpp[20] = np.nan
    wfp = np.full(n, 100.0)
    wfp[3] = 0.0  # zero year-ago denominator for month 15
    wfp[15] = 150.0
    wfp[16] = 110.0  # +10% exactly: not > 0.10
    wfp[17] = 110.1
    wfp[5] = np.nan  # missing year-ago for month 17 -> 0
    wfp[18] = 111.0
    nino = np.zeros(n)
    nino[[1, 2, 3]] = [0.5, -0.51, np.nan]
    violence = np.zeros(n)
    violence[[4, 5]] = [1.0, np.nan]
    grid = _interim({"GPP_mean": gpp, "WFP_Price": wfp, "nino34_anom": nino, "event_count_violence": violence}, n)
    signals = {k: v[1][0] for k, v in cpf.stress_signal_arrays(grid, _climate(n)).items()}
    g = signals["GPP_mean__vegetation_stress"]
    assert g[12] == 0.0 and g[13] == 1.0 and g[14] == 0.0 and np.isnan(g[20]) and np.isnan(g[0])
    w = signals["WFP_Price__price_shock_stress"]
    assert w[15] == 0.0 and w[16] == 0.0 and w[17] == 0.0 and w[18] == 1.0 and np.isnan(w[5])
    e = signals["nino34_anom__enso_stress"]
    assert e[1] == 0.0 and e[2] == 1.0 and np.isnan(e[3])
    v = signals["event_count_violence__nonzero_stress"]
    assert v[4] == 1.0 and np.isnan(v[5]) and v[6] == 0.0


def test_stress_summaries_months_since_through_missing_and_run_breaks():
    s = np.array([[1.0, 0.0, np.nan, 1.0, 1.0, np.nan, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0]])
    arr = dict(cpf.stress_arrays("x", s))
    since = arr["x__months_since_at_origin"][0]
    assert since[0] == 0 and since[2] == 2 and since[5] == 1 and since[11] == 5
    assert np.isnan(dict(cpf.stress_arrays("x", np.array([[np.nan, 0.0, 0.0]])))["x__months_since_at_origin"][0]).all()
    run = arr["x__longest_run12_at_origin"][0]
    assert np.isnan(run[6]) and run[7] == 2 and run[11] == 2  # six valid months from index 7; NaN at 5 breaks 3-4 from 6
    share = arr["x__share12_at_origin"][0]
    assert np.isnan(share[6]) and share[7] == pytest.approx(4 / 6)
    assert arr["x__any12_at_origin"][0][11] == 1.0


# --------------------------------------------------------------------------- D16, alignment and leakage


def test_source_at_origin_is_kept_without_a_carrier_row():
    """Area panel ends at 2025-10; the old carrier O+12 = 2026-10 does not exist, the source at O does."""
    rows = [(1, 2024 + (m // 12), m % 12 + 1) for m in range(0, 22)]  # 2024-01 .. 2025-10
    panel = pd.DataFrame(rows, columns=list(osf.KEYS))
    for s in cpf.INTERIM_SOURCES[:7]:
        panel[s] = np.arange(len(panel), dtype=float)
    members = {g: [f"bbg_{g}_a", f"bbg_{g}_b"] for g in ("bbg_staple_food", "bbg_oilgas", "bbg_soybean_oil", "bbg_global_food")}
    for cols in members.values():
        panel[cols[0]] = 2.0
        panel[cols[1]] = np.nan
    grid = cpf.interim_grid(panel, members)
    keys = pd.DataFrame({"area_id": [1, 1], "year": [2025, 2026], "month": [10, 1]})
    block = cpf.monthly_block(grid, _climate(12, 2025 * 12), keys, [0, 3])
    assert block[0].loc[0, "nightlight_mean__value_at_origin"] == 21.0
    assert block[0].loc[0, "nightlight_mean__ma3_at_origin"] == 20.0
    assert block[3].loc[1, "WFP_Price__value_at_origin"] == 21.0  # 2026-01 - 3 = 2025-10
    assert np.isnan(block[0].loc[1, "WFP_Price__value_at_origin"])  # 2026-01 genuinely absent from the source
    assert block[0].loc[0, "bbg_oilgas__composite_mean__value_at_origin"] == 2.0  # mean of non-missing members


@pytest.mark.parametrize("horizon", [0, 3, 6, 12])
def test_monthly_block_reads_the_calendar_origin_and_nothing_later(horizon):
    rng = np.random.default_rng(horizon)
    n, first = 60, 2020 * 12
    interim = cf.Grid(np.array([1, 2]), first, n, {s: rng.normal(size=(2, n)) + 5 for s in cpf.INTERIM_SOURCES})
    climate = cf.Grid(np.array([1, 2]), first, n, {s: rng.normal(size=(2, n)) for s in cpf.CLIMATE_SOURCES})
    keys = pd.DataFrame({"area_id": [1, 2], "year": [2023, 2024], "month": [7, 2]})
    target = osf.month_ord(keys["year"], keys["month"])
    base = cpf.monthly_block(interim, climate, keys, [horizon])[horizon]
    for i in range(2):
        col = target[i] - horizon - first
        assert base.loc[i, "GPP_mean__value_at_origin"] == interim.values["GPP_mean"][i, col]
        assert base.loc[i, "tmean_anom_month_ensmean__value_at_origin"] == climate.values["tmean_anom_month_ensmean"][i, col]
    cutoff = int((target - horizon).max()) - first
    late = {k: v.copy() for k, v in interim.values.items()}
    late_c = {k: v.copy() for k, v in climate.values.items()}
    for arr in (*late.values(), *late_c.values()):
        arr[:, cutoff + 1 :] += 1000.0
    after = cpf.monthly_block(cf.Grid(interim.area_ids, first, n, late), cf.Grid(climate.area_ids, first, n, late_c), keys, [horizon])[horizon]
    pd.testing.assert_frame_equal(base, after)


# --------------------------------------------------------------------------- growing seasons


def _seasons():
    rows = [  # admin, season_year, season, start, end_exclusive
        (1, 2020, "s1", "2020-03-01", "2020-07-01"), (1, 2020, "s2", "2020-08-01", "2020-10-01"),  # s1 longer
        (1, 2021, "s1", "2021-03-01", "2021-05-01"), (1, 2021, "s2", "2021-02-01", "2021-05-01"),  # tied end, s2 starts earlier
        (2, 2020, "s1", "2020-01-01", "2020-03-01"), (2, 2020, "s2", "2020-04-01", "2020-05-31"),  # equal durations (60 d)
        (3, 2020, "s1", "2019-11-15", "2020-02-01"),  # unpaired
    ]
    s = pd.DataFrame(rows, columns=["admin_code", "season_year", "season", "gs_start_date", "gs_end_date_exclusive"])
    for i, m in enumerate(cpf.SEASON_METRICS):
        s[m] = np.arange(len(s), dtype=float) + 10 * i
    s["ndvi_anom_gs_ensmean"] = -1.0  # present in the source, not a compact input
    return s


def test_major_flag_by_calendar_duration():
    flags = cpf.season_major_flags(_seasons()).tolist()
    assert flags[:2] == [1.0, 0.0]
    assert flags[2:4] == [0.0, 1.0]  # Mar-May 61 d vs Feb-May 89 d
    assert np.isnan(flags[4]) and np.isnan(flags[5]) and np.isnan(flags[6])


def test_completed_seasons_exclusive_end_ties_and_major_from_the_same_record():
    s = _seasons()
    # ords are year * 12 + month - 1: 2020-05, 2020-06, 2021-04, 2020-06, 2020-01, 2021-01
    keys = pd.DataFrame({"area_id": [1, 1, 1, 2, 3, 4], "o": [2020 * 12 + 4, 2020 * 12 + 5, 2021 * 12 + 3, 2020 * 12 + 5, 2020 * 12, 2021 * 12]})
    feats, ledger = cpf.completed_seasons(s, keys["area_id"], keys["o"])
    m = cpf.SEASON_METRICS[0]
    # O=2020-06: first day of O+1 = 2020-07-01 = exclusive end of s1 -> completed (boundary inclusive)
    assert ledger.loc[1, "gs_last1_season"] == "s1" and feats.loc[1, cpf.MAJOR] == 1.0
    assert feats.loc[1, "gs_last1__months_since_end_at_origin"] == 0  # ends June 2020
    assert np.isnan(feats.loc[0, f"gs_last1__{m}__at_origin"]) and np.isnan(feats.loc[0, cpf.MAJOR])  # O=2020-05: nothing complete
    # O=2021-04: both 2021 seasons end 2021-05-01; the later-starting s1 is latest, s2 second
    assert ledger.loc[2, "gs_last1_season"] == "s1" and ledger.loc[2, "gs_last2_season"] == "s2"
    assert feats.loc[2, cpf.MAJOR] == 0.0 and feats.loc[2, f"gs_last1__{m}__at_origin"] == 2.0
    assert np.isnan(feats.loc[3, cpf.MAJOR]) and ledger.loc[3, "gs_last1_season"] == "s2"  # tie in duration
    assert np.isnan(feats.loc[4, cpf.MAJOR]) and feats.loc[4, f"gs_last1__{m}__at_origin"] == 6.0  # unpaired season
    assert feats.loc[5].isna().all()  # area without seasons
    legacy = cf.last_completed_seasons(s, keys["area_id"].to_numpy(), keys["o"].to_numpy())
    for k in (1, 2):
        for metric in cf.SEASONAL_VARIABLES:
            if metric in cpf.SEASON_METRICS:
                np.testing.assert_array_equal(feats[f"gs_last{k}__{metric}__at_origin"], legacy[f"gs_last{k}__{metric}"])
        np.testing.assert_array_equal(feats[f"gs_last{k}__months_since_end_at_origin"], legacy[f"gs_last{k}__months_since_end"])


def test_season_ledger_gate_rejects_a_changed_major_or_age():
    s = _seasons()
    frame = pd.DataFrame({"area_id": [1, 1], "year": [2021, 2021], "month": [7, 8]})
    feats, ledger = cpf.completed_seasons(s, frame["area_id"], osf.month_ord(frame["year"], frame["month"]) - 3)
    ledger.insert(0, "area_id", frame["area_id"].to_numpy())
    frame = pd.concat([frame, feats], axis=1)
    assert cpf.assert_season_ledger(frame, ledger, 3) == {"rows": 2}
    bad = frame.copy()
    bad.loc[0, cpf.MAJOR] = 1.0
    with pytest.raises(ValueError, match="is_major"):
        cpf.assert_season_ledger(bad, ledger, 3)
    with pytest.raises(ValueError, match="align"):
        cpf.assert_season_ledger(frame, ledger, 6)


# --------------------------------------------------------------------------- raw oracle


def test_raw_oracle_window_and_ledger_gate():
    rng = np.random.default_rng(5)
    grid = cf.Grid(np.array([1]), 2020 * 12, 48, {v: rng.normal(size=(1, 48)) for v in wo.ORACLE_VARIABLES})
    keys = pd.DataFrame({"area_id": [1], "year": [2022], "month": [6]})
    origin = 2022 * 12 + 5 - 12
    block, ledger = cpf.raw_oracle_block(grid, keys, 12)
    assert list(block.columns) == wo.raw_features(12)
    for k in range(1, 7):
        assert block.loc[0, wo.raw_name("prcp_anom_month_ensmean", k)] == grid.values["prcp_anom_month_ensmean"][0, origin + k - grid.first_ord]
    late = {v: a.copy() for v, a in grid.values.items()}
    for a in late.values():
        a[:, origin + 7 - grid.first_ord :] += 50.0  # O+7..: must not matter at H12
        a[:, : origin + 1 - grid.first_ord] -= 50.0  # <= O: not part of the raw oracle
    again, _ = cpf.raw_oracle_block(cf.Grid(grid.area_ids, grid.first_ord, grid.n_months, late), keys, 12)
    pd.testing.assert_frame_equal(block, again)
    frame = pd.concat([keys, block], axis=1)
    assert cpf.assert_oracle_ledger(frame, ledger, 12) == {"rows": 1}
    frame.loc[0, wo.raw_name("tmean_anom_month_ensmean", 6)] = np.nan
    with pytest.raises(ValueError, match="finite-month"):
        cpf.assert_oracle_ledger(frame, ledger, 12)
    with pytest.raises(ValueError, match="horizon"):
        cpf.assert_oracle_ledger(pd.concat([keys, block], axis=1), ledger, 6)
