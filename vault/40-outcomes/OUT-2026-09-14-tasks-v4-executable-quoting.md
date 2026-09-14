---
id: OUT-2026-09-14-tasks-v4-executable-quoting
step: tasks
records: [REQ-WP-071]
commit: null
---

## What was done

Broke [[REQ-WP-071]] into 39 tasks across nine phases in
`specs/112-v4-executable-quoting/tasks.md`, then ran the cross-artifact analysis
over spec, plan and tasks. It found eight inconsistencies, four of them HIGH.
All eight are fixed; none is deferred.

## What was decided

**A mandated test that could not pass was caught before it was written.** T015
originally asked for the forward and reverse quotes on pool `0x88249e68…` to be
reciprocal to within `1e-6`. Computed from the fixture's own numbers, they differ
by **1.93%**: buying gives `746527124.6970774645442279` `currency1` per
`currency0`, selling costs `760969961.257573001614822577892706206184793472934`.
That gap *is* the round-trip cost, and it is the interesting thing about the
pool. The task now asserts both figures, the gap, and the direction of the
inequality — because a test that only checked "close" would pass with the two
sides swapped, which is the same error wearing a different hat.

**The spec still named an architecture the plan had rejected.** Its Key Entities
listed a `QuoteSource` protocol with live and replay implementations; the plan
had already replaced that with `ChainDataProvider` as the seam, so the encoder is
exercised offline. The spec now names the provider. Two artifacts describing two
architectures is the kind of drift that is invisible until somebody implements
the wrong one.

**SC-004 was stated more strongly than the plan can deliver, and the plan was
right.** It said no test or code path can obtain a depth figure for these pools
from the tick kernel — while the plan mandates exactly one test that goes round
the gate on purpose, to pin what the kernel answers there. The criterion now says
what is true: the gate raises, and one test deliberately bypasses it so the
hazard is asserted rather than assumed away. Weakening a success criterion to
match reality is only honest when the reality is the better design; here it is,
because a hazard nobody has written down is a hazard nobody will remember.

**Our adapter is `ExecutableQuoter`, not `V4Quoter`.** The contract it calls is
already called `V4Quoter`. One name for two things in one module is how a reader
ends up reasoning about the wrong one.

**Also fixed**: the contract's constructor signature omitted the `PoolRegistry`
its own prose required two lines later (a `PoolId` is a hash; without the
registry nothing can be encoded at all); `QuoteNotCaptured` now says where it
lives — with the replay provider in the test tree, since nothing in production
can raise it; T006 no longer asks for a module's test to be written inside the
module under test; and a new T033 covers the spec's edge case that a quote from a
later block is not this quote, which had no task at all.

## What is still open

Nothing from the analysis. The two items carried forward from planning stand
unchanged: the class gate has no chokepoint until a v4→`PoolState` bridge exists,
and `poolManager()` replays from a decoded header value.
