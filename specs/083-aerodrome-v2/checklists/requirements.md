# Specification Quality Checklist: Aerodrome v2, priced by its own invariant

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-09-11
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

- **FR-001 asks for equality where the PRD asks for tolerance**, and that is a
  strengthening rather than a deviation. §18.25 says "within tolerance" because
  an adapter may model a contract approximately; this one ports integer
  arithmetic, so it can be asked for the stronger thing. A tolerance here would
  pass a port that rounded the wrong way at every step and drifted with trade
  size — precisely the error a depth curve carries invisibly.
- **FR-003 exists because FR-001 alone is not enough.** A module that used one
  curve for both pool types could still match the chain on whichever pool it
  happened to be right about. Asserting that the two invariants *disagree* is
  what closes that.
- **User Story 3 came from the mutation sweep**, and the spec records it as a
  story rather than hiding it: the two real pools converge cleanly and never
  touch the iteration's edge branches, so three mutants survived there. The
  inputs that reach them were found by searching the input space, which is a
  legitimate way to test a branch the field does not reach on demand.
