# Specification Quality Checklist: EVM connector

**Created**: 2026-09-08 | **Feature**: [spec.md](../spec.md)

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

ADR-033 is the decision worth reading twice: a reorg orphans a record and never
edits or deletes one, and a read as of an instant before the reorg still
returns it. Deleting would be the obvious implementation and would make a
replayed backtest disagree with the live system in a direction that looks like
the strategy improving.

ADR-034 separates the two failure modes PRD §18.6 rules out in one sentence:
guessing at an upgraded contract, and dropping the only evidence of what
happened.
