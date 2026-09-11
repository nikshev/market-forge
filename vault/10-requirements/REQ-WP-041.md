---
id: REQ-WP-041
title: The catalog the stack runs is the catalog CI proves
type: work-package
prd_ref: "§7, §29.0"
prd_lines: "786-790"
phase: 8
status: implemented
depends_on: [REQ-WP-039]
tags: []
---

## Requirement

PRD §7 names the pieces:

    - S3-compatible object storage: canonical durable data plane
    - Apache Iceberg: lakehouse table/catalog semantics for normalized, feature
      and research-grade datasets
    - PostgreSQL: transactional metadata/control plane

[[ADR-060]] put those together and said the catalog is "SQL — SQLite-backed for
local runs and CI's fast gate, and PostgreSQL-backed on the dev stack and
beyond… the same catalog implementation with a different URL".

**Nothing checks the second half of that sentence.** Every test runs against
SQLite. The claim that one implementation serves both is the entire argument for
REQ-INFRA-002 surviving the migration — a test double behind a port is fine, a
second production path is not — and it is currently an assertion in a document.

[[ADR-002]] made the identical argument about storage and acted on it: MinIO
rather than a local directory, "because developing against a filesystem and
switching to S3 later would reintroduce exactly the local-versus-production
divergence Principle VII exists to prevent". The same reasoning applies to where
the catalog lives, and the same answer follows.

**A catalog that has never been opened against PostgreSQL is a deployment
waiting to find out.** It will find out on the day something first runs there,
which is the day nobody wants a surprise.

## Acceptance

- A table commits, reads and time-travels through a PostgreSQL-backed catalog,
  verified against the stack's own database in CI.
- The same code path serves both catalogs: one factory, two URLs, no branch on
  which one it is.
- The fast gate still needs no service (REQ-INFRA-002).
- What configures the catalog is read from the environment, not written into the
  code — a hard-coded DSN works in exactly one deployment.
- Nothing about the SQLite path changes.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-079-stack-catalog]]
- **Tests:**
    - `tests/integration/test_catalog_on_postgres.py::test_a_table_commits_reads_and_time_travels_through_the_stack_catalog`
    - `tests/integration/test_catalog_on_postgres.py::test_an_earlier_read_is_unchanged_by_a_later_commit`
    - `tests/integration/test_catalog_on_postgres.py::test_the_same_factory_opens_both_catalogs`
- **Code:**
    - `src/channelflow/lakehouse/iceberg.py`
- **Outcomes:** [[OUT-2026-09-11-implement-stack-catalog]], [[OUT-2026-09-11-requirement-stack-catalog]]
<!-- trace:end -->

## Notes

Human territory. Never machine-rewritten.

The driver is new. `pyiceberg`'s SQL catalog goes through SQLAlchemy, which
needs a synchronous PostgreSQL driver; `asyncpg` is asynchronous and serves the
API's own queries. PRD §7 names "SQLAlchemy or asyncpg for Postgres metadata",
so both belong, and this is not a choice this requirement is making on its own.

Out of scope, and named rather than implied: **nothing runs on the stack yet.**
This proves the catalog opens, commits and reads there. What creates the
namespace in a deployment, and who owns the migration of it, is deployment work
and Phase 8 lists that separately.
