---
id: OUT-2026-09-07-tasks-domain-model
step: tasks
records: [REQ-WP-002]
commit: null
---

## What was done

16 tasks in five phases: foundations, the seven events, identity, fixtures,
close.

## What was decided

- **T001 tests `EventMeta` alone before any event exists.** The riskiest property
  — that a nanosecond timestamp survives a double-parsing consumer — belongs to
  the metadata, so it can be proven before six of the seven models are written.
- **T013 requires proving the fixture guard by breaking a model**, not by
  watching it pass. A fixture test that has never failed is a claim.

## What is still open

- Whether these per-model fixtures should later live alongside PRD §35.2's
  end-to-end raw-to-signal fixtures.
