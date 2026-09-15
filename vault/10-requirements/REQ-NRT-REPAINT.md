---
id: REQ-NRT-REPAINT
title: Repaint regression over a stream of stored channel snapshots
type: constraint
prd_ref: "§35.3"
prd_lines: "4870-4877"
phase: null
status: specified
depends_on: [REQ-WP-006]
tags: []
hard_gated: true
---

## Requirement

PRD §35.3, quoted in full — the section calls it the *critical test*:

> **Critical test:**
>
> 1. Feed bars one at a time.
> 2. Store channel snapshots.
> 3. Continue feeding future bars.
> 4. Assert all previous snapshots unchanged.

**The token is a word, not a letter.** `REQ-NRT-A` through `REQ-NRT-F` are
§13A.28's six named tests, "Test A" to "Test F". This is a different section, and
lettering it `G` would claim §13A.28 has a seventh test it does not.

### What already holds, and why it is not this

`tests/unit/channels/test_no_lookahead.py::test_appending_future_bars_does_not_change_a_past_snapshot`
fits `RollingOLSChannel` at one moment, appends future bars, **refits the same
moment**, and demands the same answer. That proves the fit is a function of its
prefix — a real property, and the one [[REQ-WP-006]] was written for.

§35.3 asks for something a refit cannot catch. It says *store* the snapshots and
assert the **stored** ones are unchanged. The failure that separates the two is a
model that returns a correct value and then mutates what it already handed out:
a snapshot holding a view into a rolling buffer, a cached array reused between
calls, a field filled in later "once we know". A refit constructs a fresh answer
every time and never looks at the old one, so it is blind to exactly this.

It is also one model at one moment. Four models exist — `RollingOLSChannel`,
`HuberChannel`, `QuantileChannel`, `KalmanChannel` — and `KalmanChannel` is the
one where this matters most, because a filter carries state between bars by
design.

## Acceptance

- Bars are fed **one at a time**, and a snapshot is taken and retained after
  each. Not a refit: the object handed out earlier is the object checked later.
- After every subsequent bar, **every** previously stored snapshot is compared
  against what it was when it was stored, and must be unchanged.
- The comparison is by value over the whole snapshot, not over a chosen field. A
  check that compared only the centre would pass a model that repainted a band.
- It runs for every channel model, enumerated mechanically from the package, so
  a model added later without this test is a red suite rather than an omission.
- A model that deliberately mutates a stored snapshot is caught and named —
  proven by a test that introduces exactly that fault and watches the suite fail.
- The suite needs no services and no network.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-114-repaint-and-leak-suites]]
- **Outcomes:** [[OUT-2026-09-15-spec-repaint-and-leak-suites]]
<!-- trace:end -->

## Notes

Human territory. Never machine-rewritten.
