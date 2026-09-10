# Specification Quality Checklist: An instrument's trading rules

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-09-10
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

This spec shares the event bus spec's hazard — a one-line PRD deliverable with
no acceptance behind it, which a specification can satisfy while saying almost
anything. The guards are different here.

- **Every field is justified by a downstream failure, not by an exchange
  publishing it.** A venue's payload has dozens of fields; the argument for
  these five is written in [[REQ-WP-021]] and is the thing to disagree with.
- **FR-003 and FR-010 are two halves of one rule.** A missing input is refused,
  and a missing record reads as absent rather than zero. Both exist because an
  unknown tick size and a tick size of zero must never look alike — the same
  distinction three other requirements in this repository have had to make.
- **FR-005 is not pedantry.** A spot instrument has no contract size, and
  storing one as `1` would let a later calculation multiply by it and be right
  by accident, which is worse than being wrong.

Two edge cases are stated rather than left to the implementation: a duplicate
symbol in a payload (the later entry wins) and a tick size of zero (refused).
Both are decisions someone would otherwise make silently by choosing a data
structure.
