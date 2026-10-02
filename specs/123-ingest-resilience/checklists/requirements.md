# Specification Quality Checklist: The multi-venue ingest stays connected, files its archive where readers look, and keeps its log bounded

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-10-02
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

**On "no implementation details".** This is a repair specification, and it names
the things that are broken: `build_daemon`, `FrameArchive`, `StreamSession`,
`CHANNELFLOW_ARCHIVE_URI`, `docker-compose.yml`. They are named because each is
the *seam* a defect hides in, and a specification that described them abstractly
would reproduce the original mistake: the existing tests passed because they
exercised the parts and not the joins. Section "Seven defects, one cause" is
where this is argued, and each acceptance scenario that matters is phrased so it
cannot pass against the broken wiring.

The object key layout in Assumptions is a **decision recorded for review**, with
its reason and the alternative rejected, not a placeholder.

**On clarifications.** None were needed. Three judgement calls are written into
Assumptions where a reader can disagree: the symbol as a path component, the
overwritten frames being unrecoverable, and the silence default being
configuration with a stated basis rather than a constant.

**Success criteria SC-001 to SC-006** are measured against deployment quantities
(bars by venue, objects per hour, log megabytes per day) and not against code. SC-004's
ceiling is a judgement, stated against its measured baseline.

**Left to `/sdd-plan`**: the numeric defaults for silence and for log caps, how a
connector reports that its reader has ended, and the shape of backoff under
repeated refusal.
