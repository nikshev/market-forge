# Implementation Plan: The timeframe is chosen on the chart

**Branch**: `119-chart-timeframe-control` | **Date**: 2026-09-23 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/119-chart-timeframe-control/spec.md`

## Summary

The chart parses `tf` and then asks for fifteen minutes regardless
(`apps/web/src/App.tsx:62`), so [[REQ-WP-073]]'s series reach a request that
never names them. This plan wires the whole mechanism the spec describes:

1. **A read reporting the offered set** — `GET /api/v1/timeframes`, computed
   from `CHANNELFLOW_TIMEFRAMES` plus the source timeframe, so the frontend
   carries no list of its own.
2. **A control that re-reads everything at the chosen timeframe** — bars,
   channel, features and extrema, with the in-force timeframe held in one place.
3. **The link as initial value, and the address kept current** — `tf` on open,
   `history.replaceState` on change, for the channel mode too.
4. **Refusal instead of substitution** — an unhonourable token is named, and no
   request is issued at a timeframe nobody asked for.

## Technical Context

**Language/Version**: Python 3.12 (API, `src/`), TypeScript 5 + React 18
(`apps/web/`).

**Primary Dependencies**: FastAPI + Pydantic v2 (existing API surface);
React + Vite + vitest + Testing Library (existing web toolchain). No new
dependency on either side.

**Storage**: none. The offered set is configuration read once at process start;
the endpoint serves no table.

**Testing**: `pytest` for the API and settings (`@pytest.mark.trace("REQ-WP-074")`);
`vitest` + Testing Library for the frontend, mocking `fetch` to capture the
parameters that reached the network. The web gates run in CI (`make
web-typecheck`, `make web-test`, `make web-build`, ADR-021) and are run locally
for this feature.

**Target Platform**: the existing deployment — API container, static web
bundle; no new service.

**Performance Goals**: none beyond the existing read. The endpoint is a
constant-size list built at startup; the control adds no request of its own per
change beyond re-reading the four series the chart already reads.

**Constraints**: FR-016's vocabulary (`ok`/`empty`/`failed`) is reused, not
extended with a second failure vocabulary. No look-ahead applies trivially
(nothing here computes over time), and live/replay parity is untouched: this is
a read and a view.

**Scale/Scope**: one new endpoint, one new control, one module of query
helpers, and the wiring between them. Eight tokens in the default offered set.

## Constitution Check

*GATE: passed before Phase 0, re-checked after Phase 1.*

| Principle | How this design satisfies it |
|---|---|
| **I. No look-ahead** | A view: it issues reads at a `timeframe_ns` and renders what returns. The offered set is configuration, not data. |
| **II. Time is not one thing** | The token→`timeframe_ns` mapping comes from the API, so the frontend never re-derives a duration; `at`/`at_ns` handling is untouched. |
| **III. History is immutable** | Reads only; `history.replaceState` changes the reader's own address, never a stored row. |
| **VII. Live and replay are the same code** | Nothing in the producing path changes; the endpoint serves the same configuration the resampler reads. |
| **IX. No automatic execution** | No write path is added; the endpoint is read-only like every other in §28. |
| **X. Thresholds are configuration** | Exactly the point of FR-002: the offered set is configuration, never a compiled list. |
| **XI/XII/XIII** | No dataset, no optimization, no phase skipped: [[REQ-WP-074]] follows [[REQ-WP-073]] as its acceptance required. |
| **XIV. Everything is traceable** | Every source file carries `# @trace: REQ-WP-074` (or `// @trace:`), every test the marker, and the spec its `traces:` edge. |

No violations. No complexity to track.

## Key decisions

### The offered set is a read, and it carries durations as well as tokens

`GET /api/v1/timeframes` returns `{token, timeframe_ns}` for each offered
timeframe, ascending by duration: the source (`1m`, always offered, per §5.1
and the ingest daemon's shape) plus whatever `CHANNELFLOW_TIMEFRAMES` names.

The durations ride along **so the frontend has no token table**. A TS map of
`"4h" → 14400e9` would be exactly the second list FR-002 forbids; with the
duration on the wire, the frontend matches the link's token against what the
deployment reported and uses the duration it was given. There is no fallback
table to disagree with.

### The API process reads the same variable the resampler does

`Settings` gains `timeframes: tuple[Timeframe, ...]`, parsed once from
`CHANNELFLOW_TIMEFRAMES` through `channelflow.timeframes.parse_list` — the same
parser, so a token the resampler refuses (a calendar period, a typo) refuses the
API at startup too. Unset means the source alone is offered, which is what a
deployment that resamples nothing can honestly serve.

`docker-compose.yml` passes the variable to `api` as it does to `resample`, from
one `.env` value. `create_app` takes the tuple and puts it on `app.state`, the
way `repository` and `metrics` already travel ([[ADR-019]]).

### The route is `/api/v1/timeframes`, and the union happens in one function

`channelflow.timeframes.offered(configured)` returns `(SOURCE,) + configured`,
de-duplicated and sorted by `ns`. One function, one test, and both the endpoint
and any later caller ([[REQ-WP-075]]'s markets view names the same set) use it
rather than repeating the union.

### The in-force timeframe is state, initialised from the link

`App` holds `timeframe: string`, initialised to `link.timeframe` — and
`parseDeepLink` gains `DEFAULT_TIMEFRAME` from the new frontend module as its
one default. The heading prints the state, not the parsed link, so the displayed
and requested values cannot differ (FR-013).

The four requests read the duration from the matched offered entry. Until the
offered set arrives, no request goes out; an unhonourable token produces the
refusal instead of a request (FR-006).

### The address is written with `replaceState`, preserving what it does not own

`history.replaceState` rather than `pushState`: changing a timeframe or a mode
is not navigation, and a back button that steps through six timeframes is a
worse interface than one that leaves the page. A helper rebuilds the query from
the current `URLSearchParams`, touching only its own key (`tf`, or
`as_seen_then`), so `at`, `signal`, `chain`, `pool` and the overlay parameters
survive (FR-009). `as_seen_then=false` is written for the refit and the key is
**removed** for AS-SEEN-THEN — absence is the default [[ADR-020]] already
relies on, and writing `as_seen_then=true` would put a value in every copied
link that the parser treats as the default anyway.

### A stale response is dropped by sequence, not by hope

`load` takes a sequence number from a ref; when a response arrives under an
older number than the current one it is discarded. The effect's cleanup also
stops a response setting state after unmount. This is small and observable
(FR-012): two fast clicks must end on the last one, and jsdom can drive that
with mocked promises resolved out of order.

### Refusal is a state of the page, not a toast

When the offered set is loaded and the in-force token is not in it, the page
renders a `role="alert"` paragraph naming the token and listing what is offered,
and does **not** render the chart. Rendering the chart with no data would draw
an empty chart, which is the "empty series" meaning FR-011 reserves for a quiet
market. When the offered set itself fails to load, `LoadState` `failed` carries
the detail (FR-010).

## Project Structure

### Documentation (this feature)

```text
specs/119-chart-timeframe-control/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── timeframes-api.md
│   └── web.md
└── tasks.md             # /speckit-tasks output
```

### Source Code (repository root)

```text
src/channelflow/
├── timeframes.py                    # + offered()
├── settings.py                      # + timeframes field, read from CHANNELFLOW_TIMEFRAMES
└── api/
    ├── app.py                       # + timeframes on app.state
    ├── main.py                      # + settings.timeframes into create_app
    ├── routes.py                    # + GET /api/v1/timeframes
    └── schemas.py                   # + TimeframeOut, TimeframesResponse

apps/web/src/
├── timeframes.ts                    # NEW: DEFAULT_TIMEFRAME, TimeframeOption, matchTimeframe
├── TimeframeControl.tsx             # NEW: the row of buttons
├── deepLink.ts                      # default from timeframes.ts; query-writing helpers
├── api.ts                           # + fetchTimeframes
├── App.tsx                          # wiring: state, refusal, URL sync, heading
└── __tests__/
    ├── timeframes.test.ts           # NEW
    ├── TimeframeControl.test.tsx    # NEW
    └── timeframeControl.test.tsx    # NEW: the whole mechanism, fetch mocked

tests/
├── unit/test_timeframes.py          # + offered() tests (REQ-WP-074)
├── unit/test_settings.py            # + timeframes from env
└── unit/api/test_timeframes_route.py# NEW

docker-compose.yml                   # api service: CHANNELFLOW_TIMEFRAMES
docs/deployment.md                   # the endpoint and where the set comes from
```

**Structure Decision**: the backend piece follows the existing layers —
vocabulary in `timeframes.py`, configuration in `settings.py`, surface in
`api/`. The frontend piece is three new files rather than one large `App.tsx`
change: the control, the pure query/token helpers and the link constant are each
testable without rendering the page, which is how the existing `deepLink.ts` and
`ChannelMode.tsx` split already works.

## Complexity Tracking

No violations to justify.
