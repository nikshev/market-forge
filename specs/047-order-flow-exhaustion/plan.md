# Implementation Plan: Order-flow exhaustion around extrema

**Branch**: `exp-014-exhaustion` | **Date**: 2026-09-09 | **Spec**: [spec.md](./spec.md)

## Summary

One research module holding two separate studies over the same seven series:
a conditional one that straddles each labelled turn and declares itself
retrospective, and a point-in-time one that reads nothing at or after the bar it
decides.

## Technical Context

**Language/Version**: Python 3.12, `mypy --strict`.

**Primary Dependencies**: numpy, `statistics`.

**Testing**: pytest, over a signal that leads each turn, one that only trails
it, a wave on an unrelated period, a flat signal, a single-spike signal and a
series whose two halves have different distributions.

**Target Platform**: `src/channelflow/research/`.

**Constraints**: FR-004 (Principle I, at the calling threshold), FR-006, FR-007.

**Scale/Scope**: 1 module, 17 tests.

## Constitution Check

- **I (no look-ahead, ever)** — the predictive arm's whole design, threshold
  included. The conditional arm is retrospective and says so in a field.
- **XI (results are reproducible)** — no sampling; every fixture is analytic.
- **XIV** — traces to REQ-EXP-014.

**Gate result: PASS.**

## Project Structure

```text
src/channelflow/research/exhaustion.py   # NEW
```

**Structure Decision**: the signals arrive as series and the extrema as indices.
Computing either here would make this module a test of the feature registry and
the detector rather than of EXP-014's question, and both already have their own.

## Approach

**Two computations, not one with a flag.** The arms differ in their window, in
what they may read, and in what their number means. A shared code path with a
`retrospective=True` switch is exactly the confusion the requirement names, one
level down.

**`trailing_calls` is public** because it carries the property the predictive
arm rests on: the calls made over a prefix are the calls the whole series makes
at those bars. That equality is testable; "we were careful" is not.

**Strictly above the quantile.** An order-flow signal sits at one value most of
the time — absorption is zero on a quiet bar — and the quantile of such a series
*is* that value. "At or above" then calls every bar and reports a lift of
exactly one.

**A lift floor, not a comparison against one.** A signal unrelated to the turns
lands a few points either side of one by accident; two of this module's own
control fixtures read 1.07 and 1.16.

## Complexity Tracking

> No violations.
