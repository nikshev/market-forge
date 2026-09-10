---
traces: [REQ-WP-031]
status: draft
---

# Feature Specification: Long/short positioning, and its absence

**Feature Branch**: `wp-031-long-short`

**Created**: 2026-09-10

**Status**: Draft

**Input**: REQ-WP-031 — Phase 3's last deliverable.

## Context

`DerivativesState` carries funding, open interest and basis and says nothing
about who is positioned which way. PRD §16 asks for "long/short squeeze context
where available".

The feature can go wrong in one specific way, and it is the way a sometimes-absent
field always goes wrong: **a venue that publishes no positioning is not a
balanced market.** A ratio of 1.0 says longs and shorts are even, which is a
reading. An absent ratio says nobody knows. Collapsing them puts a confident
"balanced" in front of every instrument on every venue that does not publish, and
nothing downstream ever sees a gap.

The second thing worth stating: a ratio alone is not context. 2.0 is ordinary on
one instrument and extreme on another, so crowding is measured against the
instrument's own recent positioning.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Positioning is carried, or its absence is (Priority: P1)

**Acceptance Scenarios**:

1. **Given** a venue publishing positioning, **When** state is read, **Then** both the account ratio and the top-trader ratio are available.
2. **Given** a venue publishing none, **When** state is read, **Then** the ratios are absent — not 1.0, not 0.
3. **Given** a venue publishing one and not the other, **When** state is read, **Then** the two are independent.

---

### User Story 2 - Crowding is relative to the instrument (Priority: P1)

**Acceptance Scenarios**:

1. **Given** an instrument whose ratio has been near 1.0 and is now 2.0, **When** crowding is read, **Then** it reads as unusual.
2. **Given** an instrument whose ratio is always near 2.0 and is now 2.0, **When** crowding is read, **Then** it reads as ordinary.
3. **Given** too little history to say what is usual, **When** crowding is read, **Then** it is refused rather than reported as average.

---

### User Story 3 - The same rules as its neighbours (Priority: P2)

**Acceptance Scenarios**:

1. **Given** a stale positioning reading, **When** it is read, **Then** it is refused as a stale funding reading is.
2. **Given** the registry, **When** the new features are looked up, **Then** each states its null policy.
3. **Given** the existing derivatives features, **When** they are computed, **Then** nothing about them changed.

### Edge Cases

- **A ratio of exactly 1.0.** A real reading: perfectly balanced. Never confused with absence.
- **A ratio of zero.** Refused at the boundary — a ratio of zero means no longs at all, which no venue reports and which would break every ratio built on it.
- **A negative ratio.** Refused; it describes nothing.
- **States where only some carry positioning.** The z-score reads the ones that do, and says how many — a window of three readings and one of three hundred are different claims.
- **Both ratios absent for the whole history.** Crowding is unavailable, with the reason, rather than zero.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Derivatives state MUST carry an optional long/short account ratio and an optional top-trader ratio.
- **FR-002**: An absent ratio MUST be distinguishable from a balanced one.
- **FR-003**: A non-positive ratio MUST be refused.
- **FR-004**: Crowding MUST be measured against the instrument's own recent positioning.
- **FR-005**: Crowding MUST be refused, with a reason, when there is too little history.
- **FR-006**: The z-score MUST be the one funding and open interest use.
- **FR-007**: A stale reading MUST be refused, on the same rule as its neighbours.
- **FR-008**: The features MUST be registered with their null policy stated.
- **FR-009**: Nothing existing MUST change.

### Key Entities

- **Positioning**: who is on which side, as the venue reports it, or the fact that it does not.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A state without positioning reports absent for both ratios; one with 1.0 reports 1.0.
- **SC-002**: A ratio of zero or below is refused at construction.
- **SC-003**: The same ratio reads as unusual on one history and ordinary on another.
- **SC-004**: Too little history yields a refusal naming the observation count.
- **SC-005**: A reading older than the tolerance is refused.
- **SC-006**: Every new feature is in the registry with a non-empty null policy.
- **SC-007**: Every existing derivatives test passes unchanged.

## Assumptions

- **Two ratios, not an average.** A venue's global account ratio and its top-trader position ratio measure different populations; averaging them would produce a number describing neither.
- **The connector mapping is out of scope.** Which venue field feeds which ratio belongs with the connector; this carries and reads them.
- **Nothing writes positioning yet**, as nothing writes the other derivative features. This adds the state and the readings; filling them is the derivatives path's.
