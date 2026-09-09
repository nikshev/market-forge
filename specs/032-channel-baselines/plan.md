# Implementation Plan: Channel baselines B, C and D

**Branch**: `chan-001-alternative-baselines` | **Date**: 2026-09-09 | **Spec**: [spec.md](./spec.md)

## Summary

Three estimators beside baseline A, sharing its window rule, its snapshot shape
and its quality vocabulary where that vocabulary still means the same thing.

## Technical Context

**Language/Version**: Python 3.12, `mypy --strict`.

**Primary Dependencies**: NumPy, already present. No SciPy, no statsmodels.

**Testing**: pytest, over the existing deterministic series builders.

**Target Platform**: `src/channelflow/channels/`.

**Constraints**: FR-013 (no backward pass) and FR-002 (window rule), both
checked structurally.

**Scale/Scope**: 4 modules including the extracted window, 16 tests.

## Constitution Check

- **I (no look-ahead)** — the window rule is shared, not reimplemented three
  times, and baseline D's forward-only structure is asserted over its source.
- **X (thresholds are configuration)** — every tuning constant is a field with
  the reason for its default written beside it.
- **XI (results are reproducible)** — the quantile fit is exact, so there is
  nothing to converge and nothing to seed.
- **XIV** — traces to REQ-CHAN-001.

**Gate result: PASS.**

## Project Structure

```text
src/channelflow/channels/
├── window.py      # NEW: the shared window rule, extracted from baseline A
├── huber.py       # NEW: baseline B, PRD 13.3
├── quantile.py    # NEW: baseline C, PRD 13.4
├── kalman.py      # NEW: baseline D, PRD 13.5
└── rolling_ols.py # baseline A, now delegating its window
```

**Structure Decision**: the window rule moved to its own module before the
second baseline existed. Three copies of "finalized, at or before `as_of`,
sorted, at least `lookback`" would agree today and drift later, and it is the
rule Principle I rests on.

## Approach

**No new dependency for two fits.** Huber is iteratively reweighted least
squares in a dozen lines; the quantile fit enumerates the lines through pairs of
points, which is exact.

**The quantile fit is exact, not descended.** A gradient descent on the pinball
loss needs a step size, a smoothing width and an iteration count — three
research defaults with nothing behind them — and the first version got them
wrong in a way no acceptance test would have caught: on a perfectly flat series
it oscillated around the solution and reported a two-and-a-half percent channel.
Enumeration has no knobs, and at a lookback of sixty it costs two milliseconds.

**Baseline D is a loop.** §13.5 forbids the smoother, and the loop is the
guarantee: there is nowhere in it a later observation could enter. The test
checks for the patterns a backward pass is made of, not for the word
"smoother" — which the module's own docstring uses to explain what it refuses to
be.

**Quality is reported in each model's own terms.** Baseline A's coverage
submetrics do not transfer to conditional quantiles or to a filtered level, so
each names what it cannot compute rather than reporting a number that means
something else.

## Complexity Tracking

> No violations.
