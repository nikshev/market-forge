---
id: SPEC-140-cross-venue-consensus
requirement: REQ-WP-091
speckit_path: specs/140-cross-venue-consensus/spec.md
status: draft
---

## Summary

The chart shows a cross-venue consensus mid line (optional layer, off by default) computed as the median of fresh mids from ≥2 venues per market type at each bar's close, and a lower pane `venue_basis_bps` showing the viewed venue's basis to its type's consensus. The `crossvenue` library's `consensus_mid` is reused (no look-ahead). Book subscription (top-of-book quotes) is separate and must land first. Mixed instrument types are handled by consensus per market type (spot/perp).

## Links

- Requirement: [[REQ-WP-091]]
- Built on: [[REQ-WP-016]], [[REQ-WP-011]], [[REQ-WP-060]], [[REQ-WP-083]]