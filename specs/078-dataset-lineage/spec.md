---
traces: [REQ-WP-040]
status: draft
---

# Feature Specification: A registration names the dataset it was trained on

**Feature Branch**: `wp-040-dataset-lineage`

**Created**: 2026-09-11

**Status**: Draft

**Input**: REQ-WP-040.

## Context

PRD §0 item 13 asks a result to be reproducible from four things. Three are
recorded and the fourth — the versioned dataset — has no field anywhere in the
chain: not on the registration, not on the certified dataset it was built from.

So a registration today supports one claim and not the other. You can rebuild
the model: the code commit, the hyperparameters and the artifact hash are all
there. You cannot rebuild the *result*, because the same code and the same
weights over a different slice of history give a different number and nothing
says which slice it was.

**The failure is silent by construction.** A run with no dataset recorded does
not look incomplete — it looks like every other run, and `require_registered`
passes it. The absence is only visible to somebody who goes looking for the
field and finds there isn't one.

[[REQ-WP-038]]'s retention is waiting on this: it keeps the snapshots a lineage
names, and there is no lineage to read.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A result names its data (Priority: P1)

**Acceptance Scenarios**:

1. **Given** a study over a dataset, **When** its registrations are read, **Then** each names the table, the snapshot and that snapshot's content hash.
2. **Given** a registration with no dataset, **When** it is built, **Then** it is refused.
3. **Given** two runs over the same rows, **When** their datasets are compared, **Then** the content hashes match.

---

### User Story 2 - A vanished dataset is visible (Priority: P1)

**Acceptance Scenarios**:

1. **Given** a registration whose snapshot has been expired, **When** its dataset is resolved, **Then** the answer says it is gone rather than raising.
2. **Given** a registration whose snapshot exists but now holds different rows, **When** it is resolved, **Then** the mismatch is reported, not the id's mere presence.
3. **Given** a resolvable dataset, **When** it is resolved, **Then** it reads back.

---

### User Story 3 - Retention reads the lineage (Priority: P1)

**Acceptance Scenarios**:

1. **Given** a registry holding registrations over a table, **When** retention asks for pins, **Then** it gets the snapshots those registrations name.
2. **Given** a pass using those pins, **When** it runs, **Then** every snapshot a registration names survives.
3. **Given** a registry holding nothing for that table, **When** pins are asked for, **Then** the answer is empty and says so, rather than pruning being quietly unprotected.

### Edge Cases

- **A registration over a table that no longer exists.** Reported as unresolvable, not as an error: the run happened, and the record of it is still worth reading.
- **Two registrations naming one snapshot.** One pin.
- **A snapshot named by a registration and older than every policy.** It survives. That is the point.
- **A dataset whose content hash matches but whose snapshot id differs.** The same rows under a different name; reported as resolved, because identity is the rows ([[ADR-053]]).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A registration MUST name the table, the snapshot and the snapshot's content hash.
- **FR-002**: A registration without a dataset MUST be refused, not defaulted.
- **FR-003**: Resolving a dataset MUST distinguish present-and-matching, present-and-different, and gone.
- **FR-004**: An unresolvable dataset MUST NOT prevent the registration from being read.
- **FR-005**: Retention MUST be able to obtain pins from the registry.
- **FR-006**: An empty pin set MUST be distinguishable from pins nobody asked for.
- **FR-007**: The other eleven §23.9 fields MUST be unchanged.

### Key Entities

- **Dataset origin**: which table, which snapshot, and what was under it.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every registration a study writes carries a resolvable dataset.
- **SC-002**: A registration built without one is refused.
- **SC-003**: An expired snapshot resolves as gone; a changed one resolves as different.
- **SC-004**: Retention pins read from a registry keep every named snapshot alive.
- **SC-005**: Every existing registry test passes unchanged but for the new field.

## Assumptions

- **One dataset per registration.** A run reads one table at one snapshot, so
  one origin is right. A walk-forward study over several tables would need more,
  and nothing does that yet.
- **Resolution is by content hash, not by id.** An id is a name and a hash is a
  claim about what was under it — [[ADR-053]]'s distinction, applied to the
  citation rather than to the dataset.
- **The origin is supplied, not inferred.** Whoever built the dataset knows
  which snapshot they read; a layer that guessed would guess wrong exactly when
  a table has moved on.

## Open Questions

- **Whether `require_registered` should refuse an unresolvable dataset.** It
  would make a stale citation fatal at the point of use, and it would also make
  a report unreadable after a legitimate retention pass.
