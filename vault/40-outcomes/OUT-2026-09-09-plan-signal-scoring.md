---
id: OUT-2026-09-09-plan-signal-scoring
step: plan
records: [REQ-SCORE-001]
commit: null
---

## What was done

Four modules under `src/channelflow/scoring/`, three test files, 11 tasks.

## What was decided

- **The caps live with the groups.** A contribution validates itself at
  construction, so one that cannot exist out of range cannot reach the summation
  out of range either — and the summation is then plain arithmetic with nothing
  left to check.
- **`GroupContribution` is a dataclass, not a Pydantic model**, so
  `ContributionOutOfRange` reaches the caller as itself rather than wrapped in a
  validation error, where a scoring mistake would be handled as a parsing one.
- **Threshold specificity is a fixed list, not a search** over the override keys.
  With overrides at more than one level, taking the first match found would make
  the answer depend on dictionary order.

## What is still open

- Nothing from this step.
