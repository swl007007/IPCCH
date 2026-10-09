"""Check exact plotted-record/table values, geometry coverage and actual-input-only codebook.

Run under the frozen modeling interpreter from repository root after final output corrections.
PNG layout is additionally inspected by the supervisor; this script checks their keyed underlying values.
"""
import csv
import hashlib
import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

RESULTS = Path("results/launch/nowcasting_2026_04_compact_cds_v1")
REPORTS = Path("reports/launch/nowcasting_2026_04_compact_cds_v1")
INPUTS = Path("../../../1.Source Data/assembled_IPCCH/model_ready/compact_cds_launch_v1")
RESEARCH = Path(".trellis/tasks/10-08-compact-cds-launch/research")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return pd.read_csv(path, float_precision="round_trip", keep_default_na=False, na_values=[""])


manifest = json.loads((INPUTS / "compact_cds_launch_v1_manifest.json").read_text())
area = read(RESULTS / "population/area_population_predictions.csv")
vis = RESULTS / "visualizations"
meta = json.loads((vis / "figure_metadata.json").read_text())
assert len(meta["figures"]) == 7
pngs = list((REPORTS / "figures").glob("*.png"))
assert len(pngs) == 7 and {p.stem for p in pngs} == set(meta["figures"])
for name, rec in meta["figures"].items():
    assert Path(rec["figure"]).stem == name and Path(rec["figure"]).stat().st_size > 0
    assert sha(rec["record"]) == rec["record_sha256"]
for ext, item in meta["geometry"].items():
    assert sha(item["path"]) == item["sha256"], ext
geometry = gpd.read_file(meta["geometry"][".shp"]["path"])
geometry["area_id"] = pd.to_numeric(geometry["admin_code"], errors="raise").astype(int)
assert not geometry.area_id.duplicated().any()
ids = sorted(area.area_id.unique().tolist())
joined = geometry.set_index("area_id").reindex(ids)
assert len(joined) == 6188 and not joined.geometry.isna().any() and not joined.geometry.is_empty.any()
assert np.isfinite(joined.geometry.bounds.to_numpy()).all()
assert meta["figures"]["p3plus_share_comparison_2x3"]["color_limits"] == [0, 100]
lim = meta["figures"]["p3plus_share_difference_1x2"]["color_limits"]
assert lim[0] == -lim[1] and lim[1] > 0

for rid, entry in manifest["runs"].items():
    name = f"crisis_categorical_{entry['arm']}_{entry['horizon']}m_{entry['target_month']}"
    cat = read(vis / f"{name}.csv").set_index("area_id").sort_index()
    pred = read(RESULTS / "runs" / rid / "predictions_raw.csv").set_index("area_id").sort_index()
    assert cat.index.tolist() == pred.index.tolist() == ids
    assert np.array_equal(cat.overall_phase_pred, pred.overall_phase_pred)
    assert np.array_equal(cat.predicted_crisis, pred.overall_phase_pred >= 3)
    assert (cat.target_month == entry["target_month"]).all() and (cat.run_id == rid).all()
    assert meta["figures"][name]["mapped_areas"] == 6188

shares = read(vis / "p3plus_share_comparison_2x3.csv")
assert len(shares) == 6 * 6188 and len(shares.groupby(["display_arm", "horizon"])) == 6
for (arm, h), part in shares.groupby(["display_arm", "horizon"]):
    part = part.set_index("area_id").sort_index()
    tab = area[(area.display_arm == arm) & (area.horizon == h)].set_index("area_id").sort_index()
    assert part.index.tolist() == ids
    assert part.source_run_id.tolist() == tab.source_run_id.tolist()
    assert part.target_month.tolist() == tab.target_month.tolist()
    assert np.array_equal(part.share_p3plus, tab.share_p3plus)
    assert np.allclose(part.p3plus_percent, tab.share_p3plus * 100, atol=1e-10, rtol=0)
delta = read(vis / "p3plus_share_difference_1x2.csv")
assert len(delta) == 2 * 6188 and sorted(delta.horizon.unique().tolist()) == [6, 12]
for h in (6, 12):
    part = delta[delta.horizon == h].set_index("area_id").sort_index()
    baseline = area[(area.display_arm == "compact_baseline") & (area.horizon == h)].set_index("area_id").sort_index()
    weather = area[(area.display_arm == "compact_cds_weather") & (area.horizon == h)].set_index("area_id").sort_index()
    assert part.index.tolist() == ids
    assert np.allclose(part.p3plus_pp_difference, (weather.share_p3plus - baseline.share_p3plus) * 100, atol=1e-10, rtol=0)
    assert np.abs(part.p3plus_pp_difference).max() <= lim[1]

with (INPUTS / "approved_spec/expected_feature_contract.csv").open(encoding="utf-8-sig") as f:
    contract = list(csv.DictReader(f))
cb_path = REPORTS / "model_run_codebook_en.csv"
with cb_path.open(encoding="utf-8-sig") as f:
    codebook = list(csv.DictReader(f))
assert len(codebook) == len(contract) == 308
assert [r["predictor"] for r in codebook] == [r["predictor"] for r in contract]
fields = ["training_source", "inference_source", "training_formula", "inference_formula", "training_missing_semantics",
          "inference_missing_semantics", "training_reference_period", "inference_reference_period",
          "training_spatial_definition", "inference_spatial_definition"]
for actual, design in zip(codebook, contract):
    name = actual["predictor"]
    positions = {rid: entry["features"].index(name) + 1 for rid, entry in manifest["runs"].items() if name in entry["features"]}
    assert positions and json.loads(actual["actual_model_columns"]) == [name]
    assert json.loads(actual["actual_model_positions"]) == positions == json.loads(design["expected_model_positions"])
    assert actual["fit_status"] == "fitted_verified_all_20_boosters" and actual["expected_matches_actual"].lower() == "true"
    assert "This is an expected input, not a fitted result." not in actual["limitations"]
    for field in fields:
        assert actual[field] == design[field], (name, field)
    for rid in manifest["runs"]:
        key = rid.replace("/", "_")
        assert (actual[key].lower() == "true") == (rid in positions)
        assert int(actual[f"{key}_expanded_count"]) == int(rid in positions)
outputs = json.loads((RESULTS / "report_outputs.json").read_text())
assert outputs["codebook"]["sha256"] == sha(cb_path)
result = {"passed": True, "checked_utc": pd.Timestamp.now(tz="UTC").isoformat(), "figures": 7, "mapped_areas_per_panel": 6188,
          "categorical_values": "exact raw phase >=3; five unique run records", "continuous_values": "repaired shares x100; six cohorts",
          "difference_values": "(CDS-baseline) repaired shares x100; two cohorts", "geometry_sidecars_rehashed": True,
          "codebook_union_rows": 308, "codebook_membership_and_order": {rid: len(e["features"]) for rid, e in manifest["runs"].items()},
          "codebook_actual_only": True, "codebook_training_inference_fields_match_contract": fields, "codebook_sha256": sha(cb_path),
          "figure_metadata_sha256": sha(vis / "figure_metadata.json"), "figure_sha256": {p.name: sha(p) for p in pngs}}
(RESEARCH / "supervisor-map-codebook-verification.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=1))
