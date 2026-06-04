from __future__ import annotations

from pathlib import Path
import shutil
import uuid

import numpy as np
import pandas as pd
import pytest

from ipcch import launch_nowcasting as ln


def _config(**kw) -> ln.LaunchConfig:
    defaults = dict(comprehensive_source=Path("dummy.csv"))
    defaults.update(kw)
    return ln.LaunchConfig(**defaults)


@pytest.fixture
def grouped_shap_output_roots():
    token = uuid.uuid4().hex[:8]
    out = ln.paths.RESULTS_DIR / "launch" / f"_pytest_grouped_shap_{token}"
    rep = ln.paths.REPORTS_DIR / "launch" / f"_pytest_grouped_shap_{token}"
    yield out, rep
    for path in (out, rep):
        shutil.rmtree(path, ignore_errors=True)


@pytest.fixture
def grouped_shap_config(grouped_shap_output_roots):
    out, rep = grouped_shap_output_roots
    return _config(out_root=out, report_root=rep, scope_months=3)


@pytest.fixture
def grouped_shap_mode_args(tmp_path):
    return {
        "train_and_predict": {"compute_grouped_shap": True},
        "predict_with_supplied_models": {"compute_grouped_shap": True, "skip_training": True, "model_artifact_dir": tmp_path / "models"},
        "report_from_supplied_predictions": {"compute_grouped_shap": True, "skip_prediction": True, "predictions": tmp_path / "predictions.csv"},
    }


# --- Scope config (005 launch scope foundation) ------------------------------


def test_launch_config_scope_defaults_to_zero():
    cfg = _config()
    assert cfg.scope_months == 0


def test_launch_config_accepts_supported_scope_values():
    assert _config(scope_months=0).scope_months == 0
    assert _config(scope_months=3).scope_months == 3
    assert _config(scope_months=6).scope_months == 6
    assert _config(scope_months=12).scope_months == 12


def test_launch_config_rejects_unsupported_scope_values():
    with pytest.raises(ln.LaunchError, match="scope_months must be one of"):
        _config(scope_months=2)


def test_default_and_explicit_scope_zero_have_equivalent_config_semantics():
    default = _config()
    explicit = _config(scope_months=0)
    assert default.scope_months == explicit.scope_months == 0
    assert default.launch_month == explicit.launch_month
    assert default.training_cutoff == explicit.training_cutoff


# --- Source validation (T005, FR-006/010) -----------------------------------

def test_validate_source_missing_identifier_columns(comprehensive_frame):
    df = comprehensive_frame.drop(columns=["month"])
    with pytest.raises(ln.LaunchError, match="missing required identifier columns"):
        ln.validate_source(df, _config())


def test_validate_source_no_april_rows_hard_stops(comprehensive_frame):
    df = comprehensive_frame[~((comprehensive_frame.year == 2026) & (comprehensive_frame.month == 4))].copy()
    with pytest.raises(ln.LaunchError, match="April 2026 rows is required"):
        ln.validate_source(df, _config())


def test_validate_source_ok_reports_counts(comprehensive_frame):
    summary = ln.validate_source(comprehensive_frame, _config())
    assert summary["launch_month_rows"] == 5
    assert summary["training_rows_before_cutoff"] > 0
    assert summary["checks"]["cumulative_targets_derivable"] is True


# --- Training filter incl. Feb/Mar 2026 (T006, FR-007, R4) -------------------

def test_training_frame_includes_feb_mar_2026_excludes_april(comprehensive_frame):
    prepared = ln.prepare_source(comprehensive_frame)
    train, summary = ln.build_training_frame(prepared, _config())
    assert train["date"].max() < pd.Timestamp("2026-04-01")
    assert "2026-02" in summary["rows_per_month"] and "2026-03" in summary["rows_per_month"]
    assert not ((train.year == 2026) & (train.month == 4)).any()


# --- April X_test preservation + dedup (T007, FR-008/009) --------------------

def test_xtest_preserves_all_label_less_areas(comprehensive_frame):
    prepared = ln.prepare_source(comprehensive_frame)
    april, coverage = ln.build_xtest_april(prepared, _config())
    assert coverage["launch_month_area_count"] == 5
    assert april["overall_phase"].isna().all()  # label-less April preserved


def test_duplicate_april_area_id_hard_stops_by_default(comprehensive_frame):
    dup = comprehensive_frame[(comprehensive_frame.year == 2026) & (comprehensive_frame.month == 4)].iloc[[0]]
    df = pd.concat([comprehensive_frame, dup], ignore_index=True)
    prepared = ln.prepare_source(df)
    with pytest.raises(ln.LaunchError, match="Duplicate launch-month area_id"):
        ln.build_xtest_april(prepared, _config())


def test_duplicate_april_resolved_with_latest_date_rule(comprehensive_frame):
    dup = comprehensive_frame[(comprehensive_frame.year == 2026) & (comprehensive_frame.month == 4)].iloc[[0]]
    df = pd.concat([comprehensive_frame, dup], ignore_index=True)
    prepared = ln.prepare_source(df)
    april, coverage = ln.build_xtest_april(prepared, _config(dedup_rule="latest-date"))
    assert coverage["launch_month_area_count"] == 5
    assert coverage["dedup"]["rows_dropped"] == 1
    assert coverage["dedup"]["candidate_counts"]


# --- Feature pipeline + exclusion audit (T008/T009, FR-011/012/013) ----------

def test_identifier_features_detected_and_features_exclude_targets(comprehensive_frame):
    frame = comprehensive_frame.copy()
    frame["estimated_population"] = range(len(frame))
    prepared = ln.prepare_source(frame)
    featured, transform = ln.apply_identifier_features(prepared, _config())
    assert transform["lat_lon"] == "detected"
    assert any(c.startswith("month_") for c in featured.columns)
    train, _ = ln.build_training_frame(featured, _config())
    feats = ln.select_model_features(train)
    assert {"feat_x", "feat_y", "lat", "lon", "estimated_population"}.issubset(set(feats))
    # Targets / target-derived / identifiers / launch metadata excluded
    for bad in ["overall_phase", "phase2_worse", "phase3_percent", "overall_phase_lag1", "area_id", "country", "region", "year", "month", "scope_months"]:
        assert bad not in feats


def test_feature_schema_report_audit_fields_and_warning(comprehensive_frame):
    prepared = ln.prepare_source(comprehensive_frame)
    featured, transform = ln.apply_identifier_features(prepared, _config())
    train, _ = ln.build_training_frame(featured, _config())
    april, _ = ln.build_xtest_april(featured, _config())
    feats = ln.select_model_features(train)
    schema, warnings = ln.build_feature_schema_report(featured, feats, train.columns, april.columns, transform)
    row = schema[schema.column == "overall_phase_lag1"].iloc[0]
    assert row["exclusion_family"] == "target_derived"
    assert row["matched_pattern"] in ("target", "overall_phase_lag")
    assert not row["included_in_model"]
    # phase percent target row
    pr = schema[schema.column == "phase3_percent"].iloc[0]
    assert pr["exclusion_family"] == "target_label"


def test_out_of_family_warning_fires(comprehensive_frame):
    # Add a numeric column that is neither target nor identifier but is intentionally excluded
    prepared = ln.prepare_source(comprehensive_frame)
    featured, transform = ln.apply_identifier_features(prepared, _config())
    train, _ = ln.build_training_frame(featured, _config())
    feats = [f for f in ln.select_model_features(train) if f != "feat_y"]  # drop one numeric feature
    schema, warnings = ln.build_feature_schema_report(featured, feats, train.columns, train.columns, transform)
    assert any("Out-of-family" in w for w in warnings)


# --- Grouped SHAP nowcasting helpers -----------------------------------------


def test_grouped_shap_training_matrix_uses_phase3_nonmissing_rows_in_feature_order():
    train = pd.DataFrame(
        {
            "phase3_worse": [0.2, np.nan, 0.8],
            "b": [2.0, 20.0, 200.0],
            "a": [1.0, 10.0, 100.0],
        },
        index=[10, 11, 12],
    )
    matrix = ln.build_phase3_grouped_shap_training_matrix(train, ["a", "b"])
    assert matrix.index.tolist() == [10, 12]
    assert matrix.columns.tolist() == ["a", "b"]
    assert matrix.to_dict("list") == {"a": [1.0, 100.0], "b": [2.0, 200.0]}


def test_grouped_shap_training_matrix_rejects_feature_order_mismatch():
    train = pd.DataFrame({"phase3_worse": [0.2], "a": [1.0]})
    with pytest.raises(ln.LaunchError, match="feature columns"):
        ln.build_phase3_grouped_shap_training_matrix(train, ["a", "missing"])


def test_grouped_shap_artifact_paths_are_reported_under_results_and_reports(grouped_shap_config):
    layout = ln.resolve_output_layout(grouped_shap_config)
    artifact_paths = ln.grouped_shap_artifact_paths(layout)
    assert artifact_paths["grouped_long"].is_relative_to(ln.paths.RESULTS_DIR)
    assert artifact_paths["grouped_matrix"].is_relative_to(ln.paths.RESULTS_DIR)
    assert artifact_paths["heatmap"].is_relative_to(ln.paths.REPORTS_DIR)


def test_run_summary_includes_grouped_shap_counts_coverage_and_paths(grouped_shap_config):
    layout = ln.resolve_output_layout(grouped_shap_config)
    grouped = {"enabled": True, "matched_feature_count": 2, "coverage": {"unmatched_feature_count": 1}}
    summary = ln.build_run_summary(grouped_shap_config, layout, {"training_rows": 3}, {"launch_month_area_count": 2}, ["a", "b"], {}, grouped_shap=grouped)
    assert summary["grouped_shap"] == grouped
    assert "grouped_shap" in summary["output_paths"]
    assert "metadata" in summary["output_paths"]["grouped_shap"]


def test_compute_nowcasting_grouped_shap_uses_phase3_model_and_ordered_matrix(tmp_path, monkeypatch, grouped_shap_config):
    class DummyModel:
        pass

    captured = {}

    def fake_compute(model, matrix, feature_columns):
        captured["model"] = model
        captured["matrix"] = matrix.copy()
        captured["feature_columns"] = list(feature_columns)
        return np.ones((len(matrix), len(feature_columns))), ln.fshap.ShapEngineInfo("fake", "0")

    crosswalk_path = tmp_path / "crosswalk.csv"
    expected_groups = ["food prices", "geography", "econ", "conflict", "agriculture", "weather", ln.fshap.WEATHER_FORECAST_GROUP]
    pd.DataFrame({"variable": ["a", "b", "c", "d", "e", "f"], "six_category": expected_groups[:6]}).to_csv(crosswalk_path, index=False)
    cfg = ln.LaunchConfig(
        comprehensive_source=Path("dummy.csv"),
        out_root=grouped_shap_config.out_root,
        report_root=grouped_shap_config.report_root,
        compute_grouped_shap=True,
        grouped_shap_crosswalk_path=crosswalk_path,
    )
    layout = ln.resolve_output_layout(cfg)
    train = pd.DataFrame({"phase3_worse": [0.2, np.nan], "a": [1.0, 10.0], "b": [2.0, 20.0]})
    model = DummyModel()
    monkeypatch.setattr(ln.fshap, "compute_phase3_shap_values", fake_compute)
    result = ln.compute_nowcasting_grouped_shap({"phase3_worse": model}, train, ["a", "b"], cfg, layout, weather_forecast_features=[])
    assert captured["model"] is model
    assert captured["matrix"].columns.tolist() == ["a", "b"]
    assert len(captured["matrix"]) == 1
    assert result["metadata_path"] == str(layout.grouped_shap_metadata_json)
    assert "unmatched_feature_diagnostics" not in result["artifact_paths"]
    matrix = pd.read_csv(layout.grouped_shap_matrix_csv)
    assert matrix["feature_group"].tolist() == expected_groups
    absent = matrix[matrix["feature_group"].isin(["econ", "conflict", "agriculture", "weather", ln.fshap.WEATHER_FORECAST_GROUP])]
    assert absent["0m"].tolist() == [0.0] * 5


# --- Forecasted weather feature handling -------------------------------------


def _weather_percent_rows(phase: int) -> dict:
    base = {f"phase{i}_percent": 0.0 for i in range(1, 6)}
    base[f"phase{phase}_percent"] = 1.0
    return base


def _weather_value(year: int, month: int, offset: int = 0) -> float:
    return float((year - 2024) * 12 + month - 7 + offset)


def _weather_frame() -> pd.DataFrame:
    rows = []
    periods = list(pd.period_range("2024-07", "2025-10", freq="M")) + [pd.Period("2026-04", freq="M")]
    for area in ["A", "B"]:
        offset = 0 if area == "A" else 1000
        for period in periods:
            year = int(period.year)
            month = int(period.month)
            phase = np.nan if str(period) == "2026-04" else int((period.ordinal % 4) + 1)
            rain = _weather_value(year, month, offset)
            temp = 280.0 + _weather_value(year, month, offset)
            row = {
                "area_id": area,
                "country": "X",
                "region": "R",
                "year": year,
                "month": month,
                "lat": 1.0,
                "lon": 2.0,
                "overall_phase": phase,
                "feat_x": rain,
                "Rainf_f_tavg_mean": rain,
                "Tair_f_tavg_mean": temp,
            }
            if pd.isna(phase):
                row.update({f"phase{i}_percent": np.nan for i in range(1, 6)})
            else:
                row.update(_weather_percent_rows(int(phase)))
            rows.append(row)
    return pd.DataFrame(rows)


def _forecast_weather_csv(tmp_path, start: str = "2026-04") -> Path:
    path = tmp_path / "forecast_weather.csv"
    rows = []
    for area in ["A", "B"]:
        offset = 0 if area == "A" else 1000
        for period in pd.period_range(start, "2026-10", freq="M"):
            month_index = int(period.month)
            rows.append({
                "area_id": area,
                "time": period.strftime("%b%Y").lower(),
                "Rainf_f_tavg_mean": float(month_index * 10 + offset),
                "Tair_f_tavg_mean": float(290 + month_index + offset),
            })
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def test_forecasted_weather_proxy_columns_are_scope_specific():
    assert ln.forecasted_weather_proxy_columns() == [
        "Rainf_f_tavg_mean_forecast_proxy",
        "Tair_f_tavg_mean_forecast_proxy",
    ]
    assert ln.forecasted_weather_proxy_columns(0) == []
    assert len(ln.forecasted_weather_proxy_columns(3)) == 8
    assert ln.forecasted_weather_proxy_columns(3) == [
        "Rainf_f_tavg_mean_forecast_proxy",
        "Tair_f_tavg_mean_forecast_proxy",
        "Rainf_f_tavg_mean_minus_1_forecast_proxy",
        "Tair_f_tavg_mean_minus_1_forecast_proxy",
        "Rainf_f_tavg_mean_minus_2_forecast_proxy",
        "Tair_f_tavg_mean_minus_2_forecast_proxy",
        "Rainf_f_tavg_mean_minus_3_forecast_proxy",
        "Tair_f_tavg_mean_minus_3_forecast_proxy",
    ]
    assert len(ln.forecasted_weather_proxy_columns(6)) == 14
    assert len(ln.forecasted_weather_proxy_columns(12)) == 14
    assert "Rainf_f_tavg_mean_minus_12_forecast_proxy" in ln.forecasted_weather_proxy_columns(12)


def test_forecasted_weather_disabled_keeps_training_and_xtest_schema_unchanged(tmp_path):
    prepared = ln.prepare_source(_weather_frame())
    cfg = _config(scope_months=3, training_cutoff="2026-01-01")
    train, _ = ln.build_training_frame(prepared, cfg)
    xtest, _ = ln.build_xtest_april(prepared, cfg)
    out_train, out_xtest, report = ln.apply_forecasted_weather_features(train, xtest, prepared, cfg)
    assert out_train.columns.tolist() == train.columns.tolist()
    assert out_xtest.columns.tolist() == xtest.columns.tolist()
    assert report["active"] is False


def test_forecasted_weather_scope0_is_noop_even_when_enabled(tmp_path):
    prepared = ln.prepare_source(_weather_frame())
    cfg = _config(scope_months=0, using_forecasted_weather=True, forecasted_weather_source=_forecast_weather_csv(tmp_path))
    train, _ = ln.build_training_frame(prepared, cfg)
    xtest, _ = ln.build_xtest_april(prepared, cfg)
    out_train, out_xtest, report = ln.apply_forecasted_weather_features(train, xtest, prepared, cfg)
    assert out_train.columns.tolist() == train.columns.tolist()
    assert out_xtest.columns.tolist() == xtest.columns.tolist()
    assert report["action"].startswith("scope_0_noop")


def test_scope3_forecasted_weather_uses_target_to_feature_window_for_train_and_inference(tmp_path):
    prepared = ln.prepare_source(_weather_frame())
    cfg = _config(scope_months=3, training_cutoff="2026-01-01", using_forecasted_weather=True, forecasted_weather_source=_forecast_weather_csv(tmp_path))
    train, _ = ln.build_training_frame(prepared, cfg)
    xtest, _ = ln.build_xtest_april(prepared, cfg)
    out_train, out_xtest, report = ln.apply_forecasted_weather_features(train, xtest, prepared, cfg)
    row = out_train[(out_train["area_id"] == "A") & (out_train["target_period"] == "2025-07")].iloc[0]
    assert row["Rainf_f_tavg_mean"] == _weather_value(2025, 4)
    assert row["weather_proxy_period"] == "2025-07"
    assert row["weather_proxy_period_target_minus_3"] == "2025-04"
    assert row["Rainf_f_tavg_mean_forecast_proxy"] == _weather_value(2025, 7)
    assert row["Rainf_f_tavg_mean_minus_1_forecast_proxy"] == _weather_value(2025, 6)
    assert row["Rainf_f_tavg_mean_minus_2_forecast_proxy"] == _weather_value(2025, 5)
    assert row["Rainf_f_tavg_mean_minus_3_forecast_proxy"] == _weather_value(2025, 4)
    xtest_row = out_xtest[out_xtest["area_id"] == "A"].iloc[0]
    assert xtest_row["weather_proxy_period"] == "2026-07"
    assert xtest_row["weather_proxy_period_target_minus_1"] == "2026-06"
    assert xtest_row["weather_proxy_period_target_minus_2"] == "2026-05"
    assert xtest_row["weather_proxy_period_target_minus_3"] == "2026-04"
    assert xtest_row["Rainf_f_tavg_mean_forecast_proxy"] == 70.0
    assert xtest_row["Rainf_f_tavg_mean_minus_1_forecast_proxy"] == 60.0
    assert xtest_row["Rainf_f_tavg_mean_minus_2_forecast_proxy"] == 50.0
    assert xtest_row["Rainf_f_tavg_mean_minus_3_forecast_proxy"] == 40.0
    assert report["inference"]["proxy_periods"] == ["2026-07"]
    assert report["inference"]["all_proxy_periods"] == ["2026-04", "2026-05", "2026-06", "2026-07"]
    assert "back through feature_month" in report["scope_note"]
    assert report["scope_mapping"]["forecast_weather_period"] == "2026-07"
    assert report["scope_mapping"]["forecast_weather_periods"] == ["2026-07", "2026-06", "2026-05", "2026-04"]
    features = ln.select_model_features(out_train)
    assert "Rainf_f_tavg_mean_minus_3_forecast_proxy" in features


def test_forecasted_weather_training_proxy_falls_back_to_raw_historical_weather(tmp_path, monkeypatch):
    source = _weather_frame().drop(columns=["Rainf_f_tavg_mean", "Tair_f_tavg_mean"])
    prepared = ln.prepare_source(source)
    raw_path = tmp_path / "raw_weather.csv"
    raw_rows = []
    for area, offset in [("A", 0), ("B", 1000)]:
        for period in pd.period_range("2024-07", "2025-10", freq="M"):
            year = int(period.year)
            month = int(period.month)
            raw_rows.append({
                "admin_code": area,
                "year": year,
                "month": month,
                "Rainf_f_tavg_mean": _weather_value(year, month, offset),
                "Tair_f_tavg_mean": 280.0 + _weather_value(year, month, offset),
            })
    pd.DataFrame(raw_rows).to_csv(raw_path, index=False)

    def fake_external_path(key):
        if key == ln.HISTORICAL_WEATHER_SOURCE_KEY:
            return raw_path
        raise KeyError(key)

    monkeypatch.setattr(ln.paths, "external_path", fake_external_path)
    cfg = _config(scope_months=3, training_cutoff="2026-01-01", using_forecasted_weather=True, forecasted_weather_source=_forecast_weather_csv(tmp_path))
    train, _ = ln.build_training_frame(prepared, cfg)
    xtest, _ = ln.build_xtest_april(prepared, cfg)

    out_train, out_xtest, report = ln.apply_forecasted_weather_features(train, xtest, prepared, cfg)

    row = out_train[(out_train["area_id"] == "A") & (out_train["target_period"] == "2025-07")].iloc[0]
    assert row["Rainf_f_tavg_mean_forecast_proxy"] == _weather_value(2025, 7)
    assert row["Rainf_f_tavg_mean_minus_2_forecast_proxy"] == _weather_value(2025, 5)
    assert row["Rainf_f_tavg_mean_minus_3_forecast_proxy"] == _weather_value(2025, 4)
    assert out_xtest.loc[out_xtest["area_id"] == "A", "Rainf_f_tavg_mean_forecast_proxy"].iloc[0] == 70.0
    assert out_xtest.loc[out_xtest["area_id"] == "A", "Rainf_f_tavg_mean_minus_3_forecast_proxy"].iloc[0] == 40.0
    assert report["training_proxy_source"] == str(raw_path)



def test_scope6_forecasted_weather_uses_target_to_feature_window_for_train_and_inference(tmp_path):
    prepared = ln.prepare_source(_weather_frame())
    cfg = _config(scope_months=6, training_cutoff="2026-01-01", using_forecasted_weather=True, forecasted_weather_source=_forecast_weather_csv(tmp_path))
    train, _ = ln.build_training_frame(prepared, cfg)
    xtest, _ = ln.build_xtest_april(prepared, cfg)
    out_train, out_xtest, report = ln.apply_forecasted_weather_features(train, xtest, prepared, cfg)
    row = out_train[(out_train["area_id"] == "A") & (out_train["target_period"] == "2025-07")].iloc[0]
    assert row["Rainf_f_tavg_mean"] == _weather_value(2025, 1)
    assert row["weather_proxy_period"] == "2025-07"
    assert row["weather_proxy_period_target_minus_6"] == "2025-01"
    assert row["Rainf_f_tavg_mean_forecast_proxy"] == _weather_value(2025, 7)
    assert row["Rainf_f_tavg_mean_minus_3_forecast_proxy"] == _weather_value(2025, 4)
    assert row["Rainf_f_tavg_mean_minus_6_forecast_proxy"] == _weather_value(2025, 1)
    xtest_row = out_xtest[out_xtest["area_id"] == "A"].iloc[0]
    assert xtest_row["weather_proxy_period"] == "2026-10"
    assert xtest_row["weather_proxy_period_target_minus_6"] == "2026-04"
    assert xtest_row["Tair_f_tavg_mean_forecast_proxy"] == 300.0
    assert xtest_row["Tair_f_tavg_mean_minus_6_forecast_proxy"] == 294.0
    assert len(report["inference"]["proxy_columns"]) == 14
    assert report["inference"]["proxy_periods"] == ["2026-10"]
    assert report["inference"]["all_proxy_periods"] == ["2026-04", "2026-05", "2026-06", "2026-07", "2026-08", "2026-09", "2026-10"]
    assert "back through feature_month" in report["scope_note"]
    assert report["scope_mapping"]["forecast_weather_period"] == "2026-10"


def test_scope12_forecasted_weather_uses_intermediate_to_feature_window_not_target_period(tmp_path):
    prepared = ln.prepare_source(_weather_frame())
    cfg = _config(scope_months=12, training_cutoff="2026-01-01", using_forecasted_weather=True, forecasted_weather_source=_forecast_weather_csv(tmp_path))
    train, _ = ln.build_training_frame(prepared, cfg)
    xtest, _ = ln.build_xtest_april(prepared, cfg)
    out_train, out_xtest, report = ln.apply_forecasted_weather_features(train, xtest, prepared, cfg)
    row = out_train[(out_train["area_id"] == "A") & (out_train["target_period"] == "2025-07")].iloc[0]
    assert row["feature_period"] == "2024-07"
    assert row["weather_proxy_period"] == "2025-01"
    assert row["weather_proxy_period_target_minus_7"] == "2024-12"
    assert row["weather_proxy_period_target_minus_12"] == "2024-07"
    assert row["Rainf_f_tavg_mean_forecast_proxy"] == _weather_value(2025, 1)
    assert row["Rainf_f_tavg_mean_minus_7_forecast_proxy"] == _weather_value(2024, 12)
    assert row["Rainf_f_tavg_mean_minus_12_forecast_proxy"] == _weather_value(2024, 7)
    xtest_row = out_xtest[out_xtest["area_id"] == "A"].iloc[0]
    assert xtest_row["weather_proxy_period"] == "2026-10"
    assert xtest_row["weather_proxy_period_target_minus_7"] == "2026-09"
    assert xtest_row["weather_proxy_period_target_minus_12"] == "2026-04"
    assert xtest_row["Rainf_f_tavg_mean_forecast_proxy"] == 100.0
    assert xtest_row["Rainf_f_tavg_mean_minus_12_forecast_proxy"] == 40.0
    assert report["inference"]["proxy_periods"] == ["2026-10"]
    assert report["inference"]["all_proxy_periods"] == ["2026-04", "2026-05", "2026-06", "2026-07", "2026-08", "2026-09", "2026-10"]
    assert "not the 12-month target horizon 2027-04" in report["scope_note"]
    assert report["scope_mapping"]["forecast_weather_period"] == "2026-10"
    assert report["scope_mapping"]["forecast_weather_periods"] == ["2026-10", "2026-09", "2026-08", "2026-07", "2026-06", "2026-05", "2026-04"]


def test_forecasted_weather_inference_falls_back_to_visible_weather_for_standing_month(tmp_path):
    prepared = ln.prepare_source(_weather_frame())
    cfg = _config(scope_months=3, training_cutoff="2026-01-01", using_forecasted_weather=True, forecasted_weather_source=_forecast_weather_csv(tmp_path, start="2026-05"))
    train, _ = ln.build_training_frame(prepared, cfg)
    xtest, _ = ln.build_xtest_april(prepared, cfg)
    _, out_xtest, report = ln.apply_forecasted_weather_features(train, xtest, prepared, cfg)
    xtest_row = out_xtest[out_xtest["area_id"] == "A"].iloc[0]
    assert xtest_row["weather_proxy_period_target_minus_3"] == "2026-04"
    assert xtest_row["Rainf_f_tavg_mean_minus_3_forecast_proxy"] == _weather_value(2026, 4)
    assert xtest_row["Rainf_f_tavg_mean_minus_2_forecast_proxy"] == 50.0
    assert report["inference_weather_fallback_source"]


@pytest.mark.parametrize("scope", [3, 6, 12])
def test_forecasted_weather_training_and_inference_share_window_definition(tmp_path, scope):
    prepared = ln.prepare_source(_weather_frame())
    cfg = _config(scope_months=scope, training_cutoff="2026-01-01", using_forecasted_weather=True, forecasted_weather_source=_forecast_weather_csv(tmp_path))
    train, _ = ln.build_training_frame(prepared, cfg)
    xtest, _ = ln.build_xtest_april(prepared, cfg)
    _, _, report = ln.apply_forecasted_weather_features(train, xtest, prepared, cfg)
    expected_columns = ln.forecasted_weather_proxy_columns(scope)
    assert report["proxy_columns"] == expected_columns
    assert report["training"]["proxy_columns"] == expected_columns
    assert report["inference"]["proxy_columns"] == expected_columns
    assert report["training"]["period_columns"] == report["inference"]["period_columns"]
    assert report["training"]["weather_window_target_minus_months"] == report["inference"]["weather_window_target_minus_months"]


# --- Prediction validation & non-finite handling (T016/T014, FR-017a) --------

def _pred_df(values):
    df = pd.DataFrame(values)
    df["area_id"] = [f"A{i}" for i in range(len(df))]
    return df


def test_clip_and_round_predictions():
    df = _pred_df([{"phase2_worse_pred": 1.4, "phase3_worse_pred": -0.2, "phase4_worse_pred": 0.123, "phase5_worse_pred": 0.0}])
    out, report = ln.validate_and_clip_predictions(df, _config())
    assert out["phase2_worse_pred"].iloc[0] == 1.0  # clipped high
    assert out["phase3_worse_pred"].iloc[0] == 0.0  # clipped low
    assert out["phase4_worse_pred"].iloc[0] == 0.12  # rounded 2dp
    assert report["clipped_high"]["phase2_worse_pred"] == 1
    assert report["clipped_low"]["phase3_worse_pred"] == 1


def test_nonfinite_predictions_fail_by_default():
    df = _pred_df([{"phase2_worse_pred": np.nan, "phase3_worse_pred": 0.1, "phase4_worse_pred": 0.0, "phase5_worse_pred": 0.0}])
    with pytest.raises(ln.LaunchError, match="Non-finite"):
        ln.validate_and_clip_predictions(df, _config())


def test_nonfinite_predictions_excluded_with_flag():
    df = _pred_df([
        {"phase2_worse_pred": np.inf, "phase3_worse_pred": 0.1, "phase4_worse_pred": 0.0, "phase5_worse_pred": 0.0},
        {"phase2_worse_pred": 0.3, "phase3_worse_pred": 0.1, "phase4_worse_pred": 0.0, "phase5_worse_pred": 0.0},
    ])
    out, report = ln.validate_and_clip_predictions(df, _config(drop_nonfinite_predictions=True))
    assert len(out) == 1 and report["rows_excluded"] == 1


# --- Phase derivation equivalence to canonical top-down (T017a, R6) ----------

def _canonical_top_down(df, threshold=0.2):
    phases = pd.Series(1, index=df.index, dtype=int)
    for p in (5, 4, 3, 2):
        mask = (phases == 1) & (df[f"phase{p}_worse_pred"] >= threshold)
        phases[mask] = p
    return phases


def test_derive_overall_phase_matches_canonical_top_down():
    cases = _pred_df([
        {"phase2_worse_pred": 0.10, "phase3_worse_pred": 0.00, "phase4_worse_pred": 0.00, "phase5_worse_pred": 0.00},  # ->1
        {"phase2_worse_pred": 0.50, "phase3_worse_pred": 0.19, "phase4_worse_pred": 0.00, "phase5_worse_pred": 0.00},  # ->2
        {"phase2_worse_pred": 0.60, "phase3_worse_pred": 0.20, "phase4_worse_pred": 0.05, "phase5_worse_pred": 0.00},  # ->3 (boundary)
        {"phase2_worse_pred": 0.80, "phase3_worse_pred": 0.50, "phase4_worse_pred": 0.25, "phase5_worse_pred": 0.05},  # ->4
        {"phase2_worse_pred": 0.90, "phase3_worse_pred": 0.70, "phase4_worse_pred": 0.40, "phase5_worse_pred": 0.20},  # ->5
    ])
    derived = ln.derive_overall_phase(cases, 0.2).astype(int)
    expected = _canonical_top_down(cases, 0.2)
    assert list(derived) == list(expected) == [1, 2, 3, 4, 5]


# --- Forbidden-source negative constraint (T038a, FR-005/FR-037) -------------

FORBIDDEN_TOKENS = ("scope_0m_model_ready", "april_only_interim", "multiscope")


def test_launch_reads_only_comprehensive_source(comprehensive_frame, tmp_path, monkeypatch):
    src = tmp_path / "comprehensive.csv"
    comprehensive_frame.to_csv(src, index=False)
    reads: list[str] = []
    real_read = ln.pd.read_csv

    def _spy(path, *a, **k):
        reads.append(str(path))
        return real_read(path, *a, **k)

    monkeypatch.setattr(ln.pd, "read_csv", _spy)
    # Resolve + load + validate-only (no training); only the comprehensive source should be read.
    config = ln.LaunchConfig(comprehensive_source=src, out_root=tmp_path / "out", report_root=tmp_path / "rep")
    df = ln.load_comprehensive_source(config.comprehensive_source)
    prepared = ln.prepare_source(df)
    ln.build_training_frame(prepared, config)
    ln.build_xtest_april(prepared, config)
    ln.apply_identifier_features(prepared, config)  # lat/lon present -> no lookup read
    assert reads == [str(src)]
    for token in FORBIDDEN_TOKENS:
        assert all(token not in r for r in reads)


def test_launch_modules_do_not_import_multiscope_builder():
    import ipcch.launch_nowcasting as m1
    import ipcch.launch_comparison as m2
    import ipcch.launch_visualizations as m3
    import inspect
    for mod in (m1, m2, m3):
        src = inspect.getsource(mod)
        for token in ("multiscope", "scope_0m_model_ready"):
            # token may appear only inside the documented forbidden-list constant, not as an import/read
            assert "import multiscope" not in src
            assert "external_path(\"deep_features_scope_0m_model_ready_dataset\")" not in src
