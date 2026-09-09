# Specification Quality Checklist: Causal derivative turning points

**Created**: 2026-09-09 | **Feature**: [spec.md](../spec.md)

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

FR-003 is separate from FR-002 on purpose. A comparison that refused centred
candidates with its own check would pass every test about refusing them and
still drift away from the production guard the moment that guard changed. The
refusal has to be the guard's, and the cause chain is how a test can tell.

FR-005 asks the report to say two things, not one. "Cannot run live" without
"centred filter" reads as a caveat about the candidates; "centred filter"
without it reads as a description of the method under test. Only both together
say what actually happened.

SC-009 exists because four horizons that cannot differ are one measurement
printed four times. On the natural fixture they do not differ — the case had to
be built.
