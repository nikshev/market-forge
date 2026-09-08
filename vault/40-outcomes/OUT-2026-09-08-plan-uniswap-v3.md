---
id: OUT-2026-09-08-plan-uniswap-v3
step: plan
records: [REQ-WP-015]
commit: null
---

## What was done

Four modules under `src/channelflow/dex/`, three test files, 9 tasks.

## What was decided

- **The amount deltas live in `math.py`, not `depth.py`**, because they are
  pool arithmetic rather than traversal logic — and separating them is what
  lets the depth test check the walk against the closed form without importing
  the walk.
- **`price_from_tick` goes through `exp(tick * ln(1.0001))`.** Raising a
  `Decimal` to a large integer power is exact but grows the intermediate to
  thousands of digits, and the exactness buys nothing a tick's own granularity
  has not already lost.
- **A swap's own reported state is authoritative.** The log says where it left
  the pool; trusting it over our arithmetic keeps the reconstruction anchored
  to the chain rather than drifting into a parallel simulation.

## What is still open

- Nothing from this step.
