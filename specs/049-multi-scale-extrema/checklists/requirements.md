# Specification Quality Checklist: Multi-scale extrema

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

FR-005 is EXP-016's last sentence made into two columns. "Measure incremental
value, not visual appeal" is a warning about a specific arithmetic: a filter
improves the average trade almost by definition, and a chart of the survivors
shows exactly that improvement and nothing about the trades it removed. The
second column is the book's outcome, and it is where a selective rule usually
loses.

FR-007 is where this experiment would lose Principle I if it lost it anywhere. A
five-minute candidate at 10:07 sits inside a fifteen-minute bar that closes at
10:15, and using that bar's zone means the context "confirming" the candidate
was partly built out of what happened after it. Every number improves and none
of them looks wrong.

FR-003 sounds like a detail and decides the population. A five-minute extremum
is interesting precisely because it printed at the boundary of the higher
timeframe's range, so an exclusive bound drops the very candidates the rule
exists to select.
