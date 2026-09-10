---
id: OUT-2026-09-10-implement-stop-alert
step: implement
records: [REQ-WP-034]
commit: null
---

## What was done

`alerting/stop_updates.py` (the alert, its renderer, its gate), a `Notification`
protocol in `dispatch.py`, and four small members on `Alert` so it satisfies the
same protocol. 18 tests; 14 of 14 mutants caught after the sweep.

[[REQ-WP-034]] moves to `implemented`, which closes [[REQ-PHASE-7A]] — the
eighth phase.

RED first: the test module failed to import `StopUpdateAlert`.

## What the sweep found

Thirteen mutants died against the first test set. The survivor was the same seam
the whole requirement is about, in a second place:

**`open_risk_before_r` reading the position's last decided stop instead of the
one in force.** The "Old stop" line and the risk figure are two renderings of a
single fact, and the test proving the line was right did not touch the number.
Under that mutation the message reads `Old stop: 111,180` and `0.66R -> 0.28R`
at the same time — a smaller move, from a level the line above says was not the
one — and both halves look plausible on their own.

Worth recording because it is the third time this session that a survivor turned
out to be a second copy of a fact with only one of the copies asserted.

## What was decided while building

- **The dispatcher stops knowing what an `Alert` is.** It now speaks a
  `Notification` protocol — identify, name the instrument, render, link. The
  existing alerting tests pass untouched, which is the evidence the signal alert
  did not change while the thing carrying it did.
- **The cost was a deferred import**, and it is a real one: `models.py` imports
  `render.py` inside two methods, because `render.py` imports `models.py`. The
  alternatives were worse — a formatter inside a frozen record, or a second
  dispatcher duplicating §26.4's retry, dead-letter, audit and never-block
  behaviour. A duplicated retry policy diverges silently, and the failure is one
  alert kind quietly not retried.
- **A hold under debug says `STOP HELD`.** Not a formatting nicety: the mutation
  that gave holds an update's header survived nothing, because a test asserts
  the two headers are different strings.

## What is still open

- **Nothing constructs a `Dispatcher` outside the alerting package**, which was
  true of the signal alert before this and is true of both now. Both wait on the
  live mode §25.1 does not describe. Named in the spec, not discovered here.
- **When the notification fires** — at the decision or at the modelled
  acknowledgement [[REQ-WP-033]] introduced — is the caller's, and stays so.
- **The deep link points at a position route nothing serves.** §44A.34's button
  says `[ OPEN POSITION CHART ]`; [[REQ-WP-032]] built the view and no router
  reaches it.
