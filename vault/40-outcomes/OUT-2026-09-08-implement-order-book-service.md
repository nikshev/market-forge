---
id: OUT-2026-09-08-implement-order-book-service
step: implement
records: [REQ-WP-004]
commit: null
---

## What was done

`channelflow.book`: the reconstruction moved out of the Binance connector, plus
`BookService` — the bootstrap buffer, the rebuild path, top-N, depth-at-bps and
event-time health. 25 new tests; the connector's 5 recorded-stream tests pass
unchanged across the move.

## What was decided

- **`apply_bootstrap` relaxes the exact-continuity rule, once, deliberately.**
  The steady-state rule demands `first == last + 1`. A venue does not promise
  that for the first delta after a snapshot: Binance documents that the one to
  apply is the delta whose *range contains* `lastUpdateId + 1`, because a delta
  may straddle the moment the snapshot was taken. Keeping the strict rule
  everywhere would have made every bootstrap against a live feed fail. The
  relaxation is narrow — the range must still contain the next sequence — and
  it lives in its own method so it cannot be reached from the steady-state path.
- **Gap counting moved from "when it happens" to "when the book retires".**
  The first version incremented the service's counter at the moment of a gap
  *and* read the live book's counter in `health`, so a single gap was reported
  as two. Now the service accumulates only the gaps of books it has replaced.
- **The duplicated read guard was removed rather than kept.** The service
  checked book validity before every read and `OrderBook` checked it again
  inside each one. That reads as defence in depth and is the opposite: with two
  guards over one property, removing either changed no result and no test
  noticed — mutation M2 passed clean. The service now checks only what it
  alone knows (whether a book exists at all); refusing an invalid book is the
  book's own job. The same shape was found twice in REQ-WP-010.

## Mutation results

Seven mutations, all caught after the duplicate guard was removed:

| Mutation | Caught by |
| --- | --- |
| Accept an out-of-sequence delta | `test_a_missing_delta_makes_the_book_admit_it_is_broken` (+8 more) |
| Let an invalid book answer a read | `test_every_read_refuses_after_a_gap` |
| Answer before bootstrap | `test_a_service_that_has_not_bootstrapped_refuses_every_read` |
| Forget the gap count on rebuild | `test_gaps_accumulate_across_rebuilds` |
| Measure depth from each side's own best price | `test_depth_is_measured_from_the_mid_and_not_from_each_side` |
| Bootstrap without checking the buffer connects | `test_a_buffer_that_does_not_reach_the_snapshot_fails_bootstrap` |
| Take staleness from ingest time instead of event time | `test_staleness_is_the_distance_from_the_last_applied_event` |

The depth mutation is the one worth noting: a test written on a tight book
would pass under either rule. It bites only because one fixture has a 500 bps
spread, where the two references give different answers.

## What is still open

- **No persistence.** PRD §29.4's `market.book_snapshot.v1` is unbuilt, so a
  restart loses the book and needs a fresh bootstrap.
- **`top(n)` sorts the whole side per call.** Linear in the book, not in n.
  PRD §0.14 puts correctness first; a sorted structure is the optimisation to
  make when a profile asks for it.
- **The features of PRD §15 are REQ-WP-011.** This supplies the book they read;
  queue imbalance, microprice, OFI and book shape are not built.
