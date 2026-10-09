# Reading the complete expected-input contract

The CSV is larger than Trellis context-injection limits. Any injected excerpt is descriptive context only and must never supply the allowlist. Read the complete `expected_feature_contract.csv` with `csv.DictReader(..., encoding="utf-8-sig")` or pandas with `encoding="utf-8-sig"`. Read `expected_feature_contract_metadata.json` and `expected_run_index.csv` explicitly from this task directory; copy approved bytes into the versioned input root before consumption so later task archival does not break runtime paths.

Assert exactly308 unique literal predictors and five run projections: compact_baseline/0m,/6m,/12m each296; compact_cds_weather/6m,/12m each308. `expected_model_positions` is a JSON mapping of run_id to1-based position; sort by these positions and require contiguous positions and exact equality to `features_by_run` and the current compact manifest arm at matching H. Schema SHA256 is UTF8 newline-joined names without a final newline. A true membership field has expanded_count1 and precisely one literal model column. All weather prefixes equal the baseline; no weather H0 or H3 projection is permitted.

CSV/metadata rows are expected_not_fitted. Actual membership/codebook must be checked against all20 saved fitted booster feature lists and replayed predictions. Retain separate training versus inference definitions: realized weather in fitting, CDS forecast cube in launch inference. Missing forecast values stop weather acceptance/fitting; nonweather source-native NA stays NA. Preserve all metadata reference/spatial limitations.

Use programmatic per-run summaries and hashes for checkpoints; avoid a tool dump that silently truncates hundreds of rows.
