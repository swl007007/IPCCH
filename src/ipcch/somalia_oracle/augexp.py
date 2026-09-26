"""Original- vs augmented-label D experiment with report isolation (design sections 4-7).

Rows are keyed by (area_id, target_ord). Every label row carries its source report:
``original_month_ord`` (the raw observation month), ``source_family`` (``anl:<id>`` for
linked rounds, ``local:<month>`` otherwise) and ``source_available_ord``. Copies exist
only in the augmented branch and never enter history.

A *round* is a distinct original-report month. Round r's OOF model is fitted on branch
rows with target <= min(r-H, r-1) and source availability <= r-H, which excludes every
row of round r's family (copies always postdate their original month). Selection scores
the latest three supported rounds (minimum two); calibration for scoring round r uses up
to three earlier rounds (minimum two), restricted to rows eligible at r's origin.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from ipcch.somalia_oracle import CUMULATIVE_COLUMNS, FOLDS, HORIZONS, PERCENT_COLUMNS, V2_FEATURES, oracle_feature_names
from ipcch.somalia_oracle import augment as au
from ipcch.somalia_oracle import data as sd
from ipcch.somalia_oracle import history as hist
from ipcch.somalia_oracle import modeling as md
from ipcch.somalia_oracle import monthly_features as mf
from ipcch.somalia_oracle import pipeline as pl
from ipcch.somalia_oracle import q3opt as qo

BRANCHES = ("original", "augmented")
FORMULATIONS = ("direct", "residual")
MODEL_VIEWS = ("D_direct", "D_residual", "D_selected")
FIRST_MODEL_YEAR = 2022


class AugExpError(RuntimeError):
    """An isolation, availability or support invariant does not hold."""


@dataclass
class AugPrepared:
    ledger: pd.DataFrame
    decisions: pd.DataFrame
    links: pd.DataFrame
    rounds_api: pd.DataFrame
    frames: Dict[int, pd.DataFrame]
    schemas: Dict[int, List[str]]
    cohort: pd.DataFrame
    jobs: pd.DataFrame
    parity: pd.DataFrame
    input_hashes: Dict[str, str]
    notes: Dict[str, object] = field(default_factory=dict)


# --------------------------------------------------------------------------
# Preparation
# --------------------------------------------------------------------------


def category_history(frame: pd.DataFrame, originals: pd.DataFrame, horizon: int) -> np.ndarray:
    """Report-aware ``overall_phase_prev_observed_asof_sH``: the raw original phase at
    calendar month T - max(1, H), unless that source is the row's own family."""
    lag = max(1, int(horizon))
    src = originals.loc[originals["valid_phase"], ["area_id", "target_ord", "overall_phase", "source_family"]]
    lookup = src.set_index(["area_id", "target_ord"])
    keys = pd.MultiIndex.from_arrays([frame["area_id"].to_numpy(), frame["target_ord"].to_numpy() - lag])
    found = lookup.reindex(keys)
    value = found["overall_phase"].to_numpy(dtype=np.float64)
    same = found["source_family"].to_numpy(dtype=object) == frame["source_family"].to_numpy(dtype=object)
    return np.where(same, np.nan, value)


def persistence_with_cutoff(originals: pd.DataFrame, area: np.ndarray, origin: np.ndarray, cutoff: np.ndarray) -> pd.DataFrame:
    src = originals.loc[originals["valid_phase"], ["area_id", "target_ord", "overall_phase"]].sort_values(["area_id", "target_ord"], kind="mergesort")
    keys = src["area_id"].to_numpy(dtype=np.int64) * 1_000_000 + src["target_ord"].to_numpy(dtype=np.int64)
    start = np.searchsorted(keys, area * 1_000_000, side="left")
    end = np.searchsorted(keys, area * 1_000_000 + cutoff, side="right")
    has = end > start
    idx = np.where(has, end - 1, 0)
    months = src["target_ord"].to_numpy(dtype=np.int64)
    out = pd.DataFrame({"persistence_available": has, "persistence_phase": np.where(has, src["overall_phase"].to_numpy(dtype=float)[idx], np.nan), "persistence_source_ord": np.where(has, months[idx], -1)})
    out["persistence_age_months"] = np.where(has, origin - out["persistence_source_ord"], np.nan)
    return out


def prepare(input_paths: Mapping[str, Path], cfg: Mapping[str, object], log=print, hash_inputs: bool = True, deep: Optional[pd.DataFrame] = None) -> AugPrepared:
    t0 = time.time()
    lookup = pd.read_csv(input_paths["lookup"])
    som = sd.somalia_area_ids(lookup)
    raw = sd.read_area_rows(input_paths["raw"], som, "admin_code", usecols=[*pl.RAW_COLUMNS, "estimated_population"])
    raw = raw.rename(columns={"admin_code": "area_id"})
    raw["target_ord"] = sd.month_ord(raw["year"], raw["month"])
    weather = sd.build_weather_ledger(raw.rename(columns={"area_id": "admin_code"}))
    log(f"[prepare] raw Somalia rows {len(raw)} ({time.time()-t0:.0f}s)")

    # ---- validity links and augmentation (R12, R15, R16) ----
    rounds_api = au.load_rounds(Path(cfg["validity_snapshot"]), cfg.get("validity_snapshot_sha256"), cfg["api_filter"])
    full = raw[list(au.LABEL_FIELDS)].notna().all(axis=1)
    linkable = raw.loc[full & (raw["year"] >= int(cfg["augmentation_years"][0])), "target_ord"]
    links = au.link_rounds(linkable, rounds_api, cfg["excluded_raw_months"])
    augmented, decisions = au.augment_labels(raw[["area_id", "target_ord", *au.LABEL_FIELDS]], links, tuple(cfg["augmentation_years"]))
    n_add = int(augmented["is_copy"].sum())
    log(f"[prepare] augmentation: {n_add} copies; decisions {decisions['decision'].value_counts().to_dict() if len(decisions) else {}}")

    # ---- label ledger over originals + copies (raw values; existing QC/normalization) ----
    rows = augmented.loc[augmented["label_state"].isin(["original", "copy"])].merge(raw[["area_id", "target_ord", "year", "month", "estimated_population"]], on=["area_id", "target_ord"])
    keys = set(zip(rows["area_id"].astype(int), rows["target_ord"].astype(int)))
    ledger = sd.build_label_ledger({"raw": rows[["area_id", "year", "month", *au.LABEL_FIELDS, "estimated_population"]]}, keys)
    meta = rows[["area_id", "target_ord", "is_copy", "original_month_ord", "source_family", "source_available_ord"]]
    ledger = ledger.merge(meta, on=["area_id", "target_ord"], how="left", validate="one_to_one")
    ledger["original_year"] = ledger["original_month_ord"] // 12
    ledger.loc[ledger["is_copy"], "valid_history"] = False  # copies are never historical observations (R8)
    originals = ledger.loc[~ledger["is_copy"]]
    history_index = hist.build_history_index(originals.loc[originals["valid_history"]])
    history_names = hist.history_feature_names()

    # ---- monthly X ----
    if deep is None:
        deep = mf.load_somalia_deep(som)
    log(f"[prepare] deep monthly panel {deep.shape} ({time.time()-t0:.0f}s)")
    v2 = pd.read_csv(input_paths["v2"], usecols=pl.V2_COLUMNS, low_memory=False)
    v2 = v2.loc[pd.to_numeric(v2["admin_code"], errors="coerce").isin(som)].copy()
    v2["admin_code"] = v2["admin_code"].astype(np.int64)
    seasons = sd.prepare_v2_seasons(v2)

    frames, schemas, parity_rows, cohort_rows, job_rows = {}, {}, [], [], []
    for h in HORIZONS:
        scope = mf.scope_frame(deep, h)
        ref = sd.read_area_rows(input_paths[pl.HORIZON_FS[h]], som, "area_id")
        invalid_ref = ~pd.to_numeric(ref["overall_phase"], errors="coerce").isin([1, 2, 3, 4, 5])
        par = mf.parity_check(scope, ref.loc[~invalid_ref], ["overall_phase_lag1", f"overall_phase_prev_observed_asof_s{h}", "estimated_population"])
        par["horizon"] = h
        par["unmatched_keys"] = par.attrs.get("unmatched_keys")
        par["skipped_invalid_phase_ref_rows"] = int(invalid_ref.sum())
        if (par["status"] != "ok").any() or par.attrs.get("unmatched_keys"):
            raise AugExpError(f"H={h}: recovered monthly features differ from the saved fs file on valid keys")
        parity_rows.append(par)
        base_cols = [c for c in sd.base_feature_columns(scope) if c not in ("target_ord",)]
        cat = f"overall_phase_prev_observed_asof_s{h}"
        model = ledger.loc[ledger["valid_target"] & (ledger["target_ord"] // 12 >= FIRST_MODEL_YEAR)]
        frame = model.merge(scope[["area_id", "target_ord", *base_cols]], on=["area_id", "target_ord"], how="inner", validate="one_to_one")
        if len(frame) != len(model):
            raise AugExpError(f"H={h}: {len(model) - len(frame)} label rows lack a monthly feature row")
        if h < 12:
            frame[cat] = category_history(frame, originals, h)
            base_cols = base_cols + [cat]
        pl.validate_scope_construction(base_cols, h)
        frame = frame.sort_values(["target_ord", "area_id"], kind="mergesort").reset_index(drop=True)
        frame["horizon"] = h
        frame["origin_ord"] = frame["target_ord"] - h
        frame["target_year"] = frame["target_ord"] // 12
        area = frame["area_id"].to_numpy(dtype=np.int64)
        origin = frame["origin_ord"].to_numpy(dtype=np.int64)
        target = frame["target_ord"].to_numpy(dtype=np.int64)
        cutoff = np.minimum(origin, target - 1)
        copy = frame["is_copy"].to_numpy(dtype=bool)
        f0 = frame["original_month_ord"].to_numpy(dtype=np.int64)
        cutoff = np.where(copy, np.minimum(cutoff, f0 - 1), cutoff)
        if copy.any():
            # Excluding the copy's own report equals cutting before F0 only if no other
            # original of that area lies in (F0, min(O, T-1)].
            span_hi = np.minimum(origin, target - 1)
            ok_keys = set(zip(originals["area_id"], originals["target_ord"]))
            for a, lo, hi in zip(area[copy], f0[copy], span_hi[copy]):
                if any((a, m) in ok_keys for m in range(lo + 1, hi + 1)):
                    raise AugExpError("another original report lies between a copy's source and its history cutoff")
        v2b = sd.v2_block(seasons, area, origin)
        oracle, _ = sd.oracle_block(weather, area, origin, h)
        hblock = pd.DataFrame(hist.build_history_block(history_index, area, origin, cutoff, history_names), columns=history_names)
        slots = hist.history_slot_sources(history_index, area, cutoff)
        pers = persistence_with_cutoff(originals, area, origin, cutoff)
        frame = pd.concat([frame, v2b, oracle, hblock, slots, pers], axis=1)
        frame["history_cutoff_ord"] = cutoff
        frames[h] = frame
        schemas[h] = list(base_cols) + list(V2_FEATURES) + oracle_feature_names(h) + history_names
        for year, window in FOLDS.items():
            test = ledger.loc[(ledger["target_ord"] // 12 == year) & ~ledger["is_copy"]]
            verified = dict(zip(zip(frame["area_id"], frame["target_ord"]), frame["oracle_all_verified"]))
            for r in test.itertuples(index=False):
                key = (int(r.area_id), int(r.target_ord))
                if not r.valid_target:
                    status, reason = "excluded", f"target:{r.target_invalid_reason}"
                elif not r.valid_score:
                    status, reason = "excluded", "invalid_reported_phase"
                elif h > 0 and not verified.get(key, False):
                    status, reason = "wider_only", "oracle_weather_unverified"
                else:
                    status, reason = "primary", None
                cohort_rows.append({"test_year": year, "horizon": h, "area_id": key[0], "target_ord": key[1], "status": status, "reason": reason})
            scorable = frame.loc[(frame["target_year"] == year) & frame["valid_score"] & ~frame["is_copy"]]
            for o, g in scorable.groupby("origin_ord"):
                job_rows.append({"job_id": f"y{year}_h{h:02d}_o{sd.ord_label(o)}", "test_year": year, "horizon": h, "origin_ord": int(o), "n_eval_rows": len(g)})
        log(f"[prepare] H={h}: frame {frame.shape}, D width {len(schemas[h])}, parity bad cols {int((par['status'] != 'ok').sum())} ({time.time()-t0:.0f}s)")
    notes = {
        "n_copies": n_add,
        "copies_by_month": ledger.loc[ledger["is_copy"]].groupby(ledger["target_ord"].map(sd.ord_label)).size().to_dict(),
        "decisions": decisions["decision"].value_counts().to_dict() if len(decisions) else {},
        "label_source": "raw panel (IPCCH_2026_completed.csv); v1/v2 used the target-corrected fs ledger",
    }
    hashes = {n: (sd.sha256_file(p) if hash_inputs else "not_computed") for n, p in input_paths.items()}
    hashes["validity_snapshot"] = cfg.get("validity_snapshot_sha256")
    return AugPrepared(ledger, decisions, links, rounds_api, frames, schemas, pd.DataFrame(cohort_rows), pd.DataFrame(job_rows), pd.concat(parity_rows, ignore_index=True), hashes, notes)


# --------------------------------------------------------------------------
# Pools and rounds (parent process)
# --------------------------------------------------------------------------


def branch_mask(frame: pd.DataFrame, branch: str) -> np.ndarray:
    if branch not in BRANCHES:
        raise AugExpError(f"unknown branch {branch}")
    return np.ones(len(frame), dtype=bool) if branch == "augmented" else ~frame["is_copy"].to_numpy(dtype=bool)


def window_mask(frame: pd.DataFrame, window: Sequence[int]) -> np.ndarray:
    return frame["target_year"].isin(list(window)).to_numpy() & frame["original_year"].isin(list(window)).to_numpy()


def fit_pool(frame: pd.DataFrame, branch: str, window: Sequence[int], label_cutoff: int, available_by: int, exclude_families: Sequence[str] = ()) -> np.ndarray:
    m = branch_mask(frame, branch) & window_mask(frame, window)
    m &= frame["target_ord"].to_numpy() <= label_cutoff
    m &= frame["source_available_ord"].to_numpy() <= available_by
    if len(exclude_families):
        m &= ~frame["source_family"].isin(list(exclude_families)).to_numpy()
    return np.flatnonzero(m)


def round_rows(frame: pd.DataFrame, branch: str, window: Sequence[int], r: int) -> np.ndarray:
    return np.flatnonzero(branch_mask(frame, branch) & window_mask(frame, window) & (frame["original_month_ord"].to_numpy() == r))


def round_pool(frame: pd.DataFrame, branch: str, window: Sequence[int], r: int, h: int) -> np.ndarray:
    """OOF pool for round r: labels strictly before the round's origin and available by it."""
    return fit_pool(frame, branch, window, qo.fit_cutoff(r, h), r - h, exclude_families=round_families(frame, r))


def round_families(frame: pd.DataFrame, r: int) -> List[str]:
    return sorted(frame.loc[frame["original_month_ord"] == r, "source_family"].unique())


def plan_rounds(frame: pd.DataFrame, branch: str, window: Sequence[int], h: int, cfg: Mapping[str, object], outer_origin: Optional[int] = None) -> Dict[str, object]:
    rounds = sorted(int(r) for r in frame.loc[branch_mask(frame, branch) & window_mask(frame, window), "original_month_ord"].unique())
    if outer_origin is not None:
        rounds = [r for r in rounds if r <= outer_origin]
    oof = [r for r in rounds if round_pool(frame, branch, window, r, h).size > 0]
    valid = frame["valid_score"].to_numpy(dtype=bool)
    scorable = [r for r in oof if valid[round_rows(frame, branch, window, r)].any()]
    scoring = scorable[-int(cfg["selection_rounds"]):]
    target = frame["target_ord"].to_numpy()
    avail = frame["source_available_ord"].to_numpy()

    def calib_for(limit_label: int, limit_avail: int, before: int) -> List[int]:
        eligible = []
        for c in oof:
            if c >= before:
                continue
            rr = round_rows(frame, branch, window, c)
            if ((target[rr] <= limit_label) & (avail[rr] <= limit_avail)).any():
                eligible.append(c)
        return eligible[-int(cfg["calibration_rounds"]):]

    calibration = {r: calib_for(qo.fit_cutoff(r, h), r - h, r) for r in scoring}
    final = None
    if outer_origin is not None:
        final = calib_for(outer_origin, outer_origin, outer_origin + 1)
    return {"rounds": rounds, "oof": oof, "scoring": scoring, "calibration": calibration, "final": final, "status": "ok" if len(scoring) >= int(cfg["min_selection_rounds"]) else "unsupported"}


def pool_hash(idx: np.ndarray, frame: pd.DataFrame) -> str:
    keys = frame.loc[idx, ["area_id", "target_ord"]].to_numpy()
    return hashlib.sha256(np.ascontiguousarray(keys).tobytes()).hexdigest()[:16]


# --------------------------------------------------------------------------
# Workers
# --------------------------------------------------------------------------

_STATE: Dict[str, object] = {}


def init_state(prepared: AugPrepared, bundles) -> None:
    _STATE.clear()
    _STATE["frames"] = prepared.frames
    _STATE["X"] = {h: prepared.frames[h].loc[:, cols].to_numpy(dtype=np.float32) for h, cols in prepared.schemas.items()}
    _STATE["bundles"] = bundles


def _params(bundle_id: str, target: str) -> Dict[str, object]:
    bundle = next(c for c in _STATE["bundles"]["candidates"] if c["id"] == bundle_id)
    return md.candidate_params(_STATE["bundles"], bundle, "q3" if target in ("q3", "delta") else target)


def _baseline(frame: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
    b = frame["hist_q3_obs1"].to_numpy(dtype=np.float64)
    src = frame["history_obs1_source_ord"].to_numpy(dtype=np.int64)
    ok = np.isfinite(b) & (src >= 0)
    if np.any(ok & (src > frame["history_cutoff_ord"].to_numpy())):
        raise AugExpError("residual baseline source after the row's history cutoff")
    return b, ok


def fit_predict_q3(h: int, formulation: str, bundle: str, fit_idx: np.ndarray, pred_idx: np.ndarray, weight_origin: int, keep_model: bool = False):
    frame = _STATE["frames"][h]
    X = _STATE["X"][h]
    q3 = frame["q3"].to_numpy(dtype=np.float64)
    months = frame["target_ord"].to_numpy(dtype=np.int64)
    info = {"n_fit": int(fit_idx.size)}
    if formulation == "residual":
        b, ok = _baseline(frame)
        fit_idx = fit_idx[ok[fit_idx]]
        y = q3[fit_idx] - b[fit_idx]
        target = "delta"
    else:
        y = q3[fit_idx]
        target = "q3"
    info.update(n_fit_used=int(fit_idx.size), fit_max_target_ord=int(months[fit_idx].max()) if fit_idx.size else None)
    if fit_idx.size == 0:
        return None, np.full(pred_idx.size, np.nan), {**info, "status": "unsupported"}
    model = md.fit_regressor(X[fit_idx], y, md.decay_weights(months[fit_idx], weight_origin), _params(bundle, target), target)
    raw = model.predict(X[pred_idx])
    if formulation == "residual":
        b, ok = _baseline(frame)
        raw = np.where(ok[pred_idx], b[pred_idx] + raw, np.nan)
    return (model if keep_model else None), raw, {**info, "status": "ok", "model_kind": model.kind}


def oof_task(t: Mapping[str, object]) -> Dict[str, object]:
    _, raw, info = fit_predict_q3(t["horizon"], t["formulation"], t["bundle"], np.asarray(t["fit_idx"]), np.asarray(t["pred_idx"]), t["weight_origin"])
    return {**{k: t[k] for k in ("branch", "fold", "horizon", "formulation", "bundle", "round", "pool_hash", "fit_label_cutoff", "available_by")}, **info, "pred_idx": np.asarray(t["pred_idx"]), "raw_q3": raw}


def final_task(t: Mapping[str, object]) -> Dict[str, object]:
    h, formulation, bundle = t["horizon"], t["formulation"], t["bundle"]
    frame = _STATE["frames"][h]
    X = _STATE["X"][h]
    fit_idx, pred_idx = np.asarray(t["fit_idx"]), np.asarray(t["pred_idx"])
    months = frame["target_ord"].to_numpy(dtype=np.int64)
    w = md.decay_weights(months[fit_idx], t["origin_ord"])
    models, others = {}, {}
    for target in ("q2", "q4", "q5"):
        models[target] = md.fit_regressor(X[fit_idx], frame[target].to_numpy(dtype=float)[fit_idx], w, _params(bundle, target), target)
        others[target] = models[target].predict(X[pred_idx])
    dm, raw, dinfo = fit_predict_q3(h, "direct", bundle, fit_idx, pred_idx, t["origin_ord"], keep_model=True)
    models["q3_direct"] = dm
    branch = np.full(pred_idx.size, "direct", dtype=object)
    if formulation == "residual":
        rm, res, rinfo = fit_predict_q3(h, "residual", bundle, fit_idx, pred_idx, t["origin_ord"], keep_model=True)
        if rm is None:
            return {**{k: t[k] for k in ("key",)}, "status": "unsupported", "reason": "no baseline-supported fitting rows"}
        models["q3_residual_delta"] = rm
        branch = np.where(np.isfinite(res), "residual", "fallback_direct").astype(object)
        raw = np.where(np.isfinite(res), res, raw)
    mapped, why = qo.apply_branches(raw, branch, t["mappings"])
    pred = pd.DataFrame({"row": pred_idx, "area_id": frame["area_id"].to_numpy()[pred_idx], "target_ord": months[pred_idx], "q2_raw": others["q2"], "q3_raw": raw, "q4_raw": others["q4"], "q5_raw": others["q5"], "branch": branch,
                         "baseline_q3": np.where(branch == "residual", frame["hist_q3_obs1"].to_numpy()[pred_idx], np.nan)})
    if mapped is None:
        pred["q3_final"], pred["clipped"], cal = np.nan, False, ("unavailable", why)
    else:
        final, clipped = qo.bound_share(mapped)
        pred["q3_final"], pred["clipped"], cal = final, clipped, ("ok", None)
    ledger = pd.DataFrame({"row": fit_idx, "area_id": frame["area_id"].to_numpy()[fit_idx], "target_ord": months[fit_idx], "source_family": frame["source_family"].to_numpy()[fit_idx],
                           "source_available_ord": frame["source_available_ord"].to_numpy()[fit_idx], "is_copy": frame["is_copy"].to_numpy()[fit_idx], "weight": w})
    return {"key": t["key"], "status": "completed", "calibration_status": cal[0], "calibration_reason": cal[1], "predictions": pred, "fit_ledger": ledger, "models": models}


# --------------------------------------------------------------------------
# OOF store, mappings and scoring (parent)
# --------------------------------------------------------------------------


class RoundStore:
    def __init__(self):
        self.data: Dict[Tuple, Tuple[np.ndarray, np.ndarray]] = {}
        self.status: Dict[Tuple, str] = {}
        self.ledger: List[Dict[str, object]] = []

    @staticmethod
    def key(branch, fold, h, formulation, bundle, r):
        return (branch, int(fold), int(h), formulation, bundle, int(r))

    def add(self, res):
        k = self.key(res["branch"], res["fold"], res["horizon"], res["formulation"], res["bundle"], res["round"])
        self.data[k] = (res["pred_idx"], np.asarray(res["raw_q3"], dtype=float))
        self.status[k] = res["status"]
        self.ledger.append({c: res.get(c) for c in ("branch", "fold", "horizon", "formulation", "bundle", "round", "pool_hash", "fit_label_cutoff", "available_by", "status", "n_fit", "n_fit_used", "fit_max_target_ord", "model_kind")})

    def ok(self, *k) -> bool:
        return self.status.get(self.key(*k)) == "ok"

    def get(self, *k):
        return self.data[self.key(*k)]


def oof_task_spec(frame, branch, fold, window, h, formulation, bundle, r) -> Dict[str, object]:
    fit_idx = round_pool(frame, branch, window, r, h)
    return {"branch": branch, "fold": fold, "horizon": h, "formulation": formulation, "bundle": bundle, "round": r, "fit_idx": fit_idx, "pred_idx": round_rows(frame, branch, window, r),
            "weight_origin": r - h, "pool_hash": pool_hash(fit_idx, frame), "fit_label_cutoff": qo.fit_cutoff(r, h), "available_by": r - h}


def branch_round_predictions(store, frame, key_prefix, formulation, bundle, r):
    """Round rows with raw q3 and branch label (direct / residual / fallback_direct)."""
    branch_name, fold, h = key_prefix
    idx, draw = store.get(branch_name, fold, h, "direct", bundle, r)
    if formulation == "direct":
        return idx, draw, np.full(idx.size, "direct", dtype=object)
    ridx, rraw = store.get(branch_name, fold, h, "residual", bundle, r)
    if not np.array_equal(idx, ridx):
        raise AugExpError("residual and direct round rows differ")
    lab = np.where(np.isfinite(rraw), "residual", "fallback_direct").astype(object)
    return idx, np.where(np.isfinite(rraw), rraw, draw), lab


def fit_round_mappings(store, frame, key_prefix, formulation, bundle, method, cal_rounds, label_limit, avail_limit, min_rounds) -> Dict[str, qo.Q3Mapping]:
    """Mappings per prediction branch fitted on eligible rows of the calibration rounds."""
    branch_name, fold, h = key_prefix
    q3 = frame["q3"].to_numpy(dtype=float)
    target = frame["target_ord"].to_numpy()
    avail = frame["source_available_ord"].to_numpy()
    names = ("direct",) if formulation == "direct" else ("residual", "fallback_direct")
    out = {}
    for name in names:
        src = "direct" if name != "residual" else "residual"
        raws, ys, rs, rows = [], [], [], []
        for c in cal_rounds:
            if not store.ok(branch_name, fold, h, src, bundle, c):
                continue
            idx, raw = store.get(branch_name, fold, h, src, bundle, c)
            keep = (target[idx] <= label_limit) & (avail[idx] <= avail_limit) & np.isfinite(raw)
            if keep.any():
                raws.append(raw[keep]), ys.append(q3[idx[keep]]), rs.append(np.full(int(keep.sum()), c)), rows.append(idx[keep])
        cat = lambda xs: np.concatenate(xs) if xs else np.array([])
        mapping = qo.fit_mapping(method, cat(raws), cat(ys), cat(rs), min_rounds)
        mapping.fit_rows = tuple(int(x) for x in cat(rows))
        out[name] = mapping
    return out


def score_view(store, frame, plan, key_prefix, formulation, cfg, bundles) -> Tuple[pd.DataFrame, pd.DataFrame]:
    branch_name, fold, h = key_prefix
    q3 = frame["q3"].to_numpy(dtype=float)
    valid = frame["valid_score"].to_numpy(dtype=bool)
    crisis = frame["actual_crisis"].to_numpy(dtype=float)
    rows, preds = [], []
    for bo, bundle in enumerate([c["id"] for c in bundles["candidates"]]):
        for method in qo.METHOD_ORDER:
            finals, truths, cr, parts, reason = [], [], [], [], None
            for r in plan["scoring"]:
                ok = store.ok(branch_name, fold, h, "direct", bundle, r) and (formulation == "direct" or store.ok(branch_name, fold, h, "residual", bundle, r))
                idx, raw, lab = branch_round_predictions(store, frame, key_prefix, formulation, bundle, r)
                keep = valid[idx]
                idx, raw, lab = idx[keep], raw[keep], lab[keep]
                if not ok or not np.isfinite(raw).all():
                    reason = f"base OOF fit unsupported at round {sd.ord_label(r)}"
                    break
                maps = fit_round_mappings(store, frame, key_prefix, formulation, bundle, method, plan["calibration"][r], qo.fit_cutoff(r, h), r - h, int(cfg["min_calibration_rounds"]))
                mapped, why = qo.apply_branches(raw, lab, maps)
                if mapped is None:
                    reason = f"{why} at round {sd.ord_label(r)}"
                    break
                fin, clipped = qo.bound_share(mapped)
                finals.append(fin), truths.append(q3[idx]), cr.append(crisis[idx])
                parts.append(pd.DataFrame({"row": idx, "round": r, "target_ord": frame["target_ord"].to_numpy()[idx], "raw_q3": raw, "final_q3": fin, "prediction_branch": lab, "is_copy": frame["is_copy"].to_numpy()[idx]}))
            base = {"branch": branch_name, "fold": fold, "view": f"D_{formulation}", "formulation": formulation, "bundle": bundle, "bundle_order": bo, "method": method,
                    "method_order": qo.METHOD_ORDER.index(method), "formulation_order": qo.FORMULATION_ORDER.index(formulation)}
            if reason:
                rows.append({**base, "status": "unsupported", "reason": reason, "n": 0, "rmse": np.nan, "auc": np.nan})
                continue
            f, t, c = np.concatenate(finals), np.concatenate(truths), np.concatenate(cr)
            from sklearn.metrics import roc_auc_score

            auc = roc_auc_score(c == 1, f) if np.unique(c).size == 2 else np.nan
            rows.append({**base, "status": "ok", "reason": None, "n": int(f.size), "rmse": float(np.sqrt(np.mean((f - t) ** 2))), "auc": auc})
            p = pd.concat(parts, ignore_index=True)
            for k, v in base.items():
                p[k] = v
            preds.append(p)
    return pd.DataFrame(rows), (pd.concat(preds, ignore_index=True) if preds else pd.DataFrame())
