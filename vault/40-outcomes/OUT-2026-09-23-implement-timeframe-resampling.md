---
id: OUT-2026-09-23-implement-timeframe-resampling
step: implement
records: [REQ-WP-073]
commit: c614adff7e32f256bdc64f7a022404abef10bf07
---

## What was done

Every configured timeframe now has a series built from the one-minute source,
and [[REQ-WP-073]] reaches `implemented`.

- `src/channelflow/timeframes.py` — the vocabulary: `Timeframe(token, ns,
  origin_ns)`, `TIMEFRAMES`, `window_start`, `parse`, `parse_list`. The week's
  `origin_ns` is what puts its windows on Mondays.
- `src/channelflow/pipeline/resample.py` — `fold`, `resample`, `Refusal`,
  `ResampleResult`, `ResampleReport`, `report_for`. Pure: no clock, no catalog.
- `src/channelflow/pipeline/resample_main.py` — the process: discovers the
  `(venue, symbol)` pairs from the source rows, reads each target's existing
  open times, appends through `BarSink`, prints one line per series and every
  refusal, and keeps going when one series fails.
- `docker-compose.yml` — a `resample` service on a loop; `.env.example` —
  `CHANNELFLOW_TIMEFRAMES=5m,15m,30m,1h,4h,1d,1w` and
  `CHANNELFLOW_RESAMPLE_INTERVAL=5m`; `docs/deployment.md` — the twelfth
  service and the two variables.
- Tests: `tests/unit/test_timeframes.py` (14), `tests/unit/test_resample.py`
  (14), `tests/unit/pipeline/test_resample_main.py` (6).

## RED, first, for the right reason

Both modules were written after their tests, and the failures are what proves it:

```text
tests/unit/test_resample.py:7: in <module>
    from channelflow.pipeline.resample import fold
E   ModuleNotFoundError: No module named 'channelflow.pipeline.resample'

tests/unit/pipeline/test_resample_main.py:9: in <module>
    from channelflow.pipeline.resample import Refusal, ResampleResult, report_for
E   ImportError: cannot import name 'report_for' from 'channelflow.pipeline.resample'
```

One further red came from a wrong fixture rather than missing code, and is
recorded because the correction is part of the evidence: the first
"not a whole multiple" test used `7m`, which *is* a whole multiple of `1m`, so
it failed with `DID NOT RAISE` and was rewritten around `90s` (1.5 minutes).

## Measured on the running stack, 2026-09-23

**Before the first pass** — every series one timeframe deep, and the request a
chart at any other timeframe makes returns nothing:

```text
BTCUSDT 1m=8844  ETHUSDT 1m=8681  SOLUSDT 1m=8673
timeframes present: [60000000000]
GET /api/v1/bars?timeframe_ns=900000000000 -> {"bars":[]}
```

**After one pass**, counted through the read API:

```text
BTCUSDT 1m=8889 5m=1777 15m=592 30m=295 1h=147 4h=36 1d=5 1w=0
ETHUSDT 1m=8725 5m=1744 15m=580 30m=289 1h=144 4h=35 1d=5 1w=0
SOLUSDT 1m=8717 5m=1743 15m=580 30m=289 1h=144 4h=35 1d=5 1w=0
every open_time_ns a multiple of its timeframe_ns
```

**Idempotence**, the assertion the quickstart names — count rows, not reports:

```text
duplicate keys: 0
```

The second pass reported `written=0` with non-zero `skipped` for every series
but one, and the exception is the honest kind: ETHUSDT 5m wrote 2 bars because
the ingest daemon completed two new minutes between the passes. `1w` stays at
zero because the deployment's history (about 3.7 days) has not yet closed a
whole week; the one closed weekly window is refused for its missing prefix
(5205 of 10080 minutes), which is the rule working rather than a gap.

## What was decided

**`(venue, symbol)` is discovered from the source rows, not configured.**
`CHANNELFLOW_TIMEFRAMES` chooses what to build; the bars table already knows
which series exist. A second symbol list could disagree with the first, and
the series to produce are exactly the series that exist.

**`ResampleReport` is separate from `ResampleResult`** because a pass can
compute ten bars and fail to append them. `report_for` takes `written` as a
parameter rather than deriving it from `len(result.bars)`, and a test pins that
the two can differ — otherwise the type would exist for nothing.

**Calendar periods are refused by a pattern, not only by the literal `1M`.**
`1y` and `3M` raise `CalendarPeriod` too: they have the same leap-length
problem, and FR-008 says "or any calendar-defined period".

**A shared interval parser was duplicated rather than extracted.**
`resample_main._interval_seconds` is deliberately the same grammar as
`maintenance_main`'s `--loop`, with a comment saying so. Promoting it to a
third module for six lines would be the larger change; if a third loop appears
it should move.

## What is still open

- **`tf` still does not reach the chart's request.** The series exist, but
  `apps/web/src/App.tsx` builds every request from `15 * MINUTE_NS`, so a chart
  at any other timeframe still shows nothing. That is [[REQ-WP-074]], the next
  requirement in the chain, and the quickstart names it so a reader does not
  blame the resampler.
- **`1w` has no bar yet for the ordinary reason**: the deployment has less
  than a week of minutes. The mechanism is tested over a constructed week.
- **The full week's first bar is refused on every pass**, because the source
  begins mid-window. That refusal is correct and will be counted on every pass
  until the window ages out of consideration — a known, visible refusal rather
  than a silent one.
