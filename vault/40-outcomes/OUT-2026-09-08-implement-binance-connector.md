---
id: OUT-2026-09-08-implement-binance-connector
step: implement
records: [REQ-WP-003]
commit: null
---

## What was done

All 13 tasks. Three modules under `src/channelflow/connectors/binance/`, 19
tests against 105 recorded messages. No test opens a socket — verified by grep
and by running the suite with the Docker stack down. `mypy --strict` clean over
12 source files.

**RED first**, for each of the three phases: `ModuleNotFoundError` for
`normalize`, then `orderbook`, then `session`.

## What was decided

- **Five behaviours proven by mutation, not by assertion.** Each was broken on
  purpose and the failing test observed:

  | Mutation | Caught by |
  |---|---|
  | apply a delta anyway across a sequence gap | `test_an_invalid_book_refuses_to_supply_state` |
  | let an invalid book answer | same |
  | parse prices through `float` | three normalization tests |
  | resume the book after a reconnect | `test_a_reconnect_demands_a_fresh_snapshot` |
  | reconnect after the 24h limit rather than before | same |

  The first is the one that matters most: applying a delta across a gap is
  exactly what PRD §8.1 forbids hiding, and exactly what a feed library would
  have hidden. It is the concrete reason ADR-004 chose a native connector, now
  demonstrated rather than argued.

- **The book refuses rather than degrades.** `best_bid_ask` raises when the book
  is stale. PRD §11.1 rule 6 forbids emitting features from an invalid book; if
  the book answered anyway, every caller would have to remember the rule, and
  one of them would not.

- **A gap does not apply the delta.** Counting the gap but applying the update
  anyway would leave a book that diverged from the venue while reporting good
  health — worse than one that admits it is broken.

- **Snapshot messages have no venue timestamp**, so `event_time_ns` and
  `ingest_time_ns` are both receipt time there. Stated at the call site rather
  than left for someone to discover; it is the one place the two clocks
  legitimately coincide.

- **The venue's push timestamp `E` is used as `event_time` for depth updates**
  but not for trades, which use `T`. A depth update has no other venue clock; a
  trade does, and the trade time is what actually happened.

## What is still open

- **Liquidations remain unimplemented.** No fixture, because the stream is
  unreachable from this network. REQ-WP-003 asks for them "when available"; when
  they become available, this is where they go.
- **Rate limiting is not implemented**, as the spec recorded. It needs its own
  requirement.
- **`session.py` has no real websocket transport yet.** The lifecycle is proven
  against a fake; wiring `websockets` to the `Transport` protocol is a small
  piece of work with no logic in it, and it belongs with the ingestion loop that
  will drive `tick()`.
- **Principle VIII's shared connector interface is provisional.** It is whatever
  this connector established; the second connector will show whether it fits.
