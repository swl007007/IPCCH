# Supervisor browser and download checks

Inspected live MLflow 3.17.0 in Model training mode after authorized import.

- Detailed historical run: readable family/arm/6-month name, 296 inputs,
  reused 2022-2025 fits and new 2026 cutoff 2025-07; original/primary/year roles
  visible, with `period.year_2026 = 2026-01..2026-04`.
- Detailed launch run: prediction-summary wording and separate inference dataset;
  readable tags precede zz_prov tags. No performance claim for those predictions.
- Registry version 2: source run and External LoggedModel links resolve; description
  identifies 4 new + 16 reused boosters and external-descriptor limitations.
- Datasets drawer: pooled original/extended, annual/regional, no-row and training
  pool descriptors displayed. Both pooled windows and Jan-Apr 2026 visible.
- Dashboard: 174 rows created/verified by executor; browser family filter shows
  the eight Compact global historical views, including H0 alias views.
- First 100 active dashboard rows: HTTP200, 2,946,272 bytes (2.810 MiB),
  measured API response time 0.412 s; this is not browser page-load timing.
- Actual HTTP downloads of original/extension parent bundles: 581,836,800 bytes;
  all 36 members referenced by Compact global baseline6m version2 matched SHA256.
  See supervisor-download.json. This is registration verification, not model replay.

PNG screenshots and browser text/URL/error snapshots are in browser/.
Native MLflow requires Model training mode and Columns selection for chosen metrics.
The detailed-description inline angle-bracket metric template renders as dots in
MLflow Markdown; actual metric names, dashboard guide and README remain visible.
This minor display limitation does not affect imported values or comparisons.

No source-lineage investigation or Trellis audit was performed for these checks.
