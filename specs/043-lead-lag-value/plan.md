# Implementation Plan: Cross-venue lead/lag value

**Branch**: `exp-010-lead-lag-value` | **Date**: 2026-09-09 | **Spec**: [spec.md](./spec.md)

## Summary

One module: a declared threshold grid chosen on the training segment, entries
delayed by a stated latency, and a verdict from the held-out segment after costs.

## Technical Context

**Language/Version**: Python 3.12, `mypy --strict`.

**Primary Dependencies**: `channelflow.backtest` for fills, outcomes and
economics. Nothing new.

**Testing**: pytest, over series that jump two bars after each signal.

**Target Platform**: `src/channelflow/research/`.

**Constraints**: FR-001 (in-sample selection), FR-005 (latency), FR-011 (the
import ban).

**Scale/Scope**: 1 module, 16 tests.

## Constitution Check

- **I (no look-ahead)** — the threshold is chosen before the segment it is
  scored on, and the entry is after the signal plus its latency.
- **X (thresholds are configuration)** — the grid is declared and visible; the
  latency is required.
- **XI (results are reproducible)** — no sampling, and equal scores resolve to
  the first threshold.
- **XIV** — traces to REQ-EXP-010.

**Gate result: PASS.**

## Project Structure

```text
src/channelflow/research/lead_lag_value.py   # NEW
```

**Structure Decision**: the signals are supplied rather than computed here.
[[REQ-WP-016]] produces the basis and says nothing about direction; reading a
divergence as a long or a short is a judgement, and a module that made it would
be testing its own reading rather than the divergence.

## Approach

**A grid, not an optimizer.** Five declared thresholds a reader can see and
disagree with, rather than a continuous search that finds whatever the training
segment happened to contain.

**Latency delays the entry, not the signal.** The signal exists when it exists;
the fill is `latency_bars` later, at the next open. A study entering on the
signal's own bar measures a trade nobody could place.

**Ties keep the first threshold.** Equal scores across a grid mean the filter did
not matter, and the narrower one is the honest report of that.

**`NO_EDGE` is returned, never raised** ([[ADR-042]]), including when every
outcome is ambiguous — that is a finding about the bars, not an exception out of
the metric layer.

## Complexity Tracking

> No violations.
