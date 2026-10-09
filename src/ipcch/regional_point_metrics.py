"""Global and all-region point metrics of saved global predictions, plus paired arm differences (no bootstrap, no fitting).

Membership is the ``area_id`` join to ``data/reference/area_id_country_region_mapping.csv`` (regions 0..8, region 0 is a
valid group). Every scored key must map to exactly one region; missing membership is an error. Every region is scored
for every period, empty or small groups included, with metric-specific undefined reasons (``osf.origin_metrics``).
Pooled values are computed from the pooled saved rows, never by averaging annual scores.
"""
from __future__ import annotations

from typing import Dict, Iterable, List, Mapping, Optional, Sequence

import numpy as np
import pandas as pd

from ipcch import origin_safe as osf

REGIONS = tuple(range(9))
KEYS = list(osf.KEYS)
PERIODS = (*osf.TARGET_YEARS, "pooled")
TRUTH = ["overall_phase", "phase3_worse"]


def load_region_map(path, expected_sha256: Optional[str] = None) -> pd.Series:
    if expected_sha256 is not None and osf.file_sha256(path) != expected_sha256:
        raise ValueError(f"region map sha256 differs from the frozen reference: {path}")
    frame = pd.read_csv(path)
    if list(frame.columns) != ["area_id", "region"]:
        raise ValueError(f"region map columns {list(frame.columns)} are not ['area_id', 'region']")
    if frame["area_id"].duplicated().any() or frame["area_id"].isna().any():
        raise ValueError("region map has duplicate or missing area_id")
    if not frame["region"].isin(REGIONS).all():
        raise ValueError(f"region map has regions outside {REGIONS}")
    return frame.set_index("area_id")["region"].astype(int)


def assign_regions(predictions: pd.DataFrame, region_map: pd.Series) -> pd.DataFrame:
    """Predictions with a ``region`` column; any key without membership raises."""
    region = region_map.reindex(predictions["area_id"].to_numpy())
    if region.isna().any():
        missing = sorted(set(predictions.loc[region.isna().to_numpy(), "area_id"]))
        raise ValueError(f"{len(missing)} scored areas have no region membership, e.g. {missing[:5]}")
    out = predictions.copy()
    out["region"] = region.to_numpy(dtype=int)
    return out


def align_pair(oracle: pd.DataFrame, baseline: pd.DataFrame) -> tuple:
    """Both arms on one sorted (area_id, year, month) index; keys and truths must be identical."""
    a = oracle.sort_values(KEYS, kind="mergesort").reset_index(drop=True)
    b = baseline.sort_values(KEYS, kind="mergesort").reset_index(drop=True)
    if a[KEYS].duplicated().any() or not a[KEYS].equals(b[KEYS]):
        raise ValueError("paired runs do not share the same evaluation keys")
    for column in TRUTH:
        if not np.array_equal(a[column].to_numpy(dtype=float), b[column].to_numpy(dtype=float)):
            raise ValueError(f"paired runs disagree on the truth column {column}")
    return a, b


def support(part: pd.DataFrame) -> Dict[str, int]:
    observed = part["overall_phase"].to_numpy(dtype=float) >= 3
    predicted = part["overall_phase_pred"].to_numpy(dtype=float) >= 3
    return {"n_rows": len(part), "n_areas": int(part["area_id"].nunique()), "observed_3plus": int(observed.sum()),
            "observed_1_2": int((~observed).sum()), "predicted_3plus": int(predicted.sum()),
            "true_positive_3plus": int((observed & predicted).sum()),
            "distinct_phase3_worse": int(part["phase3_worse"].nunique())}


def metric_rows(predictions: pd.DataFrame, run_id: str, arm: str, horizon: int, regions: Iterable = ("global", *REGIONS)) -> List[dict]:
    """Long rows: one per (scope, period, metric) with value/status/reason and support counts."""
    rows = []
    for scope in regions:
        group = predictions if scope == "global" else predictions[predictions["region"] == scope]
        for period in PERIODS:
            part = group if period == "pooled" else group[group["year"] == period]
            result = osf.origin_metrics(part, "global" if scope == "global" else f"region{scope}", period)
            sup = support(part)
            for metric in osf.ORIGIN_METRICS:
                value = result[metric]
                rows.append({"run_id": run_id, "arm": arm, "horizon": horizon, "scope": "global" if scope == "global" else "region",
                             "region": None if scope == "global" else int(scope), "period": str(period), "metric": metric,
                             "value": value["value"], "status": value["status"], "reason": value["reason"], **sup})
    return rows


def delta_rows(metrics: pd.DataFrame, oracle_arm: str, baseline_arm: str, horizons: Sequence[int]) -> List[dict]:
    """oracle - baseline per horizon/scope/region/period/metric; undefined if either side is undefined."""
    key = ["horizon", "scope", "region", "period", "metric"]
    a = metrics[metrics["arm"] == oracle_arm].set_index(key)
    b = metrics[metrics["arm"] == baseline_arm].set_index(key)
    rows = []
    for idx in a.index:
        if idx[0] not in horizons:
            continue
        if idx not in b.index:
            raise ValueError(f"baseline has no metric row for {idx}")
        x, y = a.loc[idx], b.loc[idx]
        if x["n_rows"] != y["n_rows"]:
            raise ValueError(f"{idx}: arms scored different row counts")
        defined = pd.notna(x["value"]) and pd.notna(y["value"])
        reason = None
        if not defined:
            reason = "; ".join(f"{side} {v['reason'] or 'undefined'}" for side, v in (("oracle", x), ("baseline", y)) if pd.isna(v["value"]))
        rows.append({**dict(zip(key, idx)), "contrast": f"{oracle_arm} - {baseline_arm}",
                     "oracle_value": x["value"], "baseline_value": y["value"],
                     "delta": float(x["value"]) - float(y["value"]) if defined else None,
                     "status": "ok" if defined else "undefined", "reason": reason, "n_rows": int(x["n_rows"]), "n_areas": int(x["n_areas"]),
                     "observed_3plus": int(x["observed_3plus"]), "oracle_predicted_3plus": int(x["predicted_3plus"]),
                     "baseline_predicted_3plus": int(y["predicted_3plus"])})
    return rows


def partition_check(predictions: pd.DataFrame) -> Dict[str, object]:
    """Regions partition every prediction row exactly once, per period."""
    out = {}
    for period in PERIODS:
        part = predictions if period == "pooled" else predictions[predictions["year"] == period]
        counts = part["region"].value_counts().reindex(REGIONS, fill_value=0)
        if int(counts.sum()) != len(part) or part[KEYS].duplicated().any():
            raise ValueError(f"{period}: regions do not partition the predictions exactly once")
        out[str(period)] = {int(r): int(c) for r, c in counts.items()}
    return out
