---
id: OUT-2026-09-08-plan-binance-connector
step: plan
records: [REQ-WP-003]
commit: null
---

## What was done

Planned REQ-WP-003 into 13 tasks across three separable pieces: a pure
normalizer, a pure order book, and a thin lifecycle.

## What was decided

- **The split is the point, not an aesthetic.** `normalize.py` and
  `orderbook.py` hold every rule that can be wrong in a way that corrupts data,
  and neither imports a socket. That is what makes SC-008 — no network in any
  test — achievable, and it is why PRD §35.6's replay tests prove anything about
  live behaviour at all (Principle VII).
- **Principle I binds directly for the first time.** Earlier features carried
  timestamps; this one assigns them. Every later guarantee about ordering
  inherits what the connector decides, which is why FR-004 and SC-003 exist.
- **Principle VIII is being set rather than followed.** This is the first
  connector, so the shared interface is whatever this establishes. Kept small
  deliberately: a function per message kind, and a book that accepts deltas.

## What is still open

- Nothing from this step.
