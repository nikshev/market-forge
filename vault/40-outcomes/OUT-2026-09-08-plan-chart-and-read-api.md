---
id: OUT-2026-09-08-plan-chart-and-read-api
step: plan
records: [REQ-API-001, REQ-WP-009]
commit: null
---

## What was done

Six Python modules under `src/channelflow/api/`, five frontend modules under
`apps/web/src/`, and 15 tasks in six phases.

## What was decided

- **`channels.py` holds the mode logic alone.** It is the one place in this
  feature where a mistake is invisible in the output — a refit and a stored
  snapshot are both plausible channels — so it gets its own module and its own
  test file rather than living inside a route handler.
- **`schemas.py` is separate from the domain models.** A wire format that *is*
  a domain model makes every domain change an API change, and PRD §0.5's
  immutability guarantees are about stored records, not about JSON.
- **The refit calls `RollingOLSChannel.fit` with the requested instant as
  `as_of`**, so REQ-WP-006's own guard applies. The API cannot leak the future
  even if a handler were written carelessly — the same argument REQ-WP-010's
  backtest runner relies on.
- **Phase 0 is the gates, before any code.** `make web-*` targets and the CI
  step exist first, so [[ADR-021]]'s split is real from the first commit rather
  than bolted on at the end.
- **Frontend tests assert on what a reader sees** — the mode label's text, the
  marker's presence, the failure message — never on props. A component test
  that asserts its own props passes while rendering nothing.

## What was rejected

- **Waiting for PRD §29's storage.** [[ADR-019]]'s port makes the wait
  unnecessary, and REQ-WP-008 is already emitting deep links to a page that
  cannot exist until this lands.
- **A fixture where both channel modes agree.** It would pass under an
  implementation that ignored the parameter entirely. The fixture has to make
  them disagree.

## What is still open

- Nothing from this step.
