"""q3-first optimization of the Somalia oracle experiment (task somalia-auc-r2-optimization).

H0 selection: for each fold, chronological out-of-fold (OOF) q3 predictions are
generated inside the fold's training window; each candidate
(formulation x bundle x calibration method) is scored by pooled unweighted final-q3
RMSE on frozen scoring months, with calibration mappings fitted only on earlier OOF
months. H3/H6/H12 inherit the fold's H0 recipe and only refit parameters/mappings.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import roc_auc_score

from ipcch import paths
from ipcch.somalia_oracle import CUMULATIVE_COLUMNS, FOLDS
from ipcch.somalia_oracle import data as sd
from ipcch.somalia_oracle import modeling as md

CONFIG_PATH = paths.CONFIG_DIR / "somalia_q3_optimization.json"
METHOD_ORDER = ("none", "shift", "isotonic")
FORMULATION_ORDER = ("direct", "residual")
# view -> (feature arm, q3 formulation); D_selected is a selected view, not another fit.
VIEW_SPEC = {"A": ("A", "direct"), "B": ("B", "direct"), "C": ("C", "direct"), "D_direct": ("D", "direct"), "D_residual": ("D", "residual")}
VIEWS = (*VIEW_SPEC, "D_selected")
# H0 search views; at H0 C is identical to B and reuses its selection/fits.
H0_SEARCH_VIEWS = ("A", "B", "D_direct", "D_residual")
# H>0 receiving view -> H0 recipe source view (C inherits the H0 B/C recipe).
RECIPE_SOURCE = {"A": "A", "B": "B", "C": "B", "D_direct": "D_direct", "D_residual": "D_residual"}
OTHER_TARGETS = ("q2", "q4", "q5")


class Q3OptError(RuntimeError):
    """A q3-optimization contract invariant does not hold."""


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_config(path: Path = CONFIG_PATH) -> Tuple[Dict[str, object], Dict[str, object]]:
    cfg = json.loads(Path(path).read_text(encoding="utf-8"))
    bundle_path = Path(cfg["bundle_config"])
    if not bundle_path.is_absolute():
        bundle_path = paths.PROJECT_ROOT / bundle_path
    if sha256_file(bundle_path) != cfg["bundle_config_sha256"]:
        raise Q3OptError(f"bundle config {bundle_path} does not match its pinned sha256")
    if tuple(cfg["calibration_methods"]) != METHOD_ORDER or tuple(cfg["formulation_order"]) != FORMULATION_ORDER:
        raise Q3OptError("calibration/formulation inventory drifted from the approved contract")
    if cfg["selection_metric"] != "pooled_unweighted_final_q3_rmse" or list(cfg["final_bound"]) != [0.0, 1.0]:
        raise Q3OptError("selection metric or final bound drifted from the approved contract")
    bundles = md.load_candidates(bundle_path)
    cfg["_bundle_path"] = str(bundle_path)
    return cfg, bundles


# --------------------------------------------------------------------------
# Calibration (R13): none / shift / isotonic, then the fixed [0, 1] bound
# --------------------------------------------------------------------------


@dataclass
class Q3Mapping:
    method: str
    status: str
    reason: Optional[str] = None
    shift: Optional[float] = None
    iso: object = None
    months: Tuple[int, ...] = ()
    n_rows: int = 0
    fit_rows: Tuple[int, ...] = ()

    @property
    def ok(self) -> bool:
        return self.status == "ok"

    def apply(self, raw: np.ndarray) -> np.ndarray:
        if not self.ok:
            raise Q3OptError(f"cannot apply unsupported {self.method} mapping: {self.reason}")
        raw = np.asarray(raw, dtype=np.float64)
        if self.method == "none":
            return raw.copy()
        if self.method == "shift":
            return raw - self.shift
        return np.asarray(self.iso.predict(raw), dtype=np.float64)

    def describe(self) -> Dict[str, object]:
        out = {"method": self.method, "status": self.status, "reason": self.reason, "calibration_months": ";".join(sd.ord_labels(self.months)), "calibration_rows": self.n_rows, "shift": self.shift}
        if self.iso is not None:
            out["isotonic_thresholds"] = int(len(self.iso.X_thresholds_))
            out["isotonic_x"] = json.dumps([float(v) for v in self.iso.X_thresholds_])
            out["isotonic_y"] = json.dumps([float(v) for v in self.iso.y_thresholds_])
        out["fit_rows"] = json.dumps([int(r) for r in self.fit_rows])
        return out


def fit_mapping(method: str, raw: np.ndarray, truth: np.ndarray, months: np.ndarray, min_months: int) -> Q3Mapping:
    if method not in METHOD_ORDER:
        raise Q3OptError(f"unknown calibration method {method!r}")
    if method == "none":
        return Q3Mapping("none", "ok")
    raw = np.asarray(raw, dtype=np.float64)
    truth = np.asarray(truth, dtype=np.float64)
    present = tuple(sorted({int(m) for m in np.asarray(months)}))
    if len(present) < min_months:
        return Q3Mapping(method, "unsupported", f"{len(present)} calibration months with rows; {min_months} required", months=present, n_rows=int(raw.size))
    if not (np.isfinite(raw).all() and np.isfinite(truth).all()):
        raise Q3OptError("non-finite calibration input")
    if method == "shift":
        return Q3Mapping("shift", "ok", shift=float(np.mean(raw - truth)), months=present, n_rows=int(raw.size))
    if np.unique(raw).size < 2:
        return Q3Mapping("isotonic", "unsupported", "fewer than two distinct calibration scores", months=present, n_rows=int(raw.size))
    iso = IsotonicRegression(y_min=0.0, y_max=1.0, increasing=True, out_of_bounds="clip").fit(raw, truth)
    return Q3Mapping("isotonic", "ok", iso=iso, months=present, n_rows=int(raw.size))


def bound_share(values: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    values = np.asarray(values, dtype=np.float64)
    final = np.clip(values, 0.0, 1.0)
    return final, final != values


# --------------------------------------------------------------------------
# Chronological plans
# --------------------------------------------------------------------------


def window_months(frame: pd.DataFrame, window: Sequence[int], cutoff: int) -> List[int]:
    mask = frame["target_year"].isin(list(window)) & (frame["target_ord"] <= cutoff)
    return sorted(int(m) for m in frame.loc[mask, "target_ord"].unique())


def fit_cutoff(v: int, horizon: int) -> int:
    """Latest supervised label month allowed for a model predicting target month v."""
    return min(int(v) - int(horizon), int(v) - 1)


def oof_months(months: Sequence[int], horizon: int) -> List[int]:
    return [v for v in months if any(m <= fit_cutoff(v, horizon) for m in months)]


def calibration_months_for(v: int, oof: Sequence[int], horizon: int, n: int) -> List[int]:
    return [c for c in oof if c < v and c <= v - horizon][-n:]


def selection_plan(frame: pd.DataFrame, window: Sequence[int], horizon: int, cutoff: int, cfg: Mapping[str, object]) -> Dict[str, object]:
    """Frozen from label/pool support only, before any candidate is scored."""
    months = window_months(frame, window, cutoff)
    oof = oof_months(months, horizon)
    scorable = [v for v in oof if bool(frame.loc[frame["target_ord"] == v, "valid_score"].any())]
    scoring = scorable[-int(cfg["scoring_months"]):]
    calibration = {v: calibration_months_for(v, oof, horizon, int(cfg["calibration_months"])) for v in scoring}
    final = oof[-int(cfg["calibration_months"]):]
    status = "ok" if len(scoring) >= int(cfg["min_scoring_months"]) else "unsupported"
    needed = sorted(set(scoring) | {c for cs in calibration.values() for c in cs} | set(final))
    return {"months": months, "oof": oof, "scoring": scoring, "calibration": calibration, "final": final, "needed": needed, "status": status}


def receiving_plan(frame: pd.DataFrame, window: Sequence[int], horizon: int, origin: int, cfg: Mapping[str, object]) -> Dict[str, object]:
    months = window_months(frame, window, origin)
    oof = oof_months(months, horizon)
    final = oof[-int(cfg["calibration_months"]):]
    return {"months": months, "oof": oof, "final": final, "needed": final}


# --------------------------------------------------------------------------
# Fitting primitives (executed in workers)
# --------------------------------------------------------------------------

_STATE: Dict[str, object] = {}


def init_state(frames: Mapping[int, pd.DataFrame], schemas: Mapping[Tuple[int, str], Sequence[str]], cfg, bundles) -> None:
    _STATE.clear()
    _STATE["frames"] = dict(frames)
    _STATE["X"] = {key: frames[key[0]].loc[:, list(cols)].to_numpy(dtype=np.float32) for key, cols in schemas.items()}
    _STATE["cfg"] = cfg
    _STATE["bundles"] = bundles


def _bundle(bundle_id: str) -> Mapping[str, object]:
    for candidate in _STATE["bundles"]["candidates"]:
        if candidate["id"] == bundle_id:
            return candidate
    raise Q3OptError(f"unknown bundle {bundle_id}")


def _params(bundle_id: str, target: str) -> Dict[str, object]:
    # delta (residual) is the q3 regressor and uses the q3 overrides.
    return md.candidate_params(_STATE["bundles"], _bundle(bundle_id), "q3" if target in ("q3", "delta") else target)


def baseline(frame: pd.DataFrame, cfg: Mapping[str, object]) -> Tuple[np.ndarray, np.ndarray]:
    b = frame[cfg["residual_baseline_column"]].to_numpy(dtype=np.float64)
    src = frame[cfg["residual_baseline_source_column"]].to_numpy(dtype=np.int64)
    supported = np.isfinite(b) & (src >= 0)
    if np.any(supported & (src > np.minimum(frame["origin_ord"].to_numpy(), frame["target_ord"].to_numpy() - 1))):
        raise Q3OptError("residual baseline source month violates U<=O, U<T")
    return b, supported


def _fit_rows(frame: pd.DataFrame, window: Sequence[int], label_cutoff: int) -> np.ndarray:
    return np.flatnonzero((frame["target_year"].isin(list(window)) & (frame["target_ord"] <= label_cutoff)).to_numpy())


def fit_q3(horizon: int, arm: str, formulation: str, bundle_id: str, fit_idx: np.ndarray, weight_origin: int) -> Tuple[Optional[md.FittedRegressor], Dict[str, object]]:
    """Fit the q3 regressor (direct share, or residual delta on baseline-supported rows)."""
    frame = _STATE["frames"][horizon]
    X = _STATE["X"][(horizon, arm)]
    q3 = frame["q3"].to_numpy(dtype=np.float64)
    months = frame["target_ord"].to_numpy(dtype=np.int64)
    if formulation == "residual":
        b, supported = baseline(frame, _STATE["cfg"])
        fit_idx = fit_idx[supported[fit_idx]]
        y = q3[fit_idx] - b[fit_idx]
        target = "delta"
    else:
        y = q3[fit_idx]
        target = "q3"
    info = {"n_fit": int(fit_idx.size), "fit_max_target_ord": int(months[fit_idx].max()) if fit_idx.size else None, "weight_origin_ord": int(weight_origin)}
    if fit_idx.size == 0:
        info["status"] = "unsupported"
        info["reason"] = "no baseline-supported fitting rows" if formulation == "residual" else "empty fitting pool"
        return None, info
    weights = md.decay_weights(months[fit_idx], weight_origin)
    model = md.fit_regressor(X[fit_idx], y, weights, _params(bundle_id, target), target)
    info["status"] = "ok"
    info["model_kind"] = model.kind
    return model, info


def predict_q3(horizon: int, arm: str, formulation: str, model: md.FittedRegressor, idx: np.ndarray) -> np.ndarray:
    """Raw (unbounded) q3; residual rows without a baseline get NaN (caller falls back)."""
    frame = _STATE["frames"][horizon]
    X = _STATE["X"][(horizon, arm)]
    raw = model.predict(X[idx])
    if formulation == "residual":
        b, supported = baseline(frame, _STATE["cfg"])
        out = np.full(idx.size, np.nan)
        ok = supported[idx]
        out[ok] = b[idx][ok] + raw[ok]
        return out
    return raw


def oof_task(task: Mapping[str, object]) -> Dict[str, object]:
    """One OOF fit: model for target month v trained on labels <= min(v-H, v-1)."""
    h, arm, formulation, bundle_id, v = task["horizon"], task["arm"], task["formulation"], task["bundle"], int(task["v"])
    frame = _STATE["frames"][h]
    window = task["window"]
    fit_idx = _fit_rows(frame, window, fit_cutoff(v, h))
    pred_idx = np.flatnonzero((frame["target_ord"] == v).to_numpy() & frame["target_year"].isin(list(window)).to_numpy())
    model, info = fit_q3(h, arm, formulation, bundle_id, fit_idx, v - h)
    out = {**{k: task[k] for k in ("scope", "horizon", "arm", "formulation", "bundle", "v")}, **info, "fit_label_cutoff_ord": fit_cutoff(v, h)}
    if model is None:
        out["pred_idx"], out["raw_q3"] = pred_idx, np.full(pred_idx.size, np.nan)
        return out
    out["pred_idx"], out["raw_q3"] = pred_idx, predict_q3(h, arm, formulation, model, pred_idx)
    return out


# --------------------------------------------------------------------------
# OOF store and candidate scoring (parent process)
# --------------------------------------------------------------------------


class OOFStore:
    """(scope, horizon, arm, formulation, bundle, v) -> (row idx, raw q3)."""

    def __init__(self) -> None:
        self.data: Dict[Tuple, Tuple[np.ndarray, np.ndarray]] = {}
        self.status: Dict[Tuple, str] = {}
        self.ledger: List[Dict[str, object]] = []

    def add(self, result: Mapping[str, object]) -> None:
        key = (result["scope"], result["horizon"], result["arm"], result["formulation"], result["bundle"], int(result["v"]))
        self.data[key] = (np.asarray(result["pred_idx"]), np.asarray(result["raw_q3"], dtype=np.float64))
        self.status[key] = result["status"]
        self.ledger.append({k: result.get(k) for k in ("scope", "horizon", "arm", "formulation", "bundle", "v", "status", "reason", "n_fit", "fit_max_target_ord", "fit_label_cutoff_ord", "weight_origin_ord", "model_kind")})

    def get(self, scope, horizon, arm, formulation, bundle, v) -> Tuple[np.ndarray, np.ndarray]:
        key = (scope, horizon, arm, formulation, bundle, int(v))
        if key not in self.data:
            raise Q3OptError(f"missing OOF predictions for {key}")
        return self.data[key]

    def supported(self, scope, horizon, arm, formulation, bundle, v) -> bool:
        return self.status.get((scope, horizon, arm, formulation, bundle, int(v))) == "ok"


def branch_predictions(store: OOFStore, scope, horizon, arm, formulation, bundle, v) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Rows at month v with raw q3 and branch label (direct / residual / fallback_direct)."""
    idx, raw = store.get(scope, horizon, arm, formulation, bundle, v)
    if formulation == "direct":
        return idx, raw, np.full(idx.size, "direct", dtype=object)
    didx, draw = store.get(scope, horizon, arm, "direct", bundle, v)
    if not np.array_equal(idx, didx):
        raise Q3OptError("residual and direct OOF rows differ")
    branch = np.where(np.isfinite(raw), "residual", "fallback_direct").astype(object)
    return idx, np.where(np.isfinite(raw), raw, draw), branch


def fit_branch_mappings(store: OOFStore, frame: pd.DataFrame, scope, horizon, arm, formulation, bundle, method, months: Sequence[int], cfg) -> Dict[str, Q3Mapping]:
    """Mappings per branch fitted on OOF predictions of the given calibration months."""
    q3 = frame["q3"].to_numpy(dtype=np.float64)
    min_months = int(cfg["min_calibration_months"])
    mappings = {}
    branches = ("direct",) if formulation == "direct" else ("residual", "fallback_direct")
    for branch in branches:
        raws, truths, ms, rows = [], [], [], []
        source = "direct" if branch in ("direct", "fallback_direct") else formulation
        for c in months:
            if not store.supported(scope, horizon, arm, source, bundle, c):
                continue  # an unsupported OOF fit contributes no calibration month
            idx, raw = store.get(scope, horizon, arm, source, bundle, c)
            if branch == "residual":
                keep = np.isfinite(raw)
                idx, raw = idx[keep], raw[keep]
            if idx.size == 0:
                continue
            raws.append(raw), truths.append(q3[idx]), ms.append(np.full(idx.size, c)), rows.append(idx)
        raw = np.concatenate(raws) if raws else np.array([])
        mapping = fit_mapping(method, raw, np.concatenate(truths) if truths else np.array([]), np.concatenate(ms) if ms else np.array([]), min_months)
        mapping.fit_rows = tuple(int(r) for r in (np.concatenate(rows) if rows else []))
        mappings[branch] = mapping
    return mappings


def apply_branches(raw: np.ndarray, branch: np.ndarray, mappings: Mapping[str, Q3Mapping]) -> Tuple[Optional[np.ndarray], Optional[str]]:
    mapped = np.full(raw.size, np.nan)
    for name in np.unique(branch):
        rows = branch == name
        mapping = mappings[name]
        if not mapping.ok:
            return None, f"{name} mapping unsupported: {mapping.reason}"
        mapped[rows] = mapping.apply(raw[rows])
    return mapped, None


def score_candidates(store: OOFStore, frame: pd.DataFrame, plan: Mapping[str, object], scope, horizon, view: str, cfg) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Every (bundle, method) for one view on the frozen scoring keys."""
    arm, formulation = VIEW_SPEC[view]
    q3 = frame["q3"].to_numpy(dtype=np.float64)
    valid_score = frame["valid_score"].to_numpy(dtype=bool)
    crisis = frame["actual_crisis"].to_numpy(dtype=np.float64)
    rows, preds = [], []
    for bundle_order, candidate in enumerate(_bundle_ids(cfg)):
        for method in METHOD_ORDER:
            finals, truths, crises, reason = [], [], [], None
            cand_rows = []
            for v in plan["scoring"]:
                idx, raw, branch = branch_predictions(store, scope, horizon, arm, formulation, candidate, v)
                keep = valid_score[idx]
                idx, raw, branch = idx[keep], raw[keep], branch[keep]
                base_ok = store.supported(scope, horizon, arm, "direct", candidate, v) and (formulation == "direct" or store.supported(scope, horizon, arm, formulation, candidate, v))
                if not base_ok or not np.isfinite(raw).all():
                    reason = f"base OOF fit unsupported at {sd.ord_label(v)}"
                    break
                mappings = fit_branch_mappings(store, frame, scope, horizon, arm, formulation, candidate, method, plan["calibration"][v], cfg)
                mapped, why = apply_branches(raw, branch, mappings)
                if mapped is None:
                    reason = f"{why} at {sd.ord_label(v)}"
                    break
                final, clipped = bound_share(mapped)
                finals.append(final), truths.append(q3[idx]), crises.append(crisis[idx])
                cand_rows.append(pd.DataFrame({"row": idx, "target_ord": v, "raw_q3": raw, "final_q3": final, "clipped": clipped, "branch": branch}))
            base = {"scope": scope, "horizon": horizon, "view": view, "arm": arm, "formulation": formulation, "bundle": candidate, "bundle_order": bundle_order, "method": method, "method_order": METHOD_ORDER.index(method), "formulation_order": FORMULATION_ORDER.index(formulation)}
            if reason is not None:
                rows.append({**base, "status": "unsupported", "reason": reason, "n": 0, "rmse": np.nan, "auc": np.nan})
                continue
            f, t, c = np.concatenate(finals), np.concatenate(truths), np.concatenate(crises)
            auc = roc_auc_score(c == 1, f) if np.unique(c).size == 2 else np.nan
            rows.append({**base, "status": "ok", "reason": None, "n": int(f.size), "rmse": float(np.sqrt(np.mean((f - t) ** 2))), "auc": auc, "n_clipped": int(sum(int(r["clipped"].sum()) for r in cand_rows))})
            frame_rows = pd.concat(cand_rows, ignore_index=True)
            for k, value in base.items():
                frame_rows[k] = value
            preds.append(frame_rows)
    return pd.DataFrame(rows), (pd.concat(preds, ignore_index=True) if preds else pd.DataFrame())


def _bundle_ids(cfg) -> List[str]:
    return [c["id"] for c in _STATE["bundles"]["candidates"]]


def select_candidate(scores: pd.DataFrame, tolerance: float, auc_defined: bool) -> Tuple[Optional[pd.Series], pd.DataFrame]:
    """Strict minimum RMSE; AUC only inside the numerical tie set, then fixed order."""
    ok = scores.loc[scores["status"] == "ok"].copy()
    if ok.empty:
        return None, ok
    best = ok["rmse"].min()
    tie = ok.loc[ok["rmse"] <= best + tolerance].copy()
    keys, ascending = [], []
    if auc_defined and len(tie) > 1 and tie["auc"].notna().all():
        keys.append("auc"), ascending.append(False)
    keys += ["method_order", "bundle_order", "formulation_order"]
    ascending += [True, True, True]
    tie = tie.sort_values(keys, ascending=ascending, kind="mergesort")
    return tie.iloc[0], tie


# --------------------------------------------------------------------------
# Final fits (executed in workers)
# --------------------------------------------------------------------------


def final_task(task: Mapping[str, object]) -> Dict[str, object]:
    """Fit the fixed recipe on the outer pool, refit its mapping(s), predict the job rows."""
    h, arm, formulation, bundle_id, method = task["horizon"], task["arm"], task["formulation"], task["bundle"], task["method"]
    frame = _STATE["frames"][h]
    cfg = _STATE["cfg"]
    window, origin = task["window"], int(task["origin_ord"])
    fit_idx = _fit_rows(frame, window, origin)
    pred_idx = np.flatnonzero(((frame["target_year"] == task["test_year"]) & frame["valid_score"] & (frame["origin_ord"] == origin)).to_numpy())
    months = frame["target_ord"].to_numpy(dtype=np.int64)
    out = {k: task[k] for k in ("job_id", "view", "horizon", "test_year", "arm", "formulation", "bundle", "method")}
    weights = md.decay_weights(months[fit_idx], origin)
    X = _STATE["X"][(h, arm)]
    others, models = {}, {}
    for target in OTHER_TARGETS:
        y = frame[target].to_numpy(dtype=np.float64)[fit_idx]
        models[target] = md.fit_regressor(X[fit_idx], y, weights, _params(bundle_id, target), target)
        others[target] = models[target].predict(X[pred_idx])
    direct_model, direct_info = fit_q3(h, arm, "direct", bundle_id, fit_idx, origin)
    models["q3_direct"] = direct_model
    raw = predict_q3(h, arm, "direct", direct_model, pred_idx)
    branch = np.full(pred_idx.size, "direct", dtype=object)
    fit_info = {"direct": direct_info}
    if formulation == "residual":
        res_model, res_info = fit_q3(h, arm, "residual", bundle_id, fit_idx, origin)
        fit_info["residual"] = res_info
        if res_model is None:
            out.update(status="unsupported", reason=res_info["reason"])
            return out
        models["q3_residual_delta"] = res_model
        res = predict_q3(h, arm, "residual", res_model, pred_idx)
        branch = np.where(np.isfinite(res), "residual", "fallback_direct").astype(object)
        raw = np.where(np.isfinite(res), res, raw)
    # Mappings were refitted in the parent on this recipe's OOF predictions.
    mappings: Mapping[str, Q3Mapping] = task["mappings"]
    mapped, why = apply_branches(raw, branch, mappings)
    b, supported = baseline(frame, cfg)
    pred = pd.DataFrame(
        {
            "row": pred_idx,
            "area_id": frame["area_id"].to_numpy()[pred_idx],
            "target_ord": months[pred_idx],
            "origin_ord": frame["origin_ord"].to_numpy()[pred_idx],
            "q2_raw": others["q2"],
            "q3_raw": raw,
            "q4_raw": others["q4"],
            "q5_raw": others["q5"],
            "branch": branch,
            "baseline_q3": np.where(branch == "residual", b[pred_idx], np.nan),
            "baseline_source_ord": np.where(branch == "residual", frame[cfg["residual_baseline_source_column"]].to_numpy()[pred_idx], -1),
        }
    )
    if mapped is None:
        pred["q3_mapped"], pred["q3_final"], pred["clipped"] = np.nan, np.nan, False
        out["calibration_status"], out["calibration_reason"] = "unavailable", why
    else:
        final, clipped = bound_share(mapped)
        pred["q3_mapped"], pred["q3_final"], pred["clipped"] = mapped, final, clipped
        out["calibration_status"], out["calibration_reason"] = "ok", None
    raw_bounded, _ = bound_share(raw)
    pred["q3_raw_bounded"] = raw_bounded
    out["predictions"] = pred
    out["mappings"] = [{"job_id": task["job_id"], "view": task["view"], "branch": name, **m.describe()} for name, m in mappings.items()]
    out["fit_ledger"] = pd.DataFrame({"row": fit_idx, "target_ord": months[fit_idx], "weight": weights, "baseline_supported": supported[fit_idx]})
    out["fit_info"] = fit_info
    out["models"] = models
    out["pred_idx"] = pred_idx
    out["status"], out["reason"] = "completed", None
    return out
