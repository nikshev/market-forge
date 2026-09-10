# Specification Quality Checklist: One event bus between producers and consumers

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
- [x] Scope is clearly bounded
- [x] Edge cases are identified
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

This spec has a failure mode the others did not, and it is worth naming: the PRD
gives one line with no acceptance behind it, so **the specification could say
almost anything and still look faithful**. Three things guard against that.

- **The acceptance is derived from a cost that was measured, not imagined.**
  `BarBuilder` and `BacktestRunner` do require their consumers at construction;
  that is checkable in the source, and it is the only concrete problem the bus
  solves today.
- **FR-004 and FR-005 are in the requirement rather than the design.** Ordered,
  synchronous dispatch and a propagating exception are what Principle XI and
  ordinary debuggability need, and they are the properties a reviewer would
  never see if they lived in an implementation note.
- **The last assumption is a pre-commitment.** "If the replay path does not read
  better through the bus, that is a finding" is written before the work so the
  answer cannot be chosen afterwards. A spec for a deliverable nobody asked to
  use is exactly where that temptation lives.

FR-006 (no delivery to a subscription made during dispatch) and FR-007 (a
handler subscribed twice is called twice) are not hypotheticals. Both are the
observable consequence of the obvious implementation — iterating the live list —
and one of them is a crash rather than a wrong answer.
