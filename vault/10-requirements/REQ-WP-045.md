---
id: REQ-WP-045
title: The Aerodrome family prices each pool by its own invariant
type: work-package
prd_ref: "§18.10, §18.24, §18.25, §45 Phase 4"
prd_lines: "3038-3088, 3549-3600, 6811"
phase: 4
status: draft
depends_on: [REQ-WP-015]
tags: []
---

## Requirement

PRD §45's Phase 4 lists "Aerodrome Slipstream and v2 adapters" and §18.10 says
why one adapter is not enough:

    Aerodrome currently exposes more than one AMM shape, so one decoder is
    insufficient.

    At minimum model:

        AERODROME_V2_VOLATILE
        AERODROME_V2_STABLE
        SLIPSTREAM_CL
        FUTURE_AERO/METADEX_ADAPTER

and, for v2, states the rule this requirement exists to enforce:

    Depth is calculated from the correct pool invariant, not from CL ticks.

**Three curves, one venue.** A volatile v2 pool is constant product. A stable v2
pool uses the Solidly invariant `x³y + y³x = k`, which is a different curve with
a different depth profile at the same reserves. Slipstream is concentrated
liquidity and reuses the kernel [[REQ-WP-015]] already built.

**Pricing a stable pool with the constant-product formula produces a plausible
number that is wrong**, and nothing downstream shows a symptom — the same shape
of failure as reading OKX's contract sizes as base units ([[REQ-WP-044]]), and
the reason §18.10 states the rule explicitly rather than leaving it to be
inferred.

**The pool says which it is.** Solidly-family pools expose `stable()`; a pool
that does not answer it is constant product. The classification is therefore
read from the chain, not guessed from a name or a token pair — a USDC/USDT pool
can be either.

**The contract is the oracle.** §18.25 requires every adapter's "quote curve
matches contract view within tolerance", and an Aerodrome v2 pool exposes
`getAmountOut(amountIn, tokenIn)` — its own answer to the question this adapter
computes. Verification is against that, not against a fixture somebody wrote.
Base's public RPC answers without a key and two independent endpoints agree on
the head block, so there is nothing between this repository and the authority.

## Acceptance

- A pool's curve is read from the chain (`stable()`), never inferred.
- A quote from the volatile invariant matches the pool's own `getAmountOut`
  within tolerance, at a real pool and a named block.
- A quote from the stable invariant matches the pool's own `getAmountOut` within
  tolerance, at a real pool and a named block.
- The two invariants disagree measurably on the same reserves, asserted — so a
  test cannot pass while silently using one for both.
- Depth for a v2 pool is computed from its invariant and never from ticks.
- A pool whose curve cannot be established is refused, not assumed volatile.
- Slipstream reuses [[REQ-WP-015]]'s concentrated-liquidity primitives rather
  than a second copy of them, and its protocol metadata stays separate (§18.10.2).
- The fixtures are chain reads at pinned blocks, captured by a committed tool,
  and no test opens a socket.

## Trace

<!-- trace:begin -->
_Not yet generated. Run `make graph`._
<!-- trace:end -->

## Notes

Human territory. Never machine-rewritten.

**Where the parts come from, and what is missing.** `nikshev/copy-trade`
(Apache-2.0, same owner) carries a bit-exact Uniswap V3 swap-math port verified
against QuoterV2, constant-product v2 pricing, and the `stable()` probe that
classifies Solidly pools — but **not** the stable-curve quote maths; it detects
those pools rather than pricing them. The invariant therefore comes from
Aerodrome's own published contracts, and the verification from the deployed
pool's own view function.

§18.25's other nine required tests — reorg rollback, checkpoint/replay
equivalence, gap failure, and the rest — are this requirement's too and are the
reason it is larger than a connector.

**FUTURE_AERO/METADEX is out of scope** by §18.10.3's own instruction: a new
deployment gets a new adapter version, and writing one for a contract that does
not exist would bake today's assumptions into the normalized layer.
