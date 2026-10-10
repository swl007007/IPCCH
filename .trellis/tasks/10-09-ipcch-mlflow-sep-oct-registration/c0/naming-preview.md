# C0 naming / tag / description preview

Authority: `naming.md` (task), reference Food_Crisis_Cluster `38adbda` readable-naming
(`IPCCHMLflow/naming.py:433-568`). Every string below is English and generated from one
central vocabulary in C1; unmapped identifiers fail. Status wording here is a **draft
summary**; C1 quotes the exact closure/acceptance text with its source path.

## 1. Family vocabulary (12 families, 12 source snapshots)

| family tag | family title (child / registered short title) | parent run name (long) | scope / stage / label_setting | source snapshot(s) |
|---|---|---|---|---|
| `somalia_oracle_information` | Somalia oracle information historical | Somalia oracle information historical (local Somalia fits, cumulative information sets A-D, 2025-2026) | somalia_local / historical / – | somalia_oracle_v1 |
| `somalia_q3_optimization` | Somalia q3 optimization historical | Somalia q3 optimization historical (direct vs residual phase-3+ share, calibrated, 2025-2026) | somalia_local / historical / – | somalia_oracle_v2_q3 |
| `somalia_validity_observed` | Somalia validity observed-label historical | Somalia validity historical (observed labels vs validity-augmented training, 2025-2026) — shared parent | somalia_local / historical / observed | somalia_oracle_v3_validity |
| `somalia_validity_augmented` | Somalia validity augmented-training historical | (same parent as above) | somalia_local / historical / training_augmented | somalia_oracle_v3_validity |
| `somalia_calibrated_observed` | Somalia calibrated observed-label historical | Somalia calibrated share-history historical (per-origin selected and calibrated D, 2022-2026) — shared parent | somalia_local / historical / observed | somalia_oracle_v4_calibrated_d |
| `somalia_calibrated_augmented` | Somalia calibrated augmented-label historical | (same parent as above) | somalia_local / historical / role_augmented | somalia_oracle_v4_calibrated_d |
| `origin_safe_climate_global` | Origin-safe climate global historical | Origin-safe climate global historical (annual refit, safe IPC history and IDP, 2022-2025) | global / historical / – | origin_safe_climate_idp_v1 |
| `origin_safe_weather_global` | Origin-safe weather global historical | Origin-safe weather global historical (realized future weather oracle on the origin-safe reference, 2022-2025) | global / historical / – | origin_safe_weather_oracle_v1 |
| `compact_climate_global` | Compact climate global historical | Compact climate global historical (baseline 296 inputs; weather oracle 302 at 3-month, 308 at 6/12-month; snapshot 2022-2025 / extended 2022-2026 Jan-Apr) | global / historical / – | compact_global_original, compact_global_2026_extension |
| `compact_climate_somalia` | Compact climate Somalia-local historical | Compact climate Somalia-local historical (compact inputs refit on Somalia areas only; 2022-2025 / 2022-2026 Jan-Apr) | somalia_local / historical / – | compact_somalia_original, compact_somalia_2026_extension |
| `compact_launch_global` | Compact climate global launch | Compact climate global launch (origin 2026-04; targets 2026-04, 2026-10, 2027-04; CDS forecasts at inference) | global / launch / – | compact_global_launch |
| `compact_launch_somalia` | Compact climate Somalia-local launch | Compact climate Somalia-local launch (origin 2026-04; 904 Somalia areas) | somalia_local / launch / – | compact_somalia_launch |

Original and extended compact parents share the readable family title; they are told apart by
`snapshot = original_2022_2025 | extended_2022_2026` (visible tag), description, and model version.

## 2. Arm vocabulary (raw -> readable, arm_role)

| family | raw | arm | arm_role | fitted? |
|---|---|---|---|---|
| Somalia oracle information | A / B / C / D | existing_predictors / seasonal_climate / weather_oracle / weather_oracle_with_share_history | baseline / candidate / candidate / candidate | yes; **C 0-month = alias of B 0-month** (H0 C clones B) |
| " | persistence / always_crisis | phase_persistence / always_crisis | baseline | metric only |
| Somalia q3 optimization | A, B, C, D_direct, D_residual, D_selected | as above + share_history_direct / share_history_residual / share_history_selected | baseline, candidates | D_selected = registered composition of D_residual members (both years selected residual); C 0-month alias of B |
| " | share_persistence / phase_persistence / always_crisis / v1_D_raw / v1_D_isotonic | share_persistence / phase_persistence / always_crisis / reference_weather_oracle_with_share_history_raw / reference_weather_oracle_with_share_history_isotonic | baseline / baseline / baseline / diagnostic / diagnostic | metric only (reference views point to Somalia oracle information D members) |
| Somalia validity (both settings) | D_direct / D_residual / D_selected | share_history_direct / share_history_residual / share_history_selected | candidate | yes (selected is refit; equal bytes = deterministic refit) |
| " | share_persistence / phase_persistence / always_crisis | same | baseline | metric only, duplicated into both setting families (same eval keys/truth -> same dataset digest) |
| Somalia calibrated (both settings) | selected D recipe per origin | calibrated_share_history | candidate | yes |
| Origin-safe climate | climate_no_history / climate_safe_history / climate_safe_history_idp | no_ipc_history / safe_ipc_history / safe_ipc_history_idp | baseline / candidate / candidate | yes |
| Origin-safe weather | climate_safe_history_idp_oracle / _b6 | weather_oracle / weather_oracle_with_summaries | candidate | yes (3/6/12-month only) |
| " | climate_safe_history_idp (reused) | reference_safe_ipc_history_idp | baseline | metric only; links to Origin-safe climate safe_ipc_history_idp version |
| Compact historical (global, Somalia-local) | compact_baseline / compact_weather_oracle | baseline / weather_oracle | baseline / candidate | yes; **weather_oracle 0-month = alias view of baseline 0-month** |
| Compact launch (global, Somalia-local) | compact_baseline / compact_cds_weather | baseline / cds_weather | baseline / candidate | yes (baseline 0/6/12, cds 6/12); cds_weather 0-month alias view |

## 3. Objects — patterns and one concrete example each

```
Detailed experiment        IPCCH Forecasting - detailed runs
Dashboard experiment       IPCCH Forecasting - dashboard
Child / dashboard run      Compact climate global historical | weather_oracle | 6-month
Registered model           IPCCH Forecasting Compact climate global historical | weather_oracle | 6-month
  version 1                source compact_global_original (16 members: 4 annual fits 2022-2025 x 4 phase regressors)
  version 2                source compact_global_2026_extension (16 reused 2022-2025 + 4 new 2026 members = 20)
External LoggedModel       Compact climate global historical | weather_oracle | 6-month | snapshot extended 2022-2026
Eval dataset               IPCCH Forecasting eval | 6-month | 2022-01..2026-04 | all_scored (global origin-safe cohort)
                           IPCCH Forecasting eval | 6-month | 2026-01..2026-04 | region Somalia, global model
                           IPCCH Forecasting eval | 0-month | 2026-01..2026-04 | all_scored (Somalia-local cohort)
Training descriptor        IPCCH Forecasting training pool | compact 308 inputs, observed labels | 6-month
Launch inference           IPCCH Forecasting inference | global | origin 2026-04 | target 2026-10
                           IPCCH Forecasting inference | Somalia-local | origin 2026-04 | target 2027-04
```

Lead display `0-month`, `3-month`, `6-month`, `12-month`; tag `lead_months=00|03|06|12`;
param `lead_months=0|3|6|12`. Names carry no hashes/run IDs/importer version.

## 4. Tags (visible, in write order) and provenance

`family, family_title, arm, arm_role, lead_months, model_scope, stage, label_setting (only
Somalia validity/calibrated), snapshot (compact only), period.<role> (actual spans),
source_status, record_kind (family|evaluation|dashboard_row), aggregation (dashboard)`, then
provenance under **`zz_prov.*`**, written last (runs created with the full tag set in key order,
readable tags first) — resolved by supervisor (reference README:117-120, import spec:134-137).

`source_status` values (per child; per-slot detail in description and `view/na.json`):
`complete`, `complete_with_undefined_metrics`, `incomplete_slots`, `empty_slots`,
`prediction_summary_only` (launch). Never `import_complete`; import state is `zz_prov.import_status`.

## 5. Description previews (four paragraphs)

### 5a. Compact climate global historical | weather_oracle | 6-month (extended snapshot)

**What:** Global XGBoost model of the cumulative population shares q2..q5 (four regressors per
fit, phase from the 0.20 rule on unrounded scores), using **308 inputs**: the 296 compact baseline
inputs plus realized monthly rainfall and temperature anomalies for the 6 months after the forecast
origin (2 variables x 6 offsets). Fitted on all areas (global scope), historical evaluation, 6-month
lead (origin = target month minus 6). One annual refit per evaluation year: 2022-2025 fits reused
unchanged from the original snapshot; the 2026 fit is new, with fit origin and label cutoff
**2025-07** (`runs/compact_weather_oracle/6m/run_metadata.json` `new_batch.fit_label_cutoff_month`).

**Compare with:** `Compact climate global historical | baseline | 6-month` on the same
evaluation dataset (same keys and truth). Primary pooled = 2022-01..2026-04; original pooled
2022-2025 is kept as `original.*`; `year_2026.*` covers January-April 2026 only (4 months,
not a full year). Regional cohorts (`region_<name>_global_model`, names from the saved report `region_name` column) are scores of this global
model on a region's areas, not Somalia-local or regional fits.

**Status:** Source scientific status: supervisor-accepted extension (task
10-09-compact-eval-2026-jan-apr, final execution evidence; original snapshot accepted in task
10-08). Undefined regional values are listed with reasons in `view/na.json`. Catalog import
checks are reported separately (`zz_prov.import_status`); no new research conclusion.

**Caveats + original:** The weather oracle uses realized future weather — a counterfactual
perfect forecast, not an operational forecast. 2026 support is partial (Jan-Apr). Weights are
an external descriptor of saved XGBoost boosters (members listed in `members.json`, bytes in the
parent `models.tar`); there is no callable prediction wrapper. Source:
`results/experiments/compact_climate_weather_oracle_eval_2026_jan_apr_v1/...`; MLflow times are
registration times, not fit times.

### 5b. Somalia calibrated augmented-label historical | calibrated_share_history | 6-month

**What:** Somalia-local model of the phase-3+ share: per forecast origin, the D (share history)
recipe and calibration selected out-of-fold, then refit. Label setting **role_augmented**:
validity-augmented copies participate in fitting, selection, calibration **and** outer
evaluation. 6-month lead; outer years 2022-2026.

**Compare with:** `Somalia calibrated observed-label historical | calibrated_share_history |
6-month` only with the warning that the augmented evaluation population and truth differ from
the observed-label setting; do not read the difference as a pure model effect.

**Status:** Slots: 2022 complete; **2023 incomplete — 696 of 2013 required final predictions
unavailable**; 2024-2025 complete; **2026 empty cohort (no source-eligible rows)**; pooled
**incomplete** (annual slot 2023 incomplete). Source task 09-30 closed with retained major/minor
audit debt and a user waiver — **not an audit pass** (evidence.md:84-103).

**Caveats + original:** Selection uses OOF pools with transitive family exclusion; raw and
final (calibrated) share scores are separate metric families (`share_phase3plus_raw.*` /
`share_phase3plus_final.*`). Members: 22 jobs' boosters (q2, q3_direct, q3_residual_delta when
selected, q4, q5) + calibration mappings. External descriptor; no prediction wrapper.

### 5c. Somalia oracle information historical | weather_oracle | 0-month (alias view)

**What:** Information set C (A + seasonal climate + realized rainfall/temperature after the
origin). At 0-month there is no future month, so C is identical to B: **this view reuses the
B 0-month fit** (no separate fit, no registered model).
**Compare with:** B 0-month gives the same predictions; compare C with B only at 3/6/12-month.
**Status / Caveats + original:** as the family; links `models:/` of
`Somalia oracle information historical | seasonal_climate | 0-month`.

### 5d. Compact climate global launch | cds_weather | 12-month

**What:** Global model fitted with realized weather anomalies (oracle inputs, labels before
2026-04) and applied with ECMWF SEAS5 (system 51) April-2026 forecast anomalies at inference.
Origin 2026-04, target 2027-04.
**Compare with:** `Compact climate global launch | baseline | 12-month` on the same 6188
inference areas; values are **prediction summaries and paired prediction differences**
(`prediction_summary.*`, `paired_difference.*`), not accuracy — no actual labels exist.
**Status:** Supervisor-accepted launch (task 10-08-compact-cds-launch).
**Caveats + original:** Training (realized, 1991-2020 reference) and inference (CDS hindcast
1993-2016 reference) weather differ by accepted design; 2027 calendar indicators all 0;
population fixed at April 2026 with the legacy country cap.

### 5e. Parent description (Origin-safe weather global historical)

Adds **Question** (does realized future weather improve global origin-safe forecasts at 3/6/12
months?) and **Accepted conclusion** quoted only from the source closure; if none is recorded:
"No accepted conclusion is recorded in the source; this catalog adds none." Plus a reading
guide (views, `members.json`, `view/evaluation_view.json`, `view/na.json`).

## 6. Metric keys

`<period_role>.<cohort>.<metric>`; roles per family:

- Somalia v1-v3: `year_2025` (lead-specific target months, e.g. 0-month 2025-04/07/09/10),
  `year_2026` (single target month 2026-04 / origin-dependent); no pooled role in source.
- Somalia v4: `pooled` (`period` tag gives actual years: 2022-2026 at 0/12-month, 2022-2025 at
  3/6-month because 2026 is empty), `year_2022..year_2026`.
- Origin-safe climate/weather, compact original: `primary` = pooled 2022-2025, `year_2022..2025`.
- Compact extension: `primary` = pooled 2022-2026 (Jan-Apr 2026), `original` = pooled 2022-2025,
  `year_2022..year_2026`.
- Launch: `prediction_summary.<scope>.(count|share)_(raw|effective)_<phase>`,
  `paired_difference.<scope>.cds_weather_minus_baseline.<...>`.

Cohorts: `all_scored`, `primary`, `wider_labeled`, `persistence_subset`/`phase_persistence_subset`,
`share_history_subset`, `region_<name>_global_model` (9 regions), `region_southern_africa_global_model`
(weather-oracle region3 files; label from `evaluate_region3_saved_predictions.py:1,279`). Contrasts: saved values only, `delta.<A>_minus_<B>.<metric>[.ci_low|.ci_high]`.
Leaves: see `metric_map.csv` (1,255 file x column x metric rows, 0 unresolved).
