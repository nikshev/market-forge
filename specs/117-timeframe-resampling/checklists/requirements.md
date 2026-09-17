# Specification Quality Checklist: Bars at every configured timeframe

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-09-17
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

**On "no implementation details".** The spec names `GET /api/v1/bars`,
`timeframe_ns`, `is_final` and the `bars` table key. These are **PRD vocabulary,
not implementation choices**: §28.2 names the endpoint and its `timeframe`
parameter, §29.4 names the ordering `(venue, symbol, timeframe, open_time)`, and
§31 names the `timeframes:` list. A spec that paraphrased them would be harder to
check against the PRD, which is the source of truth here.

`BarBuilder` is named once, in `## Context`, to record which alternative was
considered and rejected and why. That is the decision's evidence; removing it
would leave the choice looking arbitrary. This follows
`specs/116-live-replay-parity/spec.md`, which names `read_frames` for the same
reason.

**On clarifications.** Four questions were resolved as documented assumptions
rather than as `[NEEDS CLARIFICATION]` markers, because each has a defensible
default that the spec states explicitly: flat construction from minutes (never
chained), whole-multiple timeframes only, UTC boundaries throughout, and a late
minute being allowed to complete a window it was missing from. Each is written in
`## Assumptions` where a reader can disagree with it.

**Deliberately left to `/sdd-plan`**, and recorded in the outcome note rather
than hidden here: where the resampler runs, what the configuration surface is,
and what form the refusal for an incomplete window takes.
