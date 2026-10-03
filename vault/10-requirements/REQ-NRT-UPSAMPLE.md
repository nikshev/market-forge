---
id: REQ-NRT-UPSAMPLE
title: No unfinalized higher-timeframe close reaches a lower-timeframe consumer
type: constraint
prd_ref: "§13A.17"
prd_lines: "1853-1875"
phase: null
status: specified
depends_on: [REQ-WP-073]
tags: [timeframes, non-repainting]
hard_gated: true
---

## Requirement

PRD §13A.17's closing sentence, quoted verbatim:

> Do not upsample a higher-timeframe future close into lower-timeframe features
> before that higher-timeframe bar is finalized.

The section it closes is about extrema: "Extrema should be computed
independently on each timeframe and optionally linked", with an example that
ends "This is not equivalent to a 1h top", and a list of five optional
confluence features. **That subject is not this note.** §13A.17's extrema
hierarchy and its confluence features have no requirement note yet; this one
extracts only the prohibition, which is the part that binds any component
producing or consuming bars at more than one timeframe.

**The token is a word, not a letter**, for the reason [[REQ-NRT-REPAINT]] gives:
`A`–`F` are §13A.28's own six named tests, and lettering this one would claim
that section has a seventh.

### What this forbids that nothing else already forbids

Three rules in this repository sound like this one and are not it:

- The `bars` table already refuses an unfinalized row — "a canonical table
  holding an unfinalized bar would hold a row that is still going to change"
  ([[ADR-005]], `src/channelflow/tables/bars.py`). That governs **writing**.
- [[REQ-NRT-LEAK]] (§35.4) demands a feature give the same value on a truncated
  and a full dataset. That governs **one feature's own computation**.
- Constitution Principle I forbids look-ahead generally.

This one governs the **seam between two timeframes**: a 1h bar that has not
closed at `t` must not reach anything computed at `t`, however it travelled
there. A resampler that emits a partial window produces a row that satisfies
every rule above at the moment it is written and is still a future close handed
backwards.

### Why a resampler makes this urgent

A higher timeframe assembled from stored one-minute bars has a failure the
trade-driven `BarBuilder` does not: its input can be **incomplete without being
late**. `BarBuilder` sees a trade stream and closes a window when its watermark
passes; a resampler sees rows, and a window missing three of its 240 minutes
looks exactly like a window that has all of them unless something counts. A bar
computed from what happened to be there is wrong in a way no downstream reader
can detect.

## Acceptance

- A higher-timeframe bar covering `[s, s + T)` is published only once every
  constituent source bar in that window is present and final. A window with a
  missing source bar yields **no bar**, not a bar computed from the rest.
- An incomplete window is **refused with a reason that names the window and what
  was missing**, and the refusal is visible to the caller rather than logged and
  swallowed. A silent skip and a correct bar are indistinguishable to a reader,
  which is the failure this exists to prevent.
- Asking for the `T` bar as of any instant strictly inside `[s, s + T)` returns
  nothing for that window. Proven by asking, not by inspecting `close_time_ns`.
- A consumer computing at `t` never reads a higher-timeframe bar whose
  `close_time_ns` is greater than `t`.
- A deliberately leaking resampler — one that emits the window in progress — is
  caught by the suite and **named**, proven by introducing one. A constraint
  whose test has never seen the violation it forbids is a constraint nobody has
  checked.
- The suite runs in CI with no services and no network.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-125-no-unfinalized-upsample]]
- **Outcomes:** [[OUT-2026-10-03-plan-no-unfinalized-upsample]], [[OUT-2026-10-03-spec-no-unfinalized-upsample]], [[OUT-2026-10-03-tasks-no-unfinalized-upsample]]
<!-- trace:end -->

## Notes

Human territory. Never machine-rewritten.
