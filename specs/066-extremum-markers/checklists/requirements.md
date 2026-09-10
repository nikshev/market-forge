# Specification Quality Checklist: Extrema on the chart

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

The PRD wrote this feature's correctness rule, so the judgement is about three
things it does not say:

- **FR-005 and FR-007 together.** The first says when a confirmation may be
  returned; the second says where it is drawn once it is. Stated separately, an
  implementation could satisfy the criterion by drawing the extremum at its
  `known_at` instead — which never appears too early and is also not where the
  turn happened. Both halves are needed to pin the honest picture.
- **FR-006 applies the same rule to candidates.** The criterion names
  confirmations only. A candidate leaking in before it was observed would be the
  same defect under a different name, and nothing in the PRD would have caught
  it.
- **The two filters are separate** — window and knowledge. Collapsing them makes
  a correctness rule look like a range query, and a later refactor that
  "simplified" one would silently take the other with it.

FR-010 is there because the obvious implementation drops unconfirmed candidates
as noise. A swing that did not confirm is a fact about the market, and the chart
that hides it is the one that makes the detector look better than it is.
