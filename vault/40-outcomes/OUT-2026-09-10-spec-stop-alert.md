---
id: OUT-2026-09-10-spec-stop-alert
step: spec
records: [REQ-WP-034]
commit: null
---

## What was done

`specs/072-stop-alert/spec.md`: three user stories, 10 functional requirements,
6 success criteria. [[REQ-WP-034]] moves to `specified`.

## What was decided

- **FR-003 exists only because [[REQ-WP-033]] landed this morning.** Before the
  decided stop and the active stop were separated, "old stop" had one possible
  meaning. It now has two, and one of them announces a move from a level the
  exchange never obeyed — a change that did not happen, in a message whose
  entire purpose is to say what changed. SC-002 is what makes the right meaning
  checkable.
- **The dispatcher becomes kind-agnostic**, and the spec says so rather than
  leaving it to a diff. Two kinds of notification sharing one retry policy and
  one audit means the dispatcher depends on what every notification can do, not
  on one of them. The alternative duplicates the retry and dead-letter behaviour
  PRD §26.4 specifies once, and duplicated retry logic diverges silently.
- **A hold under debug is rendered as a hold.** Putting "STOP UPDATED" above a
  stop that did not move, in the one mode a reader turns on because they do not
  trust what is happening, is the worst place in the system to be imprecise.
- **Open risk of zero after a move past entry is a reading, not an absence** —
  the distinction this codebase keeps returning to, pointed at a number that
  genuinely is zero for once.

## What is still open

- **When the notification fires** — at the decision or at the modelled
  acknowledgement. "STOP UPDATED" is past tense, which argues for the
  acknowledgement; §44A.35's `shadow` mode has no exchange, which argues it is
  the caller's. Left to the caller and named, not decided by silence.
- **Where the deep link points.** §44A.34's button says `[ OPEN POSITION
  CHART ]`; [[REQ-WP-032]] built a position view and nothing routes to it.
- **Nothing constructs a dispatcher outside the alerting package**, so this
  lands beside the signal alert in the same waiting state — on the live mode
  §25.1 does not describe.
