# Specification Quality Checklist: Calibration per horizon

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

The PRD backs this one — §23.5A names the classes and the conditioning, §23.8
names what a calibration report contains — so the judgement is narrower than in
the day's earlier specs and sits in two places.

- **FR-003 distinguishes unmeasured from poorly calibrated.** This is the third
  time today the same distinction has had to be made explicit (an unknown tick
  size against a tick size of zero; a market with no rules against zeroed rules).
  Here it has a sharper edge: a thin slice reporting a curve reintroduces the
  exact defect the slicing removes, one level down.
- **The last edge case is the one most likely to be got wrong.** A target that
  never occurs at some horizon has observations and no positive outcomes. That is
  a measurable calibration, not an unmeasured slice, and an implementation that
  keyed on "no positives" rather than "too few rows" would merge the two.

SC-005 is written to fail an implementation that hard-codes the minimum: changing
the caller's value must change which slices are unmeasured **and nothing else**.
