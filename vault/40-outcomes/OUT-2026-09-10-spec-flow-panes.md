---
id: OUT-2026-09-10-spec-flow-panes
step: spec
records: [REQ-WP-027]
commit: null
---

## What was done

`specs/065-flow-panes/spec.md`: three user stories, 9 functional requirements,
7 success criteria. [[REQ-WP-027]] moves to `specified`.

## What was decided

- **The acceptance is put where it can be falsified.** A UI feature's usual
  hazard is that its criteria are aesthetic. Here the weight is on the mapping: a
  point with no value for the selected feature is silent, not zero, and drawn as
  zero it becomes a claim about the market.
- **FR-003 and FR-004 are stated as a pair**, because either alone is satisfiable
  by an implementation that gets the other wrong. Dropping missing values is easy
  if you also drop zeros; drawing zeros is easy if you also draw missing ones as
  zero.
- **Three empty-ish states stay apart.** No points, no values for this feature,
  and a failed load. One blank for all three is the default an implementation
  falls into, and the main chart already refuses it — a new pane would have
  quietly undone that.
- **How a gap looks is not specified.** A break in the line and a marked absence
  are both honest; pinning it would dress a preference as a requirement.

## What is still open

- **I cannot see the result.** Every criterion here is checkable by a test, which
  is deliberate, but whether the pane reads well on a screen is not something
  this session can verify. A reviewer looking at it may want the gap drawn the
  other way, and the spec leaves that open on purpose.
- **Pane selection is not persisted**, so a reload forgets it. The deep link
  carries overlays and says nothing about panes; adding it changes a format other
  things parse.
