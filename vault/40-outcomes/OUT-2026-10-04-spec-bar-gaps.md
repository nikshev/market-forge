---
id: OUT-2026-10-04-spec-bar-gaps
step: spec
records: [REQ-WP-086]
commit: null
---

## What was decided

- **Mark, do not stretch.** The lower pane lines up with the chart by index ([[REQ-WP-092]]), and the visible range and the
  channel window are indices; a time-true axis would give a 397-slot hole its width and change all of them. The hole is
  marked where it is and said in words.
- **A gap is found from the bars' own windows** (`next.open > prev.close`), not from the selected timeframe, so it cannot
  disagree with the bars.
- **The requirement's acceptance was amended.** It said the marker states N *and the span*; a series marker carries a few
  characters, so the marker states N and a notice below the chart states N and the span, which also gives a screen reader the facts.
- A bar that exists is never a gap, whatever its volume: absence and quiet must not look alike.

## What is still open

- A time-true axis (a separate decision with its own cost); freshness of the last bar ([[REQ-WP-090]]).
