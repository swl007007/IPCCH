"""Somalia oracle-information experiment (task somalia-flood-food-crisis).

Four cumulative XGBoost arms (A existing predictors, B +V2 seasonal means,
C +realized future weather, D +rich phase-distribution history) are compared
within each (test year, horizon) on frozen common keys. See the task's
``prd.md``/``design.md``/``implement.md`` for the contract.
"""

HORIZONS = (0, 3, 6, 12)
HORIZON_FS = {0: "fs0", 3: "fs1", 6: "fs2", 12: "fs3"}
# Test year -> candidate supervised training target years.
FOLDS = {2025: (2022, 2023, 2024), 2026: (2023, 2024, 2025)}
ARMS = ("A", "B", "C", "D")

# Predictors blocked from every arm after lineage review (research.md addendum A).
BLOCKED_BASE_FEATURES = ("overall_phase_lag1", "estimated_population")

V2_FEATURES = (
    "prcp_anom_gs_ensmean",
    "prcp_z_gs_ensmean",
    "rainy_days_gs_ensmean",
    "cdd_gs_ensmean",
    "tmean_anom_gs_ensmean",
    "tmax_anom_gs_ensmean",
    "hot_days_p95_gs_ensmean",
    "gdd_gs_ensmean",
    "edd_gs_ensmean",
    "sm_z_gs_ensmean",
    "ndvi_anom_gs_ensmean",
    "evi_anom_gs_ensmean",
    "spi03_gs_ensmean",
    "spei03_gs_ensmean",
)
ORACLE_WEATHER_VARIABLES = ("Rainf_f_tavg_mean", "Tair_f_tavg_mean")
MAX_ORACLE_OFFSET = 6

PHASE_THRESHOLD = 0.2
HALF_LIFE_MONTHS = 24.0
INNER_VALIDATION_MONTHS = 3
MIN_SUPPORTED_INNER_MONTHS = 2
BOOTSTRAP_DRAWS = 2000
BOOTSTRAP_SEED = 42
# Model-ready labels from this year on must also be labeled in the raw canonical source.
PROVENANCE_CHECK_FROM_YEAR = 2025

PERCENT_COLUMNS = tuple(f"phase{i}_percent" for i in range(1, 6))
NORMALIZED_COLUMNS = tuple(f"p{i}" for i in range(1, 6))
CUMULATIVE_COLUMNS = ("q2", "q3", "q4", "q5")
PREDICTION_COLUMNS = tuple(f"{c}_pred" for c in CUMULATIVE_COLUMNS)


def oracle_offsets(horizon: int) -> tuple:
    return tuple(range(1, min(int(horizon), MAX_ORACLE_OFFSET) + 1))


def oracle_feature_names(horizon: int) -> list:
    return [f"oracle_{var}_o{k}" for k in oracle_offsets(horizon) for var in ORACLE_WEATHER_VARIABLES]
