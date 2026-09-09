# Specification Quality Checklist: Structural extremum detector comparison

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

FR-004 exists because the trap was live. The threshold policy's parameter was
named `channel_width_pct` and read as a fraction of price, while the only
producer of that number — `ChannelSnapshot.width_pct` — is a percentage. Wired
together they differ by a hundred: a real 2% channel became a 5,000 bps
threshold, the detector confirmed nothing for the whole series, and the report
would have read "this method found no extrema".

FR-011 is the honest shape of this experiment. Five metrics that pull against
each other cannot produce a winner, and a report that named one would be hiding
the choice rather than informing it.
