---
description: "Task list for REQ-WP-004 order book service"
---

# Tasks: Order book service

**Tests**: Written first. Pure — no network, no clock.

## Phase 0: The move

Separate, and first, so any later failure is new behaviour rather than a
relocation.

- [x] T001 `git mv src/channelflow/connectors/binance/orderbook.py src/channelflow/book/book.py`; add `src/channelflow/book/__init__.py`; update the import in `tests/unit/connectors/binance/test_orderbook.py`. Add `# @trace: REQ-WP-004` alongside the existing `# @trace: REQ-WP-003`. Suite green before and after; commit alone.

## Phase 1: Bootstrap (US1)

- [x] T002 Write failing `tests/unit/book/test_bootstrap.py`: buffered deltas plus a mid-stream snapshot give the same book as applying only the deltas after it (SC-001); a service that has not bootstrapped refuses every read (FR-013); a buffer that does not connect to the snapshot fails bootstrap rather than producing a book with a hole. Marker `@pytest.mark.trace("REQ-WP-004")`. Confirm RED.
- [x] T003 Implement `service.py`: `BookService` buffers deltas, bootstraps on a snapshot, discards what the snapshot covers, refuses reads until bootstrapped (FR-001, FR-002, FR-013).

## Phase 2: Sequence and rebuild (US2)

- [x] T004 Write failing `tests/unit/book/test_sequence.py`: a delta that breaks the sequence is refused and changes nothing (SC-002); every read refuses afterwards (FR-005); a fresh snapshot rebuilds the book and the gap count survives (SC-003, FR-006). Confirm RED.
- [x] T005 Implement `rebuild` on `OrderBook` and the service's `needs_snapshot` state (FR-004, FR-006, FR-012).

## Phase 3: Reads (US3)

- [x] T006 Write failing `tests/unit/book/test_reads.py`: top-N returns bids descending and asks ascending, at most N, and what exists when a side is short (FR-007); depth within X bps matches hand-computed totals from the mid (SC-004, ADR-011); an empty side refuses instead of substituting a reference (spec edge case). Confirm RED.
- [x] T007 Implement `top` and `depth_within_bps` on `OrderBook` (FR-007, FR-008).

## Phase 4: Health (US4)

- [x] T008 Write failing `tests/unit/book/test_health.py`: health reports validity, gap count, last sequence and staleness through bootstrap, gap and rebuild (SC-005); staleness is `as_of_ns` minus the last applied event time (FR-010); the same stream twice gives identical books and identical health (SC-007); no module in the package references a clock (SC-006). Confirm RED.
- [x] T009 Implement `health(as_of_ns)` carrying `stale_ns`, and track the last applied `event_time_ns` (FR-009, FR-010).

## Phase 5: Close

- [x] T010 Mutation-check the three guards that matter: accept an out-of-sequence delta, let an invalid book answer a read, and forget the gap count on rebuild. Each must fail a named test.
- [x] T011 Confirm `# @trace: REQ-WP-004` on every new source file (R8 will catch an omission, but not before the commit).
- [x] T012 `make lint`, `make typecheck`, `make test`, `make validate` green.

## Coverage

Every functional requirement and success criterion maps to a task:

| | Task |
| --- | --- |
| FR-001, FR-002, FR-013 | T003 |
| FR-003 | already implemented under REQ-WP-003; T004 is where it gains a test at this level |
| FR-004, FR-005, FR-006, FR-012 | T005 |
| FR-007, FR-008 | T007 |
| FR-009, FR-010 | T009 |
| FR-011 | T001 — the move is what makes it true |
| SC-001 | T002 |
| SC-002, SC-003 | T004 |
| SC-004 | T006 |
| SC-005, SC-006, SC-007 | T008 |

FR-003 is the one requirement with no implementation task, deliberately: exact
sequence validation was built for REQ-WP-003 and this feature inherits it. It
appears here because the requirement is still this feature's to guarantee, and
T010 mutation-checks it.

## Notes

T010 exists because two of the three guards are refusals, and a refusal that
stops refusing looks exactly like a passing test suite. The backtest work found
the same shape twice: a guard whose removal changed no observable result.
