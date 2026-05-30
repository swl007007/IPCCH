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
    prepared = ln.prepare_source(comprehensive_frame)
    featured, transform = ln.apply_identifier_features(prepared, _config())
    assert transform["lat_lon"] == "detected"
    assert any(c.startswith("month_") for c in featured.columns)
    train, _ = ln.build_training_frame(featured, _config())
    feats = ln.select_model_features(train)
    assert {"feat_x", "feat_y", "lat", "lon"}.issubset(set(feats))
    # Targets / target-derived / identifiers excluded
    for bad in ["overall_phase", "phase2_worse", "phase3_percent", "overall_phase_lag1", "area_id", "country", "region", "year", "month"]:
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
