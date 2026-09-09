---
id: OUT-2026-09-09-plan-order-flow-exhaustion
step: plan
records: [REQ-EXP-014]
commit: null
---

## What was done

One module, two arms. 8 tasks.

## What was decided

- **`trailing_calls` is public.** It carries the property the predictive arm
  rests on, and a property that cannot be tested directly is one nothing
  enforces.
- **A call is strictly above the trailing quantile.** An order-flow signal sits
  at one value most of the time and the quantile of such a series is that value.
- **The four research judgements are required arguments** — window, horizon,
  control gap, call quantile — plus the reading rule's two floors.

## What is still open

- Nothing from this step.
