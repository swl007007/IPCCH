# Readable vocabulary contract

All user-facing strings are English. Authority is the reference October 9 PRD
D3–D17, adapted explicitly for 0-month, this repository's distinct arms, label
settings, launch inference and model snapshots. Do not force GeoXGB partition
roles onto IPCCH feature-set arms. Centralize mappings; unknown values fail.

## Objects

| Object | Name |
|---|---|
| Detailed experiment | IPCCH Forecasting - detailed runs |
| Dashboard experiment | IPCCH Forecasting - dashboard |
| Child/dashboard run | `<family short title> | <arm> | <N>-month` |
| Registered model | `IPCCH Forecasting <family short title> | <arm> | <N>-month` |
| Evaluation dataset | `IPCCH Forecasting eval | <N>-month | <actual period> | <cohort> (<scope/setting when needed>)` |
| Training descriptor | `IPCCH Forecasting training pool | <feature/label setting> | <N>-month` |
| Launch inference descriptor | `IPCCH Forecasting inference | <scope> | origin 2026-04 | target <month>` |

Names do not embed hashes, long source run IDs or importer versions. Original and
extended Compact detailed runs may share readable names; immutable snapshot tags,
descriptions and model version identify them. Only the latest snapshot projects
to the dashboard. Do not misleadingly call evaluation years a training window.

## Families and arms

| Source | Family short title | Raw arm -> readable arm |
|---|---|---|
| somalia_oracle/v1 | Somalia oracle information historical | A -> existing_predictors; B -> seasonal_climate; C -> weather_oracle; D -> weather_oracle_with_share_history |
| somalia_oracle/v2_q3 | Somalia q3 optimization historical | A/B/C as above; D_direct -> share_history_direct; D_residual -> share_history_residual; D_selected -> share_history_selected |
| somalia_oracle/v3_validity, original | Somalia validity observed-label historical | D_direct -> share_history_direct; D_residual -> share_history_residual; D_selected -> share_history_selected |
| somalia_oracle/v3_validity, augmented | Somalia validity augmented-training historical | Same three arm mappings |
| somalia_oracle/v4_calibrated_d, original | Somalia calibrated observed-label historical | selected D recipe -> calibrated_share_history |
| somalia_oracle/v4_calibrated_d, augmented | Somalia calibrated augmented-label historical | selected D recipe -> calibrated_share_history |
| origin_safe_climate_idp_v1 | Origin-safe climate global historical | climate_no_history -> no_ipc_history; climate_safe_history -> safe_ipc_history; climate_safe_history_idp -> safe_ipc_history_idp |
| origin_safe_weather_oracle_v1 | Origin-safe weather global historical | climate_safe_history_idp_oracle -> weather_oracle; climate_safe_history_idp_oracle_b6 -> weather_oracle_with_summaries |
| compact historical original + extension, global | Compact climate global historical | compact_baseline -> baseline; compact_weather_oracle -> weather_oracle |
| compact historical original + extension, SOM | Compact climate Somalia-local historical | Same two mappings |
| compact launch, global | Compact climate global launch | compact_baseline -> baseline; compact_cds_weather -> cds_weather |
| compact launch, SOM | Compact climate Somalia-local launch | Same two mappings |

The label settings above are scientific identity, not cosmetic versions: v3 copies
augment training only with the same outer evaluation keys, whereas v4 copies also
participate in evaluation. A–D meanings are cumulative information sets, never
opaque display names. Somalia denotes locally fitted Somalia models; region-level
scores of a global model do not get a Somalia-local family name.

Metric-only persistence/always-crisis and reused reference views use descriptive
roles (`share_persistence`, `phase_persistence`, `always_crisis`, `reference_*`).
These do not create fitted models. H0 B/C and selected recipes may have separate
comparison views but must point to their actual component members and disclose
reuse. X1–X6 are tree bundles, not scientific arms. Calibration and raw/final
output views are not automatically separate fitted-model registry entries.

## Tags and parameters

| Field | Contract |
|---|---|
| `lead_months` tag | `00`, `03`, `06`, `12`; numeric parameter 0/3/6/12 |
| `family` | readable mapping's stable English snake_case slug |
| `arm` | mapped role above |
| `arm_role` | baseline / candidate / diagnostic, grounded per comparison |
| `model_scope` | global / somalia_local |
| `stage` | historical / launch |
| `label_setting` | explicit observed / training_augmented / role_augmented when applicable |
| `period` | actual target support span; enumerate sparse months in descriptor |
| `period_role` | primary / original / year_2022 ... year_2026, or named saved subset |
| `source_status` | source-grounded scientific completion status; never importer success |
| `_prov.*` | original IDs/paths, snapshot identity, hashes, code/importer version, import state |

Descriptions and NA documents carry per-slot status even when the child has mixed
complete/empty/incomplete slots. Avoid one falsely reassuring top-level status.

## Metric vocabulary

Keep reference conventions `binary.*`, `share_phase3plus_*`, `n_rows` and explicit
contrasts `<A>_minus_<B>`. IPCCH exact phase accuracy is five-class, so use
`five_class.*`, not the reference's scientifically different `four_class.*`.

| Modern raw key | Mapped metric |
|---|---|
| exact_phase_accuracy | five_class.accuracy |
| phase3plus_accuracy | binary.accuracy |
| precision_phase3plus | binary.precision |
| sensitivity_phase3plus | binary.recall |
| f2_phase3plus | binary.f2 |
| r2_phase3plus | share_phase3plus_r2 |
| mae_phase3plus | share_phase3plus_mae |
| ordinal_mae | five_class.ordinal_mae |
| n / n_samples | n_rows |

Somalia raw/final/calibrated share scores and within-month vs pooled AUC must stay
distinct. C0 enumerates their exact source column map; do not drop an unknown
finite source metric or collapse two distinct metrics onto one key. Keep saved
intervals where present, but never compute new ones. Intentionally leaky diagnostic
views, if preserved among allowed source detail, are labeled diagnostics and
excluded from primary dashboard comparisons. Do not register their postprocessing
as new trained models.

Use full keys `<period_role>.<cohort>.<metric>`; cohort names explain scored
eligibility and region when relevant. Compact extension primary = pooled
2022–2026; original = pooled 2022–2025; year_2026 = Jan–Apr support only. In other
families use their actual saved support; do not assign these Compact periods.
Launch keys explicitly say prediction summaries/population counts or shares and
paired prediction differences; never label them accuracy/performance without a
saved, eligible actual-label evaluation source.

## Description template

**What:** Scientific information set, local/global fitting scope, stage, lead,
label treatment and selected-recipe/component meaning.

**Compare with:** Exact eligible baseline/arm, same target support and truth/cohort;
explicitly warn where original/augmented truth or evaluation populations differ.

**Status:** Source execution/scientific status, partial/empty/incomplete slots and
existing audit disposition. Source replay evidence is dated; catalog checks are
reported separately. No new research conclusion from this import.

**Caveats + original:** Counterfactual realized weather versus operational CDS;
temporal/selection limitations; actual cohort support; raw/final calibration;
source snapshot and member index links. MLflow wall time is registration time.
State external descriptor and lack of a directly callable prediction wrapper.

Parent description additionally gives the research question and an attributed
accepted conclusion only when source acceptance supports it; otherwise state
that no accepted conclusion is recorded. Explain the view/artifact reading guide.
