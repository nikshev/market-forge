---
id: SPEC-023-cross-venue
requirement: REQ-WP-016
speckit_path: specs/023-cross-venue/spec.md
status: draft
---

## Summary

PRD §17's cross-venue engine: one agreed price across venues, each venue's
distance from it, where the liquidity actually is, and which venue moves first —
the last of these marked research-only and kept off the signal path.

Two of §17's four subsections state a prohibition rather than a computation, and
both become structural facts rather than notes. §18.14 forbids applying §17.3's
mid-based basis to an AMM, so `basis_bps` refuses for a pool and
`executable_basis_bps` at a caller-supplied notional answers instead — with no
default notional, because at zero size every venue costs the same. §17.2 forbids
converting a lagged correlation into a trading rule without out-of-sample
validation; intent is not checkable, so [[ADR-040]] keeps `leadlag` out of the
package's exports and a test walks the signal, alerting and stop packages
asserting none imports it.

[[ADR-039]] has executable prices supplied rather than computed. Fees, gas and
MEV margins are venue-specific operational inputs; an engine that assumed them
would hide those assumptions at every call site.

Comparability comes from [[REQ-ASSET-001]]'s registry — two quotes are
comparable when their representations resolve to one canonical asset, never when
their tickers match.

## Links

- Requirement: [[REQ-WP-016]]
- Decisions: [[ADR-039]], [[ADR-040]]
- Builds on: [[REQ-ASSET-001]], [[REQ-WP-004]], [[REQ-WP-015]]
