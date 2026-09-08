---
id: SPEC-010-order-book-service
requirement: REQ-WP-004
speckit_path: specs/010-order-book-service/spec.md
status: draft
---

## Summary

PRD §11.1's reconstruction, made into a service: buffer deltas until a snapshot
gives them a starting point, validate every sequence exactly, refuse every read
once a gap has been seen, and rebuild from a fresh snapshot on request. Top-N
levels and depth-at-bps are the reads WP-011's features will consume.

[[ADR-011]] settles what "bps" is measured from — the mid price, because §15.1's
depth imbalance is a ratio and two sides measured from different references are
not comparable. [[ADR-012]] keeps the service venue-agnostic, free of I/O and
free of a clock: staleness is arithmetic over event times, so a recorded stream
replays to the same health twice.

## Links

- Requirement: [[REQ-WP-004]]
- Decisions: [[ADR-011]], [[ADR-012]]
- Consumes: [[REQ-WP-002]], [[REQ-WP-003]]
- Feeds: [[REQ-WP-011]]
