---
id: OUT-2026-09-09-implement-lakehouse-repository
step: implement
records: [REQ-STORE-002]
commit: null
---

## What was done

`channelflow.api.LakehouseRepository` and the six tables it reads. 31
conformance tests over two implementations, 7 mapping tests, and every existing
endpoint test parametrised over both — 138 in the two packages. 17 mutations.

[[ADR-019]] promised on 2026-09-08 that the durable repository would arrive
"without any endpoint changing". That promise is now something the suite fails
on rather than a sentence in a docstring.

## A join that was wrong in a way no single record could show

A score's contributions were joined to their score on `as_of_ns`. Scores tie on
that instant whenever the caller does not supply one — which is the default —
so a market with two scores read back as **one score carrying every group either
of them had**. Every row involved was correct. The join was not.

A round-trip test with one score passes. A conformance test with two does not,
and the mutation sweep is what made me write the second one. Scores now carry a
content-derived id and the contributions join on it; the id is content-derived
rather than random so that the same score written twice is the same score and a
re-run of a backfill does not look like new data.

The same default exposed a smaller fault beside it. `max` returns the *first*
maximal element, so the "latest score" of a tied group was the oldest one on
record. The reader takes the last of the newest now, which is what append-only
means.

## What the plane learned

§29.6 asks a channel snapshot for "quality components" and "forecast arrays" by
name. A table that could only hold scalars would have needed six child tables
across these schemas, each joined back on every read.

So the plane gained `float_list`, `string_list` and `float_map`. Arrow and
Parquet carry all three natively and DuckDB and Trino query them, which is the
whole reason [[ADR-002]] chose the physical format. Their canonical encodings
follow the same rules as everything else: framed per item so a list cannot forge
its own boundaries, and map keys sorted so two writers who inserted the same
pairs in different orders wrote the same value.

A transition history stayed a child table. §29.7 asks for a decision core plus a
separate table, and the alternative — four parallel lists on the parent — is
four columns that only mean anything read together, in an order nothing
enforces.

## Four properties no endpoint can reach

Of the five mutations that survived the first sweep, four were properties an API
test cannot see: the feature row order (which exists for the content hash, not
for a read), the transition ordinal (which matters only when rows arrive out of
order), and the two row-helper refusals. They are tested directly now, and the
transition test shuffles the rows to make the point.

## What was decided

- **One suite, both implementations.** Two would drift, and the first divergence
  would be a behaviour one has and the other does not with nothing saying which
  is right.
- **No `cap` column on a contribution.** A group's cap is `GROUP_CAPS[group]`, a
  §22.1 constant. Storing it would create a second source of truth, and the six
  caps summing to 100 would then be breakable by a row.
- **A decimal column refuses anything but its exact text on read.**
  `Decimal(str(1.1))` succeeds, and a reader that coerced would undo the column
  type silently on the way out.
- **A market list declares no event time.** It is configuration, not
  observation, so a point-in-time read of it is refused rather than answered —
  PRD §41 rule 7's point-in-time listing history is a different and harder
  question than this table answers.

## Mutation results

Seventeen mutations, all caught, every restore verified:

| Mutation | Caught by |
| --- | --- |
| A later channel snapshot is returned | `test_a_channel_snapshot_is_never_later_than_the_instant_asked_for` |
| The oldest snapshot wins | `test_a_channel_snapshot_is_never_later_than_the_instant_asked_for` |
| A snapshot for another series is returned | `test_a_snapshot_for_another_series_is_not_returned` |
| Forecast horizons are dropped | `test_a_channel_snapshot_survives_its_quality_and_its_forecast` |
| Quality submetrics are dropped | `test_a_channel_snapshot_survives_its_quality_and_its_forecast` |
| The unavailable list is dropped | `test_a_channel_snapshot_survives_its_quality_and_its_forecast` |
| Transitions lose their order | `test_a_transition_history_is_restored_by_its_ordinal` |
| The signal id is invented rather than shared | `test_a_signal_is_reachable_by_the_id_its_deep_link_uses` |
| A signal filter is ignored | `test_signals_filter_on_every_field_the_port_offers` |
| The history is not attached | `test_a_signal_round_trips_with_its_history_in_order` |
| Features are not sorted by name | `test_feature_rows_do_not_depend_on_a_mapping_s_insertion_order` |
| The newest score is not taken | `test_the_latest_score_is_the_one_returned` |
| A market with no score returns an empty one | `test_a_market_nobody_scored_has_no_score` |
| The bar limit takes the oldest | `test_bars_come_back_in_time_order_and_the_limit_takes_the_newest` |
| Feature points are not grouped by instant | `test_feature_points_are_bounded_at_both_ends` |
| The contributions join on the instant, not the score | `test_the_latest_score_is_the_one_returned` |
| A decimal column accepts a float on read | `test_a_decimal_column_refuses_anything_but_its_exact_text` |

## What is still open

- **Nothing fills these tables from a live feed.** The writers exist for tests
  and backfills; a process that runs a connector into them is deployment work.
- **Each writer is a commit.** Right for a test and wrong for a backfill, which
  should use the table modules where the batch is the unit. The signature
  matches the in-memory repository's deliberately, and that is the cost.
- **§29.7's resolution/outcome table does not exist.** §29.7 asks for the
  decision core *plus* one; [[REQ-BT-001]] models outcomes and nothing joins
  them to signals.
- **Every read is a full scan.** The plane has no predicate pushdown and the
  filters run in Python after the read. That is fine for the sizes here and is
  the first thing that will not be.
- **The in-memory repository is still the default.** Nothing selects the durable
  one at startup, because nothing starts.
