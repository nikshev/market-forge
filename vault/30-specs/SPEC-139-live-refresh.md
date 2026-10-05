---
id: SPEC-139-live-refresh
requirement: REQ-WP-090
speckit_path: specs/139-live-refresh/spec.md
status: draft
---

## Summary

On a live chart the page re-runs the same series load it ran on open (bars, channel, feature series, extrema, plus the
profile and DEX depth where they apply) on a configured interval (`VITE_CHART_REFRESH_MS`, default 60 s) and draws the
answers without a reload. A pinned chart never refreshes; a hidden tab issues nothing and refreshes once on becoming
visible; a tick never starts while the previous load is in flight; a failed refresh keeps the old picture, states the
failure, and recovers on the next tick. Timeframe, mode, pane, candidate switch and visible range are the reader's and are
preserved — only the initial load (or a timeframe/mode change) sets the range. Stage 2 (push) is explicitly out.

## Links

- Requirement: [[REQ-WP-090]]
- Built on: [[REQ-WP-009]], [[REQ-WP-083]], [[REQ-WP-092]], [[REQ-WP-089]]