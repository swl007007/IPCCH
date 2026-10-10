# IPCCH September–October model registration and MLflow maintenance

## Authorization

Grill decisions were confirmed in this conversation on 2026-10-09. The user then
instructed: “启动，用herdr技能与空闲的claude opus 5.5 1m一起实现，用supervisor(你)-executor模式，你审阅diff，checkpoint，不启动trellis audit。”
Codex supervises; the verified idle Herdr Claude Opus 5.5 (1M) implements. This
authorizes implementation and registration after the checkpoint reviews below.
No Trellis audit registration/start/close or claim of an audit pass is authorized.

## Problem and outcome

IPCCH historical and launch models trained in September–October 2026 are spread
across saved result directories. Make their existing metrics, recipes, weight
bundles and limitations browsable in the existing local MLflow service. Names,
tags and descriptions must follow Food_Crisis_Cluster's **2026-10-09 readable
naming** standard, not its superseded October 7–8 naming or stale AGENTS text.

## Confirmed requirements

1. Initial eligibility is actual fitting/retraining in September–October 2026,
   evidenced by training ledgers, execution/task records and code provenance.
   Evaluation target year, report rewrite time, copying and file mtime do not
   establish eligibility. `sources.csv` is the finite initial source allowlist.
2. Exclude the Nigeria September 18 experiment and the entire `climate2015_v1`
   family, including metrics, reports and provenance-only catalog entries. Do
   not delete local originals. Do not import older models as reference entries.
   Mixed reports must not carry these excluded results into MLflow.
3. Include Somalia oracle v1/v2/v3/v4, origin-safe climate/IDP and weather oracle,
   compact global and Somalia-local historical models (including the 2026
   extension), and compact global/Somalia-local CDS launch models.
4. Reuse the existing MLflow service/store. Create separate experiments
   `IPCCH Forecasting - detailed runs` and `IPCCH Forecasting - dashboard`;
   registered model names start with `IPCCH Forecasting`. Existing reference
   experiments/models must retain their contents and identities.
5. Use external model descriptors, associated with source detailed runs and
   downloadable complete saved recipe/weight bundles. No inference wrapper or
   `load_model/predict` promise. No retraining, new scoring, bootstrap or SHAP.
6. A registered model represents family × arm × lead. Scope and historical vs
   launch are explicit in family names. Annual fits, origins, phase regressors,
   calibration and selection components belong within the model version.
   Persistence/constant baselines have metrics but no fitted registered model.
7. Compact 2026 extensions are later versions of their existing scope-specific
   historical families. Preserve original detailed runs/model versions; latest
   dashboard rows include both pooled 2022–2025 and pooled 2022–2026 and annual
   values. January–April 2026 is a partial year, not twelve-month support.
   Mark 2022–2025 weights reused and only 2026 fits new.
8. Use English readable names, tags and descriptions, with explicit vocabulary
   mappings. Lead display is `0-month` etc.; `lead_months` tag is `00/03/06/12`,
   parameter numeric. Technical IDs/hashes/importer identities use `zz_prov.*`.
   Descriptions use What / Compare with / Status / Caveats + original; parent
   descriptions may add supported research question and accepted conclusion.
9. Preserve scientific caveats. Somalia v4 augmented 2023 6-month and its pooled
   result are incomplete; four 2026 3-/6-month slots are structurally empty.
   Existing audit debt/waivers remain visible. Import completion, source
   scientific status and task/audit lifecycle are separate concepts.
10. Historical performance, paired differences and launch prediction summaries
    remain distinct. Different truths/cohorts and global-versus-local fits are
    never silently treated as interchangeable. Undefined values have reasons.
11. Update AGENTS.md and CLAUDE.md consistently: after future training or result
    changes agents must incrementally register and verify; failures are recorded
    and resumable. Future new historical/launch models are included; excluded
    and pre-period sources stay excluded. This is an agent workflow, not a
    watcher or a trigger on arbitrary manually run training scripts.

## Acceptance

Evidence: c0/C0-report.md, c1/C1-report.md, c2/C2-report.md and the supervisor's c2/supervisor-*.json/md and browser/.

- [x] Reviewed source/model/metric inventory has an explicit inclusion decision,
      fitting-date evidence, recipe membership and expected object counts.
- [x] Names/tags/descriptions pass the explicit mappings in `naming.md`, including
      0-month, scope, label setting, oracle limitations and source status.
- [x] Every imported finite value equals its saved value and maps to a source
      path/key. NA status/reason preserved; no invented metrics or CIs.
- [x] Evaluation dataset identity binds sorted keys, truth, definition, actual
      supported period and cohort. Same name implies same digest; each historical
      metric is associated with its correct evaluation dataset.
- [x] Downloaded model bundles match original member hashes and include the
      associated schema/recipe/calibration information. Aliases/reuse do not
      inflate distinct fitting counts or conceal a missing required member.
- [x] Latest Compact rows include both pooled windows, while original versions
      and annual fit provenance remain browsable.
- [x] Initial and repeated registration, interruption recovery, source-change
      rejection and append-only new snapshots are verified. Repeating a completed
      unchanged import is a deep-verified no-op, without duplicate objects.
- [x] Existing MLflow objects/artifacts are unchanged; backup and isolated restore
      evidence exist. Source data, fitted outputs and frozen scripts are unchanged.
- [x] Browser checks cover dashboard, a detailed run, model versions and Inputs;
      descriptions, filters and 100-row payload size are checked and reported.
- [x] Maintenance CLI/docs and both agent guidance files agree; focused tests,
      offline/scratch integration and supervisor checkpoint evidence pass.

## Exclusions

No model training, model repair, rescoring, new conclusions, serving, background
watcher, autostart, external/cloud service, reference-store rebuild, modification
of Food_Crisis_Cluster, push/merge, or Trellis audit. Existing unrelated dirty
files must be preserved and excluded from task commits.

## User scope correction (2026-10-09, during C1)

The user stated that data provenance is not to be treated as a blocker ("不把数据溯源当做blocker"). Source-lineage
completeness (full descriptor provenance, historical missing fit-timestamp evidence, retained audit debt) is a
disclosure item, not a C1/C2 gate. Concrete importer defects (wrong values or dataset associations where saved data
exist, omitted support numbers, resume duplicates, non-idempotent repeats, broken backup/download) are still fixed.
Saved truth is reused directly; no expanded scientific reconstruction. Old store and source files stay preserved;
no retraining; no Trellis audit.
