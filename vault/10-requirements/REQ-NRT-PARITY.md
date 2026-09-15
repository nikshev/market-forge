---
id: REQ-NRT-PARITY
title: A captured live segment replays to the same features, channels and signals
type: constraint
prd_ref: "§35.5"
prd_lines: "4889-4895"
phase: null
status: draft
depends_on: [REQ-WP-066, REQ-NRT-LEAK]
tags: []
hard_gated: true
---

## Requirement

PRD §35.5, quoted in full:

> **Live/replay parity**
>
> Capture a 30–60 minute live event segment.
>
> Replay it offline.
>
> Assert feature/channel/signal parity.

The token is a word rather than a letter, for the reason [[REQ-NRT-REPAINT]]
gives: `REQ-NRT-A` through `-F` are §13A.28's own six named tests.

### What [[REQ-NRT-E]] covers, and why it is not this

`REQ-NRT-E` is §13A.28's Test E — *"live recorded outputs and deterministic
replay outputs must match"* — and it is `implemented`. Its tests differ from
§35.5 in both scope and method:

- **Scope.** They run `detector().run(history)` over **extrema detectors only**.
  §35.5 asks for *feature*, *channel* **and** *signal* parity.
- **Method.** Their "live" run is a second in-process call of the same function
  on the same list. That proves determinism, which is worth proving. §35.5 asks
  for a segment **captured from a live socket**, written down, and replayed from
  what was written — which additionally exercises the archive, the decoder, and
  every boundary between the socket and the feature.

A function that is deterministic in one process can still disagree with itself
across a capture-and-replay boundary, and the places it would disagree — frame
ordering, a timestamp narrowed on the way to disk, a field the archive drops —
are exactly the ones `detector().run(history)` twice cannot reach.

### Step one already exists

[[REQ-WP-066]]'s ingest daemon archives one gzip object per minute of raw
frames, and the running deployment has been doing it for 43 hours. Measured:
**1,717 minutes** captured across two days at roughly **8 KB per minute**, so a
sixty-minute segment is comfortably under a megabyte and can be committed as a
CI fixture like every other capture in this repository.

So §35.5's first line is satisfied by data the system already produces. What is
missing is the second and third.

## Acceptance

- A segment of **30–60 minutes** of captured raw frames is committed as a
  fixture, with the block of wall-clock time it covers recorded beside it.
- The replay reads that fixture from disk — not a second call against an
  in-memory list. The archive and the decoder are part of what is under test.
- Parity is asserted for **all three**: features, channels and signals. A run
  that compared features alone would satisfy the word "parity" and miss two
  thirds of the sentence.
- Every compared value is named in the failure, not merely counted. "17
  mismatches" sends nobody anywhere.
- The comparison covers what was produced *and* what was not: a replay emitting
  fewer signals than the live run fails, and so does one emitting more.
- A deliberately divergent replay is caught and named, proven by introducing
  one.
- It runs in CI with no services and no network.

## Trace

<!-- trace:begin -->
_No linked artifacts yet._
<!-- trace:end -->

## Notes

Human territory. Never machine-rewritten.
