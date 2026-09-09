---
id: OUT-2026-09-09-plan-experiment-registry
step: plan
records: [REQ-REPRO-001, REQ-BIAS-011]
commit: null
---

## What was done

Four modules, no new third-party dependencies. 9 tasks.

## What was decided

- **The registry is a lakehouse table**, not a PostgreSQL one ([[ADR-054]]): a
  registry that could be edited after the fact would defeat the rule it exists
  to enforce, and a lakehouse table cannot be.
- **Config hashing is its own function**, not the lakehouse's row encoding. Same
  discipline — length-prefixed, type-tagged — and a different shape: one encodes
  a flat row against a declared schema, the other an arbitrary nested structure
  with none.
- **No integration test.** The registry is a lakehouse table and the lakehouse's
  own MinIO tests already cover the storage path; a second copy would test the
  same round trip through a different caller.

## What is still open

- Nothing from this step.
