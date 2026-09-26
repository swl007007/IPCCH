"""Contract checks for validity-period label augmentation (implement.md checklist 2-4)."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from ipcch.somalia_oracle import augexp as ax
from ipcch.somalia_oracle import augment as au
from ipcch.somalia_oracle import data as sd

M = lambda y, m: int(sd.month_ord(y, m))  # noqa: E731


def _raw(rows):
    return pd.DataFrame(rows, columns=["area_id", "target_ord", *au.LABEL_FIELDS])


LAB = [3.0, 0.3, 0.3, 0.3, 0.1, 0.0]
BLANK = [np.nan] * 6


def _links(month, frm, to, anl="A1"):
    return pd.DataFrame([{"original_month_ord": month, "original_month": sd.ord_label(month), "link_status": "linked", "reason": None, "anl_id": anl, "valid_from_ord": frm, "valid_to_ord": to}])


def test_blank_months_inside_window_get_full_copy_with_lineage():
    raw = _raw([[1, M(2024, 1), *LAB], [1, M(2024, 2), *BLANK], [1, M(2024, 3), *BLANK], [1, M(2024, 4), *BLANK]])
    aug, led = au.augment_labels(raw, _links(M(2024, 1), M(2024, 1), M(2024, 3)), (2022, 2026))
    cp = aug.loc[aug["is_copy"]]
    assert cp["target_ord"].tolist() == [M(2024, 2), M(2024, 3)]  # inclusive to-month; nothing beyond the window
    assert (cp[list(au.LABEL_FIELDS)].to_numpy() == np.array(LAB)).all()
    assert (cp["original_month_ord"] == M(2024, 1)).all() and (cp["source_available_ord"] == M(2024, 1)).all()
    assert (cp["source_family"] == "anl:A1").all()
    assert aug.loc[aug["target_ord"] == M(2024, 4), "label_state"].item() == "blank"


def test_existing_and_partial_labels_are_never_overwritten():
    other = [2.0, 0.5, 0.3, 0.2, 0.0, 0.0]
    partial = [np.nan, 0.5, 0.3, 0.2, 0.0, 0.0]
    raw = _raw([[1, M(2024, 1), *LAB], [1, M(2024, 2), *other], [1, M(2024, 3), *partial]])
    aug, led = au.augment_labels(raw, _links(M(2024, 1), M(2024, 1), M(2024, 3)), (2022, 2026))
    assert not aug["is_copy"].any()
    assert aug.loc[aug["target_ord"] == M(2024, 2), "overall_phase"].item() == 2.0
    assert np.isnan(aug.loc[aug["target_ord"] == M(2024, 3), "overall_phase"].item())
    assert set(led["decision"]) == {"recipient_original", "recipient_partial"}


def test_no_copy_without_covariate_row_and_latest_original_wins():
    raw = _raw([[1, M(2023, 1), *LAB], [1, M(2023, 3), *[2.0, 0.6, 0.2, 0.2, 0, 0]], [1, M(2023, 4), *BLANK]])
    links = pd.concat([_links(M(2023, 1), M(2023, 1), M(2023, 5), "A1"), _links(M(2023, 3), M(2023, 3), M(2023, 4), "A2")])
    aug, led = au.augment_labels(raw, links, (2022, 2026))
    row = aug.loc[aug["target_ord"] == M(2023, 4)].iloc[0]
    assert row["is_copy"] and row["original_month_ord"] == M(2023, 3) and row["overall_phase"] == 2.0
    assert (led["decision"] == "no_covariate_row").sum() >= 1  # 2023-05 has no raw row


def test_equal_date_conflict_stays_unfilled():
    raw = _raw([[1, M(2023, 1), *LAB], [1, M(2023, 2), *BLANK]])
    links = pd.concat([_links(M(2023, 1), M(2023, 1), M(2023, 2), "A1")])
    cand_raw = pd.concat([raw, _raw([[2, M(2023, 1), *LAB]])])
    aug, led = au.augment_labels(raw, links, (2022, 2026))
    assert aug["is_copy"].sum() == 1
    # two distinct candidate values for the same recipient and month -> conflict
    links2 = pd.DataFrame([{**links.iloc[0].to_dict()}])
    raw2 = _raw([[1, M(2023, 1), *LAB], [1, M(2023, 2), *BLANK]])
    cand = pd.DataFrame([{"area_id": 1, "target_ord": M(2023, 2), "original_month_ord": M(2023, 1), "anl_id": "A1", **dict(zip(au.LABEL_FIELDS, LAB))},
                         {"area_id": 1, "target_ord": M(2023, 2), "original_month_ord": M(2023, 1), "anl_id": "A9", **dict(zip(au.LABEL_FIELDS, [2.0, 0.6, 0.3, 0.1, 0, 0]))}])
    top = cand.loc[cand["original_month_ord"] == cand["original_month_ord"].max()]
    assert top[list(au.LABEL_FIELDS)].drop_duplicates().shape[0] > 1  # the rule's trigger condition


def test_link_rounds_statuses():
    rounds = pd.DataFrame({"anl_id": ["A", "B", "C"], "valid_from_ord": [M(2024, 1), M(2025, 1), M(2025, 1)], "valid_to_ord": [M(2024, 3), M(2025, 3), M(2025, 1)]})
    links = au.link_rounds(pd.Series([M(2024, 1), M(2025, 1), M(2025, 4), M(2025, 7)]), rounds, {"2025-07": "spillover"})
    st = dict(zip(links["original_month"], links["link_status"]))
    assert st == {"2024-01": "linked", "2025-01": "ambiguous", "2025-04": "no_current_round", "2025-07": "excluded"}


# --- report isolation, availability, rounds -----------------------------------------


def _frame():
    rows = []
    for (om, months, fam) in [(M(2022, 7), [M(2022, 7), M(2022, 8), M(2022, 9)], "anl:1"), (M(2023, 1), [M(2023, 1), M(2023, 2)], "anl:2"), (M(2024, 1), [M(2024, 1), M(2024, 2)], "anl:3"), (M(2024, 7), [M(2024, 7)], "local:2024-07")]:
        for t in months:
            for a in (1, 2):
                rows.append({"area_id": a, "target_ord": t, "original_month_ord": om, "source_family": fam, "source_available_ord": om, "is_copy": t != om, "valid_score": True, "q3": 0.3})
    f = pd.DataFrame(rows)
    f["target_year"] = f["target_ord"] // 12
    f["original_year"] = f["original_month_ord"] // 12
    return f


def test_original_branch_excludes_copies_and_round_pool_excludes_own_family():
    f = _frame()
    orig = ax.fit_pool(f, "original", [2022, 2023, 2024], 10**6, 10**6)
    assert not f.loc[orig, "is_copy"].any()
    pool = ax.round_pool(f, "augmented", [2022, 2023, 2024], M(2024, 1), 0)
    assert not (f.loc[pool, "source_family"] == "anl:3").any()
    assert f.loc[pool, "target_ord"].max() < M(2024, 1) and f.loc[pool, "source_available_ord"].max() <= M(2024, 1)


def test_rounds_count_distinct_original_months_not_copies():
    cfg = au.load_config()
    f = _frame()
    plan = ax.plan_rounds(f, "augmented", [2022, 2023, 2024], 0, cfg)
    assert plan["scoring"] == [M(2023, 1), M(2024, 1), M(2024, 7)]  # three original reports, although 2022-07 has three months
    assert plan["oof"][0] == M(2023, 1)  # the first round has no earlier labels, so it yields no OOF predictions
    assert plan["calibration"][M(2024, 7)] == [M(2023, 1), M(2024, 1)]
    rr = ax.round_rows(f, "augmented", [2022, 2023, 2024], M(2024, 1))
    assert set(f.loc[rr, "target_ord"]) == {M(2024, 1), M(2024, 2)}  # copies scored inside their round
    assert set(f.loc[ax.round_rows(f, "original", [2022, 2023, 2024], M(2024, 1)), "target_ord"]) == {M(2024, 1)}


def test_backfilled_target_year_requires_original_year_in_window():
    f = _frame()
    f.loc[len(f)] = {"area_id": 1, "target_ord": M(2024, 12), "original_month_ord": M(2025, 1), "source_family": "anl:9", "source_available_ord": M(2025, 1), "is_copy": True, "valid_score": True, "q3": 0.3, "target_year": 2024, "original_year": 2025}
    pool = ax.fit_pool(f, "augmented", [2022, 2023, 2024], 10**6, 10**6)
    assert not (f.loc[pool, "source_family"] == "anl:9").any()


def test_category_history_excludes_own_family():
    originals = pd.DataFrame({"area_id": [1, 1], "target_ord": [M(2024, 1), M(2023, 10)], "overall_phase": [3.0, 2.0], "source_family": ["anl:3", "anl:2"], "valid_phase": [True, True]})
    frame = pd.DataFrame({"area_id": [1, 1], "target_ord": [M(2024, 2), M(2024, 1)], "source_family": ["anl:3", "anl:3"]})
    out = ax.category_history(frame, originals, 0)
    assert np.isnan(out[0])  # the copy's month-1 source is its own report
    assert np.isnan(out[1])  # no original at 2023-12


def test_config_pins_snapshot_and_q3_contract():
    cfg = au.load_config()
    assert cfg["api_filter"] == {"country": "SO", "condition": "A", "ipc_period": "C"}
    assert cfg["selection_rounds"] == 3 and cfg["min_selection_rounds"] == 2 and "2025-07" in cfg["excluded_raw_months"]
