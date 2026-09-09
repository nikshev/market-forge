---
id: REQ-TBL-001
title: The `bars` canonical table, written by the bar builder
type: work-package
prd_ref: "§29.4 bars, §29.B canonical tables, §29.0 adapters"
prd_lines: "4643-4647, 4579-4602, 4546-4556"
phase: null
status: implemented
depends_on: ["REQ-STORE-001", "REQ-WP-005"]
tags: []
hard_gated: false
---

## Requirement

PRD §29.4:

> ## 29.4. `bars`
>
> Order:
>
> `(venue, symbol, timeframe, open_time)`

PRD §29.B lists `bars` among the canonical Iceberg tables, and ends:

> Every research-grade table must support dataset lineage/snapshot
> reproducibility.

PRD §29.0:

> Any backend-specific DDL must live behind migrations/adapters and must not
> leak into signal/channel domain code.

[[REQ-STORE-001]] built the plane and nothing writes to it. This is the first of
§29.B's seventeen tables to hold real domain data, produced by the subsystem
that makes it.

## Acceptance

- every field of a `Bar` survives the round trip exactly, prices included;
- a price float64 cannot hold comes back unchanged;
- only finalized bars are stored, and an unfinalized one is refused rather than
  written;
- a point-in-time read is on the bar's close, so a window that had opened and
  not finished at the instant asked for is not returned;
- rows come back in PRD §29.4's order;
- a read can be narrowed to one venue, symbol or timeframe;
- the writer is usable as `BarBuilder.on_final` directly, buffers, and commits
  in batches rather than once per bar;
- flushing an empty buffer commits nothing;
- the table keeps the plane's guarantees: an immutable history and an identity
  per snapshot;
- no storage backend leaks into the bar builder, and the plane does not learn
  what a `Bar` is.

## Scope

**In:** the `bars` schema, the row mapping both ways, the sink that fits the
builder's hook, the reads, and the `decimal` column type the plane needed to
carry money exactly.

**Out, and named rather than silently dropped:**

- **The other sixteen §29.B tables.** Each arrives with the subsystem that
  produces it and its own requirement.
- **Wiring a live connector into the sink.** The sink fits `on_final`; a running
  pipeline that fills the table is deployment work, and nothing here starts one.
- **Compaction and retention.** A snapshot per flush is right for a backfill and
  will need manifest lists eventually ([[REQ-STORE-001]]'s open questions).

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-054-bars-table]]
- **Tests:**
    - `tests/unit/tables/test_bars.py::test_a_bar_survives_the_round_trip_exactly`
    - `tests/unit/tables/test_bars.py::test_a_point_in_time_read_uses_the_close_and_not_the_open`
    - `tests/unit/tables/test_bars.py::test_a_price_that_float64_cannot_hold_comes_back_unchanged`
    - `tests/unit/tables/test_bars.py::test_a_read_can_be_narrowed_to_one_series`
    - `tests/unit/tables/test_bars.py::test_a_row_carries_every_field_of_a_bar`
    - `tests/unit/tables/test_bars.py::test_a_row_round_trips_through_the_reader_alone`
    - `tests/unit/tables/test_bars.py::test_an_unfinalized_bar_is_refused`
    - `tests/unit/tables/test_bars.py::test_every_stored_bar_reads_back_final`
    - `tests/unit/tables/test_bars.py::test_flushing_nothing_commits_nothing`
    - `tests/unit/tables/test_bars.py::test_rows_come_back_in_the_order_the_prd_names`
    - `tests/unit/tables/test_bars.py::test_the_sink_buffers_and_commits_once`
    - `tests/unit/tables/test_bars.py::test_the_sink_is_the_builder_s_own_hook`
    - `tests/unit/tables/test_bars.py::test_the_table_keeps_the_plane_s_own_guarantees`
- **Code:**
    - `src/channelflow/tables/__init__.py`
    - `src/channelflow/tables/bars.py`
- **Outcomes:** [[OUT-2026-09-09-implement-bars-table]], [[OUT-2026-09-09-plan-bars-table]], [[OUT-2026-09-09-requirement-bars-table]], [[OUT-2026-09-09-spec-bars-table]]
<!-- trace:end -->

## Notes

Hand-written: PRD §46 has no work package for §29's tables. This section is human
territory and is never machine-rewritten.
