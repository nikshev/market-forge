---
id: REQ-WP-104
title: "The stack answers in seconds, not minutes: one resample read and commit per pass, filters in Arrow, and every table compacted"
type: work-package
prd_ref: "§36 (chart historical load p95 < 2 s), §29.0; owner's report 2026-10-13"
prd_lines: "6034-6052"
phase: null
status: tested
depends_on: [REQ-WP-068, REQ-WP-070, REQ-WP-073, REQ-WP-100]
tags: [performance, resample, lakehouse, api]
hard_gated: false
---

## Requirement

On 2026-10-13, asked to add loading spinners because "it is not clear whether it is a bug or it is just taking this long to load"
([[REQ-WP-103]]), the stack was measured: **a bars request took 54 s and the volume profile 82 s** (§36's budget is 2 s), the host's
load average was 41, `resample` was at 345 % CPU, MinIO at 250 %, swap full. Four causes, each measured, and the first three
cost nothing to fix once seen:

1. **The resample pass read the whole bars table once per `(series, timeframe)` and committed per series.** Seventeen series at
   seven timeframes is over a hundred reads of a table of hundreds of thousands of rows every five minutes, plus a snapshot per
   series that had something to write. It reads **once** and commits **once** (the same rule the worker's context pass learned),
   with the windows each target already holds taken from that one read.
2. **`volume_bins` was in no maintenance pass.** It is written by every ingest daemon; it had **5,077 files** and a 23 s read, which
   is the volume profile. Maintenance names its tables rather than discovering them, so a table nobody decided about is never
   compacted -- a test now fails if any table module declares a table the list does not cover.
3. **Maintenance ran every six hours**; the files accumulate all day and a read costs a request per file (1,482 in `bars` made a bars
   request take 8 s). The default is **one hour**: a pass over a compacted table takes seconds.
4. **The API turned every row of a table into a Python dict before filtering** -- the features table is over a million rows and one
   chart wants a few thousand. The bars, features, consensus and volume-bin reads **narrow in Arrow first** (`narrow`), and only the
   rows that remain become dicts. (This is the smallest of the four -- the dict conversion was 2 s of 5 -- and the cheapest to
   keep: nothing is held that the answer does not need.)

None of this changes what is computed or returned.

## Acceptance

- A resample pass reads the table exactly once and appends at most once, for any number of series and timeframes; it produces the
  bars it produced before; a pass with nothing to write commits nothing; a failed commit writes nothing, is named, is not counted
  as written, and the next pass writes the windows; one series that cannot be resampled does not stop the others (tests).
- `narrow` keeps the rows meeting every condition in the order they had, supports ranges closed at both ends and open at either,
  treats `None` as "not asked", and refuses an unknown column (tests).
- The maintenance table list covers every table a `tables/` module declares (test).
- On the running stack after the deploy: the resampler is off the top of the CPU list and the object store's load falls; a bars
  request, the volume profile and the features series answer in a fraction of their former time, and the files in `bars` and
  `volume_bins` are in the tens, not thousands.

## Trace

<!-- trace:begin -->
<!-- trace:end -->
