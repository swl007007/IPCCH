# Complete schema context

The approved expected schema is on disk in this task's `expected_feature_contract.csv` and `expected_feature_contract_metadata.json`. The JSON is about98KB, above the native injection per-file limit; do not inject a truncated copy or infer a schema from its prefix.

After loading the injected PRD/design/plan, read the complete metadata with a local JSON parser and the CSV with `csv.DictReader` (UTF-8 BOM supported). `features_by_run` is the exact ordered list for each of seven runs. CSV `expected_model_positions` supplies 1-based order and `formula`/`missing_semantics` describe each literal. Neither file is fitting evidence.

Expected union:308 unique columns. Baseline:296 at H0/H3/H6/H12. Oracle:302 at H3 and308 at H6/H12. Order: static29,ordinary120,z56,stress28,season29,calendar27,history5,IDP2,then raw oracle if present. H0 is shared, with no separate oracle run.

Validate contract/spec hashes from the full metadata and execution approval. Implementation must match the whole schema, never an injected JSON prefix. Preserve the two existing legacy namespaces and this frozen compact version for rollback.
