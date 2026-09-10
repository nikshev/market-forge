---
traces: [REQ-WP-029]
status: draft
---

# Feature Specification: A replay records the extrema it detected

**Feature Branch**: `wp-029-record-extrema`

**Created**: 2026-09-10

**Status**: Draft

**Input**: REQ-WP-029 — the caller REQ-WP-028 left open.

## Context

The tables, the endpoint and the chart markers exist and nothing fills them. The
replay already turns bars into channel snapshots and signals on the plane; the
detector takes the same bars and produces candidates and confirmations.

Two things make this more than plumbing.

**One run should produce everything the chart reads.** A replay that wrote
channels and signals but left extrema to a second, separate process would give a
reader two pictures assembled from two runs, and nothing would say whether they
agree.

**The bus gets a second producer.** Its own note calls the first benefit "one
caller, one capability, proven by tests rather than by use". Whether the seam
holds when something else publishes into it is not knowable from one consumer,
and this is the first chance to find out.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A replay fills the extremum tables (Priority: P1)

**Acceptance Scenarios**:

1. **Given** bars containing turns, **When** a replay runs, **Then** the confirmed extrema it detected are on the plane and readable through the repository.
2. **Given** the same bars, **When** a replay runs, **Then** the candidates observed along the way are recorded too.
3. **Given** a run, **When** what it wrote is read back, **Then** every field matches what the detector produced.

---

### User Story 2 - A caller can observe the same events (Priority: P1)

**Acceptance Scenarios**:

1. **Given** a caller's own bus with a subscriber, **When** a replay runs on it, **Then** the subscriber sees every extremum event.
2. **Given** such a subscriber, **When** it does nothing, **Then** what was recorded is unchanged.
3. **Given** a confirmation on a particular bar, **When** the events are observed, **Then** it arrives in that bar's turn rather than in a batch at the end.

---

### User Story 3 - A second run over the same input writes nothing (Priority: P1)

**Acceptance Scenarios**:

1. **Given** a replay already recorded, **When** the same input is replayed, **Then** no extremum row is added.
2. **Given** that second run, **When** its result is read, **Then** the number it skipped is reported rather than silent.
3. **Given** a run over input extending an earlier one, **When** it runs, **Then** only what is new is written.

### Edge Cases

- **Bars with no turn at all.** Nothing is recorded and nothing is refused — an absence of turns is a fact about the series.
- **A candidate later confirmed.** Both are recorded: the candidate happened, and PRD §13A.2's lifecycle is append-only. The chart already knows not to draw it twice.
- **Two replays of one series into two stores.** Identical rows, because the detector is deterministic and the ids are derived.
- **A replay whose bars span more than one instrument.** Refused, as `record_bars` already refuses it: one detector tracks one instrument.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A replay MUST run the detector over the bars it was given.
- **FR-002**: Confirmed extrema and candidates MUST be recorded on the plane.
- **FR-003**: They MUST be published as events and recorded by subscribers, not written directly.
- **FR-004**: A caller-supplied bus MUST see every extremum event.
- **FR-005**: A confirmation MUST be published in the turn of the bar that confirmed it.
- **FR-006**: A second replay over recorded input MUST write nothing and report what it skipped.
- **FR-007**: A replay over extending input MUST write only what is new.
- **FR-008**: What a replay already records MUST be unchanged, dataset identity included.
- **FR-009**: Bars spanning more than one instrument MUST be refused.

### Key Entities

- **Extremum event**: a confirmation, or a candidate observation, as it happened.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After a replay over a series with N confirmed turns, the repository returns N.
- **SC-002**: Candidates recorded equal candidates the detector observed.
- **SC-003**: A caller's subscriber receives one event per recorded extremum.
- **SC-004**: A second replay adds no rows and reports a non-zero skip count.
- **SC-005**: A replay over a longer series adds only the new turns.
- **SC-006**: Bars, snapshots, signals and the dataset identity are unchanged from before this feature.
- **SC-007**: Two replays into two stores produce identical rows.

## Assumptions

- **Detection is its own pass over the same bars.** The runner owns its loop and offers no per-bar hook; adding one would change a component with nothing to do with extrema. Principle VII is satisfied by the events being identical, not the iteration shared.
- **Nothing about the detector changes.** Where a turn is confirmed is [[REQ-WP-019]]'s.
- **Idempotence follows [[ADR-056]].** A per-series watermark, on knowledge rather than on the turn — the same instant the table is keyed by.
