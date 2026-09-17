---
id: OUT-2026-09-17-spec-live-replay-parity
step: spec
records: [REQ-NRT-PARITY]
commit: null
---

## What was done

Specified [[REQ-NRT-PARITY]] as `specs/116-live-replay-parity/spec.md`, captured
a 45-minute live segment with `tools/record/parity_capture.py` — and the capture
found a defect in the raw archive before a single parity assertion ran.

**[[REQ-NRT-PARITY]] stays at `specified`.** Its parity assertion cannot run on
the fixture that exists, because that fixture was captured from the broken
archive. What is delivered here is the spec, the capture tool, the defect, its
fix, and the tests that guard it.

## The defect §35.5 found before it asserted anything

`FrameArchive.flush()` wrote the buffered frames under the current minute's key
and cleared the buffer. `store.put` **replaces** an object. So a flush in the
middle of a minute — the ingest daemon does one on its commit cadence — wrote
what it had, and the frames arriving afterwards in that same minute were written
**alone** when the minute closed. The minute was replaced by its own tail.

Proven in ten lines: add five frames, flush, add five more, roll the minute. The
object holds five, and they are the last five.

Measured on the running deployment, across the 45 captured minutes:

| | |
|---|---|
| minutes short of their bar's trade count | **45 of 45** |
| frames missing at the **start** of a minute | 19 to 465 |
| frames missing at the **end** | 0 or 1 |
| worst minute | 274 archived against 744 traded |

The aggregate trade ids inside each object are contiguous, so this was never
scattered loss. Each object is a clean suffix. The nought-or-one at the end is
the ordinary skew between receipt and event time at a boundary: a trade at
`:59.99` can be received at `:00.01` and archived under the next minute.

**Why this matters more than a count.** PRD §6.4.4's raw tier exists so a later
build can re-normalize what this one could not read, which is why
[[REQ-WP-066]] archives every frame *before* deciding anything about it. A tier
silently holding a third of each minute cannot do that, and nothing would have
noticed: the bars were right, the charts were right, and the only thing wrong
was the record kept in case they ever were not.

**The fix** keeps what a minute has already had, not only what arrived since the
last write, and releases it when the minute rolls so a long-running daemon does
not accumulate. Eleven mutations against `archive.py`, including three that undo
exactly this, all caught.

## What was decided

**The fixture is kept as evidence, and the test says what of.** It cannot
demonstrate parity, so it does not claim to: it pins the shape of the loss —
contiguous ids, short at the start, whole at the end — because that is what it
honestly shows, and because a later capture that still looked like this would
mean the fix did not take.

**The tolerance was measured, not chosen.** "Nought or one missing at the end"
is the observed distribution across all forty-five minutes, not a number picked
to make a test pass.

**The deployment was restarted with the fix** so clean minutes accumulate. A
second capture, and then §35.5's actual parity assertion, is the next step.

## What is still open

- **The parity assertion itself** — bars, channels and signals — awaits a
  segment captured from the fixed archive.
- **How much history is affected.** Every minute archived before today is short
  by its prefix. The bars built from those frames are correct, because the live
  path decoded every frame it received; it is the raw tier that cannot be
  replayed. Nothing in this project has needed to replay it yet, which is why
  the loss was invisible.
