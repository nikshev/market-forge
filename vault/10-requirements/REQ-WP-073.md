---
id: REQ-WP-073
title: Bars exist at every configured timeframe, built from the one-minute series
type: work-package
prd_ref: "§5.1, §31, §29.4, §28.2"
prd_lines: "289-313, 4698-4711, 4647-4651, 4475-4487"
phase: null
status: specified
depends_on: [REQ-TBL-001, REQ-WP-066]
tags: [timeframes]
---

## Requirement

§5.1 names the Phase 1 timeframes:

> Timeframes:
>
> - 1m;
> - 5m;
> - 15m;
> - 1h.

§31 makes the list configuration rather than a constant, in its example market:

> ```yaml
> markets:
>   - venue: binance
>     type: perp
>     symbols: [BTCUSDT, ETHUSDT, SOLUSDT]
>     timeframes: [1m, 5m, 15m, 1h]
> ```

§29.4 keys the table by that dimension — `(venue, symbol, timeframe, open_time)`
— and §28.2 serves it, taking `timeframe` among its parameters. So a timeframe
is a configured value that flows through storage to the read API, and **no
component may hard-code the set**. §5.1's four are Phase 1's scope, not the
mechanism's limit.

### Built by resampling, not by a second builder

`BarBuilder`'s docstring already anticipates the alternative — "One symbol, one
timeframe. Composition of several is the caller's" — so running one builder per
timeframe against the same trade stream is the path the code was shaped for.
This deployment takes the other one: higher timeframes are **assembled from the
stored one-minute series**, which is idempotent, can be run over history, and
does not multiply work on the socket side.

That choice has a cost, recorded here rather than discovered later: a resampler's
input can be *incomplete without being late*, a failure mode the trade-driven
builder does not have. [[REQ-NRT-UPSAMPLE]] is that cost written as a
non-waivable constraint.

### Two boundaries that arithmetic gets wrong

`BarBuilder.window_start` is `(event_time_ns // timeframe_ns) * timeframe_ns`,
which aligns every window to the Unix epoch. For 5m, 15m, 30m, 1h, 4h and 1d
that is also the UTC boundary, because each divides a day evenly.

- **A week does not.** 604800e9 nanoseconds is a fixed duration, but 1 January
  1970 was a **Thursday**, so epoch-aligned weekly windows open on Thursdays.
  A weekly bar has to open on Monday 00:00 UTC, which floor division alone
  cannot express.
- **A month is not a duration at all.** A calendar month is 28, 29, 30 or 31
  days, so it has no `timeframe_ns` — the column is `int64` nanoseconds
  (`src/channelflow/tables/bars.py`). `1M` is therefore **outside this
  requirement**, deliberately and on the record, rather than approximated as 30
  days: a monthly boundary that drifts against the calendar is wrong in a way a
  reader of a chart cannot see.

## Acceptance

- For each configured timeframe, `GET /api/v1/bars` with that `timeframe_ns`
  returns a series of final bars, contiguous across the windows for which source
  minutes exist.
- A resampled bar's values equal the aggregation of its source minutes: `open` is
  the first minute's open, `high` the maximum high, `low` the minimum low,
  `close` the last minute's close, and `volume_base`, `volume_quote`,
  `trade_count`, `aggressive_buy_base` the sums. Pinned by a test over a window
  whose minutes differ in every one of those fields.
- A timeframe outside §5.1's four — 30m, 4h, 1d, 1w — is produced by
  **configuration alone, with no code change**. Proven by configuring one that no
  test data previously used.
- A weekly bar opens on Monday 00:00 UTC. Proven by a window containing a
  Thursday, which epoch-aligned arithmetic would have split.
- Bars at 5m, 15m, 30m, 1h, 4h and 1d open on UTC boundaries.
- Resampling is idempotent: a second run over the same source rows adds no row
  and changes none.
- `1M` is **refused with a reason naming the calendar-month problem**, not
  silently accepted as an approximate duration and not silently ignored.
- Windows whose source minutes are incomplete produce no bar — the condition
  [[REQ-NRT-UPSAMPLE]] states and tests.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-117-timeframe-resampling]]
- **Outcomes:** [[OUT-2026-09-17-spec-timeframe-resampling]]
<!-- trace:end -->

## Notes

Human territory. Never machine-rewritten.
