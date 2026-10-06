import numpy as np
import pandas as pd
import pytest

from ipcch import climate2015_features as cf
from ipcch import origin_safe as osf


def obs_frame(records):
    """records: (area_id, year, month, phase)"""
    df = pd.DataFrame(records, columns=["area_id", "year", "month", "overall_phase"])
    return osf.valid_phase_observations(df)


def rows(records):
    return pd.DataFrame(records, columns=["area_id", "year", "month"])


OBS = obs_frame([(1, 2020, 1, 1), (1, 2020, 4, 2), (1, 2020, 7, 3), (1, 2020, 10, 4), (2, 2020, 10, 5)])


def history_values(horizon, area=1, year=2020, month=10):
    block, ledger = osf.build_safe_history(OBS, rows([(area, year, month)]), horizon)
    return block.iloc[0, :3].to_numpy(float), ledger


def test_h0_excludes_target_month_and_h3_includes_origin_month():
    h0, _ = history_values(0)
    np.testing.assert_array_equal(h0, [3, 2, 1])  # Oct 2020 itself is excluded
    h3, _ = history_values(3)
    np.testing.assert_array_equal(h3, [3, 2, 1])  # origin Jul 2020 is inclusive
    h6, _ = history_values(6)
    np.testing.assert_allclose(h6, [2, 1, np.nan])
    h12, ledger = history_values(12, month=10, year=2021)
    np.testing.assert_array_equal(h12, [4, 3, 2])  # origin Oct 2020 inclusive at H=12
    assert ledger["label_cutoff_ord"].iloc[0] == 2020 * 12 + 9


def test_irregular_observations_missing_history_and_area_isolation():
    sparse = obs_frame([(1, 2019, 2, 2), (1, 2020, 9, 3), (2, 2020, 8, 5)])
    block, ledger = osf.build_safe_history(sparse, rows([(1, 2020, 10), (3, 2020, 10)]), 0)
    np.testing.assert_allclose(block.iloc[0, :3].to_numpy(float), [3, 2, np.nan])
    assert block.iloc[1].isna().all()  # area 3 has no observations; area 2 is never borrowed
    assert ledger["history_1_source_ord"].iloc[0] == 2020 * 12 + 8
    assert ledger["history_2_source_ord"].iloc[0] == 2019 * 12 + 1
    np.testing.assert_allclose(block.iloc[0, 3:].to_numpy(float), [1, np.nan])


def test_duplicate_or_invalid_labels_fail():
    with pytest.raises(ValueError):
        osf.valid_phase_observations(pd.DataFrame({"area_id": [1, 1], "year": [2020, 2020], "month": [1, 1], "overall_phase": [1, 2]}))
    bad = OBS.copy()
    bad.loc[0, "overall_phase"] = 0
    with pytest.raises(ValueError):
        osf.build_safe_history(bad, rows([(1, 2020, 10)]), 0)


def test_post_cutoff_label_perturbation_cannot_change_history():
    target = rows([(1, 2020, 10)])
    base, _ = osf.build_safe_history(OBS, target, 3)
    perturbed = OBS.copy()
    late = perturbed["ord"] > 2020 * 12 + 6  # after origin Jul 2020
    perturbed.loc[late, "overall_phase"] = 5
    after, _ = osf.build_safe_history(perturbed, target, 3)
    pd.testing.assert_frame_equal(base, after)
    early = perturbed.copy()
    early.loc[early["ord"] == 2020 * 12 + 6, "overall_phase"] = 5
    changed, _ = osf.build_safe_history(early, target, 3)
    assert changed.iloc[0, 0] == 5


def test_reference_check_detects_tampered_ledger_and_gate_rejects_bad_provenance():
    frame = rows([(1, 2020, 10), (1, 2021, 1), (2, 2021, 1)])
    block, ledger = osf.build_safe_history(OBS, frame, 3)
    stats = osf.reference_history_check(OBS, ledger, block)
    assert stats["rows_checked"] == 3
    data = pd.concat([frame, block], axis=1)
    osf.assert_history_ledger(data, ledger, 3)
    tampered = ledger.copy()
    tampered.loc[0, "history_1_source_ord"] = 2020 * 12 + 9  # Oct 2020 > origin Jul 2020
    with pytest.raises(AssertionError):
        osf.reference_history_check(OBS, tampered, block)
    with pytest.raises(ValueError, match="after min"):
        osf.assert_history_ledger(data, tampered, 3)
    no_source = ledger.copy()
    no_source.loc[0, "history_1_source_ord"] = np.nan
    with pytest.raises(ValueError, match="without source"):
        osf.assert_history_ledger(data, no_source, 3)
    with pytest.raises(ValueError, match="horizon"):
        osf.assert_history_ledger(data, ledger, 6)


def test_gate_rejects_history_difference_not_derived_from_validated_values():
    frame = rows([(1, 2020, 10), (1, 2021, 1), (2, 2021, 1)])
    block, ledger = osf.build_safe_history(OBS, frame, 3)
    data = pd.concat([frame, block], axis=1)
    leaky = data.copy()
    leaky.loc[0, "overall_phase_history_change_1_2"] = 5 - leaky.loc[0, "overall_phase_history_1"]  # target-relative (truth 5), != 3 - 2
    with pytest.raises(ValueError, match="overall_phase_history_change_1_2"):
        osf.assert_history_ledger(leaky, ledger, 3)
    filled = data.copy()
    filled.loc[filled["overall_phase_history_change_1_3"].isna(), "overall_phase_history_change_1_3"] = 0.0
    with pytest.raises(ValueError, match="overall_phase_history_change_1_3"):
        osf.assert_history_ledger(filled, ledger, 3)


def test_legacy_history_and_target_side_population_are_forbidden():
    assert osf.forbidden_features(["overall_phase_lag1", "overall_phase_prev_observed_asof_s3", "estimated_population",
                                   "phase3_worse", "phase2_percent", "GPP_mean__l12", "overall_phase_history_1"]) == [
        "overall_phase_lag1", "overall_phase_prev_observed_asof_s3", "estimated_population", "phase3_worse", "phase2_percent"]


def test_fitting_label_cutoff_and_origin_weights():
    target = 2022 * 12 + 4  # May 2022
    ords = np.arange(target - 30, target + 2)
    valid = np.ones(len(ords), dtype=bool)
    h0 = osf.fit_mask(ords, valid, target, 0)
    assert ords[h0].max() == target - 1  # target-month labels excluded for every area
    h12 = osf.fit_mask(ords, valid, target, 12)
    assert ords[h12].max() == target - 12
    w = osf.origin_weights(ords[osf.fit_mask(ords, valid, target, 3)], target - 3, 24.0)
    assert w.max() == 1.0  # age 0 allowed for H > 0
    np.testing.assert_allclose(w[-25], 0.5)
    with pytest.raises(ValueError):
        osf.origin_weights(np.array([target]), target - 3)
    invalid = valid.copy()
    invalid[-3] = False
    assert not osf.fit_mask(ords, invalid, target + 1, 0)[-3]


def share_frame(shares, phases):
    df = pd.DataFrame(shares, columns=list(osf.SHARE_COLUMNS))
    df["overall_phase"] = phases
    return df


def test_share_normalization_keeps_raw_shares_and_flags_malformed_rows():
    df = share_frame([[1, 0, 0, 0, 0], [0.2, 0.2, 0.2, 0.2, 0.4], [0, 0, 0, 0, 0], [0.5, np.nan, 0.5, 0, 0], [1.2, -0.1, 0, 0, 0], [0.5, 0.5, 0, 0, 0]],
                     [1, 3, 2, 3, 1, 0])
    raw = df.copy()
    out = osf.normalized_cumulative_targets(df)
    pd.testing.assert_frame_equal(df, raw)
    assert out["share_valid"].tolist() == [True, True, False, False, False, False]
    np.testing.assert_allclose(out.loc[0, list(osf.CUMULATIVE_TARGETS)].to_numpy(float), 0.0)  # genuine phase 1
    np.testing.assert_allclose(out.loc[1, list(osf.CUMULATIVE_TARGETS)].to_numpy(float), [1 - 0.2 / 1.2, 0.8 / 1.2, 0.6 / 1.2, 0.4 / 1.2])
    assert out.loc[2:, list(osf.CUMULATIVE_TARGETS)].isna().all().all()


def test_classification_uses_unrounded_scores_and_keeps_zero_predictions():
    preds = pd.DataFrame({"phase2_pred": [0, 0.196, 0.2, 0.204, 0.9, 0.3], "phase3_pred": [0, 0, 0, 0.199, 0.5, 0.2],
                          "phase4_pred": [0, 0, 0, 0, 0.2, 0], "phase5_pred": [0, 0, 0, 0, 0.19999, 0]})
    assert osf.classify_cumulative(preds, 0.2).tolist() == [1, 1, 2, 2, 4, 3]


def test_idp_latest_report_age_missing_and_future_reports():
    idp = osf.idp_observations(pd.DataFrame({
        "admin0Pcode": ["NGA", "NGA", "NGA", "SOM"], "year": [2020, 2020, 2021, 2020], "month": [2, 6, 3, 1],
        "idp_ind": [100.0, np.nan, 300.0, 50.0], "observed": [1, 0, 1, 1],
        "reportingDate": ["2020-02-15", None, "2021-03-30", "2020-01-31"]}))
    frame = rows([(1, 2020, 1), (1, 2020, 5), (1, 2021, 3), (2, 2021, 3), (3, 2021, 3)])
    block, ledger = osf.build_idp_features(idp, frame, ["NGA", "NGA", "NGA", "SOM", None], 0)
    np.testing.assert_allclose(block.iloc[:, 0].to_numpy(float), [np.nan, 100, 300, 50, np.nan])  # never zero-filled
    np.testing.assert_allclose(block.iloc[:, 1].to_numpy(float), [np.nan, 3, 0, 14, np.nan])
    assert osf.reference_idp_check(idp, ledger, block)["idp_present"] == 3
    block3, _ = osf.build_idp_features(idp, frame, ["NGA", "NGA", "NGA", "SOM", None], 3)
    assert block3.iloc[2, 0] == 100  # March 2021 report is after the Dec 2020 origin
    with pytest.raises(ValueError):
        osf.idp_observations(pd.DataFrame({"admin0Pcode": ["NGA"], "year": [2020], "month": [2], "idp_ind": [1.0], "observed": [1], "reportingDate": ["2020-03-01"]}))


def test_completed_season_boundary_is_month_end_of_origin():
    seasons = pd.DataFrame({"admin_code": [1, 1], "season_year": [2020, 2020], "season": ["s1", "s2"],
                            "gs_start_date": ["2020-01-01", "2020-03-01"], "gs_end_date_exclusive": ["2020-04-01", "2020-04-02"]})
    for v in cf.SEASONAL_VARIABLES:
        seasons[v] = [1.0, 2.0]
    out = cf.last_completed_seasons(seasons, [1], [2020 * 12 + 2])  # origin March 2020 (month end)
    assert out[f"gs_last1__{cf.SEASONAL_VARIABLES[0]}"].iloc[0] == 1.0  # ends exactly at Apr 1 -> complete
    later = cf.last_completed_seasons(seasons, [1], [2020 * 12 + 3])
    assert later[f"gs_last1__{cf.SEASONAL_VARIABLES[0]}"].iloc[0] == 2.0


def test_metrics_report_mae_ordinal_and_undefined_precision():
    preds = pd.DataFrame({"overall_phase": [1, 2, 3], "overall_phase_pred": [1, 1, 1], "phase3_worse": [0.0, 0.1, 0.5], "phase3_pred": [0.1, 0.1, 0.1]})
    m = osf.origin_metrics(preds, "overall", 2022)
    assert "accuracy" not in m
    assert m["exact_phase_accuracy"]["value"] == pytest.approx(1 / 3)
    assert m["phase3plus_accuracy"]["value"] == pytest.approx(2 / 3)  # truth 3+ only on row 3, predicted 3+ on none
    assert m["precision_phase3plus"]["status"] == "unavailable"
    assert m["ordinal_mae"]["value"] == pytest.approx(1.0)
    assert m["mae_phase3plus"]["value"] == pytest.approx((0.1 + 0 + 0.4) / 3)


def test_pooled_metrics_keep_the_aggregate_label():
    preds = pd.DataFrame({"overall_phase": [1, 3, 3], "overall_phase_pred": [1, 3, 1], "phase3_worse": [0.0, 0.4, 0.5], "phase3_pred": [0.1, 0.3, 0.1]})
    pooled = osf.origin_metrics(preds, "overall", "pooled")
    assert pooled["test_year"] == "pooled" and pooled["sensitivity_phase3plus"]["value"] == pytest.approx(0.5)
    assert pooled["exact_phase_accuracy"]["value"] == pytest.approx(2 / 3) and pooled["phase3plus_accuracy"]["value"] == pytest.approx(2 / 3)
    binary_only = preds.assign(overall_phase_pred=[2, 4, 4])  # every exact phase wrong, every 3+ class right
    both = osf.origin_metrics(binary_only, "overall", "pooled")
    assert both["exact_phase_accuracy"]["value"] == 0.0 and both["phase3plus_accuracy"]["value"] == 1.0
    assert osf.origin_metrics(preds.iloc[:0], "overall", "pooled")["test_year"] == "pooled"
    assert osf.flatten_origin_metrics(pooled)["test_year"] == "pooled"
