---
id: OUT-2026-10-13-implement-loading-indicators
step: implement
records: [REQ-WP-103]
commit: null
---

## What was done

Specified, planned and implemented [[REQ-WP-103]] (spec 155) in one step; status `tested` until the deployed check.

- `Busy.tsx`: one spinner, a `progressbar` with a name (inline or with a caption).
- Overview: markets and timeframes. Chart page: timeframes; a spinner over the chart (mounted beneath) until the first bars answer; a small
  mark by the title during a reload; each pane until its own answer (`pointsLoaded` for the feature panes, `barsLoaded` for Volume), with no
  "no data" claim meanwhile; the volume profile; the consensus when its layer is on.
- `LiveChip` + `useLiveBars`: a `connecting` status with a spinner until the feed has spoken; `delayed` only for a feed that is not
  connected or will not carry the series.
- `index.html`: a spinner in `#root` before the script has loaded.

## Evidence

**RED first**: `busy.test.tsx` and `appBusy.test.tsx` failed before the code (no `Busy`, no spinners, no `connecting`). **GREEN**: the
web suite (612 tests) and `tsc`; the pytest artifact file (18 tests).

In a headless browser against the rebuilt image the spinners were on screen -- *and the stack was genuinely that slow*: with no help
from the test, a bars request took **54 s** and the volume profile **82 s**, with the host's load average at 41 (`resample` at 345 % CPU,
MinIO at 250 %, the worker at 95 %, swap full). That is what the owner was looking at; it is not a bug in the page, and it is a real
problem the spinners now make visible rather than hide.

## Deployed check (2026-10-13)

With the data requests held back in a headless browser against the rebuilt image the page showed, in turn, the boot spinner, "Loading
timeframes", "Loading the chart", the profile's and the pane's spinners, and none was left once the requests completed. After
[[REQ-WP-104]] the whole page is free of spinners in 9 s.

## What is still open

- The slow API: a read competes with the resampler and the worker for the object store. Measured, not fixed here.
- The DEX depth overlay (only when a link names a pool) has no spinner; it is not on any chart the deployment links to.
