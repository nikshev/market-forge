---
id: OUT-2026-09-08-spec-bar-aggregation
step: spec
records: [REQ-WP-005]
commit: null
---

## What was done

Specified REQ-WP-005 as `specs/006-bar-aggregation/spec.md`: 14 functional
requirements, 7 success criteria.

## What was decided

- **The PRD requires a late-event policy and never defines one.** Searching for
  the term finds only REQ-WP-005's own bullet. It had to be decided, and the
  situation is routine rather than exceptional — websockets deliver out of
  order, reconnections replay, backfills overlap. Recorded as [[ADR-005]].
- **Reopening a closed bar was never a candidate.** §0.5 forbids rewriting
  finalized snapshots and §0.3 forbids a value computed at `t` changing
  afterwards. A bar that amends itself after publication is repainting — the one
  failure this whole project exists to prevent. The policy is therefore: grace
  period, then discard and count.
- **The watermark is event time, never wall-clock** (FR-007, SC-006). Closing a
  bar on local time would make boundaries depend on our own latency, so a replay
  and a live run would produce different bars from identical input. That breaks
  Principle VII, which is what the backtest rests on. SC-006 makes it checkable:
  the builder takes no clock argument, so it cannot consult one.
- **A quiet market leaves the last bar open, deliberately.** With no trades there
  is no evidence the window has passed. A consumer needing a heartbeat supplies
  one as an explicit event rather than having the builder invent time.
- **Order-independence is a success criterion** (SC-003, FR-013), not an
  assumption. Feeding shuffled trades must produce identical bars, because
  out-of-order arrival is the normal case and a builder sensitive to it would
  produce different history on every replay.
- **Deduplication is the caller's job.** The builder aggregates what it is given.
  PRD §11.2 already defines the identity; implementing it here would duplicate
  that logic into every consumer.

## What is still open

- **The five-second grace default is a starting value, not a measurement.**
  ADR-005 records that it needs checking against real venue behaviour. The
  late-trade counter is what will show whether it is wrong.
- **Multi-timeframe composition is the caller's.** One instance handles one
  symbol and one timeframe, which keeps the state machine small; whether a
  higher-level component should fan out is a later question.
- **No persistence.** PRD §29.4's `bars` table is a separate concern.
