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

from ipcch.somalia_oracle import CUMULATIVE_COLUMNS, FOLDS, HALF_LIFE_MONTHS, HORIZONS, PERCENT_COLUMNS, V2_FEATURES, oracle_feature_names
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
    label_diff: pd.DataFrame
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


def mark_partial_originals(augmented: pd.DataFrame, links: pd.DataFrame) -> pd.DataFrame:
    """Partially populated raw reports with a reported phase stay original reports.

    They are never copy sources or recipients, but the label-ledger QC decides their own
    target/history validity (e.g. the flagged missing-P5 history-only rule). Their family
    follows the same month link as complete originals of that month.
    """
    out = augmented.copy()
    partial = out["label_state"].eq("partial") & out["overall_phase"].notna()
    if partial.any():
        linked = links.loc[links["link_status"] == "linked"].set_index("original_month_ord")["anl_id"]
        months = out.loc[partial, "target_ord"].astype(int)
        out.loc[partial, "label_state"] = "partial_original"
        out.loc[partial, "is_copy"] = False
        out.loc[partial, "original_month_ord"] = months.to_numpy()
        out.loc[partial, "source_available_ord"] = months.to_numpy()
        out.loc[partial, "source_family"] = [f"anl:{linked[m]}" if m in linked.index else f"local:{sd.ord_label(m)}" for m in months]
    return out


def prepare(input_paths: Mapping[str, Path], cfg: Mapping[str, object], log=print, hash_inputs: bool = True, deep: Optional[pd.DataFrame] = None,
            first_model_year: Optional[int] = FIRST_MODEL_YEAR, folds: Mapping[int, Sequence[int]] = FOLDS) -> AugPrepared:
    """``first_model_year=None`` keeps every valid label row (v4); ``folds`` drives the v3 cohort/jobs
    (v4 passes ``{}`` and freezes its own per-setting cohorts)."""
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
    augmented = mark_partial_originals(augmented, links)
    rows = augmented.loc[augmented["label_state"].isin(["original", "copy", "partial_original"])].merge(raw[["area_id", "target_ord", "year", "month", "estimated_population"]], on=["area_id", "target_ord"])
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
        extra = sorted(set(base_cols) - set(ref.columns))
        if extra:
            raise AugExpError(f"H={h}: recovered predictors absent from the saved fs file: {extra[:5]}")
        cat = f"overall_phase_prev_observed_asof_s{h}"
        model = ledger.loc[ledger["valid_target"] & ((ledger["target_ord"] // 12 >= first_model_year) if first_model_year is not None else True)]
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
        for year, window in folds.items():
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
    fs_labels = pd.concat([sd.read_area_rows(input_paths[n], som, "area_id")[["area_id", "year", "month", *au.LABEL_FIELDS]] for n in ("fs0", "fs1")]).drop_duplicates(["area_id", "year", "month"])
    fs_labels["target_ord"] = sd.month_ord(fs_labels["year"], fs_labels["month"])
    diff = originals[["area_id", "target_ord", *au.LABEL_FIELDS]].merge(fs_labels[["area_id", "target_ord", *au.LABEL_FIELDS]], on=["area_id", "target_ord"], how="outer", suffixes=("_raw", "_fs"), indicator=True)
    both = diff["_merge"] == "both"
    a = diff[[f"{c}_raw" for c in au.LABEL_FIELDS]].to_numpy(dtype=float)
    b = diff[[f"{c}_fs" for c in au.LABEL_FIELDS]].to_numpy(dtype=float)
    diff["values_differ"] = both & ~np.isclose(a, b, atol=1e-9, equal_nan=True).all(axis=1)
    diff["key_status"] = diff["_merge"].map({"both": "both", "left_only": "raw_only", "right_only": "fs_only"}).astype(str)
    diff["year"] = diff["target_ord"] // 12
    label_diff = diff.drop(columns="_merge")
    notes = {
        "raw_vs_fs_label_diff": label_diff.groupby("year").agg(shared=("key_status", lambda s: int((s == "both").sum())), differ=("values_differ", "sum"), raw_only=("key_status", lambda s: int((s == "raw_only").sum())), fs_only=("key_status", lambda s: int((s == "fs_only").sum()))).to_dict("index"),
        "n_copies": n_add,
        "copies_by_month": ledger.loc[ledger["is_copy"]].groupby(ledger["target_ord"].map(sd.ord_label)).size().to_dict(),
        "decisions": decisions["decision"].value_counts().to_dict() if len(decisions) else {},
        "label_source": "raw panel (IPCCH_2026_completed.csv); v1/v2 used the target-corrected fs ledger",
    }
    hashes = {n: (sd.sha256_file(p) if hash_inputs else "not_computed") for n, p in input_paths.items()}
    hashes["validity_snapshot"] = cfg.get("validity_snapshot_sha256")
    return AugPrepared(ledger, decisions, links, rounds_api, frames, schemas, label_diff, pd.DataFrame(cohort_rows), pd.DataFrame(job_rows), pd.concat(parity_rows, ignore_index=True), hashes, notes)


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


def fit_predict_q3(h: int, formulation: str, bundle: str, fit_idx: np.ndarray, pred_idx: np.ndarray, weight_origin: int, keep_model: bool = False, half_life: Optional[float] = HALF_LIFE_MONTHS):
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
    model = md.fit_regressor(X[fit_idx], y, md.decay_weights(months[fit_idx], weight_origin, half_life), _params(bundle, target), target)
    raw = model.predict(X[pred_idx])
    if formulation == "residual":
        b, ok = _baseline(frame)
        raw = np.where(ok[pred_idx], b[pred_idx] + raw, np.nan)
    return (model if keep_model else None), raw, {**info, "status": "ok", "model_kind": model.kind}


def oof_task(t: Mapping[str, object]) -> Dict[str, object]:
    _, raw, info = fit_predict_q3(t["horizon"], t["formulation"], t["bundle"], np.asarray(t["fit_idx"]), np.asarray(t["pred_idx"]), t["weight_origin"])
    return {**{k: t[k] for k in ("branch", "fold", "horizon", "formulation", "bundle", "round", "pool_hash", "fit_label_cutoff", "available_by", "excluded_families", "pool_families", "pool_max_source_available_ord", "pool_n_copies")}, **info, "pred_idx": np.asarray(t["pred_idx"]), "raw_q3": raw}


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
        self.ledger.append({c: res.get(c) for c in ("branch", "fold", "horizon", "formulation", "bundle", "round", "pool_hash", "fit_label_cutoff", "available_by", "excluded_families", "pool_families", "pool_max_source_available_ord", "pool_n_copies", "status", "n_fit", "n_fit_used", "fit_max_target_ord", "model_kind")})

    def ok(self, *k) -> bool:
        return self.status.get(self.key(*k)) == "ok"

    def get(self, *k):
        return self.data[self.key(*k)]


def oof_task_spec(frame, branch, fold, window, h, formulation, bundle, r) -> Dict[str, object]:
    fit_idx = round_pool(frame, branch, window, r, h)
    fams = frame["source_family"].to_numpy()[fit_idx]
    return {"branch": branch, "fold": fold, "horizon": h, "formulation": formulation, "bundle": bundle, "round": r, "fit_idx": fit_idx, "pred_idx": round_rows(frame, branch, window, r),
            "weight_origin": r - h, "pool_hash": pool_hash(fit_idx, frame), "fit_label_cutoff": qo.fit_cutoff(r, h), "available_by": r - h,
            "excluded_families": ";".join(round_families(frame, r)), "pool_families": ";".join(sorted(set(fams))),
            "pool_max_source_available_ord": int(frame["source_available_ord"].to_numpy()[fit_idx].max()) if fit_idx.size else -1,
            "pool_n_copies": int(frame["is_copy"].to_numpy()[fit_idx].sum())}


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


# ==========================================================================
# v4 calibrated D (task somalia-v4-calibrated-d, design sections 3-7)
#
# Two label scenarios (``original`` observed labels only; ``augmented`` observed
# labels plus permitted validity copies) in every label role, expanding annual
# folds (all eligible labels through Y-1), independent origin-valid selection at
# every horizon, and a 6 bundle x 4 decay x 2 formulation x 3 calibration search.
#
# Every OOF prediction is made by a *unit*: one fit on a pool fixed by a PoolSpec
# (setting, horizon, label cutoff, source-availability cutoff, fold upper year,
# excluded source families) for one (formulation, bundle, half-life). A row's pool
# uses the row's own target month v: labels <= min(v-H, v-1), sources available
# <= v-H, weights anchored at v-H, and it excludes the row's own family, the
# scoring family it serves and the outer context's test families. Specs are
# normalized (ineffective fold bound / exclusions dropped) so identical pools share
# one fit; the normalized spec, not a legacy cache key, is the dependency identity.
# ==========================================================================

V4_HALF_LIVES: Tuple[Optional[int], ...] = (12, 24, 48, None)
V4_DECAY_ORDER = {None: 0, 48: 1, 24: 2, 12: 3}  # deterministic tie order: no decay, 48, 24, 12
HX_SCALE = 4096  # prediction keys pack (frame row, history-exclusion code)


def half_life_label(half_life: Optional[float]) -> str:
    return "none" if half_life is None else str(int(half_life))


def parse_half_life(label: str) -> Optional[int]:
    return None if label in ("none", None) else int(label)


class V4History:
    """Context-specific history inputs (design sections 4-5).

    The frames hold features built from every original report except the row's own.
    When a context excludes further report families, every row that participates in it
    (fitting row, OOF prediction row, outer test row) and whose history contains an
    observation of an excluded family gets its rich history, residual baseline
    (``hist_q3_obs1`` / ``history_obs1_source_ord``) and categorical phase history
    recomputed from the original reports minus those families. Unexposed rows keep
    their frame features, which equal the recomputation with nothing excluded.
    """

    def __init__(self, ledger: pd.DataFrame, frames: Mapping[int, pd.DataFrame], schemas: Mapping[int, List[str]]):
        orig = ledger.loc[~ledger["is_copy"].astype(bool)]
        self.orig = orig
        self.frames, self.schemas = frames, schemas
        self.names = hist.history_feature_names()
        obs = orig.loc[orig["valid_history"].astype(bool) | orig["valid_phase"].astype(bool), ["area_id", "target_ord", "source_family", "valid_history", "valid_phase"]]
        self.rich = {f: dict(zip(g.loc[g["valid_history"].astype(bool), "area_id"].astype(int), g.loc[g["valid_history"].astype(bool), "target_ord"].astype(int)))
                     for f, g in obs.groupby("source_family")}
        self.cat = {f: set(zip(g.loc[g["valid_phase"].astype(bool), "area_id"].astype(int), g.loc[g["valid_phase"].astype(bool), "target_ord"].astype(int))) for f, g in obs.groupby("source_family")}
        self._index: Dict[Tuple[str, ...], Tuple[object, pd.DataFrame]] = {}
        self._codes: Dict[Tuple[str, ...], int] = {(): 0}
        self._base: Dict[Tuple[int, int, int], Tuple[float, bool]] = {}
        self._feat: Dict[Tuple[int, Tuple[str, ...], int], Tuple[np.ndarray, float, bool]] = {}

    def code(self, hx: Tuple[str, ...]) -> int:
        if hx not in self._codes:
            self._codes[hx] = len(self._codes)
            if self._codes[hx] >= HX_SCALE:
                raise AugExpError("too many distinct history-exclusion sets")
        return self._codes[hx]

    def codes(self) -> Dict[int, Tuple[str, ...]]:
        return {c: hx for hx, c in self._codes.items()}

    def exposing(self, h: int, rows: np.ndarray, families: Sequence[str]) -> List[Tuple[str, ...]]:
        """Per row: the families among ``families`` with an observation visible in its history
        (same area, rich-history month <= history cutoff, or the categorical source month T-max(1,H)).
        The row's own family is already absent from its frame history and is never reported."""
        f = self.frames[h]
        rows = np.asarray(rows, dtype=np.int64)
        own = f["source_family"].to_numpy(dtype=object)[rows]
        area = f["area_id"].to_numpy(dtype=np.int64)[rows]
        cutoff = f["history_cutoff_ord"].to_numpy(dtype=np.int64)[rows]
        catm = f["target_ord"].to_numpy(dtype=np.int64)[rows] - max(1, int(h))
        out: List[List[str]] = [[] for _ in range(rows.size)]
        for fam in sorted(set(families)):
            rich, cat = self.rich.get(fam, {}), self.cat.get(fam, set())
            if not rich and not cat:
                continue
            for k in range(rows.size):
                if own[k] == fam:
                    continue
                a = int(area[k])
                m = rich.get(a)
                if (m is not None and m <= cutoff[k]) or (h < 12 and (a, int(catm[k])) in cat):
                    out[k].append(fam)
        return [tuple(x) for x in out]

    def _excluded_index(self, excluded: Tuple[str, ...]):
        if excluded not in self._index:
            o = self.orig.loc[~self.orig["source_family"].isin(list(excluded))]
            self._index[excluded] = (hist.build_history_index(o.loc[o["valid_history"].astype(bool)]), o)
        return self._index[excluded]

    def features(self, h: int, rows: np.ndarray, excluded: Sequence[str]) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """(X rows float32, baseline q3, baseline source month, baseline ok) with ``excluded`` removed."""
        excluded = tuple(sorted(set(excluded)))
        rows = np.asarray(rows, dtype=np.int64)
        index, kept = self._excluded_index(excluded)
        f = self.frames[h].iloc[rows].reset_index(drop=True)
        area = f["area_id"].to_numpy(dtype=np.int64)
        origin = f["origin_ord"].to_numpy(dtype=np.int64)
        cutoff = f["history_cutoff_ord"].to_numpy(dtype=np.int64)
        hb = pd.DataFrame(hist.build_history_block(index, area, origin, cutoff, self.names), columns=self.names)
        slots = hist.history_slot_sources(index, area, cutoff)
        X = f[self.schemas[h]].copy()
        X[self.names] = hb.to_numpy()
        cat = mf.CATEGORY_HISTORY.format(h=h)
        if h < 12 and cat in X.columns:
            X[cat] = category_history(f, kept, h)
        b = hb["hist_q3_obs1"].to_numpy(dtype=np.float64)
        src = slots["history_obs1_source_ord"].to_numpy(dtype=np.int64)
        return X.to_numpy(dtype=np.float32), b, src, np.isfinite(b) & (src >= 0)

    def row_inputs(self, h: int, rows: np.ndarray, hxs: Sequence[Tuple[str, ...]]) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Feature rows, baseline, baseline-ok and baseline source month for (row, history
        exclusion) pairs; cached."""
        rows = np.asarray(rows, dtype=np.int64)
        width = len(self.schemas[h])
        X = np.empty((rows.size, width), dtype=np.float32)
        b = np.empty(rows.size)
        ok = np.empty(rows.size, dtype=bool)
        src = np.empty(rows.size, dtype=np.int64)
        todo: Dict[Tuple[str, ...], List[int]] = {}
        for k, (r, hx) in enumerate(zip(rows, hxs)):
            key = (int(h), tuple(hx), int(r))
            if key in self._feat:
                X[k], b[k], ok[k], src[k] = self._feat[key]
            else:
                todo.setdefault(tuple(hx), []).append(k)
        for hx, ks in todo.items():
            Xr, br, sr, okr = self.features(h, rows[ks], hx)
            for j, k in enumerate(ks):
                X[k], b[k], ok[k], src[k] = Xr[j], br[j], okr[j], sr[j]
                self._feat[(int(h), hx, int(rows[k]))] = (Xr[j], br[j], okr[j], sr[j])
        return X, b, ok, src

    def base_ok(self, h: int, rows: np.ndarray, hxs: Sequence[Tuple[str, ...]]) -> np.ndarray:
        frame = self.frames[h]
        _, frame_ok = _baseline(frame)
        rows = np.asarray(rows, dtype=np.int64)
        out = frame_ok[rows].copy()
        need = [k for k, hx in enumerate(hxs) if hx]
        if need:
            _, _, ok, _ = self.row_inputs(h, rows[need], [hxs[k] for k in need])
            out[need] = ok
        return out


@dataclass(frozen=True)
class PoolSpec:
    setting: str
    horizon: int
    label_cutoff: int
    available_by: int
    max_year: Optional[int]
    excluded: Tuple[str, ...]

    @property
    def id(self) -> str:
        text = json.dumps([self.setting, int(self.horizon), int(self.label_cutoff), int(self.available_by), self.max_year, list(self.excluded)])
        return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]

    def describe(self) -> Dict[str, object]:
        return {"spec_id": self.id, "setting": self.setting, "horizon": int(self.horizon), "label_cutoff_ord": int(self.label_cutoff), "available_by_ord": int(self.available_by),
                "max_year": self.max_year, "excluded_families": ";".join(self.excluded)}


class PoolIndex:
    """Normalizes pool specifications of one (setting, horizon) frame and caches their rows.

    An excluded family is kept in the normalized spec when it has labels in the pool or an
    observation visible in some pool row's history; such rows are fitted with history
    recomputed without it (``exposed``)."""

    def __init__(self, frame: pd.DataFrame, setting: str, horizon: int, history: Optional[V4History] = None):
        self.setting, self.horizon, self.history = setting, int(horizon), history
        self.setting_mask = branch_mask(frame, setting)
        self.target = frame["target_ord"].to_numpy(dtype=np.int64)
        self.avail = frame["source_available_ord"].to_numpy(dtype=np.int64)
        self.family = frame["source_family"].to_numpy(dtype=object)
        self.target_year = self.target // 12
        self.original_year = frame["original_month_ord"].to_numpy(dtype=np.int64) // 12
        self._rows: Dict[PoolSpec, np.ndarray] = {}
        self._exposed: Dict[PoolSpec, np.ndarray] = {}
        self._memo: Dict[Tuple, PoolSpec] = {}

    def normalize(self, label_cutoff: int, available_by: int, max_year: Optional[int], excluded: Sequence[str]) -> PoolSpec:
        memo_key = (int(label_cutoff), int(available_by), max_year, frozenset(excluded))
        if memo_key not in self._memo:
            self._memo[memo_key] = self._normalize(label_cutoff, available_by, max_year, excluded)
        return self._memo[memo_key]

    def _normalize(self, label_cutoff: int, available_by: int, max_year: Optional[int], excluded: Sequence[str]) -> PoolSpec:
        base = self.setting_mask & (self.target <= label_cutoff) & (self.avail <= available_by)
        if max_year is not None and label_cutoff <= int(max_year) * 12 + 11:
            max_year = None  # target <= cutoff already implies target and source year <= max_year
        if max_year is not None:
            base &= (self.target_year <= max_year) & (self.original_year <= max_year)
        present = set(self.family[base])
        eff = {f for f in set(excluded) if f in present}
        rest = sorted(set(excluded) - eff)
        if rest and self.history is not None:
            cand = np.flatnonzero(base & ~np.isin(self.family, sorted(eff))) if eff else np.flatnonzero(base)
            for fams in self.history.exposing(self.horizon, cand, rest):
                eff.update(fams)
        eff = tuple(sorted(eff))
        spec = PoolSpec(self.setting, self.horizon, int(label_cutoff), int(available_by), None if max_year is None else int(max_year), eff)
        if spec not in self._rows:
            m = base & ~np.isin(self.family, list(eff)) if eff else base
            rows = np.flatnonzero(m)
            self._rows[spec] = rows
            exposed = np.zeros(rows.size, dtype=bool)
            if eff and self.history is not None:
                exposed = np.array([bool(x) for x in self.history.exposing(self.horizon, rows, eff)], dtype=bool)
            self._exposed[spec] = exposed
        return spec

    def rows(self, spec: PoolSpec) -> np.ndarray:
        return self._rows[spec]

    def exposed(self, spec: PoolSpec) -> np.ndarray:
        """Boolean per pool row: history contains an excluded family (refit with recomputed history)."""
        return self._exposed[spec]


def v4_row_spec(pools: PoolIndex, v: int, h: int, max_year: int, excluded: Sequence[str]) -> PoolSpec:
    """Pool for predicting a row with target month v at horizon h (its own origin v-h)."""
    return pools.normalize(qo.fit_cutoff(v, h), int(v) - int(h), max_year, excluded)


@dataclass
class V4Context:
    setting: str
    year: int
    horizon: int
    origin: int
    test_families: Tuple[str, ...]
    status: str
    reason: Optional[str]
    rounds: List[int]
    scoring: List[int]
    members: pd.DataFrame  # row, round, target_ord, spec_id, hx, base_ok (scoring keys, frozen before scores)
    calibration: pd.DataFrame  # scoring_round, scoring_target_ord, row, round, target_ord, spec_id, hx, base_ok
    final_calibration: pd.DataFrame  # row, round, target_ord, spec_id, hx, base_ok
    fit_spec: Optional[PoolSpec]
    specs: Dict[str, PoolSpec]

    @property
    def selection_signature(self) -> str:
        cols_m = self.members[["row", "round", "spec_id", "hx"]].to_numpy().tolist()
        cols_c = self.calibration[["scoring_round", "scoring_target_ord", "row", "round", "spec_id", "hx"]].to_numpy().tolist()
        text = json.dumps([self.setting, int(self.horizon), self.status, cols_m, cols_c], default=str)
        return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]

    @property
    def context_id(self) -> str:
        return f"{self.setting}_y{self.year}_h{self.horizon:02d}_o{sd.ord_label(self.origin)}"


def v4_label_mask(frame: pd.DataFrame, setting: str, year: int, origin: int, test_families: Sequence[str]) -> np.ndarray:
    """Eligible supervised labels of an outer context: setting role, fold window (<= Y-1 for
    recipient and source year), recipient target and source availability <= origin, no test family."""
    m = branch_mask(frame, setting)
    m &= (frame["target_year"].to_numpy() <= year - 1) & (frame["original_year"].to_numpy() <= year - 1)
    m &= (frame["target_ord"].to_numpy() <= origin) & (frame["source_available_ord"].to_numpy() <= origin)
    if len(test_families):
        m &= ~frame["source_family"].isin(list(test_families)).to_numpy()
    return m


def hx_label(hx: Sequence[str]) -> str:
    return ";".join(hx)


def hx_parse(label) -> Tuple[str, ...]:
    return tuple(x for x in str(label).split(";") if x) if isinstance(label, str) else ()


def v4_plan_context(frame: pd.DataFrame, pools: PoolIndex, setting: str, year: int, h: int, origin: int, test_families: Sequence[str], cfg: Mapping[str, object]) -> V4Context:
    """Frozen from label/pool/history support only, before any candidate is scored.

    Every key row carries ``hx``: the families of its context (outer test families, the
    scoring family it serves) visible in its own history, which its prediction excludes.
    """
    test_families = tuple(sorted(set(test_families)))
    max_year = year - 1
    L = v4_label_mask(frame, setting, year, origin, test_families)
    target = frame["target_ord"].to_numpy(dtype=np.int64)
    rnd = frame["original_month_ord"].to_numpy(dtype=np.int64)
    fam = frame["source_family"].to_numpy(dtype=object)
    valid = frame["valid_score"].to_numpy(dtype=bool)
    specs: Dict[str, PoolSpec] = {}

    def spec_for(i: int, extra: Sequence[str]) -> PoolSpec:
        sp = v4_row_spec(pools, int(target[i]), h, max_year, (*test_families, fam[i], *extra))
        specs[sp.id] = sp
        return sp

    def keyed(idx: Sequence[int], extra: Sequence[str]) -> List[Dict[str, object]]:
        idx = np.asarray(idx, dtype=np.int64)
        nominal = sorted(set(test_families) | set(extra))
        hxs = pools.history.exposing(h, idx, nominal) if (pools.history is not None and nominal) else [()] * idx.size
        base = pools.history.base_ok(h, idx, hxs) if pools.history is not None else _baseline(frame)[1][idx]
        return [{"row": int(i), "target_ord": int(target[i]), "spec_id": spec_for(int(i), extra).id, "hx": hx_label(hx), "base_ok": bool(bk)} for i, hx, bk in zip(idx, hxs, base)]

    rounds = sorted(int(r) for r in np.unique(rnd[L]))
    eligible = []
    for r in rounds:
        mem = np.flatnonzero(L & (rnd == r) & valid)
        if mem.size and all(pools.rows(spec_for(i, ())).size > 0 for i in mem):
            eligible.append(r)
    scoring = eligible[-int(cfg["selection_rounds"]):]
    members, cal_rows = [], []
    avail = frame["source_available_ord"].to_numpy()
    for r in scoring:
        mem = np.flatnonzero(L & (rnd == r) & valid)
        fam_r = fam[mem[0]]
        members += [{**k, "round": r} for k in keyed(mem, (fam_r,))]
        for v in sorted(set(int(x) for x in target[mem])):
            chosen = 0
            for c in reversed([c for c in rounds if c < r]):
                lim = v - h
                cand = np.flatnonzero(L & (rnd == c) & (target < v) & (target <= lim) & (avail <= lim))
                keep = [i for i in cand if pools.rows(spec_for(i, (fam_r,))).size > 0]
                if not keep:
                    continue
                cal_rows += [{**k, "scoring_round": r, "scoring_target_ord": v, "round": c} for k in keyed(keep, (fam_r,))]
                chosen += 1
                if chosen >= int(cfg["calibration_rounds"]):
                    break
    final_rows, chosen = [], 0
    for c in reversed(rounds):
        cand = np.flatnonzero(L & (rnd == c))
        keep = [i for i in cand if pools.rows(spec_for(i, ())).size > 0]
        if not keep:
            continue
        final_rows += [{**k, "round": c} for k in keyed(keep, ())]
        chosen += 1
        if chosen >= int(cfg["calibration_rounds"]):
            break
    fit_spec = pools.normalize(origin, origin, max_year, test_families)
    specs[fit_spec.id] = fit_spec
    ok = len(scoring) >= int(cfg["min_selection_rounds"])
    status, reason = ("ok", None) if ok else ("unsupported", f"{len(scoring)} supported selection rounds; {cfg['min_selection_rounds']} required")
    if pools.rows(fit_spec).size == 0:
        status, reason = "unsupported", "empty outer fitting pool"
    cols_m = ["row", "round", "target_ord", "spec_id", "hx", "base_ok"]
    cols_c = ["scoring_round", "scoring_target_ord", "row", "round", "target_ord", "spec_id", "hx", "base_ok"]
    return V4Context(setting, year, h, origin, test_families, status, reason, rounds, scoring, pd.DataFrame(members, columns=cols_m), pd.DataFrame(cal_rows, columns=cols_c),
                     pd.DataFrame(final_rows, columns=cols_m), fit_spec, specs)


def v4_unit_key(spec_id: str, formulation: str, bundle: str, half_life: Optional[float]) -> Tuple[str, str, str, str]:
    return (spec_id, formulation, bundle, half_life_label(half_life))


def v4_unit_id(key: Tuple[str, str, str, str]) -> str:
    return hashlib.sha256("|".join(key).encode("utf-8")).hexdigest()[:16]


def _v4_matrix(h: int, idx: np.ndarray, ovr: Optional[Mapping[str, np.ndarray]]):
    """Feature rows, residual baseline and baseline-ok for ``idx`` with context overrides."""
    frame = _STATE["frames"][h]
    X = _STATE["X"][h][idx].copy()
    b_all, ok_all = _baseline(frame)
    b, ok = b_all[idx].copy(), ok_all[idx].copy()
    if ovr is not None and len(ovr["pos"]):
        X[ovr["pos"]] = ovr["X"]
        b[ovr["pos"]] = ovr["b"]
        ok[ovr["pos"]] = ovr["ok"]
    return X, b, ok


def v4_fit_predict(h: int, formulation: str, bundle: str, fit_idx: np.ndarray, fit_ovr, pred_idx: np.ndarray, pred_ovr, weight_origin: int, half_life, keep_model: bool = False):
    """One q3 fit (direct, or residual on baseline-supported rows) and its predictions; the
    residual prediction exists exactly on prediction rows with a baseline."""
    frame = _STATE["frames"][h]
    q3 = frame["q3"].to_numpy(dtype=np.float64)
    months = frame["target_ord"].to_numpy(dtype=np.int64)
    Xf, bf, okf = _v4_matrix(h, fit_idx, fit_ovr)
    sel = np.flatnonzero(okf) if formulation == "residual" else np.arange(fit_idx.size)
    y = q3[fit_idx[sel]] - bf[sel] if formulation == "residual" else q3[fit_idx]
    target = "delta" if formulation == "residual" else "q3"
    w = md.decay_weights(months[fit_idx[sel]], weight_origin, half_life) if sel.size else np.array([])
    info = {"n_fit": int(fit_idx.size), "n_fit_used": int(sel.size), "fit_max_target_ord": int(months[fit_idx[sel]].max()) if sel.size else None,
            "sum_weight": float(w.sum()), "min_weight": float(w.min()) if w.size else np.nan, "n_fit_history_overrides": int(len(fit_ovr["pos"])) if fit_ovr else 0}
    Xp, bp, okp = _v4_matrix(h, pred_idx, pred_ovr)
    if sel.size == 0:
        return None, np.full(pred_idx.size, np.nan), {**info, "status": "unsupported"}, okp
    model = md.fit_regressor(Xf[sel], y, w, _params(bundle, target), target)
    raw = model.predict(Xp)
    if formulation == "residual":
        raw = np.where(okp, bp + raw, np.nan)
    return (model if keep_model else None), raw, {**info, "status": "ok", "model_kind": model.kind}, okp


def v4_unit_task(t: Mapping[str, object]) -> Dict[str, object]:
    """One OOF fit (worker)."""
    _, raw, info, _ = v4_fit_predict(t["horizon"], t["formulation"], t["bundle"], np.asarray(t["fit_idx"]), t.get("fit_ovr"), np.asarray(t["pred_idx"]), t.get("pred_ovr"),
                                     t["weight_origin"], parse_half_life(t["half_life"]))
    return {"key": t["key"], "status": info["status"], "pred_key": np.asarray(t["pred_key"]), "raw_q3": np.asarray(raw, dtype=np.float64),
            **{k: info.get(k) for k in ("n_fit", "n_fit_used", "fit_max_target_ord", "model_kind", "sum_weight", "min_weight", "n_fit_history_overrides")}}


class V4UnitStore:
    """OOF predictions per unit, keyed by ``row * HX_SCALE + history-exclusion code``."""

    def __init__(self):
        self.units: Dict[Tuple[str, str, str, str], Dict[str, object]] = {}

    def add(self, res: Mapping[str, object]) -> None:
        order = np.argsort(res["pred_key"], kind="mergesort")
        self.units[tuple(res["key"])] = {"status": res["status"], "keys": np.asarray(res["pred_key"], dtype=np.int64)[order], "raw": np.asarray(res["raw_q3"], dtype=np.float64)[order],
                                          **{k: res.get(k) for k in ("n_fit", "n_fit_used", "fit_max_target_ord", "model_kind", "sum_weight", "min_weight", "n_fit_history_overrides")}}

    def ok(self, key) -> bool:
        return key in self.units and self.units[key]["status"] == "ok"

    def raw(self, key, pred_keys: np.ndarray) -> np.ndarray:
        """Raw q3 for packed prediction keys; NaN where the unit is unsupported or a key was not requested."""
        pred_keys = np.asarray(pred_keys, dtype=np.int64)
        out = np.full(pred_keys.size, np.nan)
        u = self.units.get(key)
        if u is None or u["status"] != "ok" or pred_keys.size == 0:
            return out
        pos = np.searchsorted(u["keys"], pred_keys)
        hit = (pos < u["keys"].size) & (u["keys"][np.minimum(pos, u["keys"].size - 1)] == pred_keys)
        out[hit] = u["raw"][pos[hit]]
        return out


def v4_pred_keys(tab: pd.DataFrame, history: Optional[V4History]) -> np.ndarray:
    codes = [history.code(hx_parse(x)) if history is not None else 0 for x in tab["hx"]] if "hx" in tab else [0] * len(tab)
    return tab["row"].to_numpy(dtype=np.int64) * HX_SCALE + np.asarray(codes, dtype=np.int64)


def v4_candidate_raw(store: V4UnitStore, pred_keys: np.ndarray, spec_ids: np.ndarray, formulation: str, bundle: str, half_life, has_base: np.ndarray) -> Tuple[np.ndarray, np.ndarray, bool]:
    """Raw q3, prediction branch and whether every *required* unit was fitted.

    A residual model is required exactly on rows with a permitted history baseline
    (``has_base``, after the row's context exclusions); rows without one use the
    same-bundle/decay direct model (``fallback_direct``). A baseline row whose residual
    unit could not be fitted makes the candidate unsupported -- it is never relabelled
    as missing history.
    """
    raw = np.full(pred_keys.size, np.nan)
    lab = np.full(pred_keys.size, "direct", dtype=object)
    if formulation == "residual":
        lab[:] = np.where(has_base, "residual", "fallback_direct")
    supported = True
    for sid in np.unique(spec_ids):
        sel = spec_ids == sid
        need_direct = sel & (lab != "residual")
        if need_direct.any():
            dkey = v4_unit_key(sid, "direct", bundle, half_life)
            supported &= store.ok(dkey)
            raw[need_direct] = store.raw(dkey, pred_keys[need_direct])
        need_res = sel & (lab == "residual")
        if need_res.any():
            rkey = v4_unit_key(sid, "residual", bundle, half_life)
            supported &= store.ok(rkey)
            raw[need_res] = store.raw(rkey, pred_keys[need_res])
    return raw, lab, bool(supported)


def v4_fit_mappings(store: V4UnitStore, frame: pd.DataFrame, cal: pd.DataFrame, formulation: str, bundle: str, half_life, method: str, min_rounds: int, history: Optional[V4History] = None) -> Dict[str, qo.Q3Mapping]:
    """Branch mappings fitted on the calibration keys' own OOF predictions.

    direct / fallback_direct: direct predictions of every calibration key; residual:
    residual predictions of the calibration keys with a permitted baseline. A learned
    mapping whose required unit is unsupported on any of its keys is unsupported (the
    key set never shrinks after a failure); ``none`` needs no calibration.
    """
    q3 = frame["q3"].to_numpy(dtype=np.float64)
    rows = cal["row"].to_numpy(dtype=np.int64)
    pkeys = v4_pred_keys(cal, history)
    base_ok = cal["base_ok"].to_numpy(dtype=bool) if "base_ok" in cal else _baseline(frame)[1][rows]
    rounds = cal["round"].to_numpy(dtype=np.int64)
    sids = cal["spec_id"].to_numpy(dtype=object)
    names = ("direct",) if formulation == "direct" else ("residual", "fallback_direct")
    out = {}
    for name in names:
        if method == "none":
            out[name] = qo.fit_mapping("none", np.array([]), np.array([]), np.array([]), min_rounds)
            continue
        form = "residual" if name == "residual" else "direct"
        keep = base_ok if name == "residual" else np.ones(rows.size, dtype=bool)
        raw = np.full(rows.size, np.nan)
        failed = []
        for sid in np.unique(sids[keep]) if keep.any() else []:
            sel = keep & (sids == sid)
            key = v4_unit_key(sid, form, bundle, half_life)
            if not store.ok(key):
                failed.append(sid)
                continue
            raw[sel] = store.raw(key, pkeys[sel])
        if failed or not np.isfinite(raw[keep]).all():
            mapping = qo.Q3Mapping(method, "unsupported", f"{form} OOF unit unsupported for {len(failed)} calibration pool spec(s)" if failed else "missing calibration OOF prediction",
                                   months=tuple(sorted({int(r) for r in rounds[keep]})), n_rows=int(keep.sum()))
        else:
            mapping = qo.fit_mapping(method, raw[keep], q3[rows[keep]], rounds[keep], min_rounds)
        mapping.fit_rows = tuple(int(x) for x in rows[keep])
        out[name] = mapping
    return out


def v4_candidates(bundles: Mapping[str, object]) -> List[Dict[str, object]]:
    out = []
    for bo, b in enumerate([c["id"] for c in bundles["candidates"]]):
        for hl in V4_HALF_LIVES:
            for formulation in FORMULATIONS:
                for method in qo.METHOD_ORDER:
                    out.append({"bundle": b, "bundle_order": bo, "half_life": half_life_label(hl), "decay_order": V4_DECAY_ORDER[hl], "formulation": formulation,
                                "formulation_order": qo.FORMULATION_ORDER.index(formulation), "method": method, "method_order": qo.METHOD_ORDER.index(method)})
    return out


def v4_score_context(store: V4UnitStore, frame: pd.DataFrame, ctx: V4Context, bundles: Mapping[str, object], cfg: Mapping[str, object], history: Optional[V4History] = None) -> Tuple[pd.DataFrame, Dict[Tuple, pd.DataFrame]]:
    """Every declared recipe on the frozen scoring keys; returns scores and per-candidate predictions."""
    from sklearn.metrics import roc_auc_score

    q3 = frame["q3"].to_numpy(dtype=np.float64)
    crisis = frame["actual_crisis"].to_numpy(dtype=np.float64)
    min_rounds = int(cfg["min_calibration_rounds"])
    groups = [(r, v, g) for (r, v), g in ctx.members.groupby(["round", "target_ord"], sort=True)]
    cal_by = {k: g for k, g in ctx.calibration.groupby(["scoring_round", "scoring_target_ord"], sort=True)}
    empty_cal = ctx.calibration.iloc[0:0]
    rows_out, preds = [], {}
    for cand in v4_candidates(bundles):
        b, hl, form, method = cand["bundle"], parse_half_life(cand["half_life"]), cand["formulation"], cand["method"]
        finals, truths, crs, parts, reason = [], [], [], [], None
        for r, v, g in groups:
            idx = g["row"].to_numpy(dtype=np.int64)
            raw, lab, supported = v4_candidate_raw(store, v4_pred_keys(g, history), g["spec_id"].to_numpy(dtype=object), form, b, hl, g["base_ok"].to_numpy(dtype=bool))
            if not supported or not np.isfinite(raw).all():
                reason = f"base OOF fit unsupported at scoring month {sd.ord_label(v)} (round {sd.ord_label(r)})"
                break
            maps = v4_fit_mappings(store, frame, cal_by.get((r, v), empty_cal), form, b, hl, method, min_rounds, history)
            mapped, why = qo.apply_branches(raw, lab, maps)
            if mapped is None:
                reason = f"{why} at scoring month {sd.ord_label(v)} (round {sd.ord_label(r)})"
                break
            fin, clipped = qo.bound_share(mapped)
            finals.append(fin), truths.append(q3[idx]), crs.append(crisis[idx])
            parts.append(pd.DataFrame({"row": idx, "hx": g["hx"].to_numpy(), "round": r, "target_ord": v, "raw_q3": raw, "final_q3": fin, "clipped": clipped, "prediction_branch": lab}))
        base = {"context_id": ctx.context_id, "selection_signature": ctx.selection_signature, **cand}
        if reason:
            rows_out.append({**base, "status": "unsupported", "reason": reason, "n": 0, "rmse": np.nan, "auc": np.nan})
            continue
        f, t, c = np.concatenate(finals), np.concatenate(truths), np.concatenate(crs)
        auc = float(roc_auc_score(c == 1, f)) if np.unique(c).size == 2 else np.nan
        rows_out.append({**base, "status": "ok", "reason": None, "n": int(f.size), "rmse": float(np.sqrt(np.mean((f - t) ** 2))), "auc": auc})
        preds[(b, cand["half_life"], form, method)] = pd.concat(parts, ignore_index=True)
    return pd.DataFrame(rows_out), preds


def v4_final_task(t: Mapping[str, object]) -> Dict[str, object]:
    """Fit the selected recipe on the outer pool and predict the job's frozen test rows (worker).

    ``fit_ovr`` / ``pred_ovr`` carry recomputed history for rows exposed to the job's test
    families; every q2/q3/q4/q5 model uses the same context-specific feature rows."""
    h, formulation, bundle = t["horizon"], t["formulation"], t["bundle"]
    hl = parse_half_life(t["half_life"])
    frame = _STATE["frames"][h]
    fit_idx, pred_idx = np.asarray(t["fit_idx"]), np.asarray(t["pred_idx"])
    months = frame["target_ord"].to_numpy(dtype=np.int64)
    Xf, _, _ = _v4_matrix(h, fit_idx, t.get("fit_ovr"))
    Xp, _, _ = _v4_matrix(h, pred_idx, t.get("pred_ovr"))
    w = md.decay_weights(months[fit_idx], t["origin_ord"], hl)
    models, others = {}, {}
    for target in ("q2", "q4", "q5"):
        models[target] = md.fit_regressor(Xf, frame[target].to_numpy(dtype=float)[fit_idx], w, _params(bundle, target), target)
        others[target] = models[target].predict(Xp)
    dm, raw, _, okp = v4_fit_predict(h, "direct", bundle, fit_idx, t.get("fit_ovr"), pred_idx, t.get("pred_ovr"), t["origin_ord"], hl, keep_model=True)
    models["q3_direct"] = dm
    branch = np.full(pred_idx.size, "direct", dtype=object)
    status, reason = "completed", None
    base = np.full(pred_idx.size, np.nan)
    if formulation == "residual":
        rm, res, _, need = v4_fit_predict(h, "residual", bundle, fit_idx, t.get("fit_ovr"), pred_idx, t.get("pred_ovr"), t["origin_ord"], hl, keep_model=True)
        if rm is None and need.any():
            status, reason = "unsupported", "no baseline-supported outer fitting rows for test rows with a baseline"
        models["q3_residual_delta"] = rm
        branch = np.where(need, "residual", "fallback_direct").astype(object)
        raw = np.where(need, res, raw)
        _, bp, _ = _v4_matrix(h, pred_idx, t.get("pred_ovr"))
        base = np.where(need, bp, np.nan)
    pred = pd.DataFrame({"row": pred_idx, "area_id": frame["area_id"].to_numpy()[pred_idx], "target_ord": months[pred_idx], "hx": t.get("pred_hx", [""] * pred_idx.size), "q2_raw": others["q2"], "q3_raw": raw,
                         "q4_raw": others["q4"], "q5_raw": others["q5"], "prediction_branch": branch, "baseline_q3": base})
    mapped, why = (None, reason) if status != "completed" else qo.apply_branches(raw, branch, t["mappings"])
    if mapped is None:
        pred["q3_final"], pred["clipped"], cal = np.nan, False, ("unavailable", why)
    else:
        final, clipped = qo.bound_share(mapped)
        pred["q3_final"], pred["clipped"], cal = final, clipped, ("ok", None)
    ledger = pd.DataFrame({"row": fit_idx, "area_id": frame["area_id"].to_numpy()[fit_idx], "target_ord": months[fit_idx], "source_family": frame["source_family"].to_numpy()[fit_idx],
                           "source_available_ord": frame["source_available_ord"].to_numpy()[fit_idx], "is_copy": frame["is_copy"].to_numpy()[fit_idx], "weight": w})
    return {"key": t["key"], "status": status, "reason": reason, "calibration_status": cal[0], "calibration_reason": cal[1], "predictions": pred, "fit_ledger": ledger, "models": models}


def v4_freeze_cohorts(ledger: pd.DataFrame, frames: Mapping[int, pd.DataFrame], settings: Sequence[str], years: Sequence[int], horizons: Sequence[int]) -> pd.DataFrame:
    """Per-setting outer cohorts, frozen from labels/sources before any fit.

    original: observed labels of year Y only; augmented: observed labels plus permitted
    copies of year Y. Exclusions: invalid target shares, invalid reported phase, and
    (H>0) unverified realized weather at the oracle offsets.
    """
    out = []
    for h in horizons:
        f = frames[h]
        verified = dict(zip(zip(f["area_id"].astype(int), f["target_ord"].astype(int)), f["oracle_all_verified"].astype(bool)))
        for setting in settings:
            for year in years:
                m = ledger["target_ord"] // 12 == year
                if setting == "original":
                    m &= ~ledger["is_copy"]
                for r in ledger.loc[m].itertuples(index=False):
                    key = (int(r.area_id), int(r.target_ord))
                    if not r.valid_target:
                        status, reason = "excluded", f"target:{r.target_invalid_reason}"
                    elif not r.valid_score:
                        status, reason = "excluded", "invalid_reported_phase"
                    elif h > 0 and not verified.get(key, False):
                        status, reason = "excluded", "oracle_weather_unverified"
                    else:
                        status, reason = "primary", None
                    out.append({"data_setting": setting, "outer_year": year, "horizon": h, "area_id": key[0], "target_ord": key[1], "is_copy": bool(r.is_copy),
                                "source_family": r.source_family, "original_month_ord": int(r.original_month_ord), "status": status, "reason": reason})
    cohort = pd.DataFrame(out)
    if cohort.duplicated(["data_setting", "outer_year", "horizon", "area_id", "target_ord"]).any():
        raise AugExpError("duplicate canonical cohort keys")
    if cohort.loc[cohort["data_setting"] == "original", "is_copy"].any():
        raise AugExpError("a copied label entered the original outer cohort")
    return cohort


def cohort_digest(keys: pd.DataFrame) -> str:
    k = keys[["area_id", "target_ord"]].astype(np.int64).sort_values(["area_id", "target_ord"], kind="mergesort").to_numpy()
    return hashlib.sha256(np.ascontiguousarray(k).tobytes()).hexdigest()


def v4_jobs(cohort: pd.DataFrame, frames: Mapping[int, pd.DataFrame]) -> pd.DataFrame:
    """One outer job per (setting, year, H, origin) over the frozen primary keys."""
    rows = []
    prim = cohort.loc[cohort["status"] == "primary"]
    for (setting, year, h), g in prim.groupby(["data_setting", "outer_year", "horizon"], sort=True):
        g = g.assign(origin_ord=g["target_ord"] - h)
        for o, gg in g.groupby("origin_ord", sort=True):
            rows.append({"job_id": f"{setting}_y{year}_h{h:02d}_o{sd.ord_label(o)}", "data_setting": setting, "outer_year": int(year), "horizon": int(h), "origin_ord": int(o),
                         "n_test": len(gg), "n_test_copies": int(gg["is_copy"].sum()), "test_families": ";".join(sorted(set(gg["source_family"])))})
    return pd.DataFrame(rows)


def v4_slot_metrics(m: pd.DataFrame) -> Dict[str, object]:
    """Metrics of one keyed truth/prediction frame (q3, actual_crisis, q3_raw, q3_final, ...)."""
    from ipcch.somalia_oracle import q3eval as qe

    out: Dict[str, object] = {"n": int(len(m)), "n_areas": int(m["area_id"].nunique()), "n_months": int(m["target_ord"].nunique()), "n_original_reports": int(m["source_family"].nunique()),
                              "n_originals": int((~m["is_copy"]).sum()), "n_copies": int(m["is_copy"].sum())}
    for kind in ("raw", "final"):
        sm = qe.share_metrics(m["q3"], m[f"q3_{kind}"])
        out.update({f"{kind}_{k}": v for k, v in sm.items()})
        out[f"{kind}_r2_reason"] = "constant truth" if not np.isfinite(sm["r2"]) else None
        out[f"{kind}_auc"] = qe.pooled_auc(m["actual_crisis"], m[f"q3_{kind}"])
        out[f"{kind}_auc_reason"] = "one crisis class" if not np.isfinite(out[f"{kind}_auc"]) else None
    out.update({f"bin_{k}": v for k, v in qe.binary_metrics(m["actual_crisis"], m["q3_final"].to_numpy() >= qe.BINARY_THRESHOLD).items()})
    out["n_clipped"] = int(m["clipped"].astype(bool).sum())
    out["n_fallback_direct"] = int((m["prediction_branch"] == "fallback_direct").sum())
    out["n_residual_branch"] = int((m["prediction_branch"] == "residual").sum())
    return out


def v4_evaluate(cohort: pd.DataFrame, preds: pd.DataFrame, frames: Mapping[int, pd.DataFrame], settings, years, horizons) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Annual slots per (setting, year, H) and pooled slots per (setting, H).

    Truth and predictions are joined on explicit keys with one-to-one validation. A
    missing or non-finite required final prediction makes the slot, and its setting/H
    pooled result, incomplete (G9); raw predictions never replace final ones.
    """
    truth_cols = ["area_id", "target_ord", "q3", "actual_crisis"]
    annual, pooled_parts, pooled_status = [], {}, {}
    for setting in settings:
        for h in horizons:
            f = frames[h][truth_cols]
            parts, bad = [], []
            for year in years:
                c = cohort.loc[(cohort["data_setting"] == setting) & (cohort["outer_year"] == year) & (cohort["horizon"] == h)]
                prim = c.loc[c["status"] == "primary", ["area_id", "target_ord", "is_copy", "source_family"]]
                base = {"data_setting": setting, "outer_year": year, "horizon": h, "n_cohort": len(c), "n_primary": len(prim), "n_excluded": int((c["status"] != "primary").sum()),
                        "cohort_sha256": cohort_digest(prim)}
                if prim.empty:
                    annual.append({**base, "status": "empty_cohort", "reason": "no source-eligible rows"})
                    continue
                p = preds.loc[(preds["data_setting"] == setting) & (preds["outer_year"] == year) & (preds["horizon"] == h)]
                if p.duplicated(["area_id", "target_ord"]).any():
                    raise AugExpError(f"duplicate prediction keys in {setting}/{year}/H{h}")
                extra = p.merge(prim[["area_id", "target_ord"]], on=["area_id", "target_ord"], how="left", indicator=True)["_merge"].eq("left_only")
                if extra.any():
                    raise AugExpError(f"{int(extra.sum())} prediction keys outside the frozen {setting}/{year}/H{h} cohort")
                m = prim.merge(f, on=["area_id", "target_ord"], how="left", validate="one_to_one")
                m = m.merge(p[["area_id", "target_ord", "q3_raw", "q3_final", "clipped", "prediction_branch", "job_id"]], on=["area_id", "target_ord"], how="left", validate="one_to_one")
                missing = ~np.isfinite(m["q3_final"].to_numpy(dtype=float))
                if missing.any():
                    annual.append({**base, "status": "incomplete", "reason": f"{int(missing.sum())} of {len(m)} required final predictions missing or unavailable"})
                    bad.append(year)
                    continue
                annual.append({**base, "status": "complete", "reason": None, **v4_slot_metrics(m)})
                parts.append(m.assign(outer_year=year))
            key = (setting, h)
            pooled_parts[key] = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
            pooled_status[key] = bad
    pooled = []
    for (setting, h), m in pooled_parts.items():
        base = {"data_setting": setting, "horizon": h, "years": ";".join(str(y) for y in years)}
        if pooled_status[(setting, h)]:
            pooled.append({**base, "status": "incomplete", "reason": "annual slots incomplete: " + ";".join(str(y) for y in pooled_status[(setting, h)])})
            continue
        if m.empty:
            pooled.append({**base, "status": "empty_cohort", "reason": "no source-eligible rows in any year"})
            continue
        comp = m.groupby("outer_year").size()
        pooled.append({**base, "status": "complete", "reason": None, "rows_by_year": ";".join(f"{y}:{n}" for y, n in comp.items()), "cohort_sha256": cohort_digest(m), **v4_slot_metrics(m)})
    return pd.DataFrame(annual), pd.DataFrame(pooled)
