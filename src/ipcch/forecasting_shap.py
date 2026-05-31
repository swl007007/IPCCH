from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

TARGET = "phase3_worse"
ALLOWED_SAMPLE_TYPES = ("train", "test")
EXPECTED_FEATURE_GROUP_COUNT = 6
DEFAULT_CROSSWALK_KEY = "six_category_feature_crosswalk"
DEFAULT_TEST_YEARS = (2022, 2023, 2024, 2025)
RAW_SHAP_MAX_ROWS_DEFAULT = 100_000
VALID_DIAGNOSTIC_SEVERITIES = ("info", "warning", "error")


@dataclass(frozen=True)
class ShapRunConfig:
    enabled: bool = False
    sample_type: str = "train"
    crosswalk_path: Optional[Path] = None
    crosswalk_key: str = DEFAULT_CROSSWALK_KEY
    crosswalk_feature_column: Optional[str] = None
    crosswalk_category_column: Optional[str] = None
    allow_unmapped_features: bool = False
    save_raw: bool = False
    raw_max_rows: int = RAW_SHAP_MAX_ROWS_DEFAULT
    allow_large_raw: bool = False


@dataclass(frozen=True)
class ShapArtifactPaths:
    feature_summary_csv: Path
    six_category_long_csv: Path
    diagnostics_csv: Path
    metadata_json: Path
    raw_values_csv: Path
    matrix_csv_paths: Mapping[str, Path]
    heatmap_png_paths: Mapping[str, Path]


@dataclass(frozen=True)
class ShapEngineInfo:
    package: str
    version: str


@dataclass(frozen=True)
class ShapDiagnostic:
    forecasting_scope: str
    test_year: int
    target: str
    diagnostic_type: str
    severity: str
    message: str
    feature_name: Optional[str] = None
    mapped_abs_shap_sum: Optional[float] = None
    unmapped_abs_shap_sum: Optional[float] = None
    unmapped_abs_shap_share: Optional[float] = None


@dataclass(frozen=True)
class Phase3ShapContext:
    forecasting_scope: str
    scope_label: str
    test_year: int
    sample_type: str
    feature_columns: Sequence[str]
    shap_matrix: pd.DataFrame
    shap_values: np.ndarray
    engine_info: ShapEngineInfo


class ShapDependencyError(RuntimeError):
    pass


class ShapValidationError(ValueError):
    pass


def phase3_shap_filename(artifact_type: str, forecasting_scope: Optional[str] = None, suffix: str = "csv") -> str:
    parts = [TARGET]
    if forecasting_scope:
        parts.append(forecasting_scope)
    parts.append(artifact_type)
    return "_".join(parts) + f".{suffix}"


def validate_sample_type(sample_type: str) -> str:
    if sample_type not in ALLOWED_SAMPLE_TYPES:
        raise ShapValidationError(f"Unsupported SHAP explanation sample type: {sample_type}")
    return sample_type


def validate_phase3_target(target: str) -> None:
    if target != TARGET:
        raise ShapValidationError(f"SHAP recording supports only {TARGET}; received {target}")


def import_shap_engine() -> Tuple[Any, ShapEngineInfo]:
    try:
        import shap  # type: ignore
    except Exception as exc:
        raise ShapDependencyError("SHAP was enabled but the shap package/engine is unavailable") from exc
    version = getattr(shap, "__version__", "unknown")
    return shap, ShapEngineInfo(package="shap", version=str(version))


def validate_feature_alignment(shap_matrix: pd.DataFrame, feature_columns: Sequence[str]) -> None:
    expected = list(feature_columns)
    actual = list(shap_matrix.columns)
    if actual != expected:
        raise ShapValidationError("SHAP matrix columns do not match fitted phase-3 feature order")


def normalize_shap_values(raw_values: Any, shap_matrix: pd.DataFrame) -> np.ndarray:
    values = getattr(raw_values, "values", raw_values)
    if isinstance(values, list):
        if len(values) != 1:
            raise ShapValidationError("Expected one SHAP output array for phase-3 regressor")
        values = values[0]
    array = np.asarray(values)
    if array.ndim == 3 and array.shape[-1] == 1:
        array = array[:, :, 0]
    if array.ndim != 2:
        raise ShapValidationError(f"Expected 2D SHAP values, received {array.ndim}D")
    expected_shape = (len(shap_matrix), len(shap_matrix.columns))
    if array.shape != expected_shape:
        raise ShapValidationError(f"SHAP values shape {array.shape} does not match SHAP matrix shape {expected_shape}")
    if not np.isfinite(array).all():
        raise ShapValidationError("SHAP values contain NaN or infinite values")
    return array.astype(float, copy=False)


def compute_phase3_shap_values(model: Any, shap_matrix: pd.DataFrame, feature_columns: Sequence[str]) -> Tuple[np.ndarray, ShapEngineInfo]:
    validate_phase3_target(TARGET)
    validate_feature_alignment(shap_matrix, feature_columns)
    shap, engine_info = import_shap_engine()
    try:
        explainer = shap.TreeExplainer(model)
        raw_values = explainer.shap_values(shap_matrix)
    except Exception as exc:
        raise ShapDependencyError("SHAP engine failed to explain the fitted phase-3 model") from exc
    return normalize_shap_values(raw_values, shap_matrix), engine_info


def diagnostic_record(
    forecasting_scope: str,
    test_year: int,
    diagnostic_type: str,
    severity: str,
    message: str,
    feature_name: Optional[str] = None,
    mapped_abs_shap_sum: Optional[float] = None,
    unmapped_abs_shap_sum: Optional[float] = None,
    unmapped_abs_shap_share: Optional[float] = None,
) -> Dict[str, object]:
    if severity not in VALID_DIAGNOSTIC_SEVERITIES:
        raise ShapValidationError(f"Unsupported diagnostic severity: {severity}")
    return ShapDiagnostic(
        forecasting_scope=forecasting_scope,
        test_year=int(test_year),
        target=TARGET,
        diagnostic_type=diagnostic_type,
        severity=severity,
        message=message,
        feature_name=feature_name,
        mapped_abs_shap_sum=mapped_abs_shap_sum,
        unmapped_abs_shap_sum=unmapped_abs_shap_sum,
        unmapped_abs_shap_share=unmapped_abs_shap_share,
    ).__dict__.copy()


def unavailable_split_diagnostic(forecasting_scope: str, test_year: int, reason: str) -> Dict[str, object]:
    return diagnostic_record(forecasting_scope, test_year, "unavailable split", "warning", reason)


def empty_shap_rows_diagnostic(forecasting_scope: str, test_year: int, sample_type: str) -> Dict[str, object]:
    return diagnostic_record(
        forecasting_scope,
        test_year,
        "skipped SHAP",
        "warning",
        f"No SHAP explanation rows available for {sample_type} sample",
    )


def load_crosswalk(path: Path, feature_column: Optional[str] = None, category_column: Optional[str] = None) -> Tuple[pd.DataFrame, str, str]:
    crosswalk = pd.read_csv(path)
    feature_col, category_col = detect_crosswalk_columns(crosswalk, feature_column, category_column)
    return crosswalk[[feature_col, category_col]].copy(), feature_col, category_col


def detect_crosswalk_columns(crosswalk: pd.DataFrame, feature_column: Optional[str] = None, category_column: Optional[str] = None) -> Tuple[str, str]:
    feature_candidates = ("feature_name", "variable", "variable_name", "feature", "column")
    category_candidates = ("feature_group", "six_category", "category", "group")
    feature_col = _select_column(crosswalk, feature_column, feature_candidates, "feature")
    category_col = _select_column(crosswalk, category_column, category_candidates, "category")
    if feature_col == category_col:
        raise ShapValidationError("Crosswalk feature and category columns must be different")
    return feature_col, category_col


def _select_column(crosswalk: pd.DataFrame, explicit: Optional[str], candidates: Sequence[str], label: str) -> str:
    if explicit:
        if explicit not in crosswalk.columns:
            raise ShapValidationError(f"Crosswalk {label} column not found: {explicit}")
        return explicit
    lower_to_original = {str(column).lower(): str(column) for column in crosswalk.columns}
    for candidate in candidates:
        if candidate in lower_to_original:
            return lower_to_original[candidate]
    raise ShapValidationError(f"Could not auto-detect crosswalk {label} column")


def validate_crosswalk(
    crosswalk: pd.DataFrame,
    feature_columns: Sequence[str],
    feature_column: str,
    category_column: str,
    allow_unmapped: bool = False,
) -> Tuple[pd.DataFrame, List[Dict[str, object]]]:
    required = {feature_column, category_column}
    missing_columns = required - set(crosswalk.columns)
    if missing_columns:
        raise ShapValidationError("Crosswalk is missing required columns: " + ", ".join(sorted(missing_columns)))
    cleaned = crosswalk[[feature_column, category_column]].dropna().copy()
    cleaned[feature_column] = cleaned[feature_column].astype(str)
    cleaned[category_column] = cleaned[category_column].astype(str)
    mapping_counts = cleaned.groupby(feature_column)[category_column].nunique()
    duplicates = mapping_counts[mapping_counts > 1]
    if not duplicates.empty:
        raise ShapValidationError("Duplicate crosswalk mappings with multiple groups: " + ", ".join(duplicates.index.astype(str)))
    cleaned = cleaned.drop_duplicates(subset=[feature_column]).rename(columns={feature_column: "feature_name", category_column: "feature_group"})
    groups = sorted(cleaned["feature_group"].dropna().unique())
    if len(groups) != EXPECTED_FEATURE_GROUP_COUNT:
        raise ShapValidationError(f"Crosswalk must define exactly {EXPECTED_FEATURE_GROUP_COUNT} feature groups; found {len(groups)}")
    feature_set = set(map(str, feature_columns))
    mapped_set = set(cleaned["feature_name"])
    missing = sorted(feature_set - mapped_set)
    diagnostics: List[Dict[str, object]] = []
    if missing and not allow_unmapped:
        raise ShapValidationError("Missing SHAP crosswalk mappings: " + ", ".join(missing))
    for feature_name in missing:
        diagnostics.append(diagnostic_record("", 0, "missing mapping", "warning", "Feature missing from SHAP crosswalk", feature_name))
    return cleaned, diagnostics


def per_feature_shap_summary(
    shap_values: np.ndarray,
    feature_columns: Sequence[str],
    crosswalk: pd.DataFrame,
    forecasting_scope: str,
    scope_label: str,
    test_year: int,
    sample_type: str,
) -> pd.DataFrame:
    array = np.asarray(shap_values, dtype=float)
    if array.ndim != 2 or array.shape[1] != len(feature_columns):
        raise ShapValidationError("SHAP values do not align with feature columns for per-feature summary")
    abs_sums = np.abs(array).sum(axis=0)
    mapping = crosswalk.set_index("feature_name")["feature_group"].to_dict()
    rows = []
    for feature_name, abs_sum in zip(feature_columns, abs_sums):
        if feature_name not in mapping:
            continue
        rows.append(
            {
                "forecasting_scope": forecasting_scope,
                "scope_label": scope_label,
                "test_year": int(test_year),
                "target": TARGET,
                "sample_type": sample_type,
                "feature_name": feature_name,
                "feature_group": mapping[feature_name],
                "abs_shap_sum": float(abs_sum),
                "mean_abs_shap": float(abs_sum / array.shape[0]) if array.shape[0] else 0.0,
                "n_explanation_rows": int(array.shape[0]),
            }
        )
    return pd.DataFrame(rows)


def aggregate_six_category_importance(
    per_feature_summary: pd.DataFrame,
    feature_groups: Sequence[str],
    forecasting_scope: str,
    scope_label: str,
    test_year: int,
    sample_type: str,
) -> Tuple[pd.DataFrame, List[Dict[str, object]]]:
    diagnostics: List[Dict[str, object]] = []
    grouped = per_feature_summary.groupby("feature_group", as_index=True)["abs_shap_sum"].sum() if not per_feature_summary.empty else pd.Series(dtype=float)
    total = float(grouped.sum()) if len(grouped) else 0.0
    zero_denominator = total == 0.0
    if zero_denominator:
        diagnostics.append(diagnostic_record(forecasting_scope, test_year, "zero denominator", "warning", "Mapped absolute SHAP denominator is zero"))
    rows = []
    for feature_group in feature_groups:
        group_sum = float(grouped.get(feature_group, 0.0))
        rows.append(
            {
                "forecasting_scope": forecasting_scope,
                "scope_label": scope_label,
                "test_year": int(test_year),
                "target": TARGET,
                "sample_type": sample_type,
                "feature_group": feature_group,
                "feature_group_abs_shap_sum": group_sum,
                "total_mapped_abs_shap_sum": total,
                "relative_importance": 0.0 if zero_denominator else group_sum / total,
                "zero_denominator": bool(zero_denominator),
            }
        )
    return pd.DataFrame(rows), diagnostics


def unmapped_feature_diagnostics(
    shap_values: np.ndarray,
    feature_columns: Sequence[str],
    mapped_features: Sequence[str],
    forecasting_scope: str,
    test_year: int,
) -> List[Dict[str, object]]:
    mapped_set = set(mapped_features)
    abs_sums = np.abs(np.asarray(shap_values, dtype=float)).sum(axis=0)
    mapped_sum = float(sum(value for feature, value in zip(feature_columns, abs_sums) if feature in mapped_set))
    unmapped = [(feature, float(value)) for feature, value in zip(feature_columns, abs_sums) if feature not in mapped_set]
    unmapped_sum = float(sum(value for _, value in unmapped))
    denominator = mapped_sum + unmapped_sum
    share = 0.0 if denominator == 0.0 else unmapped_sum / denominator
    return [
        diagnostic_record(
            forecasting_scope,
            test_year,
            "missing mapping",
            "warning",
            "Unmapped SHAP features excluded from six-category denominator",
            feature_name=feature,
            mapped_abs_shap_sum=mapped_sum,
            unmapped_abs_shap_sum=unmapped_sum,
            unmapped_abs_shap_share=share,
        )
        for feature, _ in unmapped
    ]


def scope_matrix(
    six_category_long: pd.DataFrame,
    forecasting_scope: str,
    feature_groups: Sequence[str],
    test_years: Sequence[int] = DEFAULT_TEST_YEARS,
) -> pd.DataFrame:
    subset = six_category_long[six_category_long["forecasting_scope"] == forecasting_scope]
    matrix = subset.pivot_table(
        index="feature_group",
        columns="test_year",
        values="relative_importance",
        aggfunc="first",
    )
    matrix = matrix.reindex(index=list(feature_groups), columns=list(test_years), fill_value=0.0)
    matrix.columns = [str(year) for year in matrix.columns]
    matrix.index.name = "feature_group"
    return matrix.reset_index()


def validate_phase3_artifact_name(path: Path) -> None:
    name = path.name
    forbidden = ("phase4", "phase5", "phase3_phase4", "combined")
    if not name.startswith(TARGET) or any(token in name for token in forbidden):
        raise ShapValidationError(f"Invalid phase-3 SHAP artifact name: {name}")


def render_heatmap(matrix: pd.DataFrame, output_path: Path, title: str, sample_type: str) -> None:
    validate_phase3_artifact_name(output_path)
    import matplotlib.pyplot as plt

    years = [str(year) for year in DEFAULT_TEST_YEARS]
    values = matrix.set_index("feature_group")[years].astype(float)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(7, 3.8))
    vmax = max(0.4, float(values.to_numpy().max()))
    image = ax.imshow(values.to_numpy(), vmin=0, vmax=vmax, cmap="YlGnBu", aspect="auto")
    ax.set_xticks(range(len(years)), years)
    ax.set_yticks(range(len(values.index)), values.index)
    for row_index in range(values.shape[0]):
        for col_index in range(values.shape[1]):
            value = float(values.iat[row_index, col_index])
            text_color = "white" if value / vmax >= 0.58 else "black"
            ax.text(col_index, row_index, f"{value:.2f}", ha="center", va="center", fontsize=8, color=text_color)
    fig.colorbar(image, ax=ax, label=f"relative importance (0-{vmax:.2f})")
    ax.set_title(f"{title} ({TARGET}, SHAP sample: {sample_type})")
    ax.set_xlabel("test year")
    ax.set_ylabel("feature group")
    fig.tight_layout()
    fig.savefig(output_path, dpi=200)
    plt.close(fig)


def raw_shap_frame(
    shap_values: np.ndarray,
    shap_matrix: pd.DataFrame,
    forecasting_scope: str,
    scope_label: str,
    test_year: int,
    sample_type: str,
) -> pd.DataFrame:
    values = normalize_shap_values(shap_values, shap_matrix)
    rows = []
    for row_position, index_value in enumerate(shap_matrix.index):
        for col_position, feature_name in enumerate(shap_matrix.columns):
            rows.append(
                {
                    "forecasting_scope": forecasting_scope,
                    "scope_label": scope_label,
                    "test_year": int(test_year),
                    "target": TARGET,
                    "sample_type": sample_type,
                    "row_index": index_value,
                    "feature_name": feature_name,
                    "shap_value": float(values[row_position, col_position]),
                }
            )
    return pd.DataFrame(rows)


def enforce_raw_export_size(frame: pd.DataFrame, max_rows: int, allow_large: bool) -> None:
    if max_rows <= 0:
        raise ShapValidationError("Raw SHAP max rows must be positive")
    if len(frame) > max_rows and not allow_large:
        raise ShapValidationError(
            f"Raw SHAP export would write {len(frame)} rows, exceeding limit {max_rows}; use --allow-large-raw-shap or raise --raw-shap-max-rows"
        )
