# Approval record

Date: 2026-10-09.

## Requirements convergence: approved

The user selected A for each question in sequence:

1. Fixed annual fit; no 2026 fitting labels.
2. All existing valid January-April labels, with explicit monthly support.
3. Expanded pooled 2022-2026 plus preserved/recomputed pooled 2022-2025.
4. Verify/reuse 2022-2025, fit only 2026, publish a new version.
5. Preserve all historical horizons 0/3/6/12.

The final convergence question stated both model scopes, baseline/oracle, all four horizons, separate2026 January-April,56 new regressors, old-year reuse, two pooled ranges, annual/regional absolute values/differences/reports/codebook, and unchanged launch/CDS. The user's exact answer was: **A: confirm convergence, persist the spec as stated** (`A：确认收敛，按此落盘 spec（推荐）`).

## Written implementation plan: approved

The three formal documents and expected-run contract were written after convergence, presented as concrete file links, and checked for document/reference/count consistency. A subsequent question explicitly requested approval of the written spec and execution through Herdr Claude Opus5.5(1M), with Codex supervision and no Trellis audit. The user's exact answer was **A: approve spec, start execution** (`A：批准 spec，开始执行（推荐）`). This separately authorizes the bounded implementation, tests,14annualbatches/56newmodels and reports/verification in `implement.md`. No product code or extension models existed at approval.

## Executor and audit policy

Carry forward the explicit instruction to use Herdr Claude Opus5.5 with1M context for execution, with Codex supervising and **no Trellis audit**. Actual live executor identity/model must be verified before dispatch. No historical pane or session is binding for this new task yet.
