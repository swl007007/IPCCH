from __future__ import annotations

import pandas as pd

from ipcch import launch_nowcasting as ln


def test_config_static_features_have_no_observed_area_level_variation():
    df = pd.DataFrame(
        {
            "area_id": ["A", "A", "B", "B"],
            "year": [2025, 2025, 2025, 2025],
            "month": [1, 2, 1, 2],
            "static_ok": [10.0, 10.0, None, 20.0],
            "dynamic": [1.0, 2.0, 3.0, 4.0],
        }
    )
    result = ln.classify_static_time_varying_features(df, ["static_ok", "dynamic"], config_static_features=["static_ok"])
    assert result.static_features == ["static_ok"]
    assert "dynamic" in result.time_varying_features
    assert result.inconsistent_static_features == []


def test_non_invariant_config_static_features_are_time_varying_and_inconsistent():
    df = pd.DataFrame(
        {
            "area_id": ["A", "A", "B", "B"],
            "year": [2025, 2025, 2025, 2025],
            "month": [1, 2, 1, 2],
            "candidate": [10.0, 11.0, 20.0, 20.0],
        }
    )
    result = ln.classify_static_time_varying_features(df, ["candidate"], config_static_features=["candidate"])
    assert result.static_features == []
    assert result.time_varying_features == ["candidate"]
    assert result.inconsistent_static_features == ["candidate"]


def test_one_period_only_area_does_not_prove_global_static_status():
    df = pd.DataFrame(
        {
            "area_id": ["A", "B", "B"],
            "year": [2025, 2025, 2025],
            "month": [1, 1, 2],
            "candidate": [10.0, 20.0, 21.0],
        }
    )
    result = ln.classify_static_time_varying_features(df, ["candidate"], config_static_features=["candidate"])
    assert result.static_features == []
    assert result.inconsistent_static_features == ["candidate"]


def test_missing_static_classification_infers_invariant_features():
    df = pd.DataFrame(
        {
            "area_id": ["A", "A", "B", "B"],
            "year": [2025, 2025, 2025, 2025],
            "month": [1, 2, 1, 2],
            "candidate": [10.0, 10.0, 20.0, 20.0],
            "dynamic": [1.0, 2.0, 3.0, 4.0],
        }
    )
    result = ln.classify_static_time_varying_features(df, ["candidate", "dynamic"])
    assert result.static_features == ["candidate"]
    assert result.time_varying_features == ["dynamic"]


def test_unresolved_static_inconsistency_can_raise_launch_error():
    df = pd.DataFrame(
        {
            "area_id": ["A", "A"],
            "year": [2025, 2025],
            "month": [1, 2],
            "candidate": [10.0, 11.0],
        }
    )
    try:
        ln.resolve_static_feature_classification(df, ["candidate"], config_static_features=["candidate"], fail_on_inconsistency=True)
    except ln.LaunchError as exc:
        assert "static classification inconsistency" in str(exc)
    else:
        raise AssertionError("expected LaunchError")
