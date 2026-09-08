# Implementation Plan: Signal state machine

**Branch**: `wp-007-signal-state-machine` | **Date**: 2026-09-08 | **Spec**: [spec.md](./spec.md)

## Summary

One transition table over PRD §21.2's lifecycle, with direction and boundary as
candidate attributes rather than states. Pure: bars and channel snapshots in,
candidate history out.

## Technical Context

**Language/Version**: Python 3.12, `mypy --strict`.

**Primary Dependencies**: the `Bar` of REQ-WP-005 and the `ChannelSnapshot` of
REQ-WP-006. Nothing new.

**Storage**: none. PRD §21.2 says to persist transitions; they are produced as
immutable records and persisting them is later work.

**Testing**: pytest, pure, fast gate.

**Target Platform**: `src/channelflow/signals/`.

**Performance Goals**: none stated.

**Constraints**: FR-006 — determinism. A state machine whose path depends on
anything but its inputs cannot be backtested, and PRD §0.13 requires results
reproducible from a versioned dataset and a commit hash.

**Scale/Scope**: a state enum, a candidate record, one transition table, one
rejection detector, and their tests.

## Constitution Check

- **I (no look-ahead)** — the machine sees one bar at a time and the channel
  snapshot for that moment. It never reaches forward, and REQ-WP-006 already
  guarantees the snapshot could not have.
- **III (history is immutable)** — transitions are appended, never edited. A
  confirmation that happened stays recorded even when price immediately
  invalidates it; erasing it would be repainting wearing a different shape.
- **IX (no automatic execution)** — this produces signals and nothing else. PRD
  §0.11 puts Phases 1 to 3 under this rule, and the lifecycle deliberately ends
  at alerted rather than at anything actionable.
- **X (thresholds are configuration)** — every bound is a constructor argument.
  PRD §13.11 calls its own zone defaults "research defaults, not proven
  parameters", and treating them as constants would make that untrue by
  omission.
- **XIV** — traces to REQ-WP-007.

**Gate result: PASS.**

## Project Structure

```text
src/channelflow/signals/
├── __init__.py
├── models.py       # CandidateState, Transition, Candidate
├── rejection.py    # the pluggable detector protocol + close-back-inside
└── machine.py      # the transition table

tests/unit/signals/
├── test_lifecycle.py       # SC-001, SC-002, SC-007
├── test_preconditions.py   # SC-003, SC-004
└── test_termination.py     # SC-005, SC-006, SC-008
```

**Structure Decision**: the transition table lives alone in `machine.py`, so
"does this skip a step" is answerable by reading one file.

## Complexity Tracking

> No violations.
