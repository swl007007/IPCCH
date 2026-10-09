# Journal - William Shi (Part 1)

> AI development session journal
> Started: 2026-09-24

---



## Session 1: Wrap Somalia experiment branch and verify main integration
<!-- trellis-session: v=2 fp=269825631fbfb446 -->

**Date**: 2026-10-01
**Task**: Wrap Somalia experiment branch and verify main integration
**Branch**: `feat/somalia-oracle-experiment`

### Summary

Verified 76 Somalia unit tests and v4 smoke/replay; 96-row reporting output reproduced; 12 known failures reproduced identically on main and branch; retain accepted v4 audit debt. Feature pushed, ready for fast-forward integration.

### Main Changes

## Scope and integration pins

- User authorized wrapping `feat/somalia-oracle-experiment`, pushing it, checking it and merging into `main`.
- Checked experiment HEAD: `06f1a91803ab4cb304ed15999e07eb5fcbe79eeb`; main baseline: `4a85488dadcbb26c478d415387ac30e571dca26d`.
- Main is an ancestor; integration can fast-forward without rewriting experiment history. The branch contains Somalia v1-v4 and the committed Trellis scaffold.
- V4 is already completed and archived. Its documented user-authorized native archive/waiver and round-2 audit debt remain unchanged. No fresh scientific audit pass is claimed and no controller lifecycle action was repeated.
- No product changes followed the pinned round-2 audit SHA `6fde76f36a2d3daf447f2929e0863cc7d54421fa` before this wrap-up. The only added product artifact now is the existing reporting script committed as `2f31c17`.
- Existing non-Somalia product source, dependency declaration and tests are byte-identical to main. No tracked CI workflow exists.

## Current verification

- Frozen interpreter: `/home/swl007007/.venvs/ipcch-geo/bin/python` (Python 3.12.3; NumPy 2.4.4; pandas 3.0.3; scikit-learn 1.8.0; XGBoost 3.2.0).
- Four Somalia unit files (`oracle`, `q3opt`, `augment`, `v4`): **76 passed**, 6 warnings, 6.19 s.
- `tests/smoke/test_somalia_v4_pipeline.py`: **1 passed**, 297.80 s, including its independent replay. Synthetic fixtures replace real monthly feature scope/parity, so this check does not claim new production-data validation.
- Ran `scripts/reporting/somalia_oracle_wrapup.py --out <temporary CSV>`: **96 rows**, unique `(setting,cohort,view,period)` keys, exactly matching the existing saved CSV. This H0 v2/v3 report explicitly uses descriptive n-weighted annual AUC/R2 averages, not v4 pooled estimates.
- Ran the 12 archived failing test nodes in isolated Git archives of both main and checked HEAD: **12 failures on each**, identical node outcomes and normalized failure messages. These are existing alert-risk-map/launch tests, not new branch regressions. The metadata-output failure is an old `OutputLayout` fixture missing nine grouped-SHAP arguments.
- Isolated baseline logs and XML: `/tmp/ipcch-merge-baseline-v5tlkl2s/{main,head}/`; local summary `summary.json`. The archived original full-suite result remains under the v4 task evidence.
- Precommit staged whitespace checks passed. Whole-branch whitespace check reports only existing scaffold/journal EOF blanks and two Markdown hard-break trailing spaces; those managed files were not mechanically rewritten.
- GitNexus staged checks show only intended files; whole-branch compare reports broad critical scope (513 indexed symbols / 44 flows). Actual Git scope and bounded tests provide the current verification; graph indexing is not a scientific acceptance result.

## Publication

- Reporting script commit `2f31c17` and all prior experiment commits have been pushed to `origin/feat/somalia-oracle-experiment`.
- This journal records the completed pre-merge checks. Next operation: push the journal commit, fast-forward main, push main, and verify remote refs plus a clean working tree.
- No branch deletion, force-push, real model rerun, new task or changes to accepted audit findings are part of this wrap-up.


### Git Commits

| Hash | Message |
|------|---------|
| `2f31c17` | feat(reporting): add Somalia oracle wrap-up table |

### Status

[OK] **Completed**


## Session 2: Global model rerun with 2015-2026 climate features
<!-- trellis-session: v=2 fp=9c2bf0b46fe5c13b -->

**Date**: 2026-10-05
**Task**: Global model rerun with 2015-2026 climate features
**Branch**: `feat/global-climate2015-features`

### Summary

Forked the upstream deep-feature climate recipe onto the 14 ensemble-mean variables of the 2015-2026 climate release plus last-two completed growing seasons, replacing FLDAS/MODIS climate features; fidelity gate 78/80 asof12 columns; 11 global runs (baseline rerun, masked, unmasked) for 0m/3m/6m/12m, test years 2022-2025. Masked mean deltas: sensitivity 3+ +0.05/+0.03/+0.01/+0.03, F2 +0.04/+0.02/+0.01/+0.02, gains concentrated in 2022; 0m 2025 R2 falls 0.351->0.183 (Yemen, East/Southern Africa). Found upstream scope-block NaN gap (59.7%/46.1% of 2025 rows at 0m/3m) and stale May 3m/6m baseline (539 vs 540 features).

### Git Commits

| Hash | Message |
|------|---------|
| `585640b` | feat(features): global model rerun with 2015-2026 climate features |

### Status

[OK] **Completed**


## Session 3: Origin-safe global climate + safe IPC history + national IDP benchmark
<!-- trellis-session: v=2 fp=9cfdee282c474cc7 -->

**Date**: 2026-10-06
**Task**: Origin-safe global climate + safe IPC history + national IDP benchmark
**Branch**: `feat/global-origin-safe-climate-idp`

### Summary

Repaired forecast-origin leakage in global IPCCH (safe latest-three history <= min(O,T-1), national DTM IDP <= O, unmasked climate2015, frozen 28,205-key cohort), annual origin-safe fits for H=0/3/6/12 x 3 arms; verified; close audit round 1 major findings A01-A04 fixed without rerun.

### Main Changes

- New --protocol origin-safe in the global CLI (one fit per test year, labels <= Jan(Y)-max(H,1)); global annual protocol blocked
- Input builder with recipe-verified inherited features, source-support perturbation and saved-dataset timing audit (0 leaks, 9 cutoffs x 4 horizons)
- Monthly refits dropped after re-grill (10-50 eval rows per month); monthly outputs deleted
- Results: safe history improves exact/phase3+ accuracy and R2 at every horizon; national IDP shows no consistent gain (single seed)

### Git Commits

| Hash | Message |
|------|---------|
| `c57ab03` | feat(global): origin-safe monthly protocol with safe IPC history and national IDP |
| `7cffb5a` | fix(metrics): keep the pooled label in compute_metrics; strengthen verifier |
| `98fc6cd` | refactor(global): annual origin-safe blocks instead of monthly refits |
| `5d76abd` | docs(task): origin-safe climate/IDP evidence and verified results |
| `302728d` | fix(global): address close-audit findings A01-A04 for origin-safe runs |
| `6cec4d3` | chore(task): archive 10-06-global-origin-safe-climate-idp |

### Testing

- [OK] 45 selected tests pass in ~/.venvs/ipcch-geo; independent verifier passed (288 artifacts, 96 model reloads, sklearn replay)

### Status

[OK] **Completed**

### Next Steps

- Controller gate from close audit round 1 remains open (no re-audit by user decision)
- Optional: refresh GitNexus index


## Session 4: Compact climate and raw oracle experiments completed
<!-- trellis-session: v=2 fp=032534db22cdc0de -->

**Date**: 2026-10-08
**Task**: Compact climate and raw oracle experiments completed
**Branch**: `task/compact-climate-weather-oracle`

### Summary

Completed the approved compact feature suite with verified Claude Opus5.5 1M in Herdr. Seven runs,28 annual batches,112 models; exact model replay,2800 metric cells and372800 sampled input cells verified. Actual296/302/308 input schemas,308-row English codebook,global and all-region annual/pooled metrics and deltas delivered. Supervisor rehashed203 artifacts and confirmed740 legacy files unchanged. Rollback selections and post-archive dry-run passed. No bootstrap,B6,tuning,SHAP,regional fitting,extra audit enrollment or push.

### Git Commits

| Hash | Message |
|------|---------|
| `928d080` | docs: approve compact climate features and oracle comparison |
| `40060dd` | feat: add frozen compact climate and raw oracle suite |
| `10dfc23` | docs: record compact oracle experiment acceptance |

### Status

[OK] **Completed**


## Session 5: Compact CDS launch accepted
<!-- trellis-session: v=2 fp=9cf9597527b8686c -->

**Date**: 2026-10-09
**Task**: Compact CDS launch accepted
**Branch**: `task/compact-climate-weather-oracle`

### Summary

Completed the approved five-run April2026-origin compact CDS launch:20 model replays,6188 areas, population summaries, seven maps and actual-input codebook; A1-A9 accepted.

### Main Changes

- Saved versioned baseline H0/H6/H12 and oracle-trained/CDS-inferred H6/H12 models; shared H0, exact296/308 columns, fixed April population and old cap.

### Git Commits

| Hash | Message |
|------|---------|
| `58dd9cd` | feat: add compact CDS launch with verified real inputs |
| `414ae4c` | docs: accept compact CDS launch outputs and provenance |

### Testing

- [OK] 20 boosters independently replayed with max error0;1446597 population cells checked;107 inventory hashes and488 old-artifact hashes verified; all7 maps visually/keyed checked.

### Status

[OK] **Completed**

### Next Steps

- No required scientific work remains. Preserve accepted reference/October endpoint/TP/unseen-year limitations and legacy rollback paths.
