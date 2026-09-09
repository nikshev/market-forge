# Implementation Plan: Deterministic signal score, explainability and the alert ranker

**Branch**: `score-001-signal-scoring` | **Date**: 2026-09-09 | **Spec**: [spec.md](./spec.md)

## Summary

Four modules under `src/channelflow/scoring/`: PRD §22.1's groups and caps, the
score they combine into, §22.4's explanation, and §43's ranker with §22.3's
threshold.

## Technical Context

**Language/Version**: Python 3.12, `mypy --strict`.

**Primary Dependencies**: none new.

**Storage**: none. Contributions are supplied per call.

**Testing**: pytest, pure. The central fixture is PRD §22.2's own worked
example.

**Target Platform**: `src/channelflow/scoring/`.

**Constraints**: FR-003 and FR-006 ([[ADR-044]]), FR-015 (no clock).

**Scale/Scope**: 4 modules, 32 tests.

## Constitution Check

- **VI (every feature is documented)** — a score carries the contributions it was
  built from, so §0 item 10's "explain why a signal received its score" is
  answerable from the score itself rather than from a log.
- **X (thresholds are configuration)** — §22.3's 75 is a default on a
  configuration object and carries the PRD's own "research value only" label to
  every reader.
- **XI (results are reproducible)** — both orderings break ties on a declared
  key, so one input produces one list.
- **XIV** — traces to REQ-SCORE-001.

**Gate result: PASS.**

## Project Structure

```text
src/channelflow/scoring/
├── __init__.py
├── groups.py    # 22.1's six groups, their caps, and a contribution's range
├── score.py     # the raw and final score, and what was missing
├── explain.py   # 22.4's five items
└── ranker.py    # 43's rank_score, and 22.3's threshold

tests/unit/scoring/{test_score,test_explain,test_ranker}.py
```

**Structure Decision**: the caps live with the groups, not with the scoring, so
a contribution validates itself at construction. A contribution that cannot
exist out of range cannot reach the summation out of range either, and the
summation is then plain arithmetic with nothing to check.

## Approach

**Contributions are supplied.** Each family's arithmetic already lives in its own
package. An engine that reached into all six would own none of them and depend
on all of them; taking them as arguments puts each family's number where the
caller can see it.

**A missing family leaves the denominator** ([[ADR-044]]). §22.1's sentence is
explicit that a missing family "must not automatically equal zero", and the
confidence carries the downgrade instead.

**A `GroupContribution` is a dataclass, not a model.** Pydantic would wrap
`ContributionOutOfRange` in a validation error, and a scoring mistake would then
be handled by whatever already catches malformed input.

**Threshold specificity is a fixed list, not a search.** With overrides at more
than one level, picking the first match found would make the answer depend on
dictionary order.

## Complexity Tracking

> No violations.
