# Phase 1 Data Model: Bars at every configured timeframe

No table changes. `timeframe_ns` is already a column of §29.4's `bars`, and the
existing schema carries every field a resampled bar needs. What follows is the
in-memory model.

## `Timeframe`

A duration and the instant its windows are aligned to.

| field | type | meaning |
|---|---|---|
| `token` | `str` | the configured spelling: `5m`, `1h`, `1w` |
| `ns` | `int` | the duration in nanoseconds |
| `origin_ns` | `int` | the instant windows align to; `0` for all but the week |

**Validation**

- `ns > 0`.
- `origin_ns >= 0` and `origin_ns < ns` — an origin at or beyond one whole
  duration is the same alignment written confusingly, and permitting it would
  allow two `Timeframe` values that behave identically to compare unequal.
- A token naming a calendar period (`1M`, `1y`, and any future spelling of one)
  is **refused at construction** with a message naming the calendar problem.
  There is no `Timeframe` value for a month, so no later code can hold one.

**Behaviour**

```text
window_start(t) = ((t - origin_ns) // ns) * ns + origin_ns
```

Floor division, deliberately: for `t < origin_ns` this must round toward
negative infinity. Pinned by a test, because the same arithmetic is destined for
a language where `/` truncates.

A pre-origin window could never be *stored* in any case — `Bar.open_time_ns`
carries `Field(ge=0)`, so the model refuses a negative instant before the table
ever sees one. The test pins the arithmetic, not the storage path: this function
is the one the markets view will need, and it will need it in TypeScript.

**Known values**

| token | ns | origin_ns |
|---|---|---|
| `1m` | 60e9 | 0 |
| `5m` | 300e9 | 0 |
| `15m` | 900e9 | 0 |
| `30m` | 1800e9 | 0 |
| `1h` | 3600e9 | 0 |
| `4h` | 14400e9 | 0 |
| `1d` | 86400e9 | 0 |
| `1w` | 604800e9 | 345_600_000_000_000 |

## `Window`

A half-open interval at one timeframe, identified by its opening instant.

| field | type | meaning |
|---|---|---|
| `timeframe` | `Timeframe` | which series this window belongs to |
| `open_time_ns` | `int` | the window's identity; always `timeframe.window_start` of itself |
| `close_time_ns` | `int` | `open_time_ns + timeframe.ns` |

`close_time_ns` is the table's event time, for the reason the `bars` schema
already gives: a bar becomes knowable when it closes, so a point-in-time read as
of an instant inside the window must not return it.

## `Refusal`

Why a window produced no bar. Carried as a value, not logged and discarded —
FR-005 requires it to reach the caller.

| field | type | meaning |
|---|---|---|
| `open_time_ns` | `int` | the window refused |
| `expected` | `int` | source bars the window needs, `timeframe.ns // source.ns` |
| `present` | `int` | source bars actually found |
| `reason` | `str` | a sentence naming the window and what was missing |

A refusal is produced **only** for a window that is closed and incomplete. A
window still in progress is not refused, because nothing about it is wrong yet;
it is simply not this pass's business.

## `ResampleReport`

What one pass did, for one `(venue, symbol, timeframe)`.

| field | type | meaning |
|---|---|---|
| `venue`, `symbol` | `str` | which series |
| `timeframe` | `Timeframe` | which target |
| `written` | `int` | bars appended |
| `skipped` | `int` | windows already present — the idempotence path |
| `refusals` | `tuple[Refusal, ...]` | closed windows that could not be built |
| `line` | `str` | one-line summary, as `maintenance.run`'s report already does |

`skipped` is reported rather than inferred: a pass that wrote nothing because
everything existed and a pass that wrote nothing because it read nothing are
different events, and a report that showed `written=0` for both would hide the
second.

## Relationships

```text
Timeframe ──< Window ──> Bar (written)
                    └──> Refusal (closed, incomplete)

source: list[Bar] at 1m ──> grouped by Window ──> fold ──> Bar at Timeframe
```

Every target timeframe is built from the **source** timeframe directly. No
target is built from another target: chaining would compound both arithmetic
error and incompleteness, and the level that refused would not be the level that
was wrong.

## The fold

For a complete window, over its source bars in `open_time_ns` order:

| field | rule |
|---|---|
| `open` | first bar's `open` |
| `high` | maximum `high` |
| `low` | minimum `low` |
| `close` | last bar's `close` |
| `volume_base`, `volume_quote`, `trade_count` | sums |
| `aggressive_buy_base`, `aggressive_sell_base` | sums |
| `delta_base` | `aggressive_buy_base - aggressive_sell_base` of the sums, exactly as `BarBuilder` computes it |
| `vwap` | `volume_quote / volume_base`, or `close` when `volume_base` is zero — the builder's own rule, `builder.py:176` |
| `high_time_ns`, `low_time_ns` | the times from the bars holding the extremes |
| `first_trade_id` | first bar's `first_trade_id` |
| `last_trade_id` | last bar's `last_trade_id` |
| `is_final` | `True` — a window is only folded when complete and closed |

**`vwap` is the one field that is not a sum or an end value.** A mean of
five means is not the mean of the whole unless every bar carries equal volume,
which is precisely what a bar does not guarantee. Recomputing from the summed
quote and base volumes is exact. A test pins this against a window whose minutes
differ in volume, because averaging the averages produces a plausible number.
