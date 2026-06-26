from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[2]
CLI = REPO_ROOT / "scripts" / "modeling" / "export_operational_launch_package.py"
REQUIRED_ARTIFACTS = (
    "phase2_worse_model.json",
    "phase3_worse_model.json",
    "phase4_worse_model.json",
    "phase5_worse_model.json",
    "feature_columns.json",
    "feature_contract.csv",
)


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        check=False,
    )


def write_scope_artifacts(
    root: Path,
    scope: int,
    *,
    unsafe_contract: bool = False,
    omit_artifact: str | None = None,
    feature_columns: list[str] | None = None,
    contract_scope: str | None = None,
) -> None:
    scope_dir = root / f"scope_{scope}m"
    scope_dir.mkdir(parents=True)
    feature_columns = ["rain_safe"] if feature_columns is None else feature_columns
    contract_scope = str(scope) if contract_scope is None else contract_scope
    for phase in range(2, 6):
        name = f"phase{phase}_worse_model.json"
        if name != omit_artifact:
            (scope_dir / name).write_text(
                json.dumps({"phase": phase, "scope_months": scope}),
                encoding="utf-8",
            )

    if omit_artifact != "feature_columns.json":
        (scope_dir / "feature_columns.json").write_text(
            json.dumps(feature_columns),
            encoding="utf-8",
        )

    if omit_artifact != "feature_contract.csv":
        notes = (
            "forecasted weather proxy should fail"
            if unsafe_contract
            else "safe feature available by feature month"
        )
        pd.DataFrame(
            [
                {
                    "feature_name": "rain_safe",
                    "scope_months": contract_scope,
                    "category": "required",
                    "source_column": "rain_observed",
                    "dtype": "float",
                    "required_in_input": True,
                    "missing_tolerance": 0.0,
                    "fill_method": "none",
                    "fill_value_or_stat_key": "",
                    "lookup_asset": "",
                    "derive_function": "",
                    "as_of_policy": "feature_month_end",
                    "notes": notes,
                }
            ]
        ).to_csv(scope_dir / "feature_contract.csv", index=False)


def write_package_source(
    root: Path,
    *,
    unsafe_scope: int | None = None,
    missing_artifact: tuple[int, str] | None = None,
    empty_feature_columns_scope: int | None = None,
    contract_scope_override: tuple[int, str] | None = None,
) -> None:
    for scope in (0, 6, 12):
        omit = missing_artifact[1] if missing_artifact and missing_artifact[0] == scope else None
        feature_columns = [] if empty_feature_columns_scope == scope else None
        contract_scope = (
            contract_scope_override[1]
            if contract_scope_override and contract_scope_override[0] == scope
            else None
        )
        write_scope_artifacts(
            root,
            scope,
            unsafe_contract=unsafe_scope == scope,
            omit_artifact=omit,
            feature_columns=feature_columns,
            contract_scope=contract_scope,
        )


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_exports_manifest_metadata_and_required_scope_files(tmp_path):
    source = tmp_path / "source"
    out = tmp_path / "package"
    write_package_source(source)

    result = run_cli(
        "--from-existing-artifacts",
        str(source),
        "--output-package",
        str(out),
        "--feature-month",
        "2026-04",
        "--package-id",
        "launch_2026_04_test",
    )

    assert result.returncode == 0, result.stderr
    manifest_path = out / "model_package_manifest.json"
    assert result.stdout.strip() == str(manifest_path)
    manifest = read_json(manifest_path)
    assert manifest["package_id"] == "launch_2026_04_test"
    assert manifest["feature_month"] == "2026-04"
    assert manifest["scopes"] == [0, 6, 12]
    assert manifest["target_periods"] == {
        "0": "2026-04",
        "6": "2026-10",
        "12": "2027-04",
    }
    assert manifest["forecasted_weather"] == {"enabled": False}

    expected_targets = {0: "2026-04", 6: "2026-10", 12: "2027-04"}
    for scope, target_month in expected_targets.items():
        scope_dir = out / f"scope_{scope}m"
        for artifact in REQUIRED_ARTIFACTS:
            assert (scope_dir / artifact).exists()
        copied_model = read_json(scope_dir / "phase3_worse_model.json")
        assert copied_model["scope_months"] == scope
        metadata = read_json(scope_dir / "model_metadata.json")
        assert metadata["scope_months"] == scope
        assert metadata["feature_month"] == "2026-04"
        assert metadata["target_month"] == target_month
        assert metadata["thresholds"] == {"default": 0.2}
        assert metadata["monotonicity_policy"] == "fail"
        assert metadata["feature_contract_validation"]["status"] == "passed"
        assert metadata["feature_eligibility_validation"]["status"] == "passed"


def test_existing_output_without_overwrite_fails_without_replacing(tmp_path):
    source = tmp_path / "source"
    out = tmp_path / "package"
    write_package_source(source)
    out.mkdir()
    sentinel = out / "sentinel.txt"
    sentinel.write_text("keep me", encoding="utf-8")

    result = run_cli(
        "--from-existing-artifacts",
        str(source),
        "--output-package",
        str(out),
        "--feature-month",
        "2026-04",
        "--package-id",
        "launch_2026_04_test",
    )

    assert result.returncode == 2
    assert "already exists" in result.stderr
    assert sentinel.read_text(encoding="utf-8") == "keep me"


def test_overwrite_replaces_existing_output(tmp_path):
    source = tmp_path / "source"
    out = tmp_path / "package"
    write_package_source(source)
    out.mkdir()
    (out / "stale.txt").write_text("old", encoding="utf-8")

    result = run_cli(
        "--from-existing-artifacts",
        str(source),
        "--output-package",
        str(out),
        "--feature-month",
        "2026-04",
        "--package-id",
        "launch_2026_04_test",
        "--overwrite",
    )

    assert result.returncode == 0, result.stderr
    assert not (out / "stale.txt").exists()
    assert (out / "model_package_manifest.json").exists()


def test_overwrite_rejects_output_same_as_source_and_preserves_source(tmp_path):
    source = tmp_path / "source"
    write_package_source(source)
    sentinel_artifact = source / "scope_6m" / "phase3_worse_model.json"
    original = sentinel_artifact.read_text(encoding="utf-8")

    result = run_cli(
        "--from-existing-artifacts",
        str(source),
        "--output-package",
        str(source),
        "--feature-month",
        "2026-04",
        "--package-id",
        "launch_2026_04_test",
        "--overwrite",
    )

    assert result.returncode == 2
    assert "overlap" in result.stderr
    assert "Traceback" not in result.stderr
    assert sentinel_artifact.read_text(encoding="utf-8") == original


def test_overwrite_rejects_output_inside_source_tree(tmp_path):
    source = tmp_path / "source"
    out = source / "nested_package"
    write_package_source(source)

    result = run_cli(
        "--from-existing-artifacts",
        str(source),
        "--output-package",
        str(out),
        "--feature-month",
        "2026-04",
        "--package-id",
        "launch_2026_04_test",
        "--overwrite",
    )

    assert result.returncode == 2
    assert "overlap" in result.stderr
    assert "Traceback" not in result.stderr
    assert not out.exists()


def test_overwrite_rejects_source_inside_output_tree_and_preserves_source(tmp_path):
    out = tmp_path / "package"
    source = out / "source_artifacts"
    write_package_source(source)
    sentinel_artifact = source / "scope_12m" / "feature_columns.json"
    original = sentinel_artifact.read_text(encoding="utf-8")

    result = run_cli(
        "--from-existing-artifacts",
        str(source),
        "--output-package",
        str(out),
        "--feature-month",
        "2026-04",
        "--package-id",
        "launch_2026_04_test",
        "--overwrite",
    )

    assert result.returncode == 2
    assert "overlap" in result.stderr
    assert "Traceback" not in result.stderr
    assert sentinel_artifact.read_text(encoding="utf-8") == original


def test_missing_scope_artifact_fails(tmp_path):
    source = tmp_path / "source"
    out = tmp_path / "package"
    write_package_source(source, missing_artifact=(6, "phase4_worse_model.json"))

    result = run_cli(
        "--from-existing-artifacts",
        str(source),
        "--output-package",
        str(out),
        "--feature-month",
        "2026-04",
        "--package-id",
        "launch_2026_04_test",
    )

    assert result.returncode == 2
    assert "scope_6m" in result.stderr
    assert "phase4_worse_model.json" in result.stderr
    assert not out.exists()


def test_unsafe_feature_contract_fails(tmp_path):
    source = tmp_path / "source"
    out = tmp_path / "package"
    write_package_source(source, unsafe_scope=12)

    result = run_cli(
        "--from-existing-artifacts",
        str(source),
        "--output-package",
        str(out),
        "--feature-month",
        "2026-04",
        "--package-id",
        "launch_2026_04_test",
    )

    assert result.returncode == 2
    assert "scope_12m" in result.stderr
    assert "production-safe" in result.stderr
    assert not out.exists()


def test_model_feature_contract_scope_must_match_exported_scope(tmp_path):
    source = tmp_path / "source"
    out = tmp_path / "package"
    write_package_source(source, contract_scope_override=(6, "0"))

    result = run_cli(
        "--from-existing-artifacts",
        str(source),
        "--output-package",
        str(out),
        "--feature-month",
        "2026-04",
        "--package-id",
        "launch_2026_04_test",
    )

    assert result.returncode == 2
    assert "scope_6m" in result.stderr
    assert "scope_months" in result.stderr
    assert "rain_safe" in result.stderr
    assert not out.exists()


def test_empty_feature_columns_fails(tmp_path):
    source = tmp_path / "source"
    out = tmp_path / "package"
    write_package_source(source, empty_feature_columns_scope=0)

    result = run_cli(
        "--from-existing-artifacts",
        str(source),
        "--output-package",
        str(out),
        "--feature-month",
        "2026-04",
        "--package-id",
        "launch_2026_04_test",
    )

    assert result.returncode == 2
    assert "feature_columns" in result.stderr
    assert "empty" in result.stderr
    assert not out.exists()
