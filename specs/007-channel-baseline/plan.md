# Implementation Plan: Channel baseline

**Branch**: `wp-006-channel-baseline` | **Date**: 2026-09-08 | **Spec**: [spec.md](./spec.md)

## Summary

Baseline A: OLS on log close over a rolling lookback, bands from empirical
residual quantiles, plus a quality score from the six submetrics whose inputs
exist. Pure — bars in, snapshot out.

## Technical Context

**Language/Version**: Python 3.12, `mypy --strict`.

**Primary Dependencies**: NumPy for the fit (PRD §7). The `Bar` model from
REQ-WP-005.

**Storage**: none. Snapshots are immutable values; PRD §29.6's table is later.

**Testing**: pytest, pure, in the fast gate.

**Target Platform**: `src/channelflow/channels/`.

**Performance Goals**: none stated. A least-squares fit over a few hundred
points is not where PRD §36's budget goes.

**Constraints**: `source_max_event_time <= as_of`. Everything else here is a
modelling choice that can be revisited; this one is the product's premise.

**Scale/Scope**: a snapshot model, a fitter, a quality scorer, and their tests.

## Constitution Check

This is the feature the constitution was written for.

- **I (no look-ahead, ever)** — the whole point. The fit filters by `as_of`
  itself rather than trusting its caller, and SC-001 proves it by refitting
  after appending future bars and demanding an identical result. Principle I
  says this holds "even when violating it would improve a backtest", which is
  exactly the temptation a channel model presents.
- **III (history is immutable)** — snapshots are frozen. PRD §0.5 forbids
  rewriting them after finalization, and a value that cannot be mutated cannot
  be rewritten.
- **V (calibration, not accuracy)** — the quality score is a descriptive
  composite, not a probability, and nothing here claims otherwise. When it
  becomes probabilistic, §13.9's ML scoring, calibration metrics become due.
- **VI (every feature documented)** — each submetric states what it measures and
  in what units, because a score in `[0,1]` composed of unnamed parts is a
  number nobody can argue with.
- **XII (correctness before performance)** — NumPy in float64 for the fit, with
  the reasoning stated in the module: log-space regression is inherently
  floating-point, and pretending otherwise with `Decimal` would be theatre.

**Gate result: PASS**, with the float64 choice named rather than assumed.

## Project Structure

```text
src/channelflow/channels/
├── __init__.py
├── models.py     # ChannelSnapshot, ChannelQuality
├── quality.py    # the six submetrics and their weighted average
└── rolling_ols.py  # Baseline A

tests/unit/channels/
├── test_no_lookahead.py   # SC-001, SC-002 -- the ones that matter
├── test_fit.py            # SC-003, SC-004, SC-008
└── test_quality.py        # SC-005 to SC-007
```

**Structure Decision**: `test_no_lookahead.py` is its own file rather than a
section of another, because it tests the property the product exists to
guarantee and it should be obvious when it is missing.

## Complexity Tracking

> No violations.
