---
id: OUT-2026-09-08-plan-telegram-alerting
step: plan
records: [REQ-WP-008]
commit: null
---

## What was done

Four modules under `src/channelflow/alerting/` — models, render, dedupe,
dispatch — and four test files. 14 tasks in six phases.

## What was decided

- **The renderer is tested against a literal expected message.** Asserting
  field by field passes even when the layout is unreadable, and layout is most
  of what a message is for.
- **The omission rule gets its own test rather than only its own branch**
  ([[ADR-016]]). The test asserts the section's heading does not appear at all,
  so a renderer emitting an empty heading fails rather than passing quietly.
- **`dedupe` is separate from `dispatch`.** They answer different questions —
  "should this be said" and "did saying it work". Folded together, the retry
  tests would need dedupe fixtures for no reason.
- **The audit is the tests' observation point**, and an operator's too. Every
  assertion about retry, dead-lettering and suppression reads the same record
  that will actually be looked at when something goes wrong.

## What was rejected

- **Mocking at the HTTP layer.** [[ADR-018]] puts the transport behind a
  protocol, so the fake is ten lines and the package contains no client to
  mock.
- **Sleeping in the retry test.** The requirement is that delays increase, and
  a test that slept would assert the same thing and take a minute.

## What is still open

- Nothing from this step.
