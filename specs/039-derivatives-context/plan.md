# Implementation Plan: Derivatives context

**Branch**: `exp-006-derivatives-context` | **Date**: 2026-09-09 | **Spec**: [spec.md](./spec.md)

## Summary

One module: declared buckets over four variables, [[REQ-BT-001]]'s economics per
bucket, and a label saying whether the study forecasts or explains.

## Technical Context

**Language/Version**: Python 3.12, `mypy --strict`.

**Primary Dependencies**: `channelflow.backtest` for the economics. Nothing new.

**Testing**: pytest, over hand-built populations at chosen readings.

**Target Platform**: `src/channelflow/research/`.

**Constraints**: FR-005 (absence is not a flat conditional), FR-008 (the label
has no default).

**Scale/Scope**: 1 module, 12 tests.

## Constitution Check

- **VI (every feature is documented)** — every report says what kind of study it
  is, in words, in its own payload.
- **X (thresholds are configuration)** — the edges and the minimum bucket are
  arguments with named research defaults.
- **XI (results are reproducible)** — declared edges rather than sample
  quantiles, so two windows bucket the same reading the same way.
- **XIV** — traces to REQ-EXP-006.

**Gate result: PASS.**

## Project Structure

```text
src/channelflow/research/derivatives_context.py   # NEW
```

**Structure Decision**: the study takes observations carrying both the state and
the outcome. Reading a funding z-score at signal time is pipeline work, and a
study that fetched its own would decide the point-in-time question for its
caller — which is exactly the question it is required to state.

## Approach

**Declared edges, not sample quantiles.** Quantiles move with the window, so the
same funding reading would land in different buckets depending on what else was
in it, and two studies could not be compared.

**A missing variable is not a bucket.** Rendered as one bucket holding
everything, "no data" and "no relationship" look identical.

**The point-in-time flag is required.** It decides whether the answer is a
forecast or an explanation, and the note is generated from it so the two cannot
drift apart.

**The economics come from [[REQ-BT-001]].** A second scoring path would make
these conditionals incomparable with every other experiment's numbers, and would
need its own §41 rule 9 refusal.

## Complexity Tracking

> No violations.
