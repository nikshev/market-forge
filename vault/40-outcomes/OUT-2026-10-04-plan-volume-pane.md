---
id: OUT-2026-10-04-plan-volume-pane
step: plan
records: [REQ-WP-085]
commit: null
---

## What was decided

- **`BAR_PANES` beside `PANES`, joined as `ROW`.** Rejected: a `source` flag on `PANES` entries (breaks or
  complicates the registry check), and a special case for `"volume"` inside `FlowPane` (a second place that
  knows the name).
- **`volumeSeries(bars)` returns the same `PaneSeries`** the feature panes use, so empty/ok messages and
  availability go through one path; a non-finite `volume_base` is skipped, not drawn as zero.
- **Vertical bars, not a line**: a volume is an amount per bar, and a line through volumes reads as a trend.
- **Time is the bar's `open_time_ns`**, the instant it starts, stated as such.
- **`barsLoaded`** is its own fact (see the tasks note for how it was found).

## What was rejected

- Putting volume in the features table (needs a writer that does not exist and duplicates a number the bar has).
- Waiting for the feature series before offering Volume.

## What is still open

- REQ-WP-084's own pane-counting tests (`flowPaneAvailability`, `chartPanesLoading`) assume nine panes and a
  feature pane first; the edits are listed in the implement note.
