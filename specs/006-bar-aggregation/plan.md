# Implementation Plan: Bar aggregation

**Branch**: `wp-005-bar-aggregation` | **Date**: 2026-09-08 | **Spec**: [spec.md](./spec.md)

## Summary

A `Bar` model and a `BarBuilder` that accumulates trades into event-time windows
and finalizes them by watermark. Pure: no clock, no I/O, no persistence.

## Technical Context

**Language/Version**: Python 3.12, `mypy --strict`.

**Primary Dependencies**: the domain models from REQ-WP-002. Nothing new.

**Storage**: none.

**Testing**: pytest, pure. Runs in the fast gate.

**Target Platform**: `src/channelflow/bars/`.

**Performance Goals**: none stated. PRD §36's ingestion targets bind the loop
that will drive this, not the aggregation itself.

**Constraints**: FR-007 and FR-009 — no wall-clock, and no amendment after
close. Everything else is recoverable; those two are what separate a bar
pipeline from a repainting one.

**Scale/Scope**: one model, one builder, and their tests.

## Constitution Check

- **I (no look-ahead)** and **III (history is immutable)** bind hardest here. A
  finalized bar that can still change is a value computed at `t` that differs
  later, which is the definition both principles forbid. FR-009 and SC-002 make
  it checkable.
- **II (time is not one thing)** — the builder reads `event_time_ns` only. It
  takes no clock argument at all, so `ingest_time` cannot leak into a boundary
  decision even by accident. That is the strongest available form of the rule:
  not a convention but an absence.
- **VII (live and replay are the same code)** — SC-003's order-independence is
  what makes replay reproduce live. A builder sensitive to arrival order would
  produce different history on every run from identical input.
- **XII, XIV** — exact decimals over speed; traces to REQ-WP-005.

**Gate result: PASS.**

## Project Structure

```text
src/channelflow/bars/
├── __init__.py
├── models.py     # Bar: the fourteen fields PRD §12 lists
└── builder.py    # windows, watermark, finalization, late counting

tests/unit/bars/
├── test_bar_fields.py    # SC-001, SC-007
├── test_finalization.py  # SC-002, SC-004, SC-005
└── test_determinism.py   # SC-003, SC-006
```

**Structure Decision**: the model is separate from the builder because the model
is what every consumer imports and the builder is what only ingestion touches.

**Not produced**: no `data-model.md` (the model is typed), no `contracts/`.

## Complexity Tracking

> No violations.
