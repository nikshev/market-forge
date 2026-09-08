# Implementation Plan: Uniswap v3 adapter

**Branch**: `wp-015-uniswap-v3` | **Date**: 2026-09-08 | **Spec**: [spec.md](./spec.md)

## Summary

Four modules under `src/channelflow/dex/`: the price math, the pool's events,
the state reconstruction, and PRD §18.7.1's depth curve.

## Technical Context

**Language/Version**: Python 3.12, `mypy --strict`.

**Primary Dependencies**: none new. `Decimal` at the project's configured
precision (ADR-006).

**Storage**: none.

**Testing**: pytest, pure. The single-range depth case is checked against the
closed form computed independently.

**Target Platform**: `src/channelflow/dex/`.

**Constraints**: FR-005 ([[ADR-035]]), FR-013 ([[ADR-036]]), FR-016 (no clock,
no socket).

**Scale/Scope**: 4 modules, 42 tests.

## Constitution Check

- **I (no look-ahead)** — the adapter reads what REQ-WP-014's ledger says was
  knowable; availability is that layer's rule and is not re-decided here.
- **III (history is immutable)** — §18.7.2's divergence raises an incident and
  never patches, the same rule [[ADR-033]] applies to reorgs.
- **VII (live and replay are the same code)** — the reconstruction is a pure
  function of an ordered event list, so a replay is the same call.
- **XII (correctness precedes performance)** — the depth walk is linear in
  initialized ticks and the math is `Decimal`. A pool with thousands of
  initialized ticks would want an indexed traversal; that is an optimisation
  to make when a profile asks.
- **XIV** — traces to REQ-WP-015.

**Gate result: PASS.**

## Project Structure

```text
src/channelflow/dex/
├── __init__.py
├── math.py    # sqrtPriceX96, ticks, the two amount deltas
├── events.py  # Swap, Mint/Burn, Collect, and canonical position
├── pool.py    # state reconstruction, §18.7.2's integrity check
└── depth.py   # §18.7.1's traversal and curve

tests/unit/dex/{test_math.py,test_pool.py,test_depth.py}
```

**Structure Decision**: the amount deltas live in `math.py` rather than in
`depth.py` because they are pool arithmetic rather than traversal logic — and
keeping them separate is what lets the depth test check the walk against the
closed form without importing the walk.

## Approach

**`price_from_tick` goes through `exp(tick * ln(1.0001))`.** Raising a `Decimal`
to a large integer power is exact but grows the intermediate to thousands of
digits, and the exactness buys nothing a tick's own granularity has not already
lost.

**The rebuild sorts what it is given**, so arrival order cannot change the
answer — the same reasoning REQ-WP-006's fitter uses for its own window.

**A swap's own reported state is authoritative.** The log says where it left the
pool, and trusting it over our arithmetic is what keeps the reconstruction
anchored to the chain rather than drifting into a parallel simulation.

## Complexity Tracking

> No violations.
