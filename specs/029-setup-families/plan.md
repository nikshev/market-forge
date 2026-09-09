# Implementation Plan: Backtesting one setup family at a time

**Branch**: `us-005-setup-families` | **Date**: 2026-09-09 | **Spec**: [spec.md](./spec.md)

## Summary

One new module holding PRD §31's `signals:` block as data, one field on the
production machine saying which setups it may open, and a runner that builds its
machine from a family.

## Technical Context

**Language/Version**: Python 3.12, `mypy --strict`.

**Primary Dependencies**: none new.

**Testing**: pytest, over the existing 400-bar fixture plus its mirror.

**Target Platform**: `src/channelflow/backtest/`, one field in
`src/channelflow/signals/machine.py`.

**Constraints**: FR-010 — configuration only, checked by a test over the source.

**Scale/Scope**: 1 module, 1 machine field, 12 tests.

## Constitution Check

- **VII (live and replay are the same code)** — the family builds a production
  `SignalMachine`; nothing here decides a transition.
- **X (thresholds are configuration)** — that is what a family *is*.
- **XI (results are reproducible)** — the machine is built fresh per run, as the
  runner already copies its own.
- **XIV** — traces to REQ-US-005.

**Gate result: PASS.**

## Project Structure

```text
src/channelflow/backtest/
├── families.py   # NEW: PRD 31's signals block, as data
├── runner.py     # + family, and its machine
└── report.py     # + family

src/channelflow/signals/machine.py   # + opens
```

**Structure Decision**: the restriction is a field on `SignalMachine`, not a
filter in the runner. The engine tracks one candidate at a time, so a middle-zone
setup occupies the machine and the upper-zone setup two bars later never opens —
filtering a finished report would leave that interference in the counts while
looking clean. `opens=None` is every pair, which is what every existing caller
gets and what REQ-WP-010's parity test compares against.

## Approach

**A family is data.** A test asserts `families.py` contains no `CandidateState`,
no `Transition`, no `on_bar` and no detector call: PRD §25.2 forbids a separate
backtest implementation, and a transition rule here would be a second engine with
a nicer name.

**Three of §31's fields are deliberately absent.** `confirmation_bars` is the
engine's own two-bar rule, `min_score` belongs to [[REQ-SCORE-001]], and
`cooldown_bars` has no engine support. Fields nothing reads describe behaviour
that does not exist.

**`middle_continuation_short` takes §13.11's middle-zone defaults**, because §31
writes out only the upper family. The report says which numbers it ran under, so
the borrowing is visible.

## Complexity Tracking

> No violations.
