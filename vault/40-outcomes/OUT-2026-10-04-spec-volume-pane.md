---
id: OUT-2026-10-04-spec-volume-pane
step: spec
records: [REQ-WP-085]
commit: null
---

## What was decided

- **Volume is a bar-sourced pane, not an entry of `PANES`.** `test_pane_features.py` parses `PANES` and checks
  every entry against the feature registry, for a reason (a pane naming a feature nobody records reads "no
  readings" forever). Volume is a property of the bar, not a feature, so it lives in its own list and is
  rendered first.
- **Final bars only; zero is data.** A forming bar's volume will change, which the chart already respects for
  candles; a final bar in which nothing traded has volume `0`, which is a fact about the market and must be drawn.
- **Volume's availability is its own.** It must not wait for, or be hidden by, the feature series: a failed
  feature request is the commonest way for the one pane with data to disappear.
- **`depth_imbalance_10` stays.** §27.3 does not list it, but removing a pane by side effect of adding another
  is not this change's call.

## What is still open

- Whether `depth_imbalance_10` should remain (owner's call).
- A quote-currency volume is not on the bar and is not invented.
- Gaps between bars are drawn at their own times with no claim they were adjacent; marking them is
  [[REQ-WP-086]].
