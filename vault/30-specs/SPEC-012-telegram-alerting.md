---
id: SPEC-012-telegram-alerting
requirement: REQ-WP-008
speckit_path: specs/012-telegram-alerting/spec.md
status: draft
---

## Summary

PRD §26: a confirmed candidate becomes a formatted message with a chart deep
link, deduped against what has already been said, delivered with retry and
dead-lettering, and audited attempt by attempt — without ever blocking the
signal engine.

[[ADR-016]] settles what the message can honestly contain: score, model
probability, derivatives and DeFi have no source yet, so those sections are
absent rather than placeheld, and §26.3's severity tiers go with the score.
[[ADR-017]] derives the signal id from the candidate so a replay produces the
same alert. [[ADR-018]] keeps the transport, the sleeping and the clock outside
the package, which is what turns "never block the signal engine" into a
property rather than a promise.

This is the first half of [[ADR-010]]'s gap: `ALERTED` finally has something
that performs it.

## Links

- Requirement: [[REQ-WP-008]]
- Decisions: [[ADR-016]], [[ADR-017]], [[ADR-018]]
- Consumes: [[REQ-WP-006]], [[REQ-WP-007]], [[REQ-WP-011]]
- Blocked on for its link target: [[REQ-WP-009]]
