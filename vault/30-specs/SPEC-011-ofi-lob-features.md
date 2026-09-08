---
id: SPEC-011-ofi-lob-features
requirement: REQ-WP-011
speckit_path: specs/011-ofi-lob-features/spec.md
status: draft
---

## Summary

PRD §15's order-flow features over REQ-WP-004's book and REQ-WP-002's trades:
queue and depth imbalance, microprice, Cont-style OFI over event-time windows,
cumulative volume delta, and the wall lifecycle of §15.6.

It also brings PRD §19's feature registry, because this is the first work
package that produces a feature at all ([[ADR-015]]) — which is what finally
gives [[REQ-PRIN-008]] something to attach to. [[ADR-013]] leaves CVD-price
divergence unbuilt: §15.4 names it without defining it, and four defensible
readings give four different numbers under one name. [[ADR-014]] states the
rule that splits a wall's shrinkage into executed and cancelled.

## Links

- Requirements: [[REQ-WP-011]], [[REQ-PRIN-008]]
- Decisions: [[ADR-013]], [[ADR-014]], [[ADR-015]]
- Consumes: [[REQ-WP-004]], [[REQ-WP-005]], [[REQ-WP-002]]
