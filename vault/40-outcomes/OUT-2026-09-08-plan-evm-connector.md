---
id: OUT-2026-09-08-plan-evm-connector
step: plan
records: [REQ-WP-014]
commit: null
---

## What was done

Four modules under `src/channelflow/chain/`, three test files, 12 tasks.

## What was decided

- **The ledger owns both availability and reorgs**, because they are the same
  question asked twice: what was knowable at an instant. A reorg changes the
  answer for instants after it and must not change it for instants before, and
  that is one rule rather than two.
- **`Finality` is an `IntEnum`**, so `status >= Finality.SAFE` reads as PRD
  §18.4 rule 2 states it. Ordering is the whole point of a ladder.
- **The record validates its own time ordering at construction**, so no read
  has to defend against a record whose `available_at` precedes its
  `observed_at`.

## What is still open

- Nothing from this step.
