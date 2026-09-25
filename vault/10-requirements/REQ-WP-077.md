---
id: REQ-WP-077
title: Channels, signals and extrema are produced for the running deployment
type: work-package
prd_ref: "§6.2, §25.1, §29.6"
prd_lines: "405-420, 4200-4210, 4653-4668"
phase: null
status: planned
depends_on: [REQ-PIPE-001, REQ-WP-073]
tags: []
---

## Requirement

§6.2's MVP compose list names a service this deployment does not have:

> - `api`
> - `worker`
> - `ingest-binance`
> - …

`docs/deployment.md` records why: "`worker` is the one §6.2 service with no
container, because it has no code: [[REQ-PIPE-001]] chose a replay over a
daemon." That was the right call for building the pipeline and it leaves a
deployment with bars and nothing else.

**Measured on the running stack, 2026-09-17**: the `bars` table holds 133 rows
and `channel_snapshots` holds **0**. Nine services run; none of them fits a
channel. §29.6's table exists, §28.3's read serves it, the chart draws it — and
nothing produces it.

### The code exists; nothing runs it

`channelflow.pipeline.replay` already holds both halves, and they are already
separated the way this needs:

- `record_bars(trades, …)` aggregates trades into bars and writes them.
- `record_replay(bars, …)` — "Replay `bars` and write the channel snapshots and
  signals it produced" — reads bars and writes channel snapshots, signals,
  confirmed extrema and extremum candidates. Its own comment is explicit that
  "this function reads it and never writes it" of the `bars` table.

So the missing piece is not an algorithm. It is a process that reads the bars
this deployment already has, at each configured timeframe, and calls the
function that exists. This is the "deployment work" [[REQ-PIPE-001]] named and
deliberately excluded.

### Why it depends on the resampler

`record_replay` fits a channel over the bars it is given, and a channel at 4h is
a fit over 4h bars. Until [[REQ-WP-073]] produces those series, this process has
one timeframe to work on. The two together are what makes a timeframe control
([[REQ-WP-074]]) show a channel at every position rather than at one.

### What must not be assumed

Every recorder in `replay.py` carries a watermark and skips what the table
already covers, so repetition is already designed for. That is a property to
**verify under this requirement's own conditions** — a loop running every few
minutes over a growing series is not the same exercise as a single replay over
a fixture — not a property to inherit on trust.

## Acceptance

- After one pass, `GET /api/v1/channels` answers for a `(venue, symbol,
  timeframe)` that has bars, where before it answered with nothing.
- A pass runs for each configured timeframe ([[REQ-WP-073]]), not only the
  ingested one.
- A second pass over unchanged bars writes **zero** new channel snapshots,
  signals, confirmed extrema and extremum candidates — proven by counting rows
  before and after, not by trusting the watermarks.
- A pass writes nothing for a timeframe whose bars do not exist yet, and says so
  rather than failing.
- Channel snapshots are written once and never rewritten — Constitution III and
  §29.6's "Immutable append-only". A pass that re-fits an already-recorded
  moment must not replace it.
- One timeframe failing does not end the pass; the failure is named and the
  remaining timeframes are done, the rule `maintenance_main` already follows.
- A signal reaches the table in its final state only, never one row per bar —
  the property [[REQ-PIPE-001]] established, re-checked here because a loop
  invokes it far more often than a fixture does.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-122-channel-production]]
- **Outcomes:** [[OUT-2026-09-24-spec-channel-production]]
<!-- trace:end -->

## Notes

Human territory. Never machine-rewritten.
