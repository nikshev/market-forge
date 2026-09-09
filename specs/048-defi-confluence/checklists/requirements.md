# Specification Quality Checklist: Derivatives/DeFi confluence at turning points

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

FR-002 turns an adjective into a refusal. EXP-015 says "strict ablation" and
leaves it there, which is how ablations end up with arms that differ in two
things: the number still comes out, and it still gets written down under one
family's name.

FR-005 exists because the obvious fingerprint is wrong. Counting the folds is
not identifying them, and two studies over different rows with the same number
of folds are exactly the case "same walk-forward folds" is meant to exclude.

FR-007 asks for both directions because they disagree whenever families overlap,
which for derivatives and DeFi context is most of the time — funding, basis and
swap flow all read the same imbalance from different sides. Reporting one
direction would settle the question by choosing which fact to measure.
