---
description: "Task list for REQ-WP-008 Telegram alerting"
---

# Tasks: Telegram alerting

**Tests**: Written first. The transport is a scripted fake; nothing here
touches a network or a clock.

## Phase 1: The alert and its identity (US4 in part)

- [ ] T001 Write failing `test_render.py` cases for the signal id: derived from the candidate, stable across runs, different for different candidates (SC-007, FR-014). Marker `@pytest.mark.trace("REQ-WP-008")`. Confirm RED.
- [ ] T002 Implement `models.py`: `Alert`, `DeliveryAttempt`, `AuditRecord`, and `signal_id_for` (ADR-017).

## Phase 2: The message (US1, US4)

- [ ] T003 Write failing `test_render.py`: the whole message against a literal expected string; every §26.1 section that has data; a section with no data absent by heading, not empty (SC-001, SC-002); the deep link in §27.1's format from a configured base (SC-007); identical inputs give an identical message (FR-005). Confirm RED.
- [ ] T004 Implement `render.py` (FR-001 to FR-005, FR-013).

## Phase 3: Dedupe (US2)

- [ ] T005 Write failing `test_dedupe.py`: the same state twice emits once; a phase change emits again; an elapsed cooldown alone does not; cooldown plus a new touch does (SC-003, SC-004). Confirm RED.
- [ ] T006 Implement `dedupe.py` (FR-006 to FR-008).

## Phase 4: Delivery (US3)

- [ ] T007 Write failing `test_dispatch.py`: a transport failing twice then succeeding gives one delivery and three audited attempts; a transport that always fails dead-letters; backoff delays strictly increase; queueing never raises even against a transport that throws (SC-005, SC-006). Confirm RED.
- [ ] T008 Implement `dispatch.py` (FR-009 to FR-012), with `Transport` as a protocol.

## Phase 5: Safety (US5)

- [ ] T009 Write failing `test_safety.py`: a stale book suppresses the alert and records why; an invalid book suppresses it; the suppression is visible in the audit; no module references a clock or an HTTP client; no credential appears in a message or the audit (SC-008, SC-009). Confirm RED.
- [ ] T010 Implement the staleness gate (FR-015 to FR-017).

## Phase 6: Close

- [ ] T011 Mutation-check the five guards: emit a duplicate; deliver from a stale book; swallow a dead letter; let a transport exception escape queueing; make the signal id random. Each must fail a named test.
- [ ] T012 Add Telegram placeholders to `.env.example` — a name and an empty value, never a token.
- [ ] T013 Confirm `# @trace: REQ-WP-008` on every new source file.
- [ ] T014 `make lint`, `make typecheck`, `make test`, `make validate` green.

## Coverage

| | Task |
| --- | --- |
| FR-001 to FR-005, FR-013 | T004 |
| FR-006 to FR-008 | T006 |
| FR-009 to FR-012 | T008 |
| FR-014 | T002 |
| FR-015 to FR-017 | T010 |
| SC-001, SC-002 | T003 |
| SC-003, SC-004 | T005 |
| SC-005, SC-006 | T007 |
| SC-007 | T001, T003 |
| SC-008, SC-009 | T009 |

## Notes

T011's last mutation is the one that would otherwise pass review. A random
signal id looks more correct than a derived one — it is what a UUID field
usually holds — and everything keeps working until someone replays a stream and
gets a different audit out of identical input.
