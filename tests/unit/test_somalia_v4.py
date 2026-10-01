"""Contract checks for Somalia v4 calibrated D (implement.md section 5)."""
from __future__ import annotations

import io

import numpy as np
import pandas as pd
import pytest

from ipcch.somalia_oracle import augexp as ax
from ipcch.somalia_oracle import data as sd
from ipcch.somalia_oracle import modeling as md
from ipcch.somalia_oracle import q3opt as qo

M = lambda y, m: int(sd.month_ord(y, m))  # noqa: E731
CFG = {"selection_rounds": 3, "min_selection_rounds": 2, "calibration_rounds": 3, "min_calibration_rounds": 2}
BUNDLES = {"candidates": [{"id": f"X{i}"} for i in range(1, 7)]}


def _frame(rows):
    """rows: (area, target, original_month, is_copy, family) with q3/crisis filled deterministically."""
    f = pd.DataFrame(rows, columns=["area_id", "target_ord", "original_month_ord", "is_copy", "source_family"])
    f["source_available_ord"] = f["original_month_ord"]
    f["target_year"] = f["target_ord"] // 12
    f["original_year"] = f["original_month_ord"] // 12
    f["valid_score"] = True
    rng = np.random.default_rng(0)
    f["q3"] = rng.uniform(0, 0.6, len(f))
    f["actual_crisis"] = (f["q3"] >= 0.2).astype(float)
    f["hist_q3_obs1"] = np.nan
    f["history_obs1_source_ord"] = -1
    f["history_cutoff_ord"] = f["target_ord"] - 1
    f["oracle_all_verified"] = True
    return f


def _with_baseline(f, rows_without=()):
    f = f.copy()
    f["hist_q3_obs1"] = 0.3
    f["history_obs1_source_ord"] = f["target_ord"] - 6
    f.loc[list(rows_without), ["hist_q3_obs1"]] = np.nan
    f.loc[list(rows_without), ["history_obs1_source_ord"]] = -1
    return f


def _panel():
    """Two areas; semiannual originals 2019-2021 (Jan/Jul), a Jul-Sep 2020 validity window
    with copies, and an outer-year 2022 report with a copy."""
    rows = []
    for y in (2019, 2020, 2021, 2022):
        for m in (1, 7):
            for a in (1, 2):
                rows.append((a, M(y, m), M(y, m), False, f"local:{y}-{m:02d}" if (y, m) != (2020, 7) else "anl:77"))
    rows += [(a, M(2020, k), M(2020, 7), True, "anl:77") for a in (1, 2) for k in (8, 9)]
    rows += [(1, M(2022, 8), M(2022, 7), True, "local:2022-07")]
    return _frame(rows)


# ---------------- decay and search inventory ----------------


def test_no_decay_is_exactly_one_and_future_labels_are_rejected():
    w = md.decay_weights(np.array([100, 50, 1]), 100, None)
    assert w.dtype == np.float64 and (w == 1.0).all()
    assert md.decay_weights(np.array([100, 88]), 100, 12).tolist() == [1.0, 0.5]
    with pytest.raises(md.ModelingError):
        md.decay_weights(np.array([101]), 100, None)


def test_declared_inventory_is_144_unique_recipes_with_decay_tie_order():
    cands = ax.v4_candidates(BUNDLES)
    keys = {(c["bundle"], c["half_life"], c["formulation"], c["method"]) for c in cands}
    assert len(cands) == 144 and len(keys) == 144
    assert {c["half_life"] for c in cands} == {"12", "24", "48", "none"}
    order = sorted({(c["half_life"], c["decay_order"]) for c in cands}, key=lambda x: x[1])
    assert [o[0] for o in order] == ["none", "48", "24", "12"]


def test_selection_is_strict_rmse_then_auc_then_fixed_order_including_decay():
    base = {"status": "ok", "method_order": 0, "bundle_order": 0, "formulation_order": 0}
    s = pd.DataFrame([{**base, "rmse": 0.1, "auc": 0.9, "decay_order": 3, "id": "a"}, {**base, "rmse": 0.1, "auc": 0.9, "decay_order": 0, "id": "b"},
                      {**base, "rmse": 0.1 + 1e-9, "auc": 0.99, "decay_order": 0, "id": "c"}])
    best, tie = qo.select_candidate(s, 1e-12, True, extra_order=["decay_order"])
    assert best["id"] == "b" and len(tie) == 2  # 1e-9 worse RMSE is not in the tie set despite higher AUC
    legacy, _ = qo.select_candidate(s.drop(columns="decay_order"), 1e-12, True)
    assert legacy["id"] == "a"  # legacy callers keep their original order


# ---------------- pools, origins and report isolation ----------------


def test_original_pool_has_no_copies_and_augmented_admits_them():
    f = _panel()
    po, pa = ax.PoolIndex(f, "original", 0), ax.PoolIndex(f, "augmented", 0)
    so, sa = po.normalize(M(2021, 12), M(2021, 12), None, ()), pa.normalize(M(2021, 12), M(2021, 12), None, ())
    assert not f["is_copy"].to_numpy()[po.rows(so)].any()
    assert f["is_copy"].to_numpy()[pa.rows(sa)].sum() == 4


def test_pool_respects_cutoffs_and_normalizes_ineffective_constraints():
    f = _panel()
    p = ax.PoolIndex(f, "augmented", 0)
    s = p.normalize(M(2020, 8), M(2020, 8), 2021, ("anl:77", "local:2022-01"))
    rows = p.rows(s)
    assert f["target_ord"].to_numpy()[rows].max() <= M(2020, 8) and not f["source_family"].to_numpy()[rows].tolist().count("anl:77")
    assert s.max_year is None and s.excluded == ("anl:77",)  # 2022 family absent from the pool; fold bound implied by the cutoff
    s2 = p.normalize(M(2020, 8), M(2020, 8), None, ("anl:77",))
    assert s2 == s and s2.id == s.id
    # outer H0 pool of fold 2022: labels <= origin but the fold bound (<= 2021) must hold
    outer = p.normalize(M(2022, 8), M(2022, 8), 2021, ())
    assert (f["target_year"].to_numpy()[p.rows(outer)] <= 2021).all() and outer.max_year == 2021


def test_copied_rows_use_their_own_origin_and_exclude_their_family():
    f = _panel()
    p = ax.PoolIndex(f, "augmented", 0)
    ctx = ax.v4_plan_context(f, p, "augmented", 2021, 0, M(2021, 1), [], CFG)
    mem = ctx.members.loc[ctx.members["round"] == M(2020, 7)]
    assert sorted(set(mem["target_ord"])) == [M(2020, 7), M(2020, 8), M(2020, 9)]
    for r in mem.itertuples(index=False):
        sp = ctx.specs[r.spec_id]
        assert sp.label_cutoff == r.target_ord - 1 and sp.available_by == r.target_ord  # own origin v-H, not the round's
        assert "anl:77" not in set(f["source_family"].to_numpy()[p.rows(sp)])
    # a later copy month's pool may use more history than the round month itself but never its own report
    s7 = ctx.specs[mem.loc[mem["target_ord"] == M(2020, 7), "spec_id"].iloc[0]]
    s9 = ctx.specs[mem.loc[mem["target_ord"] == M(2020, 9), "spec_id"].iloc[0]]
    assert s9.label_cutoff > s7.label_cutoff


def test_calibration_rows_precede_the_scoring_target_and_purge_the_scoring_family():
    f = _panel()
    p = ax.PoolIndex(f, "augmented", 0)
    ctx = ax.v4_plan_context(f, p, "augmented", 2022, 0, M(2022, 1), [], CFG)
    assert ctx.status == "ok" and ctx.scoring == [M(2020, 7), M(2021, 1), M(2021, 7)]
    for (r, v), g in ctx.calibration.groupby(["scoring_round", "scoring_target_ord"]):
        assert (g["target_ord"] < v).all() and (g["round"] < r).all()
        assert g["round"].nunique() <= 3
        fam_r = f.loc[f["original_month_ord"] == r, "source_family"].iloc[0]
        for sid in g["spec_id"].unique():
            assert fam_r not in set(f["source_family"].to_numpy()[p.rows(ctx.specs[sid])])


def test_long_horizon_selection_never_uses_labels_after_the_outer_origin():
    f = _panel()
    p = ax.PoolIndex(f, "original", 12)
    origin = M(2021, 1)  # target 2022-01 at H12
    ctx = ax.v4_plan_context(f, p, "original", 2022, 12, origin, [], CFG)
    assert ctx.members["target_ord"].max() <= origin
    for sid in set(ctx.members["spec_id"]) | set(ctx.calibration["spec_id"]):
        sp = ctx.specs[sid]
        assert sp.available_by <= origin and sp.label_cutoff <= origin
    assert ctx.fit_spec.label_cutoff == origin and ctx.fit_spec.available_by == origin


def test_outer_test_family_is_purged_from_every_dependency():
    f = _panel()
    p = ax.PoolIndex(f, "augmented", 0)
    ctx = ax.v4_plan_context(f, p, "augmented", 2021, 0, M(2021, 1), ["anl:77"], CFG)
    for sid, sp in ctx.specs.items():
        assert "anl:77" not in set(f["source_family"].to_numpy()[p.rows(sp)])
    assert M(2020, 7) not in ctx.rounds


def test_context_with_fewer_than_two_rounds_is_unsupported_not_shrunk():
    f = _panel()
    p = ax.PoolIndex(f, "original", 0)
    ctx = ax.v4_plan_context(f, p, "original", 2019, 0, M(2019, 7), [], CFG)
    assert ctx.status == "unsupported"


# ---------------- candidate scoring ----------------


def _store_for(ctx, f, residual_ok=True, drop_row=None, residual_unsupported_specs=()):
    store = ax.V4UnitStore()
    need = pd.concat([ctx.members[["row", "spec_id"]], ctx.calibration[["row", "spec_id"]], ctx.final_calibration[["row", "spec_id"]]])
    for sid, g in need.groupby("spec_id"):
        rows = np.array(sorted(set(g["row"])))
        for b in [c["id"] for c in BUNDLES["candidates"]]:
            for hl in ax.V4_HALF_LIVES:
                for form in ax.FORMULATIONS:
                    raw = f["q3"].to_numpy()[rows] + (0.01 if form == "direct" else 0.02)
                    if form == "residual":
                        _, base = ax._baseline(f)
                        raw = np.where(base[rows], raw, np.nan)  # residual predictions exist only where a baseline exists
                    if drop_row is not None and form == "direct" and b == "X1":
                        raw = np.where(rows == drop_row, np.nan, raw)
                    status = "ok" if (form == "direct" or (residual_ok and sid not in residual_unsupported_specs)) else "unsupported"
                    store.add({"key": ax.v4_unit_key(sid, form, b, hl), "status": status, "pred_idx": rows, "raw_q3": raw, "n_fit": 1, "n_fit_used": 1, "fit_max_target_ord": 0, "model_kind": "x", "sum_weight": 1.0, "min_weight": 1.0})
    return store


def test_residual_rows_without_baseline_fall_back_and_unsupported_residual_fails_the_candidate():
    f = _panel()
    f = _with_baseline(f, rows_without=[i for i in range(len(f)) if i % 2 == 1])
    p = ax.PoolIndex(f, "original", 0)
    ctx = ax.v4_plan_context(f, p, "original", 2022, 0, M(2022, 1), [], CFG)
    scores, preds = ax.v4_score_context(_store_for(ctx, f), f, ctx, BUNDLES, CFG)
    assert len(scores) == 144 and (scores["status"] == "ok").all()
    labs = set(preds[("X1", "24", "residual", "none")]["prediction_branch"])
    assert labs == {"residual", "fallback_direct"}
    scores2, _ = ax.v4_score_context(_store_for(ctx, f, residual_ok=False), f, ctx, BUNDLES, CFG)
    assert (scores2.loc[scores2["formulation"] == "residual", "status"] == "unsupported").all()
    assert (scores2.loc[scores2["formulation"] == "direct", "status"] == "ok").all()


def test_candidate_missing_one_scoring_key_is_unsupported_not_rescored_on_fewer_rows():
    f = _with_baseline(_panel(), rows_without=[i for i in range(len(_panel())) if i % 2 == 1])
    p = ax.PoolIndex(f, "original", 0)
    ctx = ax.v4_plan_context(f, p, "original", 2022, 0, M(2022, 1), [], CFG)
    row = int(ctx.members["row"].iloc[0])
    scores, _ = ax.v4_score_context(_store_for(ctx, f, drop_row=row), f, ctx, BUNDLES, CFG)
    bad = scores.loc[(scores["bundle"] == "X1") & (scores["formulation"] == "direct")]
    assert (bad["status"] == "unsupported").all() and (bad["n"] == 0).all()
    # residual candidates need the direct model only on fallback (no-baseline) rows
    fallback_row = int(ctx.members.loc[ctx.members["row"] % 2 == 1, "row"].iloc[0])
    scores_fb, _ = ax.v4_score_context(_store_for(ctx, f, drop_row=fallback_row), f, ctx, BUNDLES, CFG)
    assert (scores_fb.loc[scores_fb["bundle"] == "X1", "status"] == "unsupported").all()
    good = scores.loc[scores["bundle"] != "X1"]
    assert (good["n"] == len(ctx.members)).all()


def test_isotonic_needs_two_distinct_scores_and_two_rounds():
    m = qo.fit_mapping("isotonic", np.array([0.3, 0.3]), np.array([0.1, 0.2]), np.array([1, 2]), 2)
    assert m.status == "unsupported"
    m = qo.fit_mapping("shift", np.array([0.3, 0.4]), np.array([0.1, 0.2]), np.array([1, 1]), 2)
    assert m.status == "unsupported"
    assert qo.fit_mapping("none", np.array([]), np.array([]), np.array([]), 2).ok


# ---------------- cohorts and evaluation ----------------


def _ledger(f):
    led = f[["area_id", "target_ord", "is_copy", "source_family", "original_month_ord"]].copy()
    led["valid_target"], led["valid_score"], led["target_invalid_reason"] = True, True, ""
    return led


def test_cohorts_are_frozen_per_setting_with_copies_only_in_augmented():
    f = _panel()
    frames = {0: f, 3: f.assign(oracle_all_verified=f["target_ord"] != M(2022, 7))}
    c = ax.v4_freeze_cohorts(_ledger(f), frames, ["original", "augmented"], [2022], [0, 3])
    orig = c.loc[(c["data_setting"] == "original") & (c["horizon"] == 0)]
    aug = c.loc[(c["data_setting"] == "augmented") & (c["horizon"] == 0)]
    assert not orig["is_copy"].any() and aug["is_copy"].sum() == 1 and len(aug) == len(orig) + 1
    h3 = c.loc[(c["horizon"] == 3) & (c["target_ord"] == M(2022, 7))]
    assert (h3["status"] == "excluded").all() and (h3["reason"] == "oracle_weather_unverified").all()


def _preds(c, f, setting, year, h, drop=0):
    prim = c.loc[(c["data_setting"] == setting) & (c["outer_year"] == year) & (c["horizon"] == h) & (c["status"] == "primary")]
    q = prim.merge(f[["area_id", "target_ord", "q3"]], on=["area_id", "target_ord"])
    p = q.assign(q3_raw=q["q3"] + 0.05, q3_final=np.clip(q["q3"] + 0.05, 0, 1), clipped=False, prediction_branch="direct", job_id="j", data_setting=setting, outer_year=year, horizon=h)
    return p.iloc[drop:]


def test_missing_final_prediction_makes_only_that_setting_incomplete_and_pools_rows():
    f = _panel()
    frames = {0: f}
    c = ax.v4_freeze_cohorts(_ledger(f), frames, ["original", "augmented"], [2021, 2022], [0])
    preds = pd.concat([_preds(c, f, "original", 2021, 0), _preds(c, f, "original", 2022, 0), _preds(c, f, "augmented", 2021, 0), _preds(c, f, "augmented", 2022, 0, drop=1)])
    annual, pooled = ax.v4_evaluate(c, preds, frames, ["original", "augmented"], [2021, 2022], [0])
    st = annual.set_index(["data_setting", "outer_year"])["status"].to_dict()
    assert st[("original", 2022)] == "complete" and st[("augmented", 2022)] == "incomplete" and st[("augmented", 2021)] == "complete"
    ps = pooled.set_index("data_setting")
    assert ps.loc["augmented", "status"] == "incomplete" and ps.loc["original", "status"] == "complete"
    o = annual.set_index(["data_setting", "outer_year"])
    assert ps.loc["original", "n"] == o.loc[("original", 2021), "n"] + o.loc[("original", 2022), "n"]
    # pooled R2 is recomputed from concatenated rows, not an average of annual R2
    both = preds.loc[preds["data_setting"] == "original"].merge(f[["area_id", "target_ord"]], on=["area_id", "target_ord"])
    t, pr = both["q3"].to_numpy(), both["q3_final"].to_numpy()
    assert ps.loc["original", "final_r2"] == pytest.approx(1 - ((t - pr) ** 2).sum() / ((t - t.mean()) ** 2).sum())


def test_duplicate_prediction_keys_are_rejected():
    f = _panel()
    c = ax.v4_freeze_cohorts(_ledger(f), {0: f}, ["original"], [2022], [0])
    p = _preds(c, f, "original", 2022, 0)
    with pytest.raises(ax.AugExpError):
        ax.v4_evaluate(c, pd.concat([p, p.iloc[:1]]), {0: f}, ["original"], [2022], [0])


def test_threshold_and_isotonic_ties_survive_csv_round_trip():
    vals = np.array([0.2, np.nextafter(0.2, 0), np.nextafter(0.2, 1), 0.1 + 0.2, 1 / 3])
    buf = io.StringIO()
    pd.DataFrame({"x": vals}).to_csv(buf, index=False)
    back = pd.read_csv(io.StringIO(buf.getvalue()), float_precision="round_trip")["x"].to_numpy()
    assert (back == vals).all() and ((back >= 0.2) == (vals >= 0.2)).all()
    m = ax.v4_slot_metrics(pd.DataFrame({"area_id": [1, 2], "target_ord": [1, 1], "source_family": ["a", "a"], "is_copy": [False, False], "q3": [0.3, 0.3], "actual_crisis": [1.0, 1.0],
                                         "q3_raw": [0.2, 0.4], "q3_final": [0.2, 0.4], "clipped": [False, False], "prediction_branch": ["direct", "direct"]}))
    assert np.isnan(m["final_r2"]) and m["final_r2_reason"] == "constant truth" and np.isnan(m["final_auc"]) and m["bin_tp"] == 2


def test_unsupported_residual_unit_on_a_baseline_calibration_key_makes_learned_residual_mappings_unavailable():
    f = _with_baseline(_panel())
    p = ax.PoolIndex(f, "original", 0)
    ctx = ax.v4_plan_context(f, p, "original", 2022, 0, M(2022, 1), [], CFG)
    cal_only = set(ctx.calibration["spec_id"]) - set(ctx.members["spec_id"])
    assert cal_only
    scores, _ = ax.v4_score_context(_store_for(ctx, f, residual_unsupported_specs=cal_only), f, ctx, BUNDLES, CFG)
    res = scores.loc[scores["formulation"] == "residual"]
    assert (res.loc[res["method"] != "none", "status"] == "unsupported").all()  # not refit on the remaining calibration rows
    assert (res.loc[res["method"] == "none", "status"] == "ok").all()
    assert (scores.loc[scores["formulation"] == "direct", "status"] == "ok").all()
    maps = ax.v4_fit_mappings(_store_for(ctx, f, residual_unsupported_specs=cal_only), f, ctx.calibration, "residual", "X1", 24, "shift", 2)
    assert maps["residual"].status == "unsupported" and maps["fallback_direct"].ok


def test_scoring_row_without_baseline_does_not_need_its_residual_unit():
    f0 = _panel()
    p0 = ax.PoolIndex(f0, "original", 0)
    ctx0 = ax.v4_plan_context(f0, p0, "original", 2022, 0, M(2022, 1), [], CFG)
    r0 = ctx0.scoring[0]
    rows_r0 = ctx0.members.loc[ctx0.members["round"] == r0, "row"].tolist()
    f = _with_baseline(f0, rows_without=rows_r0)
    p = ax.PoolIndex(f, "original", 0)
    ctx = ax.v4_plan_context(f, p, "original", 2022, 0, M(2022, 1), [], CFG)
    specs_r0 = set(ctx.members.loc[ctx.members["round"] == r0, "spec_id"])
    scores, preds = ax.v4_score_context(_store_for(ctx, f, residual_unsupported_specs=specs_r0), f, ctx, BUNDLES, CFG)
    ok = scores.loc[(scores["formulation"] == "residual") & (scores["method"] == "none")]
    assert (ok["status"] == "ok").all()
    pr = preds[("X1", "24", "residual", "none")]
    assert set(pr.loc[pr["round"] == r0, "prediction_branch"]) == {"fallback_direct"}
