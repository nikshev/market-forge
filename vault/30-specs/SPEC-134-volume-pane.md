---
id: SPEC-134-volume-pane
requirement: REQ-WP-085
speckit_path: specs/134-volume-pane/spec.md
status: draft
---

## Summary

PRD §27.3's first lower pane, volume, is added as a bar-sourced pane listed first in the row: one vertical bar
per final bar, equal to its `volume_base`, with a zero drawn as zero and a non-final bar left out. It is live
whenever final bars are loaded, independent of the feature series, and the page opens on it. `PANES` stays a
list of registered features, and the comment that claimed all nine of §27.3 were present is corrected.

## Links

- Requirement: [[REQ-WP-085]]
- Built on: [[REQ-WP-084]], [[REQ-WP-027]], [[REQ-WP-083]]
