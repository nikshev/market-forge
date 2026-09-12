# Specification Quality Checklist: Curve, quoted from its own invariant

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-09-11
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

- **FR-001 asks for equality where the PRD asks for tolerance**, for the reason
  [[SPEC-083-aerodrome-v2]] gives: the arithmetic is integer throughout, so a
  faithful port agrees bit for bit, and a tolerance would pass a port that
  rounded the wrong way at every step.
- **FR-003 and FR-005 exist because FR-001 does not reach them on its own.**
  It does — for these four pools — but only because all four have their fee
  multiplier switched on and one holds an accruing token. Asserting both
  directly means the coverage survives a fixture refresh that happens to pick
  four plainer pools.
- **FR-008 is the specification's smallest requirement and its least obvious.**
  A registry that does not know an address is answering "this is not a Curve
  pool"; storing that as `false` alongside every genuine non-metapool turns it
  into "a Curve pool that is not a metapool", and the classifier then has no way
  back. The third state has to survive from the capture tool to the classifier.
- **The two discarded discriminators are asserted absent**, not merely unused.
  Both are the first thing a reader would reach for, and both are wrong; a test
  that says so is cheaper than the afternoon it saves.
