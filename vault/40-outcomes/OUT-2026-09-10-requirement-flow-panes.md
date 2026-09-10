---
id: OUT-2026-09-10-requirement-flow-panes
step: requirement
records: [REQ-WP-027]
commit: null
---

## What was done

[[REQ-WP-027]] extracted from PRD §27.3 and §45's Phase 2. It is the only entry
in [[REQ-PHASE-2]]'s `not_delivered`.

## What was decided

- **The PRD answered the design question I had deferred.** §27.3 names the nine
  panes outright, so "which features, and in what form" was never mine to ask —
  it was written down. Checking the PRD before asking a second time is the
  lesson, and it is recorded here because the first instinct was to ask.
- **Scope is the three panes Phase 2 has data for**: CVD, OFI and depth
  imbalance. The derivatives panes belong to Phase 3's own deliverable and the
  DEX panes to Phase 4; building them here would ship panes for data those
  phases have not finished.
- **A missing value leaves a gap, never a zero.** A feature is a key in a mapping
  per instant, and a mapping without that key is silent rather than zero. This is
  the same distinction three other requirements here have had to make, and it is
  the first place it would be drawn on a screen and believed.
- **The decision about what to draw is separated from the drawing**, following
  what this application already does and the reason it records: jsdom cannot lay
  out a chart container, so a component test can never see a line. The part that
  can be wrong is the part that gets tested.

## What is still open

- **How a gap should look is not settled by the requirement.** A break in the
  line and a marked absence are both honest; which reads better is a judgement
  the plan makes and a reviewer can overturn.
- **The pane selection is not persisted.** The deep link carries overlays
  ([[REQ-WP-009]]) and says nothing about panes, so a reload forgets. Adding it
  to the link is a change to a format other things parse, and it is not in scope.
