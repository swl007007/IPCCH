"""Contract tests for scripts/modeling/run_compact_eval_2026_extension.py on tiny mixed SOM/non-SOM fixtures.

The fixture builds a label grid 2019-01..2026-04 with partial January-April 2026 support, a frozen cohort (original
evaluation keys 2022-2025 only), per-run datasets and GENUINE original 2022-2025 runs for both scopes produced by the
unchanged annual fitter (global masks, and Somalia-local fitting+evaluation masks), plus their original metric tables
from the original code paths. The extension then validates (no writes), fits only 2026, reports and verifies for real.
"""
import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ipcch import compact_features as cpf
from ipcch import origin_safe as osf
from ipcch import regional_point_metrics as rpm

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("compact_eval_2026_extension_script", ROOT / "scripts" / "modeling" / "run_compact_eval_2026_extension.py")
ext = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = ext
_spec.loader.exec_module(ext)
som = ext.som
runner = ext.runner

KEYS = ["area_id", "year", "month"]
SHARES = list(osf.SHARE_COLUMNS)
SOM, KEN = [1, 2, 3], [10, 11, 12]
AREAS = SOM + KEN
REGION = {1: 7, 2: 7, 3: 7, 10: 1, 11: 3, 12: 8}  # regions 0, 2, 4, 5, 6 empty; region 8 has one 2026 row
BASE_FEATS = ["f1", "f2", "month_4"]
# tiny synthetic-fit settings (quality guidelines): production configs are never used for these toy fits
TINY_HP = {"n_estimators": 4, "max_depth": 2, "learning_rate": 0.3, "subsample": 1, "colsample_bytree": 1}
TINY = (dict(TINY_HP), dict(TINY_HP))
PARAMS = {"seed": 42, "half_life_months": 24.0, "phase_threshold": 0.2, "n_jobs": 16}
NAMES = {0: "Asia", 1: "East Africa", 2: "West Africa", 3: "Southern Africa", 4: "Central Africa", 5: "Latin America", 6: "Mali", 7: "Somalia", 8: "Palestine"}


def sha(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def features(arm, horizon):
    return list(BASE_FEATS) if arm == cpf.BASELINE_ARM else BASE_FEATS + (["o1"] if horizon == 3 else ["o1", "o2"])


def _phase(shares):
    norm = shares / shares.sum(axis=1, keepdims=True)
    cum = np.column_stack([norm[:, k:].sum(axis=1) for k in (1, 2, 3, 4)])
    out = np.ones(len(shares))
    for k in (2, 3, 4, 5):
        out[cum[:, k - 2] >= 0.2] = k
    return out


def build_world(base: Path, seed: int = 7):
    rng = np.random.default_rng(seed)
    base.mkdir(parents=True, exist_ok=True)
    keys = pd.DataFrame([(a, y, m) for a in AREAS for y in range(2019, 2027) for m in range(1, 13) if y * 12 + m - 1 <= 2026 * 12 + 3], columns=KEYS)
    shares = rng.dirichlet([2.0, 2.0, 1.2, 0.5, 0.2], size=len(keys)) * 100.0
    y, m, a = keys["year"].to_numpy(), keys["month"].to_numpy(), keys["area_id"].to_numpy()
    invalid = (y == 2026) & (((np.isin(a, SOM)) & ~(((a == 1) & (m == 1)) | ((m == 4) & (a != 3))))  # SOM 2026: (1,Jan) + Apr areas 1,2
                             | ((a == 11) & (m == 2)) | ((a == 12) & (m != 4)))
    invalid |= (a == 10) & (y == 2021) & (m == 3)
    shares[invalid] = np.nan
    data = keys.copy()
    data["overall_phase"] = np.where(np.isnan(shares).any(axis=1), 1.0, _phase(np.nan_to_num(shares) + 1e-12))
    for i, c in enumerate(SHARES):
        data[c] = shares[:, i]
    norm = np.nan_to_num(shares) / np.maximum(np.nan_to_num(shares).sum(axis=1, keepdims=True), 1e-9)
    data["f1"] = norm[:, 2:].sum(axis=1) + rng.normal(0, 0.05, len(keys))
    data["f2"] = rng.normal(size=len(keys))
    data.loc[rng.random(len(keys)) < 0.1, "f2"] = np.nan
    data["month_4"] = m == 4
    data["o1"], data["o2"] = rng.normal(size=len(keys)), rng.normal(size=len(keys))
    valid = osf.share_validity(data)
    evalk = valid & np.isin(y, osf.TARGET_YEARS)
    cohort = keys.assign(share_valid=valid, share_total_raw=np.nansum(shares, axis=1), eval_key=evalk)
    cohort.to_csv(base / "cohort.csv", index=False)
    pd.DataFrame({"area_id": [*SOM, *KEN], "iso3": ["SOM"] * 3 + ["KEN"] * 3, "country": ["Somalia"] * 3 + ["Kenya"] * 3}).to_csv(base / "lookup.csv", index=False)
    pd.DataFrame({"area_id": list(REGION), "region": list(REGION.values())}).to_csv(base / "regions.csv", index=False)
    cdir = base / "contract"
    cdir.mkdir()
    rows = []
    for name in BASE_FEATS + ["o1", "o2"]:
        pos = {ext.run_id(arm, h): features(arm, h).index(name) + 1 for arm, h in ext.RUNS if name in features(arm, h)}
        rows.append({"position": len(rows) + 1, "predictor": name, "group": "g", "description": f"{name} d", "unit": "u", "source": "s",
                     "time_relative_to_origin": "O", "formula": "x", "missing_semantics": "NA kept", "input_type": "numeric",
                     "expected_model_positions": json.dumps(pos), "horizons_months": "[0]", "family": "f", "source_variable": name,
                     "base_source_definition": "d", "definition_evidence": "e", "limitations": "Proxy month. This is an expected input, not a fitted result."})
    pd.DataFrame(rows).to_csv(cdir / "expected_feature_contract.csv", index=False, encoding="utf-8-sig")
    (cdir / "meta.json").write_text("{}")
    man = {"version": cpf.VERSION, "status": "COMPLETE",
           "cohort": {"path": str(base / "cohort.csv"), "sha256": sha(base / "cohort.csv")},
           "contract": {"files": {"expected_feature_contract.csv": {"path": str(cdir / "expected_feature_contract.csv"), "sha256": sha(cdir / "expected_feature_contract.csv")},
                                  "meta.json": {"path": str(cdir / "meta.json"), "sha256": sha(cdir / "meta.json")}}},
           "horizons": {str(h): {"arms": {arm: {"features": features(arm, h), "feature_sha256": osf.list_sha256(features(arm, h))}
                                           for arm in cpf.ARMS if h in cpf.ARM_HORIZONS[arm]}} for h in osf.HORIZONS}}
    (base / "parent_manifest.json").write_text(json.dumps(man))

    def load_inputs(args):
        if args.country_iso3 or args.protocol != "origin-safe" or args.seed != 42 or args.n_jobs != 16:
            raise ValueError("fixture parent gate: wrong protocol/scope/parameters")
        f = features(args.arm, args.horizon)
        frame = data[KEYS + ["overall_phase", *SHARES] + f].copy()
        targets = osf.normalized_cumulative_targets(frame)
        payload = {"fixture_parent": True, "arm": args.arm, "horizon": args.horizon}
        return {"manifest": man, "features": f, "data": frame, "targets": targets, "share_valid": targets["share_valid"].to_numpy(),
                "eval_key": evalk.copy(), "ords": osf.month_ord(frame["year"], frame["month"]), "fingerprint": som.digest(payload),
                "fingerprint_payload": payload}

    som_fp = lambda inputs, arm, h: som.digest({"original_som_local": True, "parent": inputs["fingerprint"], "arm": arm, "h": h})  # noqa: E731
    originals = {"global": base / "orig_global", "SOM": base / "orig_som"}
    hp, hp3 = TINY
    region_map = rpm.load_region_map(base / "regions.csv")
    metric_frames = {}
    for scope, root in originals.items():
        all_rows = []
        for arm, h in ext.RUNS:
            args = argparse.Namespace(arm=arm, horizon=h, seed=42, half_life_months=24.0, phase_threshold=0.2, n_jobs=16)
            inputs = load_inputs(argparse.Namespace(**vars(args), country_iso3=None, protocol="origin-safe"))
            if scope == "SOM":
                inscope = data["area_id"].isin(SOM).to_numpy()
                inputs = dict(inputs, share_valid=inputs["share_valid"] & inscope, eval_key=inputs["eval_key"] & inscope)
                inputs["fingerprint"] = som_fp(inputs, arm, h)  # computed from the parent fingerprint, like the local script
            rdir = root / "runs" / arm / f"{h}m"
            records = [runner.run_origin_batch(inputs, args, year, hp, hp3, rdir / "batches" / str(year)) for year in osf.TARGET_YEARS]
            (rdir / "predictions").mkdir()
            frames = []
            for year in osf.TARGET_YEARS:
                p = pd.read_csv(rdir / "batches" / str(year) / "predictions.csv", float_precision="round_trip")
                p.to_csv(rdir / "predictions" / f"predictions_{year}.csv", index=False, float_format="%.17g")
                frames.append(p)
            meta = {"protocol": "origin-safe", "status": "COMPLETE", "fingerprint": inputs["fingerprint"], "features": features(arm, h), "batches": records, **PARAMS}
            if scope == "SOM":
                meta["local_version"] = som.HIST_VERSION
                (rdir / "metrics").mkdir()
                pd.DataFrame([osf.flatten_origin_metrics(osf.origin_metrics(pd.concat(frames), "SOM", "pooled"))]).to_csv(rdir / "metrics" / "metrics_overall.csv", index=False)
            (rdir / "run_metadata.json").write_text(json.dumps(meta))
            pred = pd.concat(frames, ignore_index=True)
            if scope == "global":
                all_rows += rpm.metric_rows(rpm.assign_regions(pred, region_map), ext.run_id(arm, h), arm, h)
            else:
                all_rows += som.som_metric_rows(pred, arm, h)
        metrics = pd.DataFrame(all_rows)
        metric_frames[scope] = metrics
        if scope == "global":
            (root / "verification").mkdir(parents=True)
            metrics.insert(5, "region_name", [None if pd.isna(r) else NAMES[int(r)] for r in metrics["region"]])
            metrics.to_csv(root / "verification" / "all_metrics_long.csv", index=False)
            d = pd.DataFrame(rpm.delta_rows(metrics, cpf.ORACLE_ARM, cpf.BASELINE_ARM, (3, 6, 12)))
            d[d.scope == "global"].to_csv(root / "verification" / "global_deltas.csv", index=False)
            d[d.scope == "region"].to_csv(root / "verification" / "regional_deltas.csv", index=False)
            inv = []
            for arm, h in ext.RUNS:
                rdir = root / "runs" / arm / f"{h}m"
                inv.append({"run": ext.run_id(arm, h), "year": None, "artifact": "run_metadata.json", "path": str(rdir / "run_metadata.json"),
                            "recorded_sha256": None, "current_sha256": sha(rdir / "run_metadata.json")})
                for year in osf.TARGET_YEARS:
                    for name in sorted(osf.REQUIRED_BATCH_ARTIFACTS) + ["batch_record.json"]:
                        q = rdir / "batches" / str(year) / name
                        inv.append({"run": ext.run_id(arm, h), "year": year, "artifact": name, "path": str(q),
                                    "recorded_sha256": None if name == "batch_record.json" else sha(q), "current_sha256": sha(q)})
            pd.DataFrame(inv).to_csv(root / "verification" / "artifact_inventory.csv", index=False)
            (root / "verification" / "verification_summary.json").write_text(json.dumps(
                {"passed": True, "problems": [], "batches": 28, "models_reloaded": 112,
                 "region_name_annotation": {"region_names": {str(k): v for k, v in NAMES.items()}}}))
        else:
            for sub in ("report", "verification", "inputs"):
                (root / sub).mkdir(parents=True)
            metrics.to_csv(root / "report" / "som_metrics_long.csv", index=False)
            som.hist_delta_table(metrics).to_csv(root / "report" / "som_oracle_minus_baseline_deltas.csv", index=False)
            (root / "inputs" / f"{som.HIST_VERSION}_manifest.json").write_text("{}")
            inv = [{"path": str(q), "sha256": sha(q), "bytes": q.stat().st_size} for q in sorted(root.rglob("*")) if q.is_file()]
            (root / "verification" / "verification.json").write_text(json.dumps(
                {"passed": True, "problems": [], "checks": {"batches": 28, "models_reloaded": 112}, "inventory": inv}))
    # approved spec with independently derived expectations
    spec_dir = base / "spec"
    (spec_dir / "research").mkdir(parents=True)
    exp_rows = []
    for scope in ext.SCOPES:
        inscope = np.ones(len(keys), bool) if scope == "global" else np.isin(a, SOM)
        ev = valid & inscope & (y == 2026)
        for arm, h in ext.RUNS:
            cutoff = 2026 * 12 - max(h, 1)
            fit = valid & inscope & (y * 12 + m - 1 <= cutoff)
            exp_rows.append({"scope": scope, "model_scope": ext.MODEL_SCOPE[scope], "arm": arm, "horizon": h, "block_year": 2026,
                             "fit_origin_month": osf.ord_label(2026 * 12 - h), "fit_label_cutoff_month": osf.ord_label(cutoff), "fit_rows": int(fit.sum()),
                             "fit_areas": int(len(set(a[fit]))), "eval_rows": int(ev.sum()), "eval_areas": int(len(set(a[ev]))),
                             "feature_count": len(features(arm, h)), "new_boosters": 4})
    pd.DataFrame(exp_rows).to_csv(spec_dir / "expected_runs.csv", index=False)
    for name in ext.SPEC_FILES:
        if not (spec_dir / name).exists():
            (spec_dir / name).write_text(f"fixture {name}\n")
    protected = sorted(p for r in originals.values() for p in r.rglob("*") if p.is_file()) + [base / "parent_manifest.json", base / "cohort.csv"]

    def ctx(scope, **kw):
        inscope = np.ones(len(keys), bool) if scope == "global" else np.isin(a, SOM)
        ev = valid & inscope & (y == 2026)
        old = keys[evalk & inscope].reset_index(drop=True)
        base_kw = dict(scope=scope, results=base / "out" / "results" / ext.VERSIONS[scope], reports=base / "out" / "reports" / ext.VERSIONS[scope],
                       original_results=originals[scope], parent_manifest=base / "parent_manifest.json", membership=base / "lookup.csv",
                       region_map=base / "regions.csv", region_map_sha256=None, spec_dir=spec_dir,
                       month_support={mm: int((ev & (m == mm)).sum()) for mm in (1, 2, 3, 4)}, original_eval_sha256=osf.keys_sha256(old),
                       frozen_feature_sha256=None, contract_sha256=None, load_inputs=load_inputs, hyperparameters=lambda: TINY,
                       original_fingerprint=(lambda inputs, arm, h: inputs["fingerprint"]) if scope == "global" else som_fp,
                       protected_paths=lambda: [("old", p) for p in protected])
        base_kw.update(kw)
        return ext.Ctx(**base_kw)

    return argparse.Namespace(ctx=ctx, data=data, cohort=cohort, keys=keys, valid=valid, evalk=evalk, base=base, originals=originals,
                              metrics=metric_frames, protected=protected)


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    w = build_world(tmp_path_factory.mktemp("eval2026"))
    w.before = {p: p.stat().st_mtime_ns for p in w.base.rglob("*")}
    w.validate = {s: ext.validate(w.ctx(s)) for s in ext.SCOPES}
    w.after_validate = {p: p.stat().st_mtime_ns for p in w.base.rglob("*")}
    w.train = {s: ext.train(w.ctx(s)) for s in ext.SCOPES}
    w.report = {s: ext.report(w.ctx(s)) for s in ext.SCOPES}
    w.pending = {s: {"meta": json.loads((w.ctx(s).results / "report" / "comparison_metadata.json").read_text())["status"],
                     "md": (w.ctx(s).reports / "report.md").read_text()} for s in ext.SCOPES}
    w.verify = {s: ext.verify(w.ctx(s)) for s in ext.SCOPES}
    return w


# --------------------------------------------------------------------------- selection, validation and fitting contract


def test_validate_only_passes_and_writes_nothing(world):
    assert world.after_validate == world.before
    for scope in ext.SCOPES:
        v = world.validate[scope]
        assert v["passed"], v["problems"][:5]
        assert v["original_parity_cells"] == 7 * (10 if scope == "global" else 1) * 5 * 8
        assert all(r["fit_max_label_month"] < "2026-01" for r in v["runs"].values())
        assert len({r["extension_fingerprint_if_manifest_written"] for r in v["runs"].values()}) == 7
        assert all(r["extension_fingerprint_if_manifest_written"] != r["original_fingerprint"] for r in v["runs"].values())


def test_2026_selection_is_complete_january_april_and_local(world):
    y, m, a = world.keys["year"].to_numpy(), world.keys["month"].to_numpy(), world.keys["area_id"].to_numpy()
    for scope in ext.SCOPES:
        sel = ext.prepare(world.ctx(scope), write=False)["selection"]
        inscope = np.ones(len(a), bool) if scope == "global" else np.isin(a, SOM)
        want = world.keys[world.valid & inscope & (y == 2026)].reset_index(drop=True)
        assert sel["new_keys"].equals(want)  # complete set, not a subset
        assert np.array_equal(sel["fit_valid"], world.valid & inscope)
    som_sel = ext.prepare(world.ctx("SOM"), write=False)["selection"]["summary"]
    assert som_sel["month_support_rows"] == {1: 1, 2: 0, 3: 0, 4: 2} and som_sel["new_eval_areas"] == 2  # (1, Jan) also has an April row
    with pytest.raises(ext.LocalError, match="support"):
        ext.prepare(world.ctx("SOM", month_support={1: 1, 2: 1, 3: 0, 4: 2}), write=False)


def test_only_2026_fitted_with_annual_anchors_and_no_2026_labels(world):
    for scope in ext.SCOPES:
        ctx = world.ctx(scope)
        assert not (ctx.results / "runs" / cpf.ORACLE_ARM / "0m").exists()
        for arm, h in ext.RUNS:
            rdir = ext.run_dir(ctx, arm, h)
            assert sorted(p.name for p in (rdir / "batches").iterdir()) == ["2026"]  # no old-year refit
            meta = json.loads((rdir / "run_metadata.json").read_text())
            assert meta["reused_years"] == [2022, 2023, 2024, 2025] and meta["fitted_here_years"] == [2026]
            assert meta["fingerprint"] != meta["original_fingerprint"]
            fk = pd.read_csv(rdir / "batches" / "2026" / "fit_keys.csv.gz")
            ords = fk["year"] * 12 + fk["month"] - 1
            assert ords.max() <= 2026 * 12 - max(h, 1) and (fk["year"] < 2026).all()
            assert np.allclose(fk["sample_weight"], 0.5 ** ((2026 * 12 - h - ords) / 24.0), rtol=0, atol=1e-15)
            if scope == "SOM":
                assert fk["area_id"].isin(SOM).all()
            combined = pd.read_csv(meta["predictions"]["path"], float_precision="round_trip")
            orig = pd.concat([pd.read_csv(ext.original_run_dir(ctx, arm, h) / "predictions" / f"predictions_{yy}.csv", float_precision="round_trip")
                              for yy in osf.TARGET_YEARS], ignore_index=True)
            kept = combined[combined["year"] < 2026].reset_index(drop=True)
            assert kept.equals(orig.sort_values(KEYS, kind="mergesort").reset_index(drop=True))  # original rows preserved exactly


def test_new_boosters_counted_and_verification_passes(world):
    for scope in ext.SCOPES:
        v = world.verify[scope]
        assert v["passed"], v["problems"][:5]
        c = v["checks"]
        assert c["new_batches"] == 7 and c["new_models_replayed"] == 28 and c["schemas_inspected"] == 140 and c["original_batches_checked"] == 28
        assert c["max_new_replay_abs_diff"] <= 1e-6
        assert c["metric_cells_replayed"] == 7 * (10 if scope == "global" else 1) * 7 * 8
        assert c["original_parity_cells"] == 7 * (10 if scope == "global" else 1) * 5 * 8


# --------------------------------------------------------------------------- metrics, periods and reports


def test_periods_pooled_rows_empty_regions_and_single_row_r2(world):
    ctx = world.ctx("global")
    m = pd.read_csv(ctx.results / "report" / "all_metrics_long.csv", keep_default_na=False, na_values=[""])
    assert len(m) == 3920 and set(m["period"].astype(str)) == set(ext.PERIODS)
    g = m[(m["scope"] == "global") & (m["metric"] == "exact_phase_accuracy") & (m["run_id"] == "compact_baseline/0m")].set_index("period")
    n_old, n_new = int(world.evalk.sum()), int((world.valid & (world.keys["year"] == 2026)).sum())
    assert g.loc["pooled_2022_2025", "n_rows"] == n_old and g.loc["pooled_2022_2026", "n_rows"] == n_old + n_new and g.loc["2026", "n_rows"] == n_new
    empty = m[(m["scope"] == "region") & (m["region"] == 2)]
    assert len(empty) == 7 * 7 * 8 and empty["value"].isna().all() and (empty["reason"] == "no eligible samples").all()
    r8 = m[(m["region"] == 8) & (m["period"].astype(str) == "2026") & (m["metric"] == "r2_phase3plus")]
    assert r8["value"].isna().all() and (r8["n_rows"] == 1).all() and (r8["reason"] == "fewer than two valid samples").all()
    assert (m.loc[m["scope"] == "region", "region_name"] == m.loc[m["scope"] == "region", "region"].astype(int).map(NAMES)).all()
    sm = pd.read_csv(world.ctx("SOM").results / "report" / "som_metrics_long.csv", keep_default_na=False, na_values=[""])
    assert len(sm) == 392 and set(sm["scope"]) == {"SOM"}
    d = pd.read_csv(world.ctx("SOM").results / "report" / "som_oracle_minus_baseline_deltas.csv", keep_default_na=False, na_values=[""])
    h0 = d[d["horizon"] == 0]
    assert len(h0) == 7 * 8 and ((h0["status"] == "shared_h0_zero") == h0["delta"].notna()).all() and (h0["delta"].dropna() == 0).all()


def test_reports_are_pending_until_verification_then_truthfully_final(world):
    for scope in ext.SCOPES:
        ctx = world.ctx(scope)
        assert world.pending[scope]["meta"] == "verification_pending" and "**Status: verification_pending**" in world.pending[scope]["md"]
        meta = json.loads((ctx.results / "report" / "comparison_metadata.json").read_text())
        assert meta["status"] == "verified" and meta["models"] == {"reused_boosters": 112, "new_boosters": 28, "referenced_boosters": 140}
        assert meta["main_pooled_period"] == "pooled_2022_2026" and meta["periods"]["pooled_2022_2025"] == [2022, 2023, 2024, 2025]
        md = (ctx.reports / "report.md").read_text()
        assert "January-April only" in md and "**Status: verified**" in md and "verification_pending" not in md
        cb = ctx.reports / "model_run_codebook" / ext.CODEBOOK_NAME[scope]
        assert meta["report_md"]["sha256"] == sha(ctx.reports / "report.md") and meta["codebook"]["sha256"] == sha(cb)
        idx = pd.read_csv(ctx.reports / "model_run_codebook" / "model_run_index.csv")
        assert idx["reused_boosters"].sum() == 112 and idx["new_boosters"].sum() == 28 and (idx["reused_years"] == "2022|2023|2024|2025").all()
        book = pd.read_csv(cb, encoding="utf-8-sig")
        assert (book["limitations"] == "Proxy month.").all() and book["fit_status"].str.endswith("112 reused 2022-2025 + 28 fitted 2026); verified").all()
        summary = json.loads((ctx.results / "verification" / "verification_summary.json").read_text())
        assert summary["final_reporting"]["status"] == "verified" and summary["final_reporting"]["codebook_sha256"] == sha(cb)
        lineage = json.loads((ext.run_dir(ctx, cpf.BASELINE_ARM, 0) / "run_metadata.json").read_text())["sources_by_year"]["2022"]
        assert lineage["accepted_inventory"]["entries_checked"] == 7


# --------------------------------------------------------------------------- identity, resume and tamper detection


def test_resume_verifies_without_refit(world):
    ctx = world.ctx("global")
    stamp = {p: p.stat().st_mtime_ns for p in ctx.results.rglob("model_*.ubj")}
    out = ext.train(ctx)
    assert len(out["runs"]) == 7 and {p: p.stat().st_mtime_ns for p in ctx.results.rglob("model_*.ubj")} == stamp


def test_incomplete_batch_and_changed_identity_are_rejected(tmp_path):
    w = build_world(tmp_path / "b", seed=3)
    ctx = w.ctx("SOM")
    bdir = ext.run_dir(ctx, cpf.BASELINE_ARM, 0) / "batches" / "2026"
    bdir.mkdir(parents=True)
    (bdir / "model_phase2_worse.ubj").write_bytes(b"partial")
    with pytest.raises(ext.LocalError, match="no batch record"):
        ext.train(ctx)
    assert (bdir / "model_phase2_worse.ubj").read_bytes() == b"partial"
    # a changed approved spec cannot resume into the same root
    (w.base / "spec" / "design.md").write_text("edited\n")
    with pytest.raises(ext.LocalError, match="different bytes"):
        ext.prepare(ctx, write=False)


def test_tampered_original_artifact_blocks_reuse(tmp_path):
    w = build_world(tmp_path / "t", seed=5)
    ctx = w.ctx("global")
    pred = ext.original_run_dir(ctx, cpf.BASELINE_ARM, 3) / "batches" / "2024" / "predictions.csv"
    pred.write_bytes(pred.read_bytes() + b"\n")
    out = ext.validate(ctx)
    assert not out["passed"] and any("not reconciled with the accepted inventory" in p for p in out["problems"])
    with pytest.raises(ext.LocalError, match="original 2022-2025 artifacts failed"):
        ext.train(ctx)
    pred.write_bytes(pred.read_bytes()[:-1])  # restore; then a published file outside the accepted inventory
    pub = ext.original_run_dir(ctx, cpf.BASELINE_ARM, 6) / "predictions" / "predictions_2023.csv"
    frame = pd.read_csv(pub, float_precision="round_trip")
    frame.loc[0, "phase3_pred"] += 0.5
    frame.to_csv(pub, index=False, float_format="%.17g")
    assert any("published original predictions differ" in p for p in ext.validate(ctx)["problems"])
    summary = ctx.original_results / "verification" / "verification_summary.json"
    s = json.loads(summary.read_text())
    summary.write_text(json.dumps(dict(s, passed=False)))
    with pytest.raises(ext.LocalError, match="did not pass"):
        ext.prepare(ctx, write=False)


def test_verify_detects_missing_report_metric_tamper_and_protected_change(world):
    ctx = world.ctx("SOM")
    md, metrics = ctx.reports / "report.md", ctx.results / "report" / "som_metrics_long.csv"
    meta = ctx.results / "report" / "comparison_metadata.json"
    prot = world.protected[0]
    saved = {p: p.read_bytes() for p in (md, metrics, prot)}
    try:
        md.unlink()
        prot.write_bytes(saved[prot] + b" ")
        v = ext.verify(ctx)
        assert not v["passed"] and any("mandatory report outputs missing" in p for p in v["problems"])
        assert any("protected files changed" in p for p in v["problems"])
        assert json.loads(meta.read_text())["status"] == "verification_failed"  # no stale accepted status survives a failure
        md.write_bytes(saved[md])
        prot.write_bytes(saved[prot])
        m = pd.read_csv(metrics, keep_default_na=False, na_values=[""])
        row = m.index[m["period"].astype(str) == "2026"][0]
        m.loc[row, "n_areas"] += 1  # a support-only change must fail
        m.to_csv(metrics, index=False, float_format="%.17g")
        v = ext.verify(ctx)
        assert not v["passed"] and any("support columns" in p for p in v["problems"])
        assert "**Status: verification_failed**" in md.read_text()
    finally:
        metrics.write_bytes(saved[metrics])
        prot.write_bytes(saved[prot])
        if not md.exists():
            md.write_bytes(saved[md])
    final = ext.verify(ctx)
    assert final["passed"] and json.loads(meta.read_text())["status"] == "verified" and "**Status: verified**" in md.read_text()


def test_global_split_tables_must_equal_their_canonical_subsets(world):
    ctx = world.ctx("global")
    split = ctx.results / "report" / "regional_metrics.csv"
    original = split.read_bytes()
    try:
        m = pd.read_csv(split, keep_default_na=False, na_values=[""])
        m.loc[0, "true_positive_3plus"] += 1
        m.to_csv(split, index=False, float_format="%.17g")
        v = ext.verify(ctx)
        assert not v["passed"] and any("regional_metrics.csv is not exactly the region subset" in p for p in v["problems"])
    finally:
        split.write_bytes(original)
    assert ext.verify(ctx)["passed"]


def test_archived_spec_copies_keep_identity(world):
    ctx = world.ctx("global")
    want = sha(ext.manifest_path(ctx))
    spec = ctx.spec_dir
    moved = spec.with_name("archived_spec")
    spec.rename(moved)
    try:
        assert ext.prepare(ctx, write=False)["sha256"] == want
        copy = ext.manifest_path(ctx).parent / "approved_spec" / "prd.md"
        original = copy.read_bytes()
        copy.write_bytes(original + b"x")
        try:
            with pytest.raises(ext.LocalError, match="differs from its manifest hash"):
                ext.prepare(ctx, write=False)
        finally:
            copy.write_bytes(original)
    finally:
        moved.rename(spec)


def test_reloaded_class_must_match_even_within_raw_tolerance():
    pred = pd.DataFrame({"phase2_pred": [0.9], "phase3_pred": [0.19999995], "phase4_pred": [0.0], "phase5_pred": [0.0], "overall_phase_pred": [2]})
    ok = {c: pred[c].to_numpy() for c in osf.PRED_COLUMNS}
    assert som.replayed_class_problems("x", pred, ok, 0.2) == []
    assert som.replayed_class_problems("x", pred, dict(ok, phase3_pred=np.array([0.20000005])), 0.2)


def test_new_roots_never_enter_protected_namespaces():
    with pytest.raises(ext.LocalError, match="protected namespace"):
        ext.assert_new_root(ext.ORIG_GLOBAL / "runs")
    assert ext.assert_new_root(ext.Ctx(scope="global").results)
