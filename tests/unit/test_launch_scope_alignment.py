from __future__ import annotations

from pathlib import Path

import pandas as pd

from ipcch import launch_nowcasting as ln


def test_add_months_supports_scope_offsets_and_year_boundaries():
    assert ln.add_months(pd.Period("2026-04", freq="M"), 0) == pd.Period("2026-04", freq="M")
    assert ln.add_months(pd.Period("2026-04", freq="M"), 3) == pd.Period("2026-07", freq="M")
    assert ln.add_months(pd.Period("2026-04", freq="M"), 6) == pd.Period("2026-10", freq="M")
    assert ln.add_months(pd.Period("2025-11", freq="M"), 3) == pd.Period("2026-02", freq="M")
    assert ln.add_months(pd.Period("2026-04", freq="M"), 12) == pd.Period("2027-04", freq="M")


def test_subtract_months_supports_scope_offsets_and_year_boundaries():
    assert ln.subtract_months(pd.Period("2025-07", freq="M"), 3) == pd.Period("2025-04", freq="M")
    assert ln.subtract_months(pd.Period("2026-01", freq="M"), 6) == pd.Period("2025-07", freq="M")
    assert ln.subtract_months(pd.Period("2027-04", freq="M"), 12) == pd.Period("2026-04", freq="M")


def test_monthly_period_from_year_month():
    df = pd.DataFrame({"year": [2026], "month": [4]})
    period = ln.monthly_period_from_year_month(df["year"], df["month"])
    assert period.iloc[0] == pd.Period("2026-04", freq="M")


def test_target_periods_for_april_2026_scope_examples():
    feature_period = pd.Period("2026-04", freq="M")
    assert ln.target_period_for_scope(feature_period, 0) == pd.Period("2026-04", freq="M")
    assert ln.target_period_for_scope(feature_period, 3) == pd.Period("2026-07", freq="M")
    assert ln.target_period_for_scope(feature_period, 6) == pd.Period("2026-10", freq="M")
    assert ln.target_period_for_scope(feature_period, 12) == pd.Period("2027-04", freq="M")


def _scoped_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "area_id": ["A", "A", "A", "A", "B", "B"],
            "year": [2025, 2025, 2025, 2025, 2025, 2025],
            "month": [1, 4, 7, 10, 4, 7],
            "overall_phase": [1, 2, 3, 4, 2, 5],
            "phase1_percent": [0.8, 0.5, 0.2, 0.1, 0.5, 0.1],
            "phase2_percent": [0.2, 0.3, 0.3, 0.2, 0.3, 0.1],
            "phase3_percent": [0.0, 0.2, 0.3, 0.3, 0.2, 0.3],
            "phase4_percent": [0.0, 0.0, 0.2, 0.3, 0.0, 0.3],
            "phase5_percent": [0.0, 0.0, 0.0, 0.1, 0.0, 0.2],
            "time_feature": [1, 4, 7, 10, 40, 70],
            "static_feature": [100, 100, 100, 100, 200, 200],
        }
    )


def test_scope3_alignment_uses_same_area_three_month_prior_features():
    prepared = ln.prepare_source(_scoped_frame())
    cfg = ln.LaunchConfig(comprehensive_source=Path("dummy.csv"), scope_months=3, training_cutoff="2026-01-01")
    aligned, _ = ln.build_training_frame(prepared, cfg, static_features=["static_feature"])
    row = aligned[(aligned["area_id"] == "A") & (aligned["year"] == 2025) & (aligned["month"] == 7)].iloc[0]
    assert row["time_feature"] == 4
    assert row["static_feature"] == 100
    assert row["feature_period"] == "2025-04"
    assert row["target_period"] == "2025-07"


def test_scope6_alignment_uses_calendar_month_join_not_row_shift():
    prepared = ln.prepare_source(_scoped_frame())
    cfg = ln.LaunchConfig(comprehensive_source="dummy.csv", scope_months=6, training_cutoff="2026-01-01")
    aligned, _ = ln.build_training_frame(prepared, cfg, static_features=["static_feature"])
    row = aligned[(aligned["area_id"] == "A") & (aligned["year"] == 2025) & (aligned["month"] == 7)].iloc[0]
    assert row["time_feature"] == 1
    assert row["feature_period"] == "2025-01"


def test_scoped_alignment_never_borrows_across_area_ids():
    prepared = ln.prepare_source(_scoped_frame())
    cfg = ln.LaunchConfig(comprehensive_source="dummy.csv", scope_months=3, training_cutoff="2026-01-01")
    aligned, _ = ln.build_training_frame(prepared, cfg, static_features=["static_feature"])
    row = aligned[(aligned["area_id"] == "B") & (aligned["year"] == 2025) & (aligned["month"] == 7)].iloc[0]
    assert row["time_feature"] == 40
    assert row["static_feature"] == 200


def test_scope3_launch_prediction_uses_april_features_not_future_months():
    df = pd.DataFrame({
        "area_id": ["A", "A", "A", "A"],
        "year": [2026, 2026, 2026, 2026],
        "month": [4, 5, 6, 7],
        "time_feature": [4, 5, 6, 7],
    })
    prepared = ln.prepare_source(df)
    cfg = ln.LaunchConfig(comprehensive_source="dummy.csv", scope_months=3)
    launch, _ = ln.build_launch_prediction_frame(prepared, cfg)
    assert launch["time_feature"].tolist() == [4]
    assert launch["target_period"].tolist() == ["2026-07"]


def test_scope6_launch_prediction_uses_april_features_not_future_months():
    df = pd.DataFrame({
        "area_id": ["A"] * 7,
        "year": [2026] * 7,
        "month": [4, 5, 6, 7, 8, 9, 10],
        "time_feature": [4, 5, 6, 7, 8, 9, 10],
    })
    prepared = ln.prepare_source(df)
    cfg = ln.LaunchConfig(comprehensive_source="dummy.csv", scope_months=6)
    launch, _ = ln.build_launch_prediction_frame(prepared, cfg)
    assert launch["time_feature"].tolist() == [4]
    assert launch["target_period"].tolist() == ["2026-10"]


def test_scope12_launch_prediction_uses_april_features_for_next_april_target():
    df = pd.DataFrame({
        "area_id": ["A"] * 3,
        "year": [2026, 2026, 2027],
        "month": [4, 10, 4],
        "time_feature": [4, 10, 404],
    })
    prepared = ln.prepare_source(df)
    cfg = ln.LaunchConfig(comprehensive_source="dummy.csv", scope_months=12)
    launch, _ = ln.build_launch_prediction_frame(prepared, cfg)
    assert launch["time_feature"].tolist() == [4]
    assert launch["feature_period"].tolist() == ["2026-04"]
    assert launch["target_period"].tolist() == ["2027-04"]
