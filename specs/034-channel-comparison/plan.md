# Implementation Plan: Channel model comparison

**Branch**: `exp-001-channel-comparison` | **Date**: 2026-09-09 | **Spec**: [spec.md](./spec.md)

## Summary

One research module running EXP-001's five models over one series and reporting
its seven metrics, plus the two small changes that make five models possible at
all: baseline A's std-band option and a `ChannelModel` protocol.

## Technical Context

**Language/Version**: Python 3.12, `mypy --strict`.

**Primary Dependencies**: `channelflow.channels` for the models,
`channelflow.backtest` for the outcomes, fills and economics. Nothing new.

**Testing**: pytest over deterministic 400-bar series shaped for each metric.

**Target Platform**: `src/channelflow/research/`.

**Constraints**: FR-008 and FR-009 ([[ADR-049]]).

**Scale/Scope**: 1 module, 16 tests.

## Constitution Check

- **I (no look-ahead)** — coverage looks forward from each fit, which is an
  evaluation; nothing measured here re-enters a fit.
- **X (thresholds are configuration)** — the touch band, horizon, split and
  quality floor are arguments, and the report carries them.
- **XI (results are reproducible)** — including the cost metric, which is an
  operation count rather than a stopwatch reading.
- **XIV** — traces to REQ-EXP-001.

**Gate result: PASS.**

## Project Structure

```text
src/channelflow/research/channel_comparison.py   # NEW
src/channelflow/channels/rolling_ols.py          # + bands="std"
src/channelflow/channels/models.py               # + ChannelModel protocol
src/channelflow/backtest/runner.py               # takes any ChannelModel
```

**Structure Decision**: EXP-001's first two models are one fitter under two
width options, because PRD §13.2 lists both and prefers the second. A separate
class would have duplicated the fit to change three lines — but the model name
changes, so a comparison never compares a model with itself under two labels.

## Approach

**Each metric's definition lives in the docstring of the function that computes
it.** EXP-001 names seven and defines none, so a reader has to be able to
disagree with a definition rather than with a number.

**The runner takes a protocol, not a class.** Typing it to baseline A would have
meant the comparison needed its own runner — and then §25.2's rule against a
second backtest implementation would be broken by the experiment testing it.

**The rejection rule is fixed across models.** EXP-001 compares channels, not
exit policies: enter at the next open after a confirmation, stop at the rejected
boundary, target the centre. Which rule it is matters less than that it is one.

**A model's refusal does not end the run.** One model failing to fit is a fact
about that model, and stopping would make the comparison unavailable exactly
when a candidate misbehaves.

## Complexity Tracking

> No violations.
