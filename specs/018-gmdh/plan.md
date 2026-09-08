# Implementation Plan: GMDH layer

**Branch**: `wp-018-gmdh` | **Date**: 2026-09-08 | **Spec**: [spec.md](./spec.md)

## Summary

Three modules under `src/channelflow/models/`: the model protocol with its two
baselines, the layered polynomial search, and the comparison report that is the
only place a GMDH score should be read from.

## Technical Context

**Language/Version**: Python 3.12, `mypy --strict`.

**Primary Dependencies**: NumPy, already present. No new ones — [[ADR-029]]
explains why the tree baselines are named rather than added.

**Storage**: none.

**Testing**: pytest, deterministic fixtures with known structure. One dataset
whose target is a genuine interaction, one that is pure noise.

**Target Platform**: `src/channelflow/models/`.

**Performance Goals**: none stated, but the width budget is load-bearing:
without it each layer's node count grows as C(n,2) and the search does not
terminate in practice.

**Constraints**: FR-001 and FR-002 ([[ADR-030]]), FR-012 (deterministic).

**Scale/Scope**: 3 modules, ~21 tests.

## Constitution Check

- **IV (baselines before models)** — the principle that kept this work package
  closed until now. Deterministic baselines exist (REQ-WP-006, REQ-WP-007,
  REQ-WP-019) and their leakage tests pass (REQ-NRT-A to E, REQ-WP-017).
- **V (calibration, not accuracy)** — the report scores Brier, not accuracy.
  PRD §23.8 names it, and accuracy would let a majority-class predictor look
  strong on an imbalanced target.
- **XI (results are reproducible)** — no randomness anywhere: plain gradient
  descent with a fixed step, and a deterministic node ordering.
- **XIV** — traces to REQ-WP-018.

**Gate result: PASS.**

## Project Structure

```text
src/channelflow/models/
├── __init__.py
├── base.py    # the Model protocol, BaseRate, LogisticRegression, split guard
├── gmdh.py    # the layered search
└── report.py  # PRD §23.6's comparison, with all six baselines named

tests/unit/models/{test_gmdh.py,test_report.py}
```

**Structure Decision**: the split guard lives in `base.py` beside the protocol
rather than in `gmdh.py`, because the report needs it too — a comparison
computed on training rows is the most flattering number in the system.

## Approach

**Two fixtures, and both are necessary.** One target turns on `x0 * x1`, which
no linear model can capture, so GMDH beating logistic regression there is
evidence the search works. One is pure noise, where the base rate is unbeatable
by construction and the search must stop growing.

**`fit` raises.** The `Model` protocol's single-split `fit` cannot be honestly
implemented for GMDH, and inventing a split inside would choose a rule PRD §41
rules 1 and 10 are specifically about.

**The report keeps PRD §23.6's order and lists all six baselines**, run or not,
so a reader comparing against the PRD reads down the same list.

## Complexity Tracking

> No violations.
