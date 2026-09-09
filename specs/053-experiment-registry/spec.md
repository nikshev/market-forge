---
traces: [REQ-REPRO-001, REQ-BIAS-011]
status: draft
---

# Feature Specification: Run identity, the experiment registry, and the reporting gate

**Feature Branch**: `repro-001-experiment-registry`

**Created**: 2026-09-09

**Input**: REQ-REPRO-001 — PRD §0 item 13's four hashes, §41 rule 11, §29.B's registry tables.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Identify a run by all four of PRD §0 item 13's components (Priority: P1)

Dataset, config, code commit, model artifact.

**Why this priority**: it is the sentence the whole of Phase 6's
"reproducible reports" rests on, and three of the four hashes did not exist.

**Acceptance Scenarios**:

1. **Given** all four components, **When** the run is checked, **Then** it is reproducible.
2. **Given** a run that fits no model, **When** it is checked, **Then** it is still reproducible.
3. **Given** a run whose model artifact nobody recorded, **When** it is checked, **Then** it is not, and the two cases are distinguishable.
4. **Given** a commit taken from a dirty working tree, **When** the run is checked, **Then** it is not reproducible.
5. **Given** several missing components, **When** the run is checked, **Then** all of them are named at once.
6. **Given** the same four components, **When** hashed in any process, **Then** the run hash is the same; any change to any of them changes it.

---

### User Story 2 - Hash a dataset and a config deterministically (Priority: P1)

**Why this priority**: two of the four components are not hashes to begin with —
a run reads several tables, and a config is a nested mapping with no schema.

**Acceptance Scenarios**:

1. **Given** a config, **When** its keys are written in a different order, **Then** it hashes the same.
2. **Given** two configs differing anywhere — including only in a value's type — **When** they are hashed, **Then** they differ.
3. **Given** a config holding something with no canonical encoding, **When** it is hashed, **Then** it is refused rather than rendered.
4. **Given** several tables at their snapshots, **When** the dataset reference is built, **Then** it does not depend on the order they were listed in and does depend on both the snapshot id and its content hash.
5. **Given** no tables, or a table with no content hash, **When** a reference is built, **Then** it is refused.

---

### User Story 3 - Record every variant and gate every report (Priority: P1)

**Why this priority**: PRD §41 rule 11 and §0 item 13 are both unenforceable as
storage. They become enforceable as a precondition of reporting.

**Acceptance Scenarios**:

1. **Given** a discarded variant, **When** the study is recorded, **Then** it is stored exactly like the one that was kept.
2. **Given** an unreproducible run, **When** it is recorded, **Then** it is stored as unreproducible with the reason, rather than refused.
3. **Given** the registry, **When** more runs are appended, **Then** its earlier history is unchanged.
4. **Given** an unreproducible run, **When** a result is published from it, **Then** the publication is refused and names the missing component.
5. **Given** a field containing a variant that is not in the registry, **When** a winner is published, **Then** the publication is refused.
6. **Given** a winner that is not in its own field, or a field counting one variant twice, **When** it is published, **Then** it is refused.

---

### Edge Cases

- What happens when a study compared nothing? A field of one is a legitimate report — of a study that compared nothing.
- What happens to a config value that is `None`? It is a value, not an absence: `{"stop": None}` and `{}` are different configs.
- What happens when someone never mentions a variant at all? Nothing here catches it, and the module says so rather than implying otherwise.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A run identity MUST carry all four components, each present or explicitly absent.
- **FR-002**: "Fits no model" and "artifact unrecorded" MUST be distinguishable, and only the second MUST make a run unreproducible.
- **FR-003**: A commit from a dirty tree MUST make a run unreproducible, and a commit that is not a full hash MUST be refused.
- **FR-004**: Every missing component MUST be named at once.
- **FR-005**: The run hash MUST cover all four components and the dirty flag, and MUST be framed so no component can borrow a character from the next.
- **FR-006**: A config MUST hash independently of key order and differently for any difference, including a difference of type.
- **FR-007**: A config value with no canonical encoding, and a non-string key, MUST be refused.
- **FR-008**: A dataset reference MUST cover each table's snapshot id and content hash, MUST NOT depend on their order, and MUST refuse an empty set or a missing content hash.
- **FR-009**: Every run MUST be recorded whatever its outcome, and an unreproducible run MUST be recorded as such with its reason.
- **FR-010**: The registry MUST be append-only with an immutable history, and MUST read back identities and outcomes intact.
- **FR-011**: A report MUST be refused unless its run is reproducible, naming the missing component.
- **FR-012**: A report MUST be refused unless every variant in the winner's field is in the registry, the winner is in it, and no variant appears twice.
- **FR-013**: Nothing in the package MUST read a clock or shell out to git.

### Key Entities

- **Run identity**: PRD §0 item 13's four components and whether they add up.
- **Run**: one variant of one experiment, its identity, and what became of it.
- **Report**: a result that has passed both gates.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A complete identity is reproducible; a dirty tree and an unrecorded artifact each are not; "no model" is.
- **SC-002**: Two missing components produce two named gaps.
- **SC-003**: An abbreviated, empty or upper-case commit is refused.
- **SC-004**: Changing any of the four components changes the run hash; a dirty run and its clean commit differ.
- **SC-005**: Two components cannot borrow a character from each other.
- **SC-006**: Key order does not change a config hash; a quoted flag, a quoted number and a changed nesting all do.
- **SC-007**: An opaque object and a non-string key are refused.
- **SC-008**: A dataset reference is order-independent and changes with snapshot or content; empty, hashless and zero-snapshot references are refused.
- **SC-009**: Three variants recorded, one kept and two discarded, all read back.
- **SC-010**: An unreproducible run is on record with its reason.
- **SC-011**: The registry's first snapshot is unchanged after a second append.
- **SC-012**: A dirty run and an unrecorded artifact each stop a report.
- **SC-013**: An unrecorded variant, a winner outside its field, and a duplicated variant each stop a report.
- **SC-014**: A field of one publishes.
- **SC-015**: No module in the package reaches for a clock or for git.

## Assumptions

- **The commit and the dirty flag are supplied.** A library that shells out to `git` cannot be tested and answers about whatever directory it is in.
- **A model artifact's hash is supplied.** Its format belongs to whatever produced it.
- **Nothing adopts the registry automatically.** Each experiment reports through it as its own step, which is why [[REQ-BIAS-011]] stops at `specified`.
