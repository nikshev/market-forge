# Specification Quality Checklist: Canonical Parquet data plane

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

FR-006 says what a hash must *not* cover, which is unusual in a requirement and
is the point. The obvious implementation — digest the files — passes every other
requirement here and fails the one thing PRD §0 item 13 needs, on a schedule
nobody controls: the next `pyarrow` release.

FR-014's second half is the one that would be quietly dropped. Emulating a
conditional write with a read followed by a write compiles, passes a
single-writer test suite, and loses races silently. A backend that cannot make
the promise has to say so at the moment of the write.

SC-013 exists because a double proves a mapping and not a guarantee. A unit test
shows that a `PreconditionFailed` becomes a `KeyExists`; only a real object store
shows that a `PreconditionFailed` is ever sent. MinIO does send one — which is
worth knowing, because if it did not, every commit in this layer would be a race
nobody loses and nobody notices.
