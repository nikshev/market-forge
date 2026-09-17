# Phase 0 Research: Bars at every configured timeframe

## 1. Window alignment

**Decision**: a timeframe carries a duration *and* an origin. Window start is

```python
((t - origin_ns) // ns) * ns + origin_ns
```

Every timeframe but the week has `origin_ns = 0`, where this reduces exactly to
`BarBuilder.window_start`'s existing `(t // ns) * ns`.

**Rationale**: measured, not assumed. 1 January 1970 was a **Thursday**, so
`(t // 604800e9) * 604800e9` opens weekly windows on Thursdays:

| instant | naive floor | with origin |
|---|---|---|
| 2026-09-17T09:15:00Z | 2026-09-17 **Thu** | 2026-09-14 **Mon** |
| 2026-09-14T00:00:00Z | 2026-09-10 **Thu** | 2026-09-14 **Mon** |
| 2026-09-13T23:59:59Z | 2026-09-10 **Thu** | 2026-09-07 **Mon** |

The origin is the first Monday at or after the epoch, 1970-01-05, which is
`4 * 86400 * 10**9 = 345_600_000_000_000` ns.

**A language-specific caveat that needs a test.** For an instant *before* the
origin the expression relies on Python's floor division rounding toward negative
infinity: `1970-01-01T00:00:00Z` yields 1969-12-29, a Monday, which is right. A
truncating division — C, Go, Rust, and JavaScript's `Math.trunc` — would round
toward zero and give a Thursday again. Nothing in this repository is at risk
today, but the same arithmetic is destined for the frontend, so the property is
pinned by a test rather than by this paragraph.

**Alternatives rejected**:

- *Special-casing the week in the caller* — puts the correction somewhere every
  future caller has to remember it, which is how the second caller gets it wrong.
- *Storing a weekday offset as configuration* — configurable Monday is a setting
  nobody would ever change, and a wrong value produces bars that look plausible.

## 2. Completeness

**Decision**: a window `[s, s + T)` at timeframe `T` over a source of `S` is
complete exactly when the number of distinct source bars whose `open_time_ns`
falls in the window equals `T // S`.

**Rationale**: it is a count, so it is checkable without a clock, and it
distinguishes the case that matters — a window with 237 of 240 minutes — from a
complete one. Every source bar in the table is final (`to_row` refuses
otherwise), so presence is the whole test; there is no second condition about
finality to get wrong.

**Alternatives rejected**:

- *Trusting contiguity of the first and last minute* — a gap in the middle passes.
- *A watermark on the source* — tells you time moved on, not that rows exist.

## 3. Idempotence

**Decision**: each pass reads the `open_time_ns` values already stored for
`(venue, symbol, timeframe_ns)` and produces only the windows absent from that
set.

**Rationale**: measured — `BarSink.flush` is `self.table.append(self._buffer)`
and `IcebergTable` offers no upsert, no delete-by-key and no predicate
pushdown. A second pass would therefore append a duplicate of every bar, and no
layer below the producer would object. Idempotence has to be the producer's
property.

Cost, measured on the running stack: `rows=89 full_read=132ms`. [[REQ-WP-068]]
measured the same read at 717 files as 6478ms before compaction and 45ms after,
and compaction already runs on a loop. So the cost is bounded by machinery that
exists.

**Alternatives rejected**:

- *A stored watermark* — cheapest, and it forecloses the late-minute case the
  spec allows: a window behind the watermark could never be filled, leaving a
  permanent hole indistinguishable from a quiet market.
- *Delete and rewrite the timeframe each pass* — buildable with
  `delete_rows_before`, violates Constitution III on every pass, and makes the
  one destructive operation in this system routine.

## 4. Where the process lives

**Decision**: a new module and a new compose service, `resample`, mirroring
`maintenance`'s shape — pure functions in one file, the loop in another.

**Rationale**: `maintenance` prunes, compacts and expires; it removes. A
producer of canonical rows inside it would be invisible to whoever reads the
compose file. The cost is a tenth service, which is real and is the reason this
was considered at all.

**Alternatives rejected**:

- *Inside the ingest daemon, after each flush* — couples a socket-paced process
  that must keep up with a live feed to a whole-table read.
- *On read, in the API* — every reader pays the aggregation, nothing is stored,
  and §29.4's `timeframe` column stops meaning anything.

## 5. Configuration surface

**Decision**: `CHANNELFLOW_TIMEFRAMES`, a comma-separated list of tokens
(`5m,15m,30m,1h,4h,1d,1w`), parsed by `channelflow.timeframes`.

**Rationale**: §31 describes a `timeframes:` list per market, and this
deployment configures by environment (there is no §31 YAML loader yet, and
building one is not this requirement). One parser, at package root, because the
read API and the markets view will need the same set and a second reader of the
same variable would drift from the first — the reason `settings.py` gives for
its own location.

**Open, and deliberately left to [[REQ-WP-075]]**: how the frontend learns the
set. FR-002 forbids it holding its own copy, and §28 lists no endpoint that
carries it. That is a decision about the API surface and belongs with the view
that needs it, not here.

## 6. Calendar periods

**Decision**: the token parser refuses `1M` and any other calendar-defined
period, with a message naming the reason.

**Rationale**: `timeframe_ns` is `int64` nanoseconds and a calendar month is
28–31 days, so there is no value to store. Refusing at the parser puts the
refusal in one place, where configuration, a future API parameter and anything
else that parses a token all meet it.

**Alternatives rejected**:

- *30 days* — drifts against the calendar, invisibly to anyone reading a chart.
- *Silently dropping unknown tokens* — a configuration typo would then produce a
  missing timeframe and no message, which is the failure mode this repository
  keeps finding and keeps deciding against.
