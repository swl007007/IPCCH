import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = PROJECT_ROOT / "configs"
DATA_DIR = PROJECT_ROOT / "data"
REFERENCE_DATA_DIR = DATA_DIR / "reference"
RESULTS_DIR = PROJECT_ROOT / "results"
REPORTS_DIR = PROJECT_ROOT / "reports"
SOURCE_DATA_DIR = PROJECT_ROOT.parents[2] / "1.Source Data"

DEFAULT_EXTERNAL_PATHS = {
    "raw_data_dir": SOURCE_DATA_DIR,
    "forecasting_dataset": SOURCE_DATA_DIR / "forecasting_subset_IPCCH_v1210.csv",
    "processed_forecasting_dataset": SOURCE_DATA_DIR / "forecasting_subset_IPCCH_v1210_processed.csv",
    "nowcasting_dataset": SOURCE_DATA_DIR / "nowcasting_subset_IPCCH_v0318_no_lat_lon.csv",
    "ipcch_reference_dataset": SOURCE_DATA_DIR / "IPCCH_2017_2025_final_v12102025_with_zscores.csv",
    "ipc_ch_geojson": SOURCE_DATA_DIR / "Outcome" / "gdf_ipc_ch_final.geojson",
    "deep_features_scope_0m_model_ready_dataset": SOURCE_DATA_DIR
    / "assembled_IPCCH"
    / "model_ready"
    / "forecasting_subset_IPCCH_2026_target_corrected_deep_features_scope_0m_model_ready.csv",
    "deep_features_scope_3m_model_ready_dataset": SOURCE_DATA_DIR
    / "assembled_IPCCH"
    / "model_ready"
    / "forecasting_subset_IPCCH_2026_target_corrected_deep_features_scope_3m_model_ready.csv",
    "deep_features_scope_6m_model_ready_dataset": SOURCE_DATA_DIR
    / "assembled_IPCCH"
    / "model_ready"
    / "forecasting_subset_IPCCH_2026_target_corrected_deep_features_scope_6m_model_ready.csv",
    "deep_features_forecasting_dataset": SOURCE_DATA_DIR
    / "assembled_IPCCH"
    / "model_ready"
    / "forecasting_subset_IPCCH_2026_target_corrected_deep_features_forecasting_ready.csv",
    "ipcch_2026_completed_dataset": SOURCE_DATA_DIR / "assembled_IPCCH" / "raw" / "IPCCH_2026_completed.csv",
    "six_category_feature_crosswalk": SOURCE_DATA_DIR
    / "assembled_IPCCH"
    / "metadata"
    / "forecasting_2026_model_ready_variable_six_category_crosswalk.csv",
}


def project_path(*parts: str) -> Path:
    return PROJECT_ROOT.joinpath(*parts)


def external_path(key: str) -> Path:
    local_config = CONFIG_DIR / "paths.local.json"
    if local_config.exists():
        local_paths = json.loads(local_config.read_text(encoding="utf-8"))
        if key in local_paths:
            return Path(local_paths[key]).expanduser()
    return DEFAULT_EXTERNAL_PATHS[key]
