# Specification Quality Checklist: The DeFi primitives land on the canonical plane

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-09-12
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

- **FR-007 was not in the first draft**, and is the requirement this work
  actually turned on. Storing a sometimes-absent field looked like a property of
  the table; it was a capability the plane did not have, and discovering that
  cost a failing test and a fix to [[REQ-WP-039]]'s encoder ([[ADR-066]]).
- **SC-004's third term — "and an empty string"** — comes from a mutation that
  survived. The encoder produces no bytes for an empty string, so a null marked
  by an empty payload would have hashed identically to `""`, and "this field is
  empty" and "nobody recorded this field" would have been one dataset.
- **FR-006 and FR-007 pull in opposite directions on purpose.** A field nothing
  will ever fill is left out; a field sometimes filled is nullable. The first
  keeps the schema honest, the second keeps the rows honest, and conflating them
  is how a table ends up with a column that is null on every row and a reader who
  assumes somebody meant to fill it.
