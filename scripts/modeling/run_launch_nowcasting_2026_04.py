#!/usr/bin/env python
"""CLI: April 2026 global nowcasting launch (comprehensive-CSV fallback).

Runs from the repository root. See specs/004-launch-2026-04-nowcasting-fallback/contracts/cli.md
for the complete, authoritative flag list. Heavy Mode-1 training is gated behind
--approve-training and is never executed without it.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Self-locating PROJECT_ROOT bootstrap so the script runs from the repo root
# without requiring an editable install.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import pandas as pd  # noqa: E402

from ipcch import launch_nowcasting as ln  # noqa: E402
from ipcch import launch_comparison as lc  # noqa: E402


def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="April 2026 global nowcasting launch (comprehensive-CSV fallback).")
    # Core / paths
    p.add_argument("--comprehensive-source", help="Comprehensive feature CSV (training + X_test). Default resolves the workspace key from configs/paths.local.json.")
    p.add_argument("--launch-month", default=ln.DEFAULT_LAUNCH_MONTH, help="Launch feature month YYYY-MM. Default 2026-04.")
    p.add_argument("--scope", type=int, choices=ln.ALLOWED_SCOPE_MONTHS, default=0, help="Forecast scope in calendar months between feature period and target period.")
    p.add_argument("--scale", default=ln.DEFAULT_SCALE, choices=["global"], help="Only 'global' is supported.")
    p.add_argument("--training-cutoff", default=ln.DEFAULT_TRAINING_CUTOFF, help="Train strictly before this date (YYYY-MM-DD).")
    p.add_argument("--out-root", help="Machine-readable output root.")
    p.add_argument("--report-root", help="Human-readable report root.")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--dedup-rule", choices=["latest-date"], help="Resolve duplicate launch-month area_id rows deterministically (requires a date column). Absent => hard-stop.")
    # Canonical model settings
    p.add_argument("--hyperparameter-set", choices=["canonical", "custom"], default="canonical")
    p.add_argument("--hyperparameters", help="Phase 2/4/5 hyperparameter JSON override.")
    p.add_argument("--hyperparameters-p3", help="Phase 3 hyperparameter JSON override.")
    id_group = p.add_mutually_exclusive_group()
    id_group.add_argument("--add-identifier-features", dest="add_identifier_features", action="store_true", default=True)
    id_group.add_argument("--no-identifier-features", dest="add_identifier_features", action="store_false")
    p.add_argument("--identifier-source", help="Identifier lookup CSV (admin_code/year/month/lat/lon). Used only when identifier-derived columns are absent.")
    p.add_argument("--allow-missing-identifier-features", action="store_true")
    p.add_argument("--half-life-months", type=float, default=ln.fwd.DEFAULT_HALF_LIFE_MONTHS)
    p.add_argument("--no-time-decay", dest="use_time_decay", action="store_false", default=True)
    p.add_argument("--threshold", type=float, default=ln.CANONICAL_THRESHOLD, help="Fixed/informational; only 0.2 accepted.")
    p.add_argument("--drop-nonfinite-predictions", action="store_true")
    # Execution modes
    p.add_argument("--skip-training", action="store_true", help="Mode 2: requires --model-artifact-dir.")
    p.add_argument("--model-artifact-dir", help="Directory with fitted model artifacts (Mode 2).")
    p.add_argument("--skip-prediction", action="store_true", help="Mode 3: requires --predictions.")
    p.add_argument("--predictions", help="Supplied April prediction CSV (Mode 3).")
    # Comparison & visualization
    p.add_argument("--actual-source", help="April 2026 actual labels CSV (post-prediction comparison only).")
    p.add_argument("--actual-crisis-flag", help="Documented actual-crisis boolean column (else overall_phase>=3).")
    p.add_argument("--spatial-path", help="Spatial boundary file for the two-panel map.")
    map_group = p.add_mutually_exclusive_group()
    map_group.add_argument("--make-map", dest="make_map", action="store_true", default=None)
    map_group.add_argument("--no-map", dest="make_map", action="store_false")
    p.add_argument("--no-basemap", action="store_true")
    p.add_argument("--overwrite", action="store_true")
    # Safety
    p.add_argument("--validate-only", "--dry-run", dest="validate_only", action="store_true")
    p.add_argument("--approve-training", action="store_true", help="Required to run Mode-1 heavy training.")
    p.add_argument("--sample-rows", type=int, help="Limit loaded rows (lightweight validation).")
    return p.parse_args(argv)


def _resolve_mode(args) -> str:
    if args.skip_prediction:
        return "report_from_supplied_predictions"
    if args.skip_training:
        return "predict_with_supplied_models"
    return "train_and_predict"


def build_config(args) -> ln.LaunchConfig:
    if abs(float(args.threshold) - ln.CANONICAL_THRESHOLD) > 1e-12:
        raise ln.LaunchError("This launch is constitutionally fixed to canonical th=0.2; --threshold cannot be changed.")
    mode = _resolve_mode(args)
    source = None
    if mode != "report_from_supplied_predictions":
        source = ln.resolve_comprehensive_source(args.comprehensive_source)
    from ipcch import paths
    return ln.LaunchConfig(
        comprehensive_source=source or Path(args.predictions or "."),
        launch_month=args.launch_month,
        scale=args.scale,
        training_cutoff=args.training_cutoff,
        threshold=ln.CANONICAL_THRESHOLD,
        scope_months=args.scope,
        out_root=Path(args.out_root) if args.out_root else (paths.RESULTS_DIR / "launch" / "nowcasting_2026_04"),
        report_root=Path(args.report_root) if args.report_root else (paths.REPORTS_DIR / "launch" / "nowcasting_2026_04"),
        seed=args.seed,
        add_identifier_features=args.add_identifier_features,
        allow_missing_identifier_features=args.allow_missing_identifier_features,
        identifier_source=Path(args.identifier_source) if args.identifier_source else None,
        half_life_months=args.half_life_months,
        use_time_decay=args.use_time_decay,
        hyperparameter_set=args.hyperparameter_set,
        hyperparameters_path=Path(args.hyperparameters) if args.hyperparameters else None,
        hyperparameters_p3_path=Path(args.hyperparameters_p3) if args.hyperparameters_p3 else None,
        dedup_rule=args.dedup_rule,
        drop_nonfinite_predictions=args.drop_nonfinite_predictions,
        execution_mode=mode,
    )


def run(args) -> int:
    mode = _resolve_mode(args)
    # Mode-required artifacts
    if args.skip_training and not args.model_artifact_dir:
        raise ln.LaunchError("--skip-training (Mode 2) requires --model-artifact-dir <dir>.")
    if args.skip_prediction and not args.predictions:
        raise ln.LaunchError("--skip-prediction (Mode 3) requires --predictions <csv>.")

    config = build_config(args)
    layout = ln.resolve_output_layout(config)

    # --- Mode 3: report-from-supplied-predictions -------------------------
    if mode == "report_from_supplied_predictions":
        if args.validate_only:
            if not Path(args.predictions).exists():
                raise ln.LaunchError(f"--predictions file not found: {args.predictions}")
            print(f"[validate-only] Mode 3 predictions present: {args.predictions}")
            return 0
        pred_out = pd.read_csv(args.predictions)
        _post_prediction(config, layout, args, pred_out, train_summary={}, coverage={"launch_month_area_count": int(pred_out['area_id'].nunique())}, feature_columns=[], hp_prov={}, warnings=[])
        return 0

    # --- Modes 1/2 need the comprehensive source --------------------------
    # Memory-safe load: filter to training-eligible + launch-month rows during read
    # (dropped rows are never used downstream), so multi-million-row sources fit in RAM.
    df = ln.load_comprehensive_source(
        config.comprehensive_source,
        sample_rows=args.sample_rows,
        training_cutoff=config.training_cutoff,
        launch_month=config.launch_month,
    )

    if args.validate_only:
        summary = ln.run_validation_only(config, df, layout, args.overwrite)
        print(f"[validate-only] status={summary.get('status')} train_rows={summary.get('training_rows_before_cutoff')} "
              f"april_rows={summary.get('launch_month_rows')} features={summary.get('feature_count')}")
        if summary.get("feature_schema_warnings"):
            print("[validate-only] warnings:", "; ".join(summary["feature_schema_warnings"]))
        return 0

    if mode == "train_and_predict" and not args.approve_training:
        raise ln.LaunchError(
            "Mode-1 heavy training requires explicit approval. Re-run with --approve-training "
            "(or use --validate-only / --skip-training / --skip-prediction)."
        )

    # Validate + build frames + features (whole-frame feature application keeps schemas aligned)
    ln.validate_source(df, config)
    prepared = ln.prepare_source(df)
    featured_all, transform = ln.apply_identifier_features(prepared, config)
    train_featured, train_summary = ln.build_training_frame(featured_all, config)
    april_featured, coverage = ln.build_xtest_april(featured_all, config)

    if mode == "predict_with_supplied_models":
        models, feature_columns = ln.load_model_artifacts(Path(args.model_artifact_dir))
        hp_prov = {"set": "supplied_models", "model_artifact_dir": args.model_artifact_dir}
    else:
        feature_columns = ln.select_model_features(train_featured)
        models, hp_prov = ln.train_cumulative_regressors(train_featured, feature_columns, config, layout.model_artifacts_dir)

    schema_df, warnings = ln.build_feature_schema_report(
        featured_all, feature_columns, train_featured.columns, april_featured.columns, transform,
    )

    pred = ln.predict_april(models, april_featured, feature_columns, config)
    pred_valid, pred_validation = ln.validate_and_clip_predictions(pred, config)
    overall = ln.derive_overall_phase(pred_valid, config.threshold)
    pred_out = ln.assemble_prediction_output(pred_valid, overall, config)

    # Output safety for production artifacts
    ln.guard_output_conflicts([layout.predictions_csv, layout.run_summary_json], args.overwrite)
    layout.out_root.mkdir(parents=True, exist_ok=True)
    schema_df.to_csv(layout.feature_schema_csv, index=False)
    pd.DataFrame([train_summary]).to_csv(layout.training_summary_csv, index=False)
    ln.write_prediction_outputs(layout, pred_out, april_featured, feature_columns, coverage, pred_validation, args.overwrite)

    _post_prediction(config, layout, args, pred_out, train_summary, coverage, feature_columns, hp_prov, warnings)
    return 0


def _post_prediction(config, layout, args, pred_out, train_summary, coverage, feature_columns, hp_prov, warnings):
    """Comparison (US3), map (US4), reports (US5), run summary. Actuals loaded ONLY here."""
    comparison_payload = None
    map_summary = None
    viz_paths = {}

    # US3 comparison (post-prediction only; actuals never touch training/prediction)
    april_actuals = None
    if args.actual_source:
        actuals_df = pd.read_csv(args.actual_source)
        april_actuals = lc.load_april_actuals(actuals_df, str(ln.launch_target_period(config)), args.actual_crisis_flag)
        result = lc.compare_predictions_to_actuals(pred_out, april_actuals)
        lc.write_comparison_outputs(result, layout.comparison_dir, str(ln.launch_target_period(config)))
        comparison_payload = {"coverage": result.coverage, "metrics": result.metrics}
    else:
        comparison_payload = lc.unavailable_actuals_comparison_summary(pred_out, str(ln.launch_target_period(config)))

    # US4 map
    make_map = args.make_map if args.make_map is not None else bool(args.spatial_path)
    if make_map and args.spatial_path:
        from ipcch import launch_visualizations as lv
        target_label = str(ln.launch_target_period(config)).replace("-", "_")
        suffix = "actual_vs_predicted" if april_actuals is not None and len(april_actuals) else "predicted_only"
        figure_path = layout.viz_report_dir / f"ipcch_{target_label}_global_{suffix}_crisis_map.png"
        summary_path = layout.viz_results_dir / f"{target_label}_crisis_map_validation_summary.json"
        join_csv = layout.viz_results_dir / f"{target_label}_crisis_map_join_validation.csv"
        ms = lv.build_map(
            predictions=pred_out,
            april_actuals=april_actuals,
            spatial_path=Path(args.spatial_path),
            figure_path=figure_path,
            summary_path=summary_path,
            join_validation_csv=join_csv,
            actual_source=args.actual_source or "none",
            prediction_source=str(layout.predictions_csv),
            scope=config.scale,
            no_basemap=args.no_basemap,
            overwrite=args.overwrite,
        )
        map_summary = ms.to_dict()
        viz_paths = {"figure": str(figure_path), "validation_summary": str(summary_path)}

    run_summary = ln.build_run_summary(config, layout, train_summary, coverage, feature_columns, hp_prov, viz_paths)
    ln.write_json(layout.run_summary_json, run_summary)
    ln.write_json(layout.config_json, ln.asdict(config) if hasattr(ln, "asdict") else {"launch_month": config.launch_month})
    pred_dist = ln.prediction_distribution_summary(pred_out) if "phase2_worse_pred" in pred_out.columns else None
    phase_dist = ln.predicted_phase_distribution(pred_out) if "overall_phase_pred" in pred_out.columns else None
    ln.write_launch_reports(config, layout, run_summary, pred_out, pred_dist, phase_dist, comparison_payload, map_summary, warnings)
    print(f"[done] mode={config.execution_mode} predicted_areas={run_summary.get('predicted_area_count')} "
          f"outputs={layout.out_root}")


def main(argv=None) -> int:
    args = parse_args(argv)
    try:
        return run(args)
    except ln.LaunchError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
