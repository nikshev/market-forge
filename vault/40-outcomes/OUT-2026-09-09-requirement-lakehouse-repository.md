---
id: OUT-2026-09-09-requirement-lakehouse-repository
step: requirement
records: [REQ-STORE-002]
commit: null
---

## What was done

`REQ-STORE-002`, hand-written from [[ADR-019]]'s promise and PRD §29.5-29.7.

## What was decided

- **The acceptance criteria are about the two implementations agreeing**, not
  about one of them working. That is what [[ADR-019]] actually promised.
- **The in-memory repository stays.** It is the fixture every test builds and the
  fastest thing to run; the point of a port is that both exist.
- **§29.7's resolution/outcome table is out of scope** and named: §29.7 asks for
  a decision core *plus* an outcome table, [[REQ-BT-001]] models outcomes, and
  nothing joins them to signals yet.

## What is still open

- **Nothing fills these tables from a live feed.** The writers exist for tests
  and backfills.
