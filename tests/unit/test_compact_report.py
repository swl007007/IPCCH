import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]


def _verifier():
    spec = importlib.util.spec_from_file_location("compact_verify", REPO_ROOT / "scripts/postprocessing/verify_compact_climate_weather_oracle.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_wide_metrics_has_no_phantom_groups_and_keeps_all_undefined_groups():
    rows = []
    for arm, h, period, n, values in (("compact_baseline", 0, "2022", 10, (0.5, 0.2)), ("compact_baseline", 3, "2022", 10, (0.6, 0.1)),
                                      ("compact_weather_oracle", 3, "2022", 10, (np.nan, np.nan))):  # an all-undefined group
        for metric, value in zip(("exact_phase_accuracy", "r2_phase3plus"), values):
            rows.append({"arm": arm, "horizon": h, "period": period, "n_rows": n, "metric": metric, "value": value})
    wide = _verifier().wide_metrics(pd.DataFrame(rows), ["arm", "horizon", "period", "n_rows"])
    assert len(wide) == 3
    assert not ((wide["arm"] == "compact_weather_oracle") & (wide["horizon"] == 0)).any()
    oracle = wide[(wide["arm"] == "compact_weather_oracle")]
    assert len(oracle) == 1 and oracle[["exact_phase_accuracy", "r2_phase3plus"]].isna().all(axis=None)
