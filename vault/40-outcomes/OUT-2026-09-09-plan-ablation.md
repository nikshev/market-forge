---
id: OUT-2026-09-09-plan-ablation
step: plan
records: [REQ-US-006]
commit: null
---

## What was done

One module in a new `research` package, 10 tasks.

## What was decided

- **A new package rather than a module under `models`.** `models` holds
  estimators and their comparison report; an ablation is a research procedure
  over a dataset, and EXP-004 and EXP-015 belong beside it rather than inside
  the estimator package.
- **The missing-family check runs before the duplicate check**, so the reason
  names the cause. Ordered the other way, "channel + DEX" reads as a repeat of
  "channel only" and the absent family disappears from the report.
- **`rank_arms` is public**, because two arms over different features almost
  never tie and the tie-break would otherwise go untested forever.

## What is still open

- Nothing from this step.
