# Implementation Plan: Adaptive stop management

**Branch**: `wp-020-adaptive-stops` | **Date**: 2026-09-08 | **Spec**: [spec.md](./spec.md)

## Summary

Three modules under `src/channelflow/stops/`: PRD §44A.3's models, §44A.16's
proposal pipeline, and §44A.28's counterfactual replay with the costs §41 rule
9 requires.

## Technical Context

**Language/Version**: Python 3.12, `mypy --strict`.

**Primary Dependencies**: nothing new. Anchors arrive as `(price, known_at)`,
so the policy has no opinion about whether a level came from REQ-WP-019's
extrema, REQ-WP-006's channel or REQ-WP-012's volume nodes.

**Storage**: none.

**Testing**: pytest, pure, every R hand-computed.

**Target Platform**: `src/channelflow/stops/`.

**Constraints**: FR-001 (never widen), FR-003 (never a future anchor), FR-013
([[ADR-031]]), FR-018 (no price-only anchor kind).

**Scale/Scope**: 3 modules, ~31 tests.

## Constitution Check

- **I (no look-ahead)** — FR-003 is the rule, and REQ-WP-019's `known_at` is
  what makes it checkable.
- **III (history is immutable)** — §44A.39 requires an immutable stop path;
  every model is frozen.
- **IX (no automatic execution)** — the engine proposes. Nothing here places or
  amends an order, and §44A.39 is explicit that live mode needs a separate
  acceptance process.
- **X (thresholds are configuration)** — improvement threshold, cooldown, noise
  multiple and costs are all arguments.
- **XI (results are reproducible)** — the replay is deterministic.
- **XIV** — traces to REQ-WP-020 and REQ-BIAS-009.

**Gate result: PASS.**

## Project Structure

```text
src/channelflow/stops/
├── __init__.py
├── models.py   # §44A.3's PositionState, anchors, proposals, outcomes
├── policy.py   # §44A.16's filter pipeline
└── replay.py   # §44A.28's counterfactual, with §44A.23's cost model

tests/unit/stops/{test_policy.py,test_replay.py}
```

**Structure Decision**: the naive baselines live in `replay.py` beside the cost
model rather than in `policy.py`. They are not policies this engine offers —
they exist to be compared against, and keeping them out of the policy module
means nothing can accidentally configure one as the default.

## Approach

**The filters run in a fixed order and each may only hold or tighten.** PRD
§44A.16 ends "No individual feature is allowed to bypass the safety filters",
so the order is the design: buffer, then monotonic, then market distance, then
threshold, then the initial-risk contract last.

**A hold is a proposal** ([[ADR-032]]), carrying its reason code.

**`AnchorKind` has no price-only member.** §44A.39 forbids a blind
price-following path in the default policy, and an enumeration that cannot
express one enforces it better than a comment.

## Complexity Tracking

> No violations.
