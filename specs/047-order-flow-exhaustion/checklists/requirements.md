# Specification Quality Checklist: Order-flow exhaustion around extrema

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

FR-004 says "including the calling threshold" because that is the half of it
nobody looks at. A study can read only trailing windows and still choose what
counts as an extreme value from the whole series — and the precision that
results looks exactly like skill.

FR-006 exists because the obvious reading of a quantile threshold is wrong for
this data. Order-flow signals are zero on most bars; the quantile of such a
series is zero; "at or above zero" is every bar. The failure is silent and
produces a lift of exactly one, which reads as "this signal carries nothing"
about a signal nobody actually thresholded.

FR-011 came out of the fixtures. Two control series built to carry no
information scored lifts of 1.07 and 1.16, and a rule of `lift > 1.0` called
both of them forecasts.
