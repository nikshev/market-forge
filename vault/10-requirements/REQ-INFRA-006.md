---
id: REQ-INFRA-006
title: "SignalNotary: a minimal contract on Monad testnet that notarizes signal hashes"
type: infrastructure
prd_ref: "none -- user-directed integration, 2026-10-03; touches §0.13 (reproducibility), §26.4 (alerting), §29.B (dataset identity)"
prd_lines: "0-0"
phase: null
status: draft
depends_on: []
tags: [monad, notary, onchain]
hard_gated: false
---

## Requirement

**Why this exists.** The product's central promise is "signals are not repainted". While the signal
journal sits in a private database that is only words. A hash of each decision written to a public
chain makes it checkable by anyone, so long as what is hashed is exactly what was shown.

The contract is deliberately minimal for the MVP:

- `commit(bytes32 hash, uint64 barTs)` records that `hash` was committed, with the bar's close time,
  and emits `Committed(hash, barTs, committer)`.
- `resolve(bytes32 hash, uint8 outcome)` records the outcome of a previously committed hash and emits
  `Resolved(hash, outcome)`. Outcomes: `1` target hit, `2` invalidated, `3` expired.
- A hash can be committed once and resolved once; neither can be changed afterwards.
- Only the deployer's configured account may write (the contract is a notary of this system's own
  decisions, not a public registry).

**What this does and does not prove.** The block timestamp proves the hash existed no later than that
block. It does *not* by itself prove the signal preceded a price move: that holds only if the commit
lands before the move, so the claim the product may make is "committed within N seconds of bar
close", with N measured, not "before the move".

## Acceptance

- The contract source, its tests and a deploy script are in the repository.
- Tests (no network) show: a commit emits its event; a second commit of the same hash reverts; a resolve
  of an uncommitted hash reverts; a second resolve reverts; a non-owner write reverts; `outcome`
  outside `1..3` reverts.
- The contract is deployed to **Monad testnet** and its address and deployment transaction are recorded
  in the outcome note and in `.env.example` as a documented variable. This is the evidence for the
  hackathon submission's *Live product* field.
- The address is recorded **only after** a transaction has been read back from the chain; nothing in the
  repository claims a deployment that did not happen.

## Trace

<!-- trace:begin -->
_No linked artifacts yet._
<!-- trace:end -->

## Notes

Human territory. Never machine-rewritten.

- Needs, from the user: the account that deploys (key held outside the repository), testnet funds, and the
  RPC endpoint. None is requested or stored here. Deployment is an outward-facing step and waits for them.
- Deadline given by the user: **2026-10-14**.
