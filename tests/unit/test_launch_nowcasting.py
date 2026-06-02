from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ipcch import launch_nowcasting as ln


def _config(**kw) -> ln.LaunchConfig:
    defaults = dict(comprehensive_source=Path("dummy.csv"))
    defaults.update(kw)
    return ln.LaunchConfig(**defaults)


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


# --- Forecasted weather feature handling -------------------------------------


def _weather_percent_rows(phase: int) -> dict:
    base = {f"phase{i}_percent": 0.0 for i in range(1, 6)}
    base[f"phase{phase}_percent"] = 1.0
    return base


def _weather_frame() -> pd.DataFrame:
    rows = []
    for area in ["A", "B"]:
        offset = 0 if area == "A" else 1000
        for year, month, rain, temp, phase in [
            (2024, 7, -5.0, 275.0, 1),
            (2024, 10, -2.0, 278.0, 2),
            (2025, 1, 1.0, 280.0, 1),
            (2025, 4, 4.0, 284.0, 2),
            (2025, 7, 7.0, 287.0, 3),
            (2025, 10, 10.0, 290.0, 4),
            (2026, 4, 16.0, 296.0, np.nan),
        ]:
            row = {
                "area_id": area,
                "country": "X",
                "region": "R",
                "year": year,
                "month": month,
                "lat": 1.0,
                "lon": 2.0,
                "overall_phase": phase,
                "feat_x": rain + offset,
                "Rainf_f_tavg_mean": rain + offset,
                "Tair_f_tavg_mean": temp + offset,
            }
            if pd.isna(phase):
                row.update({f"phase{i}_percent": np.nan for i in range(1, 6)})
            else:
                row.update(_weather_percent_rows(int(phase)))
            rows.append(row)
    return pd.DataFrame(rows)


def _forecast_weather_csv(tmp_path) -> Path:
    path = tmp_path / "forecast_weather.csv"
    pd.DataFrame(
        [
            {"area_id": "A", "time": "apr2026", "Rainf_f_tavg_mean": 40.0, "Tair_f_tavg_mean": 299.0},
            {"area_id": "A", "time": "jul2026", "Rainf_f_tavg_mean": 70.0, "Tair_f_tavg_mean": 300.0},
            {"area_id": "A", "time": "oct2026", "Rainf_f_tavg_mean": 100.0, "Tair_f_tavg_mean": 303.0},
            {"area_id": "B", "time": "apr2026", "Rainf_f_tavg_mean": 1040.0, "Tair_f_tavg_mean": 1299.0},
            {"area_id": "B", "time": "jul2026", "Rainf_f_tavg_mean": 1070.0, "Tair_f_tavg_mean": 1300.0},
            {"area_id": "B", "time": "oct2026", "Rainf_f_tavg_mean": 1100.0, "Tair_f_tavg_mean": 1303.0},
        ]
    ).to_csv(path, index=False)
    return path


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


def test_scope3_forecasted_weather_uses_target_period_proxy_for_train_and_inference(tmp_path):
    prepared = ln.prepare_source(_weather_frame())
    cfg = _config(scope_months=3, training_cutoff="2026-01-01", using_forecasted_weather=True, forecasted_weather_source=_forecast_weather_csv(tmp_path))
    train, _ = ln.build_training_frame(prepared, cfg)
    xtest, _ = ln.build_xtest_april(prepared, cfg)
    out_train, out_xtest, report = ln.apply_forecasted_weather_features(train, xtest, prepared, cfg)
    row = out_train[(out_train["area_id"] == "A") & (out_train["target_period"] == "2025-07")].iloc[0]
    assert row["Rainf_f_tavg_mean"] == 4.0
    assert row["Rainf_f_tavg_mean_forecast_proxy"] == 7.0
    assert out_xtest.loc[out_xtest["area_id"] == "A", "weather_proxy_period"].iloc[0] == "2026-07"
    assert out_xtest.loc[out_xtest["area_id"] == "A", "Rainf_f_tavg_mean_forecast_proxy"].iloc[0] == 70.0
    assert report["inference"]["proxy_periods"] == ["2026-07"]
    assert "target_month weather as the forecast proxy" in report["scope_note"]
    assert report["scope_mapping"]["forecast_weather_period"] == "2026-07"


def test_forecasted_weather_training_proxy_falls_back_to_raw_historical_weather(tmp_path, monkeypatch):
    source = _weather_frame().drop(columns=["Rainf_f_tavg_mean", "Tair_f_tavg_mean"])
    prepared = ln.prepare_source(source)
    raw_path = tmp_path / "raw_weather.csv"
    raw_rows = []
    for area, offset in [("A", 0), ("B", 1000)]:
        for year, month, rain, temp in [
            (2024, 10, -2.0, 278.0),
            (2025, 1, 1.0, 280.0),
            (2025, 4, 4.0, 284.0),
            (2025, 7, 7.0, 287.0),
            (2025, 10, 10.0, 290.0),
            (2026, 7, 70.0, 300.0),
        ]:
            raw_rows.append({"admin_code": area, "year": year, "month": month, "Rainf_f_tavg_mean": rain + offset, "Tair_f_tavg_mean": temp + offset})
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
    assert row["Rainf_f_tavg_mean_forecast_proxy"] == 7.0
    assert out_xtest.loc[out_xtest["area_id"] == "A", "Rainf_f_tavg_mean_forecast_proxy"].iloc[0] == 70.0
    assert report["training_proxy_source"] == str(raw_path)



def test_scope6_forecasted_weather_uses_october_2026_forecast(tmp_path):
    prepared = ln.prepare_source(_weather_frame())
    cfg = _config(scope_months=6, training_cutoff="2026-01-01", using_forecasted_weather=True, forecasted_weather_source=_forecast_weather_csv(tmp_path))
    train, _ = ln.build_training_frame(prepared, cfg)
    xtest, _ = ln.build_xtest_april(prepared, cfg)
    out_train, out_xtest, report = ln.apply_forecasted_weather_features(train, xtest, prepared, cfg)
    row = out_train[(out_train["area_id"] == "A") & (out_train["target_period"] == "2025-07")].iloc[0]
    assert row["Rainf_f_tavg_mean"] == 1.0
    assert row["Rainf_f_tavg_mean_forecast_proxy"] == 7.0
    assert out_xtest.loc[out_xtest["area_id"] == "A", "weather_proxy_period"].iloc[0] == "2026-10"
    assert out_xtest.loc[out_xtest["area_id"] == "A", "Tair_f_tavg_mean_forecast_proxy"].iloc[0] == 303.0
    assert report["inference"]["proxy_periods"] == ["2026-10"]
    assert "target_month weather as the forecast proxy" in report["scope_note"]
    assert report["scope_mapping"]["forecast_weather_period"] == "2026-10"


def test_scope12_forecasted_weather_uses_six_month_intermediate_proxy_not_target_period(tmp_path):
    prepared = ln.prepare_source(_weather_frame())
    cfg = _config(scope_months=12, training_cutoff="2026-01-01", using_forecasted_weather=True, forecasted_weather_source=_forecast_weather_csv(tmp_path))
    train, _ = ln.build_training_frame(prepared, cfg)
    xtest, _ = ln.build_xtest_april(prepared, cfg)
    out_train, out_xtest, report = ln.apply_forecasted_weather_features(train, xtest, prepared, cfg)
    row = out_train[(out_train["area_id"] == "A") & (out_train["target_period"] == "2025-07")].iloc[0]
    assert row["feature_period"] == "2024-07"
    assert row["weather_proxy_period"] == "2025-01"
    assert row["Rainf_f_tavg_mean_forecast_proxy"] == 1.0
    assert out_xtest.loc[out_xtest["area_id"] == "A", "weather_proxy_period"].iloc[0] == "2026-10"
    assert out_xtest.loc[out_xtest["area_id"] == "A", "Rainf_f_tavg_mean_forecast_proxy"].iloc[0] == 100.0
    assert report["inference"]["proxy_periods"] == ["2026-10"]
    assert "six-month intermediate forecast weather for 2026-10" in report["scope_note"]
    assert report["scope_mapping"]["forecast_weather_period"] == "2026-10"


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
