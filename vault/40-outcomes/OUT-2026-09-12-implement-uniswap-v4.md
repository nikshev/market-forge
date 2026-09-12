---
id: OUT-2026-09-12-implement-uniswap-v4
step: implement
records: [REQ-WP-047]
commit: null
---

## What was done

`tools/record/uniswap_v4_capture.py`, a fixture of real `Initialize` logs, and
`dex/uniswap_v4.py` — pool id derivation, singleton event routing and §18.8.1's
hook safety classification. 74 tests, **25 of 25 mutants caught**.

## The one fixture that can prove the mapping

`Initialize` is the only event whose data contains a `PoolId`'s preimage: it
carries the id the singleton computed *and* every field of the key it computed
it from. Everything else — a `Swap`, a `ModifyLiquidity` — carries the id alone,
and a hash cannot be inverted.

So the id derivation is checked against the chain's own hash rather than against
a reading of `PoolIdLibrary`. Sixteen pools, sixteen exact.

That matters because the two plausible ways to get it wrong fail differently.
Packing the fields instead of ABI-encoding them makes *every* id wrong, which is
loud. Sign-extending `int24 tickSpacing` wrongly makes only the negative-spacing
pools wrong, which is quiet — most of the system keeps working.

## §18.8.2's claim, measured rather than repeated

The capture discovers the manager by scanning for the `Initialize` topic and
**refuses if more than one contract emitted it**. That check is also the
measurement: **2960 pools initialised in a forty-thousand-block window, all
through one address.**

A v3-shaped ingestion keyed on `(chain_id, address)` files all of them under one
key. The tick map that falls out is a superposition of thousands of pools —
internally consistent, and describing nothing.

## The permissions are in the address

Not in the hook's code, and not behind a call: `Hooks.sol` reads the low
fourteen bits of the hook's address, and a hook is deployed to an address whose
bits match what it implements. That is what makes the safety classification
computable **offline**, and therefore computable in a replay, where Principle I
forbids reaching for the present.

Four of those bits do the real work — the "returns delta" permissions, which are
exactly what let a hook change the amounts a swap moves. That is the line
between "a hook runs alongside the curve" and "the curve no longer describes
this pool".

## Three readings that go beyond quoting the PRD

- **The classes are not mutually exclusive, so the answer must forbid the most.**
  A pool can be dynamic-fee *and* returns-delta. `CUSTOM_ACCOUNTING` wins; calling
  it `DYNAMIC_FEE_CL` would say "depth is fine, mind the fee" about a pool whose
  curve does not apply.
- **A static-fee pool with a swap hook is not a static-fee pool.** `beforeSwap`
  may return `OVERRIDE_FEE_FLAG` and replace the LP fee for that swap, so the
  key's fee is not the fee charged. Treated as `DYNAMIC_FEE_CL`.
- **`isDynamicFee` is equality, not a bit test.** `0x800001` has the sentinel's
  high bit and is *not* a dynamic fee — it is an invalid fee the manager rejects.
  A bit test would classify it as dynamic and quote it.

`UNKNOWN` has no live instance and needs none: every key the manager accepted is
valid by construction, so the only way to reach the class is with keys the
manager would have rejected, which is what it is for. Seven of them are tested,
including all four returns-delta-without-its-action pairings.

## Twenty-five of twenty-five

The first clean sweep in this phase. Worth noting *why*, because it is not that
this module is better written: it is that almost every line here is a
classification with a discrete answer, and a discrete answer is easy to assert
exactly. The Curve and Aerodrome ports left survivors in the branches no real
state reaches; this module has no such branches, because its inputs are
enumerable.

One test was wrong in the first draft and instructively so: the "hook address
with no permissions" case used `0x40` repeated, whose low fourteen bits are
`afterSwap`. It was a valid hook, and the case proved nothing.

## What is still open

- **Quoting a `CUSTOM_ACCOUNTING` pool.** §18.8.1 asks for an executable
  quoting adapter; knowing which pools need one is the prior work and is what
  this delivers.
- **Effective LP fee history.** §18.8 lists it among what to track, the `Swap`
  event carries it, and nothing consumes it yet.
