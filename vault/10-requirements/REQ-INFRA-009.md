---
id: REQ-INFRA-009
title: "A signal's outcome is written on-chain when its horizon passes"
type: infrastructure
prd_ref: "none -- user-directed integration, 2026-10-03; touches §0.13 (reproducibility), §26.4 (alerting), §29.B (dataset identity)"
prd_lines: "0-0"
phase: null
status: draft
depends_on: [REQ-INFRA-007]
tags: [monad, outcomes]
hard_gated: false
---

## Requirement

When a signal's horizon elapses, its outcome — target hit, invalidated or expired — is written with
`resolve` next to the original commit, so the history of outcomes is public and cannot be edited later.

The outcome is derived from final bars only and by the same code in live and in replay (Principle VII);
it is never derived from a bar still in progress. A signal that resolves is resolved once.

## Acceptance

- For a fixture of final bars, each of the three outcomes is produced and resolved on a fake chain
  client exactly once.
- Re-running the resolution over the same bars commits nothing new.
- An outcome is never written from an unfinalized bar (a test that would fail on one).
- On testnet, a committed signal reaches `Resolved` and the transaction is recorded.

## Trace

<!-- trace:begin -->
_No linked artifacts yet._
<!-- trace:end -->

## Notes

Human territory. Never machine-rewritten.
