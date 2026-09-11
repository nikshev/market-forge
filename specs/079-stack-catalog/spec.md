---
traces: [REQ-WP-041]
status: draft
---

# Feature Specification: The catalog the stack runs is the catalog CI proves

**Feature Branch**: `wp-041-stack-catalog`

**Created**: 2026-09-11

**Status**: Draft

**Input**: REQ-WP-041.

## Context

[[ADR-060]] made a claim and nothing has tested it: the catalog is one
implementation, SQLite locally and PostgreSQL on the stack, differing only in a
URL. That claim is what keeps REQ-INFRA-002's "a commit needs no running
service" compatible with a canonical plane that needs a catalog at all.

Every test opens SQLite. So the thing standing between "a test double behind a
port" and "a second production path" is a sentence.

**A catalog nobody has opened against PostgreSQL is a deployment waiting to find
out** — on the day something first runs there, which is the day a surprise costs
most. [[ADR-002]] reasoned exactly this way about storage and chose MinIO over a
local directory rather than accepting the same gap.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The same code opens both (Priority: P1)

**Acceptance Scenarios**:

1. **Given** a PostgreSQL URL, **When** a catalog is opened, **Then** it is opened by the same factory that opens a SQLite one.
2. **Given** either catalog, **When** the code is read, **Then** nothing branches on which it is.

---

### User Story 2 - A table lives there (Priority: P1)

**Acceptance Scenarios**:

1. **Given** a PostgreSQL-backed catalog, **When** a table is committed to, **Then** the commit lands and reads back.
2. **Given** several commits, **When** an earlier snapshot is read, **Then** it returns what that commit saw.
3. **Given** a point-in-time read, **When** it runs there, **Then** it excludes rows whose event time is later.

---

### User Story 3 - Configuration comes from outside (Priority: P2)

**Acceptance Scenarios**:

1. **Given** the stack's settings, **When** a catalog is built for it, **Then** the DSN comes from the environment.
2. **Given** no settings, **When** a catalog is asked for, **Then** the failure says the stack is not configured rather than failing to connect to a guess.

### Edge Cases

- **A database that is not running.** The failure names the stack, as the other integration fixtures do; a connection error alone sends somebody to the wrong question.
- **Two processes creating the same namespace.** One creates it, the other finds it, neither gets half of one.
- **A table name already in the catalog.** The same refusal as anywhere else.
- **The fast gate.** Untouched: nothing in it opens PostgreSQL.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: One factory MUST open both catalogs, with no branch on the URL's scheme.
- **FR-002**: A table MUST commit, read, time-travel and answer a point-in-time read through a PostgreSQL-backed catalog.
- **FR-003**: The DSN MUST come from the environment.
- **FR-004**: A missing configuration MUST fail by naming the stack.
- **FR-005**: The fast gate MUST still need no service.
- **FR-006**: The SQLite path MUST be unchanged.

### Key Entities

- **Catalog**: where tables are found; one implementation, two homes.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The round trip passes against the stack's PostgreSQL in CI.
- **SC-002**: The factory has no scheme-dependent branch.
- **SC-003**: `make test-fast` passes with no containers running.
- **SC-004**: Every existing lakehouse test passes unchanged.

## Assumptions

- **A synchronous driver joins the dependencies.** `pyiceberg`'s SQL catalog
  goes through SQLAlchemy; `asyncpg` is asynchronous and serves the API. PRD §7
  names both tools, so this is not a stack choice being made here.
- **The warehouse stays MinIO.** This is about where the *pointer* lives; the
  data plane is settled ([[ADR-002]]).
- **Nothing runs on the stack yet.** This proves a capability, not an operation,
  and deployment is a separate Phase 8 deliverable.

## Open Questions

- **Who creates the namespace in a real deployment**, and whether the catalog's
  schema needs a migration of its own. `pyiceberg` creates its tables on first
  use, which is convenient and is not a migration story.
