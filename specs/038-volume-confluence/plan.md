# Implementation Plan: Volume profile confluence

**Branch**: `exp-005-volume-confluence` | **Date**: 2026-09-09 | **Spec**: [spec.md](./spec.md)

## Summary

One module: a classifier over [[REQ-WP-012]]'s profile, and a study over
[[REQ-BT-001]]'s outcomes that answers in three values.

## Technical Context

**Language/Version**: Python 3.12, `mypy --strict`.

**Primary Dependencies**: `channelflow.volume` for the levels,
`channelflow.backtest` for the outcomes. Nothing new.

**Testing**: pytest, over a constructed profile with a deliberate shelf and
hand-built populations.

**Target Platform**: `src/channelflow/research/`.

**Constraints**: FR-008 (no default effect size), FR-010 (nothing decided is not
zero).

**Scale/Scope**: 1 module, 14 tests.

## Constitution Check

- **X (thresholds are configuration)** — the band and the minimum population
  have named research defaults; the effect size has none, deliberately.
- **XI (results are reproducible)** — pure arithmetic over supplied outcomes.
- **XIV** — traces to REQ-EXP-005.

**Gate result: PASS.**

## Project Structure

```text
src/channelflow/research/volume_confluence.py   # NEW
```

**Structure Decision**: the study takes observations, not bars. Deciding what
happened to a setup is [[REQ-BT-001]]'s job, and a study that resolved its own
outcomes would be scoring its own choices — and would be untestable at the point
where the populations are constructed.

## Approach

**The effect size is a required argument.** `inspect.signature` is asserted in a
test, because a default is the judgement "materially" names, made by whoever
wrote the module rather than by the researcher asking the question.

**Three answers, and the third is real.** Most confluence claims are "not
materially different".

**Timeouts are counted and are not decisions.** Target-before-stop is a
probability over setups that reached one or the other; folding timeouts into the
denominator makes a quiet market look like a losing one.

**A price in no bin is not a node.** Nothing traded there to be a low-volume
one — which is a distinction the classifier gets right and a test nearly got
wrong, because a thin bin *is* an LVN and EXP-005 counts it.

## Complexity Tracking

> No violations.
