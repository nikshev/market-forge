# Implementation Plan: Order book service

**Branch**: `wp-004-order-book-service` | **Date**: 2026-09-08 | **Spec**: [spec.md](./spec.md)

## Summary

PRD §11.1's five-step reconstruction, made into something with a lifecycle. The
book state and its sequence rules already exist from REQ-WP-003; this feature
moves them out of the Binance connector, adds the bootstrap buffer, the rebuild
path, the two reads WP-011 needs, and health measured in event time.

## Technical Context

**Language/Version**: Python 3.12, `mypy --strict`.

**Primary Dependencies**: `BookDelta`, `BookSnapshot`, `PriceLevel` from
REQ-WP-002. Nothing new.

**Storage**: none. The book is in-memory; PRD §29.4's
`market.book_snapshot.v1` table is a later concern.

**Testing**: pytest, pure, fast gate. The existing recorded-Binance test moves
to the new import path and stays a real cross-check that the move changed no
behaviour.

**Target Platform**: `src/channelflow/book/`.

**Performance Goals**: none stated. `top(n)` sorts the whole side each call,
which is O(levels log levels) — fine for a book of a few thousand rungs, and
PRD §0.14 puts correctness first. A sorted structure is the optimisation to
make when a profile asks for it.

**Constraints**: FR-010 to FR-012 — no clock, no I/O, no venue knowledge.

**Scale/Scope**: a moved module, a service, and their tests.

## Constitution Check

- **I (no look-ahead)** — the book holds present state only, and staleness is
  the caller's `as_of_ns` minus the last applied event time. Nothing here can
  see forward, and `health` refuses no more than any other read.
- **II (time is not one thing)** — staleness is computed from `event_time_ns`
  and never from `ingest_time_ns`. PRD §9 forbids treating ingest time as
  market information; ADR-012 drops `latency_ms` for exactly that reason.
- **VII (live and replay are the same code)** — no clock and no I/O means a
  recorded stream and a live stream take the same path. SC-007 asserts it.
- **VIII (connectors share one interface)** — the move out of
  `connectors/binance/` is what makes that principle non-vacuous (ADR-012).
- **X (thresholds are configuration)** — the bps distance and N are query
  arguments, not constants.
- **XIV** — traces to REQ-WP-004.

**Gate result: PASS.**

## Project Structure

```text
src/channelflow/book/
├── __init__.py    # OrderBook, BookService, BookHealth, BookInvalid
├── book.py        # moved from connectors/binance/orderbook.py:
│                  #   state, sequence validation, rebuild, reads, health
└── service.py     # BookService: the bootstrap buffer and the lifecycle

tests/unit/book/
├── test_bootstrap.py   # US1: SC-001, and the refusals before bootstrap
├── test_sequence.py    # US2: SC-002, SC-003 -- gap, refusal, rebuild
├── test_reads.py       # US3: SC-004 -- top-N and depth-at-bps
└── test_health.py      # US4: SC-005, SC-006, SC-007
```

`tests/unit/connectors/binance/test_orderbook.py` stays where it is and changes
only its import: it drives the reconstruction from recorded Binance depth
updates, which is a connector-plus-book integration and belongs with the
connector.

**Structure Decision**: state and reads live together in `book.py` — a read is
a question about state, and splitting them would put the mid-price rule in one
file and the prices it reads in another. The buffer and the rebuild policy are
a lifecycle around that state, which is a different responsibility and a
different file.

## Approach

**The move comes first, as its own commit.** `git mv` plus an import update,
with the existing WP-003 tests green before and after. Any later failure is
then attributable to new behaviour rather than to relocation.

**Bootstrap is a small state machine, and it is the part worth being careful
about.** `BookService` starts with no book and a buffer. Deltas accumulate.
When a snapshot arrives, deltas ending at or before its `update_id` are
dropped, and the remainder must connect to it exactly — if the first surviving
delta does not begin at `update_id + 1`, the snapshot is too new or too old for
this buffer and bootstrap fails rather than producing a book with a hole.

**Rebuild keeps the gap count.** SC-003 requires it: a book that forgot its
gaps on every rebuild would report perfect health while flapping.

**Depth-at-bps refuses when there is no mid.** ADR-011. The refusal reuses
`BookInvalid` rather than inventing a second exception type — a caller that
must handle "book unusable" already handles this.

## Complexity Tracking

> No violations.
