---
id: SPEC-006-bar-aggregation
requirement: REQ-WP-005
speckit_path: specs/006-bar-aggregation/spec.md
status: draft
---

## Summary

OHLCV bars on event-time windows with the fourteen fields PRD §12 lists,
finalized by an event-time watermark. A closed bar is never amended — see
[[ADR-005]], which had to define a late-event policy the PRD requires but does
not specify.

## Links

- Requirement: [[REQ-WP-005]]
- Decision: [[ADR-005]]
