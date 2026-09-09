---
id: OUT-2026-09-09-requirement-replay-recorder
step: requirement
records: [REQ-PIPE-001]
commit: null
---

## What was done

`REQ-PIPE-001`, hand-written from PRD §25.1, §29.B and §0 item 13.

## Why this one next

Three requirements finished today each left the same sentence in their open
questions, in their own words: nothing writes to the plane. Everything else
waits on it — the durable repository has nothing to serve, and
[[REQ-REPRO-001]]'s dataset reference has nothing to reference, which is why
[[REQ-BIAS-011]] stopped at `specified`.

## What was decided

- **Replay, not live.** PRD §25.1 has two modes; the replay one can be tested,
  repeated and pointed at a fixture. A live process attaching the same sinks is
  deployment work and shows nothing this cannot.
- **Feature snapshots and scores stay out**, and the reason is named: a replay
  produces neither, because features come from the registry against a book this
  replay does not have.

## What is still open

- **No resumable backfill.** One replay is one batch per table; resuming needs a
  watermark this does not keep.
