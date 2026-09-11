# Specification Quality Checklist: A backup is a claim about restoring

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

- **SC-003 is unusual and deliberate.** It describes a corruption the backup
  cannot produce, which is the point: FR-001's ordering is what buys it, and
  stating the criterion as "this state would fail verification, and here is why
  it cannot arise" is the only way to make an ordering rule visible in the
  success criteria at all. A criterion asserting only that backups succeed would
  pass for an implementation copying manifests first.
- **"Scope is bounded"** rests on three exclusions argued in the derivation
  document rather than assumed here: retention, Postgres metadata, encryption.
- **The assumption about digest-based verification versus row-based tests** is
  the one a reviewer should push on. A digest check proves the manifests agree
  with the files; only reading the rows proves the data came back. Both are
  specified, and which one runs where is stated rather than left to taste.
