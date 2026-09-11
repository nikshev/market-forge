---
traces: [REQ-WP-039]
status: draft
---

# Feature Specification: The canonical plane migrates to Apache Iceberg

**Feature Branch**: `wp-039-iceberg`

**Created**: 2026-09-11

**Status**: Draft

**Input**: REQ-WP-039, following [[ADR-060]].

## Context

[[ADR-002]] chose "Parquet on S3-compatible object storage with Iceberg table
semantics". What was built implements those semantics by hand. [[REQ-WP-038]]
found where the implementation and the format part company: our table can only
append, so no operation it offers makes a data file unreferenced, so retention
has nothing to free.

**The migration's failure mode is not a crash.** It is arriving with a working
Iceberg table that has quietly stopped doing one of the things the old one
guaranteed. There are nine of those, every one is depended on by something, and
none of them announces itself when it goes.

The dangerous ones are the quiet ones. A point-in-time read that silently starts
including later rows still returns a table. A content hash that changes because
the writer changed still returns a hash. A commit race that silently merges
still leaves the data readable. Each is a green test suite away from being
noticed, and each destroys a claim the PRD makes.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The past does not change (Priority: P1)

**Acceptance Scenarios**:

1. **Given** a table read at an instant, **When** later rows are appended, **Then** the earlier read returns what it returned before.
2. **Given** a snapshot, **When** it is read by id, **Then** it returns exactly the rows that commit could see.
3. **Given** rows carrying an event time, **When** a read asks for an instant, **Then** rows with a later event time are absent.

---

### User Story 2 - A commit is all or nothing (Priority: P1)

**Acceptance Scenarios**:

1. **Given** two writers committing from the same parent, **When** both commit, **Then** one wins and one is refused, and no state mixes the two.
2. **Given** a refused commit, **When** the table is read, **Then** nothing of it is visible.

---

### User Story 3 - A dataset keeps its name (Priority: P1)

**Acceptance Scenarios**:

1. **Given** the same rows written twice in separate processes, **When** each content hash is taken, **Then** they are equal.
2. **Given** a table on the new format, **When** a snapshot's identity is read, **Then** it is derived from rows, not from an allocated id.

---

### User Story 4 - The callers do not notice (Priority: P2)

**Acceptance Scenarios**:

1. **Given** the domain tables, **When** they are read and written, **Then** their call sites are unchanged.
2. **Given** the fast gate, **When** it runs, **Then** it needs no service.

---

### User Story 5 - Retention becomes possible (Priority: P1)

**Acceptance Scenarios**:

1. **Given** a table with rows past a cutoff, **When** they are deleted and the old snapshots expired, **Then** files nothing references remain identifiable.
2. **Given** that state, **When** the unreferenced files are removed, **Then** the table still reads and the bytes are gone.

### Edge Cases

- **A table with no event-time column.** Point-in-time reads are meaningless and must be refused, not silently answered with everything.
- **A read at an instant before any data.** Empty, and not an error: nothing was knowable then, which is a true answer.
- **An empty append.** Refused: a commit that adds nothing is a snapshot that says something happened when it did not.
- **A schema the table does not have.** Refused at write, as today.
- **Two processes creating the same table at once.** One creates it, the other finds it; neither gets a half-created table.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A read at an instant MUST exclude rows whose event time is later.
- **FR-002**: Appending MUST NOT change what an earlier read returns.
- **FR-003**: A read by snapshot MUST return exactly that commit's visible rows.
- **FR-004**: A losing commit in a race MUST be refused, with nothing of it visible.
- **FR-005**: Dataset identity MUST be a hash of rows, stable across processes and library versions ([[ADR-053]]).
- **FR-006**: A point-in-time read on a table with no event time MUST be refused.
- **FR-007**: An empty append MUST be refused.
- **FR-008**: The fast gate MUST run with no services.
- **FR-009**: Files no live snapshot references MUST be identifiable, so retention can remove them.
- **FR-010**: The domain tables' call sites MUST be unchanged.

### Key Entities

- **Table**: a named, schema'd, append-only dataset with a readable history.
- **Snapshot**: one commit, and the rows it could see.
- **Catalog**: where tables are found; a file locally, a database on the stack.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A read at an instant, repeated after later appends, returns the same rows.
- **SC-002**: Two commits from one parent produce one winner and one refusal.
- **SC-003**: The same rows written in two processes produce one hash.
- **SC-004**: A point-in-time read without an event-time column is refused.
- **SC-005**: After a delete and an expiry, the unreferenced files are listed, and removing them leaves the table readable.
- **SC-006**: `make test-fast` passes with no containers running.
- **SC-007**: Every existing lakehouse behaviour has an equivalent test on the new format.

## Assumptions

- **This step adds the format; it does not remove the old one.** The migration
  is staged, and the requirement stays open until the last caller moves.
  A half-migrated plane is the state to leave quickly, not to settle in.
- **The catalog is `pyiceberg`'s SQL catalog**, SQLite-backed for local and CI
  runs, PostgreSQL-backed on the stack: the same implementation with a different
  URL, which is the line [[ADR-002]] drew between a test double and a second
  production path.
- **Identity stays ours.** Iceberg allocates snapshot ids, so two runs over
  identical data get different ones. PRD §0 item 13 rests on a hash of the rows,
  and that continues to be computed here.

## Open Questions

- **Whether point-in-time reads use a row filter or a snapshot lookup.** Iceberg
  offers both; they differ when a commit carries rows older than its
  predecessor, which this system's replays do.
- **Where the catalog lives on the stack**, and who creates the namespace.
