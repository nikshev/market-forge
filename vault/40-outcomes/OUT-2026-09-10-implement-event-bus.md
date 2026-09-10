---
id: OUT-2026-09-10-implement-event-bus
step: implement
records: [REQ-INFRA-003, REQ-PHASE-0]
commit: null
---

## What was done

`channelflow/bus.py` (the mechanism, knows no domain type) and
`channelflow/events.py` (three values, knows no bus). [[REQ-PIPE-001]]'s replay
path rewired: the builder and the runner each receive one publishing hook, and
the recorders subscribe.

12 new tests, 1504 in the suite, mypy clean at 164 files, 8 of 8 mutants caught.

[[REQ-PHASE-0]]'s last unbuilt deliverable is closed, and the phase reaches
`implemented` — the second one to.

## Does the abstraction earn its place?

The spec pre-committed to answering this rather than choosing the answer
afterwards. **Narrowly yes, and only because of one parameter.**

Against it: `record_bars` got longer. `on_final=finalized.append` was one line
and is now three — a bus, a subscription and a publishing lambda for the same
result. In isolation that call site is worse.

For it: a caller can now observe either path without editing this package, which
was not possible before and is the only concrete cost the current wiring had.
Three tests hold that claim: a subscriber sees every channel snapshot and every
candidate update, adding one does not change what is recorded, and the same
works for finalized bars.

**The version I nearly shipped did not earn its place.** The first working
implementation created the bus *inside* `record_bars` and `record_replay`. Every
test passed, the deliverable looked closed, and a caller still could not observe
a bar without editing the file — the coupling had been moved, not removed. The
`bus` parameter is what makes the difference, and it was missing until the test
that was supposed to prove the benefit turned out to be unwritable.

## What was decided

- **`publish` iterates a copy.** A handler that subscribes another one would
  otherwise get a `RuntimeError` or a silently skipped handler depending on which
  way the list mutated.
- **A subscriber's exception propagates.** In a replay a swallowed handler is a
  missing row nobody hears about.
- **Exact-type dispatch, no unsubscribe.** Both are real features with no caller.
  A bus whose subscriptions can disappear mid-run is harder to reason about in a
  replay than one whose cannot.
- **`CandidateUpdated`, not `SignalOpened`.** The machine emits the same signal
  on every bar it is alive for, each time more complete. The wrong name here is
  how a reader ends up counting bars and calling them signals — the distinction
  [[REQ-PIPE-001]]'s recorder already had to make.

## What the mutation sweep found

8 mutants, 8 caught — one after fixing a test that did not test what it claimed.

- **B2 (a duplicate subscription is deduplicated) survived.** The test subscribed
  two *different* lambdas that happened to do the same thing, so deduplication
  would not have touched them: it passed whether or not the behaviour existed.
  Subscribing the same object twice is the actual claim.

## What is still open

- **Live mode is what a bus most obviously serves and still does not exist.**
  PRD §25.1's other mode would give the abstraction its second consumer and its
  real reason. Until then the benefit is real but thin: one caller, one
  capability, proven by tests rather than by use.
- **Nothing publishes from inside a producer.** `BarBuilder` and
  `BacktestRunner` remain ignorant of the bus, which is deliberate — but it means
  a caller who constructs them directly gets no events, and nothing says so
  except this note.
