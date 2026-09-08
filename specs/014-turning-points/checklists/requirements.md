# Specification Quality Checklist: Causal turning points

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-09-08
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
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [ ] **Feature meets measurable outcomes defined in Success Criteria** — for
      the five REQ-NRT-* constraints, yes. For REQ-WP-019, deliberately not:
      two of its five acceptance criteria need REQ-WP-017 and REQ-WP-018, and
      ADR-023 records that it stops at `tested` rather than being marked
      complete on a third of its scope.
- [x] No implementation details leak into specification

## Notes

The unchecked box above is the point of this checklist rather than a defect in
it. A spec that quietly narrowed REQ-WP-019's acceptance to what is buildable
today would pass every item here and leave nothing saying the work package is
a third done.

ADR-022 explains why Test D is a declaration rather than an inspection: the PRD
says the path fails when a transform *declares* future dependence, and
inferring centredness in general is not achievable — a checker catching three
of its four forms would give false confidence about the fourth.
