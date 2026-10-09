# Independent launch artifact check

Reviewer: Codex scout `/root/som_launch_artifact_check`; read-only, frozen interpreter, no artifact writes or repository verifier calls. Main supervisor received the complete result and inspected all seven PNGs separately.

Result: no saved launch numeric, key, hash or actual-codebook alignment differences found.

| H / target | Baseline P3+ share | CDS P3+ share | Baseline effective P3+ people | CDS effective P3+ people | Delta pp |
|---|---:|---:|---:|---:|---:|
| 0 / 2026-04 | 0.2782543003049251 | shared | 5195564.865714877 | shared | 0 |
| 6 / 2026-10 | 0.27209640413708713 | 0.2771690595386566 | 5080584.61584532 | 5175301.247902368 | 0.5072655401569481 |
| 12 / 2027-04 | 0.25036198011285565 | 0.26492619382855165 | 4674759.4059093 | 4946702.434265414 | 1.4564213715695995 |

- Independent raw-score difference/clip/normalize reconstruction of every phase1–5/P3+/P4+ area share and raw/effective count, SOM weighted total/share, and all paired differences: 110 array comparisons; maximum share error 6.106226635438361e-16, count error 1.30385160446167e-08. Share atol1e-12/rtol0; count atol1e-6/rtol1e-12.
- All 5×904 raw classifications match the highest cumulative phase with unrounded score >=0.2. Fixed April population: raw 62,695,007; factor 0.29782279233177217; effective 18,672,002.05. Equal paired denominators; all H0 differences exactly zero.
- Exact membership 905; launch 904 excludes only3146. All five fitting sets retain3146 and equal independently selected complete 5,835 valid SOM pre-April rows. Normalized target error0. All ordered fitting keys/targets/weights/fit_ord, ages and half-life24 weights match; all five sets agree.
- Actual local inference equals each explicit parent SOM projection; matrix order equals the fitted schema. CDS H6/H12 baseline prefixes match.
- 65 explicit source/input/report/geometry/map/codebook/summary SHA256 checks match. Run metadata manifest pins and local-code pin match.
- Exactly seven metadata entries/CSVs/PNGs: five categorical CSVs each904 rows, comparison5424, difference1808. All keyed map values match raw classes or repaired shares/deltas as declared. Actual shapefile admin_code supplies904 unique nonempty geometry joins.
- Launch English codebook has308 ordered unique features; five fitted-schema inclusion/position lists match: baseline296, CDS308. Weather descriptions distinguish observed1991–2020/crop-area training and System51 hindcast1993–2016/containing-cell inference; preserve unresolved upstream spatial documentation and no spatial-match claim.

Evidence: local launch `population/som_population_summary.csv:2-7`, `report_outputs.json:28-142`, manifest explicit run entries, fitted `feature_schema.json`, and launch report `model_run_codebook_en.csv:298-309`.

Command environment: `PYTHONDONTWRITEBYTECODE=1 /home/swl007007/.venvs/ipcch-geo/bin/python`, read-only inline Python. No repository files changed.

Excluded: fitting reproduction, model reload, PNG visual inspection and upstream weather/reference/spatial certification. Main supervisor performs visual checks and a fresh complete saved-model verifier separately. These launch levels cannot establish accuracy.
