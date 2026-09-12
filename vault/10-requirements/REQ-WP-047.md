---
id: REQ-WP-047
title: Uniswap v4 routes by pool id and knows what its hook makes unsafe
type: work-package
prd_ref: "§18.8, §18.25, §18.27, §45 Phase 4"
prd_lines: "2904-2961, 3592-3594, 3652-3653, 6791-6792"
phase: 4
status: implemented
depends_on: [REQ-WP-015]
tags: []
---

## Requirement

PRD §18.8 opens with a prohibition rather than a description:

    Uniswap v4 must **not** be implemented as "v3 with a different factory". v4
    uses a singleton `PoolManager`, where pools are identified by `PoolId` and
    pool configuration includes currencies, fee, tick spacing and an optional
    hook.

    Official v4 architecture also permits dynamic fees, hooks and custom
    accounting. Therefore the adapter must capture enough metadata to know
    whether standard concentrated-liquidity assumptions remain valid.

§18.8.2 says why address-based ingestion breaks:

    Because many pools emit through the same manager contract, filtering by
    contract address is insufficient.

    Required key:

        (chain_id, pool_manager, pool_id)

and §18.8.1 requires a reconstruction class per pool:

    STANDARD_CL
    DYNAMIC_FEE_CL
    HOOK_AUGMENTED_CL
    CUSTOM_ACCOUNTING
    UNKNOWN

with the rule that `CUSTOM_ACCOUNTING` means *"do not assume the standard curve"*
and `UNKNOWN` means *"raw data only; exclude from predictive depth features"*.

**One address, every pool.** This is the failure that has no symptom: a
v3-shaped ingestion keyed on `(chain_id, address)` files every v4 pool on the
chain under one key, and the resulting tick map is a superposition of thousands
of pools that is internally consistent and describes nothing.

**A `PoolId` is a hash, so it cannot be inverted.** The preimage appears in
exactly one place — the `Initialize` event — so a registry built from anything
else cannot resolve a `Swap`. And the hash is over five whole words, with
`int24 tickSpacing` sign-extended: pack it instead and every id is wrong; extend
the sign wrongly and only the pools with negative spacing are wrong, which is
worse.

**The hook's permissions are in the hook's address.** Not its code, not a call —
the low fourteen bits of the address. That is what makes §18.8.1's
classification possible offline, and therefore possible in a replay where
Principle I forbids reaching for the present.

**Four of those bits are the dangerous ones.** The "returns delta" permissions
are exactly what let a hook change the amounts a swap moves, which is the
difference between a hook running alongside the curve and the curve no longer
describing the pool.

## Acceptance

- A pool id is derived from its key and matches the id the manager computed, on
  real `Initialize` logs at a named block range.
- A pool with a negative tick spacing is covered, or the sign extension is
  otherwise shown to be exercised.
- Events route on `(chain_id, pool_manager, pool_id)`, and the emitting address
  is shown to be insufficient — measured, on a real chain.
- Every one of §18.8.1's five classes is produced, and each of the four that can
  exist on chain is produced from a real pool.
- A hook holding any "returns delta" permission classifies as
  `CUSTOM_ACCOUNTING`, ahead of any other class it also qualifies for.
- A key the manager would have rejected classifies as `UNKNOWN`, not as whatever
  its bits resemble.
- Asking a dynamic-fee pool's key for its fee is refused; §18.8.1 requires the
  effective fee to be point-in-time.
- An event for a pool id never initialised is refused, not resolved to a guess.
- The fixtures are chain reads over a named block range, captured by a committed
  tool, and no test opens a socket.

## Notes

Human territory. Never machine-rewritten.

**The manager address is discovered rather than recalled**, by scanning for the
`Initialize` topic and refusing if more than one contract emitted it. That check
doubles as the measurement §18.8.2 asks to be believed: 2960 pools in a
forty-thousand-block window, one address.

**`isDynamicFee` is equality, not a bit test.** The source compares the fee to
`0x800000` exactly, so `0x800001` is not a dynamic fee — it is an invalid fee the
manager rejects. A bit test would classify it as dynamic and quote it.

**A static-fee pool with a swap hook is not a static-fee pool.** `beforeSwap`
may return `OVERRIDE_FEE_FLAG` and replace the LP fee for that swap, so the
key's fee is not the fee charged. This requirement treats such a pool as
`DYNAMIC_FEE_CL` for that reason, which is a reading of §18.8.1's rule rather
than a quotation of it.

**Quoting is out of scope**, deliberately. §18.8.1 says `CUSTOM_ACCOUNTING`
pools want an "executable quoting/simulation adapter", which is a different piece
of work from knowing which pools need one. Classification first.
