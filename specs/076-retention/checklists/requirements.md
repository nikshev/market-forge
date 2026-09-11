# Specification Quality Checklist: Retention expires by policy, never what a lineage names

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
- [x] Scope is clearly bounded
- [x] Edge cases are identified
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

- **FR-005 is the one that makes the feature almost do nothing**, and that is
  correct. Manifests are cumulative, so a file from the first commit is named by
  every later manifest and survives until every one of them is expired. A
  specification that skipped this would produce a retention pass that deletes
  files a surviving snapshot still needs — which reads as "retention works"
  right up to the first point-in-time query.
- **FR-008 is close to an implementation statement** and is kept because the
  alternative is not checkable. "Retention may delete and the table layer may
  not" is a promise about discipline; "the table layer is never given something
  that can delete" is a fact about a type.
- **The pin-refusal rule (FR-009) is a judgement call.** A pin naming a snapshot
  that does not exist could be ignored. It is refused because the likeliest
  cause is a typo, and ignoring it prunes something somebody meant to keep — the
  one outcome this feature cannot undo.
