# Read-only final publication consistency check

A default scout checked only the two new result/report namespaces and their explicit references after both verifier actions returned 0. No edits, task changes, old-data/model reads, training or Trellis audit were performed.

| checked fact | global | SOM local |
|---|---:|---:|
| final inventory records | 86 | 84 |
| result-root files | 84 | 82 |
| report-root files | 4 | 4 |
| missing/hash/bytes/coverage discrepancies | 0 | 0 |
| new 2026 batches / models | 7 / 28 | 7 / 28 |
| complete run lineage records | 7 | 7 |
| durable approved-spec copies, exact manifest hashes/bytes | 6 | 6 |

Inventories cover every new file except their own inventory and verification summary. Every inventory path is inside its selected version's result/report roots. No other new batch year exists. All run records distinguish original 2022-2025 fingerprints from the separate extension 2026 fingerprint. There is no oracle H0 model.

Both Markdown reports, comparison metadata and all 308 actual-input codebook records per scope have final status `verified`. Current report, codebook and comparison metadata hashes match both comparison metadata and each verifier's final reporting records. Both scopes report 7 new batches, 28 new models replayed, 140 schemas inspected and 28 original batches checked; prediction replay error is 0.0. Global cells are 3920 metrics / 1680 deltas / 2800 original parity; SOM cells are 392 / 224 / 280.

Evidence lives in each exact version's `verification/artifact_inventory.csv`, `verification/verification_summary.json`, `report/comparison_metadata.json`, `runs/<arm>/<H>m/run_metadata.json`, `inputs/extension_manifest.json` and `inputs/approved_spec/`, with Markdown/codebooks in `reports/<version>/`. The coordinator independently spot-checked current final reporting hashes/status and six 2026 absolute accuracy pairs after receiving this extraction.
