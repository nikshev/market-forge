---
id: SPEC-036-detector-comparison
requirement: REQ-EXP-003
speckit_path: specs/036-detector-comparison/spec.md
status: draft
---

## Summary

EXP-003's four rejection detectors, each run inside the production signal
machine. `WickOnly` and `TwoBarConfirmation` join `CloseBackInside` at
[[REQ-WP-007]]'s plugin point — PRD §21.3 asks for them as plugins, and a
detector only an experiment can reach is not one.

The fourth is named and not scored: order-flow confirmation needs inputs the
detector interface does not carry, and a detector scored on inputs it never saw
would be compared against three that had them.

Four metrics, because there are four ways a detector can be wrong: too few
confirmations, too slow, too eager, or unprofitable. The third — confirmations
the market later takes back — is the one no bar series has been found to
produce, so the measurement is separated from the run and tested on constructed
candidate lives rather than assumed from a green sweep.

## Links

- Requirement: [[REQ-EXP-003]]
- Criteria derived: `docs/superpowers/specs/2026-09-09-experiment-acceptance-design.md`
- Builds on: [[REQ-WP-007]], [[REQ-BT-001]], [[REQ-EXP-001]]
