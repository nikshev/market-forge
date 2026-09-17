---
traces: [REQ-NRT-PARITY]
status: draft
---

# Feature Specification: A captured live segment replays to the same outputs

**Feature Branch**: `nrt-parity`

**Created**: 2026-09-17

**Status**: Draft

**Input**: [[REQ-NRT-PARITY]] — PRD §35.5, the last section of this family with
no requirement note until now.

## Context

§35.5 asks three things: capture a 30–60 minute live segment, replay it offline,
assert feature/channel/signal parity.

**The first is already done.** [[REQ-WP-066]]'s ingest daemon archives one gzip
object per minute of raw frames, and the running deployment has been doing it
for two days. Measured: **1,717 minutes** across two days at roughly 8 KB a
minute, and **3,881 bars** in the canonical plane from the same run. Both halves
of the comparison exist — what the live path produced, and the frames it
produced them from.

**[[REQ-NRT-E]] is not this.** It is §13A.28's Test E, it is `implemented`, and
its tests run `detector().run(history)` over extrema detectors only — with a
"live" run that is a second in-process call of the same function on the same
list. That proves determinism, which is worth proving. §35.5 additionally
exercises the archive, the decoder and every boundary between the socket and the
feature: a function deterministic inside one process can still disagree with
itself across a capture-and-replay boundary, and frame ordering, a timestamp
narrowed on the way to disk, or a field the archive drops are exactly where it
would.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The replay reads what the socket delivered (Priority: P1)

**Acceptance**: the fixture is archived frames as written, read back through the
same `read_frames` a replay uses. Not a decoded summary, not a re-serialisation.

### User Story 2 - The bars match (Priority: P1)

**Acceptance**: replaying the segment through the same ingest path produces the
bars the live run produced, field for field, for every minute wholly inside the
segment.

### User Story 3 - The channels match (Priority: P1)

**Acceptance**: a channel fitted over the replayed bars equals one fitted over
the live bars, at every moment both can be asked about.

### User Story 4 - The signals match (Priority: P1)

**Acceptance**: the signal engine run over each produces the same transitions,
in the same order, with the same times. A run that produced fewer fails, and so
does one that produced more.

### User Story 5 - A divergence is caught and named (Priority: P1)

**Acceptance**: a deliberately altered replay fails, and the failure names what
differed — the bar's minute, the field, and both values.

### Edge Cases

- A segment's first and last minutes are partial: a bar spanning the boundary
  saw trades the segment does not hold. Only minutes wholly inside it are
  comparable, and the boundary ones must be excluded by construction rather than
  by a tolerance.
- The live run may have written a bar the replay cannot, or the reverse. Counting
  matches alone would pass a replay that produced nothing.
- A comparison that examined no bars reports success. The count is asserted.
- Parity of a value computed from an empty series is agreement about nothing.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The fixture holds 30–60 minutes of archived frames, verbatim, with
  the wall-clock window recorded beside them.
- **FR-002**: The fixture holds the bars the live run produced for that window.
- **FR-003**: The replay drives the same ingest code the daemon runs, through a
  replay transport, with no branch on which it is (Principle VII).
- **FR-004**: Bars are compared field for field, for minutes wholly inside the
  window.
- **FR-005**: Channels and signals are computed from both bar sets and compared.
- **FR-006**: Any difference names the minute, the field and both values.
- **FR-007**: The number of bars, channels and signals compared is asserted, so
  an empty comparison cannot pass.
- **FR-008**: The suite runs with no services and no network.

### Key Entities

- **Segment**: a window of wall-clock time, the frames archived inside it, and
  the bars the live run produced from them.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every bar wholly inside the segment matches, and the count is
  non-zero and asserted.
- **SC-002**: Channels and signals derived from both sets match.
- **SC-003**: An altered replay fails and names the difference.
- **SC-004**: The suite needs no services and no network.

## Assumptions

- **One symbol, one timeframe.** The daemon runs one process per symbol
  ([[REQ-WP-066]]), so a segment is one symbol's, and a second would test the
  same code twice.
- **The live bars are taken as given.** This asserts that a replay reproduces
  them, not that they were right. What makes them right is every other test in
  this repository.
- **Boundary minutes are excluded, not tolerated.** A partial bar is a different
  bar, and a tolerance wide enough to accept one would be wide enough to hide a
  real difference.
