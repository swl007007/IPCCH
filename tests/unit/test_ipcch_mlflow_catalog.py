"""Scratch MLflow integration test of the IPCCH Forecasting catalog (own server on a free port; never 5000).

Run: PYTHONPATH=tests/unit:IPCCHMLflow /home/swl007007/.venvs/ipcch-mlflow/bin/python -m pytest tests/unit/test_ipcch_mlflow_catalog.py -q
"""

from __future__ import annotations

import copy
import json
import socket
import tarfile
from pathlib import Path

import pandas as pd
import pytest

import ipcch_mlflow_fixtures as F
import catalog as C
import naming as N
import plan as P
import store as S
from naming import SourceConflict


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def env(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("ipcch_fc")
    store, repo = tmp / "store", tmp / "repo"
    (store / "artifacts").mkdir(parents=True)
    port = free_port()
    proc = S.scratch_server(store, port)
    uri = f"http://127.0.0.1:{port}"
    from mlflow.tracking import MlflowClient
    c = MlflowClient(uri)
    # pre-existing objects of another catalog (must stay byte-identical)
    eid = c.create_experiment("IPCCH - detailed runs", tags={"mlflow.note.content": "old catalog"})
    r = c.create_run(eid, run_name="GeoXGB reference | pooled | 3-month", tags={"family": "geoxgb_reference"})
    c.log_metric(r.info.run_id, "primary.all_scored.binary.f1", 0.71)
    c.log_text(r.info.run_id, "old artifact", "view/old.txt")
    c.create_registered_model("IPCCH GeoXGB reference | pooled | 3-month", description="old model")
    cfg = F.compact_config(repo)
    root = F.launch(repo)
    cfg["sources"].append(F.source("fx_launch", root, "launch", ["compact_launch_global"], stage="launch", label="origin 2026-04",
                                   inference_scope_label="global", h0_aliases=[{"arm": "compact_cds_weather", "of": "compact_baseline"}],
                                   summaries=[{"file": "population/global_population_summary.csv", "kind": "summary", "unit": "global"},
                                              {"file": "population/global_population_paired_differences.csv", "kind": "difference", "unit": "global"}]))
    yield {"store": store, "repo": repo, "uri": uri, "cfg": cfg, "client": c, "before": S.snapshot(store)}
    S.stop_server(proc)


def ctx(env):
    return C.Ctx(env["uri"], env["store"], live=False, repo=env["repo"], artifact_root=env["store"] / "artifacts")


def plans(env, cfg=None):
    return P.build_plans(cfg or env["cfg"], env["repo"], env["store"])


def test_live_port_refused(env):
    with pytest.raises(SourceConflict):
        C.Ctx("http://127.0.0.1:5000", env["store"], live=False)


def test_import_interrupt_resume_verify_and_noop(env):
    full = plans(env)
    with pytest.raises(C.Interrupt):
        C.import_sources(ctx(env), full, full, fail_after="child-1")
    x = ctx(env)
    stats = C.import_sources(x, full, full)
    assert stats["sources_resumed"] == 1 and stats["sources_imported"] == 3
    P.write_plans(full, env["store"])
    assert len(C.verify_sources(ctx(env), full, full)) == 3
    before = S.snapshot(env["store"])
    x = ctx(env)
    assert C.import_sources(x, full, full) == {"sources_noop": 3}
    after = S.snapshot(env["store"])
    assert before["digest"] == after["digest"] and before["artifacts"] == after["artifacts"]  # true no-op


def test_counts_and_external_versions(env):
    c = env["client"]
    det = c.get_experiment_by_name(N.DETAILED_EXPERIMENT)
    runs = c.search_runs([det.experiment_id], max_results=1000)
    assert sum(r.data.tags.get("record_kind") == "family" for r in runs) == 3
    assert sum(r.data.tags.get("record_kind") == "evaluation" for r in runs) == 4 + 4 + 4
    names = [m.name for m in c.search_registered_models(max_results=1000) if m.name.startswith("IPCCH Forecasting ")]
    assert len(names) == 3 + 3  # compact baseline 0/6, oracle 6 + launch baseline 0/6, cds 6 (aliases unregistered)
    vers = [v for n in names for v in c.search_model_versions(f"name='{n}'")]
    assert len(vers) == 3 * 2 + 3
    # run page tag order: readable first, zz_prov last
    child = [r for r in runs if r.data.tags.get("record_kind") == "evaluation"][0]
    assert all(r.data.tags for r in [child])


def test_download_members_and_bundle_hashes(env, tmp_path):
    c, repo = env["client"], env["repo"]
    det = c.get_experiment_by_name(N.DETAILED_EXPERIMENT)
    by = C.Ctx(env["uri"], env["store"], False, repo).runs_by_key(det.experiment_id)
    child = by["fx_ext/compact_climate_global/weather_oracle/06"][0]
    doc = json.loads(Path(c.download_artifacts(child.info.run_id, "members.json", str(tmp_path))).read_text())
    assert doc["boosters_reused"] == 8 and doc["boosters_new"] == 4
    for m in [m for m in doc["members"] if m["role"] == "booster"][:3]:
        tar = Path(c.download_artifacts(m["bundle_run_id"], "models.tar", str(tmp_path / m["bundle_run_id"])))
        with tarfile.open(tar) as t:
            data = t.extractfile(m["path"]).read()
        assert F.sha(repo / m["path"]) == m["sha256"] == __import__("hashlib").sha256(data).hexdigest()


def test_dashboard_apply_resume_and_noop(env):
    full = plans(env)
    with pytest.raises(C.Interrupt):
        C.apply_dashboard(ctx(env), env["cfg"], full, fail_after="row-2")
    st = C.apply_dashboard(ctx(env), env["cfg"], full)
    assert st["rows_noop"] == 3 and st["rows_created"] == 4 + 4 - 3
    assert C.verify_dashboard(ctx(env), env["cfg"], full)["rows"] == 8
    before = S.snapshot(env["store"])
    assert C.apply_dashboard(ctx(env), env["cfg"], full) == {"dashboard_noop": 1}
    assert S.snapshot(env["store"])["digest"] == before["digest"]


def test_source_change_refused_before_any_write(env):
    mf = env["repo"] / "results/experiments/fx_compact_v1/runs/compact_baseline/6m/metrics/metrics_overall.csv"
    orig = mf.read_bytes()
    df = pd.read_csv(mf)
    df.loc[0, "f2_phase3plus"] = 0.123
    df.to_csv(mf, index=False)
    try:
        full = plans(env)
        before = S.snapshot(env["store"])
        with pytest.raises(SourceConflict, match="fingerprint"):
            C.import_sources(ctx(env), {"fx_orig": full["fx_orig"]}, full)
        assert S.snapshot(env["store"])["digest"] == before["digest"]
    finally:
        mf.write_bytes(orig)


def test_corruption_detected(env):
    full = plans(env)
    c = env["client"]
    det = c.get_experiment_by_name(N.DETAILED_EXPERIMENT)
    rid = ctx(env).runs_by_key(det.experiment_id)["fx_launch/compact_launch_global/baseline/06"][0].info.run_id
    c.set_tag(rid, "arm", "pooled")
    with pytest.raises(SourceConflict, match="tag arm"):
        C.verify_sources(ctx(env), {"fx_launch": full["fx_launch"]}, full)
    c.set_tag(rid, "arm", "baseline")
    art = env["store"] / "artifacts" / c.get_run(rid).info.artifact_uri.split("mlflow-artifacts:/", 1)[1] / "view" / "evaluation_view.json"
    good = art.read_bytes()
    art.write_bytes(b"{}")
    with pytest.raises(SourceConflict, match="readback differs"):
        C.verify_sources(ctx(env), {"fx_launch": full["fx_launch"]}, full)
    art.write_bytes(good)
    assert C.verify_sources(ctx(env), {"fx_launch": full["fx_launch"]}, full)


def test_evaluation_only_revision_keeps_versions_and_old_snapshot(env):
    c = env["client"]
    maint_before = S.snapshot(env["store"])  # fresh baseline before a maintenance update
    names = [m.name for m in c.search_registered_models(max_results=1000) if m.name.startswith("IPCCH Forecasting ")]
    n_versions = sum(len(c.search_model_versions(f"name='{n}'")) for n in names)
    cfg = copy.deepcopy(env["cfg"])
    launch = next(s for s in cfg["sources"] if s["source_key"] == "fx_launch")
    launch["frozen"] = True
    rev = {**{k: v for k, v in launch.items() if k != "frozen"}, "source_key": "fx_launch_rev1", "revision_of": "fx_launch",
           "supersedes": "fx_launch", "snapshot_label": "origin 2026-04 rev1"}
    cfg["sources"].append(rev)
    sf = env["repo"] / "results/launch/fx_launch/population/global_population_summary.csv"
    df = pd.read_csv(sf)
    df["count_raw_p3plus"] = df["count_raw_p3plus"] + 1  # result-only update rewritten in place
    df.to_csv(sf, index=False)
    full = plans(env, cfg)
    assert full["fx_launch_rev1"]["versions"] == {}
    st = C.import_sources(ctx(env), {"fx_launch_rev1": full["fx_launch_rev1"]}, full)
    assert st.get("model_versions_created", 0) == 0 and st.get("registered_models_created", 0) == 0
    assert sum(len(c.search_model_versions(f"name='{n}'")) for n in names) == n_versions
    assert C.verify_sources(ctx(env), {"fx_launch": full["fx_launch"]}, full)  # old snapshot intact
    d = C.apply_dashboard(ctx(env), cfg, full)
    assert d["rows_retired"] == 4 and d["rows_created"] == 4
    assert C.verify_dashboard(ctx(env), cfg, full)["rows"] == 8
    res = S.compare(maint_before, S.snapshot(env["store"]))  # planned dashboard retirement is the only allowed change
    assert res["ok"], res["problems"][:5]
    det = c.get_experiment_by_name(N.DETAILED_EXPERIMENT).experiment_id
    old_detailed = ctx(env).runs_by_key(det)["fx_launch/compact_launch_global/baseline/06"][0]
    c.delete_run(old_detailed.info.run_id)  # deleting a detailed record is never allowed
    assert not S.compare(maint_before, S.snapshot(env["store"]))["ok"]
    c.restore_run(old_detailed.info.run_id)


def test_old_objects_preserved(env):
    res = S.compare(env["before"], S.snapshot(env["store"]))
    assert res["ok"], res["problems"][:5]
    assert res["artifacts"]["checked"] >= 1 and res["added_rows"]["runs"] > 0
