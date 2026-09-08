# Implementation Plan: Derivatives feature engine

**Branch**: `wp-013-derivatives` | **Date**: 2026-09-08 | **Spec**: [spec.md](./spec.md)

## Summary

Four modules under `src/channelflow/derivatives/`: the state join, funding,
open interest and basis, and liquidations. Every feature registered in the
registry REQ-WP-011 built.

## Technical Context

**Language/Version**: Python 3.12, `mypy --strict`.

**Primary Dependencies**: `DerivativesState`, `LiquidationEvent` (REQ-WP-002),
the feature registry (REQ-WP-011). Nothing new.

**Storage**: none.

**Testing**: pytest, pure. Every expected value hand-computed.

**Target Platform**: `src/channelflow/derivatives/`.

**Performance Goals**: none. Windows are linear scans.

**Constraints**: FR-001 (funding never unsettled), FR-002 and FR-003
([[ADR-026]]), FR-006 ([[ADR-027]]), FR-012 (no clock).

**Scale/Scope**: 4 modules, ~35 tests, ~16 registered features.

## Constitution Check

- **I (no look-ahead)** — FR-001 is the derivatives family's characteristic
  leak, and the state join is where it would happen.
- **II (time is not one thing)** — a funding observation carries a settlement
  time and an event time, and conflating them is PRD §41 rule 5.
- **VI (every feature is documented)** — the registry, extended rather than
  duplicated.
- **X (thresholds are configuration)** — window lengths and cluster bucket
  sizes are arguments.
- **XIV** — traces to REQ-WP-013 and REQ-BIAS-005.

**Gate result: PASS.**

## Project Structure

```text
src/channelflow/derivatives/
├── __init__.py
├── state.py        # the as-of join over DerivativesState, and its refusals
├── funding.py      # §16.1, and the settlement boundary
├── openinterest.py # §16.2, including the regime label
└── liquidations.py # §16.4

tests/unit/derivatives/
├── test_state.py, test_funding.py, test_openinterest.py, test_liquidations.py
```

Basis lives in `openinterest.py`'s module only in the sense that both are
arithmetic over a joined state; it gets its own functions and its own tests
inside `test_openinterest.py`, because a third module for two subtractions
would be structure for its own sake.

**Structure Decision**: `state.py` holds the as-of join, mirroring
REQ-WP-017's: the point-in-time rule belongs in one place per package, not in
each feature function.

## Approach

**The z-score helper is shared and refuses twice** ([[ADR-026]]). Written once
in `state.py` so funding and open interest cannot diverge on what "too few
observations" means.

**Funding's settlement boundary is the module's reason to exist.** A
`DerivativesState` carries `funding_rate` and `next_funding_time_ns`; the rate
is for the interval *ending* at that time, so at any `t` before it the rate is
an estimate the venue may revise. `settled_funding_at` returns only rates whose
interval has closed.

**The regime is computed and returned, never branched on** ([[ADR-027]]).

## Complexity Tracking

> No violations.
