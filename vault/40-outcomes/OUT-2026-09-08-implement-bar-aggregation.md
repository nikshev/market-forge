---
id: OUT-2026-09-08-implement-bar-aggregation
step: implement
records: [REQ-WP-005]
commit: null
---

## What was done

All 13 tasks. `Bar` with the fourteen fields PRD §12 lists, and a `BarBuilder`
that accumulates on event-time windows and finalizes by watermark. Nine bar
tests, 209 in the suite, `mypy --strict` clean over 16 source files.

## Three real defects, each found by a test rather than by review

**Decimal arithmetic was silently rounding at 28 significant digits.** A VWAP
test with a 29-digit price failed, and the loss was not in the division — it was
in `price * quantity`, which meant it reached `normalize.py`'s `notional_quote`
too, in REQ-WP-003, already merged. Python's default decimal context applies to
every operation in the codebase. REQ-WP-002 claims exact monetary arithmetic;
at 28 digits that was true of every realistic value and false of the values its
own tests used. Fixed by setting the context explicitly at package import and
guarding it with a test — [[ADR-006]]. No practical value was ever at risk,
which is precisely why it survived a whole requirement unnoticed.

**`high_time_ns` and `low_time_ns` depended on arrival order.** The comparison
was strict, so when a price repeated, whichever copy arrived first won. Shuffle
the same trades and the timestamps changed — meaning a replay would produce
different history from identical input, and Principle VII would not hold. Fixed
by breaking ties on the earliest event time. Found by SC-003's shuffle test,
which exists for exactly this.

**A guard that did not guard.** Mutation-checking the late-event policy showed
that removing the discard still left all nine tests passing. The test asserted
the published bar was unchanged — but a published bar is frozen and handed away,
so it could not change. What the mutation actually caused was a *second* bar for
an already-closed window: the first bar untouched, the history rewritten anyway.
The test now asserts a finalized window produces exactly one bar ever, and the
mutation fails.

## What was decided

- **A tie on high or low goes to the earliest event time**, not the first
  arrival. Arrival order is not market information.
- **Precision is process-wide rather than per-call-site.** A `localcontext` at
  every arithmetic site is the kind of discipline that holds until someone adds
  a helper; an absence of local contexts is easier to verify than their presence
  everywhere.
- **Division is still not claimed exact.** ADR-006 says 60 digits reduces loss
  rather than abolishing it, and a test asserts one-third times three is not one
  — so nobody later reads the precision as a guarantee it never was.

## What is still open

- **The five-second grace default remains unmeasured.** ADR-005 said it needs
  checking against real venue behaviour; the late-trade counter is what will
  show whether it is wrong, and nothing has run against a live stream yet.
- **A quiet market leaves the last bar open indefinitely**, by design. A
  consumer needing a heartbeat must supply one as an explicit event.
- **Multi-timeframe fan-out is the caller's**, unbuilt.
- **No persistence.** PRD §29.4's `bars` table is separate.
