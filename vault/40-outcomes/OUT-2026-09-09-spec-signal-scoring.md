---
id: OUT-2026-09-09-spec-signal-scoring
step: spec
records: [REQ-SCORE-001]
commit: null
---

## What was done

`specs/025-signal-scoring/spec.md`: five user stories, 15 functional
requirements, 11 success criteria.

## What was decided

- **The requirement was extracted first.** [[REQ-US-001]] and [[REQ-US-004]]
  both needed a score, and no requirement covered PRD §22 or §43. Closing the
  user stories against an uncovered PRD section would have left the score itself
  outside the graph — the same reason [[REQ-ASSET-001]] was extracted before
  [[REQ-WP-016]].
- **A missing family leaves the denominator** ([[ADR-044]]).
- **Group contributions are supplied**, not computed here. Each family's
  arithmetic lives in its own package already.
- **§26.3's severity tiers are out of scope.** They read a score; this produces
  one.

## What is still open

- **Nothing consumes the score yet.** [[REQ-US-001]] and [[REQ-US-004]] are the
  next two.
