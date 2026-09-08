---
description: "Task list for REQ-WP-003 Binance connector"
---

# Tasks: Binance connector

**Tests**: Written first, replaying committed fixtures. No test opens a socket.

## Phase 1: Normalization (US1)

- [x] T001 Write failing tests in `tests/unit/connectors/binance/test_normalize.py`: a recorded aggTrade becomes a `TradeEvent`; the venue's millisecond `T` becomes exactly `T * 1_000_000` ns; `event_time_ns` and `ingest_time_ns` differ (SC-001-SC-003). Marker `@pytest.mark.trace("REQ-WP-003")`. Confirm RED.
- [x] T002 Implement `normalize.py`: aggTrade and trade to `TradeEvent`, depth update to `BookDelta`, REST snapshot to `BookSnapshot` (FR-001, FR-002, FR-004, FR-005, FR-006).
- [x] T003 Make unknown or missing fields raise with the offending field named (FR-007). Test with a truncated fixture message.
- [x] T004 Normalize the REST premium-index and open-interest payloads to `DerivativesState` (FR-003).

## Phase 2: Order book (US2)

- [x] T005 Write failing tests in `test_orderbook.py`: the recorded snapshot plus 30 consecutive deltas leaves the book valid with zero gaps; removing one delta makes it invalid and raises the gap count without applying the out-of-order delta; an invalid book refuses to supply state; a zero-quantity level removes a rung (SC-004-SC-006, FR-011). Confirm RED.
- [x] T006 Implement `orderbook.py` following PRD §11.1 exactly — buffer, snapshot, discard obsolete, apply by sequence, mark stale on gap — with the `BookHealth` fields §11.1 names (FR-008, FR-009).
- [x] T007 Make the book refuse to supply state when invalid (FR-010). This is §11.1 rule 6; a book that answers anyway leaves the rule to every caller.

## Phase 3: Lifecycle (US3)

- [x] T008 Write failing tests in `test_session.py` using a fake clock and a fake transport: reconnect fires before 24 hours; a ping is answered; a reconnect triggers a fresh snapshot; each failure kind increments a counter (SC-007, FR-012-FR-014, FR-017).
- [x] T009 Implement `session.py` against an injected transport so no test opens a socket (FR-018).
- [x] T010 Make the subscribed stream set configurable rather than hard-coded (FR-015), and the poll interval likewise (FR-016).

## Phase 4: Close

- [x] T011 Add `# @trace: REQ-WP-003` to each new source file.
- [x] T012 Confirm no test opens a socket — grep the connector tests for network calls and assert the suite passes with the stack down (SC-008).
- [x] T013 `make lint`, `make typecheck`, `make test` green.

## Notes

Liquidation normalization is absent by decision, not omission: the stream that
carries it is unreachable from this network, so there is no fixture to test
against. The spec's Assumptions record it.
