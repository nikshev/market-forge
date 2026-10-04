---
id: SPEC-137-bar-gaps
requirement: REQ-WP-086
speckit_path: specs/137-bar-gaps/spec.md
status: draft
---

## Summary

A missing bar is found from two consecutive bars' own windows and marked on the chart with one amber marker at the first bar
after the hole stating how many bars are missing, and said in words in a notice under the chart with the UTC span. The axis
is not changed: the lower pane lines up with it by index, so the hole is marked, not stretched. The Volume pane and a CVD run
that starts at a gap carry the same marker.

## Links

- Requirement: [[REQ-WP-086]]
- Built on: [[REQ-WP-092]], [[REQ-WP-083]]
