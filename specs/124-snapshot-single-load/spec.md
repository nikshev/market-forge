---
traces: [REQ-WP-079]
status: draft
---

# Feature Specification: A snapshot read resolves its snapshot against the table it reads

**Feature Branch**: `124-snapshot-single-load`

**Created**: 2026-10-03

**Status**: Draft

**Input**: [[REQ-WP-079]] — PRD §6.4 (Iceberg tables "where snapshot isolation, schema
evolution, partition evolution and reproducibility matter") and §7.

## Context

On 2026-10-03, the morning after [[REQ-WP-078]] closed, the deployment's own logs held a
failure nobody had caused and no test had seen: `NoSuchSnapshot: bars has no snapshot 4424; it
has (1, 2, 3, …)`. It appeared ten times in the channel worker and four times in the resample
job overnight. Three of the resample's four were caught per series and skipped for one pass; the
fourth was raised outside that handler and ended the process.

The cause is in how the newest snapshot of a table is found. A read asks the catalog for the
table, then asks again for the list of snapshots to learn which is newest, and then looks that
number up in the **first** answer. Five ingest processes and the resample job all commit to the
`bars` table. When one commit lands between the two questions, the second answer names a
snapshot the first has never heard of.

The reading operations that ask twice, or three times, are the ones everything else is built on:
reading the newest snapshot, naming the current one, and describing a snapshot by number. Their
callers include the worker's replay, model registry lookups and the research reads, so a fault
here is not a resample fault.

### What this is not

It is not a retry. A caller that catches `NoSuchSnapshot` and reads again would hide the fault,
and would also hide the case where the snapshot genuinely does not exist, which must keep
raising. It is not a fix for write conflicts (the writer's library already retries those), for
snapshot expiry, or for making the resample job survive an unrelated failed read; each is a
separate decision.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The newest snapshot is read from one version of the table (Priority: P1)

The channel worker, the resample job, the replay and the research reads each ask for "the newest
snapshot of this table". The answer must be a snapshot that belongs to the version of the table
they are reading, however many other processes commit while they do.

**Why this priority**: it is the observed fault, it recurs about once an hour, and it grows with
the number of writers.

**Independent Test**: a catalog whose successive loads of a table return successive versions,
each one commit newer than the last, makes the race happen on every call instead of once an
hour. Reading the newest snapshot against it fails today with `NoSuchSnapshot` and succeeds when
the read uses one version.

**Acceptance Scenarios**:

1. **Given** a table that gains a commit between any two loads of it, **When** the newest
   snapshot is read, **Then** the rows returned are those of one snapshot that exists in the
   version read, and no error is raised.
2. **Given** the same table, **When** the current snapshot is described, **Then** the
   description is of a snapshot that exists in the version read.
3. **Given** the same table, **When** a snapshot is described by number, **Then** a number that
   exists in the version read is described and no other load can make it vanish.

---

### User Story 2 - Pinned reads stay reproducible and honest (Priority: P1)

A run that recorded "snapshot 3" must read the same rows again later, and a number that does not
exist must still be refused, by name.

**Why this priority**: the fix touches the code that carries PRD §0 item 13 (results are
reproducible, [[REQ-PRIN-013]] and Principle XI); a fix that made the race disappear by
tolerating a missing snapshot would trade a loud fault for a silent one.

**Independent Test**: read a pinned snapshot, commit more, read it again, compare; ask for a
number the table does not have and read the error.

**Acceptance Scenarios**:

1. **Given** a pinned snapshot that exists, **When** later commits land and it is read again,
   **Then** the rows are identical.
2. **Given** a snapshot number the table does not have, **When** it is read or described,
   **Then** `NoSuchSnapshot` is raised naming the snapshots that do exist.
3. **Given** a table nothing has been committed to, **When** the newest snapshot is read,
   **Then** the answer is the same empty result it is today.

---

### User Story 3 - The fault is gone from the running deployment (Priority: P2)

**Why this priority**: the log is where it was found, so the log is where it is shown to be gone.

**Independent Test**: after deployment, the `worker` and `resample` logs over a full day hold no
`NoSuchSnapshot`, with the date recorded. Beside a real catalog, a reader looping beside a writer
looping completes without it; that is evidence, not proof, because the deterministic test above
is what proves the single load.

**Acceptance Scenarios**:

1. **Given** the deployed stack with five writers, **When** a full day passes, **Then** neither
   the worker nor the resample log contains `NoSuchSnapshot`.

### Edge Cases

- A commit lands **after** the single load: the read returns the snapshot that was newest in the
  version it loaded, a moment old. That is not look-ahead (Principle I): it is the same answer a
  reader who arrived a moment earlier would have got.
- A snapshot is expired between a pinned read and a later one: out of scope (retention), and the
  error must remain the honest one.
- A table that does not exist yet.
- Snapshot numbers that are not contiguous after expiry: the existing behaviour, by sequence
  number rather than position, is preserved.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Reading the newest snapshot of a table MUST resolve the snapshot and read its rows
  against one version of the table.
- **FR-002**: Describing the current snapshot MUST resolve against one version of the table.
- **FR-003**: Describing a snapshot by number MUST check that it exists and describe it against
  the same version.
- **FR-004**: A snapshot number the version does not have MUST raise `NoSuchSnapshot` naming the
  snapshot numbers it does have, as today.
- **FR-005**: A pinned read of an existing snapshot MUST return the same rows regardless of later
  commits.
- **FR-006**: A table with no commits MUST read as the empty result and describe as no current
  snapshot, as today.
- **FR-007**: No caller may be made to tolerate `NoSuchSnapshot`; the fix lives in the layer that
  produces it.
- **FR-008**: The test that proves FR-001 to FR-003 MUST fail against today's code for the stated
  reason (Principle XIV; the repository's RED discipline).

### Key Entities

- **Table version**: what one load of a table from the catalog returns — its snapshots at that
  moment. A later load may hold more snapshots; it never holds fewer except by expiry.
- **Snapshot number**: the commit sequence number this system calls a snapshot id; it survives
  expiry.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Against a table that gains a commit between every two loads, 1,000 reads of the
  newest snapshot raise no `NoSuchSnapshot` (today: every one does).
- **SC-002**: After deployment, 24 hours of the five-writer stack leave zero `NoSuchSnapshot` in
  the `worker` and `resample` logs (today: 14 in about 13 hours).
- **SC-003**: Every existing lakehouse test passes unchanged; a pinned read before and after later
  commits returns identical rows.
- **SC-004**: The resample job does not exit because of this fault (today: once in 13 hours).

## Assumptions

- The catalog returns a consistent version of a table on each load; the fault is asking twice.
- Snapshots are only added during normal operation; they are removed only by the retention pass,
  which is not concurrent with the readers named here.
- The pyiceberg library's own retry of write conflicts is adequate and is not touched.
- Making `resample` survive an unrelated failed read at its first read is a separate decision and
  stays out of this change.
