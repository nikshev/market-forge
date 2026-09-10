---
id: OUT-2026-09-10-requirement-stop-path
step: requirement
records: [REQ-WP-032]
commit: null
---

## What was done

`vault/10-requirements/REQ-WP-032.md`, extracted from PRD §44A.33 and §45's
Phase 7A. [[REQ-PHASE-7A]]'s first open deliverable.

## What was decided

- **The requirement is the last line of §44A.33, not the list above it.** The
  list of fifteen fields is satisfiable by drawing them; the line under it —
  "must show the stop path exactly as generated live/replay, not recompute a
  prettier historical trail" — forbids the thing a chart naturally does.
  Recomputing is easier than storing, looks better, and uses anchors confirmed
  after the instant they are drawn at. It is Principle I in visual form.
- **Rejected proposals are elevated to an acceptance criterion.** [[ADR-032]]
  spent its argument on keeping six kinds of hold distinguishable in the model;
  a view drawing only movements collapses them again at the last step. A stop
  that held on a cooldown and one that held because no anchor was knowable are
  the same flat line, and the difference is what a reader inspecting a decision
  came for.
- **`AS_SEEN_THEN` is reused, not redefined.** [[REQ-WP-028]] already filters
  extremum markers on knowledge. Two implementations of "as seen then" would
  drift, and the drift would be invisible, because both would draw lines.
- **An absent hard stop is absent.** Written into acceptance rather than left
  implied, for the reason [[REQ-WP-031]] just spent a requirement on: the
  natural default (equal to the initial stop) is a plausible value that no
  reader would question.

## What is still open

- **Clicking a stop update** (§44A.33's "Why moved / Why not tighter" panel) is
  in the requirement's quoted text and will need its own decision at spec time:
  the reason codes exist, the grouping into "moved" and "not tighter" does not.
- **Trail aggressiveness and data-health status** are listed fields with no
  producer yet. Whether they are this requirement's or the engine's is a spec
  question.
