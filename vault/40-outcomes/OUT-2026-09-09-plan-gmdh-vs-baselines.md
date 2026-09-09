---
id: OUT-2026-09-09-plan-gmdh-vs-baselines
step: plan
records: [REQ-EXP-008]
commit: null
---

## What was done

Three modules and a change to the comparison report. 8 tasks.

## What was decided

- **The report declares its own regularization strengths.** The model refuses to
  default them; a report still has to run with some pair, and saying so in the
  report's module keeps ADR-029's objection intact.
- **Depth two by default**, the shallowest that holds an interaction.
- **A minimum leaf size**, because a tree that splits to single rows memorizes
  its fold and then flatters whatever it is compared against.

## What is still open

- Nothing from this step.
