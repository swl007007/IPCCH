# Somalia oracle audit debt and waiver record

Follow-up to archived tasks `somalia-flood-food-crisis` (completion `264a986`) and `somalia-oracle-audit-repair` (completion `ed978ba`).

## Explicit user waiver (2026-09-24)

The user explicitly waived climate-variable lineage for this experiment: "气候变量的lineage可以豁免。" (climate-variable lineage may be exempted). Together with the earlier close-audit instruction "气候特征校准来源可以给通过" this approves, as an acceptance change for AC3/AC4/AC9 and design sections 2 and 4:

- G1: V2 generation/calibration provenance is not required to be bound to the V2 file hash.
- G2: affirmative source-product evidence for retained monthly `Rainf_f_tavg_mean`/`Tair_f_tavg_mean` is not required; the implemented screen (finite and not an exact previous-month repeat; frozen/forward-filled months excluded) is the accepted oracle-weather rule.

These remain disclosed limitations of the results, not verified provenance claims. They are no longer acceptance gaps.

## Minor debt to fix

- D1 (repair close-audit A02; spot re-audit A01): replay must record required-contrast coverage before the single-area early exit, and must check prediction coverage for the published wider-labeled cohort (arms A/B).
- D2 (repair close-audit A03; spot re-audit A02): history QC must require a finite positive total, rejecting overflowed sums of finite components.
- D3 (repair close-audit A01): the repair evidence reported 23 changed metric rows; 24 changed when q3 R-squared is included. Correct the record.

## Acceptance

Focused regressions for D1/D2 pass; the full-run artifacts are unaffected (D2 cannot occur on the real data; D1 is replay-only), verified by replay on the saved v1 outputs and by an unchanged `--prepare-only` ledger/feature hash comparison.
