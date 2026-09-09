---
id: OUT-2026-09-09-implement-bars-table
step: implement
records: [REQ-TBL-001]
commit: null
---

## What was done

`channelflow.tables.bars`: PRD §29.4's schema, the row mapping both ways, the
sink that fits `BarBuilder.on_final`, and the reads. 13 tests here, 3 added to
the lakehouse for the new column type, 12 mutations.

## The plane could not carry money

`Bar` holds `Decimal` for every price and size, and the lakehouse's vocabulary
had `float64` and nothing better. float64 cannot represent a tenth; a canonical
table that rounded on the way in would make every downstream figure wrong by an
amount nobody could reconstruct afterwards.

The type added is `decimal`, stored as the value's exact string form. Not an
Arrow decimal: that needs a precision and a scale declared per column, PRD §29's
schemas give neither, and the first value exceeding a guessed precision would be
truncated silently. A string round-trips every `Decimal` and costs bytes.

It also means `Decimal("1.10")` and `Decimal("1.1")` are different content. They
compare equal and carry different exponents, and the two strings are stored
distinctly — the same conservative reading [[ADR-053]] takes for `-0.0`.

## The column choice that is a look-ahead rule

The event-time column is `close_time_ns`, not `open_time_ns`. A bar becomes
knowable when it closes, so a point-in-time read as of an instant *inside* a
window must not return that window.

With the open as the event time it would: the read would hand back a bar whose
high, low and close had not happened yet, and every leakage check upstream would
already have passed, because the leak is in the storage read. The test asks for
a bar at one nanosecond before its close and expects nothing.

## Eleven of twelve, and the twelfth was not a mutation

Removing the explicit `Decimal(...)` conversion in `from_row` changed no test,
because `Bar` is a Pydantic model whose validator coerces the exact string form
to the same `Decimal`.

The conversion is not redundant — it is what keeps `from_row` correct if the
model's field type ever changes, and a `float` field would coerce that same
string silently and lose the exactness. But it is not a behavioural guard today,
and reporting it as an uncaught gap would have overstated what the suite misses.

That is the third time today the distinction has come up: the lakehouse's
zero-padding, the experiments package's single type tag, and now this. A
mutation that changes code without changing behaviour is not a finding about the
tests, and calling one a survivor makes a sweep's number mean less rather than
more.

## What was decided

- **`is_final` is not a column.** It would be `true` on every row here, which
  makes it a field nobody reads and a door held open for the row that says
  otherwise. The refusal in `to_row` carries the meaning and cannot be bypassed
  by writing a row directly.
- **The sink is the builder's own hook**, so a replay fills the table by the
  same path a live feed would — Principle VII, without a second code path.
- **A flush of nothing commits nothing**, because a snapshot identical to its
  parent under a new id would make every consumer keyed by snapshot see a change
  that did not happen.

## Mutation results

Eleven behavioural mutations, all caught, every restore verified:

| Mutation | Caught by |
| --- | --- |
| An unfinalized bar is written | `test_an_unfinalized_bar_is_refused` |
| The event time is the open, not the close | `test_a_point_in_time_read_uses_the_close_and_not_the_open` |
| Point-in-time filters on the open time | `test_a_point_in_time_read_uses_the_close_and_not_the_open` |
| Prices are stored as floats | `test_a_price_that_float64_cannot_hold_comes_back_unchanged` |
| The order key is ignored | `test_rows_come_back_in_the_order_the_prd_names` |
| The sink flushes an empty buffer | `test_flushing_nothing_commits_nothing` |
| The sink does not clear after flushing | `test_the_sink_buffers_and_commits_once` |
| A filter is ignored | `test_a_read_can_be_narrowed_to_one_series` |
| A decimal column takes a float | `test_a_decimal_column_takes_a_decimal_and_nothing_else` |
| A decimal is written as a float | `test_a_price_that_float64_cannot_hold_comes_back_unchanged` |
| `decimal_columns` names nothing | `test_a_schema_names_the_columns_a_reader_has_to_convert_back` |

## What is still open

- **Nothing runs a pipeline into this table.** The sink fits the builder's hook
  and no process attaches it; that is deployment work.
- **Sixteen of §29.B's seventeen tables do not exist.** Each arrives with the
  subsystem that produces it.
- **A snapshot per flush.** Right for a backfill, and a live feed flushing often
  would grow the manifest chain — [[REQ-STORE-001]] already records compaction as
  its open question, and this is the first table that will need it.
- **No integration test of its own.** The plane's MinIO tests cover the storage
  path; this module adds a mapping on top of it, and a second round trip through
  a different caller would test the same thing.
