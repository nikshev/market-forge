# Implementation Plan: Signal outcomes, fill models and economic metrics

**Branch**: `bt-001-outcomes-economics` | **Date**: 2026-09-09 | **Spec**: [spec.md](./spec.md)

## Summary

Three modules under `src/channelflow/backtest/`: PRD §40's outcome resolution,
§25.4's two phase-1 fills, and §25.5's metrics — the last of which cannot be
built without a cost model.

## Technical Context

**Language/Version**: Python 3.12, `mypy --strict`.

**Primary Dependencies**: none new; `statistics` from the standard library.

**Testing**: pytest, over hand-built OHLC bars whose ranges are the point.

**Target Platform**: `src/channelflow/backtest/`.

**Constraints**: FR-003 (never the favourable ordering) and FR-012 (§41 rule 9),
recorded in [[ADR-048]].

**Scale/Scope**: 3 modules, 25 tests.

## Constitution Check

- **I (no look-ahead)** — an outcome is refused when its horizon reaches past the
  bars, so no study is fed a shortened window labelled as a full one.
- **VI (every feature is documented)** — the costs travel with the metrics they
  produced.
- **XI (results are reproducible)** — no clock, no sampling; one input, one
  report.
- **XIV** — traces to REQ-BT-001.

**Gate result: PASS.**

## Project Structure

```text
src/channelflow/backtest/
├── outcomes.py    # NEW: PRD 40's SignalOutcome and its resolution
├── fills.py       # NEW: 25.4's two phase-1 models
└── economics.py   # NEW: 25.5's metrics, after costs
```

**Structure Decision**: three modules, not one. The outcome is a fact about
price, the fill is a fact about execution, and the metrics are arithmetic over
both — and only the third is allowed to require a cost model. Merging them would
put §41 rule 9's gate in front of the outcome resolution, which does not need it.

## Approach

**The ambiguous case is the module.** §40 emphasises "never choose the favorable
ordering", and a bar containing both levels is where a backtest can flatter
itself with both readings looking plausible. Resolved either way it produces a
number that survives every review, because nothing downstream can tell which
ordering was assumed.

**The loop's `break` is the guarantee, not a second guard.** An earlier draft
also nulled the touch times when ambiguous; the mutation sweep showed the guard
could not fire, and — worse — that with it in place, deleting the `break`
changed no test. One guard, checked.

**A touch includes equality.** Requiring a strict breach is choosing the
favourable ordering by a tick, on every trade.

**The cost model is a required argument, not a documented step.** [[ADR-009]]
already wrote down why: "a backtest that reports 62% win rate before fees will
be quoted as 62%, because the caveat does not travel with the number". A
required argument travels.

## Complexity Tracking

> No violations.
