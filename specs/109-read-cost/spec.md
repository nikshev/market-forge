---
traces: [REQ-WP-068]
status: draft
---

# Feature Specification: A read costs what its rows cost

**Feature Branch**: `wp-068-read-cost`

**Created**: 2026-09-14

**Status**: Draft

**Input**: REQ-WP-068 — the target REQ-WP-067 found missed.

## Context

§36's chart-load target was missed at 4.4s for one client. Three compounding
causes, each measured: a serial per-file read, one file per bar, and no way to
rewrite a table that already fragmented.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The read waits concurrently (Priority: P1)

**Acceptance**: files open through a shared bounded pool and rows come back in
exactly the order they did serially.

### User Story 2 - Commits hold more than one bar (Priority: P1)

**Acceptance**: the flush is a bar count with a time ceiling, so a quiet symbol
still commits and a busy one does not commit per bar.

### User Story 3 - A fragmented table can be rewritten (Priority: P1)

**Acceptance**: compaction returns the same rows in the same order from one
file, and does nothing to a table that needs nothing.

### User Story 4 - The target is met (Priority: P1)

**Acceptance**: the load tool reports `met` at every concurrency it drives.

### Edge Cases

- A per-read bound makes sixteen clients slower, not faster.
- A single-file table must not pay for a pool or a snapshot.
- An interval equal to the bar size is a commit per bar.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Data files are read through one process-wide bounded pool.
- **FR-002**: Commit order is preserved by sorting paths and concatenating in
  that order.
- **FR-003**: `FLUSH_EVERY_BARS` counts bars; `FLUSH_CEILING_NS` bounds time.
- **FR-004**: `compact()` rewrites live rows into one file, order preserved.
- **FR-005**: Compaction of one file writes no snapshot.
- **FR-006**: A maintenance tool covers every appended table, named explicitly.

### Key Entities

- **READ_WORKERS**, the shared pool, `compact()`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 717 files, 721 rows: read 6478ms → 45ms after compaction.
- **SC-002**: chart_historical_load p95 at 16 clients 20207ms → 944ms, met.
- **SC-003**: Compaction returns rows equal to the ones before it.
- **SC-004**: Mutating the order, the bound, the rewrite or the single-file
  guard is caught by a test.

## Assumptions

- Compaction runs on a schedule an operator sets; the tool does not schedule
  itself.

## Open Questions

- Old snapshots still reference the pre-compaction files until expired.
