---
id: SPEC-136-lower-pane-chart
requirement: REQ-WP-092
speckit_path: specs/136-lower-pane-chart/spec.md
status: draft
---

## Summary

The lower pane becomes a second chart of the same library under the main one, on the main chart's own time axis: both
hold the same sequence of bar times (whitespace where a bar has no value), the visible range and the crosshair are
synchronised both ways, the price-scale widths and the containers' insets are equal, and the pane has a title, last
value, axis, a zero line for CVD, one line per run and volume bars coloured by candle direction. Without a handle to the
main chart it falls back to the SVG, so a missing chart is never an empty pane.

## Links

- Requirement: [[REQ-WP-092]]
- Built on: [[REQ-WP-084]], [[REQ-WP-085]], [[REQ-WP-088]], [[REQ-WP-083]]
