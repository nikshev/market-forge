---
id: OUT-2026-10-04-implement-volume-profile
step: implement
records: [REQ-WP-089]
commit: a4d188b
---

## What was done

Volume by price level with the buy/sell split, collected and shown, on the **live stack**. The ingest now aggregates each
symbol's trades into five-minute blocks of price bins (buy, sell and unknown base volume by aggressor side, from the trade
itself, PRD section 14.1) and writes a block when it closes; the API serves `GET /api/v1/volume-profile` (4h, 24h, 7d); the chart
draws the profile at its right edge on its own price scale as horizontal bars, buy and sell in two colours, the point of control
outlined and the value area stronger, with a line under the chart that says how much of the window the data covers.

- `volume/bins.py`: `PriceBinBuilder` (grid `floor(price/width)` from zero, width per symbol, late trades discarded and counted, a
  block whose trade ids show missed trades **dropped, not flagged** on venues with sequential ids), `nice_bin_width`,
  `parse_bin_widths`.
- `tables/volume_bins.py`: the `volume_bins` table (event time = block close), `BinSink`, `select_bins` (latest width only, whole
  blocks closed at or before the instant, Principle I).
- `volume/profile.py`: `from_bins`, over the same `_point_of_control` and `_value_area` as `build`; SC-002 compares it with
  `build(anchor=0)` and the two agree.
- `api/volume_profile.py`, `routes.py`, `schemas.py`, both repositories: the route; 404 while nothing is collected, 422 for another window;
  `covered_ns`, `complete` and `covers_from_ns` say what the profile spans.
- `ingest.py`, `ingest_main.py`, `docker-compose.yml`, `.env.example`, `docs/deployment.md`: `CHANNELFLOW_PROFILE_BIN_WIDTHS`,
  `CHANNELFLOW_PROFILE_BLOCK_SECONDS`.
- Web: `profileView.ts` (pure geometry and the words), `profilePrimitive.ts` (a series primitive), `ProfileControls.tsx`,
  `profileWindows.ts`, `fetchVolumeProfile`, wiring in `Chart.tsx` and `App.tsx`.

**RED first.** Python phases A-C were written before their modules (tasks T002-T004, T010-T011). Web phase D, five files against the
unchanged source:

    Failed to resolve import "../ProfileControls" / "../profileView" / "../profilePrimitive"      (three files)
    Failed Tests 6: chartProfile (no primitive attached, replaced or detached), volumeProfileApi (fetchVolumeProfile is not a function)

**After.** pytest **3,394 passed** (3,056 unit at the start, plus the integration set); web **502/502** (471 at the start, 31 new);
`make lint`, `make typecheck`, `make web-typecheck` clean; `make web-build` green. **Bundle gzip** 166,906 B -> 168,338 B (+1.4 kB).
Mutation sweeps: `price_bins.toml` 11/11 caught, `profile_from_bins.toml` 7/7 caught.

## Edits to existing tests

Each is a guard that a legitimate addition tripped, edited for its reason and not to make anything pass:

- `tests/unit/api/test_security.py`: EXPECTED_ROUTES 18 -> 19 (the new route, which is a read like its neighbours).
- `tests/unit/api/test_wire_time.py`: the four `_ns` fields of `VolumeProfileOut` are classified: `as_of_ns` and `covers_from_ns`
  are instants (strings), `window_ns` and `covered_ns` durations (integers). The guard is what forces the choice.
- `tests/unit/pipeline/test_resample_main.py`: the "no 4h literal outside the timeframe vocabulary" guard now matches the quoted
  token only, and `volume_profile.py` joins `timeframes.py` as a vocabulary: a profile window is how far back bins are summed, not
  a bar width.
- `apps/web/src/__tests__/chartTimeframeControl.test.tsx`: the same guard on the web side; `profileWindows.ts` joins `timeframes.ts`.
- `tests/mutations/ingest.toml`: anchors re-read for the changed `stop()`.

## What looking at the live screenshots showed

`docs/ui/profile-btc15m-{24h,4h}-{light,dark}.png`, **live data**: BTCUSDT 15m with the profile at the right edge. Collection began
at 15:38 UTC on 2026-10-04, so the line reads "covers 30 m of 24 h" -- eleven bins of width 20 -- and the bars are thin against a
chart of days. That is the honest picture and the point of the line: until history accrues it is a profile of the last half hour.

1. The bars sit at the right edge on the chart's own price scale and follow it; buy (teal) and sell (red) read apart in both schemes.
2. The point of control is outlined and is the widest bar, but the outline runs the whole bar width and is heavier than it needs to be.
   Left as is; one pixel of line width if it bothers.
3. **First version of the controls was unstyled** (plain buttons beside Material ones). Rebuilt as a `ToggleButtonGroup`.
4. **Two buttons named "4h"** (the timeframe's and the window's) broke two existing tests and cannot be told apart by a screen reader.
   The window buttons are named "4h profile", "24h profile", "7d profile".
5. **A profile response of the wrong shape crashed the page** (found by an existing test whose stub answers every call alike).
   The page now states "the response was not a volume profile" instead.

## Findings outside this requirement

- **`make web-test` exits 1 on a clean checkout.** All 471 tests pass at HEAD but vitest reports 3 unhandled errors
  (`paneSeries`: `points` undefined, from test stubs of `fetchFeatureSeries` that return no `points`) and exits non-zero. Measured in a
  worktree at HEAD. CI's `web-test` step would be red for that reason alone; this requirement did not cause it and did not fix it.
- First partial block after an ingest restart is dropped on Binance by the id check (as designed): a restart costs up to five minutes.

## What was decided

- Bins are collected **from now on**; none is invented from bars and nothing is backfilled (PRD 14.1: no direction from candle colour).
- Five-minute blocks of coarse bins: a few thousand rows a day, nothing a profile over hours can show is lost.
- A profile states what it covers (`covered_ns`, `complete`); it never reads as the full window when it is not.

## What is still open

- History: a profile is only as long as the collection has run; a 7d profile needs seven days. No backfill is planned.
- Venues without sequential trade ids (Bybit, OKX) are not checked for missed trades; their blocks are written as seen.
- The profile is not yet drawn for CURRENT-REFIT-style "as of" views beyond the deep link's `at`; [[REQ-WP-090]] (live refresh) is next.
- Commit: a4d188b.
