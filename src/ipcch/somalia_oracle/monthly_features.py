"""Complete monthly Somalia feature frames for H0/H3/H6/H12 (design section 8).

H12 uses the full monthly deep-feature artifact as is. H0/H3/H6 scope features are
rebuilt in memory with the upstream multi-scope builder's own functions over the
complete per-area monthly panel (no files written). The label-derived categorical
history column is recomputed separately under report-aware rules (augexp).
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Dict, List, Sequence, Set, Tuple

import numpy as np
import pandas as pd

from ipcch import paths
from ipcch.somalia_oracle import BLOCKED_BASE_FEATURES
from ipcch.somalia_oracle import data as sd

UPSTREAM_DIR = paths.PROJECT_ROOT.parent / "assemble_latest_IPCCH"
DEEP_FEATURES_PATH = paths.SOURCE_DATA_DIR / "assembled_IPCCH" / "features" / "forecasting_subset_IPCCH_2026_target_corrected_deep_features.csv"
SCOPE_BY_HORIZON = {0: "scope_0m", 3: "scope_3m", 6: "scope_6m"}
LABEL_COLUMNS = ("overall_phase", "phase1_percent", "phase2_percent", "phase3_percent", "phase4_percent", "phase5_percent")
CATEGORY_HISTORY = "overall_phase_prev_observed_asof_s{h}"


class FeatureError(RuntimeError):
    """A feature-recovery or parity invariant does not hold."""


def upstream():
    if str(UPSTREAM_DIR) not in sys.path:
        sys.path.insert(0, str(UPSTREAM_DIR))
    return importlib.import_module("build_multiscope_ipcch_features")


def load_somalia_deep(area_ids: Set[int], path: Path = DEEP_FEATURES_PATH) -> pd.DataFrame:
    parts = []
    for chunk in pd.read_csv(path, chunksize=100_000, low_memory=False):
        keep = pd.to_numeric(chunk["area_id"], errors="coerce").isin(area_ids)
        if keep.any():
            parts.append(chunk.loc[keep])
    deep = pd.concat(parts, ignore_index=True)
    deep["area_id"] = deep["area_id"].astype(np.int64)
    deep["target_ord"] = sd.month_ord(deep["year"], deep["month"])
    if deep.duplicated(["area_id", "target_ord"]).any():
        raise FeatureError("deep-feature panel has duplicate Somalia area/month keys")
    gaps = deep.sort_values(["area_id", "target_ord"]).groupby("area_id")["target_ord"].diff().dropna()
    if (gaps != 1).any():
        raise FeatureError("deep-feature panel is not monthly-continuous within some area")
    return deep.sort_values(["area_id", "target_ord"], kind="mergesort").reset_index(drop=True)


def scope_frame(deep: pd.DataFrame, horizon: int) -> pd.DataFrame:
    """Model-ready columns for one horizon, keyed by area_id/target_ord, all months."""
    if horizon == 12:
        frame = deep.drop(columns=[c for c in BLOCKED_BASE_FEATURES if c in deep.columns])
        return frame.drop(columns=[c for c in LABEL_COLUMNS if c in frame.columns])
    up = upstream()
    scope = SCOPE_BY_HORIZON[horizon]
    scenario = up.SCENARIOS[scope]
    source = deep.copy()
    source["area_id"] = source["area_id"].astype("string")
    source["date"] = pd.to_datetime({"year": source["year"], "month": source["month"], "day": 1})
    source = source.sort_values(["area_id", "date"], kind="mergesort").reset_index(drop=True)
    columns = up.needed_source_columns(list(source.columns))
    dynamic = up.available_dynamic_source_columns(columns)
    enso = up.detect_enso_column(columns)
    baseline_cols = [c for c in deep.columns if c not in set(up.KEY_COLUMNS) | set(LABEL_COLUMNS) | {"target_ord", "date"} and not any(p in c for p in up.TARGET_DERIVED_PATTERNS)]
    baseline_block = source[baseline_cols].reset_index(drop=True)
    state = up.ScenarioState(scope=scope, output_path=Path("/dev/null"), sidecars={})
    ordinary, _, _ = up.build_ordinary_features(source, state, dynamic, scenario["blackout_months"], scenario["suffix"])
    enso_frame = up.build_enso_features(source, state, enso, scenario["blackout_months"], scenario["suffix"])
    final_base = pd.concat([source[up.REQUIRED_OUTPUT_COLUMNS].reset_index(drop=True), baseline_block], axis=1)
    feature_frame = pd.concat([ordinary, enso_frame], axis=1)
    interactions = up.build_interactions(final_base, feature_frame, state, scenario["suffix"])
    out = pd.concat([source[["area_id", "year", "month"]].reset_index(drop=True), baseline_block, feature_frame, interactions], axis=1)
    out = up.coerce_model_feature_types(out)
    out["area_id"] = out["area_id"].astype(np.int64)
    out["target_ord"] = sd.month_ord(out["year"], out["month"])
    return out


def parity_check(recovered: pd.DataFrame, reference: pd.DataFrame, skip: Sequence[str]) -> pd.DataFrame:
    """Compare recovered non-label features with a saved fs file on its keys."""
    ref = reference.copy()
    ref["area_id"] = ref["area_id"].astype(np.int64)
    ref["target_ord"] = sd.month_ord(ref["year"], ref["month"])
    cols = [c for c in ref.columns if c not in set(LABEL_COLUMNS) | {"area_id", "year", "month", "target_ord"} | set(skip)]
    missing = [c for c in cols if c not in recovered.columns]
    m = ref[["area_id", "target_ord", *cols]].merge(recovered[["area_id", "target_ord", *[c for c in cols if c in recovered.columns]]], on=["area_id", "target_ord"], how="left", suffixes=("_ref", "_new"), indicator=True)
    rows = [{"column": c, "status": "missing_in_recovered", "n_mismatch": len(m)} for c in missing]
    for c in cols:
        if c in missing:
            continue
        a = pd.to_numeric(m[f"{c}_ref"], errors="coerce").to_numpy(dtype=float)
        b = pd.to_numeric(m[f"{c}_new"], errors="coerce").to_numpy(dtype=float)
        same = (np.isnan(a) & np.isnan(b)) | np.isclose(a, b, rtol=1e-9, atol=1e-12, equal_nan=False)
        rows.append({"column": c, "status": "ok" if same.all() else "mismatch", "n_mismatch": int((~same).sum())})
    out = pd.DataFrame(rows)
    out.attrs["unmatched_keys"] = int((m["_merge"] != "both").sum())
    return out
