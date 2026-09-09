# Implementation Plan: The `bars` canonical table

**Branch**: `tbl-001-bars` | **Date**: 2026-09-09 | **Spec**: [spec.md](./spec.md)

## Summary

One adapter module holding PRD §29.4's schema, the mapping both ways, and a sink
that fits the bar builder's own hook — plus the `decimal` column type the plane
needed before it could carry money.

## Technical Context

**Language/Version**: Python 3.12, `mypy --strict`.

**Primary Dependencies**: `channelflow.bars`, `channelflow.lakehouse`.

**Testing**: 13 unit tests for the table, 3 added to the lakehouse for the new
column type.

**Target Platform**: `src/channelflow/tables/`, with an addition to
`lakehouse/schema.py`.

**Constraints**: FR-001 (exactness), FR-004 (the close, not the open), FR-009
(PRD §29.0's isolation).

**Scale/Scope**: 1 new package, 1 module, 16 tests, 12 mutations.

## Constitution Check

- **I (no look-ahead, ever)** — the event-time column is the bar's close, so an
  as-of read cannot return a window that had not finished.
- **V (finalized records are not rewritten)** — only finalized bars are stored,
  and the plane's history is immutable underneath.
- **VII (live and replay are the same code)** — the sink is the builder's own
  hook, so a replay fills the table by the same path a live feed would.
- **XI (results are reproducible)** — every flush has a content hash.
- **XIV** — traces to REQ-TBL-001.

**Gate result: PASS.**

## Project Structure

```text
src/channelflow/tables/bars.py        # NEW: schema, mapping, sink, reads
src/channelflow/lakehouse/schema.py   # + the `decimal` column type
```

**Structure Decision**: a third package, because neither side may import the
other. The lakehouse must not know what a `Bar` is — a row that had to be one
would tie the plane to a single subsystem — and the bar builder must not import
a storage backend, which is PRD §29.0's rule and an existing test. §29.0 asks
for exactly this: "backend-specific DDL must live behind migrations/adapters".

## Approach

**Money is stored as text, not as a float or an Arrow decimal.** float64 cannot
hold 0.1; an Arrow decimal needs a precision and scale per column that PRD §29's
schemas do not give and that would silently truncate the first value exceeding
them. The exact string form round-trips every `Decimal` and costs bytes.

**The event-time column is `close_time_ns`.** A bar becomes knowable when it
closes. Filtering on the open would return a window whose high, low and close
had not happened yet, handed over as if they had.

**`is_final` is not a column.** Every row here is final, so a column holding
`true` on every row would be a field nobody reads and a door left open. The
refusal in `to_row` carries the meaning instead.

**The sink buffers.** Every append is a commit, and a commit per bar would make
the snapshot chain as long as the series — metadata larger than data. It does
not flush on a timer, because nothing here reads a clock.

## Complexity Tracking

> No violations.
