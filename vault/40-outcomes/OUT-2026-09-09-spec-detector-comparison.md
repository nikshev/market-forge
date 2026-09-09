---
id: OUT-2026-09-09-spec-detector-comparison
step: spec
records: [REQ-EXP-003]
commit: null
---

## What was done

`specs/036-detector-comparison/spec.md`: three user stories, 12 functional
requirements, 11 success criteria, over criteria derived the same day.

## What was decided

- **The metric set is a judgement**, and the derivation says so: count, lag,
  later-invalidation share and expectancy are the four ways a detector can be
  wrong.
- **The order-flow detector is named, not approximated.**
- **The detectors live at the plugin point**, not in the experiment.

## What is still open

- **Order-flow confirmation needs a protocol change** to [[REQ-WP-007]]'s
  `RejectionDetector`, and features from [[REQ-WP-011]] reachable from it.
