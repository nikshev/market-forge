# Specification Quality Checklist: No centred filter reaches a live feature

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
- [x] Success criteria are technology-agnostic (no implementation details)
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

Every claim in the Context section was checked against the repository before it
was written, because each is an accusation that something is not covered:

- `require_causal` — one call site outside its own module and its tests, in
  `research/derivative_turning.py`.
- The import scan — `tests/unit/extrema/test_non_repainting.py` builds its path
  as `src/channelflow/extrema` and globs that directory only. There are 27 other
  packages.
- `point_in_time_safe` — every occurrence in `src/` is `True`, and no test or
  validator rule reads the field.

Two items deserve their reasoning stated rather than only ticked:

- **FR-005 exists because a vacuous pass is the failure mode of any scan.** The
  existing test already guards it with "the package has no modules; this would
  pass vacuously", and widening the scan makes the same mistake easier, not
  harder.
- **FR-003 exists because the exemption list is where this rule will erode.** An
  entry naming a deleted package is how a list stops describing anything, and
  the next person reads it as authority.

One item is a deliberate deviation. The spec names `savgol_filter`,
`point_in_time_safe`, `require_causal` and specific file paths under "no
implementation details". They are the evidence for the gap being claimed; a
version that said "the guards do not reach far enough" would be an assertion
rather than a finding.
