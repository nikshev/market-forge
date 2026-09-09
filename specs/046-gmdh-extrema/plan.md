# Implementation Plan: GMDH derivative extrema

**Branch**: `exp-013-gmdh-extrema` | **Date**: 2026-09-09 | **Spec**: [spec.md](./spec.md)

## Summary

One research module running EXP-013's four arms over one set of folds, plus the
extraction that let the derivative arm share [[REQ-WP-019]]'s promotion loop
rather than own a second copy of it.

## Technical Context

**Language/Version**: Python 3.12, `mypy --strict`.

**Primary Dependencies**: `channelflow.turning`, `channelflow.models`,
`channelflow.backtest`.

**Testing**: pytest, over a linearly learnable fixture, an interaction fixture no
linear model can learn, a near-boundary root, and a fixture whose paths the
features cannot predict.

**Target Platform**: `src/channelflow/research/`, with a refactor in
`turning/experiment.py`.

**Constraints**: FR-003 to FR-006 (the denominators, [[ADR-051]]), FR-011
(costs, PRD §41 rule 9), FR-013 (both failures named).

**Scale/Scope**: 1 module, 1 refactor, 16 tests.

## Constitution Check

- **I (no look-ahead, ever)** — the forward path is label-side by §24.2, and the
  arms read only the design matrix `run_direct_baseline` already builds.
- **IV (a number without its baselines is not a result)** — every arm is scored
  against the no-skill base rate, and the incremental figure is against the
  cheapest arm.
- **VII (live and replay are the same code)** — the promotion gate and the
  perturbation lattice are [[REQ-WP-019]]'s, reached through the extracted
  reading function rather than reimplemented.
- **XI (results are reproducible)** — no sampling anywhere: the lattice is
  exhaustive and the folds are the dataset's.
- **XIV** — traces to REQ-EXP-013.

**Gate result: PASS.**

## Project Structure

```text
src/channelflow/research/gmdh_extrema.py   # NEW
src/channelflow/turning/experiment.py      # read_derivative_folds extracted
src/channelflow/turning/__init__.py        # + the readings and wanted_turn_type
```

**Structure Decision**: `run_derivative_experiment` was one function doing two
jobs — reading every validation row's forward path, and ruling on what the
readings were worth. EXP-013 needs the first and asks a different question of
the second. Splitting them is why this experiment has one promotion gate rather
than two that only look alike.

## Approach

**Four arms, one design matrix.** The comparison is only meaningful if the arms
see the same rows in the same order; each arm supplies its own probabilities to
the same `compare` call.

**The denominators are the whole design problem**, and [[ADR-051]] records them.
Averaging a root's presence rate over rows whose path never turned measures how
often the market turns, not how stable a turn is — and on the first fixture built
here it failed the gate at 0.50 for exactly that reason.

**A classifier arm is not given a time-to-turn error.** It never named a time.
That blank is what the derivative route's complexity is being weighed against.

**The verdict names every failure.** One that stopped at the first would send a
reader back to run the experiment again with that one fixed, only to meet the
second.

## Complexity Tracking

> No violations.
