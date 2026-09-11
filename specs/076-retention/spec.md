---
traces: [REQ-WP-038]
status: draft
---

# Feature Specification: Retention expires by policy, never what a lineage names

**Feature Branch**: `wp-038-retention`

**Created**: 2026-09-11

**Status**: Draft

**Input**: REQ-WP-038 — one of Phase 8's five remaining deliverables.

## Context

PRD §6.4.9 asks for retention configurable per event family and says, in the
same breath, "suggested semantics, **not hard-coded durations**". The section
declines to name a number; so does this.

Retention is the only operation in this system that destroys. Everything else
appends, and the whole plane is built on that — which means the ways retention
can go wrong are not the ways the rest of the code can go wrong.

**It can expire the thing that made a result checkable.** §6.4.9's Tier D is
"retained by experiment/model lineage policy": a snapshot an experiment names
must survive however old it is. Expiring one destroys §0 item 13's
reproducibility in the quietest way available — the model still loads, the
config still reads, and the run simply stops being checkable. Nothing fails.

**It can leave the corruption the writer refuses to create.** A commit writes
data files before the manifest naming them, because orphans are invisible and a
manifest over absent files is not. Removal is the same rule backwards: the
manifest goes first, and only then what it named. Prune in the writing order and
there is a window where the table is broken — and if the pass dies in that
window, permanently.

**It can leave nothing to read.** A policy aggressive enough to expire the
newest snapshot produces a table with no current state. That is not a retained
table; it is a deleted one with extra steps.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Nothing a lineage names is expired (Priority: P1)

**Acceptance Scenarios**:

1. **Given** an old snapshot named as pinned, **When** retention runs, **Then** it survives.
2. **Given** a pinned snapshot older than every other, **When** retention runs, **Then** the table still reads at it.
3. **Given** no pins at all, **When** retention runs, **Then** it prunes by age alone and says that no pins were supplied.

---

### User Story 2 - A pruned table is still a table (Priority: P1)

**Acceptance Scenarios**:

1. **Given** any policy, **When** retention runs, **Then** the newest snapshot survives.
2. **Given** a pruned table, **When** it is read, **Then** the current state is unchanged.
3. **Given** a pruned table, **When** a surviving snapshot is read, **Then** it reads.
4. **Given** a pruned table, **When** it is verified, **Then** no manifest names an absent file.

---

### User Story 3 - Removal is the inverse of writing (Priority: P1)

**Acceptance Scenarios**:

1. **Given** a retention pass interrupted partway, **When** the table is verified, **Then** no surviving manifest names an absent file.
2. **Given** the same interrupted pass, **When** it is re-run, **Then** it completes.

---

### User Story 4 - Durations are the caller's (Priority: P2)

**Acceptance Scenarios**:

1. **Given** two different policies, **When** each runs on the same table, **Then** they expire different snapshots.
2. **Given** a report, **When** it is read, **Then** it names what was expired and what was kept, with the reason for each keep.

### Edge Cases

- **A file still named by a surviving snapshot.** Manifests are cumulative, so an old file is named by every later manifest. It is removed only when no surviving manifest names it — which, for a cumulative history, means almost never, and that is correct rather than disappointing.
- **A policy that would expire everything.** The newest snapshot survives regardless, and the report says the policy was clamped.
- **A pin naming a snapshot that does not exist.** Refused: a pin nobody can honour is more likely a typo than a wish, and honouring it silently means pruning something somebody meant to keep.
- **An empty table.** Nothing to expire, and not an error.
- **Running twice.** The second pass expires nothing and says so.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Every duration MUST be an argument; no duration may be written into the code.
- **FR-002**: A pinned snapshot MUST NOT be expired, whatever its age.
- **FR-003**: The newest snapshot MUST NOT be expired, whatever the policy.
- **FR-004**: A manifest MUST be removed before the files it uniquely named.
- **FR-005**: A data file MUST NOT be removed while any surviving manifest names it.
- **FR-006**: An interrupted pass MUST leave a table in which no manifest names an absent file.
- **FR-007**: A report MUST name what was expired and what was kept, with the reason for each keep.
- **FR-008**: The ability to delete MUST be available to retention and not to the table layer.
- **FR-009**: A pin naming an absent snapshot MUST be refused.
- **FR-010**: The round trip MUST be verified against a real object store in CI.
- **FR-011**: Nothing existing MUST change.

### Key Entities

- **Retention policy**: how long a family of data is worth keeping, expressed by the caller.
- **Pin**: a snapshot something else depends on, which age does not reach.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A pinned snapshot older than the cutoff survives and reads.
- **SC-002**: The newest snapshot survives a policy that would expire it.
- **SC-003**: A pruned table verifies clean under [[REQ-WP-037]]'s check.
- **SC-004**: An interrupted pass verifies clean and completes on a re-run.
- **SC-005**: Two policies over one table expire different sets.
- **SC-006**: A report names each kept snapshot's reason.
- **SC-007**: The pass runs against MinIO in CI.

## Assumptions

- **Tiers A and C have no store.** Tier A is Pinot, deferred by [[ADR-002]];
  Tier C is a raw archive nothing writes. This covers Tier B, the canonical
  plane, and Tier D, its research artifacts. That is not deferred work hiding
  here — there is nothing to retain.
- **Pins are supplied, not discovered.** `Registration` does not record which
  dataset snapshot a model was trained on, so there is no lineage to read. The
  requirement names that gap; retention takes pins as an argument and will read
  lineage the day something records it.
- **Verification is [[REQ-WP-037]]'s.** A pruned table is checked with the same
  function a restored one is, because "no manifest names an absent file" is the
  same property whichever operation might have broken it.

## Open Questions

- **Whether an unpinned prune should require an explicit acknowledgement.**
  Pruning with no pins is legitimate and is also exactly what someone does by
  accident when the lineage source is missing.
- **Nothing schedules a pass**, as nothing schedules a backup.
