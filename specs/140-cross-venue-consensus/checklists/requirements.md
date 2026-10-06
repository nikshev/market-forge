# Specification Quality Checklist: Cross-venue consensus mid and venue basis

**Created**: 2026-10-06
**Feature**: [spec.md](../spec.md)

- [x] Facts read from the code (crossvenue library, no mids in ingest, book subscription separate, basis_bps collision)
- [x] Requirements testable (SC-001 median/exclusions, SC-002 no look-ahead, SC-003 API, SC-004 chart, SC-005 pane)
- [x] Scope bounded (no DeFi in consensus, no consolidated bars, no book sub)
- [x] Edge cases identified (one venue, stale/future quotes, mixed types, gaps)
- [x] No [NEEDS CLARIFICATION] markers

## Notes

Key design decision: consensus per market type (spot/perp) to avoid blending spot-perp basis into consensus. This is explicit in FR-006 and SC-005 with a test. The book subscription is explicitly out of scope and ordered before this.