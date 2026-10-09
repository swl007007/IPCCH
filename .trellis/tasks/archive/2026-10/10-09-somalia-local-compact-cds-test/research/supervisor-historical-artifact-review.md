# Independent historical artifact check

Reviewer: Codex scout `/root/som_hist_artifact_check`; read-only, frozen interpreter, no repository verifier imports or artifact writes. Main supervisor received the complete result and checked the cited report rows. Implementation HEAD: `e563b0bd2ac7fba1094c0e30f7f5d889a1c99fa4`.

Result: no concrete defects within the saved historical-artifact scope.

- Exact lookup membership: 905 SOM IDs. Independent parent intersection: 6,741 label rows, 6,739 valid-share rows and 4,933 evaluation rows; annual evaluation counts 1,129/1,217/711/1,876. Complete ordered membership/valid/evaluation ledgers match.
- Seven runs, 28 batches and 112 model hashes match batch records. Checked 64,850 ordered fitting keys, cutoffs, ages and individual weights; maximum weight error 0.
- Annual fitting counts (2022–2025): H0/H3 901/2030/3247/3958; H6 901/1504/2899/3958; H12 858/944/2554/3603. Paired arms agree. Cutoff `12*Y-max(H,1)`, origin `12*Y-H`, weight `0.5**((origin-row_ordinal)/24)`.
- Checked 34,531 prediction rows: complete ordered evaluation keys, batch/public-copy equality, source reported phase, raw shares, independently normalized cumulative targets and raw `>=0.2` classes. Maximum target error 2.220446049250313e-16.
- Checked every paired H3/H6/H12 matrix: 5,986,008 baseline-prefix feature cells, including missingness, and 80,892 target cells. All 6,741 SOM source rows are included; ordered counts 296/302/308 agree.
- Recomputed 280 annual/pooled metric cells and 160 delta cells, including 40 shared-H0 cells; values, undefined masks/reasons and denominator metadata match. Maximum metric/delta error 1.1102230246251565e-16.
- Only undefined cell: oracle H12/2023 F2, `zero f2 denominator` under the inherited precision/recall formula; 743 observed positives, one predicted positive, zero true positives. Delta reason: `oracle zero f2 denominator`.
- Pinned 257 files; size/mtime checks with rehash on change detected no content drift.

| H | Baseline F2 / R² / MAE | Oracle F2 / R² / MAE |
|---|---|---|
| 0 | 0.696911724515 / -0.064958705508 / 0.139177842593 | shared H0 |
| 3 | 0.657423971377 / -0.043704186615 / 0.137984309605 | 0.634693307252 / -0.081058606158 / 0.139129619112 |
| 6 | 0.615244627983 / -0.198829613703 / 0.146221657455 | 0.610936955765 / -0.181954951836 / 0.146179259181 |
| 12 | 0.429638854296 / -0.397702368502 / 0.161325081804 | 0.463088687201 / -0.448394245085 / 0.164780312979 |

Method: read-only inline Python with `pandas.read_csv(float_precision="round_trip")`, independent NumPy normalization and sklearn accuracy/precision/recall/F2/R²/MAE. Binary labels use reported/raw-reconstructed phase >=3; continuous metrics use normalized phase3_worse/raw phase3_pred. Python3.12.3, NumPy2.4.4, pandas3.0.3, sklearn1.8.0.

Pins: local manifest `573b0d0bb074a2de9251afacf549dfe18a30321af8bce87dfce75ac0644fe228`; parent manifest `456360536a3929e1571d96ba9f16e2f0de54bc1b20019f797bbe62c0c89732ca`; script `88aee59be33033dd85f180bd9cc4e5f317bc9c033b1a32a972fe0acf82ea8c56`; metrics `f5d9da2233edb4f34918514d2e906531964e3efebc3231e64ac85b24f3744c18`; deltas `4f2ba8b66b50e738920da69979d55e1d9b61c4a8f104015095c3df82d4d31215`.

Evidence: historical result `report/som_metrics_long.csv`, `som_oracle_minus_baseline_deltas.csv`, `som_undefined_reasons.csv`; historical human report `report.md:16,31,36,51,56,71,76`.

Excluded: model reload/replay, fitting reproduction, upstream feature rebuilding and launch/CDS. The separate supervisor full verifier covers saved-model replay; consistency is not independent retraining.
