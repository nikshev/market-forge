# Specification Quality Checklist: The API's reads from the canonical plane

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

FR-002 and FR-003 are the two requirements that make the rest checkable.
[[ADR-019]] promised the durable repository would arrive "without any endpoint
changing", and a promise of that shape is worth nothing unless something fails
when it is broken. One suite over both implementations is that something.

FR-008 came out of a defect the mutation sweep found rather than out of
foresight. Contributions were joined to their score on the instant, and scores
tie on their instant whenever the caller does not supply one — so a market with
two scores read back as one score carrying every group either had. Every row was
correct and the join was not, which is the kind of fault a round-trip test with
a single record cannot see.

FR-012 exists because `Decimal(str(1.1))` succeeds. A reader that coerced would
reintroduce the rounding the column type was added to prevent, and it would do
it silently on the way out rather than on the way in.
