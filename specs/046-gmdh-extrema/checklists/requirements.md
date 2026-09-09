# Specification Quality Checklist: GMDH derivative extrema

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

FR-003 is a requirement about a denominator, which reads like a detail and is
the difference between two opposite verdicts. PRD §13A.12 defines the presence
rate over one root's perturbed members; EXP-013 wants it over an experiment, and
nobody wrote down which rows count. Averaging over all of them reported 0.50 on
the first fixture and failed the gate — about roots that were stable in every
member of every lattice.

FR-004 asks for two numbers to be *absent*. That is unusual in a metrics spec
and it is the point: the derivative route's whole claim is that it names a time
and a price, and a comparison that filled those in for the classifier arms would
be comparing them on a promise only one side made.

FR-013 asks for every failure, not the first. An experiment that reports one
reason at a time costs a full re-run per reason.
