---
id: SPEC-133-chart-candidates-no-data
requirement: REQ-WP-084
speckit_path: specs/133-chart-candidates-no-data/spec.md
status: draft
---

## Summary

Candidate extrema are off by default behind a "Candidate extrema" switch that is a view option of the page and
not a deep-link layer (the link's vocabulary is §27.2's). A lower pane whose feature the loaded series does not
carry reads "no data" and cannot be pressed, decided by the existing `paneSeries` from points the page already
loads; a failure or an in-flight load never reads as "no data". The page opens on the first pane that has data.

## Links

- Requirement: [[REQ-WP-084]]
- Built on: [[REQ-WP-083]], [[REQ-WP-027]], [[REQ-WP-009]], [[REQ-US-002]]
