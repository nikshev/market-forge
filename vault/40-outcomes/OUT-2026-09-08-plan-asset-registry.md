---
id: OUT-2026-09-08-plan-asset-registry
step: plan
records: [REQ-ASSET-001]
commit: null
---

## What was done

Two modules under `src/channelflow/assets/`, one test file, 10 tasks.

## What was decided

- **Invariants split by who can see them.** A native marker and a contract
  address are mutually exclusive whatever registry holds the representation, so
  that lives in the model; a dangling canonical asset is only visible to the
  registry, so it lives there.
- **The fixture is PRD §18.13's own ETH example**, so the test that matters
  most is a direct reading of the section rather than an invention.
- **The wrapper walk is bounded as well as cycle-checked.** With only the cycle
  check, removing it makes the traversal run for ever, and no answer is a
  weaker signal than a wrong one.

## What is still open

- Nothing from this step.
