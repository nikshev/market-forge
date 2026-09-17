---
id: OUT-2026-09-17-implement-live-replay-parity
step: implement
records: [REQ-NRT-PARITY]
commit: null
---

## What was done

Closed PRD §35.5. A 30-minute segment captured from the running deployment
replays offline to the same **bars, channels and signals** — the three §35.5
names. [[REQ-NRT-PARITY]] reaches `implemented`.

With it, every section of this family now has a requirement and a test: §13A.28
(A–F), §35.3, §35.4 and §35.5.

- `tools/record/parity_capture.py` — captures both halves from a live stack.
- `tests/unit/parity/test_live_replay_parity.py` — seven tests over the whole
  chain: frames → bars → channels → signals.
- `tests/fixtures/parity/` — 31 archived objects (316 KiB) and 30 live bars.

## The defect this found, and what closing it proved

The first capture found `FrameArchive.flush` replacing each minute with its own
tail. That is written up in `OUT-2026-09-17-spec-live-replay-parity.md`; what
belongs here is the **confirmation**, because a fix is a claim until the thing
that found the defect stops finding it.

| | before the fix | after |
|---|---|---|
| minutes short of their bar | 45 of 45 | 0 of 30 |
| offset at the **start** of a minute | +19 to +465 | −1 to 0 |
| offset at the end | 0 to +1 | 0 to +1 |

The start offset is the whole signature. Before, the archive always began late,
by as much as 465 trades. Now it begins within one trade of its bar, in either
direction — the ordinary skew between receipt and event time at a boundary, and
symmetric, which a loss never is.

## What was decided

**Three margins, each for a different reason**, and each found by a failure
rather than foreseen:

- *At the start of the segment*, because a bar spanning the edge saw trades the
  segment does not hold.
- *At the end*, because the builder finalizes a minute when a trade arrives
  after it — without a trailing object the replay produces one bar fewer, which
  looks like a parity failure and is a fixture stopping one minute too soon.
- *Back from the present*, because the bar sink commits on a cadence: the newest
  minutes have frames in the archive and no bar in the plane. Measured as the
  last three of a window taken up to now; the capture now backs off
  `FLUSH_EVERY_BARS + 3`.

**The capture refuses a fixture it cannot compare.** If any window minute has no
live bar it exits, naming them. That failure would otherwise arrive as a parity
mismatch and cost somebody a morning on the replay when the fault was the
capture.

**The tolerance is a measured distribution.** Start offset ∈ {−1, 0}, end offset
∈ {0, 1}, over all thirty minutes. Not a number chosen until the suite passed.

**The live bars are taken as given.** This asserts that a replay reproduces them,
not that they are right; what makes them right is every other test here.

## Why this was worth more than [[REQ-NRT-E]]

`REQ-NRT-E` runs `detector().run(history)` twice in one process. It proves
determinism. This drives the frames through the archive's own reader, the
`ReplayTransport` a backfill uses, and the `IngestDaemon` the deployment runs —
and it found, on its first capture, that the raw tier had been holding a third
of each minute. No amount of calling a pure function twice would have.

## What is still open

**The history before 2026-09-17 is short by its prefix.** The bars built from it
are correct — the live path decoded every frame it received — but that stretch of
the raw tier cannot be replayed. Nothing has needed to yet, which is why the loss
was invisible.

**One symbol, one timeframe**, per [[REQ-WP-066]]'s one-process-per-symbol shape.
A second would exercise the same code.
