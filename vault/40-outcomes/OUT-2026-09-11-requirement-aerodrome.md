---
id: OUT-2026-09-11-requirement-aerodrome
step: requirement
records: [REQ-WP-045]
commit: null
---

## What was done

`vault/10-requirements/REQ-WP-045.md`, from PRD §18.10 and §45's Phase 4, after
surveying `nikshev/copy-trade` and establishing that the chain itself is
reachable.

## What the survey settled

**What the source repository gives**, under Apache-2.0 and the same owner: a
bit-exact Uniswap V3 swap-math port verified against QuoterV2, constant-product
v2 pricing, and the `stable()` selector probe that classifies Solidly-family
pools.

**What it does not give**: the stable-curve quote maths. It detects stable pools
in order to treat them separately, not to price them. So the one curve this
project does not already have is also the one the source does not have, and it
comes from Aerodrome's published contracts instead.

That is worth stating plainly rather than discovering during implementation: the
repository shortens the work substantially and does not eliminate the part that
needed care.

## What makes this verifiable

Base's public RPC answers without a key, and two independent endpoints agree on
the head block. The Aerodrome v2 factory is live at the address BaseScan labels,
holding 29,242 pools.

An Aerodrome v2 pool exposes `getAmountOut(amountIn, tokenIn)` — the contract's
own answer to precisely the question this adapter computes. §18.25 asks for the
quote curve to match "contract view within tolerance", and that view is
callable. **This is stronger than the exchange connectors' recorded fixtures**:
there the recording was evidence, here the chain is the authority.

## The failure this requirement is about

Pricing a stable pool with the constant-product formula gives a plausible number
that is wrong, and nothing downstream shows a symptom. It is the same shape as
reading OKX's contract sizes as base units, met for the third time this session
— which is why the acceptance asks for the two invariants to be asserted as
*disagreeing* on the same reserves, so no test can pass while quietly using one
for both.

## What is still open

- **The nine other tests §18.25 requires per adapter** — reorg rollback,
  checkpoint/replay equivalence, gap failure and the rest. They are why this is
  larger than a connector.
- **FUTURE_AERO/METADEX**, excluded by §18.10.3's own instruction.
