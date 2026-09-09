---
traces: [REQ-PIPE-001]
status: draft
---

# Feature Specification: A replay writes to the canonical plane

**Feature Branch**: `pipe-001-replay-recorder`

**Created**: 2026-09-09

**Input**: REQ-PIPE-001 — the half three storage requirements each left open.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Turn trades into stored bars (Priority: P1)

**Why this priority**: `bars` is the table everything else reads, and it was
empty.

**Acceptance Scenarios**:

1. **Given** trades, **When** they are recorded, **Then** the finalized bars are in the table.
2. **Given** a window still open when the input ends, **When** the recording finishes, **Then** it is not written.

---

### User Story 2 - Store what a replay computed, not what it counted (Priority: P1)

**Why this priority**: the report is a summary by design. A replay that had to
write its channel snapshots needs the snapshots, and refitting them outside the
loop would be a second fitting path that could disagree with it.

**Acceptance Scenarios**:

1. **Given** a replay, **When** it finishes, **Then** every bar that had a channel has a stored snapshot.
2. **Given** a signal alive for many bars, **When** it is stored, **Then** there is one row for it, carrying its whole history.
3. **Given** the same replay with and without recorders, **When** the reports are compared, **Then** they are identical.
4. **Given** a runner passed in, **When** the replay finishes, **Then** it carries no sinks.
5. **Given** a replay, **When** it finishes, **Then** it has not written the bars it read.

---

### User Story 3 - Name the dataset that was produced (Priority: P1)

**Why this priority**: PRD §0 item 13's first hash. [[REQ-REPRO-001]] takes a
dataset reference and nothing produced one.

**Acceptance Scenarios**:

1. **Given** a recording, **When** its tables are read, **Then** only the ones it wrote to are named.
2. **Given** a replay that produced nothing, **When** its dataset is asked for, **Then** it is refused.
3. **Given** two replays of one series, **When** their datasets are compared, **Then** they are equal.
4. **Given** a recorded replay, **When** the durable repository is asked, **Then** it serves what was recorded.

---

### Edge Cases

- What happens to a candidate that opens, closes and is replaced at the same instant? It cannot: a candidate may not reopen on the bar that closed one, so `opened_at_ns` identifies one signal.
- What happens when the series is flat? A channel with no width opens nothing; snapshots are written and signals are not, and the recording names only the tables it filled.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Only finalized bars MUST be written, through the builder's own hook.
- **FR-002**: A window still open at the end of the input MUST NOT be written.
- **FR-003**: A replay MUST write one channel snapshot per bar that had one.
- **FR-004**: A signal MUST be written once, in its final state.
- **FR-005**: A replay MUST NOT write the bars it read.
- **FR-006**: The observers MUST NOT change the report.
- **FR-007**: A caller's runner MUST come back without sinks.
- **FR-008**: A recording MUST name only the tables the run is answerable for — wrote to, or skipped rows destined for. A table that merely holds something MUST NOT be named.
- **FR-009**: A recording that wrote nothing MUST refuse to name a dataset.
- **FR-010**: Two replays of one series MUST produce the same dataset identity.
- **FR-011**: The durable repository MUST serve what a replay recorded.
- **FR-012**: A run over input a table already covers MUST NOT write it again, per series.
- **FR-013**: A run MUST report how many rows it skipped as already covered.
- **FR-014**: A run over partly-overlapping input MUST write the part that is new.
- **FR-015**: A run that skipped everything MUST still name the dataset its input corresponds to.
- **FR-016**: Trades spanning more than one venue or symbol MUST be refused.

### Key Entities

- **Recording**: what a replay wrote, and the identity of what it wrote.
- **Channel recorder / signal recorder**: the runner's observers.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Recorded bars equal the table's contents and all are final.
- **SC-002**: No stored bar closes after the last trade's event time.
- **SC-003**: Stored snapshots equal bars replayed less bars skipped.
- **SC-004**: Stored signals equal candidates opened, and their histories sum to the report's transitions.
- **SC-005**: A recorded run's report equals an unrecorded one's.
- **SC-006**: A passed-in runner's hooks are `None` afterwards.
- **SC-007**: The bars table is untouched by a replay.
- **SC-008**: `bars` is absent from a replay's recording; the channel table is present. A recording for a series with no rows names nothing, even on a store another series filled.
- **SC-009**: An empty replay names nothing and refuses a dataset.
- **SC-010**: Two replays of one series share a dataset identity.
- **SC-011**: The repository returns the recorded bars, a snapshot and the signals.
- **SC-012**: A second pass over the same trades writes no bars; the table's row count is unchanged.
- **SC-013**: A second replay over the same bars writes no snapshots, signals or transitions; all three row counts are unchanged.
- **SC-014**: A second run's `skipped` equals what the first run wrote.
- **SC-015**: A run resumed over overlapping input leaves the table identical to one run over the whole input.
- **SC-016**: One symbol's history does not suppress another symbol's first bar.
- **SC-017**: A fully-skipped re-run's dataset identity equals the first run's.

## Assumptions

- **The producing subsystems' hooks are the seam.** `BarBuilder.on_final` existed; the runner gained two observers that cannot steer it.
- **One replay is one batch per table** *within* a run. Across runs it is not: the plane is append-only and nothing rejects a row already there, so each entry point reads a per-series watermark first and writes only past it. See [[ADR-056]].
