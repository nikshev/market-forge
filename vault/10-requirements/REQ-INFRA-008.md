---
id: REQ-INFRA-008
title: "A Telegram alert links to the transaction that notarized it"
type: infrastructure
prd_ref: "none -- user-directed integration, 2026-10-03; touches §0.13 (reproducibility), §26.4 (alerting), §29.B (dataset identity)"
prd_lines: "0-0"
phase: null
status: draft
depends_on: [REQ-INFRA-007]
tags: [monad, alerting]
hard_gated: false
---

## Requirement

An alert that is sent includes a link to the commit transaction of the snapshot it announces, so a
reader can verify the signal existed in exactly this form at that block.

A link to a transaction that has not been submitted is worse than no link. The alert is not delayed
indefinitely for it ([[REQ-WP-008]]: never block the engine on delivery); if the transaction is not yet
submitted when the alert goes, the alert says so and carries the hash, and the link is added when the
transaction exists.

## Acceptance

- An alert for a notarized snapshot contains the explorer URL of its commit transaction (a test with a
  fake chain client).
- An alert whose commit is not yet submitted goes out without a link and says it is pending; it is never
  held back for the chain.
- The explorer base URL is configuration (Principle X), not a literal.

## Trace

<!-- trace:begin -->
_No linked artifacts yet._
<!-- trace:end -->

## Notes

Human territory. Never machine-rewritten.
