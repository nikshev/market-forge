---
id: OUT-2026-10-04-tasks-trade-flow-features
step: tasks
records: [REQ-WP-088]
commit: null
---

## What was done

21 tasks, tests first. The specification was rewritten before the tasks (see the spec note: the bars already store the
aggressor split), and the tasks follow the rewrite. `speckit-analyze` ran over the first version and found two medium
issues (the acceleration at an epoch's start; a replay over minutes already written live); both were about a design that
was then replaced, and both vanish with it: the function is pure over bars, so there is no live/replay divergence, and
the first bar of a run has no acceleration (absent, in the data model, the spec and T002).

## What the second pass over the new artifacts found, and how it was resolved

- The spec said the id checks apply to "venues whose ids are sequential" without saying which. **Measured**: Binance,
  yes; Bybit not numeric; OKX numeric but not sequential. So a `sequential_trade_ids` registry flag (T008, T012), true
  for Binance only; SC-005 now records the measurement instead of asking for one.
- The pane entry is renamed `cvd` -> `cvd_base`, which changes one expected line in the existing `panes.test.ts`
  (T010, T016); listed so it is not a surprise.
- Deploy touches `worker` and `api` only, after checking for a running time-boxed measurement (the project's own rule).

## What is still open

- The notional version (the quote split stored in the bar) is [[ADR-068]]'s way back, not this work.
