"""April 2026 global nowcasting launch (comprehensive-CSV fallback).

Production launch workflow (NOT a held-out validation experiment): trains the
canonical four-regressor cumulative-phase XGBoost workflow on valid-target rows
strictly before the training cutoff, then predicts ``phase2_worse``..``phase5_worse``
for every eligible launch-month ``area_id`` and derives ``overall_phase_pred`` via
the canonical top-down rule with ``th=0.2``.

Both training rows and the launch X_test come from one comprehensive deep-feature
CSV. This module reuses the canonical deep-feature workflow utilities in
``ipcch.forecasting_weight_decay`` and the prediction-only phase conversion in
``ipcch.forecast_diagnostics`` (see specs/004-launch-2026-04-nowcasting-fallback).

Reusable launch logic lives here (Principle II). Heavy Mode-1 training is gated
behind explicit approval by the CLI; this module never trains unless asked.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from ipcch import paths
from ipcch import forecasting_weight_decay as fwd
from ipcch import forecast_diagnostics as fdiag
from ipcch import forecasting_shap as fshap

# --- Launch constants -------------------------------------------------------
COMPREHENSIVE_SOURCE_KEY = "deep_features_2026_target_corrected_dataset"
EXPECTED_SOURCE_FILENAME = (
    "assembled_IPCCH/features/forecasting_subset_IPCCH_2026_target_corrected_deep_features.csv"
)
DEFAULT_LAUNCH_MONTH = "2026-04"
DEFAULT_TRAINING_CUTOFF = "2026-04-01"
DEFAULT_SCALE = "global"
CANONICAL_THRESHOLD = 0.2
MODEL_WORKFLOW = "deep_feature_weight_decay_cumulative_regression"
FORECASTED_WEATHER_SOURCE_KEY = "forecasted_weather_by_area_time"
HISTORICAL_WEATHER_SOURCE_KEY = "ipcch_2026_completed_dataset"
GROUPED_SHAP_CROSSWALK_KEY = fshap.DEFAULT_CROSSWALK_KEY
FORECASTED_WEATHER_DEFAULT_RELATIVE_PATH = Path("assembled_IPCCH") / "spatial" / "cds_api_tif_values_by_area_time.csv"
FORECASTED_WEATHER_COLUMNS = ("Rainf_f_tavg_mean", "Tair_f_tavg_mean")
FORECASTED_WEATHER_PROXY_SUFFIX = "_forecast_proxy"
TARGET_COLUMNS = fwd.TARGET_COLUMNS  # phase2_worse..phase5_worse
PHASE_FROM_TARGET = {"phase2_worse": 2, "phase3_worse": 3, "phase4_worse": 4, "phase5_worse": 5}
IDENTIFIER_DERIVED_BASE = ("lat", "lon")
# Target/label columns excluded from features (FR-011b); patterns enforced by
# select_numeric_feature_columns plus the documented audit families below.
TARGET_LABEL_COLUMNS = (
    "overall_phase",
    "overall_phase_pred",
    *fwd.PERCENT_TARGET_COLUMNS,
    *fwd.TARGET_COLUMNS,
)
TARGET_DERIVED_PATTERNS = ("overall_phase_lag", "target_relative", "diagnostic", "phase_target", "target")
ALLOWED_SCOPE_MONTHS = (0, 3, 6, 12)
# Raw identifier / reporting columns preserved for output/joins but never modelled.
REPORTING_ID_COLUMNS = ("area_id", "country", "region", "name", "admin_code", "pcode", "iso3", "iso")
MODEL_METADATA_COLUMNS = ("scope_months",)


class LaunchError(ValueError):
    """Raised for actionable launch configuration / data errors."""


@dataclass(frozen=True)
class ForecastedWeatherMonthSpec:
    offset_from_feature_months: int
    target_minus_months: int
    period_column: str


@dataclass(frozen=True)
class LaunchConfig:
    comprehensive_source: Path
    launch_month: str = DEFAULT_LAUNCH_MONTH
    scale: str = DEFAULT_SCALE
    training_cutoff: str = DEFAULT_TRAINING_CUTOFF
    threshold: float = CANONICAL_THRESHOLD
    scope_months: int = 0
    out_root: Path = field(default_factory=lambda: paths.RESULTS_DIR / "launch" / "nowcasting_2026_04")
    report_root: Path = field(default_factory=lambda: paths.REPORTS_DIR / "launch" / "nowcasting_2026_04")
    seed: int = 42
    add_identifier_features: bool = True
    allow_missing_identifier_features: bool = False
    identifier_source: Optional[Path] = None
    half_life_months: float = fwd.DEFAULT_HALF_LIFE_MONTHS
    use_time_decay: bool = True
    hyperparameter_set: str = "canonical"
    hyperparameters_path: Optional[Path] = None
    hyperparameters_p3_path: Optional[Path] = None
    dedup_rule: Optional[str] = None
    drop_nonfinite_predictions: bool = False
    using_forecasted_weather: bool = False
    forecasted_weather_source: Optional[Path] = None
    compute_grouped_shap: bool = False
    grouped_shap_crosswalk_path: Optional[Path] = None
    grouped_shap_crosswalk_key: str = GROUPED_SHAP_CROSSWALK_KEY
    grouped_shap_crosswalk_feature_column: Optional[str] = None
    grouped_shap_crosswalk_category_column: Optional[str] = None
    run_id: str = "launch_2026_04"
    execution_mode: str = "train_and_predict"

    def __post_init__(self) -> None:
        if self.scope_months not in ALLOWED_SCOPE_MONTHS:
            allowed = ", ".join(str(v) for v in ALLOWED_SCOPE_MONTHS)
            raise LaunchError(f"scope_months must be one of {allowed}; received {self.scope_months!r}.")


# --- Source resolution & validation (T005, FR-006/010, I1) ------------------

def resolve_comprehensive_source(explicit_path: Optional[str]) -> Path:
    """Resolve the comprehensive source from an explicit flag or the workspace key.

    The key ``deep_features_2026_target_corrected_dataset`` is workspace-local and
    expected in ``configs/paths.local.json``; it is intentionally not a repo default.
    """
    if explicit_path:
        resolved = Path(explicit_path).expanduser()
    else:
        try:
            resolved = paths.external_path(COMPREHENSIVE_SOURCE_KEY)
        except KeyError as exc:
            raise LaunchError(
                "Comprehensive source path is not configured. The external key "
                f"'{COMPREHENSIVE_SOURCE_KEY}' is not defined. Either pass "
                "--comprehensive-source <path> or add the key to configs/paths.local.json "
                f"pointing at '{EXPECTED_SOURCE_FILENAME}'."
            ) from exc
    if not resolved.exists():
        raise LaunchError(f"Comprehensive source file does not exist: {resolved}")
    return resolved


def _parse_month(launch_month: str) -> Tuple[int, int]:
    try:
        year_s, month_s = launch_month.split("-")
        return int(year_s), int(month_s)
    except Exception as exc:  # noqa: BLE001
        raise LaunchError(f"launch_month must be 'YYYY-MM'; received {launch_month!r}") from exc


def add_months(period: pd.Period, months: int) -> pd.Period:
    return pd.Period(period, freq="M") + int(months)


def subtract_months(period: pd.Period, months: int) -> pd.Period:
    return pd.Period(period, freq="M") - int(months)


def target_period_for_scope(feature_period: pd.Period, scope_months: int) -> pd.Period:
    if scope_months not in ALLOWED_SCOPE_MONTHS:
        allowed = ", ".join(str(v) for v in ALLOWED_SCOPE_MONTHS)
        raise LaunchError(f"scope_months must be one of {allowed}; received {scope_months!r}.")
    return add_months(feature_period, scope_months)


def launch_feature_period(config: LaunchConfig) -> pd.Period:
    year, month = _parse_month(config.launch_month)
    return pd.Period(f"{year:04d}-{month:02d}", freq="M")


def launch_target_period(config: LaunchConfig) -> pd.Period:
    return target_period_for_scope(launch_feature_period(config), config.scope_months)


def monthly_period_from_year_month(year: pd.Series, month: pd.Series) -> pd.Series:
    y = pd.to_numeric(year, errors="raise").astype(int).astype(str)
    m = pd.to_numeric(month, errors="raise").astype(int).astype(str).str.zfill(2)
    return pd.Series(pd.PeriodIndex(y + "-" + m, freq="M"), index=year.index)


_MASK_COLUMNS = ("area_id", "year", "month", "overall_phase", *fwd.PERCENT_TARGET_COLUMNS)


def _row_keep_mask(
    small: pd.DataFrame,
    training_cutoff: str,
    launch_month: str,
    scope_months: int = 0,
    using_forecasted_weather: bool = False,
) -> np.ndarray:
    """Boolean keep-mask in original file order for the memory-safe CSV pass."""
    prepared = small.replace([np.inf, -np.inf], np.nan).copy()
    prepared = fwd.add_monthly_date(prepared)
    prepared = fwd.derive_cumulative_targets(prepared)
    prepared["overall_phase"] = pd.to_numeric(prepared["overall_phase"], errors="coerce")
    cutoff = pd.Timestamp(training_cutoff)
    ly, lm = _parse_month(launch_month)
    train_mask = _training_mask(prepared, cutoff)
    launch_mask = (prepared["year"].astype(int) == ly) & (prepared["month"].astype(int) == lm)
    keep_mask = train_mask | launch_mask
    if scope_months:
        target_period = monthly_period_from_year_month(prepared.loc[train_mask, "year"], prepared.loc[train_mask, "month"])
        feature_periods = target_period.map(lambda p: subtract_months(p, scope_months)).astype(str)
        period = monthly_period_from_year_month(prepared["year"], prepared["month"]).astype(str)
        scoped_feature_keys = pd.MultiIndex.from_frame(
            pd.DataFrame({
                "area_id": prepared.loc[train_mask, "area_id"].astype(str),
                "period": feature_periods,
            })
        )
        row_keys = pd.MultiIndex.from_frame(pd.DataFrame({"area_id": prepared["area_id"].astype(str), "period": period}))
        keep_mask |= pd.Series(row_keys.isin(scoped_feature_keys), index=prepared.index)
        if using_forecasted_weather and scope_months in (3, 6, 12):
            feature_period_index = pd.PeriodIndex(feature_periods, freq="M")
            proxy_frames = []
            for spec in _forecasted_weather_month_specs(scope_months):
                proxy_frames.append(
                    pd.DataFrame({
                        "area_id": prepared.loc[train_mask, "area_id"].astype(str).values,
                        "period": (feature_period_index + spec.offset_from_feature_months).astype(str),
                    })
                )
            proxy_keys = pd.MultiIndex.from_frame(pd.concat(proxy_frames, ignore_index=True))
            keep_mask |= pd.Series(row_keys.isin(proxy_keys), index=prepared.index)
    return keep_mask.to_numpy()


def load_comprehensive_source(
    path: Path,
    sample_rows: Optional[int] = None,
    *,
    training_cutoff: Optional[str] = None,
    launch_month: Optional[str] = None,
    scope_months: int = 0,
    using_forecasted_weather: bool = False,
) -> pd.DataFrame:
    """Load the comprehensive source.

    When ``training_cutoff`` and ``launch_month`` are supplied (and no
    ``sample_rows`` cap is requested), use a memory-safe two-pass read: pass 1
    reads only the narrow mask columns to find which rows are training-eligible,
    launch-month, or needed as scoped feature/proxy rows; pass 2 reads all columns
    for just those rows. Falls back to a plain read for samples or when the mask
    columns are unavailable.
    """
    if sample_rows is not None or training_cutoff is None or launch_month is None:
        return pd.read_csv(path, nrows=sample_rows)
    header = pd.read_csv(path, nrows=0)
    if not all(c in header.columns for c in _MASK_COLUMNS):
        return pd.read_csv(path)
    small = pd.read_csv(path, usecols=list(_MASK_COLUMNS))
    keep = _row_keep_mask(small, training_cutoff, launch_month, scope_months, using_forecasted_weather)
    del small
    keep_positions = set(np.flatnonzero(keep).tolist())
    return pd.read_csv(path, skiprows=lambda i: i > 0 and (i - 1) not in keep_positions)


def validate_required_source_columns(df: pd.DataFrame, predictor_columns: Optional[Sequence[str]] = None) -> None:
    required = ["area_id", "year", "month"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise LaunchError(f"Comprehensive source missing required identifier columns: {', '.join(missing)}")
    if predictor_columns is not None:
        missing_predictors = [c for c in predictor_columns if c not in df.columns]
        if missing_predictors:
            raise LaunchError(f"Comprehensive source missing required predictor columns: {', '.join(missing_predictors)}")


def validate_source(df: pd.DataFrame, config: LaunchConfig) -> dict:
    """Validate the comprehensive source; raise actionable LaunchError on failure.

    Returns an input-validation summary dict (FR-006).
    """
    summary: dict = {"comprehensive_source": str(config.comprehensive_source), "checks": {}}
    required_ids = ["area_id", "year", "month"]
    missing = [c for c in required_ids if c not in df.columns]
    summary["checks"]["required_identifier_columns_present"] = not missing
    validate_required_source_columns(df)

    prepared = prepare_source(df)
    cutoff = pd.Timestamp(config.training_cutoff)
    ly, lm = _parse_month(config.launch_month)

    train_candidates = _training_mask(prepared, cutoff)
    april_mask = (prepared["year"].astype(int) == ly) & (prepared["month"].astype(int) == lm)
    n_train = int(train_candidates.sum())
    n_april = int(april_mask.sum())

    summary["checks"]["date_constructable"] = True  # prepare_source would have raised otherwise
    summary["checks"]["valid_training_rows_before_cutoff"] = n_train > 0
    summary["checks"]["april_xtest_rows_exist"] = n_april > 0
    summary["checks"]["cumulative_targets_derivable"] = all(t in prepared.columns for t in TARGET_COLUMNS)
    summary["training_rows_before_cutoff"] = n_train
    summary["launch_month_rows"] = n_april
    summary["launch_month"] = config.launch_month
    summary["training_cutoff"] = config.training_cutoff

    if n_april == 0:
        raise LaunchError(
            f"No launch-month rows (year={ly}, month={lm}) found in the comprehensive source. "
            "A valid comprehensive source with April 2026 rows is required."
        )
    if n_train == 0:
        raise LaunchError(
            f"No valid-target training rows strictly before {config.training_cutoff} found in the comprehensive source."
        )
    # Duplicate launch-month area_id detection (report; hard-stop handled in build_xtest_april)
    april_ids = prepared.loc[april_mask, "area_id"].astype(str)
    dup_ids = sorted(april_ids[april_ids.duplicated()].unique().tolist())
    summary["launch_month_duplicate_area_ids"] = dup_ids
    summary["launch_month_unique_area_ids"] = int(april_ids.nunique())
    return summary


def prepare_source(df: pd.DataFrame) -> pd.DataFrame:
    """Construct date + cumulative targets without requiring labels on every row.

    Unlike ``fwd.prepare_forecasting_dataset`` (which requires all percent targets),
    the launch tolerates missing targets on launch-month rows. Date construction and
    target derivation are applied where columns exist.
    """
    fwd.validate_required_columns(df, ["area_id", "year", "month"])
    result = df.replace([np.inf, -np.inf], np.nan).copy()
    result = fwd.add_monthly_date(result)
    if all(c in result.columns for c in fwd.PERCENT_TARGET_COLUMNS):
        result = fwd.derive_cumulative_targets(result)
    if "overall_phase" in result.columns:
        result["overall_phase"] = pd.to_numeric(result["overall_phase"], errors="coerce")
    return result.sort_values(["area_id", "date"]).reset_index(drop=True)


# --- Forecasted weather feature handling -------------------------------------


def _forecasted_weather_primary_target_minus(scope_months: int) -> int:
    return 6 if scope_months == 12 else 0


def _forecasted_weather_month_specs(scope_months: int) -> List[ForecastedWeatherMonthSpec]:
    if scope_months == 0:
        return []
    if scope_months in (3, 6):
        primary_target_minus = _forecasted_weather_primary_target_minus(scope_months)
        return [
            ForecastedWeatherMonthSpec(
                offset_from_feature_months=scope_months - target_minus,
                target_minus_months=target_minus,
                period_column=_forecasted_weather_period_column(target_minus, primary_target_minus),
            )
            for target_minus in range(0, scope_months + 1)
        ]
    if scope_months == 12:
        primary_target_minus = _forecasted_weather_primary_target_minus(scope_months)
        return [
            ForecastedWeatherMonthSpec(
                offset_from_feature_months=12 - target_minus,
                target_minus_months=target_minus,
                period_column=_forecasted_weather_period_column(target_minus, primary_target_minus),
            )
            for target_minus in range(6, 13)
        ]
    raise LaunchError(f"Forecasted weather is only supported for scope 0, 3, 6, or 12; received {scope_months}.")


def _forecasted_weather_proxy_column(base_column: str, target_minus_months: int, primary_target_minus: int) -> str:
    if target_minus_months == primary_target_minus:
        return f"{base_column}{FORECASTED_WEATHER_PROXY_SUFFIX}"
    return f"{base_column}_minus_{target_minus_months}{FORECASTED_WEATHER_PROXY_SUFFIX}"


def _forecasted_weather_period_column(target_minus_months: int, primary_target_minus: int) -> str:
    if target_minus_months == primary_target_minus:
        return "weather_proxy_period"
    return f"weather_proxy_period_target_minus_{target_minus_months}"


def forecasted_weather_proxy_columns(scope_months: Optional[int] = None) -> List[str]:
    if scope_months is None:
        return [f"{c}{FORECASTED_WEATHER_PROXY_SUFFIX}" for c in FORECASTED_WEATHER_COLUMNS]
    primary_target_minus = _forecasted_weather_primary_target_minus(scope_months)
    return [
        _forecasted_weather_proxy_column(c, spec.target_minus_months, primary_target_minus)
        for spec in _forecasted_weather_month_specs(scope_months)
        for c in FORECASTED_WEATHER_COLUMNS
    ]


def grouped_shap_weather_forecast_features(config: LaunchConfig) -> List[str]:
    if forecasted_weather_is_active(config):
        return forecasted_weather_proxy_columns(config.scope_months)
    return forecasted_weather_proxy_columns()


def forecasted_weather_is_active(config: LaunchConfig) -> bool:
    return bool(config.using_forecasted_weather and config.scope_months in (3, 6, 12))


def resolve_forecasted_weather_source(explicit_path: Optional[Path] = None) -> Path:
    if explicit_path is not None:
        resolved = Path(explicit_path).expanduser()
    else:
        try:
            resolved = paths.external_path(FORECASTED_WEATHER_SOURCE_KEY)
        except KeyError:
            resolved = paths.SOURCE_DATA_DIR / FORECASTED_WEATHER_DEFAULT_RELATIVE_PATH
    if not resolved.exists():
        raise LaunchError(f"Forecasted weather source file does not exist: {resolved}")
    return resolved


def _forecast_period_from_time(time: pd.Series) -> pd.Series:
    text = time.astype(str).str.strip()
    parsed = pd.to_datetime(text, format="%b%Y", errors="coerce")
    missing = parsed.isna()
    if missing.any():
        parsed_fallback = pd.to_datetime(text.loc[missing], errors="coerce")
        parsed.loc[missing] = parsed_fallback
    if parsed.isna().any():
        examples = time.loc[parsed.isna()].astype(str).head(5).tolist()
        raise LaunchError(f"Forecasted weather time values cannot be parsed as months, e.g. {examples}.")
    return pd.Series(pd.PeriodIndex(parsed.dt.strftime("%Y-%m"), freq="M"), index=time.index).astype(str)


def load_forecasted_weather(path: Path) -> pd.DataFrame:
    required = ["area_id", "time", *FORECASTED_WEATHER_COLUMNS]
    forecast = pd.read_csv(path, usecols=required)
    missing = [c for c in required if c not in forecast.columns]
    if missing:
        raise LaunchError("Forecasted weather source missing required columns: " + ", ".join(missing))
    forecast = forecast.replace([np.inf, -np.inf], np.nan).copy()
    forecast["area_id"] = forecast["area_id"].astype(str)
    forecast["forecast_period"] = _forecast_period_from_time(forecast["time"])
    dup = forecast.duplicated(["area_id", "forecast_period"], keep=False)
    if dup.any():
        examples = forecast.loc[dup, ["area_id", "forecast_period"]].drop_duplicates().head(10).to_dict("records")
        raise LaunchError(f"Forecasted weather has duplicate area_id/forecast_period keys, e.g. {examples}.")
    weather_na = forecast.loc[:, list(FORECASTED_WEATHER_COLUMNS)].isna().sum().to_dict()
    if any(v for v in weather_na.values()):
        raise LaunchError(f"Forecasted weather contains missing values in required weather columns: {weather_na}")
    return forecast.loc[:, ["area_id", "forecast_period", *FORECASTED_WEATHER_COLUMNS]]


def load_historical_weather_source(path: Optional[Path] = None) -> pd.DataFrame:
    resolved = Path(path).expanduser() if path is not None else paths.external_path(HISTORICAL_WEATHER_SOURCE_KEY)
    required = ["admin_code", "year", "month", *FORECASTED_WEATHER_COLUMNS]
    weather = pd.read_csv(resolved, usecols=required)
    missing = [c for c in required if c not in weather.columns]
    if missing:
        raise LaunchError("Historical weather source missing required columns: " + ", ".join(missing))
    weather = weather.replace([np.inf, -np.inf], np.nan).copy()
    weather = weather.rename(columns={"admin_code": "area_id"})
    weather["area_id"] = weather["area_id"].astype(str)
    weather["forecast_period"] = monthly_period_from_year_month(weather["year"], weather["month"]).astype(str)
    dup = weather.duplicated(["area_id", "forecast_period"], keep=False)
    if dup.any():
        examples = weather.loc[dup, ["area_id", "forecast_period"]].drop_duplicates().head(10).to_dict("records")
        raise LaunchError(f"Historical weather source has duplicate area_id/period keys, e.g. {examples}.")
    weather_na = weather.loc[:, list(FORECASTED_WEATHER_COLUMNS)].isna().sum().to_dict()
    if any(v for v in weather_na.values()):
        raise LaunchError(f"Historical weather source contains missing values in required weather columns: {weather_na}")
    return weather.loc[:, ["area_id", "forecast_period", *FORECASTED_WEATHER_COLUMNS]]


def _training_weather_source(source_featured: pd.DataFrame) -> Tuple[pd.DataFrame, str]:
    if all(c in source_featured.columns for c in FORECASTED_WEATHER_COLUMNS):
        train_weather = source_featured.loc[:, ["area_id", "year", "month", *FORECASTED_WEATHER_COLUMNS]].copy()
        train_weather["area_id"] = train_weather["area_id"].astype(str)
        train_weather["forecast_period"] = monthly_period_from_year_month(train_weather["year"], train_weather["month"]).astype(str)
        return train_weather.loc[:, ["area_id", "forecast_period", *FORECASTED_WEATHER_COLUMNS]], "comprehensive_source_current_period_weather"
    return load_historical_weather_source(), str(paths.external_path(HISTORICAL_WEATHER_SOURCE_KEY))


def _combine_inference_weather_sources(forecast: pd.DataFrame, visible_weather: pd.DataFrame) -> pd.DataFrame:
    combined = pd.concat([forecast, visible_weather], ignore_index=True)
    combined = combined.drop_duplicates(["area_id", "forecast_period"], keep="first")
    return combined.loc[:, ["area_id", "forecast_period", *FORECASTED_WEATHER_COLUMNS]]


def _add_forecasted_weather_period_columns(frame: pd.DataFrame, config: LaunchConfig) -> Tuple[pd.DataFrame, List[str]]:
    out = frame.copy()
    feature_period = pd.PeriodIndex(out["feature_period"].astype(str), freq="M")
    period_columns = []
    for spec in _forecasted_weather_month_specs(config.scope_months):
        out[spec.period_column] = (feature_period + spec.offset_from_feature_months).astype(str)
        period_columns.append(spec.period_column)
    return out, period_columns


def _weather_window_periods(config: LaunchConfig) -> List[str]:
    feature_period = launch_feature_period(config)
    return [str(add_months(feature_period, spec.offset_from_feature_months)) for spec in _forecasted_weather_month_specs(config.scope_months)]


def _weather_window_target_minus_months(config: LaunchConfig) -> List[int]:
    return [spec.target_minus_months for spec in _forecasted_weather_month_specs(config.scope_months)]


def forecasted_weather_scope_note(config: LaunchConfig) -> str:
    if config.scope_months in (3, 6):
        return (
            f"scope {config.scope_months}: training aligns labels to feature_month=target_month-{config.scope_months} "
            f"and adds visible forecast weather from target_month back through feature_month; inference uses April 2026 base features "
            f"plus forecast weather for {', '.join(_weather_window_periods(config))}"
        )
    if config.scope_months == 12:
        intermediate = add_months(launch_feature_period(config), 6)
        return (
            f"scope 12: April 2026 prediction rows use forecast weather from six-month intermediate {intermediate} "
            f"back through feature month {launch_feature_period(config)}, not the 12-month target horizon {launch_target_period(config)}"
        )
    return "scope 0: forecasted weather disabled/no-op"


def forecasted_weather_scope_mapping(config: LaunchConfig) -> dict:
    forecast_run_period = str(launch_feature_period(config))
    if config.scope_months == 0:
        return {
            "mode": "noop",
            "forecast_value_source": "none",
            "feature_period": forecast_run_period,
            "target_period": forecast_run_period,
            "forecast_weather_period": None,
            "forecast_run_period": forecast_run_period,
            "april_forecast_valid_period": None,
            "inference_forecast_period": None,
        }
    if config.scope_months in (3, 6):
        valid_period = str(launch_target_period(config))
        periods = _weather_window_periods(config)
        target_minus_months = _weather_window_target_minus_months(config)
        return {
            "mode": "target_month_weather_forecast_proxy",
            "forecast_value_source": "scope_specific_forecast_weather_values",
            "feature_period": forecast_run_period,
            "target_period": valid_period,
            "forecast_weather_period": valid_period,
            "primary_forecast_weather_period": valid_period,
            "forecast_weather_periods": periods,
            "forecast_run_period": forecast_run_period,
            "launch_feature_period": forecast_run_period,
            "april_forecast_valid_period": valid_period,
            "inference_forecast_period": valid_period,
            "weather_window_target_minus_months": target_minus_months,
            "weather_window_feature_offsets": [s.offset_from_feature_months for s in _forecasted_weather_month_specs(config.scope_months)],
            "weather_window_month_count": len(periods),
            "lead_months": config.scope_months,
            "requirement_interpretation": "For scope 3/6, April 2026 base features are target_month-scope lagged features; weather forecast proxy columns use visible months from target_month back through feature_month.",
        }
    if config.scope_months == 12:
        intermediate = add_months(launch_feature_period(config), 6)
        periods = _weather_window_periods(config)
        target_minus_months = _weather_window_target_minus_months(config)
        return {
            "mode": "six_month_intermediate_weather_forecast_proxy",
            "forecast_value_source": "six_month_intermediate_forecast_weather_values",
            "feature_period": forecast_run_period,
            "target_period": str(launch_target_period(config)),
            "forecast_weather_period": str(intermediate),
            "primary_forecast_weather_period": str(intermediate),
            "forecast_weather_periods": periods,
            "forecast_run_period": forecast_run_period,
            "launch_feature_period": forecast_run_period,
            "april_forecast_valid_period": str(intermediate),
            "inference_forecast_period": str(intermediate),
            "weather_window_target_minus_months": target_minus_months,
            "weather_window_feature_offsets": [s.offset_from_feature_months for s in _forecasted_weather_month_specs(config.scope_months)],
            "weather_window_month_count": len(periods),
            "lead_months": 6,
            "requirement_interpretation": "For scope 12, April 2026 base features are target_month-12 lagged features; weather forecast proxy columns use visible months from target_month-6 back through feature_month.",
        }
    return {
        "mode": "unsupported",
        "forecast_value_source": "none",
        "feature_period": forecast_run_period,
        "target_period": str(launch_target_period(config)),
        "forecast_weather_period": None,
        "forecast_run_period": forecast_run_period,
        "april_forecast_valid_period": None,
        "inference_forecast_period": None,
    }


def _merge_weather_proxy(
    frame: pd.DataFrame,
    weather_source: pd.DataFrame,
    config: LaunchConfig,
    *,
    source_label: str,
) -> Tuple[pd.DataFrame, dict]:
    before = len(frame)
    out = frame.copy()
    out["area_id"] = out["area_id"].astype(str)
    out, period_cols = _add_forecasted_weather_period_columns(out, config)
    specs = _forecasted_weather_month_specs(config.scope_months)
    primary_target_minus = _forecasted_weather_primary_target_minus(config.scope_months)
    proxy_cols = forecasted_weather_proxy_columns(config.scope_months)
    generated_cols = set(period_cols) | set(proxy_cols)
    preexisting_generated = sorted(c for c in generated_cols if c in frame.columns)
    if preexisting_generated:
        raise LaunchError(f"Forecasted weather generated columns already exist in {source_label} frame: {preexisting_generated}")
    merged = out
    for spec in specs:
        renamed_weather = {
            c: _forecasted_weather_proxy_column(c, spec.target_minus_months, primary_target_minus)
            for c in FORECASTED_WEATHER_COLUMNS
        }
        lookup = weather_source.rename(columns=renamed_weather)
        lookup_cols = ["area_id", "forecast_period", *renamed_weather.values()]
        merged = merged.merge(
            lookup.loc[:, lookup_cols],
            left_on=["area_id", spec.period_column],
            right_on=["area_id", "forecast_period"],
            how="left",
            validate="many_to_one",
        ).drop(columns=["forecast_period"])
        after_merge = len(merged)
        if after_merge != before:
            raise LaunchError(f"Forecasted weather merge changed {source_label} row count from {before} to {after_merge}.")
    after = len(merged)
    missing_counts = merged.loc[:, proxy_cols].isna().sum().to_dict()
    if any(v for v in missing_counts.values()):
        missing_mask = merged.loc[:, proxy_cols].isna().any(axis=1)
        missing_period_values = pd.unique(merged.loc[missing_mask, period_cols].astype(str).values.ravel()).tolist()[:10]
        raise LaunchError(
            f"Forecasted weather merge left missing {source_label} proxy values: {missing_counts}; "
            f"example periods={missing_period_values}."
        )
    return merged, {
        "source": source_label,
        "rows_before": int(before),
        "rows_after": int(after),
        "proxy_periods": sorted(merged["weather_proxy_period"].astype(str).unique().tolist()),
        "all_proxy_periods": sorted(pd.unique(merged.loc[:, period_cols].astype(str).values.ravel()).tolist()),
        "proxy_periods_by_column": {c: sorted(merged[c].astype(str).unique().tolist()) for c in period_cols},
        "period_columns": period_cols,
        "weather_window_target_minus_months": [s.target_minus_months for s in specs],
        "weather_window_feature_offsets": [s.offset_from_feature_months for s in specs],
        "proxy_columns": proxy_cols,
        "missing_proxy_values": {k: int(v) for k, v in missing_counts.items()},
    }


def apply_forecasted_weather_features(
    train_featured: pd.DataFrame,
    xtest_featured: pd.DataFrame,
    source_featured: pd.DataFrame,
    config: LaunchConfig,
) -> Tuple[pd.DataFrame, pd.DataFrame, dict]:
    report: dict = {
        "enabled": bool(config.using_forecasted_weather),
        "active": forecasted_weather_is_active(config),
        "scope_months": config.scope_months,
        "weather_columns": list(FORECASTED_WEATHER_COLUMNS),
        "proxy_columns": forecasted_weather_proxy_columns(config.scope_months) if forecasted_weather_is_active(config) else forecasted_weather_proxy_columns(),
        "scope_note": forecasted_weather_scope_note(config),
        "scope_mapping": forecasted_weather_scope_mapping(config),
    }
    if not config.using_forecasted_weather:
        report["action"] = "disabled; existing weather feature behavior unchanged"
        return train_featured, xtest_featured, report
    if config.scope_months == 0:
        report["action"] = "scope_0_noop; existing weather feature behavior unchanged"
        return train_featured, xtest_featured, report
    if config.scope_months not in (3, 6, 12):
        raise LaunchError(f"Forecasted weather is only supported for scope 0, 3, 6, or 12; received {config.scope_months}.")
    train_weather, training_proxy_source = _training_weather_source(source_featured)
    dup = train_weather.duplicated(["area_id", "forecast_period"], keep=False)
    if dup.any():
        examples = train_weather.loc[dup, ["area_id", "forecast_period"]].drop_duplicates().head(10).to_dict("records")
        raise LaunchError(f"Training weather proxy source has duplicate area_id/period keys, e.g. {examples}.")
    train_featured, train_report = _merge_weather_proxy(train_featured, train_weather, config, source_label="training")

    forecast_path = resolve_forecasted_weather_source(config.forecasted_weather_source)
    forecast = load_forecasted_weather(forecast_path)
    inference_weather = _combine_inference_weather_sources(forecast, train_weather)
    xtest_featured, xtest_report = _merge_weather_proxy(xtest_featured, inference_weather, config, source_label="inference")
    report.update({
        "action": "added forecast proxy weather features",
        "forecasted_weather_source": str(forecast_path),
        "inference_weather_fallback_source": training_proxy_source,
        "training_proxy_source": training_proxy_source,
        "training": train_report,
        "inference": xtest_report,
    })
    return train_featured, xtest_featured, report


# --- Training / X_test frames (T006, T007; FR-007/008/009) ------------------

def _training_mask(prepared: pd.DataFrame, cutoff: pd.Timestamp) -> pd.Series:
    has_targets = pd.Series(True, index=prepared.index)
    for t in TARGET_COLUMNS:
        has_targets &= prepared[t].notna() if t in prepared.columns else False
    overall = prepared.get("overall_phase")
    valid_label = overall.notna() & (overall != 0) if overall is not None else pd.Series(False, index=prepared.index)
    return (prepared["date"] < cutoff) & valid_label & has_targets


def build_training_frame(
    prepared: pd.DataFrame,
    config: LaunchConfig,
    static_features: Optional[Sequence[str]] = None,
) -> Tuple[pd.DataFrame, dict]:
    cutoff = pd.Timestamp(config.training_cutoff)
    mask = _training_mask(prepared, cutoff)
    train = prepared.loc[mask].copy()
    if train.empty:
        raise LaunchError(f"No eligible training rows strictly before {config.training_cutoff}.")
    if config.scope_months:
        train = align_scoped_training_frame(prepared, train, config, static_features)
    else:
        train["feature_period"] = monthly_period_from_year_month(train["year"], train["month"]).astype(str)
        train["target_period"] = train["feature_period"]
        train["scope_months"] = 0
    per_month = (
        train.assign(ym=train["date"].dt.strftime("%Y-%m"))
        .groupby("ym").size().sort_index().to_dict()
    )
    summary = {
        "training_rows": int(len(train)),
        "train_min_date": fwd._format_date(train["date"].min()),
        "train_max_date": fwd._format_date(train["date"].max()),
        "rows_per_month": {k: int(v) for k, v in per_month.items()},
        "scope_months": config.scope_months,
    }
    return train, summary


def align_scoped_training_frame(
    prepared: pd.DataFrame,
    target_rows: pd.DataFrame,
    config: LaunchConfig,
    static_features: Optional[Sequence[str]],
) -> pd.DataFrame:
    target = target_rows.copy()
    target_period = monthly_period_from_year_month(target["year"], target["month"])
    feature_period = target_period.map(lambda p: subtract_months(p, config.scope_months))
    target["target_period"] = target_period.astype(str)
    target["feature_period"] = feature_period.astype(str)
    feature_source = prepared.copy()
    feature_source["feature_period"] = monthly_period_from_year_month(feature_source["year"], feature_source["month"]).astype(str)
    candidate_columns = [
        c for c in feature_source.columns
        if c not in set(TARGET_COLUMNS) | set(fwd.PERCENT_TARGET_COLUMNS) | {"overall_phase", "date", "year", "month", "area_id", "feature_period"}
    ]
    resolved_static = static_features
    if resolved_static is None:
        resolved_static = resolve_static_feature_classification(feature_source, candidate_columns).static_features
    static_set = set(resolved_static)
    passthrough = set(TARGET_COLUMNS) | set(fwd.PERCENT_TARGET_COLUMNS) | {"area_id", "overall_phase", "date", "year", "month"}
    dynamic_columns = [
        c for c in feature_source.columns
        if c not in passthrough and c not in static_set and c not in {"feature_period"}
    ]
    feature_cols = ["area_id", "feature_period", *dynamic_columns]
    feature_values = feature_source.loc[:, feature_cols].copy()
    aligned = target.drop(columns=[c for c in dynamic_columns if c in target.columns], errors="ignore").merge(
        feature_values,
        on=["area_id", "feature_period"],
        how="inner",
        validate="many_to_one",
    )
    if aligned.empty:
        raise LaunchError(
            f"No usable scoped training/evaluation records after aligning target rows to {config.scope_months}-month-prior features."
        )
    aligned["scope_months"] = config.scope_months
    return aligned


def build_launch_prediction_frame(prepared: pd.DataFrame, config: LaunchConfig) -> Tuple[pd.DataFrame, dict]:
    ly, lm = _parse_month(config.launch_month)
    mask = (prepared["year"].astype(int) == ly) & (prepared["month"].astype(int) == lm)
    launch = prepared.loc[mask].copy()
    if launch.empty:
        raise LaunchError(
            f"No usable launch feature-period prediction records (year={ly}, month={lm}). "
            "A valid comprehensive source with launch feature-period rows is required."
        )
    launch["area_id"] = launch["area_id"].astype(str)
    dup_ids = sorted(launch.loc[launch["area_id"].duplicated(keep=False), "area_id"].unique().tolist())
    dedup_report: dict = {"duplicate_area_ids": dup_ids, "dedup_rule": config.dedup_rule}
    if dup_ids:
        if config.dedup_rule != "latest-date":
            raise LaunchError(
                f"Duplicate launch-month area_id rows found ({len(dup_ids)} ids). "
                "Default is hard-stop. Re-run with --dedup-rule latest-date (requires a date column) "
                "to resolve deterministically, or de-duplicate the source."
            )
        candidate_counts = launch.groupby("area_id").size().to_dict()
        before = len(launch)
        launch = launch.sort_values(["area_id", "date"]).drop_duplicates("area_id", keep="last")
        dedup_report["candidate_counts"] = {k: int(candidate_counts[k]) for k in dup_ids}
        dedup_report["rows_dropped"] = int(before - len(launch))
        dedup_report["selected_date"] = config.launch_month
    feature_period = str(launch_feature_period(config))
    target_period = str(launch_target_period(config))
    launch["feature_period"] = feature_period
    launch["target_period"] = target_period
    launch["scope_months"] = config.scope_months
    coverage = {
        "launch_month_area_count": int(launch["area_id"].nunique()),
        "launch_month_rows": int(len(launch)),
        "feature_period": feature_period,
        "target_period": target_period,
        "scope_months": config.scope_months,
        "dedup": dedup_report,
    }
    return launch.reset_index(drop=True), coverage


def build_xtest_april(prepared: pd.DataFrame, config: LaunchConfig) -> Tuple[pd.DataFrame, dict]:
    return build_launch_prediction_frame(prepared, config)


# --- Feature pipeline (T008, T009; FR-011/011a/011b/012/013) ----------------

def _add_month_year_dummies(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    month = pd.to_numeric(result["month"], errors="raise").astype(int)
    year = pd.to_numeric(result["year"], errors="raise").astype(int)
    month_dummies = pd.get_dummies(month, prefix="month", dtype=bool)
    year_dummies = pd.get_dummies(year, prefix="year", dtype=bool)
    return pd.concat([result, month_dummies, year_dummies], axis=1)


def apply_identifier_features(
    prepared: pd.DataFrame, config: LaunchConfig
) -> Tuple[pd.DataFrame, dict]:
    """Apply the canonical identifier-feature setting (FR-011a).

    Detect identifier-derived columns when present; otherwise construct them via the
    canonical ``forecasting_weight_decay.add_identifier_features`` lookup helper.
    Records, per identifier-derived feature, whether it was detected or constructed.
    """
    transform: dict = {"enabled": config.add_identifier_features, "lat_lon": "absent", "month_year_dummies": "none"}
    if not config.add_identifier_features:
        transform["note"] = "identifier-feature setting disabled by flag"
        return prepared.copy(), transform

    have_latlon = all(c in prepared.columns and prepared[c].notna().any() for c in IDENTIFIER_DERIVED_BASE)
    if have_latlon:
        result = _add_month_year_dummies(prepared)
        transform["lat_lon"] = "detected"
        transform["month_year_dummies"] = "constructed"
        return result, transform

    # Need to construct lat/lon via lookup
    lookup_path = config.identifier_source
    if lookup_path is None:
        try:
            lookup_path = paths.external_path(fwd.DEFAULT_SOMALIA_LOOKUP_KEY)
        except KeyError:
            lookup_path = None
    if lookup_path is None or not Path(lookup_path).exists():
        if config.allow_missing_identifier_features:
            transform["note"] = "identifier-derived features missing; proceeding under --allow-missing-identifier-features"
            return _add_month_year_dummies(prepared), transform
        raise LaunchError(
            "Required identifier-derived features (lat/lon) are absent from the comprehensive source and no "
            "identifier lookup is configured. Provide --identifier-source <csv> (admin_code/year/month/lat/lon) "
            f"or set the '{fwd.DEFAULT_SOMALIA_LOOKUP_KEY}' key, or pass --allow-missing-identifier-features to override."
        )
    lookup_df = pd.read_csv(lookup_path)
    result = fwd.add_identifier_features(prepared, lookup_df)
    transform["lat_lon"] = "constructed"
    transform["month_year_dummies"] = "constructed"
    transform["identifier_source"] = str(lookup_path)
    return result, transform


def _exclusion_family(column: str) -> Optional[Tuple[str, str]]:
    """Return (family, matched_pattern) if the column should be excluded, else None."""
    lower = column.lower()
    if lower in {c.lower() for c in TARGET_LABEL_COLUMNS}:
        return ("target_label", lower)
    for pat in TARGET_DERIVED_PATTERNS:
        if pat in lower:
            return ("target_derived", pat)
    if lower in {c.lower() for c in REPORTING_ID_COLUMNS} or lower in {"year", "month", "date"}:
        return ("identifier_reporting", lower)
    if lower in {c.lower() for c in MODEL_METADATA_COLUMNS}:
        return ("model_metadata", lower)
    return None


@dataclass(frozen=True)
class StaticFeatureClassification:
    static_features: List[str]
    time_varying_features: List[str]
    inconsistent_static_features: List[str]


def _is_area_level_invariant(df: pd.DataFrame, column: str) -> bool:
    observed = df[["area_id", column]].dropna(subset=[column])
    if observed.empty:
        return True
    return bool(observed.groupby("area_id")[column].nunique(dropna=True).le(1).all())


def classify_static_time_varying_features(
    df: pd.DataFrame,
    predictor_columns: Sequence[str],
    config_static_features: Optional[Sequence[str]] = None,
) -> StaticFeatureClassification:
    validate_required_source_columns(df, predictor_columns)
    infer_static = config_static_features is None
    config_static = set(config_static_features or [])
    static_features: List[str] = []
    time_varying_features: List[str] = []
    inconsistent: List[str] = []
    for column in predictor_columns:
        invariant = _is_area_level_invariant(df, column)
        if infer_static and invariant:
            static_features.append(column)
        elif column in config_static and invariant:
            static_features.append(column)
        else:
            time_varying_features.append(column)
            if column in config_static:
                inconsistent.append(column)
    return StaticFeatureClassification(static_features, time_varying_features, inconsistent)


def resolve_static_feature_classification(
    df: pd.DataFrame,
    predictor_columns: Sequence[str],
    config_static_features: Optional[Sequence[str]] = None,
    *,
    fail_on_inconsistency: bool = True,
) -> StaticFeatureClassification:
    classification = classify_static_time_varying_features(df, predictor_columns, config_static_features)
    if fail_on_inconsistency and classification.inconsistent_static_features:
        raise LaunchError(
            "Unresolved static classification inconsistency for config static feature(s): "
            + ", ".join(classification.inconsistent_static_features)
        )
    return classification


def build_feature_schema_report(
    featured: pd.DataFrame, feature_columns: Sequence[str], train_cols: Sequence[str], xtest_cols: Sequence[str], transform: dict
) -> Tuple[pd.DataFrame, List[str]]:
    feature_set = set(feature_columns)
    train_set, xtest_set = set(train_cols), set(xtest_cols)
    rows = []
    warnings: List[str] = []
    identifier_derived = {c for c in featured.columns if c in IDENTIFIER_DERIVED_BASE or c.startswith("month_") or c.startswith("year_")}
    numeric_cols = set(featured.select_dtypes(include=[np.number, "bool"]).columns)
    out_of_family_excluded = []
    for col in featured.columns:
        included = col in feature_set
        fam = _exclusion_family(col)
        role = "model_feature" if included else "other_excluded"
        matched, exclusion_family, reason = "", "", ""
        if included and col in identifier_derived:
            role = "identifier_derived_feature"
        if not included:
            if fam is not None:
                exclusion_family, matched = fam[0], fam[1]
                role = {"target_label": "target", "target_derived": "target_derived_excluded",
                        "identifier_reporting": "raw_identifier_reporting",
                        "model_metadata": "model_metadata_excluded"}[fam[0]]
                reason = f"matched {fam[0]} ({fam[1]})"
            elif col not in numeric_cols:
                exclusion_family, role, reason = "non_numeric", "non_numeric_excluded", "non-numeric column"
            else:
                exclusion_family, reason = "unused_extra", "not selected as a model feature"
                out_of_family_excluded.append(col)
        rows.append({
            "column": col,
            "included_in_model": included,
            "role": role,
            "scope_role": "time_varying_predictor" if included else "not_scope_aligned",
            "matched_pattern": matched,
            "exclusion_family": exclusion_family,
            "exclusion_reason": reason,
            "identifier_derived": col in identifier_derived,
            "identifier_lat_lon_origin": transform.get("lat_lon", "") if col in IDENTIFIER_DERIVED_BASE else "",
            "present_in_training": col in train_set,
            "present_in_xtest": col in xtest_set,
            "expected_identifier_feature_missing": (col in IDENTIFIER_DERIVED_BASE and col not in featured.columns),
        })
    # Over-exclusion / out-of-family warning (FR-009/audit, analysis fix #3)
    total = len(featured.columns)
    excluded = total - len(feature_set)
    if total and excluded / total > 0.9:
        warnings.append(f"Over-exclusion warning: {excluded}/{total} columns excluded from features (>90%).")
    if out_of_family_excluded:
        warnings.append(
            "Out-of-family exclusions (numeric columns dropped without a known target/identifier reason): "
            + ", ".join(out_of_family_excluded[:20]) + (" ..." if len(out_of_family_excluded) > 20 else "")
        )
    if train_set != xtest_set:
        only_train = sorted(train_set - xtest_set)[:20]
        only_xtest = sorted(xtest_set - train_set)[:20]
        warnings.append(f"Train/X_test feature schema differ. only_train={only_train} only_xtest={only_xtest}")
    return pd.DataFrame(rows), warnings


def select_model_features(featured_train: pd.DataFrame) -> List[str]:
    """Canonical numeric feature selection, then enforce the FR-011b exclusion families.

    ``select_numeric_feature_columns`` covers identifiers/dates/percent/worse targets and
    ``*_pred``/``*_target``/``*_label`` patterns, but does NOT catch target-derived
    diagnostics like ``overall_phase_lag1``. We additionally drop any column whose name
    matches a documented target-label / target-derived family (FR-011b).
    """
    base = fwd.select_numeric_feature_columns(featured_train)
    selected = [c for c in base if _target_or_derived_exclusion(c) is None and c not in MODEL_METADATA_COLUMNS]
    if not selected:
        raise LaunchError("No eligible model feature columns remain after target-derived exclusion.")
    return selected


def _target_or_derived_exclusion(column: str) -> Optional[Tuple[str, str]]:
    """Return (family, matched) only for target/target-derived families (not identifiers)."""
    fam = _exclusion_family(column)
    if fam is not None and fam[0] in ("target_label", "target_derived"):
        return fam
    return None


# --- Sample weighting anchored at launch month (R5) -------------------------

def launch_time_decay_weights(dates: pd.Series, launch_month: str, half_life_months: float) -> pd.Series:
    """Time-decay weights anchored at the launch month (mirrors fwd.DECAY_FORMULATION).

    distance = months before the launch month; weight = 0.5 ** (distance / half_life).
    Uses only training-row dates (no future information).
    """
    fwd.validate_half_life(half_life_months)
    ly, lm = _parse_month(launch_month)
    normalized = pd.to_datetime(dates).dt.to_period("M").dt.to_timestamp()
    distances = (ly - normalized.dt.year) * 12 + (lm - normalized.dt.month)
    if (distances <= 0).any():
        raise LaunchError("All training rows must precede the launch month for time-decay weighting.")
    weights = pd.Series(np.power(0.5, distances.astype(float) / float(half_life_months)), index=dates.index, name="sample_weight")
    fwd.validate_weights(weights)
    return weights


# --- Prediction validation & phase derivation (T016/T017; FR-017a/018) ------

def validate_and_clip_predictions(pred_df: pd.DataFrame, config: LaunchConfig) -> Tuple[pd.DataFrame, dict]:
    """Clip cumulative predictions to [0,1] + round 2dp; surface non-finite (FR-017a)."""
    cols = [f"{t}_pred" for t in TARGET_COLUMNS]
    report: dict = {"clipped_low": {}, "clipped_high": {}, "nonfinite": {}, "rows_excluded": 0}
    out = pred_df.copy()
    nonfinite_mask = pd.Series(False, index=out.index)
    for c in cols:
        vals = pd.to_numeric(out[c], errors="coerce")
        nf = ~np.isfinite(vals.to_numpy(dtype=float))
        report["nonfinite"][c] = int(nf.sum())
        nonfinite_mask |= nf
        report["clipped_low"][c] = int((vals < 0).sum())
        report["clipped_high"][c] = int((vals > 1).sum())
        out[c] = vals.clip(0.0, 1.0).round(2)
    if nonfinite_mask.any():
        if not config.drop_nonfinite_predictions:
            bad = out.loc[nonfinite_mask, "area_id"].astype(str).tolist()[:20]
            raise LaunchError(
                f"Non-finite cumulative predictions for {int(nonfinite_mask.sum())} area_id(s) "
                f"(e.g. {bad}). Re-run with --drop-nonfinite-predictions to exclude+report them, "
                "or investigate the input features."
            )
        report["rows_excluded"] = int(nonfinite_mask.sum())
        report["excluded_area_ids"] = out.loc[nonfinite_mask, "area_id"].astype(str).tolist()
        out = out.loc[~nonfinite_mask].copy()
    return out, report


def derive_overall_phase(pred_df: pd.DataFrame, threshold: float = CANONICAL_THRESHOLD) -> pd.Series:
    resolved = {p: f"{t}_pred" for t, p in PHASE_FROM_TARGET.items()}
    return fdiag.reconstruct_phase_from_cumulative(pred_df, resolved, threshold)


# --- Output layout & run summary (T010; FR-029/031/034) ---------------------

@dataclass
class OutputLayout:
    out_root: Path
    report_root: Path
    predictions_csv: Path
    run_summary_json: Path
    config_json: Path
    input_validation_json: Path
    training_summary_csv: Path
    feature_schema_csv: Path
    xtest_coverage_csv: Path
    eligibility_csv: Path
    xtest_aligned_csv: Path
    prediction_distribution_csv: Path
    prediction_validation_json: Path
    predicted_phase_distribution_csv: Path
    model_artifacts_dir: Path
    grouped_shap_dir: Path
    grouped_shap_report_dir: Path
    grouped_shap_mapping_csv: Path
    grouped_shap_unmatched_csv: Path
    grouped_shap_feature_summary_csv: Path
    grouped_shap_long_csv: Path
    grouped_shap_matrix_csv: Path
    grouped_shap_metadata_json: Path
    grouped_shap_heatmap_png: Path
    comparison_dir: Path
    viz_results_dir: Path
    viz_report_dir: Path

    @property
    def validation_only_targets(self) -> List[Path]:
        return [self.input_validation_json, self.feature_schema_csv]


def resolve_output_layout(config: LaunchConfig) -> OutputLayout:
    out = config.out_root
    rep = config.report_root
    if config.scope_months != 0:
        out = out / f"scope_{config.scope_months}m"
        rep = rep / f"scope_{config.scope_months}m"
    fdiag_paths = paths  # noqa: F841 (paths used below)
    # Output-path safety: results under RESULTS_DIR, reports under REPORTS_DIR.
    from ipcch.alert_risk_maps import ensure_under  # reuse guardrail
    ensure_under(out, paths.RESULTS_DIR, "Launch results output")
    ensure_under(rep, paths.REPORTS_DIR, "Launch report output")
    return OutputLayout(
        out_root=out,
        report_root=rep,
        predictions_csv=out / "predictions_2026_04_all_area_id.csv",
        run_summary_json=out / "run_summary.json",
        config_json=out / "launch_config_resolved.json",
        input_validation_json=out / "input_validation_summary.json",
        training_summary_csv=out / "training_data_summary.csv",
        feature_schema_csv=out / "feature_schema_report.csv",
        xtest_coverage_csv=out / "x_test_area_coverage.csv",
        eligibility_csv=out / "april_2026_area_id_eligibility.csv",
        xtest_aligned_csv=out / "x_test_2026_04_all_area_id_model_aligned.csv",
        prediction_distribution_csv=out / "prediction_distribution_summary.csv",
        prediction_validation_json=out / "prediction_validation_summary.json",
        predicted_phase_distribution_csv=out / "predicted_phase_distribution.csv",
        model_artifacts_dir=out / "model_artifacts",
        grouped_shap_dir=out / "grouped_shap",
        grouped_shap_report_dir=rep / "grouped_shap",
        grouped_shap_mapping_csv=out / "grouped_shap" / "feature_to_group_mapping.csv",
        grouped_shap_unmatched_csv=out / "grouped_shap" / "unmatched_feature_diagnostics.csv",
        grouped_shap_feature_summary_csv=out / "grouped_shap" / "phase3_worse_feature_shap_summary.csv",
        grouped_shap_long_csv=out / "grouped_shap" / "phase3_worse_grouped_shap_long.csv",
        grouped_shap_matrix_csv=out / "grouped_shap" / "phase3_worse_grouped_shap_matrix.csv",
        grouped_shap_metadata_json=out / "grouped_shap" / "grouped_shap_metadata.json",
        grouped_shap_heatmap_png=rep / "grouped_shap" / "phase3_worse_grouped_shap_heatmap.png",
        comparison_dir=out / "actual_comparison",
        viz_results_dir=out / "visualizations",
        viz_report_dir=rep / "visualizations",
    )


def resolve_grouped_shap_crosswalk(config: LaunchConfig) -> Path:
    if config.grouped_shap_crosswalk_path:
        resolved = Path(config.grouped_shap_crosswalk_path).expanduser()
    else:
        try:
            resolved = paths.external_path(config.grouped_shap_crosswalk_key)
        except KeyError as exc:
            raise LaunchError(
                "Grouped SHAP crosswalk path is not configured. Pass --grouped-shap-crosswalk-path <path> "
                f"or configure external path key '{config.grouped_shap_crosswalk_key}' in configs/paths.local.json."
            ) from exc
    if not resolved.exists():
        raise LaunchError(f"Grouped SHAP crosswalk file does not exist: {resolved}")
    return resolved


def build_phase3_grouped_shap_training_matrix(train_featured: pd.DataFrame, feature_columns: Sequence[str]) -> pd.DataFrame:
    missing = [feature for feature in feature_columns if feature not in train_featured.columns]
    if missing:
        raise LaunchError("Grouped SHAP feature columns are missing from the phase3 training frame: " + ", ".join(missing))
    if fshap.NOWCASTING_GROUPED_SHAP_TARGET not in train_featured.columns:
        raise LaunchError(f"Grouped SHAP target column is missing: {fshap.NOWCASTING_GROUPED_SHAP_TARGET}")
    matrix = train_featured.dropna(subset=[fshap.NOWCASTING_GROUPED_SHAP_TARGET]).loc[:, list(feature_columns)]
    fshap.validate_feature_alignment(matrix, feature_columns)
    if matrix.empty:
        raise LaunchError("Grouped SHAP phase3 training matrix is empty after dropping missing phase3_worse rows.")
    return matrix


def _grouped_shap_reported_artifact_paths(layout: OutputLayout, include_unmatched_diagnostics: Optional[bool] = None) -> Dict[str, Path]:
    paths_by_name = grouped_shap_artifact_paths(layout)
    include_unmatched = bool(layout.grouped_shap_unmatched_csv.exists()) if include_unmatched_diagnostics is None else bool(include_unmatched_diagnostics)
    if not include_unmatched:
        paths_by_name.pop("unmatched_feature_diagnostics", None)
    return paths_by_name


def compute_nowcasting_grouped_shap(
    models: Mapping[str, object],
    train_featured: pd.DataFrame,
    feature_columns: Sequence[str],
    config: LaunchConfig,
    layout: OutputLayout,
    weather_forecast_features: Sequence[str],
) -> Dict[str, object]:
    if not config.compute_grouped_shap:
        return {}
    if fshap.NOWCASTING_GROUPED_SHAP_TARGET not in models:
        raise LaunchError("Grouped SHAP requires a fitted phase3_worse model.")
    crosswalk_path = resolve_grouped_shap_crosswalk(config)
    crosswalk, feature_col, category_col = fshap.load_crosswalk(
        crosswalk_path,
        config.grouped_shap_crosswalk_feature_column,
        config.grouped_shap_crosswalk_category_column,
    )
    shap_matrix = build_phase3_grouped_shap_training_matrix(train_featured, feature_columns)
    try:
        shap_values, engine_info = fshap.compute_phase3_shap_values(models[fshap.NOWCASTING_GROUPED_SHAP_TARGET], shap_matrix, feature_columns)
        mapping = fshap.map_features_to_groups(feature_columns, crosswalk, feature_col, category_col, weather_forecast_features=weather_forecast_features)
        mapped = mapping.loc[~mapping["is_unmatched"], ["feature_name", "assigned_group"]].rename(columns={"assigned_group": "feature_group"})
        summary = fshap.per_feature_shap_summary(shap_values, feature_columns, mapped, "nowcasting", f"{config.scope_months}m", 0, "train")
        group_labels = fshap.expected_nowcasting_feature_groups(crosswalk, category_col)
        long, diagnostics = fshap.aggregate_grouped_importance(summary, group_labels, "nowcasting", f"{config.scope_months}m", 0, "train")
        matrix = fshap.nowcasting_scope_group_matrix(long, group_labels)
        coverage = fshap.attribution_coverage_summary(shap_values, feature_columns, mapping.loc[~mapping["is_unmatched"], "feature_name"])
    except Exception as exc:
        raise LaunchError(f"Grouped SHAP computation failed: {exc}") from exc
    layout.grouped_shap_dir.mkdir(parents=True, exist_ok=True)
    layout.grouped_shap_report_dir.mkdir(parents=True, exist_ok=True)
    mapping.to_csv(layout.grouped_shap_mapping_csv, index=False)
    has_unmatched = bool(mapping["is_unmatched"].any())
    if has_unmatched:
        mapping.loc[mapping["is_unmatched"]].to_csv(layout.grouped_shap_unmatched_csv, index=False)
    summary.to_csv(layout.grouped_shap_feature_summary_csv, index=False)
    long.to_csv(layout.grouped_shap_long_csv, index=False)
    matrix.to_csv(layout.grouped_shap_matrix_csv, index=False)
    fshap.render_nowcasting_scope_heatmap(matrix, layout.grouped_shap_heatmap_png)
    reported_paths = _grouped_shap_reported_artifact_paths(layout, include_unmatched_diagnostics=has_unmatched)
    metadata = {
        "target": fshap.NOWCASTING_GROUPED_SHAP_TARGET,
        "sample_source": "train_featured.dropna(subset=['phase3_worse']).loc[:, feature_columns]",
        "feature_order_validated": True,
        "aggregation_metric": "absolute SHAP sum and relative importance",
        "scope_label": f"{config.scope_months}m",
        "expected_feature_groups": group_labels,
        "crosswalk_path": str(crosswalk_path),
        "crosswalk_feature_column": feature_col,
        "crosswalk_category_column": category_col,
        "engine": asdict(engine_info),
        "coverage": coverage,
        "diagnostic_count": len(diagnostics),
        "artifact_paths": {name: str(path) for name, path in reported_paths.items() if name == "metadata" or path.exists()},
    }
    write_json(layout.grouped_shap_metadata_json, metadata)
    return {
        "metadata_path": str(layout.grouped_shap_metadata_json),
        "coverage": coverage,
        "artifact_paths": metadata["artifact_paths"],
        "matched_feature_count": coverage["matched_feature_count"],
        "weather_forecast_feature_count": int(mapping["is_weather_forecast"].sum()),
        "unmatched_feature_count": coverage["unmatched_feature_count"],
    }


def grouped_shap_artifact_paths(layout: OutputLayout) -> Dict[str, Path]:
    return {
        "feature_to_group_mapping": layout.grouped_shap_mapping_csv,
        "unmatched_feature_diagnostics": layout.grouped_shap_unmatched_csv,
        "feature_summary": layout.grouped_shap_feature_summary_csv,
        "grouped_long": layout.grouped_shap_long_csv,
        "grouped_matrix": layout.grouped_shap_matrix_csv,
        "metadata": layout.grouped_shap_metadata_json,
        "heatmap": layout.grouped_shap_heatmap_png,
    }


def guard_output_conflicts(targets: Sequence[Path], overwrite: bool) -> List[str]:
    conflicts = [str(p) for p in targets if p.exists()]
    if conflicts and not overwrite:
        raise LaunchError("Existing output file conflict without --overwrite: " + ", ".join(conflicts))
    return conflicts


def write_json(path: Path, payload: Mapping) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=_json_default), encoding="utf-8")


def _json_default(value):
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, Path):
        return str(value)
    return str(value)


# --- Hyperparameters (T015; R3) ---------------------------------------------

def resolve_hyperparameters(config: LaunchConfig) -> Tuple[dict, dict, dict]:
    """Return (hyperparams, hyperparams_p3, provenance). Default = canonical forecasting set."""
    if config.hyperparameter_set == "custom":
        if not (config.hyperparameters_path and config.hyperparameters_p3_path):
            raise LaunchError("--hyperparameter-set custom requires both --hyperparameters and --hyperparameters-p3.")
        hp = json.loads(Path(config.hyperparameters_path).read_text(encoding="utf-8"))
        hp3 = json.loads(Path(config.hyperparameters_p3_path).read_text(encoding="utf-8"))
        prov = {"set": "custom", "hyperparameters": str(config.hyperparameters_path), "hyperparameters_p3": str(config.hyperparameters_p3_path)}
        return hp, hp3, prov
    hp_path = config.hyperparameters_path or (paths.CONFIG_DIR / "forecasting_hyperparameters.json")
    hp3_path = config.hyperparameters_p3_path or (paths.CONFIG_DIR / "forecasting_hyperparameters_p3.json")
    missing = [str(p) for p in (hp_path, hp3_path) if not Path(p).exists()]
    if missing:
        raise LaunchError("Missing hyperparameter config files: " + "; ".join(missing))
    hp = json.loads(Path(hp_path).read_text(encoding="utf-8"))
    hp3 = json.loads(Path(hp3_path).read_text(encoding="utf-8"))
    prov = {"set": "canonical", "hyperparameters": str(hp_path), "hyperparameters_p3": str(hp3_path)}
    return hp, hp3, prov


def _fit_model(X_train, y_train, sample_weight, target_column, hyperparams, hyperparams_p3, seed):
    """Mirror of the canonical deep-feature fit_model (generic; no weight-decay assumptions)."""
    import xgboost as xgb

    params = dict(hyperparams_p3 if target_column == "phase3_worse" else hyperparams)
    params["random_state"] = seed
    model = xgb.XGBRegressor(**params)
    model.fit(X_train, y_train, sample_weight=sample_weight)
    return model


def train_cumulative_regressors(
    train_featured: pd.DataFrame, feature_columns: Sequence[str], config: LaunchConfig, model_dir: Optional[Path] = None
) -> Tuple[Dict[str, object], dict]:
    """Train four canonical cumulative regressors (FR-014/015). Persists boosters if model_dir given."""
    hp, hp3, prov = resolve_hyperparameters(config)
    weights_all = None
    if config.use_time_decay:
        weights_all = launch_time_decay_weights(train_featured["date"], config.launch_month, config.half_life_months)
    models: Dict[str, object] = {}
    for target in TARGET_COLUMNS:
        ready = train_featured.dropna(subset=[target])
        X = ready.loc[:, list(feature_columns)]
        y = ready[target]
        w = weights_all.reindex(ready.index) if weights_all is not None else pd.Series(1.0, index=ready.index)
        fwd.validate_weights(w)
        models[target] = _fit_model(X, y, w, target, hp, hp3, config.seed)
    prov["time_decay"] = {"enabled": config.use_time_decay, "half_life_months": config.half_life_months, "anchor_month": config.launch_month}
    prov["feature_count"] = len(feature_columns)
    if model_dir is not None:
        save_model_artifacts(models, feature_columns, model_dir)
    return models, prov


def save_model_artifacts(models: Mapping[str, object], feature_columns: Sequence[str], model_dir: Path) -> None:
    model_dir.mkdir(parents=True, exist_ok=True)
    for target, model in models.items():
        model.save_model(str(model_dir / f"{target}_model.json"))
    (model_dir / "feature_columns.json").write_text(json.dumps(list(feature_columns), indent=2), encoding="utf-8")


def load_model_artifacts(model_dir: Path) -> Tuple[Dict[str, object], List[str]]:
    import xgboost as xgb

    if not Path(model_dir).exists():
        raise LaunchError(f"--model-artifact-dir does not exist: {model_dir}")
    feature_file = Path(model_dir) / "feature_columns.json"
    if not feature_file.exists():
        raise LaunchError(f"Model artifact directory missing feature_columns.json: {model_dir}")
    feature_columns = json.loads(feature_file.read_text(encoding="utf-8"))
    models: Dict[str, object] = {}
    for target in TARGET_COLUMNS:
        path = Path(model_dir) / f"{target}_model.json"
        if not path.exists():
            raise LaunchError(f"Model artifact directory missing {target}_model.json: {model_dir}")
        model = xgb.XGBRegressor()
        model.load_model(str(path))
        models[target] = model
    return models, feature_columns


def predict_april(models: Mapping[str, object], xtest_featured: pd.DataFrame, feature_columns: Sequence[str], config: LaunchConfig) -> pd.DataFrame:
    """Predict the four cumulative targets for every eligible April area (FR-017/019)."""
    X = xtest_featured.reindex(columns=list(feature_columns), fill_value=0)
    out_cols = {}
    for target in TARGET_COLUMNS:
        out_cols[f"{target}_pred"] = np.asarray(models[target].predict(X), dtype=float)
    pred = xtest_featured[[c for c in ("area_id", "year", "month", "date") if c in xtest_featured.columns]].copy()
    for c in ("country", "region", "name"):
        if c in xtest_featured.columns:
            pred[c] = xtest_featured[c].values
    for k, v in out_cols.items():
        pred[k] = v
    return pred.reset_index(drop=True)


def assemble_prediction_output(pred_validated: pd.DataFrame, overall_phase: pd.Series, config: LaunchConfig) -> pd.DataFrame:
    out = pred_validated.copy()
    out["overall_phase_pred"] = overall_phase.reindex(out.index).astype("Int64")
    # aliases phase{2..5}_pred mirroring canonical naming
    for target, phase in PHASE_FROM_TARGET.items():
        out[f"phase{phase}_pred"] = out[f"{target}_pred"]
    feature_period = str(launch_feature_period(config))
    target_period = str(launch_target_period(config))
    out["scope_months"] = config.scope_months
    out["feature_period"] = feature_period
    out["target_period"] = target_period
    out["launch_month"] = config.launch_month
    out["model_workflow"] = MODEL_WORKFLOW
    out["scale"] = config.scale
    out["threshold"] = config.threshold
    out["training_cutoff"] = config.training_cutoff
    out["comprehensive_source"] = str(config.comprehensive_source)
    out["run_id"] = config.run_id
    return out


# --- Distribution summaries & output writing (T019; FR-030/031) -------------

def prediction_distribution_summary(pred_out: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for target in TARGET_COLUMNS:
        col = f"{target}_pred"
        s = pd.to_numeric(pred_out[col], errors="coerce")
        rows.append({
            "target": col, "count": int(s.notna().sum()), "min": float(s.min()), "p25": float(s.quantile(0.25)),
            "median": float(s.median()), "p75": float(s.quantile(0.75)), "max": float(s.max()), "mean": float(s.mean()),
        })
    return pd.DataFrame(rows)


def predicted_phase_distribution(pred_out: pd.DataFrame) -> pd.DataFrame:
    counts = pred_out["overall_phase_pred"].value_counts(dropna=False).sort_index()
    total = int(counts.sum())
    return pd.DataFrame([
        {"overall_phase_pred": (int(k) if pd.notna(k) else None), "count": int(v), "share": (float(v) / total if total else 0.0)}
        for k, v in counts.items()
    ])


def write_prediction_outputs(
    layout: OutputLayout, pred_out: pd.DataFrame, xtest_featured: pd.DataFrame, feature_columns: Sequence[str],
    coverage: dict, pred_validation: dict, overwrite: bool,
) -> None:
    layout.out_root.mkdir(parents=True, exist_ok=True)
    pred_out.to_csv(layout.predictions_csv, index=False)
    prediction_distribution_summary(pred_out).to_csv(layout.prediction_distribution_csv, index=False)
    predicted_phase_distribution(pred_out).to_csv(layout.predicted_phase_distribution_csv, index=False)
    write_json(layout.prediction_validation_json, pred_validation)
    # model-aligned X_test artifact
    aligned = xtest_featured.reindex(columns=["area_id", *list(feature_columns)], fill_value=0) if "area_id" in xtest_featured.columns else xtest_featured.reindex(columns=list(feature_columns), fill_value=0)
    aligned.to_csv(layout.xtest_aligned_csv, index=False)
    # coverage + eligibility
    pd.DataFrame([coverage.get("dedup", {})]).to_csv(layout.xtest_coverage_csv, index=False)
    pred_out[["area_id"]].assign(eligible=True, predicted=True).to_csv(layout.eligibility_csv, index=False)


def build_run_summary(
    config: LaunchConfig,
    layout: OutputLayout,
    training_summary: dict,
    coverage: dict,
    feature_columns: Sequence[str],
    hp_prov: dict,
    viz_paths: Optional[dict] = None,
    forecasted_weather: Optional[dict] = None,
    grouped_shap: Optional[dict] = None,
) -> dict:
    feature_period = str(launch_feature_period(config))
    target_period = str(launch_target_period(config))
    return {
        "run_id": config.run_id,
        "scale": config.scale,
        "comprehensive_source": str(config.comprehensive_source),
        "training_cutoff": config.training_cutoff,
        "launch_month": config.launch_month,
        "scope_months": config.scope_months,
        "feature_period": feature_period,
        "target_period": target_period,
        "threshold": config.threshold,
        "model_workflow": MODEL_WORKFLOW,
        "execution_mode": config.execution_mode,
        "hyperparameters": hp_prov,
        "identifier_feature_setting": config.add_identifier_features,
        "sample_weighting": {"time_decay": config.use_time_decay, "half_life_months": config.half_life_months, "anchor_month": config.launch_month},
        "forecasted_weather": forecasted_weather or {"enabled": bool(config.using_forecasted_weather), "active": False},
        "grouped_shap": grouped_shap or {"enabled": bool(config.compute_grouped_shap), "active": False},
        "training_rows": training_summary.get("training_rows"),
        "train_min_date": training_summary.get("train_min_date"),
        "train_max_date": training_summary.get("train_max_date"),
        "predicted_area_count": coverage.get("launch_month_area_count"),
        "feature_count": len(feature_columns),
        "output_paths": {
            "predictions": str(layout.predictions_csv),
            "run_summary": str(layout.run_summary_json),
            "feature_schema": str(layout.feature_schema_csv),
            "grouped_shap": {name: str(path) for name, path in _grouped_shap_reported_artifact_paths(layout).items()},
        },
        "visualization_paths": viz_paths or {},
    }


# --- Validate-only (T022; FR-006/036, I1) -----------------------------------

def run_validation_only(config: LaunchConfig, df: pd.DataFrame, layout: OutputLayout, overwrite: bool) -> dict:
    """Validate inputs/schema/mode without training or prediction. Writes only validation artifacts."""
    summary = validate_source(df, config)
    prepared = prepare_source(df)
    train, train_summary = build_training_frame(prepared, config)
    april, coverage = build_xtest_april(prepared, config)
    featured_train, transform = apply_identifier_features(train, config)
    featured_xtest, _ = apply_identifier_features(april, config)
    featured_train, featured_xtest, weather_report = apply_forecasted_weather_features(
        featured_train, featured_xtest, prepared, config
    )
    feature_columns = select_model_features(featured_train)
    schema_df, warnings = build_feature_schema_report(
        featured_train, feature_columns, featured_train.columns, featured_xtest.columns, transform,
    )
    summary["feature_count"] = len(feature_columns)
    summary["feature_schema_warnings"] = warnings
    summary["training_summary"] = train_summary
    summary["coverage"] = coverage
    summary["forecasted_weather"] = weather_report
    summary["execution_mode"] = config.execution_mode
    summary["status"] = "validated"
    # Only validation artifacts are written; never production outputs.
    guard_output_conflicts(layout.validation_only_targets, overwrite)
    layout.out_root.mkdir(parents=True, exist_ok=True)
    write_json(layout.input_validation_json, summary)
    schema_df.to_csv(layout.feature_schema_csv, index=False)
    # Report (do not block on) intended production-output conflicts.
    production_conflicts = [str(p) for p in (layout.predictions_csv, layout.run_summary_json) if p.exists()]
    summary["intended_production_output_conflicts"] = production_conflicts
    return summary


# --- Human-readable launch report (T035; SC-010) ----------------------------

def _df_to_md(df: pd.DataFrame) -> str:
    """Render a DataFrame as a markdown table without requiring the optional 'tabulate' dep."""
    try:
        return df.to_markdown(index=False)
    except Exception:  # noqa: BLE001 - tabulate not installed
        cols = list(df.columns)
        header = "| " + " | ".join(str(c) for c in cols) + " |"
        sep = "| " + " | ".join("---" for _ in cols) + " |"
        rows = ["| " + " | ".join(str(v) for v in row) + " |" for row in df.itertuples(index=False, name=None)]
        return "\n".join([header, sep, *rows])


def write_launch_reports(
    config: LaunchConfig, layout: OutputLayout, run_summary: dict, pred_out: Optional[pd.DataFrame],
    pred_dist: Optional[pd.DataFrame], phase_dist: Optional[pd.DataFrame], comparison: Optional[dict],
    map_summary: Optional[dict], warnings: Sequence[str],
) -> None:
    layout.report_root.mkdir(parents=True, exist_ok=True)
    lines: List[str] = []
    lines.append(f"# April 2026 Global Nowcasting Launch — {config.launch_month}")
    lines.append("")
    lines.append("**This is a production launch, NOT a held-out validation experiment.** Global scale only.")
    lines.append("")
    lines.append("**Fallback comprehensive-source caveat:** This launch draws features directly from the comprehensive "
                 "feature CSV rather than the canonical `scope_0m_model_ready` feature schema. Results may not be "
                 "directly comparable to prior canonical 0m model-ready experiments if the feature schema differs.")
    lines.append("")
    lines.append("## Configuration")
    lines.append(f"- Comprehensive source: `{config.comprehensive_source}`")
    lines.append(f"- Training cutoff: `{config.training_cutoff}` (train strictly before)")
    lines.append(f"- Scope: `{config.scope_months}` month(s); feature period `{launch_feature_period(config)}`; target period `{launch_target_period(config)}`")
    lines.append(f"- Threshold: `th={config.threshold}` (canonical, fixed)")
    lines.append(f"- Execution mode: `{config.execution_mode}`")
    lines.append(f"- Hyperparameters: `{run_summary.get('hyperparameters', {})}`")
    lines.append(f"- Sample weighting: `{run_summary.get('sample_weighting', {})}`")
    lines.append(f"- Forecasted weather: `{run_summary.get('forecasted_weather', {})}`")
    lines.append(f"- Grouped SHAP: `{run_summary.get('grouped_shap', {})}`")
    lines.append(f"- Training rows: {run_summary.get('training_rows')} (dates {run_summary.get('train_min_date')} .. {run_summary.get('train_max_date')})")
    lines.append(f"- Predicted April 2026 areas: {run_summary.get('predicted_area_count')}")
    lines.append(f"- Feature count: {run_summary.get('feature_count')}")
    lines.append("")
    if phase_dist is not None and len(phase_dist):
        lines.append("## Predicted phase distribution")
        lines.append(_df_to_md(phase_dist))
        lines.append("")
    if pred_dist is not None and len(pred_dist):
        lines.append("## phase2-5 worse prediction distributions")
        lines.append(_df_to_md(pred_dist))
        lines.append("")
    if comparison is not None:
        cov = comparison.get("coverage", {})
        lines.append(f"## Actual comparison ({cov.get('target_period', launch_target_period(config))})")
        m = comparison.get("metrics", {})
        if m.get("status") == "unavailable":
            lines.append(f"- Actual-dependent metrics unavailable: {m.get('reason')}.")
        else:
            lines.append(f"- Predicted areas: {cov.get('predicted_area_count')}; actual-labeled: {cov.get('april_actual_labeled_area_count')}; "
                         f"covered intersection: {cov.get('covered_intersection_count')} ({cov.get('coverage_share_of_predicted', 0):.1%} of predicted).")
            if cov.get("actual_coverage_partial"):
                lines.append("- **Warning: actual coverage is partial.** Metrics below apply ONLY to the covered subset.")
            lines.append("- These are **descriptive** comparison metrics — not held-out validation, model-selection, or threshold-tuning evidence.")
            if m.get("covered_area_count"):
                lines.append(f"- Covered n={m.get('covered_area_count')}; accuracy={m.get('accuracy')}, macro-F1={m.get('macro_f1')}, weighted-F1={m.get('weighted_f1')}.")
                lines.append(f"- 3+ crisis P/R/F1/F2 = {m.get('phase3_plus_precision')}/{m.get('phase3_plus_recall')}/{m.get('phase3_plus_f1')}/{m.get('phase3_plus_f2')}.")
                lines.append(f"- 4+ crisis P/R/F1/F2 = {m.get('phase4_plus_precision')}/{m.get('phase4_plus_recall')}/{m.get('phase4_plus_f1')}/{m.get('phase4_plus_f2')}.")
        lines.append("")
    if map_summary is not None:
        heading = "Predicted-only crisis map" if map_summary.get("status") == "rendered_predicted_only" else "Two-panel crisis map"
        lines.append(f"## {heading}")
        lines.append(f"- Figure: `{map_summary.get('output_path')}`")
        lines.append(f"- Mapped predicted areas: {map_summary.get('mapped_predicted_count')}; mapped actual areas: {map_summary.get('mapped_actual_count')}.")
        lines.append(f"- Unmatched prediction ids: {len(map_summary.get('unmatched_prediction_area_ids', []))}; unmatched actual ids: {len(map_summary.get('unmatched_actual_area_ids', []))}.")
        if map_summary.get("status") == "rendered_predicted_only":
            lines.append("- Target-period actuals unavailable; map shows predictions only.")
        else:
            lines.append("- Top panel: actual crisis (actual-covered subset). Bottom panel: predicted crisis (all eligible). Coverage may differ.")
        lines.append("")
    if warnings:
        lines.append("## Warnings")
        for w in warnings:
            lines.append(f"- {w}")
        lines.append("")
    (layout.report_root / "launch_summary.md").write_text("\n".join(lines), encoding="utf-8")
    # supporting summaries
    if pred_dist is not None:
        (layout.report_root / "prediction_distribution_summary.md").write_text(
            "# Prediction distribution summary\n\n" + (_df_to_md(pred_dist) if len(pred_dist) else "n/a"), encoding="utf-8")
    cov_warn = "\n".join(f"- {w}" for w in warnings) or "- none"
    (layout.report_root / "data_coverage_and_warnings.md").write_text(
        f"# Data coverage and warnings\n\n{cov_warn}\n", encoding="utf-8")
    if comparison is not None:
        (layout.report_root / "actual_comparison_summary.md").write_text(
            "# April 2026 actual comparison (descriptive only)\n\n"
            f"Coverage: {comparison.get('coverage', {})}\n\nMetrics: {comparison.get('metrics', {})}\n", encoding="utf-8")

