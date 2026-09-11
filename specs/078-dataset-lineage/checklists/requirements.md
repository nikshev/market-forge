# Specification Quality Checklist: A registration names the dataset it was trained on

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

- **FR-003 is the one that does the work.** "Present" is not an answer: a
  snapshot id that still exists over different rows is the case a citation is
  supposed to catch, and a check that only asked whether the id resolved would
  pass it. Three outcomes, not two.
- **FR-004 exists because the opposite is tempting.** Refusing to read a
  registration whose dataset is gone would make every report unreadable after a
  legitimate retention pass, and the run still happened. The open question at
  the end is the sharper version of the same trade, and it is left open rather
  than decided here.
- **The scope boundary is one dataset per registration**, and it is honest
  rather than convenient: a run reads one table at one snapshot today. If a
  study ever spans several, this is wrong and will need to be.
