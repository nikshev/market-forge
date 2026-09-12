# Specification Quality Checklist: The DEX depth curve reaches the screen with its refusals intact

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

- **FR-004's "never omitted" is the half a reader would not think to ask for.**
  Marking an unreached band is obvious; *keeping* it is not, and omitting it is
  the same lie by absence — a chart with no 100 bps band reads as a chart nobody
  asked about 100 bps.
- **FR-009 was a docstring before it was a requirement.** Two repository
  implementations were claimed to agree about "as of" and nothing checked it; a
  mutation sweep showed the lakehouse reader was never exercised by any test at
  all, because the route tests use the in-memory one.
- **FR-006 came out of a failing test rather than a design session.** The
  staleness assertion was off by 120 nanoseconds, which turned out to be the
  float64 grid at 1.7e18. It is recorded as an open question rather than fixed
  everywhere, because fixing it everywhere is a different piece of work with its
  own risk.
