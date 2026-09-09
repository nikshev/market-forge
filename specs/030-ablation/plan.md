# Implementation Plan: An ablation across feature families

**Branch**: `us-006-ablation` | **Date**: 2026-09-09 | **Spec**: [spec.md](./spec.md)

## Summary

One module under a new `research` package: REQ-US-006's five arms, each scored
on one shared fold set through the direct baseline, with unrunnable arms named
rather than scored.

## Technical Context

**Language/Version**: Python 3.12, `mypy --strict`.

**Primary Dependencies**: `channelflow.dataset` for the folds,
`channelflow.turning.direct` for the scoring path. Nothing new.

**Testing**: pytest, over 120 constructed rows and four walk-forward folds.

**Target Platform**: `src/channelflow/research/`.

**Constraints**: FR-004 and FR-005 are the requirement; FR-011 (no clock, no
random source).

**Scale/Scope**: 1 module, 13 tests.

## Constitution Check

- **IV (no ML layer before deterministic baselines)** — the arms are scored by
  the same logistic baseline REQ-WP-019's direct target uses, against the
  no-skill base rate.
- **VI (every feature is documented)** — an arm that did not run says why, in
  the report.
- **XI (results are reproducible)** — the ranking breaks ties by name, and one
  input produces one report.
- **XIV** — traces to REQ-US-006.

**Gate result: PASS.**

## Project Structure

```text
src/channelflow/research/
├── __init__.py
└── ablation.py   # the arms, the report, and what it refuses to say

tests/unit/research/test_ablation.py
```

**Structure Decision**: a new package rather than a module under `models`.
`models` holds estimators and their comparison report; an ablation is a research
procedure over a dataset, and the next things of its kind — EXP-004's
incremental-value study, EXP-015's confluence — belong beside it rather than
inside the estimator package.

## Approach

**The folds are the caller's.** EXP-015 says "use strict ablation and same
walk-forward folds"; rebuilding them per arm would make each arm's score depend
on its own split, and the difference between two arms would no longer be the
families under test.

**An arm that could not look is never reported as having looked.** The registry
carries no channel or DEX features today, so "channel + DEX" resolves to the
channel's own features. Scored, it produces the same number as "channel only" —
and a reader takes that as evidence the DEX family adds nothing. The missing
family is checked *before* the duplicate test, so the reason names the cause
rather than the symptom.

**The ranking is a public function.** Two arms over different features almost
never score identically, so a ranking that depended on entry order would agree
with itself on every realistic input. Exposed, the tie-break can be tested on a
constructed tie.

**One scoring path.** `run_direct_baseline` does the fitting, so an arm's score
means the same thing as REQ-WP-019's.

## Complexity Tracking

> No violations.
