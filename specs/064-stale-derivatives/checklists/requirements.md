# Specification Quality Checklist: A stale derivatives state is refused

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

Unlike most specs here, this one quotes an acceptance criterion the PRD already
wrote. The judgement is therefore not about *what* to require but about three
boundaries, each of which a careless implementation gets wrong:

- **FR-008 protects the feature from the fix.** `funding_z` reads a window of
  history on purpose. A staleness rule applied to the window rather than to the
  reading would refuse the feature exactly when it has the most to say, and it
  would look like the rule working.
- **FR-003 keeps two facts apart.** A venue that never published and one that
  stopped are different, and a single exception type would merge them — the same
  distinction three other requirements in this repository have had to make
  explicit.
- **FR-006 fixes the boundary.** "Older than the tolerance" has two readings and
  the spec picks one, because a boundary left to the implementation is a boundary
  that changes when someone refactors.

The last assumption is the one to argue with: existing callers will break. That
is stated as a finding rather than a cost, because a test whose fixture holds a
state older than any sensible tolerance was asserting on a value this criterion
says must not be used.
