# Implementation Plan: Chart and read API

**Branch**: `wp-009-chart` | **Date**: 2026-09-08 | **Spec**: [spec.md](./spec.md)

## Summary

A FastAPI application reading through repository protocols, and a React chart
that consumes it. The chart's default view is PRD §27.5's `AS-SEEN-THEN`, and
the mode is on screen at all times.

## Technical Context

**Language/Version**: Python 3.12 (`mypy --strict`) and TypeScript 5.6
(`tsc --noEmit`, strict).

**Primary Dependencies**: FastAPI and Uvicorn, new; `lightweight-charts` for
the frontend, which PRD §37's reference list names. React 18 and Vite are
already in the WP-001 scaffold.

**Storage**: none — repository protocols with in-memory implementations
([[ADR-019]]).

**Testing**: pytest with `TestClient` for the API, Vitest with Testing Library
for the chart. Both pure; no service, no network.

**Target Platform**: `src/channelflow/api/` and `apps/web/src/`.

**Performance Goals**: none stated. The in-memory repositories scan lists.

**Constraints**: FR-001/FR-002 (the default and the stored snapshot), FR-010
and FR-017 (the API reads, and never past the requested instant), ADR-021 (the
frontend gates in CI only).

**Scale/Scope**: 6 Python modules, 5 frontend modules, ~70 tests.

## Constitution Check

- **I (no look-ahead)** — FR-017 is the point-in-time rule at the API boundary,
  and SC-010 tests it by planting later data and asserting it is not returned.
- **III (history is immutable)** — `as_seen_then=true` returns the stored
  snapshot unmodified. The test compares against what was stored, which is only
  possible because REQ-WP-006's snapshots are frozen.
- **VI (every feature is documented)** — the features endpoint serves values
  that REQ-WP-011's registry already describes; nothing new is exposed.
- **VII (live and replay are the same code)** — the API computes nothing except
  FR-003's explicit refit, which calls REQ-WP-006's fitter rather than a copy.
- **IX (no automatic execution)** — read-only. Every endpoint is a GET.
- **XIV** — traces to REQ-API-001 and REQ-WP-009.

**Gate result: PASS.**

## Project Structure

```text
src/channelflow/api/
├── __init__.py
├── repositories.py  # the protocols, and in-memory implementations
├── schemas.py       # response models; the wire shape, separate from domain
├── routes.py        # PRD §28's endpoints
├── channels.py      # AS-SEEN-THEN vs CURRENT REFIT, in one place
├── ws.py            # §28.7's subscribe protocol and fan-out
└── app.py           # the application, assembled from the above

apps/web/src/
├── api.ts           # typed client for the endpoints above
├── Chart.tsx        # candles, channel, zones, marker
├── ChannelMode.tsx  # the AS-SEEN-THEN / CURRENT REFIT control and label
├── LoadState.tsx    # "no data" vs "not loaded" vs "not live" (FR-015)
└── App.tsx          # routing and the deep link

tests/unit/api/
├── test_bars.py, test_markets.py, test_features.py, test_signals.py
├── test_channel_modes.py   # US1: SC-001, SC-002, SC-010
└── test_ws.py              # US3: SC-005, SC-006

apps/web/src/__tests__/
├── Chart.test.tsx        # US4: SC-007
└── ChannelMode.test.tsx  # US1: SC-008
└── LoadState.test.tsx    # SC-009
```

**Structure Decision**: `channels.py` holds the mode logic alone, away from
routing. It is the one piece of this feature where a mistake is invisible in
the output — a refit and a snapshot are both plausible channels — so it gets a
module and a test file of its own rather than living inside a route handler.

`schemas.py` is separate from the domain models deliberately: a wire format that
is a domain model makes every domain change an API change, and PRD §0.5's
immutability guarantees are about stored records, not about JSON.

## Approach

**The mode test is the feature's centre.** Store a snapshot, let later bars
arrive, request both modes for the same instant, and assert they differ *and*
that the stored one is byte-identical. A test where both modes agree would pass
under an implementation that ignored the parameter entirely, so the fixture has
to make them disagree.

**The API computes nothing except the explicit refit.** FR-010. The refit calls
`RollingOLSChannel.fit` with `as_of` set to the requested instant, so
REQ-WP-006's own guard applies and the API cannot leak the future even if a
handler were written carelessly.

**Frontend tests assert on what a reader sees**, not on props: the mode label's
text, the presence of a marker, the failure message. A chart test that asserts
its own props passes while rendering nothing.

**`make web-*` targets first**, before any frontend code, so CI has something to
call and ADR-021's split is real from the first commit rather than added at the
end.

## Complexity Tracking

> Two requirements in one plan, justified in the spec: neither is testable
> alone. No other violations.
