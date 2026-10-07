"""Region3 (Southern Africa) local evaluation of saved GLOBAL predictions for origin_safe_weather_oracle_v1.

Reads only saved predictions and metadata: no training pipeline, refit or regional/local model. Membership is
the ``area_id`` join to ``data/reference/area_id_country_region_mapping.csv`` with ``region == 3``; the country
lookup only attaches bootstrap strata. Computes the eight global metrics annually and pooled for the reference
(H0/H3/H6/H12) and both oracle arms (H3/H6/H12), the three paired deltas, and country-stratified whole-area paired
bootstrap draws (2,000, PCG64(42) per period) with conditional percentile intervals (>= 1,000 jointly valid draws).
Requires the global verification (``verify_origin_safe_weather_oracle.py --stage all``) to have passed.
"""
from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = next(path for path in Path(__file__).resolve().parents if (path / "src").exists())
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import numpy as np
import pandas as pd

from ipcch import origin_safe as osf
from ipcch import paths
from ipcch import regional_bootstrap as rb
from ipcch import weather_oracle as wo

VERSION = wo.ORACLE_VERSION
RESULTS = paths.RESULTS_DIR / "experiments" / VERSION
REPORTS = paths.REPORTS_DIR / VERSION
REFERENCE_RUNS = paths.RESULTS_DIR / "experiments" / wo.PARENT_VERSION / "runs" / wo.PARENT_ARM
MAPPING = PROJECT_ROOT / "data" / "reference" / "area_id_country_region_mapping.csv"
LOOKUP = paths.SOURCE_DATA_DIR / "assembled_IPCCH" / "country_area_id_lookup.csv"
FROZEN = {"mapping_sha256": "18ab5099ce2d1154fb5686183ee399124e18427cc1594923f7abe2769da1611d",
          "lookup_sha256": "e2baf6ae9481b42b127db5ce81f3c53ad784bb08ae56dfa56cea74e416b44c90",
          "rows_by_year": {2022: 703, 2023: 514, 2024: 594, 2025: 1423}, "rows": 3234, "areas": 1021,
          "countries": ["AGO", "LSO", "MDG", "MOZ", "MWI", "NAM", "SWZ", "ZAF", "ZMB", "ZWE"], "mapping_region3_areas": 1104}
REGION = 3
KEYS = list(osf.KEYS)
METRICS = osf.ORIGIN_METRICS
PERIODS = (*osf.TARGET_YEARS, "pooled")
ARM_LABEL = {wo.PARENT_ARM: "reference", wo.RAW_ARM: "+raw oracle", wo.B6_ARM: "+raw oracle+B6"}
CONTRASTS = (("raw_oracle - reference", wo.RAW_ARM, wo.PARENT_ARM),
             ("raw_oracle_b6 - reference", wo.B6_ARM, wo.PARENT_ARM),
             ("raw_oracle_b6 - raw_oracle (whole B6 package increment)", wo.B6_ARM, wo.RAW_ARM))
DUPLICATION_CHECK_DRAWS = (0, 1, 2, 1999)


def run_paths() -> dict:
    runs = {(wo.PARENT_ARM, h): REFERENCE_RUNS / f"{h}m" for h in osf.HORIZONS}
    runs.update({(arm, h): RESULTS / "runs" / arm / f"{h}m" for arm in wo.ORACLE_ARMS for h in wo.ORACLE_HORIZONS})
    return runs


def load_run(run: Path) -> tuple:
    meta = json.loads((run / "run_metadata.json").read_text())
    if meta.get("status") != "COMPLETE":
        raise ValueError(f"{run}: run is not COMPLETE")
    files = [run / "predictions" / f"predictions_{y}.csv" for y in osf.TARGET_YEARS]
    frame = pd.concat([pd.read_csv(f, float_precision="round_trip") for f in files], ignore_index=True)
    return frame, {str(f): osf.file_sha256(f) for f in files}, meta["fingerprint"]


def select_region(frame: pd.DataFrame, mapping: pd.Series, iso: pd.Series, label: str) -> pd.DataFrame:
    region = mapping.reindex(frame["area_id"]).to_numpy()
    if pd.isna(region).any():
        raise ValueError(f"{label}: {int(pd.isna(region).sum())} prediction rows lack region membership")
    selected = frame.loc[region == REGION].copy()
    selected["region"] = REGION
    selected["iso3"] = iso.reindex(selected["area_id"]).to_numpy()
    if selected["iso3"].isna().any():
        raise ValueError(f"{label}: selected region3 areas without a country ID: {sorted(selected.loc[selected['iso3'].isna(), 'area_id'].unique())[:10]}")
    return selected


def period_frame(frame: pd.DataFrame, period) -> pd.DataFrame:
    return frame if period == "pooled" else frame[frame["year"] == period].reset_index(drop=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out-dir", default=str(RESULTS / "region3"))
    parser.add_argument("--report", default=str(REPORTS / "region3_report.md"))
    args = parser.parse_args()
    out_dir = Path(args.out_dir)
    if wo.PARENT_VERSION in out_dir.resolve().parts:
        raise SystemExit("refusing to write into the reference namespace")
    summary_path = RESULTS / "verification" / "verification_summary.json"
    verification = json.loads(summary_path.read_text())
    if verification.get("stage") != "all" or not verification.get("passed"):
        raise SystemExit("global verification (--stage all) has not passed; regional evaluation needs verified predictions")
    for path, want in ((MAPPING, FROZEN["mapping_sha256"]), (LOOKUP, FROZEN["lookup_sha256"])):
        if osf.file_sha256(path) != want:
            raise SystemExit(f"{path} sha256 differs from the frozen input")
    out_dir.mkdir(parents=True, exist_ok=True)
    mapping_df = pd.read_csv(MAPPING)
    lookup_df = pd.read_csv(LOOKUP)
    for name, df in (("mapping", mapping_df), ("lookup", lookup_df)):
        if df["area_id"].duplicated().any():
            raise SystemExit(f"{name} has duplicate area_id")
    mapping = mapping_df.set_index("area_id")["region"]
    iso = lookup_df.set_index("area_id")["iso3"]

    runs = run_paths()
    regional, provenance = {}, {}
    for (arm, horizon), run in runs.items():
        frame, hashes, fingerprint = load_run(run)
        regional[(arm, horizon)] = select_region(frame, mapping, iso, f"{arm} h{horizon}")
        provenance[f"{arm} h{horizon}"] = {"run_dir": str(run), "fingerprint": fingerprint, "prediction_sha256": hashes,
                                           "global_rows": len(frame), "region3_rows": len(regional[(arm, horizon)])}
    aligned = rb.align_paired_predictions(regional)
    base = aligned[(wo.PARENT_ARM, 0)]
    for (arm, horizon), frame in aligned.items():
        if not frame["iso3"].equals(base["iso3"]):
            raise SystemExit(f"{arm} h{horizon}: country strata differ")
    rows_by_year = {int(k): int(v) for k, v in base["year"].value_counts().sort_index().items()}
    countries = sorted(base["iso3"].unique())
    if rows_by_year != FROZEN["rows_by_year"] or len(base) != FROZEN["rows"] or base["area_id"].nunique() != FROZEN["areas"] \
            or countries != FROZEN["countries"] or int((mapping == REGION).sum()) != FROZEN["mapping_region3_areas"]:
        raise SystemExit(f"region3 cohort differs from the frozen expectation: {rows_by_year}, {base['area_id'].nunique()} areas, {countries}")

    # ---------------------------------------------------------------- saved local predictions and membership ledger
    local = pd.concat([f.assign(run_arm=arm, run_horizon=h) for (arm, h), f in aligned.items()], ignore_index=True)
    local.to_csv(out_dir / "region3_predictions.csv", index=False, float_format="%.17g")
    membership = []
    region3_areas = mapping[mapping == REGION].index
    for country in countries:
        in_map = lookup_df[lookup_df["area_id"].isin(region3_areas) & (lookup_df["iso3"] == country)]
        part = base[base["iso3"] == country]
        row = {"iso3": country, "mapping_region3_areas": len(in_map), "evaluated_areas": part["area_id"].nunique(), "rows": len(part)}
        for year in osf.TARGET_YEARS:
            row[f"rows_{year}"] = int((part["year"] == year).sum())
            row[f"areas_{year}"] = int(part.loc[part["year"] == year, "area_id"].nunique())
        membership.append(row)
    unmapped_region3 = sorted(set(region3_areas) - set(lookup_df["area_id"]))
    membership = pd.DataFrame(membership)
    membership.to_csv(out_dir / "region3_membership_coverage.csv", index=False)
    key_hashes = {str(p): osf.keys_sha256(period_frame(base, p)) for p in PERIODS}

    # ---------------------------------------------------------------- point metrics and deltas
    point_rows, point = [], {}
    for (arm, horizon), frame in aligned.items():
        for period in PERIODS:
            part = period_frame(frame, period)
            values = rb.weighted_metrics(part, np.ones(len(part)))
            check = osf.origin_metrics(part, "region3", period)
            row = {"arm": arm, "horizon": horizon, "period": str(period), "n_rows": len(part), "n_areas": part["area_id"].nunique(),
                   "n_countries": part["iso3"].nunique()}
            for metric in METRICS:
                v, d = values[metric][0][0], bool(values[metric][1][0])
                want = check[metric]["value"]
                if (want is None) == d or (d and abs(v - want) > 1e-12):
                    raise SystemExit(f"{arm} h{horizon} {period} {metric}: weighted point {v} differs from the global evaluator {want}")
                row[metric] = v if d else None
                row[f"{metric}_status"] = check[metric]["status"]
                row[f"{metric}_reason"] = check[metric]["reason"]
                point[(arm, horizon, str(period), metric)] = (v, d)
            point_rows.append(row)
    order = {wo.PARENT_ARM: 0, wo.RAW_ARM: 1, wo.B6_ARM: 2}
    point_df = pd.DataFrame(point_rows)
    point_df = point_df.sort_values(["horizon", "arm", "period"], key=lambda s: s.map(order) if s.name == "arm" else s, kind="mergesort")
    point_df.to_csv(out_dir / "region3_metrics.csv", index=False)

    # ---------------------------------------------------------------- bootstrap
    interval_rows, metric_draw_frames, delta_draw_frames, dup_rows, bundles = [], [], [], [], {}
    boot_runs = [(arm, h) for h in wo.ORACLE_HORIZONS for arm in (wo.PARENT_ARM, *wo.ORACLE_ARMS)]
    for period in PERIODS:
        frames = {key: period_frame(aligned[key], period) for key in boot_runs}
        ref = frames[boot_runs[0]]
        areas = ref[["area_id", "iso3"]].drop_duplicates("area_id")
        bundle = rb.stratified_area_multiplicities(areas)
        position = pd.Series(np.arange(len(bundle["area_id"])), index=bundle["area_id"])
        row_area = position.reindex(ref["area_id"]).to_numpy()
        W = bundle["multiplicity"][:, row_area]
        np.savez_compressed(out_dir / f"multiplicities_{period}.npz", area_id=bundle["area_id"], iso3=bundle["iso3"].astype(str),
                            multiplicity=bundle["multiplicity"].astype(np.int16), row_area_id=ref["area_id"].to_numpy(),
                            row_year=ref["year"].to_numpy(), row_month=ref["month"].to_numpy(), seed=bundle["seed"])
        multi = any(n >= 2 for n in bundle["stratum_sizes"].values())
        bundles[str(period)] = {"countries": list(bundle["stratum_sizes"]), "stratum_sizes": bundle["stratum_sizes"], "areas": len(bundle["area_id"]),
                                "rows": len(ref), "keys_sha256_sorted": key_hashes[str(period)], "has_multi_area_stratum": multi,
                                "multiplicity_sha256": osf.list_sha256([",".join(map(str, r)) for r in bundle["multiplicity"]]),
                                "generator": bundle["generator"], "draw_order": bundle["draw_order"], "seed": bundle["seed"], "n_draws": bundle["n_draws"]}
        draws = {}
        for key in boot_runs:
            draws[key] = rb.weighted_metrics(frames[key], W)
            arm, horizon = key
            for metric in METRICS:
                values, defined = draws[key][metric]
                metric_draw_frames.append(pd.DataFrame({"period": str(period), "horizon": horizon, "arm": arm, "metric": metric,
                                                        "draw": np.arange(len(values)), "value": values, "defined": defined}))
            for d in DUPLICATION_CHECK_DRAWS:
                want = rb.duplicated_metrics(frames[key], W[d])
                for metric in METRICS:
                    v, ok = draws[key][metric][0][d], bool(draws[key][metric][1][d])
                    agree = (want[metric] is None and not ok) or (want[metric] is not None and ok and abs(v - want[metric]) <= 1e-12)
                    dup_rows.append({"period": str(period), "horizon": horizon, "arm": arm, "draw": d, "metric": metric,
                                     "weighted": v if ok else None, "duplicated": want[metric], "agree": agree})
        for horizon in wo.ORACLE_HORIZONS:
            for label, a, b in CONTRASTS:
                for metric in METRICS:
                    va, da = draws[(a, horizon)][metric]
                    vb, db = draws[(b, horizon)][metric]
                    joint = da & db
                    delta = np.where(joint, va - vb, np.nan)
                    delta_draw_frames.append(pd.DataFrame({"period": str(period), "horizon": horizon, "contrast": label, "metric": metric,
                                                           "draw": np.arange(len(delta)), "delta": delta, "joint_valid": joint}))
                    pa, pda = point[(a, horizon, str(period), metric)]
                    pb, pdb = point[(b, horizon, str(period), metric)]
                    ci = rb.conditional_interval(delta, joint, pda and pdb, multi)
                    interval_rows.append({"period": str(period), "horizon": horizon, "contrast": label, "metric": metric,
                                          "point_delta": pa - pb if pda and pdb else None, "point_status": "ok" if pda and pdb else "undefined",
                                          **ci})
        print(f"period {period}: {len(ref)} rows, {len(bundle['area_id'])} areas, {len(bundle['stratum_sizes'])} strata", flush=True)
    intervals = pd.DataFrame(interval_rows)
    intervals.to_csv(out_dir / "region3_paired_intervals.csv", index=False)
    pd.concat(metric_draw_frames, ignore_index=True).to_csv(out_dir / "region3_metric_draws.csv.gz", index=False, float_format="%.17g")
    pd.concat(delta_draw_frames, ignore_index=True).to_csv(out_dir / "region3_delta_draws.csv.gz", index=False, float_format="%.17g")
    dup = pd.DataFrame(dup_rows)
    dup.to_csv(out_dir / "region3_duplication_check.csv", index=False)
    if not dup["agree"].all():
        raise SystemExit("weighted bootstrap metrics disagree with explicit row duplication")

    # ---------------------------------------------------------------- replay of saved draws from saved multiplicities
    replay = {}
    for period in PERIODS:
        saved = np.load(out_dir / f"multiplicities_{period}.npz")
        again = rb.stratified_area_multiplicities(pd.DataFrame({"area_id": saved["area_id"], "iso3": saved["iso3"]}))
        replay[str(period)] = bool(np.array_equal(again["multiplicity"], saved["multiplicity"]))
    if not all(replay.values()):
        raise SystemExit(f"multiplicities do not replay from the seed: {replay}")

    import sklearn

    metadata = {
        "version": VERSION, "stage": "region3 saved-prediction evaluation (no fitting)",
        "membership": {"authority": str(MAPPING.relative_to(PROJECT_ROOT)), "sha256": FROZEN["mapping_sha256"], "rule": "area_id join, region == 3",
                       "mapping_region3_areas": int((mapping == REGION).sum()), "evaluated_areas": int(base["area_id"].nunique()),
                       "region3_areas_without_lookup_row": len(unmapped_region3)},
        "country_strata": {"lookup": str(LOOKUP), "sha256": FROZEN["lookup_sha256"], "use": "bootstrap strata only", "countries": countries},
        "cohort": {"rows": len(base), "rows_by_year": rows_by_year, "areas": int(base["area_id"].nunique()),
                   "key_convention": "rows sorted by (area_id, year, month); osf.keys_sha256 over the sorted keys (differs from the parent manifest's order-sensitive hash)",
                   "keys_sha256_sorted": key_hashes},
        "runs": provenance, "global_verification_summary": {"path": str(summary_path), "sha256": osf.file_sha256(summary_path)},
        "bootstrap": {"method": "country-stratified whole-area paired bootstrap", "n_draws": rb.N_DRAWS, "seed": rb.SEED,
                      "generator": "numpy PCG64, one generator per period", "quantiles": list(rb.QUANTILES), "quantile_method": rb.QUANTILE_METHOD,
                      "interval": rb.INTERVAL_TYPE, "min_valid_draws": rb.MIN_VALID_DRAWS, "replenishment": "none; invalid draws are kept and masked",
                      "weighting": "observation rows weighted by their area's multiplicity; no country/area re-weighting", "periods": bundles,
                      "multiplicities_replay_from_seed": replay, "duplication_check_draws": list(DUPLICATION_CHECK_DRAWS),
                      "duplication_check_cells": len(dup), "duplication_check_all_agree": bool(dup["agree"].all())},
        "no_fitting": {"xgboost_imported": "xgboost" in sys.modules, "training_cli_imported": "run_deep_feature_weight_decay_forecasting" in sys.modules},
        "runtime": {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__, "sklearn": sklearn.__version__,
                    "executable": sys.executable,
                    "git_head": subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=PROJECT_ROOT).stdout.strip(),
                    "code_sha256": {p: osf.file_sha256(PROJECT_ROOT / p) for p in ("scripts/postprocessing/evaluate_region3_saved_predictions.py",
                                                                                    "src/ipcch/regional_bootstrap.py", "src/ipcch/origin_safe.py",
                                                                                    "src/ipcch/forecasting_weight_decay.py")}},
        "reading": {"draw_and_interval_csvs": "pd.read_csv(path, dtype={'period': str}); period holds years and 'pooled'",
                    "multiplicities_npz": "multiplicity[d, j] is draw d's count of area_id[j]; rows carry their area's count"},
        "outputs": {p.name: osf.file_sha256(p) for p in sorted(out_dir.glob("*")) if p.is_file() and p.name != "region3_metadata.json"},
    }
    if metadata["no_fitting"]["xgboost_imported"] or metadata["no_fitting"]["training_cli_imported"]:
        raise SystemExit("regional evaluation imported model-fitting code")
    osf.dump_json(out_dir / "region3_metadata.json", metadata)
    write_report(Path(args.report), point_df, intervals, membership, metadata)
    print(json.dumps({"rows": len(base), "areas": int(base["area_id"].nunique()), "intervals": len(intervals),
                      "conditional": int((intervals["ci_status"] == "conditional").sum()),
                      "unavailable": int((intervals["ci_status"] != "conditional").sum())}, indent=2))
    return 0


def fmt(value, digits: int = 4) -> str:
    return "undefined" if value is None or pd.isna(value) else f"{value:.{digits}f}"


def write_report(path: Path, point: pd.DataFrame, intervals: pd.DataFrame, membership: pd.DataFrame, meta: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# {VERSION}: Southern Africa (region3) local evaluation of global predictions", "",
             f"Machine-readable sources: `results/experiments/{VERSION}/region3/`. These are the saved predictions of the globally fitted "
             "models restricted to region3 areas; no regional or local model was trained and nothing was refit.", "",
             f"Membership: `{meta['membership']['authority']}` (sha256 `{meta['membership']['sha256'][:12]}…`), `area_id` join with `region == 3`; "
             f"{meta['membership']['mapping_region3_areas']} mapped areas, {meta['cohort']['areas']} with evaluation rows; {meta['cohort']['rows']} rows "
             f"({', '.join(f'{y}: {n}' for y, n in meta['cohort']['rows_by_year'].items())}). Country IDs come from the country lookup and define "
             "bootstrap strata only.", "", "| country | mapped areas | evaluated areas | rows | 2022 | 2023 | 2024 | 2025 |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for _, r in membership.iterrows():
        lines.append(f"| {r.iso3} | {r.mapping_region3_areas} | {r.evaluated_areas} | {r.rows} | {r.rows_2022} | {r.rows_2023} | {r.rows_2024} | {r.rows_2025} |")
    head = "| arm | period | n | exact-phase acc | phase 3+ acc | precision 3+ | recall 3+ | F2 3+ | R² 3+ | MAE 3+ | ordinal MAE |"
    sep = "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    lines += ["", "## Point metrics (reference first)", "", "Units as in the global report: accuracies, precision, recall in shares; F2/R² dimensionless; "
              "MAE 3+ in normalized population share; ordinal MAE in phase steps. Observation rows are weighted equally.", ""]
    for horizon in osf.HORIZONS:
        lines += [f"### H = {horizon}" + (" (reference only)" if horizon == 0 else ""), "", head, sep]
        for arm in (wo.PARENT_ARM, *wo.ORACLE_ARMS):
            for _, r in point[(point.horizon == horizon) & (point.arm == arm)].iterrows():
                lines.append(f"| {ARM_LABEL[arm]} | {r.period} | {r.n_rows} | " + " | ".join(fmt(r[m]) for m in METRICS) + " |")
        lines.append("")
    b = meta["bootstrap"]
    lines += ["## Paired differences with conditional 95% bootstrap intervals", "",
              f"Country-stratified whole-area paired bootstrap: within each observed country the N_c areas of the period are drawn N_c times "
              f"with replacement and carry all their rows; {b['n_draws']} draws from one PCG64(seed {b['seed']}) generator per period, shared by every "
              "arm, horizon, metric and contrast. Intervals are percentile intervals (0.025/0.975, linear) **conditional on both compared metrics "
              f"being defined in a draw**; they are reported only when at least {b['min_valid_draws']} of the {b['n_draws']} paired draws are jointly "
              "valid, otherwise marked unavailable with the reason. Invalid draws are kept and masked, never replaced or set to zero. "
              "`valid` is the count of jointly valid draws.", ""]
    for horizon in wo.ORACLE_HORIZONS:
        lines += [f"### H = {horizon}", "", "| contrast | period | metric | point Δ | 95% CI (conditional) | valid / 2000 | invalid share |",
                  "|---|---|---|---:|---|---:|---:|"]
        for _, r in intervals[intervals.horizon == horizon].iterrows():
            ci = f"[{fmt(r.ci_lower)}, {fmt(r.ci_upper)}]" if r.ci_status == "conditional" else f"unavailable: {r.ci_reason}"
            lines.append(f"| {r.contrast} | {r.period} | {r.metric} | {fmt(r.point_delta)} | {ci} | {r.draws_valid} | {fmt(r.invalid_fraction, 3)} |")
        lines.append("")
    lines += ["## Interpretation limits", "",
              "- The intervals condition on the fitted global models (single seed 42) and on the observed countries, years and each "
              "country's number of areas; they do not include model-fitting or seed uncertainty, generalization to new countries or "
              "future years, or shocks shared by different areas of one country.",
              "- Countries with more rows per area carry more weight; the bootstrap fixes area-sampling slots per country, not each country's row share.",
              "- Conditional intervals describe the resampling distribution restricted to draws where both metrics are defined; the invalid "
              "share is part of the result. The 1,000-draw threshold is a reporting rule, not a statistical adequacy guarantee.",
              "- The oracle arms assume realized weather was a perfect forecast available at origin; `raw_oracle_b6 - raw_oracle` is the whole "
              "fixed B6 package increment, not an isolated IPC interaction or causal effect.", ""]
    path.write_text("\n".join(lines))


if __name__ == "__main__":
    raise SystemExit(main())
