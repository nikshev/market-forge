---
traces: [REQ-PHASE-0, REQ-PHASE-1, REQ-PHASE-1A, REQ-PHASE-2, REQ-PHASE-3, REQ-PHASE-4, REQ-PHASE-5, REQ-PHASE-6, REQ-PHASE-7, REQ-PHASE-7A, REQ-PHASE-8]
status: draft
---

# Feature Specification: Phase coverage and the last derived acceptance criteria

**Feature Branch**: `phase-coverage`

**Created**: 2026-09-09

**Input**: PRD §45's eleven phases — three without acceptance criteria, and none with a way to say what delivers them.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Give the last three phases acceptance criteria (Priority: P1)

Phases 5, 6 and 8 state deliverables and stop. Ten notes carried the
`ACCEPTANCE-NOT-SPECIFIED` marker; these are the last three.

**Why this priority**: a requirement cannot honestly leave `draft` while nobody
can say what would satisfy it, and three of the eleven phases were stuck there.

**Acceptance Scenarios**:

1. **Given** a phase with no PRD criteria, **When** criteria are written, **Then** each line names the PRD section it is derived from.
2. **Given** the derivation, **When** it is read, **Then** it says what was deliberately left out and why.
3. **Given** the vault, **When** it is scanned, **Then** no requirement note carries the marker.
4. **Given** the extractor re-run over a section with no criteria, **When** it writes a note, **Then** the marker comes back and the scan fails.

---

### User Story 2 - Say what delivers each phase, and what does not (Priority: P1)

Two lists per phase: the requirements that deliver it, and the deliverables
nothing does.

**Why this priority**: a phase is a roll-up, and no validator rule reads a
roll-up. Without the lists, a phase's status is an opinion.

**Acceptance Scenarios**:

1. **Given** any phase note, **When** its frontmatter is read, **Then** it carries both lists, even when one is empty.
2. **Given** a covering requirement, **When** it is looked up, **Then** it exists as a requirement note.
3. **Given** a covering requirement, **When** its status is read, **Then** it is `implemented` or later.
4. **Given** a phase at `implemented` or later, **When** its undelivered list is read, **Then** it is empty.

---

### User Story 3 - Move every phase off `draft` to the rung the evidence supports (Priority: P1)

**Why this priority**: eleven notes sitting at `draft` say nothing about a
system where most of the work is built. A status that is checked is worth more
than a status that is generous.

**Acceptance Scenarios**:

1. **Given** a phase whose covering requirements are all implemented and whose undelivered list is empty, **When** its status is set, **Then** `implemented` is available to it.
2. **Given** a phase with any undelivered deliverable, **When** its status is set, **Then** it stops at `planned` and the note says which deliverable.
3. **Given** every phase today, **When** the statuses are read, **Then** all eleven are `planned`, because all eleven have a gap.

---

### Edge Cases

- What happens when a phase covers nothing at all? Its `covers:` list is empty and every deliverable is in the other list — which is Phase 8.
- What happens when a covering id is misspelled? The lookup fails, because a typo in a coverage claim reads exactly like coverage.
- What happens when a new phase note is added? The completeness test fails until it is checked too.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Phases 5, 6 and 8 MUST carry acceptance criteria, each line naming the PRD section it is derived from.
- **FR-002**: The derivation MUST be recorded, including what was deliberately not made a criterion.
- **FR-003**: No requirement note MUST carry the `ACCEPTANCE-NOT-SPECIFIED` marker, and its reappearance MUST fail loudly.
- **FR-004**: Every phase note MUST carry `covers:` and `not_delivered:` lists, even empty ones.
- **FR-005**: Every covering requirement MUST exist and MUST have reached `implemented`.
- **FR-006**: A phase at `implemented` or later MUST have an empty `not_delivered:` list.
- **FR-007**: Every phase note MUST be checked by one of these tests, and a new note MUST fail until it is.
- **FR-008**: Every phase MUST hold the highest status its evidence supports, and no higher.

### Key Entities

- **Phase note**: PRD §45's deliverables, its acceptance criteria, and the two coverage lists.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Phases 5, 6 and 8 carry criteria; every line cites a section.
- **SC-002**: A derivation document exists and names its exclusions.
- **SC-003**: A scan of the requirement notes finds no marker.
- **SC-004**: All eleven phase notes carry both lists.
- **SC-005**: Every id in every `covers:` list resolves to a note at `implemented` or later.
- **SC-006**: No phase is at `implemented` with a non-empty gap list.
- **SC-007**: The set of phase notes on disk equals the set the tests check.
- **SC-008**: All eleven phases are `planned`.

## Assumptions

- **A phase is its deliverables.** A phase with one missing deliverable is a phase in progress, however much of it is built — which is why every phase stops at `planned` today.
- **The PRD is unchanged.** The derived criteria live in the notes and in the derivation document; nothing was written into `channel_flow_prd_codex_ua_v5.md`.
- **`covers:` is advisory to the graph.** `collect_requirements` ignores unknown frontmatter keys, so the lists are checked by a test rather than by a validator rule — the same arrangement `hard_gated` had before R5 existed.
