---
traces: [REQ-WP-067]
status: draft
---

# Feature Specification: The targets under load

**Feature Branch**: `wp-067-load-generation`

**Created**: 2026-09-14

**Status**: Draft

**Input**: REQ-WP-067 — Phase 8's load tests against §36's targets.

## Context

REQ-WP-057 measured §36's targets one call at a time and found large headroom.
That says what one user waits for and nothing about twenty waiting together.
§36 states no concurrency, so the shape is reported rather than a made-up number
asserted — the choice REQ-WP-057 made when it asserted a scaling ratio.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The shape is visible (Priority: P1)

**Acceptance**: the percentile at each concurrency is reported, so where a
target stops being met is read rather than inferred.

### User Story 2 - A missed target is reported (Priority: P1)

**Acceptance**: a target over budget is reported with its numbers and what
reproduces them.

### User Story 3 - A target nobody measured says so (Priority: P1)

**Acceptance**: `NOT_MEASURED` appears for every target with no result, and is
not a pass.

### User Story 4 - A failing system does not measure as a fast one (Priority: P1)

**Acceptance**: errors are counted apart; any error fails the target; a run
where everything failed raises.

### Edge Cases

- Fewer requests than workers leaves a worker idle.
- A target met at one client and missed at ten is not met.
- An empty report is not a pass.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `drive` times each request individually at a stated concurrency.
- **FR-002**: Errors are counted separately and never enter the samples.
- **FR-003**: A run with no successful samples raises.
- **FR-004**: `report` covers every target; missing ones are `NOT_MEASURED`.
- **FR-005**: The worst concurrency decides a target's verdict.
- **FR-006**: Any error makes a target `NOT_MET`.
- **FR-007**: `passed` requires every target `MET`.
- **FR-008**: Each line carries concurrency, request count and budget.
- **FR-009**: The tool runs against a deployment, deliberately.

### Key Entities

- **LoadResult**, **TargetReport**, **Verdict**.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The first run reported `chart_historical_load` not met at p95
  4431ms for one client against a 2s budget.
- **SC-002**: Two targets reported `not measured` rather than omitted.
- **SC-003**: Workers are shown to run concurrently.
- **SC-004**: Mutating the error handling, the verdict set, the worst-case rule
  or the pass condition is caught by a test.

## Assumptions

- Only `chart_historical_load` is observable over HTTP; the other two are
  pipeline timings.

## Open Questions

- The missed target's cause is 654 files for 657 rows; the fix is its own
  requirement.
