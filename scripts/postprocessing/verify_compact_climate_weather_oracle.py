"""Independent verification, global/all-region scoring and actual-input codebook for compact_climate_weather_oracle_v1.

``--stage inputs`` (before fitting): frozen runtime/config/parent hashes, compact manifest and every pinned input,
oracle-input baseline projection parity, an independent pure-Python replay of the compact recipes on sampled real rows
(ordinary, same-month z, stress, seasons/major) and of the raw oracle from the shared source, and the legacy
no-overwrite inventory. ``--stage all`` adds, for the seven runs: all 28 batches and 112 models reloaded and replayed,
fitting keys/ages/weights (equal across arms and equal to the parent reference protocol), normalized targets, cohort
and class rule, scikit-learn metric replay (global and regions 0..8, annual and pooled), paired oracle - baseline
deltas, the actual-input codebook checked against every booster and the expected-vs-actual comparison.
Regional scoring reads saved predictions only; nothing is fitted or bootstrapped here.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import statistics
import sys
from fractions import Fraction
from pathlib import Path

PROJECT_ROOT = next(path for path in Path(__file__).resolve().parents if (path / "src").exists())
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import numpy as np
import pandas as pd

from ipcch import compact_features as cpf
from ipcch import origin_safe as osf
from ipcch import paths
from ipcch import regional_point_metrics as rpm
from ipcch import weather_oracle as wo


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, PROJECT_ROOT / rel)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ov = _load("oracle_verify", "scripts/postprocessing/verify_origin_safe_weather_oracle.py")
legacy = ov.legacy

VERSION = cpf.VERSION
MODEL_READY = paths.SOURCE_DATA_DIR / "assembled_IPCCH" / "model_ready"
MANIFEST = MODEL_READY / VERSION / f"{VERSION}_manifest.json"
PARENT_MANIFEST = MODEL_READY / cpf.PARENT_VERSION / f"{cpf.PARENT_VERSION}_manifest.json"
PARENT_RUNS = paths.RESULTS_DIR / "experiments" / cpf.PARENT_VERSION / "runs" / cpf.PARENT_ARM
RESULTS = paths.RESULTS_DIR / "experiments" / VERSION
REPORTS = paths.REPORTS_DIR / VERSION
REGION_MAP = PROJECT_ROOT / "data" / "reference" / "area_id_country_region_mapping.csv"
REGION_MAP_SHA256 = "18ab5099ce2d1154fb5686183ee399124e18427cc1594923f7abe2769da1611d"
TASK_DIR = PROJECT_ROOT / ".trellis" / "tasks" / "10-08-compact-climate-weather-oracle"
LEGACY_INVENTORY = RESULTS / "preflight" / "legacy_hash_inventory_before.csv"
KEYS = list(osf.KEYS)
YEARS = osf.TARGET_YEARS
SAMPLE_ROWS = 400
LEGACY_DIRS = (MODEL_READY / wo.PARENT_VERSION, MODEL_READY / wo.ORACLE_VERSION,
               paths.RESULTS_DIR / "experiments" / wo.PARENT_VERSION, paths.RESULTS_DIR / "experiments" / wo.ORACLE_VERSION)


def run_id(arm: str, horizon: int) -> str:
    return f"{arm}/{horizon}m"


def run_dir(arm: str, horizon: int) -> Path:
    return RESULTS / "runs" / arm / f"{horizon}m"


# --------------------------------------------------------------------------- independent recipe replay (pure Python)


def series_by_area(frame: pd.DataFrame, column: str) -> dict:
    out: dict = {}
    for area, o, v in zip(frame["area_id"].to_numpy(), frame["ord"].to_numpy(), frame[column].to_numpy(dtype=float)):
        out.setdefault(area, {})[int(o)] = float(v)
    return out


def _get(s: dict, u: int) -> float:
    return s.get(u, float("nan"))


def _valid(values):
    return [v for v in values if v == v]


def exact_mean(vals) -> Fraction:
    return sum(Fraction(v) for v in vals) / len(vals)


def exact_sd(vals) -> float:
    """Sample SD (ddof 1) from exact rational mean and squared deviations; one final float rounding."""
    mean = exact_mean(vals)
    return math.sqrt(float(sum((Fraction(v) - mean) ** 2 for v in vals) / (len(vals) - 1)))


def ref_mean(s, o, w, minp):
    vals = _valid(_get(s, u) for u in range(o - w + 1, o + 1))
    return float(exact_mean(vals)) if len(vals) >= minp else float("nan")


def ref_z(s, u):
    """Exact-arithmetic z (statistics.fmean rounds the mean to a float first and fails on near-constant histories)."""
    x = _get(s, u)
    prior = _valid(s.get(u - 12 * k, float("nan")) for k in range(1, 40))
    if x != x or len(prior) < 2 or min(prior) == max(prior):
        return float("nan")
    return float(Fraction(x) - exact_mean(prior)) / exact_sd(prior)


def ref_signal(stem: str, s: dict, u: int) -> float:
    x = _get(s, u)
    if x != x:
        return float("nan")
    prev = _get(s, u - 12)
    if stem == "GPP_mean__vegetation_stress":
        return float(prev == prev and x < 0.9 * prev)
    if stem == "event_count_violence__nonzero_stress":
        return float(x > 0)
    if stem == "WFP_Price__price_shock_stress":
        return float(prev == prev and prev != 0 and (x - prev) / prev > 0.10)
    if stem == "nino34_anom__enso_stress":
        return float(abs(x) > 0.5)
    return {"spi03_month_ensmean__deficit_stress": float(x <= -1.0), "tmean_anom_month_ensmean__hot_stress": float(x >= 1.0),
            "evi_anom_month_ensmean__vegetation_stress": float(x <= -0.015)}[stem]


def ref_stress(stem, s, o, first_ord):
    sig = [ref_signal(stem, s, u) for u in range(o - 11, o + 1)]
    valid = _valid(sig)
    share = sum(valid) / len(valid) if len(valid) >= 6 else float("nan")
    anyv = max(valid) if len(valid) >= 6 else float("nan")
    best = cur = 0
    for v in sig:
        cur = cur + 1 if v == 1 else 0
        best = max(best, cur)
    run = float(best) if len(valid) >= 6 else float("nan")
    since = float("nan")
    for u in range(o, first_ord - 1, -1):
        if ref_signal(stem, s, u) == 1:
            since = float(o - u)
            break
    return [share, since, run, anyv]


def ref_seasons(rows: pd.DataFrame, o: int):
    """Independent selection of the two latest completed seasons and the major flag of the latest."""
    cut = pd.Timestamp(year=(o + 1) // 12, month=(o + 1) % 12 + 1, day=1)
    done = rows[pd.to_datetime(rows["gs_end_date_exclusive"]) <= cut].copy()
    done["_end"] = pd.to_datetime(done["gs_end_date_exclusive"])
    done["_start"] = pd.to_datetime(done["gs_start_date"])
    done = done.sort_values(["_end", "_start", "_src"], kind="mergesort")
    picked = [done.iloc[-1] if len(done) >= 1 else None, done.iloc[-2] if len(done) >= 2 else None]
    out = []
    for p in picked:
        if p is None:
            out += [float("nan")] * (len(cpf.SEASON_METRICS) + 1)
        else:
            end_month = p["_end"] - pd.Timedelta(days=1)
            out += [float(p[m]) for m in cpf.SEASON_METRICS] + [float(o - (end_month.year * 12 + end_month.month - 1))]
    major = float("nan")
    if picked[0] is not None:
        pair = rows[(rows["season_year"] == picked[0]["season_year"])]
        if len(pair) == 2 and set(pair["season"]) == {"s1", "s2"}:
            days = {r["season"]: (pd.Timestamp(r["gs_end_date_exclusive"]) - pd.Timestamp(r["gs_start_date"])).days for _, r in pair.iterrows()}
            mine, other = days[picked[0]["season"]], days["s2" if picked[0]["season"] == "s1" else "s1"]
            if mine > 0 and other > 0 and mine != other:
                major = float(mine > other)
    return out + [major]


def independent_replay(datasets: dict, manifest: dict, problems: list, checks: dict) -> pd.DataFrame:
    """Sampled real rows per horizon: every compact dynamic feature recomputed from the long source tables."""
    parent = json.loads(PARENT_MANIFEST.read_text())
    members = manifest["commodity_members"]
    interim = pd.read_csv(parent["inputs"]["interim"]["path"], usecols=["admin_code", "year", "month", *cpf.INTERIM_SOURCES[:7],
                                                                        *[c for v in members.values() for c in v]])
    for group, cols in members.items():
        block = interim[cols].apply(pd.to_numeric, errors="coerce").to_numpy(dtype=float)
        n = np.isfinite(block).sum(axis=1)
        with np.errstate(invalid="ignore", divide="ignore"):
            interim[f"{group}__composite_mean"] = np.where(n > 0, np.nansum(block, axis=1) / np.maximum(n, 1), np.nan)
    interim = interim.rename(columns={"admin_code": "area_id"})
    interim["ord"] = interim["year"] * 12 + interim["month"] - 1
    climate = pd.read_csv(parent["inputs"]["climate_monthly"]["path"], usecols=["admin_code", "year", "month", *cpf.CLIMATE_SOURCES]).rename(columns={"admin_code": "area_id"})
    climate["ord"] = climate["year"] * 12 + climate["month"] - 1
    first = {s: int((interim if s in cpf.INTERIM_SOURCES else climate)["ord"].min()) for s in cpf.ORDINARY_SOURCES}
    series = {s: series_by_area(interim if s in cpf.INTERIM_SOURCES else climate, s) for s in cpf.ORDINARY_SOURCES}
    seasons = pd.read_csv(parent["inputs"]["climate_seasonal"]["path"], usecols=["admin_code", "season_year", "season", "gs_start_date",
                                                                                   "gs_end_date_exclusive", *cpf.SEASON_METRICS])
    seasons["_src"] = np.arange(len(seasons))
    by_area = {a: g for a, g in seasons.groupby("admin_code")}
    stems = dict(zip(cpf.STRESS_STEMS, ("GPP_mean", "event_count_violence", "WFP_Price", "nino34_anom", "spi03_month_ensmean",
                                         "tmean_anom_month_ensmean", "evi_anom_month_ensmean")))
    rng = np.random.default_rng(20261008)
    rows = []
    for h, data in datasets.items():
        idx = rng.choice(len(data), SAMPLE_ROWS, replace=False)
        for i in idx:
            r = data.iloc[i]
            area, o = r["area_id"], int(r["year"]) * 12 + int(r["month"]) - 1 - h
            expected = {}
            for s in cpf.ORDINARY_SOURCES:
                x = series[s].get(area, {})
                vals = _valid(_get(x, u) for u in range(o - 11, o + 1))
                expected.update(dict(zip(cpf.ordinary_names(s), [_get(x, o), ref_mean(x, o, 3, 2), ref_mean(x, o, 6, 3), ref_mean(x, o, 12, 6),
                                                                  exact_sd(vals) if len(vals) >= 6 else float("nan")])))
            for s in cpf.Z_SOURCES:
                x = series[s].get(area, {})
                z = {u: ref_z(x, u) for u in range(o - 11, o + 1)}
                expected.update(dict(zip(cpf.z_names(s), [z[o], ref_mean(z, o, 3, 2), ref_mean(z, o, 6, 3), ref_mean(z, o, 12, 6)])))
            for stem, s in stems.items():
                expected.update(dict(zip(cpf.stress_names(stem), ref_stress(stem, series[s].get(area, {}), o, first[s]))))
            expected.update(dict(zip(cpf.season_names(), ref_seasons(by_area.get(area, seasons.iloc[:0]), o))))
            for name, want in expected.items():
                got = float(r[name])
                same = (got != got and want != want) or (got == got and want == want and np.isclose(got, want, rtol=1e-7, atol=1e-9))
                rows.append({"horizon": h, "row": int(i), "area_id": area, "origin": osf.ord_label(o), "feature": name,
                             "saved": got, "independent": want, "match": bool(same)})
    out = pd.DataFrame(rows)
    checks["independent_feature_cells"] = len(out)
    bad = out[~out["match"]]
    checks["independent_feature_mismatches"] = len(bad)
    if len(bad):
        problems.append(f"independent recipe replay: {len(bad)} cell mismatches, e.g. {bad.head(5).to_dict('records')}")
    return out


def independent_oracle(data: pd.DataFrame, horizon: int, source: pd.DataFrame) -> dict:
    src = source.assign(ord=source["year"] * 12 + source["month"] - 1).set_index(["area_id", "ord"])
    origin = data["year"].to_numpy() * 12 + data["month"].to_numpy() - 1 - horizon
    out = {}
    for k in range(1, wo.window(horizon) + 1):
        got = src.reindex(pd.MultiIndex.from_arrays([data["area_id"].to_numpy(), origin + k]))
        for v in wo.ORACLE_VARIABLES:
            out[wo.raw_name(v, k)] = got[v].to_numpy(dtype=float)
    return out


# --------------------------------------------------------------------------- legacy no-overwrite inventory


def legacy_inventory_check(problems: list, out_dir: Path) -> dict:
    before = pd.read_csv(LEGACY_INVENTORY)
    rows = []
    for d in LEGACY_DIRS:
        for p in sorted(d.rglob("*")):
            if p.is_file():
                rows.append({"path": str(p), "bytes": p.stat().st_size, "sha256": legacy.sha(p)})
    after = pd.DataFrame(rows)
    after.to_csv(out_dir / "legacy_hash_inventory_after.csv", index=False)
    merged = before.merge(after, on="path", how="outer", suffixes=("_before", "_after"), indicator=True)
    changed = merged[(merged["_merge"] != "both") | (merged["sha256_before"] != merged["sha256_after"])]
    if len(changed):
        problems.append(f"legacy artifacts changed/added/removed: {changed['path'].head(10).tolist()}")
    return {"files_before": len(before), "files_after": len(after), "changed_added_removed": len(changed)}


# --------------------------------------------------------------------------- codebook


def write_codebook(manifest: dict, fitted: dict, problems: list, verified: bool) -> dict:
    """Actual-input codebook from fitted feature lists, plus expected-vs-actual.

    ``verified`` must mean every run, batch, booster schema and replay check passed; otherwise the files carry an
    ``UNVERIFIED`` name and ``unverified_diagnostic`` status and are not the published actual codebook.
    """
    out_dir = REPORTS / "model_run_codebook"
    out_dir.mkdir(parents=True, exist_ok=True)
    contract_path = Path(manifest["contract"]["files"]["expected_feature_contract.csv"]["path"])
    if legacy.sha(contract_path) != cpf.FROZEN_CONTRACT_SHA256["expected_feature_contract.csv"]:
        problems.append("expected contract CSV copy differs from the approved bytes")
    with open(contract_path, encoding="utf-8-sig", newline="") as fh:
        expected_rows = list(csv.DictReader(fh))
    runs = [run_id(a, h) for a, h in cpf.RUN_PLAN]
    positions = {r: {f: i + 1 for i, f in enumerate(fitted[r])} for r in runs}
    union = [f for r in runs for f in fitted[r]]
    union = list(dict.fromkeys(union))
    keep = ["predictor", "group", "description", "unit", "source", "time_relative_to_origin", "formula", "missing_semantics", "input_type"]
    tail = ["horizons_months", "family", "source_variable", "base_source_definition", "definition_evidence", "limitations"]
    by_name = {r["predictor"]: r for r in expected_rows}
    codebook, comparison = [], []
    for pos, name in enumerate(union, 1):
        base = by_name.get(name)
        if base is None:
            problems.append(f"fitted feature {name} has no contract row")
            continue
        row = {"position": pos, **{k: base[k] for k in keep}}
        for r in runs:
            col = r.replace("/", "_")
            row[col] = "true" if name in positions[r] else "false"
            row[f"{col}_expanded_count"] = 1 if name in positions[r] else 0
        row["actual_model_columns"] = json.dumps([name])
        row["actual_model_positions"] = json.dumps({r: positions[r][name] for r in runs if name in positions[r]}, separators=(",", ":"))
        row.update({k: base[k] for k in tail})
        row["fit_status"] = "fitted_verified_all_batches" if verified else "unverified_diagnostic"
        codebook.append(row)
        exp = json.loads(base["expected_model_positions"])
        act = {r: positions[r][name] for r in runs if name in positions[r]}
        comparison.append({"predictor": name, "expected_model_positions": json.dumps(exp, sort_keys=True),
                           "actual_model_positions": json.dumps(act, sort_keys=True), "match": exp == act})
    missing = sorted(set(by_name) - set(union))
    for name in missing:
        comparison.append({"predictor": name, "expected_model_positions": by_name[name]["expected_model_positions"],
                           "actual_model_positions": "{}", "match": False})
    comp = pd.DataFrame(comparison)
    if not comp["match"].all() or len(union) != len(expected_rows):
        problems.append(f"expected vs actual fitted inputs differ for {int((~comp['match']).sum())} predictors")
    suffix = "" if verified else "_UNVERIFIED"
    path = out_dir / f"IPCCH_compact_climate_weather_oracle_model_run_codebook_en{suffix}.csv"
    pd.DataFrame(codebook).to_csv(path, index=False, encoding="utf-8-sig")
    comp.to_csv(out_dir / f"expected_vs_actual_inputs{suffix}.csv", index=False)
    index = pd.DataFrame([{"run_id": r, "arm": r.split("/")[0], "horizon_months": int(r.split("/")[1][:-1]),
                           "actual_feature_count": len(fitted[r]), "actual_feature_sha256": osf.list_sha256(fitted[r]),
                           "expected_feature_sha256": cpf.FROZEN_FEATURE_SHA256[(r.split("/")[0], int(r.split("/")[1][:-1]))],
                           "run_path": str(run_dir(r.split("/")[0], int(r.split("/")[1][:-1])).relative_to(PROJECT_ROOT))} for r in runs])
    index["match"] = index["actual_feature_sha256"] == index["expected_feature_sha256"]
    index.to_csv(out_dir / f"model_run_index{suffix}.csv", index=False)
    if not index["match"].all():
        problems.append("a run's fitted feature hash differs from the frozen contract")
    return {"codebook": str(path), "status": "verified" if verified else "unverified_diagnostic", "rows": len(codebook),
            "expected_rows": len(expected_rows), "all_match": bool(comp["match"].all())}


# --------------------------------------------------------------------------- report


def fmt(value, digits=4):
    return "undefined" if value is None or pd.isna(value) else f"{value:.{digits}f}"


METRIC_LABELS = {"exact_phase_accuracy": "exact acc", "phase3plus_accuracy": "3+ acc", "precision_phase3plus": "prec 3+",
                 "sensitivity_phase3plus": "recall 3+", "f2_phase3plus": "F2 3+", "r2_phase3plus": "R² 3+",
                 "mae_phase3plus": "MAE 3+", "ordinal_mae": "ordinal MAE"}


def wide_metrics(long: pd.DataFrame, index: list, value: str = "value") -> pd.DataFrame:
    """One row per existing ``index`` group (all-undefined groups kept), one column per metric; no phantom groups."""
    if long.duplicated(index + ["metric"]).any():
        raise ValueError("metric table has duplicate rows for a group/metric")
    return long.set_index(index + ["metric"])[value].unstack("metric").reset_index()


def write_report(gm: pd.DataFrame, gd: pd.DataFrame, rm: pd.DataFrame, rd: pd.DataFrame, summary: dict, manifest: dict) -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    metrics = list(osf.ORIGIN_METRICS)
    head = "| " + " | ".join(["arm", "period", "n"] + [METRIC_LABELS[m] for m in metrics]) + " |"
    sep = "|---|---|---:|" + "---:|" * len(metrics)
    wide = wide_metrics(gm, ["arm", "horizon", "period", "n_rows"])
    lines = [f"# {VERSION}: compact features with and without the raw weather oracle (global and regions 0-8)", "",
             f"Machine-readable sources: `results/experiments/{VERSION}/verification/`. Every value is computed from saved unrounded "
             "predictions on the frozen 28,205 evaluation keys and replayed with scikit-learn (atol 1e-12, identical undefined masks).", "",
             f"Verification passed: `{summary['passed']}`; runs {summary.get('runs_verified')}/7; batches {summary.get('batches')}; "
             f"models reloaded {summary.get('models_reloaded')}; max model replay diff {summary.get('max_model_replay_abs_diff')}.", "",
             "## Configurations", "",
             "- **compact_baseline** (296 inputs, H0/H3/H6/H12): static 29, ordinary 120 (value/MA3/MA6/MA12/SD12 of 24 sources at origin O), "
             "same-month z 56, stress 28, two completed growing seasons + latest major dummy 29, coordinates/target calendar 27, safe IPC "
             "history 5, national IDP 2. Inputs rebuilt directly at O without carrier masks (D16).",
             "- **compact_weather_oracle** (H3 302, H6/H12 308): the same 296 inputs plus realized prcp/tmean anomalies at O+1..O+min(H,6), "
             "treated as perfect forecasts available at O. H0 has no oracle run (shared baseline).", "",
             "Units: accuracies/precision/recall are row shares; MAE 3+ is a normalized population share; ordinal MAE is in phase steps; "
             "differences are raw differences in the same units (not percentage points). Evaluation weights are rows.", ""]
    for h in (0, 3, 6, 12):
        lines += [f"## Global, H = {h} months", "", head, sep]
        for _, r in wide[wide.horizon == h].sort_values(["arm", "period"]).iterrows():
            lines.append(f"| {r.arm} | {r.period} | {r.n_rows} | " + " | ".join(fmt(r.get(m)) for m in metrics) + " |")
        if h in wo.ORACLE_HORIZONS:
            dw = wide_metrics(gd[gd.horizon == h], ["period"], "delta")
            for _, r in dw.iterrows():
                lines.append(f"| **oracle - baseline** | {r.period} | | " + " | ".join(fmt(r.get(m)) for m in metrics) + " |")
        lines.append("")
    lines += ["## Regions 0-8: pooled 2022-2025 oracle - baseline", "",
              "Region = `area_id` join to `data/reference/area_id_country_region_mapping.csv` (numeric labels; no names inferred). "
              "Annual regional tables, support counts and undefined reasons are in `verification/regional_metrics.csv` / `regional_deltas.csv`.", ""]
    for h in wo.ORACLE_HORIZONS:
        lines += [f"### H = {h}", "", "| region | n | areas | obs 3+ | " + " | ".join(METRIC_LABELS[m] for m in metrics) + " |",
                  "|---:|---:|---:|---:|" + "---:|" * len(metrics)]
        part = rd[(rd.horizon == h) & (rd.period == "pooled")]
        for region in rpm.REGIONS:
            rr_ = part[part.region == region].set_index("metric")
            if rr_.empty:
                continue
            first = rr_.iloc[0]
            lines.append(f"| {region} | {first.n_rows} | {first.n_areas} | {first.observed_3plus} | " + " | ".join(fmt(rr_.loc[m, "delta"]) for m in metrics) + " |")
        lines.append("")
    comp = pd.read_csv(manifest["checks"]["files"]["old_new_comparability"])
    comp = comp[comp["status"] != "no_comparable_old_recipe"]
    corr = comp[comp["value_mismatch"] > 0]
    lines += ["## Inputs, coverage and limits", "",
              "- Old-vs-new comparability on matched keys (diagnostic, `input_checks/old_new_comparability.csv`), per horizon: "
              + "; ".join(f"H{h}: {len(g)} same-origin features compared, {int((g['value_mismatch'] > 0).sum())} with value differences "
                          f"({int(g['value_mismatch'].sum())} cells), {int(g['old_na_restored'].sum())} old-NA cells now carrying source "
                          f"values (D16 mask removal), {int(g['old_present_now_na'].sum())} old values now NA"
                          for h, g in comp.groupby("horizon")) + ".",
              "- Value differences are the intended numerical corrections of the compact recipes (exactly zero SD for constant "
              "windows, shift-centred same-month z for near-constant histories, no running-sum residue), not new definitions: "
              + ", ".join(sorted(f"H{r.horizon} {r.feature} ({int(r.value_mismatch)}, max |diff| {r.max_abs_diff:.3g})" for r in corr.itertuples()))
              + ". Restored old-NA cells are reported separately above.",
              "- Same-month z: cells whose prior same-month history is exactly constant are NA (zero SD); counts per source "
              f"{manifest['source_grids']['same_month_z_exact_constant_history_cells_set_na']}. Near-constant non-identical histories keep "
              "finite, possibly very large z values (no clipping).",
              "- Single seed (42) and one fit per annual block: differences are point estimates without intervals; no bootstrap was run.",
              *[f"- {x}" for x in manifest["limits"]], ""]
    (REPORTS / "report.md").write_text("\n".join(lines), encoding="utf-8")


# --------------------------------------------------------------------------- main


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--stage", choices=("inputs", "all"), required=True)
    parser.add_argument("--manifest", default=str(MANIFEST))
    args = parser.parse_args()
    problems: list = []
    checks = {"batches": 0, "artifacts_rehashed": 0, "models_reloaded": 0, "fit_rows_checked": 0, "max_model_replay_abs_diff": 0.0}
    identity = ov.frozen_checks(problems)
    identity["code_sha256"].update({p: legacy.sha(PROJECT_ROOT / p) for p in (
        "scripts/postprocessing/verify_compact_climate_weather_oracle.py", "src/ipcch/compact_features.py", "src/ipcch/regional_point_metrics.py",
        "scripts/preprocessing/build_compact_climate_weather_oracle_inputs.py", "scripts/modeling/run_compact_climate_weather_oracle_suite.py")})
    out_dir = RESULTS / ("input_verification" if args.stage == "inputs" else "verification")
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = Path(args.manifest)
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("version") != VERSION or manifest.get("status") != "COMPLETE" or manifest["parent_manifest"]["sha256"] != ov.FROZEN["parent_manifest_sha256"]:
        problems.append("compact manifest version/status/parent hash")
    for rel, digest in manifest["code_sha256"].items():
        if legacy.sha(PROJECT_ROOT / rel) != digest:
            problems.append(f"builder code changed since the input build: {rel}")
    parent = json.loads(PARENT_MANIFEST.read_text())
    # pinned identities, re-hashed from disk and compared with the frozen parent references, before any replay
    identities = {}
    for name, item in manifest["sources"].items():
        if item != {"path": parent["inputs"][name]["path"], "sha256": parent["inputs"][name]["sha256"]}:
            problems.append(f"source {name}: compact manifest entry differs from the frozen parent reference")
        identities[f"source {name}"] = legacy.sha(Path(item["path"]))
        if identities[f"source {name}"] != item["sha256"]:
            problems.append(f"source {name}: sha256 on disk differs")
    if set(manifest["sources"]) != {"interim", "climate_monthly", "climate_seasonal"}:
        problems.append(f"compact manifest sources {sorted(manifest['sources'])} are not the three pinned sources")
    if manifest["cohort"] != parent["cohort"] or legacy.sha(Path(manifest["cohort"]["path"])) != parent["cohort"]["sha256"]:
        problems.append("cohort entry/bytes differ from the frozen parent cohort")
    for name, item in manifest["contract"]["files"].items():
        identities[f"contract {name}"] = legacy.sha(Path(item["path"]))
        if identities[f"contract {name}"] != cpf.FROZEN_CONTRACT_SHA256.get(name) or item["sha256"] != cpf.FROZEN_CONTRACT_SHA256.get(name):
            problems.append(f"contract {name}: stable copy differs from the approved bytes")
    if set(manifest["contract"]["files"]) != set(cpf.FROZEN_CONTRACT_SHA256):
        problems.append("compact manifest does not bind every approved contract file")
    runtime = cpf.runtime_identity()
    fit_code = cpf.fit_code_sha256(PROJECT_ROOT)
    cohort = pd.read_csv(parent["cohort"]["path"])
    eval_keys = cohort.loc[cohort["eval_key"], KEYS].reset_index(drop=True)
    valid = cohort["share_valid"].to_numpy(dtype=bool)
    if osf.keys_sha256(eval_keys) != ov.FROZEN["eval_keys_sha256"] or \
            {int(k): int(v) for k, v in eval_keys["year"].value_counts().items()} != ov.FROZEN["eval_by_year"]:
        problems.append("frozen evaluation keys differ")
    source = pd.read_csv(parent["inputs"]["climate_monthly"]["path"], usecols=["admin_code", "year", "month", *wo.ORACLE_VARIABLES]).rename(columns={"admin_code": "area_id"})
    baselines, inventory, fit_digests, predictions, fitted, metric_replay = {}, [], {}, {}, {}, []
    for h in osf.HORIZONS:
        entry = manifest["horizons"][str(h)]
        for label, item in (("baseline dataset", entry["arms"][cpf.BASELINE_ARM]["dataset"]), ("season ledger", entry["season_ledger"]),
                            ("history ledger", entry["history_ledger"]), ("IDP ledger", entry["idp_ledger"]),
                            *((("oracle dataset", entry["arms"][cpf.ORACLE_ARM]["dataset"]), ("oracle ledger", entry["oracle_ledger"]))
                              if h in wo.ORACLE_HORIZONS else ())):
            if legacy.sha(Path(item["path"])) != item["sha256"]:
                problems.append(f"h{h}: {label} sha256 differs from the manifest")
        base = pd.read_csv(entry["arms"][cpf.BASELINE_ARM]["dataset"]["path"], float_precision="round_trip", low_memory=False)
        parent_features = parent["horizons"][str(h)]["arms"][cpf.PARENT_ARM]["features"]
        if entry["arms"][cpf.BASELINE_ARM]["features"] != cpf.run_features(parent_features, cpf.BASELINE_ARM, h):
            problems.append(f"h{h}: baseline manifest schema differs from the frozen contract")
        parent_data = pd.read_csv(parent["horizons"][str(h)]["dataset"]["path"], float_precision="round_trip", low_memory=False)
        bg = [c for c in parent_features if c in base.columns]
        if len(bg) != 63 or not np.array_equal(base[KEYS + ["overall_phase", *osf.SHARE_COLUMNS] + bg].to_numpy(dtype=float),
                                               parent_data[KEYS + ["overall_phase", *osf.SHARE_COLUMNS] + bg].to_numpy(dtype=float), equal_nan=True):
            problems.append(f"h{h}: keys/labels/background differ numerically from the parent inputs")
        del parent_data
        baselines[h] = base
        labels = ov.load_labels(base, cohort)
        runs = [(cpf.BASELINE_ARM, base)]
        if h in wo.ORACLE_HORIZONS:
            orc = pd.read_csv(entry["arms"][cpf.ORACLE_ARM]["dataset"]["path"], float_precision="round_trip", low_memory=False)
            if list(orc.columns[: base.shape[1]]) != list(base.columns) or not orc[list(base.columns)].equals(base):
                problems.append(f"h{h}: oracle input's baseline projection differs from the compact baseline")
            replay = independent_oracle(orc, h, source)
            for name, want in replay.items():
                if not np.array_equal(orc[name].to_numpy(dtype=float), want, equal_nan=True):
                    problems.append(f"h{h}: {name} differs from the independent source replay")
            if entry["arms"][cpf.ORACLE_ARM]["features"] != cpf.run_features(parent_features, cpf.ORACLE_ARM, h):
                problems.append(f"h{h}: oracle manifest schema differs from the frozen contract")
            runs.append((cpf.ORACLE_ARM, orc))
        if args.stage == "all":
            for arm, data in runs:
                features = entry["arms"][arm]["features"]
                run = run_dir(arm, h)
                pred, meta = ov.verify_run(run, run_id(arm, h), features, h, data, labels, valid, eval_keys, problems, checks, inventory, fit_digests)
                if meta is not None:
                    params = {k: ov.FROZEN["protocol"][k] for k in ("seed", "half_life_months", "phase_threshold", "n_jobs")}
                    want = cpf.fingerprint_payload(manifest, legacy.sha(manifest_path), arm, h, params, fit_code, runtime)
                    digest = hashlib.sha256(json.dumps(want, sort_keys=True).encode()).hexdigest()
                    if meta["fingerprint_payload"] != json.loads(json.dumps(want)) or meta["fingerprint"] != digest \
                            or meta["manifest"] != str(manifest_path):
                        diff = sorted(k for k in set(want) | set(meta["fingerprint_payload"]) if json.loads(json.dumps(want)).get(k) != meta["fingerprint_payload"].get(k))
                        problems.append(f"{run_id(arm, h)}: fingerprint differs from the current expected identity ({diff})")
                    for b in meta["batches"]:
                        if b["fingerprint"] != digest:
                            problems.append(f"{run_id(arm, h)} {b['block_year']}: batch fingerprint differs from the run identity")
                    checks["fingerprints_recomputed"] = checks.get("fingerprints_recomputed", 0) + 1
                    fitted[run_id(arm, h)] = meta["features"]
                if pred is not None:
                    predictions[(arm, h)] = pred
                    metric_replay += ov.metric_rows(arm, h, pred, run, problems)
                for year in YEARS:  # identical fitting keys, ages and weights to the parent reference protocol
                    mine = run / "batches" / str(year) / "fit_keys.csv.gz"
                    ref = PARENT_RUNS / f"{h}m" / "batches" / str(year) / "fit_keys.csv.gz"
                    if mine.exists() and not pd.read_csv(mine, float_precision="round_trip").equals(pd.read_csv(ref, float_precision="round_trip")):
                        problems.append(f"{run_id(arm, h)} {year}: fitting keys/ages/weights differ from the parent reference protocol")
                print(f"{run_id(arm, h)}: verified ({len(problems)} problems so far)", flush=True)
            del labels
            if h in wo.ORACLE_HORIZONS:
                del orc
        print(f"h{h}: inputs verified ({len(problems)} problems so far)", flush=True)
    independent = independent_replay(baselines, manifest, problems, checks)
    independent.to_csv(out_dir / "independent_feature_replay.csv", index=False)
    del baselines
    legacy_check = legacy_inventory_check(problems, out_dir)
    summary = {"stage": args.stage, "problems": problems, **checks, "legacy_no_overwrite": legacy_check, "pinned_identities": identities,
               "current_verification_identity": identity, "manifest": str(manifest_path), "manifest_sha256": legacy.sha(manifest_path),
               "tolerances": {"model_replay": "atol 1e-6, rtol 0", "metric_replay": "atol 1e-12, identical undefined mask",
                              "independent_feature_replay": "rtol 1e-7, atol 1e-9, identical NA", "csv_parsing": "float_precision=round_trip"}}
    if args.stage == "all":
        for (h, year), digests in fit_digests.items():
            if len(set(digests.values())) != 1:
                problems.append(f"h{h} {year}: fitting keys differ across arms")
        region_map = rpm.load_region_map(REGION_MAP, REGION_MAP_SHA256)
        metric_rows, partitions = [], {}
        for (arm, h), pred in predictions.items():
            pred = rpm.assign_regions(pred, region_map)
            predictions[(arm, h)] = pred
            partitions[run_id(arm, h)] = rpm.partition_check(pred)
            metric_rows += rpm.metric_rows(pred, run_id(arm, h), arm, h)
        for h in wo.ORACLE_HORIZONS:
            if (cpf.ORACLE_ARM, h) in predictions and (cpf.BASELINE_ARM, h) in predictions:
                rpm.align_pair(predictions[(cpf.ORACLE_ARM, h)], predictions[(cpf.BASELINE_ARM, h)])
        metrics = pd.DataFrame(metric_rows)
        # independent scikit-learn replay of every (run, scope, region, period) cell
        replay_cells = 0
        for (arm, h), pred in predictions.items():
            for scope in ("global", *rpm.REGIONS):
                group = pred if scope == "global" else pred[pred["region"] == scope]
                for period in rpm.PERIODS:
                    part = group if period == "pooled" else group[group["year"] == period]
                    ref = legacy.replay(part) if len(part) else {m: None for m in osf.ORIGIN_METRICS}
                    sel = metrics[(metrics.run_id == run_id(arm, h)) & (metrics.scope == ("global" if scope == "global" else "region"))
                                  & ((metrics.region.isna()) if scope == "global" else (metrics.region == scope)) & (metrics.period == str(period))]
                    for _, row in sel.iterrows():
                        a = ref[row.metric]
                        a = np.nan if a is None else float(a)
                        b = np.nan if pd.isna(row.value) else float(row.value)
                        if np.isnan(a) != np.isnan(b) or (not np.isnan(a) and abs(a - b) > 1e-12):
                            problems.append(f"{run_id(arm, h)} {scope} {period} {row.metric}: replay {a} vs table {b}")
                        replay_cells += 1
        checks["metric_cells_replayed"] = replay_cells
        metrics.to_csv(out_dir / "all_metrics_long.csv", index=False)
        metrics[metrics.scope == "global"].to_csv(out_dir / "global_metrics.csv", index=False)
        metrics[metrics.scope == "region"].to_csv(out_dir / "regional_metrics.csv", index=False)
        deltas = pd.DataFrame(rpm.delta_rows(metrics, cpf.ORACLE_ARM, cpf.BASELINE_ARM, wo.ORACLE_HORIZONS))
        deltas[deltas.scope == "global"].to_csv(out_dir / "global_deltas.csv", index=False)
        deltas[deltas.scope == "region"].to_csv(out_dir / "regional_deltas.csv", index=False)
        undefined = metrics[metrics["value"].isna()].groupby(["scope", "metric", "reason"]).size().rename("cells").reset_index()
        undefined.to_csv(out_dir / "undefined_reasons.csv", index=False)
        pd.DataFrame(metric_replay).to_csv(out_dir / "global_metric_replay_vs_runner.csv", index=False)
        pd.DataFrame(inventory).to_csv(out_dir / "artifact_inventory.csv", index=False)
        fully_verified = not problems and len(predictions) == len(cpf.RUN_PLAN) and checks["batches"] == 28 and checks["models_reloaded"] == 112
        codebook = write_codebook(manifest, fitted, problems, fully_verified) if len(fitted) == len(cpf.RUN_PLAN) else None
        timing = []
        for (arm, h) in cpf.RUN_PLAN:
            meta_path = run_dir(arm, h) / "run_metadata.json"
            if meta_path.exists():
                for b in json.loads(meta_path.read_text())["batches"]:
                    timing.append({"run_id": run_id(arm, h), "block_year": b["block_year"], "fit_rows": b["fit_rows"], "eval_rows": b["eval_rows"],
                                   "batch_seconds": b["batch_seconds"], "peak_rss_mb": b["peak_rss_mb"], **{f"fit_s_{k}": v for k, v in b["fit_seconds"].items()}})
        pd.DataFrame(timing).to_csv(out_dir / "batch_timing.csv", index=False)
        comparison_meta = {"version": VERSION, "runs": {run_id(a, h): str(run_dir(a, h)) for a, h in cpf.RUN_PLAN},
                           "manifest": str(manifest_path), "region_map": {"path": str(REGION_MAP), "sha256": REGION_MAP_SHA256},
                           "regions": list(rpm.REGIONS), "periods": [str(p) for p in rpm.PERIODS], "metrics": list(osf.ORIGIN_METRICS),
                           "contrast": f"{cpf.ORACLE_ARM} - {cpf.BASELINE_ARM} at H in {list(wo.ORACLE_HORIZONS)}; H0 is baseline only",
                           "pairing": "sorted (area_id, year, month); identical keys and truths required",
                           "region_partition_counts": partitions, "bootstrap": "not run (out of scope)", "regional_training": "none"}
        osf.dump_json(out_dir / "comparison_metadata.json", comparison_meta)
        summary.update({"runs_verified": len(predictions), "expected_runs": len(cpf.RUN_PLAN), "codebook": codebook, **checks,
                        "eval_keys": len(eval_keys), "eval_keys_sha256": osf.keys_sha256(eval_keys)})
        summary["passed"] = not problems and len(predictions) == len(cpf.RUN_PLAN) and checks["batches"] == 28 and checks["models_reloaded"] == 112
        write_report(metrics[metrics.scope == "global"], deltas[deltas.scope == "global"], metrics[metrics.scope == "region"],
                     deltas[deltas.scope == "region"], summary, manifest)
    else:
        summary["passed"] = not problems
    summary["problems"] = problems
    osf.dump_json(out_dir / "verification_summary.json", summary)
    print(json.dumps({k: v for k, v in summary.items() if k not in ("problems", "current_verification_identity")}, indent=2, default=str))
    for p in problems[:50]:
        print("PROBLEM:", p)
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
