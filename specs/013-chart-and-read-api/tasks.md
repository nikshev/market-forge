---
description: "Task list for REQ-API-001 and REQ-WP-009"
---

# Tasks: Chart and read API

**Tests**: Written first. The API's use `TestClient` over in-memory
repositories; the chart's assert on what a reader sees.

## Phase 0: Gates before code

- [x] T001 Add `web-typecheck`, `web-test`, `web-build` to the Makefile and call them from `.github/workflows/ci.yml` (ADR-021). Add Vitest and Testing Library to `apps/web`. Commit alone, with the frontend suite passing empty.

## Phase 1: Reading (US2)

- [x] T002 Write failing `test_bars.py`, `test_markets.py`, `test_features.py`, `test_signals.py`: filters, ordering, limit-takes-most-recent, and an empty match returning an empty result with a success status (SC-003, SC-004). Markers `@pytest.mark.trace("REQ-API-001")`. Confirm RED.
- [x] T003 Implement `repositories.py` — the protocols and their in-memory implementations (ADR-019).
- [x] T004 Implement `schemas.py` and `routes.py` for bars, markets, features and signals (FR-004 to FR-009).

## Phase 2: The two channel modes (US1)

The centre of the feature.

- [x] T005 Write failing `test_channel_modes.py`: the parameter defaults to true; `as_seen_then=true` returns the stored snapshot byte-identical; `as_seen_then=false` returns a refit that *differs*; a refit with too little history is refused; data later than the requested instant is never returned (SC-001, SC-002, SC-010). Confirm RED.
- [x] T006 Implement `channels.py` and wire it into `routes.py` (FR-001 to FR-003, FR-017).

## Phase 3: Live updates (US3)

- [x] T007 Write failing `test_ws.py`: PRD §28.7's subscribe message is accepted; only named channels, venue, symbol and timeframe are delivered; a malformed message is rejected with a reason and the connection survives (SC-005, SC-006). Confirm RED.
- [x] T008 Implement `ws.py` and `app.py` (FR-011, FR-012).

## Phase 4: The chart (US4, US1)

- [x] T009 Write failing `Chart.test.tsx`: candles for each bar; centre, upper and lower lines; three zone bands; a marker at the signal's time on its boundary; no channel drawn when none exists (SC-007). Confirm RED.
- [x] T010 Implement `api.ts` and `Chart.tsx` with `lightweight-charts` (FR-013).
- [x] T011 Write failing `ChannelMode.test.tsx` and `LoadState.test.tsx`: a deep link opens in AS-SEEN-THEN and says so; switching states the other mode; "no data", "not loaded" and "not live" are distinguishable on screen (SC-008, SC-009). Confirm RED.
- [x] T012 Implement `ChannelMode.tsx`, `LoadState.tsx` and `App.tsx` (FR-014 to FR-016).

## Phase 5: Close

- [x] T013 Mutation-check the five guards: default `as_seen_then` to false; return a refit for `as_seen_then=true`; let the bars query ignore its end bound; deliver a channel a subscriber did not name; drop the chart's mode label. Each must fail a named test.
- [x] T014 Confirm `# @trace: REQ-API-001` on API sources and `// @trace: REQ-WP-009` on frontend sources.
- [x] T015 `make lint`, `make typecheck`, `make test`, `make web-typecheck`, `make web-test`, `make web-build`, `make validate` green.

## Coverage

| | Task |
| --- | --- |
| FR-001 to FR-003, FR-017 | T006 |
| FR-004 to FR-009 | T004 |
| FR-010 | T004, T006 — the API reads; only T006 computes, and only the refit |
| FR-011, FR-012 | T008 |
| FR-013 | T010 |
| FR-014 to FR-016 | T012 |
| SC-001, SC-002, SC-010 | T005 |
| SC-003, SC-004 | T002 |
| SC-005, SC-006 | T007 |
| SC-007 | T009 |
| SC-008, SC-009 | T011 |

## Notes

T013's first two mutations are the ones that matter. Defaulting `as_seen_then`
to false, or returning a refit when the stored snapshot was asked for, both
produce a perfectly plausible channel — and every alert this system has already
sent carries a deep link that would then open a refit. The failure would be
retrospective: old signals would start looking better than they were, and
nothing would say why.
