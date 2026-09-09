---
id: OUT-2026-09-09-plan-channel-baselines
step: plan
records: [REQ-CHAN-001]
commit: null
---

## What was done

Four modules — three estimators and the window rule extracted from baseline A —
and 12 tasks.

## What was decided

- **The window rule moved out before the second baseline existed.** Three copies
  of "finalized, at or before `as_of`, sorted, at least `lookback`" would agree
  today and drift later, and it is the rule Principle I rests on.
- **No new dependency for two fits.** Huber is IRLS in a dozen lines; the
  quantile fit is exact by enumeration.
- **The backward-pass check is over code patterns**, not over the word
  "smoother" — which the module's own docstring uses to explain what it refuses
  to be.

## What is still open

- Nothing from this step.
