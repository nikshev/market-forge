---
traces: [REQ-WP-100]
status: draft
---

# Feature Specification: Compaction under concurrent writers

**Input**: [[REQ-WP-100]] -- owner's report 2026-10-12. Builds on [[REQ-WP-068]], [[REQ-WP-070]].

## Context

1. The read API took 25 s for a 30-minute bars request; a table read of `bars` (170,526 rows) took 25.8 s, of `features`
   (1.25 M rows) 1.0 s. The difference is the number of files.
2. Maintenance had failed to compact `bars` sixteen times running with a `ValidationException`: pyiceberg's default
   `serializable` isolation refuses an overwrite when any file was added since it started, and writers add one every minute.
3. Compaction used `overwrite(read())`: the overwrite replaces the whole table, so making the validation permissive alone
   would have deleted rows committed after the read.
4. The read order comes from each file's sequence number. A file committed after a writer's file gets a later number, so a
   compacted file would sort after rows that came later than it contains.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The page has data (P1)

**Independent Test**: compaction on a table that a second writer appends to during the run lands and loses nothing.

**Acceptance Scenarios**:

1. **Given** ten one-row files and a writer that commits while the compaction runs, **When** it runs, **Then** it returns 10 and all rows are present once.
2. **Given** that, **Then** the order is compacted rows, the writer's row, then later appends.
3. **Given** two such passes, **Then** the whole order is kept and only one order record exists.

### Edge Cases

- A compaction whose own commit loses the race retries (pyiceberg's) and still lands, because only files it names are touched.
- A file it replaced was removed by someone else: the commit refuses, as it must.
