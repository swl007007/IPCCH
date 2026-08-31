#!/usr/bin/env python3
"""Preflight and paired comparison for Spec 008 Nigeria weather-land reruns."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RELEASE = Path(
    "/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/Google fund/Analysis/1.Source Data/assembled_IPCCH/"
    "releases/nigeria_weather_land/nga-weather-land-20260825-v1"
)
SOURCE_ROOT = RELEASE.parents[2]
SCOPE_CONFIG = {
    "fs0": ("0m", "nga_scope_0m_model_ready_v1.csv", 537, "overall_phase_prev_observed_asof_s0"),
    "fs1": ("3m", "nga_scope_3m_model_ready_v1.csv", 538, None),
    "fs2": ("6m", "nga_scope_6m_model_ready_v1.csv", 538, "overall_phase_prev_observed_asof_s6"),
}
DEPENDENCIES = {
    "release_manifest": RELEASE / "release_manifest.json",
    "country_lookup": SOURCE_ROOT / "country_area_id_lookup.csv",
    "identifier_source": SOURCE_ROOT / "raw/IPCCH_2026_completed.csv",
    "runner": PROJECT_ROOT / "scripts/modeling/run_deep_feature_weight_decay_forecasting.py",
    "selector": PROJECT_ROOT / "src/ipcch/forecasting_weight_decay.py",
    "hyperparameters_standard": PROJECT_ROOT / "configs/forecasting_hyperparameters.json",
    "hyperparameters_p3": PROJECT_ROOT / "configs/forecasting_hyperparameters_p3.json",
}
EXPECTED_RELEASE_HASH = "f5eec437693a4e28ba32ce3c39ba581fa7532023ca527e2300a67921c8a64573"
KEYS = ["area_id", "year", "month"]
TARGET_PERCENT_COLUMNS = [f"phase{i}_percent" for i in range(1, 6)]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_output(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=PROJECT_ROOT, text=True).strip()


def baseline_dir(label: str) -> Path:
    return PROJECT_ROOT / "results/experiments/deep_feature_weight_decay_forecasting" / (
        f"{label}_nigeria_identifier_features_threshold_0_20"
    )


def new_dir(label: str) -> Path:
    return PROJECT_ROOT / "results/experiments/deep_feature_weight_decay_forecasting" / (
        f"{label}_nigeria_weather_land_v1_threshold_0_20_seed_42"
    )


def eligible_evaluation_keys(df: pd.DataFrame) -> set[tuple[object, int, int]]:
    ready = df.loc[df[TARGET_PERCENT_COLUMNS].notna().all(axis=1), KEYS].copy()
    ready = ready.loc[ready["year"].isin([2022, 2023, 2024, 2025])]
    return set(ready.itertuples(index=False, name=None))


def historical_keys(label: str) -> set[tuple[object, int, int]]:
    frames = [
        pd.read_csv(baseline_dir(label) / f"predictions/predictions_{year}.csv", usecols=KEYS)
        for year in (2022, 2023, 2024, 2025)
    ]
    return set(pd.concat(frames, ignore_index=True).itertuples(index=False, name=None))


def preflight(output: Path) -> None:
    release_manifest = json.loads((RELEASE / "release_manifest.json").read_text(encoding="utf-8"))
    checks: dict[str, object] = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "release_id": "nga-weather-land-20260825-v1",
        "git_head": git_output("rev-parse", "HEAD"),
        "git_status_porcelain": git_output("status", "--porcelain").splitlines(),
        "dependencies": {},
        "scopes": {},
    }
    for name, path in DEPENDENCIES.items():
        if not path.exists():
            raise FileNotFoundError(path)
        checks["dependencies"][name] = {"path": str(path), "sha256": sha256(path)}
    if checks["dependencies"]["release_manifest"]["sha256"] != EXPECTED_RELEASE_HASH:
        raise ValueError("Release manifest SHA-256 does not match the frozen spec")
    if not release_manifest.get("release_ready") or release_manifest.get("critical_failures"):
        raise ValueError("Release manifest is not ready")

    for fs, (label, filename, expected_columns, expected_all_null) in SCOPE_CONFIG.items():
        path = RELEASE / "model_ready" / filename
        df = pd.read_csv(path)
        summary = json.loads((RELEASE / "audits" / f"nga_scope_{label}_validation_summary_v1.json").read_text())
        added = summary["added_features"]
        all_null = sorted(df.columns[df.isna().all()].tolist())
        duplicate_count = int(df.duplicated(KEYS).sum())
        new_keys = eligible_evaluation_keys(df)
        old_keys = historical_keys(label)
        scope_check = {
            "dataset": str(path),
            "sha256": sha256(path),
            "rows": int(len(df)),
            "columns": int(len(df.columns)),
            "areas": int(df["area_id"].nunique()),
            "duplicate_keys": duplicate_count,
            "date_min": f"{int(df.year.min()):04d}-{int(df.loc[df.year.idxmin(), 'month']):02d}",
            "date_max_year": int(df.year.max()),
            "added_features": added,
            "added_feature_count": len(added),
            "added_features_all_nonempty": bool(df[added].notna().any().all()),
            "all_null_columns": all_null,
            "eligible_evaluation_key_count": len(new_keys),
            "historical_evaluation_key_count": len(old_keys),
            "evaluation_keys_equal": new_keys == old_keys,
            "new_only_keys": sorted(new_keys - old_keys),
            "old_only_keys": sorted(old_keys - new_keys),
            "planned_result_dir": str(new_dir(label)),
            "planned_result_dir_exists": new_dir(label).exists(),
        }
        expected_nulls = [] if expected_all_null is None else [expected_all_null]
        assertions = {
            "rows_6538": len(df) == 6538,
            "areas_545": df["area_id"].nunique() == 545,
            "columns_expected": len(df.columns) == expected_columns,
            "no_duplicate_keys": duplicate_count == 0,
            "added_16": len(added) == 16,
            "added_nonempty": scope_check["added_features_all_nonempty"],
            "all_null_contract": all_null == expected_nulls,
            "evaluation_keys_equal": new_keys == old_keys,
            "output_clear": not new_dir(label).exists(),
        }
        scope_check["assertions"] = assertions
        if not all(assertions.values()):
            raise ValueError(f"Preflight failed for {fs}: {assertions}")
        checks["scopes"][fs] = scope_check

    spi_qa = pd.read_csv(RELEASE / "spi/nigeria_era5_drought_spi_area_month_scale_qa_v1.csv")
    status_column = next(column for column in ("status", "qa_status", "value_status") if column in spi_qa.columns)
    checks["spi_qa_status_counts"] = {
        str(key): int(value) for key, value in spi_qa[status_column].value_counts(dropna=False).items()
    }
    checks["status"] = "PASS"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(checks, indent=2, default=str) + "\n", encoding="utf-8")
    print(f"Preflight PASS: {output}")


def compare(output: Path) -> None:
    rows = []
    for fs, (label, _, _, _) in SCOPE_CONFIG.items():
        for year in (2022, 2023, 2024, 2025):
            old_path = baseline_dir(label) / f"predictions/predictions_{year}.csv"
            new_path = new_dir(label) / f"predictions/predictions_{year}.csv"
            old = pd.read_csv(old_path)
            new = pd.read_csv(new_path)
            merged = old.merge(new, on=KEYS, suffixes=("_old", "_new"), validate="one_to_one")
            if len(merged) != len(old) or len(merged) != len(new):
                raise ValueError(f"Prediction keys differ for {fs} {year}")
            rows.append(
                {
                    "scope": label,
                    "test_year": year,
                    "rows": len(merged),
                    "mae_old": float((merged["overall_phase_old"] - merged["overall_phase_pred_old"]).abs().mean()),
                    "mae_new": float((merged["overall_phase_new"] - merged["overall_phase_pred_new"]).abs().mean()),
                }
            )
    result = pd.DataFrame(rows)
    result["mae_change_new_minus_old"] = result["mae_new"] - result["mae_old"]
    output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output, index=False)
    provenance = json.loads((PROJECT_ROOT / "results/preflight/nga-weather-land-20260825-v1/preflight_manifest.json").read_text())
    for _, (label, _, _, _) in SCOPE_CONFIG.items():
        metadata = new_dir(label) / "metadata/experiment_provenance.json"
        metadata.write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    print(result.to_string(index=False))
    print(f"Comparison written: {output}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("preflight", "compare"))
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.mode == "preflight":
        preflight(args.output)
    else:
        compare(args.output)


if __name__ == "__main__":
    main()
