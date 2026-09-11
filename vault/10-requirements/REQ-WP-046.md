---
id: REQ-WP-046
title: The Curve family quotes from its own invariant, at a point-in-time state
type: work-package
prd_ref: "§18.9, §18.25, §18.27, §45 Phase 4"
prd_lines: "2962-3040, 3596-3600, 3651, 6790"
phase: 4
status: draft
depends_on: [REQ-WP-014]
tags: []
---

## Requirement

PRD §18.27 puts "Curve Stableswap-NG/Cryptoswap quote adapter" seventh in the
DeFi ingestion order, immediately after the Aerodrome invariant adapter, and
§18.9 opens by ruling out the shortcut:

    Curve must be modeled as an invariant/quote-based AMM family rather than as
    a tick-based AMM.

    At minimum distinguish:

        STABLESWAP
        STABLESWAP_NG
        CRYPTOSWAP
        CRYPTOSWAP_NG
        META_POOL
        OTHER/UNKNOWN

and §18.9.1 says it again about depth:

    Do **not** derive a fake tick map.

    Build the depth curve by quote simulation for a configured notional grid
    ... Use protocol quote math or verified view functions at a point-in-time
    state.

    For Stableswap-NG, dynamic fees and token rate types are part of state and
    must be included in quoting.

**Six shapes, one venue, and the venue does not announce which.** Stableswap
solves `A·n^n·Σx + D = A·D·n^n + D^(n+1)/(n^n·Πx)` by Newton; Cryptoswap adds a
`gamma` and a `price_scale` the pool rebalances around. Two families, several
generations, and a metapool that is a pool whose second coin is another pool's
LP token — so a quote through it is two quotes.

**The families do not even share a function signature.** Stableswap answers
`get_dy(int128,int128,uint256)`; Cryptoswap answers
`get_dy(uint256,uint256,uint256)`. A caller that assumes one gets a revert from
the other, which is the kind of failure that is loud — but a caller that
assumes the *invariant* gets a plausible number and no symptom, which is the
failure this requirement exists to prevent, and the fourth of its shape in this
phase after [[REQ-WP-044]]'s contract sizes and [[REQ-WP-045]]'s stable curve.

**The fee is not one number.** Curve's denominator is 1e10, not the 1e6 every
other venue in this project uses, and Stableswap-NG's effective fee moves with
how far off peg the pool sits — so a fee read once and cached is wrong in
exactly the states that matter most.

**The contract is the oracle.** §18.25 asks for the quote curve to match
"contract view within tolerance", and every Curve pool exposes `get_dy` — its
own answer to what this adapter computes. Ethereum's public RPC answers without
a key, and three independent endpoints are reachable, so verification is against
the deployed pool rather than against a fixture somebody wrote.

**Why the maths must be local anyway.** §18.9.1 permits a verified view
function, and calling one is right for a live quote. It is not available to a
replay: a depth curve reconstructed from stored state at a past event time
cannot call a contract at that state without an archive node, and Principle I
forbids reaching for the present instead. The view function is therefore the
authority this adapter is checked against, not the way it answers.

## Acceptance

- A pool's family is established from the chain — its implementation and the
  signatures it answers — and never from its name or its coins.
- A pool of an unrecognised shape is classified `OTHER/UNKNOWN` and refused for
  quoting, not priced as the nearest familiar family.
- A Stableswap-NG quote matches the pool's own `get_dy` at a real pool and a
  named block, including its dynamic off-peg fee and its stored coin rates.
- A Cryptoswap quote matches the pool's own `get_dy` at a real pool and a named
  block, including `price_scale`.
- Coin indices are handled by index, not by token address ordering, and a
  three-coin pool is exercised — so a two-coin assumption cannot pass.
- The dynamic fee is shown to differ from the base fee on a real pool, asserted,
  so a test cannot pass while silently using the base fee for both.
- Depth is built by quote simulation over a notional grid and by inverse solve
  for a bps grid, never from a derived tick map.
- The fixtures are chain reads at pinned blocks, captured by a committed tool,
  and no test opens a socket.

## Notes

Human territory. Never machine-rewritten.

**What `nikshev/copy-trade` gives, and what it deliberately does not.** It has a
Curve adapter, and its own docstring explains that it declines to port the
maths: *"Rather than reimplement the fragile per-type math (A scaling,
rate/precision, variants), we call each pool's OWN `get_dy` via eth_call."*
That is the right call for an arbitrage bot quoting live state, and it is
unavailable here for the reason stated above — a replay has no chain to call.

What it does contribute is the classification work and two facts learned the
hard way: the two `get_dy` signature families, and that a non-standard pool's
`fee()` can return a garbage word rather than reverting. Both carry over.

**Two halves, as [[REQ-WP-045]] had.** Stableswap-NG first — it carries the
dynamic fee and the stored rates, which is where the substance is. Cryptoswap
second: a larger invariant, but a self-contained one.

**Metapools are classified here and quoted later.** §18.9 asks for `META_POOL`
as a distinguishable shape, and it is one; quoting through a metapool is two
quotes composed, which is worth building on top of a base-pool quote that is
already verified rather than alongside it.
