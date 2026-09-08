# Implementation Plan: OFI / LOB features

**Branch**: `wp-011-ofi-lob-features` | **Date**: 2026-09-08 | **Spec**: [spec.md](./spec.md)

## Summary

Five modules under `src/channelflow/features/`: three feature families (book
instant, order flow, trade flow), the wall lifecycle, and the registry that
makes all of them documented by construction.

## Technical Context

**Language/Version**: Python 3.12, `mypy --strict`.

**Primary Dependencies**: `OrderBook`/`BookService` (REQ-WP-004), `TradeEvent`
(REQ-WP-002), `Bar` (REQ-WP-005). Nothing new.

**Storage**: none. PRD §24.1's feature snapshot table is unbuilt.

**Testing**: pytest, pure, fast gate. Every value in the tests is hand-computed
from a constructed book or trade sequence — a feature checked against another
implementation of itself proves nothing.

**Target Platform**: `src/channelflow/features/`.

**Performance Goals**: none stated. Instant features are O(levels); OFI is O(1)
per observation; the wall tracker is O(tracked walls) per observation. PRD §0.14
puts correctness first.

**Constraints**: FR-005 (refuse on an invalid book), FR-009 (no increment
across a gap), FR-019 (no clock), FR-020 (point-in-time safe).

**Scale/Scope**: 5 modules, ~18 registered features.

## Constitution Check

- **I (no look-ahead)** — every feature is a function of observations at or
  before `t`. FR-020 makes each registration state it, and the OFI tracker's
  refusal to difference across a gap is the one place the rule could have been
  broken silently.
- **II (time is not one thing)** — windows are event-time; `ingest_time_ns` is
  never read. Same rule as REQ-WP-004's staleness.
- **VI (every feature is documented)** — the registry, and the test that
  enforces it (ADR-015). This principle is the reason US5 is P1.
- **X (thresholds are configuration)** — the wall anomaly threshold, the window
  lengths and the depth bands are arguments.
- **XIV** — traces to REQ-WP-011 and REQ-PRIN-008.

**Gate result: PASS.**

## Project Structure

```text
src/channelflow/features/
├── __init__.py
├── registry.py    # FeatureSpec + REGISTRY: PRD §19's sixteen fields
├── instant.py     # QI, depth imbalance (levels and bands), microprice
├── ofi.py         # Cont increments, event-time windows
├── flow.py        # delta, CVD, slope, acceleration, normalized delta
└── walls.py       # §15.6 lifecycle, ADR-014's executed/cancelled split

tests/unit/features/
├── test_instant.py     # US1: SC-001, SC-002, SC-009
├── test_ofi.py         # US2: SC-003, SC-004
├── test_flow.py        # US3: SC-005
├── test_walls.py       # US4: SC-006
└── test_registry.py    # US5: SC-007, and SC-008's clock check
```

**Structure Decision**: one module per feature family, because the families
differ in what they are functions *of* — a book state, a pair of consecutive
states, a trade stream, a tracked history. Splitting by that boundary means a
module's tests need only one kind of fixture.

The registry is a module, not a YAML file. PRD §19's example is YAML, but a
feature's registration and its implementation drift the moment they live in
different files — and the test that catches the drift can only compare what it
can import. The entries carry §19's fields verbatim.

## Approach

**The registry comes first, before any feature.** Written afterwards it would
be documentation of what happened to get built; written first it is the shape
each feature has to fit. ADR-015's gate only works in that order.

**Every expected value in the tests is hand-computed and written as a literal.**
The temptation with feature code is to assert against a second implementation
of the formula, which passes whenever both are wrong the same way.

**OFI's gap rule is the subtle one.** The tracker holds the previous
observation; on a rebuild the caller signals discontinuity and the tracker
drops it. A tracker that simply differenced whatever came next would invent
flow across the gap — and the number would look ordinary.

**Walls need both streams, so the tracker takes an interval.** Each `observe`
call receives the current book and the trades since the last call. That keeps
ADR-014's `min(decrease, traded)` local to one interval rather than requiring
the tracker to hold a trade history.

## Complexity Tracking

> No violations. The module count is high because the feature families are
> genuinely different functions; the alternative is one file that needs every
> fixture at once.
