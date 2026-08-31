from pathlib import Path

import pandas as pd
import pytest

from ipcch.forecasting_weight_decay import (
    extract_country_area_ids,
    extract_country_name,
    extract_somalia_area_ids,
    plan_outputs,
)


def test_country_lookup_resolves_nigeria_by_iso3():
    lookup = pd.DataFrame(
        {
            "area_id": [10, 11, 20],
            "iso3": ["NGA", "NGA", "SOM"],
            "country": ["Nigeria", "Nigeria", "Somalia"],
            "country_en": ["Nigeria", "Nigeria", "Somalia"],
        }
    )

    assert extract_country_area_ids(lookup, "nga") == [10, 11]
    assert extract_country_name(lookup, "NGA") == "Nigeria"
    assert extract_somalia_area_ids(lookup) == [20]


def test_country_lookup_can_fall_back_to_country_name():
    lookup = pd.DataFrame(
        {
            "admin_code": [100, 101],
            "country": ["Nigeria", "Somalia"],
        }
    )

    assert extract_country_area_ids(lookup, "NGA", "Nigeria") == [100]
    assert extract_country_name(lookup, "NGA", "Nigeria") == "Nigeria"


def test_country_lookup_rejects_invalid_iso3():
    lookup = pd.DataFrame({"area_id": [10], "iso3": ["NGA"]})

    with pytest.raises(ValueError, match="exactly three letters"):
        extract_country_area_ids(lookup, "NG")


def test_output_plan_uses_country_specific_metric_filename(tmp_path: Path):
    output_plan = plan_outputs(
        str(tmp_path / "results"),
        str(tmp_path / "reports"),
        metric_scope="Nigeria",
    )

    assert output_plan.metrics_scope_csv.name == "metrics_nigeria.csv"
    assert output_plan.report_metrics_scope_csv.name == "metrics_nigeria.csv"
    assert output_plan.metrics_somalia_csv == output_plan.metrics_scope_csv
    assert output_plan.report_metrics_somalia_csv == output_plan.report_metrics_scope_csv
