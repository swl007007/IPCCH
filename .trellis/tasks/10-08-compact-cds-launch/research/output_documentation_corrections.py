"""Documentation-only output corrections for compact_cds_launch_v1 (supervisor requests 2026-10-09). No model/code/config change.

1. Codebook (reports/.../model_run_codebook_en.csv): copy the approved per-variable training/inference fields from the expected
   contract (training_source, inference_source, training/inference formula, missing semantics, reference period, spatial
   definition) and drop the expected-contract sentences from ``limitations``. Rows, predictor order, membership columns,
   actual_model_columns/positions, expected_matches_actual and fit_status are asserted unchanged.
2. Five categorical PNGs: re-rendered from the SAVED categorical records (results/.../visualizations/crisis_categorical_*.csv,
   classes asserted equal to each run's predictions_raw.csv) with the same geometry and the frozen launch_visualizations /
   alert_risk_maps helpers (join, _panel incl. Latin-America inset, colors, legend, figure size, margins, dpi). Only the
   panel title (short) and the suptitle (accurate predicted-only wording) change; text extents are asserted inside the canvas.
3. figure_metadata.json and report_outputs.json: record the correction and refresh figure/codebook hashes.
Superseded PNGs are copied to research/final_verify_attempt1/superseded_figures/ before overwrite.

Run from the repository root (frozen model interpreter):
  PYTHONPATH=src /home/swl007007/.venvs/ipcch-geo/bin/python .trellis/tasks/10-08-compact-cds-launch/research/output_documentation_corrections.py
"""
import hashlib
import json
import shutil
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import pandas as pd  # noqa: E402

from ipcch import alert_risk_maps as arm  # noqa: E402
from ipcch import compact_launch as cl  # noqa: E402
from ipcch import launch_visualizations as lv  # noqa: E402

TASK = Path(".trellis/tasks/10-08-compact-cds-launch/research")
SCRIPT = TASK / "output_documentation_corrections.py"
RES, REP = Path(cl.RESULTS_ROOT), Path(cl.REPORTS_ROOT)
SUPERSEDED = TASK / "final_verify_attempt1" / "superseded_figures"
CONTRACT = Path(cl.INPUT_ROOT) / "approved_spec" / "expected_feature_contract.csv"
DOC_FIELDS = ("training_source", "inference_source", "training_formula", "inference_formula", "training_missing_semantics",
              "inference_missing_semantics", "training_reference_period", "inference_reference_period", "training_spatial_definition",
              "inference_spatial_definition")
EXPECTED_SENTENCES = (" This is an expected input, not a fitted result.", "Expected inputs only; no fit verified. ")
WEATHER_OUTCOME = (" Launch outcome: CDS weather stage ACCEPTED (file identity/completeness checks; September overlap gate passed at all "
                   "6227 points under the empirically verified (month start, next month start] temperature window; provenance sha256 {prov}).")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


log = {"script": str(SCRIPT), "script_sha256": sha(SCRIPT), "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
       "scope": "documentation/figure-text only; models, predictions, records, fitted code and configs unchanged"}

# ---------------------------------------------------------------- 1. codebook
cb_path = REP / "model_run_codebook_en.csv"
old = pd.read_csv(cb_path, keep_default_na=False, dtype=str, encoding="utf-8-sig")
contract = pd.read_csv(CONTRACT, keep_default_na=False, dtype=str, encoding="utf-8-sig")
assert len(old) == len(contract) == 308 and old["predictor"].tolist() == contract["predictor"].tolist()
prov_sha = sha(Path(cl.INPUT_ROOT) / "cds_weather_provenance.json")
new = old.copy()
lim = new["limitations"]
for s in EXPECTED_SENTENCES:
    lim = lim.str.replace(s, "", regex=False)
weather = new["family"] == "weather_oracle"
lim = lim.where(~weather, lim + WEATHER_OUTCOME.format(prov=prov_sha))
new["limitations"] = lim.str.strip()
assert not new["limitations"].str.contains("expected input|Expected inputs|no fit verified", case=False, regex=True).any()
for f in DOC_FIELDS:
    new[f] = contract[f].to_numpy()
head = list(old.columns[: old.columns.get_loc("limitations") + 1])
order = head + list(DOC_FIELDS) + ["fit_status"]
assert set(order) == set(old.columns) | set(DOC_FIELDS)
new = new[order]
frozen_cols = [c for c in old.columns if c not in ("limitations", "inference_source")]
assert all(new[c].tolist() == old[c].tolist() for c in frozen_cols), "membership/order/actual columns changed"
assert (new["fit_status"] == "fitted_verified_all_20_boosters").all() and (new["expected_matches_actual"] == "True").all()
old_sha = sha(cb_path)
new.to_csv(cb_path, index=False, encoding="utf-8-sig")
back = pd.read_csv(cb_path, keep_default_na=False, dtype=str, encoding="utf-8-sig")
assert back.equals(new)
log["codebook"] = {"path": str(cb_path), "sha256_before": old_sha, "sha256_after": sha(cb_path), "rows": len(new), "columns_before": len(old.columns),
                   "columns_after": len(new.columns), "fields_copied_from_contract": list(DOC_FIELDS), "contract_sha256": sha(CONTRACT),
                   "limitations_sentences_removed": list(EXPECTED_SENTENCES), "weather_rows_outcome_appended": int(weather.sum()),
                   "unchanged_columns_asserted": frozen_cols}

# ---------------------------------------------------------------- 2. five categorical PNGs
plt, listed_cmap, patch = arm._require_matplotlib()
boundaries = arm.load_spatial_boundaries(cl.GEOMETRY)
meta_path = RES / "visualizations" / "figure_metadata.json"
meta = json.loads(meta_path.read_text())
SUPERSEDED.mkdir(parents=True, exist_ok=True)
figs = {}
for arm_, horizon in cl.RUNS:
    rid = cl.run_id(arm_, horizon)
    name = next(k for k, v in meta["figures"].items() if v.get("run_id") == rid)
    entry = meta["figures"][name]
    rec_path, fig_path = Path(entry["record"]), Path(entry["figure"])
    assert sha(rec_path) == entry["record_sha256"]
    rec = pd.read_csv(rec_path)
    raw = pd.read_csv(RES / "runs" / arm_ / f"{horizon}m" / "predictions_raw.csv", low_memory=False)
    chk = rec.merge(raw[["area_id", "overall_phase_pred"]], on="area_id", how="outer", suffixes=("", "_raw"), validate="one_to_one", indicator=True)
    assert len(rec) == 6188 and (chk["_merge"] == "both").all() and (chk["overall_phase_pred"] == chk["overall_phase_pred_raw"]).all()
    assert (rec["predicted_crisis"] == (rec["overall_phase_pred"] >= 3)).all() and (rec["run_id"] == rid).all()
    target = str(rec["target_month"].iloc[0])
    join = lv.join_for_two_panel(rec[["area_id", "overall_phase_pred", "target_month"]], rec.iloc[0:0][["area_id", "overall_phase_pred", "target_month"]], boundaries)
    assert not join.unmatched_prediction and join.mapped_predicted_count == 6188
    lv._ensure_crisis_columns(join)
    shared = " (shared H0 fit)" if horizon == 0 else ""
    panel_title = f"Predicted crisis (phase >= 3), target {target}, n={join.mapped_predicted_count} areas"
    suptitle = (f"IPCCH compact launch, origin 2026-04: {arm_} H{horizon}{shared}\n"
                "Predicted-only view; actual-outcome panels are excluded by design for this launch.")
    shutil.copy2(fig_path, SUPERSEDED / fig_path.name)
    before = sha(fig_path)
    # same layout as the frozen lv.plot_predicted_only (figsize, _panel with LatAm inset, legend, margins, dpi); text only differs
    fig, ax = plt.subplots(1, 1, figsize=(10, 7))
    lv._panel(ax, join.predicted_joined, "predicted_crisis", panel_title, listed_cmap, True, True)
    handles = [patch(color=arm.NO_ALERT_COLOR, label="No crisis (phase 1-2)"), patch(color=arm.ALERT_COLOR, label="Crisis (phase 3+)")]
    fig.legend(handles=handles, loc="lower center", ncol=2)
    sup = fig.suptitle(suptitle, fontsize=12)
    fig.subplots_adjust(left=0.04, right=0.97, bottom=0.10, top=0.88)
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    canvas = fig.bbox
    texts = [sup, ax.title] + [t for t in fig.legends[0].get_texts()]
    clipped = [t.get_text() for t in texts if t.get_text() and not (t.get_window_extent(renderer).x0 >= canvas.x0 and t.get_window_extent(renderer).x1 <= canvas.x1
                                                                      and t.get_window_extent(renderer).y0 >= canvas.y0 and t.get_window_extent(renderer).y1 <= canvas.y1)]
    assert not clipped, f"{name}: text outside canvas {clipped}"
    fig.savefig(fig_path, dpi=300)
    plt.close(fig)
    figs[name] = {"figure_sha256_before": before, "figure_sha256_after": sha(fig_path), "superseded_copy": str(SUPERSEDED / fig_path.name),
                  "panel_title": panel_title, "suptitle": suptitle, "text_inside_canvas": True, "record_sha256_unchanged": sha(rec_path),
                  "classes_equal_predictions_raw": True}
    entry["figure_sha256"] = sha(fig_path)
    entry["rendering_correction"] = {"version": 2, "reason": "v1 panel/suptitle text clipped at canvas edges (target_period embedded run_id/origin) and "
                                     "inherited subtitle wrongly said target-period actuals unavailable", "script": str(SCRIPT), "script_sha256": log["script_sha256"],
                                     "panel_title": panel_title, "suptitle": suptitle, "superseded_figure_sha256": before,
                                     "unchanged": "saved record, geometry, colors, legend, Latin-America inset, figure size/margins/dpi, filename"}
log["categorical_figures"] = figs
meta["documentation_corrections"] = {"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "script": str(SCRIPT), "script_sha256": log["script_sha256"],
                                     "figures_rerendered": sorted(figs), "continuous_figures": "unchanged"}
meta_path.write_text(json.dumps(meta, indent=2))

# ---------------------------------------------------------------- 3. report_outputs.json
ro_path = RES / "report_outputs.json"
ro = json.loads(ro_path.read_text())
log["report_outputs_sha256_before"] = sha(ro_path)
ro["maps"] = meta
ro["codebook"].update({"sha256": sha(cb_path), "columns": len(new.columns)})
ro["documentation_corrections"] = {"script": str(SCRIPT), "script_sha256": log["script_sha256"], "codebook_sha256_before": old_sha,
                                   "figure_metadata_sha256": sha(meta_path), "evidence": str(TASK / "output-documentation-corrections.json")}
ro_path.write_text(json.dumps(ro, indent=2, default=str))
log.update({"report_outputs_sha256_after": sha(ro_path), "figure_metadata_sha256_after": sha(meta_path),
            "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
(TASK / "output-documentation-corrections.json").write_text(json.dumps(log, indent=2))
print(json.dumps({"codebook": {k: log["codebook"][k] for k in ("sha256_before", "sha256_after", "rows", "columns_before", "columns_after")},
                  "figures": {k: v["figure_sha256_after"][:12] for k, v in figs.items()}}, indent=1))
