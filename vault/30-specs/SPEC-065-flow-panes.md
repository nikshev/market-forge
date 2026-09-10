---
id: SPEC-065-flow-panes
requirement: REQ-WP-027
speckit_path: specs/065-flow-panes/spec.md
status: draft
---

## Summary

PRD §27.3 asks for selectable lower panes and the chart has none. Phase 2's
features — CVD, OFI, depth imbalance — are registered and already served by
`GET /api/v1/features/timeseries`, which returns a point per instant carrying a
mapping of feature name to value.

**That mapping is where a pane can lie.** A point with no value for the selected
feature is silent, not zero. Drawn as zero it becomes a reading: a flat line
through the middle of a CVD pane says "no net delta", which is a claim about the
market rather than about the data. Everything else in this feature is
presentation; that is the correctness rule, and it is the same distinction three
other requirements here have had to make — the first one that would be drawn on
a screen and believed.

Three states have to stay apart and are easy to collapse: no points at all, no
values for this feature, and a failed load. The application already insists on
this for its main chart ([[REQ-WP-009]]'s FR-016 — a failed load must never be
drawn as though it were data), and a pane that showed one blank for all three
would quietly undo it.

The decision about what to draw is separated from the drawing, because this
application already splits there and records why: `lightweight-charts` needs a
laid-out container, jsdom does not provide one, and a component test can never
see a line. The part that can be wrong is the part that gets tested.

## Links

- Requirement: [[REQ-WP-027]]
- The phase it closes: [[REQ-PHASE-2]]
- The chart it extends: [[REQ-WP-009]]
- The features it draws: [[REQ-WP-011]]
