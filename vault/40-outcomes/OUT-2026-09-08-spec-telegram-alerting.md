---
id: OUT-2026-09-08-spec-telegram-alerting
step: spec
records: [REQ-WP-008]
commit: null
---

## What was done

`specs/012-telegram-alerting/spec.md`: five user stories, 17 functional
requirements, 9 success criteria, three ADRs.

## What was decided

- **Four of PRD §26.1's blocks are omitted, not placeheld** ([[ADR-016]]).
  Score needs §43's ranker, model probability needs a model Principle IV
  forbids for now, derivatives is WP-013 and DeFi is WP-014/015. A placeholder
  in a trading alert is worse than a gap: a reader scanning a dozen messages
  reads the shape, and "Score: —" beside "Score: 82/100" is a formatting
  difference. §26.3's severity tiers are score ranges, so they go too.
- **The signal id is derived, never generated** ([[ADR-017]]). A random UUID
  would make a replay produce different alerts, different dedupe decisions and
  a different audit — all looking correct. Deriving it from the candidate's
  identity is also what gives dedupe its key for free.
- **No transport, no sleep, no clock** ([[ADR-018]]). "Never block the signal
  engine" becomes a property of the code rather than a promise, because there
  is nothing in the queue path that can block. Backoff is a policy that maps an
  attempt to a delay; the waiting belongs to the caller.
- **Stale data is a hard stop** (FR-015). PRD §25.6 lists "stale-data alert
  count" and adds "must be zero" — the only metric in the document that comes
  with a required value.

## What is still open

- **A real Telegram transport is owed.** This package defines the protocol and
  ships no adapter; the adapter is small and belongs behind the connector
  boundary.
- **The deep link points at a chart that does not exist** (REQ-WP-009). The URL
  is correct by construction; its target arrives later.
- **Nothing is durable.** The dead-letter record and the audit live in memory;
  PRD §29's storage is unbuilt.
