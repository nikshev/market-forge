---
id: OUT-2026-09-10-requirement-stop-alert
step: requirement
records: [REQ-WP-034]
commit: null
---

## What was done

`vault/10-requirements/REQ-WP-034.md`, extracted from PRD §44A.34 and §45's
Phase 7A. [[REQ-PHASE-7A]]'s last open deliverable.

## What was decided

- **The message is a transition, not a state.** Old stop against new, open risk
  against the risk it replaced. A notification reporting only where the stop now
  sits tells a reader what the chart already shows and withholds the one thing
  it does not: how much risk just came off. A rendering that lost the "from"
  half would still look complete, which is why it is written into acceptance.
- **The old stop is the stop that was in force.** [[REQ-WP-033]] separated
  decided from active a few hours ago; a notification announcing a move from a
  level the exchange never obeyed describes a change that did not happen.
- **"Do not notify for rejected micro-updates" is read strictly.** The phrase
  admits two readings — rejections that were micro, or rejections and
  micro-updates — and the requirement takes the stricter one: announce a move,
  and everything else is debug. Stated in the note so a future reader can
  disagree with it rather than discover it.
- **Debug mode announces a hold as a hold.** Rendering a hold in the shape of an
  update would put "STOP UPDATED" above a stop that did not move, in the one
  mode a reader turns on precisely because they do not trust what is happening.

## What is still open

- **When the notification fires** — at the decision or at the modelled
  acknowledgement. §44A.27's semantics argue for the acknowledgement, since
  "STOP UPDATED" is past tense, and §44A.35's `shadow` mode has no exchange to
  acknowledge anything. A spec question.
- **Nothing constructs a `Dispatcher` outside the alerting package**, so this
  will land in the same state the signal alert is already in: a mechanism with
  no caller, waiting on the live mode §25.1 does not describe yet. Pre-existing,
  and worth naming rather than inheriting quietly.
