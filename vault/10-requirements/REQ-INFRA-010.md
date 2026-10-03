---
id: REQ-INFRA-010
title: "Monad DEX pools join the DEX↔CEX basis confirmation group"
type: infrastructure
prd_ref: "none -- user-directed integration, 2026-10-03; touches §0.13 (reproducibility), §26.4 (alerting), §29.B (dataset identity)"
prd_lines: "0-0"
phase: null
status: draft
depends_on: []
tags: [monad, dex, optional]
hard_gated: false
---

## Requirement

Pools on Monad are added to the group that confirms DEX↔CEX basis. **The least mandatory part of the
Monad work**: if it cannot be done in time it is dropped, and nothing else depends on it.

Whatever is added follows the existing DEX connector contract (Principle VIII, one common interface) and
the existing quoting and freshness rules; a Monad pool that is stale is stale, not silently used.

## Acceptance

- A Monad pool is ingested through the common DEX interface and appears in the basis group.
- A stale pool is excluded from confirmation and reported as stale.
- Not delivered by 2026-10-14 is an acceptable outcome, recorded as such in this note.

## Trace

<!-- trace:begin -->
_No linked artifacts yet._
<!-- trace:end -->

## Notes

Human territory. Never machine-rewritten.
