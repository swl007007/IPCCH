#!/usr/bin/env python
"""Export a metadata-validated operational launch model package."""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import pandas as pd  # noqa: E402

from ipcch import operational_contract as oc  # noqa: E402


OPERATIONAL_SCOPES = (0, 6, 12)
REQUIRED_ARTIFACTS = (
    "phase2_worse_model.json",
    "phase3_worse_model.json",
    "phase4_worse_model.json",
    "phase5_worse_model.json",
    "feature_columns.json",
    "feature_contract.csv",
)
THRESHOLDS = {"default": 0.2}
MONOTONICITY_POLICY = "fail"


@dataclass(frozen=True)
class ScopePackage:
    scope_months: int
    source_dir: Path
    feature_columns: list[str]
    feature_contract_validation: dict[str, object]
    feature_eligibility_validation: dict[str, object]


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Assemble an operational launch package from existing 0m, 6m, and 12m artifacts."
    )
    parser.add_argument(
        "--from-existing-artifacts",
        required=True,
        type=Path,
        help="Source root containing scope_0m, scope_6m, and scope_12m artifact directories.",
    )
    parser.add_argument(
        "--output-package",
        required=True,
        type=Path,
        help="Output model package directory to create.",
    )
    parser.add_argument(
        "--feature-month",
        required=True,
        help="Launch feature month formatted as YYYY-MM.",
    )
    parser.add_argument(
        "--package-id",
        required=True,
        help="Stable package identifier to record in the root manifest.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace the output package directory if it already exists.",
    )
    return parser.parse_args(argv)


def read_feature_columns(path: Path) -> list[str]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise oc.OperationalContractError(f"invalid JSON in {path}") from exc

    if isinstance(payload, list):
        columns = payload
    elif isinstance(payload, dict) and isinstance(payload.get("feature_columns"), list):
        columns = payload["feature_columns"]
    else:
        raise oc.OperationalContractError(
            f"{path} must contain a JSON list or an object with a feature_columns list"
        )

    if not columns:
        raise oc.OperationalContractError(f"{path} must not be empty")
    if not all(isinstance(column, str) and column.strip() for column in columns):
        raise oc.OperationalContractError(
            f"{path} must contain only non-empty string feature names"
        )
    return list(columns)


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def validate_path_overlap(source_root: Path, output_package: Path) -> None:
    resolved_source = source_root.resolve()
    resolved_output = output_package.resolve(strict=False)
    if (
        resolved_output == resolved_source
        or is_relative_to(resolved_output, resolved_source)
        or is_relative_to(resolved_source, resolved_output)
    ):
        raise oc.OperationalContractError(
            "--output-package and --from-existing-artifacts overlap; choose a package directory outside the source artifact tree"
        )


def validate_model_feature_scope(
    contract: pd.DataFrame, feature_columns: Sequence[str], scope_months: int
) -> None:
    model_rows = contract[
        contract["feature_name"].astype(str).isin(set(feature_columns))
    ].copy()
    allowed_scopes = {str(scope_months), "all"}
    row_scopes = model_rows["scope_months"].astype(str).str.strip().str.lower()
    mismatched = sorted(
        model_rows.loc[~row_scopes.isin(allowed_scopes), "feature_name"]
        .astype(str)
        .tolist()
    )
    if mismatched:
        raise oc.OperationalContractError(
            f"model feature contract rows must have scope_months={scope_months} or all; mismatched feature(s): {mismatched}"
        )


def validate_scope(source_root: Path, scope_months: int) -> ScopePackage:
    scope_dir = source_root / f"scope_{scope_months}m"
    if not scope_dir.is_dir():
        raise oc.OperationalContractError(f"missing required scope directory: {scope_dir}")

    missing_artifacts = [
        artifact for artifact in REQUIRED_ARTIFACTS if not (scope_dir / artifact).is_file()
    ]
    if missing_artifacts:
        raise oc.OperationalContractError(
            f"{scope_dir} is missing required artifact(s): {missing_artifacts}"
        )

    feature_columns = read_feature_columns(scope_dir / "feature_columns.json")
    contract_path = scope_dir / "feature_contract.csv"
    try:
        contract = pd.read_csv(contract_path)
    except Exception as exc:
        raise oc.OperationalContractError(
            f"failed to read feature contract CSV for scope_{scope_months}m: {contract_path}"
        ) from exc

    try:
        feature_contract_validation = oc.validate_feature_contract(
            contract, feature_columns
        )
        feature_eligibility_validation = oc.validate_production_safe_feature_contract(
            contract
        )
        validate_model_feature_scope(contract, feature_columns, scope_months)
    except oc.OperationalContractError as exc:
        raise oc.OperationalContractError(
            f"scope_{scope_months}m feature contract validation failed: {exc}"
        ) from exc

    return ScopePackage(
        scope_months=scope_months,
        source_dir=scope_dir,
        feature_columns=feature_columns,
        feature_contract_validation=feature_contract_validation,
        feature_eligibility_validation=feature_eligibility_validation,
    )


def validate_inputs(
    source_root: Path, output_package: Path, feature_month: str, overwrite: bool
) -> tuple[dict[int, str], list[ScopePackage]]:
    if not source_root.is_dir():
        raise oc.OperationalContractError(f"source artifact root not found: {source_root}")
    validate_path_overlap(source_root, output_package)
    if output_package.exists() and not overwrite:
        raise oc.OperationalContractError(
            f"output package already exists; pass --overwrite to replace it: {output_package}"
        )

    target_periods = oc.target_periods_for_feature_month(
        feature_month, OPERATIONAL_SCOPES
    )
    scope_packages = [validate_scope(source_root, scope) for scope in OPERATIONAL_SCOPES]
    return target_periods, scope_packages


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def assemble_package(
    output_package: Path,
    feature_month: str,
    package_id: str,
    target_periods: dict[int, str],
    scope_packages: Sequence[ScopePackage],
    overwrite: bool,
) -> Path:
    if output_package.exists():
        if overwrite:
            shutil.rmtree(output_package)
        else:
            raise oc.OperationalContractError(
                f"output package already exists; pass --overwrite to replace it: {output_package}"
            )

    output_package.mkdir(parents=True)
    for scope_package in scope_packages:
        scope_dir = output_package / f"scope_{scope_package.scope_months}m"
        scope_dir.mkdir()
        for artifact in REQUIRED_ARTIFACTS:
            shutil.copy2(scope_package.source_dir / artifact, scope_dir / artifact)

        metadata = {
            "scope_months": scope_package.scope_months,
            "feature_month": feature_month,
            "target_month": target_periods[scope_package.scope_months],
            "thresholds": THRESHOLDS,
            "monotonicity_policy": MONOTONICITY_POLICY,
            "feature_contract_validation": scope_package.feature_contract_validation,
            "feature_eligibility_validation": scope_package.feature_eligibility_validation,
        }
        write_json(scope_dir / "model_metadata.json", metadata)

    manifest = {
        "package_id": package_id,
        "created_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "feature_month": feature_month,
        "target_periods": {
            str(scope): target_periods[scope] for scope in OPERATIONAL_SCOPES
        },
        "scopes": list(OPERATIONAL_SCOPES),
        "forecasted_weather": {"enabled": False},
    }
    manifest_path = output_package / "model_package_manifest.json"
    write_json(manifest_path, manifest)
    return manifest_path


def run(args: argparse.Namespace) -> Path:
    target_periods, scope_packages = validate_inputs(
        args.from_existing_artifacts,
        args.output_package,
        args.feature_month,
        args.overwrite,
    )
    return assemble_package(
        args.output_package,
        args.feature_month,
        args.package_id,
        target_periods,
        scope_packages,
        args.overwrite,
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        manifest_path = run(args)
    except oc.OperationalContractError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(manifest_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
