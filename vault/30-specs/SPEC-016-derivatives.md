---
id: SPEC-016-derivatives
requirement: REQ-WP-013
speckit_path: specs/016-derivatives/spec.md
status: draft
---

## Summary

PRD §16's funding, open interest, basis and liquidation features, with the
settlement boundary that makes them legal: a funding rate is not knowable
until its interval closes, which is PRD §41 rule 5 and [[REQ-BIAS-005]].

[[ADR-026]] makes every z-score refuse rather than return zero on a degenerate
input — zero is the most meaningful value a z-score can take, and a feature
saying "exactly average" whenever it has nothing to say reads as a calm market
to everything downstream. [[ADR-027]] keeps §16.2's price/OI matrix a label:
the PRD says "stored as feature, not hard-coded trading truth", and a signal
rule branching on it would encode folklore as a threshold.

## Links

- Requirements: [[REQ-WP-013]], [[REQ-BIAS-005]]
- Decisions: [[ADR-026]], [[ADR-027]]
- Consumes: [[REQ-WP-002]], [[REQ-WP-003]], [[REQ-WP-011]]
- Feeds: [[REQ-WP-020]], and [[ADR-016]]'s missing alert block
