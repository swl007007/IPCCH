from __future__ import annotations

from pathlib import Path

import pandas as pd

from ipcch import launch_nowcasting as ln
from ipcch import paths


def _config(**kw) -> ln.LaunchConfig:
    defaults = dict(comprehensive_source=Path("dummy.csv"))
    defaults.update(kw)
    return ln.LaunchConfig(**defaults)


def _pred_validated() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "area_id": ["A", "B"],
            "year": [2026, 2026],
            "month": [4, 4],
            "phase2_worse_pred": [0.4, 0.1],
            "phase3_worse_pred": [0.2, 0.0],
            "phase4_worse_pred": [0.0, 0.0],
            "phase5_worse_pred": [0.0, 0.0],
        }
    )


def test_scope0_prediction_output_adds_scope_period_metadata_without_replacing_existing_fields():
    cfg = _config(scope_months=0)
    out = ln.assemble_prediction_output(_pred_validated(), pd.Series([3, 1]), cfg)

    for col in ["launch_month", "model_workflow", "scale", "threshold", "training_cutoff", "comprehensive_source", "run_id"]:
        assert col in out.columns
    assert out["scope_months"].tolist() == [0, 0]
    assert out["feature_period"].tolist() == ["2026-04", "2026-04"]
    assert out["target_period"].tolist() == ["2026-04", "2026-04"]


def test_scope0_run_summary_adds_scope_period_metadata_without_replacing_output_paths():
    cfg = _config(scope_months=0, out_root=paths.RESULTS_DIR / "launch" / "_pytest_scope0", report_root=paths.REPORTS_DIR / "launch" / "_pytest_scope0")
    layout = ln.resolve_output_layout(cfg)
    summary = ln.build_run_summary(cfg, layout, {"training_rows": 10}, {"launch_month_area_count": 2}, ["feat"], {})

    assert summary["scope_months"] == 0
    assert summary["feature_period"] == "2026-04"
    assert summary["target_period"] == "2026-04"
    assert summary["output_paths"]["predictions"].endswith("predictions_2026_04_all_area_id.csv")


def test_model_aligned_xtest_excludes_scope_months_metadata(tmp_path):
    cfg = _config(scope_months=3, out_root=paths.RESULTS_DIR / "launch" / "_pytest_scope_xtest", report_root=paths.REPORTS_DIR / "launch" / "_pytest_scope_xtest")
    layout = ln.OutputLayout(
        out_root=tmp_path,
        report_root=tmp_path,
        predictions_csv=tmp_path / "predictions.csv",
        run_summary_json=tmp_path / "run_summary.json",
        config_json=tmp_path / "config.json",
        input_validation_json=tmp_path / "input_validation.json",
        training_summary_csv=tmp_path / "training.csv",
        feature_schema_csv=tmp_path / "feature_schema.csv",
        xtest_coverage_csv=tmp_path / "coverage.csv",
        eligibility_csv=tmp_path / "eligibility.csv",
        xtest_aligned_csv=tmp_path / "xtest_aligned.csv",
        prediction_distribution_csv=tmp_path / "pred_dist.csv",
        prediction_validation_json=tmp_path / "pred_validation.json",
        predicted_phase_distribution_csv=tmp_path / "phase_dist.csv",
        model_artifacts_dir=tmp_path / "models",
        comparison_dir=tmp_path / "comparison",
        viz_results_dir=tmp_path / "viz_results",
        viz_report_dir=tmp_path / "viz_report",
    )
    pred_out = ln.assemble_prediction_output(_pred_validated(), pd.Series([3, 1]), cfg)
    xtest = pd.DataFrame({"area_id": ["A", "B"], "feat": [1.0, 2.0], "scope_months": [3, 3]})

    ln.write_prediction_outputs(layout, pred_out, xtest, ["feat"], {"dedup": {}}, {}, overwrite=True)

    aligned = pd.read_csv(layout.xtest_aligned_csv)
    assert aligned.columns.tolist() == ["area_id", "feat"]


def test_scope0_legacy_output_paths_remain_available():
    cfg = _config(scope_months=0, out_root=paths.RESULTS_DIR / "launch" / "nowcasting_2026_04", report_root=paths.REPORTS_DIR / "launch" / "nowcasting_2026_04")
    layout = ln.resolve_output_layout(cfg)
    assert layout.predictions_csv == cfg.out_root / "predictions_2026_04_all_area_id.csv"
    assert layout.run_summary_json == cfg.out_root / "run_summary.json"


def test_scope3_scope6_and_scope12_outputs_compute_future_target_periods_without_future_actuals():
    for scope, expected in [(3, "2026-07"), (6, "2026-10"), (12, "2027-04")]:
        cfg = _config(scope_months=scope)
        out = ln.assemble_prediction_output(_pred_validated(), pd.Series([3, 1]), cfg)
        assert out["scope_months"].tolist() == [scope, scope]
        assert out["feature_period"].tolist() == ["2026-04", "2026-04"]
        assert out["target_period"].tolist() == [expected, expected]


def test_missing_future_target_or_actual_rows_are_not_missing_prediction_records(comprehensive_frame):
    cfg = _config(scope_months=3)
    prepared = ln.prepare_source(comprehensive_frame)
    launch, coverage = ln.build_launch_prediction_frame(prepared, cfg)
    assert coverage["launch_month_area_count"] == 5
    assert coverage["target_period"] == "2026-07"
    assert launch["overall_phase"].isna().all()


def test_scope3_scope6_and_scope12_run_summary_include_scope_period_metadata():
    for scope, expected in [(3, "2026-07"), (6, "2026-10"), (12, "2027-04")]:
        cfg = _config(scope_months=scope, out_root=paths.RESULTS_DIR / "launch" / f"_pytest_scope{scope}", report_root=paths.REPORTS_DIR / "launch" / f"_pytest_scope{scope}")
        layout = ln.resolve_output_layout(cfg)
        summary = ln.build_run_summary(cfg, layout, {"training_rows": 10}, {"launch_month_area_count": 2}, ["feat"], {})
        assert summary["scope_months"] == scope
        assert summary["feature_period"] == "2026-04"
        assert summary["target_period"] == expected


def test_scope_output_paths_coexist_without_replacing_scope0():
    root = paths.RESULTS_DIR / "launch" / "nowcasting_2026_04"
    report_root = paths.REPORTS_DIR / "launch" / "nowcasting_2026_04"
    scope0 = ln.resolve_output_layout(_config(scope_months=0, out_root=root, report_root=report_root))
    scope3 = ln.resolve_output_layout(_config(scope_months=3, out_root=root, report_root=report_root))
    scope6 = ln.resolve_output_layout(_config(scope_months=6, out_root=root, report_root=report_root))
    scope12 = ln.resolve_output_layout(_config(scope_months=12, out_root=root, report_root=report_root))

    assert scope0.predictions_csv == root / "predictions_2026_04_all_area_id.csv"
    assert scope3.predictions_csv != scope0.predictions_csv
    assert scope6.predictions_csv != scope0.predictions_csv
    assert scope12.predictions_csv != scope0.predictions_csv
    assert len({scope3.predictions_csv, scope6.predictions_csv, scope12.predictions_csv}) == 3
    assert "scope_3m" in str(scope3.predictions_csv)
    assert "scope_6m" in str(scope6.predictions_csv)
    assert "scope_12m" in str(scope12.predictions_csv)


def test_scope_output_conflict_targets_are_scope_qualified_for_forward_scopes():
    root = paths.RESULTS_DIR / "launch" / "nowcasting_2026_04"
    report_root = paths.REPORTS_DIR / "launch" / "nowcasting_2026_04"
    paths_by_scope = {
        scope: ln.resolve_output_layout(_config(scope_months=scope, out_root=root, report_root=report_root)).predictions_csv
        for scope in (0, 3, 6, 12)
    }
    assert len(set(paths_by_scope.values())) == 4
