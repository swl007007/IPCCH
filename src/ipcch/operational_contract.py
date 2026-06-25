"""Operational launch inference contract helpers."""

from __future__ import annotations

import math
import re
from numbers import Integral
from typing import Iterable, Mapping

import pandas as pd


class OperationalContractError(ValueError):
    """Raised when an operational launch contract is invalid."""


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

VALID_CATEGORIES = {
    "required",
    "derived",
    "static_join",
    "carry_forward",
    "median_impute",
    "unsupported",
    "excluded",
}
VALID_DTYPES = {"string", "integer", "float", "boolean", "categorical"}
VALID_FILL_METHODS = {"none", "median", "static lookup", "carry forward", "derived"}
VALID_SCOPES = {"0", "6", "12", "all"}
VALID_AS_OF_POLICIES = {
    "after_feature_month",
    "carry_forward",
    "feature_month_end",
    "forecast_weather",
    "future",
    "latest_known",
    "not_allowed",
    "post_feature_month",
    "post_target",
    "static",
    "target_period",
    "training_period_stat",
}
VALID_TARGET_SCOPES = {0, 6, 12}
UNSUPPORTED_MODEL_CATEGORIES = {"unsupported", "excluded"}
PROHIBITED_AS_OF_POLICIES = {
    "after_feature_month",
    "forecast_weather",
    "future",
    "post_feature_month",
    "post_target",
    "target_period",
    "not_allowed",
}
TARGET_LEAKAGE_PATTERN = re.compile(
    r"(^|[^A-Za-z0-9])(overall_phase|phase[1-5]_percent|phase[2-5]_worse|target)([^A-Za-z0-9]|$)",
    re.IGNORECASE,
)
FEATURE_MONTH_PATTERN = re.compile(r"^\d{4}-\d{2}$")
FORECAST_PROXY_MARKERS = ("forecast_proxy", "forecasted_weather", "forecast_weather")
FORECAST_WEATHER_PATTERN = re.compile(r"\bforecast(?:ed)?\s+weather\b", re.IGNORECASE)
COMPLETED_PANEL_ONLY_PATTERN = re.compile(r"completed[-_ ]panel[-_ ]only", re.IGNORECASE)
MANUAL_BACKFILL_PATTERN = re.compile(r"manual[-_ ]backfill", re.IGNORECASE)
ROLLING_AFTER_FEATURE_MONTH_PATTERN = re.compile(
    r"\b(rolling|window|cumulative)\b.*\b(after feature month|future|post[-_ ]target)\b"
    r"|\b(after feature month|future|post[-_ ]target)\b.*\b(rolling|window|cumulative)\b",
    re.IGNORECASE,
)
SAFETY_SCAN_FIELDS = (
    "feature_name",
    "source_column",
    "as_of_policy",
    "derive_function",
    "lookup_asset",
    "fill_value_or_stat_key",
    "notes",
)


def target_periods_for_feature_month(
    feature_month: str, scopes: Iterable[int | str]
) -> dict[int, str]:
    """Return target YYYY-MM periods by launch horizon."""

    period = _parse_month(feature_month)
    rows: dict[int, str] = {}
    for scope in scopes:
        scope_months = _parse_scope(scope)
        if scope_months not in VALID_TARGET_SCOPES:
            raise OperationalContractError(
                f"unsupported target scope {scope_months}; expected one of {sorted(VALID_TARGET_SCOPES)}"
            )
        rows[scope_months] = str(period + scope_months)
    return rows


def training_cutoff_for_feature_month(feature_month: str) -> str:
    """Return the exclusive training cutoff date for a feature month."""

    return _parse_month(feature_month).start_time.strftime("%Y-%m-%d")


def validate_feature_contract(
    contract: pd.DataFrame, feature_columns: Iterable[str]
) -> dict[str, object]:
    """Validate feature contract schema and model feature coverage."""

    if not isinstance(contract, pd.DataFrame):
        raise OperationalContractError("feature contract must be a pandas DataFrame")

    feature_columns = list(feature_columns)
    _validate_contract_schema(contract)

    duplicate_features = _duplicates(contract["feature_name"].astype(str).tolist())
    if duplicate_features:
        raise OperationalContractError(
            f"feature contract must contain one row per feature; duplicate feature_name values: {duplicate_features}"
        )

    contract_features = set(contract["feature_name"].astype(str))
    model_features = set(feature_columns)
    missing = sorted(model_features - contract_features)
    if missing:
        raise OperationalContractError(
            f"feature contract is missing model feature rows: {missing}"
        )

    duplicate_model_features = _duplicates(feature_columns)
    if duplicate_model_features:
        raise OperationalContractError(
            f"model feature columns contain duplicates: {duplicate_model_features}"
        )

    model_rows = contract[contract["feature_name"].isin(model_features)]
    unsupported = sorted(
        model_rows.loc[
            model_rows["category"]
            .astype(str)
            .str.strip()
            .str.lower()
            .isin(UNSUPPORTED_MODEL_CATEGORIES),
            "feature_name",
        ].astype(str)
    )
    if unsupported:
        raise OperationalContractError(
            f"unsupported model features are not allowed in feature_columns: {unsupported}"
        )

    extras = sorted(contract_features - model_features)
    return {
        "status": "passed",
        "model_feature_count": len(feature_columns),
        "contract_feature_count": len(contract),
        "ignored_contract_features": extras,
    }


def validate_production_safe_feature_contract(
    contract: pd.DataFrame,
) -> dict[str, object]:
    """Reject contract rows that cannot be used in production-default exports."""

    if not isinstance(contract, pd.DataFrame):
        raise OperationalContractError("feature contract must be a pandas DataFrame")

    _validate_contract_schema(contract)

    unsafe: list[str] = []
    for row in contract.to_dict("records"):
        fields = {field: _clean(row.get(field)) for field in SAFETY_SCAN_FIELDS}
        feature_name = fields["feature_name"]
        as_of_policy = fields["as_of_policy"].lower()
        scanned_values = [value.lower() for value in fields.values() if value]
        category = _clean(row.get("category")).lower()
        fill_method = _clean(row.get("fill_method")).lower()
        lookup_asset = _clean(row.get("lookup_asset"))
        stat_key = _clean(row.get("fill_value_or_stat_key"))

        if any(TARGET_LEAKAGE_PATTERN.search(value) for value in fields.values() if value):
            unsafe.append(f"{feature_name}: target or label leakage")
        if _has_forecast_proxy_marker(scanned_values, as_of_policy):
            unsafe.append(f"{feature_name}: forecasted weather is disabled")
        if as_of_policy in PROHIBITED_AS_OF_POLICIES:
            unsafe.append(f"{feature_name}: prohibited as-of policy {as_of_policy}")
        if any(COMPLETED_PANEL_ONLY_PATTERN.search(value) for value in scanned_values):
            unsafe.append(f"{feature_name}: completed-panel-only source has no approved fallback")
        if any(MANUAL_BACKFILL_PATTERN.search(value) for value in scanned_values):
            unsafe.append(f"{feature_name}: manual backfill lacks an approved as-of policy")
        if any(ROLLING_AFTER_FEATURE_MONTH_PATTERN.search(value) for value in scanned_values):
            unsafe.append(f"{feature_name}: rolling/window feature uses data after feature month")
        if category in {"static_join", "carry_forward"} and not lookup_asset:
            unsafe.append(f"{feature_name}: {category} feature lacks lookup_asset")
        if category == "median_impute" and not stat_key:
            unsafe.append(f"{feature_name}: median_impute feature lacks fill_value_or_stat_key")
        if fill_method in {"static lookup", "carry forward"} and not lookup_asset:
            unsafe.append(f"{feature_name}: {fill_method} fill lacks lookup_asset")
        if fill_method == "median" and not stat_key:
            unsafe.append(f"{feature_name}: median fill lacks fill_value_or_stat_key")

    if unsafe:
        raise OperationalContractError(
            "feature contract is not production-safe: " + "; ".join(unsafe)
        )

    return {"status": "passed", "feature_count": len(contract)}


def decode_phase_predictions(
    scores: pd.DataFrame,
    thresholds: Mapping[str, float],
    monotonicity_policy: str = "fail",
) -> pd.DataFrame:
    """Threshold cumulative phase scores and decode the top phase."""

    if monotonicity_policy not in {"fail", "cummax"}:
        raise OperationalContractError(
            f"unsupported monotonicity_policy: {monotonicity_policy}"
        )

    decoded = scores.copy()
    score_columns = [f"phase{phase}_worse_score" for phase in range(2, 6)]
    pred_columns = [f"phase{phase}_worse_pred" for phase in range(2, 6)]
    present_score_columns = [col for col in score_columns if col in decoded.columns]
    present_pred_columns = [col for col in pred_columns if col in decoded.columns]
    has_complete_scores = len(present_score_columns) == len(score_columns)
    has_any_scores = bool(present_score_columns)
    has_complete_preds = len(present_pred_columns) == len(pred_columns)

    if has_any_scores and present_pred_columns:
        raise OperationalContractError(
            "input must contain either score columns or pred columns, not mixed phase inputs"
        )

    if has_complete_scores:
        score_frame = decoded[score_columns].apply(pd.to_numeric, errors="coerce")
        finite_scores = score_frame.apply(lambda col: col.map(math.isfinite))
        if not finite_scores.all().all():
            raise OperationalContractError(
                "phase score columns must be finite numeric and non-missing"
            )

        for phase in range(2, 6):
            score_col = f"phase{phase}_worse_score"
            pred_col = f"phase{phase}_worse_pred"
            threshold = _threshold_for_phase(thresholds, phase)
            decoded[pred_col] = (score_frame[score_col] >= threshold).astype(int)
    elif not has_any_scores and has_complete_preds:
        pred_frame = decoded[pred_columns].apply(pd.to_numeric, errors="coerce")
        finite_preds = pred_frame.apply(lambda col: col.map(math.isfinite))
        if not finite_preds.all().all() or not pred_frame.isin([0, 1]).all().all():
            raise OperationalContractError(
                "phase prediction columns must be binary 0/1 and non-missing"
            )
        decoded[pred_columns] = pred_frame.astype(int)
    else:
        raise OperationalContractError(
            "input must contain complete score columns or complete pred columns, not mixed/incomplete phase inputs"
        )

    if monotonicity_policy == "cummax":
        corrected = decoded[pred_columns].iloc[:, ::-1].cummax(axis=1).iloc[:, ::-1]
        decoded[pred_columns] = corrected

    if monotonicity_policy == "fail":
        non_monotonic = (decoded[pred_columns].diff(axis=1).iloc[:, 1:] > 0).any(axis=1)
        if non_monotonic.any():
            count = int(non_monotonic.sum())
            raise OperationalContractError(
                f"non-monotonic cumulative phase predictions detected in {count} rows"
            )

    overall = pd.Series(1, index=decoded.index, dtype="int64")
    for phase in range(5, 1, -1):
        pred_col = f"phase{phase}_worse_pred"
        overall = overall.mask((overall == 1) & (decoded[pred_col] == 1), phase)
    decoded["overall_phase_pred"] = overall
    return decoded


def _parse_month(value: str) -> pd.Period:
    if not isinstance(value, str) or not FEATURE_MONTH_PATTERN.fullmatch(value):
        raise OperationalContractError(
            f"feature_month must be formatted as YYYY-MM: {value!r}"
        )
    try:
        return pd.Period(value, freq="M")
    except ValueError as exc:
        raise OperationalContractError(
            f"feature_month must be formatted as YYYY-MM: {value!r}"
        ) from exc


def _parse_scope(value: int | str) -> int:
    if isinstance(value, bool):
        raise OperationalContractError(
            f"scope must be an integer month horizon: {value!r}"
        )
    if isinstance(value, Integral):
        scope = int(value)
    elif isinstance(value, str) and re.fullmatch(r"\d+", value.strip()):
        scope = int(value)
    else:
        raise OperationalContractError(
            f"scope must be an integer month horizon: {value!r}"
        )
    if scope < 0:
        raise OperationalContractError(f"scope must be non-negative: {scope}")
    return scope


def _validate_contract_schema(
    contract: pd.DataFrame, check_category_requirements: bool = True
) -> None:
    missing_columns = [column for column in CONTRACT_COLUMNS if column not in contract.columns]
    if missing_columns:
        raise OperationalContractError(
            f"feature contract is missing required columns: {missing_columns}"
        )

    rows = contract[list(CONTRACT_COLUMNS)].copy()
    invalid_categories = _invalid_values(rows, "category", VALID_CATEGORIES)
    invalid_dtypes = _invalid_values(rows, "dtype", VALID_DTYPES)
    invalid_fill_methods = _invalid_values(rows, "fill_method", VALID_FILL_METHODS)
    invalid_scopes = _invalid_values(rows, "scope_months", VALID_SCOPES)
    invalid_as_of_policies = _invalid_values(rows, "as_of_policy", VALID_AS_OF_POLICIES)

    errors = []
    if invalid_categories:
        errors.append(f"invalid categories: {invalid_categories}")
    if invalid_dtypes:
        errors.append(f"invalid dtypes: {invalid_dtypes}")
    if invalid_fill_methods:
        errors.append(f"invalid fill methods: {invalid_fill_methods}")
    if invalid_scopes:
        errors.append(f"invalid scopes: {invalid_scopes}")
    if invalid_as_of_policies:
        errors.append(f"invalid as_of_policy values: {invalid_as_of_policies}")

    if (
        rows["feature_name"].isna().any()
        or rows["feature_name"].astype(str).str.strip().eq("").any()
    ):
        errors.append("feature_name values must be non-empty")
    if rows["as_of_policy"].astype(str).str.strip().eq("").any():
        errors.append("as_of_policy values must be non-empty")

    required_in_input = rows["required_in_input"]
    invalid_required = ~required_in_input.map(lambda value: isinstance(value, bool))
    if invalid_required.any():
        errors.append("required_in_input values must be boolean")

    tolerance = pd.to_numeric(rows["missing_tolerance"], errors="coerce")
    if tolerance.isna().any() or ((tolerance < 0.0) | (tolerance > 1.0)).any():
        errors.append("missing_tolerance values must be numeric rates from 0 to 1")

    if check_category_requirements:
        _validate_category_requirements(rows, errors)

    if errors:
        raise OperationalContractError("; ".join(errors))


def _validate_category_requirements(rows: pd.DataFrame, errors: list[str]) -> None:
    for row in rows.to_dict("records"):
        feature = _clean(row["feature_name"])
        category = _clean(row["category"]).lower()
        fill_method = _clean(row["fill_method"]).lower()
        source_column = _clean(row["source_column"])
        lookup_asset = _clean(row["lookup_asset"])
        derive_function = _clean(row["derive_function"])
        stat_key = _clean(row["fill_value_or_stat_key"])

        if category == "required" and not source_column:
            errors.append(f"{feature}: required features need source_column")
        if category == "derived" and (not derive_function or fill_method != "derived"):
            errors.append(f"{feature}: derived features need derive_function and fill_method=derived")
        if category == "static_join" and (not lookup_asset or fill_method != "static lookup"):
            errors.append(f"{feature}: static_join features need lookup_asset and fill_method=static lookup")
        if category == "carry_forward" and (not lookup_asset or fill_method != "carry forward"):
            errors.append(f"{feature}: carry_forward features need lookup_asset and fill_method=carry forward")
        if category == "median_impute" and (not stat_key or fill_method != "median"):
            errors.append(f"{feature}: median_impute features need fill_value_or_stat_key and fill_method=median")


def _invalid_values(
    rows: pd.DataFrame, column: str, valid_values: set[str]
) -> list[str]:
    values = rows[column].astype(str).str.strip().str.lower()
    return sorted(values.loc[~values.isin(valid_values)].unique().tolist())


def _duplicates(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    duplicated: set[str] = set()
    for value in values:
        if value in seen:
            duplicated.add(value)
        seen.add(value)
    return sorted(duplicated)


def _threshold_for_phase(thresholds: Mapping[str, float], phase: int) -> float:
    for key in (
        f"phase{phase}_worse_score",
        f"phase{phase}_worse",
        f"phase{phase}",
        str(phase),
        "default",
    ):
        if key in thresholds:
            try:
                threshold = float(thresholds[key])
            except (TypeError, ValueError) as exc:
                raise OperationalContractError(
                    f"threshold for phase {phase} must be a finite numeric value in [0, 1]"
                ) from exc
            if not math.isfinite(threshold) or threshold < 0.0 or threshold > 1.0:
                raise OperationalContractError(
                    f"threshold for phase {phase} must be a finite numeric value in [0, 1]"
                )
            return threshold
    raise OperationalContractError(f"missing threshold for phase {phase}")


def _has_forecast_proxy_marker(values: Iterable[str], as_of_policy: str) -> bool:
    return (
        as_of_policy == "forecast_weather"
        or any(marker in value for marker in FORECAST_PROXY_MARKERS for value in values)
        or any(FORECAST_WEATHER_PATTERN.search(value) for value in values)
    )


def _clean(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()
