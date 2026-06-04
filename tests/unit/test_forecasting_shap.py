import numpy as np
import pandas as pd
import pytest

from ipcch.forecasting_shap import (
    NOWCASTING_SCOPE_ORDER,
    TARGET,
    WEATHER_FORECAST_GROUP,
    aggregate_grouped_importance,
    aggregate_six_category_importance,
    attribution_coverage_summary,
    detect_crosswalk_columns,
    diagnostic_record,
    empty_shap_rows_diagnostic,
    enforce_raw_export_size,
    map_features_to_groups,
    normalize_shap_values,
    nowcasting_scope_group_matrix,
    per_feature_shap_summary,
    phase3_shap_filename,
    render_heatmap,
    render_nowcasting_scope_heatmap,
    scope_matrix,
    unavailable_split_diagnostic,
    unmapped_feature_diagnostics,
    validate_crosswalk,
    validate_feature_alignment,
    validate_phase3_artifact_name,
    validate_phase3_target,
    validate_sample_type,
)


def test_phase3_shap_filename_includes_target_scope_and_artifact_type():
    assert phase3_shap_filename("matrix", "fs0") == "phase3_worse_fs0_matrix.csv"
    assert phase3_shap_filename("heatmap", "fs3", "png") == "phase3_worse_fs3_heatmap.png"


def test_validate_sample_type_rejects_unknown_sample():
    assert validate_sample_type("train") == "train"
    with pytest.raises(ValueError, match="sample type"):
        validate_sample_type("validation")


def test_phase3_only_target_enforcement_rejects_other_targets():
    validate_phase3_target(TARGET)
    for target in ("phase2_worse", "phase4_worse", "phase5_worse", "overall_phase_pred"):
        with pytest.raises(ValueError, match="phase3_worse"):
            validate_phase3_target(target)


def test_feature_alignment_requires_exact_column_order():
    shap_matrix = pd.DataFrame({"a": [1.0], "b": [2.0]})
    validate_feature_alignment(shap_matrix, ["a", "b"])
    with pytest.raises(ValueError, match="feature order"):
        validate_feature_alignment(shap_matrix, ["b", "a"])


def test_normalize_shap_values_accepts_2d_array_matching_matrix():
    shap_matrix = pd.DataFrame({"a": [1.0, 2.0], "b": [3.0, 4.0]})
    values = normalize_shap_values(np.array([[0.1, -0.2], [0.3, 0.4]]), shap_matrix)
    assert values.shape == (2, 2)
    assert values.dtype == float


def test_normalize_shap_values_rejects_shape_mismatch():
    shap_matrix = pd.DataFrame({"a": [1.0, 2.0], "b": [3.0, 4.0]})
    with pytest.raises(ValueError, match="shape"):
        normalize_shap_values(np.array([[0.1, -0.2, 0.5], [0.3, 0.4, 0.6]]), shap_matrix)


def test_normalize_shap_values_unwraps_single_output_list():
    shap_matrix = pd.DataFrame({"a": [1.0], "b": [3.0]})
    values = normalize_shap_values([np.array([[0.1, -0.2]])], shap_matrix)
    assert values.tolist() == [[0.1, -0.2]]


def test_unavailable_and_empty_row_diagnostics_include_phase3_target():
    unavailable = unavailable_split_diagnostic("fs0", 2022, "missing model")
    empty = empty_shap_rows_diagnostic("fs0", 2022, "train")
    assert unavailable["target"] == TARGET
    assert unavailable["diagnostic_type"] == "unavailable split"
    assert empty["diagnostic_type"] == "skipped SHAP"
    assert "train" in empty["message"]


def test_diagnostic_record_rejects_invalid_severity():
    with pytest.raises(ValueError, match="severity"):
        diagnostic_record("fs0", 2022, "test", "fatal", "bad")


def six_group_crosswalk():
    return pd.DataFrame(
        {
            "variable": ["a", "b", "c", "d", "e", "f"],
            "six_category": ["food prices", "geography", "econ", "conflict", "agriculture", "weather"],
        }
    )


@pytest.fixture
def grouped_shap_feature_matrix():
    return pd.DataFrame(
        {
            "food_price_index_lag1": [1.0, 1.2, 1.3],
            "conflict_events_current": [0.0, 2.0, 1.0],
            "Rainf_f_tavg_mean_forecast_proxy": [40.0, 42.0, 41.0],
            "unmapped_runtime_feature": [5.0, 6.0, 7.0],
        }
    )


@pytest.fixture
def grouped_shap_values(grouped_shap_feature_matrix):
    return np.array(
        [
            [0.10, -0.20, 0.30, 0.05],
            [0.20, -0.10, 0.40, 0.10],
            [0.30, -0.30, 0.50, 0.15],
        ]
    )


@pytest.fixture
def grouped_shap_crosswalk_rows():
    return pd.DataFrame(
        {
            "variable": [
                "food_price_index",
                "conflict_events",
                "soil_moisture",
                "market_access",
                "cropland_area",
                "population_density",
            ],
            "six_category": [
                "food prices",
                "conflict",
                "weather",
                "econ",
                "agriculture",
                "geography",
            ],
        }
    )


@pytest.fixture
def weather_forecast_feature_seeds():
    return {"Rainf_f_tavg_mean_forecast_proxy", "Tair_f_tavg_mean_forecast_proxy"}


def test_crosswalk_column_auto_detection_and_explicit_selection():
    crosswalk = six_group_crosswalk()
    assert detect_crosswalk_columns(crosswalk) == ("variable", "six_category")
    assert detect_crosswalk_columns(crosswalk, "variable", "six_category") == ("variable", "six_category")


def test_crosswalk_validation_requires_exactly_six_groups():
    crosswalk = pd.DataFrame({"variable": ["a", "b"], "six_category": ["food prices", "weather"]})
    with pytest.raises(ValueError, match="exactly 6"):
        validate_crosswalk(crosswalk, ["a", "b"], "variable", "six_category")


def test_duplicate_feature_to_multiple_groups_fails():
    crosswalk = pd.concat(
        [six_group_crosswalk(), pd.DataFrame({"variable": ["a"], "six_category": ["weather"]})],
        ignore_index=True,
    )
    with pytest.raises(ValueError, match="Duplicate"):
        validate_crosswalk(crosswalk, ["a", "b"], "variable", "six_category")


def test_missing_mappings_fail_by_default():
    with pytest.raises(ValueError, match="Missing SHAP crosswalk"):
        validate_crosswalk(six_group_crosswalk(), ["a", "missing"], "variable", "six_category")


def test_allowed_unmapped_features_are_excluded_and_diagnosed():
    validated, diagnostics = validate_crosswalk(six_group_crosswalk(), ["a", "b", "missing"], "variable", "six_category", allow_unmapped=True)
    assert set(validated["feature_name"]) == {"a", "b", "c", "d", "e", "f"}
    assert diagnostics[0]["feature_name"] == "missing"
    details = unmapped_feature_diagnostics(np.array([[1.0, 2.0, 3.0]]), ["a", "b", "missing"], ["a", "b"], "fs0", 2022)
    assert details[0]["mapped_abs_shap_sum"] == 3.0
    assert details[0]["unmapped_abs_shap_sum"] == 3.0
    assert details[0]["unmapped_abs_shap_share"] == 0.5


def test_nowcasting_mapping_exact_crosswalk_match(grouped_shap_crosswalk_rows):
    mapping = map_features_to_groups(["conflict_events"], grouped_shap_crosswalk_rows, "variable", "six_category")
    row = mapping.iloc[0]
    assert row["feature_name"] == "conflict_events"
    assert row["assigned_group"] == "conflict"
    assert row["match_method"] == "exact"
    assert row["matched_reference_feature"] == "conflict_events"
    assert not row["is_unmatched"]


def test_nowcasting_mapping_normalized_base_variants_preserve_original_names(grouped_shap_crosswalk_rows):
    features = ["food_price_index_lag1", "conflict_events_current", "market_access_3m", "missing_signal"]
    mapping = map_features_to_groups(features, grouped_shap_crosswalk_rows, "variable", "six_category")
    by_feature = mapping.set_index("feature_name")
    assert by_feature.loc["food_price_index_lag1", "assigned_group"] == "food prices"
    assert by_feature.loc["food_price_index_lag1", "match_method"] in {"normalized", "base_variable"}
    assert by_feature.loc["food_price_index_lag1", "matched_reference_feature"] == "food_price_index"
    assert by_feature.loc["conflict_events_current", "assigned_group"] == "conflict"
    assert by_feature.loc["market_access_3m", "assigned_group"] == "econ"
    assert by_feature.loc["missing_signal", "is_unmatched"]


def test_nowcasting_mapping_weather_forecast_seed_precedes_crosswalk(grouped_shap_crosswalk_rows, weather_forecast_feature_seeds):
    crosswalk = pd.concat(
        [grouped_shap_crosswalk_rows, pd.DataFrame({"variable": ["Rainf_f_tavg_mean_forecast_proxy"], "six_category": ["weather"]})],
        ignore_index=True,
    )
    mapping = map_features_to_groups(["Rainf_f_tavg_mean_forecast_proxy"], crosswalk, "variable", "six_category", weather_forecast_features=weather_forecast_feature_seeds)
    row = mapping.iloc[0]
    assert row["assigned_group"] == WEATHER_FORECAST_GROUP
    assert row["match_method"] == "weather_forecast"
    assert row["is_weather_forecast"]


def test_nowcasting_mapping_ambiguous_normalized_match_is_unresolved(grouped_shap_crosswalk_rows):
    crosswalk = pd.concat(
        [grouped_shap_crosswalk_rows, pd.DataFrame({"variable": ["food_price_index_current"], "six_category": ["econ"]})],
        ignore_index=True,
    )
    mapping = map_features_to_groups(["food_price_index_lag1"], crosswalk, "variable", "six_category")
    row = mapping.iloc[0]
    assert row["match_method"] == "ambiguous"
    assert row["is_unmatched"]
    assert not row["assigned_group"]


def test_nowcasting_unmatched_coverage_reports_abs_shap_share(grouped_shap_feature_matrix, grouped_shap_values, grouped_shap_crosswalk_rows):
    mapping = map_features_to_groups(grouped_shap_feature_matrix.columns, grouped_shap_crosswalk_rows, "variable", "six_category", weather_forecast_features={"Rainf_f_tavg_mean_forecast_proxy"})
    matched = mapping.loc[~mapping["is_unmatched"], "feature_name"]
    coverage = attribution_coverage_summary(grouped_shap_values, grouped_shap_feature_matrix.columns, matched)
    assert coverage["unmatched_feature_count"] == 1
    assert coverage["unmatched_features"] == ["unmapped_runtime_feature"]
    assert coverage["unmatched_abs_shap_sum"] == pytest.approx(0.30)
    assert 0 < coverage["unmatched_abs_shap_share"] < 1


def test_nonzero_six_category_relative_importance_sums_to_one():
    crosswalk, _ = validate_crosswalk(six_group_crosswalk(), ["a", "b", "c", "d", "e", "f"], "variable", "six_category")
    summary = per_feature_shap_summary(np.ones((2, 6)), list("abcdef"), crosswalk, "fs0", "0m", 2022, "train")
    long, diagnostics = aggregate_six_category_importance(summary, crosswalk["feature_group"].tolist(), "fs0", "0m", 2022, "train")
    assert diagnostics == []
    assert long["relative_importance"].sum() == pytest.approx(1.0)
    assert len(long) == 6


def test_zero_mapped_denominator_writes_six_zero_values_and_diagnostic():
    crosswalk, _ = validate_crosswalk(six_group_crosswalk(), ["a", "b", "c", "d", "e", "f"], "variable", "six_category")
    summary = per_feature_shap_summary(np.zeros((2, 6)), list("abcdef"), crosswalk, "fs0", "0m", 2022, "train")
    long, diagnostics = aggregate_six_category_importance(summary, crosswalk["feature_group"].tolist(), "fs0", "0m", 2022, "train")
    assert len(long) == 6
    assert long["relative_importance"].tolist() == [0.0] * 6
    assert diagnostics[0]["diagnostic_type"] == "zero denominator"


def test_complete_long_table_has_96_rows():
    groups = ["food prices", "geography", "econ", "conflict", "agriculture", "weather"]
    frames = []
    for scope in ("fs0", "fs1", "fs2", "fs3"):
        for year in (2022, 2023, 2024, 2025):
            summary = pd.DataFrame({"feature_group": groups, "abs_shap_sum": [1, 1, 1, 1, 1, 1]})
            frame, _ = aggregate_six_category_importance(summary, groups, scope, scope, year, "train")
            frames.append(frame)
    assert len(pd.concat(frames, ignore_index=True)) == 96


def test_scope_matrix_has_6x4_shape_and_preserves_crosswalk_labels():
    groups = ["food prices", "geography", "econ", "conflict", "agriculture", "weather"]
    frames = []
    for year in (2022, 2023, 2024, 2025):
        summary = pd.DataFrame({"feature_group": groups, "abs_shap_sum": [1, 1, 1, 1, 1, 1]})
        frame, _ = aggregate_six_category_importance(summary, groups, "fs0", "0m", year, "train")
        frames.append(frame)
    matrix = scope_matrix(pd.concat(frames, ignore_index=True), "fs0", groups)
    assert matrix.shape == (6, 5)
    assert matrix["feature_group"].tolist() == groups
    assert list(matrix.columns) == ["feature_group", "2022", "2023", "2024", "2025"]


def test_nowcasting_scope_group_matrix_has_seven_rows_and_canonical_scope_order():
    groups = ["food prices", "geography", "econ", "conflict", "agriculture", "weather", WEATHER_FORECAST_GROUP]
    long = pd.DataFrame(
        {
            "feature_group": ["food prices", WEATHER_FORECAST_GROUP, "food prices", WEATHER_FORECAST_GROUP],
            "scope_label": ["3m", "3m", "0m", "0m"],
            "relative_importance": [0.4, 0.6, 0.7, 0.3],
        }
    )
    matrix = nowcasting_scope_group_matrix(long, groups)
    assert matrix.shape == (7, 3)
    assert matrix["feature_group"].tolist() == groups
    assert list(matrix.columns) == ["feature_group", "0m", "3m"]
    assert [scope for scope in NOWCASTING_SCOPE_ORDER if scope in matrix.columns] == ["0m", "3m"]


def test_nowcasting_scope_heatmap_writes_subset_scope_artifact(tmp_path):
    groups = ["food prices", "geography", "econ", "conflict", "agriculture", "weather", WEATHER_FORECAST_GROUP]
    matrix = pd.DataFrame({"feature_group": groups, "3m": [0.1] * 7, "12m": [0.2] * 7})
    out = tmp_path / "phase3_worse_nowcasting_grouped_shap_heatmap.png"
    render_nowcasting_scope_heatmap(matrix, out)
    assert out.exists()


def test_nowcasting_scope_group_matrix_includes_zero_rows_for_expected_groups():
    groups = ["food prices", "geography", "econ", "conflict", "agriculture", "weather", WEATHER_FORECAST_GROUP]
    long = pd.DataFrame({"feature_group": ["food prices"], "scope_label": ["6m"], "relative_importance": [0.0]})
    matrix = nowcasting_scope_group_matrix(long, groups)
    assert matrix["feature_group"].tolist() == groups
    assert matrix["6m"].tolist() == [0.0] * 7


def test_heatmap_artifact_name_rejects_non_phase3_outputs():
    validate_phase3_artifact_name(pd.Timestamp("2022-01-01") and __import__("pathlib").Path("phase3_worse_fs0_heatmap.png"))
    for name in ("phase4_worse_fs0_heatmap.png", "phase5_worse_fs0_heatmap.png", "phase3_phase4_heatmap.png"):
        with pytest.raises(ValueError, match="Invalid phase-3"):
            validate_phase3_artifact_name(__import__("pathlib").Path(name))


def test_render_heatmap_writes_sample_type_caption_artifact(tmp_path):
    groups = ["food prices", "geography", "econ", "conflict", "agriculture", "weather"]
    matrix = pd.DataFrame({"feature_group": groups, "2022": [0.1] * 6, "2023": [0.2] * 6, "2024": [0.3] * 6, "2025": [0.4] * 6})
    out = tmp_path / "phase3_worse_fs0_heatmap.png"
    render_heatmap(matrix, out, "0m", "train")
    assert out.exists()


def test_raw_export_size_guard_refuses_oversized_output_without_override():
    frame = pd.DataFrame({"a": range(3)})
    enforce_raw_export_size(frame, 3, False)
    enforce_raw_export_size(frame, 1, True)
    with pytest.raises(ValueError, match="exceeding limit"):
        enforce_raw_export_size(frame, 1, False)
