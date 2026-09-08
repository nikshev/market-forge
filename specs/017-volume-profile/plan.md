# Implementation Plan: Volume profile

**Branch**: `wp-012-volume-profile` | **Date**: 2026-09-08 | **Spec**: [spec.md](./spec.md)

## Summary

Three Python modules under `src/channelflow/volume/` and one frontend module:
the binning, the value area and nodes, the shape features, and the chart's
profile series.

## Technical Context

**Language/Version**: Python 3.12 (`mypy --strict`), TypeScript 5.6.

**Primary Dependencies**: `TradeEvent` (REQ-WP-002), the registry
(REQ-WP-011), `ChannelSnapshot` (REQ-WP-006) for node overlap.

**Storage**: none.

**Testing**: pytest and Vitest, both pure. Every bin total hand-summed.

**Target Platform**: `src/channelflow/volume/` and `apps/web/src/`.

**Performance Goals**: none. Binning is one pass over trades.

**Constraints**: FR-001 (from trades, never from candles), FR-007 (an empty
window refuses), FR-014 (no clock).

**Scale/Scope**: 3 Python modules, 1 frontend module, ~35 tests.

## Constitution Check

- **I (no look-ahead)** — a profile describes the trades it was given; the
  caller chooses the window, and nothing here reaches outside it.
- **VI (every feature is documented)** — registry entries for the shape
  features.
- **X (thresholds are configuration)** — bin width, value-area share and node
  thresholds are arguments; PRD §14.1 names 70% as a default, not a constant.
- **XI (results are reproducible)** — the tie-breaks in [[ADR-028]] are fixed,
  so two builds of one trade set give one profile.
- **XIV** — traces to REQ-WP-012.

**Gate result: PASS.**

## Project Structure

```text
src/channelflow/volume/
├── __init__.py
├── profile.py   # binning from trades, POC, value area (ADR-028)
├── nodes.py     # HVN/LVN, and overlap with channel boundaries
└── shape.py     # entropy, skew, distances, and the registry entries

apps/web/src/
└── volumeProfile.ts   # the bars the chart draws

tests/unit/volume/{test_profile.py,test_nodes.py,test_shape.py}
apps/web/src/__tests__/volumeProfile.test.ts
```

**Structure Decision**: `profile.py` owns the value-area construction because
it is the one piece with a decision behind it ([[ADR-028]]); putting it beside
the binning keeps the rule next to the data it applies to. Nodes and shape read
a finished profile and never rebuild one.

## Approach

**Bin assignment is by integer division from an anchor**, so the same trades
always produce the same bins regardless of arrival order, and a trade on a
boundary always falls in the upper bin.

**The value area is grown, not selected** ([[ADR-028]]), and the result carries
a flag when the target could not be met by a proper subset.

**The frontend module is series-only**, like `series.ts`: jsdom cannot lay out
a chart, so the tested thing is the bar lengths and which bin is marked.

## Complexity Tracking

> No violations.
