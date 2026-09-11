---
id: OUT-2026-09-11-requirement-stack-catalog
step: requirement
records: [REQ-WP-041]
commit: null
---

## What was done

`vault/10-requirements/REQ-WP-041.md`. [[ADR-060]] said the catalog is the same
implementation against SQLite and PostgreSQL; nothing has ever opened one
against PostgreSQL.

## What was decided

- **The unverified half of a decision I made is the requirement.** ADR-060's
  "same implementation, different URL" is what keeps REQ-INFRA-002 true through
  the migration, and it is currently a sentence in a document. Writing a
  sentence is not the same as it being so.
- **[[ADR-002]] already settled the principle** for storage, and acted on it:
  MinIO rather than a local directory, because developing against a filesystem
  and switching later reintroduces the divergence Principle VII exists to
  prevent. The catalog is the same shape of question and gets the same answer.
- **A synchronous driver is needed and is not a new decision.** `pyiceberg`'s
  SQL catalog goes through SQLAlchemy; `asyncpg` is asynchronous and serves the
  API. PRD §7 names both tools, so this requirement is not choosing a stack.
- **Scope is the catalog opening, committing and reading there.** What creates a
  namespace in a real deployment is deployment work, which Phase 8 lists
  separately — named rather than quietly folded in.

## What is still open

- **Nothing runs on the stack.** This proves a capability, not an operation.
