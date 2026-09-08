# Implementation Plan: Telegram alerting

**Branch**: `wp-008-telegram` | **Date**: 2026-09-08 | **Spec**: [spec.md](./spec.md)

## Summary

Four modules under `src/channelflow/alerting/`: the alert value and its signal
id, the message renderer, the dedupe policy, and a dispatcher that queues,
retries, dead-letters and audits. No transport, no clock, no credential.

## Technical Context

**Language/Version**: Python 3.12, `mypy --strict`.

**Primary Dependencies**: `Candidate` (REQ-WP-007), `ChannelSnapshot`
(REQ-WP-006), the feature values of REQ-WP-011. Nothing new.

**Storage**: none. The audit and the dead-letter record are in memory; PRD §29
is unbuilt.

**Testing**: pytest, pure, fast gate. The transport in the tests is a scripted
fake — no network, no mock at the socket layer.

**Target Platform**: `src/channelflow/alerting/`.

**Performance Goals**: none. The dispatcher holds a list.

**Constraints**: FR-012 (queueing never raises), FR-016 (no clock, no I/O),
FR-017 (no credential anywhere in the package).

**Scale/Scope**: 4 modules, ~40 tests.

## Constitution Check

- **VII (live and replay are the same code)** — no clock and no transport means
  a replayed stream produces a byte-identical message and audit. ADR-017's
  derived id is the other half of that.
- **IX (no automatic execution)** — this is the boundary the principle names.
  The package formats and sends text; nothing here can place an order, and
  nothing downstream of it can either.
- **X (thresholds are configuration)** — cooldown, staleness tolerance, attempt
  budget and backoff base are arguments.
- **XI (results are reproducible)** — ADR-017.
- **XIV** — traces to REQ-WP-008.

**Gate result: PASS.**

## Project Structure

```text
src/channelflow/alerting/
├── __init__.py
├── models.py       # Alert, DeliveryAttempt, AuditRecord; the derived signal id
├── render.py       # PRD §26.1's message and §27.1's deep link
├── dedupe.py       # §26.2, minus the score clause ADR-016 removes
└── dispatch.py     # queue, retry policy, dead letter, audit; Transport protocol

tests/unit/alerting/
├── test_render.py    # US1, US4: SC-001, SC-002, SC-007
├── test_dedupe.py    # US2: SC-003, SC-004
├── test_dispatch.py  # US3: SC-005, SC-006
└── test_safety.py    # US5 and the cross-cutting rules: SC-008, SC-009
```

**Structure Decision**: `dedupe` is separate from `dispatch` because they answer
different questions — "should this be said" and "did saying it work". Folding
them together would make the retry tests need dedupe fixtures.

## Approach

**The renderer is tested against literal expected strings.** A message asserted
field by field passes even when the layout is unreadable, and layout is most of
what a message is for. One test holds the whole expected output.

**The omission rule gets its own test, not just its own branch.** ADR-016 says
a section with no data is absent; the test asserts the section's heading does
not appear at all, so a renderer emitting an empty heading fails.

**Dedupe is keyed on the derived signal id plus the candidate state.** That
makes "the same setup in the same state" a tuple comparison rather than a
similarity judgement.

**The dispatcher's audit is append-only and is the test's observation point.**
Every assertion about retry, dead-lettering and suppression reads the audit,
which is also what an operator would read — so the tests exercise the thing
that will actually be looked at when something goes wrong.

## Complexity Tracking

> No violations.
