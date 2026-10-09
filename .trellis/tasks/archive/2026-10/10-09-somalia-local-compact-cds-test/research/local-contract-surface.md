# Local fitting and verification surface

Read-only current-source scout2026-10-09; main read exact loader/batch and launch-fit spans. No implementation/tests/training.

## Fitting primitives

- `scripts/modeling/run_deep_feature_weight_decay_forecasting.py:984-1046`, load_compact_inputs: fullschema/hash/cohort/history/IDP/season/oracle/runtime gates; aligneddata/targets/share_valid/eval_key/ords/features/parent fingerprint.
- `:1078-1149`, run_origin_batch: suppliedshare_valid determinesfit, suppliedeval_key determineseval. Mask BOTH withSOM; replace globalfingerprint. Onlyevalmask stillfitsglobally.
- `:884-885`, retain existing global country rejection; oldannualcountry protocol is different.
- `src/ipcch/compact_launch.py:674-745`, fit_run: explicitfit_selection/inference, no6188gate inside primitive. New localset gates required. Existing12-row fixture `tests/unit/test_compact_launch.py:133-156` supportsprimitive.
- `compact_launch.py:615-643`, validate_inputs: validatefullparent first; globalcohort/cap gates are notlocal acceptance.
- `:646-654`, fingerprint bindsmanifest/dataset/selection/inference/contracts/config/runtime/frozenfitcode. Addlocalcode/spec/membership to hashedlocalmanifest before fitting.

## Frozen code and unsuitable global assumptions

- `src/ipcch/compact_features.py:82-85,479-508`: frozeninputhelpers andfit fingerprints includeoriginalrunner. Editingthem invalidatesoldglobal replay; preservebytes.
- LaunchFIT_CODE `compact_launch.py:605` addslaunch_nowcasting/compact_launch/oldCLI; builder`:535-537` checksparentcode. Preserveunchanged.
- Historicalverifier globalcohort/counts/globalfitkey equality `verify_compact_climate_weather_oracle.py:503-521`, inventories`:578,597`; globalreporttext`:355-359`. Local inventorysizes stay7/28/112 butkeys/scope differ.
- Launchglobalgates`:50,235,636-642,764,924,944,970,1128,1288-1307`; cap`:462-463` needsallreferencecountries; verify`:1166-1184,1202` comparesglobalfit/population/regions. Reusecomponents, notglobalacceptanceassumptions.

## Report/replay reuse

- Eight metrics `src/ipcch/origin_safe.py:387-424`; independent sklearnreplay `scripts/postprocessing/verify_origin_safe_climate_idp.py:62-77`.
- `scripts/postprocessing/verify_origin_safe_weather_oracle.py:116`, verify_run acceptsdata/labels/valid/evalkeys/fouryears;`:220-239` metricreplay. Supplylocalidentities ratherthan assumedglobaldriver.
- `src/ipcch/regional_point_metrics.py:47`, align_pair requireskeys/truths;`:85` undefineddeltas. Changeoutputscope labelinglocally, notglobalhelper.
- Launchmapping_frame`:427`,repaired_shares`:475`,aggregate`:810`,paired_differences`:831`; originalglobalcap auditthenentireSOMprojection preservesfactor.
- `launch_visualizations.py:62,121`, join_for_two_panel/plot_predicted_only allowSOMscope; fullwrite_maps hasglobalgates. Preservekeyedmapvalues/joins independently.

## Tests and inventories

- Historicalbatch predictions,fitkeys/weights,fourUBJs,batch_record; runlevelannualpredictions/metrics/metadata at runner`:1197-1207`.
- Launchinventory `compact_launch.py:603-605,729-745` plusartifact_record.
- Newfocusedchecks: completefit/eval/inferenceSOMsets, cutoffs/weights/pairedtargets/schema, nonSOMexclusion, membershipchanged-resume rejection, globalcompatibility, read-onlyvalidate. Existingpopulation/delta/zero tests `tests/unit/test_compact_launch.py:53-73`; assembly/version/fingerprint tests `tests/smoke/test_origin_safe_cli.py:137-152,374-388,403-438`.
