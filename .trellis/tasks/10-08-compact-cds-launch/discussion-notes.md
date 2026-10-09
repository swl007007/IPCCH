# Planning discussion — compact CDS launch

This is a discussion ledger, not the formal spec. Grilling has converged and the user approved the final PRD/design/implement through the continuous supervisor/executor goal request. The current branch is retained. Executor-native task start and execution evidence are tracked separately.

## Confirmed user intent

- Use the current compact feature version as the baseline.
- Recreate the forecast-weather launch using realized oracle weather in training and CDS forecast weather at inference.
- Targets: April2026, October2026, April2027, with predicted population shares/counts and crisis maps.
- Metrics means forecast summaries, not accuracy/F1/actual-label scoring (user clarification).
- Three targets use the same April2026 population denominator; no separate population-growth projection (user selected recommendation).
- Retain the legacy country cap: if the April area-population sum exceeds110% of the country's2025 reference, scale to95% of that reference. Retain raw counts and scaling factors for provenance (user confirmed retaining the old cap).
- Use the numerically reconstructed legacy population-share rule: cumulative differences, component clipping to[0,1], then row normalization; population P3+/P4+ totals sum the corresponding repaired phase populations. Keep the raw compact predictions separately. The user selected this rule; it is reporting postprocessing, not model fitting/calibration or replacement of raw compact classification.
- Keep the current Git branch; use Windows Git preferentially.
- The user identified `.cdsapirc` in home. Existence/readability were checked at `/home/swl007007/.cdsapirc` without reading or exposing its contents. It can be used in the later execution stage; no CDS retrieve/download has been submitted.
- Accept the anomaly-reference difference: retain compact observed anomalies in training (declared1991–2020), use CDS system-specific model anomalies at inference (official1993–2016 hindcast reference), and explicitly record both definitions. The user responded that this difference is acceptable. No calibration or claim of identical anomaly lineage is implied.
- Retain the full May–October oracle window: the user confirmed supplementing the missing true October with same-April-init system51 original-frequency forecasts and1993–2016 hindcasts, constructing a monthly model anomaly and checking aggregation against overlapping official monthly products. No later initialization or realized October substitution; download/construction are planned for the later authorized execution stage.
- Common IPC label cutoff: for all H0/H6/H12 fitting, use only valid target labels before2026-04-01; inference IPC-history observations also stop at2026-03. The user selected this recommendation. Ordinary predictors still use April origin, and forecast weather still spans May–October. Historical fitting rows retain their own compact per-row origin/history safety rules, additionally bounded by the common available-label source.
- Keep the frozen compact calendar columns:2027 targets set all year_2014..year_2026 dummies to0, retain target-month dummies, and record an unseen-year flag in metadata only. The user selected this recommendation. No year_2027 model feature, year2026 substitution or calendar-at-origin recoding.
- Use the existing fixed area coordinates for all CDS forecast months and hindcasts, as selected by the user. Retain point-cell extraction, without new polygon/crop-weight aggregation or interpolation. Record that this does not establish a spatial match to the observed climate export.
- Produce both CDS-weather and no-oracle compact launch predictions. The user selected this scope. There are five unique model sets: sharedH0 baseline296, baselineH6/H12 each296, and oracle-training/CDS-inferenceH6/H12 each308. Keep common fitting keys, targets, weights, base features, population denominators and postprocessing across paired arms; report CDS-minus-baseline population/share changes and difference maps. These are prediction differences, not performance differences.
- Produce both predicted crisis/non-crisis categorical maps and P3+ population-share maps for the two arms/three targets. The user selected both. Categorical crisis preserves the canonical raw-model phase classification; continuous share maps and weather-minus-baseline difference maps use the approved repaired population shares, with percentage/percentage-point units and an explicit table/figure value contract. Raw cumulative model predictions remain available separately.

- Produce area/country/region/global forecast population summaries and corresponding paired differences. The user adopted the four-level recommendation. Region joins on area_id using the pinned mapping, retaining all regions0..8; aggregate shares are summed phase counts divided by summed population. New versioned input/result/report directories preserve all previous launch artifacts.

## Convergence status

All result-changing user choices are resolved. The user approved execution after the final summary by requesting a bound Opus5.5/1M Herdr executor and continuous goal supervision. Source retrieval, implementation and numerical acceptance had not begun at this approval checkpoint.

## Evidence

See `research/launch-input-findings.md` for local artifacts, code anchors, raw GRIB statistical months and limitations. No formal scientific choice is inferred from old implementation alone.
