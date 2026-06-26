from __future__ import annotations

import pandas as pd
import pytest

from ipcch import operational_contract as oc


def test_april_2026_baseline_target_months():
    rows = oc.target_periods_for_feature_month("2026-04", [0, 6, 12])
    assert rows == {
        0: "2026-04",
        6: "2026-10",
        12: "2027-04",
    }


def test_target_periods_reject_unsupported_operational_scope():
    with pytest.raises(oc.OperationalContractError, match="scope"):
        oc.target_periods_for_feature_month("2026-04", [3])


@pytest.mark.parametrize("scope", [6.5, False, "six"])
def test_target_periods_reject_non_strict_scope_values(scope):
    with pytest.raises(oc.OperationalContractError, match="scope"):
        oc.target_periods_for_feature_month("2026-04", [scope])


def test_target_periods_accept_digit_string_scope():
    assert oc.target_periods_for_feature_month("2026-04", ["6"]) == {6: "2026-10"}


def test_scope0_training_cutoff_excludes_april_2026():
    assert oc.training_cutoff_for_feature_month("2026-04") == "2026-04-01"


def test_feature_month_requires_strict_year_month_format():
    with pytest.raises(oc.OperationalContractError, match="YYYY-MM"):
        oc.target_periods_for_feature_month("2026-04-01", [0])

    with pytest.raises(oc.OperationalContractError, match="YYYY-MM"):
        oc.training_cutoff_for_feature_month("Apr 2026")


def test_feature_contract_requires_one_row_per_model_feature():
    feature_columns = ["rain", "static_crop"]
    contract = pd.DataFrame(
        [
            {
                "feature_name": "rain",
                "scope_months": "all",
                "category": "required",
                "source_column": "Rainf_f_tavg_mean",
                "dtype": "float",
                "required_in_input": True,
                "missing_tolerance": 0.0,
                "fill_method": "none",
                "fill_value_or_stat_key": "",
                "lookup_asset": "",
                "derive_function": "",
                "as_of_policy": "feature_month_end",
                "notes": "monthly rainfall",
            },
            {
                "feature_name": "static_crop",
                "scope_months": "all",
                "category": "static_join",
                "source_column": "",
                "dtype": "integer",
                "required_in_input": False,
                "missing_tolerance": 0.0,
                "fill_method": "static lookup",
                "fill_value_or_stat_key": "",
                "lookup_asset": "lookups/static_features.csv",
                "derive_function": "",
                "as_of_policy": "static",
                "notes": "crop class",
            },
        ]
    )
    report = oc.validate_feature_contract(contract, feature_columns)
    assert report["status"] == "passed"
    assert report["model_feature_count"] == 2


def test_feature_contract_rejects_unknown_as_of_policy():
    contract = pd.DataFrame(
        [
            {
                "feature_name": "rain",
                "scope_months": "all",
                "category": "required",
                "source_column": "Rainf_f_tavg_mean",
                "dtype": "float",
                "required_in_input": True,
                "missing_tolerance": 0.0,
                "fill_method": "none",
                "fill_value_or_stat_key": "",
                "lookup_asset": "",
                "derive_function": "",
                "as_of_policy": "feature_moth_end",
                "notes": "typo in policy",
            }
        ]
    )
    with pytest.raises(oc.OperationalContractError, match="as_of_policy"):
        oc.validate_feature_contract(contract, ["rain"])


def test_feature_contract_rejects_null_feature_name():
    contract = pd.DataFrame(
        [
            {
                "feature_name": pd.NA,
                "scope_months": "all",
                "category": "required",
                "source_column": "Rainf_f_tavg_mean",
                "dtype": "float",
                "required_in_input": True,
                "missing_tolerance": 0.0,
                "fill_method": "none",
                "fill_value_or_stat_key": "",
                "lookup_asset": "",
                "derive_function": "",
                "as_of_policy": "feature_month_end",
                "notes": "monthly rainfall",
            }
        ]
    )
    with pytest.raises(oc.OperationalContractError, match="feature_name"):
        oc.validate_feature_contract(contract, ["rain"])


def test_unsupported_feature_in_model_columns_fails():
    contract = pd.DataFrame(
        [
            {
                "feature_name": "bad_target",
                "scope_months": "all",
                "category": "unsupported",
                "source_column": "overall_phase",
                "dtype": "float",
                "required_in_input": False,
                "missing_tolerance": 0.0,
                "fill_method": "none",
                "fill_value_or_stat_key": "",
                "lookup_asset": "",
                "derive_function": "",
                "as_of_policy": "not_allowed",
                "notes": "target leakage",
            }
        ]
    )
    with pytest.raises(oc.OperationalContractError, match="unsupported"):
        oc.validate_feature_contract(contract, ["bad_target"])


def test_unsupported_feature_category_is_stripped_before_model_feature_check():
    contract = pd.DataFrame(
        [
            {
                "feature_name": "bad_target",
                "scope_months": "all",
                "category": " unsupported ",
                "source_column": "overall_phase",
                "dtype": "float",
                "required_in_input": False,
                "missing_tolerance": 0.0,
                "fill_method": "none",
                "fill_value_or_stat_key": "",
                "lookup_asset": "",
                "derive_function": "",
                "as_of_policy": "not_allowed",
                "notes": "target leakage",
            }
        ]
    )
    with pytest.raises(oc.OperationalContractError, match="unsupported"):
        oc.validate_feature_contract(contract, ["bad_target"])


def test_phase_decoding_uses_scores_threshold_and_top_down_rule():
    pred = pd.DataFrame(
        {
            "area_id": ["A", "B"],
            "phase2_worse_score": [0.7, 0.1],
            "phase3_worse_score": [0.6, 0.1],
            "phase4_worse_score": [0.1, 0.1],
            "phase5_worse_score": [0.1, 0.1],
        }
    )
    decoded = oc.decode_phase_predictions(pred, {"default": 0.2}, monotonicity_policy="fail")
    assert decoded["phase2_worse_pred"].tolist() == [1, 0]
    assert decoded["phase3_worse_pred"].tolist() == [1, 0]
    assert decoded["overall_phase_pred"].tolist() == [3, 1]


def test_non_monotonic_predictions_fail_when_policy_is_fail():
    pred = pd.DataFrame(
        {
            "area_id": ["A"],
            "phase2_worse_score": [0.1],
            "phase3_worse_score": [0.9],
            "phase4_worse_score": [0.1],
            "phase5_worse_score": [0.1],
        }
    )
    with pytest.raises(oc.OperationalContractError, match="non-monotonic"):
        oc.decode_phase_predictions(pred, {"default": 0.2}, monotonicity_policy="fail")


def test_phase_decoding_accepts_binary_prediction_columns_without_thresholds():
    pred = pd.DataFrame(
        {
            "area_id": ["A", "B"],
            "phase2_worse_pred": [1.0, 0],
            "phase3_worse_pred": [1, 0.0],
            "phase4_worse_pred": [0, 0],
            "phase5_worse_pred": [0, 0],
        }
    )
    decoded = oc.decode_phase_predictions(pred, thresholds={})
    assert decoded["phase2_worse_pred"].tolist() == [1, 0]
    assert decoded["phase3_worse_pred"].tolist() == [1, 0]
    assert decoded["overall_phase_pred"].tolist() == [3, 1]


def test_phase_decoding_rejects_non_binary_prediction_columns():
    pred = pd.DataFrame(
        {
            "area_id": ["A"],
            "phase2_worse_pred": [1],
            "phase3_worse_pred": [0.5],
            "phase4_worse_pred": [0],
            "phase5_worse_pred": [0],
        }
    )
    with pytest.raises(oc.OperationalContractError, match="binary"):
        oc.decode_phase_predictions(pred, thresholds={})


@pytest.mark.parametrize(
    "pred",
    [
        pd.DataFrame(
            {
                "area_id": ["A"],
                "phase2_worse_score": [0.7],
                "phase3_worse_score": [0.6],
                "phase4_worse_score": [0.1],
                "phase5_worse_pred": [0],
            }
        ),
        pd.DataFrame(
            {
                "area_id": ["A"],
                "phase2_worse_pred": [1],
                "phase3_worse_pred": [1],
                "phase4_worse_pred": [0],
            }
        ),
        pd.DataFrame(
            {
                "area_id": ["A"],
                "phase2_worse_score": [0.7],
                "phase3_worse_score": [0.6],
                "phase4_worse_score": [0.1],
                "phase5_worse_score": [0.1],
                "phase2_worse_pred": [1],
                "phase3_worse_pred": [1],
                "phase4_worse_pred": [0],
                "phase5_worse_pred": [0],
            }
        ),
    ],
)
def test_phase_decoding_rejects_mixed_or_incomplete_inputs(pred):
    with pytest.raises(oc.OperationalContractError, match="score|pred|complete"):
        oc.decode_phase_predictions(pred, thresholds={})


@pytest.mark.parametrize("threshold", [float("nan"), float("inf"), -0.01, 1.01])
def test_phase_decoding_rejects_invalid_thresholds(threshold):
    pred = pd.DataFrame(
        {
            "area_id": ["A"],
            "phase2_worse_score": [0.7],
            "phase3_worse_score": [0.6],
            "phase4_worse_score": [0.1],
            "phase5_worse_score": [0.1],
        }
    )
    with pytest.raises(oc.OperationalContractError, match="threshold"):
        oc.decode_phase_predictions(pred, {"default": threshold})


@pytest.mark.parametrize("score", [float("inf"), -float("inf")])
def test_phase_decoding_rejects_infinite_scores(score):
    pred = pd.DataFrame(
        {
            "area_id": ["A"],
            "phase2_worse_score": [0.7],
            "phase3_worse_score": [score],
            "phase4_worse_score": [0.1],
            "phase5_worse_score": [0.1],
        }
    )
    with pytest.raises(oc.OperationalContractError, match="phase score"):
        oc.decode_phase_predictions(pred, {"default": 0.2})


def test_cummax_policy_corrects_non_monotonic_predictions():
    pred = pd.DataFrame(
        {
            "area_id": ["A"],
            "phase2_worse_score": [0.1],
            "phase3_worse_score": [0.9],
            "phase4_worse_score": [0.1],
            "phase5_worse_score": [0.1],
        }
    )
    decoded = oc.decode_phase_predictions(pred, {"default": 0.2}, monotonicity_policy="cummax")
    assert decoded["phase2_worse_pred"].tolist() == [1]
    assert decoded["phase3_worse_pred"].tolist() == [1]
    assert decoded["phase4_worse_pred"].tolist() == [0]
    assert decoded["overall_phase_pred"].tolist() == [3]


def test_feature_eligibility_rejects_targets_forecast_weather_and_future_policy():
    contract = pd.DataFrame(
        [
            {
                "feature_name": "phase3_percent",
                "scope_months": "all",
                "category": "required",
                "source_column": "phase3_percent",
                "dtype": "float",
                "required_in_input": True,
                "missing_tolerance": 0.0,
                "fill_method": "none",
                "fill_value_or_stat_key": "",
                "lookup_asset": "",
                "derive_function": "",
                "as_of_policy": "feature_month_end",
                "notes": "target leakage",
            },
            {
                "feature_name": "Rainf_f_tavg_mean_forecast_proxy",
                "scope_months": "6",
                "category": "required",
                "source_column": "Rainf_f_tavg_mean_forecast_proxy",
                "dtype": "float",
                "required_in_input": True,
                "missing_tolerance": 0.0,
                "fill_method": "none",
                "fill_value_or_stat_key": "",
                "lookup_asset": "",
                "derive_function": "",
                "as_of_policy": "forecast_weather",
                "notes": "forecasted weather disabled",
            },
            {
                "feature_name": "rolling_after_target",
                "scope_months": "12",
                "category": "required",
                "source_column": "rolling_after_target",
                "dtype": "float",
                "required_in_input": True,
                "missing_tolerance": 0.0,
                "fill_method": "none",
                "fill_value_or_stat_key": "",
                "lookup_asset": "",
                "derive_function": "",
                "as_of_policy": "post_target",
                "notes": "future-dependent rolling feature",
            },
        ]
    )
    with pytest.raises(oc.OperationalContractError, match="production-safe"):
        oc.validate_production_safe_feature_contract(contract)


def test_feature_eligibility_rejects_after_feature_month_policy():
    contract = pd.DataFrame(
        [
            {
                "feature_name": "future_rain",
                "scope_months": "0",
                "category": "required",
                "source_column": "rain",
                "dtype": "float",
                "required_in_input": True,
                "missing_tolerance": 0.0,
                "fill_method": "none",
                "fill_value_or_stat_key": "",
                "lookup_asset": "",
                "derive_function": "",
                "as_of_policy": "after_feature_month",
                "notes": "available after the feature month",
            }
        ]
    )
    with pytest.raises(oc.OperationalContractError, match="production-safe"):
        oc.validate_production_safe_feature_contract(contract)


def test_feature_eligibility_requires_dataframe():
    with pytest.raises(oc.OperationalContractError, match="DataFrame"):
        oc.validate_production_safe_feature_contract("not a dataframe")


def test_feature_eligibility_rejects_forecast_proxy_source_column():
    contract = pd.DataFrame(
        [
            {
                "feature_name": "rain_proxy",
                "scope_months": "6",
                "category": "required",
                "source_column": "Rainf_f_tavg_mean_forecast_proxy",
                "dtype": "float",
                "required_in_input": True,
                "missing_tolerance": 0.0,
                "fill_method": "none",
                "fill_value_or_stat_key": "",
                "lookup_asset": "",
                "derive_function": "",
                "as_of_policy": "feature_month_end",
                "notes": "forecasted weather proxy should be rejected",
            }
        ]
    )
    with pytest.raises(
        oc.OperationalContractError, match="forecasted weather|production-safe"
    ):
        oc.validate_production_safe_feature_contract(contract)


def test_feature_eligibility_rejects_compact_forecast_weather_source_column():
    contract = pd.DataFrame(
        [
            {
                "feature_name": "rain_safe_name",
                "scope_months": "6",
                "category": "required",
                "source_column": "Rainf_forecast_weather",
                "dtype": "float",
                "required_in_input": True,
                "missing_tolerance": 0.0,
                "fill_method": "none",
                "fill_value_or_stat_key": "",
                "lookup_asset": "",
                "derive_function": "",
                "as_of_policy": "feature_month_end",
                "notes": "source column uses compact marker",
            }
        ]
    )
    with pytest.raises(oc.OperationalContractError, match="production-safe"):
        oc.validate_production_safe_feature_contract(contract)


def test_feature_eligibility_rejects_target_marker_in_derive_function():
    contract = pd.DataFrame(
        [
            {
                "feature_name": "derived_risk",
                "scope_months": "0",
                "category": "required",
                "source_column": "rain",
                "dtype": "float",
                "required_in_input": True,
                "missing_tolerance": 0.0,
                "fill_method": "none",
                "fill_value_or_stat_key": "",
                "lookup_asset": "",
                "derive_function": "derive_from_overall_phase",
                "as_of_policy": "feature_month_end",
                "notes": "derive function leaks target",
            }
        ]
    )
    with pytest.raises(oc.OperationalContractError, match="production-safe"):
        oc.validate_production_safe_feature_contract(contract)


def test_feature_eligibility_rejects_target_marker_in_notes():
    contract = pd.DataFrame(
        [
            {
                "feature_name": "risk_note",
                "scope_months": "0",
                "category": "required",
                "source_column": "rain",
                "dtype": "float",
                "required_in_input": True,
                "missing_tolerance": 0.0,
                "fill_method": "none",
                "fill_value_or_stat_key": "",
                "lookup_asset": "",
                "derive_function": "",
                "as_of_policy": "feature_month_end",
                "notes": "unsafe because it references overall_phase",
            }
        ]
    )
    with pytest.raises(oc.OperationalContractError, match="production-safe"):
        oc.validate_production_safe_feature_contract(contract)


def test_feature_eligibility_rejects_forecast_marker_in_notes():
    contract = pd.DataFrame(
        [
            {
                "feature_name": "rain_note",
                "scope_months": "6",
                "category": "required",
                "source_column": "rain",
                "dtype": "float",
                "required_in_input": True,
                "missing_tolerance": 0.0,
                "fill_method": "none",
                "fill_value_or_stat_key": "",
                "lookup_asset": "",
                "derive_function": "",
                "as_of_policy": "feature_month_end",
                "notes": "would require Rainf_f_tavg_mean_forecast_proxy",
            }
        ]
    )
    with pytest.raises(oc.OperationalContractError, match="production-safe"):
        oc.validate_production_safe_feature_contract(contract)


def test_feature_eligibility_rejects_space_separated_forecast_weather_note():
    contract = pd.DataFrame(
        [
            {
                "feature_name": "rain_note_text",
                "scope_months": "6",
                "category": "required",
                "source_column": "rain",
                "dtype": "float",
                "required_in_input": True,
                "missing_tolerance": 0.0,
                "fill_method": "none",
                "fill_value_or_stat_key": "",
                "lookup_asset": "",
                "derive_function": "",
                "as_of_policy": "feature_month_end",
                "notes": "forecasted weather proxy should be rejected",
            }
        ]
    )
    with pytest.raises(oc.OperationalContractError, match="production-safe"):
        oc.validate_production_safe_feature_contract(contract)


def test_feature_eligibility_allows_non_proxy_forecast_text():
    contract = pd.DataFrame(
        [
            {
                "feature_name": "rain_forecast_reference",
                "scope_months": "6",
                "category": "required",
                "source_column": "rain_observed_reference",
                "dtype": "float",
                "required_in_input": True,
                "missing_tolerance": 0.0,
                "fill_method": "none",
                "fill_value_or_stat_key": "",
                "lookup_asset": "",
                "derive_function": "",
                "as_of_policy": "feature_month_end",
                "notes": "not a forecast proxy marker",
            }
        ]
    )
    assert oc.validate_production_safe_feature_contract(contract)["status"] == "passed"


@pytest.mark.parametrize(
    "notes",
    ["actual rainfall observed by feature month", "label encoding not used"],
)
def test_feature_eligibility_allows_safe_actual_and_label_notes(notes):
    contract = pd.DataFrame(
        [
            {
                "feature_name": "rain_note_safe",
                "scope_months": "0",
                "category": "required",
                "source_column": "rain",
                "dtype": "float",
                "required_in_input": True,
                "missing_tolerance": 0.0,
                "fill_method": "none",
                "fill_value_or_stat_key": "",
                "lookup_asset": "",
                "derive_function": "",
                "as_of_policy": "feature_month_end",
                "notes": notes,
            }
        ]
    )
    assert oc.validate_production_safe_feature_contract(contract)["status"] == "passed"


def test_feature_eligibility_rejects_completed_panel_only_marker():
    contract = pd.DataFrame(
        [
            {
                "feature_name": "panel_only_feature",
                "scope_months": "0",
                "category": "required",
                "source_column": "completed_panel_only_rain",
                "dtype": "float",
                "required_in_input": True,
                "missing_tolerance": 0.0,
                "fill_method": "none",
                "fill_value_or_stat_key": "",
                "lookup_asset": "",
                "derive_function": "",
                "as_of_policy": "feature_month_end",
                "notes": "completed-panel-only source with no fallback",
            }
        ]
    )
    with pytest.raises(oc.OperationalContractError, match="production-safe"):
        oc.validate_production_safe_feature_contract(contract)


def test_feature_eligibility_rejects_manual_backfill_without_approved_policy():
    contract = pd.DataFrame(
        [
            {
                "feature_name": "manual_backfill_rain",
                "scope_months": "0",
                "category": "required",
                "source_column": "rain",
                "dtype": "float",
                "required_in_input": True,
                "missing_tolerance": 0.0,
                "fill_method": "none",
                "fill_value_or_stat_key": "",
                "lookup_asset": "",
                "derive_function": "",
                "as_of_policy": "feature_month_end",
                "notes": "manual backfill from analyst spreadsheet",
            }
        ]
    )
    with pytest.raises(oc.OperationalContractError, match="production-safe"):
        oc.validate_production_safe_feature_contract(contract)


def test_feature_eligibility_rejects_invalid_derived_contract_row():
    contract = pd.DataFrame(
        [
            {
                "feature_name": "derived_rain",
                "scope_months": "0",
                "category": "derived",
                "source_column": "rain",
                "dtype": "float",
                "required_in_input": True,
                "missing_tolerance": 0.0,
                "fill_method": "none",
                "fill_value_or_stat_key": "",
                "lookup_asset": "",
                "derive_function": "",
                "as_of_policy": "feature_month_end",
                "notes": "derived feature missing derivation metadata",
            }
        ]
    )
    with pytest.raises(oc.OperationalContractError, match="derived"):
        oc.validate_production_safe_feature_contract(contract)


def test_feature_eligibility_rejects_rolling_feature_after_feature_month():
    contract = pd.DataFrame(
        [
            {
                "feature_name": "rolling_rain_mean",
                "scope_months": "0",
                "category": "required",
                "source_column": "rolling_rain_mean",
                "dtype": "float",
                "required_in_input": True,
                "missing_tolerance": 0.0,
                "fill_method": "none",
                "fill_value_or_stat_key": "",
                "lookup_asset": "",
                "derive_function": "",
                "as_of_policy": "feature_month_end",
                "notes": "rolling window includes data after feature month",
            }
        ]
    )
    with pytest.raises(oc.OperationalContractError, match="production-safe"):
        oc.validate_production_safe_feature_contract(contract)


@pytest.mark.parametrize(
    "category,fill_method,lookup_asset,stat_key",
    [
        ("static_join", "static lookup", "", ""),
        ("carry_forward", "carry forward", "", ""),
        ("median_impute", "median", "", ""),
    ],
)
def test_feature_eligibility_rejects_undocumented_fallback_rules(
    category, fill_method, lookup_asset, stat_key
):
    contract = pd.DataFrame(
        [
            {
                "feature_name": f"{category}_feature",
                "scope_months": "0",
                "category": category,
                "source_column": "",
                "dtype": "float",
                "required_in_input": False,
                "missing_tolerance": 0.0,
                "fill_method": fill_method,
                "fill_value_or_stat_key": stat_key,
                "lookup_asset": lookup_asset,
                "derive_function": "",
                "as_of_policy": "static" if category == "static_join" else "latest_known",
                "notes": "fallback rule is undocumented",
            }
        ]
    )
    with pytest.raises(oc.OperationalContractError, match="production-safe|lookup|stat"):
        oc.validate_production_safe_feature_contract(contract)


@pytest.mark.parametrize(
    "fill_method,lookup_asset,stat_key",
    [
        ("static lookup", "", ""),
        ("carry forward", "", ""),
        ("median", "", ""),
    ],
)
def test_feature_eligibility_rejects_undocumented_fallback_rules_by_fill_method(
    fill_method, lookup_asset, stat_key
):
    contract = pd.DataFrame(
        [
            {
                "feature_name": "required_feature_with_fill",
                "scope_months": "0",
                "category": "required",
                "source_column": "rain",
                "dtype": "float",
                "required_in_input": True,
                "missing_tolerance": 0.0,
                "fill_method": fill_method,
                "fill_value_or_stat_key": stat_key,
                "lookup_asset": lookup_asset,
                "derive_function": "",
                "as_of_policy": "feature_month_end",
                "notes": "fill method requires documented fallback",
            }
        ]
    )
    with pytest.raises(oc.OperationalContractError, match="production-safe|lookup|stat"):
        oc.validate_production_safe_feature_contract(contract)
