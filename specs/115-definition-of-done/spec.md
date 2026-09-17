---
traces: [REQ-DOD-001]
status: draft
---

# Feature Specification: The definition of done, checked rather than claimed

**Feature Branch**: `req-definition-of-done`

**Created**: 2026-09-17

**Status**: Draft

**Input**: [[REQ-DOD-001]] — PRD §47, the only place the PRD says what finishing
means.

> **This spec was written after the implementation.** The ladder is
> `draft → specified → planned → tested → implemented`, and this requirement
> went from `draft` to `implemented` in one step. `make validate` refused it —
> R1, "status 'implemented' requires at least one spec, found none" — which is
> the validator catching what the discipline did not. Recorded here rather than
> back-dated, because a spec presented as having come first would be the same
> kind of claim §47 exists to stop.

## Context

§47 states nineteen conditions for "whole product MVP+". Every one of them
already had delivery behind it. The mapping did not exist: it was reconstructed
by reading 103 requirement titles and grepping the source, and a mapping made
that way is a claim about a moment.

This is the fourth rule in this repository found holding only because nothing
checked it — after §34's seven requirements, §35.3 and §35.4. §47 is the largest,
because it is the definition of done.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - "Is it done" has a mechanical answer (Priority: P1)

**Acceptance**: each of the nineteen conditions names at least one requirement
that delivers it, and every named requirement has reached `implemented`. A
condition short of that makes §47 unmet **by item number**.

### User Story 2 - A condition cannot be softened (Priority: P1)

**Acceptance**: the conditions are compared against §47 as it stands in the PRD,
not against a copy. A reworded condition fails.

### User Story 3 - A condition cannot go missing (Priority: P1)

**Acceptance**: the count is asserted against the PRD's own. A note that lost a
condition cannot report that the rest are met.

### User Story 4 - The two lists cannot drift (Priority: P2)

**Acceptance**: the flat `covers:` list, which R8 follows, is exactly the union
of the per-condition lists, compared in both directions.

### Edge Cases

- A parser that finds no conditions makes every comparison vacuously true.
- A section range with no upper bound swallows §48's numbered list, which is a
  different list of sixteen.
- `tested` is not delivery: it means failing tests exist, not that anything
  works.
- A misspelled requirement id would otherwise read as coverage.
- A missing requirement note and an unknown status are different faults and must
  say so differently, or removing one check changes nothing.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The conditions are read from the PRD between §47's heading and
  §48's, and a range that cannot be bounded raises.
- **FR-002**: A PRD section stating no numbered conditions raises.
- **FR-003**: Each condition's text matches the PRD verbatim; markdown emphasis
  is stripped before comparison and nothing else.
- **FR-004**: A condition with no covering requirement is reported by item.
- **FR-005**: A covering requirement below `implemented` is reported with its
  condition and its status.
- **FR-006**: A covering requirement with no note raises, distinctly from one
  with an unrecognised status.
- **FR-007**: The flat `covers:` list is compared with the union in both
  directions.

### Key Entities

- **Condition**: an item number, §47's text, and the requirements delivering it.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All nineteen conditions are present, quoted and covered.
- **SC-002**: Each check is demonstrated to bite by a test that breaks it.
- **SC-003**: The suite needs no services and no network.

## Assumptions

- **§47 is the definition, not this note.** If the PRD gains a twentieth
  condition, the suite goes red until somebody maps it. That is the intent.
- **Met at `implemented` is not `verified`.** This says the work exists and its
  tests pass; it does not say a human has read each requirement against the PRD.
