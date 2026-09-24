---
id: OUT-2026-09-23-tasks-multi-venue-ingest
step: tasks
records: [REQ-WP-076]
commit: 4486f291e2ad38d1aa1f41a38099820cdb1f41ad
---

## What was done

`specs/121-multi-venue-ingest/tasks.md` generated and analysed against
`spec.md` and `plan.md`: 32 tasks in 7 phases.

| phase | tasks | delivers |
|---|---|---|
| Setup | T001 | the baseline recorded (ingest-binance only) |
| Foundational | T002–T010 | `VenueConnector` protocol, registry, stream builders, 3 connector impls, `StreamSession` update, `ingest_main` wiring |
| US1 (P1) | T011–T017 | daemon per venue, bars/archives with venue |
| US2 (P1) | T018–T025 | stream builders, 3 connector impls, subscription messages |
| US3 (P1) | T026–T027 | `StreamSession` uses `VenuePolicy` per venue |
| US4 (P2) | T028–T028a | silence detector, failure visible |
| Polish | T029–T032 | config, compose, env, docs, quickstart, gates |

## What the analysis found, and how it was resolved

**Task numbering** was non-sequential (gaps at T004, T025, T028; duplicate T028/T028a, T035/T035b). Renumbered to T001–T032 sequentially; updated all cross-references in notes and dependency section.

**FR/SC traceability** was implicit via US labels. Added explicit mapping table in Notes:
US1→FR-001,004,005,008,009/SC-001,004,005
US2→FR-002/SC-002
US3→FR-003/SC-004
US4→FR-006,007/SC-003
FR-009/SC-005 (Binance frozen) is the regression guard across all stories.

**Test/implementation ordering** clarified: where a phase lists an implementation task before its test task (T002/T003, T004/T005, T006/T007, T008/T009, T010/T011, T012/T013, T014/T015, T020/T021, T023/T024), the test task runs first — the list keeps each module next to its tests for readability.

## Metrics after resolution

- Requirements: 9 FR + 5 SC = 14; coverage 14/14 (100%).
- Tasks: 32 (30 implementation/test + 2 no-change guards), 13 marked `[P]`.
- Critical: 0. High: 0. Medium: 1 (resolved). Low: 3 (resolved).
- Ambiguity: 0. Duplication: 0. Unmapped tasks: none.

## What is still open

- **The subscription seam implementation** (which layer assembles the subscribe message) is the central planning decision; the spec records the constraint that it must serve three venues with different mechanics.
- **Live verification** against Bybit/OKX is a deployment step, not a CI gate (ADR-063).
- **Connect rate limits** remain conservative guesses; establishing them requires exceeding a venue's cap deliberately.