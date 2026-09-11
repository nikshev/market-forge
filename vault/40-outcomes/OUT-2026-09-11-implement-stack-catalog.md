---
id: OUT-2026-09-11-implement-stack-catalog
step: implement
records: [REQ-WP-041]
commit: null
---

## What was done

`tests/integration/test_catalog_on_postgres.py`, `psycopg[binary]` as a
dependency, and one change to the factory: it carries storage properties
through. 3 tests against the stack's PostgreSQL, 3 of 3 mutants caught, every
gate green. CI already provisions PostgreSQL, so the workflow needed nothing.

[[REQ-WP-041]] reaches `implemented`, and [[ADR-060]]'s claim that the catalog
is one implementation is now checked rather than asserted.

## A test that reads the source, and why

`test_the_same_factory_opens_both_catalogs` reads `iceberg.py` and fails if the
factory mentions a scheme. That is a strange thing for a test to do, and every
behavioural test in the file is the reason: a catalog that reached PostgreSQL
through a second code path would pass all of them and be exactly the second
production path [[ADR-002]] refused. The claim under test is not "PostgreSQL
works"; it is "it is the same path", and no amount of behaviour can say so.

The mutation sweep confirms it is load-bearing: adding `if
uri.startswith("postgresql")` to the factory leaves every round trip passing and
fails only that test.

## What the work uncovered

**The MinIO integration tests were building their catalogs by hand**, bypassing
the factory entirely — so the older of them proved the storage worked and said
nothing about the thing [[ADR-060]] actually claimed. They go through the
factory now, which is what made it need `**properties` in the first place.

Worth noticing that this was invisible while every test that could have caught
it was written against SQLite. The claim and its evidence were in different
files and neither knew.

## A dependency added, and why it is not a decision

`pyiceberg`'s SQL catalog goes through SQLAlchemy, which needs a synchronous
driver; `asyncpg` is asynchronous and serves the API's own queries. PRD §7 names
"SQLAlchemy or asyncpg for Postgres metadata", so both belong and this
requirement is not choosing a stack. The binary wheel is chosen so CI needs no
build toolchain.

## What is still open

- **Nothing runs on the stack.** This proves a capability, not an operation.
- **Who creates the namespace in a deployment**, and whether the catalog's own
  tables need a migration story. `pyiceberg` creates them on first use, which is
  convenient and is not a migration story.
