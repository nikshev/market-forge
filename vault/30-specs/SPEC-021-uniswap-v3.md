---
id: SPEC-021-uniswap-v3
requirement: REQ-WP-015
speckit_path: specs/021-uniswap-v3/spec.md
status: draft
---

## Summary

PRD §18.7's concentrated-liquidity adapter: the price math, event decoding,
state reconstruction from an ordered log stream, and §18.7.1's executable depth
curve.

[[ADR-035]] enforces §18.7's own ordering rule — block, transaction index, log
index, never the timestamp every log in a block shares — and refuses a repeated
triple, because that is the same log ingested twice and deduplicating it
silently would double a mint.

[[ADR-036]] keeps an unreachable depth query a refusal. "It costs this much to
move 50 bps" and "it cost this much to exhaust what we know about" are
different facts, and a bare number cannot tell them apart.

## Links

- Requirement: [[REQ-WP-015]]
- Decisions: [[ADR-035]], [[ADR-036]]
- Consumes: [[REQ-WP-014]]
