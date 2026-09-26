"""Validity-period label augmentation (task somalia-validity-label-augmentation).

A raw Somalia label month is linked to the unique current IPC analysis whose
validity starts in that month (grill G3, PRD R16). Blank area-months inside that
analysis window receive a full copy of the area's original six-field label.
Copies keep the original's values, source family and availability date.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Mapping, Tuple

import numpy as np
import pandas as pd

from ipcch import paths
from ipcch.somalia_oracle import PERCENT_COLUMNS
from ipcch.somalia_oracle import data as sd

CONFIG_PATH = paths.CONFIG_DIR / "somalia_validity_augmentation.json"
LABEL_FIELDS = ("overall_phase", *PERCENT_COLUMNS)


class AugmentError(RuntimeError):
    """An augmentation contract invariant does not hold."""


def load_config(path: Path = CONFIG_PATH) -> Dict[str, object]:
    cfg = json.loads(Path(path).read_text(encoding="utf-8"))
    for key, rel in (("q3_config", "q3_config_sha256"),):
        p = Path(cfg[key])
        p = p if p.is_absolute() else paths.PROJECT_ROOT / p
        if sd.sha256_file(p) != cfg[rel]:
            raise AugmentError(f"{p} does not match its pinned sha256")
    return cfg


def load_rounds(snapshot: Path, expected_sha: str | None, api_filter: Mapping[str, str]) -> pd.DataFrame:
    """One row per current analysis: anl_id, validity window as month ordinals, feature count."""
    if expected_sha is not None and sd.sha256_file(snapshot) != expected_sha:
        raise AugmentError("validity snapshot does not match its pinned sha256")
    data = json.loads(Path(snapshot).read_text(encoding="utf-8"))
    rows = []
    for feature in data["features"]:
        p = feature["properties"]
        if all(str(p.get(k)) == v for k, v in api_filter.items()):
            rows.append({"anl_id": str(p["anl_id"]), "from": p["from"], "to": p["to"]})
    frame = pd.DataFrame(rows)
    if frame.empty:
        raise AugmentError("no current-period analyses in the validity snapshot for the filter")
    counts = frame.groupby("anl_id").size().rename("n_features")
    windows = frame.drop_duplicates()
    if windows["anl_id"].duplicated().any():
        raise AugmentError("an analysis has more than one validity window")
    f = pd.to_datetime(windows["from"], format="%b %Y")
    t = pd.to_datetime(windows["to"], format="%b %Y")
    windows = windows.assign(valid_from_ord=sd.month_ord(f.dt.year, f.dt.month), valid_to_ord=sd.month_ord(t.dt.year, t.dt.month))
    return windows.join(counts, on="anl_id").sort_values("valid_from_ord").reset_index(drop=True)


def link_rounds(raw_months: pd.Series, rounds: pd.DataFrame, excluded: Mapping[str, str]) -> pd.DataFrame:
    """Round-level link: raw label month -> unique current analysis starting that month."""
    out = []
    for m in sorted(set(int(x) for x in raw_months)):
        label = sd.ord_label(m)
        starting = rounds.loc[rounds["valid_from_ord"] == m]
        if label in excluded:
            status, reason = "excluded", excluded[label]
        elif starting.empty:
            status, reason = "no_current_round", "no current analysis starts in this month"
        elif len(starting) > 1:
            status, reason = "ambiguous", "multiple current analyses start in this month"
        else:
            status, reason = "linked", None
        row = {"original_month_ord": m, "original_month": label, "link_status": status, "reason": reason, "anl_id": None, "valid_from_ord": np.nan, "valid_to_ord": np.nan}
        if status == "linked":
            r = starting.iloc[0]
            row.update(anl_id=r["anl_id"], valid_from_ord=int(r["valid_from_ord"]), valid_to_ord=int(r["valid_to_ord"]))
        out.append(row)
    return pd.DataFrame(out)


def augment_labels(raw: pd.DataFrame, links: pd.DataFrame, year_range: Tuple[int, int]) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Return (augmented raw-label frame, decision ledger).

    ``raw``: one row per (area_id, target_ord) of the raw panel with the six label fields.
    Recipients must have all six fields missing; originals are never modified.
    """
    raw = raw.copy()
    if raw.duplicated(["area_id", "target_ord"]).any():
        raise AugmentError("raw panel has duplicate area/month keys")
    present = raw[list(LABEL_FIELDS)].notna()
    full = present.all(axis=1)
    empty = ~present.any(axis=1)
    raw["label_state"] = np.where(full, "original", np.where(empty, "blank", "partial"))
    raw["is_copy"] = False
    raw["original_month_ord"] = np.where(full, raw["target_ord"], -1)
    link_by_month = links.set_index("original_month_ord")
    fam = raw["original_month_ord"].map(lambda m: link_by_month["anl_id"].get(m) if m in link_by_month.index else None)
    raw["source_family"] = np.where(full, np.where(fam.notna(), "anl:" + fam.astype(str), "local:" + raw["target_ord"].map(sd.ord_label)), None)
    lo, hi = sd.month_ord(year_range[0], 1).item(), sd.month_ord(year_range[1], 12).item()
    keys = raw.set_index(["area_id", "target_ord"])
    candidates = []
    linked = links.loc[links["link_status"] == "linked"]
    # An augmentable source must pass the existing target/phase QC (valid reported phase,
    # finite nonnegative shares with a positive sum); other complete blocks are not copied.
    vals = raw[list(PERCENT_COLUMNS)].to_numpy(dtype=float)
    qc_ok = full & raw["overall_phase"].isin([1, 2, 3, 4, 5]).to_numpy() & np.isfinite(vals).all(axis=1) & (vals >= 0).all(axis=1) & (np.nan_to_num(vals).sum(axis=1) > 0)
    raw["source_qc_ok"] = qc_ok
    originals = raw.loc[qc_ok]
    for link in linked.itertuples(index=False):
        src = originals.loc[originals["target_ord"] == link.original_month_ord]
        months = [m for m in range(int(link.valid_from_ord), int(link.valid_to_ord) + 1) if m != link.original_month_ord and lo <= m <= hi]
        for m in months:
            for rec in src.itertuples(index=False):
                candidates.append({"area_id": rec.area_id, "target_ord": m, "original_month_ord": int(link.original_month_ord), "anl_id": link.anl_id, **{f: getattr(rec, f) for f in LABEL_FIELDS}})
    cand = pd.DataFrame(candidates)
    decisions: List[Dict[str, object]] = []
    invalid_src = raw.loc[full & ~qc_ok]
    for link in linked.itertuples(index=False):
        bad = invalid_src.loc[invalid_src["target_ord"] == link.original_month_ord]
        for rec in bad.itertuples(index=False):
            for m in range(int(link.valid_from_ord), int(link.valid_to_ord) + 1):
                if m != link.original_month_ord and lo <= m <= hi:
                    decisions.append({"area_id": rec.area_id, "target_ord": m, "n_candidates": 1, "candidates": f"{sd.ord_label(link.original_month_ord)}:{link.anl_id}", "decision": "source_invalid", "winner_month_ord": -1})
    if cand.empty:
        raw["source_available_ord"] = np.where(raw["original_month_ord"] >= 0, raw["original_month_ord"], -1)
        return raw, pd.DataFrame(decisions, columns=["area_id", "target_ord", "n_candidates", "candidates", "decision", "winner_month_ord"])
    for (area, m), g in cand.groupby(["area_id", "target_ord"], sort=True):
        base = {"area_id": area, "target_ord": m, "n_candidates": len(g), "candidates": ";".join(f"{sd.ord_label(o)}:{a}" for o, a in zip(g["original_month_ord"], g["anl_id"]))}
        if (area, m) not in keys.index:
            decisions.append({**base, "decision": "no_covariate_row", "winner_month_ord": -1})
            continue
        state = keys.loc[(area, m), "label_state"]
        if state != "blank":
            decisions.append({**base, "decision": f"recipient_{state}", "winner_month_ord": -1})
            continue
        latest = g["original_month_ord"].max()
        top = g.loc[g["original_month_ord"] == latest]
        if len(top) > 1 and top[list(LABEL_FIELDS)].drop_duplicates().shape[0] > 1:
            decisions.append({**base, "decision": "conflict_equal_date", "winner_month_ord": -1})
            continue
        decisions.append({**base, "decision": "filled", "winner_month_ord": int(latest), "winner_anl_id": top.iloc[0]["anl_id"]})
    ledger = pd.DataFrame(decisions)
    filled = ledger.loc[ledger["decision"] == "filled"]
    if len(filled):
        win = cand.merge(filled[["area_id", "target_ord", "winner_month_ord"]], left_on=["area_id", "target_ord", "original_month_ord"], right_on=["area_id", "target_ord", "winner_month_ord"])
        win = win.drop_duplicates(["area_id", "target_ord"]).set_index(["area_id", "target_ord"])
        idx = raw.set_index(["area_id", "target_ord"]).index
        hit = idx.isin(win.index)
        w = win.reindex(idx[hit])
        for f in LABEL_FIELDS:
            raw.loc[hit, f] = w[f].to_numpy()
        raw.loc[hit, "is_copy"] = True
        raw.loc[hit, "label_state"] = "copy"
        raw.loc[hit, "original_month_ord"] = w["original_month_ord"].to_numpy()
        raw.loc[hit, "source_family"] = "anl:" + w["anl_id"].astype(str).to_numpy()
    raw["source_available_ord"] = np.where(raw["original_month_ord"] >= 0, raw["original_month_ord"], -1)
    return raw, ledger
