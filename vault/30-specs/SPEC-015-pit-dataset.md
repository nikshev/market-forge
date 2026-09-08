---
id: SPEC-015-pit-dataset
requirement: REQ-WP-017
speckit_path: specs/015-pit-dataset/spec.md
status: draft
---

## Summary

PRD §24's training join, made honest: features as of `t`, labels about after
`t`, and nothing in a row computed from later than `t`. Chronological folds
with purge and embargo (§24.3), a point-in-time universe (§42), and a leakage
checker that names what it caught.

The labels come from [[REQ-WP-019]]'s confirmed extrema, and it is their
`known_at` that makes a future-aware target legal — PRD §41 rule 3's escape
clause is precisely what §13A.1 built.

[[ADR-024]] sets out which six of §41's eleven anti-bias rules this closes and
why the other five cannot be, rule 2 in particular being enforced for one
engine rather than in general. [[ADR-025]] makes a leakage check over an empty
dataset a failure.

## Links

- Requirements: [[REQ-WP-017]], [[REQ-BIAS-001]], [[REQ-BIAS-003]], [[REQ-BIAS-004]], [[REQ-BIAS-007]], [[REQ-BIAS-008]], [[REQ-BIAS-010]]
- Decisions: [[ADR-024]], [[ADR-025]]
- Consumes: [[REQ-WP-005]], [[REQ-WP-011]], [[REQ-WP-019]]
- Unblocks: [[REQ-WP-018]], and REQ-WP-019's remaining acceptance criteria
