---
id: OUT-2026-09-23-implement-chart-timeframe-control
step: implement
records: [REQ-WP-074]
commit: null
---

## What was done

The chart's timeframe is now chosen on the chart, the link is its initial
value, and the address keeps up. [[REQ-WP-074]] reaches `implemented`.

- `src/channelflow/timeframes.py` — `offered(configured)`: the source plus the
  configured targets, the one place the union is computed.
- `src/channelflow/settings.py` — `Settings.timeframes`, read through the same
  `parse_list` the resampler uses.
- `src/channelflow/api/` — `GET /api/v1/timeframes` (`TimeframeOut`,
  `TimeframesResponse`), wired through `create_app` and `build_app`.
- `apps/web/src/timeframes.ts` (new) — `DEFAULT_TIMEFRAME`, `TimeframeOption`,
  `matchTimeframe`; no token→duration table, because durations arrive on the
  wire.
- `apps/web/src/TimeframeControl.tsx` (new) — the row of buttons.
- `apps/web/src/deepLink.ts` — the default now comes from `DEFAULT_TIMEFRAME`;
  `withTimeframe`/`withMode` write one key and preserve the rest.
- `apps/web/src/App.tsx` — the offered set, in-force timeframe state, refusal,
  `replaceState`, the sequence guard, and one link-identity fix (below).
- `docker-compose.yml`, `docs/deployment.md` — the variable reaches the API and
  the endpoint is documented.

Tests: 5 new/updated Python (`test_timeframes.py`, `test_settings.py`,
`test_timeframes_route.py`), 4 new/updated web files (203 tests pass overall).
`make lint`, `make typecheck`, `make test-fast`, `npx tsc --noEmit`,
`npx vitest run` and `npx vite build` all pass.

## The defect found while wiring this, and its measurement

`App.tsx` re-parsed the deep link **on every render**. `link` was a fresh
object each time, so `load`'s `useCallback` identity changed each time, so the
`useEffect([load])` refired after every render — and each refire set fresh
arrays, causing the next render. The page fetched in a loop.

Measured before the fix, with `fetch` stubbed and `/chart/binance/BTCUSDT?tf=4h`
open: **1264 fetch calls in 300ms, 316 of them bars**. Measured after: exactly
one bars request, one channel, one features, one extrema per change. No test
caught this because no App-level test existed; `Chart.test.tsx` tests the series
decision without rendering, and every other web test is module-level.

The fix is in the shape the feature already demands: the link is parsed once at
mount, and from then on the UI state is authoritative and the address is an
output. That is what "the link is the initial value, not the alternative" means
in code.

## What the tests measure, and where the RED evidence is

The request assertions inspect the URLs that reached `fetch`, not component
state: a constant `15 * MINUTE_NS` passes any test that asks React what it
holds, and that constant was the defect.

RED, captured before the implementation landed:

```text
tests/unit/test_timeframes.py: ImportError: cannot import name 'offered'
tests/unit/test_settings.py: 4 failed — no 'timeframes' on Settings
tests/unit/api/test_timeframes_route.py: TypeError: create_app() got an
    unexpected keyword argument 'timeframes'
apps/web/src/__tests__/chartTimeframeControl.test.tsx:
    AssertionError: expected '/api/v1/bars?venue=binance&symbol=BTC…'
    to contain 'timeframe_ns=14400000000000'   (4 failed, 2 passed)
apps/web/src/__tests__/deepLinkQuery.test.ts:
    expected source not to contain '"15m"'; withTimeframe is not a function
apps/web/src/__tests__/TimeframeControl.test.tsx:
    Failed to resolve import "../TimeframeControl"
```

The two regression tests for FR-011 (empty vs failed) passed before the change
and after it, as intended: they guard a vocabulary the request-path rewrite
could have broken, and they are not RED evidence.

**Where the RED discipline was not followed, stated rather than fabricated:**
the refusal path (US2, T023/T026) and the "options come from the API" behaviour
(US4, T031/T032) were implemented together with T019 before their tests existed,
so those tests passed on first run. The overall request path had its RED; these
two arms did not, and the tests are meaningful only because they fail under
mutation, not because a red run was observed. Recorded here so the omission is
not mistaken for a skipped step.

## Measured on the running stack, 2026-09-23

**Before** (headless, from the deployment as it stood): the API had no
`/api/v1/timeframes` (404), and the page constant lived at `App.tsx:62`.

**After**, the API rebuilt with the code and `.env`:

```text
GET /api/v1/timeframes
{"timeframes":[
  {"token":"1m","timeframe_ns":60000000000},
  {"token":"5m","timeframe_ns":300000000000},
  {"token":"15m","timeframe_ns":900000000000},
  {"token":"30m","timeframe_ns":1800000000000},
  {"token":"1h","timeframe_ns":3600000000000},
  {"token":"4h","timeframe_ns":14400000000000},
  {"token":"1d","timeframe_ns":86400000000000},
  {"token":"1w","timeframe_ns":604800000000000}]}
```

The web container was rebuilt from this checkout; the served bundle contains
`api/v1/timeframes` and the refusal text. The interactive chart flow
(`?tf=1h` → four requests at `3600000000000`, press `5m` → address `tf=5m`) is
proved by `chartTimeframeControl.test.tsx` against a stubbed wire; the deployed
bundle is the same source, but **no browser was driven against the stack** —
recorded as the limit of what was measured rather than implied to have been
done.

## What was decided, beyond the plan

- **The source timeframe is offered unconditionally.** `1m` is in the set even
  though `CHANNELFLOW_TIMEFRAMES` never names it: §5.1 lists it and the ingest
  daemon always writes it, so a set without it would hide the one series
  guaranteed to exist.
- **The `link` identity fix** (above) was not in the plan; it is unavoidably in
  scope, because a loop that hammers the API at the wrong timeframe is not an
  improvement on one that asks once at the wrong timeframe.
- **Three gate repairs outside this feature**, each required to make the gate
  green and each recorded because they touch other requirements' files:
  `tests/mutations/wire_time.toml`'s "a duration is converted too" pattern
  became ambiguous once `TimeframeOut.timeframe_ns` existed and is now anchored;
  `test_wire_time.py` declares the new duration field; `test_security.py`'s
  route count grew to 18. `tests/unit/test_opencode_config.py` and
  `tools/validate_opencode_config.py` were reformatted — pre-existing drift from
  [[REQ-INFRA-005]] that `make lint` refused.
- **The default-missing case refuses rather than substitutes** — a deployment
  that configures `15m` away gets the alert naming `15m`, not a neighbour.

## What is still open

- **No browser was driven against the running stack.** The end-to-end claim is
  covered by vitest with a stubbed `fetch`; a manual pass of
  `quickstart.md` section 3 remains for whoever has a browser.
- **Presentation is unsettled by design** ([[REQ-WP-074]]'s Reference); the
  control is plain buttons, and replacing them reopens nothing.
- **The chart does not re-read when only the address changes.** Parsing happens
  once at mount; a full navigation is the way to open a different link, which is
  how links already arrive. If a future requirement wants in-page back/forward,
  it should say so.
