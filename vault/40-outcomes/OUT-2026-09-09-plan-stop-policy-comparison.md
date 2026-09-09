---
id: OUT-2026-09-09-plan-stop-policy-comparison
step: plan
records: [REQ-EXP-017]
commit: null
---

## What was done

One module, one replay extension. 12 tasks.

## What was decided

- **An ablation transforms the path, not the policy.** A capability the engine
  does not have cannot veto and cannot supply a level, so removing it is exactly
  removing what it contributed; a branch inside the policy would be a second
  policy that only looked like the first.
- **The walk is recorded by the replay** ([[ADR-052]]), because it is the only
  place holding the path and the position's side together.
- **Three capabilities are vetoes rather than levels.** The order-flow view, the
  turning-point forecast and the cross-venue context say whether tightening is
  permitted; none of them produces a price.

## What is still open

- Nothing from this step.
