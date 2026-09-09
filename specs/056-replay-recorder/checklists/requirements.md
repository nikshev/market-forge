# Specification Quality Checklist: A replay writes to the canonical plane

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

FR-004 is the requirement that shapes the recorder. The signal machine hands
back the live candidate on every bar it is alive for, and the obvious
implementation — write what you are given — produces a row per bar, each one a
partial history of the same signal. Nothing about those rows is malformed;
counting them just answers a different question than "how many signals".

FR-006 exists because a recorder that could steer would make a recorded run a
different run from an unrecorded one, and the whole point of recording a replay
is that it is the replay. It is checked by comparing the two reports rather than
by inspecting the recorder.

SC-010 is Principle XI at the end of the pipeline. Two replays of one series
produce the same rows, so they produce the same dataset identity — and an
identity that did not hold that would not be worth citing in the reproducibility
record it exists for.
