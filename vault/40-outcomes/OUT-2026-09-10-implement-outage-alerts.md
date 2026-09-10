---
id: OUT-2026-09-10-implement-outage-alerts
step: implement
records: [REQ-WP-035]
commit: null
---

## What was done

`channelflow/health.py` (PRD §32's four states and the assessment) and
`alerting/outages.py` (the alert, its renderer, the watch). 22 tests; 18 of 18
mutants caught after the sweep.

RED first: both test modules failed to import what they were testing.

## What the sweep found

Fifteen mutants died against the first test set. Three survived, and one of them
was not a missing test — it was a **guard that could not fire**.

**"The worst reading decides" was indistinguishable from "the last one
decides".** The rule list happened to run in non-decreasing severity — two
DEGRADED, then STALE, then two INVALID — so overwriting the running answer on
every bad reading produced the same result as keeping the worst. The guard was
correct, unreachable, and untestable at the same time.

The fix is not a test. The list is now in **§32's own order**, which is
deliberately not sorted by severity: a gap rate is checked before missing bars
and is worse than it. The guard is now load-bearing, and a test asks for exactly
that case. Following the PRD's order is also a better reason than "so a test can
fail", and it is the reason a tenth metric will not quietly reintroduce the
problem.

The other two were ordinary gaps: the assessment reading nothing at all was
asserted only through its message and not its state, and the notification id
named the feed but not the state it announced — so a feed degrading and then
failing at the same instant would have carried one identity, and any dedupe
reading it would drop the second.

## What was decided while building

- **"Nothing reported" is INVALID, with the reason carrying the difference.**
  A fifth state would need a rule in each of §32's four eligibility lines that
  the PRD never gives. "Invalid because gappy" and "invalid because silent" are
  distinguished by the reason, which is where a reader needs the difference
  anyway.
- **An unreported metric is held against the feed at the state it would have
  produced.** Not at some generic penalty: an unreported gap rate is exactly as
  informative about whether to trust this stream as a bad one.
- **`HealthState` is an `IntEnum`.** The ranking is the mechanism, not a
  convenience, and it has its own test — mis-ordered, a stale feed outranks an
  invalid one and every assessment still returns a plausible state.

## What is still open

- **Nothing produces a health reading.** No connector runs, so nothing counts a
  reconnect or a gap. This assesses and announces what it is handed, as
  [[REQ-WP-031]] carries a ratio nothing writes.
- **§33's metrics export and dashboards** remain a separate Phase 8 deliverable.
- **§32's eligibility rules have no consumer**: no signal path reads a health
  state yet.
- **Whether a DEGRADED feed should escalate on duration alone.** An hour
  degraded is arguably a different fact from a second degraded.
