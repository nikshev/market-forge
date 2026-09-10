---
id: OUT-2026-09-10-requirement-derivatives-panes
step: requirement
records: [REQ-WP-030]
commit: null
---

## What was done

[[REQ-WP-030]] extracted from PRD §27.3 and Phase 3's `not_delivered`.
[[REQ-WP-027]] named these four panes as Phase 3's work when it built the first
three, and Phase 3's data is finished.

## What was decided

- **The requirement is the mechanical check, not the four entries.** Adding a
  pane is a line in a list. The failure it invites is a pane naming a feature
  nobody registers, which renders as "no readings of this feature" forever and
  reads as a quiet market rather than a typo. A test comparing the pane list
  against the registry catches that when it is written, and is what makes the
  fifth pane safe to add.
- **The check crosses languages on purpose.** The panes are TypeScript and the
  registry is Python; a check on either side alone would compare a list against
  itself. Reading the pane list from the Python suite is the only place the two
  meet.
- **DEX panes stay out.** Phase 4's data is unfinished, and the reason
  [[REQ-WP-027]] gave for deferring these four applies unchanged to those two.

## What is still open

- **Nothing writes derivative features into the feature table.** The registry
  knows them and the endpoint serves whatever is there; whether a live or replay
  path fills them is a separate gap, and it is not this requirement's — but a
  pane over an empty table shows "no feature points in this window", which is
  honest and will look like a bug to whoever opens it first.
