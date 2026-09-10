---
id: SPEC-069-long-short
requirement: REQ-WP-031
speckit_path: specs/069-long-short/spec.md
status: draft
---

## Summary

PRD §16 asks for "long/short squeeze context where available", and both halves
of that phrase are the specification.

**Where available.** A venue that publishes no positioning is not a balanced
market. A ratio of 1.0 says longs and shorts are even — a reading; an absent
ratio says nobody knows. Collapsing them puts a confident "balanced" in front of
every instrument on every venue that does not publish, and nothing downstream
ever sees a gap. This is the failure mode of every sometimes-absent field, and
the fifth time this repository has had to draw the distinction explicitly.

**Squeeze context.** A ratio alone is not context: 2.0 is ordinary on one
instrument and extreme on another. Crowding is measured against the instrument's
own recent positioning, through the same z-score funding and open interest use —
which refuses rather than returning zero, because [[ADR-026]] settled that a
feature saying "exactly average" whenever it has nothing to say reads as a calm
market to everything downstream.

"Optional" in the PRD describes the venue, not the rigour.

## Links

- Requirement: [[REQ-WP-031]]
- The package it joins: [[REQ-WP-013]]
- The staleness rule it inherits: [[REQ-WP-026]]
- Why the z-score refuses: [[ADR-026]]
