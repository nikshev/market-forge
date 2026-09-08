---
id: SPEC-020-evm-connector
requirement: REQ-WP-014
speckit_path: specs/020-evm-connector/spec.md
status: draft
---

## Summary

PRD §18's EVM ingestion: §18.3's raw envelope, §18.4's finality ladder and
reorg model, §18.6's versioned decoder registry, and §18.17's provider pool.
No network — the provider is a protocol the caller supplies, the same boundary
[[ADR-012]] drew for the order book's transport.

[[ADR-033]] settles the reorg: a record is orphaned, never edited or deleted,
and a read as of an instant before the reorg still returns it. That is
[[REQ-BIAS-006]] — using later corrected state as if known earlier is what
makes a replayed backtest disagree with the live system in a direction that
looks like improvement.

[[ADR-034]] separates the two failures PRD §18.6 rules out at once: a decoder
guessing at an upgraded contract, and ingestion dropping the only evidence of
what happened.

## Links

- Requirements: [[REQ-WP-014]], [[REQ-BIAS-006]]
- Decisions: [[ADR-033]], [[ADR-034]]
- Feeds: [[REQ-WP-015]]
