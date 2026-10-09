"""Contract tests for scripts/modeling/run_somalia_local_compact_test.py on tiny mixed SOM/non-SOM fixtures.

The fixture parents mimic the frozen historical (compact cohort + per-arm datasets) and launch (fit selections, inference
matrices, population ledger, cap audit, contract) inputs. The unchanged frozen fitters run for real: the complete fixed
historical plan (7 runs x 4 annual blocks x 4 regressors) and launch plan (5 runs x 4 regressors), then report and the
independent verifier. Real parent gates are replaced by injected loaders that return the same structures.
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
from ipcch import compact_launch as cl
from ipcch import origin_safe as osf

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("somalia_local_compact_test_script", ROOT / "scripts" / "modeling" / "run_somalia_local_compact_test.py")
sl = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = sl
_spec.loader.exec_module(sl)

KEYS = ["area_id", "year", "month"]
SHARES = list(osf.SHARE_COLUMNS)
SOM, KEN = [1, 2, 3], [10, 11]
AREAS = SOM + KEN
LAUNCH_INFERENCE = [1, 2, 10, 11]  # SOM area 3 has no April 2026 parent row (like 3146)
BASE_FEATS = ["f1", "f2", "month_4"]


def sha(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def frozen_code_hashes():
    return {str(p): sha(p) for role, p in sl.default_frozen_paths() if role == "code"}


# --------------------------------------------------------------------------- fixture parents


def _shares(rng, n):
    s = rng.dirichlet([2.0, 2.0, 1.2, 0.5, 0.2], size=n) * 100.0
    return s


def _phase(shares):
    norm = shares / shares.sum(axis=1, keepdims=True)
    cum = np.column_stack([norm[:, k:].sum(axis=1) for k in (1, 2, 3, 4)])
    out = np.ones(len(shares))
    for k in (2, 3, 4, 5):
        out[cum[:, k - 2] >= 0.2] = k
    return out


def _features(rng, frame, shares):
    with np.errstate(invalid="ignore", divide="ignore"):
        norm = shares / np.nansum(shares, axis=1, keepdims=True)
    out = pd.DataFrame(index=frame.index)
    out["f1"] = np.nan_to_num(norm[:, 2:].sum(axis=1)) + rng.normal(0, 0.05, len(frame))
    out["f2"] = rng.normal(size=len(frame))
    out.loc[rng.random(len(frame)) < 0.1, "f2"] = np.nan
    out["month_4"] = frame["month"].to_numpy() == 4
    out["o1"] = rng.normal(size=len(frame))
    out["o2"] = rng.normal(size=len(frame))
    return out


def hist_features(arm, horizon):
    if arm == cpf.BASELINE_ARM:
        return list(BASE_FEATS)
    return BASE_FEATS + (["o1"] if horizon == 3 else ["o1", "o2"])


def contract_rows(runs, feature_fn):
    rows = []
    for name in BASE_FEATS + ["o1", "o2"]:
        pos = {run: feature_fn(*sl._split(run)).index(name) + 1 for run in runs if name in feature_fn(*sl._split(run))}
        rows.append({"position": len(rows) + 1, "predictor": name, "group": "g", "description": f"{name} description", "unit": "u", "source": "s",
                     "time_relative_to_origin": "O", "formula": "x", "missing_semantics": "NA kept", "input_type": "numeric",
                     "expected_model_positions": json.dumps(pos), "horizons_months": "[0]", "family": "weather_oracle" if name.startswith("o") else "f",
                     "source_variable": name, "base_source_definition": "d", "definition_evidence": "e",
                     "limitations": "Proxy month. This is an expected input, not a fitted result.",
                     **{k: f"{k} of {name}" for k in ("training_source", "inference_source", "training_formula", "inference_formula",
                                                      "training_missing_semantics", "inference_missing_semantics", "training_reference_period",
                                                      "inference_reference_period", "training_spatial_definition", "inference_spatial_definition")}})
    return pd.DataFrame(rows)


def write_contract(directory: Path, runs, feature_fn) -> dict:
    directory.mkdir(parents=True, exist_ok=True)
    contract_rows(runs, feature_fn).to_csv(directory / "expected_feature_contract.csv", index=False, encoding="utf-8-sig")
    (directory / "expected_feature_contract_metadata.json").write_text(json.dumps({"fixture": True}))
    (directory / "expected_run_index.csv").write_text("run_id\n" + "\n".join(runs) + "\n")
    return {n: {"path": str(directory / n), "sha256": sha(directory / n)} for n in ("expected_feature_contract.csv",
                                                                                     "expected_feature_contract_metadata.json", "expected_run_index.csv")}


def build_world(base: Path, seed: int = 7):
    rng = np.random.default_rng(seed)
    base.mkdir(parents=True, exist_ok=True)
    # membership (Namibia's literal NA code must survive)
    lookup = pd.DataFrame({"area_id": [*SOM, *KEN, 20], "iso3": ["SOM"] * 3 + ["KEN"] * 2 + ["NAM"],
                           "country": ["Somalia"] * 3 + ["Kenya"] * 2 + ["Namibia"], "country_code": ["SO"] * 3 + ["KE"] * 2 + ["NA"],
                           "country_en": ["Somalia"] * 3 + ["Kenya"] * 2 + ["Namibia"]})
    lookup.to_csv(base / "lookup.csv", index=False)
    spec_dir = base / "spec"
    spec_dir.mkdir()
    for name in sl.SPEC_FILES:
        (spec_dir / name).write_text(f"fixture {name}\n")
    # ---- historical parent: one label grid, a cohort and per-arm datasets
    keys = pd.DataFrame([(a, y, m) for a in AREAS for y in range(2019, 2026) for m in range(1, 13)], columns=KEYS)
    shares = _shares(rng, len(keys))
    som24 = (keys["area_id"].isin(SOM) & (keys["year"] == 2024)).to_numpy()
    shares[som24] = [60.0, 40.0, 0.0, 0.0, 0.0]  # no observed phase 3+ and constant truth: undefined recall/F2/R2 cells
    bad = keys.index[(keys["area_id"] == 2) & (keys["year"] == 2022) & (keys["month"] == 5)].tolist() + \
        keys.index[(keys["area_id"] == 10) & (keys["year"] == 2021) & (keys["month"] == 3)].tolist()
    shares[bad] = np.nan
    data = keys.copy()
    data["overall_phase"] = np.where(np.isnan(shares).any(axis=1), 1.0, _phase(np.nan_to_num(shares) + 1e-12))
    for i, c in enumerate(SHARES):
        data[c] = shares[:, i]
    feats = _features(rng, keys, np.nan_to_num(shares))
    data = pd.concat([data, feats], axis=1)
    valid = osf.share_validity(data)
    evalk = valid & data["year"].isin(osf.TARGET_YEARS).to_numpy()
    cohort = keys.assign(share_valid=valid, share_total_raw=np.nansum(shares, axis=1), eval_key=evalk)
    cohort.to_csv(base / "cohort.csv", index=False)
    hdir = base / "hist_parent"
    contract = write_contract(hdir / "contract", [sl.run_id(a, h) for a, h in sl.HIST_RUNS], hist_features)
    hman = {"version": cpf.VERSION, "status": "COMPLETE",
            "cohort": {"path": str(base / "cohort.csv"), "sha256": sha(base / "cohort.csv"), "label_keys_sha256": osf.keys_sha256(keys),
                       "eval_keys_sha256": osf.keys_sha256(keys[evalk])},
            "contract": {"files": contract},
            "horizons": {str(h): {"arms": {a: {"features": hist_features(a, h), "feature_sha256": osf.list_sha256(hist_features(a, h))}
                                           for a in cpf.ARMS if h in cpf.ARM_HORIZONS[a]}} for h in osf.HORIZONS}}
    (hdir / "manifest.json").write_text(json.dumps(hman))

    def load_hist_inputs(args):
        if args.country_iso3 or args.protocol != "origin-safe" or args.n_jobs != 16 or args.seed != 42:
            raise ValueError("fixture parent gate: wrong protocol/scope/parameters")
        f = hist_features(args.arm, args.horizon)
        frame = data[KEYS + ["overall_phase", *SHARES] + f].copy()
        targets = osf.normalized_cumulative_targets(frame)
        payload = {"fixture_parent": True, "arm": args.arm, "horizon": args.horizon}
        return {"manifest": hman, "manifest_path": hdir / "manifest.json", "entry": {}, "features": f, "data": frame, "targets": targets,
                "share_valid": targets["share_valid"].to_numpy(), "eval_key": evalk.copy(), "ords": osf.month_ord(frame["year"], frame["month"]),
                "fingerprint": sl.digest(payload), "fingerprint_payload": payload}

    # ---- launch parent: training datasets, all-country fit selections/inference, population, contract, cap audit
    ldir = base / "launch_parent"
    (ldir / "training").mkdir(parents=True)
    (ldir / "inference").mkdir()
    lkeys = pd.DataFrame([(a, y, m) for a in AREAS for y, m in [(y, m) for y in (2024, 2025, 2026) for m in range(1, 13)] if y * 12 + m - 1 <= 2026 * 12 + 3],
                         columns=KEYS)
    lshares = _shares(rng, len(lkeys))
    lshares[(lkeys["area_id"] == 1).to_numpy() & (lkeys["year"] == 2025).to_numpy() & (lkeys["month"] == 7).to_numpy()] = np.nan
    lbase = lkeys.copy()
    lbase["overall_phase"] = _phase(np.nan_to_num(lshares) + 1e-12)
    for i, c in enumerate(SHARES):
        lbase[c] = lshares[:, i]
    lbase = pd.concat([lbase, _features(rng, lkeys, np.nan_to_num(lshares))], axis=1)
    ords = osf.month_ord(lbase["year"], lbase["month"])
    eligible = osf.share_validity(lbase) & (ords <= cl.LABEL_CUTOFF_ORD)
    tg = osf.normalized_cumulative_targets(lbase.loc[eligible].reset_index(drop=True))
    fit = lbase.loc[eligible, KEYS].reset_index(drop=True)
    fit["fit_ord"] = ords[eligible]
    for c in osf.CUMULATIVE_TARGETS:
        fit[c] = tg[c].to_numpy()
    fit["sample_weight"] = osf.origin_weights(fit["fit_ord"], cl.ORIGIN_ORD, 24.0)
    fit["age_months"] = cl.ORIGIN_ORD - fit["fit_ord"]
    runs = {}
    weather_extra = rng.normal(size=(len(LAUNCH_INFERENCE), 2))
    base_inf = pd.DataFrame({"area_id": LAUNCH_INFERENCE, "f1": rng.normal(size=4), "f2": [0.1, np.nan, 0.3, 0.4]})
    for arm, horizon in sl.LAUNCH_RUNS:
        feats = BASE_FEATS + (["o1", "o2"] if arm == cl.WEATHER else [])
        tpath = ldir / "training" / f"train_{cl.TRAINING_ARM[arm]}_h{horizon}.csv"
        lbase[KEYS + ["overall_phase", *SHARES] + feats].to_csv(tpath, index=False, float_format="%.17g")
        spath = ldir / "training" / f"fit_selection_{arm}_h{horizon}.csv"
        fit.to_csv(spath, index=False, float_format="%.17g")
        ty, tm = cl.TARGETS[horizon]
        inf = pd.DataFrame({"area_id": LAUNCH_INFERENCE, "year": ty, "month": tm, "f1": base_inf["f1"], "f2": base_inf["f2"], "month_4": tm == 4})
        if arm == cl.WEATHER:
            inf["o1"], inf["o2"] = weather_extra[:, 0], weather_extra[:, 1]
        ipath = ldir / "inference" / f"inference_{arm}_h{horizon}.csv"
        inf.to_csv(ipath, index=False, float_format="%.17g")
        runs[sl.run_id(arm, horizon)] = {
            "arm": arm, "horizon": horizon, "training_arm": cl.TRAINING_ARM[arm], "target_month": f"{ty}-{tm:02d}", "features": feats,
            "feature_count": len(feats), "feature_sha256": osf.list_sha256(feats), "training_dataset": {"path": str(tpath), "sha256": sha(tpath)},
            "fit_selection": {"path": str(spath), "sha256": sha(spath)}, "inference": {"path": str(ipath), "sha256": sha(ipath)},
            "weather_inference": "CDS cube (accepted weather stage)" if arm == cl.WEATHER else "none"}
    pop = pd.DataFrame({"area_id": LAUNCH_INFERENCE, "estimated_population": [1000.0, 0.0, 500.0, 700.0]})
    pop.to_csv(ldir / "population.csv", index=False)
    lcontract = write_contract(ldir / "approved_spec", [sl.run_id(a, h) for a, h in sl.LAUNCH_RUNS],
                               lambda a, h: BASE_FEATS + (["o1", "o2"] if a == cl.WEATHER else []))
    lman = {"version": cl.VERSION, "status": "COMPLETE", "contract": {"dir": str(ldir / "approved_spec"), "sha256": {k: v["sha256"] for k, v in lcontract.items()}},
            "origin": "2026-04", "targets": {"0": "2026-04", "6": "2026-10", "12": "2027-04"}, "training_label_cutoff_exclusive": "2026-04-01",
            "inference_ipc_history_max_month": "2026-03", "weight_rule": "0.5 ** ((2026-04 - U) / 24)", "runs": runs,
            "ledgers": {"population": {"path": str(ldir / "population.csv"), "sha256": sha(ldir / "population.csv")}},
            "weather": {"cube": {"path": "fixture", "sha256": "0" * 64}, "status": "ACCEPTED"}}
    (ldir / "manifest.json").write_text(json.dumps(lman))

    def validate_launch_parent(path):
        m = json.loads(Path(path).read_text())
        for entry in m["runs"].values():
            for label in ("training_dataset", "fit_selection", "inference"):
                if sha(entry[label]["path"]) != entry[label]["sha256"]:
                    raise cl.LaunchError(f"fixture parent gate: {label} bytes differ")
        return m

    som_raw, ref = 1000.0, 600.0

    def cap_audit(parent):
        rows = []
        for country, raw, areas, reference in (("Kenya", 1200.0, 2, 5000.0), ("Somalia", som_raw, 2, ref)):
            applied = raw > 1.10 * reference
            factor = 0.95 * reference / raw if applied else 1.0
            rows.append({"country": country, "raw_population": raw, "areas": areas, "zero_population_areas": int(country == "Somalia"),
                         "country_code": "NA" if country == "Kenya" else "SO", "country_en": country, "population_as_of_date": "2025",
                         "lookup_code_used": "NA" if country == "Kenya" else "SO", "reference_population": reference,
                         "raw_to_reference_ratio": raw / reference, "cap_trigger_ratio": 1.10, "cap_applied": applied, "cap_factor": factor,
                         "effective_population": raw * factor})
        return pd.DataFrame(rows)

    # ---- geometry (tiny squares) and frozen "parent" files
    import geopandas as gpd
    from shapely.geometry import box

    geo = gpd.GeoDataFrame({"area_id": [str(a) for a in AREAS]}, geometry=[box(41 + i, 0, 41.9 + i, 0.9) for i in range(len(AREAS))], crs="EPSG:4326")
    geo.to_file(base / "geom.shp")
    from ipcch import alert_risk_maps as arm

    (base / "old_result.txt").write_text("accepted global output\n")
    frozen = [("parent_inputs", hdir / "manifest.json"), ("parent_inputs", ldir / "manifest.json"), ("membership", base / "lookup.csv"),
              ("old_results", base / "old_result.txt")]
    roots = base / "out"
    ctx = sl.Ctx(membership=base / "lookup.csv", hist_manifest=hdir / "manifest.json", launch_manifest=ldir / "manifest.json",
                 hist_results=roots / "results" / "experiments" / sl.HIST_VERSION, hist_reports=roots / "reports" / sl.HIST_VERSION,
                 launch_results=roots / "results" / "launch" / sl.LAUNCH_VERSION, launch_reports=roots / "reports" / "launch" / sl.LAUNCH_VERSION,
                 spec_dir=spec_dir, hist_contract_sha256=None, launch_contract_sha256=None, frozen_feature_sha256=None,
                 load_hist_inputs=load_hist_inputs, validate_launch_parent=validate_launch_parent, parent_cap_audit=cap_audit,
                 load_boundaries=lambda: arm.load_spatial_boundaries(base / "geom.shp"),
                 geometry_files=[p for p in base.glob("geom.*")], frozen_paths=lambda: list(frozen))
    # independently derived expectations (the gates must hold exactly)
    som_eval = cohort[cohort["eval_key"] & cohort["area_id"].isin(SOM)]
    ctx.expected = {"members": 3, "hist_eval_rows": len(som_eval),
                    "hist_eval_by_year": {int(y): int(n) for y, n in som_eval["year"].value_counts().sort_index().items()},
                    "hist_eval_areas_by_year": {int(y): int(g["area_id"].nunique()) for y, g in som_eval.groupby("year")}, "hist_eval_union_areas": 3,
                    "launch_fit_rows": int((fit["area_id"].isin(SOM)).sum()), "launch_fit_areas": 3, "launch_inference_areas": 2, "launch_excluded": [3],
                    "population": {"country": "Somalia", "raw": som_raw, "reference": ref, "cap_factor": 0.95 * ref / som_raw,
                                   "effective": round(som_raw * 0.95 * ref / som_raw, 2), "areas": 2}}
    return argparse.Namespace(ctx=ctx, data=data, cohort=cohort, lbase=lbase, parent_fit=fit, base=base, frozen=frozen)


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    code_before = frozen_code_hashes()
    w = build_world(tmp_path_factory.mktemp("somalia_local"))
    w.pilot = sl.train_main(w.ctx, pilot=True)
    w.pilot_meta = json.loads((sl.hist_run_dir(w.ctx, cpf.BASELINE_ARM, 0) / "run_metadata.json").read_text())
    w.pilot_launch_exists = Path(w.ctx.launch_results / "inputs").exists()
    w.train = sl.train_main(w.ctx, pilot=False)
    w.report = {"historical": sl.hist_report(w.ctx), "launch": sl.launch_report(w.ctx)}
    w.verify = sl.verify_main(w.ctx)
    w.code_before = code_before
    return w


# --------------------------------------------------------------------------- membership and scope


def test_membership_is_exact_iso3_without_name_fallback(tmp_path):
    lookup = pd.DataFrame({"area_id": [1, 2, 3, 4], "iso3": ["SOM", "SOM", "", "KEN"], "country": ["Somalia", "Somalia", "Somalia", "Kenya"]})
    lookup.to_csv(tmp_path / "l.csv", index=False)
    ctx = sl.Ctx(membership=tmp_path / "l.csv", expected={"members": 2})
    m = sl.load_membership(ctx)
    assert m["area_ids"] == [1, 2] and m["country"] == "Somalia"  # area 3 (name only, no ISO3) is not a member
    ctx.expected = {"members": 3}
    with pytest.raises(sl.LocalError, match="SOM members"):
        sl.load_membership(ctx)
    lookup.loc[1, "country"] = "Somaliland"
    lookup.to_csv(tmp_path / "l.csv", index=False)
    with pytest.raises(sl.LocalError, match="exactly the country name"):
        sl.load_membership(sl.Ctx(membership=tmp_path / "l.csv", expected=None))
    pd.concat([lookup, lookup.iloc[[0]]]).to_csv(tmp_path / "l.csv", index=False)
    with pytest.raises(sl.LocalError, match="duplicate"):
        sl.load_membership(sl.Ctx(membership=tmp_path / "l.csv", expected=None))


def test_local_roots_never_enter_parent_namespaces():
    for bad in (cl.RESULTS_ROOT / "x", sl.paths.RESULTS_DIR / "experiments" / cpf.VERSION / "runs", cl.INPUT_ROOT):
        with pytest.raises(sl.LocalError, match="parent namespace"):
            sl.assert_local_root(bad)
    for good in (sl.HIST_RESULTS, sl.HIST_REPORTS, sl.LAUNCH_RESULTS, sl.LAUNCH_REPORTS):
        assert sl.assert_local_root(good) == good


def test_global_origin_safe_cli_still_rejects_country_scopes():
    args = argparse.Namespace(country_iso3="SOM", region_scope=0, country_name=None)
    with pytest.raises(ValueError, match="global protocol"):
        sl.runner.load_origin_inputs(args)


def test_validate_only_writes_nothing_and_reports_local_fingerprints(tmp_path, capsys):
    w = build_world(tmp_path / "v", seed=11)
    before = {p: p.stat().st_mtime_ns for p in (tmp_path / "v").rglob("*")}
    assert sl.main(["--validate-only"], w.ctx) == 0
    assert {p: p.stat().st_mtime_ns for p in (tmp_path / "v").rglob("*")} == before
    out = json.loads(capsys.readouterr().out)
    assert not any(Path(r).exists() for r in w.ctx.roots()) and not (tmp_path / "v" / "out").exists()
    hist = out["historical"]["runs"]
    assert set(hist) == {sl.run_id(a, h) for a, h in sl.HIST_RUNS}
    assert len({r["local_fingerprint"] for r in hist.values()}) == 7 and "fit_run_fingerprints" in out["launch"]
    assert all(r["local_fingerprint"] != r["parent_fingerprint"] for r in hist.values())
    assert out["launch"]["checks"]["excluded_areas"] == [3] and out["launch"]["checks"]["inference_areas"] == 2


def test_cli_rejects_pilot_without_training():
    with pytest.raises(SystemExit):
        sl.parse_args(["--report", "--pilot"])


# --------------------------------------------------------------------------- historical stage


def test_localized_inputs_mask_fitting_and_evaluation_and_bind_membership(tmp_path):
    w = build_world(tmp_path / "m", seed=5)
    prep = sl.hist_prepare(w.ctx, write=False)
    args = sl.hist_args(w.ctx, cpf.BASELINE_ARM, 3)
    parent = w.ctx.load_hist_inputs(args)
    local = sl.hist_localize(w.ctx, prep, parent, cpf.BASELINE_ARM, 3)
    ids = parent["data"]["area_id"].to_numpy()
    assert set(ids[local["share_valid"]]) == set(SOM) and set(ids[local["eval_key"]]) == set(SOM)
    assert np.array_equal(local["share_valid"], parent["share_valid"] & np.isin(ids, SOM))  # complete, not a subset
    assert np.array_equal(local["eval_key"], parent["eval_key"] & np.isin(ids, SOM))
    assert local["fingerprint"] != parent["fingerprint"] and local["fingerprint_payload"]["parent_fingerprint"] == parent["fingerprint"]
    # a different membership is a different local manifest and fingerprint
    lk = pd.read_csv(w.ctx.membership)
    lk.loc[lk["area_id"] == 3, "iso3"] = "KEN"
    lk.loc[lk["area_id"] == 3, "country"] = "Kenya"
    lk.to_csv(tmp_path / "lk.csv", index=False)
    ctx2 = sl.Ctx(**{**w.ctx.__dict__, "membership": tmp_path / "lk.csv", "expected": None})
    prep2 = sl.hist_prepare(ctx2, write=False)
    assert prep2["sha256"] != prep["sha256"]
    assert sl.hist_localize(ctx2, prep2, parent, cpf.BASELINE_ARM, 3)["fingerprint"] != local["fingerprint"]


def test_pilot_fits_only_historical_h0_2022(world):
    assert world.pilot["historical"] == [{"run_id": "compact_baseline/0m", "status": "PARTIAL", "batches": [2022]}]
    assert world.pilot_meta["status"] == "PARTIAL" and [b["block_year"] for b in world.pilot_meta["batches"]] == [2022]
    assert not world.pilot_launch_exists


def test_full_historical_plan_complete_som_sets_cutoffs_weights_and_shared_h0(world):
    ctx = world.ctx
    assert [r["status"] for r in world.train["historical"]] == ["COMPLETE"] * 7
    assert not (ctx.hist_results / "runs" / cpf.ORACLE_ARM / "0m").exists()  # H0 shared: no oracle fit
    data, cohort = world.data, world.cohort
    ords = data["year"].to_numpy() * 12 + data["month"].to_numpy() - 1
    som = data["area_id"].isin(SOM).to_numpy()
    models = 0
    for arm, h in sl.HIST_RUNS:
        run = sl.hist_run_dir(ctx, arm, h)
        meta = json.loads((run / "run_metadata.json").read_text())
        assert meta["local_version"] == sl.HIST_VERSION and meta["parent_model_contract_version"] == cpf.VERSION and meta["scope"] == "SOM"
        assert meta["features"] == hist_features(arm, h)
        for year in osf.TARGET_YEARS:
            b = run / "batches" / str(year)
            fk = pd.read_csv(b / "fit_keys.csv.gz", float_precision="round_trip")
            cutoff = year * 12 - max(h, 1)
            want = data.loc[som & cohort["share_valid"].to_numpy() & (ords <= cutoff), KEYS].reset_index(drop=True)
            assert fk[KEYS].equals(want)  # every valid SOM label within the cutoff, nothing else
            age = (year * 12 - h) - (fk["year"] * 12 + fk["month"] - 1)
            assert np.array_equal(fk["age_months"], age) and np.allclose(fk["sample_weight"], 0.5 ** (age / 24.0), rtol=0, atol=1e-15)
            pred = pd.read_csv(b / "predictions.csv")
            want_eval = cohort.loc[cohort["eval_key"] & cohort["area_id"].isin(SOM) & (cohort["year"] == year), KEYS].reset_index(drop=True)
            assert pred[KEYS].equals(want_eval)
            models += len(list(b.glob("model_*.ubj")))
    assert models == 112
    # resume: the pilot batch was verified, not refit, inside the complete run
    assert json.loads((sl.hist_run_dir(ctx, cpf.BASELINE_ARM, 0) / "batches" / "2022" / "batch_record.json").read_text()) == world.pilot_meta["batches"][0]


def test_historical_report_has_som_metrics_undefined_reasons_and_deltas(world):
    rep = world.ctx.hist_results / "report"
    metrics = pd.read_csv(rep / "som_metrics_long.csv", keep_default_na=False, na_values=[""])
    assert set(metrics["scope"]) == {"SOM"} and metrics["region"].isna().all()
    assert len(metrics) == 7 * 5 * 8 and set(metrics["period"].astype(str)) == {"2022", "2023", "2024", "2025", "pooled"}
    undefined = metrics[metrics["value"].isna()]
    assert len(undefined) and undefined["reason"].str.len().gt(0).all()
    assert set(undefined[undefined["period"].astype(str) == "2024"]["metric"]) >= {"sensitivity_phase3plus", "r2_phase3plus"}
    deltas = pd.read_csv(rep / "som_oracle_minus_baseline_deltas.csv", keep_default_na=False, na_values=[""])
    h0 = deltas[deltas["horizon"] == 0]
    assert len(h0) == 5 * 8 and (h0["delta"].dropna() == 0).all() and set(deltas["horizon"]) == {0, 3, 6, 12}
    book = pd.read_csv(world.ctx.hist_reports / "model_run_codebook" / "IPCCH_compact_climate_weather_oracle_somalia_local_model_run_codebook_en.csv",
                       encoding="utf-8-sig")
    assert book["predictor"].tolist() == BASE_FEATS + ["o1", "o2"] and (book["model_scope"] == "Somalia local").all()
    assert (book["limitations"] == "Proxy month.").all()  # obsolete expected-only sentence removed, scientific limitation kept


# --------------------------------------------------------------------------- launch stage


def test_launch_projections_fits_population_coverage_and_scope(world):
    ctx = world.ctx
    local = json.loads((ctx.launch_results / "inputs" / f"{sl.LAUNCH_VERSION}_manifest.json").read_text())
    assert local["version"] == sl.LAUNCH_VERSION and local["parent_model_contract_version"] == cl.VERSION and local["scope"] == "SOM"
    want_fit = world.parent_fit[world.parent_fit["area_id"].isin(SOM)].reset_index(drop=True)
    for arm, h in sl.LAUNCH_RUNS:
        rid = sl.run_id(arm, h)
        sel = pd.read_csv(local["runs"][rid]["fit_selection"]["path"], float_precision="round_trip")
        assert cl.same_frame(sel, want_fit)  # complete SOM fitting set, exact values
        run = sl.launch_run_dir(ctx, arm, h)
        meta = json.loads((run / "run_metadata.json").read_text())
        assert meta["input_manifest"] == str(ctx.launch_results / "inputs" / f"{sl.LAUNCH_VERSION}_manifest.json")
        pred = pd.read_csv(run / "predictions_raw.csv")
        assert pred["area_id"].tolist() == [1, 2] and len(list(run.glob("model_*.ubj"))) == 4
    scope = json.loads((ctx.launch_results / "scope" / "run_scope.json").read_text())
    assert len(scope["runs"]) == 5 and scope["local_manifest"]["sha256"] == sha(ctx.launch_results / "inputs" / f"{sl.LAUNCH_VERSION}_manifest.json")
    cov = pd.read_csv(local["ledgers"]["som_launch_coverage"]["path"])
    assert cov.set_index("area_id").loc[3, "launch_status"].startswith("outside launch coverage") and cov["historical_eval_keys"].gt(0).all()
    pop = pd.read_csv(local["ledgers"]["population"]["path"])
    assert pop["area_id"].tolist() == [1, 2]  # area 3's population is not invented
    cap = pd.read_csv(local["ledgers"]["country_population_cap_audit_som"]["path"], keep_default_na=False)
    assert cap["country"].tolist() == ["Somalia"] and cap["cap_factor"].iloc[0] == pytest.approx(0.57, abs=1e-15)


def test_launch_population_tables_and_shared_h0_zero_differences(world):
    pop_dir = world.ctx.launch_results / "population"
    som = pd.read_csv(pop_dir / "som_population_summary.csv")
    assert len(som) == 6 and set(som["country"]) == {"Somalia"} and (som["n_areas"] == 2).all() and (som["population_raw"] == 1000.0).all()
    assert np.allclose(som["population_effective"], 570.0) and (som["n_zero_population_areas"] == 1).all()
    assert np.allclose(som[[f"share_effective_phase{k}" for k in range(1, 6)]].sum(axis=1), 1.0)
    diff = pd.read_csv(pop_dir / "som_population_paired_differences.csv")
    h0 = diff[diff["horizon"] == 0]
    assert (h0[[c for c in diff.columns if c.startswith("delta_") and c != "delta_status"]].to_numpy() == 0).all()
    assert set(diff["scope"]) == {"SOM"}


def test_seven_som_maps_with_complete_keyed_records(world):
    figs = sorted(p.name for p in (world.ctx.launch_reports / "figures").glob("*.png"))
    assert len(figs) == 7 and "p3plus_share_comparison_2x3.png" in figs and "p3plus_share_difference_1x2.png" in figs
    meta = json.loads((world.ctx.launch_results / "visualizations" / "figure_metadata.json").read_text())
    assert meta["scope"] == "SOM" and all(e["mapped_areas"] == 2 for e in meta["figures"].values())
    book = pd.read_csv(world.ctx.launch_reports / "model_run_codebook_en.csv", encoding="utf-8-sig", keep_default_na=False)
    assert not book["limitations"].str.contains("expected input").any() and book["training_source"].str.startswith("training_source").all()


# --------------------------------------------------------------------------- verification, resume and tamper detection


def test_independent_verification_passes_on_the_complete_fixed_plan(world):
    v = world.verify
    assert v["passed"], (v["historical"]["problems"][:5], v["launch"]["problems"][:5], v["frozen_problems"])
    assert v["historical"]["checks"]["batches"] == 28 and v["historical"]["checks"]["models_reloaded"] == 112
    assert v["launch"]["checks"]["models_reloaded"] == 20 and v["historical"]["checks"]["max_model_replay_abs_diff"] <= 1e-6
    assert v["historical"]["checks"]["metric_cells_replayed"] == 7 * 5 * 8 and v["historical"]["checks"]["delta_cells_replayed"] == 4 * 5 * 8
    assert (world.ctx.hist_results / "verification" / "verification.json").exists() and (world.ctx.launch_results / "verification.json").exists()


def test_resume_verifies_without_refit_and_rejects_changed_inputs(world, tmp_path):
    ctx = world.ctx
    stamp = {p: p.stat().st_mtime_ns for p in ctx.launch_results.rglob("model_*.ubj")}
    again = sl.train_main(ctx, pilot=False)
    assert [r["status"] for r in again["historical"]] == ["COMPLETE"] * 7
    assert {p: p.stat().st_mtime_ns for p in ctx.launch_results.rglob("model_*.ubj")} == stamp
    # changed membership -> different immutable local inputs -> refuse to resume into the same root
    lk = pd.read_csv(ctx.membership, keep_default_na=False)
    lk = lk[lk["area_id"] != 2]
    lk.to_csv(tmp_path / "lk.csv", index=False)
    ctx2 = sl.Ctx(**{**ctx.__dict__, "membership": tmp_path / "lk.csv", "expected": None})
    with pytest.raises(sl.LocalError, match="different bytes"):
        sl.train_main(ctx2, pilot=False)
    # a changed batch artifact is never resumed
    batch = sl.hist_run_dir(ctx, cpf.BASELINE_ARM, 3) / "batches" / "2023"
    meta = json.loads((sl.hist_run_dir(ctx, cpf.BASELINE_ARM, 3) / "run_metadata.json").read_text())
    pred = batch / "predictions.csv"
    original = pred.read_bytes()
    try:
        pred.write_bytes(original + b"\n")
        with pytest.raises(ValueError, match="changed since its batch record"):
            sl.runner.verify_batch(batch, meta["fingerprint"])
    finally:
        pred.write_bytes(original)


def test_verifier_detects_tampering_missing_outputs_and_frozen_changes(world):
    ctx = world.ctx
    table = ctx.launch_results / "population" / "som_population_summary.csv"
    frozen = Path(world.frozen[-1][1])  # an unbound accepted output: only the frozen inventory can notice it
    report_md = ctx.hist_reports / "report.md"
    figmeta = ctx.launch_results / "visualizations" / "figure_metadata.json"
    metrics = ctx.hist_results / "report" / "som_metrics_long.csv"
    saved = {p: p.read_bytes() for p in (table, frozen, report_md, figmeta, metrics)}
    try:
        frame = pd.read_csv(table, float_precision="round_trip", keep_default_na=False, na_values=[""])
        frame.loc[0, "count_effective_p3plus"] += 1.0
        frame.to_csv(table, index=False, float_format="%.17g")
        frozen.write_bytes(saved[frozen] + b" ")
        report_md.unlink()
        meta = json.loads(saved[figmeta])
        meta["figures"].pop("p3plus_share_difference_1x2")
        figmeta.write_text(json.dumps(meta))
        m = pd.read_csv(metrics, keep_default_na=False, na_values=[""])
        idx = m.index[m["value"].isna()][0]
        m.loc[idx, "reason"] = "fabricated reason"
        m.to_csv(metrics, index=False, float_format="%.17g")
        v = sl.verify_main(ctx)
        hist, launch = v["historical"]["problems"], v["launch"]["problems"]
        assert not v["passed"]
        assert any("count_effective_p3plus" in p for p in launch)
        assert any("mandatory report outputs missing" in p and "report.md" in p for p in hist)
        assert any("not exactly the seven maps" in p for p in launch)
        assert v["frozen_problems"] and v["frozen"]["frozen_files_changed"] == 1
        # the undefined reason is checked once the report.md is restored
        report_md.write_bytes(saved[report_md])
        v = sl.verify_main(ctx)
        assert any("fabricated reason" in p for p in v["historical"]["problems"])
    finally:
        for path, data in saved.items():
            path.write_bytes(data)


def test_replayed_classes_must_match_exactly_across_the_threshold():
    pred = pd.DataFrame({"phase2_pred": [0.9], "phase3_pred": [0.19999995], "phase4_pred": [0.0], "phase5_pred": [0.0]})
    pred["overall_phase_pred"] = sl.legacy.classes(pred, 0.2)
    assert pred["overall_phase_pred"].tolist() == [2]
    ok = {c: pred[c].to_numpy() for c in osf.PRED_COLUMNS}
    assert sl.replayed_class_problems("x", pred, ok, 0.2) == []
    crossed = dict(ok, phase3_pred=np.array([0.20000005]))  # within the 1e-6 raw tolerance, but class 3
    assert any("reloaded predictions" in p for p in sl.replayed_class_problems("x", pred, crossed, 0.2))
    assert sl.replayed_class_problems("x", pred, {"phase2_pred": ok["phase2_pred"]}, 0.2)


def test_frozen_snapshot_must_be_complete_and_unchanged(world, tmp_path):
    ctx = world.ctx
    problems, checks = [], {}
    sl.frozen_check(ctx, problems, checks)
    assert problems == [] and checks["frozen_files_checked"] == len(world.frozen)
    extra = tmp_path / "new_old_output.txt"
    extra.write_text("x")
    added = sl.Ctx(**{**ctx.__dict__, "frozen_paths": lambda: list(world.frozen) + [("old_results", extra)]})
    problems = []
    sl.frozen_check(added, problems, {})
    assert any("gained files" in p for p in problems)
    snaps = [ctx.hist_results / "preflight" / "frozen_inventory_before.csv", ctx.launch_results / "preflight" / "frozen_inventory_before.csv"]
    saved = {p: p.read_bytes() for p in snaps}
    try:
        for p in snaps:
            p.write_text("role,path,bytes,sha256\n")
        problems = []
        sl.frozen_check(ctx, problems, {})
        assert any("empty" in p for p in problems)
    finally:
        for p, data in saved.items():
            p.write_bytes(data)


def test_incomplete_batch_directory_is_rejected_and_preserved(tmp_path):
    w = build_world(tmp_path / "b", seed=3)
    batch = sl.hist_run_dir(w.ctx, cpf.BASELINE_ARM, 0) / "batches" / "2022"
    batch.mkdir(parents=True)
    (batch / "model_phase2_worse.ubj").write_bytes(b"partial")
    with pytest.raises(sl.LocalError, match="no batch record"):
        sl.train_main(w.ctx, pilot=True)
    assert (batch / "model_phase2_worse.ubj").read_bytes() == b"partial" and not (batch / "predictions.csv").exists()


def test_archived_task_uses_manifest_bound_spec_copies(world):
    ctx = world.ctx
    hist_sha = sha(sl.hist_manifest_path(ctx))
    launch_sha = sha(sl.launch_manifest_path(ctx))
    archived = ctx.spec_dir.with_name("archived_task_spec")
    copy = ctx.hist_results / "inputs" / "approved_spec" / "prd.md"
    original = copy.read_bytes()
    ctx.spec_dir.rename(archived)
    try:
        assert sl.hist_prepare(ctx, write=False)["sha256"] == hist_sha  # same identity, no archive path in it
        assert sl.launch_prepare(ctx, write=False)["sha256"] == launch_sha
        v = sl.verify_main(ctx)
        assert v["passed"], (v["historical"]["problems"][:3], v["launch"]["problems"][:3])
        copy.write_bytes(original + b"edited")
        with pytest.raises(sl.LocalError, match="differs from its local manifest hash"):
            sl.hist_prepare(ctx, write=False)
    finally:
        copy.write_bytes(original)
        archived.rename(ctx.spec_dir)


def test_frozen_global_code_is_untouched(world):
    assert frozen_code_hashes() == world.code_before
    assert all(sha(p) == d for p, d in world.code_before.items())
