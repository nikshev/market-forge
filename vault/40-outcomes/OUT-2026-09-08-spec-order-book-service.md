---
id: OUT-2026-09-08-spec-order-book-service
step: spec
records: [REQ-WP-004]
commit: null
---

## What was done

`specs/010-order-book-service/spec.md`: four user stories, 13 functional
requirements, 7 success criteria. Two ADRs for what the PRD leaves open.

## What was decided

- **"Depth within X bps" needed a reference price and the PRD never names one**
  ([[ADR-011]]). The mid, for both sides, because §15.1's `DI_k` is a bid/ask
  depth ratio — measuring each side from its own best price would make it a
  comparison of two different distances, moving with the spread instead of with
  the liquidity. An empty side means no mid, and the query refuses.
- **The book is not a Binance thing** ([[ADR-012]]). REQ-WP-003's
  reconstruction contains no venue-specific logic and moves to
  `src/channelflow/book/`; Principle VIII ("connectors share one interface")
  is empty if the shared thing lives inside one connector.
- **No I/O and no clock in the service.** A rebuild is a method call taking a
  snapshot, so the caller owns the retry policy and the tests need no fake
  transport. Staleness is `as_of_ns` minus the last applied event time, which
  is what makes replaying a recorded stream twice give the same health.
- **`latency_ms` from PRD §11.1's `BookHealth` is deliberately not reported.**
  It measures transport, not reconstruction; reporting it would reintroduce
  the ingest-time dependency ADR-012 removes. It belongs to the connector's
  error metrics.

## What is still open

- **Wall/level lifecycle (§15.6) and absorption (§15.7) are not in scope.**
  They read a book; they are features, and REQ-WP-011 owns them.
- Persistence of book snapshots (§29.4's `market.book_snapshot.v1`) is unbuilt,
  so nothing here is durable across a restart.
