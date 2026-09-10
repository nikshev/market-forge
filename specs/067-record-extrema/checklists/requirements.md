# Specification Quality Checklist: A replay records the extrema it detected

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

This is the sixth "write down the caller" specification in one session, so the
hazard is a spec that says "wire A to B" and calls it acceptance. Three
requirements exist to stop that:

- **FR-003 forbids writing directly.** Recording through subscribers is what
  makes the bus's second producer real; a spec that only required the rows to
  arrive would be satisfied by the shortest path, and the bus would still have
  one consumer.
- **FR-005 fixes the ordering.** A batch flushed at the end produces the same
  rows and a different event stream, and the difference is invisible until a
  live process attaches the same subscribers and sees a burst.
- **FR-006 with FR-007.** Writing nothing on a re-run is easy if you also write
  nothing on an extension. Stated as a pair, they pin idempotence rather than
  inertia — the same shape [[ADR-056]] was written about.

SC-006 is the one that would catch this feature breaking its neighbours: the
dataset identity of everything the replay already wrote must be unchanged.
