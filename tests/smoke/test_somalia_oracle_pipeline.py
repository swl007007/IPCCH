"""Synthetic end-to-end smoke run of the Somalia oracle CLI (tiny XGBoost fits)."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from ipcch.somalia_oracle import PERCENT_COLUMNS, V2_FEATURES
from ipcch.somalia_oracle import modeling as md

MONTHS = [(2022, 7), (2022, 10), (2023, 1), (2023, 3), (2023, 8), (2024, 1), (2024, 7), (2025, 4), (2025, 10), (2026, 4)]


def _shares(rng):
    p = rng.dirichlet([2, 2, 1.5, 0.7, 0.2])
    return p


def _build_inputs(tmp_path):
    rng = np.random.default_rng(3)
    areas = list(range(1600, 1612))
    lookup = pd.DataFrame({"area_id": areas + [9], "iso3": ["SOM"] * len(areas) + ["KEN"], "country": ["Somalia"] * len(areas) + ["Kenya"], "country_code": "SO", "country_en": ["Somalia"] * len(areas) + ["Kenya"]})
    raw_rows, fs_rows = [], []
    for area in areas + [9]:
        for year in range(2021, 2027):
            for month in range(1, 13):
                if (year, month) > (2026, 4):
                    continue
                labeled = (year, month) in MONTHS
                p = _shares(rng) if labeled else None
                phase = (3.0 if p[2:].sum() >= 0.2 else 2.0) if labeled else np.nan
                rain, temp = float(rng.random()), float(295 + rng.random())
                raw_rows.append({"admin_code": area, "ISO3": "SOM" if area != 9 else "KEN", "year": year, "month": month, "overall_phase": phase, **{c: (p[i] if labeled else np.nan) for i, c in enumerate(PERCENT_COLUMNS)}, "Rainf_f_tavg_mean": rain, "Tair_f_tavg_mean": temp})
                if labeled:
                    fs_rows.append({"area_id": area, "year": year, "month": month, "overall_phase": phase, **{c: p[i] for i, c in enumerate(PERCENT_COLUMNS)}, "estimated_population": 1000.0, "static_x": float(area % 3), "overall_phase_lag1": 2.0})
    raw = pd.DataFrame(raw_rows)
    fs = pd.DataFrame(fs_rows)
    paths = {}
    fs_specs = {"fs0": ("feat__l0_s0", 0), "fs1": ("feat__l3_s3", 3), "fs2": ("feat__l6_s6", 6), "fs3": ("feat__l12", 12)}
    for name, (column, lag) in fs_specs.items():
        frame = fs.copy()
        frame[column] = rng.normal(size=len(frame)) + frame["phase3_percent"] * 3
        paths[name] = tmp_path / f"{name}.csv"
        frame.to_csv(paths[name], index=False)
    paths["raw"] = tmp_path / "raw.csv"
    raw.to_csv(paths["raw"], index=False)
    paths["lookup"] = tmp_path / "lookup.csv"
    lookup.to_csv(paths["lookup"], index=False)
    v2_rows = []
    for area in areas:
        for year in range(2022, 2027):
            for season, start, end in (("s1", f"{year}-04-10", f"{year}-08-10"), ("s2", f"{year - 1}-09-20", f"{year}-02-20")):
                row = {"admin_code": area, "season_year": year, "season": season, "gs_start_date": start, "gs_end_date_exclusive": end, "gs_calendar_valid": 1, "gs_calendar_quality": "high", "gs_available_window_days": 120, "gs_duration_recalculated_days": 120}
                row.update({c: float(rng.normal()) for c in V2_FEATURES})
                v2_rows.append(row)
    paths["v2"] = tmp_path / "v2.csv"
    pd.DataFrame(v2_rows).to_csv(paths["v2"], index=False)
    return paths


@pytest.fixture
def tiny_candidates(tmp_path, monkeypatch):
    config = md.load_candidates()
    for candidate in config["candidates"]:
        candidate["common"]["n_estimators"] = 3
    path = tmp_path / "candidates.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    original = md.load_candidates
    monkeypatch.setattr(md, "load_candidates", lambda p=path: original(p))
    return path


def test_cli_end_to_end_synthetic(tmp_path, tiny_candidates):
    from importlib import util

    spec = util.spec_from_file_location("runner", str(md.paths.PROJECT_ROOT / "scripts" / "modeling" / "run_somalia_oracle_experiment.py"))
    runner = util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    inputs = _build_inputs(tmp_path)
    out, report = tmp_path / "out", tmp_path / "report"
    argv = ["--out-dir", str(out), "--report-dir", str(report), "--workers", "1", "--skip-input-hash"]
    for name, path in inputs.items():
        argv += [f"--{name}-path", str(path)]
    assert runner.main(argv) == 0

    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["mode"] == "full" and "overall_phase_lag1" in manifest["notes"]["blocked_base_features"]
    schema = json.loads((out / "features" / "feature_schema.json").read_text())
    for key, columns in schema.items():
        assert "overall_phase_lag1" not in columns and "estimated_population" not in columns
    assert schema["h00_B"] == schema["h00_C"]
    assert len(schema["h03_C"]) - len(schema["h03_B"]) == 6 and len(schema["h12_C"]) - len(schema["h12_B"]) == 12

    predictions = pd.read_csv(out / "predictions" / "predictions.csv.gz")
    assert set(predictions["arm"]) == {"A", "B", "C", "D"}
    h0 = predictions.loc[predictions["horizon"] == 0].pivot_table(index=["job_id", "area_id", "target_ord"], columns="arm", values="q3_pred")
    np.testing.assert_array_equal(h0["B"].to_numpy(), h0["C"].to_numpy())
    status = pd.read_csv(out / "fits" / "arm_job_status.csv")
    assert (status.loc[status["reused_from"].notna(), "arm"] == "C").all()

    fits = pd.read_csv(out / "fits" / "final_fit_ledger.csv.gz")
    jobs = pd.read_csv(out / "ledgers" / "jobs.csv").set_index("job_id")
    merged = fits.join(jobs[["origin_ord", "test_year"]], on="job_id")
    assert (merged["target_ord"] <= merged["origin_ord"]).all()
    assert (merged["target_ord"] // 12 < merged["test_year"]).all()
    folds = pd.read_csv(out / "fits" / "inner_folds.csv")
    supported = folds.loc[folds["supported"]]
    assert (supported["fit_max_target_ord"] <= supported["fit_label_cutoff_ord"]).all()
    assert (supported["fit_label_cutoff_ord"] < supported["validation_ord"]).all()

    metrics = pd.read_csv(out / "metrics" / "metrics.csv")
    contrasts = pd.read_csv(out / "metrics" / "contrasts.csv")
    assert {"primary", "persistence_subset", "wider_labeled"} <= set(metrics["cohort"])
    assert {"always_crisis", "persistence"} <= set(metrics["specification"])
    h0c = contrasts.loc[(contrasts["horizon"] == 0) & (contrasts["contrast"] == "C-B") & contrasts["point_delta_f2"].notna()]
    assert (h0c["point_delta_f2"] == 0).all()
    draws = np.load(out / "metrics" / "bootstrap_draws.npz")
    assert any(key.endswith("__multiplicities") for key in draws.files)
    assert (report / "metrics.csv").exists()

    # Replay must fail when a frozen-cohort prediction is missing (close-audit A01).
    from importlib import util as _util

    replay_spec = _util.spec_from_file_location("replay", str(md.paths.PROJECT_ROOT / "scripts" / "postprocessing" / "replay_somalia_oracle.py"))
    replay_mod = _util.module_from_spec(replay_spec)
    replay_spec.loader.exec_module(replay_mod)
    checks, *_ = replay_mod.replay(out)
    assert checks["pass"].all()
    dropped = predictions.drop(index=predictions.index[(predictions["arm"] == "A")][:1])
    bad_checks, *_ = replay_mod.replay(out, predictions_override=dropped)
    assert not bad_checks.loc[bad_checks["check"] == "prediction_coverage", "pass"].all()
