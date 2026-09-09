# Specification Quality Checklist: Lookback sensitivity

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

FR-007 and FR-009 are EXP-002's instruction made structural. "Do not select
solely on maximum PnL" cannot be enforced by saying so in a docstring: a report
that names the best expectancy and nothing else *is* selection by PnL whatever
the surrounding text says. So the recommendation comes from the plateau, the
peak is reported beside it, and with no plateau there is no recommendation — the
peak is never a fallback.

FR-010 matters more than it looks. Skipping an absent value would join two
separate plateaus across a lookback nobody could measure, which is the kind of
plateau that exists only in the report.
