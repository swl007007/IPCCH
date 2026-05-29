"""Shared fixtures for the April 2026 nowcasting launch tests.

Builds a tiny synthetic comprehensive feature CSV: pre-cutoff valid-target rows
(incl. 2026-02/03) plus label-less April 2026 rows, with lat/lon present (so no
identifier lookup is needed) and a couple of numeric features + a target-derived
diagnostic column to exercise exclusion. No heavy training occurs here.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


def _percent_rows(phase: int) -> dict:
    """Phase-percentage columns that decode to overall_phase=`phase` under th=0.2 top-down."""
    base = {f"phase{i}_percent": 0.0 for i in range(1, 6)}
    if phase == 1:
        base["phase1_percent"] = 0.9
    elif phase == 2:
        base.update(phase1_percent=0.5, phase2_percent=0.4, phase3_percent=0.1)
    elif phase == 3:
        base.update(phase1_percent=0.3, phase2_percent=0.3, phase3_percent=0.3, phase4_percent=0.1)
    elif phase == 4:
        base.update(phase1_percent=0.1, phase2_percent=0.2, phase3_percent=0.3, phase4_percent=0.3, phase5_percent=0.1)
    else:  # 5
        base.update(phase1_percent=0.1, phase2_percent=0.1, phase3_percent=0.2, phase4_percent=0.3, phase5_percent=0.3)
    return base


def build_comprehensive_frame(rng_seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(rng_seed)
    areas = [("A", "Somalia", "East Africa", 45.0, 2.0),
             ("B", "Somalia", "East Africa", 46.0, 3.0),
             ("C", "Nigeria", "West Africa", 8.0, 9.0),
             ("D", "Guatemala", "Latin America", -90.0, 15.0),
             ("E", "Haiti", "Latin America", -72.0, 19.0)]
    rows = []
    # Training months: 2024-06, 2024-12, 2025-06, 2025-12, 2026-01, 2026-02, 2026-03
    train_periods = [(2024, 6), (2024, 12), (2025, 6), (2025, 12), (2026, 1), (2026, 2), (2026, 3)]
    for (aid, country, region, lon, lat) in areas:
        for k, (yr, mo) in enumerate(train_periods):
            phase = 1 + ((hash((aid, yr, mo)) % 5))
            row = {"area_id": aid, "country": country, "region": region, "year": yr, "month": mo,
                   "lat": lat, "lon": lon, "overall_phase": phase,
                   "feat_x": float(rng.normal()), "feat_y": float(rng.normal()) + phase,
                   "overall_phase_lag1": float(phase - 1)}  # target-derived diagnostic
            row.update(_percent_rows(phase))
            rows.append(row)
        # April 2026 prediction rows: NO labels (missing overall_phase + percents)
        rows.append({"area_id": aid, "country": country, "region": region, "year": 2026, "month": 4,
                     "lat": lat, "lon": lon, "overall_phase": np.nan,
                     "feat_x": float(rng.normal()), "feat_y": float(rng.normal()),
                     "overall_phase_lag1": np.nan,
                     **{f"phase{i}_percent": np.nan for i in range(1, 6)}})
    return pd.DataFrame(rows)


@pytest.fixture
def comprehensive_frame() -> pd.DataFrame:
    return build_comprehensive_frame()


@pytest.fixture
def comprehensive_csv(tmp_path, comprehensive_frame) -> "object":
    path = tmp_path / "comprehensive.csv"
    comprehensive_frame.to_csv(path, index=False)
    return path
