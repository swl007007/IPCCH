"""Focused tests of the IPCCH Forecasting MLflow catalog vocabulary and extraction (no MLflow server).

Run: PYTHONPATH=IPCCHMLflow /home/swl007007/.venvs/ipcch-mlflow/bin/python -m pytest tests/unit/test_ipcch_mlflow_naming_extract.py -q
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import ipcch_mlflow_fixtures as F  # noqa: F401  (adds IPCCHMLflow to sys.path)
import extract as X
import naming as N
import plan as P
import store as S
from naming import SourceConflict


def plans_for(repo: Path, cfg: dict, tmp: Path, keys=None) -> dict:
    return P.build_plans(cfg, repo, tmp / "store", keys)


# ------------------------------------------------------------------ naming

def test_lead_and_names():
    assert N.lead_label(0) == "0-month" and N.lead_tag(0) == "00" and N.lead_tag(12) == "12"
    assert N.registered_model_name("compact_climate_global", "weather_oracle", 6) == \
        "IPCCH Forecasting Compact climate global historical | weather_oracle | 6-month"
    with pytest.raises(SourceConflict):
        N.logged_model_name("compact_climate_global", "baseline", 0, "snapshot v1.2")  # '.' not allowed


def test_unknown_vocabulary_refused():
    for f, x in ((N.arm, "E_persist"), (N.cohort, "region_atlantis_global_model"), (N.leaf, "f3_phase3plus"),
                 (N.family, "nigeria_sep18"), (N.period_role, "main")):
        with pytest.raises(SourceConflict):
            f(x)
    with pytest.raises(SourceConflict):
        N.launch_cohort("region", region=3, region_name="East Africa")  # region 3 is Southern Africa


def test_region_cohorts_follow_declared_mapping():
    assert N.region_cohort(3) == "region_southern_africa_global_model"
    assert N.cohort("region_somalia_global_model") == "region_somalia_global_model"
    assert "Southern Africa" in N.cohort_definition("region_southern_africa_global_model")


def test_metric_semantics():
    assert N.leaf("exact_phase_accuracy") == "five_class.accuracy"
    assert N.leaf("phase3plus_accuracy") == "binary.accuracy"
    assert N.leaf("accuracy") == "five_class.accuracy"  # v1 exact phase (evaluation.py:63-65)
    assert N.leaf("legacy_f1") != N.leaf("bin_f1")  # legacy phase-binary kept apart from q3-binary
    assert N.leaf("raw_r2") != N.leaf("final_r2")
    assert N.leaf("within_month_auc_months").endswith("n_months")


def test_truth_wording():
    q3 = N.family("somalia_q3_optimization")["truth"]
    assert "reported overall phase >= 3" in q3 and "prediction rule" in q3
    assert "crisis = q3 >= 0.20" not in q3
    launch = N.family("compact_launch_global")["truth"]
    assert "no attached scoring truth" in launch and "No actual labels" not in launch


# ------------------------------------------------------------------ builder semantics

def builder(tmp: Path) -> X.Builder:
    return X.Builder({"source_key": "s", "root": "r", "snapshot_label": "snap", "eval_group": "g"}, tmp, {}, {"plans": {}, "external": {}})


def kt(q3=(0.1, 0.2)):
    return pd.DataFrame({"area_id": [1, 2], "target_ord": [24300, 24300], "overall_phase": [2, 3], "q3": list(q3)})


def test_put_na_and_duplicates(tmp_path):
    b = builder(tmp_path)
    v = b.view("compact_climate_global", "compact_baseline", 6, "fitted")
    b.put(v, "primary.all_scored.binary.f2", None, "f.csv", 3, "f2", "f2", None, "zero f2 denominator", "unavailable")
    assert "primary.all_scored.binary.f2" not in v["metrics"]
    assert v["na"]["primary.all_scored.binary.f2"]["reason"] == "zero f2 denominator"
    b.put(v, "primary.all_scored.n_rows", 0, "f.csv", 1, "n", "n", "ds")  # finite zero support is kept
    assert v["metrics"]["primary.all_scored.n_rows"] == 0.0
    b.put(v, "primary.all_scored.n_rows", 0, "g.csv", 2, "n", "n", "ds")
    assert v["sources"]["primary.all_scored.n_rows"]["also"][0]["file"] == "g.csv"
    with pytest.raises(SourceConflict):
        b.put(v, "primary.all_scored.n_rows", 0, "h.csv", 1, "n", "n", "other dataset")
    with pytest.raises(SourceConflict):
        b.put(v, "primary.all_scored.n_rows", 1, "h.csv", 1, "n", "n", "ds")


def test_dataset_identity_role_independent_and_truth_bound(tmp_path):
    b = builder(tmp_path)
    a = b.eval_dataset(6, "primary", "all_scored", "g", kt(), ["overall_phase", "q3"], "t")
    o = b.eval_dataset(6, "original", "all_scored", "g", kt(), ["overall_phase", "q3"], "t")
    assert a == o and len(b.datasets) == 1  # same keys + truth under another reporting role = same dataset
    with pytest.raises(SourceConflict):
        b.eval_dataset(6, "primary", "all_scored", "g", kt(q3=(0.1, 0.25)), ["overall_phase", "q3"], "t")


def test_persistence_rule_matches_source_definition():
    ledger = pd.DataFrame({"area_id": [1, 1, 2, 3], "target_ord": [100, 104, 103, 90],
                           "actual_crisis": [np.nan, 1.0, 0.0, 1.0]})  # area 1 month 100 invalid phase
    keys = pd.DataFrame({"area_id": [1, 1, 2, 3], "target_ord": [104, 105, 103, 95], "origin_ord": [104, 105, 103, 89]})
    got = X.persistence_rule(ledger, keys)
    # area1 T104: only valid month 104 is not < T -> no; T105: 104 <= min(105, 104) -> yes;
    # area2 H0 own month excluded -> no; area3 origin 89 < first valid 90 -> no
    assert got.to_dict("records") == [{"area_id": 1, "target_ord": 105}]


# ------------------------------------------------------------------ fixture sources

def test_compact_original_extension_reuse_and_aliases(tmp_path):
    cfg = F.compact_config(tmp_path)
    plans = plans_for(tmp_path, cfg, tmp_path)
    o, e = plans["fx_orig"], plans["fx_ext"]
    assert o["counts"]["versions"] == 3 and e["counts"]["versions"] == 3
    ver = e["versions"]["compact_climate_global/weather_oracle/06@fx_ext"]
    assert (ver["boosters_new"], ver["boosters_reused"], ver["boosters_total"]) == (4, 8, 12)
    assert {m["bundle_source"] for m in ver["members"] if m["kind"] == "reused_from_snapshot"} == {"fx_orig"}
    assert "fit origin 2025-07, label cutoff 2025-07" in [v for v in e["views"] if v["view_key"].endswith("weather_oracle/06")][0]["description"]
    alias = [v for v in o["views"] if v["view_key"] == "compact_climate_global/weather_oracle/00"][0]
    assert alias["view_kind"] == "alias" and alias["alias_of"] == "compact_climate_global/baseline/00@fx_orig"
    assert not any(k.endswith("weather_oracle/00@fx_orig") for k in o["versions"])
    # pooled 2022-2023 of the original = 'original' period of the extension: one dataset, two roles
    v_o = [v for v in o["views"] if v["view_key"] == "compact_climate_global/baseline/06"][0]
    v_e = [v for v in e["views"] if v["view_key"] == "compact_climate_global/baseline/06"][0]
    assert v_o["metric_dataset"]["primary.all_scored.five_class.accuracy"] == v_e["metric_dataset"]["original.all_scored.five_class.accuracy"]
    tot = P.check_global(cfg, plans, full=False)
    assert tot["dashboard_rows"] == 4 and tot["registered_models"] == 3 and tot["model_versions"] == 6


def test_same_name_different_truth_across_sources_rejected(tmp_path):
    cfg = F.compact_config(tmp_path)
    p = tmp_path / "results/experiments/fx_compact_ext/runs/compact_baseline/6m/predictions/predictions_2022_2026.csv"
    df = pd.read_csv(p)
    df.loc[0, "phase3_worse"] = 0.999  # 2022 truth now differs from the original snapshot
    for arm, h, _ in F.RUNS:
        df.to_csv(tmp_path / f"results/experiments/fx_compact_ext/runs/{arm}/{h}m/predictions/predictions_2022_2026.csv", index=False)
    with pytest.raises(SourceConflict, match="two contents"):
        plans_for(tmp_path, cfg, tmp_path)


def test_missing_or_changed_booster_refused(tmp_path):
    cfg = F.compact_config(tmp_path)
    b = tmp_path / "results/experiments/fx_compact_v1/runs/compact_baseline/6m/batches/2022/model_phase3_worse.ubj"
    b.write_bytes(b"changed")
    with pytest.raises(SourceConflict, match="digest differs"):
        plans_for(tmp_path, cfg, tmp_path, ["fx_orig"])
    b.unlink()
    with pytest.raises(SourceConflict, match="missing"):
        plans_for(tmp_path, cfg, tmp_path, ["fx_orig"])


def test_mixed_excluded_content_refused(tmp_path):
    cfg = F.compact_config(tmp_path)
    F.write(tmp_path / "results/experiments/fx_compact_v1/report/mixed.md", "context: climate2015_v1 annual F2 0.71")
    with pytest.raises(SourceConflict, match="excluded-family content"):
        plans_for(tmp_path, cfg, tmp_path, ["fx_orig"])


def test_evaluation_only_revision_reuses_versions(tmp_path):
    cfg = F.compact_config(tmp_path)
    rev = copy.deepcopy(cfg["sources"][0])
    rev.update(source_key="fx_orig_rev1", revision_of="fx_orig", supersedes="fx_orig", snapshot_label="snapshot original rev1")
    cfg["sources"] = [cfg["sources"][0], rev]
    mf = tmp_path / "results/experiments/fx_compact_v1/runs/compact_baseline/6m/metrics/metrics_overall.csv"
    plans = plans_for(tmp_path, cfg, tmp_path)
    assert plans["fx_orig_rev1"]["versions"] == {}
    rv = [v for v in plans["fx_orig_rev1"]["views"] if v["view_key"] == "compact_climate_global/baseline/06"][0]
    assert rv["view_kind"] == "evaluation_revision" and rv["alias_of"] == "compact_climate_global/baseline/06@fx_orig"
    assert not any(f["path"].endswith(".ubj") and f["decision"].startswith(("bundle", "archive")) for f in plans["fx_orig_rev1"]["files"])
    assert P.check_global(cfg, plans, full=False)["model_versions"] == 3
    # a changed booster under the revision is a new fit, not an evaluation-only revision
    (tmp_path / "results/experiments/fx_compact_v1/runs/compact_baseline/6m/batches/2023/model_phase2_worse.ubj").write_bytes(b"refit")
    rec = tmp_path / "results/experiments/fx_compact_v1/runs/compact_baseline/6m/batches/2023/batch_record.json"
    j = json.loads(rec.read_text())
    j["artifacts"]["model_phase2_worse.ubj"] = F.sha(rec.parent / "model_phase2_worse.ubj")
    rec.write_text(json.dumps(j))
    cfg2 = copy.deepcopy(cfg)
    base = P.plan_source(cfg2, cfg2["sources"][0], tmp_path, P.Hasher(None), {})
    with pytest.raises(SourceConflict, match="new fit"):
        P.plan_source(cfg2, cfg2["sources"][1], tmp_path, P.Hasher(None), {"fx_orig": {**plans["fx_orig"]}})
    assert base["versions"]


def test_launch_alias_and_prediction_summaries(tmp_path):
    root = F.launch(tmp_path)
    cfg = F.config([F.source("fx_launch", root, "launch", ["compact_launch_global"], stage="launch", label="origin 2026-04",
                             inference_scope_label="global", h0_aliases=[{"arm": "compact_cds_weather", "of": "compact_baseline"}],
                             summaries=[{"file": "population/global_population_summary.csv", "kind": "summary", "unit": "global"},
                                        {"file": "population/global_population_paired_differences.csv", "kind": "difference", "unit": "global"}])])
    p = plans_for(tmp_path, cfg, tmp_path)["fx_launch"]
    cds6 = [v for v in p["views"] if v["view_key"] == "compact_launch_global/cds_weather/06"][0]
    assert any(k.startswith("prediction_summary.all_inference_areas.paired_difference.cds_weather_minus_baseline") for k in cds6["metrics"])
    assert not any("accuracy" in k for v in p["views"] for k in v["metrics"])
    infer = {n for n, d in p["datasets"].items() if d["descriptor"]["context"] == "inference"}
    assert any("baseline inputs" in n for n in infer) and any("CDS weather inputs" in n for n in infer)
    a0 = [v for v in p["views"] if v["view_key"] == "compact_launch_global/cds_weather/00"][0]
    assert a0["view_kind"] == "alias" and "compact_launch_global/cds_weather/00@fx_launch" not in p["versions"]


def v4_cfg(repo, copy_q3=0.5):
    root = F.somalia_v4(repo, copy_q3=copy_q3)
    return F.config([F.source("fx_v4", root, "somalia_v4", ["somalia_calibrated_observed", "somalia_calibrated_augmented"],
                              model_scope="somalia_local")])


def test_v4_incomplete_and_empty_slots_keep_required_cohort(tmp_path):
    p = plans_for(tmp_path, v4_cfg(tmp_path), tmp_path)["fx_v4"]
    v = p["views"][0]
    assert v["source_status"] == "incomplete_slots"
    assert v["slots"]["year_2023.primary"].startswith("incomplete") and v["slots"]["year_2024.primary"].startswith("empty_cohort")
    assert v["metrics"]["year_2023.primary.n_rows_required"] == 3.0 and v["metrics"]["year_2023.primary.n_rows"] == 2.0
    assert "year_2023.primary.share_phase3plus_final.r2" in v["na"]
    ds23 = p["datasets"][v["metric_dataset"]["year_2023.primary.n_rows_required"]]["descriptor"]
    assert ds23["n_required"] == 3 and ds23["n_keys"] == 3  # missing predictions do not shrink the dataset
    assert v["metrics"]["pooled.primary.n_rows_required"] == 6.0


def test_v4_copy_truth_bound_to_digest(tmp_path):
    a = plans_for(tmp_path / "a", v4_cfg(tmp_path / "a", copy_q3=0.5), tmp_path / "a")["fx_v4"]["datasets"]
    b = plans_for(tmp_path / "b", v4_cfg(tmp_path / "b", copy_q3=0.6), tmp_path / "b")["fx_v4"]["datasets"]
    da = {n: d["digest"] for n, d in a.items() if d["descriptor"]["context"] == "evaluation"}
    db = {n: d["digest"] for n, d in b.items() if d["descriptor"]["context"] == "evaluation"}
    assert da.keys() == db.keys() and any(da[n] != db[n] for n in da)


def test_store_compare_old_rows_and_namespace(tmp_path):
    def snap(rows, exps, arts):
        return {"tables": {"experiments": {"rows": {json.dumps([e]): [json.dumps({"experiment_id": e, "name": n})] for e, n in exps}},
                           "tags": {"rows": {json.dumps(k): [json.dumps(v)] for k, v in rows}},
                           "runs": {"rows": {json.dumps(["r3"]): [json.dumps({"run_uuid": "r3", "experiment_id": 3})]}}},
                "artifacts": arts}
    before = snap([(["k", "r1"], {"key": "k", "value": "a", "run_uuid": "r1"})], [(1, "IPCCH - dashboard")], {"1/x": {"sha256": "s"}})
    exps = [(1, "IPCCH - dashboard"), (3, N.DETAILED_EXPERIMENT)]
    ok = snap([(["k", "r1"], {"key": "k", "value": "a", "run_uuid": "r1"}), (["k", "r3"], {"key": "k", "value": "b", "run_uuid": "r3"})],
              exps, {"1/x": {"sha256": "s"}, "3/new": {"sha256": "t"}})
    assert S.compare(before, ok)["ok"]
    bad = snap([(["k", "r1"], {"key": "k", "value": "CHANGED", "run_uuid": "r1"})], exps, {"1/x": {"sha256": "s"}})
    assert not S.compare(before, bad)["ok"]
    foreign = snap([(["k", "r1"], {"key": "k", "value": "a", "run_uuid": "r1"}), (["k", "r9"], {"key": "k", "value": "b", "run_uuid": "r9"})],
                   exps, {"1/x": {"sha256": "s"}, "1/new": {"sha256": "t"}})
    res = S.compare(before, foreign)
    assert not res["ok"] and any("outside" in p for p in res["problems"])


def test_scratch_server_refuses_live_port(tmp_path):
    with pytest.raises(SourceConflict):
        S.scratch_server(tmp_path, 5000)
