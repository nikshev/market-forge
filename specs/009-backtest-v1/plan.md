# Implementation Plan: Backtest v1

**Branch**: `wp-010-backtest-v1` | **Date**: 2026-09-08 | **Spec**: [spec.md](./spec.md)

## Summary

A replay loop that walks bars in event-time order, fits a channel at each, and
drives the production `SignalMachine`. It owns no strategy logic of its own —
that is the requirement, and the parity test is how it is proven.

## Technical Context

**Language/Version**: Python 3.12, `mypy --strict`.

**Primary Dependencies**: `Bar`, `RollingOLSChannel`, `SignalMachine`. Nothing
new — the absence of new dependencies is itself the point.

**Storage**: none.

**Testing**: pytest, pure, fast gate.

**Target Platform**: `src/channelflow/backtest/`.

**Performance Goals**: none stated. Refitting the channel at every bar is
O(n·lookback) and obviously wasteful; PRD §0.14 puts correctness first, and an
incremental fit is an optimisation to make once there is something to measure.

**Constraints**: FR-002 and FR-005 — the backtest must not own strategy logic,
and parity with the live engine must hold.

**Scale/Scope**: a report model, a runner, and their tests.

## Constitution Check

- **VII (live and replay are the same code)** — this feature exists to make that
  true rather than aspirational. The runner imports the engine; the parity test
  catches any drift into a second implementation.
- **I (no look-ahead)** — the runner fits the channel at each bar with `as_of`
  set to that bar, and REQ-WP-006 already refuses to see past it. The backtest
  cannot leak the future even if the loop were written carelessly, because the
  guard lives in the model.
- **XI (results are reproducible)** — the report names its configuration, so a
  number can be traced to what produced it.
- **XIV** — traces to REQ-WP-010.

**Gate result: PASS.**

## Project Structure

```text
src/channelflow/backtest/
├── __init__.py
├── report.py     # BacktestReport: counts, rates, configuration
└── runner.py     # the replay loop

tests/unit/backtest/
├── test_parity.py    # SC-001 -- the requirement
├── test_report.py    # SC-004, SC-005, SC-006, SC-007
└── test_virtual_clock.py  # SC-002, SC-003
```

**Structure Decision**: `test_parity.py` stands alone, like the channel's
no-look-ahead file, because it tests the property the requirement is about.

## Complexity Tracking

> No violations.
