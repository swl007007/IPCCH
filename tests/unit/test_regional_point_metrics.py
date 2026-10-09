import sys

import numpy as np
import pandas as pd
import pytest

from ipcch import regional_point_metrics as rpm


def _pred(rows):
    """rows: (area_id, year, month, overall_phase, overall_phase_pred, phase3_worse, phase3_pred)."""
    df = pd.DataFrame(rows, columns=["area_id", "year", "month", "overall_phase", "overall_phase_pred", "phase3_worse", "phase3_pred"])
    return df


REGION_MAP = pd.Series({1: 0, 2: 0, 3: 1, 4: 2}, name="region")


def _value(rows, scope, region, period, metric):
    hit = [r for r in rows if r["scope"] == scope and r["region"] == region and r["period"] == period and r["metric"] == metric]
    assert len(hit) == 1
    return hit[0]


def test_metrics_match_hand_formulas_and_keep_empty_and_small_regions():
    pred = rpm.assign_regions(_pred([
        (1, 2022, 1, 3, 3, 0.5, 0.4), (2, 2022, 1, 1, 3, 0.0, 0.3), (1, 2023, 2, 4, 2, 0.6, 0.1),
        (3, 2023, 1, 2, 2, 0.1, 0.1), (3, 2025, 1, 2, 1, 0.1, 0.0),
    ]), REGION_MAP)
    rows = rpm.metric_rows(pred, "r", "a", 3)
    # region 0 pooled: truths 3,1,4 vs preds 3,3,2 -> exact 1/3; 3+ obs [1,0,1] pred [1,1,0]
    assert _value(rows, "region", 0, "pooled", "exact_phase_accuracy")["value"] == pytest.approx(1 / 3)
    assert _value(rows, "region", 0, "pooled", "precision_phase3plus")["value"] == pytest.approx(1 / 2)
    assert _value(rows, "region", 0, "pooled", "sensitivity_phase3plus")["value"] == pytest.approx(1 / 2)
    assert _value(rows, "region", 0, "pooled", "f2_phase3plus")["value"] == pytest.approx(5 * 0.25 / (4 * 0.5 + 0.5))
    assert _value(rows, "region", 0, "pooled", "ordinal_mae")["value"] == pytest.approx((0 + 2 + 2) / 3)
    t, s = np.array([0.5, 0.0, 0.6]), np.array([0.4, 0.3, 0.1])
    assert _value(rows, "region", 0, "pooled", "r2_phase3plus")["value"] == pytest.approx(1 - ((t - s) ** 2).sum() / ((t - t.mean()) ** 2).sum())
    assert _value(rows, "region", 0, "pooled", "mae_phase3plus")["value"] == pytest.approx(np.abs(t - s).mean())
    # region 1 has no observed 3+ and no predicted 3+: precision/recall/F2 undefined, others defined
    r1 = {m: _value(rows, "region", 1, "pooled", m) for m in ("precision_phase3plus", "sensitivity_phase3plus", "f2_phase3plus", "phase3plus_accuracy")}
    assert r1["precision_phase3plus"]["value"] is None and "predicted" in r1["precision_phase3plus"]["reason"]
    assert r1["sensitivity_phase3plus"]["value"] is None and "observed" in r1["sensitivity_phase3plus"]["reason"]
    assert r1["f2_phase3plus"]["value"] is None and r1["phase3plus_accuracy"]["value"] == 1.0
    assert _value(rows, "region", 1, "pooled", "r2_phase3plus")["value"] is None  # constant target
    # region 2 has an area in the map but no rows; region 8 has neither: both kept, all undefined, n_rows 0
    for region in (2, 8):
        r = _value(rows, "region", region, "2024", "exact_phase_accuracy")
        assert r["value"] is None and r["n_rows"] == 0 and r["reason"] == "no eligible samples"
    # single-row region-year (region 0, 2023): defined accuracy, undefined R2
    assert _value(rows, "region", 0, "2023", "exact_phase_accuracy")["value"] == 0.0
    assert _value(rows, "region", 0, "2023", "r2_phase3plus")["value"] is None
    assert len(rows) == 10 * 5 * 8  # global + regions 0..8, four years + pooled, eight metrics


def test_pooled_is_computed_from_rows_not_averaged():
    pred = rpm.assign_regions(_pred([(1, 2022, 1, 3, 3, 0.5, 0.5), (1, 2023, 1, 1, 3, 0.0, 0.3), (2, 2023, 1, 1, 1, 0.0, 0.0),
                                     (2, 2023, 2, 1, 1, 0.0, 0.0)]), REGION_MAP)
    rows = rpm.metric_rows(pred, "r", "a", 3)
    assert _value(rows, "global", None, "pooled", "exact_phase_accuracy")["value"] == pytest.approx(3 / 4)
    annual = [_value(rows, "global", None, str(y), "exact_phase_accuracy")["value"] for y in (2022, 2023)]
    assert np.mean(annual) != pytest.approx(3 / 4)


def test_missing_membership_and_bad_maps_fail(tmp_path):
    with pytest.raises(ValueError, match="no region membership"):
        rpm.assign_regions(_pred([(9, 2022, 1, 1, 1, 0.0, 0.0)]), REGION_MAP)
    path = tmp_path / "map.csv"
    pd.DataFrame({"area_id": [1, 1], "region": [0, 1]}).to_csv(path, index=False)
    with pytest.raises(ValueError, match="duplicate"):
        rpm.load_region_map(path)
    pd.DataFrame({"area_id": [1], "region": [9]}).to_csv(path, index=False)
    with pytest.raises(ValueError, match="outside"):
        rpm.load_region_map(path)
    with pytest.raises(ValueError, match="sha256"):
        rpm.load_region_map(path, "0" * 64)


def test_pairing_requires_equal_keys_and_truth_and_deltas_propagate_undefined():
    base = rpm.assign_regions(_pred([(1, 2022, 1, 3, 1, 0.5, 0.1), (3, 2022, 1, 1, 1, 0.0, 0.0)]), REGION_MAP)
    orc = base.copy()
    orc.loc[0, "overall_phase_pred"] = 3
    orc.loc[0, "phase3_pred"] = 0.45
    a, b = rpm.align_pair(orc.iloc[::-1], base)
    assert a["area_id"].tolist() == [1, 3]
    with pytest.raises(ValueError, match="same evaluation keys"):
        rpm.align_pair(orc.iloc[:1], base)
    bad = orc.copy()
    bad.loc[0, "overall_phase"] = 4
    with pytest.raises(ValueError, match="truth"):
        rpm.align_pair(bad, base)
    metrics = pd.DataFrame(rpm.metric_rows(a, "o", "oracle", 3) + rpm.metric_rows(b, "b", "base", 3))
    deltas = pd.DataFrame(rpm.delta_rows(metrics, "oracle", "base", [3]))
    g = deltas[(deltas.scope == "global") & (deltas.period == "pooled")].set_index("metric")
    assert g.loc["exact_phase_accuracy", "delta"] == pytest.approx(0.5)
    assert g.loc["precision_phase3plus", "status"] == "undefined" and "baseline" in g.loc["precision_phase3plus", "reason"]
    assert g.loc["sensitivity_phase3plus", "delta"] == pytest.approx(1.0)


def test_partition_and_no_bootstrap_or_fitting_imports():
    pred = rpm.assign_regions(_pred([(1, 2022, 1, 1, 1, 0.0, 0.0), (4, 2025, 1, 1, 1, 0.0, 0.0)]), REGION_MAP)
    part = rpm.partition_check(pred)
    assert part["pooled"][0] == 1 and part["pooled"][2] == 1 and sum(part["pooled"].values()) == 2
    assert "ipcch.regional_bootstrap" not in sys.modules or "regional_bootstrap" not in rpm.__dict__
    assert "xgboost" not in rpm.__dict__ and "regional_bootstrap" not in open(rpm.__file__).read().split('"""', 2)[2]
