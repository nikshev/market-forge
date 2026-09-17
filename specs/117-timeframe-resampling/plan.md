# Implementation Plan: Bars at every configured timeframe

**Branch**: `wp-073-timeframe-resampling` | **Date**: 2026-09-17 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/117-timeframe-resampling/spec.md`

## Summary

Build the higher timeframes from the stored one-minute series, in a module with
no clock and no IO, driven by a process that mirrors `maintenance`. Three things
planning found reshape the approach: the table has **no deduplication of any
kind**, so idempotence has to be built rather than assumed; window alignment
needs an origin, not just a duration, or weekly bars open on Thursdays; and the
existing read is whole-table, which is affordable now and is the thing that
stops being affordable first.

## What planning measured

**The deployment has one series, and the table has 89 rows.** Read from the
running stack, 2026-09-17:

    rows=89 full_read=132ms
    timeframes present: [60000000000]

So the fifteen-minute request the chart makes returns nothing because nothing
ever produced a fifteen-minute bar — not because of a read bug.

**`BarSink.flush` is a bare append.** `src/channelflow/tables/bars.py`:

    snapshot = self.table.append(self._buffer)

`IcebergTable` exposes `read`, `append` and `delete_rows_before` — no upsert, no
delete-by-key, no predicate pushdown. **A second resampling pass over the same
source would append a second copy of every bar**, and nothing would complain:
FR-009's idempotence is not a property of the storage layer and has to be a
property of the producer.

**`to_row` already refuses an unfinalized bar**, with a message naming §0.5's
repainting. So FR-010 is enforced by the table today; this plan inherits the
guard rather than rebuilding it, and the resampler's own job is to not *offer*
a bar whose window is incomplete — a different condition the table cannot check,
because a complete-looking bar assembled from 237 of 240 minutes is final.

**`read_bars` reads the whole table and filters in Python.** At 89 rows that is
132ms. [[REQ-WP-068]] measured the same shape at 717 files: 6478ms before
compaction and 45ms after. The idempotence check needs the open times already
written, so it pays this read once per pass. Named here because it is the first
thing that will stop working, and because the answer is already built and
scheduled — compaction, every `CHANNELFLOW_MAINTENANCE_INTERVAL`.

**The epoch was a Thursday.** `(t // tf) * tf` with `tf = 604800e9` puts weekly
window starts on Thursdays. Confirmed by arithmetic, not by assumption: the
first Monday at or after the epoch is 1970-01-05, which is `4 * 86400e9 =
345_600_000_000_000` nanoseconds after it.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: none new. The arithmetic is integer division and the
aggregation is a fold; a dependency for either would be a supply-chain cost for
`min` and `max`.

**Storage**: the existing `bars` Iceberg table, read and appended through
`channelflow.tables.bars`. No schema change — a timeframe is already a column.

**Testing**: pytest, `@pytest.mark.trace("REQ-WP-073")`, unit-only. The
resampler is pure functions over rows, so no live service is needed and the
whole suite stays in the fast gate.

**Target Platform**: `src/channelflow/`, `docker-compose.yml`, `.env.example`

**Project Type**: single project — a new module in an existing package

**Performance Goals**: one pass over one venue/symbol/timeframe costs one
whole-table read plus a linear fold. No target beyond "does not grow worse than
the read it already pays".

**Constraints**: no clock inside the resampling functions, for the reason
`BarBuilder` and `FrameArchive` both give — a component that read the time would
be untestable exactly where its behaviour matters.

**Scale/Scope**: seven timeframes × the configured symbols, over a table that is
one day old today.

## Constitution Check

*GATE: passed before Phase 0, re-checked after Phase 1.*

| Principle | How this design satisfies it |
|---|---|
| **I. No look-ahead** | A window is emitted only when closed **and** complete. The completeness count is what makes this more than a boundary check, and [[REQ-NRT-UPSAMPLE]] tests it. |
| **II. Time is not one thing** | `open_time_ns` and `close_time_ns` stay distinct; the window's identity is its open time, the table's event time is its close time. Nothing conflates them. |
| **III. History is immutable** | A window is written once. A window never written may be written later when its missing minute arrives — that is a first write, not a correction. |
| **VII. Live and replay are one code path** | The resampler is pure functions over rows. There is no live variant to diverge from. |
| **X. Thresholds are configuration** | The timeframe set comes from configuration; no component holds it as a constant (FR-002). |
| **XII. Correctness before performance** | The whole-table read is accepted, named and left alone. Optimising it before the feature is correct would be the inversion this principle forbids. |
| **XIV. Everything is traceable** | `# @trace: REQ-WP-073` on every source file; `@pytest.mark.trace` on every test. |

No violations. Complexity Tracking is therefore empty and omitted.

## Project Structure

### Documentation (this feature)

```text
specs/117-timeframe-resampling/
├── plan.md              # This file
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   └── resample.md      # Phase 1 — the module's contract
├── checklists/
│   └── requirements.md
└── spec.md
```

### Source Code (repository root)

```text
src/channelflow/
├── timeframes.py              # NEW: Timeframe, parsing, alignment, refusals
└── pipeline/
    ├── resample.py            # NEW: pure functions — windows, completeness, fold
    └── resample_main.py       # NEW: wiring, loop, report printing

tests/unit/
├── test_timeframes.py         # NEW: tokens, alignment, refusals
└── pipeline/
    └── test_resample.py       # NEW: aggregation, completeness, idempotence

docker-compose.yml             # NEW service: resample
.env.example                   # NEW: CHANNELFLOW_TIMEFRAMES
```

**Structure Decision**: `timeframes.py` sits at package root rather than under
`pipeline/`, because the read API and later the markets view both need the same
set, and a second parser reading the same variable would drift from the first —
the reason `settings.py` already gives for living where it does.

`resample.py` holds no clock and no catalog, exactly as `archive.py` and
`builder.py` hold none. `resample_main.py` is the only file that knows a loop
exists.

## Key decisions

### A process of its own, not a corner of `maintenance`

`maintenance` already loops on `CHANNELFLOW_MAINTENANCE_INTERVAL` and would take
this work with no new container. It is rejected: that service prunes metadata,
compacts and expires — it *removes*. A producer of canonical rows hidden inside
it would be found by whoever reads the compose file last, and "maintenance
wrote my bars" is a sentence nobody should have to say.

The cost is one more service in a stack that has nine. Recorded rather than
waved away.

### Idempotence by reading what is already there

The pass reads the open times already written for `(venue, symbol, timeframe)`
and produces only the windows missing from that set. Rejected alternatives:

- **A stored watermark** — cheapest, and it forecloses the spec's late-minute
  case: a window behind the watermark could never be filled, so every restart
  would leave a permanent hole that looks like a quiet market.
- **Delete-and-rewrite the timeframe each pass** — `delete_rows_before` exists,
  so this is buildable. It violates Principle III on every pass, and turns the
  one operation in this system that destroys into routine.

### Alignment is an origin, not just a duration

`Timeframe` carries `ns` **and** `origin_ns`, and window start is
`((t - origin) // ns) * ns + origin`. Every timeframe but the week has
`origin_ns = 0`, where this reduces to the existing expression. The week has
`origin_ns = 345_600_000_000_000`.

A separate special case for weeks was rejected: it would put the correction in
the caller, and every future caller would have to remember it.

### Calendar periods are refused at the parser

`1M` never reaches the resampler. The token parser raises with a message naming
the calendar-month problem, so the refusal is one place and applies to
configuration, to a future API parameter, and to anything else that parses a
timeframe token.

## Phases

- **Phase 0** — `research.md`: alignment arithmetic, the completeness rule, and
  what the existing table can and cannot guarantee.
- **Phase 1** — `data-model.md` (Timeframe, Window, ResampleReport),
  `contracts/resample.md` (the module boundary), `quickstart.md` (how to prove
  it works against the running stack).
- **Phase 2** — `/speckit-tasks`, not this command.
