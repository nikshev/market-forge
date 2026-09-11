# Specification Quality Checklist: A Slipstream fee is an observation, not a derivation

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

- **SC-002 is a claim about the venue, not about this code**, and that is
  deliberate. It can fail without a line of ours changing — if Aerodrome ever
  reset every pool to its spacing's default, the assertion would go red while
  nothing was broken. That is the right trade: the assertion is what stops
  anyone reintroducing a lookup table on the grounds that it "looks about
  right", and a red test that says "the venue changed, re-read this" is more
  useful than silence.
- **FR-005 and FR-006 exist because FR-001 alone does not reach them.** Eight
  live pools happen not to sit at a bound, so a port that applied the cap first,
  or substituted the default scaling under a pool's own cap, would match the
  chain on all eight. Both are asserted on constructed inputs instead.
- **The edge cases are not hypothetical.** Truncating division, the zero-fee
  sentinel and the three-way initial-fee sentinel are each a place where a
  reasonable reading of the contract gives a different number from the
  contract, and each was written as a scenario before the port was checked
  against the chain.
