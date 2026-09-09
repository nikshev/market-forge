# Implementation Plan: Multi-scale extrema

**Branch**: `exp-016-multi-scale` | **Date**: 2026-09-09 | **Spec**: [spec.md](./spec.md)

## Summary

One research module that prices each of EXP-016's three nesting rules against
the same candidates without it, per trade *and* in total, over context that had
actually closed.

## Technical Context

**Language/Version**: Python 3.12, `mypy --strict`.

**Primary Dependencies**: `channelflow.backtest`.

**Testing**: pytest, over a candidate set where the zone decides the outcome and
alignment adds a hair, plus an inverted variant and several single-candidate
cases.

**Target Platform**: `src/channelflow/research/`.

**Constraints**: FR-005 (both numbers), FR-007 (only closed frames), FR-002.

**Scale/Scope**: 1 module, 17 tests.

## Constitution Check

- **I (no look-ahead, ever)** — `available_frame` is the whole guard: the frame a
  candidate sits inside has not closed, and its zone is partly made of bars that
  come after the candidate.
- **IV (a number without its baselines is not a result)** — every rule is priced
  against the same candidates without it.
- **XI (results are reproducible)** — no sampling.
- **XIV** — traces to REQ-EXP-016.

**Gate result: PASS.**

## Project Structure

```text
src/channelflow/research/multi_scale.py   # NEW
```

**Structure Decision**: the rules are predicates over a candidate and its two
frames, and the pricing is one function applied to three sets. A rule that
carried its own scoring would let two rules' numbers stop meaning the same
thing.

## Approach

**Two numbers per rule, because a chart shows one.** Per trade, a filter looks
good almost by definition. In total it can be a loss, because it removed winners
along with losers, and the removed trades are not on the picture.

**The floor guards the per-trade number only.** That is the one a filter inflates
by construction. The total is the book's own outcome over the same candidates: if
it went up, it went up, and holding it to a floor measured in per-trade R would
be one number meaning two different things.

**The rejected set is priced.** EXP-016 names "aligned/conflicted" as a pair, and
the conflicted candidates are an arm of the experiment rather than a discard.

**A candidate without context is excluded from every arm.** Scoring it in the
base and not in the filtered arm would make the warm-up look like the rule's
contribution.

## Complexity Tracking

> No violations.
