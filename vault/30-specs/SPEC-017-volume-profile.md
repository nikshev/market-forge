---
id: SPEC-017-volume-profile
requirement: REQ-WP-012
speckit_path: specs/017-volume-profile/spec.md
status: draft
---

## Summary

PRD §14.1's profile: volume binned from the trade stream — never inferred from
candle direction, which the PRD forbids outright — with the point of control,
the value area, the high- and low-volume nodes, the shape features, and a chart
plugin.

[[ADR-028]] settles how the value area grows, which §14.1 leaves open: expand
from the POC taking the larger neighbour, so the area is contiguous and
contains the POC. Both are properties a reader assumes from the name and
neither is implied by the 70% target.

## Links

- Requirement: [[REQ-WP-012]]
- Decision: [[ADR-028]]
- Consumes: [[REQ-WP-002]], [[REQ-WP-003]], [[REQ-WP-006]], [[REQ-WP-011]]
- Renders in: [[REQ-WP-009]]
