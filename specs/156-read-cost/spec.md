---
traces: [REQ-WP-104]
status: draft
---

# Feature Specification: The cost of a read and of a pass

**Input**: [[REQ-WP-104]] -- measured 2026-10-13. Builds on [[REQ-WP-068]], [[REQ-WP-070]], [[REQ-WP-073]], [[REQ-WP-100]].

## Context (measured)

1. API on 2026-10-13: bars 54 s, volume profile 82 s, features 5 s; host load average 41.
2. `resample`: 345 % CPU, one full table read per (series, timeframe), a commit per series.
3. `volume_bins`: 5,077 files, 23 s to read; absent from the maintenance list. `bars`: 1,482 files, 7.6 s to read.
4. `read().to_pylist()` of a million-row features table to keep one series' day: ~2 s of 5.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The chart answers in seconds (P1)

**Acceptance Scenarios**:

1. **Given** the deployed stack, **When** the page asks for bars, the profile and a feature series, **Then** each answers in a fraction of the 54 / 82 / 5 s above.
2. **Given** a resample pass over many series, **Then** it reads once and commits once.
3. **Given** a table a module declares, **Then** maintenance compacts it.

### Edge Cases

- A commit that fails mid-pass: nothing is written, every report says 0, and the next pass writes the same windows.
- A series that cannot be resampled is named and skipped; the others are written.
