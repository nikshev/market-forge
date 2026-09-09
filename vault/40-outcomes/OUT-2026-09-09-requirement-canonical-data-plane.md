---
id: OUT-2026-09-09-requirement-canonical-data-plane
step: requirement
records: [REQ-STORE-001]
commit: null
---

## What was done

`REQ-STORE-001`, hand-written from PRD §7's target storage profile, §29.0's
deployment profiles and §29.B's canonical tables.

## Why it is hand-written

PRD §46 has no work package for §29, and `tools/extract_prd.py` reads neither §7
nor §29. [[REQ-API-001]], [[REQ-BT-001]], [[REQ-CHAN-001]] and
[[REQ-SCORE-001]] were written the same way, from sections no work package
covers.

## What was decided

- **The acceptance criteria are derived where the PRD states a property rather
  than a test** — "immutable snapshots", "dataset lineage/snapshot
  reproducibility", "must not leak into signal/channel domain code" — and quoted
  where it states them outright.
- **The scope names what it excludes.** Pinot and Trino stay deferred by
  [[ADR-002]]; the full Iceberg specification and its catalog protocol are not
  what §29.B asks for; the seventeen canonical tables arrive with the subsystems
  that produce them; and migrating the API's in-memory repository onto this plane
  is its own step, because [[ADR-019]] made it a port precisely so it could be.

## What is still open

- **Nothing writes to this plane yet.** It is the floor the §29.B tables stand
  on, and every one of them is still a separate piece of work.
