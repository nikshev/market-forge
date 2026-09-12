# Specification Quality Checklist: One contract, every pool, and the hook address says what is safe

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-09-12
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

- **FR-005 exists because the classes are not mutually exclusive**, which the
  PRD's list does not say and the chain makes plain: a pool can carry a dynamic
  fee *and* a hook that returns swap deltas. Calling that `DYNAMIC_FEE_CL` would
  say "depth is reconstructible, mind the fee" about a pool whose curve does not
  describe it.
- **FR-009 turns a provenance check into evidence.** Discovering the manager by
  scanning for the event topic, and aborting if a second contract emits it,
  is both how the address is established and how §18.8.2's claim is measured
  rather than repeated.
- **The `UNKNOWN` class has no live instance and needs none.** Every key the
  manager accepted is valid by construction, so the only way to exercise the
  class is with keys the manager would have rejected — which is exactly what it
  is for.
