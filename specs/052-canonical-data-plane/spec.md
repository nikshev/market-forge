---
traces: [REQ-STORE-001]
status: draft
---

# Feature Specification: Canonical Parquet data plane and DuckDB research reads

**Feature Branch**: `store-001-lakehouse`

**Created**: 2026-09-09

**Input**: REQ-STORE-001 — PRD §7's target storage profile, §29.0's deployment profiles, §29.B's canonical tables.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Commit data as immutable snapshots (Priority: P1)

A table's history is a chain; appending adds to it and changes nothing already
in it.

**Why this priority**: PRD §0 item 5 forbids rewriting finalized snapshots, and
a storage layer that allowed it would make that rule unenforceable one level
above.

**Acceptance Scenarios**:

1. **Given** a committed snapshot, **When** more data is appended, **Then** the earlier snapshot's files, counts and identity are unchanged.
2. **Given** an older snapshot, **When** it is read, **Then** it returns exactly what it held.
3. **Given** two writers racing for one version, **When** one wins, **Then** the other is refused and the table is unchanged.
4. **Given** a data file with no manifest, **When** the table is read, **Then** the file is invisible.
5. **Given** an append of no rows, **When** it is attempted, **Then** it is refused.
6. **Given** an append under a different schema, **When** it is attempted, **Then** it is refused.

---

### User Story 2 - Name a dataset so a research run can be pinned to it (Priority: P1)

A content hash over the rows, not over the files.

**Why this priority**: PRD §29.B requires "dataset lineage/snapshot
reproducibility" and PRD §0 item 13 requires a result reproducible from a
versioned dataset. A version that changes when a library is upgraded is not one.

**Acceptance Scenarios**:

1. **Given** the same rows written to two different stores, **When** their identities are compared, **Then** they are the same.
2. **Given** one value changed, **When** identities are compared, **Then** they differ.
3. **Given** identical rows in files written by different library versions, **When** identities are compared, **Then** they are the same and the file digests differ.
4. **Given** a renamed or reordered column, **When** identities are compared, **Then** they differ.
5. **Given** a manifest edited after it was committed, **When** it is read, **Then** it is refused.

---

### User Story 3 - Read as of an instant, and query a snapshot (Priority: P1)

**Why this priority**: PRD §24.1's invariant is where look-ahead enters a
research pipeline, and PRD §29.0 names DuckDB as the way research reads this
plane.

**Acceptance Scenarios**:

1. **Given** an as-of instant, **When** a table is read, **Then** nothing later than it is returned, and a row at exactly that instant is.
2. **Given** a table with no event-time column, **When** a point-in-time read is asked of it, **Then** it is refused.
3. **Given** a snapshot, **When** it is queried through DuckDB, **Then** the table is visible under its own name.
4. **Given** an orphaned file under the data prefix, **When** a query runs, **Then** it is not read.
5. **Given** a query, **When** it finishes, **Then** its extract no longer exists.

---

### Edge Cases

- What happens when a backend cannot promise a conditional write? It is refused rather than emulated with a read followed by a write.
- What happens when a table has never been committed to? It has no current snapshot, reads empty under its schema, and refuses a query.
- What happens to a value that is a Python `bool` in an integer column? Refused: `True == 1` in Python and not in a schema.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A snapshot MUST be immutable once committed.
- **FR-002**: A read at a snapshot MUST return what that snapshot held.
- **FR-003**: A commit MUST be atomic, and a lost race MUST leave the table unchanged.
- **FR-004**: A data file MUST NOT be readable before a manifest names it.
- **FR-005**: An empty append and an append under another schema MUST be refused.
- **FR-006**: A snapshot MUST carry a content hash over its logical content, never over its files' bytes.
- **FR-007**: The content hash MUST cover the schema, MUST NOT depend on file order, and MUST change with any change to the data.
- **FR-008**: Each file MUST also carry a digest of its stored bytes, reported separately.
- **FR-009**: A manifest MUST record its own content hash, and a disagreement MUST be refused.
- **FR-010**: A point-in-time read MUST return nothing later than the instant, inclusive of it.
- **FR-011**: A table with no event-time column MUST refuse a point-in-time read.
- **FR-012**: A snapshot MUST be queryable through DuckDB, over only the files its manifest names.
- **FR-013**: An extract MUST NOT outlive its query.
- **FR-014**: The object store MUST be reached through a port; a backend without conditional writes MUST be refused.
- **FR-015**: No signal or channel domain code MUST import this package or a storage backend.
- **FR-016**: Nothing in this package MUST read a clock.

### Key Entities

- **Object store**: four operations, one of which is conditional.
- **Schema**: ordered typed columns, an optional event-time column, and a fingerprint.
- **Snapshot**: files, parent, schema fingerprint, and a content hash.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An earlier snapshot is byte-for-byte the same after later appends.
- **SC-002**: A read at snapshot N ignores everything appended since.
- **SC-003**: A simulated race raises, leaves the winner's snapshot current, and leaves exactly one unreferenced file no query can see.
- **SC-004**: A stray data file does not appear in the chain or in a read.
- **SC-005**: The same rows in two stores share an identity; one changed value does not.
- **SC-006**: Two files with the same rows and different bytes share a snapshot identity.
- **SC-007**: A reordered or renamed schema is a different fingerprint.
- **SC-008**: A tampered manifest and a non-integer manifest field are both refused; an untouched one round-trips.
- **SC-009**: An as-of read includes its own instant and excludes the next.
- **SC-010**: A table without an event time refuses a point-in-time read.
- **SC-011**: A DuckDB query sees the manifest's files and not an orphan beside them.
- **SC-012**: An extract's directory is gone after the query.
- **SC-013**: A conditional write is refused by a real object store, not only by a double.
- **SC-014**: No domain package imports the lakehouse, pyarrow, duckdb or boto3.
- **SC-015**: No module in the package reaches for a clock.

## Assumptions

- **"Iceberg semantics" means the properties, not the file format.** §29.B needs immutable snapshots, atomic commits, versioned schemas and dataset lineage. Adopting the specification itself later means writing a compatible manifest, not changing what a dataset means.
- **The seventeen §29.B tables are not part of this.** This is the plane they sit on; each table arrives with the subsystem that produces it.
- **Pinot and Trino stay deferred**, by [[ADR-002]]: Pinot until a HOT serving requirement exists, Trino until the data outgrows one machine.
