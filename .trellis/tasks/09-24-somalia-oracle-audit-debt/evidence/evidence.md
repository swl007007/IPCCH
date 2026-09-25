# Evidence — somalia-oracle-audit-debt

Evidence Status: Ready. Validation Status: Executed.

## Waiver record

User statement in the executor session on 2026-09-24: "气候变量的lineage可以豁免。" (climate-variable lineage may be exempted). This resolves spot-audit gaps G1 (V2 calibration provenance) and G2 (affirmative realized-weather provenance) as an approved acceptance change (see `prd.md`). Both remain disclosed limitations in `reports/somalia_oracle/v1/summary.md`.

## Debt fixes

| Item | Source | Fix | Check |
|---|---|---|---|
| D1 | repair close-audit A02; spot re-audit A01 | replay checks required contrasts before the single-area bootstrap exit, and checks A/B prediction coverage on the wider labeled cohort | `test_replay_flags_missing_contrast_and_wider_prediction` |
| D2 | repair close-audit A03; spot re-audit A02 | history QC requires a finite positive total (`nonpositive_or_nonfinite_sum`) | `test_history_qc_rejects_overflowing_total` |
| D3 | repair close-audit A01 | Correction: the repair changed 24 metric rows when q3 R-squared is included (23 had F2/accuracy changes). | this record |

## Validation

- `PYTHONPATH=src ~/.venvs/ipcch-geo/bin/python -m pytest tests/unit/test_somalia_oracle.py -q` → 25 passed.
- Replay on the saved v1 outputs (produced at `f576e69`) → 646/646 checks passed (16 new coverage checks).
- `--prepare-only` with the fixed code: cohort ledger and all four feature matrices byte-identical to the v1 run; the label ledger differs only in the renamed invalid-reason text for rows already invalid (no validity change). No refit is needed; published predictions and metrics stand.
