# Specification Quality Checklist: Adaptive stop-management policy comparison

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

FR-005 is a requirement about where a number lives. PRD §44A.29 warns that the
premature-stop rate is trivially improved by widening the stop until risk
control is gone, and asks for it to be read with realized expectancy. Advice
does not survive a spreadsheet; a property on the object that carries expectancy
does.

FR-008 exists because the alternative is worse in both directions. Dropping a
path that never stopped lets a policy that never exits report no losses and win
every comparison. Charging it a stop's adverse slippage bills it for a fill it
never took. It is marked out at the last price, with fees.

FR-010 says an ablation delta may be negative, which sounds like permission and
is a requirement. On a clean trend, removing the volatility noise floor improves
the engine — the buffer widens the stop and the wider stop exits later on the
way down. An experiment that assumed every capability earns its place would have
nowhere to put that number.

FR-013's "excluding itself" is not pedantry. The verdict is a margin over the
best rival, and an engine counted among its own rivals is the best of them by
construction, with a margin of exactly zero.
