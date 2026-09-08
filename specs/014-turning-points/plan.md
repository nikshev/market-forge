# Implementation Plan: Causal turning points

**Branch**: `wp-019-turning-points` | **Date**: 2026-09-08 | **Spec**: [spec.md](./spec.md)

## Summary

A directional-change detector that carries two timestamps, an adaptive
threshold computed point-in-time, a prominence filter, and the five
non-repainting tests that prove none of it repaints.

## Technical Context

**Language/Version**: Python 3.12, `mypy --strict`.

**Primary Dependencies**: `Bar` (REQ-WP-005), `ChannelSnapshot` (REQ-WP-006)
for the channel-width threshold mode. Nothing new.

**Storage**: none. §13A.21's tables are unbuilt.

**Testing**: pytest, pure. The non-repainting tests are the deliverable as much
as the detector is.

**Target Platform**: `src/channelflow/extrema/`.

**Performance Goals**: none stated. The detector is O(1) per bar; ATR and
realized volatility are rolling windows.

**Constraints**: FR-006 and FR-014 (point-in-time throughout), FR-009 and
FR-010 (immutable, append-only), FR-011 (no centered transform in production),
FR-012 (no clock).

**Scale/Scope**: 5 modules, ~45 tests.

## Constitution Check

- **I (no look-ahead)** — the whole feature. Test A is the mechanical proof and
  FR-006 is where it could most easily be broken: a threshold recomputed for a
  past swing would use data from after it.
- **II (time is not one thing)** — `extremum_time`, `known_at` and
  `available_at` are three distinct fields, and PRD §13A.1 exists because
  conflating the first two invalidates every backtest built on them.
- **III (history is immutable)** — Test B. Records are frozen and invalidation
  appends.
- **IV (baselines before models)** — this feature *is* the baseline. ADR-023
  records that its work package cannot complete until the layers Principle IV
  gates are built.
- **VII (live and replay are the same code)** — Test E.
- **X (thresholds are configuration)** — every threshold mode's parameters are
  arguments; PRD §13A.27 states its config values "are research defaults and
  must not be treated as optimized constants".
- **XIV** — traces to REQ-WP-019 and REQ-NRT-A through E.

**Gate result: PASS**, with ADR-023's exception recorded rather than waived.

## Project Structure

```text
src/channelflow/extrema/
├── __init__.py
├── models.py      # ExtremumCandidate, ConfirmedExtremum: §13A.19, frozen
├── thresholds.py  # §13A.5's five modes, all point-in-time
├── causality.py   # ADR-022's transform declaration and the production guard
├── prominence.py  # §13A.6's filter
└── detector.py    # the directional-change state machine

tests/unit/extrema/
├── test_directional_change.py  # US1, US2: SC-001 to SC-003
├── test_prominence.py          # US3: SC-004
├── test_thresholds.py          # US2: SC-003
└── test_non_repainting.py      # US4: SC-005 to SC-010 — Tests A to E
```

**Structure Decision**: `test_non_repainting.py` is one file for all five
tests, not five files. They are a single mandated suite in PRD §13A.28 and are
read together; splitting them would let one quietly disappear.

`causality.py` is separate from `detector.py` because ADR-022's guard is a
general rule about the production path, not a property of one detector — the
local-polynomial and Kalman baselines of §13A.30's steps 3 and 4 will use the
same guard.

## Approach

**The two timestamps are the design.** `ConfirmedExtremum` cannot be
constructed with `known_at < extremum_time`; the model refuses it. Test C then
has something to test rather than a convention to trust.

**The threshold is computed once, at the bar it is used on, and stored with the
confirmation.** Recomputing it later — for a report, a chart, or a backtest —
is how a point-in-time value silently becomes a hindsight one, and storing it
makes the recomputation unnecessary.

**Test A is written to be hard to pass by accident.** It appends *random* bars,
compares every field of every prior output, and asserts the outputs are
non-empty first — a version comparing empty lists would pass trivially.

**Prominence is measured against the causal baseline only.** §13A.6 permits
centered peak-finding for labels; the filter here looks backward from the
candidate, never forward, and `causality.py`'s guard is what stops that
changing later.

## Complexity Tracking

> ADR-023: this plan does not complete its work package, and says so. No other
> violations.
