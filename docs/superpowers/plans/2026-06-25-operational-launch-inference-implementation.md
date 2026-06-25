# Operational Launch Inference Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a production inference package that loads fixed 0m, 6m, and 12m launch models, validates one monthly IPCCH input table, applies a machine-readable feature contract, and writes six primary delivery files.

**Architecture:** Keep training and export in the research `IPCCH` repository, then copy only the pure inference runtime and exported model package into `IPCCH_monthly_operational`. The research side owns temporal training/export, feature eligibility, and model package creation; the production side owns monthly input validation, feature construction, scoring, phase decoding, atomic delivery writing, and audit reports.

**Tech Stack:** Python 3, pandas, xgboost, pytest/unittest, existing `ipcch.launch_nowcasting` helpers, existing production `workflow_config.py` path conventions, GeoPandas/matplotlib only where current map rendering already requires them.

---

## Scope And Repository Roots

- Research repo root: `/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/Google fund/Analysis/2.source_code/Step5_Geo_RF_trial/IPCCH`
- Production repo root: `/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/IPCCH_monthly_operational`
- Design spec: `docs/superpowers/specs/2026-06-25-operational-launch-inference-design.md`
- Do not edit unrelated dirty files. `AGENTS.md` is already dirty in the research repo and should remain untouched unless the user explicitly requests otherwise.

## File Structure

Research repo additions:

- Create `src/ipcch/operational_contract.py`
  - Owns temporal helpers, feature contract schema validation, feature eligibility checks, threshold decoding, and package metadata validation that should be tested before export.
- Create `scripts/modeling/export_operational_launch_package.py`
  - Runs or packages scope `0m`, `6m`, and `12m` launch models and exports production artifacts.
- Create `tests/unit/test_operational_contract.py`
  - Unit tests for temporal contract, feature contract schema, feature eligibility, and phase decoding.
- Create `tests/smoke/test_export_operational_launch_package_cli.py`
  - CLI smoke tests using tiny prebuilt artifacts; no heavy training.
- Modify `src/ipcch/launch_nowcasting.py`
  - Add optional model metadata save/load support and canonical score/output aliases without changing existing launch behavior by default.
- Modify `scripts/modeling/run_launch_nowcasting_2026_04.py`
  - Add flags needed by the exporter only if existing Mode 1/Mode 2 cannot pass metadata cleanly.

Production repo additions:

- Create `model_pipeline/run_operational_launch_inference.py`
  - Non-interactive CLI entrypoint.
- Create `model_pipeline/ipcch_launch_runtime/__init__.py`
- Create `model_pipeline/ipcch_launch_runtime/adapters.py`
  - Monthly input contract validation, ID normalization, null parsing, row identity.
- Create `model_pipeline/ipcch_launch_runtime/feature_contract.py`
  - Feature contract parsing, dtype coercion, fill rules, compatibility reports.
- Create `model_pipeline/ipcch_launch_runtime/model_package.py`
  - Model package discovery, metadata validation, xgboost model loading.
- Create `model_pipeline/ipcch_launch_runtime/inference.py`
  - Feature matrix construction, scoring, thresholding, phase decoding.
- Create `model_pipeline/ipcch_launch_runtime/outputs.py`
  - Output path planning, temporary writes, atomic commit, run summary.
- Create `model_pipeline/ipcch_launch_runtime/visualization.py`
  - Thin adapter around current map behavior; keep map rendering details minimal.
- Create `tests/test_operational_launch_input_contract.py`
- Create `tests/test_operational_launch_feature_contract.py`
- Create `tests/test_operational_launch_inference.py`
- Create `tests/test_operational_launch_cli.py`
- Modify `.gitignore`
  - Ignore generated `Outcome/ipcch_unified/predictions/` files and large model artifacts if they should stay local.
- Modify `README.md` or `docs/03_workflow_runbook.md`
  - Add one short operational inference command after implementation is verified.

---

### Task 1: Research Temporal And Feature Contract Helpers

**Files:**
- Create: `src/ipcch/operational_contract.py`
- Create: `tests/unit/test_operational_contract.py`

- [ ] **Step 1: Write failing tests for temporal contract and feature contract schema**

Add `tests/unit/test_operational_contract.py`:

```python
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from ipcch import operational_contract as oc


def test_april_2026_baseline_target_months():
    rows = oc.target_periods_for_feature_month("2026-04", [0, 6, 12])
    assert rows == {
        0: "2026-04",
        6: "2026-10",
        12: "2027-04",
    }


def test_scope0_training_cutoff_excludes_april_2026():
    assert oc.training_cutoff_for_feature_month("2026-04") == "2026-04-01"


def test_feature_contract_requires_one_row_per_model_feature():
    feature_columns = ["rain", "static_crop"]
    contract = pd.DataFrame(
        [
            {
                "feature_name": "rain",
                "scope_months": "all",
                "category": "required",
                "source_column": "Rainf_f_tavg_mean",
                "dtype": "float",
                "required_in_input": True,
                "missing_tolerance": 0.0,
                "fill_method": "none",
                "fill_value_or_stat_key": "",
                "lookup_asset": "",
                "derive_function": "",
                "as_of_policy": "feature_month_end",
                "notes": "monthly rainfall",
            },
            {
                "feature_name": "static_crop",
                "scope_months": "all",
                "category": "static_join",
                "source_column": "",
                "dtype": "integer",
                "required_in_input": False,
                "missing_tolerance": 0.0,
                "fill_method": "static lookup",
                "fill_value_or_stat_key": "",
                "lookup_asset": "lookups/static_features.csv",
                "derive_function": "",
                "as_of_policy": "static",
                "notes": "crop class",
            },
        ]
    )
    report = oc.validate_feature_contract(contract, feature_columns)
    assert report["status"] == "passed"
    assert report["model_feature_count"] == 2


def test_unsupported_feature_in_model_columns_fails():
    contract = pd.DataFrame(
        [
            {
                "feature_name": "bad_target",
                "scope_months": "all",
                "category": "unsupported",
                "source_column": "overall_phase",
                "dtype": "float",
                "required_in_input": False,
                "missing_tolerance": 0.0,
                "fill_method": "none",
                "fill_value_or_stat_key": "",
                "lookup_asset": "",
                "derive_function": "",
                "as_of_policy": "not_allowed",
                "notes": "target leakage",
            }
        ]
    )
    with pytest.raises(oc.OperationalContractError, match="unsupported"):
        oc.validate_feature_contract(contract, ["bad_target"])


def test_phase_decoding_uses_scores_threshold_and_top_down_rule():
    pred = pd.DataFrame(
        {
            "area_id": ["A", "B"],
            "phase2_worse_score": [0.7, 0.1],
            "phase3_worse_score": [0.6, 0.1],
            "phase4_worse_score": [0.1, 0.1],
            "phase5_worse_score": [0.1, 0.1],
        }
    )
    decoded = oc.decode_phase_predictions(pred, {"default": 0.2}, monotonicity_policy="fail")
    assert decoded["phase2_worse_pred"].tolist() == [1, 0]
    assert decoded["phase3_worse_pred"].tolist() == [1, 0]
    assert decoded["overall_phase_pred"].tolist() == [3, 1]


def test_non_monotonic_predictions_fail_when_policy_is_fail():
    pred = pd.DataFrame(
        {
            "area_id": ["A"],
            "phase2_worse_score": [0.1],
            "phase3_worse_score": [0.9],
            "phase4_worse_score": [0.1],
            "phase5_worse_score": [0.1],
        }
    )
    with pytest.raises(oc.OperationalContractError, match="non-monotonic"):
        oc.decode_phase_predictions(pred, {"default": 0.2}, monotonicity_policy="fail")


def test_feature_eligibility_rejects_targets_forecast_weather_and_future_policy():
    contract = pd.DataFrame(
        [
            {
                "feature_name": "phase3_percent",
                "scope_months": "all",
                "category": "required",
                "source_column": "phase3_percent",
                "dtype": "float",
                "required_in_input": True,
                "missing_tolerance": 0.0,
                "fill_method": "none",
                "fill_value_or_stat_key": "",
                "lookup_asset": "",
                "derive_function": "",
                "as_of_policy": "feature_month_end",
                "notes": "target leakage",
            },
            {
                "feature_name": "Rainf_f_tavg_mean_forecast_proxy",
                "scope_months": "6",
                "category": "required",
                "source_column": "Rainf_f_tavg_mean_forecast_proxy",
                "dtype": "float",
                "required_in_input": True,
                "missing_tolerance": 0.0,
                "fill_method": "none",
                "fill_value_or_stat_key": "",
                "lookup_asset": "",
                "derive_function": "",
                "as_of_policy": "forecast_weather",
                "notes": "forecasted weather disabled",
            },
            {
                "feature_name": "rolling_after_target",
                "scope_months": "12",
                "category": "required",
                "source_column": "rolling_after_target",
                "dtype": "float",
                "required_in_input": True,
                "missing_tolerance": 0.0,
                "fill_method": "none",
                "fill_value_or_stat_key": "",
                "lookup_asset": "",
                "derive_function": "",
                "as_of_policy": "post_target",
                "notes": "future-dependent rolling feature",
            },
        ]
    )
    with pytest.raises(oc.OperationalContractError, match="production-safe"):
        oc.validate_production_safe_feature_contract(contract)
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
PYTHONPATH=src pytest tests/unit/test_operational_contract.py -q
```

Expected: FAIL during import because `ipcch.operational_contract` does not exist.

- [ ] **Step 3: Implement the contract helper module**

Create `src/ipcch/operational_contract.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import pandas as pd


APPROVED_SCOPES = {"0", "6", "12", "all"}
APPROVED_CATEGORIES = {
    "required",
    "derived",
    "static_join",
    "carry_forward",
    "median_impute",
    "unsupported",
    "excluded",
}
APPROVED_DTYPES = {"string", "integer", "float", "boolean", "categorical"}
APPROVED_FILL_METHODS = {"none", "median", "static lookup", "carry forward", "derived"}
TARGET_OR_LABEL_PATTERNS = (
    "overall_phase",
    "phase1_percent",
    "phase2_percent",
    "phase3_percent",
    "phase4_percent",
    "phase5_percent",
    "phase2_worse",
    "phase3_worse",
    "phase4_worse",
    "phase5_worse",
)
PROHIBITED_AS_OF_POLICIES = {"post_target", "target_period", "after_feature_month", "forecast_weather"}
FORECAST_WEATHER_MARKERS = ("forecast_proxy", "forecasted_weather")
CONTRACT_COLUMNS = (
    "feature_name",
    "scope_months",
    "category",
    "source_column",
    "dtype",
    "required_in_input",
    "missing_tolerance",
    "fill_method",
    "fill_value_or_stat_key",
    "lookup_asset",
    "derive_function",
    "as_of_policy",
    "notes",
)
SCORE_COLUMNS = {
    2: "phase2_worse_score",
    3: "phase3_worse_score",
    4: "phase4_worse_score",
    5: "phase5_worse_score",
}
PRED_COLUMNS = {
    2: "phase2_worse_pred",
    3: "phase3_worse_pred",
    4: "phase4_worse_pred",
    5: "phase5_worse_pred",
}


class OperationalContractError(ValueError):
    pass


def _period(value: str) -> pd.Period:
    try:
        return pd.Period(value, freq="M")
    except Exception as exc:
        raise OperationalContractError(f"Invalid feature month: {value!r}") from exc


def target_periods_for_feature_month(feature_month: str, scopes: Sequence[int]) -> dict[int, str]:
    base = _period(feature_month)
    return {int(scope): str(base + int(scope)) for scope in scopes}


def training_cutoff_for_feature_month(feature_month: str) -> str:
    base = _period(feature_month)
    return base.to_timestamp().date().isoformat()


def validate_feature_contract(contract: pd.DataFrame, feature_columns: Sequence[str]) -> dict[str, object]:
    missing_cols = [c for c in CONTRACT_COLUMNS if c not in contract.columns]
    if missing_cols:
        raise OperationalContractError("feature_contract.csv missing columns: " + ", ".join(missing_cols))

    features = list(feature_columns)
    duplicated = contract.loc[contract["feature_name"].duplicated(), "feature_name"].astype(str).tolist()
    if duplicated:
        raise OperationalContractError("Duplicate contract feature rows: " + ", ".join(sorted(set(duplicated))))

    by_name = contract.set_index("feature_name", drop=False)
    missing_contract = [name for name in features if name not in by_name.index]
    if missing_contract:
        raise OperationalContractError("Model features missing from contract: " + ", ".join(missing_contract))

    invalid_scope = sorted(set(by_name["scope_months"].astype(str)) - APPROVED_SCOPES)
    if invalid_scope:
        raise OperationalContractError("Invalid scope_months values: " + ", ".join(invalid_scope))

    invalid_category = sorted(set(by_name["category"].astype(str)) - APPROVED_CATEGORIES)
    if invalid_category:
        raise OperationalContractError("Invalid category values: " + ", ".join(invalid_category))

    invalid_dtype = sorted(set(by_name["dtype"].astype(str)) - APPROVED_DTYPES)
    if invalid_dtype:
        raise OperationalContractError("Invalid dtype values: " + ", ".join(invalid_dtype))

    invalid_fill = sorted(set(by_name["fill_method"].astype(str)) - APPROVED_FILL_METHODS)
    if invalid_fill:
        raise OperationalContractError("Invalid fill_method values: " + ", ".join(invalid_fill))

    unsupported = by_name.loc[features]
    blocked = unsupported[unsupported["category"].isin(["unsupported", "excluded"])]["feature_name"].astype(str).tolist()
    if blocked:
        raise OperationalContractError("Model references unsupported or excluded feature(s): " + ", ".join(blocked))

    extra = [name for name in by_name.index.astype(str).tolist() if name not in features]
    return {
        "status": "passed",
        "model_feature_count": len(features),
        "contract_feature_count": int(len(contract)),
        "ignored_extra_features": extra,
    }


def validate_production_safe_feature_contract(contract: pd.DataFrame) -> dict[str, object]:
    problems: list[str] = []
    for _, row in contract.iterrows():
        feature = str(row["feature_name"])
        source = str(row.get("source_column", "") or "")
        as_of = str(row.get("as_of_policy", "") or "")
        lower_names = (feature.lower(), source.lower())
        if any(pattern in name for name in lower_names for pattern in TARGET_OR_LABEL_PATTERNS):
            problems.append(f"{feature}: target or label leakage")
        if any(marker in name for name in lower_names for marker in FORECAST_WEATHER_MARKERS):
            problems.append(f"{feature}: forecasted-weather proxy disabled")
        if as_of in PROHIBITED_AS_OF_POLICIES:
            problems.append(f"{feature}: prohibited as_of_policy {as_of}")
    if problems:
        raise OperationalContractError("Feature contract is not production-safe: " + "; ".join(problems))
    return {"status": "passed", "checked_feature_count": int(len(contract))}


def _threshold_for_phase(thresholds: Mapping[str, float], phase: int) -> float:
    key = f"phase{phase}_worse"
    if key in thresholds:
        return float(thresholds[key])
    return float(thresholds["default"])


def decode_phase_predictions(
    scores: pd.DataFrame,
    thresholds: Mapping[str, float],
    *,
    monotonicity_policy: str,
) -> pd.DataFrame:
    if monotonicity_policy not in {"fail", "cummax"}:
        raise OperationalContractError("monotonicity_policy must be 'fail' or 'cummax'")
    out = scores.copy()
    for phase, score_col in SCORE_COLUMNS.items():
        if score_col not in out.columns:
            raise OperationalContractError(f"Missing score column: {score_col}")
        out[PRED_COLUMNS[phase]] = (pd.to_numeric(out[score_col], errors="raise") >= _threshold_for_phase(thresholds, phase)).astype(int)

    pred = out[[PRED_COLUMNS[p] for p in (2, 3, 4, 5)]].copy()
    invalid = (
        (pred[PRED_COLUMNS[3]] > pred[PRED_COLUMNS[2]])
        | (pred[PRED_COLUMNS[4]] > pred[PRED_COLUMNS[3]])
        | (pred[PRED_COLUMNS[5]] > pred[PRED_COLUMNS[4]])
    )
    if invalid.any() and monotonicity_policy == "fail":
        raise OperationalContractError("Thresholded worse-or-equal predictions are non-monotonic")
    if invalid.any() and monotonicity_policy == "cummax":
        for lower, higher in ((4, 5), (3, 4), (2, 3)):
            out[PRED_COLUMNS[lower]] = out[[PRED_COLUMNS[lower], PRED_COLUMNS[higher]]].max(axis=1)

    out["overall_phase_pred"] = 1
    for phase in (5, 4, 3, 2):
        out.loc[out[PRED_COLUMNS[phase]] == 1, "overall_phase_pred"] = phase
    return out
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
PYTHONPATH=src pytest tests/unit/test_operational_contract.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/ipcch/operational_contract.py tests/unit/test_operational_contract.py
git commit -m "feat: add operational launch contract helpers"
```

---

### Task 2: Research Launch Metadata And Export Package CLI

**Files:**
- Modify: `src/ipcch/launch_nowcasting.py`
- Create: `scripts/modeling/export_operational_launch_package.py`
- Create: `tests/smoke/test_export_operational_launch_package_cli.py`

- [ ] **Step 1: Write failing smoke test for metadata-only package assembly**

Add `tests/smoke/test_export_operational_launch_package_cli.py`:

```python
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _write_scope_artifacts(root: Path, scope: int) -> None:
    scope_dir = root / f"scope_{scope}m"
    scope_dir.mkdir(parents=True)
    for target in ("phase2_worse", "phase3_worse", "phase4_worse", "phase5_worse"):
        (scope_dir / f"{target}_model.json").write_text("{}", encoding="utf-8")
    (scope_dir / "feature_columns.json").write_text(json.dumps(["rain"]), encoding="utf-8")
    (scope_dir / "feature_contract.csv").write_text(
        "\n".join(
            [
                "feature_name,scope_months,category,source_column,dtype,required_in_input,missing_tolerance,fill_method,fill_value_or_stat_key,lookup_asset,derive_function,as_of_policy,notes",
                "rain,all,required,Rainf_f_tavg_mean,float,True,0.0,none,,,,feature_month_end,monthly rain",
            ]
        ),
        encoding="utf-8",
    )


def test_export_operational_launch_package_manifest_from_existing_artifacts(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    for scope in (0, 6, 12):
        _write_scope_artifacts(source, scope)
    out = tmp_path / "package"
    cmd = [
        sys.executable,
        "scripts/modeling/export_operational_launch_package.py",
        "--from-existing-artifacts",
        str(source),
        "--output-package",
        str(out),
        "--feature-month",
        "2026-04",
        "--package-id",
        "launch_2026_04_test",
    ]
    result = subprocess.run(cmd, check=True, text=True, capture_output=True)
    manifest = json.loads((out / "model_package_manifest.json").read_text(encoding="utf-8"))
    assert manifest["package_id"] == "launch_2026_04_test"
    assert manifest["feature_month"] == "2026-04"
    assert manifest["forecasted_weather"] == {"enabled": False}
    assert manifest["scopes"] == [0, 6, 12]
    assert (out / "scope_0m" / "feature_columns.json").exists()
    assert "model_package_manifest.json" in result.stdout
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
PYTHONPATH=src pytest tests/smoke/test_export_operational_launch_package_cli.py -q
```

Expected: FAIL because `scripts/modeling/export_operational_launch_package.py` does not exist.

- [ ] **Step 3: Add package export CLI**

Create `scripts/modeling/export_operational_launch_package.py`:

```python
#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ipcch import operational_contract as oc


TARGETS = ("phase2_worse", "phase3_worse", "phase4_worse", "phase5_worse")
SCOPES = (0, 6, 12)


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Export IPCCH operational launch model package.")
    p.add_argument("--from-existing-artifacts", required=True, help="Directory containing scope_0m, scope_6m, and scope_12m artifacts.")
    p.add_argument("--output-package", required=True, help="Destination model package directory.")
    p.add_argument("--feature-month", required=True, help="Baseline feature month YYYY-MM.")
    p.add_argument("--package-id", required=True)
    p.add_argument("--overwrite", action="store_true")
    return p.parse_args(argv)


def _copy_scope(source_root: Path, out_root: Path, scope: int) -> dict[str, object]:
    source = source_root / f"scope_{scope}m"
    dest = out_root / f"scope_{scope}m"
    if not source.exists():
        raise FileNotFoundError(f"Missing scope artifact directory: {source}")
    dest.mkdir(parents=True, exist_ok=True)
    required = [source / f"{target}_model.json" for target in TARGETS] + [
        source / "feature_columns.json",
        source / "feature_contract.csv",
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing required scope artifacts: " + "; ".join(missing))
    for path in required:
        shutil.copy2(path, dest / path.name)
    feature_columns = json.loads((dest / "feature_columns.json").read_text(encoding="utf-8"))
    contract = __import__("pandas").read_csv(dest / "feature_contract.csv")
    report = oc.validate_feature_contract(contract, feature_columns)
    eligibility = oc.validate_production_safe_feature_contract(contract)
    metadata = {
        "scope_months": scope,
        "feature_month": None,
        "target_month": None,
        "thresholds": {"default": 0.2},
        "monotonicity_policy": "fail",
        "feature_contract_validation": report,
        "feature_eligibility_validation": eligibility,
    }
    (dest / "model_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return {"scope_months": scope, "feature_count": len(feature_columns)}


def run(args) -> int:
    source = Path(args.from_existing_artifacts)
    out = Path(args.output_package)
    if out.exists() and not args.overwrite:
        raise FileExistsError(f"Output package exists; pass --overwrite to replace: {out}")
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    target_periods = oc.target_periods_for_feature_month(args.feature_month, SCOPES)
    scopes = []
    for scope in SCOPES:
        item = _copy_scope(source, out, scope)
        item["feature_month"] = args.feature_month
        item["target_month"] = target_periods[scope]
        metadata_path = out / f"scope_{scope}m" / "model_metadata.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        metadata["feature_month"] = args.feature_month
        metadata["target_month"] = target_periods[scope]
        metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        scopes.append(scope)
    manifest = {
        "package_id": args.package_id,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "feature_month": args.feature_month,
        "target_periods": {str(k): v for k, v in target_periods.items()},
        "scopes": list(SCOPES),
        "forecasted_weather": {"enabled": False},
    }
    (out / "model_package_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(out / "model_package_manifest.json")
    return 0


def main(argv=None) -> int:
    return run(parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run smoke test**

Run:

```bash
PYTHONPATH=src pytest tests/smoke/test_export_operational_launch_package_cli.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/modeling/export_operational_launch_package.py tests/smoke/test_export_operational_launch_package_cli.py
git commit -m "feat: add operational launch package exporter"
```

---

### Task 3: Production Monthly Input Contract Runtime

**Files:**
- Create: `/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/IPCCH_monthly_operational/model_pipeline/ipcch_launch_runtime/__init__.py`
- Create: `/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/IPCCH_monthly_operational/model_pipeline/ipcch_launch_runtime/adapters.py`
- Create: `/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/IPCCH_monthly_operational/tests/test_operational_launch_input_contract.py`

- [ ] **Step 1: Write failing input contract tests**

Add `/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/IPCCH_monthly_operational/tests/test_operational_launch_input_contract.py`:

```python
import unittest

import pandas as pd

from model_pipeline.ipcch_launch_runtime import adapters


class OperationalLaunchInputContractTests(unittest.TestCase):
    def test_validates_single_feature_month_and_string_ids(self):
        df = pd.DataFrame(
            {
                "admin_code": ["001", "002"],
                "year": [2026, 2026],
                "month": [7, 7],
                "Rainf_f_tavg_mean": [1.2, 3.4],
            }
        )
        validated, report = adapters.validate_monthly_input(df, feature_month="2026-07")
        self.assertEqual(["001", "002"], validated["area_id"].tolist())
        self.assertEqual("passed", report["status"])
        self.assertEqual("2026-07", report["feature_month"])

    def test_feature_month_mismatch_fails(self):
        df = pd.DataFrame({"admin_code": ["001"], "year": [2026], "month": [7]})
        with self.assertRaisesRegex(adapters.InputContractError, "feature-month"):
            adapters.validate_monthly_input(df, feature_month="2026-08")

    def test_duplicate_area_id_fails(self):
        df = pd.DataFrame({"area_id": ["001", "001"], "year": [2026, 2026], "month": [7, 7]})
        with self.assertRaisesRegex(adapters.InputContractError, "Duplicate area_id"):
            adapters.validate_monthly_input(df, feature_month="2026-07")

    def test_area_id_and_admin_code_must_match_when_both_present(self):
        df = pd.DataFrame({"area_id": ["001"], "admin_code": ["002"], "year": [2026], "month": [7]})
        with self.assertRaisesRegex(adapters.InputContractError, "map consistently"):
            adapters.validate_monthly_input(df, feature_month="2026-07")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run from the production repo:

```bash
cd "/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/IPCCH_monthly_operational"
python3 -m unittest tests.test_operational_launch_input_contract -v
```

Expected: FAIL because `model_pipeline.ipcch_launch_runtime.adapters` does not exist.

- [ ] **Step 3: Implement input adapter**

Create `/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/IPCCH_monthly_operational/model_pipeline/ipcch_launch_runtime/__init__.py`:

```python
"""Runtime helpers for IPCCH operational launch inference."""
```

Create `/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/IPCCH_monthly_operational/model_pipeline/ipcch_launch_runtime/adapters.py`:

```python
from __future__ import annotations

import pandas as pd


NULL_TOKENS = ("", "NA", "N/A", "nan", "NaN", "NULL", "None")


class InputContractError(ValueError):
    pass


def _normalize_id(series: pd.Series) -> pd.Series:
    return series.astype("string").str.strip()


def _period_from_columns(df: pd.DataFrame) -> str:
    if "year" not in df.columns or "month" not in df.columns:
        raise InputContractError("Input must contain year and month columns")
    periods = pd.PeriodIndex(
        pd.to_numeric(df["year"], errors="raise").astype(int).astype(str)
        + "-"
        + pd.to_numeric(df["month"], errors="raise").astype(int).astype(str).str.zfill(2),
        freq="M",
    )
    unique = sorted(set(periods.astype(str)))
    if len(unique) != 1:
        raise InputContractError("Input must contain exactly one feature month")
    return unique[0]


def validate_monthly_input(df: pd.DataFrame, *, feature_month: str) -> tuple[pd.DataFrame, dict[str, object]]:
    result = df.replace(list(NULL_TOKENS), pd.NA).copy()
    observed_month = _period_from_columns(result)
    if observed_month != feature_month:
        raise InputContractError(f"CLI feature-month {feature_month} does not match input feature-month {observed_month}")
    has_area = "area_id" in result.columns
    has_admin = "admin_code" in result.columns
    if not has_area and not has_admin:
        raise InputContractError("Input must contain either area_id or admin_code")
    if has_area:
        result["area_id"] = _normalize_id(result["area_id"])
    if has_admin:
        result["admin_code"] = _normalize_id(result["admin_code"])
    if has_area and has_admin and not result["area_id"].equals(result["admin_code"]):
        raise InputContractError("area_id and admin_code must map consistently")
    if not has_area:
        result.insert(0, "area_id", result["admin_code"])
    if result["area_id"].duplicated().any():
        dupes = sorted(result.loc[result["area_id"].duplicated(), "area_id"].astype(str).unique())
        raise InputContractError("Duplicate area_id rows for feature month: " + ", ".join(dupes))
    result["_row_id"] = range(len(result))
    report = {
        "status": "passed",
        "feature_month": feature_month,
        "row_count": int(len(result)),
        "unique_area_count": int(result["area_id"].nunique()),
        "input_columns": list(df.columns),
    }
    return result, report
```

- [ ] **Step 4: Run input contract tests**

Run:

```bash
cd "/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/IPCCH_monthly_operational"
python3 -m unittest tests.test_operational_launch_input_contract -v
```

Expected: PASS.

- [ ] **Step 5: Commit in production repo**

```bash
cd "/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/IPCCH_monthly_operational"
git add model_pipeline/ipcch_launch_runtime/__init__.py model_pipeline/ipcch_launch_runtime/adapters.py tests/test_operational_launch_input_contract.py
git commit -m "feat: add operational launch input validation"
```

---

### Task 4: Production Feature Contract Runtime

**Files:**
- Create: `/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/IPCCH_monthly_operational/model_pipeline/ipcch_launch_runtime/feature_contract.py`
- Create: `/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/IPCCH_monthly_operational/tests/test_operational_launch_feature_contract.py`

- [ ] **Step 1: Write failing feature contract runtime tests**

Add `/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/IPCCH_monthly_operational/tests/test_operational_launch_feature_contract.py`:

```python
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from model_pipeline.ipcch_launch_runtime import feature_contract


CONTRACT_ROWS = [
    {
        "feature_name": "rain",
        "scope_months": "all",
        "category": "required",
        "source_column": "Rainf_f_tavg_mean",
        "dtype": "float",
        "required_in_input": "True",
        "missing_tolerance": "0.0",
        "fill_method": "none",
        "fill_value_or_stat_key": "",
        "lookup_asset": "",
        "derive_function": "",
        "as_of_policy": "feature_month_end",
        "notes": "rain",
    },
    {
        "feature_name": "static_crop",
        "scope_months": "all",
        "category": "static_join",
        "source_column": "",
        "dtype": "integer",
        "required_in_input": "False",
        "missing_tolerance": "0.0",
        "fill_method": "static lookup",
        "fill_value_or_stat_key": "",
        "lookup_asset": "lookups/static.csv",
        "derive_function": "",
        "as_of_policy": "static",
        "notes": "crop",
    },
    {
        "feature_name": "soil_median",
        "scope_months": "all",
        "category": "median_impute",
        "source_column": "soil",
        "dtype": "float",
        "required_in_input": "False",
        "missing_tolerance": "1.0",
        "fill_method": "median",
        "fill_value_or_stat_key": "soil_median",
        "lookup_asset": "",
        "derive_function": "",
        "as_of_policy": "training_stat",
        "notes": "soil median",
    },
]


class OperationalFeatureContractTests(unittest.TestCase):
    def test_apply_contract_builds_feature_matrix_and_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lookup = root / "lookups" / "static.csv"
            lookup.parent.mkdir()
            lookup.write_text("area_id,static_crop\n001,7\n002,8\n", encoding="utf-8")
            df = pd.DataFrame({"area_id": ["001", "002"], "Rainf_f_tavg_mean": [1.5, 2.5]})
            contract = pd.DataFrame(CONTRACT_ROWS)
            matrix, report = feature_contract.apply_feature_contract(
                df,
                contract,
                ["rain", "static_crop", "soil_median"],
                package_root=root,
                metadata={"imputation_statistics": {"soil_median": 3.25}},
            )
            self.assertEqual(["rain", "static_crop", "soil_median"], list(matrix.columns))
            self.assertEqual([1.5, 2.5], matrix["rain"].tolist())
            self.assertEqual([7, 8], matrix["static_crop"].tolist())
            self.assertEqual([3.25, 3.25], matrix["soil_median"].tolist())
            self.assertEqual("passed", report["status"])
            self.assertEqual(1, len(report["filled_features"]))

    def test_missing_required_column_fails(self):
        contract = pd.DataFrame(CONTRACT_ROWS[:1])
        with self.assertRaisesRegex(feature_contract.FeatureContractError, "required source column"):
            feature_contract.apply_feature_contract(
                pd.DataFrame({"area_id": ["001"]}),
                contract,
                ["rain"],
                package_root=Path("."),
                metadata={},
            )


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd "/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/IPCCH_monthly_operational"
python3 -m unittest tests.test_operational_launch_feature_contract -v
```

Expected: FAIL because `feature_contract.py` does not exist.

- [ ] **Step 3: Implement feature contract runtime**

Create `/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/IPCCH_monthly_operational/model_pipeline/ipcch_launch_runtime/feature_contract.py` with these functions:

```python
from __future__ import annotations

from pathlib import Path
from typing import Mapping, Sequence

import pandas as pd


class FeatureContractError(ValueError):
    pass


def _truthy(value) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def _coerce(series: pd.Series, dtype: str) -> pd.Series:
    if dtype == "float":
        return pd.to_numeric(series, errors="raise").astype(float)
    if dtype == "integer":
        return pd.to_numeric(series, errors="raise").astype("Int64")
    if dtype == "boolean":
        return series.astype(bool)
    if dtype in {"string", "categorical"}:
        return series.astype("string")
    raise FeatureContractError(f"Unsupported dtype: {dtype}")


def _load_lookup(package_root: Path, relative_path: str) -> pd.DataFrame:
    path = package_root / relative_path
    if not path.exists():
        raise FeatureContractError(f"Missing lookup asset: {path}")
    return pd.read_csv(path, dtype={"area_id": "string"})


def apply_feature_contract(
    monthly_input: pd.DataFrame,
    contract: pd.DataFrame,
    feature_columns: Sequence[str],
    *,
    package_root: Path,
    metadata: Mapping[str, object],
) -> tuple[pd.DataFrame, dict[str, object]]:
    rows = contract.set_index("feature_name", drop=False)
    matrix = pd.DataFrame(index=monthly_input.index)
    filled = []
    warnings = []
    for feature in feature_columns:
        if feature not in rows.index:
            raise FeatureContractError(f"Model feature missing from feature_contract.csv: {feature}")
        row = rows.loc[feature]
        category = str(row["category"])
        source_column = str(row.get("source_column", "") or "")
        dtype = str(row["dtype"])
        required = _truthy(row.get("required_in_input", False))
        if category in {"unsupported", "excluded"}:
            raise FeatureContractError(f"Model references unsupported feature: {feature}")
        if category == "required":
            if source_column not in monthly_input.columns:
                raise FeatureContractError(f"Missing required source column for {feature}: {source_column}")
            series = monthly_input[source_column]
        elif category == "static_join":
            lookup = _load_lookup(package_root, str(row["lookup_asset"]))
            if feature not in lookup.columns:
                raise FeatureContractError(f"Lookup asset missing feature column {feature}")
            joined = monthly_input[["area_id"]].merge(lookup[["area_id", feature]], on="area_id", how="left", validate="many_to_one")
            series = joined[feature]
            filled.append({"feature_name": feature, "fill_method": "static lookup"})
        elif category == "median_impute":
            stats = metadata.get("imputation_statistics", {})
            key = str(row["fill_value_or_stat_key"])
            if key not in stats:
                raise FeatureContractError(f"Missing imputation statistic for {feature}: {key}")
            if source_column and source_column in monthly_input.columns:
                series = monthly_input[source_column].fillna(stats[key])
            else:
                series = pd.Series([stats[key]] * len(monthly_input), index=monthly_input.index)
            filled.append({"feature_name": feature, "fill_method": "median"})
        elif category == "carry_forward":
            lookup = _load_lookup(package_root, str(row["lookup_asset"]))
            if feature not in lookup.columns:
                raise FeatureContractError(f"Carry-forward asset missing feature column {feature}")
            joined = monthly_input[["area_id"]].merge(lookup[["area_id", feature]], on="area_id", how="left", validate="many_to_one")
            series = joined[feature]
            filled.append({"feature_name": feature, "fill_method": "carry forward"})
        elif category == "derived":
            raise FeatureContractError("Derived features require registered derive functions before use")
        else:
            raise FeatureContractError(f"Unsupported category: {category}")
        missing_rate = float(pd.isna(series).mean()) if len(series) else 0.0
        tolerance = float(row["missing_tolerance"])
        if missing_rate > tolerance:
            raise FeatureContractError(f"Missing rate for {feature} exceeds tolerance: {missing_rate} > {tolerance}")
        matrix[feature] = _coerce(series, dtype)
    report = {
        "status": "passed",
        "feature_count": len(feature_columns),
        "filled_features": filled,
        "warnings": warnings,
    }
    return matrix.loc[:, list(feature_columns)], report
```

- [ ] **Step 4: Run tests**

Run:

```bash
cd "/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/IPCCH_monthly_operational"
python3 -m unittest tests.test_operational_launch_feature_contract -v
```

Expected: PASS.

- [ ] **Step 5: Commit in production repo**

```bash
cd "/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/IPCCH_monthly_operational"
git add model_pipeline/ipcch_launch_runtime/feature_contract.py tests/test_operational_launch_feature_contract.py
git commit -m "feat: apply operational launch feature contracts"
```

---

### Task 5: Production Model Package Loading And Phase Decoding

**Files:**
- Create: `/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/IPCCH_monthly_operational/model_pipeline/ipcch_launch_runtime/model_package.py`
- Create: `/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/IPCCH_monthly_operational/model_pipeline/ipcch_launch_runtime/inference.py`
- Create: `/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/IPCCH_monthly_operational/tests/test_operational_launch_inference.py`

- [ ] **Step 1: Write failing inference tests with fake models**

Add `/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/IPCCH_monthly_operational/tests/test_operational_launch_inference.py`:

```python
import unittest

import pandas as pd

from model_pipeline.ipcch_launch_runtime import inference


class ConstantModel:
    def __init__(self, value):
        self.value = value

    def predict(self, matrix):
        return [self.value] * len(matrix)


class OperationalLaunchInferenceTests(unittest.TestCase):
    def test_scores_thresholds_and_decodes_phase(self):
        matrix = pd.DataFrame({"rain": [1.0, 2.0]}, index=[0, 1])
        models = {
            "phase2_worse": ConstantModel(0.8),
            "phase3_worse": ConstantModel(0.7),
            "phase4_worse": ConstantModel(0.1),
            "phase5_worse": ConstantModel(0.1),
        }
        result, summary = inference.score_scope(
            monthly_rows=pd.DataFrame({"area_id": ["001", "002"], "admin_code": ["001", "002"]}),
            feature_matrix=matrix,
            models=models,
            thresholds={"default": 0.2},
            scope_months=6,
            feature_month="2026-07",
            target_month="2027-01",
            model_package_id="pkg",
            source_input="input.csv",
            monotonicity_policy="fail",
        )
        self.assertEqual([3, 3], result["overall_phase_pred"].tolist())
        self.assertEqual([0.7, 0.7], result["phase3_worse_score"].tolist())
        self.assertEqual("passed", summary["status"])
        self.assertEqual({"default": 0.2}, summary["thresholds"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd "/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/IPCCH_monthly_operational"
python3 -m unittest tests.test_operational_launch_inference -v
```

Expected: FAIL because `inference.py` does not exist.

- [ ] **Step 3: Implement inference and decoding**

Create `/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/IPCCH_monthly_operational/model_pipeline/ipcch_launch_runtime/inference.py`:

```python
from __future__ import annotations

from typing import Mapping

import pandas as pd


TARGETS = ("phase2_worse", "phase3_worse", "phase4_worse", "phase5_worse")


class InferenceError(ValueError):
    pass


def _threshold(thresholds: Mapping[str, float], target: str) -> float:
    return float(thresholds.get(target, thresholds["default"]))


def _decode(out: pd.DataFrame, thresholds: Mapping[str, float], monotonicity_policy: str) -> pd.DataFrame:
    for target in TARGETS:
        out[f"{target}_pred"] = (out[f"{target}_score"] >= _threshold(thresholds, target)).astype(int)
    invalid = (
        (out["phase3_worse_pred"] > out["phase2_worse_pred"])
        | (out["phase4_worse_pred"] > out["phase3_worse_pred"])
        | (out["phase5_worse_pred"] > out["phase4_worse_pred"])
    )
    if invalid.any() and monotonicity_policy == "fail":
        raise InferenceError("Thresholded worse-or-equal predictions are non-monotonic")
    if invalid.any() and monotonicity_policy == "cummax":
        out["phase4_worse_pred"] = out[["phase4_worse_pred", "phase5_worse_pred"]].max(axis=1)
        out["phase3_worse_pred"] = out[["phase3_worse_pred", "phase4_worse_pred"]].max(axis=1)
        out["phase2_worse_pred"] = out[["phase2_worse_pred", "phase3_worse_pred"]].max(axis=1)
    out["overall_phase_pred"] = 1
    for phase in (5, 4, 3, 2):
        out.loc[out[f"phase{phase}_worse_pred"] == 1, "overall_phase_pred"] = phase
    return out


def score_scope(
    *,
    monthly_rows: pd.DataFrame,
    feature_matrix: pd.DataFrame,
    models: Mapping[str, object],
    thresholds: Mapping[str, float],
    scope_months: int,
    feature_month: str,
    target_month: str,
    model_package_id: str,
    source_input: str,
    monotonicity_policy: str,
) -> tuple[pd.DataFrame, dict[str, object]]:
    out = monthly_rows[[c for c in ("area_id", "admin_code") if c in monthly_rows.columns]].copy()
    for target in TARGETS:
        if target not in models:
            raise InferenceError(f"Missing model for {target}")
        out[f"{target}_score"] = models[target].predict(feature_matrix)
    out = _decode(out, thresholds, monotonicity_policy)
    out["feature_period"] = feature_month
    out["target_period"] = target_month
    out["scope_months"] = scope_months
    out["model_package_id"] = model_package_id
    out["source_input"] = source_input
    summary = {
        "status": "passed",
        "scope_months": scope_months,
        "feature_month": feature_month,
        "target_month": target_month,
        "thresholds": dict(thresholds),
        "monotonicity_policy": monotonicity_policy,
        "row_count": int(len(out)),
    }
    return out, summary
```

- [ ] **Step 4: Add model package loader**

Create `/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/IPCCH_monthly_operational/model_pipeline/ipcch_launch_runtime/model_package.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


TARGETS = ("phase2_worse", "phase3_worse", "phase4_worse", "phase5_worse")


class ModelPackageError(ValueError):
    pass


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_scope_package(package_root: Path, scope_months: int):
    scope_dir = package_root / f"scope_{scope_months}m"
    if not scope_dir.exists():
        raise ModelPackageError(f"Missing scope package: {scope_dir}")
    feature_columns = load_json(scope_dir / "feature_columns.json")
    metadata = load_json(scope_dir / "model_metadata.json")
    contract = pd.read_csv(scope_dir / "feature_contract.csv")
    models = {}
    try:
        import xgboost as xgb
    except ImportError as exc:
        raise ModelPackageError("xgboost is required to load model package") from exc
    for target in TARGETS:
        model_path = scope_dir / f"{target}_model.json"
        if not model_path.exists():
            raise ModelPackageError(f"Missing model file: {model_path}")
        model = xgb.XGBRegressor()
        model.load_model(str(model_path))
        models[target] = model
    return {
        "scope_dir": scope_dir,
        "feature_columns": feature_columns,
        "metadata": metadata,
        "contract": contract,
        "models": models,
    }
```

- [ ] **Step 5: Run inference tests**

Run:

```bash
cd "/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/IPCCH_monthly_operational"
python3 -m unittest tests.test_operational_launch_inference -v
```

Expected: PASS.

- [ ] **Step 6: Commit in production repo**

```bash
cd "/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/IPCCH_monthly_operational"
git add model_pipeline/ipcch_launch_runtime/model_package.py model_pipeline/ipcch_launch_runtime/inference.py tests/test_operational_launch_inference.py
git commit -m "feat: score operational launch model packages"
```

---

### Task 6: Production Atomic Outputs And CLI

**Files:**
- Create: `/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/IPCCH_monthly_operational/model_pipeline/ipcch_launch_runtime/outputs.py`
- Create: `/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/IPCCH_monthly_operational/model_pipeline/ipcch_launch_runtime/visualization.py`
- Create: `/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/IPCCH_monthly_operational/model_pipeline/run_operational_launch_inference.py`
- Create: `/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/IPCCH_monthly_operational/tests/test_operational_launch_cli.py`

- [ ] **Step 1: Write CLI smoke test using monkeypatched fake package**

Add `/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/IPCCH_monthly_operational/tests/test_operational_launch_cli.py`:

```python
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pandas as pd

from model_pipeline import run_operational_launch_inference as cli


class OperationalLaunchCliTests(unittest.TestCase):
    def test_cli_no_map_writes_prediction_outputs_and_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_path = root / "input.csv"
            input_path.write_text("admin_code,year,month,Rainf_f_tavg_mean\n001,2026,7,1.5\n", encoding="utf-8")
            package = root / "package"
            package.mkdir()
            output = root / "predictions"

            def fake_run_scope(scope, monthly_rows, package_root, feature_month, input_path):
                target = {0: "2026-07", 6: "2027-01", 12: "2027-07"}[scope]
                return pd.DataFrame(
                    {
                        "area_id": ["001"],
                        "admin_code": ["001"],
                        "feature_period": [feature_month],
                        "target_period": [target],
                        "scope_months": [scope],
                        "phase2_worse_score": [0.8],
                        "phase3_worse_score": [0.7],
                        "phase4_worse_score": [0.1],
                        "phase5_worse_score": [0.1],
                        "phase2_worse_pred": [1],
                        "phase3_worse_pred": [1],
                        "phase4_worse_pred": [0],
                        "phase5_worse_pred": [0],
                        "overall_phase_pred": [3],
                        "model_package_id": ["pkg"],
                        "source_input": [str(input_path)],
                    }
                ), {"status": "passed", "scope_months": scope, "target_month": target}

            with mock.patch.object(cli, "run_scope", side_effect=fake_run_scope):
                code = cli.main(
                    [
                        "--input",
                        str(input_path),
                        "--model-package",
                        str(package),
                        "--output-dir",
                        str(output),
                        "--feature-month",
                        "2026-07",
                        "--no-map",
                    ]
                )
            self.assertEqual(0, code)
            for scope in ("0m", "6m", "12m"):
                self.assertTrue((output / f"ipcch_launch_202607_scope_{scope}_predictions.csv").exists())
                self.assertFalse((output / f"ipcch_launch_202607_scope_{scope}_map.png").exists())
            summary = json.loads((output / "run_summary.json").read_text(encoding="utf-8"))
            self.assertEqual("passed", summary["status"])
            self.assertEqual([0, 6, 12], summary["scopes_completed"])
            self.assertEqual(True, summary["map_generation_disabled"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd "/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/IPCCH_monthly_operational"
python3 -m unittest tests.test_operational_launch_cli -v
```

Expected: FAIL because `run_operational_launch_inference.py` does not exist.

- [ ] **Step 3: Implement output writer**

Create `/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/IPCCH_monthly_operational/model_pipeline/ipcch_launch_runtime/outputs.py`:

```python
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Mapping

import pandas as pd


class OutputError(ValueError):
    pass


def month_label(feature_month: str) -> str:
    return feature_month.replace("-", "")


def primary_paths(output_dir: Path, feature_month: str, scopes=(0, 6, 12)) -> dict[int, dict[str, Path]]:
    label = month_label(feature_month)
    return {
        scope: {
            "predictions": output_dir / f"ipcch_launch_{label}_scope_{scope}m_predictions.csv",
            "map": output_dir / f"ipcch_launch_{label}_scope_{scope}m_map.png",
        }
        for scope in scopes
    }


def guard_outputs(paths: Mapping[int, Mapping[str, Path]], overwrite: bool) -> None:
    existing = [str(path) for scope_paths in paths.values() for path in scope_paths.values() if path.exists()]
    if existing and not overwrite:
        raise OutputError("Primary delivery outputs already exist: " + "; ".join(existing))


def write_csv_atomic(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    frame.to_csv(tmp, index=False)
    os.replace(tmp, path)


def write_text_atomic(text: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def write_json_atomic(payload: Mapping[str, object], path: Path) -> None:
    write_text_atomic(json.dumps(payload, indent=2), path)
```

- [ ] **Step 4: Implement visualization shim and CLI**

Create `/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/IPCCH_monthly_operational/model_pipeline/ipcch_launch_runtime/visualization.py`:

```python
from __future__ import annotations

from pathlib import Path

import pandas as pd


class VisualizationError(ValueError):
    pass


def write_prediction_map(predictions: pd.DataFrame, *, spatial_path: Path, output_path: Path, scope_months: int, feature_month: str) -> dict[str, object]:
    if not spatial_path.exists():
        raise VisualizationError(f"Missing spatial boundary file: {spatial_path}")
    try:
        import geopandas as gpd
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise VisualizationError("geopandas and matplotlib are required for map generation") from exc

    gdf = gpd.read_file(spatial_path)
    if "area_id" not in gdf.columns:
        if "admin_code" in gdf.columns:
            gdf["area_id"] = gdf["admin_code"].astype("string")
        else:
            raise VisualizationError("Spatial file must contain area_id or admin_code")
    pred = predictions.copy()
    pred["area_id"] = pred["area_id"].astype("string")
    gdf["area_id"] = gdf["area_id"].astype("string")
    joined = gdf.merge(pred[["area_id", "overall_phase_pred"]], on="area_id", how="left", validate="one_to_one")
    matched = int(joined["overall_phase_pred"].notna().sum())
    if matched == 0:
        raise VisualizationError("Spatial join matched zero prediction rows")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ax = joined.plot(column="overall_phase_pred", legend=True, figsize=(10, 8), missing_kwds={"color": "lightgrey"})
    ax.set_axis_off()
    ax.set_title(f"IPCCH {feature_month} scope {scope_months}m predicted phase")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()
    return {
        "status": "passed",
        "scope_months": scope_months,
        "matched_rows": matched,
        "unmatched_rows": int(len(pred) - matched),
        "output_path": str(output_path),
    }
```

Create `/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/IPCCH_monthly_operational/model_pipeline/run_operational_launch_inference.py`:

```python
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

import pandas as pd

from model_pipeline.ipcch_launch_runtime import adapters, feature_contract, inference, model_package, outputs, visualization


SCOPES = (0, 6, 12)


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Run IPCCH operational launch inference.")
    p.add_argument("--input", required=True)
    p.add_argument("--model-package", required=True)
    p.add_argument("--spatial-path")
    p.add_argument("--output-dir", required=True)
    p.add_argument("--feature-month", required=True)
    p.add_argument("--validate-only", action="store_true")
    p.add_argument("--overwrite", action="store_true")
    p.add_argument("--no-map", action="store_true")
    return p.parse_args(argv)


def _hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def target_month(feature_month: str, scope: int) -> str:
    return str(pd.Period(feature_month, freq="M") + scope)


def run_scope(scope, monthly_rows, package_root, feature_month, input_path):
    package = model_package.load_scope_package(package_root, scope)
    matrix, compatibility = feature_contract.apply_feature_contract(
        monthly_rows,
        package["contract"],
        package["feature_columns"],
        package_root=package["scope_dir"],
        metadata=package["metadata"],
    )
    thresholds = package["metadata"].get("thresholds", {"default": 0.2})
    monotonicity_policy = package["metadata"].get("monotonicity_policy", "fail")
    predictions, summary = inference.score_scope(
        monthly_rows=monthly_rows,
        feature_matrix=matrix,
        models=package["models"],
        thresholds=thresholds,
        scope_months=scope,
        feature_month=feature_month,
        target_month=target_month(feature_month, scope),
        model_package_id=package_root.name,
        source_input=str(input_path),
        monotonicity_policy=monotonicity_policy,
    )
    summary["feature_compatibility"] = compatibility
    return predictions, summary


def run(args) -> int:
    input_path = Path(args.input)
    package_root = Path(args.model_package)
    output_dir = Path(args.output_dir)
    planned = outputs.primary_paths(output_dir, args.feature_month, SCOPES)
    guard_plan = planned if not args.no_map else {
        scope: {"predictions": scope_paths["predictions"]}
        for scope, scope_paths in planned.items()
    }
    outputs.guard_outputs(guard_plan, args.overwrite)
    raw = pd.read_csv(input_path, dtype={"area_id": "string", "admin_code": "string"})
    monthly_rows, input_report = adapters.validate_monthly_input(raw, feature_month=args.feature_month)
    if args.validate_only:
        outputs.write_json_atomic(
            {
                "status": "validated",
                "feature_month": args.feature_month,
                "input_report": input_report,
                "scopes_attempted": list(SCOPES),
            },
            output_dir / "run_summary.json",
        )
        return 0
    summaries = []
    completed = []
    for scope in SCOPES:
        predictions, summary = run_scope(scope, monthly_rows, package_root, args.feature_month, input_path)
        outputs.write_csv_atomic(predictions, planned[scope]["predictions"])
        if not args.no_map:
            if not args.spatial_path:
                raise visualization.VisualizationError("--spatial-path is required unless --no-map is used")
            map_summary = visualization.write_prediction_map(
                predictions,
                spatial_path=Path(args.spatial_path),
                output_path=planned[scope]["map"],
                scope_months=scope,
                feature_month=args.feature_month,
            )
            summary["map"] = map_summary
        summaries.append(summary)
        completed.append(scope)
    outputs.write_json_atomic(
        {
            "status": "passed",
            "feature_month": args.feature_month,
            "model_package_id": package_root.name,
            "scopes_attempted": list(SCOPES),
            "scopes_completed": completed,
            "input_path": str(input_path),
            "input_sha256": _hash_file(input_path),
            "map_generation_disabled": bool(args.no_map),
            "input_report": input_report,
            "scope_summaries": summaries,
            "output_paths": {
                str(scope): {name: str(path) for name, path in scope_paths.items()}
                for scope, scope_paths in planned.items()
            },
        },
        output_dir / "run_summary.json",
    )
    return 0


def main(argv=None) -> int:
    return run(parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Run CLI tests**

Run:

```bash
cd "/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/IPCCH_monthly_operational"
python3 -m unittest tests.test_operational_launch_cli -v
```

Expected: PASS.

- [ ] **Step 6: Commit in production repo**

```bash
cd "/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/IPCCH_monthly_operational"
git add model_pipeline/run_operational_launch_inference.py model_pipeline/ipcch_launch_runtime/outputs.py model_pipeline/ipcch_launch_runtime/visualization.py tests/test_operational_launch_cli.py
git commit -m "feat: add operational launch inference cli"
```

---

### Task 7: Documentation, Ignore Rules, And End-To-End Validation

**Files:**
- Modify: `/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/IPCCH_monthly_operational/.gitignore`
- Modify: `/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/IPCCH_monthly_operational/README.md`
- Modify: `/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/IPCCH_monthly_operational/docs/03_workflow_runbook.md`

- [ ] **Step 1: Add generated output ignore rules**

Patch production `.gitignore`:

```gitignore

# Generated operational launch inference outputs
Outcome/ipcch_unified/predictions/

# Large local operational launch model packages
model_artifacts/
```

- [ ] **Step 2: Add README command**

Add this short section to production `README.md`:

```markdown
## Operational Launch Inference

After the monthly model input table is built, run pure inference with a fixed
model package:

```bash
python3 model_pipeline/run_operational_launch_inference.py \
  --input Outcome/ipcch_unified/model_input/ipcch_monthly_base_input_YYYYMM.csv \
  --model-package model_artifacts/launch_2026_04 \
  --spatial-path Outcome/ipcch_unified/spatial/ipcch_admin_geometry.shp \
  --output-dir Outcome/ipcch_unified/predictions/YYYYMM \
  --feature-month YYYY-MM
```

The command writes six primary delivery files: prediction sheet and map for
`0m`, `6m`, and `12m`. The production command does not train models.
```

- [ ] **Step 3: Add runbook note**

Add to production `docs/03_workflow_runbook.md` after the monthly model input build step:

```markdown
### Operational launch inference

Use this only after the fixed model package has been exported from the research
IPCCH repository and copied into `model_artifacts/launch_2026_04`.

Run `--validate-only` first:

```bash
python3 model_pipeline/run_operational_launch_inference.py \
  --input Outcome/ipcch_unified/model_input/ipcch_monthly_base_input_YYYYMM.csv \
  --model-package model_artifacts/launch_2026_04 \
  --spatial-path Outcome/ipcch_unified/spatial/ipcch_admin_geometry.shp \
  --output-dir Outcome/ipcch_unified/predictions/YYYYMM \
  --feature-month YYYY-MM \
  --validate-only
```

Then run without `--validate-only` to generate the six primary delivery files.
```

- [ ] **Step 4: Run production unit and CLI tests**

Run:

```bash
cd "/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/IPCCH_monthly_operational"
python3 -m unittest \
  tests.test_operational_launch_input_contract \
  tests.test_operational_launch_feature_contract \
  tests.test_operational_launch_inference \
  tests.test_operational_launch_cli -v
```

Expected: PASS.

- [ ] **Step 5: Run research tests touched by exporter**

Run:

```bash
cd "/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/Google fund/Analysis/2.source_code/Step5_Geo_RF_trial/IPCCH"
PYTHONPATH=src pytest tests/unit/test_operational_contract.py tests/smoke/test_export_operational_launch_package_cli.py -q
```

Expected: PASS.

- [ ] **Step 6: Check both git worktrees**

Run:

```bash
git -C "/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/Google fund/Analysis/2.source_code/Step5_Geo_RF_trial/IPCCH" status --short
git -C "/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/IPCCH_monthly_operational" status --short
```

Expected: Only user-approved pending docs/spec changes or ignored generated outputs remain.

- [ ] **Step 7: Commit docs in production repo**

```bash
cd "/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/IPCCH_monthly_operational"
git add .gitignore README.md docs/03_workflow_runbook.md
git commit -m "docs: document operational launch inference"
```

---

## Plan Self-Review

Spec coverage:

- Temporal contract: Task 1 adds tests/helpers for target periods and cutoff; Task 2 uses the feature month in package metadata.
- Feature contract schema and source-of-truth: Task 1 validates schema on research side; Task 4 enforces it in production runtime.
- Feature eligibility: Task 1 rejects target leakage, forecast-weather proxy features, and prohibited as-of policies; Task 2 runs that eligibility validation before packaging.
- Monthly input contract: Task 3 validates single month, ID rules, duplicates, and feature-month mismatch before model loading.
- Output semantics and phase decoding: Task 1 and Task 5 implement score, binary threshold, monotonicity policy, and decoded phase.
- Fail-fast and audit behavior: Task 6 adds output guards, atomic writes, run summary, and whole-run CLI behavior.
- Docker/cloud details remain out of scope except for a non-interactive CLI and explicit paths.

Placeholder scan:

- The plan contains no unfinished placeholder markers.
- Code snippets define concrete functions, tests, commands, and expected results.

Type consistency:

- `feature_month` is consistently `YYYY-MM`.
- Scopes are consistently integers `0`, `6`, `12` in code and `scope_0m` path labels in files.
- Prediction score columns use `phase{k}_worse_score`; thresholded binary columns use `phase{k}_worse_pred`.
